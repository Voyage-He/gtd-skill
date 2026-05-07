from __future__ import annotations

import json
import unittest
from datetime import timedelta

import gtd_core
import tools
from tests.helpers import decode, temp_gtd_dir


class GTDDataReliabilityTests(unittest.TestCase):
    def test_init_is_idempotent_and_stats_start_empty(self):
        with temp_gtd_dir() as gtd_dir:
            first = decode(tools.handle_init({}))
            second = decode(tools.handle_init({}))
            waiting = (gtd_dir / "waiting_for.md").read_text(encoding="utf-8")
            stats = decode(tools.handle_stats({}))

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertNotIn("W001", waiting)
        self.assertEqual(stats["waiting"], 0)
        self.assertEqual(stats["pending_actions"], 0)

    def test_gtd_dir_is_resolved_per_call(self):
        with temp_gtd_dir() as first_dir:
            decode(tools.handle_init({}))
            decode(tools.handle_capture({"content": "first"}))

            with temp_gtd_dir() as second_dir:
                decode(tools.handle_init({}))
                decode(tools.handle_capture({"content": "second"}))

                self.assertIn("first", (first_dir / "inbox.md").read_text(encoding="utf-8"))
                self.assertNotIn("second", (first_dir / "inbox.md").read_text(encoding="utf-8"))
                self.assertIn("second", (second_dir / "inbox.md").read_text(encoding="utf-8"))

    def test_duplicate_inbox_entries_only_remove_selected_line(self):
        with temp_gtd_dir() as gtd_dir:
            decode(tools.handle_init({}))
            duplicate = "- [ ] 同一条目 (added: 2026-05-06 10:00)\n"
            (gtd_dir / "inbox.md").write_text(
                "# 收集箱\n\n## 2026-05-06\n\n" + duplicate + duplicate,
                encoding="utf-8",
            )

            result = decode(
                tools.handle_inbox_process(
                    {"index": 1, "target": "next_actions", "context": "@电脑", "deadline": "2026-05-07"}
                )
            )
            inbox = (gtd_dir / "inbox.md").read_text(encoding="utf-8")
            actions = (gtd_dir / "next_actions.md").read_text(encoding="utf-8")

        self.assertTrue(result["ok"])
        self.assertEqual(inbox.count("同一条目"), 1)
        self.assertEqual(actions.count("同一条目"), 1)

    def test_invalid_inbox_index_preserves_files(self):
        with temp_gtd_dir() as gtd_dir:
            decode(tools.handle_init({}))
            decode(tools.handle_capture({"content": "保留我"}))
            before = {path.name: path.read_text(encoding="utf-8") for path in gtd_dir.glob("*.md")}

            result = decode(tools.handle_inbox_process({"index": 99, "target": "trash"}))
            after = {path.name: path.read_text(encoding="utf-8") for path in gtd_dir.glob("*.md")}

        self.assertFalse(result["ok"])
        self.assertEqual(before, after)

    def test_inbox_targets_return_structured_results(self):
        targets = [
            "trash",
            "reference",
            "someday_maybe",
            "done",
            "next_actions",
            "waiting_for",
            "projects",
        ]
        with temp_gtd_dir():
            decode(tools.handle_init({}))
            for target in targets:
                with self.subTest(target=target):
                    decode(tools.handle_capture({"content": f"item {target}"}))
                    args = {
                        "index": 1,
                        "target": target,
                        "context": "@电脑",
                        "deadline": "2026-05-07",
                        "delegate": "张三",
                        "estimated": "2026-05-08",
                        "project_name": "测试项目",
                        "first_action": "写第一步",
                    }
                    result = decode(tools.handle_inbox_process(args))
                    self.assertTrue(result["ok"])
                    self.assertEqual(result["action"], target)
                    self.assertIn("content", result)

    def test_complete_project_marks_status_and_stats_exclude_it(self):
        with temp_gtd_dir() as gtd_dir:
            decode(tools.handle_init({}))
            decode(tools.handle_capture({"content": "发布 Hermes 版本"}))
            project = decode(
                tools.handle_inbox_process(
                    {
                        "index": 1,
                        "target": "projects",
                        "project_name": "发布 Hermes 版本",
                        "first_action": "跑测试",
                    }
                )
            )
            complete = decode(tools.handle_complete({"number": project["project_number"]}))
            stats = decode(tools.handle_stats({}))
            projects = (gtd_dir / "projects.md").read_text(encoding="utf-8")

        self.assertTrue(complete["ok"])
        self.assertIn("- **状态**: 已完成", projects)
        self.assertIn("- **完成日期**:", projects)
        self.assertEqual(stats["active_projects"], 0)

    def test_archive_only_completed_items_and_preserves_notes(self):
        with temp_gtd_dir() as gtd_dir:
            decode(tools.handle_init({}))
            (gtd_dir / "next_actions.md").write_text(
                "# 下一步行动\n\n"
                "## @电脑\n\n"
                "保留备注\n"
                "- [x] N001: 已完成 (completed: 2026-05-06)\n"
                "- [ ] N002: 未完成 (context: @电脑)\n",
                encoding="utf-8",
            )

            result = decode(tools.handle_archive({}))
            actions = (gtd_dir / "next_actions.md").read_text(encoding="utf-8")
            archive_files = list((gtd_dir / "archive").rglob("*.md"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["archived_count"], 1)
        self.assertNotIn("N001", actions)
        self.assertIn("N002", actions)
        self.assertIn("保留备注", actions)
        self.assertTrue(archive_files)

    def test_date_boundaries_for_stats_and_weekly_review(self):
        today = gtd_core.local_date()
        monday = today - timedelta(days=today.weekday())
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        with temp_gtd_dir() as gtd_dir:
            decode(tools.handle_init({}))
            (gtd_dir / "inbox.md").write_text(
                f"# 收集箱\n\n## {monday}\n\n- [ ] 本周新增 (added: {monday} 08:00)\n",
                encoding="utf-8",
            )
            (gtd_dir / "next_actions.md").write_text(
                "# 下一步行动\n\n"
                f"- [ ] N001: 今天截止 (deadline: {today})\n"
                f"- [ ] N002: 昨天截止 (deadline: {yesterday})\n"
                f"- [ ] N003: 明天截止 (deadline: {tomorrow})\n",
                encoding="utf-8",
            )

            stats = decode(tools.handle_stats({}))
            review = decode(tools.handle_weekly_review({}))
            overdue_text = json.dumps(review["overdue"], ensure_ascii=False)

        self.assertEqual(stats["new_items_this_week"], 1)
        self.assertIn("昨天截止", overdue_text)
        self.assertNotIn("今天截止", overdue_text)
        self.assertNotIn("明天截止", overdue_text)

    def test_reference_init_and_add_memo_link_file_preserves_existing_data(self):
        with temp_gtd_dir() as gtd_dir:
            decode(tools.handle_init({}))
            (gtd_dir / "next_actions.md").write_text("keep action\n", encoding="utf-8")
            memo = decode(
                tools.handle_reference_add(
                    {
                        "title": "客户A付款条款",
                        "note": "客户A周五前确认付款条款",
                        "tags": ["客户A", "付款"],
                        "related_items": "P003",
                    }
                )
            )
            link = decode(
                tools.handle_reference_add(
                    {"title": "GTD 官网", "url": "https://gettingthingsdone.com/", "source": "web"}
                )
            )
            attachment_path = gtd_dir / "客户A 二期合同评审表.txt"
            attachment_path.write_text("付款条款：月结 30 天", encoding="utf-8")
            file_ref = decode(
                tools.handle_reference_add(
                    {
                        "title": "客户A 二期合同评审表",
                        "file_path": str(attachment_path),
                        "source": "张三",
                        "tags": "客户A,合同",
                    }
                )
            )
            decode(tools.handle_init({}))

            references = gtd_dir / "references"
            cards = list((references / "cards").glob("R*.md"))
            actions = (gtd_dir / "next_actions.md").read_text(encoding="utf-8")
            has_cards_dir = (references / "cards").is_dir()
            has_assets_dir = (references / "assets").is_dir()
            has_cache_dir = (references / "cache").is_dir()
            has_index = (references / "index.jsonl").exists()

        self.assertTrue(memo["ok"])
        self.assertTrue(link["ok"])
        self.assertTrue(file_ref["ok"])
        self.assertTrue(has_cards_dir)
        self.assertTrue(has_assets_dir)
        self.assertTrue(has_cache_dir)
        self.assertTrue(has_index)
        self.assertEqual(len(cards), 3)
        self.assertEqual(actions, "keep action\n")

    def test_reference_attachment_link_copy_and_missing_path(self):
        with temp_gtd_dir() as gtd_dir:
            decode(tools.handle_init({}))
            source_file = gtd_dir / "source.txt"
            source_file.write_text("hello", encoding="utf-8")

            linked = decode(
                tools.handle_reference_add(
                    {"title": "链接附件", "file_path": str(source_file), "managed": "link", "source": "张三"}
                )
            )
            copied = decode(
                tools.handle_reference_add(
                    {
                        "title": "复制附件",
                        "purpose": "归档",
                        "file_path": str(source_file),
                        "managed": "copy",
                        "source": "李四",
                    }
                )
            )
            missing = decode(tools.handle_reference_add({"title": "丢失附件", "file_path": str(gtd_dir / "missing.txt")}))
            has_asset_month_dir = (
                gtd_dir / "references" / "assets" / gtd_core.today_str()[:4] / gtd_core.today_str()[5:7]
            ).exists()

        self.assertTrue(linked["ok"])
        self.assertEqual(linked["attachment"]["path"], str(source_file.resolve()))
        self.assertEqual(linked["attachment"]["managed"], "link")
        self.assertTrue(copied["ok"])
        self.assertEqual(copied["attachment"]["managed"], "copy")
        self.assertIn("/references/assets/", copied["attachment"]["path"])
        self.assertTrue(copied["attachment"]["name"].startswith(copied["reference_id"]))
        self.assertIn("复制附件_归档", copied["suggested_name"])
        self.assertIn("__李四__v1", copied["suggested_name"])
        self.assertTrue(has_asset_month_dir)
        self.assertFalse(missing["ok"])
        self.assertIn("附件不存在", missing["message"])

    def test_reference_search_is_metadata_only_and_supports_fields(self):
        with temp_gtd_dir() as gtd_dir:
            decode(tools.handle_init({}))
            binary_file = gtd_dir / "binary.bin"
            binary_file.write_bytes(b"\xff\xfe\x00\x00")
            added = decode(
                tools.handle_reference_add(
                    {
                        "title": "客户A 二期合同",
                        "file_path": str(binary_file),
                        "tags": ["合同"],
                        "aliases": ["评审表"],
                        "people": ["张三"],
                        "project": "P003",
                        "related_items": ["P003"],
                        "purpose": "评审",
                        "note": "付款条款待确认",
                    }
                )
            )
            by_title = decode(tools.handle_reference_search({"query": "客户A"}))
            by_alias = decode(tools.handle_reference_search({"query": "评审表"}))
            by_related = decode(tools.handle_reference_search({"related_item": "P003"}))
            by_date = decode(tools.handle_reference_search({"query": added["captured_at"][:10]}))
            by_purpose = decode(tools.handle_reference_search({"query": "评审"}))

        self.assertTrue(added["ok"])
        self.assertTrue(by_title["ok"])
        self.assertTrue(by_title["metadata_only"])
        self.assertEqual(by_title["count"], 1)
        self.assertIn("title", by_title["results"][0]["match_fields"])
        self.assertEqual(by_alias["count"], 1)
        self.assertEqual(by_related["count"], 1)
        self.assertEqual(by_date["count"], 1)
        self.assertIn("captured_at", by_date["results"][0]["match_fields"])
        self.assertEqual(by_purpose["count"], 1)
        self.assertIn("purpose", by_purpose["results"][0]["match_fields"])

    def test_reference_index_rebuilds_when_missing_before_upsert(self):
        with temp_gtd_dir() as gtd_dir:
            decode(tools.handle_init({}))
            first = decode(tools.handle_reference_add({"title": "旧资料", "note": "alpha"}))
            decode(tools.handle_reference_add({"title": "第二条", "note": "beta"}))
            (gtd_dir / "references" / "index.jsonl").unlink()

            third = decode(tools.handle_reference_add({"title": "新资料", "note": "gamma"}))
            by_first = decode(tools.handle_reference_search({"query": "旧资料"}))
            by_third = decode(tools.handle_reference_search({"query": "新资料"}))

        self.assertTrue(first["ok"])
        self.assertTrue(third["ok"])
        self.assertEqual(by_first["count"], 1)
        self.assertEqual(by_first["results"][0]["reference_id"], first["reference_id"])
        self.assertEqual(by_third["count"], 1)
        self.assertEqual(by_third["results"][0]["reference_id"], third["reference_id"])

    def test_reference_index_rebuilds_when_corrupted(self):
        with temp_gtd_dir() as gtd_dir:
            decode(tools.handle_init({}))
            first = decode(tools.handle_reference_add({"title": "第一条", "note": "alpha"}))
            second = decode(tools.handle_reference_add({"title": "第二条", "note": "beta"}))
            index_path = gtd_dir / "references" / "index.jsonl"
            valid_second_line = index_path.read_text(encoding="utf-8").splitlines()[1]
            index_path.write_text("{bad json}\n" + valid_second_line + "\n", encoding="utf-8")

            by_first = decode(tools.handle_reference_search({"query": "alpha"}))
            by_second = decode(tools.handle_reference_search({"query": "beta"}))

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(by_first["count"], 1)
        self.assertEqual(by_first["results"][0]["reference_id"], first["reference_id"])
        self.assertEqual(by_second["count"], 1)
        self.assertEqual(by_second["results"][0]["reference_id"], second["reference_id"])

    def test_reference_link_validation_and_explicit_read(self):
        with temp_gtd_dir() as gtd_dir:
            decode(tools.handle_init({}))
            text_file = gtd_dir / "readme.txt"
            text_file.write_text("0123456789", encoding="utf-8")
            added = decode(tools.handle_reference_add({"title": "可读附件", "file_path": str(text_file)}))

            linked = decode(
                tools.handle_reference_link({"reference_id": added["reference_id"], "related_item": "N001"})
            )
            before = (gtd_dir / "references" / "cards" / f"{added['reference_id']}.md").read_text(encoding="utf-8")
            invalid = decode(
                tools.handle_reference_link({"reference_id": added["reference_id"], "related_item": "X999"})
            )
            after = (gtd_dir / "references" / "cards" / f"{added['reference_id']}.md").read_text(encoding="utf-8")
            read = decode(tools.handle_reference_read({"reference_id": added["reference_id"], "max_chars": 4}))
            memo = decode(tools.handle_reference_add({"title": "可读备忘", "note": "abcdef"}))
            memo_read = decode(tools.handle_reference_read({"reference_id": memo["reference_id"], "max_chars": 3}))

        self.assertTrue(linked["ok"])
        self.assertIn("N001", linked["related_items"])
        self.assertFalse(invalid["ok"])
        self.assertEqual(before, after)
        self.assertTrue(read["ok"])
        self.assertEqual(read["content"], "0123")
        self.assertTrue(read["truncated"])
        self.assertEqual(read["range"], {"unit": "chars", "start": 0, "end": 4, "total": 10})
        self.assertEqual(read["read_chars"], 4)
        self.assertTrue(memo_read["ok"])
        self.assertEqual(memo_read["content"], "abc")
        self.assertEqual(memo_read["range"], {"unit": "chars", "start": 0, "end": 3, "total": 6})
        self.assertTrue(memo_read["truncated"])


if __name__ == "__main__":
    unittest.main()
