"""Core GTD file operations for the Hermes plugin."""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


class GTDError(Exception):
    """Base error for expected GTD operation failures."""


class GTDValidationError(GTDError):
    """Raised when user supplied arguments are invalid."""


TARGETS = {
    "trash",
    "reference",
    "someday_maybe",
    "done",
    "next_actions",
    "waiting_for",
    "projects",
}

PREFIX_FILES = {
    "N": "next_actions.md",
    "W": "waiting_for.md",
    "P": "projects.md",
}

DEFAULT_CONFIG = {
    "user_name": "用户",
    "preferred_contexts": ["@电脑", "@电话", "@家"],
    "work_hours": {"start": "09:00", "end": "18:00"},
    "review": {"day": "周日", "time": "20:00", "enabled": True},
    "notifications": {
        "daily_digest": True,
        "deadline_reminder": True,
        "waiting_followup": True,
    },
    "auto_archive": True,
}


def _optional_yaml():
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    return yaml


def get_gtd_dir() -> Path:
    """Resolve the GTD data directory for the current call."""

    return Path(os.path.expanduser(os.environ.get("GTD_DIR", "~/gtd"))).resolve()


def gtd_path(filename: str) -> Path:
    return get_gtd_dir() / filename


def local_date() -> date:
    override = os.environ.get("GTD_TODAY")
    if override:
        return datetime.strptime(override, "%Y-%m-%d").date()
    return date.today()


def local_datetime() -> datetime:
    override = os.environ.get("GTD_NOW")
    if override:
        return datetime.strptime(override, "%Y-%m-%d %H:%M")
    return datetime.now()


def today_str() -> str:
    return local_date().strftime("%Y-%m-%d")


def now_str() -> str:
    return local_datetime().strftime("%Y-%m-%d %H:%M")


def time_str() -> str:
    return local_datetime().strftime("%H:%M")


def validate_date(value: str, field_name: str = "date") -> None:
    if not value:
        return
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise GTDValidationError(f"{field_name} 必须使用 YYYY-MM-DD 格式") from exc


def ensure_gtd_dir() -> Path:
    gtd_dir = get_gtd_dir()
    gtd_dir.mkdir(parents=True, exist_ok=True)
    (gtd_dir / "archive").mkdir(parents=True, exist_ok=True)
    (gtd_dir / "reviews").mkdir(parents=True, exist_ok=True)
    return gtd_dir


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        write_text(path, "# GTD\n\n")
    with path.open("a", encoding="utf-8") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")


def _without_code_fences(content: str) -> str:
    kept: list[str] = []
    in_fence = False
    for line in content.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            kept.append(line)
    return "\n".join(kept)


def count_tasks(content: str) -> tuple[int, int]:
    visible_content = _without_code_fences(content)
    pending = len(re.findall(r"^- \[ \]", visible_content, flags=re.MULTILINE))
    completed = len(re.findall(r"^- \[x\]", visible_content, flags=re.MULTILINE))
    return pending, completed


def parse_date_field(line: str, field_name: str) -> str | None:
    names = {
        "added": ["added", "添加"],
        "deadline": ["deadline", "截止"],
        "estimated": ["estimated", "预计", "expected"],
        "asked": ["asked", "询问日期", "询问"],
        "completed": ["completed", "完成"],
    }.get(field_name, [field_name])

    for name in names:
        match = re.search(rf"{re.escape(name)}:\s*(\d{{4}}-\d{{2}}-\d{{2}})", line)
        if match:
            return match.group(1)
    return None


def get_week_range() -> tuple[date, date]:
    today = local_date()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


FILE_TEMPLATES = {
    "inbox.md": """# 收集箱

> 快速记录任何想法，稍后整理。

---

""",
    "projects.md": """# 项目清单

项目 = 任何需要多步骤完成的事项。

## 活跃项目

（暂无活跃项目）

## 暂停项目

（暂无暂停项目）

---

### 项目模板

```
### PXXX: 项目名称
- **目标**: 项目完成的标准
- **状态**: 活跃/暂停/已完成
- **下一步**: [[next_actions.md#NXXX|行动编号]]
- **笔记**: 相关链接或备注
```
""",
    "next_actions.md": """# 下一步行动

按情境分类，使用动词开头描述具体行动。

## @电脑

（暂无）

## @电话

（暂无）

## @外出

（暂无）

## @家

（暂无）

## @办公室

（暂无）

## @任意

（暂无）

---

### 行动编号模板

```
- [ ] NXXX: 动词 + 具体内容 (context: @情境, deadline: YYYY-MM-DD)
```
""",
    "waiting_for.md": """# 等待清单

记录所有委派给他人、等待反馈的事项。

---

> 格式：`- [ ] WXXX: 事项描述 (询问日期: YYYY-MM-DD, 预计: YYYY-MM-DD, 委派给: 姓名)`

""",
    "someday_maybe.md": """# 将来/也许

暂时不执行但想保留的想法。

## 学习成长

（暂无）

## 生活兴趣

（暂无）

## 职业发展

（暂无）

## 旅行计划

（暂无）

""",
    "calendar.md": """# 日历

## {year}年{month}月

### 本周

-

### 下周

-

### 本月重要日期

-

""",
    "reference.md": """# 参考资料

存储有用的信息、想法、资源链接。

---

## 快速链接

- GTD 原则: https://gettingthingsdone.com/

## 笔记

（在此添加参考资料）

""",
    "trash.md": """# 垃圾箱

记录从收集箱丢弃的条目，便于短期追溯。

---

""",
}


def init_gtd() -> dict[str, Any]:
    gtd_dir = ensure_gtd_dir()
    today = today_str()
    values = {"year": today[:4], "month": today[5:7]}

    created: list[str] = []
    skipped: list[str] = []
    for filename, template in FILE_TEMPLATES.items():
        path = gtd_dir / filename
        if path.exists():
            skipped.append(filename)
            continue
        write_text(path, template.format(**values))
        created.append(filename)

    config_path = get_config_path()
    if not config_path.exists():
        save_config(deepcopy(DEFAULT_CONFIG))
        created.append(config_path.name)
    else:
        skipped.append(config_path.name)

    return {
        "gtd_dir": str(gtd_dir),
        "created": created,
        "skipped": skipped,
    }


def capture(content: str) -> dict[str, Any]:
    content = (content or "").strip()
    if not content:
        raise GTDValidationError("content 不能为空")

    ensure_gtd_dir()
    inbox = gtd_path("inbox.md")
    if not inbox.exists():
        write_text(inbox, FILE_TEMPLATES["inbox.md"])

    existing = read_text(inbox)
    today = today_str()
    entry_prefix = "" if existing.endswith("\n") else "\n"
    if f"## {today}" not in existing:
        entry_prefix += f"\n## {today}\n\n"
    entry = f"{entry_prefix}- [ ] {content} (added: {today} {time_str()})\n"
    append_text(inbox, entry)
    return {"content": content, "date": today, "gtd_dir": str(get_gtd_dir())}


@dataclass(frozen=True)
class InboxItem:
    index: int
    line_index: int
    date: str
    raw: str
    content: str


def read_inbox_items() -> list[InboxItem]:
    inbox = gtd_path("inbox.md")
    if not inbox.exists():
        return []

    lines = inbox.read_text(encoding="utf-8").splitlines()
    items: list[InboxItem] = []
    current_date = ""
    for line_index, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped.startswith("## "):
            current_date = stripped.replace("## ", "", 1).strip()
        elif raw.startswith("- [ ]"):
            content = raw.replace("- [ ]", "", 1).strip()
            if content:
                items.append(
                    InboxItem(
                        index=len(items) + 1,
                        line_index=line_index,
                        date=current_date,
                        raw=raw,
                        content=content,
                    )
                )
    return items


def clean_content(item_or_content: InboxItem | str) -> str:
    content = item_or_content.content if isinstance(item_or_content, InboxItem) else item_or_content
    content = re.sub(r"\s*\(added:\s*[^)]+\)\s*$", "", content)
    return content.strip()


def remove_inbox_item(item: InboxItem) -> None:
    inbox = gtd_path("inbox.md")
    lines = inbox.read_text(encoding="utf-8").splitlines(keepends=True)
    if item.line_index >= len(lines) or lines[item.line_index].rstrip("\n") != item.raw:
        raise GTDError("收集箱已变化，请重新读取后再处理")

    del lines[item.line_index]
    content = "".join(lines)
    content = re.sub(r"\n{3,}", "\n\n", content)
    write_text(inbox, content)


def get_next_number(prefix: str) -> str:
    prefix = (prefix or "").upper()
    filename = PREFIX_FILES.get(prefix)
    if filename is None:
        raise GTDValidationError("prefix 必须是 N、W 或 P")

    content = read_text(gtd_path(filename))
    existing = [int(n) for n in re.findall(rf"\b{prefix}(\d{{3}})\b", content)]
    return f"{prefix}{(max(existing) + 1) if existing else 1:03d}"


def _append_target(filename: str, text: str) -> None:
    append_text(gtd_path(filename), text)


def process_inbox(
    index: int,
    target: str,
    *,
    context: str = "",
    deadline: str = "",
    delegate: str = "",
    estimated: str = "",
    project_name: str = "",
    first_action: str = "",
) -> dict[str, Any]:
    if target not in TARGETS:
        raise GTDValidationError(f"target 不支持: {target}")
    if index < 1:
        raise GTDValidationError("index 必须大于等于 1")
    validate_date(deadline, "deadline")
    validate_date(estimated, "estimated")

    items = read_inbox_items()
    if not items:
        raise GTDValidationError("收集箱是空的")
    if index > len(items):
        raise GTDValidationError(f"无效索引: {index}（共 {len(items)} 条）")

    item = items[index - 1]
    content = clean_content(item)
    result: dict[str, Any] = {
        "action": target,
        "content": content,
        "date": item.date,
    }

    if target == "trash":
        remove_inbox_item(item)
        _append_target("trash.md", f"- {content} (trashed: {today_str()})\n")
    elif target == "reference":
        remove_inbox_item(item)
        _append_target("reference.md", f"- {content} (archived: {today_str()})\n")
    elif target == "someday_maybe":
        remove_inbox_item(item)
        _append_target("someday_maybe.md", f"- [ ] {content} (added: {item.date or today_str()})\n")
    elif target == "done":
        remove_inbox_item(item)
        archive_file = gtd_path("archive") / today_str()[:4] / f"{today_str()[5:7]}_quick.md"
        append_text(archive_file, f"- [x] {content} (quick, completed: {today_str()})\n")
    elif target == "next_actions":
        number = get_next_number("N")
        action_context = context or "@任意"
        metadata = [f"context: {action_context}"]
        if deadline:
            metadata.append(f"deadline: {deadline}")
        remove_inbox_item(item)
        _append_target("next_actions.md", f"- [ ] {number}: {content} ({', '.join(metadata)})\n")
        result.update({"number": number, "context": action_context, "deadline": deadline})
    elif target == "waiting_for":
        number = get_next_number("W")
        metadata = [f"询问日期: {today_str()}"]
        if delegate:
            metadata.append(f"委派给: {delegate}")
        if estimated:
            metadata.append(f"预计: {estimated}")
        remove_inbox_item(item)
        _append_target("waiting_for.md", f"- [ ] {number}: {content} ({', '.join(metadata)})\n")
        result.update({"number": number, "delegate": delegate, "estimated": estimated})
    elif target == "projects":
        project_number = get_next_number("P")
        action_number = get_next_number("N")
        name = project_name or content
        first = first_action or f"明确 {name} 的下一步"
        remove_inbox_item(item)
        _append_target(
            "projects.md",
            "\n"
            f"### {project_number}: {name}\n"
            f"- **目标**: {content}\n"
            "- **状态**: 活跃\n"
            f"- **创建日期**: {today_str()}\n"
            f"- **下一步**: [[next_actions.md#{action_number}|{action_number}: {first}]]\n",
        )
        _append_target("next_actions.md", f"- [ ] {action_number}: {first} (context: @任意)\n")
        result.update(
            {
                "project_number": project_number,
                "action_number": action_number,
                "project_name": name,
                "first_action": first,
            }
        )

    return result


def parse_action_line(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    status_match = re.match(r"^- \[([ x])\]\s*", stripped)
    if not status_match:
        return None

    number_match = re.search(r"\b([NWP]\d{3}):", stripped)
    if not number_match:
        return None

    number = number_match.group(1)
    rest = stripped[status_match.end() :]
    rest = re.sub(rf"{re.escape(number)}:\s*", "", rest, count=1)
    metadata: dict[str, str] = {}
    meta_match = re.search(r"\((.+)\)\s*$", rest)
    if meta_match:
        meta = meta_match.group(1)
        rest = rest[: meta_match.start()].strip()
        for key, value in re.findall(r"([^:,]+):\s*([^,)]+)", meta):
            metadata[key.strip()] = value.strip()

    return {
        "done": status_match.group(1) == "x",
        "number": number,
        "content": rest.strip(),
        "context": metadata.get("context", ""),
        "deadline": metadata.get("deadline", ""),
        "completed": metadata.get("completed", ""),
    }


def list_actions(context: str = "", show_all: bool = False) -> list[dict[str, Any]]:
    content = read_text(gtd_path("next_actions.md"))
    actions: list[dict[str, Any]] = []
    current_context = ""
    for line in content.splitlines():
        if line.startswith("## @"):
            current_context = line.replace("## ", "", 1).strip()
            continue
        action = parse_action_line(line)
        if not action:
            continue
        if not action["context"] and current_context:
            action["context"] = current_context
        if action["done"] and not show_all:
            continue
        if context and context.lower() not in action["context"].lower():
            continue
        actions.append(action)

    def sort_key(action: dict[str, Any]) -> tuple[int, str]:
        return (0, action["deadline"]) if action["deadline"] else (1, action["number"])

    return sorted(actions, key=sort_key)


def complete_number(number: str) -> dict[str, Any]:
    number = (number or "").strip().upper()
    if re.fullmatch(r"\d{1,3}", number):
        number = f"N{int(number):03d}"
    if not re.fullmatch(r"[NWP]\d{3}", number):
        raise GTDValidationError("number 必须是 N001、W001 或 P001 这样的编号")

    prefix = number[0]
    if prefix == "P":
        return complete_project(number)
    return complete_task_line(number, PREFIX_FILES[prefix])


def complete_task_line(number: str, filename: str) -> dict[str, Any]:
    path = gtd_path(filename)
    content = read_text(path)
    if not content:
        raise GTDValidationError(f"文件不存在或为空: {filename}")

    if re.search(rf"^- \[x\]\s*{re.escape(number)}:", content, flags=re.MULTILINE):
        return {"number": number, "file": filename, "already_completed": True}

    pattern = rf"^(- \[ \]\s*{re.escape(number)}:.*)$"
    if not re.search(pattern, content, flags=re.MULTILINE):
        raise GTDValidationError(f"未找到任务: {number}")

    def mark(match: re.Match[str]) -> str:
        line = match.group(1)
        if "completed:" in line:
            return line.replace("- [ ]", "- [x]", 1)
        return line.replace("- [ ]", "- [x]", 1) + f" (completed: {today_str()})"

    write_text(path, re.sub(pattern, mark, content, count=1, flags=re.MULTILINE))
    return {"number": number, "file": filename, "completed": today_str()}


def _project_blocks(content: str) -> list[tuple[int, int, str]]:
    matches = list(re.finditer(r"^###\s+P\d{3}:.*$", content, flags=re.MULTILINE))
    blocks = []
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        blocks.append((match.start(), end, content[match.start() : end]))
    return blocks


def complete_project(number: str) -> dict[str, Any]:
    path = gtd_path("projects.md")
    content = read_text(path)
    if not content:
        raise GTDValidationError("projects.md 不存在或为空")

    for start, end, block in _project_blocks(content):
        if not re.match(rf"^###\s+{re.escape(number)}:", block):
            continue
        if "- **状态**: 已完成" in block:
            return {"number": number, "file": "projects.md", "already_completed": True}

        if re.search(r"^- \*\*状态\*\*:", block, flags=re.MULTILINE):
            block = re.sub(
                r"^- \*\*状态\*\*:.*$",
                "- **状态**: 已完成",
                block,
                count=1,
                flags=re.MULTILINE,
            )
        else:
            block = block.rstrip() + "\n- **状态**: 已完成\n"

        if re.search(r"^- \*\*完成日期\*\*:", block, flags=re.MULTILINE):
            block = re.sub(
                r"^- \*\*完成日期\*\*:.*$",
                f"- **完成日期**: {today_str()}",
                block,
                count=1,
                flags=re.MULTILINE,
            )
        else:
            block = block.rstrip() + f"\n- **完成日期**: {today_str()}\n"

        write_text(path, content[:start] + block + content[end:])
        return {"number": number, "file": "projects.md", "completed": today_str()}

    raise GTDValidationError(f"未找到项目: {number}")


def archive_completed() -> dict[str, Any]:
    archived: list[str] = []
    for filename in ("next_actions.md", "waiting_for.md"):
        path = gtd_path(filename)
        lines = read_text(path).splitlines(keepends=True)
        if not lines:
            continue
        kept: list[str] = []
        for line in lines:
            if re.match(r"^- \[x\].*\(completed:\s*\d{4}-\d{2}-\d{2}\)", line):
                archived.append(f"{filename}: {line.strip()}")
            else:
                kept.append(line)
        if len(kept) != len(lines):
            write_text(path, re.sub(r"\n{3,}", "\n\n", "".join(kept)))

    projects = read_text(gtd_path("projects.md"))
    if projects:
        kept_parts: list[str] = []
        cursor = 0
        for start, end, block in _project_blocks(projects):
            kept_parts.append(projects[cursor:start])
            if "- **状态**: 已完成" in block:
                archived.append(f"projects.md: {block.strip()}")
            else:
                kept_parts.append(block)
            cursor = end
        kept_parts.append(projects[cursor:])
        if "".join(kept_parts) != projects:
            write_text(gtd_path("projects.md"), re.sub(r"\n{3,}", "\n\n", "".join(kept_parts)))

    if archived:
        archive_file = gtd_path("archive") / today_str()[:4] / f"{today_str()[5:7]}_completed.md"
        append_text(archive_file, f"\n## {today_str()}\n" + "\n".join(archived) + "\n")

    return {"archived_count": len(archived), "items": archived}


def get_calendar_items() -> list[str]:
    content = read_text(gtd_path("calendar.md"))
    if not content:
        return []

    items: list[str] = []
    in_today = False
    today = today_str()
    for line in content.splitlines():
        if today in line or "今天" in line:
            in_today = True
            continue
        if in_today:
            if line.startswith("#"):
                break
            if line.strip().startswith("-") and line.strip() != "-":
                items.append(line.strip())
    return items


def get_urgent_actions() -> tuple[list[str], list[str]]:
    content = read_text(gtd_path("next_actions.md"))
    today = local_date()
    tomorrow = today + timedelta(days=1)
    today_tasks: list[str] = []
    tomorrow_tasks: list[str] = []

    for line in content.splitlines():
        if not line.startswith("- [ ]"):
            continue
        deadline_str = parse_date_field(line, "deadline")
        if not deadline_str:
            continue
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        if deadline == today:
            today_tasks.append(line.strip())
        elif deadline == tomorrow:
            tomorrow_tasks.append(line.strip())
    return today_tasks, tomorrow_tasks


def get_waiting_followups() -> list[str]:
    content = read_text(gtd_path("waiting_for.md"))
    today = local_date()
    followups: list[str] = []
    for line in content.splitlines():
        if not line.startswith("- [ ]"):
            continue
        estimated = parse_date_field(line, "estimated")
        asked = parse_date_field(line, "asked")
        if estimated and datetime.strptime(estimated, "%Y-%m-%d").date() <= today:
            followups.append(line.strip())
        elif asked and (today - datetime.strptime(asked, "%Y-%m-%d").date()).days >= 3:
            followups.append(line.strip())
    return followups


def daily_check() -> dict[str, Any]:
    today_tasks, tomorrow_tasks = get_urgent_actions()
    followups = get_waiting_followups()
    return {
        "date": today_str(),
        "calendar": [{"item": item} for item in get_calendar_items()],
        "today_deadlines": [{"task": item} for item in today_tasks],
        "tomorrow_deadlines": [{"task": item} for item in tomorrow_tasks],
        "followups": [{"task": item} for item in followups],
        "urgent_count": len(today_tasks) + len(tomorrow_tasks),
        "followup_count": len(followups),
    }


def count_active_projects(content: str) -> int:
    count = 0
    for _, _, block in _project_blocks(content):
        if "- **状态**: 已完成" not in block:
            count += 1
    return count


def get_archive_stats() -> int:
    archive_dir = gtd_path("archive")
    if not archive_dir.exists():
        return 0
    total = 0
    for path in archive_dir.rglob("*.md"):
        total += count_tasks(read_text(path))[1]
    return total


def weekly_stats() -> dict[str, Any]:
    monday, _ = get_week_range()
    inbox_content = read_text(gtd_path("inbox.md"))
    next_content = read_text(gtd_path("next_actions.md"))
    waiting_content = read_text(gtd_path("waiting_for.md"))
    projects_content = read_text(gtd_path("projects.md"))

    new_items = 0
    for line in inbox_content.splitlines():
        added = parse_date_field(line, "added")
        if added and datetime.strptime(added, "%Y-%m-%d").date() >= monday:
            new_items += 1

    pending_n, completed_n = count_tasks(next_content)
    pending_w, _ = count_tasks(waiting_content)
    return {
        "new_items": new_items,
        "pending_actions": pending_n,
        "completed_actions": completed_n,
        "waiting": pending_w,
        "projects": count_active_projects(projects_content),
    }


def collect_weekly_data() -> dict[str, Any]:
    monday, sunday = get_week_range()
    stats = weekly_stats()
    next_content = read_text(gtd_path("next_actions.md"))
    waiting_content = read_text(gtd_path("waiting_for.md"))

    completed_this_week = 0
    overdue: list[str] = []
    for line in next_content.splitlines():
        completed = parse_date_field(line, "completed")
        if completed:
            completed_date = datetime.strptime(completed, "%Y-%m-%d").date()
            if monday <= completed_date <= sunday:
                completed_this_week += 1
        deadline = parse_date_field(line, "deadline")
        if deadline and line.startswith("- [ ]"):
            deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
            if deadline_date < local_date():
                overdue.append(line.strip())

    stale_waiting: list[str] = []
    for line in waiting_content.splitlines():
        if not line.startswith("- [ ]"):
            continue
        asked = parse_date_field(line, "asked")
        if asked and (local_date() - datetime.strptime(asked, "%Y-%m-%d").date()).days >= 3:
            stale_waiting.append(line.strip())

    return {
        "new_items": stats["new_items"],
        "completed_this_week": completed_this_week,
        "pending_actions": stats["pending_actions"],
        "waiting_count": stats["waiting"],
        "project_count": stats["projects"],
        "overdue": overdue,
        "stale_waiting": stale_waiting,
    }


def create_weekly_review() -> dict[str, Any]:
    monday, sunday = get_week_range()
    review_dir = gtd_path("reviews")
    review_dir.mkdir(parents=True, exist_ok=True)
    path = review_dir / f"{monday.strftime('%Y-%m-%d')}_weekly.md"
    data = collect_weekly_data()

    if not path.exists():
        overdue = "\n".join(f"- {item}" for item in data["overdue"]) or "（无过期任务）"
        stale = "\n".join(f"- {item}" for item in data["stale_waiting"]) or "（无需跟进事项）"
        content = f"""# 周回顾 - {monday.strftime('%Y-%m-%d')} ~ {sunday.strftime('%Y-%m-%d')}

回顾日期: {now_str()}

## 检查清单

- [ ] 清空收集箱
- [ ] 回顾日历
- [ ] 回顾项目清单
- [ ] 回顾下一步行动
- [ ] 回顾等待清单
- [ ] 回顾将来/也许

## 自动统计

| 指标 | 数值 |
|------|------|
| 本周新增想法 | {data['new_items']} |
| 本周完成任务 | {data['completed_this_week']} |
| 待办任务 | {data['pending_actions']} |
| 等待中 | {data['waiting_count']} |
| 活跃项目 | {data['project_count']} |

## 过期任务

{overdue}

## 需跟进的等待事项

{stale}

## 回顾笔记

### 本周成就

-

### 下周重点

-
"""
        write_text(path, content)

    return {"filepath": str(path), **data}


def get_config_path() -> Path:
    yaml = _optional_yaml()
    if yaml is not None:
        return gtd_path("config.yaml")
    return gtd_path("config.json")


def load_config() -> dict[str, Any]:
    yaml = _optional_yaml()
    yaml_path = gtd_path("config.yaml")
    json_path = gtd_path("config.json")

    config: dict[str, Any] = {}
    if yaml is not None and yaml_path.exists():
        loaded = yaml.safe_load(read_text(yaml_path)) or {}
        if isinstance(loaded, dict):
            config = loaded
    elif json_path.exists():
        loaded = json.loads(read_text(json_path) or "{}")
        if isinstance(loaded, dict):
            config = loaded

    merged = deepcopy(DEFAULT_CONFIG)
    _merge_dict(merged, config)
    if not yaml_path.exists() and not json_path.exists():
        save_config(merged)
    return merged


def save_config(config: dict[str, Any]) -> Path:
    ensure_gtd_dir()
    yaml = _optional_yaml()
    path = get_config_path()
    if yaml is not None:
        write_text(path, yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
    else:
        write_text(path, json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    return path


def _merge_dict(base: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(base.get(key), dict) and isinstance(value, dict):
            _merge_dict(base[key], value)
        else:
            base[key] = value


def get_config(key: str | None = None) -> Any:
    config = load_config()
    if not key:
        return config
    current: Any = config
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _coerce_config_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    lowered = value.lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def set_config(key: str, value: Any) -> dict[str, Any]:
    if not key:
        raise GTDValidationError("key 不能为空")

    config = load_config()
    current = config
    parts = key.split(".")
    for part in parts[:-1]:
        nested = current.setdefault(part, {})
        if not isinstance(nested, dict):
            raise GTDValidationError(f"配置路径不是对象: {part}")
        current = nested
    current[parts[-1]] = _coerce_config_value(value)
    path = save_config(config)
    return {"key": key, "value": current[parts[-1]], "config_file": str(path)}
