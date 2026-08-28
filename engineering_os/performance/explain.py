"""WHY drilldown: denominator membership and exclusions."""

from __future__ import annotations

from typing import Any

from engineering_os.analytics.db import connect, fetch_all, fetch_one
from engineering_os.performance import CONTRACT_VERSION
from engineering_os.performance.engine import enrich_population, load_configs, run_engine
from engineering_os.performance.materialize import load_population


def explain_aggregate(
    metric_id: str,
    cohort_id: str,
    dimension_type: str = "cohort",
    dimension_value: str | None = None,
) -> dict[str, Any]:
    with connect() as connection:
        row = fetch_one(
            connection,
            """
            SELECT * FROM performance_aggregates
            WHERE is_current AND metric_id = %s AND cohort_id = %s
              AND dimension_type = %s AND dimension_value = %s
            """,
            (metric_id, cohort_id, dimension_type, dimension_value or cohort_id),
        )
        tasks = load_population(connection)
    configs = load_configs()
    result = run_engine(tasks, configs=configs, metric_ids=[metric_id], cohort_ids=[cohort_id], include_ui_hidden=True)
    members = result["membership"].get(cohort_id) or []
    excluded = result["exclusions"].get(cohort_id) or []
    match = None
    for agg in result["aggregates"]:
        if (
            agg["metric_id"] == metric_id
            and agg["dimension_type"] == dimension_type
            and agg["dimension_value"] == (dimension_value or cohort_id)
        ):
            match = agg
            break
    return {
        "status": "AVAILABLE" if match or row else "NOT_FOUND",
        "contract_version": CONTRACT_VERSION,
        "why": {
            "metric_id": metric_id,
            "cohort_id": cohort_id,
            "denominator": "known_n of the metric; UNKNOWN and NA are reported separately and not coerced to failure",
            "population_n": (match or row or {}).get("population_n") if isinstance(row, dict) or match else None,
            "known_n": (match or {}).get("known_n") if match else (row or {}).get("known_n"),
            "unknown_n": (match or {}).get("unknown_n") if match else (row or {}).get("unknown_n"),
            "na_n": (match or {}).get("na_n") if match else (row or {}).get("na_n"),
            "known_ids": (match or {}).get("known_ids") or [],
            "excluded": excluded[:50],
            "excluded_total": len(excluded),
            "member_total": len(members),
            "prompt_version_performance": "UNSUPPORTED_EVIDENCE",
            "causal": False,
        },
        "aggregate": match or row,
        "phase3_hint": "/analytics/tasks/{task_id}",
        "phase4_hint": "/evaluations/tasks/{task_id}",
    }


def explain_task(board: str, task_id: str) -> dict[str, Any]:
    with connect() as connection:
        outcome = fetch_one(
            connection,
            "SELECT * FROM task_outcomes WHERE board = %s AND task_id = %s",
            (board, task_id),
        )
        evaluation = fetch_one(
            connection,
            """
            SELECT r.*, s.quality_vector, s.summary_state
            FROM evaluation_runs r
            LEFT JOIN evaluation_summaries s ON s.evaluation_run_id = r.evaluation_run_id
            WHERE r.board = %s AND r.task_id = %s AND r.is_current
            """,
            (board, task_id),
        )
        models = fetch_all(
            connection,
            """
            SELECT m.* FROM run_model_usage m
            JOIN run_facts r ON r.board = m.board AND r.run_id = m.run_id
            WHERE r.board = %s AND r.task_id = %s
            """,
            (board, task_id),
        )
        skills = fetch_all(
            connection,
            """
            SELECT s.* FROM run_skill_usage s
            JOIN run_facts r ON r.board = s.board AND r.run_id = s.run_id
            WHERE r.board = %s AND r.task_id = %s
            """,
            (board, task_id),
        )
    if not outcome:
        return {"status": "NOT_FOUND", "board": board, "task_id": task_id}
    from engineering_os.performance.attribution import classify_model_attribution, classify_skill_attribution
    from engineering_os.performance.failures import labels_for

    models_attr = classify_model_attribution(models)
    skills_attr = classify_skill_attribution(skills)
    task = dict(outcome)
    task["evaluation"] = evaluation
    return {
        "status": "AVAILABLE",
        "contract_version": CONTRACT_VERSION,
        "board": board,
        "task_id": task_id,
        "outcome": outcome,
        "evaluation": evaluation,
        "model_attribution": models_attr,
        "skill_attribution": skills_attr,
        "profile_name": None,
        "profile_config_version": "UNKNOWN",
        "prompt_version_performance": "UNSUPPORTED_EVIDENCE",
        "failure_labels": labels_for(task),
        "causal": False,
    }
