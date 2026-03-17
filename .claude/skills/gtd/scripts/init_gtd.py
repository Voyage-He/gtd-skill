#!/usr/bin/env python3
"""
GTD系统初始化脚本
创建GTD目录结构和初始文件
"""

import os
from gtd_utils import get_gtd_dir, today_str, now_str

GTD_DIR = get_gtd_dir()

FILES = {
    "inbox.md": """# 收集箱

> 快速记录任何想法，稍后整理
>
> 提示：大脑是用来产生想法的，不是用来存储想法的。

---

## {today}

- [ ] 欢迎使用GTD系统！尝试在这里记录第一个想法 (added: {now})

""",
    "projects.md": """# 项目清单

项目 = 任何需要多步骤完成的事项

## 活跃项目

（暂无活跃项目）

## 暂停项目

（暂无暂停项目）

---

### 项目模板

```
### PXXX: 项目名称
- **目标**: 项目完成的标准
- **状态**: 活跃/暂停/已完成
- **下一步**: [[next_actions.md#NXXX|行动编号]]
- **笔记**: 相关链接或备注
```
""",
    "next_actions.md": """# 下一步行动

按情境分类，使用动词开头描述具体行动。

## @电脑

（暂无）

## @电话

（暂无）

## @外出

（暂无）

## @家

（暂无）

## @办公室

（暂无）

## @任意

（暂无）

---

### 行动编号模板

```
- [ ] NXXX: 动词 + 具体内容 (context: @情境, deadline: YYYY-MM-DD)
```
""",
    "waiting_for.md": """# 等待清单

记录所有委派给他人、等待反馈的事项。

---

- [ ] W001: （示例）等待同事提供数据 (询问日期: {today}, 预计: {today})

> 格式：`- [ ] WXXX: 事项描述 (询问日期: YYYY-MM-DD, 预计: YYYY-MM-DD, 委派给: 姓名)`

""",
    "someday_maybe.md": """# 将来/也许

暂时不执行但想保留的想法。

## 学习成长

（暂无）

## 生活兴趣

（暂无）

## 职业发展

（暂无）

## 旅行计划

（暂无）

""",
    "calendar.md": """# 日历

## {year}年{month}月

### 本周

-

### 下周

-

### 本月重要日期

-

""",
    "reference.md": """# 参考资料

存储有用的信息、想法、资源链接。

---

## 快速链接

- [GTD 原则](references/gtd_principles.md)

## 笔记

（在此添加参考资料）

""",
}


def init_gtd():
    """初始化GTD系统"""
    print(f"\U0001f5c2\ufe0f  初始化GTD系统...")
    print(f"\U0001f4c1 目录: {GTD_DIR}")

    os.makedirs(GTD_DIR, exist_ok=True)
    os.makedirs(os.path.join(GTD_DIR, "archive"), exist_ok=True)
    os.makedirs(os.path.join(GTD_DIR, "reviews"), exist_ok=True)

    today = today_str()
    now = now_str()
    year = today[:4]
    month = today[5:7]

    created = []
    skipped = []

    for filename, template in FILES.items():
        filepath = os.path.join(GTD_DIR, filename)
        if not os.path.exists(filepath):
            content = template.format(today=today, now=now, year=year, month=month)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            created.append(filename)
        else:
            skipped.append(filename)

    print(f"\n\u2705 已创建文件: {', '.join(created) if created else '无'}")
    print(f"\u23ed\ufe0f  已存在文件: {', '.join(skipped) if skipped else '无'}")

    print(f"\n\U0001f389 GTD系统初始化完成！")
    print(f"   收集箱位置: {GTD_DIR}/inbox.md")
    print(f"   开始使用: 添加你的想法到收集箱")


if __name__ == "__main__":
    init_gtd()
