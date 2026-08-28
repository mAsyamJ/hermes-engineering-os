from __future__ import annotations

import unittest

from tests.python.test_backend import load_backend


class AdaptationBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.api = load_backend()

    def test_adaptation_routes_are_get_only(self) -> None:
        routes = [route for route in self.api.router.routes if hasattr(route, "methods")]
        adaptation_routes = [route for route in routes if "/adaptation" in route.path]
        self.assertGreaterEqual(len(adaptation_routes), 5)
        for route in adaptation_routes:
            self.assertEqual(route.methods, {"GET"}, route.path)

    def test_no_deploy_or_approve_routes(self) -> None:
        paths = {route.path for route in self.api.router.routes if hasattr(route, "methods")}
        for forbidden in ("/promote", "/deploy", "/winner", "/auto-route", "/approve", "/optimize"):
            self.assertFalse(any(forbidden in path for path in paths), forbidden)
