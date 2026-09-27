"""Hermes Agent GTD plugin."""

from __future__ import annotations

from pathlib import Path


PLUGIN_DIR = Path(__file__).resolve().parent
SKILL_PATH = PLUGIN_DIR / "skills" / "gtd" / "SKILL.md"


def _load_runtime():
    try:
        from .schemas import ALL_SCHEMAS
        from .tools import HANDLERS, reminder_handler, manage_handler, init_handler
    except ImportError:
        from schemas import ALL_SCHEMAS
        from tools import HANDLERS, reminder_handler, manage_handler, init_handler
    return ALL_SCHEMAS, HANDLERS, reminder_handler, manage_handler, init_handler


def register(ctx):
    """Register GTD tools and the GTD skill with Hermes."""

    if not SKILL_PATH.is_file():
        raise FileNotFoundError(f"Hermes GTD skill not found: {SKILL_PATH}")
    all_schemas, handlers, reminder_handler, manage_handler, init_handler = _load_runtime()
    try:
        from .gtd_policy import register_policy
    except ImportError:
        from gtd_policy import register_policy
    register_policy(ctx)
    handlers = dict(handlers)
    handlers["gtd_init"] = init_handler(getattr(ctx, "dispatch_tool", None))
    handlers["gtd_reminder"] = reminder_handler(getattr(ctx, "dispatch_tool", None))
    handlers["gtd_manage"] = manage_handler(getattr(ctx, "dispatch_tool", None))
    missing = [schema["name"] for schema in all_schemas if schema["name"] not in handlers]
    if missing:
        raise RuntimeError(f"Missing GTD handler(s): {', '.join(missing)}")

    for schema in all_schemas:
        name = schema["name"]
        ctx.register_tool(
            name=name,
            toolset="gtd",
            schema=schema,
            handler=handlers[name],
            description=schema.get("description", ""),
        )

    ctx.register_skill("gtd", SKILL_PATH)
