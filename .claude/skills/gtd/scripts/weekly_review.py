#!/usr/bin/env python3
"""
GTD周回顾脚本
创建周回顾记录文件，并自动收集本周数据
"""

import os
import re
from datetime import datetime, timedelta
from gtd_utils import (
    get_gtd_dir, today_str, now_str, get_week_range,
    read_file_if_exists, count_tasks
)

GTD_DIR = get_gtd_dir()
REVIEWS_DIR = os.path.join(GTD_DIR, "reviews")


def collect_weekly_data():
    """自动收集本周统计数据"""
    monday, sunday = get_week_range()

    inbox_content = read_file_if_exists(os.path.join(GTD_DIR, "inbox.md"))
    next_content = read_file_if_exists(os.path.join(GTD_DIR, "next_actions.md"))
    waiting_content = read_file_if_exists(os.path.join(GTD_DIR, "waiting_for.md"))
    projects_content = read_file_if_exists(os.path.join(GTD_DIR, "projects.md"))

    # 本周新增想法
    new_items = 0
    for line in inbox_content.split('\n'):
        date_match = re.search(r'added:\s*(\d{4}-\d{2}-\d{2})', line)
        if date_match:
            try:
                d = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                if monday <= d <= sunday:
                    new_items += 1
            except ValueError:
                pass

    # 本周完成数
    completed_this_week = 0
    for line in next_content.split('\n'):
        date_match = re.search(r'completed:\s*(\d{4}-\d{2}-\d{2})', line)
        if date_match:
            try:
                d = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                if monday <= d <= sunday:
                    completed_this_week += 1
            except ValueError:
                pass

    _, total_completed = count_tasks(next_content)
    pending_n, _ = count_tasks(next_content)
    pending_w, _ = count_tasks(waiting_content)
    project_count = len(re.findall(r'###\s+P\d+', projects_content))

    # 检查过期任务
    today = datetime.now()
    overdue = []
    for line in next_content.split('\n'):
        date_match = re.search(r'deadline:\s*(\d{4}-\d{2}-\d{2})', line)
        if date_match:
            try:
                d = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                if d < today and '- [ ]' in line:
                    overdue.append(line.strip())
            except ValueError:
                pass

    # 需要跟进的等待事项
    stale_waiting = []
    for line in waiting_content.split('\n'):
        if '- [ ]' not in line:
            continue
        asked_match = re.search(r'(?:询问日期|asked):\s*(\d{4}-\d{2}-\d{2})', line)
        if asked_match:
            try:
                asked_date = datetime.strptime(asked_match.group(1), '%Y-%m-%d')
                if (today - asked_date).days >= 3:
                    stale_waiting.append(line.strip())
            except ValueError:
                pass

    return {
        'new_items': new_items,
        'completed_this_week': completed_this_week,
        'total_completed': total_completed,
        'pending_actions': pending_n,
        'waiting_count': pending_w,
        'project_count': project_count,
        'overdue': overdue,
        'stale_waiting': stale_waiting,
    }


def create_weekly_review():
    """创建周回顾模板，含自动收集的数据"""
    monday, sunday = get_week_range()
    week_str = monday.strftime("%Y-%m-%d")

    os.makedirs(REVIEWS_DIR, exist_ok=True)

    filepath = os.path.join(REVIEWS_DIR, f"{week_str}_weekly.md")

    if os.path.exists(filepath):
        print(f"\u26a0\ufe0f  本周回顾已存在: {filepath}")
        return filepath

    data = collect_weekly_data()

    overdue_lines = ""
    if data['overdue']:
        overdue_lines = "\n".join(f"   - {t}" for t in data['overdue'])
    else:
        overdue_lines = "   （无过期任务）"

    stale_lines = ""
    if data['stale_waiting']:
        stale_lines = "\n".join(f"   - {t}" for t in data['stale_waiting'])
    else:
        stale_lines = "   （无需跟进事项）"

    template = f"""# 周回顾 - {monday.strftime("%Y年%m月%d日")} ~ {sunday.strftime("%m月%d日")}

回顾日期: {now_str()}

---

## \u2705 检查清单

### 1. 收集
- [ ] 收集所有散落的笔记、想法
- [ ] 检查邮件、聊天工具
- [ ] 检查物理收集盒

### 2. 清空收集箱
- [ ] 处理 inbox.md 中的所有条目

### 3. 回顾日历
- [ ] 查看过去一周: calendar.md
- [ ] 查看未来两周: 有什么需要准备的？

### 4. 回顾项目清单
- [ ] 每个活跃项目都有下一步行动吗？
- [ ] 有什么项目需要更新状态？

### 5. 回顾下一步行动
- [ ] 清理已完成的任务
- [ ] 更新情境分类
- [ ] 检查即将到期的任务

### 6. 回顾等待清单
- [ ] 需要跟进的事项？
- [ ] 已完成的等待事项？

### 7. 回顾将来/也许
- [ ] 有什么可以启动的吗？
- [ ] 有什么不再感兴趣的吗？

### 8. 创意与灵感
- [ ] 有什么新想法要捕捉？
- [ ] 下周有什么想要专注的？

---

## \U0001f4ca 自动统计

| 指标 | 数值 |
|------|------|
| \U0001f4e5 本周新增想法 | {data['new_items']} |
| \u2705 本周完成任务 | {data['completed_this_week']} |
| \u23f3 待办任务 | {data['pending_actions']} |
| \u23f8\ufe0f  等待中 | {data['waiting_count']} |
| \U0001f4c1 活跃项目 | {data['project_count']} |

### \U0001f534 过期任务

{overdue_lines}

### \U0001f4e8 需跟进的等待事项

{stale_lines}

---

## \U0001f4dd 回顾笔记

### 本周成就

1.
2.
3.

### 遇到的挑战

-

### 下周重点

1.
2.
3.

### 新想法

-

---

## \U0001f4ca 统计数据

- 完成任务数:
- 新建项目数:
- 收集想法数:
"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(template)

    print(f"\u2705 创建周回顾: {filepath}")
    print(f"\U0001f4ca 已自动收集本周数据：")
    print(f"   \U0001f4e5 本周新增: {data['new_items']} 个想法")
    print(f"   \u2705 本周完成: {data['completed_this_week']} 个任务")
    print(f"   \U0001f534 过期任务: {len(data['overdue'])} 个")
    print(f"   \U0001f4e8 需跟进: {len(data['stale_waiting'])} 个")

    return filepath


if __name__ == "__main__":
    create_weekly_review()
