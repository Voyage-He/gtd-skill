from __future__ import annotations

import unittest

import gtd_core as core
import gtd_policy as policy
import gtd_response as response
from tests.helpers import temp_gtd_dir
from tests.test_plugin_runtime import FakeHermesContext, load_plugin_module


class PolicyTests(unittest.TestCase):
    def test_old_runtime_gets_policy_without_skill_selection(self):
        ctx = FakeHermesContext()
        load_plugin_module().register(ctx)
        name, callback = ctx.hooks[0]
        self.assertEqual(name, 'pre_llm_call')
        for message in ('提醒我洗衣服', '旧任务：今天要洗衣服了', '已经完成了'):
            self.assertEqual(callback(user_message=message, platform='cron')['context'],
                             policy.RESPONSE_POLICY)

    def test_modern_runtime_registers_one_bounded_static_section(self):
        ctx = FakeHermesContext()
        sections = []
        ctx.register_system_prompt_section = lambda *a, **kw: sections.append((a, kw))
        load_plugin_module().register(ctx)
        self.assertEqual(ctx.hooks, [])
        args, kwargs = sections[0]
        self.assertEqual(args, ('gtd.response-policy', policy.RESPONSE_POLICY))
        self.assertLessEqual(len(args[1]), kwargs['max_chars'])

    def test_unsupported_runtime_does_not_silently_skip_policy(self):
        ctx = FakeHermesContext()
        ctx.register_hook = None
        with self.assertRaisesRegex(RuntimeError, 'upgrade Hermes'):
            load_plugin_module().register(ctx)
        self.assertEqual(ctx.tools, [])

    def test_review_reads_live_config_without_rewriting_legacy_config(self):
        with temp_gtd_dir():
            core.save_config({'user_name': '测试', 'notifications': {'daily_digest': False}})
            path = core.get_config_path()
            original = path.read_bytes()
            first = response.review({}, None)
            self.assertFalse(first['config']['notifications']['daily_digest'])
            self.assertEqual(first['config']['response']['verbosity'], 'concise')
            self.assertEqual(path.read_bytes(), original)
            core.set_config('response.verbosity', 'detailed')
            core.set_config('response.silent_when_unchanged', False)
            second = response.review({}, None)
            self.assertEqual(second['config']['response'],
                             {'verbosity': 'detailed', 'silent_when_unchanged': False})

    def test_invalid_response_preferences_do_not_overwrite_config(self):
        with temp_gtd_dir():
            core.save_config({'user_name': '测试'})
            path = core.get_config_path()
            original = path.read_bytes()
            for key, value in [('response.verbosity', 'verbose'),
                               ('response.silent_when_unchanged', 'sometimes'),
                               ('response', 'bad')]:
                with self.assertRaises(core.GTDValidationError):
                    core.set_config(key, value)
            self.assertEqual(path.read_bytes(), original)

    def test_config_read_failure_is_not_a_default_success(self):
        with temp_gtd_dir():
            core.save_config({'user_name': '测试'})
            core.get_config_path().write_text('[]')
            with self.assertRaises(core.GTDValidationError):
                response.review({}, None)
