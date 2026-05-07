# gtd-data-reliability Specification

## Purpose
TBD - created by archiving change complete-hermes-adaptation. Update Purpose after archive.
## Requirements
### Requirement: GTD 数据目录在调用时解析
GTD 核心操作 SHALL 在每次工具调用时解析 `GTD_DIR` 或默认 `~/gtd`，MUST 不在模块 import 时永久缓存数据目录路径。

#### Scenario: 插件加载后修改 GTD_DIR
- **WHEN** Python 模块已经 import，随后测试设置 `GTD_DIR` 指向临时目录并调用 `gtd_init`
- **THEN** GTD 文件创建在新的临时目录中，而不是 import 时的旧目录

#### Scenario: 多个临时目录隔离
- **WHEN** 两次测试使用不同 `GTD_DIR` 调用 `gtd_capture`
- **THEN** 每次记录只写入当前调用对应目录的 `inbox.md`

### Requirement: 初始化不污染真实任务编号和统计
`gtd_init` SHALL 只创建缺失的 GTD Markdown 文件和目录，MUST 不创建带真实编号的未完成示例任务。

#### Scenario: 初始化后等待事项为空
- **WHEN** 用户在空目录调用 `gtd_init`
- **THEN** `waiting_for.md` 不包含未完成的 `W001` 示例任务，`gtd_stats` 返回等待事项数量为 0

#### Scenario: 初始化幂等
- **WHEN** 用户对已有 GTD 目录重复调用 `gtd_init`
- **THEN** 现有用户数据不被覆盖，缺失文件被补齐，工具返回成功 JSON

### Requirement: 收集箱处理只移动被选中的条目
收集箱读取 SHALL 为每个条目保留稳定的物理行位置或唯一引用，`gtd_inbox_process` MUST 只删除被选中的一条 inbox 记录。

#### Scenario: 重复内容只删除一条
- **WHEN** `inbox.md` 中有两条内容和日期完全相同的记录
- **THEN** 用户处理第一条后，目标文件新增一条记录，`inbox.md` 中仍保留另一条重复记录

#### Scenario: 无效索引不修改文件
- **WHEN** 用户传入小于 1 或大于条目数量的 `index`
- **THEN** `gtd_inbox_process` 返回 `ok: false`，所有 GTD Markdown 文件内容保持不变

### Requirement: 项目编号可被完成
`gtd_complete` SHALL 支持 schema 声明的 `N`、`W` 和 `P` 编号；当编号为项目时，MUST 将对应项目标记为完成并保留完成日期。

#### Scenario: 完成项目编号
- **WHEN** `projects.md` 中存在 `P001` 项目且用户调用 `gtd_complete` 传入 `P001`
- **THEN** 工具返回 `ok: true`，项目状态变为已完成，并且后续统计不再把该项目计为活跃项目

#### Scenario: 完成不存在编号
- **WHEN** 用户调用 `gtd_complete` 传入不存在的 `P999`
- **THEN** 工具返回 `ok: false`，且 `projects.md`、`next_actions.md` 和 `waiting_for.md` 不被修改

### Requirement: 日期统计按日期边界计算
GTD 统计和周回顾 SHALL 使用日期边界而非当前时分秒比较，MUST 正确处理本周开始、今天截止、昨天截止和明天截止。

#### Scenario: 本周范围从周一零点开始
- **WHEN** 当前日期位于周中且周一早些时候有新增 inbox 项
- **THEN** `gtd_stats` 将该新增项计入本周新增数量

#### Scenario: 今天截止不是过期
- **WHEN** 未完成任务的 deadline 等于今天日期
- **THEN** `gtd_weekly_review` 不将该任务计入过期任务

#### Scenario: 昨天截止是过期
- **WHEN** 未完成任务的 deadline 早于今天日期
- **THEN** `gtd_weekly_review` 将该任务计入过期任务

### Requirement: Markdown 文件更新保持用户数据完整
所有 GTD 写操作 SHALL 使用原子或最小范围更新策略，MUST 保留与当前操作无关的用户文本、备注、章节和归档内容。

#### Scenario: 处理 inbox 保留其他内容
- **WHEN** `inbox.md` 中包含标题、说明文本和多个待处理条目
- **THEN** `gtd_inbox_process` 只移除被处理条目，并保留其他标题、说明文本和条目顺序

#### Scenario: 归档已完成任务
- **WHEN** 用户调用 `gtd_archive`
- **THEN** 已完成任务移动到归档文件，未完成任务和其他章节内容保留在活动文件中

### Requirement: 初始化创建 Reference Registry 目录
`gtd_init` SHALL 幂等创建 Reference Registry 所需目录和索引文件，MUST 不覆盖已有 reference 资料卡、附件、缓存或用户编辑内容。

#### Scenario: 空目录初始化 reference registry
- **WHEN** 用户在空 GTD 目录调用 `gtd_init`
- **THEN** 系统创建 `references/cards/`、`references/assets/`、`references/cache/` 和可用索引文件

#### Scenario: 重复初始化保留资料
- **WHEN** 用户已有 reference 资料卡和附件后再次调用 `gtd_init`
- **THEN** 系统不覆盖已有资料卡、附件、缓存和索引内容

### Requirement: Reference 写入保持数据完整
Reference Registry 写操作 SHALL 使用原子或最小范围更新策略，MUST 保留与当前操作无关的资料卡、索引记录、附件和 Markdown GTD 文件内容。

#### Scenario: 新增资料不修改行动清单
- **WHEN** 用户新增 reference 资料卡
- **THEN** `next_actions.md`、`waiting_for.md`、`projects.md` 和既有资料卡内容保持不变

#### Scenario: 关联资料只修改目标资料卡
- **WHEN** 用户将 reference 关联到一个项目编号
- **THEN** 系统只更新该 reference 的关联字段和索引记录，不重写无关资料卡

### Requirement: Reference 索引可从资料卡重建
Reference Registry SHALL 将 `references/index.jsonl` 视为可重建索引；当索引缺失或损坏时，系统 MUST 能从 `references/cards/*.md` 恢复搜索所需 metadata，或返回可诊断的重建提示。

#### Scenario: 索引文件缺失
- **WHEN** `references/index.jsonl` 缺失但资料卡存在
- **THEN** 系统能够重建索引或返回明确提示，且不删除资料卡

#### Scenario: 索引文件包含损坏记录
- **WHEN** `references/index.jsonl` 包含无法解析的 JSONL 记录但资料卡存在
- **THEN** 系统能够从资料卡重建索引或返回明确提示，且搜索结果不静默丢失可恢复资料

#### Scenario: 索引记录指向缺失资料卡
- **WHEN** 搜索命中一条索引记录但对应资料卡不存在
- **THEN** 系统跳过该条或返回可诊断警告，不影响其他搜索结果
