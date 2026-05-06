"""Hermes tool handlers for the GTD plugin."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

try:
    from . import gtd_core as core
    from .schemas import ALL_SCHEMAS
except ImportError:
    import gtd_core as core
    from schemas import ALL_SCHEMAS


Operation = Callable[[dict[str, Any]], dict[str, Any]]


def _json_result(ok: bool, message: str, **extra: Any) -> str:
    result = {"ok": ok, "message": message}
    result.update(extra)
    return json.dumps(result, ensure_ascii=False)


def _schema_map() -> dict[str, dict[str, Any]]:
    return {schema["name"]: schema for schema in ALL_SCHEMAS}


def _coerce_args(args: dict[str, Any] | None) -> dict[str, Any]:
    if args is None:
        return {}
    if not isinstance(args, dict):
        raise core.GTDValidationError("args 必须是 JSON object")
    coerced = dict(args)
    if isinstance(coerced.get("prefix"), str):
        coerced["prefix"] = coerced["prefix"].upper()
    if isinstance(coerced.get("number"), str):
        coerced["number"] = coerced["number"].upper()
    return coerced


def _type_matches(value: Any, expected: str | list[str]) -> bool:
    expected_types = expected if isinstance(expected, list) else [expected]
    for expected_type in expected_types:
        if expected_type == "string" and isinstance(value, str):
            return True
        if expected_type == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if expected_type == "boolean" and isinstance(value, bool):
            return True
        if expected_type == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
    return False


def _validate_args(name: str, args: dict[str, Any]) -> dict[str, Any]:
    schema = _schema_map()[name]
    params = schema.get("parameters", {})
    properties = params.get("properties", {})
    required = params.get("required", [])

    for field in required:
        if field not in args or args[field] is None or args[field] == "":
            raise core.GTDValidationError(f"缺少必填参数: {field}")

    for field, value in list(args.items()):
        prop = properties.get(field)
        if prop is None or value is None or value == "":
            continue
        expected_type = prop.get("type")
        if expected_type and not _type_matches(value, expected_type):
            if expected_type == "integer" and isinstance(value, str) and value.isdigit():
                args[field] = int(value)
                value = args[field]
            else:
                raise core.GTDValidationError(f"参数 {field} 类型不正确")
        enum = prop.get("enum")
        if enum is not None and value not in enum:
            raise core.GTDValidationError(f"参数 {field} 必须是: {', '.join(enum)}")
        if prop.get("format") == "date":
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError as exc:
                raise core.GTDValidationError(f"参数 {field} 必须使用 YYYY-MM-DD 格式") from exc
    return args


def _run(name: str, args: dict[str, Any] | None, operation: Operation) -> str:
    try:
        normalized = _validate_args(name, _coerce_args(args))
        payload = operation(normalized)
        message = payload.pop("message", "操作成功")
        return _json_result(True, message, **payload)
    except SystemExit as exc:
        return _json_result(
            False,
            "底层操作提前退出",
            error={"type": "SystemExit", "code": exc.code},
        )
    except core.GTDValidationError as exc:
        return _json_result(
            False,
            str(exc),
            error={"type": exc.__class__.__name__, "detail": str(exc)},
        )
    except Exception as exc:  # noqa: BLE001 - Hermes handlers must not leak exceptions.
        return _json_result(
            False,
            "GTD 工具执行失败",
            error={"type": exc.__class__.__name__, "detail": str(exc)},
        )


def handle_init(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    return _run(
        "gtd_init",
        args,
        lambda _args: {
            **core.init_gtd(),
            "message": f"GTD 系统已初始化，目录: {core.get_gtd_dir()}",
        },
    )


def handle_capture(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    return _run(
        "gtd_capture",
        args,
        lambda data: {
            **core.capture(data["content"]),
            "message": f"已记录: {data['content'].strip()}",
        },
    )


def handle_inbox(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    def operation(_args: dict[str, Any]) -> dict[str, Any]:
        items = core.read_inbox_items()
        return {
            "message": f"收集箱共 {len(items)} 条待处理" if items else "收集箱是空的",
            "items": [
                {
                    "index": item.index,
                    "content": core.clean_content(item),
                    "date": item.date,
                    "line": item.line_index + 1,
                }
                for item in items
            ],
            "count": len(items),
        }

    return _run("gtd_inbox", args, operation)


def handle_inbox_process(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    def operation(data: dict[str, Any]) -> dict[str, Any]:
        result = core.process_inbox(
            data["index"],
            data["target"],
            context=data.get("context", ""),
            deadline=data.get("deadline", ""),
            delegate=data.get("delegate", ""),
            estimated=data.get("estimated", ""),
            project_name=data.get("project_name", ""),
            first_action=data.get("first_action", ""),
        )
        return {"message": f"已处理到 {result['action']}: {result['content']}", **result}

    return _run("gtd_inbox_process", args, operation)


def handle_next_number(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    return _run(
        "gtd_next_number",
        args,
        lambda data: {
            "message": f"下一个可用编号: {core.get_next_number(data['prefix'])}",
            "number": core.get_next_number(data["prefix"]),
        },
    )


def handle_list_actions(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    def operation(data: dict[str, Any]) -> dict[str, Any]:
        actions = core.list_actions(data.get("context", ""), data.get("show_all", False))
        return {
            "message": f"找到 {len(actions)} 项任务",
            "actions": actions,
            "count": len(actions),
        }

    return _run("gtd_list_actions", args, operation)


def handle_complete(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    def operation(data: dict[str, Any]) -> dict[str, Any]:
        result = core.complete_number(data["number"])
        return {"message": f"已标记完成: {result['number']}", **result}

    return _run("gtd_complete", args, operation)


def handle_archive(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    def operation(_args: dict[str, Any]) -> dict[str, Any]:
        result = core.archive_completed()
        return {"message": f"已归档 {result['archived_count']} 个条目", **result}

    return _run("gtd_archive", args, operation)


def handle_daily_check(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    return _run(
        "gtd_daily_check",
        args,
        lambda _args: {
            "message": f"每日检查 - {core.today_str()}",
            **core.daily_check(),
        },
    )


def handle_weekly_review(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    return _run(
        "gtd_weekly_review",
        args,
        lambda _args: {
            "message": "周回顾已创建或已存在",
            **core.create_weekly_review(),
        },
    )


def handle_stats(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    def operation(_args: dict[str, Any]) -> dict[str, Any]:
        stats = core.weekly_stats()
        archive_total = core.get_archive_stats()
        total = stats["pending_actions"] + stats["completed_actions"]
        rate = (stats["completed_actions"] / total * 100) if total else 0.0
        return {
            "message": "GTD 统计报告",
            "archive_total": archive_total + stats["completed_actions"],
            "new_items_this_week": stats["new_items"],
            "pending_actions": stats["pending_actions"],
            "waiting": stats["waiting"],
            "active_projects": stats["projects"],
            "completion_rate": round(rate, 1),
        }

    return _run("gtd_stats", args, operation)


def handle_config_get(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    return _run(
        "gtd_config_get",
        args,
        lambda data: {
            "message": "配置读取成功",
            "key": data.get("key"),
            "value": core.get_config(data.get("key")),
        },
    )


def handle_config_set(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    return _run(
        "gtd_config_set",
        args,
        lambda data: {
            "message": f"配置已更新: {data['key']}",
            **core.set_config(data["key"], data["value"]),
        },
    )


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
