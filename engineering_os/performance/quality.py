"""Phase 5 data-quality invariants."""

from __future__ import annotations

from typing import Any

CHECKS = [
    (
        "denominator_lt_known",
        """
        SELECT aggregate_id, metric_id, population_n, known_n
        FROM performance_aggregates
        WHERE is_current AND known_n > population_n
        """,
    ),
    (
        "quality_includes_insufficient",
        """
        SELECT a.aggregate_id, a.metric_id
        FROM performance_aggregates a
        WHERE a.is_current
          AND a.metric_id LIKE 'quality_%'
          AND a.known_n > 0
          AND EXISTS (
            SELECT 1 FROM evaluation_runs e
            WHERE e.cohort = 'production' AND e.eligibility = 'INSUFFICIENT_EVIDENCE'
              AND e.is_current
              AND a.extras ? 'includes_insufficient'
          )
        """,
    ),
    (
        "fixture_in_production",
        """
        SELECT a.aggregate_id, a.cohort_id, a.metric_id
        FROM performance_aggregates a
        WHERE a.is_current
          AND a.cohort_id LIKE 'production%'
          AND (
            a.dimension_value IN ('t_eval_canary_a','t_eval_canary_b','t_eval_canary_c')
            OR a.dimension_value LIKE 't_eval_canary%'
          )
        """,
    ),
    (
        "single_model_contains_mixed",
        """
        SELECT a.aggregate_id FROM performance_aggregates a
        WHERE a.is_current AND a.cohort_id = 'production_single_model'
          AND a.dimension_type = 'model'
          AND a.extras->>'mixed' = 'true'
        """,
    ),
    (
        "profile_version_claimed",
        """
        SELECT a.aggregate_id FROM performance_aggregates a
        WHERE a.is_current
          AND a.extras->>'profile_config_version' IS NOT NULL
          AND a.extras->>'profile_config_version' NOT IN ('', 'UNKNOWN', 'None')
        """,
    ),
    (
        "not_comparable_numeric_effect",
        """
        SELECT comparison_id FROM performance_comparisons
        WHERE is_current AND comparability = 'NOT_COMPARABLE'
          AND absolute_difference IS NOT NULL
        """,
    ),
    (
        "insufficient_as_supported",
        """
        SELECT aggregate_id, metric_id, evidence_tier, known_n
        FROM performance_aggregates
        WHERE is_current AND evidence_tier = 'SUPPORTED' AND known_n < 100
        """,
    ),
    (
        "missing_coverage",
        """
        SELECT aggregate_id FROM performance_aggregates
        WHERE is_current AND coverage IS NULL AND population_n > 0 AND known_n > 0
        """,
    ),
    (
        "version_mismatch_comparable",
        """
        SELECT comparison_id FROM performance_comparisons
        WHERE is_current AND comparability = 'COMPARABLE'
          AND confounding_status IN ('RULESET_MISMATCH', 'EVALUATION_CONTRACT_MISMATCH')
        """,
    ),
]


def coverage_sql() -> str:
    return """
    SELECT
      (SELECT COUNT(*) FROM task_outcomes WHERE production_cohort) AS production_tasks,
      (SELECT COUNT(*) FROM performance_aggregates WHERE is_current) AS current_aggregates,
      (SELECT COUNT(*) FROM performance_comparisons WHERE is_current) AS current_comparisons,
      (SELECT COUNT(*) FROM performance_aggregates
         WHERE is_current AND metric_id LIKE 'quality_%' AND known_n = 0) AS quality_insufficient_rows,
      (SELECT COUNT(*) FROM performance_aggregates
         WHERE is_current AND cohort_id = 'production_all' AND dimension_type = 'cohort'
           AND metric_id = 'lifecycle_completion_rate') AS lifecycle_present
    """


def run_checks(connection: Any) -> dict[str, Any]:
    violations = []
    for name, sql in CHECKS:
        try:
            rows = list(connection.execute(sql).fetchall())
        except Exception as exc:
            violations.append({"check": name, "count": -1, "sample": [{"error": str(exc)}]})
            continue
        if rows:
            violations.append({"check": name, "count": len(rows), "sample": rows[:5]})
    coverage = connection.execute(coverage_sql()).fetchone() or {}
    return {
        "status": "PASS" if not violations else "FAIL",
        "violations": violations,
        "coverage": dict(coverage),
        "contract_version": "phase5-perf-v1",
    }


def main() -> int:
    import json
    from engineering_os.analytics.db import connect

    with connect() as connection:
        payload = run_checks(connection)
    print(json.dumps(payload, default=str))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
