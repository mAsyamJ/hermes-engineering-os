"""Experiment statistics unit tests."""

from __future__ import annotations

import unittest

from engineering_os.experiments.stats import independent_binary, paired_binary
from engineering_os.performance.stats import difference_of_proportions


class ExperimentStatsTests(unittest.TestCase):
    def test_reuses_wilson(self) -> None:
        base = difference_of_proportions(0, 8, 8, 8)
        paired = paired_binary([0] * 8, [1] * 8)
        self.assertEqual(base["absolute_difference"], paired["absolute_difference"])

    def test_missing_pairs(self) -> None:
        result = paired_binary([1, None, 0], [0, 1, 1])
        self.assertEqual(result["missing_pairs"], 1)
        self.assertEqual(result["n_complete"], 2)
