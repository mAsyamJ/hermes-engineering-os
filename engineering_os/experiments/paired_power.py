"""Independent paired-binary sample size. Does not call plan_binary."""

from __future__ import annotations

import math
from typing import Any

# Standard normal quantiles (same constants as published tables, not imported from plan.py)
Z_A = {0.10: 1.6448536269514722, 0.05: 1.959963984540054, 0.01: 2.5758293035489004}
Z_B = {0.80: 0.8416212335729143, 0.90: 1.2815515655446004}


def _z_a(alpha: float) -> float:
    if alpha not in Z_A:
        raise ValueError("unsupported alpha")
    return Z_A[alpha]


def _z_b(power: float) -> float:
    if power not in Z_B:
        raise ValueError("unsupported power")
    return Z_B[power]


def _binom_pmf(k: int, n: int, p: float) -> float:
    if k < 0 or k > n:
        return 0.0
    return math.comb(n, k) * (p**k) * ((1.0 - p) ** (n - k))


def _binom_cdf(k: int, n: int, p: float) -> float:
    return sum(_binom_pmf(i, n, p) for i in range(0, k + 1))


def _exact_mcnemar_reject(x: int, d: int, alpha: float) -> bool:
    """Two-sided exact McNemar on d discordant pairs, x in the + direction."""
    if d <= 0:
        return False
    lower = _binom_cdf(x, d, 0.5)
    upper = 1.0 - _binom_cdf(x - 1, d, 0.5)
    p_two = 2.0 * min(lower, upper)
    return p_two <= alpha + 1e-15


def connor_pairs(*, discordance: float, mde: float, alpha: float, power: float) -> int:
    """Connor 1987 McNemar normal approximation (no continuity correction)."""
    if not 0 < discordance <= 1 or mde <= 0 or mde >= discordance:
        raise ValueError("discordance must exceed MDE and lie in (0,1]")
    za = _z_a(alpha)
    zb = _z_b(power)
    inner = za * math.sqrt(discordance) + zb * math.sqrt(discordance - mde * mde)
    return max(1, math.ceil((inner * inner) / (mde * mde)))


def connor_pairs_continuity(*, discordance: float, mde: float, alpha: float, power: float) -> int:
    """Connor approximation plus 2/|MDE| continuity correction (conservative)."""
    base = connor_pairs(discordance=discordance, mde=mde, alpha=alpha, power=power)
    return max(base, math.ceil(base + 2.0 / mde))


def exact_mcnemar_power(
    n_pairs: int,
    *,
    discordance: float,
    mde: float,
    alpha: float,
) -> float:
    """Unconditional exact McNemar power under p10=(ψ+δ)/2, p01=(ψ-δ)/2."""
    p10 = (discordance + mde) / 2.0
    pi = p10 / discordance
    total = 0.0
    for d in range(0, n_pairs + 1):
        pd = _binom_pmf(d, n_pairs, discordance)
        if pd == 0.0:
            continue
        reject = 0.0
        for x in range(0, d + 1):
            if _exact_mcnemar_reject(x, d, alpha):
                reject += _binom_pmf(x, d, pi)
        total += pd * reject
    return total


def smallest_n_exact_power(
    *,
    discordance: float,
    mde: float,
    alpha: float,
    power: float,
    start: int,
    limit: int = 80,
) -> int:
    n = max(1, start)
    while n <= limit:
        if exact_mcnemar_power(n, discordance=discordance, mde=mde, alpha=alpha) >= power - 1e-9:
            return n
        n += 1
    return limit


def freeze_paired_horizon(
    *,
    discordance: float,
    mde: float,
    alpha: float,
    power: float,
    eos_planner_n: int,
) -> dict[str, Any]:
    """Return the conservative frozen pair count. Call before any model output."""
    connor = connor_pairs(discordance=discordance, mde=mde, alpha=alpha, power=power)
    connor_cc = connor_pairs_continuity(discordance=discordance, mde=mde, alpha=alpha, power=power)
    exact_n = smallest_n_exact_power(
        discordance=discordance,
        mde=mde,
        alpha=alpha,
        power=power,
        start=min(connor, eos_planner_n),
    )
    frozen = max(int(eos_planner_n), connor, connor_cc, exact_n)
    return {
        "eos_planner_n": int(eos_planner_n),
        "connor_n": connor,
        "connor_continuity_n": connor_cc,
        "exact_power_n": exact_n,
        "frozen_pairs": frozen,
        "frozen_units": frozen * 2,
        "assumptions": {
            "alpha": alpha,
            "power": power,
            "mde": mde,
            "discordance": discordance,
            "method": "max(EOS planner, Connor 1987, Connor+CC 2/MDE, exact McNemar power)",
        },
        "exact_power_at_frozen": exact_mcnemar_power(
            frozen, discordance=discordance, mde=mde, alpha=alpha
        ),
        "pilot_v1_pairs": 5,
        "v1_class": "PILOT_ONLY",
    }
