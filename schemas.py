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

# ── gtd_reference_add ─────────────────────────────────
REFERENCE_ADD = {
    "name": "gtd_reference_add",
    "description": "新增 GTD reference 资料卡，可登记纯备忘、链接或本地文件附件。默认只读取文件元数据，不解析附件正文。",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "资料标题。可留空但必须提供 note、url 或 file_path 之一。"},
            "note": {"type": "string", "description": "短备注或备忘内容，作为 metadata-first 召回依据。"},
            "kind": {"type": "string", "enum": ["memo", "link", "file"], "description": "资料类型。留空时从 url 或 file_path 推断。"},
            "url": {"type": "string", "description": "链接资料的 URL。工具不会主动抓取远程页面内容。"},
            "file_path": {"type": "string", "description": "本地附件路径。工具默认只登记文件元数据，不读取正文。"},
            "tags": {"type": ["string", "array"], "description": "标签，可传逗号分隔字符串或字符串数组。"},
            "aliases": {"type": ["string", "array"], "description": "别名，可传逗号分隔字符串或字符串数组。"},
            "people": {"type": ["string", "array"], "description": "相关人员，可传逗号分隔字符串或字符串数组。"},
            "project": {"type": "string", "description": "相关项目名称或编号。"},
            "related_items": {"type": ["string", "array"], "description": "关联 GTD 编号，如 N001、W001、P001，或 inbox:<原文>。"},
            "purpose": {"type": "string", "description": "文件或资料用途，用于生成包含主题和用途的命名建议。"},
            "source": {"type": "string", "description": "资料来源，如 企业微信、邮件、张三。"},
            "owner": {"type": "string", "description": "责任人或文件提供者，用于命名建议。"},
            "version": {"type": "string", "description": "版本标识，默认 v1。"},
            "read_policy": {
                "type": "string",
                "enum": ["metadata_only", "preview_allowed", "read_on_request"],
                "description": "读取策略，默认 metadata_only。",
            },
            "managed": {
                "type": "string",
                "enum": ["link", "copy"],
                "description": "附件托管策略。link 只保存原路径；copy 复制到 references/assets/。",
            },
        },
        "required": [],
    },
}

# ── gtd_reference_search ──────────────────────────────
REFERENCE_SEARCH = {
    "name": "gtd_reference_search",
    "description": "按 metadata 和短备注搜索 GTD reference；不会读取、解析或摘要附件正文。",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词。"},
            "related_item": {"type": "string", "description": "按关联编号过滤，如 P003、N014、W002。"},
            "limit": {"type": "integer", "description": "最多返回条数，默认 10，最大 50。"},
        },
        "required": [],
    },
}

# ── gtd_reference_get ─────────────────────────────────
REFERENCE_GET = {
    "name": "gtd_reference_get",
    "description": "查看单条 GTD reference 资料卡 metadata 和附件元数据；不会读取附件正文。",
    "parameters": {
        "type": "object",
        "properties": {
            "reference_id": {"type": "string", "description": "资料编号，如 R20260507-001。"},
        },
        "required": ["reference_id"],
    },
}

# ── gtd_reference_link ────────────────────────────────
REFERENCE_LINK = {
    "name": "gtd_reference_link",
    "description": "将 GTD reference 与 N/W/P 编号或 inbox 原文建立关联；不会读取附件正文。",
    "parameters": {
        "type": "object",
        "properties": {
            "reference_id": {"type": "string", "description": "资料编号，如 R20260507-001。"},
            "related_item": {"type": "string", "description": "关联对象，如 N001、W001、P001 或 inbox:<原文>。"},
        },
        "required": ["reference_id", "related_item"],
    },
}

# ── gtd_reference_read ────────────────────────────────
REFERENCE_READ = {
    "name": "gtd_reference_read",
    "description": "显式读取 GTD reference 的备注或文本附件内容，并返回读取范围和截断信息。只有用户明确要求读取、总结、预览或抽取内容时才使用。",
    "parameters": {
        "type": "object",
        "properties": {
            "reference_id": {"type": "string", "description": "资料编号，如 R20260507-001。"},
            "max_chars": {"type": "integer", "description": "最多读取字符数，默认 4000，最大 20000。"},
        },
        "required": ["reference_id"],
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
    REFERENCE_ADD,
    REFERENCE_SEARCH,
    REFERENCE_GET,
    REFERENCE_LINK,
    REFERENCE_READ,
]
