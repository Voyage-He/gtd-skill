## Why

当前项目已经有 Hermes 插件入口和 13 个 `gtd_*` tools，但注册方式、handler 形态、skill 文档、README 和底层 GTD 脚本仍带有明显的 Claude Code 迁移痕迹。Hermes Agent 用户需要一个可以按官方插件约定安装、启用、调用、测试和发布的完整适配版本，且本次可以不再为 Claude Code 兼容性保留实现约束。

## What Changes

- 将项目主目标调整为 Hermes Agent 插件，按 Hermes 官方插件结构维护 `plugin.yaml`、`__init__.py`、`schemas.py`、`tools.py` 和插件内 `SKILL.md`。
- 修复 Hermes 工具注册，所有 GTD 工具通过 `ctx.register_tool(name=..., toolset="gtd", schema=..., handler=...)` 归入 `gtd` toolset。
- 将所有 handler 统一为 Hermes 兼容形态，接收 `args: dict, **kwargs`，返回 JSON 字符串，并把参数错误、`SystemExit`、底层异常转换为结构化错误结果。
- 新增 Hermes 专用 GTD skill，指导 Agent 优先调用 `gtd_*` tools，而不是直接执行 Claude 脚本命令。
- 整理底层 GTD 文件操作，使 `GTD_DIR` 在工具调用时解析，修复项目完成、初始化示例污染、重复 inbox 条目误删、日期边界和统计偏差。
- 更新 README 和发布文件，提供 Hermes 安装路径、项目本地插件启用说明、tool 列表、返回 JSON 示例、`GTD_DIR` 配置、测试和故障排查。
- 增加自动化测试入口，覆盖 Hermes 注册、handler JSON 契约、GTD 数据迁移行为、日期统计和关键用户工作流。
- **BREAKING**: Claude Code marketplace、`.claude/skills/gtd/SKILL.md` 和 Claude 专用安装路径不再作为验收目标；实现可以删除、迁移或停止维护 Claude 专用集成。

## Capabilities

### New Capabilities

- `hermes-plugin-runtime`: 覆盖 Hermes 插件清单、工具注册、toolset 归属、handler 签名、JSON 返回和错误处理契约。
- `hermes-gtd-agent-workflow`: 覆盖 Hermes Agent 加载 GTD skill 后的自然语言工作流、tool 使用优先级、初始化、收集、整理、执行、回顾和配置行为。
- `gtd-data-reliability`: 覆盖 GTD Markdown 数据文件的正确性，包括动态 `GTD_DIR`、编号、项目完成、重复 inbox 条目、初始化样例、日期边界和统计结果。
- `hermes-release-readiness`: 覆盖面向 Hermes 用户的安装文档、插件发布结构、依赖说明、忽略规则和自动化验证入口。

### Modified Capabilities

- 无。当前仓库没有已归档的 OpenSpec specs，本次新增 Hermes 适配相关 capability。

## Impact

- 影响 Hermes 插件入口：`plugin.yaml`、`__init__.py`、`schemas.py`、`tools.py`。
- 影响 Agent 行为文档：新增或迁移 Hermes 专用 `SKILL.md`，停止依赖 `.claude/skills/gtd/SKILL.md` 作为 Hermes skill。
- 影响 GTD 脚本和 Markdown 文件语义：初始化文件模板、收集箱处理、项目完成、日期统计、归档和配置读取。
- 影响文档和发布体验：`README.md`、`.gitignore`、依赖说明和插件安装说明。
- 影响测试体系：新增测试目录、测试配置和基于临时 `GTD_DIR` 的回归测试。
