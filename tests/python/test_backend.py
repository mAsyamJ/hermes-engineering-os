from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load_backend():
    entry = ROOT / "dashboard/plugin_api.py"
    spec = importlib.util.spec_from_file_location("_engineering_os_api_test", entry)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.api = load_backend()

    def test_all_plugin_routes_are_get_only(self) -> None:
        routes = [route for route in self.api.router.routes if hasattr(route, "methods")]
        self.assertGreaterEqual(len(routes), 10)
        for route in routes:
            self.assertEqual(route.methods, {"GET"}, route.path)

    def test_health_declares_read_only_authority(self) -> None:
        value = self.api.health()
        self.assertEqual(value["mode"], "read-only")
        self.assertEqual(value["canonical_task_authority"], "Hermes Kanban")

    def test_observability_is_fail_open(self) -> None:
        value = self.api.observability()
        self.assertTrue(value["fail_open"])
        self.assertIn(value["status"], {"AVAILABLE", "DEGRADED"})


if __name__ == "__main__":
    unittest.main()

