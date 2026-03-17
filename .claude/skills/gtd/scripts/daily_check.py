#!/usr/bin/env python3
"""
每日检查脚本
生成今日待办和提醒
"""

import os
import re
from datetime import datetime, timedelta
from gtd_utils import get_gtd_dir, parse_date_field, today_str, read_file_if_exists

GTD_DIR = get_gtd_dir()


def get_calendar_items():
    """获取今日日历事项"""
    content = read_file_if_exists(os.path.join(GTD_DIR, "calendar.md"))
    if not content:
        return []

    today = today_str()
    items = []
    lines = content.split('\n')
    in_today = False

    for line in lines:
        if today in line or '今天' in line:
            in_today = True
            continue
        if in_today:
            if line.startswith('###') or (line.startswith('#') and '月' in line):
                break
            if line.strip().startswith('-'):
                items.append(line.strip())

    return items


def get_urgent_actions():
    """获取紧急任务（今天或明天截止）"""
    content = read_file_if_exists(os.path.join(GTD_DIR, "next_actions.md"))
    if not content:
        return [], []

    today = datetime.now()
    tomorrow = today + timedelta(days=1)

    today_tasks = []
    tomorrow_tasks = []

    for line in content.split('\n'):
        if not line.startswith('- [ ]'):
            continue

        deadline_str = parse_date_field(line, 'deadline')
        if not deadline_str:
            continue

        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
            if deadline.date() == today.date():
                today_tasks.append(line.strip())
            elif deadline.date() == tomorrow.date():
                tomorrow_tasks.append(line.strip())
        except ValueError:
            pass

    return today_tasks, tomorrow_tasks


def get_waiting_followups():
    """获取需要跟进的等待事项"""
    content = read_file_if_exists(os.path.join(GTD_DIR, "waiting_for.md"))
    if not content:
        return []

    today = datetime.now()
    followups = []

    for line in content.split('\n'):
        if not line.startswith('- [ ]'):
            continue

        need_followup = False

        # 检查预计日期是否已到
        estimated = parse_date_field(line, 'estimated')
        if estimated:
            try:
                expected = datetime.strptime(estimated, '%Y-%m-%d')
                if expected <= today:
                    need_followup = True
            except ValueError:
                pass

        # 检查询问日期是否超过3天
        asked = parse_date_field(line, 'asked')
        if asked and not need_followup:
            try:
                asked_date = datetime.strptime(asked, '%Y-%m-%d')
                if (today - asked_date).days >= 3:
                    need_followup = True
            except ValueError:
                pass

        if need_followup:
            followups.append(line.strip())

    return followups


def print_daily_digest():
    """打印每日摘要"""
    today = today_str()
    weekday = datetime.now().strftime("%A")
    weekday_cn = {
        'Monday': '\u4e00', 'Tuesday': '\u4e8c', 'Wednesday': '\u4e09',
        'Thursday': '\u56db', 'Friday': '\u4e94', 'Saturday': '\u516d', 'Sunday': '\u65e5'
    }.get(weekday, weekday)

    print("\n" + "=" * 50)
    print(f"\U0001f305 早安，主人！")
    print(f"\U0001f4c5 今天是 {today} 星期{weekday_cn}")
    print("=" * 50)

    # 日历事项
    calendar = get_calendar_items()
    if calendar:
        print("\n\U0001f4c5 今日日程：")
        for item in calendar:
            print(f"   {item}")

    # 紧急任务
    today_tasks, tomorrow_tasks = get_urgent_actions()

    if today_tasks:
        print(f"\n\U0001f534 今日截止 ({len(today_tasks)}个)：")
        for task in today_tasks:
            desc = re.sub(r'\([^)]*deadline[^)]*\)', '', task)
            desc = re.sub(r'- \[ \]', '', desc).strip()
            print(f"   \u26a0\ufe0f  {desc}")

    if tomorrow_tasks:
        print(f"\n\U0001f7e1 明日截止 ({len(tomorrow_tasks)}个)：")
        for task in tomorrow_tasks:
            desc = re.sub(r'\([^)]*deadline[^)]*\)', '', task)
            desc = re.sub(r'- \[ \]', '', desc).strip()
            print(f"   \u23f0 {desc}")

    # 等待跟进
    followups = get_waiting_followups()
    if followups:
        print(f"\n\U0001f4e8 需要跟进 ({len(followups)}个)：")
        for item in followups:
            desc = re.sub(r'\([^)]+\)', '', item)
            desc = re.sub(r'- \[ \]', '', desc).strip()
            print(f"   \U0001f4de {desc}")

    # 总结
    total_urgent = len(today_tasks) + len(tomorrow_tasks)
    if total_urgent == 0:
        print("\n\u2728 今天没有紧急任务，轻松的一天！")
    else:
        print(f"\n\U0001f4a1 今日共有 {total_urgent} 个任务需要关注")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    print_daily_digest()
