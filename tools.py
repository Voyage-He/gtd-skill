"""GTD plugin tool handlers for Hermes agent.

Each handler is a pure function that takes a params dict and returns a result.
All file I/O is delegated to the existing scripts under .claude/skills/gtd/scripts/
"""

import sys
import os
import json

# Ensure scripts directory is importable
_scripts_dir = os.path.join(
    os.path.dirname(__file__), ".claude", "skills", "gtd", "scripts"
)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


def _format_result(success, message, **extra):
    """统一返回格式"""
    result = {"ok": success, "message": message}
    result.update(extra)
    return json.dumps(result, ensure_ascii=False)


# ── gtd_init ──────────────────────────────────────────

def handle_init(_params):
    from init_gtd import init_gtd, GTD_DIR

    init_gtd()
    return _format_result(True, f"GTD 系统已初始化，目录: {GTD_DIR}")


# ── gtd_capture ───────────────────────────────────────

def handle_capture(params):
    from add_to_inbox import add_to_inbox

    content = params["content"]
    add_to_inbox(content)
    return _format_result(True, f"已记录: {content}")


# ── gtd_inbox ─────────────────────────────────────────

def handle_inbox(_params):
    from process_inbox import read_inbox_items, _clean_content

    items = read_inbox_items()
    if not items:
        return _format_result(True, "收集箱是空的", items=[], count=0)

    result_items = [
        {"index": it["index"], "content": _clean_content(it), "date": it["date"]}
        for it in items
    ]
    return _format_result(
        True,
        f"收集箱共 {len(items)} 条待处理",
        items=result_items,
        count=len(items),
    )


# ── gtd_inbox_process ─────────────────────────────────

def handle_inbox_process(params):
    from process_inbox import (
        read_inbox_items,
        _clean_content,
        move_to_trash,
        move_to_reference,
        move_to_someday,
        move_to_done,
        move_to_next_actions,
        move_to_waiting,
        move_to_projects,
    )

    index = params["index"]
    target = params["target"]

    items = read_inbox_items()
    if not items:
        return _format_result(False, "收集箱是空的")
    if index < 1 or index > len(items):
        return _format_result(False, f"无效索引: {index}（共 {len(items)} 条）")

    item = items[index - 1]

    dispatch = {
        "trash": lambda: move_to_trash(item),
        "reference": lambda: move_to_reference(item),
        "someday_maybe": lambda: move_to_someday(item),
        "done": lambda: move_to_done(item),
        "next_actions": lambda: move_to_next_actions(
            item,
            context=params.get("context", ""),
            deadline=params.get("deadline", ""),
        ),
        "waiting_for": lambda: move_to_waiting(
            item,
            delegate=params.get("delegate", ""),
            estimated=params.get("estimated", ""),
        ),
        "projects": lambda: move_to_projects(
            item,
            name=params.get("project_name", ""),
            action=params.get("first_action", ""),
        ),
    }

    result = dispatch[target]()
    return _format_result(
        True,
        f"已处理: [{target}] {_clean_content(item)}",
        **result,
    )


# ── gtd_next_number ───────────────────────────────────

def handle_next_number(params):
    from process_inbox import get_next_number

    prefix = params["prefix"]
    number = get_next_number(prefix)
    return _format_result(True, f"下一个可用编号: {number}", number=number)


# ── gtd_list_actions ──────────────────────────────────

def handle_list_actions(params):
    import os
    from gtd_utils import get_gtd_dir

    actions_file = os.path.join(get_gtd_dir(), "next_actions.md")
    if not os.path.exists(actions_file):
        return _format_result(True, "暂无待办事项", actions=[], count=0)

    from list_actions import parse_action_line

    with open(actions_file, "r", encoding="utf-8") as f:
        content = f.read()

    context_filter = params.get("context", "")
    show_all = params.get("show_all", False)

    actions = []
    current_context = ""

    for line in content.split("\n"):
        if line.startswith("## @"):
            current_context = line.replace("## ", "").strip()
        action = parse_action_line(line)
        if action:
            if not action["context"] and current_context:
                action["context"] = current_context
            if not action["done"] or show_all:
                if context_filter and context_filter.lower() not in action["context"].lower():
                    continue
                actions.append(
                    {
                        "number": action["number"],
                        "content": action["content"],
                        "context": action["context"],
                        "deadline": action["deadline"],
                        "done": action["done"],
                    }
                )

    return _format_result(
        True,
        f"找到 {len(actions)} 项任务",
        actions=actions,
        count=len(actions),
    )


# ── gtd_complete ──────────────────────────────────────

def handle_complete(params):
    from complete_action import find_and_complete

    number = params["number"]
    success = find_and_complete(number)
    if success:
        return _format_result(True, f"已标记完成: {number}")
    return _format_result(False, f"未找到任务: {number}")


# ── gtd_archive ───────────────────────────────────────

def handle_archive(_params):
    from complete_action import archive_completed

    archive_completed()
    return _format_result(True, "归档完成")


# ── gtd_daily_check ───────────────────────────────────

def handle_daily_check(_params):
    from datetime import datetime
    from daily_check import get_calendar_items, get_urgent_actions, get_waiting_followups

    today = datetime.now().strftime("%Y-%m-%d")
    calendar = get_calendar_items()
    today_tasks, tomorrow_tasks = get_urgent_actions()
    followups = get_waiting_followups()

    return _format_result(
        True,
        f"每日检查 - {today}",
        date=today,
        calendar=[{"item": c} for c in calendar],
        today_deadlines=[{"task": t} for t in today_tasks],
        tomorrow_deadlines=[{"task": t} for t in tomorrow_tasks],
        followups=[{"task": f} for f in followups],
        urgent_count=len(today_tasks) + len(tomorrow_tasks),
        followup_count=len(followups),
    )


# ── gtd_weekly_review ─────────────────────────────────

def handle_weekly_review(_params):
    from weekly_review import create_weekly_review, collect_weekly_data

    data = collect_weekly_data()
    filepath = create_weekly_review()

    return _format_result(
        True,
        f"周回顾已创建: {filepath}",
        filepath=filepath,
        new_items=data["new_items"],
        completed_this_week=data["completed_this_week"],
        pending_actions=data["pending_actions"],
        waiting_count=data["waiting_count"],
        project_count=data["project_count"],
        overdue_count=len(data["overdue"]),
        stale_waiting_count=len(data["stale_waiting"]),
    )


# ── gtd_stats ─────────────────────────────────────────

def handle_stats(_params):
    from gtd_stats import get_weekly_stats, get_archive_stats

    stats = get_weekly_stats()
    archive_total = get_archive_stats()
    total = stats["pending_actions"] + stats["completed_actions"]
    rate = (stats["completed_actions"] / total * 100) if total > 0 else 0.0

    return _format_result(
        True,
        "GTD 统计报告",
        archive_total=archive_total + stats["completed_actions"],
        new_items_this_week=stats["new_items"],
        pending_actions=stats["pending_actions"],
        waiting=stats["waiting"],
        active_projects=stats["projects"],
        completion_rate=round(rate, 1),
    )


# ── gtd_config_get ────────────────────────────────────

def handle_config_get(params):
    from config_manager import get_config

    key = params.get("key")
    value = get_config(key)
    return _format_result(True, "配置读取成功", key=key, value=value)


# ── gtd_config_set ────────────────────────────────────

def handle_config_set(params):
    from config_manager import set_config

    key = params["key"]
    value = params["value"]
    set_config(key, value)
    return _format_result(True, f"配置已更新: {key} = {value}")


# ── Handler registry ──────────────────────────────────

HANDLERS = {
    "gtd_init": handle_init,
    "gtd_capture": handle_capture,
    "gtd_inbox": handle_inbox,
    "gtd_inbox_process": handle_inbox_process,
    "gtd_next_number": handle_next_number,
    "gtd_list_actions": handle_list_actions,
    "gtd_complete": handle_complete,
    "gtd_archive": handle_archive,
    "gtd_daily_check": handle_daily_check,
    "gtd_weekly_review": handle_weekly_review,
    "gtd_stats": handle_stats,
    "gtd_config_get": handle_config_get,
    "gtd_config_set": handle_config_set,
}
