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

    def call(self, **args):
        return decode(self.handler(args, task_id='init-session'))

    def test_defaults_registration_and_retry_preserve_user_changes(self):
        self.assertEqual(self.scheduler.calls, [])
        result = self.call()
        self.assertTrue(result['ok'], result)
        self.assertEqual([j['schedule'] for j in self.scheduler.jobs], ['0 9 * * *', '0 21 * * *'])
        self.assertFalse(result['schedules']['delivery_verified'])
        for job in self.scheduler.jobs:
            self.assertEqual(job['skills'], ['gtd:gtd'])
            self.assertEqual(job['deliver'], 'origin')
            self.assertIn(str(self.root), job['prompt'])
        self.scheduler.jobs[0].update(enabled=False, schedule='0 8 * * *', deliver='qqbot:me', prompt='custom')
        before = copy.deepcopy(self.scheduler.jobs)
        self.assertTrue(self.call(reminder_time='10:00', deliver='telegram:other')['ok'])
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
            result = self.call(reminder_time='07:35', summary_time='22:15', deliver='telegram:me')
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['schedules']['timezone'], 'Europe/London')
        self.assertEqual([j['schedule'] for j in self.scheduler.jobs], ['35 7 * * *', '15 22 * * *'])

    def test_data_only_does_not_touch_scheduler(self):
        self.assertTrue(self.call(setup_schedules=False)['ok'])
        self.assertEqual(self.scheduler.calls, [])
        self.assertTrue((self.root / 'inbox.md').exists())

    def test_missing_dispatch_reports_partial_success(self):
        result = decode(tools.handle_init({}))
        self.assertFalse(result['ok'])
        self.assertTrue(result['initialized'])
        self.assertEqual(result['schedules']['status'], 'incomplete')
        self.assertTrue((self.root / 'inbox.md').exists())

    def test_invalid_options_do_not_create_jobs(self):
        for args in ({'summary_time': '25:00'}, {'timezone': 'UTC'}, {'deliver': 'all'}):
            self.assertFalse(self.call(**args)['ok'])
        self.assertEqual(self.scheduler.jobs, [])

    def test_partial_failure_retries_only_missing_job(self):
        dispatch = self.scheduler.dispatch_tool

        def fail_summary(name, data, **kwargs):
            if data['action'] == 'create' and data['name'].startswith('gtd-summary-'):
                return {'success': False, 'error': 'unavailable'}
            return dispatch(name, data, **kwargs)

        result = decode(tools.init_handler(fail_summary)({}))
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
