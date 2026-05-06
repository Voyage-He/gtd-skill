from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_hermes_skill_is_tool_first(self):
        skill = (ROOT / "skills" / "gtd" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("gtd_capture", skill)
        self.assertIn("gtd_inbox_process", skill)
        self.assertNotIn(".claude", skill)
        self.assertNotIn("python scripts", skill.lower())

    def test_readme_is_hermes_first_and_lists_tools(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for tool in [
            "gtd_init",
            "gtd_capture",
            "gtd_inbox",
            "gtd_inbox_process",
            "gtd_next_number",
            "gtd_list_actions",
            "gtd_complete",
            "gtd_archive",
            "gtd_daily_check",
            "gtd_weekly_review",
            "gtd_stats",
            "gtd_config_get",
            "gtd_config_set",
        ]:
            with self.subTest(tool=tool):
                self.assertIn(tool, readme)

        self.assertIn("~/.hermes/plugins/gtd", readme)
        self.assertIn("HERMES_ENABLE_PROJECT_PLUGINS=true", readme)
        self.assertIn("ok: false", readme)


if __name__ == "__main__":
    unittest.main()
