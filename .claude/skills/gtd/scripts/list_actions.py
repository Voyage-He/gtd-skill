#!/usr/bin/env python3
"""
列出下一步行动
支持按情境过滤
"""

import os
import re
import argparse
from datetime import datetime
from gtd_utils import get_gtd_dir

GTD_DIR = get_gtd_dir()


def parse_action_line(line):
    """
    解析行动行，提取编号、内容、情境、截止日期。

    支持格式:
      - [ ] N001: 内容 (context: @电脑, deadline: 2024-01-20)
      - [ ] N001: 内容 (deadline: 2024-01-20, context: @电脑)
      - [ ] N001: 内容 (context: @电脑)
      - [ ] N001: 内容
    """
    line = line.strip()
    if not line.startswith('- ['):
        return None

    # 提取状态
    status_match = re.match(r'- \[([ x])\]\s*', line)
    if not status_match:
        return None
    done = status_match.group(1) == 'x'

    # 提取编号
    number_match = re.search(r'(?:^|\s)([NWP]\d{3}):', line)
    if not number_match:
        return None
    number = number_match.group(1)

    # 提取编号后的内容（到括号元数据之前）
    rest = line[status_match.end():]
    # 去掉编号部分
    rest = re.sub(rf'{re.escape(number)}:\s*', '', rest, count=1)

    # 提取括号内的元数据
    meta_match = re.search(r'\((.+)\)\s*$', rest)
    meta = {}
    if meta_match:
        meta_str = meta_match.group(1)
        rest = rest[:meta_match.start()].strip()
        # 解析 key: value 对
        for m in re.finditer(r'(context|deadline|completed|预计|询问日期|委派给|added)\s*:\s*([^,)]+)', meta_str):
            meta[m.group(1)] = m.group(2).strip()

    return {
        'done': done,
        'number': number,
        'content': rest.strip(),
        'context': meta.get('context', ''),
        'deadline': meta.get('deadline', ''),
    }


def list_actions(context_filter=None, show_done=False):
    """列出所有下一步行动"""
    filepath = os.path.join(GTD_DIR, "next_actions.md")

    if not os.path.exists(filepath):
        print(f"\u274c 文件不存在: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    actions = []
    current_context = ""

    for line in content.split('\n'):
        # 检测情境标题
        if line.startswith('## @'):
            current_context = line.replace('## ', '').strip()
            # 去掉 emoji
            current_context = re.sub(r'\s+\S$', '', current_context).strip()

        action = parse_action_line(line)
        if action:
            if not action['context'] and current_context:
                action['context'] = current_context
            action['section'] = current_context
            if not action['done'] or show_done:
                actions.append(action)

    # 过滤
    if context_filter:
        actions = [a for a in actions
                   if context_filter.lower() in a['context'].lower()
                   or context_filter.lower() in a.get('section', '').lower()]

    # 排序：有截止日期的优先，然后按日期
    def sort_key(a):
        if a['deadline']:
            try:
                return (0, datetime.strptime(a['deadline'], '%Y-%m-%d'))
            except ValueError:
                return (1, a['deadline'])
        return (2, '')

    actions.sort(key=sort_key)

    if not actions:
        print("\U0001f4ed 暂无待办事项")
        return

    print(f"\n\U0001f4cb 找到 {len(actions)} 项任务\n")

    current_section = ""
    for action in actions:
        if action['section'] != current_section:
            current_section = action['section']
            print(f"\n{current_section}")
            print("-" * 40)

        status = "\u2705" if action['done'] else "\u2b1c"
        deadline = f" \U0001f4c5{action['deadline']}" if action['deadline'] else ""
        print(f"{status} {action['number']}: {action['content']}{deadline}")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='列出GTD下一步行动')
    parser.add_argument('--context', '-c', help='按情境过滤 (如: 电脑, 电话)')
    parser.add_argument('--all', '-a', action='store_true', help='显示已完成任务')

    args = parser.parse_args()
    list_actions(context_filter=args.context, show_done=args.all)
