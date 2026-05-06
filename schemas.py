"""GTD plugin tool JSON schemas for Hermes Agent."""

# ── gtd_init ──────────────────────────────────────────
INIT = {
    "name": "gtd_init",
    "description": "初始化 GTD Markdown 文件结构。默认使用 ~/gtd，也可通过 GTD_DIR 指向其他目录。该操作幂等，不会覆盖已有用户数据。",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

# ── gtd_capture ───────────────────────────────────────
CAPTURE = {
    "name": "gtd_capture",
    "description": "快速记录一个想法或待办事项到 GTD 收集箱，稍后统一整理。",
    "parameters": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "要记录的内容",
            },
        },
        "required": ["content"],
    },
}

# ── gtd_inbox ─────────────────────────────────────────
INBOX = {
    "name": "gtd_inbox",
    "description": "列出 GTD 收集箱中所有待处理条目。用于查看有哪些想法等待整理。返回条目索引和内容。",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

# ── gtd_inbox_process ─────────────────────────────────
INBOX_PROCESS = {
    "name": "gtd_inbox_process",
    "description": "处理收集箱中的一个条目：移动到指定目标位置（垃圾、参考资料、将来也许、快速完成、下一步行动、等待清单、项目）。",
    "parameters": {
        "type": "object",
        "properties": {
            "index": {
                "type": "integer",
                "description": "条目索引（从 gtd_inbox 获取的编号）",
            },
            "target": {
                "type": "string",
                "enum": ["trash", "reference", "someday_maybe", "done",
                         "next_actions", "waiting_for", "projects"],
                "description": "目标位置",
            },
            "context": {
                "type": "string",
                "description": "情境标签，如 @电脑、@电话、@外出（仅 target=next_actions 时使用）",
            },
            "deadline": {
                "type": "string",
                "format": "date",
                "description": "截止日期 YYYY-MM-DD（仅 target=next_actions 时使用）",
            },
            "delegate": {
                "type": "string",
                "description": "委派对象姓名（仅 target=waiting_for 时使用）",
            },
            "estimated": {
                "type": "string",
                "format": "date",
                "description": "预计完成日期 YYYY-MM-DD（仅 target=waiting_for 时使用）",
            },
            "project_name": {
                "type": "string",
                "description": "项目名称（仅 target=projects 时使用）",
            },
            "first_action": {
                "type": "string",
                "description": "第一步行动描述（仅 target=projects 时使用）",
            },
        },
        "required": ["index", "target"],
    },
}

# ── gtd_next_number ───────────────────────────────────
NEXT_NUMBER = {
    "name": "gtd_next_number",
    "description": "获取下一个可用的任务编号。N=下一步行动，W=等待事项，P=项目。",
    "parameters": {
        "type": "object",
        "properties": {
            "prefix": {
                "type": "string",
                "enum": ["N", "W", "P"],
                "description": "编号前缀",
            },
        },
        "required": ["prefix"],
    },
}

# ── gtd_list_actions ──────────────────────────────────
LIST_ACTIONS = {
    "name": "gtd_list_actions",
    "description": "列出下一步行动清单，可按情境过滤、按截止日期排序。",
    "parameters": {
        "type": "object",
        "properties": {
            "context": {
                "type": "string",
                "description": "情境过滤（如 电脑、电话、外出），不填则显示全部",
            },
            "show_all": {
                "type": "boolean",
                "description": "是否显示已完成任务，默认 false",
            },
        },
        "required": [],
    },
}

# ── gtd_complete ──────────────────────────────────────
COMPLETE = {
    "name": "gtd_complete",
    "description": "标记一个任务为完成。支持 N（下一步行动）、W（等待）、P（项目）三种编号。",
    "parameters": {
        "type": "object",
        "properties": {
            "number": {
                "type": "string",
                "description": "任务编号，如 N001、W003、P002",
            },
        },
        "required": ["number"],
    },
}

# ── gtd_archive ───────────────────────────────────────
ARCHIVE = {
    "name": "gtd_archive",
    "description": "归档所有已完成的任务和项目。将已完成条目从活动文件中移除，存入 archive/ 目录，并保留未完成内容和备注。",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

# ── gtd_daily_check ───────────────────────────────────
DAILY_CHECK = {
    "name": "gtd_daily_check",
    "description": "执行每日检查：显示今日日程、今日/明日截止的紧急任务、需要跟进的等待事项。",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

# ── gtd_weekly_review ─────────────────────────────────
WEEKLY_REVIEW = {
    "name": "gtd_weekly_review",
    "description": "创建周回顾记录文件，自动收集本周统计数据（新增想法、完成任务、过期任务、需跟进事项），生成回顾检查清单模板。",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

# ── gtd_stats ─────────────────────────────────────────
STATS = {
    "name": "gtd_stats",
    "description": "获取 GTD 系统统计数据：累计完成任务数、本周新增想法、待办任务数、等待事项数、活跃项目数、本周完成率。",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

# ── gtd_config_get ────────────────────────────────────
CONFIG_GET = {
    "name": "gtd_config_get",
    "description": "读取 GTD 配置项。不传 key 返回全部配置。支持点号分隔的嵌套键（如 notifications.daily_digest）。",
    "parameters": {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "配置键，支持点号分隔。留空返回全部。",
            },
        },
        "required": [],
    },
}

# ── gtd_config_set ────────────────────────────────────
CONFIG_SET = {
    "name": "gtd_config_set",
    "description": "修改 GTD 配置项。支持点号分隔的嵌套键。",
    "parameters": {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "配置键，如 user_name、review.day",
            },
            "value": {
                "type": ["string", "number", "boolean"],
                "description": "新值。字符串 true/false、整数会在写入时转换为对应类型。",
            },
        },
        "required": ["key", "value"],
    },
}


# ── All schemas ───────────────────────────────────────
ALL_SCHEMAS = [
    INIT,
    CAPTURE,
    INBOX,
    INBOX_PROCESS,
    NEXT_NUMBER,
    LIST_ACTIONS,
    COMPLETE,
    ARCHIVE,
    DAILY_CHECK,
    WEEKLY_REVIEW,
    STATS,
    CONFIG_GET,
    CONFIG_SET,
]
