"""Deterministic statistical primitives. Standard library only."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

Z_WILSON = 1.96


def proportion(successes: int, n: int) -> float | None:
    if n <= 0:
        return None
    if successes < 0 or successes > n:
        raise ValueError("successes must be in [0, n]")
    return successes / n


def wilson_interval(successes: int, n: int, z: float = Z_WILSON) -> tuple[float | None, float | None]:
    """Wilson score interval for a binomial proportion.

    Chosen over Wald because it remains defined at 0/n and n/n and has better
    small-sample coverage. z defaults to 1.96 (nominal 95%).
    """
    if n <= 0:
        return None, None
    if successes < 0 or successes > n:
        raise ValueError("successes must be in [0, n]")
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    rad = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n) / denom
    lo = max(0.0, center - rad)
    hi = min(1.0, center + rad)
    return lo, hi


def difference_of_proportions(
    left_k: int,
    left_n: int,
    right_k: int,
    right_n: int,
    z: float = Z_WILSON,
) -> dict[str, float | None]:
    """Absolute difference (right - left) with a conservative Wilson combination.

    Interval is [left_lo - right_hi, left_hi - right_lo] negated to right-left:
    [right_lo - left_hi, right_hi - left_lo]. Uncorrelated. No p-value.
    """
    left_p = proportion(left_k, left_n)
    right_p = proportion(right_k, right_n)
    left_lo, left_hi = wilson_interval(left_k, left_n, z)
    right_lo, right_hi = wilson_interval(right_k, right_n, z)
    delta = None if left_p is None or right_p is None else right_p - left_p
    rel = None
    if left_p not in (None, 0) and right_p is not None:
        rel = (right_p - left_p) / left_p
    if None in (left_lo, left_hi, right_lo, right_hi):
        dlo = dhi = None
    else:
        dlo = (right_lo or 0) - (left_hi or 0)
        dhi = (right_hi or 0) - (left_lo or 0)
    return {
        "left": left_p,
        "right": right_p,
        "absolute_difference": delta,
        "relative_difference": rel,
        "interval_low": dlo,
        "interval_high": dhi,
        "left_interval_low": left_lo,
        "left_interval_high": left_hi,
        "right_interval_low": right_lo,
        "right_interval_high": right_hi,
    }


def coverage_ratio(known_n: int, population_n: int) -> float | None:
    if population_n <= 0:
        return None
    return known_n / population_n


def safe_relative_difference(left: float | None, right: float | None) -> float | None:
    if left in (None, 0) or right is None:
        return None
    return (right - left) / left


def quantile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    if q < 0 or q > 1:
        raise ValueError("q must be in [0, 1]")
    xs = sorted(float(v) for v in values)
    if len(xs) == 1:
        return xs[0]
    pos = q * (len(xs) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def median(values: Sequence[float]) -> float | None:
    return quantile(values, 0.5)


def mean(values: Sequence[float]) -> float | None:
    xs = list(values)
    if not xs:
        return None
    return sum(xs) / len(xs)


def iqr(values: Sequence[float]) -> float | None:
    lo = quantile(values, 0.25)
    hi = quantile(values, 0.75)
    if lo is None or hi is None:
        return None
    return hi - lo


def distribution_summary(
    values: Iterable[float],
    *,
    p90_min_n: int = 20,
    p95_min_n: int = 40,
) -> dict[str, float | int | None]:
    xs = [float(v) for v in values]
    n = len(xs)
    summary: dict[str, float | int | None] = {
        "n": n,
        "mean": mean(xs),
        "median": median(xs),
        "p25": quantile(xs, 0.25),
        "p75": quantile(xs, 0.75),
        "iqr": iqr(xs),
        "p90": quantile(xs, 0.90) if n >= p90_min_n else None,
        "p95": quantile(xs, 0.95) if n >= p95_min_n else None,
        "min": min(xs) if xs else None,
        "max": max(xs) if xs else None,
    }
    return summary


def intervals_overlap(lo_a: float | None, hi_a: float | None, lo_b: float | None, hi_b: float | None) -> bool | None:
    if None in (lo_a, hi_a, lo_b, hi_b):
        return None
    return not (hi_a < lo_b or hi_b < lo_a)
