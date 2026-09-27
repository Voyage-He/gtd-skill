import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import gtd_core as core
import reminders
import tools
from tests.helpers import decode, temp_gtd_dir
from tests.test_plugin_runtime import FakeHermesContext, load_plugin_module
from tests.test_response import Scheduler


class UpgradeTests(unittest.TestCase):
    def test_existing_json_survives_yaml_dependency_added(self):
        with temp_gtd_dir() as root:
            with patch.object(core, '_optional_yaml', return_value=None):
                core.init_gtd()
                core.set_config('user_name', '保留用户')
            # Presence of YAML support must not switch an existing JSON store.
            with patch.object(core, '_optional_yaml', return_value=object()):
                core.init_gtd()
                self.assertEqual(core.get_config('user_name'), '保留用户')
                core.set_config('review.time', '19:30')
            self.assertFalse((root / 'config.yaml').exists())
            self.assertEqual(json.loads((root / 'config.json').read_text())['review']['time'], '19:30')

    def test_yaml_dependency_removed_does_not_create_defaults(self):
        with temp_gtd_dir() as root, patch.object(core, '_optional_yaml', return_value=None):
            path = root / 'config.yaml'
            path.write_text('user_name: 保留用户\n')
            before = path.read_bytes()
            core.init_gtd()
            with self.assertRaises(core.GTDValidationError):
                core.load_config()
            with self.assertRaises(core.GTDValidationError):
                core.save_config({'user_name': 'default'})
            self.assertFalse((root / 'config.json').exists())
            self.assertEqual(path.read_bytes(), before)

    def test_conflicting_or_invalid_configs_never_silently_reset(self):
        with temp_gtd_dir() as root:
            (root / 'config.yaml').write_text('user_name: A\n')
            (root / 'config.json').write_text('{"user_name": "B"}')
            with self.assertRaises(core.GTDValidationError):
                core.init_gtd()
            self.assertEqual(json.loads((root / 'config.json').read_text())['user_name'], 'B')
        with temp_gtd_dir() as root:
            path = root / 'config.json'
            path.write_text('[]')
            with self.assertRaises(core.GTDValidationError):
                core.set_config('user_name', 'new')
            self.assertEqual(path.read_text(), '[]')

    def test_reloaded_plugin_retains_live_schedule_state_and_deleted_jobs(self):
        with temp_gtd_dir(), patch.object(reminders, 'runtime_timezone', return_value='Asia/Shanghai'):
            scheduler = Scheduler()
            result = decode(tools.init_handler(scheduler.dispatch_tool)({'routines': [
                {'key': 'weekly_plan', 'frequency': 'weekly', 'weekday': 1, 'time': '08:00', 'prompt': '计划'}]}))
            self.assertTrue(result['ok'], result)
            scheduler.jobs[0].update(enabled=False, schedule='30 7 * * 2', deliver='qqbot:changed')
            before = copy.deepcopy(scheduler.jobs)
            scheduler.calls.clear()
            load_plugin_module().register(scheduler)
            handler = next(t['handler'] for t in scheduler.tools if t['name'] == 'gtd_init')
            result = decode(handler({}))
            self.assertEqual(result['schedules']['status'], 'ready')
            self.assertEqual(before, scheduler.jobs)
            self.assertEqual([c[0]['action'] for c in scheduler.calls], ['list'])
            scheduler.jobs.clear()
            result = decode(handler({}))
            self.assertFalse(result['ok'])
            self.assertEqual(scheduler.jobs, [])

    def test_opt_out_and_newer_setup_format_survive_reload(self):
        with temp_gtd_dir() as root:
            self.assertTrue(decode(tools.handle_init({'routines': []}))['ok'])
            self.assertEqual(decode(tools.handle_init({}))['schedules']['status'], 'skipped')
            path = root / 'schedule-setup.json'
            path.write_text('{"version": 99, "names": []}')
            self.assertFalse(decode(tools.handle_init({'routines': []}))['ok'])
            self.assertEqual(json.loads(path.read_text())['version'], 99)

    def test_old_install_without_inventory_discovers_existing_reminder(self):
        with temp_gtd_dir(), patch.object(reminders, 'runtime_timezone', return_value='Asia/Shanghai'):
            scheduler = Scheduler()
            decode(tools.reminder_handler(scheduler.dispatch_tool)({'action': 'enable'}))
            scheduler.jobs[0]['enabled'] = False
            before = copy.deepcopy(scheduler.jobs)
            result = decode(tools.init_handler(scheduler.dispatch_tool)({}))
            self.assertTrue(result['schedules']['discovered'])
            self.assertEqual(before, scheduler.jobs)

    def test_incomplete_install_registers_no_tools(self):
        module = load_plugin_module()
        ctx = FakeHermesContext()
        with tempfile.TemporaryDirectory() as directory:
            module.SKILL_PATH = Path(directory) / 'missing.md'
            with self.assertRaises(FileNotFoundError):
                module.register(ctx)
        self.assertEqual(ctx.tools, [])
        self.assertEqual(ctx.skills, [])

    def test_clean_copied_install_uses_own_modules_and_preserves_data(self):
        source = Path(__file__).resolve().parents[1]
        with temp_gtd_dir() as root, tempfile.TemporaryDirectory() as directory:
            core.init_gtd()
            core.capture('重装后保留')
            core.set_config('user_name', '已有偏好')
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*')
                      if p.is_file() and p.name != '.gtd.lock'}
            # Two fresh installation paths, with no repository on sys.path.
            for name in ('install_v1', 'install_v2'):
                target = Path(directory) / name
                target.mkdir()
                for file in source.glob('*.py'):
                    shutil.copy2(file, target / file.name)
                shutil.copytree(source / 'skills', target / 'skills')
                script = '''
import importlib.util, sys
from pathlib import Path
root = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('installed_gtd', root / '__init__.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
schemas, handlers, *_ = module._load_runtime()
assert sys.modules['installed_gtd.gtd_core'].__file__.startswith(str(root))
import json
assert json.loads(handlers['gtd_init']({'setup_schedules': False}))['ok']
assert json.loads(handlers['gtd_config_get']({'key': 'user_name'}))['ok']
'''
                subprocess.run([sys.executable, '-I', '-c', script, str(target)],
                               cwd=directory, check=True, capture_output=True, text=True)
            after = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*')
                     if p.is_file() and p.name != '.gtd.lock'}
            self.assertEqual(before, after)
