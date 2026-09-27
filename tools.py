"""Hermes tool handlers for the GTD plugin."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

try:
    from . import gtd_core as core
    from . import reminders, materials, gtd_response
    from .schemas import ALL_SCHEMAS
except ImportError:
    import gtd_core as core
    import reminders
    import materials
    import gtd_response
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
        if expected_type == "array" and isinstance(value, list):
            return True
        if expected_type == "object" and isinstance(value, dict):
            return True
    return False


def _validate_value(field: str, value: Any, prop: dict) -> None:
    if prop.get("type") and not _type_matches(value, prop["type"]):
        raise core.GTDValidationError(f"参数 {field} 类型不正确")
    if "enum" in prop and value not in prop["enum"]:
        raise core.GTDValidationError(f"参数 {field} 值不允许")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in prop and value < prop["minimum"]:
            raise core.GTDValidationError(f"参数 {field} 小于最小值")
    if isinstance(value, list) and "items" in prop:
        for index, item in enumerate(value):
            _validate_value(f"{field}[{index}]", item, prop["items"])
    if isinstance(value, dict):
        for required in prop.get("required", []):
            if not value.get(required):
                raise core.GTDValidationError(f"缺少 {field}.{required}")
        for key, item in value.items():
            if key in prop.get("properties", {}):
                _validate_value(f"{field}.{key}", item, prop["properties"][key])


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
        _validate_value(field, value, prop)
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
        return _json_result(payload.pop("ok", True), message, **payload)
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
    return init_handler(None)(args, **kwargs)


def init_handler(dispatch):
    def handler(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
        def operation(data):
            result = core.init_gtd()
            schedules = reminders.initialize(data, dispatch, **kwargs)
            complete = schedules['status'] != 'incomplete'
            return {**result, 'ok': complete, 'initialized': True,
                    **({} if complete else {'error': {'type': 'ScheduleInitializationError',
                                                      'detail': '数据已保存；查看 schedules 中的调度错误'}}),
                    'schedules': schedules,
                    'message': f"GTD 数据已初始化，目录: {core.get_gtd_dir()}；" +
                    {'ready': '常规调度已核实（已有任务保留原状态）；实际投递需要 Gateway 和渠道可用',
                     'skipped': '已跳过常规调度',
                     'needs_preferences': '请在对话中选择调度内容、频率、星期和具体时间；尚未创建调度',
                     'incomplete': '常规调度未全部完成，请检查 schedules 后重试 gtd_init'}[schedules['status']]}
        return _run('gtd_init', args, operation)
    return handler


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
            "archive_total": archive_total + stats["active_completed_actions"] + stats["active_completed_waiting"],
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


def handle_reference_add(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    def operation(data: dict[str, Any]) -> dict[str, Any]:
        result = core.add_reference(
            title=data.get("title", ""),
            note=data.get("note", ""),
            kind=data.get("kind", ""),
            url=data.get("url", ""),
            file_path=data.get("file_path", ""),
            tags=data.get("tags"),
            aliases=data.get("aliases"),
            people=data.get("people"),
            project=data.get("project", ""),
            related_items=data.get("related_items"),
            purpose=data.get("purpose", ""),
            source=data.get("source", ""),
            owner=data.get("owner", ""),
            version=data.get("version", "v1"),
            read_policy=data.get("read_policy", "metadata_only"),
            managed=data.get("managed", "link"),
        )
        return {"message": f"已新增参考资料: {result['reference_id']} {result['title']}", **result}

    return _run("gtd_reference_add", args, operation)


def handle_reference_search(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    def operation(data: dict[str, Any]) -> dict[str, Any]:
        result = core.search_references(
            data.get("query", ""),
            related_item=data.get("related_item", ""),
            limit=data.get("limit", 10),
        )
        return {"message": f"找到 {result['count']} 条参考资料", **result}

    return _run("gtd_reference_search", args, operation)


def handle_reference_get(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    def operation(data: dict[str, Any]) -> dict[str, Any]:
        result = core.get_reference(data["reference_id"])
        return {"message": f"参考资料: {result['reference_id']} {result.get('title', '')}", **result}

    return _run("gtd_reference_get", args, operation)


def handle_reference_link(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    def operation(data: dict[str, Any]) -> dict[str, Any]:
        result = core.link_reference(data["reference_id"], data["related_item"])
        return {"message": f"已关联 {result['reference_id']} -> {data['related_item']}", **result}

    return _run("gtd_reference_link", args, operation)


def handle_reference_read(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    def operation(data: dict[str, Any]) -> dict[str, Any]:
        result = core.read_reference(data["reference_id"], max_chars=data.get("max_chars", core.REFERENCE_READ_LIMIT_CHARS), attachment_index=data.get("attachment_index", 1), offset=data.get("offset", 0))
        return {"message": f"已读取参考资料: {result['reference_id']}", **result}

    return _run("gtd_reference_read", args, operation)


def handle_message_capture(args: dict | None = None, **kwargs):
    def operation(data):
        result = core.capture_message(**data)
        return {"message": "消息已保存" if not result.get("duplicate") else "该消息已保存，无需重复收集", **result}
    return _run("gtd_message_capture", args, operation)


def handle_reference_files(args: dict | None = None, **kwargs):
    return _run("gtd_reference_files", args, lambda data: {
        "message": "原件已准备，需由 Hermes 渠道发送；这不是送达确认", **core.reference_files(**data)})


def handle_reference_reindex(args: dict | None = None, **kwargs):
    return _run("gtd_reference_reindex", args, lambda data: {"message": "索引已重建，请检查 skipped", **core.rebuild_reference_index()})


def handle_notice_update(args: dict | None = None, **kwargs):
    return _run("gtd_notice_update", args, lambda data: {"message": "通知状态已更新", **core.update_notice(**data)})


def handle_reminder(args: dict | None = None, **kwargs):
    return _run("gtd_reminder", args, lambda data: reminders.manage(data, None))


def reminder_handler(dispatch):
    def handler(args: dict | None = None, **kwargs):
        return _run("gtd_reminder", args, lambda data: reminders.manage(data, dispatch, **kwargs))
    return handler


def handle_materials_context(args: dict | None = None, **kwargs):
    return _run("gtd_materials_context", args, lambda data: {
        "message": "已读取材料上下文；候选不代表自动归组", **materials.context(**data)})


def handle_materials_analyze(args: dict | None = None, **kwargs):
    return _run("gtd_materials_analyze", args, lambda data: {
        "message": "已保存附件分析结果", **materials.analyze_attachment(**data)})


def handle_materials_organize(args: dict | None = None, **kwargs):
    return _run("gtd_materials_organize", args, lambda data: {
        "message": "已整理材料，请区分保存状态和分析覆盖范围", **materials.organize(**data)})


def handle_relations(args: dict | None = None, **kwargs):
    return _run("gtd_relations", args, lambda data: {
        "message": "关联已处理；任务与资料各自独立", **core.relations(**data)})


def handle_memory(args: dict | None = None, **kwargs):
    return _run("gtd_memory", args, lambda data: {"message": "记忆操作完成", **core.memory(**data)})


def handle_manage(args: dict | None = None, **kwargs):
    return _run("gtd_manage", args, lambda data: gtd_response.manage(data, None, **kwargs))


def manage_handler(dispatch):
    def handler(args: dict | None = None, **kwargs):
        return _run("gtd_manage", args, lambda data: gtd_response.manage(data, dispatch, **kwargs))
    return handler


HANDLERS = {
    "gtd_manage": handle_manage,
    "gtd_memory": handle_memory,
    "gtd_relations": handle_relations,
    "gtd_materials_context": handle_materials_context,
    "gtd_materials_analyze": handle_materials_analyze,
    "gtd_materials_organize": handle_materials_organize,
    "gtd_message_capture": handle_message_capture,
    "gtd_reference_files": handle_reference_files,
    "gtd_reference_reindex": handle_reference_reindex,
    "gtd_notice_update": handle_notice_update,
    "gtd_reminder": handle_reminder,
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
    "gtd_reference_add": handle_reference_add,
    "gtd_reference_search": handle_reference_search,
    "gtd_reference_get": handle_reference_get,
    "gtd_reference_link": handle_reference_link,
    "gtd_reference_read": handle_reference_read,
}
