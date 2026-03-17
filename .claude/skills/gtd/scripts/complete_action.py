#!/usr/bin/env python3
"""
完成任务并归档
支持 N(下一步行动)、W(等待)、P(项目) 三类任务
"""

import os
import re
import sys
from gtd_utils import get_gtd_dir, today_str

GTD_DIR = get_gtd_dir()

# 编号前缀 → 文件名映射
PREFIX_FILE_MAP = {
    'N': 'next_actions.md',
    'W': 'waiting_for.md',
    'P': 'projects.md',
}


def find_and_complete(action_number):
    """在对应文件中查找并标记任务完成"""
    prefix = action_number[0].upper()
    filename = PREFIX_FILE_MAP.get(prefix)

    if filename is None:
        print(f"\u274c 不支持的编号类型: {action_number}（支持 N/W/P）")
        return False

    filepath = os.path.join(GTD_DIR, filename)

    if not os.path.exists(filepath):
        print(f"\u274c 文件不存在: {filepath}")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找任务：匹配整行 - [ ] <编号>: ...
    line_pattern = rf'^(- \[ \])\s*({re.escape(action_number)}:.*)$'

    if not re.search(line_pattern, content, flags=re.MULTILINE):
        print(f"\u274c 未找到任务: {action_number}（在 {filename} 中）")
        return False

    completed_date = today_str()
    new_content = re.sub(
        line_pattern,
        rf'- [x] \2 (completed: {completed_date})',
        content,
        flags=re.MULTILINE
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"\u2705 已标记完成: {action_number}")
    return True


def archive_completed():
    """归档所有文件中已完成的任务"""
    archived_total = 0

    for prefix, filename in PREFIX_FILE_MAP.items():
        filepath = os.path.join(GTD_DIR, filename)
        if not os.path.exists(filepath):
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        completed_pattern = r'- \[x\].*\(completed: \d{4}-\d{2}-\d{2}\).*'
        completed_tasks = re.findall(completed_pattern, content)

        if not completed_tasks:
            continue

        archive_dir = os.path.join(
            GTD_DIR, "archive", today_str()[:4]
        )
        os.makedirs(archive_dir, exist_ok=True)

        archive_file = os.path.join(
            archive_dir, f"{today_str()[5:7]}_completed.md"
        )

        with open(archive_file, 'a', encoding='utf-8') as f:
            f.write(f"\n## {today_str()}\n")
            for task in completed_tasks:
                f.write(task + '\n')

        # 从原文件删除已完成任务
        new_content = re.sub(completed_pattern + r'\n?', '', content)
        # 清理多余的空行
        new_content = re.sub(r'\n{3,}', '\n\n', new_content)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        archived_total += len(completed_tasks)

    if archived_total == 0:
        print("\U0001f4ed 没有需要归档的已完成任务")
    else:
        print(f"\U0001f4e6 已归档 {archived_total} 个任务")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python complete_action.py N001      # 完成任务N001")
        print("  python complete_action.py W001      # 完成等待W001")
        print("  python complete_action.py P001      # 完成项目P001")
        print("  python complete_action.py --archive # 归档所有已完成任务")
        sys.exit(1)

    if sys.argv[1] == '--archive':
        archive_completed()
    else:
        action_number = sys.argv[1].upper()
        # 自动补全前缀（如果没有字母前缀，默认 N）
        if action_number[0].isdigit():
            action_number = 'N' + action_number
        find_and_complete(action_number)
