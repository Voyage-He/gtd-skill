## ADDED Requirements

### Requirement: Hermes skill 支持 reference 资料工作流
Hermes GTD skill SHALL 指导 Agent 使用 `gtd_reference_*` tools 完成参考资料新增、搜索、查看、关联、命名建议和显式读取工作流。

#### Scenario: 用户登记群文件
- **WHEN** 用户要求“把这个客户A合同表作为参考资料登记”
- **THEN** Agent 调用 reference 新增工具保存资料卡和附件元数据，并向用户返回 reference ID 与命名建议

#### Scenario: 用户搜索参考资料
- **WHEN** 用户问“找一下客户A二期相关资料”
- **THEN** Agent 调用 reference 搜索工具，并基于 metadata 和短备注展示候选资料，不主动读取附件正文

### Requirement: Hermes skill 默认不读取 reference 附件
Hermes GTD skill SHALL 要求 Agent 在 reference 搜索、列表和关联场景中默认只使用 metadata；MUST 在用户明确要求读取、总结、预览或抽取附件内容前避免读取大文件。

#### Scenario: 用户只要求找资料
- **WHEN** 用户说“找到上次群里的评审表”
- **THEN** Agent 返回匹配 reference 的标题、文件名、来源、日期和路径，不读取表格内容

#### Scenario: 用户明确要求读取资料
- **WHEN** 用户说“打开 R20260507-001 并总结付款条款”
- **THEN** Agent 调用显式读取工具，再基于读取结果回答

### Requirement: Hermes skill 区分 GTD reference 与长期 memory
Hermes GTD skill SHALL 指导 Agent 将工作资料、项目事实、群消息备忘和附件索引写入 Reference Registry；只有跨项目稳定偏好、身份信息或长期习惯才适合写入 Hermes Agent memory。

#### Scenario: 工作事实进入 reference
- **WHEN** 用户要求记录某个客户项目中的临时事实
- **THEN** Agent 使用 `gtd_reference_add` 创建 memo 型资料卡，并可关联项目编号

#### Scenario: 稳定偏好进入 memory
- **WHEN** 用户要求长期记住输出偏好
- **THEN** Agent 不把该偏好作为普通 reference 附件资料处理
