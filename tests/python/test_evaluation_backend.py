"""GET-only evaluation routes stay on the analytics sidecar."""

from __future__ import annotations

import unittest

from tests.python.test_backend import load_backend


class EvaluationBackendTests(unittest.TestCase):
    def test_evaluation_routes_are_get_only(self) -> None:
        api = load_backend()
        paths = {route.path for route in api.router.routes if hasattr(route, "methods")}
        for path in (
            "/evaluations",
            "/evaluations/health",
            "/evaluations/coverage",
            "/evaluations/tasks/{task_id}",
        ):
            self.assertIn(path, paths)
        for route in api.router.routes:
            if hasattr(route, "methods"):
                self.assertEqual(route.methods, {"GET"}, route.path)
