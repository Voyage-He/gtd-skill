# gtd-reference-registry Specification

## Purpose
Define structured GTD reference material storage, metadata-first recall, attachment registration, on-demand reading, and the boundary between GTD reference memos and Hermes Agent memory.

## Requirements
### Requirement: Reference Registry 保存结构化资料卡
GTD 系统 SHALL 使用 Reference Registry 保存参考资料；每条资料 SHALL 拥有稳定 `reference_id`、标题、类型、来源、创建时间、标签、别名、短备注、关联 GTD 对象和读取策略。

#### Scenario: 新增纯备忘资料
- **WHEN** 用户新增一条不含附件的参考备忘
- **THEN** 系统创建一条 `kind: "memo"` 的资料卡，返回 `reference_id`、标题、短备注和资料卡路径

#### Scenario: 新增链接资料
- **WHEN** 用户新增一条包含 URL 的参考资料
- **THEN** 系统创建一条 `kind: "link"` 的资料卡，保存 URL、标题、来源和标签，且不主动抓取远程页面内容

### Requirement: Reference Registry 支持附件登记
GTD 系统 SHALL 支持为资料卡登记本地附件，并 MUST 默认只读取文件元数据，不解析附件正文。

#### Scenario: 登记本地文件附件
- **WHEN** 用户用文件路径新增 reference
- **THEN** 系统保存文件名、扩展名、路径、大小、MIME 类型或可推断类型、托管策略和读取策略

#### Scenario: 文件路径不存在
- **WHEN** 用户登记不存在的文件路径
- **THEN** 工具返回 `ok: false`，包含可读错误信息，且不创建半完成资料卡

### Requirement: Reference Registry 提供规范文件名建议
GTD 系统 SHALL 能基于资料卡元数据生成适合召回的文件名建议，格式 MUST 包含 reference ID、主题、用途、来源或责任人和版本信息。

#### Scenario: 为表格生成命名建议
- **WHEN** 用户登记标题为“客户A 二期合同评审表”的表格附件，并提供来源“张三”
- **THEN** 系统返回类似 `RYYYYMMDD-NNN__客户A_二期合同评审表__张三__v1.xlsx` 的命名建议

#### Scenario: 文件名字段缺失
- **WHEN** 用户未提供来源、责任人或版本
- **THEN** 系统仍生成合法文件名，并使用安全默认值或省略缺失片段

### Requirement: Reference Registry 支持 metadata-first 搜索
GTD 系统 SHALL 支持按标题、标签、别名、来源、人物、项目、日期、类型、关联编号和短备注搜索 reference，且 `gtd_reference_search` MUST 不读取附件正文。

#### Scenario: 搜索命中附件资料
- **WHEN** 用户搜索“客户A 二期合同”
- **THEN** 系统返回匹配的 reference 列表、命中字段和简短备注，但不返回附件正文内容

#### Scenario: 按项目编号搜索
- **WHEN** 用户搜索关联 `P003` 的资料
- **THEN** 系统返回所有 `related_items` 包含 `P003` 的资料卡摘要

### Requirement: Reference Registry 支持按需读取附件
GTD 系统 SHALL 提供显式读取 reference 附件的工具；只有用户明确请求读取、总结、预览或抽取内容时，系统 MAY 访问附件正文。

#### Scenario: 显式读取文本附件
- **WHEN** 用户请求读取某个 reference 的文本附件
- **THEN** 系统读取附件内容，并返回读取范围、是否截断和内容摘要或正文片段

#### Scenario: 搜索不触发读取
- **WHEN** 用户只执行 reference 搜索或列表操作
- **THEN** 系统不打开、不解析、不摘要附件正文

### Requirement: Reference Registry 支持 GTD 对象关联
GTD 系统 SHALL 支持将 reference 与 `N`、`W`、`P` 编号或 inbox 原文建立关联，并能按关联关系召回。

#### Scenario: 关联到项目
- **WHEN** 用户将 `R20260507-001` 关联到 `P003`
- **THEN** 资料卡的 `related_items` 包含 `P003`，后续按 `P003` 搜索能返回该资料

#### Scenario: 关联编号格式非法
- **WHEN** 用户尝试关联非法编号 `X999`
- **THEN** 工具返回 `ok: false`，并且资料卡不被修改

### Requirement: Reference memo 与 Agent memory 边界明确
GTD 系统 SHALL 将工作备忘、项目事实、群消息资料和附件索引保存为 reference；MUST 不把这些内容自动写入 Hermes Agent 长期 memory。

#### Scenario: 用户要求记录工作备忘
- **WHEN** 用户说“记一下客户A周五前确认付款条款”
- **THEN** Agent 使用 reference 工具创建 `kind: "memo"` 的资料卡，而不是写入长期 memory

#### Scenario: 用户表达长期偏好
- **WHEN** 用户说“以后默认把周报写成中文简洁格式”
- **THEN** Agent MAY 使用长期 memory，因为这是跨项目稳定偏好而非 GTD reference
