import copy
import os
import unittest
from unittest.mock import patch

import reminders
import tools
from tests.helpers import decode, temp_gtd_dir
from tests.test_plugin_runtime import load_plugin_module
from tests.test_response import Scheduler


class InitializationTests(unittest.TestCase):
    def setUp(self):
        directory = temp_gtd_dir()
        self.root = directory.__enter__()
        self.addCleanup(directory.__exit__, None, None, None)
        clock = patch.object(reminders, 'runtime_timezone', return_value='Asia/Shanghai')
        clock.start()
        self.addCleanup(clock.stop)
        self.scheduler = Scheduler()
        load_plugin_module().register(self.scheduler)
        self.handler = next(t['handler'] for t in self.scheduler.tools if t['name'] == 'gtd_init')

    def selected(self):
        return [
            {'key': 'daily_reminder', 'frequency': 'daily', 'time': '07:00', 'prompt': '每日提醒'},
            {'key': 'daily_summary', 'frequency': 'daily', 'time': '20:00', 'prompt': '每日总结'},
        ]

    def call(self, **args):
        args.setdefault('routines', self.selected())
        return decode(self.handler(args, task_id='init-session'))

    def test_unspecified_preferences_create_only_data(self):
        result = decode(self.handler({}))
        self.assertTrue(result['ok'])
        self.assertTrue(result['initialized'])
        self.assertEqual(result['schedules']['status'], 'needs_preferences')
        self.assertEqual([c[0]['action'] for c in self.scheduler.calls], ['list'])

    def test_only_selected_evening_job_and_no_jobs_option(self):
        self.assertTrue(self.call(routines=[])['ok'])
        self.assertEqual(self.scheduler.calls, [])
        self.assertTrue(self.call(routines=[self.selected()[1]])['ok'])
        self.assertEqual(len(self.scheduler.jobs), 1)
        self.assertEqual(self.scheduler.jobs[0]['schedule'], '0 20 * * *')

    def test_week_end_and_week_start_at_user_chosen_times(self):
        routines = [
            {'key': 'weekly_review', 'frequency': 'weekly', 'weekday': 0,
             'time': '20:30', 'prompt': '每周最后一天晚上回顾'},
            {'key': 'weekly_plan', 'frequency': 'weekly', 'weekday': 1,
             'time': '08:00', 'prompt': '每周第一天早上计划'},
        ]
        self.assertTrue(self.call(routines=routines)['ok'])
        self.assertEqual([j['schedule'] for j in self.scheduler.jobs], ['30 20 * * 0', '0 8 * * 1'])

    def test_missing_time_or_weekday_never_chooses_defaults(self):
        for routine in (
            {'key': 'morning', 'frequency': 'daily', 'prompt': '提醒'},
            {'key': 'week', 'frequency': 'weekly', 'time': '08:00', 'prompt': '回顾'},
        ):
            self.assertFalse(self.call(routines=[routine])['ok'])
        self.assertEqual(self.scheduler.calls, [])

    def test_defaults_registration_and_retry_preserve_user_changes(self):
        self.assertEqual(self.scheduler.calls, [])
        result = self.call()
        self.assertTrue(result['ok'], result)
        self.assertEqual([j['schedule'] for j in self.scheduler.jobs], ['0 7 * * *', '0 20 * * *'])
        self.assertFalse(result['schedules']['delivery_verified'])
        for job in self.scheduler.jobs:
            self.assertEqual(job['skills'], ['gtd:gtd'])
            self.assertEqual(job['deliver'], 'origin')
            self.assertIn(str(self.root), job['prompt'])
        self.scheduler.jobs[0].update(enabled=False, schedule='0 8 * * *', deliver='qqbot:me', prompt='custom')
        before = copy.deepcopy(self.scheduler.jobs)
        self.assertTrue(self.call(deliver='telegram:other')['ok'])
        self.assertEqual(before, self.scheduler.jobs)
        self.assertTrue(all(kw['task_id'] == 'init-session' for _, kw in self.scheduler.calls))

    def test_legacy_reminder_is_reused(self):
        decode(tools.reminder_handler(self.scheduler.dispatch_tool)({'action': 'enable'}))
        self.scheduler.jobs[0]['enabled'] = False
        old = copy.deepcopy(self.scheduler.jobs[0])
        result = self.call()
        self.assertTrue(result['ok'], result)
        self.assertEqual(len(self.scheduler.jobs), 2)
        self.assertEqual(old, self.scheduler.jobs[0])

    def test_custom_times_and_runtime_timezone(self):
        with patch.object(reminders, 'runtime_timezone', return_value='Europe/London'):
            routines = self.selected()
            routines[0]['time'], routines[1]['time'] = '07:35', '22:15'
            result = self.call(routines=routines, deliver='telegram:me')
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['schedules']['timezone'], 'Europe/London')
        self.assertEqual([j['schedule'] for j in self.scheduler.jobs], ['35 7 * * *', '15 22 * * *'])

    def test_data_only_does_not_touch_scheduler(self):
        self.assertTrue(self.call(setup_schedules=False)['ok'])
        self.assertEqual(self.scheduler.calls, [])
        self.assertTrue((self.root / 'inbox.md').exists())

    def test_missing_dispatch_reports_partial_success(self):
        result = decode(tools.handle_init({'routines': self.selected()}))
        self.assertFalse(result['ok'])
        self.assertTrue(result['initialized'])
        self.assertEqual(result['schedules']['status'], 'incomplete')
        self.assertTrue((self.root / 'inbox.md').exists())

    def test_invalid_options_do_not_create_jobs(self):
        for args in ({'routines': [{**self.selected()[0], 'time': '25:00'}]}, {'timezone': 'UTC'}, {'deliver': 'all'}):
            self.assertFalse(self.call(**args)['ok'])
        self.assertEqual(self.scheduler.jobs, [])

    def test_partial_failure_retries_only_missing_job(self):
        dispatch = self.scheduler.dispatch_tool

        def fail_summary(name, data, **kwargs):
            if data['action'] == 'create' and data['name'].startswith('gtd-summary-'):
                return {'success': False, 'error': 'unavailable'}
            return dispatch(name, data, **kwargs)

        result = decode(tools.init_handler(fail_summary)({'routines': self.selected()}))
        self.assertFalse(result['ok'])
        self.assertEqual(len(self.scheduler.jobs), 1)
        self.assertTrue(self.call()['ok'])
        self.assertEqual(len(self.scheduler.jobs), 2)

    def test_uncertain_readback_does_not_duplicate_on_retry(self):
        self.scheduler.fail_verification = True
        result = self.call()
        self.assertFalse(result['ok'])
        self.assertEqual(result['schedules']['jobs'][0]['status'], 'unverified')
        self.assertEqual(len(self.scheduler.jobs), 1)
        self.scheduler.fail_verification = False
        self.assertTrue(self.call()['ok'])
        self.assertEqual(len(self.scheduler.jobs), 2)

    def test_directories_have_independent_routines(self):
        self.assertTrue(self.call()['ok'])
        with temp_gtd_dir():
            self.assertTrue(self.call()['ok'])
        self.assertEqual(len({j['name'] for j in self.scheduler.jobs}), 4)

    def test_duplicate_names_are_reported_without_modifying_existing_jobs(self):
        self.assertTrue(self.call()['ok'])
        duplicate = {**self.scheduler.jobs[0], 'id': 'duplicate'}
        self.scheduler.jobs.append(duplicate)
        before = copy.deepcopy(self.scheduler.jobs)
        self.assertFalse(self.call()['ok'])
        self.assertEqual(self.scheduler.jobs, before)

    def test_scheduled_policy_is_not_bypassed(self):
        with patch.dict(os.environ, {'HERMES_CRON_SESSION': 'true'}), patch(
                'gtd_response.check_scheduling_policy', side_effect=ValueError('scheduling disabled')):
            result = self.call()
        self.assertFalse(result['ok'])
        self.assertEqual(self.scheduler.calls, [])


if __name__ == '__main__':
    unittest.main()
