# Hermes Agent GTD Plugin

Hermes Agent GTD 插件基于 Getting Things Done 方法论，通过 23 个 `gtd_*` tools 维护一套 Markdown 任务系统。默认数据目录是 `~/gtd`，也可以用 `GTD_DIR` 指向其他目录。

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

核心数据操作只依赖 Python 标准库，文件锁目前面向 macOS/Linux 本地文件系统。`PyYAML>=5.1` 是可选增强，用于以 YAML 格式读写配置；未安装时自动使用 JSON。

```bash
python3 -m pip install 'PyYAML>=5.1'
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
- `storage.py`
- `reminders.py`
- `skills/gtd/SKILL.md`
- `README.md`
- `LICENSE`

发布前确认没有 `.DS_Store`、`__pycache__/`、`*.pyc` 或测试缓存进入文件清单。

## 许可

MIT

## 转发通知与资料召回

把通知原文、照片和文件转发到已接入 Hermes 的聊天后，Agent 使用
`gtd_message_capture` 保存为一条资料。文字可以为空；多个附件自动复制保存，
不依赖渠道临时下载路径。`reference_id` 可将明确属于同一通知的补发附件或日期补充进去。
渠道提供的 channel/chat_id/message_id 用于重复投递去重；缺失来源信息不会猜测。

| 工具 | 用途 |
|---|---|
| `gtd_message_capture` | 保存原文、多附件副本、来源、提取文字和通知日期 |
| `gtd_reference_add` | 登记普通备忘、链接或单个本地文件 |
| `gtd_reference_search` | 搜索元数据和提取文字，可同时按关联编号过滤 |
| `gtd_reference_get` | 获取完整资料卡、原文和附件列表 |
| `gtd_reference_link` | 关联项目或任务 |
| `gtd_reference_read` | 分段读取 UTF-8 文本；支持附件序号与字符偏移 |
| `gtd_reference_files` | 准备原文和附件的 Hermes MEDIA 回传标签 |
| `gtd_reference_reindex` | 手工修改资料卡后重建索引，返回跳过记录 |
| `gtd_notice_update` | 标记通知事项已处理或重新打开 |
| `gtd_reminder` | 创建/更新、查询、暂停、试运行 Hermes 每日提醒 |

例：“找上次张三发的报名通知，把报名表发回来。”Agent 搜索资料，选中后
通过 `gtd_reference_files` 获取原件，使用 Hermes 的 MEDIA 标签回复。
`prepared` 仅表示文件已准备，真实送达由渠道处理。

图片文字提取由 Hermes 可用的视觉工具完成，存入 `extracted_text`，原图保留。
插件本身不内置 OCR/PDF 解析器，不会假装能直接读二进制附件。没有提取文字的
图片仍可按标题、标签、来源检索。通知中的明确日期可存入 `notices`；含糊的
“下周五”等表述要有可靠原始日期才能转换。

## 每日自动提醒

在已连接的 Hermes 聊天里说：“每天北京时间九点提醒我今天要做的事。”
Agent 调用 `gtd_reminder(action="enable", time="09:00", timezone="Asia/Shanghai")`。
默认发回启用时的聊天；可显式指定一个 `platform:chat_id` 目标。
改时间会更新已有任务，省略目标时保留原接收人，不重复创建任务。

- `status`：查看真实调度状态、下次执行时间及运行结果。
- `disable`：暂停。
- `run`：请求试运行，仍需检查后续执行和投递结果。

每天包含逾期、今天/明天截止任务、等待跟进、通知日期和未整理数量；没有待办
也简短告知。通知项通过 `gtd_notice_update` 标记处理后不再提醒。
当前 `notifications.*`、`review.*` 配置字段只是偏好记录，**不会创建定时任务**。

需要支持 `ctx.dispatch_tool` 和 `cronjob_manage` 的 Hermes 版本；Gateway 必须
在线，Hermes 时区须与指定时区一致，并配置可用模型及收发渠道。
插件不自动安装 Hermes，不在启用前创建真实任务。配置成功不等于消息已经送达。
QQ/微信的附件下载、文件发送和主动推送限制取决于对应适配器，部署后须实机验证。

官方接口参考：[定时任务](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron/)、
[插件接口](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins/)。

## 数据可靠性与兼容

- GTD 操作使用进程/线程锁与持久化撤销日志；异常会回滚，进程中断后下次调用先恢复。
- 锁约束插件调用；外部编辑器不会遵守该锁，避免与插件同时修改同一份数据。
- 序号存入 `sequences.json`，并扫描历史归档兼容旧数据，支持超过三位的编号。
- `captures.jsonl` 保存收集历史用于周统计。已有系统首次收集时只补录当前收集箱，
  无法推断过去已经移走且未留下收集日期的条目。
- 旧单附件资料卡仍可使用；新资料卡使用 JSON front matter（YAML 子集），避免依赖变化
  导致新卡不可读。读取历史 YAML 卡仍需 PyYAML。
- 文本附件限量读取，未读到末尾时 `total_chars` 为 null，使用 `next_offset` 继续读。
- 自动测试使用临时目录，覆盖回滚、崩溃恢复、并发、消息归组、原件保留和模拟调度。
  这些测试不代表已验证真实 QQ/微信送达。
