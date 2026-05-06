"""Hermes Agent GTD plugin."""

from __future__ import annotations

from pathlib import Path


PLUGIN_DIR = Path(__file__).resolve().parent
SKILL_PATH = PLUGIN_DIR / "skills" / "gtd" / "SKILL.md"


def _load_runtime():
    try:
        from .schemas import ALL_SCHEMAS
        from .tools import HANDLERS
    except ImportError:
        from schemas import ALL_SCHEMAS
        from tools import HANDLERS
    return ALL_SCHEMAS, HANDLERS


def register(ctx):
    """Register GTD tools and the GTD skill with Hermes."""

    all_schemas, handlers = _load_runtime()
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

    if not SKILL_PATH.exists():
        raise FileNotFoundError(f"Hermes GTD skill not found: {SKILL_PATH}")
    ctx.register_skill("gtd", str(SKILL_PATH))
