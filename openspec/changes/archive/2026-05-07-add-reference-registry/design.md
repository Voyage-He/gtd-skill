## Context

当前 GTD 数据模型以 Markdown 文件为主：`inbox.md`、`next_actions.md`、`waiting_for.md`、`projects.md`、`reference.md` 等文件由 `gtd_core.py` 直接读写，Hermes 通过 `schemas.py`、`tools.py` 和 `skills/gtd/SKILL.md` 暴露自然语言工作流。`reference` 目前只是 `gtd_inbox_process(target="reference")` 的归档目标，不能表达附件、来源、项目关联、召回理由、读取策略或与 Agent memory 的边界。

Reference Registry 需要符合本项目的现有约束：优先本地文件、无需服务端、工具返回 JSON 字符串、初始化幂等、写操作保留用户数据，并且 Agent 默认不读取大型文件内容。

## Goals / Non-Goals

**Goals:**

- 将 reference 扩展为结构化资料登记和召回系统，而不是单个 `reference.md` 列表。
- 支持登记纯备忘、链接、本地文件附件和由 inbox 整理产生的资料。
- 支持资料卡与 `N`、`W`、`P` 编号或 inbox 原文关联。
- 支持基于标题、别名、标签、人物、项目、来源、日期、文件类型和短备注的 metadata-first 搜索。
- 支持文件命名建议和可选文件托管策略，让不读取内容时也能凭文件名准确识别。
- 明确默认读取策略：搜索和列表不读取附件内容，只有显式读取工具才访问文件内容或生成预览。
- 明确 GTD reference memo 与 Hermes Agent memory 的边界。

**Non-Goals:**

- 不实现跨设备同步、云存储或权限系统。
- 不自动 OCR、转写音视频或解析所有复杂文件格式；第一版只提供显式读取入口和安全失败。
- 不将所有历史 `reference.md` 内容强制迁移成结构化资料卡。
- 不替代 Hermes Agent 的长期 memory；Reference Registry 保存工作资料和项目事实。

## Decisions

### 资料卡作为主记录，索引作为加速结构

每条 reference 使用独立资料卡保存到 `references/cards/<id>.md`。资料卡采用 YAML front matter 加正文备注的形式，便于人类阅读、手工编辑、版本管理和备份。`references/index.jsonl` 保存搜索所需的扁平字段，作为可重建的加速索引。

替代方案是仅使用 SQLite。SQLite 查询能力更强，但降低了手工可读性，也让简单 GTD 目录更难直接检查。第一版采用 Markdown card + JSONL index；后续如果搜索维度变复杂，可以在不改变工具契约的前提下替换索引后端。

### Reference ID 独立于任务编号

Reference ID 使用 `RYYYYMMDD-NNN` 格式，例如 `R20260507-001`。它不占用 `N/W/P` 任务编号，避免资料和行动混淆。资料卡通过 `related_items` 保存 `N014`、`W003`、`P002` 等关联编号。

### 文件附件默认登记，不读取

附件记录保存 `original_path`、托管后的 `path`、`name`、`size`、`mime`、`sha256`、`ext` 和 `managed` 等字段。新增 reference 时默认只读取文件系统元数据和可选 hash，不解析文件内容。搜索结果返回资料卡 metadata、短备注和命中理由，不返回附件正文。

文件托管策略提供两种：

- `link`: 保存原路径，不复制文件。
- `copy`: 复制到 `references/assets/YYYY/MM/` 并使用规范文件名。

第一版默认 `link`，避免移动用户文件；用户明确要求“纳入 GTD 资料库”时使用 `copy`。

### 命名建议与实际文件分离

规范文件名建议为：

`<reference-id>__<subject>_<purpose>__<source-or-owner>__<version>.<ext>`

文件名用于肉眼识别和 Finder/文件管理器召回；完整标签、别名、项目关系和备注仍存于资料卡。这样既避免文件名过长，也避免把召回完全押在命名上。

### 明确读取策略

每条资料卡包含 `read_policy`：

- `metadata_only`: 默认策略，搜索和列表只使用 metadata。
- `preview_allowed`: 允许使用已存在的短预览，但不自动重新解析附件。
- `read_on_request`: 只有用户明确要求读取时才访问附件内容。

`gtd_reference_search` MUST 不读取附件内容。`gtd_reference_read` 是唯一显式读取入口，读取时需要返回读取范围、文件类型、是否截断和失败原因。

### 兼容 `reference.md`

`reference.md` 保留为概览入口。`gtd_init` 可在其中加入说明和最近资料区域，但 registry 的权威数据在 `references/cards/` 和索引中。现有 `gtd_inbox_process(target="reference")` 可继续把纯文本追加到 `reference.md`；实现阶段可选择同时创建一条 memo 型资料卡以增强召回，但必须保持旧行为兼容。

### Memory 边界由 skill 和工具返回共同表达

Reference Registry 保存工作资料、项目事实、群消息备忘、附件索引和一次性上下文。Hermes Agent memory 保存跨会话稳定偏好、身份和长期习惯。`skills/gtd/SKILL.md` 需要要求 Agent：当用户说“记一条资料/备忘/这个文件以后要用”时优先使用 `gtd_reference_add`；只有用户表达长期偏好时才使用 memory。

## Risks / Trade-offs

- [索引与资料卡不一致] → 将 `index.jsonl` 视为可重建缓存，写入资料卡后再更新索引；搜索时遇到缺失 card 返回可诊断错误。
- [文件 hash 计算拖慢大文件登记] → 第一版可对超大文件跳过 hash 或只在用户要求去重时计算，返回 `hash_status`。
- [默认 link 后源文件被移动] → 搜索结果保留原路径并在 `get/read` 时检查存在性；失败时提示用户重新定位或改为 copy 托管。
- [资料卡字段过多导致使用成本高] → 工具参数保留少量必填字段，只要求 `title` 或 `note`；其他 metadata 可选。
- [reference memo 与 memory 混淆] → 在 skill 中写明边界，并让工具 schema 描述 `kind: memo` 是 GTD 工作资料，不是 Agent 长期记忆。
- [新增工具改变注册数量测试] → 更新 runtime spec 和测试，避免硬编码旧的 13 个工具数量。

## Migration Plan

1. `gtd_init` 新增幂等创建 `references/cards/`、`references/assets/`、`references/cache/` 和 `references/index.jsonl`。
2. 保留现有 `reference.md`，不自动迁移旧内容。
3. 新增工具和测试后，更新 `plugin.yaml`、`ALL_SCHEMAS`、`HANDLERS` 和 Hermes skill。
4. 可选提供 `gtd_reference_add` 从旧文本创建 memo 型资料卡，但不删除原 Markdown 文本。
5. 回滚时保留 `references/` 数据目录；移除新工具不会影响现有 GTD Markdown 文件。

## Open Questions

- 第一版是否需要支持 `move` 托管策略，还是只支持 `link` 和 `copy`？
- 是否需要加入 `gtd_reference_reindex` 工具，用于从 `cards/*.md` 重建 `index.jsonl`？
- `gtd_inbox_process(target="reference")` 是否应默认创建资料卡，还是保持只写 `reference.md` 并引导用户使用 `gtd_reference_add`？
