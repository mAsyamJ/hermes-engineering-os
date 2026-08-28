from __future__ import annotations

import unittest

from tests.python.test_backend import load_backend


class ExperimentBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.api = load_backend()

    def test_experiment_routes_are_get_only(self) -> None:
        routes = [route for route in self.api.router.routes if hasattr(route, "methods")]
        experiment_routes = [route for route in routes if "/experiments" in route.path]
        self.assertGreaterEqual(len(experiment_routes), 5)
        for route in experiment_routes:
            self.assertEqual(route.methods, {"GET"}, route.path)

    def test_no_promote_route(self) -> None:
        paths = {route.path for route in self.api.router.routes if hasattr(route, "methods")}
        for forbidden in ("/promote", "/deploy", "/winner", "/auto-route"):
            self.assertFalse(any(forbidden in path for path in paths))
