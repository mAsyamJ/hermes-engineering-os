"""Comparability, confounding, and pairwise effect estimates. No winner ranking."""

from __future__ import annotations

from collections import Counter
from typing import Any

from engineering_os.performance.metrics import compute_metric, group_by
from engineering_os.performance.stats import difference_of_proportions, intervals_overlap
from engineering_os.performance.tiers import classify_tier, tier_at_least

MAJOR_CONFOUNDERS = ("repository_id", "profile_name", "model_attribution", "skill_attribution")


def _majority(values: list[str]) -> tuple[str | None, float]:
    counted = Counter(v for v in values if v and v != "UNKNOWN")
    if not counted:
        return None, 0.0
    key, n = counted.most_common(1)[0]
    return key, n / max(len(values), 1)


def comparability(
    left_members: list[dict[str, Any]],
    right_members: list[dict[str, Any]],
    *,
    metric_id: str,
    left_ruleset: str,
    right_ruleset: str,
    left_eval_contract: str | None,
    right_eval_contract: str | None,
    quality_metric: bool,
    stratifiers: list[str],
) -> dict[str, Any]:
    if left_ruleset != right_ruleset:
        return {
            "comparability": "NOT_COMPARABLE",
            "confounding_status": "RULESET_MISMATCH",
            "reason": "Phase 3 ruleset versions differ",
        }
    if quality_metric and left_eval_contract != right_eval_contract:
        return {
            "comparability": "NOT_COMPARABLE",
            "confounding_status": "EVALUATION_CONTRACT_MISMATCH",
            "reason": "Phase 4 evaluation contracts differ",
        }
    confounders: list[str] = []
    for field in stratifiers or ["repository_id", "profile_name"]:
        left_maj, left_share = _majority([str(row.get(field) or row.get("profile") or "UNKNOWN") for row in left_members])
        right_maj, right_share = _majority(
            [str(row.get(field) or row.get("profile") or "UNKNOWN") for row in right_members]
        )
        if left_maj and right_maj and left_maj != right_maj and left_share >= 0.6 and right_share >= 0.6:
            confounders.append(field)
    if "model" in metric_id:
        pass
    # Comparing models: if profile mix differs, confounded.
    if confounders:
        return {
            "comparability": "CONFOUNDED",
            "confounding_status": "CONFOUNDED",
            "reason": "observed difference cannot be attributed to one dimension: " + ",".join(confounders),
            "confounders": confounders,
        }
    return {
        "comparability": "COMPARABLE",
        "confounding_status": "NONE",
        "reason": "cohort semantics and major mix appear compatible",
        "confounders": [],
    }


def simpson_guard(
    left_members: list[dict[str, Any]],
    right_members: list[dict[str, Any]],
    metric_id: str,
    stratifier: str,
    tier_config: dict[str, Any],
    global_delta: float | None,
) -> dict[str, Any]:
    left_strata = group_by(left_members, stratifier) if stratifier in {"repository_id", "profile_name", "board"} else {}
    right_strata = group_by(right_members, stratifier) if stratifier in {"repository_id", "profile_name", "board"} else {}
    keys = sorted(set(left_strata) | set(right_strata))
    breakdown = []
    reversal = False
    populated = 0
    for key in keys:
        left = left_strata.get(key) or []
        right = right_strata.get(key) or []
        if not left or not right:
            continue
        left_agg = compute_metric(metric_id, left, tier_config)
        right_agg = compute_metric(metric_id, right, tier_config)
        if left_agg.get("value") is None or right_agg.get("value") is None:
            continue
        populated += 1
        delta = right_agg["value"] - left_agg["value"]
        breakdown.append(
            {
                "stratum": key,
                "left_n": left_agg["known_n"],
                "right_n": right_agg["known_n"],
                "left": left_agg["value"],
                "right": right_agg["value"],
                "delta": delta,
            }
        )
        if global_delta is not None and delta != 0 and global_delta != 0:
            if (delta > 0) != (global_delta > 0):
                reversal = True
    unsafe = reversal or (populated >= 2 and global_delta is not None)
    return {
        "stratifier": stratifier,
        "strata": breakdown,
        "simpson_reversal": reversal,
        "unsafe_global": reversal,
        "populated_strata": populated,
    }


def pairwise(
    left_identity: str,
    right_identity: str,
    left_members: list[dict[str, Any]],
    right_members: list[dict[str, Any]],
    metric_id: str,
    *,
    left_aggregate: dict[str, Any],
    right_aggregate: dict[str, Any],
    tier_config: dict[str, Any],
    comparison_config: dict[str, Any],
    left_ruleset: str,
    right_ruleset: str,
    left_eval_contract: str | None = None,
    right_eval_contract: str | None = None,
    stratifiers: list[str] | None = None,
) -> dict[str, Any]:
    quality_metric = metric_id.startswith("quality_")
    status = comparability(
        left_members,
        right_members,
        metric_id=metric_id,
        left_ruleset=left_ruleset,
        right_ruleset=right_ruleset,
        left_eval_contract=left_eval_contract,
        right_eval_contract=right_eval_contract,
        quality_metric=quality_metric,
        stratifiers=stratifiers or ["repository_id"],
    )
    left_k = int(left_aggregate.get("successes") or 0)
    right_k = int(right_aggregate.get("successes") or 0)
    left_n = int(left_aggregate.get("known_n") or 0)
    right_n = int(right_aggregate.get("known_n") or 0)
    effect = difference_of_proportions(left_k, left_n, right_k, right_n)
    min_tier = str((comparison_config.get("observed_difference_min_tier") if comparison_config else None) or "EXPLORATORY")
    floor = int((comparison_config.get("comparison_floor_known_n") if comparison_config else None) or 10)

    interpretation = "INSUFFICIENT_DATA"
    if status["comparability"] == "NOT_COMPARABLE":
        interpretation = "NOT_COMPARABLE"
        effect = {key: None if key.endswith("difference") or "interval" in key or key in {"left", "right"} else effect.get(key) for key in effect}
        # Keep estimates for diagnostics but do not treat as a ranking.
        numeric_forbidden = True
    elif status["comparability"] == "CONFOUNDED":
        interpretation = "CONFOUNDED"
        numeric_forbidden = False
    elif left_n < floor or right_n < floor:
        interpretation = "INSUFFICIENT_DATA"
        numeric_forbidden = False
    else:
        numeric_forbidden = False
        overlap = intervals_overlap(
            effect.get("left_interval_low"),
            effect.get("left_interval_high"),
            effect.get("right_interval_low"),
            effect.get("right_interval_high"),
        )
        both_ok = tier_at_least(left_aggregate["evidence_tier"], min_tier) and tier_at_least(
            right_aggregate["evidence_tier"], min_tier
        )
        if overlap or not both_ok:
            interpretation = "NO_CLEAR_DIFFERENCE"
        else:
            interpretation = "OBSERVED_DIFFERENCE"

    strata_payload = []
    unsafe = False
    for stratifier in stratifiers or []:
        guard = simpson_guard(
            left_members,
            right_members,
            metric_id,
            stratifier,
            tier_config,
            effect.get("absolute_difference"),
        )
        strata_payload.append(guard)
        if guard.get("simpson_reversal"):
            unsafe = True
            if interpretation == "OBSERVED_DIFFERENCE":
                interpretation = "CONFOUNDED"
                status = dict(status)
                status["comparability"] = "CONFOUNDED"
                status["confounding_status"] = "SIMPSON_REVERSAL"
                status["reason"] = "global aggregate reverses inside strata"

    return {
        "left_identity": left_identity,
        "right_identity": right_identity,
        "metric_id": metric_id,
        "left_n": left_n,
        "right_n": right_n,
        "left_estimate": left_aggregate.get("value"),
        "right_estimate": right_aggregate.get("value"),
        "absolute_difference": None if status["comparability"] == "NOT_COMPARABLE" else effect.get("absolute_difference"),
        "relative_difference": None if status["comparability"] == "NOT_COMPARABLE" else effect.get("relative_difference"),
        "uncertainty": effect,
        "coverage": {
            "left": left_aggregate.get("coverage"),
            "right": right_aggregate.get("coverage"),
        },
        "left_tier": left_aggregate.get("evidence_tier"),
        "right_tier": right_aggregate.get("evidence_tier"),
        "comparability": status["comparability"],
        "confounding_status": status["confounding_status"],
        "interpretation": interpretation,
        "reason": status.get("reason"),
        "strata": strata_payload,
        "unsafe_global": unsafe,
        "winner": None,
        "numeric_forbidden": numeric_forbidden,
    }
