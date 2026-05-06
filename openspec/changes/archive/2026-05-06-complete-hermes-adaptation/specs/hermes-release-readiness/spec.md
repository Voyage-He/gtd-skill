## ADDED Requirements

### Requirement: README 以 Hermes Agent 为主安装路径
README SHALL 以 Hermes Agent 插件为主要目标，MUST 提供用户插件安装、项目本地插件启用、插件启用和启动验证步骤。

#### Scenario: 用户插件安装
- **WHEN** 用户阅读 README 的安装章节
- **THEN** 用户能看到将项目安装到 `~/.hermes/plugins/gtd` 或通过 Hermes 插件安装命令安装并启用 `gtd` 的步骤

#### Scenario: 项目本地插件启用
- **WHEN** 用户希望在当前项目中以本地插件方式测试
- **THEN** README 说明 `.hermes/plugins/` 的信任边界，并要求设置 `HERMES_ENABLE_PROJECT_PLUGINS=true`

### Requirement: README 说明工具列表和 JSON 返回
README SHALL 列出全部 `gtd_*` tools、典型自然语言用法、关键参数、`GTD_DIR` 配置和 JSON 返回示例。

#### Scenario: 用户查找 tool 用途
- **WHEN** 用户想知道如何记录、整理、完成或回顾任务
- **THEN** README 提供对应自然语言示例和底层 `gtd_*` tool 名称

#### Scenario: 用户排查工具失败
- **WHEN** 工具返回 `ok: false`
- **THEN** README 说明 `message`、`error` 和常见失败原因的处理方式

### Requirement: 发布结构不依赖 Claude Code
面向 Hermes 的发布包 SHALL 包含 Hermes 运行所需文件，MUST 不要求 Claude Code marketplace、Claude slash commands 或 `.claude` skill 才能完成安装和使用。

#### Scenario: 最小 Hermes 插件目录
- **WHEN** 用户复制发布包到 `~/.hermes/plugins/gtd`
- **THEN** 目录包含 Hermes 运行所需的 `plugin.yaml`、`__init__.py`、`schemas.py`、`tools.py`、Hermes skill 和 GTD 核心模块

#### Scenario: Claude 文件不存在
- **WHEN** 发布包不包含 `.claude/` 目录
- **THEN** Hermes 插件仍能注册工具、注册 skill 并通过测试

### Requirement: 依赖声明清晰可安装
项目 SHALL 明确运行时依赖和测试依赖；如果 `PyYAML` 是可选增强，MUST 在文档和依赖文件中体现可选性；如果是必需依赖，MUST 在安装步骤中要求安装。

#### Scenario: 新环境安装依赖
- **WHEN** 用户在干净 Python 环境安装插件依赖
- **THEN** README 和依赖文件给出一致命令，安装后 Hermes handler 不因缺少依赖而失败

#### Scenario: PyYAML 不存在
- **WHEN** 环境未安装 `PyYAML` 且项目声明其为可选依赖
- **THEN** 配置读写使用 fallback 格式并返回成功 JSON

### Requirement: 仓库忽略本地生成文件
项目 SHALL 提供根目录 `.gitignore`，MUST 忽略 `.DS_Store`、`__pycache__/`、`*.pyc`、测试缓存和其他本地生成文件。

#### Scenario: 本地运行测试后检查工作副本
- **WHEN** 开发者运行测试或导入 Python 模块
- **THEN** 新生成的缓存文件被 `.gitignore` 覆盖，不进入待发布文件清单

### Requirement: 自动化验证入口可运行
项目 SHALL 提供自动化测试入口，MUST 覆盖 Hermes 注册契约、handler JSON 契约、GTD 数据可靠性和 README 中声明的关键工作流。

#### Scenario: 运行测试命令
- **WHEN** 开发者执行 README 或项目配置中声明的测试命令
- **THEN** 测试使用临时 `GTD_DIR` 运行，不读取或修改用户真实 `~/gtd` 数据

#### Scenario: Hermes 注册测试
- **WHEN** 测试调用插件 `register(ctx)` 的 fake context
- **THEN** 测试验证 13 个工具、`gtd` toolset 和 Hermes 专用 skill 均已注册
