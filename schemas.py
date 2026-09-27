"""GTD plugin tool JSON schemas for Hermes Agent."""

# ── gtd_init ──────────────────────────────────────────
INIT = {
    "name": "gtd_init",
    "description": "对话式初始化 GTD。未提供 routines 时初始化数据并复核既有选择和真实调度；首次未配置时返回 needs_preferences，让用户决定内容、每天或每周、具体星期和时间。只创建用户明确选择的安排，保留已有任务；不自动启用任何早晚默认调度。",
    "parameters": {
        "type": "object",
        "properties": {
            "setup_schedules": {"type": "boolean", "description": "false 仅初始化数据；省略时根据 routines 处理，不代选安排"},
            "routines": {
                "type": "array", "description": "对话中用户选定的安排；省略表示待询问，空列表表示暂不安排。沿用稳定 key 以免重复创建。",
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "稳定唯一标识，例如 daily_reminder、daily_summary、weekly_review、weekly_plan"},
                        "frequency": {"type": "string", "enum": ["daily", "weekly"]},
                        "time": {"type": "string", "description": "用户指定的 HH:MM，没有默认时间"},
                        "weekday": {"type": "integer", "minimum": 0, "maximum": 6, "description": "weekly 必填：0 周日、1 周一至 6 周六；周首/周末应按用户一周的定义换算"},
                        "prompt": {"type": "string", "description": "用户选择的提醒、总结、回顾或计划内容；注明每次发送还是无变化静默"},
                    },
                    "required": ["key", "frequency", "time", "prompt"],
                },
            },
            "timezone": {"type": "string", "description": "默认 Hermes 当前时区；显式指定时必须与运行环境一致"},
            "deliver": {"type": "string", "description": "新建任务接收目标，默认 origin；或单个 platform:chat_id"},
        },
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
    "description": "修改 GTD 配置项，所有 GTD 对话和定时响应读取最新配置。支持点号分隔；response.verbosity 为 concise/detailed，response.silent_when_unchanged 为布尔值。偏好本身不创建定时任务。",
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
    "description": "读取 GTD reference 的备注或文本附件内容，并返回读取范围和截断信息。用于用户要求的阅读或统一 GTD 响应中必要的相关内容理解；普通搜索仍优先元数据。",
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


def _tool(name, description, properties, required=()):
    return {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": list(required)}}


def _string(description):
    return {"type": "string", "description": description}


REFERENCE_READ["parameters"]["properties"].update({
    "attachment_index": {"type": "integer", "minimum": 1, "description": "附件序号，从 1 开始"},
    "offset": {"type": "integer", "minimum": 0, "description": "从第几个字符开始读，默认 0"},
})
ALL_SCHEMAS.extend([
    _tool("gtd_message_capture", "保存转发消息原文和多个已下载附件的副本。可用 reference_id 补充同一条资料；仅已知的来源信息才填写。", {
        "text": _string("消息原文，完整保留；纯附件可不填"),
        "title": _string("简短标题，可省略"),
        "file_paths": {"type": "array", "items": {"type": "string"}, "description": "全部附件已下载后的本地路径，自动复制托管"},
        "channel": _string("接收渠道，例如 qqbot 或 weixin"),
        "chat_id": _string("接收聊天 ID，仅使用渠道提供的值"),
        "message_id": _string("渠道消息 ID，与 channel/chat_id 一起用于去重"),
        "sender": _string("原发送人，仅在已知时填写"),
        "sent_at": _string("原发送时间，仅在已知时填写"),
        "reference_id": _string("明确补充到已有资料时填写；不要猜测合并"),
        "extracted_text": _string("从图片或文件提取的检索文字，区别于原文；不可猜测"),
        "tags": {"type": ["string", "array"], "items": {"type": "string"}},
        "notices": {"type": "array", "description": "原文明示且无歧义的活动/截止日期；不确定时先保存原文再询问", "items": {
            "type": "object", "properties": {"label": _string("事项"), "date": {"type": "string", "format": "date"},
            "kind": {"type": "string", "enum": ["deadline", "event"]}}, "required": ["label", "date"]}},
    }),
    _tool("gtd_reference_files", "准备原文及原附件回传；不会读取附件正文。返回 MEDIA 标签供 Hermes 最终回复发送，prepared 不代表已送达。", {
        "reference_id": _string("资料编号"), "attachment_index": {"type": "integer", "minimum": 1}}, ["reference_id"]),
    _tool("gtd_reference_reindex", "从资料卡重建搜索索引；不会读取附件正文。手工编辑资料卡后使用，检查跳过记录。", {}),
    _tool("gtd_notice_update", "将通知中的活动/截止事项标记完成或重新打开，控制每日提醒。", {
        "reference_id": _string("资料编号"), "notice_index": {"type": "integer", "minimum": 1},
        "done": {"type": "boolean"}}, ["reference_id", "notice_index", "done"]),
    _tool("gtd_reminder", "兼容入口：通过 Hermes 调度器启用、查看、暂停或试运行每日 GTD 响应，执行统一审视流程。通用管理使用 gtd_manage。需 Gateway 在线。", {
        "action": {"type": "string", "enum": ["enable", "status", "disable", "run"]},
        "time": _string("每天 HH:MM，默认 09:00"),
        "timezone": _string("IANA 时区，默认 Asia/Shanghai；必须与 Hermes 时区一致"),
        "deliver": _string("默认 origin（启用时的聊天）；也可指定 platform:chat_id。修改时间时省略可保留原目标")}, ["action"]),
])

_EVIDENCE = {"type": "array", "items": {"type": "object", "properties": {
    "source": _string("上下文中的来源，例如 message:1 或 attachment:2"),
    "quote": _string("来源中实际存在的原文片段；不是推测")}, "required": ["source", "quote"]}}
_ACTION = {"type": "object", "properties": {
    "key": _string("组内稳定英文标识，例如 register；后续补充资料时复用同一行动的 key"),
    "content": _string("用户需要做的具体下一步；不要把教程步骤全当待办"),
    "deadline": {"type": "string", "format": "date", "description": "无歧义的截止日期，可省略"},
    "evidence": _EVIDENCE}, "required": ["key", "content", "evidence"]}
ALL_SCHEMAS.extend([
    _tool("gtd_materials_context", "获取同聊天的近期材料候选供语义归组，或读取一组材料的原文、附件分析、已有行动与版本号。不会读取附件文件。", {
        "reference_id": _string("已知资料组编号，读取该组"),
        "channel": _string("寻找候选时必须提供接收渠道"),
        "chat_id": _string("寻找候选时必须提供聊天 ID；不能跨聊天猜测归组")}),
    _tool("gtd_materials_analyze", "记录 Hermes 实际解析得到的单个附件正文、摘要、关键词和覆盖范围，供乱码文件名的内容召回；工具本身不执行 OCR 或转写。", {
        "reference_id": _string("资料组编号"),
        "attachment_index": {"type": "integer", "minimum": 1},
        "expected_revision": {"type": "integer", "minimum": 0, "description": "最新上下文版本；每次保存分析后递增"},
        "status": {"type": "string", "enum": ["complete", "partial", "failed"]},
        "method": _string("实际解析方法，例如文本读取、OCR、语音转写、视频画面分析"),
        "text": _string("提取文字或转写内容，保留依据"),
        "summary": _string("这个附件讲什么，有什么用途"),
        "keywords": {"type": "array", "items": {"type": "string"}},
        "locator": _string("解析覆盖页码、视频时段等；partial 时必填"),
        "error": _string("失败原因，failed 时必填")},
        ["reference_id", "attachment_index", "expected_revision", "status", "method"]),
    _tool("gtd_materials_organize", "根据 Hermes 对整组材料的理解，保存主题摘要、检索词，并原子创建有原文依据的行动/项目及双向关联。参考资料始终保留。含糊需求使用 needs_clarification。", {
        "reference_id": _string("资料组编号"),
        "expected_revision": {"type": "integer", "minimum": 0},
        "title": _string("整件事的简短标题"), "summary": _string("综合各份材料形成的摘要，明确未知内容"),
        "classification": {"type": "string", "enum": ["reference", "actions", "project", "needs_clarification"]},
        "actions": {"type": "array", "items": _ACTION},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "questions": {"type": "array", "items": {"type": "string"}, "description": "仅列真正影响判断的歧义问题"}},
        ["reference_id", "expected_revision", "title", "summary", "classification"]),
])

ALL_SCHEMAS.append(_tool("gtd_relations", "从任务或资料任一端查询、建立或解除多对多关联。双方是独立对象；解除关联不删除任务、资料、附件或历史来源依据。", {
    "item_id": _string("任务/项目编号 N001、W001、P001 或资料编号 R20260909-001"),
    "action": {"type": "string", "enum": ["get", "link", "unlink"], "description": "默认 get"},
    "other_id": _string("link/unlink 时填写另一端编号；一端是资料，另一端是任务或项目")}, ["item_id"]))

ALL_SCHEMAS.append(_tool("gtd_memory", "保存和召回用户提供的小事实、价格、数量、位置和习惯，独立于待办。保留一般/大约等限定语，不推断为实时事实。修改、删除、恢复需先 get 最新 revision；历史保留。", {
    "action": {"type": "string", "enum": ["search", "get", "add", "update", "delete", "restore"]},
    "query": _string("搜索词；空字符串列出所有未删除记忆；使用核心词例如奶茶、办公室"),
    "memory_id": _string("get/update/delete/restore 的记忆编号，如 M0001"),
    "content": _string("add/update 的完整事实，保留用户给出的单位、范围和限定词"),
    "tags": {"type": "array", "items": {"type": "string"}},
    "source": _string("用户给出的来源或上下文，不要猜测"),
    "expected_revision": {"type": "integer", "minimum": 1, "description": "update/delete/restore 必填，使用 get 返回的 revision"}}, ["action"]))

ALL_SCHEMAS.append(_tool("gtd_manage", "统一 GTD 响应入口。review 同时召回相关内容和当前目录的真实定时任务；get 读取详情；对内容或定时任务增删改查。每次对话或定时触发都先审视、执行、复核，再统一反馈。", {
    "action": {"type": "string", "enum": ["review", "get", "create", "update", "delete", "complete", "pause", "resume", "run"]},
    "target": {"type": "string", "enum": ["content", "schedule"], "description": "默认 content；review 总是包含内容与调度"},
    "id": _string("get/修改时使用 review 返回的真实内容或定时任务 ID，不猜测"),
    "revision": _string("修改已有内容或定时任务前，get 返回的最新 revision"),
    "query": _string("review 的相关关键词，多个词用空格分隔；空且无 ids 时返回概览"),
    "ids": {"type": "array", "items": {"type": "string"}, "description": "review 的内容或定时任务 ID，沿关联扩展召回"},
    "offset": {"type": "integer", "minimum": 0},
    "limit": {"type": "integer", "minimum": 1, "description": "内容概览分页，默认 50，最多 200"},
    "previous_revision": _string("与上次相同召回条件的 review 版本比较；不能仅凭 changed=false 忽略失败或问题"),
    "expected_directory": _string("定时触发时传入 GTD_CONTEXT.gtd_dir；在召回前校验，目录不一致则停止"),
    "data": {"type": "object", "properties": {
        "category": {"type": "string", "enum": ["inbox", "next_actions", "waiting_for", "projects", "someday_maybe", "materials", "memories"]},
        "content": _string("创建任务或新增/更新记忆的内容"),
        "raw": _string("更新任务/项目的完整 Markdown，保留编号及未改动的字段"),
        "title": _string("资料标题"), "note": _string("资料备注"), "url": _string("创建资料时的链接"),
        "tags": {"type": "array", "items": {"type": "string"}},
        "source": _string("记忆来源"), "context": _string("创建行动时的情境"),
        "deadline": {"type": "string", "format": "date"},
        "related_items": {"type": "array", "items": {"type": "string"}, "description": "更新资料关联的任务/项目编号"},
        "key": _string("创建定时任务的稳定英文 key；相同 key 不重复创建"),
        "gtd_dir": _string("仅接管无目录标记的旧 GTD 定时任务时使用：经上下文核实的当前目录，且需提供完整 prompt"),
        "prompt": _string("定时执行的完整事项、意图及结束条件；工具自动加入统一响应流程"),
        "schedule": _string("Hermes 支持的一次性时间或周期表达式，例如 0 9 * * *"),
        "timezone": _string("必须与 Hermes 时区一致；未提供时使用 Hermes 当前时区"),
        "deliver": _string("origin、local 或单个 platform:chat_id；更新时省略保留现有接收人"),
        "repeat": {"type": "integer", "minimum": 1, "description": "可选执行次数"},
        "related_ids": {"type": "array", "items": {"type": "string"}, "description": "定时事项关联的稳定 GTD 内容编号"}
    }}}, ["action"]))
