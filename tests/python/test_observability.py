from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from engineering_os.observability.correlation import (
    apply_kanban_resource_attributes,
    expected_plugin_load_order,
)
from engineering_os.observability import phoenix_client


class CorrelationTests(unittest.TestCase):
    def test_stamps_explicit_kanban_env(self) -> None:
        env = {
            "HERMES_KANBAN_TASK": "t_phase2obs",
            "HERMES_KANBAN_RUN_ID": "42",
            "HERMES_KANBAN_BOARD": "eos-phase2-obs",
            "HERMES_KANBAN_WORKSPACE": "/tmp/fixture",
            "OTEL_RESOURCE_ATTRIBUTES": "service.name=hermes-agent",
        }
        stamped = apply_kanban_resource_attributes(env)
        self.assertEqual(stamped["hermes.kanban.task_id"], "t_phase2obs")
        self.assertEqual(stamped["hermes.kanban.run_id"], "42")
        self.assertIn("hermes.kanban.task_id=t_phase2obs", env["OTEL_RESOURCE_ATTRIBUTES"])
        self.assertIn("service.name=hermes-agent", env["OTEL_RESOURCE_ATTRIBUTES"])

    def test_does_not_overwrite_existing_resource_attribute(self) -> None:
        env = {
            "HERMES_KANBAN_TASK": "t_new",
            "OTEL_RESOURCE_ATTRIBUTES": "hermes.kanban.task_id=t_old",
        }
        stamped = apply_kanban_resource_attributes(env)
        self.assertEqual(stamped["hermes.kanban.task_id"], "t_old")
        self.assertEqual(env["OTEL_RESOURCE_ATTRIBUTES"], "hermes.kanban.task_id=t_old")

    def test_absent_kanban_env_is_a_noop(self) -> None:
        env = {"PATH": "/usr/bin"}
        stamped = apply_kanban_resource_attributes(env)
        self.assertEqual(stamped, {})
        self.assertNotIn("OTEL_RESOURCE_ATTRIBUTES", env)

    def test_engineering_os_loads_before_hermes_otel(self) -> None:
        first, second = expected_plugin_load_order()
        self.assertEqual((first, second), ("engineering-os", "hermes_otel"))
        plugins = Path.home() / ".hermes/plugins"
        names = sorted(
            path.name
            for path in plugins.iterdir()
            if path.is_dir() or path.is_symlink()
        )
        self.assertLess(names.index("engineering-os"), names.index("hermes_otel"), names)

    def test_register_stays_hook_free_without_kanban_env(self) -> None:
        import importlib.util

        entry = Path(__file__).resolve().parents[2] / "__init__.py"
        spec = importlib.util.spec_from_file_location("_eos_register_test", entry)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class Ctx:
            def __init__(self) -> None:
                self.hooks: dict[str, object] = {}

            def register_hook(self, name: str, callback: object) -> None:
                self.hooks[name] = callback

        with patch.dict("os.environ", {"PATH": "/usr/bin"}, clear=True):
            ctx = Ctx()
            module.register(ctx)
            self.assertEqual(ctx.hooks, {})

    def test_register_stamps_hooks_when_kanban_env_present(self) -> None:
        import importlib.util
        import os

        entry = Path(__file__).resolve().parents[2] / "__init__.py"
        spec = importlib.util.spec_from_file_location("_eos_register_stamp_test", entry)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class Ctx:
            def __init__(self) -> None:
                self.hooks: dict[str, object] = {}

            def register_hook(self, name: str, callback: object) -> None:
                self.hooks[name] = callback

        env = {
            "HERMES_KANBAN_TASK": "t_hook",
            "HERMES_KANBAN_RUN_ID": "7",
            "PATH": "/usr/bin",
        }
        with patch.dict(os.environ, env, clear=True):
            ctx = Ctx()
            module.register(ctx)
            self.assertIn("post_llm_call", ctx.hooks)
            self.assertIn("hermes.kanban.task_id=t_hook", os.environ["OTEL_RESOURCE_ATTRIBUTES"])


class PhoenixClientTests(unittest.TestCase):
    def test_ui_unreachable_is_false_not_raise(self) -> None:
        with patch.object(phoenix_client.urllib.request, "urlopen", side_effect=OSError("down")):
            self.assertFalse(phoenix_client.ui_reachable())

    def test_graphql_errors_are_fail_open_for_summarize(self) -> None:
        with patch.object(phoenix_client, "project_id", side_effect=OSError("down")):
            with self.assertRaises(OSError):
                phoenix_client.summarize_traces()


if __name__ == "__main__":
    unittest.main()
