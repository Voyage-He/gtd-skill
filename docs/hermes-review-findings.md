# Hermes Agent 审查问题记录

记录日期：2026-05-06

## 背景

本文件用于保存当前项目面向 Hermes Agent 使用时的审查发现，避免只存在于对话上下文中。本文只记录问题和后续建议，不代表已完成修复。

参考范围：
- Hermes 官方插件文档：`plugin.yaml`、`__init__.py`、`schemas.py`、`tools.py` 插件结构。
- Hermes 官方构建插件指南：handler 推荐形态为 `def handler(args: dict, **kwargs) -> str`，工具返回 JSON 字符串，异常应转换为可读错误结果。
- 本仓库当前根目录插件入口、GTD 脚本、Claude skill、README 和 OpenSpec 配置。

## P0 - Hermes 使用前优先处理

### 1. Hermes 工具注册方式可能不符合当前官方示例

问题：`__init__.py` 当前使用 `ctx.register_tool(name, schema, handler)` 位置参数注册工具，没有显式传入 `toolset`。当前 Hermes 官方示例使用命名参数注册，包括 `name`、`toolset`、`schema`、`handler`。

影响：如果 Hermes 当前运行时严格按官方示例接口解析，插件可能注册失败，或工具不会按预期归入 GTD toolset。

证据：
- `__init__.py:21` 定义 `register(ctx)`。
- `__init__.py:30` 调用 `ctx.register_tool(name, schema, handler)`。

建议后续动作：
- 新建 OpenSpec change 专门处理 Hermes 注册兼容。
- 将注册改为当前 Hermes 文档推荐的命名参数形式。
- 给所有工具统一设置 `toolset="gtd"`。
- 若需要兼容旧 Hermes 版本，可以加兼容分支或最小运行时版本说明。

### 2. Hermes handler 形态缺少 `**kwargs` 和统一异常保护

问题：`tools.py` 中所有 handler 只接收单个 `params` 参数，例如 `handle_capture(params)`。Hermes 官方指南推荐 handler 接收 `args: dict, **kwargs`，并且工具应返回 JSON 字符串，不能把异常直接抛给运行时。

影响：Hermes 运行时如果传入额外上下文参数，当前 handler 可能因签名不兼容报错。底层脚本中的 `sys.exit`、`KeyError`、文件 IO 错误也可能直接中断工具调用。

证据：
- `tools.py:28`、`tools.py:37`、`tools.py:68` 等 handler 均未接收 `**kwargs`。
- `tools.py:40` 直接读取 `params["content"]`。
- `.claude/skills/gtd/scripts/add_to_inbox.py:18` 会在空内容时 `sys.exit(1)`。
- `.claude/skills/gtd/scripts/process_inbox.py:76` 对未知 prefix 直接字典索引，可能触发 `KeyError`。

建议后续动作：
- 增加统一包装器，将 handler 输入标准化并捕获 `Exception` 和 `SystemExit`。
- 保持返回格式统一为 `{"ok": false, "message": "...", "error": "..."}`。
- 为必填参数缺失、非法枚举、日期格式错误增加显式错误结果。

### 3. Hermes 注册的 skill 仍是 Claude Code 专用行为文档

问题：`__init__.py` 注册 `.claude/skills/gtd/SKILL.md` 作为 Hermes skill，但该文件大量指令要求 agent 执行 `python scripts/...`，并多处使用 Claude 角色表述。

影响：Hermes Agent 可能绕过已注册的 `gtd_*` tools，尝试直接运行脚本命令，造成行为不一致，也降低工具 schema 的价值。

证据：
- `__init__.py:33` 到 `__init__.py:37` 注册 `.claude/skills/gtd/SKILL.md`。
- `.claude/skills/gtd/SKILL.md:30` 要求首次使用时运行 `python scripts/init_gtd.py`。
- `.claude/skills/gtd/SKILL.md:38`、`:46`、`:103` 等位置描述运行脚本命令。

建议后续动作：
- 新增 Hermes 专用 skill 文档，例如 `skills/gtd/SKILL.md`。
- Hermes skill 中明确要求优先调用 `gtd_init`、`gtd_capture`、`gtd_inbox`、`gtd_inbox_process` 等工具。
- 保留 Claude skill 作为 Claude Code 集成，不与 Hermes 注册混用。

## P1 - 行为正确性和可靠性

### 4. `gtd_complete P001` 无法完成项目

问题：项目创建时写入的是 Markdown 标题 `### P001: 项目名称`，但完成逻辑只匹配任务行 `- [ ] P001: ...`。

影响：schema 宣称 `gtd_complete` 支持 `P` 项目编号，但实际无法标记项目完成。

证据：
- `schemas.py:127` 描述支持 `N/W/P`。
- `.claude/skills/gtd/scripts/process_inbox.py:194` 创建项目标题 `### {project_num}: ...`。
- `.claude/skills/gtd/scripts/complete_action.py:41` 只匹配 `^(- \[ \])\s*(P001:.*)$`。

建议后续动作：
- 为项目完成单独实现标题块状态更新，例如将 `- **状态**: 活跃` 改为 `已完成` 并追加完成日期。
- 或调整项目文件格式，使项目也有可匹配的 checkbox 行。
- 增加 `P001` 完成场景测试。

### 5. 初始化会创建未完成等待事项示例 `W001`

问题：`init_gtd.py` 初始化的 `waiting_for.md` 包含一个未完成示例任务 `W001`。

影响：新用户刚初始化后统计会显示已有等待事项，`get_next_number("W")` 也会从 `W002` 开始，污染真实任务编号。

证据：
- `.claude/skills/gtd/scripts/init_gtd.py:92` 写入 `- [ ] W001: （示例）等待同事提供数据 ...`。

建议后续动作：
- 将示例改成代码块、注释文本或格式说明，不使用真实 checkbox 编号。
- 初始化后验证统计应为 0 个等待事项。

### 6. 收集箱移除逻辑可能误删重复条目

问题：`remove_from_inbox(raw_line)` 通过整行文本过滤删除条目。如果 inbox 中存在两条完全相同内容和元数据的行，会一次删除多条。

影响：在重复记录或快速导入时可能丢失用户数据。

证据：
- `.claude/skills/gtd/scripts/process_inbox.py:99` 使用 `[l for l in lines if l.rstrip('\n') != raw_line]` 删除。

建议后续动作：
- 按选中的物理行号删除，或在 `read_inbox_items()` 中记录 line index。
- 增加重复条目的处理测试。

### 7. GTD 目录在模块 import 时固定

问题：多个脚本在模块加载时执行 `GTD_DIR = get_gtd_dir()`。如果 Hermes 运行时在插件加载后才设置或更新 `GTD_DIR`，后续调用不会感知新值。

影响：多用户、多工作区或动态配置场景下，工具可能写入错误目录。

证据：
- `.claude/skills/gtd/scripts/init_gtd.py:10`
- `.claude/skills/gtd/scripts/process_inbox.py:27`
- `.claude/skills/gtd/scripts/add_to_inbox.py:10`
- `.claude/skills/gtd/scripts/complete_action.py:12`

建议后续动作：
- 将路径解析延迟到函数调用时。
- 避免长期缓存 `GTD_DIR`、`INBOX_FILE`。
- 为 `GTD_DIR` 环境变量覆盖添加测试。

## P1 - 日期和统计偏差

### 8. 本周范围保留当前时分秒，可能漏算周一早些时候数据

问题：`get_week_range()` 使用当前时间减去 weekday，得到的周一仍带有当前时分秒。

影响：周一当天早于当前时间的新增项或完成项可能不计入本周统计。

证据：
- `.claude/skills/gtd/scripts/gtd_utils.py:85` 使用 `today = datetime.now()`。
- `.claude/skills/gtd/scripts/gtd_utils.py:86` 直接计算 `monday = today - timedelta(days=today.weekday())`。

建议后续动作：
- 使用 `date` 比较，或将 monday 归零到 `00:00:00`、sunday 设置为当天结束。
- 增加周一边界测试。

### 9. 今天截止的任务可能被周回顾判定为过期

问题：`weekly_review.py` 将 deadline 解析为当天 `00:00:00`，再与当前时间比较；今天的 deadline 在当前时间之后会被判断为 `d < today`。

影响：周回顾中今天截止的未完成任务可能错误显示为过期。

证据：
- `.claude/skills/gtd/scripts/weekly_review.py:58` 使用 `today = datetime.now()`。
- `.claude/skills/gtd/scripts/weekly_review.py:64` 解析 deadline 为日期零点。
- `.claude/skills/gtd/scripts/weekly_review.py:65` 使用 `if d < today`。

建议后续动作：
- 改为比较 `d.date() < today.date()`。
- 增加今天、昨天、明天 deadline 的回归测试。

## P2 - 文档、测试和发布清理

### 10. README 仍以 Claude Code 安装和使用为主

问题：README 标题和安装说明主要面向 Claude Code，没有 Hermes Agent 安装、启用、工具列表和返回 JSON 示例。

影响：以 Hermes Agent 为主要目标时，用户无法按 README 独立完成安装和验证。

证据：
- `README.md:3` 写明“为 Claude Code 打造”。
- `README.md:11` 到 `README.md:35` 只描述 `claude plugin` 和 `~/.claude/skills/gtd`。

建议后续动作：
- 增加 Hermes Agent 安装路径，例如 `~/.hermes/plugins/gtd`。
- 增加 Hermes tool 列表、典型调用、`GTD_DIR` 说明和故障排查。
- 将 Claude Code 内容标记为兼容集成，而非唯一目标。

### 11. 仓库缺少忽略规则，当前工作副本包含生成文件

问题：当前工作副本新增了 `.DS_Store`、`__pycache__`、`*.pyc` 等生成文件，根目录没有项目级 `.gitignore`。

影响：发布插件时容易把本机缓存和二进制文件带入仓库。

证据：
- `jj st` 显示 `.DS_Store`、`__pycache__/schemas.cpython-314.pyc`、`__pycache__/tools.cpython-314.pyc` 等新增。
- `find . -maxdepth 3 ...` 未发现根目录 `.gitignore`。

建议后续动作：
- 新增根目录 `.gitignore`，忽略 `.DS_Store`、`__pycache__/`、`*.py[cod]` 等。
- 清理已进入工作副本的生成文件。
- 清理前先确认哪些新增文件属于预期插件内容。

### 12. 缺少自动化测试入口

问题：当前仓库未发现 `pytest`、`pyproject.toml`、`Makefile` 或测试文件。

影响：后续修复 Hermes handler、日期统计和文件移动逻辑时，容易出现回归。

证据：
- 未发现 `test_*.py`、`*_test.py`。
- 未发现 `pyproject.toml`、`pytest.ini`、`Makefile`。

建议后续动作：
- 增加基于临时 `GTD_DIR` 的单元测试。
- 优先覆盖 handler JSON 返回、收集箱重复条目、项目完成、周一边界和今天截止判断。

### 13. PyYAML 声明为依赖但本地环境未安装

问题：`requirements.txt` 声明 `PyYAML>=5.1`，但本地 `python3 -B -c "import yaml"` 失败。代码有 JSON fallback，但 README 将 PyYAML 标为可选，依赖文件又要求安装。

影响：实际安装语义不清晰。Hermes 用户可能不知道是否必须安装依赖。

证据：
- `requirements.txt:1` 为 `PyYAML>=5.1`。
- `.claude/skills/gtd/scripts/config_manager.py:17` 到 `:22` 提供 fallback。
- 本地导入 `yaml` 失败。

建议后续动作：
- 明确 PyYAML 是必需依赖还是可选增强。
- 如果可选，考虑不在硬性 requirements 中列出，或在 README 说明 fallback 行为。
- 如果必需，移除 fallback 或在 Hermes 安装说明中要求安装依赖。

## 后续拆分建议

建议按以下顺序拆分后续 OpenSpec changes：

1. `fix-hermes-plugin-registration`: 修复 `register_tool`、`toolset`、handler 签名和异常包装。
2. `add-hermes-gtd-skill`: 新增 Hermes 专用 `SKILL.md`，让 agent 使用 `gtd_*` tools。
3. `fix-gtd-task-behavior`: 修复项目完成、初始化示例和重复 inbox 删除。
4. `fix-gtd-date-statistics`: 修复本周范围和过期判断。
5. `prepare-plugin-release`: 补 README、`.gitignore`、清理生成文件并增加基础测试。
