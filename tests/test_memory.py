import unittest
import gtd_core as core
import tools
from tests.helpers import temp_gtd_dir, decode
from web_data import operate, Conflict


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.scope = temp_gtd_dir()
        self.scope.__enter__()
        core.init_gtd()

    def tearDown(self):
        self.scope.__exit__(None, None, None)

    def test_tool_recall_revision_and_restore(self):
        result = decode(tools.handle_memory(dict(action='add', content='楼下的奶茶价格一般是10元', tags=['奶茶', '价格'])))
        self.assertTrue(result['ok'])
        item = result['memory']
        self.assertEqual(core.memory(query='奶茶')['memories'][0]['content'], '楼下的奶茶价格一般是10元')
        revised = core.memory('update', memory_id=item['memory_id'], expected_revision=1, content='楼下的奶茶价格一般是12元')['memory']
        self.assertEqual(revised['history'][0]['content'], item['content'])
        with self.assertRaises(core.GTDValidationError):
            core.memory('update', memory_id=item['memory_id'], expected_revision=1, content='过时数据')
        core.memory('delete', memory_id=item['memory_id'], expected_revision=2)
        self.assertEqual(core.memory(query='奶茶')['count'], 0)
        core.memory('restore', memory_id=item['memory_id'], expected_revision=3)
        self.assertEqual(core.memory(query='奶茶')['memories'][0]['content'], '楼下的奶茶价格一般是12元')
        self.assertEqual(core.list_actions(), [])
        self.assertEqual(core.read_inbox_items(), [])

    def test_web_crud_shares_core_and_conflicts(self):
        operate(dict(action='create', category='memories', content='办公室一般放着10本书', tags='办公室, 书'))
        item = next(i for i in operate({'action':'list'})['records'] if i['category']=='memories')
        core.memory('update', memory_id=item['id'], expected_revision=1, content='办公室一般放着12本书')
        with self.assertRaises(Conflict):
            operate(dict(action='update', id=item['id'], revision=item['revision'], content='旧内容'))
        item = next(i for i in operate({'action':'list'})['records'] if i['category']=='memories')
        operate(dict(action='update', id=item['id'], revision=item['revision'], content='办公室一般放着15本书'))
        self.assertEqual(core.memory(query='办公室')['memories'][0]['content'], '办公室一般放着15本书')
        item = next(i for i in operate({'action':'list'})['records'] if i['category']=='memories')
        operate(dict(action='delete', id=item['id'], revision=item['revision']))
        self.assertEqual(core.memory()['count'], 0)
        self.assertTrue(core.memory('get', memory_id=item['id'])['memory']['deleted'])

    def test_process_inbox_to_memory(self):
        core.capture('楼下的奶茶价格一般是10元')
        item = next(i for i in operate({'action':'list'})['records'] if i['category']=='inbox')
        operate(dict(action='process', id=item['id'], revision=item['revision'], target='memories'))
        self.assertEqual(core.memory()['count'], 1)
        self.assertEqual(core.read_inbox_items(), [])
        self.assertEqual(core.list_actions(), [])
