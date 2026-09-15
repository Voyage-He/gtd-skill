"""Shared-file CRUD for the optional browser interface."""
import hashlib
import json
import re
import uuid
from pathlib import Path

try:
    from . import gtd_core as core, storage
except ImportError:
    import gtd_core as core
    import storage

FILES = {"inbox": "inbox.md", "next_actions": "next_actions.md",
         "waiting_for": "waiting_for.md", "projects": "projects.md",
         "someday_maybe": "someday_maybe.md"}


class Conflict(core.GTDError):
    pass


def revision(text):
    return hashlib.sha256(text.encode()).hexdigest()


def records():
    result = []
    for category, filename in FILES.items():
        text = core.read_text(core.gtd_path(filename))
        spans = core._project_blocks(text) if category == "projects" else []
        if category != "projects":
            offset, fenced = 0, False
            for line in text.splitlines(keepends=True):
                if line.strip().startswith("```"):
                    fenced = not fenced
                if not fenced and line.startswith("- "):
                    spans.append((offset, offset + len(line), line))
                offset += len(line)
        for start, end, raw in spans:
            first = raw.splitlines()[0]
            number = re.match(r"^(?:### |\- \[[ x]\] )([NWP]\d+):", first)
            title = re.sub(r"^(?:### |\- (?:\[[ x]\] )?)(?:[NWP]\d+:\s*)?", "", first)
            result.append(dict(id=f"{category}:{start}", category=category,
                               number=number.group(1) if number else "",
                               title=title, raw=raw, start=start, end=end,
                               revision=revision(text), done=first.startswith("- [x]") or "**状态**: 已完成" in raw))
    for path in sorted(core.reference_cards_dir().glob("R*.md"), reverse=True):
        card = core.read_reference_card(path.stem)
        attachments = card.get("attachments") or ([card["attachment"]] if card.get("attachment") else [])
        downloads = [{"name": a.get("original_name") or a.get("name") or f"附件 {i}",
                      "size": a.get("size"), "available": Path(a.get("path", "")).is_file(),
                      "url": f"/api/files/{path.stem}/{i}"} for i, a in enumerate(attachments, 1)]
        result.append(dict(id=path.stem, category="materials", title=card.get("title", path.stem),
                           raw=card.get("note", ""), revision=revision(core.read_text(path)), card=card, downloads=downloads, done=False))
    for item in core.memory()["memories"]:
        result.append(dict(id=item["memory_id"], category="memories", title=item["content"],
                           raw=item["content"], memory=item, done=False,
                           revision=revision(json.dumps(item, sort_keys=True))))
    tasks = {r["number"]: r for r in result if r.get("number")}
    for record in result:
        record["related"] = []
    edges = core.relation_edges()
    for material in (r for r in result if r["category"] == "materials"):
        explicit = [e["item_id"] for e in edges if e["reference_id"] == material["id"]]
        sources = [number for number, task in tasks.items()
                   if re.search(r"\breference:\s*" + re.escape(material["id"]) + r"(?=[\s,)\]]|$)", task["raw"])]
        for number in dict.fromkeys(explicit + sources):
            task = tasks.get(number)
            material["related"].append(dict(id=task["id"] if task else None, number=number,
                                           title=task["title"] if task else "已归档或不在当前列表",
                                           source=number in sources, linked=number in explicit))
            if task:
                task["related"].append(dict(id=material["id"], title=material["title"], source=number in sources, linked=number in explicit))
    return result


def required(data, key):
    value = data.get(key, "")
    if not isinstance(value, str) or not value.strip():
        raise core.GTDValidationError(f"{key} 不能为空")
    return value.strip()


def operate(data):
    with storage.transaction(core.get_gtd_dir()):
        action = data.get("action")
        if action == "list":
            return {"records": records(), "directory": str(core.get_gtd_dir())}
        if action == "create":
            category = data.get("category")
            if category == "memories":
                core.memory("add", content=required(data, "content"), tags=data.get("tags", ""), source=data.get("source", ""))
            elif category == "materials":
                core.add_reference(title=required(data, "title"), note=data.get("note", ""),
                                   url=data.get("url", ""), tags=data.get("tags", ""))
            elif category in FILES:
                content = required(data, "content")
                if "\n" in content or "\r" in content:
                    raise core.GTDValidationError("任务标题请使用单行文字")
                core.capture(content)
                if category != "inbox":
                    core.process_inbox(len(core.read_inbox_items()), category,
                                       context=data.get("context", ""), deadline=data.get("deadline", ""))
            else:
                raise core.GTDValidationError("未知分类")
            return {"saved": True}
        if action not in {"update", "delete", "complete", "process"}:
            raise core.GTDValidationError("未知操作")
        item = next((r for r in records() if r["id"] == data.get("id")), None)
        if item is None or item["revision"] != data.get("revision"):
            raise Conflict("记录已被其他操作修改，请刷新后重试；编辑内容仍保留。")
        category = item["category"]
        if category == "memories":
            if action not in {"update", "delete"}:
                raise core.GTDValidationError("记忆没有完成状态")
            core.memory(action, memory_id=item["id"], expected_revision=item["memory"]["revision"],
                        content=data.get("content", ""), tags=data.get("tags"), source=data.get("source", ""))
        elif category == "materials":
            path = core._reference_card_path(item["id"])
            if action == "delete":
                core.write_text(core.gtd_path("web-trash") / "reference-cards" / path.name, core.read_text(path))
                storage.track(path)
                path.unlink()
                core.write_reference_index([r for r in core._load_index_records() if r["reference_id"] != item["id"]])
            elif action == "update":
                card = item["card"]
                if "related_items" in data:
                    related = data["related_items"]
                    if not isinstance(related, list) or any(not isinstance(n, str) for n in related):
                        raise core.GTDValidationError("关联任务必须是编号列表")
                    previous = core._normalize_list(card.get("related_items"))
                    available = {r.get("number") for r in records() if r.get("number")}
                    if any(n not in available and n not in previous for n in related):
                        raise Conflict("关联任务已变化，请刷新后重试")
                    for number in set(previous) - set(related):
                        core.relations(item["id"], "unlink", number)
                    for number in set(related) - set(previous):
                        core.relations(item["id"], "link", number)
                    card = core.read_reference_card(item["id"])
                card.update(title=required(data, "title"), note=data.get("note", ""),
                            tags=core._normalize_list(data.get("tags", "")))
                # Keep forwarded source text, attachments and analysis intact.
                core.write_reference_card(card)
                core.upsert_reference_index(card)
            else:
                raise core.GTDValidationError("资料不支持此操作")
        else:
            path = core.gtd_path(FILES[category])
            text = core.read_text(path)
            if action == "process":
                if category != "inbox":
                    raise core.GTDValidationError("只能整理收集箱条目")
                index = next(i.index for i in core.read_inbox_items() if i.raw == item["raw"].rstrip("\n") and sum(len(x) for x in text.splitlines(keepends=True)[:i.line_index]) == item["start"])
                target = required(data, "target")
                if target == "memories":
                    inbox_item = core.read_inbox_items()[index - 1]
                    core.memory("add", content=core.clean_content(inbox_item))
                    core.remove_inbox_item(inbox_item)
                elif target == "materials":
                    inbox_item = core.read_inbox_items()[index - 1]
                    content = core.clean_content(inbox_item)
                    core.add_reference(title=content[:60], note=content)
                    core.remove_inbox_item(inbox_item)
                elif target in {"next_actions", "waiting_for", "projects", "someday_maybe"}:
                    core.process_inbox(index, target)
                else:
                    raise core.GTDValidationError("未知整理分类")
                return {"saved": True}
            if action == "delete":
                core.write_text(core.gtd_path("web-trash") / (uuid.uuid4().hex + ".md"), item["raw"])
                replacement = ""
            elif action == "complete":
                number = re.search(r"\b([NWP]\d+):", item["raw"])
                if number:
                    core.complete_number(number.group(1))
                    return {"saved": True}
                replacement = item["raw"].replace("- [ ]", "- [x]", 1)
            else:
                replacement = required(data, "raw") + "\n"
                if category == "projects":
                    if replacement.splitlines()[0].split(":", 1)[0] != item["raw"].splitlines()[0].split(":", 1)[0] or len(core._project_blocks(replacement)) != 1:
                        raise core.GTDValidationError("请保留项目编号和标题标记")
                else:
                    if len(replacement.splitlines()) != 1 or not replacement.startswith("- "):
                        raise core.GTDValidationError("请保留单行 Markdown 列表格式")
                    old_number = re.search(r"\b([NWP]\d+):", item["raw"])
                    if old_number and not re.match(r"^- \[[ x]\] " + old_number.group(1) + ":", replacement):
                        raise core.GTDValidationError("请保留任务编号和复选框")
            core.write_text(path, text[:item["start"]] + replacement + text[item["end"]:])
        return {"saved": True}
