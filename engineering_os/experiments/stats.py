"""Deterministic experiment statistics. Standard library only."""

from __future__ import annotations

import math
from typing import Any

from engineering_os.performance.stats import Z_WILSON, difference_of_proportions, mean, median, wilson_interval


def paired_binary(control: list[int | None], candidate: list[int | None]) -> dict[str, Any]:
    """Paired discordance analysis. 1=success, 0=failure, None=missing."""
    if len(control) != len(candidate):
        raise ValueError("paired vectors must have equal length")
    n_pairs = len(control)
    complete_c: list[int] = []
    complete_t: list[int] = []
    b = c = concordant = missing = 0
    for left, right in zip(control, candidate):
        if left is None or right is None:
            missing += 1
            continue
        complete_c.append(int(left))
        complete_t.append(int(right))
        if left == 0 and right == 1:
            b += 1
        elif left == 1 and right == 0:
            c += 1
        else:
            concordant += 1
    n_complete = len(complete_c)
    control_k = sum(complete_c)
    cand_k = sum(complete_t)
    effect = difference_of_proportions(control_k, n_complete, cand_k, n_complete)
    discordance_n = b + c
    discordance = None
    discordance_interval = (None, None)
    if discordance_n > 0:
        discordance = b / discordance_n
        discordance_interval = wilson_interval(b, discordance_n)
    exact_b_or_more = None
    if discordance_n > 0 and discordance_n <= 40:
        exact_b_or_more = _exact_binomial_tail(b, discordance_n)
    return {
        "n_pairs": n_pairs,
        "n_complete": n_complete,
        "missing_pairs": missing,
        "control_successes": control_k,
        "candidate_successes": cand_k,
        "b_candidate_only": b,
        "c_control_only": c,
        "concordant": concordant,
        "discordance_rate": discordance,
        "discordance_interval_low": discordance_interval[0],
        "discordance_interval_high": discordance_interval[1],
        "exact_binomial_tail": exact_b_or_more,
        **effect,
        "method": "paired-binary-wilson-v1",
    }


def independent_binary(control: list[int | None], candidate: list[int | None]) -> dict[str, Any]:
    ck = [int(v) for v in control if v is not None]
    tk = [int(v) for v in candidate if v is not None]
    effect = difference_of_proportions(sum(ck), len(ck), sum(tk), len(tk))
    return {
        "n_control_assigned": len(control),
        "n_candidate_assigned": len(candidate),
        "n_control_known": len(ck),
        "n_candidate_known": len(tk),
        "missing_control": sum(1 for v in control if v is None),
        "missing_candidate": sum(1 for v in candidate if v is None),
        **effect,
        "method": "independent-binary-wilson-v1",
    }


def paired_continuous(control: list[float | None], candidate: list[float | None]) -> dict[str, Any]:
    diffs = [
        float(right) - float(left)
        for left, right in zip(control, candidate)
        if left is not None and right is not None
    ]
    return {
        "n_complete": len(diffs),
        "mean_difference": mean(diffs),
        "median_difference": median(diffs),
        "method": "paired-continuous-quantile-v1",
    }


def _exact_binomial_tail(successes: int, n: int) -> float:
    """Two-sided exact binomial tail under p=0.5 using math.comb. Small n only."""
    if n <= 0:
        return 1.0
    observed = min(successes, n - successes)
    total = 0.0
    denom = 2**n
    for k in range(0, observed + 1):
        total += math.comb(n, k)
    # two-sided: both tails
    return min(1.0, 2.0 * total / denom)
