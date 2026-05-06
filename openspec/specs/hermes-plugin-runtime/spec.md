# hermes-plugin-runtime Specification

## Purpose
TBD - created by archiving change complete-hermes-adaptation. Update Purpose after archive.
## Requirements
### Requirement: Hermes 插件清单完整声明
项目 SHALL 提供 Hermes 可发现的 `plugin.yaml`，清单 MUST 使用 `gtd` 作为插件名，并声明版本、描述、GTD 工具清单和运行时环境变量要求。

#### Scenario: Hermes 发现插件元数据
- **WHEN** Hermes 从插件目录读取 `plugin.yaml`
- **THEN** 清单包含 `name: gtd`、有效 `version`、面向 Hermes Agent 的 `description`、所有 `gtd_*` 工具的 `provides_tools` 列表，以及明确的 `requires_env` 配置

### Requirement: GTD 工具注册到 Hermes toolset
插件 `register(ctx)` SHALL 注册全部 GTD 工具，并且每个工具 MUST 使用命名参数形式调用 `ctx.register_tool(name=..., toolset="gtd", schema=..., handler=...)`。

#### Scenario: 注册全部工具
- **WHEN** 测试上下文调用插件的 `register(ctx)`
- **THEN** 上下文收到 13 个工具注册，工具名与 `ALL_SCHEMAS` 和 `HANDLERS` 一一对应，且每个注册项的 `toolset` 均为 `gtd`

#### Scenario: 工具缺少 handler
- **WHEN** `ALL_SCHEMAS` 中存在没有对应 handler 的工具
- **THEN** 插件注册 MUST 产生可诊断错误或测试失败，不得静默跳过该工具

### Requirement: Handler 遵循 Hermes 调用契约
每个公开 GTD handler SHALL 接收 `args: dict, **kwargs`，MUST 返回 JSON 字符串，并且 MUST 将成功和失败都编码为 JSON 结果，不得向 Hermes 运行时抛出业务异常。

#### Scenario: Handler 接收未来上下文参数
- **WHEN** Hermes 调用任意 `gtd_*` handler 并传入额外 `task_id` 或其他 `**kwargs`
- **THEN** handler 正常处理 `args`，忽略或使用额外上下文，并返回可解析 JSON 字符串

#### Scenario: 必填参数缺失
- **WHEN** Hermes 调用 `gtd_capture` 但 `args` 缺少 `content`
- **THEN** handler 返回 `ok: false` 的 JSON 字符串，包含可读 `message` 和 `error` 字段，且不抛出 `KeyError`

#### Scenario: 底层操作异常
- **WHEN** 底层 GTD 操作出现 `SystemExit`、文件 IO 错误或其他异常
- **THEN** handler 返回 `ok: false` 的 JSON 字符串，包含错误类型或错误说明，且 Hermes 会话继续运行

### Requirement: Tool schema 与 handler 行为一致
每个 GTD tool schema SHALL 准确描述 handler 支持的参数、必填字段、枚举值和返回意图，MUST 避免声明实现不支持的能力。

#### Scenario: Schema 名称一致
- **WHEN** 自动化测试遍历 `ALL_SCHEMAS`
- **THEN** 每个 schema 的 `name` 在 `HANDLERS` 中存在同名 handler，且 schema 的 `parameters` 是有效 JSON Schema object

#### Scenario: 枚举参数非法
- **WHEN** Hermes 调用 `gtd_inbox_process` 并传入 schema 未允许的 `target`
- **THEN** handler 返回结构化错误 JSON，不修改任何 GTD Markdown 文件

### Requirement: Hermes skill 注册与插件运行时解耦
插件 SHALL 注册 Hermes 专用 GTD skill，且 skill 路径 MUST 位于 Hermes 插件结构内，不得依赖 `.claude/skills/gtd/SKILL.md` 作为 Hermes 行为文档。

#### Scenario: 注册 Hermes 专用 skill
- **WHEN** 插件 `register(ctx)` 在存在 Hermes skill 文件的目录中运行
- **THEN** 上下文收到 `ctx.register_skill("gtd", <hermes_skill_path>)` 调用，路径指向 Hermes 专用 skill 文件

