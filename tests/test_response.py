from __future__ import annotations

import copy
import json
import sys
import types
import unittest
from unittest.mock import patch

import gtd_core as core
import gtd_response as response
import reminders
import tools
from tests.helpers import decode, temp_gtd_dir
from tests.test_plugin_runtime import FakeHermesContext, load_plugin_module


class Scheduler(FakeHermesContext):
    """Stateful fake; can expose both legacy and current Hermes list contracts."""
    def __init__(self, preview=False):
        super().__init__()
        self.jobs = []
        self.calls = []
        self.preview = preview
        self.fail_update = False
        self.ignore_update = False
        self.fail_verification = False
        # Hermes registers bundled skills as plugin:skill, not their short name.
        self.available_skills = {'gtd:gtd', 'reader', 'other'}

    def get_job(self, job_id):
        return copy.deepcopy(next((j for j in self.jobs if j['id'] == job_id), None))

    def dispatch_tool(self, name, data, **kwargs):
        assert name == 'cronjob_manage'
        self.calls.append((copy.deepcopy(data), kwargs))
        action = data['action']
        if action in {'create', 'update'} and 'skills' in data:
            missing = set(data['skills']) - self.available_skills
            if missing:
                return {'success': False, 'error': 'Skill not found: ' + ', '.join(sorted(missing))}
        if action == 'list':
            if self.fail_verification and any(c[0]['action'] == 'create' for c in self.calls):
                return {'success': False, 'error': 'verification offline'}
            jobs = copy.deepcopy(self.jobs)
            if self.preview:
                for job in jobs:
                    job['job_id'] = job.pop('id')
                    job['prompt_preview'] = job.pop('prompt')[:100] + '...'
            return json.dumps({'success': True, 'jobs': jobs})
        if action == 'create':
            job = {k: v for k, v in data.items() if k != 'action'}
            job.update(id=f'job-{len(self.jobs) + 1}', enabled=True)
            self.jobs.append(job)
        else:
            job = next(j for j in self.jobs if j['id'] == data['job_id'])
            if action == 'update':
                if self.fail_update:
                    return {'success': False, 'error': 'update offline'}
                if not self.ignore_update:
                    job.update({k: v for k, v in data.items() if k not in {'action', 'job_id'}})
            elif action == 'remove':
                self.jobs.remove(job)
            elif action in {'pause', 'resume'}:
                job['enabled'] = action == 'resume'
            elif action == 'run':
                # A synchronous Hermes run may invoke GTD again. No file lock
                # should be held by its parent during that external execution.
                import storage
                assert getattr(storage._state, 'txn', None) is None
        return {'success': True, 'job': copy.deepcopy(job)}


class ResponseTests(unittest.TestCase):
    def setUp(self):
        self.directory = temp_gtd_dir()
        self.root = self.directory.__enter__()
        self.addCleanup(self.directory.__exit__, None, None, None)
        core.init_gtd()
        self.clock = patch.object(reminders, 'runtime_timezone', return_value='Asia/Shanghai')
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.scheduler = Scheduler()
        load_plugin_module().register(self.scheduler)
        self.handler = next(t['handler'] for t in self.scheduler.tools if t['name'] == 'gtd_manage')

    def call(self, **args):
        result = decode(self.handler(args, task_id='test-context'))
        self.assertTrue(result['ok'], result)
        return result

    def create_job(self, **data):
        result = self.call(action='create', target='schedule', data={
            'key': 'registration', 'schedule': '0 9 * * *', 'prompt': '检查报名事项，完成后关闭跟进',
            'deliver': 'qqbot:me', **data})
        return result['jobs'][0]

    def edit_job(self, job, action='update', **data):
        return self.call(action=action, target='schedule', id=job['id'], revision=job['revision'], data=data)

    def test_deadline_change_and_completion_reconcile_with_schedule(self):
        task = self.call(action='create', data={'category': 'next_actions', 'content': '报名', 'deadline': '2026-09-18'})['records'][0]
        card = core.add_reference(title='报名通知', note='截止延期至2026-09-25')
        core.relations(card['reference_id'], 'link', task['id'])
        job = self.create_job(related_ids=[task['id']])
        before = self.call(action='review', ids=[job['id']])
        self.assertEqual({r['id'] for r in before['records']}, {task['id'], card['reference_id']})
        latest = self.call(action='get', id=task['id'])['record']
        updated = self.call(action='update', id=task['id'], revision=latest['revision'],
                            data={'raw': latest['raw'].replace('2026-09-18', '2026-09-25')})
        self.assertTrue(updated['changed'])
        job = self.edit_job(job, schedule='0 8 * * *')['jobs'][0]
        self.assertEqual(job['deliver'], 'qqbot:me')
        self.assertEqual(job['gtd_context']['related_ids'], [task['id']])
        after = self.call(action='review', ids=[job['id']], previous_revision=before['revision'])
        self.assertTrue(after['changed'])
        latest = self.call(action='get', id=task['id'])['record']
        self.call(action='complete', id=task['id'], revision=latest['revision'])
        self.edit_job(job, action='delete')
        self.assertEqual(self.scheduler.jobs, [])
        self.assertEqual(core.get_reference(card['reference_id'])['title'], '报名通知')

    def test_no_change_tick_and_retries_do_not_create_or_modify_jobs(self):
        job = self.create_job()
        before = self.call(action='review')
        self.scheduler.jobs[0].update(last_run_at='2026-09-16T09:00:00', next_run_at='2026-09-17T09:00:00', last_status='success')
        self.assertFalse(self.call(action='review', previous_revision=before['revision'])['changed'])
        self.assertFalse(self.edit_job(job, schedule='0 9 * * *')['changed'])
        retry = self.call(action='create', target='schedule', data={'key': 'registration', 'schedule': '0 9 * * *', 'prompt': 'same purpose'})
        self.assertFalse(retry['changed'])
        self.assertEqual(len(self.scheduler.jobs), 1)
        self.assertEqual([c[0]['action'] for c in self.scheduler.calls].count('update'), 0)

    def test_pause_resume_run_and_stale_schedule_revision(self):
        job = self.create_job()
        paused = self.edit_job(job, action='pause')['jobs'][0]
        self.assertFalse(paused['enabled'])
        self.assertFalse(self.edit_job(paused, action='pause')['changed'])
        stale = decode(self.handler({'action': 'update', 'target': 'schedule', 'id': job['id'],
                                     'revision': job['revision'], 'data': {'schedule': '0 10 * * *'}}))
        self.assertFalse(stale['ok'])
        resumed = self.edit_job(paused, action='resume')['jobs'][0]
        self.edit_job(resumed, action='run')
        self.assertTrue(any(kw.get('task_id') == 'test-context' for _, kw in self.scheduler.calls))

    def test_partial_failure_keeps_successful_content_edit(self):
        memory = self.call(action='create', data={'category': 'memories', 'content': '洗衣日是周五'})['records'][0]
        job = self.create_job()
        self.call(action='update', id=memory['id'], revision=memory['revision'], data={'content': '洗衣日改为周六'})
        self.scheduler.fail_update = True
        result = decode(self.handler({'action': 'update', 'target': 'schedule', 'id': job['id'],
                                      'revision': job['revision'], 'data': {'schedule': '0 9 * * 6'}}))
        self.assertFalse(result['ok'])
        self.assertEqual(self.call(action='get', id=memory['id'])['record']['title'], '洗衣日改为周六')
        self.assertEqual(self.scheduler.jobs[0]['schedule'], '0 9 * * *')

    def test_content_patch_preserves_fields_and_rejects_stale_revision(self):
        created = self.call(action='create', data={'category': 'materials', 'title': '通知', 'note': '原备注', 'tags': ['报名']})['records'][0]
        updated = self.call(action='update', id=created['id'], revision=created['revision'], data={'title': '报名通知'})['records'][0]
        self.assertEqual(updated['card']['note'], '原备注')
        self.assertEqual(updated['card']['tags'], ['报名'])
        self.assertFalse(self.call(action='update', id=updated['id'], revision=updated['revision'], data={'title': '报名通知'})['changed'])
        stale = decode(self.handler({'action': 'delete', 'id': created['id'], 'revision': created['revision']}))
        self.assertFalse(stale['ok'])
        self.call(action='delete', id=updated['id'], revision=updated['revision'])
        self.assertTrue((self.root / 'web-trash' / 'reference-cards' / (updated['id'] + '.md')).exists())

    def test_missing_scheduler_not_reported_as_empty_successful_review(self):
        result = decode(tools.handle_manage({'action': 'review'}))
        self.assertFalse(result['scheduler']['available'])
        self.assertFalse(result['review_complete'])
        malformed = tools.manage_handler(lambda *a, **kw: {'success': True})
        self.assertFalse(decode(malformed({'action': 'review'}))['scheduler']['available'])

    def test_modern_list_contract_gets_full_prompt_from_runtime(self):
        job = self.create_job()
        self.scheduler.preview = True
        runtime = types.ModuleType('cron.jobs')
        runtime.get_job = self.scheduler.get_job
        with patch.dict(sys.modules, {'cron': types.ModuleType('cron'), 'cron.jobs': runtime}):
            result = self.call(action='review')
            self.assertTrue(result['review_complete'])
            listed = result['scheduler']['jobs'][0]
            self.assertEqual(listed['prompt'], job['prompt'])
            self.assertEqual(listed['id'], job['id'])
            self.edit_job(listed, action='pause')

    def test_preview_without_details_is_not_a_complete_review(self):
        self.create_job()
        self.scheduler.preview = True
        with patch.dict(sys.modules, {'cron.jobs': None}):
            result = self.call(action='review')
            self.assertFalse(result['review_complete'])
            job = result['scheduler']['jobs'][0]
            failed = decode(self.handler({'action': 'delete', 'target': 'schedule', 'id': job['id'], 'revision': job['revision']}))
            self.assertFalse(failed['ok'])

    def test_success_ack_without_persisted_edit_is_unverified(self):
        job = self.create_job()
        self.scheduler.ignore_update = True
        result = self.edit_job(job, schedule='0 8 * * *')
        self.assertFalse(result['verified'])
        self.assertIsNone(result['changed'])

    def test_plain_named_related_job_is_discoverable_and_adoptable(self):
        self.scheduler.jobs = [{'id': 'laundry', 'name': '洗衣服', 'prompt': '每周五洗衣服',
                                'schedule': '0 9 * * 5', 'enabled': True, 'deliver': 'qqbot:me'}]
        result = self.call(action='review', query='洗衣')
        self.assertEqual(result['scheduler']['other_job_summaries'][0]['id'], 'laundry')
        job = self.call(action='get', target='schedule', id='laundry')['job']
        adopted = self.edit_job(job, gtd_dir=str(core.get_gtd_dir()), prompt='审视洗衣安排')['jobs'][0]
        self.assertTrue(response.belongs(adopted))
        self.assertEqual(len(self.scheduler.jobs), 1)

    def test_daily_compatibility_uses_modern_job_ids_and_unified_context(self):
        self.scheduler.preview = True
        runtime = types.ModuleType('cron.jobs')
        runtime.get_job = self.scheduler.get_job
        with patch.dict(sys.modules, {'cron': types.ModuleType('cron'), 'cron.jobs': runtime}):
            handler = tools.reminder_handler(self.scheduler.dispatch_tool)
            first = decode(handler({'action': 'enable'}))
            self.assertTrue(first['ok'], first)
            self.assertEqual(response.job_context(first['job'])['gtd_dir'], str(core.get_gtd_dir()))
            second = decode(handler({'action': 'enable', 'time': '10:00'}))
            self.assertTrue(second['ok'], second)
            self.assertEqual(len(self.scheduler.jobs), 1)
            self.assertEqual(self.scheduler.jobs[0]['schedule'], '0 10 * * *')
            self.assertTrue(decode(handler({'action': 'disable'}))['ok'])
            self.assertFalse(self.scheduler.jobs[0]['enabled'])

    def test_other_directory_is_excluded_and_legacy_job_can_be_adopted(self):
        foreign = {'id': 'foreign', 'name': 'gtd-another', 'prompt': 'GTD_CONTEXT=' + json.dumps({'gtd_dir': '/another'}) + '\nother', 'enabled': True}
        legacy = {'id': 'legacy', 'name': 'GTD 洗衣', 'prompt': '周五洗衣', 'enabled': False, 'schedule': '0 9 * * 5', 'deliver': 'qqbot:me'}
        self.scheduler.jobs = [foreign, legacy]
        review = self.call(action='review')
        self.assertEqual(review['scheduler']['jobs'], [])
        self.assertEqual([j['id'] for j in review['scheduler']['unscoped_jobs']], ['legacy'])
        job = review['scheduler']['unscoped_jobs'][0]
        adopted = self.edit_job(job, gtd_dir=str(core.get_gtd_dir()), prompt='周五审视洗衣事项，无变化可以静默')['jobs'][0]
        self.assertFalse(adopted['enabled'])
        self.assertEqual(adopted['deliver'], 'qqbot:me')
        self.assertTrue(response.belongs(adopted))
        self.assertFalse(decode(self.handler({'action': 'get', 'target': 'schedule', 'id': 'foreign'}))['ok'])

    def test_directory_mismatch_stops_before_read_or_dispatch(self):
        with patch.object(response.web_data, 'records', side_effect=AssertionError('must not read')):
            result = decode(self.handler({'action': 'review', 'expected_directory': '/wrong'}))
        self.assertFalse(result['ok'])
        self.assertEqual(self.scheduler.calls, [])

    def test_accepted_create_with_failed_verification_is_not_retried(self):
        self.scheduler.fail_verification = True
        result = self.call(action='create', target='schedule', data={'key': 'uncertain', 'prompt': '检查', 'schedule': '0 9 * * *'})
        self.assertFalse(result['verified'])
        self.assertIsNone(result['changed'])
        self.assertEqual(len(self.scheduler.jobs), 1)

    def test_scheduled_policy_is_respected(self):
        context = types.ModuleType('gateway.session_context')
        context.get_session_env = lambda *a: 'true'
        config = types.ModuleType('hermes_cli.config')
        config.load_config_readonly = lambda: {'cron': {'allow_agent_scheduling': False}}
        modules = {'gateway': types.ModuleType('gateway'), 'gateway.session_context': context,
                   'hermes_cli': types.ModuleType('hermes_cli'), 'hermes_cli.config': config}
        with patch.dict(sys.modules, modules):
            self.assertFalse(self.call(action='review')['scheduler']['available'])
            self.assertEqual(self.scheduler.calls, [])
            config.load_config_readonly = lambda: {'cron': {'allow_agent_scheduling': True}}
            self.assertTrue(self.call(action='review')['scheduler']['available'])

    def test_recall_pagination_and_memory_noop(self):
        for title in ('洗衣机', '洗衣液', '无关记录'):
            self.call(action='create', data={'category': 'memories', 'content': title})
        first = self.call(action='review', query='洗衣', limit=1)
        self.assertEqual(first['total'], 2)
        self.assertFalse(first['review_complete'])
        second = self.call(action='review', query='洗衣', limit=1, offset=first['next_offset'])
        self.assertIsNone(second['next_offset'])
        memory = self.call(action='get', id=first['records'][0]['id'])['record']
        result = self.call(action='update', id=memory['id'], revision=memory['revision'], data={'content': memory['title']})
        self.assertFalse(result['changed'])
        self.assertEqual(self.call(action='get', id=memory['id'])['record']['revision'], memory['revision'])

    def test_unrelated_task_edit_does_not_change_recalled_content(self):
        task = self.call(action='create', data={'category': 'next_actions', 'content': '洗衣服'})['records'][0]
        before = self.call(action='review', ids=[task['id']])
        self.call(action='create', data={'category': 'next_actions', 'content': '报名'})
        after = self.call(action='review', ids=[task['id']], previous_revision=before['revision'])
        self.assertFalse(after['changed'])

    def test_migrate_legacy_skill_without_resuming_or_changing_job(self):
        job = self.create_job()
        self.scheduler.jobs[0].update(skills=['reader', 'gtd', 'gtd:gtd'], enabled=False)
        before = copy.deepcopy(self.scheduler.jobs[0])
        latest = self.call(action='get', target='schedule', id=job['id'])['job']
        updated = self.edit_job(latest)['jobs'][0]
        self.assertEqual(updated['skills'], ['reader', 'gtd:gtd'])
        for field in ('id', 'name', 'schedule', 'prompt', 'deliver', 'enabled'):
            self.assertEqual(updated[field], before[field])
        self.assertTrue(self.edit_job(updated)['changed'] is False)
        self.assertEqual([c[0]['action'] for c in self.scheduler.calls].count('update'), 1)

    def test_namespaced_skill_discovers_neutrally_named_job(self):
        self.scheduler.jobs = [{'id': 'ordinary', 'name': '日常事项', 'prompt': '检查事项',
                                'skills': ['gtd:gtd'], 'enabled': True}]
        found = self.call(action='review')['scheduler']['unscoped_jobs']
        self.assertEqual([j['id'] for j in found], ['ordinary'])
        self.assertTrue(response.is_gtd_candidate({'skill': 'gtd:gtd'}))
        self.assertTrue(response.is_gtd_candidate({'skill': 'gtd'}))

    def test_daily_update_preserves_other_skills_and_migrates_old_name(self):
        handler = tools.reminder_handler(self.scheduler.dispatch_tool)
        created = decode(handler({'action': 'enable'}))
        self.assertTrue(created['ok'], created)
        self.assertEqual(self.scheduler.jobs[0]['skills'], ['gtd:gtd'])
        self.scheduler.jobs[0]['skills'] = ['reader', 'gtd']
        updated = decode(handler({'action': 'enable', 'time': '08:00'}))
        self.assertTrue(updated['ok'], updated)
        self.assertEqual(self.scheduler.jobs[0]['skills'], ['reader', 'gtd:gtd'])


if __name__ == '__main__':
    unittest.main()
