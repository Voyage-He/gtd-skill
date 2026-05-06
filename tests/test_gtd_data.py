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


if __name__ == "__main__":
    unittest.main()
