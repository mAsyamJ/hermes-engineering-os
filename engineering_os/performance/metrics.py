"""Deterministic metric aggregation over a cohort. Observational only."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from engineering_os.performance.stats import (
    coverage_ratio,
    distribution_summary,
    proportion,
    wilson_interval,
)
from engineering_os.performance.tiers import classify_tier

QUALITY_PASS = {"PASS"}
QUALITY_KNOWN = {"PASS", "FAIL"}
REGRESSION_INTRODUCED = {"INTRODUCED_FAILURE"}
COST_KNOWN = {"AVAILABLE", "KNOWN"}


def _binary_aggregate(
    members: list[dict[str, Any]],
    *,
    known: Callable[[dict[str, Any]], bool],
    success: Callable[[dict[str, Any]], bool],
    unknown: Callable[[dict[str, Any]], bool],
    na: Callable[[dict[str, Any]], bool],
    metric_id: str,
    tier_config: dict[str, Any],
) -> dict[str, Any]:
    population_n = len(members)
    known_rows = [row for row in members if known(row)]
    unknown_n = sum(1 for row in members if unknown(row))
    na_n = sum(1 for row in members if na(row))
    known_n = len(known_rows)
    successes = sum(1 for row in known_rows if success(row))
    value = proportion(successes, known_n)
    lo, hi = wilson_interval(successes, known_n)
    tier = classify_tier(known_n, tier_config)
    interpretation = "INSUFFICIENT_DATA" if known_n == 0 else None
    return {
        "metric_id": metric_id,
        "population_n": population_n,
        "known_n": known_n,
        "unknown_n": unknown_n,
        "na_n": na_n,
        "successes": successes,
        "coverage": coverage_ratio(known_n, population_n),
        "value": value,
        "unit": "proportion",
        "uncertainty": {
            "method": "wilson",
            "z": 1.96,
            "interval_low": lo,
            "interval_high": hi,
        },
        "evidence_tier": tier,
        "interpretation": interpretation,
        "member_ids": [f"{row['board']}:{row['task_id']}" for row in members],
        "known_ids": [f"{row['board']}:{row['task_id']}" for row in known_rows],
    }


def aggregate_lifecycle(members: list[dict[str, Any]], tier_config: dict[str, Any]) -> dict[str, Any]:
    return _binary_aggregate(
        members,
        known=lambda r: r.get("lifecycle_state") in {"DONE", "NOT_DONE"},
        success=lambda r: r.get("lifecycle_state") == "DONE",
        unknown=lambda r: r.get("lifecycle_state") == "UNKNOWN",
        na=lambda r: False,
        metric_id="lifecycle_completion_rate",
        tier_config=tier_config,
    )


def aggregate_verified_success(members: list[dict[str, Any]], tier_config: dict[str, Any]) -> dict[str, Any]:
    return _binary_aggregate(
        members,
        known=lambda r: r.get("verification_state") in {"PASS", "FAIL"},
        success=lambda r: r.get("final_outcome") == "VERIFIED_SUCCESS",
        unknown=lambda r: r.get("verification_state") == "UNKNOWN",
        na=lambda r: r.get("verification_state") == "NOT_APPLICABLE",
        metric_id="verified_success_rate",
        tier_config=tier_config,
    )


def aggregate_first_pass(members: list[dict[str, Any]], tier_config: dict[str, Any]) -> dict[str, Any]:
    return _binary_aggregate(
        members,
        known=lambda r: r.get("first_pass_state") in {"PASS", "FAIL"},
        success=lambda r: r.get("first_pass_state") == "PASS",
        unknown=lambda r: r.get("first_pass_state") == "UNKNOWN",
        na=lambda r: r.get("first_pass_state") == "NOT_APPLICABLE",
        metric_id="first_pass_rate",
        tier_config=tier_config,
    )


def aggregate_retry(members: list[dict[str, Any]], tier_config: dict[str, Any]) -> dict[str, Any]:
    return _binary_aggregate(
        members,
        known=lambda r: r.get("retry_count") is not None,
        success=lambda r: (r.get("retry_count") or 0) > 0,
        unknown=lambda r: r.get("retry_count") is None,
        na=lambda r: False,
        metric_id="retry_rate",
        tier_config=tier_config,
    )


def aggregate_rework(members: list[dict[str, Any]], tier_config: dict[str, Any]) -> dict[str, Any]:
    return _binary_aggregate(
        members,
        known=lambda r: r.get("rework_status") in {"DETECTED", "NOT_DETECTED"},
        success=lambda r: r.get("rework_status") == "DETECTED",
        unknown=lambda r: r.get("rework_status") == "UNKNOWN",
        na=lambda r: False,
        metric_id="rework_rate",
        tier_config=tier_config,
    )


def aggregate_human_intervention(members: list[dict[str, Any]], tier_config: dict[str, Any]) -> dict[str, Any]:
    """Detection rate over the full cohort. UNKNOWN stays in total N. Never false."""
    population_n = len(members)
    detected = [row for row in members if row.get("human_intervention_state") == "DETECTED"]
    unknown = [row for row in members if row.get("human_intervention_state") == "UNKNOWN"]
    # known_n is DETECTED only; absence of evidence is not a negative.
    known_n = len(detected)
    value = proportion(known_n, population_n) if population_n else None
    lo, hi = wilson_interval(known_n, population_n) if population_n else (None, None)
    return {
        "metric_id": "human_intervention_detection_rate",
        "population_n": population_n,
        "known_n": known_n,
        "unknown_n": len(unknown),
        "na_n": 0,
        "successes": known_n,
        "coverage": coverage_ratio(known_n, population_n),
        "value": value,
        "unit": "proportion",
        "uncertainty": {"method": "wilson", "z": 1.96, "interval_low": lo, "interval_high": hi},
        "evidence_tier": classify_tier(known_n, tier_config) if population_n else "NO_DATA",
        "interpretation": None if population_n else "INSUFFICIENT_DATA",
        "label": "detection rate; UNKNOWN is not false",
        "member_ids": [f"{row['board']}:{row['task_id']}" for row in members],
        "known_ids": [f"{row['board']}:{row['task_id']}" for row in detected],
    }


def _quality_members(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible = []
    for row in members:
        evaluation = row.get("evaluation") or {}
        if evaluation.get("cohort") == "fixture":
            continue
        if evaluation.get("eligibility") == "INSUFFICIENT_EVIDENCE":
            continue
        if evaluation.get("eligibility") != "ELIGIBLE":
            continue
        if evaluation.get("execution_status") != "COMPLETE":
            continue
        if not evaluation.get("quality_vector"):
            continue
        eligible.append(row)
    return eligible


def aggregate_quality(
    members: list[dict[str, Any]],
    metric_id: str,
    dimension: str,
    tier_config: dict[str, Any],
    success_states: set[str] | None = None,
) -> dict[str, Any]:
    evaluated = _quality_members(members)
    success_states = success_states or QUALITY_PASS
    known_states = QUALITY_KNOWN if dimension != "regression" else {
        "UNCHANGED_PASS",
        "INTRODUCED_FAILURE",
        "FIXED_FAILURE",
        "UNCHANGED_FAILURE",
    }
    known_rows = []
    unknown_n = 0
    na_n = 0
    for row in evaluated:
        verdict = str((row.get("evaluation") or {}).get("quality_vector", {}).get(dimension) or "UNKNOWN")
        if verdict in {"NOT_APPLICABLE", "NA"}:
            na_n += 1
        elif verdict in known_states:
            known_rows.append((row, verdict))
        else:
            unknown_n += 1
    known_n = len(known_rows)
    successes = sum(1 for _row, verdict in known_rows if verdict in success_states)
    population_n = len(members)
    value = proportion(successes, known_n)
    lo, hi = wilson_interval(successes, known_n)
    if not evaluated:
        interpretation = "INSUFFICIENT_DATA"
        tier = "NO_DATA"
        value = None
        lo = hi = None
        known_n = 0
        successes = 0
    else:
        interpretation = "INSUFFICIENT_DATA" if known_n == 0 else None
        tier = classify_tier(known_n, tier_config)
    return {
        "metric_id": metric_id,
        "population_n": population_n,
        "evaluated_n": len(evaluated),
        "known_n": known_n,
        "unknown_n": unknown_n,
        "na_n": na_n,
        "successes": successes,
        "coverage": coverage_ratio(len(evaluated), population_n),
        "value": value,
        "unit": "proportion",
        "uncertainty": {"method": "wilson", "z": 1.96, "interval_low": lo, "interval_high": hi},
        "evidence_tier": tier,
        "interpretation": interpretation,
        "quality_evaluated_n": len(evaluated),
        "member_ids": [f"{row['board']}:{row['task_id']}" for row in members],
        "known_ids": [f"{row['board']}:{row['task_id']}" for row, _v in known_rows],
    }


def aggregate_continuous(
    members: list[dict[str, Any]],
    metric_id: str,
    field: str,
    tier_config: dict[str, Any],
    p90_min_n: int,
    p95_min_n: int,
) -> dict[str, Any]:
    population_n = len(members)
    known_rows = [row for row in members if row.get(field) is not None]
    unknown_n = population_n - len(known_rows)
    values = [float(row[field]) for row in known_rows]
    summary = distribution_summary(values, p90_min_n=p90_min_n, p95_min_n=p95_min_n)
    known_n = len(known_rows)
    return {
        "metric_id": metric_id,
        "population_n": population_n,
        "known_n": known_n,
        "unknown_n": unknown_n,
        "na_n": 0,
        "coverage": coverage_ratio(known_n, population_n),
        "value": summary["median"],
        "unit": field,
        "uncertainty": {"method": "distribution", "summary": summary},
        "evidence_tier": classify_tier(known_n, tier_config),
        "interpretation": "INSUFFICIENT_DATA" if known_n == 0 else None,
        "mean_supplemental": summary["mean"],
        "member_ids": [f"{row['board']}:{row['task_id']}" for row in members],
        "known_ids": [f"{row['board']}:{row['task_id']}" for row in known_rows],
    }


def aggregate_cost(members: list[dict[str, Any]], tier_config: dict[str, Any]) -> dict[str, Any]:
    population_n = len(members)
    known_rows = [row for row in members if str(row.get("cost_status") or "UNKNOWN") in COST_KNOWN]
    unknown_n = sum(1 for row in members if str(row.get("cost_status") or "UNKNOWN") == "UNKNOWN")
    known_n = len(known_rows)
    return {
        "metric_id": "cost_known_rate",
        "population_n": population_n,
        "known_n": known_n,
        "unknown_n": unknown_n,
        "na_n": 0,
        "successes": known_n,
        "coverage": coverage_ratio(known_n, population_n),
        "value": None if known_n == 0 else proportion(known_n, population_n),
        "unit": "proportion",
        "uncertainty": {"method": "none", "reason": "no actual cost evidence; estimates forbidden"},
        "evidence_tier": classify_tier(known_n, tier_config),
        "interpretation": "INSUFFICIENT_DATA" if known_n == 0 else None,
        "cost_effectiveness": "INSUFFICIENT_EVIDENCE" if known_n == 0 else "OBSERVATIONAL",
        "member_ids": [f"{row['board']}:{row['task_id']}" for row in members],
        "known_ids": [f"{row['board']}:{row['task_id']}" for row in known_rows],
    }


QUALITY_METRICS = {
    "quality_build_pass_rate": ("build", QUALITY_PASS),
    "quality_tests_pass_rate": ("tests", QUALITY_PASS),
    "quality_regression_introduced_rate": ("regression", REGRESSION_INTRODUCED),
    "quality_lint_pass_rate": ("lint", QUALITY_PASS),
    "quality_typecheck_pass_rate": ("typecheck", QUALITY_PASS),
    "quality_security_pass_rate": ("security", QUALITY_PASS),
    "quality_architecture_pass_rate": ("architecture", QUALITY_PASS),
    "quality_acceptance_pass_rate": ("acceptance", QUALITY_PASS),
}

CONTINUOUS_METRICS = {
    "task_wall_seconds": "task_wall_seconds",
    "run_wall_seconds": "run_wall_seconds",
    "trace_wall_seconds": "trace_wall_seconds",
    "llm_call_count": "llm_call_count",
    "tool_call_count": "tool_call_count",
    "token_total": "token_total",
}

OUTCOME_METRICS = {
    "lifecycle_completion_rate": aggregate_lifecycle,
    "verified_success_rate": aggregate_verified_success,
    "first_pass_rate": aggregate_first_pass,
    "retry_rate": aggregate_retry,
    "rework_rate": aggregate_rework,
    "human_intervention_detection_rate": aggregate_human_intervention,
}


def compute_metric(
    metric_id: str,
    members: list[dict[str, Any]],
    tier_config: dict[str, Any],
    p90_min_n: int = 20,
    p95_min_n: int = 40,
) -> dict[str, Any]:
    if metric_id in OUTCOME_METRICS:
        return OUTCOME_METRICS[metric_id](members, tier_config)
    if metric_id in QUALITY_METRICS:
        dimension, success = QUALITY_METRICS[metric_id]
        return aggregate_quality(members, metric_id, dimension, tier_config, success)
    if metric_id in CONTINUOUS_METRICS:
        return aggregate_continuous(
            members, metric_id, CONTINUOUS_METRICS[metric_id], tier_config, p90_min_n, p95_min_n
        )
    if metric_id == "cost_known_rate":
        return aggregate_cost(members, tier_config)
    raise KeyError(metric_id)


def group_by(members: list[dict[str, Any]], dimension: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in members:
        if dimension == "profile_name":
            key = str(row.get("profile_name") or row.get("profile") or "UNKNOWN")
            grouped[key].append(row)
        elif dimension == "model":
            if row.get("model_attribution") != "SINGLE_MODEL":
                continue
            keys = row.get("model_keys") or []
            if len(keys) != 1:
                continue
            grouped[str(keys[0])].append(row)
        elif dimension == "skill":
            skills = row.get("skills") or []
            if row.get("skill_attribution") != "SINGLE_SKILL" or len(skills) != 1:
                continue
            grouped[str(skills[0]["skill_name"])].append(row)
        elif dimension == "repository_id":
            grouped[str(row.get("repository_id") or "UNKNOWN")].append(row)
        elif dimension == "board":
            grouped[str(row.get("board") or "UNKNOWN")].append(row)
        else:
            raise KeyError(dimension)
    return dict(grouped)
