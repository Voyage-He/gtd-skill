# Hermes Agent GTD Plugin

Hermes Agent GTD 插件基于 Getting Things Done 方法论，通过 13 个 `gtd_*` tools 维护一套 Markdown 任务系统。默认数据目录是 `~/gtd`，也可以用 `GTD_DIR` 指向其他目录。

## 安装

### 用户级插件

```bash
mkdir -p ~/.hermes/plugins
cp -R /path/to/gtd-skill ~/.hermes/plugins/gtd
hermes plugins enable gtd
```

启动 Hermes 后，确认 `gtd` toolset 中可以看到 `gtd_init`、`gtd_capture` 等工具。

### 项目本地插件

项目本地插件位于当前项目的 `.hermes/plugins/`，只应在信任该项目内容时启用：

```bash
mkdir -p .hermes/plugins
cp -R /path/to/gtd-skill .hermes/plugins/gtd
export HERMES_ENABLE_PROJECT_PLUGINS=true
hermes plugins enable gtd
```

## 数据目录

默认使用 `~/gtd`。临时测试或多套系统可以这样指定目录：

```bash
export GTD_DIR="/path/to/gtd"
```

首次使用时让 Agent 执行“初始化 GTD”，插件会调用 `gtd_init` 幂等创建缺失文件，不会覆盖已有 Markdown 数据。

## Tools

| Tool | 典型说法 | 关键参数 |
|------|----------|----------|
| `gtd_init` | 初始化 GTD | 无 |
| `gtd_capture` | 记录买牛奶 | `content` |
| `gtd_inbox` | 看看收集箱 | 无 |
| `gtd_inbox_process` | 把第 1 条整理成下一步行动 | `index`, `target`, 可选 `context`, `deadline`, `delegate`, `estimated`, `project_name`, `first_action` |
| `gtd_next_number` | 下一个项目编号 | `prefix`: `N`, `W`, `P` |
| `gtd_list_actions` | 今天有什么下一步行动 | 可选 `context`, `show_all` |
| `gtd_complete` | 完成 N001 | `number`: `N001`, `W001`, `P001` |
| `gtd_archive` | 归档已完成任务 | 无 |
| `gtd_daily_check` | 今天做什么 | 无 |
| `gtd_weekly_review` | 做周回顾 | 无 |
| `gtd_stats` | 查看统计 | 无 |
| `gtd_config_get` | 查看配置 | 可选 `key` |
| `gtd_config_set` | 修改回顾时间 | `key`, `value` |

`gtd_inbox_process` 的 `target` 支持：

`trash`, `reference`, `someday_maybe`, `done`, `next_actions`, `waiting_for`, `projects`

## JSON 返回

所有 handler 都返回 JSON 字符串。成功结果包含 `ok: true` 和 `message`，失败结果包含 `ok: false`、`message` 和 `error`。

```json
{
  "ok": true,
  "message": "已记录: 买牛奶",
  "content": "买牛奶",
  "date": "2026-05-06",
  "gtd_dir": "/Users/me/gtd"
}
```

```json
{
  "ok": false,
  "message": "缺少必填参数: content",
  "error": {
    "type": "GTDValidationError",
    "detail": "缺少必填参数: content"
  }
}
```

## 常见问题

- 未初始化或文件缺失：调用 `gtd_init`。
- 编号不存在：先调用 `gtd_list_actions` 或检查编号前缀，`gtd_complete` 支持 `N`、`W`、`P`。
- 参数非法：查看返回里的 `message`，例如 `target` 必须是上面列出的枚举值，日期必须是 `YYYY-MM-DD`。
- 工具返回 `ok: false`：Hermes 会话不会中断，按 `message` 修正参数后重试。
- 配置文件：`PyYAML` 可选。安装后使用 `config.yaml`；未安装时使用 `config.json` fallback。

## 依赖

运行时只依赖 Python 标准库。`PyYAML>=5.1` 是可选增强，用于以 YAML 格式读写配置；未安装时自动使用 JSON。

```bash
python3 -m pip install PyYAML>=5.1
```

## 测试

测试使用临时 `GTD_DIR`，不会读取或修改真实 `~/gtd`。

```bash
python3 -m unittest discover -s tests
```

## 发布文件

Hermes 插件最小发布目录应包含：

- `plugin.yaml`
- `__init__.py`
- `schemas.py`
- `tools.py`
- `gtd_core.py`
- `skills/gtd/SKILL.md`
- `README.md`
- `LICENSE`

发布前确认没有 `.DS_Store`、`__pycache__/`、`*.pyc` 或测试缓存进入文件清单。

## 许可

MIT
