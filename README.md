# GTD Skill

基于 David Allen 的 [Getting Things Done](https://gettingthingsdone.com/) 方法论，为 Claude Code 打造的 GTD 时间管理插件。

## 安装

### 通过 Marketplace 安装（推荐）

```bash
# 添加 marketplace
claude plugin marketplace add https://github.com/voyage/gtd-skill

# 安装插件
claude plugin install gtd
```

### 手动安装

```bash
# 克隆到 Claude Code skills 目录
git clone https://github.com/voyage/gtd-skill.git ~/.claude/skills/gtd
```

### 初始化 GTD 系统

安装后，在 Claude Code 中直接说：

> "初始化 GTD"

Claude 会自动运行初始化脚本，在 `~/gtd/` 创建完整的任务管理系统。

或者手动运行：

```bash
python ~/.claude/skills/gtd/scripts/init_gtd.py
```

## 使用

安装后在 Claude Code 中直接用自然语言操作：

| 你说 | Claude 做什么 |
|------|-------------|
| "记录买牛奶" | 写入收集箱 |
| "整理收集箱" | 逐条引导你走决策树 |
| "今天做什么" | 列出今日待办和紧急任务 |
| "完成 N001" | 标记任务完成 |
| "周回顾" | 创建回顾模板 + 自动统计数据 |
| "查看统计" | 显示本周完成率和任务分布 |

## GTD 文件结构

```
~/gtd/
├── inbox.md          # 收集箱 - 快速记录想法
├── projects.md       # 项目清单 - 多步骤任务
├── next_actions.md   # 下一步行动 - 可立即执行
├── waiting_for.md    # 等待清单 - 等待他人/外部
├── someday_maybe.md  # 将来/也许 - 暂不需要的想法
├── calendar.md       # 日历 - 有截止时间的事项
├── reference.md      # 参考资料
├── config.yaml       # 用户配置
├── archive/          # 归档目录
└── reviews/          # 回顾记录
```

### 自定义目录

```bash
export GTD_DIR="/path/to/your/gtd"
```

## 依赖

- Python 3.7+
- PyYAML >= 5.1（可选；未安装时配置系统回退到 JSON）

```bash
pip install -r requirements.txt
```

## 项目结构

```
gtd-skill/
├── .claude-plugin/
│   ├── plugin.json          # 插件元数据
│   └── marketplace.json     # Marketplace 注册
├── .claude/
│   └── skills/
│       └── gtd/
│           ├── SKILL.md     # 技能定义
│           ├── references/  # 参考文档
│           ├── assets/      # 模板文件
│           └── scripts/     # Python 工具脚本
├── README.md
├── requirements.txt
└── LICENSE
```

## 许可

MIT
