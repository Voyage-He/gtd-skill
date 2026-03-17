"""
GTD 共享工具模块
提供统一的路径解析、日期解析等工具函数
"""

import os
import re
from datetime import datetime


def get_gtd_dir():
    """获取GTD目录路径，支持环境变量覆盖"""
    return os.path.expanduser(os.environ.get("GTD_DIR", "~/gtd"))


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def time_str():
    return datetime.now().strftime("%H:%M")


def parse_date_field(line, field_name):
    """
    从一行文本中提取日期字段。

    支持的字段名: added, deadline, completed, 预计(estimated),
                  询问日期(asked), 询问(asked)
    返回日期字符串(YYYY-MM-DD) 或 None
    """
    # 英文格式: field: YYYY-MM-DD
    pattern = rf'{field_name}:\s*(\d{{4}}-\d{{2}}-\d{{2}})'
    match = re.search(pattern, line)
    if match:
        return match.group(1)

    # 中文格式映射
    cn_fields = {
        'added': ['added', '添加'],
        'deadline': ['deadline', '截止'],
        'estimated': ['预计', 'expected'],
        'asked': ['询问日期', '询问', 'asked'],
        'completed': ['completed', '完成'],
    }

    for cn_name in cn_fields.get(field_name, [field_name]):
        pattern = rf'{cn_name}:\s*(\d{{4}}-\d{{2}}-\d{{2}})'
        match = re.search(pattern, line)
        if match:
            return match.group(1)

    return None


def ensure_gtd_dir():
    """确保GTD目录存在"""
    gtd_dir = get_gtd_dir()
    os.makedirs(gtd_dir, exist_ok=True)
    return gtd_dir


def count_tasks(content):
    """统计文本中的待办和已完成任务数"""
    pending = len(re.findall(r'- \[ \]', content))
    completed = len(re.findall(r'- \[x\]', content))
    return pending, completed


def read_file_if_exists(filepath):
    """读取文件内容，不存在则返回空字符串"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def get_week_range():
    """返回本周一和周日的日期对象"""
    from datetime import timedelta
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday
