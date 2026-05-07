## MODIFIED Requirements

### Requirement: GTD 工具注册到 Hermes toolset
插件 `register(ctx)` SHALL 注册全部 GTD 工具，并且每个工具 MUST 使用命名参数形式调用 `ctx.register_tool(name=..., toolset="gtd", schema=..., handler=...)`。

#### Scenario: 注册全部工具
- **WHEN** 测试上下文调用插件的 `register(ctx)`
- **THEN** 上下文收到与 `ALL_SCHEMAS` 数量一致的工具注册，工具名与 `ALL_SCHEMAS` 和 `HANDLERS` 一一对应，且每个注册项的 `toolset` 均为 `gtd`

#### Scenario: 工具缺少 handler
- **WHEN** `ALL_SCHEMAS` 中存在没有对应 handler 的工具
- **THEN** 插件注册 MUST 产生可诊断错误或测试失败，不得静默跳过该工具

## ADDED Requirements

### Requirement: Reference 工具遵循 Hermes handler 契约
所有 `gtd_reference_*` handler SHALL 接收 `args: dict, **kwargs`，MUST 返回 JSON 字符串，并且 MUST 将业务失败编码为 `ok: false`，不得向 Hermes 运行时泄漏异常。

#### Scenario: Reference 必填参数缺失
- **WHEN** Hermes 调用 reference 新增工具但缺少标题、备注或文件路径等可形成资料卡的输入
- **THEN** handler 返回 `ok: false` 的 JSON 字符串，包含可读 `message` 和 `error` 字段

#### Scenario: Reference 文件读取失败
- **WHEN** Hermes 调用 reference 读取工具但附件不存在或无法读取
- **THEN** handler 返回 `ok: false` 的 JSON 字符串，Hermes 会话继续运行

### Requirement: Reference tool schema 准确声明读取行为
每个 `gtd_reference_*` schema SHALL 准确描述参数、返回意图和是否会读取附件内容；搜索、列表、查看和关联工具的描述 MUST 明确不会读取附件正文。

#### Scenario: 搜索工具 schema 声明 metadata-only
- **WHEN** 自动化测试检查 `gtd_reference_search` schema 描述
- **THEN** schema 明确说明该工具只搜索 metadata 和短备注，不读取附件正文
