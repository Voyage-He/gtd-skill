## ADDED Requirements

### Requirement: 审查发现记录文件
项目 SHALL 提供一份仓库内的 Markdown 文件，用于记录 Hermes Agent 适配审查中发现的问题、风险和后续建议。

#### Scenario: 记录文件存在
- **WHEN** 开发者需要回顾 Hermes Agent 审查发现
- **THEN** 仓库内 MUST 有一份明确命名的 Markdown 文档保存这些发现

### Requirement: 问题条目可追踪
每个审查发现条目 SHALL 包含优先级、问题描述、影响范围、证据位置和建议后续动作，便于后续创建 OpenSpec change 或实现任务。

#### Scenario: 查看单个问题
- **WHEN** 开发者阅读任一问题条目
- **THEN** 开发者 MUST 能判断问题重要性、关联文件、为什么影响 Hermes Agent 使用，以及下一步应做什么

### Requirement: 记录不改变运行行为
本次变更 SHALL 只新增或更新审查记录和 OpenSpec artifacts，不得修改 Hermes 插件注册、工具 handler、GTD 脚本或用户数据处理逻辑。

#### Scenario: 应用记录变更
- **WHEN** 本次 change 被实现
- **THEN** Python 插件代码和 GTD 脚本行为 MUST 保持不变
