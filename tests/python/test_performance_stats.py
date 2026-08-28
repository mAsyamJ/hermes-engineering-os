"""Golden statistical primitives. Expected values authored from the Wilson formula."""

from __future__ import annotations

import unittest

from engineering_os.performance.stats import (
    coverage_ratio,
    difference_of_proportions,
    distribution_summary,
    median,
    proportion,
    quantile,
    safe_relative_difference,
    wilson_interval,
)
from engineering_os.performance.tiers import classify_tier, load_tiers


class ProportionTests(unittest.TestCase):
    def test_n0(self) -> None:
        self.assertIsNone(proportion(0, 0))
        self.assertEqual(wilson_interval(0, 0), (None, None))

    def test_n1_all_failure(self) -> None:
        self.assertEqual(proportion(0, 1), 0.0)
        lo, hi = wilson_interval(0, 1)
        self.assertAlmostEqual(lo, 0.0, places=6)
        self.assertAlmostEqual(hi, 0.7934567085, places=6)

    def test_n1_all_success(self) -> None:
        self.assertEqual(proportion(1, 1), 1.0)
        lo, hi = wilson_interval(1, 1)
        self.assertAlmostEqual(lo, 0.2065432915, places=6)
        self.assertAlmostEqual(hi, 1.0, places=6)

    def test_tiny_and_large(self) -> None:
        lo, hi = wilson_interval(8, 10)
        self.assertAlmostEqual(lo, 0.4901568467, places=6)
        self.assertAlmostEqual(hi, 0.9433190520, places=6)
        lo, hi = wilson_interval(50, 100)
        self.assertAlmostEqual(lo, 0.4038298286, places=6)
        self.assertAlmostEqual(hi, 0.5961701714, places=6)

    def test_unequal_difference(self) -> None:
        delta = difference_of_proportions(8, 10, 2, 20)
        self.assertAlmostEqual(delta["absolute_difference"], 0.1 - 0.8)
        self.assertIsNotNone(delta["interval_low"])
        self.assertLess(delta["interval_high"], 0)

    def test_identical_distributions(self) -> None:
        delta = difference_of_proportions(5, 10, 5, 10)
        self.assertEqual(delta["absolute_difference"], 0.0)

    def test_zero_denominator_relative(self) -> None:
        self.assertIsNone(safe_relative_difference(0.0, 0.5))
        self.assertIsNone(coverage_ratio(0, 0))
        self.assertEqual(coverage_ratio(5, 10), 0.5)

    def test_rejects_invalid(self) -> None:
        with self.assertRaises(ValueError):
            proportion(2, 1)


class DistributionTests(unittest.TestCase):
    def test_median_and_quantiles(self) -> None:
        values = [1.0, 2.0, 100.0]
        self.assertEqual(median(values), 2.0)
        self.assertEqual(quantile(values, 0.25), 1.5)
        self.assertEqual(quantile(values, 0.75), 51.0)

    def test_outlier_does_not_own_median(self) -> None:
        self.assertEqual(median([1.0, 2.0, 3.0, 4.0, 1000.0]), 3.0)

    def test_empty_and_single(self) -> None:
        self.assertIsNone(median([]))
        self.assertEqual(median([7.0]), 7.0)
        summary = distribution_summary([1.0], p90_min_n=20, p95_min_n=40)
        self.assertIsNone(summary["p90"])
        self.assertIsNone(summary["p95"])

    def test_p95_requires_sample(self) -> None:
        summary = distribution_summary(list(range(40)), p90_min_n=20, p95_min_n=40)
        self.assertIsNotNone(summary["p90"])
        self.assertIsNotNone(summary["p95"])


class TierTests(unittest.TestCase):
    def test_defaults(self) -> None:
        cfg = load_tiers()
        self.assertEqual(classify_tier(0, cfg), "NO_DATA")
        self.assertEqual(classify_tier(1, cfg), "INSUFFICIENT")
        self.assertEqual(classify_tier(9, cfg), "INSUFFICIENT")
        self.assertEqual(classify_tier(10, cfg), "EXPLORATORY")
        self.assertEqual(classify_tier(30, cfg), "PROVISIONAL")
        self.assertEqual(classify_tier(100, cfg), "SUPPORTED")


if __name__ == "__main__":
    unittest.main()
