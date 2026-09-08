# Hermes Agent GTD Plugin

Hermes Agent GTD 插件基于 Getting Things Done 方法论，通过 `gtd_*` tools 维护一套 Markdown 任务与资料系统。默认数据目录是 `~/gtd`，也可以用 `GTD_DIR` 指向其他目录。

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
- `materials.py`
- `web_server.py`
- `web_data.py`
- `web/`
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

## 一件事的混合资料智能整理

连续发送同一件事的通知、教程文档、教学视频和截图即可。Hermes 根据上下文
判断归属，调用 `gtd_message_capture` 保存为一组资料；可以说“发完了，整理一下”。
仅时间接近不能证明是同一件事，有歧义时会询问。当前没有基于静默时长的后台归组任务。

新增工具：

| 工具 | 作用 |
|---|---|
| `gtd_materials_context` | 同聊天近期候选，或一组材料原文、附件、分析状态、已有行动和版本 |
| `gtd_materials_analyze` | 保存每个附件实际提取的内容、摘要、检索词、解析方法和覆盖范围 |
| `gtd_materials_organize` | 保存整件事的总结，创建有原文依据的行动/项目，并与原资料关联 |

语义判断由 Hermes 及其实际可用的阅读/视觉/转写工具完成，Python 负责保存、
版本校验、证据引用和原子写入。插件没有内置视频理解模型，也不自动安装 OCR 或
转写服务。不支持的附件会标为失败，部分读取标为 partial；原件始终保留。
“已整理”与“附件全部解析完成”是两个独立状态，返回 `coverage` 说明差异。

例如一组培训资料可以生成“报名”待办，教程和视频仍作为参考资料保存。纯学习
资料不会因为包含操作步骤就全部变成待办。行动记录稳定 key、来源编号与原文
引用，重复整理复用原行动；追加材料后需基于最新版本再分析，避免使用旧结论。
自动关联的任务保留资料编号，资料卡保存反向任务编号和依据。截止日期和通知
是否适用于用户的语义判断仍由 Hermes 完成，程序的原文匹配不能替代事实判断。

文件名无意义时，可按分析摘要、关键词或提取正文搜索。未经解析的视频只能
按已有元数据检索，不能宣称具备内容召回。部署验收需实际模型、文档工具和聊天
渠道；自动测试验证存储与整理契约，不代表已经验证多模态模型判断的准确性。

## 本机浏览器工作台

除对话工具外，可在浏览器里手动管理同一份数据，无需安装前端依赖：

```bash
cd /path/to/gtd-skill
GTD_DIR="/path/to/gtd" python3 web_server.py
```

打开 <http://127.0.0.1:8765>。省略 `GTD_DIR` 时使用 `~/gtd`；请与 Hermes 的
设置保持一致。端口可通过 `--port 8766` 修改，按 Ctrl+C 停止服务。
首次启动会幂等初始化指定目录。浏览器与 Hermes 必须访问同一台机器上的数据。

- 收集箱、下一步行动、等待跟进、项目、将来/也许、资料库分类浏览。收集箱可直接整理到资料库。
- 按当前分类搜索标题、正文、标签与编号；可显示已完成记录。
- 新建任务、备忘和链接资料；编辑任务 Markdown（保留编号）、资料标题、备注与标签。
- 收集箱整理、标记完成、删除记录；查看资料原文、附件路径及整理信息。
- 任务与资料卡片双向显示关联，可点击查看详情。在资料编辑页勾选任务或项目并保存即可新增或解除关联；
  关联保存在资料卡的 `related_items` 中，对话工具也能读取。任务中的 `reference` 来源引用属于历史记录，
  不随取消勾选而删除，也不单独作为当前关联展示。无稳定编号的收集箱和将来/也许条目需先整理为行动、等待跟进或项目后再在界面关联。
- 切回窗口自动刷新，也可手动刷新。编辑保存检查版本，过期内容返回冲突，避免覆盖对话的新修改。
- 删除记录保存在 `GTD_DIR/web-trash/`，资料卡保存在其中的 `reference-cards/`，
  附件保持原位。当前恢复需手工操作，恢复资料卡后调用 `gtd_reference_reindex`。
  删除任务不会删除其他任务或关联资料；相关编号会作为历史引用保留。
- 资料备注编辑不会改写转发原文或解析结果；附件可在资料列表或详情中点击“下载原文件”，支持多附件逐个下载并保留原文件名；文件缺失时显示提示。当前不提供上传或二进制预览。

服务仅监听 `127.0.0.1`，并检查 Host、Origin 和 JSON 请求类型，不开放跨域访问。
这是单用户本机界面，不提供远程登录；不要直接代理到公网。
如复制为独立插件目录使用界面，还需携带 `web_server.py`、`web_data.py` 和 `web/`。

### 安装插件之后如何打开

工作台随本项目一起安装，是 Hermes GTD 插件附带的独立本机网页服务。
启用插件会注册对话工具，**不会自动启动网页服务**。完整复制本项目到用户插件目录后，
在运行 Hermes 的同一台机器上另开一个终端，执行：

```bash
python3 ~/.hermes/plugins/gtd/web_server.py
```

保持终端运行，然后在浏览器打开 <http://127.0.0.1:8765>。如果 Hermes 使用自定义数据目录：

```bash
GTD_DIR="/实际的数据目录" python3 ~/.hermes/plugins/gtd/web_server.py
```

项目本地安装则使用 `/项目路径/.hermes/plugins/gtd/web_server.py`。
已安装旧版插件的用户需要先将更新后的项目文件复制到插件目录。
服务停止或电脑重启后，需要重新运行上述命令。页面也可加入浏览器书签。

### 任务与资料是独立对象

任务/项目和资料不存在父子或归属关系：任一方都能独立创建和保留，双方通过多对多关联连接。
完成、归档或删除任务不会自动处理资料；删除资料不会删除任务；解除关联不删除任何对象或附件。
现有资料卡的 `related_items` 作为关系的单份存储，核心层支持从任一端查询，不依赖网页反向拼接。
`reference_id`、生成行动记录和原文证据记录历史来源，不代表所有权，也不等同于当前关联。

对话工具 `gtd_relations` 支持：

- 查询：`item_id="N001", action="get"`，也可从资料编号查询。
- 关联：`item_id="N001", action="link", other_id="R20260909-001"`，两端可交换。
- 解除：`item_id="R20260909-001", action="unlink", other_id="N001"`。

`gtd_list_actions` 返回 `related_references` 数组。网页调整关联调用相同核心逻辑。
重新整理资料只关联新生成的任务，不自动恢复用户已解除的旧关联。

### 小事实与日常记忆

独立的「记忆」分类保存价格、数量、位置和习惯等小事实，例如“楼下的奶茶价格一般是10元”、
“办公室一般放着10本书”。记忆不是待办，不参与完成、归档或任务提醒，也不要求关联任务或资料。
网页支持新增、搜索、修改、删除，也可将收集箱条目整理为记忆。

对话工具 `gtd_memory` 支持 `add`、`search`、`get`、`update`、`delete`、`restore`。
查询可说“楼下奶茶一般多少钱”；修正可说“更新一下，楼下奶茶一般是12元”。
Agent 先检索已有记录，再使用最新 `revision` 修改；不会只因话题相似就覆盖已有记忆。
记忆原文保留“一般”等限定语及单位，并记录来源、创建/更新时间和历史版本。
关键词检索不代表自动语义理解，记忆内容也不保证现实情况仍未变化。

数据保存在 `GTD_DIR/memories.json`，使用与任务相同的事务锁；删除是软删除，
后续普通检索不再返回，仍可通过对话按编号恢复。网页目前不提供历史版本和恢复入口。

网页下载接口仅通过资料编号和附件序号获取已登记的附件，不接受任意文件路径。
文件以下载方式分块传输；托管附件使用已保存的副本，链接型附件需要原文件仍存在。
