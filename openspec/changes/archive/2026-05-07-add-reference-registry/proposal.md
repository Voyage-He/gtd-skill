## Why

当前 `reference` 只是收集箱整理时的一个 Markdown 归档目标，无法可靠表达工作群资料、关联文档、表格、多媒体文件、链接和备忘之间的关系。实际 GTD 工作中，资料往往需要被准确召回，但大模型默认读取大型附件会浪费 token，也可能把项目事实和 Agent 长期记忆混在一起。

本变更将 `reference` 扩展为一套资料登记与召回系统：默认只检索元数据和短备注，需要时才按用户意图读取附件内容。

## What Changes

- 新增 Reference Registry，用结构化资料卡登记参考资料、备忘、链接和附件。
- 支持将资料卡与 `inbox`、`next_actions`、`waiting_for`、`projects` 等 GTD 对象关联。
- 支持文件附件的命名建议、登记、移动/复制策略、hash/size/mime 等元数据保存。
- 支持 metadata-first 搜索，默认不读取大文件内容；仅在用户明确要求时执行文件读取、预览或摘要生成。
- 支持纯备忘信息进入 GTD reference，并明确它与 Hermes Agent memory 的边界。
- 新增 `gtd_reference_*` 工具 schema、handler 和 Hermes skill 映射。
- 更新初始化和数据可靠性要求，确保新增 reference 数据目录幂等创建、写入安全、不会破坏现有 Markdown GTD 数据。
- 无计划引入破坏性迁移；现有 `reference.md` 保留为兼容入口和人类可读概览。

## Capabilities

### New Capabilities

- `gtd-reference-registry`: 定义结构化 reference 资料卡、附件登记、元数据召回、按需读取、命名规范、备忘与 memory 边界。

### Modified Capabilities

- `hermes-gtd-agent-workflow`: 增加 reference 资料登记、搜索、关联、按需读取和 memory 边界的自然语言工作流。
- `hermes-plugin-runtime`: 增加 `gtd_reference_*` 工具注册、schema/handler 一致性和运行时 JSON 契约要求。
- `gtd-data-reliability`: 增加 reference registry 目录、索引和资料卡写入的数据完整性要求。

## Impact

- 影响核心实现：`gtd_core.py` 需要新增 reference registry 数据结构、文件操作、搜索和读取策略。
- 影响工具层：`schemas.py`、`tools.py`、`__init__.py` 需要新增并注册 `gtd_reference_*` 工具。
- 影响 Hermes skill：`skills/gtd/SKILL.md` 需要描述 reference 工具使用时机、默认不读附件策略，以及与 memory 的区分。
- 影响初始化数据：`gtd_init` 需要创建 `references/` 相关目录和可选索引文件，同时保持幂等。
- 影响测试：需要覆盖资料卡新增、搜索、关联、文件命名建议、默认不读取附件、显式读取、错误处理和现有 GTD 数据不被破坏。
