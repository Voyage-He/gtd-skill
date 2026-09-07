from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import gtd_core as core
import reminders
import tools
from tests.helpers import temp_gtd_dir, decode
from tests.test_plugin_runtime import load_plugin_module, FakeHermesContext


class ReliableWorkflows(unittest.TestCase):
    def test_failed_move_and_failed_archive_roll_back(self):
        with temp_gtd_dir() as root:
            core.init_gtd(); core.capture('重要通知')
            before = (root / 'inbox.md').read_bytes()
            with patch.object(core, '_append_target', side_effect=OSError('disk failure')):
                result = decode(tools.handle_inbox_process({'index': 1, 'target': 'projects'}))
            self.assertFalse(result['ok'])
            self.assertEqual((root / 'inbox.md').read_bytes(), before)
            item = core.process_inbox(1, 'next_actions')
            core.complete_number(item['number'])
            before = (root / 'next_actions.md').read_bytes()
            with patch.object(core, 'append_text', side_effect=OSError('disk failure')):
                self.assertRaises(OSError, core.archive_completed)
            self.assertEqual((root / 'next_actions.md').read_bytes(), before)

    def test_crash_recovery_before_next_read(self):
        with temp_gtd_dir() as root:
            core.init_gtd(); core.capture('recover me')
            before = (root / 'inbox.md').read_bytes()
            source = "import os, gtd_core as c; c._append_target=lambda *a: os._exit(19); c.process_inbox(1, 'next_actions')"
            proc = subprocess.run([sys.executable, '-c', source], env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
            self.assertEqual(proc.returncode, 19)
            self.assertTrue((root / '.gtd-transaction.json').exists())
            self.assertEqual(len(core.read_inbox_items()), 1)
            self.assertEqual((root / 'inbox.md').read_bytes(), before)
            self.assertFalse((root / '.gtd-transaction.json').exists())

    def test_archived_ids_and_stats_survive(self):
        with temp_gtd_dir():
            core.init_gtd(); core.capture('first')
            first = core.process_inbox(1, 'next_actions')
            core.complete_number(first['number'])
            before = core.collect_weekly_data()
            core.archive_completed()
            self.assertEqual(core.collect_weekly_data()['completed_this_week'], before['completed_this_week'])
            self.assertEqual(core.get_archive_stats(), 1)
            self.assertEqual(decode(tools.handle_stats({}))['archive_total'], 1)
            self.assertEqual(core.weekly_stats()['new_items'], 1)
            core.capture('second')
            self.assertEqual(core.process_inbox(1, 'next_actions')['number'], 'N002')

    def test_concurrent_processes_get_distinct_ids(self):
        with temp_gtd_dir():
            core.init_gtd()
            for i in range(8): core.capture(str(i))
            source = "import gtd_core as c; print(c.process_inbox(1, 'next_actions')['number'])"
            def run(_):
                return subprocess.check_output([sys.executable, '-c', source], env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, text=True).strip()
            with ThreadPoolExecutor(max_workers=4) as pool:
                ids = list(pool.map(run, range(8)))
            self.assertEqual(len(set(ids)), 8)
            self.assertEqual(len(core.list_actions()), 8)
            self.assertEqual(core.read_inbox_items(), [])

    def test_project_archive_preserves_other_sections(self):
        with temp_gtd_dir() as root:
            core.init_gtd()
            (root / 'projects.md').write_text('### P001: test\n- **状态**: 已完成\n## 私人备注\n不要移动\n')
            core.archive_completed()
            self.assertIn('不要移动', (root / 'projects.md').read_text())

    def test_search_intersection(self):
        with temp_gtd_dir():
            core.init_gtd()
            wanted = core.add_reference(title='合同', related_items=['P001'])
            core.add_reference(title='合同', related_items=['P002'])
            core.add_reference(title='预算', related_items=['P001'])
            results = core.search_references('合同', related_item='P001')['results']
            self.assertEqual([r['reference_id'] for r in results], [wanted['reference_id']])


class MessageWorkflows(unittest.TestCase):
    def test_forward_recall_return_and_followup(self):
        with temp_gtd_dir() as root:
            core.init_gtd()
            picture = root / '活动照片.jpg'; picture.write_bytes(b'photo')
            form = root / '报名表.pdf'; form.write_bytes(b'%PDF-example')
            args = {'text': '活动在礼堂举行', 'file_paths': [str(picture), str(form)],
                    'channel': 'weixin', 'chat_id': 'self', 'message_id': 'm1', 'sender': '张三',
                    'extracted_text': '报名方式：线上', 'notices': [{'label': '报名', 'date': core.today_str()}]}
            saved = decode(tools.handle_message_capture(args))
            self.assertTrue(saved['ok'], saved)
            self.assertEqual(saved['saved_attachment_count'], 2)
            again = core.capture_message(**args)
            self.assertTrue(again['duplicate'])
            self.assertEqual(len(list(core.reference_cards_dir().glob('*.md'))), 1)
            picture.unlink(); form.unlink()
            found = core.search_references('线上')['results']
            self.assertEqual(found[0]['reference_id'], saved['reference_id'])
            self.assertEqual(core.search_references('张三')['count'], 1)
            files = core.reference_files(saved['reference_id'])
            self.assertEqual(files['delivery_status'], 'prepared')
            self.assertEqual([Path(f['path']).read_bytes() for f in files['files']], [b'photo', b'%PDF-example'])
            self.assertEqual(len(core.daily_check()['notices']), 1)
            core.update_notice(saved['reference_id'], 1, True)
            self.assertEqual(core.daily_check()['notices'], [])
            core.capture_message(text='补充：下午开始', reference_id=saved['reference_id'])
            self.assertIn('补充', core.get_reference(saved['reference_id'])['message_text'])

    def test_copy_failure_leaves_no_partial_message(self):
        with temp_gtd_dir() as root:
            core.init_gtd()
            source = root / 'source.txt'; source.write_text('hello')
            real_copy = core.shutil.copy2
            calls = []
            def copy(*args):
                calls.append(args)
                if len(calls) == 2: raise OSError('copy failed')
                return real_copy(*args)
            with patch.object(core.shutil, 'copy2', side_effect=copy):
                result = decode(tools.handle_message_capture({'file_paths': [str(source), str(source)]}))
            self.assertFalse(result['ok'])
            self.assertEqual(list(core.reference_cards_dir().glob('*.md')), [])
            self.assertEqual([p for p in core.reference_assets_dir().rglob('*') if p.is_file()], [])
            self.assertEqual(core.search_references()['count'], 0)

    def test_bounded_read_and_next_page(self):
        with temp_gtd_dir() as root:
            source = root / 'big.txt'; source.write_text('abcdefghij' * 10000)
            data = core.capture_message(file_paths=[str(source)])
            first = core.read_reference(data['reference_id'], max_chars=4)
            self.assertEqual(first['content'], 'abcd')
            self.assertEqual(first['next_offset'], 4)
            self.assertIsNone(first['total_chars'])
            second = core.read_reference(data['reference_id'], max_chars=4, offset=4)
            self.assertEqual(second['content'], 'efgh')

    def test_nested_validation_and_overdue(self):
        with temp_gtd_dir() as root:
            result = decode(tools.handle_message_capture({'file_paths': [1]}))
            self.assertFalse(result['ok'])
            core.init_gtd()
            core.capture('overdue'); core.process_inbox(1, 'next_actions', deadline='2000-01-01')
            self.assertEqual(len(core.daily_check()['overdue']), 1)

    def test_empty_index_rebuild_and_manual_refresh(self):
        with temp_gtd_dir():
            data = core.capture_message(text='原始通知')
            path = core.reference_cards_dir() / (data['reference_id'] + '.md')
            path.write_text(path.read_text().replace('原始通知', '更新通知'))
            core.rebuild_reference_index()
            self.assertEqual(core.search_references('更新通知')['count'], 1)
            core.reference_index_path().unlink()
            self.assertEqual(core.search_references('更新通知')['count'], 1)

    def test_long_chinese_filename_and_date_followup(self):
        with temp_gtd_dir() as root:
            path = root / ('报名照片' * 18 + '.png')
            path.write_bytes(b'photo')
            data = core.capture_message(file_paths=[str(path)])
            self.assertEqual(len(core.reference_files(data['reference_id'])['files']), 1)
            core.capture_message(reference_id=data['reference_id'], notices=[{'label': '活动', 'date': core.today_str(), 'kind': 'event'}])
            self.assertEqual(len(core.daily_check()['notices']), 1)

    def test_more_than_999_and_json_without_yaml(self):
        with temp_gtd_dir() as root, patch.object(core, '_optional_yaml', return_value=None):
            core.init_gtd()
            (root / 'next_actions.md').write_text('- [ ] N999: existing\n')
            core.capture('next')
            self.assertEqual(core.process_inbox(1, 'next_actions')['number'], 'N1000')
            self.assertEqual(len(core.list_actions()), 2)
            core.complete_number('N1000')
            data = core.capture_message(text='portable')
            self.assertEqual(core.get_reference(data['reference_id'])['message_text'], 'portable')

    def test_append_to_legacy_reference_preserves_note(self):
        with temp_gtd_dir():
            data = core.add_reference(note='原有备忘')
            core.capture_message(reference_id=data['reference_id'], text='补充消息')
            text = core.get_reference(data['reference_id'])['note']
            self.assertEqual(text, '原有备忘\n补充消息')

    def test_invalid_date_does_not_create_message(self):
        with temp_gtd_dir():
            result = decode(tools.handle_message_capture({'text': '活动', 'notices': [{'label': '活动', 'date': '2026-1-1'}]}))
            self.assertFalse(result['ok'])
            self.assertEqual(list(core.reference_cards_dir().glob('*.md')), [])


class FakeScheduler(FakeHermesContext):
    def __init__(self):
        super().__init__(); self.jobs = []; self.calls = []
    def dispatch_tool(self, name, args, **kwargs):
        assert name == 'cronjob_manage'
        self.calls.append((args.copy(), kwargs))
        action = args['action']
        if action == 'list': return json.dumps({'success': True, 'jobs': self.jobs})
        if action == 'create':
            self.jobs.append({**args, 'id': 'j1', 'next_run_at': '2026-09-08T09:00:00+08:00', 'enabled': True})
        elif action == 'update': self.jobs[0].update(args)
        elif action == 'pause': self.jobs[0]['enabled'] = False
        elif action == 'resume': self.jobs[0]['enabled'] = True
        return json.dumps({'success': True, 'job': self.jobs[0]})


class ReminderWorkflows(unittest.TestCase):
    def test_registered_handler_creates_updates_pauses_and_checks(self):
        with temp_gtd_dir(), patch.object(reminders, 'runtime_timezone', return_value='Asia/Shanghai'):
            ctx = FakeScheduler(); load_plugin_module().register(ctx)
            handler = next(t['handler'] for t in ctx.tools if t['name'] == 'gtd_reminder')
            result = decode(handler({'action': 'enable', 'deliver': 'qqbot:me'}, task_id='context'))
            self.assertTrue(result['ok'], result)
            self.assertFalse(result['delivery_verified'])
            result = decode(handler({'action': 'enable', 'time': '08:00'}))
            self.assertTrue(result['ok'], result)
            self.assertEqual(len(ctx.jobs), 1)
            self.assertEqual(ctx.jobs[0]['schedule'], '0 8 * * *')
            self.assertEqual(ctx.jobs[0]['deliver'], 'qqbot:me')
            self.assertTrue(any(kw.get('task_id') == 'context' for _, kw in ctx.calls))
            self.assertTrue(decode(handler({'action': 'disable'}))['ok'])
            self.assertFalse(ctx.jobs[0]['enabled'])
            self.assertTrue(decode(handler({'action': 'status'}))['configured'])

    def test_unavailable_or_failed_scheduler_never_claims_enabled(self):
        with temp_gtd_dir():
            self.assertFalse(decode(tools.handle_reminder({'action': 'enable'}))['ok'])
            handler = tools.reminder_handler(lambda *a, **kw: '{"success": false, "error": "offline"}')
            self.assertFalse(decode(handler({'action': 'enable'}))['ok'])
            ctx = FakeScheduler()
            with patch.object(reminders, 'runtime_timezone', return_value='UTC'):
                handler = tools.reminder_handler(ctx.dispatch_tool)
                self.assertFalse(decode(handler({'action': 'enable'}))['ok'])
            self.assertEqual(ctx.jobs, [])
