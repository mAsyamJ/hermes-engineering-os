"""Pure performance engine. DB-free so golden fixtures can drive it."""

from __future__ import annotations

from typing import Any

from engineering_os.performance import CONTRACT_VERSION
from engineering_os.performance.attribution import attach_attribution, prompt_version_status
from engineering_os.performance.cohorts import cohort_members, load_cohorts, snapshot
from engineering_os.performance.compare import pairwise
from engineering_os.performance.failures import taxonomy
from engineering_os.performance.insights import insight_for_aggregate, insight_for_comparison
from engineering_os.performance.metrics import (
    CONTINUOUS_METRICS,
    OUTCOME_METRICS,
    QUALITY_METRICS,
    compute_metric,
    group_by,
)
from engineering_os.performance.tiers import load_tiers
from engineering_os.performance.trends import trend

ALL_METRICS = list(OUTCOME_METRICS) + list(QUALITY_METRICS) + list(CONTINUOUS_METRICS) + ["cost_known_rate"]


def _yaml(path_name: str) -> dict[str, Any]:
    from pathlib import Path
    import yaml

    root = Path(__file__).resolve().parents[2]
    return yaml.safe_load((root / "config" / path_name).read_text(encoding="utf-8")) or {}


def load_configs(
    cohort_config: dict[str, Any] | None = None,
    tier_config: dict[str, Any] | None = None,
    comparison_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "cohorts": cohort_config or load_cohorts(),
        "tiers": tier_config or load_tiers(),
        "comparisons": comparison_config or _yaml("performance-comparisons.yaml"),
    }


def enrich_population(
    tasks: list[dict[str, Any]],
    model_rows: list[dict[str, Any]] | None = None,
    skill_rows: list[dict[str, Any]] | None = None,
    run_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    return attach_attribution(tasks, model_rows or [], skill_rows or [], run_rows or [])


def _ruleset(members: list[dict[str, Any]]) -> str:
    versions = {str(row.get("ruleset_version") or "phase3-v1") for row in members}
    if len(versions) > 1:
        return "MIXED"
    return next(iter(versions), "phase3-v1")


def _eval_contract(members: list[dict[str, Any]]) -> str | None:
    versions = {
        str((row.get("evaluation") or {}).get("contract_version"))
        for row in members
        if (row.get("evaluation") or {}).get("contract_version")
    }
    if not versions:
        return None
    if len(versions) > 1:
        return "MIXED"
    return next(iter(versions))


def run_engine(
    tasks: list[dict[str, Any]],
    *,
    configs: dict[str, Any] | None = None,
    metric_ids: list[str] | None = None,
    cohort_ids: list[str] | None = None,
    include_ui_hidden: bool = False,
) -> dict[str, Any]:
    cfg = configs or load_configs()
    cohort_file = cfg["cohorts"]
    tier_config = cfg["tiers"]
    comparison_file = cfg["comparisons"]
    p90 = int(tier_config.get("quantile_p90_min_n") or 20)
    p95 = int(tier_config.get("quantile_p95_min_n") or 40)
    wanted = metric_ids or ALL_METRICS
    aggregates: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    insights: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    trends: list[dict[str, Any]] = []
    membership: dict[str, list[dict[str, Any]]] = {}
    exclusions: dict[str, list[dict[str, str]]] = {}

    for cohort in cohort_file.get("cohorts") or []:
        if cohort_ids and cohort["cohort_id"] not in cohort_ids:
            continue
        if cohort.get("ui_default") is False and not include_ui_hidden and not cohort_ids:
            # still compute math_fixtures only when requested
            continue
        members, excluded = cohort_members(tasks, cohort, cohort_file)
        snap = snapshot(cohort, cohort_file)
        membership[cohort["cohort_id"]] = members
        exclusions[cohort["cohort_id"]] = excluded
        ruleset = _ruleset(members)
        eval_contract = _eval_contract(members)
        for metric_id in wanted:
            agg = compute_metric(metric_id, members, tier_config, p90, p95)
            agg.update(
                {
                    "cohort_id": cohort["cohort_id"],
                    "cohort_version": snap["cohort_version"],
                    "cohort_hash": snap["config_hash"],
                    "dimension_type": "cohort",
                    "dimension_value": cohort["cohort_id"],
                    "contract_version": CONTRACT_VERSION,
                    "phase3_ruleset_version": ruleset,
                    "phase4_contract_version": eval_contract,
                    "prompt_version_performance": prompt_version_status()["prompt_version_performance"],
                }
            )
            aggregates.append(agg)
            text = insight_for_aggregate(agg, cohort["cohort_id"])
            if text:
                insights.append({"kind": "aggregate", "body": text, "causal": False, "metric_id": metric_id})

        # Profile / model / skill slices for production_all and attribution cohorts.
        slice_dimensions: list[str] = []
        if cohort["cohort_id"] == "production_all":
            slice_dimensions = ["profile_name"]
        if cohort["cohort_id"] == "production_single_model":
            slice_dimensions = ["model"]
        if cohort["cohort_id"] == "production_single_skill":
            slice_dimensions = ["skill"]
        for dimension in slice_dimensions:
            grouped = group_by(members, dimension)
            for key, group in grouped.items():
                for metric_id in wanted:
                    if metric_id.startswith("quality_") and dimension == "model" and not group:
                        continue
                    agg = compute_metric(metric_id, group, tier_config, p90, p95)
                    agg.update(
                        {
                            "cohort_id": cohort["cohort_id"],
                            "cohort_version": snap["cohort_version"],
                            "cohort_hash": snap["config_hash"],
                            "dimension_type": dimension,
                            "dimension_value": key,
                            "contract_version": CONTRACT_VERSION,
                            "phase3_ruleset_version": ruleset,
                            "phase4_contract_version": eval_contract,
                            "observational": True,
                        }
                    )
                    aggregates.append(agg)

        fail_rows = taxonomy(members, tier_config)
        for row in fail_rows:
            row["cohort_id"] = cohort["cohort_id"]
        failures.extend(fail_rows)

    index: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for agg in aggregates:
        index[(agg["cohort_id"], agg["dimension_type"], agg["dimension_value"], agg["metric_id"])] = agg

    for pair in comparison_file.get("pairs") or []:
        cohort_id = pair["cohort_id"]
        members = membership.get(cohort_id) or []
        dimension = pair["dimension"]
        grouped = group_by(members, dimension)
        keys = sorted(grouped)
        metrics = pair.get("metric_ids") or ["lifecycle_completion_rate"]
        stratifiers = list(pair.get("stratifiers") or [])
        ruleset = _ruleset(members)
        eval_contract = _eval_contract(members)
        for metric_id in metrics:
            if metric_id not in wanted:
                continue
            for i, left_key in enumerate(keys):
                for right_key in keys[i + 1 :]:
                    left_agg = index.get((cohort_id, dimension, left_key, metric_id))
                    right_agg = index.get((cohort_id, dimension, right_key, metric_id))
                    if not left_agg:
                        left_agg = compute_metric(metric_id, grouped[left_key], tier_config, p90, p95)
                    if not right_agg:
                        right_agg = compute_metric(metric_id, grouped[right_key], tier_config, p90, p95)
                    compared = pairwise(
                        left_key,
                        right_key,
                        grouped[left_key],
                        grouped[right_key],
                        metric_id,
                        left_aggregate=left_agg,
                        right_aggregate=right_agg,
                        tier_config=tier_config,
                        comparison_config=tier_config,
                        left_ruleset=ruleset,
                        right_ruleset=ruleset,
                        left_eval_contract=eval_contract,
                        right_eval_contract=eval_contract,
                        stratifiers=stratifiers,
                    )
                    compared["comparison_set"] = pair["comparison_id"]
                    compared["cohort_id"] = cohort_id
                    compared["contract_version"] = CONTRACT_VERSION
                    comparisons.append(compared)
                    insights.append(
                        {
                            "kind": "comparison",
                            "body": insight_for_comparison(compared, cohort_id),
                            "causal": False,
                            "metric_id": metric_id,
                        }
                    )

    trend_spec = comparison_file.get("trends") or {}
    trend_cohort = trend_spec.get("cohort_id") or "production_all"
    trend_members = membership.get(trend_cohort) or []
    for metric_id in trend_spec.get("metric_ids") or []:
        if metric_id not in wanted:
            continue
        for mode, size in (
            ("calendar", int(trend_spec.get("calendar_days") or 30)),
            ("rolling", int(trend_spec.get("rolling_n") or 30)),
        ):
            trends.append(
                trend(
                    trend_members,
                    metric_id,
                    cohort_id=trend_cohort,
                    tier_config=tier_config,
                    comparison_config=tier_config,
                    ruleset=_ruleset(trend_members),
                    eval_contract=_eval_contract(trend_members),
                    mode=mode,
                    size=size,
                )
            )

    coverage = _coverage(tasks, membership.get("production_all") or [])
    return {
        "contract_version": CONTRACT_VERSION,
        "prompt_version_performance": prompt_version_status(),
        "aggregates": aggregates,
        "comparisons": comparisons,
        "insights": insights,
        "failures": failures,
        "trends": trends,
        "membership": {key: [f"{row['board']}:{row['task_id']}" for row in rows] for key, rows in membership.items()},
        "exclusions": exclusions,
        "coverage": coverage,
    }


def _coverage(all_tasks: list[dict[str, Any]], production: list[dict[str, Any]]) -> dict[str, Any]:
    def count(pred) -> int:
        return sum(1 for row in production if pred(row))

    n = len(production)
    return {
        "production_tasks": n,
        "outcome_covered": count(lambda r: r.get("final_outcome")),
        "first_pass_known": count(lambda r: r.get("first_pass_state") in {"PASS", "FAIL"}),
        "trace_covered": count(lambda r: r.get("trace_wall_seconds") is not None or r.get("llm_call_count") is not None),
        "model_covered": count(lambda r: r.get("model_attribution") in {"SINGLE_MODEL", "MIXED_MODEL"}),
        "single_model": count(lambda r: r.get("model_attribution") == "SINGLE_MODEL"),
        "mixed_model": count(lambda r: r.get("model_attribution") == "MIXED_MODEL"),
        "skill_covered": count(lambda r: r.get("skill_attribution") in {"SINGLE_SKILL", "MULTI_SKILL"}),
        "quality_evaluated": count(
            lambda r: (r.get("evaluation") or {}).get("eligibility") == "ELIGIBLE"
            and (r.get("evaluation") or {}).get("execution_status") == "COMPLETE"
        ),
        "cost_known": count(lambda r: str(r.get("cost_status") or "UNKNOWN") in {"AVAILABLE", "KNOWN"}),
        "profile_name_known": count(lambda r: bool(r.get("profile_name") or r.get("profile"))),
        "profile_config_version_known": 0,
        "prompt_version_known": 0,
    }
