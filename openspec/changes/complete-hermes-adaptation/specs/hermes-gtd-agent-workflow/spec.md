## ADDED Requirements

### Requirement: Hermes GTD skill 使用 tool-first 工作流
Hermes GTD skill SHALL 指导 Agent 优先调用已注册的 `gtd_*` tools 完成 GTD 操作，MUST 不要求 Agent 直接执行 `.claude` 脚本、shell 命令或 Claude Code 专用命令。

#### Scenario: 快速收集想法
- **WHEN** 用户对 Hermes Agent 说“记录买牛奶”
- **THEN** Agent 使用 `gtd_capture`，传入 `content` 为用户要记录的事项，并向用户总结工具返回结果

#### Scenario: 初始化 GTD 系统
- **WHEN** 用户说“初始化 GTD”
- **THEN** Agent 使用 `gtd_init` 创建或检查 GTD Markdown 文件结构，不直接运行 Python 脚本命令

### Requirement: Hermes skill 覆盖 GTD 核心自然语言意图
Hermes GTD skill SHALL 覆盖初始化、收集、查看收集箱、整理收集箱、列出下一步行动、完成任务、归档、每日检查、周回顾、统计、读取配置和修改配置的自然语言映射。

#### Scenario: 查看今日待办
- **WHEN** 用户问“今天做什么”
- **THEN** Agent 使用 `gtd_daily_check` 和必要时的 `gtd_list_actions`，并基于 JSON 返回给出简洁中文结果

#### Scenario: 查看统计
- **WHEN** 用户问“查看统计”
- **THEN** Agent 使用 `gtd_stats`，并展示待办、等待、项目、本周新增和完成率等返回字段

#### Scenario: 修改配置
- **WHEN** 用户要求修改 GTD 配置项
- **THEN** Agent 使用 `gtd_config_set` 写入配置，并可使用 `gtd_config_get` 验证结果

### Requirement: 收集箱整理遵循 GTD 决策树
Hermes GTD skill SHALL 在用户要求整理收集箱时先调用 `gtd_inbox`，再按 GTD 决策树引导用户选择 `trash`、`reference`、`someday_maybe`、`done`、`next_actions`、`waiting_for` 或 `projects`。

#### Scenario: 整理为空收集箱
- **WHEN** 用户要求整理收集箱且 `gtd_inbox` 返回 `count: 0`
- **THEN** Agent 告知收集箱为空，不调用 `gtd_inbox_process`

#### Scenario: 整理下一步行动
- **WHEN** 用户将某个 inbox 条目判断为下一步行动并提供情境或截止日期
- **THEN** Agent 调用 `gtd_inbox_process`，传入对应 `index`、`target: "next_actions"`、`context` 和 `deadline`

#### Scenario: 整理项目
- **WHEN** 用户将某个 inbox 条目判断为多步骤项目
- **THEN** Agent 调用 `gtd_inbox_process`，传入 `target: "projects"`、项目名称和第一步行动

### Requirement: Agent 面向用户呈现结构化工具结果
Hermes GTD skill SHALL 要求 Agent 解析工具返回的 JSON 字符串，并基于 `ok`、`message` 和业务字段向用户说明结果；当 `ok` 为 `false` 时 MUST 给出下一步可执行修正建议。

#### Scenario: 工具调用失败
- **WHEN** `gtd_complete` 返回 `ok: false` 且提示任务编号不存在
- **THEN** Agent 告知用户未找到该编号，并建议使用 `gtd_list_actions` 或检查编号

#### Scenario: 工具调用成功
- **WHEN** `gtd_capture` 返回 `ok: true`
- **THEN** Agent 用自然语言确认已记录事项，不展示原始 JSON 除非用户明确要求

### Requirement: Hermes 工作流独立于 Claude 集成
Hermes 用户 SHALL 能在没有 Claude Code marketplace、Claude slash commands 或 `.claude` skill 的情况下完成完整 GTD 工作流。

#### Scenario: Claude 目录不存在
- **WHEN** 插件运行目录不包含 `.claude/skills/gtd/SKILL.md`
- **THEN** Hermes 仍可注册 GTD skill 和所有 `gtd_*` tools，并完成初始化、收集、整理和回顾流程
