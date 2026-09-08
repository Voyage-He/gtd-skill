import json
import threading
import unittest
from http.client import HTTPConnection

import gtd_core as core
from tests.helpers import temp_gtd_dir
from web_data import Conflict, operate
from web_server import Handler, ThreadingHTTPServer


class WebTests(unittest.TestCase):
    def test_bidirectional_relations_and_removal(self):
        with temp_gtd_dir():
            core.init_gtd()
            operate(dict(action='create', category='next_actions', content='准备培训'))
            task = self.items('next_actions')[0]
            card = core.add_reference(title='培训安排')
            item = self.items('materials')[0]
            update = dict(action='update', id=item['id'], revision=item['revision'],
                          title=item['title'], note='', tags='', related_items=[task['number']])
            operate(update)
            self.assertEqual(self.items('next_actions')[0]['related'][0]['id'], card['reference_id'])
            self.assertEqual(self.items('materials')[0]['related'][0]['id'], task['id'])
            self.assertEqual(core.get_reference(card['reference_id'])['related_items'], [task['number']])
            with self.assertRaises(Conflict):
                operate(update)
            item = self.items('materials')[0]
            operate({**update, 'revision': item['revision'], 'related_items': []})
            self.assertEqual(self.items('next_actions')[0]['related'], [])

    def test_source_relation_and_missing_task(self):
        core.add_reference(title='来源资料')
        card = self.items('materials')[0]
        operate(dict(action='create', category='next_actions', content='来源任务'))
        task = self.items('next_actions')[0]
        operate(dict(action='update', id=task['id'], revision=task['revision'],
                     raw=task['raw'].rstrip().replace('context:', 'reference: '+card['id']+', context:')))
        self.assertTrue(self.items('materials')[0]['related'][0]['source'])
        core.link_reference(card['id'], 'N999')
        missing = next(r for r in self.items('materials')[0]['related'] if r['number'] == 'N999')
        self.assertIsNone(missing['id'])

    def setUp(self):
        self.directory = temp_gtd_dir()
        self.root = self.directory.__enter__()
        core.init_gtd()

    def tearDown(self):
        self.directory.__exit__(None, None, None)

    def items(self, category):
        return [r for r in operate({'action': 'list'})['records'] if r['category'] == category]

    def test_crud_and_conflict(self):
        operate(dict(action='create', category='next_actions', content='买牛奶', deadline='2026-09-09'))
        item = self.items('next_actions')[0]
        operate(dict(action='update', id=item['id'], revision=item['revision'], raw=item['raw'].replace('牛奶', '面包')))
        self.assertEqual(core.list_actions()[0]['content'], '买面包')
        with self.assertRaises(Conflict):
            operate(dict(action='delete', id=item['id'], revision=item['revision']))
        item = self.items('next_actions')[0]
        operate(dict(action='complete', id=item['id'], revision=item['revision']))
        self.assertTrue(core.list_actions(show_all=True)[0]['done'])
        item = self.items('next_actions')[0]
        operate(dict(action='delete', id=item['id'], revision=item['revision']))
        self.assertEqual(self.items('next_actions'), [])
        self.assertEqual(len(list((self.root/'web-trash').glob('*.md'))), 1)

    def test_material_metadata_and_source_preserved(self):
        card = core.capture_message(text='通知原文', title='通知', tags=['培训'])
        item = self.items('materials')[0]
        operate(dict(action='update', id=item['id'], revision=item['revision'], title='培训通知', note='我的备注', tags='学习, 培训'))
        updated = core.get_reference(card['reference_id'])
        self.assertEqual(updated['message_text'], '通知原文')
        self.assertEqual(updated['note'], '我的备注')
        self.assertEqual(core.search_references('培训通知')['count'], 1)
        item = self.items('materials')[0]
        operate(dict(action='delete', id=item['id'], revision=item['revision']))
        self.assertEqual(self.items('materials'), [])
        self.assertEqual(core.search_references('培训通知')['count'], 0)
        new_card = core.add_reference(title='新资料')
        self.assertNotEqual(new_card['reference_id'], card['reference_id'])

    def test_capture_process_and_invalid_update(self):
        operate(dict(action='create', category='inbox', content='安排培训'))
        item = self.items('inbox')[0]
        operate(dict(action='process', id=item['id'], revision=item['revision'], target='projects'))
        self.assertEqual(len(self.items('projects')), 1)
        self.assertEqual(len(self.items('next_actions')), 1)
        item = self.items('next_actions')[0]
        with self.assertRaises(core.GTDValidationError):
            operate(dict(action='update', id=item['id'], revision=item['revision'], raw='- [ ] N999: 错误编号'))
        self.assertEqual(len(core.list_actions()), 1)

    def test_http_origin_and_routes(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = HTTPConnection('127.0.0.1', server.server_port)
            conn.request('GET', '/')
            response = conn.getresponse()
            self.assertEqual(response.status, 200)
            self.assertIn('工作台', response.read().decode())
            conn.request('POST', '/api/records', json.dumps(dict(action='create', category='inbox', content='网页任务')), {'Content-Type':'application/json'})
            response = conn.getresponse(); self.assertEqual(response.status, 200); response.read()
            conn.request('POST', '/api/records', '{}', {'Content-Type':'application/json', 'Origin':'https://evil.example'})
            response = conn.getresponse(); self.assertEqual(response.status, 403); response.read()
            conn.request('GET', '/api/records', headers={'Host':'evil.example'})
            response = conn.getresponse(); self.assertEqual(response.status, 403); response.read()
            self.assertEqual(len(core.read_inbox_items()), 1)
            conn.close()
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_process_into_materials(self):
        core.capture('保留这份培训说明')
        item = self.items('inbox')[0]
        operate(dict(action='process', id=item['id'], revision=item['revision'], target='materials'))
        self.assertEqual(self.items('inbox'), [])
        card = self.items('materials')[0]['card']
        self.assertEqual(card['note'], '保留这份培训说明')
        self.assertEqual(core.search_references('培训说明')['count'], 1)
        core.write_text(core.gtd_path('reference.md'), '- 历史资料\n')
        self.assertEqual(self.items('reference'), [])
        self.assertEqual(core.read_text(core.gtd_path('reference.md')), '- 历史资料\n')
