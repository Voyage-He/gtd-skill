"""GTD Plugin for Hermes Agent.

注册 13 个 GTD 工具 + 1 个 GTD Skill：
  工具: gtd_init, gtd_capture, gtd_inbox, gtd_inbox_process,
        gtd_next_number, gtd_list_actions, gtd_complete, gtd_archive,
        gtd_daily_check, gtd_weekly_review, gtd_stats,
        gtd_config_get, gtd_config_set
  Skill: gtd:gtd (加载 .claude/skills/gtd/SKILL.md 作为行为 prompt)
"""

import os
import sys

# Ensure scripts are importable
_plugin_dir = os.path.dirname(__file__)
_scripts_dir = os.path.join(_plugin_dir, ".claude", "skills", "gtd", "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


def register(ctx):
    from schemas import ALL_SCHEMAS
    from tools import HANDLERS

    # 注册所有 GTD 工具
    for schema in ALL_SCHEMAS:
        name = schema["name"]
        handler = HANDLERS.get(name)
        if handler:
            ctx.register_tool(name, schema, handler)

    # 注册 GTD Skill（共享 Claude Code 的 SKILL.md）
    skill_path = os.path.join(
        _plugin_dir, ".claude", "skills", "gtd", "SKILL.md"
    )
    if os.path.exists(skill_path):
        ctx.register_skill("gtd", skill_path)
