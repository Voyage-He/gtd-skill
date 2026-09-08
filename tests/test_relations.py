import unittest

import gtd_core as core
import materials
import tools
from tests.helpers import temp_gtd_dir, decode
from web_data import operate


class RelationTests(unittest.TestCase):
    def setUp(self):
        self.scope = temp_gtd_dir()
        self.root = self.scope.__enter__()
        core.init_gtd()

    def tearDown(self):
        self.scope.__exit__(None, None, None)

    def task(self, name):
        core.capture(name)
        return core.process_inbox(len(core.read_inbox_items()), 'next_actions')['number']

    def test_many_to_many_from_both_ends_and_independent_completion(self):
        first, second = self.task('任务一'), self.task('任务二')
        a, b = core.add_reference(title='资料甲')['reference_id'], core.add_reference(title='资料乙')['reference_id']
        core.relations(first, 'link', a)
        core.relations(a, 'link', second)
        core.relations(b, 'link', first)
        self.assertEqual(len(core.relations(first)['relations']), 2)
        self.assertEqual(len(core.relations(a)['relations']), 2)
        self.assertEqual(core.list_actions()[0]['related_references'], [a, b])
        result = decode(tools.handle_relations({'item_id': first, 'action': 'unlink', 'other_id': a}))
        self.assertTrue(result['ok'])
        self.assertEqual(core.get_reference(a)['related_items'], [second])
        core.complete_number(first)
        core.archive_completed()
        self.assertEqual(core.get_reference(b)['title'], '资料乙')
        self.assertEqual(len(core.relations(first)['relations']), 1)
        self.assertEqual(len(core.list_actions()), 1)

    def test_deletions_do_not_cascade(self):
        number = self.task('独立任务')
        ref = core.add_reference(title='独立资料')['reference_id']
        core.relations(number, 'link', ref)
        records = operate({'action': 'list'})['records']
        task = next(r for r in records if r.get('number') == number)
        operate(dict(action='delete', id=task['id'], revision=task['revision']))
        self.assertEqual(core.get_reference(ref)['title'], '独立资料')
        another = self.task('另一个任务')
        core.relations(another, 'link', ref)
        card = next(r for r in operate({'action': 'list'})['records'] if r['id'] == ref)
        operate(dict(action='delete', id=ref, revision=card['revision']))
        self.assertEqual(core.list_actions()[0]['number'], another)
        self.assertEqual(core.relations(another)['relations'], [])

    def test_reorganizing_does_not_restore_unlinked_task(self):
        ref = core.capture_message(text='请报名', title='报名资料')['reference_id']
        args = dict(reference_id=ref, expected_revision=1, title='报名资料', summary='报名', classification='actions',
                    actions=[{'key': 'register', 'content': '报名', 'evidence': [{'source': 'message:1', 'quote': '请报名'}]}])
        number = materials.organize(**args)['created'][0]
        core.relations(ref, 'unlink', number)
        materials.organize(**{**args, 'summary': '更新说明'})
        self.assertEqual(core.relations(number)['relations'], [])
        self.assertEqual(core.list_actions()[0]['reference_id'], ref)
        self.assertEqual(core.list_actions()[0]['related_references'], [])
        self.assertIn('register', core.get_reference(ref)['material_actions'])

    def test_invalid_link_is_rejected(self):
        ref = core.add_reference(title='独立资料')['reference_id']
        with self.assertRaises(core.GTDValidationError):
            core.relations(ref, 'link', 'N999')
        self.assertEqual(core.relations(ref)['relations'], [])
