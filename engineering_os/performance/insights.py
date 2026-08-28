"""Deterministic explanatory statements. Not recommendations. No LLM."""

from __future__ import annotations

from typing import Any


def insight_for_aggregate(aggregate: dict[str, Any], cohort_id: str) -> str | None:
    metric = aggregate.get("metric_id")
    tier = aggregate.get("evidence_tier")
    known = aggregate.get("known_n") or 0
    population = aggregate.get("population_n") or 0
    if str(metric or "").startswith("quality_") and known == 0:
        return (
            f"Quality comparison unavailable: 0 production tasks have Phase 4 evaluation "
            f"coverage in cohort {cohort_id}."
        )
    if metric == "cost_known_rate" and known == 0:
        return (
            f"Cost-effectiveness remains INSUFFICIENT_EVIDENCE in cohort {cohort_id}: "
            "no provider-backed actual cost evidence exists. Prices were not estimated."
        )
    if metric in {"trace_wall_seconds", "llm_call_count", "tool_call_count", "token_total"} and known == 0:
        return (
            f"Efficiency metric {metric} is INSUFFICIENT_DATA in cohort {cohort_id}: "
            f"0 of {population} tasks have trace coverage."
        )
    if tier in {"NO_DATA", "INSUFFICIENT"} and aggregate.get("value") is None:
        return f"{metric} in cohort {cohort_id} is {tier} (known n={known} of {population})."
    return None


def insight_for_comparison(comparison: dict[str, Any], cohort_id: str) -> str:
    metric = comparison.get("metric_id")
    left = comparison.get("left_identity")
    right = comparison.get("right_identity")
    interpretation = comparison.get("interpretation")
    left_tier = comparison.get("left_tier")
    right_tier = comparison.get("right_tier")
    left_est = comparison.get("left_estimate")
    right_est = comparison.get("right_estimate")
    delta = comparison.get("absolute_difference")
    if interpretation == "NOT_COMPARABLE":
        return (
            f"{left} vs {right} on {metric} is NOT_COMPARABLE in cohort {cohort_id}: "
            f"{comparison.get('reason') or 'incompatible cohort semantics'}."
        )
    if interpretation == "CONFOUNDED":
        return (
            f"Observed difference between {left} and {right} on {metric} in cohort {cohort_id} "
            f"cannot be attributed to one dimension because {comparison.get('reason') or 'confounding was detected'}. "
            "This is observational association, not a causal claim."
        )
    if interpretation == "INSUFFICIENT_DATA":
        if (comparison.get("left_n") or 0) == 0 and (comparison.get("right_n") or 0) == 0:
            return (
                f"{metric} comparison unavailable in cohort {cohort_id}: both groups have "
                "insufficient known evidence."
            )
        return (
            f"{left} vs {right} on {metric} in cohort {cohort_id} is INSUFFICIENT_DATA "
            f"(left n={comparison.get('left_n')}, right n={comparison.get('right_n')}; "
            f"tiers {left_tier}/{right_tier})."
        )
    pct = None
    if isinstance(delta, (int, float)):
        pct = round(delta * 100, 1)
    if interpretation == "NO_CLEAR_DIFFERENCE":
        return (
            f"Within cohort {cohort_id}, {left} vs {right} on {metric} differs "
            f"({_fmt(left_est)} vs {_fmt(right_est)}"
            f"{f', {pct} percentage points' if pct is not None else ''}), "
            "but available uncertainty/evidence does not support a clear distinction."
        )
    return (
        f"Within cohort {cohort_id}, {right} has a "
        f"{abs(pct) if pct is not None else '?'} percentage-point "
        f"{'higher' if (delta or 0) > 0 else 'lower'} observed {metric} estimate than {left} "
        f"({_fmt(right_est)} vs {_fmt(left_est)}), but this is observational, "
        f"tiers are {left_tier}/{right_tier}, and this is not a routing recommendation."
    )


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)
