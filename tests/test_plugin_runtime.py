from __future__ import annotations

import importlib.util
import inspect
import json
import unittest
from pathlib import Path

import schemas
import tools
from tests.helpers import decode, temp_gtd_dir


ROOT = Path(__file__).resolve().parents[1]


class FakeHermesContext:
    def __init__(self) -> None:
        self.tools: list[dict] = []
        self.skills: list[tuple[str, str]] = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)

    def register_skill(self, name, path):
        self.skills.append((name, path))


def load_plugin_module():
    spec = importlib.util.spec_from_file_location("gtd_plugin_runtime", ROOT / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PluginRuntimeTests(unittest.TestCase):
    def test_registers_all_tools_and_skill(self):
        ctx = FakeHermesContext()
        load_plugin_module().register(ctx)

        schema_names = [schema["name"] for schema in schemas.ALL_SCHEMAS]
        self.assertEqual(len(ctx.tools), 13)
        self.assertEqual([tool["name"] for tool in ctx.tools], schema_names)
        self.assertTrue(all(tool["toolset"] == "gtd" for tool in ctx.tools))
        self.assertTrue(all(tool["schema"]["name"] in tools.HANDLERS for tool in ctx.tools))
        self.assertTrue(all(callable(tool["handler"]) for tool in ctx.tools))
        self.assertTrue(all(tool["description"] for tool in ctx.tools))

        self.assertEqual(len(ctx.skills), 1)
        skill_name, skill_path = ctx.skills[0]
        self.assertEqual(skill_name, "gtd")
        self.assertNotIn(".claude", skill_path)
        self.assertTrue(Path(skill_path).exists())

    def test_schema_names_match_handlers(self):
        for schema in schemas.ALL_SCHEMAS:
            with self.subTest(schema=schema["name"]):
                self.assertIn(schema["name"], tools.HANDLERS)
                self.assertEqual(schema["parameters"]["type"], "object")

    def test_handlers_accept_kwargs_and_return_json_on_missing_args(self):
        for name, handler in tools.HANDLERS.items():
            with self.subTest(handler=name), temp_gtd_dir():
                signature = inspect.signature(handler)
                self.assertIn("args", signature.parameters)
                self.assertTrue(
                    any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values())
                )
                result = handler({}, task_id="future-context")
                decoded = json.loads(result)
                self.assertIn("ok", decoded)
                self.assertIn("message", decoded)

    def test_missing_required_argument_is_structured_error(self):
        with temp_gtd_dir():
            result = decode(tools.handle_capture({}, task_id="x"))

        self.assertFalse(result["ok"])
        self.assertIn("content", result["message"])
        self.assertEqual(result["error"]["type"], "GTDValidationError")

    def test_invalid_enum_does_not_modify_files(self):
        with temp_gtd_dir() as gtd_dir:
            decode(tools.handle_init({}))
            decode(tools.handle_capture({"content": "重复测试"}))
            before = (gtd_dir / "inbox.md").read_text(encoding="utf-8")
            result = decode(tools.handle_inbox_process({"index": 1, "target": "invalid"}))
            after = (gtd_dir / "inbox.md").read_text(encoding="utf-8")

        self.assertFalse(result["ok"])
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
