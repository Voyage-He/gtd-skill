from __future__ import annotations
import unittest
from unittest.mock import patch
import gtd_core as core
import materials
import tools
from tests.helpers import temp_gtd_dir, decode


class MaterialsTests(unittest.TestCase):
    def test_mixed_batch_becomes_project_and_searchable_reference(self):
        with temp_gtd_dir() as root:
            doc = root / 'a71.pdf'; doc.write_bytes(b'pdf')
            video = root / 'cf9.mp4'; video.write_bytes(b'video')
            notice = core.capture_message(text='请在2026-09-20前报名培训，然后完成学习。',
                                          file_paths=[str(doc), str(video)], channel='qqbot', chat_id='me')
            ref = notice['reference_id']
            first = materials.analyze_attachment(reference_id=ref, attachment_index=1, expected_revision=1,
                status='complete', method='test document extraction', text='平台使用方法：使用校园账号登录。',
                summary='校园平台操作教程', keywords=['校园账号'])
            materials.analyze_attachment(reference_id=ref, attachment_index=2, expected_revision=first['revision'],
                status='partial', method='test transcript', text='演示报名后的在线学习流程',
                summary='在线学习演示', locator='00:00-00:30，未分析其余画面')
            args = dict(reference_id=ref, expected_revision=3, title='培训报名及学习', summary='报名后在校园平台学习。视频仅分析开头。',
                        classification='project', keywords=['教师培训'], actions=[{
                            'key': 'register', 'content': '报名培训', 'deadline': '2026-09-20',
                            'evidence': [{'source': 'message:1', 'quote': '请在2026-09-20前报名培训'}]}])
            result = materials.organize(**args)
            self.assertEqual(result['created'], ['N001'])
            self.assertEqual(result['project_number'], 'P001')
            self.assertEqual(result['coverage']['status'], 'partial')
            self.assertTrue(materials.organize(**args)['duplicate'])
            self.assertEqual(len(core.list_actions()), 1)
            self.assertEqual(core.list_actions()[0]['deadline'], '2026-09-20')
            self.assertEqual(core.list_actions()[0]['reference_id'], ref)
            self.assertEqual(core.search_references('校园账号')['results'][0]['reference_id'], ref)
            self.assertEqual(core.search_references('在线学习演示')['count'], 1)
            card = core.get_reference(ref)
            self.assertIn('N001', card['related_items']); self.assertIn('P001', card['related_items'])
            self.assertIn('请在', card['message_text'])
            self.assertEqual(len(core.reference_files(ref)['files']), 2)

    def test_followup_invalidates_revision_and_reuses_actions(self):
        with temp_gtd_dir():
            data = core.capture_message(text='请提交申请')
            ref = data['reference_id']
            args = dict(reference_id=ref, expected_revision=1, title='申请', summary='提交申请', classification='actions',
                        actions=[{'key': 'submit', 'content': '提交申请', 'evidence': [{'source': 'message:1', 'quote': '请提交申请'}]}])
            materials.organize(**args)
            core.capture_message(reference_id=ref, text='教程供参考')
            self.assertRaises(core.GTDValidationError, materials.organize, **args)
            args['expected_revision'] = 2
            self.assertEqual(materials.organize(**args)['created'], [])
            self.assertEqual(len(core.list_actions()), 1)

    def test_reference_and_ambiguity_do_not_create_tasks(self):
        with temp_gtd_dir():
            data = core.capture_message(text='教程第一步：打开软件。')
            for classification in ['reference', 'needs_clarification']:
                result = materials.organize(reference_id=data['reference_id'], expected_revision=1,
                    title='软件教程', summary='供以后使用', classification=classification,
                    questions=['是否准备现在学习？'] if classification == 'needs_clarification' else [])
                self.assertEqual(result['action_numbers'], [])
            self.assertEqual(core.list_actions(), [])

    def test_unknown_evidence_and_write_failure_are_atomic(self):
        with temp_gtd_dir() as root:
            data = core.capture_message(text='需要报名')
            args = dict(reference_id=data['reference_id'], expected_revision=1, title='报名', summary='报名',
                        classification='project', actions=[{'key': 'apply', 'content': '报名',
                        'evidence': [{'source': 'attachment:9', 'quote': '虚构内容'}]}])
            self.assertRaises(core.GTDValidationError, materials.organize, **args)
            self.assertFalse((root / 'next_actions.md').exists())
            args['actions'][0]['evidence'] = [{'source': 'message:1', 'quote': '需要报名'}]
            original = core._append_target
            def fail_project(filename, text):
                if filename == 'projects.md': raise OSError('disk error')
                original(filename, text)
            with patch.object(core, '_append_target', side_effect=fail_project):
                self.assertRaises(OSError, materials.organize, **args)
            self.assertEqual(core.list_actions(), [])
            self.assertNotIn('material_actions', core.get_reference(data['reference_id']))

    def test_candidates_scoped_to_chat_and_failed_video_visible(self):
        with temp_gtd_dir() as root:
            video = root / 'video.mp4'; video.write_bytes(b'video')
            first = core.capture_message(file_paths=[str(video)], channel='weixin', chat_id='a')
            core.capture_message(text='别人的事情', channel='weixin', chat_id='b')
            candidates = materials.context(channel='weixin', chat_id='a')['candidates']
            self.assertEqual([c['reference_id'] for c in candidates], [first['reference_id']])
            result = decode(tools.handle_materials_analyze(dict(reference_id=first['reference_id'],
                attachment_index=1, expected_revision=1, status='failed', method='video', error='无转写工具')))
            self.assertTrue(result['ok'], result)
            context = materials.context(reference_id=first['reference_id'])
            self.assertEqual(context['files'][0]['analysis']['error'], '无转写工具')
            self.assertEqual(context['coverage']['attachments'], {'1': 'failed'})
            self.assertTrue(context['files'][0]['exists'])

    def test_analysis_results_are_searchable_and_replace_old_text(self):
        with temp_gtd_dir() as root:
            path = root / 'random.png'; path.write_bytes(b'image')
            data = core.capture_message(file_paths=[str(path)])
            ref = data['reference_id']
            materials.analyze_attachment(reference_id=ref, attachment_index=1, expected_revision=1,
                status='complete', method='OCR', text='错误词')
            materials.analyze_attachment(reference_id=ref, attachment_index=1, expected_revision=2,
                status='complete', method='corrected OCR', text='活动地点在礼堂')
            self.assertEqual(core.search_references('错误词')['count'], 0)
            self.assertEqual(core.search_references('礼堂')['count'], 1)
            self.assertEqual(core.search_references('礼堂')['results'][0]['matched_attachment_indices'], [1])
