"""Sample-size planning. Never invents variance. Never silently shrinks N."""

from __future__ import annotations

import math
from typing import Any

Z_ALPHA = {0.10: 1.6448536269514722, 0.05: 1.959963984540054, 0.01: 2.5758293035489004}
Z_POWER = {0.80: 0.8416212335729143, 0.90: 1.2815515655446004}


def _z_two_sided(alpha: float) -> float:
    if alpha in Z_ALPHA:
        return Z_ALPHA[alpha]
    return _acklam(1.0 - alpha / 2.0)


def _z_power(power: float) -> float:
    if power in Z_POWER:
        return Z_POWER[power]
    return _acklam(power)


def _acklam(p: float) -> float:
    """Approximate inverse standard normal CDF (Acklam)."""
    if p <= 0.0 or p >= 1.0:
        raise ValueError("p must be in (0, 1)")
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577509590705e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464858e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    )


def plan_binary(
    *,
    baseline_rate: float,
    mde: float,
    alpha: float,
    power: float,
    allocation_ratio: float = 1.0,
    max_units: int | None = None,
    max_llm_calls: int = 0,
    requires_llm: bool = False,
    paired: bool = False,
    discordance: float | None = None,
    variance: float | None = None,
    outcome_type: str = "binary",
) -> dict[str, Any]:
    assumptions = {
        "baseline_rate": baseline_rate,
        "mde": mde,
        "alpha": alpha,
        "power": power,
        "allocation_ratio": allocation_ratio,
        "paired": paired,
        "discordance": discordance,
        "variance": variance,
        "outcome_type": outcome_type,
        "z_alpha": _z_two_sided(alpha),
        "z_power": _z_power(power),
    }
    if outcome_type == "continuous":
        if variance is None:
            return {
                "status": "VARIANCE_REQUIRED",
                "planned_n": None,
                "assumptions": assumptions,
                "reason": "continuous plans require an operator-supplied variance; none invented",
            }
        # two-sample equal-n using supplied variance
        z = assumptions["z_alpha"] + assumptions["z_power"]
        n_arm = math.ceil((2 * variance * (z**2)) / (mde**2))
        planned = n_arm * 2
        return _feasibility(planned, max_units, max_llm_calls, requires_llm, assumptions)
    if not 0 < baseline_rate < 1 and mde == 0:
        return {
            "status": "INVALID_ASSUMPTION",
            "planned_n": None,
            "assumptions": assumptions,
            "reason": "baseline_rate must be in (0,1) or MDE must be non-zero",
        }
    p1 = baseline_rate
    p2 = min(1.0, max(0.0, baseline_rate + mde))
    if abs(p2 - p1) < 1e-12:
        return {
            "status": "INVALID_ASSUMPTION",
            "planned_n": None,
            "assumptions": assumptions,
            "reason": "MDE is zero; confirmatory sample size undefined",
        }
    z = assumptions["z_alpha"] + assumptions["z_power"]
    if paired:
        if discordance is None:
            return {
                "status": "DISCORDANCE_REQUIRED",
                "planned_n": None,
                "assumptions": assumptions,
                "reason": "paired binary plans require a discordance assumption",
            }
        # pairs needed ~ (z^2 * psi) / delta^2 with psi≈discordance
        planned = math.ceil((z**2) * discordance / (mde**2))
        planned = max(planned, 1)
        return _feasibility(planned, max_units, max_llm_calls, requires_llm, assumptions, unit="pairs")
    ratio = allocation_ratio if allocation_ratio > 0 else 1.0
    n1 = (z**2) * (p1 * (1 - p1) + p2 * (1 - p2) / ratio) / ((p2 - p1) ** 2)
    n_control = math.ceil(n1)
    n_candidate = math.ceil(n1 * ratio)
    planned = n_control + n_candidate
    result = _feasibility(planned, max_units, max_llm_calls, requires_llm, assumptions)
    result["n_control"] = n_control
    result["n_candidate"] = n_candidate
    return result


def _feasibility(
    planned: int,
    max_units: int | None,
    max_llm_calls: int,
    requires_llm: bool,
    assumptions: dict[str, Any],
    unit: str = "units",
) -> dict[str, Any]:
    status = "FEASIBLE"
    reason = "PASS"
    if requires_llm and max_llm_calls <= 0:
        status = "INFEASIBLE_BUDGET"
        reason = "real LLM experiments are disabled by max_llm_calls=0; planned N not shrunk"
    elif max_units is not None and planned > max_units:
        status = "INFEASIBLE_BUDGET"
        reason = "planned N exceeds max_units; planned N not shrunk"
    return {
        "status": status,
        "planned_n": planned,
        "unit": unit,
        "assumptions": assumptions,
        "reason": reason,
        "shrunk": False,
    }
