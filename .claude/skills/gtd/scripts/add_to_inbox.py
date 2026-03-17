#!/usr/bin/env python3
"""
添加项目到收集箱
"""

import os
import sys
from gtd_utils import get_gtd_dir, today_str, time_str

GTD_DIR = get_gtd_dir()
INBOX_FILE = os.path.join(GTD_DIR, "inbox.md")


def add_to_inbox(content):
    """添加内容到收集箱"""
    if not content or not content.strip():
        print("\u274c 内容不能为空")
        sys.exit(1)

    content = content.strip()
    os.makedirs(GTD_DIR, exist_ok=True)

    if not os.path.exists(INBOX_FILE):
        with open(INBOX_FILE, 'w', encoding='utf-8') as f:
            f.write("# 收集箱\n\n> 快速记录任何想法，稍后整理\n\n---\n\n")

    with open(INBOX_FILE, 'r', encoding='utf-8') as f:
        existing = f.read()

    today = today_str()
    now = time_str()

    if f"## {today}" not in existing:
        entry = f"\n## {today}\n\n- [ ] {content} (added: {today} {now})\n"
    else:
        entry = f"- [ ] {content} (added: {today} {now})\n"

    with open(INBOX_FILE, 'a', encoding='utf-8') as f:
        f.write(entry)

    print(f"\u2705 已添加到收集箱: {content}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python add_to_inbox.py '要记录的内容'")
        sys.exit(1)

    content = ' '.join(sys.argv[1:])
    add_to_inbox(content)
