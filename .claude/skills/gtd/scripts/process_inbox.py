#!/usr/bin/env python3
"""
整理收集箱 — 非交互式命令行工具，供 Claude Agent 调用。

Claude 负责对话和决策，本脚本负责确定的文件操作：
  列出条目、移动条目到目标文件、分配编号、删除条目。

用法:
  python process_inbox.py list                           # 列出收集箱所有条目
  python process_inbox.py next N                         # 获取下一个 N 编号
  python process_inbox.py move 3 --target trash          # 删除第3条
  python process_inbox.py move 3 --target reference      # 移到参考资料
  python process_inbox.py move 3 --target someday_maybe  # 移到将来/也许
  python process_inbox.py move 3 --target done           # 快速完成(2分钟)
  python process_inbox.py move 3 --target next_actions --context @电脑
  python process_inbox.py move 3 --target next_actions --context @电脑 --deadline 2024-02-01
  python process_inbox.py move 3 --target waiting_for --delegate 张三 --estimated 2024-02-01
  python process_inbox.py move 3 --target projects --name "网站改版" --action "设计首页"
"""

import os
import re
import sys
import argparse
from gtd_utils import get_gtd_dir, today_str, now_str

GTD_DIR = get_gtd_dir()
INBOX_FILE = os.path.join(GTD_DIR, "inbox.md")


# ── 读取 ──────────────────────────────────────────────

def read_inbox_items():
    """读取收集箱中所有未处理条目，返回 list[dict]"""
    if not os.path.exists(INBOX_FILE):
        return []

    with open(INBOX_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    items = []
    current_date = ""
    for idx, line in enumerate(lines):
        raw = line.rstrip('\n')
        if raw.startswith('## '):
            current_date = raw.replace('## ', '').strip()
        elif raw.startswith('- [ ]'):
            content = raw.replace('- [ ]', '').strip()
            if content and 'added:' in content:
                items.append({
                    'index': len(items) + 1,
                    'date': current_date,
                    'raw': raw,
                    'content': content,
                })
    return items


# ── 编号 ──────────────────────────────────────────────

def get_next_number(prefix):
    """获取下一个可用编号"""
    filepath = os.path.join(GTD_DIR, f"{_prefix_filename(prefix)}")
    if not os.path.exists(filepath):
        return f"{prefix}001"

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    existing = re.findall(rf'{prefix}(\d{{3}})', content)
    if not existing:
        return f"{prefix}001"
    return f"{prefix}{max(int(n) for n in existing) + 1:03d}"


def _prefix_filename(prefix):
    return {'N': 'next_actions.md', 'W': 'waiting_for.md', 'P': 'projects.md'}[prefix]


# ── 写入目标文件 ──────────────────────────────────────

def append_to_file(filepath, text):
    """追加文本到文件，自动创建目录和文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if not os.path.exists(filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# \u2026\n\n")
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(text + '\n')


# ── 从收集箱移除 ──────────────────────────────────────

def remove_from_inbox(raw_line):
    """从收集箱中移除指定行，并清理空日期标题"""
    with open(INBOX_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = [l for l in lines if l.rstrip('\n') != raw_line]
    content = ''.join(new_lines)
    content = re.sub(r'\n## \d{4}-\d{2}-\d{2}\n\n+', '\n', content)
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open(INBOX_FILE, 'w', encoding='utf-8') as f:
        f.write(content)


def _clean_content(item):
    """去除条目内容中的原始元数据括号 (added: ...) 等"""
    content = item['content']
    content = re.sub(r'\s*\(added:\s*[^)]+\)\s*$', '', content)
    return content.strip()


# ── 移动操作 ──────────────────────────────────────────

def move_to_trash(item):
    remove_from_inbox(item['raw'])
    return {"status": "ok", "action": "trash", "content": _clean_content(item)}


def move_to_reference(item):
    remove_from_inbox(item['raw'])
    append_to_file(
        os.path.join(GTD_DIR, "reference.md"),
        f"- {_clean_content(item)} (archived: {today_str()})"
    )
    return {"status": "ok", "action": "reference", "content": _clean_content(item)}


def move_to_someday(item):
    remove_from_inbox(item['raw'])
    append_to_file(
        os.path.join(GTD_DIR, "someday_maybe.md"),
        f"- [ ] {_clean_content(item)} (added: {item['date']})"
    )
    return {"status": "ok", "action": "someday_maybe", "content": _clean_content(item)}


def move_to_done(item):
    remove_from_inbox(item['raw'])
    today = today_str()
    archive_dir = os.path.join(GTD_DIR, "archive", today[:4])
    append_to_file(
        os.path.join(archive_dir, f"{today[5:7]}_quick.md"),
        f"- [x] {_clean_content(item)} (quick, completed: {today})"
    )
    return {"status": "ok", "action": "done", "content": _clean_content(item)}


def move_to_next_actions(item, context="", deadline=""):
    number = get_next_number('N')
    meta = [f"context: {context or '@任意'}"]
    if deadline:
        meta.append(f"deadline: {deadline}")

    remove_from_inbox(item['raw'])
    append_to_file(
        os.path.join(GTD_DIR, "next_actions.md"),
        f"- [ ] {number}: {_clean_content(item)} ({', '.join(meta)})"
    )
    return {"status": "ok", "action": "next_actions", "number": number,
            "content": _clean_content(item), "context": context or '@任意'}


def move_to_waiting(item, delegate="", estimated=""):
    number = get_next_number('W')
    meta = [f"询问日期: {today_str()}"]
    if delegate:
        meta.append(f"委派给: {delegate}")
    if estimated:
        meta.append(f"预计: {estimated}")

    remove_from_inbox(item['raw'])
    append_to_file(
        os.path.join(GTD_DIR, "waiting_for.md"),
        f"- [ ] {number}: {_clean_content(item)} ({', '.join(meta)})"
    )
    return {"status": "ok", "action": "waiting_for", "number": number,
            "content": _clean_content(item), "delegate": delegate}


def move_to_projects(item, name="", action=""):
    project_num = get_next_number('P')
    action_num = get_next_number('N')
    project_name = name or _clean_content(item)
    first_action = action or f"开始: {project_name}"

    remove_from_inbox(item['raw'])

    # 创建项目条目
    append_to_file(
        os.path.join(GTD_DIR, "projects.md"),
        f"\n### {project_num}: {project_name}\n"
        f"- **目标**: {_clean_content(item)}\n"
        f"- **状态**: 活跃\n"
        f"- **下一步**: [[next_actions.md#{action_num}|{action_num}: {first_action}]]\n"
    )

    # 添加第一步行动
    append_to_file(
        os.path.join(GTD_DIR, "next_actions.md"),
        f"- [ ] {action_num}: {first_action} (context: @电脑)"
    )
    return {"status": "ok", "action": "projects", "project_number": project_num,
            "action_number": action_num, "content": _clean_content(item)}


# ── CLI ───────────────────────────────────────────────

def cmd_list():
    """列出收集箱条目"""
    items = read_inbox_items()
    if not items:
        print("✨ 收集箱是空的")
        return

    for item in items:
        print(f"[{item['index']}] {_clean_content(item)}")
        print(f"    日期: {item['date']}")


def cmd_move(args):
    """移动条目到目标位置"""
    items = read_inbox_items()
    if not items:
        print("✨ 收集箱是空的")
        return

    # 按索引查找
    idx = args.index
    if idx < 1 or idx > len(items):
        print(f"❌ 无效索引: {idx}（共 {len(items)} 条）")
        sys.exit(1)

    item = items[idx - 1]
    target = args.target

    dispatch = {
        'trash': lambda: move_to_trash(item),
        'reference': lambda: move_to_reference(item),
        'someday_maybe': lambda: move_to_someday(item),
        'done': lambda: move_to_done(item),
        'next_actions': lambda: move_to_next_actions(
            item, context=args.context or '', deadline=args.deadline or ''
        ),
        'waiting_for': lambda: move_to_waiting(
            item, delegate=args.delegate or '', estimated=args.estimated or ''
        ),
        'projects': lambda: move_to_projects(
            item, name=args.name or '', action=args.action or ''
        ),
    }

    if target not in dispatch:
        print(f"❌ 未知目标: {target}")
        print(f"   可用: {', '.join(dispatch.keys())}")
        sys.exit(1)

    result = dispatch[target]()
    print(f"✅ [{result['action']}] {result.get('number', '')} {result['content']}")
    if 'project_number' in result:
        print(f"   项目: {result['project_number']}  下一步行动: {result['action_number']}")


def cmd_next(args):
    """获取下一个可用编号"""
    prefix = args.prefix.upper()
    if prefix not in ('N', 'W', 'P'):
        print(f"❌ 无效前缀: {prefix}（支持 N/W/P）")
        sys.exit(1)
    print(get_next_number(prefix))


def main():
    parser = argparse.ArgumentParser(description='GTD 收集箱整理工具')
    sub = parser.add_subparsers(dest='command')

    # list
    sub.add_parser('list', help='列出收集箱条目')

    # next
    p_next = sub.add_parser('next', help='获取下一个可用编号')
    p_next.add_argument('prefix', help='编号前缀 (N/W/P)')

    # move
    p_move = sub.add_parser('move', help='移动条目到目标位置')
    p_move.add_argument('index', type=int, help='条目索引（从 list 获取）')
    p_move.add_argument('--target', '-t', required=True,
                        choices=['trash', 'reference', 'someday_maybe', 'done',
                                 'next_actions', 'waiting_for', 'projects'],
                        help='目标位置')
    p_move.add_argument('--context', '-c', help='情境标签（target=next_actions）')
    p_move.add_argument('--deadline', '-d', help='截止日期 YYYY-MM-DD（target=next_actions）')
    p_move.add_argument('--delegate', help='委派对象（target=waiting_for）')
    p_move.add_argument('--estimated', '-e', help='预计完成 YYYY-MM-DD（target=waiting_for）')
    p_move.add_argument('--name', '-n', help='项目名称（target=projects）')
    p_move.add_argument('--action', '-a', help='第一步行动描述（target=projects）')

    args = parser.parse_args()

    if args.command == 'list':
        cmd_list()
    elif args.command == 'move':
        cmd_move(args)
    elif args.command == 'next':
        cmd_next(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
