## Context

Hermes 官方插件文档把通用插件定义为一个可发现目录，核心文件包括 `plugin.yaml`、`__init__.py`、`schemas.py` 和 `tools.py`；插件默认需显式启用，可安装在 `~/.hermes/plugins/<name>/`，项目本地 `.hermes/plugins/` 还需要 `HERMES_ENABLE_PROJECT_PLUGINS=true`。官方构建插件指南要求 handler 使用 `def my_handler(args: dict, **kwargs) -> str`，成功和失败都返回 JSON 字符串，并通过 `ctx.register_tool(name=..., toolset=..., schema=..., handler=...)` 注册工具。

本仓库当前已经有 Hermes 插件根文件和 13 个 GTD tool schema，但 `__init__.py` 仍使用位置参数注册工具，未显式设置 `toolset`；`tools.py` handler 未接收 `**kwargs`，异常保护不完整；Hermes 注册的 skill 仍指向 `.claude/skills/gtd/SKILL.md`；README 以 Claude Code 安装为主。`docs/hermes-review-findings.md` 还记录了项目完成、初始化示例污染、重复 inbox 删除、动态 `GTD_DIR`、日期统计和测试缺失等影响 Hermes 可用性的行为问题。

## Goals / Non-Goals

**Goals:**

- 让项目作为 Hermes Agent 插件独立安装、启用和运行，符合当前 Hermes 插件文档的注册、toolset、handler 和 JSON 返回契约。
- 让 Hermes Agent 加载 GTD skill 后通过 `gtd_*` tools 完成 GTD 工作流，不再依赖 Claude Code 专用 prompt 或脚本命令。
- 修复会破坏真实用户 GTD 数据或统计结果的底层行为缺陷。
- 提供 README、发布结构、依赖说明、忽略规则和自动化测试，使用户可以独立验证 Hermes 适配结果。

**Non-Goals:**

- 不维护 Claude Code marketplace 安装、`.claude` skill 行为或 Claude 命令兼容性。
- 不改变 GTD 方法论本身，也不引入数据库、同步服务或非 Markdown 存储。
- 不增加 Hermes 以外的 Agent 平台适配层。
- 不实现网络服务、后台 daemon 或跨设备同步。

## Decisions

### 1. 以根目录 Hermes 插件为唯一运行入口

实现以 `plugin.yaml`、`__init__.py`、`schemas.py`、`tools.py`、`SKILL.md` 或 `skills/gtd/SKILL.md` 组成 Hermes 插件。`__init__.py` 使用相对导入优先，必要时保留最小路径修正，只服务于插件内模块和迁移后的 GTD 工具代码。

替代方案：继续复用 `.claude/skills/gtd/scripts/`。该方案短期改动较小，但会把 Hermes 运行时耦合到 Claude 目录结构，且 skill 文档会继续诱导 Agent 直接运行脚本。由于用户明确不需要考虑 Claude，本次应将 Hermes 插件作为主结构。

### 2. 所有工具统一归入 `gtd` toolset

`register(ctx)` 遍历 `ALL_SCHEMAS`，对每个有 handler 的 schema 调用 `ctx.register_tool(name=name, toolset="gtd", schema=schema, handler=handler, description=schema.get("description"))`。注册失败应记录清晰错误，避免静默缺工具；如果 Hermes 运行时没有某个可选参数，应通过小型兼容封装降级，但验收以当前官方命名参数形式为准。

替代方案：每个工具单独一个 toolset。该方案会让用户启用和排查成本上升，不符合 GTD 作为一个完整工作流工具集的使用方式。

### 3. 用统一 handler 包装器保证 Hermes JSON 契约

所有公开 handler 形态改为 `def handle_x(args: dict, **kwargs) -> str`。内部使用统一工具函数完成参数字典规范化、必填字段校验、枚举校验、日期格式校验、异常捕获和 JSON 序列化。错误结果统一包含 `ok: false`、`message` 和 `error`，成功结果包含 `ok: true`、`message` 和业务字段。

替代方案：在每个 handler 中手写 try/except 和校验。该方案会导致错误格式漂移，后续新增工具容易遗漏 `SystemExit` 或 `**kwargs`。

### 4. 将 GTD 核心操作从 Claude 脚本迁移为 Hermes 可测试模块

保留 Markdown 文件格式，但把文件路径解析、读写、编号、收集箱移动、项目状态、统计和配置管理抽成插件内可测试 Python 模块，例如 `gtd_core/` 或 `core/`。所有路径在调用时通过 `get_gtd_dir()` 解析，避免模块 import 时固定 `GTD_DIR`。旧 `.claude` 脚本可以删除、停止注册或仅作为非验收遗留文件存在。

替代方案：只在 `tools.py` 外层修补旧脚本。该方案无法可靠解决 import 时路径缓存、`sys.exit`、重复行删除和项目格式不一致问题。

### 5. Hermes 专用 skill 必须要求 tool-first 行为

新增 Hermes skill 文档，注册为 `ctx.register_skill("gtd", skill_path)`，内容说明常见自然语言意图到 `gtd_*` tools 的映射、初始化前置检查、整理收集箱的决策树、错误处理和数据目录说明。文档不得要求 Agent 直接执行 `.claude` 脚本命令。

替代方案：更新原 `.claude/skills/gtd/SKILL.md`。该方案会继续混合平台语义，且路径本身会误导 Hermes 用户。

### 6. 测试以临时 `GTD_DIR` 和 Hermes 契约为核心

新增测试入口，优先覆盖 `register(ctx)` 使用的参数、所有 handler 返回合法 JSON、必填参数错误不抛异常、初始化后统计为空、重复 inbox 只处理一条、`P001` 项目可完成、周一边界和今天截止不误判。测试应使用临时目录隔离用户真实 `~/gtd`。

替代方案：只做手工命令验证。该方案不能防止后续整理代码时再次破坏 Hermes handler 契约或 GTD 数据行为。

## Risks / Trade-offs

- [Risk] 删除或迁移 `.claude` 结构可能影响仍在使用 Claude Code 的用户 -> Mitigation: README 明确本版本目标是 Hermes Agent；如保留遗留文件，也标记为非维护路径。
- [Risk] 迁移底层脚本时可能改变 Markdown 文件格式 -> Mitigation: specs 固化现有用户可见文件名和任务编号语义，只修复错误格式和示例污染。
- [Risk] Hermes 运行时 `ctx.register_tool` 参数在不同版本间存在兼容差异 -> Mitigation: 按当前官方文档实现命名参数注册，并在 README 写明最低 Hermes 版本或验证方式。
- [Risk] handler 捕获所有异常可能掩盖开发期错误 -> Mitigation: JSON 返回保留 `error` 类型和可读消息，测试中直接断言错误场景；必要时使用 logging 记录异常详情。
- [Risk] 自动化测试需要选择测试框架和依赖 -> Mitigation: 使用轻量 `pytest`，不引入额外运行时依赖；测试依赖与运行时依赖分开说明。

## Migration Plan

1. 先修正 Hermes 插件外壳：`plugin.yaml` 元数据、`__init__.py` 注册、Hermes 专用 skill 和 README 安装说明。
2. 再重构 handler 和 GTD 核心操作，保持外部 tool 名称和 JSON 字段稳定。
3. 修复 GTD 数据可靠性问题，并为每个已知问题补测试。
4. 清理发布结构和忽略规则，确保本机缓存不会进入发布包。
5. 使用临时 `GTD_DIR` 跑自动化测试，并用 Hermes 插件启用流程做一次手工验收。

回滚策略：由于本变更不迁移用户已有 `~/gtd` 数据结构到非 Markdown 存储，失败时可恢复插件代码；用户数据目录不应被删除或覆盖。初始化逻辑必须只创建缺失文件，不破坏已有文件。

## Open Questions

- Hermes 最低版本是否需要在 `plugin.yaml` 或 README 中硬性声明；实现时应以当前官方文档和本地可验证 Hermes 版本为准。
- Hermes skill 文件最终放在根目录 `SKILL.md` 还是 `skills/gtd/SKILL.md`；需要以 Hermes 插件发现和 `ctx.register_skill` 的实际行为选择。
