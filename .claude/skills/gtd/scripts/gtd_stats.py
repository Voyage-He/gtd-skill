#!/usr/bin/env python3
"""
GTD统计脚本
生成任务完成情况统计
"""

import os
import re
from datetime import datetime, timedelta
from gtd_utils import get_gtd_dir, read_file_if_exists, count_tasks, get_week_range

GTD_DIR = get_gtd_dir()


def get_archive_stats():
    """获取归档统计"""
    archive_dir = os.path.join(GTD_DIR, "archive")
    if not os.path.exists(archive_dir):
        return 0

    total = 0
    for year_dir in os.listdir(archive_dir):
        year_path = os.path.join(archive_dir, year_dir)
        if os.path.isdir(year_path):
            for filename in os.listdir(year_path):
                filepath = os.path.join(year_path, filename)
                if filepath.endswith('.md'):
                    content = read_file_if_exists(filepath)
                    total += len(re.findall(r'- \[x\]', content))

    return total


def count_projects(content):
    """统计项目数量，支持多种标题格式"""
    # 匹配: ### P001: xxx, ### P001 xxx, ### P001
    return len(re.findall(r'###\s+P\d+', content))


def get_weekly_stats():
    """获取本周统计"""
    monday, _ = get_week_range()

    inbox_content = read_file_if_exists(os.path.join(GTD_DIR, "inbox.md"))
    next_content = read_file_if_exists(os.path.join(GTD_DIR, "next_actions.md"))
    waiting_content = read_file_if_exists(os.path.join(GTD_DIR, "waiting_for.md"))
    projects_content = read_file_if_exists(os.path.join(GTD_DIR, "projects.md"))

    # 统计本周新增
    new_items = 0
    for line in inbox_content.split('\n'):
        if 'added:' in line:
            try:
                date_match = re.search(r'added:\s*(\d{4}-\d{2}-\d{2})', line)
                if date_match:
                    item_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                    if item_date >= monday:
                        new_items += 1
            except ValueError:
                pass

    pending_n, completed_n = count_tasks(next_content)
    pending_w, completed_w = count_tasks(waiting_content)
    project_count = count_projects(projects_content)

    return {
        'new_items': new_items,
        'pending_actions': pending_n,
        'completed_actions': completed_n,
        'waiting': pending_w,
        'projects': project_count
    }


def print_stats():
    """打印统计报告"""
    stats = get_weekly_stats()
    archive_total = get_archive_stats()

    print("\n" + "=" * 40)
    print("\U0001f4ca GTD 统计报告")
    print("=" * 40)
    print(f"\n\U0001f4c5 统计时间: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"\n\u2705 累计完成: {archive_total + stats['completed_actions']} 个任务")
    print(f"\U0001f4e5 本周新增: {stats['new_items']} 个想法")
    print(f"\u23f3 待办任务: {stats['pending_actions']} 个")
    print(f"\u23f8\ufe0f  等待中: {stats['waiting']} 个")
    print(f"\U0001f4c1 活跃项目: {stats['projects']} 个")

    total = stats['pending_actions'] + stats['completed_actions']
    if total > 0:
        rate = (stats['completed_actions'] / total) * 100
        print(f"\U0001f4c8 本周完成率: {rate:.1f}%")

    print("\n" + "=" * 40)

    if stats['pending_actions'] > 10:
        print("\U0001f4a1 建议：待办任务较多，建议整理优先处理重要事项")
    if stats['waiting'] > 5:
        print("\U0001f4a1 建议：有多个等待事项，可能需要跟进")
    if stats['new_items'] > 20:
        print("\U0001f4a1 建议：收集了很多想法，记得及时整理")


if __name__ == "__main__":
    print_stats()
