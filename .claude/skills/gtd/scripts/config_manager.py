#!/usr/bin/env python3
"""
GTD配置管理
管理用户偏好设置。依赖 PyYAML，如未安装会自动回退到 JSON 格式。
"""

import os
import json
import sys

from gtd_utils import get_gtd_dir

GTD_DIR = get_gtd_dir()
CONFIG_FILE = os.path.join(GTD_DIR, "config.yaml")
CONFIG_FILE_JSON = os.path.join(GTD_DIR, "config.json")

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    CONFIG_FILE = CONFIG_FILE_JSON

DEFAULT_CONFIG = {
    'user_name': '主人',
    'preferred_contexts': ['@电脑', '@电话', '@家'],
    'work_hours': {
        'start': '09:00',
        'end': '18:00'
    },
    'review': {
        'day': '周日',
        'time': '20:00',
        'enabled': True
    },
    'notifications': {
        'daily_digest': True,
        'deadline_reminder': True,
        'waiting_followup': True
    },
    'auto_archive': True,
    'context_emoji': {
        '@电脑': '\U0001f4bb',
        '@电话': '\U0001f4de',
        '@外出': '\U0001f3c3',
        '@家': '\U0001f3e0',
        '@办公室': '\U0001f3e2',
        '@任意': '\U0001f4cd'
    }
}


def load_config():
    """加载配置"""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            if HAS_YAML:
                config = yaml.safe_load(f) or {}
            else:
                config = json.load(f)
    except Exception:
        return dict(DEFAULT_CONFIG)

    # 合并默认值，确保新字段有值
    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value
    return config


def save_config(config):
    """保存配置"""
    os.makedirs(GTD_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        if HAS_YAML:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False)
        else:
            json.dump(config, f, ensure_ascii=False, indent=2)


def get_config(key=None):
    """获取配置项，支持点号分隔的嵌套键"""
    config = load_config()
    if key:
        keys = key.split('.')
        current = config
        for k in keys:
            if isinstance(current, dict):
                current = current.get(k)
            else:
                return None
        return current
    return config


def set_config(key, value):
    """设置配置项，支持点号分隔的嵌套键"""
    config = load_config()
    keys = key.split('.')

    current = config
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    current[keys[-1]] = value
    save_config(config)
    print(f"\u2705 设置已保存: {key} = {value}")


def print_config():
    """打印当前配置"""
    config = load_config()
    print("\n\u2699\ufe0f  当前配置：")
    print("-" * 30)
    if HAS_YAML:
        print(yaml.dump(config, allow_unicode=True, sort_keys=False))
    else:
        print(json.dumps(config, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print_config()
    elif len(sys.argv) == 2:
        key = sys.argv[1]
        value = get_config(key)
        print(f"{key} = {value}")
    elif len(sys.argv) >= 3:
        key = sys.argv[1]
        value = sys.argv[2]
        if value.lower() in ('true', 'yes', 'on'):
            value = True
        elif value.lower() in ('false', 'no', 'off'):
            value = False
        elif value.isdigit():
            value = int(value)
        set_config(key, value)
