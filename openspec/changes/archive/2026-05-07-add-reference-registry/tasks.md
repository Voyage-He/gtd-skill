## 1. Reference 数据模型与初始化

- [x] 1.1 在 `gtd_core.py` 中定义 reference 资料卡字段、附件字段、读取策略、托管策略和 `RYYYYMMDD-NNN` ID 生成规则
- [x] 1.2 扩展 `ensure_gtd_dir()` 或 `init_gtd()`，幂等创建 `references/cards/`、`references/assets/`、`references/cache/` 和 `references/index.jsonl`
- [x] 1.3 实现资料卡 Markdown front matter 读写、JSONL 索引追加/更新和从 `cards/*.md` 重建索引的内部函数
- [x] 1.4 实现规范文件名建议函数，生成包含 reference ID、主题、用途、来源或责任人和版本的安全文件名

## 2. Reference 核心操作

- [x] 2.1 实现 `add_reference`，支持 memo、link、本地文件附件和可选 `related_items`、tags、aliases、people、project、source
- [x] 2.2 实现附件登记逻辑，默认只读取文件元数据，支持 `link` 和 `copy` 托管策略，并处理路径不存在错误
- [x] 2.3 实现 `search_references`，按 metadata、短备注和关联编号检索，返回命中字段，确保不读取附件正文
- [x] 2.4 实现 `get_reference`，按 reference ID 返回资料卡详情和附件元数据
- [x] 2.5 实现 `link_reference`，将 reference 与 `N`、`W`、`P` 编号或 inbox 原文关联，并校验编号格式
- [x] 2.6 实现 `read_reference`，仅在显式调用时读取附件内容或缓存预览，并返回截断、范围和失败原因

## 3. Tool schema 与 handler

- [x] 3.1 在 `schemas.py` 中新增 `gtd_reference_add`、`gtd_reference_search`、`gtd_reference_get`、`gtd_reference_link`、`gtd_reference_read` 的 JSON schema
- [x] 3.2 在 `tools.py` 中新增对应 handler，保持 `args: dict, **kwargs` 输入和 JSON 字符串输出契约
- [x] 3.3 更新 `ALL_SCHEMAS`、`HANDLERS` 和 `plugin.yaml`，确保新工具被 Hermes 注册且 schema/handler 一一对应
- [x] 3.4 更新 handler 校验或错误处理，确保 reference 业务错误返回 `ok: false`，不泄漏异常

## 4. Hermes skill 工作流

- [x] 4.1 更新 `skills/gtd/SKILL.md` 的 Tool Mapping，加入 reference 新增、搜索、查看、关联和读取工具
- [x] 4.2 写明 metadata-first 策略：搜索、列表、查看和关联默认不读取附件正文
- [x] 4.3 写明 GTD reference memo 与 Hermes Agent memory 的边界和自然语言示例
- [x] 4.4 写明文件命名建议和 `link`/`copy` 托管策略的用户交互方式

## 5. 测试与验证

- [x] 5.1 添加核心数据测试：初始化目录、创建 memo/link/file 资料卡、重复初始化不覆盖数据
- [x] 5.2 添加附件测试：路径不存在失败、link 不复制文件、copy 复制到 `references/assets/YYYY/MM/` 并使用规范文件名
- [x] 5.3 添加搜索测试：按标题、标签、别名、项目编号和短备注命中，且搜索过程不读取附件正文
- [x] 5.4 添加关联和读取测试：合法编号写入 `related_items`，非法编号不修改资料卡，显式读取返回截断信息
- [x] 5.5 更新插件运行时测试，避免硬编码旧工具数量，并验证所有 `gtd_reference_*` schema 有对应 handler
- [x] 5.6 运行现有测试套件和 OpenSpec 验证，确认旧 GTD 工作流仍兼容
