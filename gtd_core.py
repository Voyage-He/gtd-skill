"""Core GTD file operations for the Hermes plugin."""

from __future__ import annotations

import json
import hashlib
import mimetypes
import os
import re
import shutil
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

REFERENCE_ID_RE = re.compile(r"^R\d{8}-\d{3}$")
GTD_RELATED_ITEM_RE = re.compile(r"^[NWP]\d{3}$")
REFERENCE_KINDS = {"memo", "link", "file"}
REFERENCE_READ_POLICIES = {"metadata_only", "preview_allowed", "read_on_request"}
REFERENCE_MANAGED_MODES = {"link", "copy"}
REFERENCE_HASH_LIMIT_BYTES = 10 * 1024 * 1024
REFERENCE_READ_LIMIT_CHARS = 4000

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
    references = gtd_dir / "references"
    (references / "cards").mkdir(parents=True, exist_ok=True)
    (references / "assets").mkdir(parents=True, exist_ok=True)
    (references / "cache").mkdir(parents=True, exist_ok=True)
    index = references / "index.jsonl"
    if not index.exists():
        write_text(index, "")
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


def reference_root() -> Path:
    return get_gtd_dir() / "references"


def reference_cards_dir() -> Path:
    return reference_root() / "cards"


def reference_assets_dir() -> Path:
    return reference_root() / "assets"


def reference_cache_dir() -> Path:
    return reference_root() / "cache"


def reference_index_path() -> Path:
    return reference_root() / "index.jsonl"


def _normalize_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[,，\n]", value) if part.strip()]
    if isinstance(value, list):
        return [str(part).strip() for part in value if str(part).strip()]
    return [str(value).strip()]


def _normalize_reference_id(reference_id: str) -> str:
    normalized = (reference_id or "").strip().upper()
    if not REFERENCE_ID_RE.fullmatch(normalized):
        raise GTDValidationError("reference_id 必须类似 R20260507-001")
    return normalized


def _validate_related_item(item: str) -> str:
    item = (item or "").strip()
    upper = item.upper()
    if GTD_RELATED_ITEM_RE.fullmatch(upper):
        return upper
    if item.startswith("inbox:") and len(item) > len("inbox:"):
        return item
    raise GTDValidationError("related_item 必须是 N001、W001、P001 或 inbox:<原文>")


def _reference_card_path(reference_id: str) -> Path:
    return reference_cards_dir() / f"{_normalize_reference_id(reference_id)}.md"


def next_reference_id() -> str:
    ensure_gtd_dir()
    prefix = f"R{local_date().strftime('%Y%m%d')}"
    existing: list[int] = []
    for path in reference_cards_dir().glob(f"{prefix}-*.md"):
        match = re.fullmatch(rf"{re.escape(prefix)}-(\d{{3}})\.md", path.name)
        if match:
            existing.append(int(match.group(1)))
    return f"{prefix}-{(max(existing) + 1) if existing else 1:03d}"


def _yaml_dump(data: dict[str, Any]) -> str:
    yaml = _optional_yaml()
    if yaml is not None:
        return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    return json.dumps(data, ensure_ascii=False, indent=2)


def _yaml_load(text: str) -> dict[str, Any]:
    yaml = _optional_yaml()
    if yaml is not None:
        loaded = yaml.safe_load(text) or {}
    else:
        loaded = json.loads(text or "{}")
    if not isinstance(loaded, dict):
        raise GTDValidationError("reference 资料卡 metadata 格式不正确")
    return loaded


def write_reference_card(data: dict[str, Any]) -> Path:
    ensure_gtd_dir()
    reference_id = _normalize_reference_id(data["reference_id"])
    note = str(data.get("note", "")).strip()
    metadata = dict(data)
    metadata.pop("note", None)
    content = f"---\n{_yaml_dump(metadata).rstrip()}\n---\n\n{note}\n"
    path = _reference_card_path(reference_id)
    write_text(path, content)
    return path


def read_reference_card(reference_id: str) -> dict[str, Any]:
    path = _reference_card_path(reference_id)
    if not path.exists():
        raise GTDValidationError(f"未找到 reference: {_normalize_reference_id(reference_id)}")
    content = read_text(path)
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", content, flags=re.DOTALL)
    if not match:
        raise GTDValidationError(f"reference 资料卡格式不正确: {path.name}")
    data = _yaml_load(match.group(1))
    data["note"] = match.group(2).strip()
    data["card_path"] = str(path)
    return data


def _reference_index_record(data: dict[str, Any]) -> dict[str, Any]:
    attachment = data.get("attachment") or {}
    searchable = [
        data.get("reference_id", ""),
        data.get("title", ""),
        data.get("kind", ""),
        data.get("source", ""),
        data.get("purpose", ""),
        data.get("project", ""),
        data.get("captured_at", ""),
        data.get("note", ""),
        attachment.get("name", ""),
        attachment.get("path", ""),
        attachment.get("original_path", ""),
    ]
    for field in ("tags", "aliases", "people", "related_items"):
        searchable.extend(_normalize_list(data.get(field)))
    return {
        "reference_id": data["reference_id"],
        "title": data.get("title", ""),
        "kind": data.get("kind", ""),
        "source": data.get("source", ""),
        "purpose": data.get("purpose", ""),
        "captured_at": data.get("captured_at", ""),
        "tags": _normalize_list(data.get("tags")),
        "aliases": _normalize_list(data.get("aliases")),
        "people": _normalize_list(data.get("people")),
        "project": data.get("project", ""),
        "related_items": _normalize_list(data.get("related_items")),
        "summary": data.get("summary", ""),
        "note": data.get("note", ""),
        "attachment": attachment,
        "search_text": " ".join(str(part).lower() for part in searchable if part),
    }


def _load_index_records() -> list[dict[str, Any]]:
    ensure_gtd_dir()
    records: list[dict[str, Any]] = []
    path = reference_index_path()
    if not path.exists():
        rebuild_reference_index()
        path = reference_index_path()
    index_damaged = False
    for line in read_text(path).splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            index_damaged = True
            continue
        if isinstance(record, dict):
            records.append(record)
        else:
            index_damaged = True
    if index_damaged:
        rebuild_reference_index()
        return _load_index_records()
    return records


def write_reference_index(records: list[dict[str, Any]]) -> None:
    lines = [json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records]
    write_text(reference_index_path(), ("\n".join(lines) + "\n") if lines else "")


def upsert_reference_index(data: dict[str, Any]) -> None:
    record = _reference_index_record(data)
    records = _load_index_records()
    if not records and any(reference_cards_dir().glob("R*.md")):
        rebuild_reference_index()
        records = _load_index_records()
    records = [item for item in records if item.get("reference_id") != data["reference_id"]]
    records.append(record)
    records.sort(key=lambda item: item.get("reference_id", ""))
    write_reference_index(records)


def rebuild_reference_index() -> dict[str, Any]:
    ensure_gtd_dir()
    records: list[dict[str, Any]] = []
    skipped: list[str] = []
    for path in sorted(reference_cards_dir().glob("R*.md")):
        try:
            records.append(_reference_index_record(read_reference_card(path.stem)))
        except GTDError:
            skipped.append(path.name)
    write_reference_index(records)
    return {"indexed": len(records), "skipped": skipped, "index_file": str(reference_index_path())}


def sanitize_filename_part(value: str, fallback: str = "未命名") -> str:
    text = (value or "").strip() or fallback
    text = re.sub(r"[\\/:*?\"<>|#\[\]\n\r\t]+", "_", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._ ")
    return text[:80] or fallback


def suggest_reference_filename(
    reference_id: str,
    title: str,
    *,
    purpose: str = "",
    source: str = "",
    owner: str = "",
    version: str = "v1",
    extension: str = "",
) -> str:
    reference_id = _normalize_reference_id(reference_id)
    subject = sanitize_filename_part(title, "资料")
    purpose_part = sanitize_filename_part(purpose, "")
    source_part = sanitize_filename_part(owner or source, "")
    version_part = sanitize_filename_part(version or "v1", "v1")
    subject_part = f"{subject}_{purpose_part}" if purpose_part else subject
    stem_parts = [reference_id, subject_part]
    if source_part:
        stem_parts.append(source_part)
    if version_part:
        stem_parts.append(version_part)
    ext = extension if extension.startswith(".") or not extension else f".{extension}"
    ext = re.sub(r"[^A-Za-z0-9.]", "", ext)
    return "__".join(stem_parts) + ext


def _infer_kind(kind: str = "", url: str = "", file_path: str = "") -> str:
    if kind:
        kind = kind.strip().lower()
        if kind not in REFERENCE_KINDS:
            raise GTDValidationError("kind 必须是 memo、link 或 file")
        return kind
    if file_path:
        return "file"
    if url:
        return "link"
    return "memo"


def _sha256_if_small(path: Path) -> tuple[str, str]:
    size = path.stat().st_size
    if size > REFERENCE_HASH_LIMIT_BYTES:
        return "", "skipped_large_file"
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest(), "computed"


def _build_attachment(
    reference_id: str,
    file_path: str,
    *,
    managed: str = "link",
    title: str = "",
    purpose: str = "",
    source: str = "",
    owner: str = "",
    version: str = "v1",
) -> tuple[dict[str, Any], str]:
    managed = (managed or "link").strip().lower()
    if managed not in REFERENCE_MANAGED_MODES:
        raise GTDValidationError("managed 必须是 link 或 copy")
    source_path = Path(os.path.expanduser(file_path)).resolve()
    if not source_path.exists() or not source_path.is_file():
        raise GTDValidationError(f"附件不存在或不是文件: {file_path}")

    ext = source_path.suffix
    suggested_name = suggest_reference_filename(
        reference_id,
        title or source_path.stem,
        purpose=purpose,
        source=source,
        owner=owner,
        version=version,
        extension=ext,
    )
    stored_path = source_path
    if managed == "copy":
        target_dir = reference_assets_dir() / today_str()[:4] / today_str()[5:7]
        target_dir.mkdir(parents=True, exist_ok=True)
        stored_path = target_dir / suggested_name
        if stored_path.resolve() != source_path:
            shutil.copy2(source_path, stored_path)

    sha256, hash_status = _sha256_if_small(source_path)
    mime, _ = mimetypes.guess_type(str(source_path))
    attachment = {
        "original_path": str(source_path),
        "path": str(stored_path),
        "name": stored_path.name,
        "original_name": source_path.name,
        "suggested_name": suggested_name,
        "size": source_path.stat().st_size,
        "mime": mime or "application/octet-stream",
        "ext": ext,
        "managed": managed,
        "sha256": sha256,
        "hash_status": hash_status,
    }
    return attachment, suggested_name


def add_reference(
    *,
    title: str = "",
    note: str = "",
    kind: str = "",
    url: str = "",
    file_path: str = "",
    tags: Any = None,
    aliases: Any = None,
    people: Any = None,
    project: str = "",
    related_items: Any = None,
    purpose: str = "",
    source: str = "",
    owner: str = "",
    version: str = "v1",
    read_policy: str = "metadata_only",
    managed: str = "link",
) -> dict[str, Any]:
    title = (title or "").strip()
    note = (note or "").strip()
    url = (url or "").strip()
    file_path = (file_path or "").strip()
    purpose = (purpose or "").strip()
    kind = _infer_kind(kind, url, file_path)
    if not (title or note or url or file_path):
        raise GTDValidationError("reference 至少需要 title、note、url 或 file_path 之一")
    if read_policy not in REFERENCE_READ_POLICIES:
        raise GTDValidationError("read_policy 必须是 metadata_only、preview_allowed 或 read_on_request")
    if kind == "file" and not file_path:
        raise GTDValidationError("kind=file 时必须提供 file_path")
    if kind == "link" and not url:
        raise GTDValidationError("kind=link 时必须提供 url")

    ensure_gtd_dir()
    reference_id = next_reference_id()
    related = [_validate_related_item(item) for item in _normalize_list(related_items)]
    attachment: dict[str, Any] = {}
    suggested_name = ""
    if file_path:
        attachment, suggested_name = _build_attachment(
            reference_id,
            file_path,
            managed=managed,
            title=title,
            purpose=purpose,
            source=source,
            owner=owner,
            version=version,
        )
    elif title:
        suggested_name = suggest_reference_filename(
            reference_id,
            title,
            purpose=purpose,
            source=source,
            owner=owner,
            version=version,
        )

    data = {
        "reference_id": reference_id,
        "title": title or note[:50] or url or (attachment.get("original_name") or "未命名资料"),
        "kind": kind,
        "source": source,
        "purpose": purpose,
        "captured_at": now_str(),
        "tags": _normalize_list(tags),
        "aliases": _normalize_list(aliases),
        "people": _normalize_list(people),
        "project": (project or "").strip(),
        "related_items": related,
        "read_policy": read_policy,
        "url": url,
        "attachment": attachment,
        "summary": note[:160],
        "suggested_name": suggested_name,
        "note": note,
    }
    card_path = write_reference_card(data)
    upsert_reference_index(data)
    return {"reference_id": reference_id, "card_path": str(card_path), "suggested_name": suggested_name, **data}


def get_reference(reference_id: str) -> dict[str, Any]:
    return read_reference_card(reference_id)


def search_references(query: str = "", *, related_item: str = "", limit: int = 10) -> dict[str, Any]:
    ensure_gtd_dir()
    if not reference_index_path().exists():
        rebuild_reference_index()
    query = (query or "").strip().lower()
    related = _validate_related_item(related_item) if related_item else ""
    limit = max(1, min(int(limit or 10), 50))
    results: list[dict[str, Any]] = []
    warnings: list[str] = []
    records = _load_index_records()
    if not records and any(reference_cards_dir().glob("R*.md")):
        rebuild_reference_index()
        records = _load_index_records()

    for record in records:
        match_fields: list[str] = []
        if related and related in _normalize_list(record.get("related_items")):
            match_fields.append("related_items")
        if query:
            field_values = {
                "title": record.get("title", ""),
                "kind": record.get("kind", ""),
                "source": record.get("source", ""),
                "purpose": record.get("purpose", ""),
                "captured_at": record.get("captured_at", ""),
                "project": record.get("project", ""),
                "tags": " ".join(_normalize_list(record.get("tags"))),
                "aliases": " ".join(_normalize_list(record.get("aliases"))),
                "people": " ".join(_normalize_list(record.get("people"))),
                "related_items": " ".join(_normalize_list(record.get("related_items"))),
                "note": record.get("note", ""),
                "attachment": " ".join(
                    str(record.get("attachment", {}).get(key, "")) for key in ("name", "path", "original_path")
                ),
            }
            for field, value in field_values.items():
                if query in str(value).lower():
                    match_fields.append(field)
        if (query or related) and not match_fields:
            continue
        card_path = _reference_card_path(record["reference_id"])
        if not card_path.exists():
            warnings.append(f"索引记录缺少资料卡: {record['reference_id']}")
            continue
        results.append(
            {
                "reference_id": record["reference_id"],
                "title": record.get("title", ""),
                "kind": record.get("kind", ""),
                "source": record.get("source", ""),
                "purpose": record.get("purpose", ""),
                "captured_at": record.get("captured_at", ""),
                "tags": record.get("tags", []),
                "aliases": record.get("aliases", []),
                "people": record.get("people", []),
                "project": record.get("project", ""),
                "related_items": record.get("related_items", []),
                "note": record.get("note", ""),
                "attachment": record.get("attachment", {}),
                "match_fields": sorted(set(match_fields)) or ["all"],
            }
        )
        if len(results) >= limit:
            break
    return {"results": results, "count": len(results), "warnings": warnings, "metadata_only": True}


def link_reference(reference_id: str, related_item: str) -> dict[str, Any]:
    related_item = _validate_related_item(related_item)
    data = read_reference_card(reference_id)
    related = _normalize_list(data.get("related_items"))
    if related_item not in related:
        related.append(related_item)
    data["related_items"] = related
    card_path = write_reference_card(data)
    upsert_reference_index(data)
    return {"reference_id": data["reference_id"], "related_items": related, "card_path": str(card_path)}


def _reference_read_range(read_chars: int, total_chars: int) -> dict[str, int | str]:
    return {"unit": "chars", "start": 0, "end": read_chars, "total": total_chars}


def read_reference(reference_id: str, *, max_chars: int = REFERENCE_READ_LIMIT_CHARS) -> dict[str, Any]:
    data = read_reference_card(reference_id)
    max_chars = max(1, min(int(max_chars or REFERENCE_READ_LIMIT_CHARS), 20000))
    attachment = data.get("attachment") or {}
    if not attachment:
        note = data.get("note", "")
        read_chars = min(len(note), max_chars)
        return {
            "reference_id": data["reference_id"],
            "content": note[:max_chars],
            "source": "note",
            "truncated": len(note) > max_chars,
            "range": _reference_read_range(read_chars, len(note)),
            "read_chars": read_chars,
            "total_chars": len(note),
        }
    path = Path(attachment.get("path") or attachment.get("original_path") or "")
    if not path.exists() or not path.is_file():
        raise GTDValidationError(f"附件不存在或无法读取: {path}")
    try:
        content = path.read_text(encoding="utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError as exc:
        raise GTDValidationError("附件不是可直接读取的 UTF-8 文本文件") from exc
    truncated = len(content) > max_chars
    read_chars = min(len(content), max_chars)
    return {
        "reference_id": data["reference_id"],
        "content": content[:max_chars],
        "source": "attachment",
        "file_path": str(path),
        "mime": attachment.get("mime", ""),
        "encoding": encoding,
        "truncated": truncated,
        "range": _reference_read_range(read_chars, len(content)),
        "read_chars": read_chars,
        "total_chars": len(content),
    }


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
