"""Assignment golden corpus."""

from __future__ import annotations

import inspect
import unittest

from engineering_os.experiments import assignment as assignment_mod
from engineering_os.experiments.assignment import ALG, assign_blocked, sort_key


class GoldenAssignment(unittest.TestCase):
    def test_no_builtin_hash(self) -> None:
        source = inspect.getsource(assignment_mod)
        self.assertNotIn("hash(unit", source)
        self.assertIn("hmac.new", source)

    def test_fixed_vector(self) -> None:
        units = [{"unit_id": "alpha", "stratum": "s"}, {"unit_id": "beta", "stratum": "s"}]
        rows = assign_blocked(units, "golden-seed", "control", "candidate")
        by_id = {row["unit_id"]: row for row in rows}
        self.assertEqual(by_id["alpha"]["sort_key"], sort_key("golden-seed", "s", "alpha"))
        self.assertEqual(by_id["beta"]["sort_key"], sort_key("golden-seed", "s", "beta"))
        self.assertEqual(ALG, "assign-hmac-sha256-v1")
        self.assertEqual(len({row["variant_role"] for row in rows}), 2)
