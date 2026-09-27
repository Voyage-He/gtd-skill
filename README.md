# Hermes Agent GTD Plugin

Hermes Agent GTD 插件基于 Getting Things Done 方法论，通过 `gtd_*` tools 维护一套 Markdown 任务与资料系统。默认数据目录是 `~/gtd`，也可以用 `GTD_DIR` 指向其他目录。

## 安装

### 用户级插件

```bash
mkdir -p ~/.hermes/plugins/gtd
cp -R /path/to/gtd-skill/. ~/.hermes/plugins/gtd/
hermes plugins enable gtd
```

启动 Hermes 后，确认 `gtd` toolset 中可以看到 `gtd_init`、`gtd_capture` 等工具。

### 项目本地插件

项目本地插件位于当前项目的 `.hermes/plugins/`，只应在信任该项目内容时启用：

```bash
mkdir -p .hermes/plugins/gtd
cp -R /path/to/gtd-skill/. .hermes/plugins/gtd/
export HERMES_ENABLE_PROJECT_PLUGINS=true
hermes plugins enable gtd
```

## 重装与更新

插件代码、GTD 数据和 Hermes cron 是三份独立状态。更新只替换插件代码；保留原来的
`GTD_DIR`（默认 `~/gtd`）及 Hermes 自己的调度存储。把数据放在插件目录之外，避免替换
或卸载代码时一起删掉。迁移数据目录属于单独操作：调度的目录标记和名称与原路径绑定，
不能只改 `GTD_DIR` 后就认为原任务会自动迁移。

更新前停止使用该插件的 Hermes 进程和独立网页服务，备份整个数据目录、Hermes 调度存储
及旧插件目录，再将完整新版发布文件复制到插件目录。上面的 `源目录/.` 写法在目标已存在时
仍复制目录内容，不会多套一层 `gtd-skill/`。不要只更新 `__init__.py` 或几个 Python 文件。
复制完成后重新启动 Hermes 与需要使用的网页服务，以免旧进程继续运行已加载的代码。
回退代码时也应重启；数据格式升级后的回退需使用对应备份，不能保证任意版本向后兼容。

在新会话中调用 `gtd_init` 复核：

- 已配置过的任务按 Hermes 中的真实时间、接收对象、提示词和暂停状态继续使用。
- 用户选择过的调度名称记录在数据目录的 `schedule-setup.json`；“暂不安排”也会记住。
  `setup_schedules=false` 只是本次跳过，不改变这份选择记录。
- 记录中的任务若缺失或重名，会报告待处理，初始化不会自动恢复被删除的任务。
  显式重新提交用户选定的 `routines` 才会补建缺失任务。
- 旧版本没有记录时，会先查询当前目录的真实调度；调度不可用会报告错误，不当作空列表。
- 更新不自动改写已有任务提示词或恢复暂停任务；需要更新指令时通过 `gtd_manage` 操作原任务。

已有 `config.json` 不会因为后来安装 PyYAML 而被默认 YAML 配置取代。已有 `config.yaml`
在缺少 PyYAML 时保留原文件，配置读写明确报错，不另建默认 JSON。两份配置同时存在时
需要先备份并核对保留哪份；损坏或非对象配置不会静默回退默认值。新版或损坏的调度初始化
记录也会报错保留，避免旧代码覆盖未知格式。

自动测试覆盖新目录加载、数据字节保留、依赖变化、调度复用与缺失检查；真实 Hermes
插件重载、模型执行和渠道送达仍需在实际部署中验收。

## 数据目录

默认使用 `~/gtd`。临时测试或多套系统可以这样指定目录：

```bash
export GTD_DIR="/path/to/gtd"
```

首次使用时让 Agent 执行“初始化 GTD”，插件会调用 `gtd_init` 幂等创建缺失文件，不会覆盖已有 Markdown 数据。

初始化通过对话确定常规安排。首次直接调用 `gtd_init` 会创建数据并检查已有调度；没有既有选择时返回
`schedules.status="needs_preferences"`，不会自动启用早晚任务或替用户选择时间。
Agent 会结合用户已经说过的偏好，询问还缺少的安排：

- 想要提醒、总结、回顾还是计划？只要早上、只要晚上、两者都要或暂不安排均可。
- 每天还是每周？每周在哪一天？“一周第一天/最后一天”按用户的一周定义换算，含糊时询问。
- 每项具体几点几分？“早上”“晚上”不足以确定时间，不默认九点或其他时间。

用户可以直接说：“每天早上七点提醒，周日晚上八点半回顾，周一早上八点安排本周。”
信息齐全就执行，不需要再走一轮确认。只询问缺失信息，用户不用填写 cron 表达式。
例如用户选择周日晚回顾和周一早计划后，Agent 可调用：

```json
{
  "routines": [
    {"key": "weekly_review", "frequency": "weekly", "weekday": 0, "time": "20:30", "prompt": "每周回顾已记录进展、未完成事项和待整理内容；每次发送简短总结"},
    {"key": "weekly_plan", "frequency": "weekly", "weekday": 1, "time": "08:00", "prompt": "结合下一步行动、截止事项和项目状态安排本周重点；每次发送"}
  ]
}
```

`routines` 只包含用户选定的安排；每天用 `frequency="daily"`，每周用 `weekly`
并指定 `weekday`（0 周日、1 周一至 6 周六）。每项必须明确 `time`，没有默认频率或时间。
时间使用 Hermes 当前时区，向用户说明；若显式提供 `timezone` 则必须与 Hermes 一致。
新任务默认投递到当前会话 `origin`，可用 `deliver` 指定单个 `platform:chat_id`。

重复提交相同 `key` 只补建缺失任务，保留已有任务的时间、内容、接收对象和暂停状态；
`daily_reminder`、`daily_summary` 兼容之前的任务名。已有安排通过 `gtd_manage` 查询和修改，
不为改时间换一个 key 创建副本。`routines=[]` 或 `setup_schedules=false` 表示此次不创建安排，
不会暂停或删除已有任务。

`initialized: true` 表示数据已就绪，调度状态另看 `schedules.status`：
`needs_preferences` 待对话选择，`ready` 已核实所选任务，`skipped` 跳过，`incomplete` 部分失败。
失败时保留数据及成功任务，返回具体错误；修复后用同一组 key 重试补齐。
任务已登记不代表已送达；实际运行需要 Hermes Gateway、模型和渠道可用。
插件加载和网页启动不会创建 cron。

## Tools

| Tool | 典型说法 | 关键参数 |
|------|----------|----------|
| `gtd_init` | 初始化 GTD | 可选 `routines`, `setup_schedules`, `timezone`, `deliver` |
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
- `gtd_response.py`
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
| `gtd_manage` | 统一召回相关内容与定时任务，执行增删改查并复核 |
| `gtd_reminder` | 每日 GTD 响应的兼容入口：启用、查询、暂停、试运行 |

例：“找上次张三发的报名通知，把报名表发回来。”Agent 搜索资料，选中后
通过 `gtd_reference_files` 获取原件，使用 Hermes 的 MEDIA 标签回复。
`prepared` 仅表示文件已准备，真实送达由渠道处理。

图片文字提取由 Hermes 可用的视觉工具完成，存入 `extracted_text`，原图保留。
插件本身不内置 OCR/PDF 解析器，不会假装能直接读二进制附件。没有提取文字的
图片仍可按标题、标签、来源检索。通知中的明确日期可存入 `notices`；含糊的
“下周五”等表述要有可靠原始日期才能转换。

## 统一 GTD 响应：对话与定时触发

每次 GTD 对话或定时运行，都执行同一套流程：**召回并审视 → 执行 → 复核 → 反馈**。
用户不需要选择“整理”或“通知”模式。审视范围是本次召回的相关任务、项目、资料、
记忆及其定时任务；按关联继续召回必要上下文，不要求每次重读全部文件。

例如“报名延期到下周五”，AI 会检查原资料、已有行动和对应跟进安排，修改任务日期并
调整原定时任务；“已经报名了”则完成行动并关闭已无用途的跟进，原资料继续保留。
定时运行也可以执行这些操作，包括理解新增资料、整理行动、创建后续定时任务、
调整时间/频率、暂停或删除失效安排。是否需要这些操作由 Hermes 根据用户意图判断。

`gtd_manage` 是统一入口，底层复用现有内容工具与 Hermes 调度接口：

| 操作 | 用途 |
|---|---|
| `action="review"` | 同时召回内容与当前目录的真实定时任务，支持关键词、编号、关联扩展和分页 |
| `action="get"` | 读取内容详情及最新 `revision`；`target="schedule"` 读取定时任务详情 |
| `create/update/delete/complete` | 默认管理内容；编辑前使用最新 `revision` |
| `target="schedule"` | 管理定时任务，支持 `create/update/delete/pause/resume/run` |

任务、资料与记忆的具体分析仍可调用 `gtd_materials_*`、`gtd_memory` 等已有工具。
这些是同一响应中的执行能力，不是互相独立的自动化模式。内容编辑与调度调整分别
执行：如果内容已保存但调度失败，必须反馈部分成功，不能声称已经全部同步。

新定时任务使用稳定 `key` 防止同一次创建被重复提交，提示词自动带上 GTD 数据目录、
相关内容编号及统一响应流程。已有任务修改时保留未提供的字段和接收对象。
运行中修改内容后，在同一响应内复核相关安排，不因自己的每次工具调用递归创建新唤醒。

### 安装后的统一配置

插件启用并重新加载 Hermes 后，通过 `register_system_prompt_section` 注册常驻
GTD 规则；旧版接口使用 `pre_llm_call` 注入。两种接口都没有时明确报兼容错误，
避免只注册工具却误以为规则已全局生效。
所有个人任务、提醒、跟进、项目、回顾和 GTD 资料响应都按此规则进入统一流程，
包括未标注 GTD 的旧 cron；无关聊天和技术执行任务不纳入。

每次 `gtd_manage(action="review")` 返回当前 `config`，模型据此应用通知、回顾、
工作时间、场景和归档偏好，不沿用旧对话或 cron 里保存的配置。修改配置后同轮重新读取。
通知开关控制对应类别的主动通知，不屏蔽用户直接提问、失败或必要确认。
当前用户明确指令优先，历史 cron 文本不能覆盖后来更新的偏好。

新增可通过 `gtd_config_set` 修改的配置：

| 配置 | 默认 | 作用 |
|---|---|---|
| `response.verbosity` | `concise` | 只报有效结果；`detailed` 允许必要说明 |
| `response.silent_when_unchanged` | `true` | 定时运行无需要关注事项时必须静默 |

禁止过程播报、工具日志、内部编号、检查回执、重复背景和泛泛建议；用户明确索要的
细节除外。内部整理成功不自动构成通知理由。启用类别中的到期提醒仍应发送，不能
因数据未改变漏掉提醒。旧配置读取时合并默认值，不覆盖原文件。

这是 Hermes 模型执行的响应策略，不是投递后的文本过滤器；真实渠道与模型行为仍需
部署验收。运行机制参考 [Hermes 插件 hooks](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks/)。

### 反馈规则

- 有用户需要关注的内容或定时任务变化：合并反馈做了什么、还缺什么。
- 有执行错误、未核实的结果或新问题：明确反馈，不能静默掩盖。
- 普通对话中的查询仍正常回答。
- 常规定时触发无需要关注事项时，默认必须静默。例如已知的“今天要洗衣服了”
  无需再发一条回执；若用户明确要求每次都提醒，则保留该要求。
- 定时静默使用 Hermes 的 `[SILENT]`，执行输出仍由 Hermes 留存；有实质反馈时不能
  混入该标记，否则整条投递会被抑制。不能只因提醒触发就把现实事项标记完成。

### 运行条件与现有任务

Hermes Gateway、模型和渠道需要可用。定时运行中管理定时任务还需要部署环境设置：

```yaml
cron:
  allow_agent_scheduling: true
```

插件检查并遵守该设置，不自行修改 Hermes 全局配置，不绕过限制直接写调度文件。
调用已注册的 `cronjob_manage` 执行操作；新版 Hermes 的列表只返回提示词预览时，
通过运行环境的只读 `cron.jobs.get_job` 接口获取完整任务。接口不可用会标记审视不完整。

未带目录标记的历史 GTD 任务作为 `unscoped_jobs` 返回；其他定时任务提供简短概览，
方便识别名称没有 GTD 但实际相关的安排。确认归属后，可通过 `update`
提供 `data.gtd_dir` 和完整 `data.prompt` 纳入统一流程，同时保留暂停状态和原接收对象。
属于其他明确数据目录的任务不会被修改。已有任务的提示词不会因更新插件而自动变化，
其任务文本保留；全局规则要求运行时读取最新配置。需要更新任务目的或目录标记时仍须明确更新。

插件注册的 skill 完整名称是 `gtd:gtd`（插件名:skill 名）。新定时任务使用该名称；
通过 `gtd_manage` 更新已有任务时，会将旧的 `gtd` 引用替换为 `gtd:gtd`，保留其他
skills、时间、提示词、接收对象和暂停状态。修复已有当前目录任务时，先用
`target="schedule", action="get"` 获取真实 ID 与最新 `revision`，再用相同 ID 和
revision 调用 `action="update", data={}`。只修复 skill 引用时不要调用
`gtd_reminder(action="enable")`，因为 enable 会恢复调度。插件加载仍保持
`ctx.register_skill("gtd", ...)`，命名空间由 Hermes 自动添加。

`gtd_reminder` 保留为每日响应的兼容入口：`enable/status/disable/run`。默认每天
Asia/Shanghai 09:00，必须与 Hermes 时区一致；省略接收目标时沿用原目标。
新建或更新的每日任务使用统一流程，无变化时可静默。`gtd_config_set` 中的通知和回顾
偏好本身不会创建定时任务。

这套流程由对话或实际 Hermes 定时运行触发，不自带文件监听器；在外部直接改 Markdown
或调度表，不会凭空启动一次 AI 响应，需要后续对话或定时触发再审视。网页服务不承担调度。
自动测试覆盖工具操作、状态校验与模拟调度；真实模型判断及 QQ/微信投递仍需部署验收。

接口参考：[Hermes 定时任务](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron/)、
[调度工具源码](https://github.com/NousResearch/hermes-agent/blob/main/tools/cronjob_tools.py)。

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
仅时间接近不能证明是同一件事，有歧义时会询问。当前没有基于静默时长的后台归组任务；对话或已配置的 GTD 定时触发可按统一流程整理相关材料。

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
