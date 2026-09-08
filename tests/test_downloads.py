import threading
import unittest
from http.client import HTTPConnection
from urllib.parse import quote

import gtd_core as core
from tests.helpers import temp_gtd_dir
from web_data import operate
from web_server import Handler, ThreadingHTTPServer


class DownloadTests(unittest.TestCase):
    def test_original_bytes_names_multi_attachment_and_access_boundaries(self):
        with temp_gtd_dir() as root:
            core.init_gtd()
            first, second = root/'培训安排.txt', root/'image.bin'
            first.write_text('中文原文件\n', encoding='utf-8')
            second.write_bytes(bytes(range(256))*600)
            card = core.capture_message(title='多附件', file_paths=[str(first), str(second)])
            single = core.add_reference(title='旧单附件', file_path=str(first), managed='link')
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = HTTPConnection('127.0.0.1', server.server_port)
                def get(path, headers=None):
                    conn.request('GET', path, headers=headers or {})
                    response = conn.getresponse()
                    return response.status, dict(response.getheaders()), response.read()
                base = '/api/files/'+card['reference_id']
                status, headers, body = get(base+'/1')
                self.assertEqual(status, 200)
                self.assertEqual(body, first.read_bytes())
                self.assertIn(quote(first.name), headers['Content-Disposition'])
                self.assertEqual(headers['Content-Type'], 'application/octet-stream')
                self.assertEqual(get(base+'/2')[2], second.read_bytes())
                self.assertEqual(get('/api/files/'+single['reference_id']+'/1')[2], first.read_bytes())
                self.assertEqual(get(base+'/3')[0], 404)
                self.assertEqual(get('/api/files/../../etc/passwd/1')[0], 404)
                self.assertEqual(get(base+'/1', {'Origin':'https://example.com'})[0], 403)
                self.assertEqual(get(base+'/1', {'Host':'example.com'})[0], 403)
                self.assertEqual(get('/api/files/R20000101-999/1')[0], 404)
                # Managed copies are still downloadable after source removal.
                first.unlink()
                self.assertEqual(get(base+'/1')[0], 200)
                self.assertEqual(get('/api/files/'+single['reference_id']+'/1')[0], 404)
                from pathlib import Path
                Path(card['attachments'][0]['path']).unlink()
                self.assertEqual(get(base+'/1')[0], 404)
                item = next(i for i in operate({'action':'list'})['records'] if i['id']==card['reference_id'])
                self.assertFalse(item['downloads'][0]['available'])
                self.assertTrue(item['downloads'][1]['available'])
                # Registered copied files cannot be redirected outside assets.
                data = core.get_reference(card['reference_id'])
                data['attachments'][1]['path'] = str(second)
                core.write_reference_card(data)
                self.assertEqual(get(base+'/2')[0], 403)
                conn.close()
            finally:
                server.shutdown(); server.server_close(); thread.join()
