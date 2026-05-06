## 1. Hermes 插件运行时

- [ ] 1.1 更新 `plugin.yaml`，将项目描述调整为 Hermes Agent GTD 插件，并声明 13 个 `gtd_*` tools、版本和 `requires_env`
- [ ] 1.2 重构 `__init__.py` 的导入和注册流程，使用 `ctx.register_tool(name=..., toolset="gtd", schema=..., handler=..., description=...)`
- [ ] 1.3 在 `__init__.py` 中注册 Hermes 专用 GTD skill，不再引用 `.claude/skills/gtd/SKILL.md`
- [ ] 1.4 新增 Hermes 专用 `SKILL.md` 或 `skills/gtd/SKILL.md`，写明 tool-first GTD 工作流和自然语言到 `gtd_*` tools 的映射
- [ ] 1.5 校准 `schemas.py`，确保 `ALL_SCHEMAS` 中每个 schema 的名称、参数、必填字段和枚举与 handler 行为一致
- [ ] 1.6 在 `tools.py` 中新增统一 JSON 结果、参数校验和异常包装机制，捕获 `SystemExit`、参数错误和底层异常
- [ ] 1.7 将所有公开 handler 改为 `def handle_x(args: dict, **kwargs) -> str` 形态，并保持成功和失败都返回 JSON 字符串

## 2. GTD 核心数据可靠性

- [ ] 2.1 新增或迁移 GTD 核心模块，集中处理 `GTD_DIR` 调用时解析、文件路径、读写和基础 Markdown 工具函数
- [ ] 2.2 重写或迁移初始化逻辑，保证 `gtd_init` 幂等创建文件且不写入真实编号的未完成示例任务
- [ ] 2.3 重写或迁移收集箱读取和移动逻辑，保留条目物理行位置并只删除用户选择的一条记录
- [ ] 2.4 实现 `next_actions`、`waiting_for`、`projects`、`reference`、`someday_maybe`、`done` 和 `trash` 目标移动的结构化结果
- [ ] 2.5 修复 `gtd_complete` 对 `N`、`W` 和 `P` 编号的支持，特别是将项目状态标记为已完成并记录完成日期
- [ ] 2.6 修复 `gtd_archive`，确保只归档已完成任务并保留无关章节和用户备注
- [ ] 2.7 修复每日检查、周回顾和统计逻辑，按日期边界处理本周范围、今天截止、昨天截止和明天截止
- [ ] 2.8 统一配置读取和写入行为，明确 `PyYAML` 缺失时的 fallback 路径并返回结构化 JSON

## 3. Hermes Agent 工作流与文档

- [ ] 3.1 更新 README 标题、简介和安装章节，以 Hermes Agent 插件为主目标
- [ ] 3.2 在 README 中补充 `~/.hermes/plugins/gtd`、`hermes plugins enable gtd` 和项目本地插件 `HERMES_ENABLE_PROJECT_PLUGINS=true` 的使用说明
- [ ] 3.3 在 README 中列出全部 `gtd_*` tools、典型自然语言用法、关键参数、`GTD_DIR` 配置和 JSON 返回示例
- [ ] 3.4 在 README 中加入常见错误排查，说明 `ok: false`、`message`、`error` 和未初始化、编号不存在、参数非法等场景
- [ ] 3.5 明确依赖策略，调整 `requirements.txt` 或 README，使 `PyYAML` 必需或可选的语义一致
- [ ] 3.6 新增根目录 `.gitignore`，忽略 `.DS_Store`、`__pycache__/`、`*.pyc`、测试缓存和本地生成文件
- [ ] 3.7 清理或停止依赖 Claude Code 专用文件，确保缺少 `.claude/` 时 Hermes 插件仍可注册并运行

## 4. 自动化测试

- [ ] 4.1 新增测试入口和配置，使用临时 `GTD_DIR`，避免读取或修改用户真实 `~/gtd`
- [ ] 4.2 添加 fake Hermes context 测试，验证 `register(ctx)` 注册 13 个工具、统一 `gtd` toolset 和 Hermes 专用 skill
- [ ] 4.3 添加 handler 契约测试，验证所有 `gtd_*` handler 接收 `**kwargs`、返回可解析 JSON，并在缺参或异常时不抛出
- [ ] 4.4 添加初始化和配置测试，验证初始化后统计为空、重复初始化不覆盖数据、`PyYAML` fallback 可用
- [ ] 4.5 添加收集箱测试，覆盖重复条目只处理一条、非法索引不修改文件和各 target 移动结果
- [ ] 4.6 添加任务完成和归档测试，覆盖 `N`、`W`、`P` 编号完成、项目完成状态和归档保留未完成内容
- [ ] 4.7 添加日期统计测试，覆盖周一零点、本周新增、今天截止不算过期、昨天截止算过期
- [ ] 4.8 添加 README 或 skill 文档断言，确保 Hermes 文档不要求直接运行 `.claude` 脚本命令

## 5. 验证与收尾

- [ ] 5.1 运行完整自动化测试命令，确认所有测试通过
- [ ] 5.2 使用临时插件目录执行一次 Hermes 注册级手工验收，确认工具和 skill 可被发现
- [ ] 5.3 用临时 `GTD_DIR` 手工验证初始化、记录、整理、完成、统计和周回顾主流程
- [ ] 5.4 检查发布文件清单，确认没有 `.DS_Store`、`__pycache__`、`*.pyc` 或其他本地生成文件
- [ ] 5.5 更新 OpenSpec tasks 勾选状态，并准备进入 verify/archive 流程
