## ADDED Requirements

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
