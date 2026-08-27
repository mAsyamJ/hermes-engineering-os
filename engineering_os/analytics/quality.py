"""Deterministic analytics data-quality checks."""

from __future__ import annotations

from typing import Any

CHECKS = [
    (
        "outcome_without_task_fact",
        """
        SELECT o.board, o.task_id FROM task_outcomes o
        LEFT JOIN task_facts t ON t.board = o.board AND t.task_id = o.task_id
        WHERE t.task_id IS NULL
        """,
    ),
    (
        "run_without_task_fact",
        """
        SELECT r.board, r.run_id, r.task_id FROM run_facts r
        LEFT JOIN task_facts t ON t.board = r.board AND t.task_id = r.task_id
        WHERE t.task_id IS NULL
        """,
    ),
    (
        "trace_task_mismatch",
        """
        SELECT tr.trace_id, tr.task_id, tr.board FROM trace_facts tr
        JOIN task_facts t ON t.board = tr.board AND t.task_id = tr.task_id
        WHERE tr.task_id IS NOT NULL AND t.task_id IS NOT NULL
          AND tr.task_id <> t.task_id
        """,
    ),
    (
        "negative_task_wall",
        "SELECT board, task_id, task_wall_seconds FROM task_outcomes WHERE task_wall_seconds < 0",
    ),
    (
        "first_pass_pass_with_retries",
        """
        SELECT board, task_id, first_pass_state, retry_count
        FROM task_outcomes
        WHERE first_pass_state = 'PASS' AND COALESCE(retry_count, 0) > 0
        """,
    ),
    (
        "verified_success_without_pass_verification",
        """
        SELECT board, task_id FROM task_outcomes
        WHERE final_outcome = 'VERIFIED_SUCCESS' AND verification_state <> 'PASS'
        """,
    ),
    (
        "human_intervention_false",
        """
        SELECT board, task_id, human_intervention_state FROM task_outcomes
        WHERE human_intervention_state IN ('false', 'FALSE', 'NOT_DETECTED')
          AND human_intervention_state = 'false'
        """,
    ),
    (
        "human_stored_as_false",
        """
        SELECT board, task_id FROM task_outcomes
        WHERE lower(human_intervention_state) IN ('false', 'no', '0')
        """,
    ),
]


def coverage_sql() -> str:
    return """
    SELECT
      COUNT(*) FILTER (WHERE production_cohort) AS eligible_production,
      COUNT(*) AS materialized,
      COUNT(*) FILTER (WHERE NOT production_cohort) AS excluded_or_fixture,
      COUNT(*) FILTER (WHERE production_cohort AND COALESCE(llm_call_count, tool_call_count) IS NOT NULL) AS with_trace_metrics,
      COUNT(*) FILTER (WHERE production_cohort AND git_evidence_state = 'AVAILABLE') AS with_git,
      COUNT(*) FILTER (WHERE production_cohort AND github_evidence_state = 'AVAILABLE') AS with_github,
      COUNT(*) FILTER (WHERE production_cohort AND github_evidence_state = 'BLOCKED_AUTH') AS github_blocked_auth,
      COUNT(*) FILTER (WHERE production_cohort AND verification_state = 'PASS') AS with_objective_verification,
      COUNT(*) FILTER (WHERE production_cohort AND first_pass_state = 'UNKNOWN') AS unknown_first_pass,
      COUNT(*) FILTER (WHERE production_cohort AND human_intervention_state = 'UNKNOWN') AS unknown_intervention,
      COUNT(*) FILTER (WHERE production_cohort AND final_outcome = 'VERIFIED_SUCCESS') AS verified_success,
      COUNT(*) FILTER (WHERE production_cohort AND final_outcome = 'COMPLETED_UNVERIFIED') AS completed_unverified,
      COUNT(*) FILTER (WHERE production_cohort AND final_outcome = 'VERIFIED_FAILURE') AS verified_failure,
      COUNT(*) FILTER (WHERE production_cohort AND final_outcome = 'INCOMPLETE') AS incomplete,
      COUNT(*) FILTER (WHERE production_cohort AND final_outcome = 'UNKNOWN') AS unknown_outcome
    FROM task_outcomes
    """


def run_checks(connection: Any) -> dict[str, Any]:
    violations = []
    for name, sql in CHECKS:
        rows = list(connection.execute(sql).fetchall())
        if rows:
            violations.append({"check": name, "count": len(rows), "sample": rows[:5]})
    coverage = connection.execute(coverage_sql()).fetchone() or {}
    return {
        "violations": violations,
        "coverage": dict(coverage),
        "status": "FAIL" if violations else "PASS",
    }


def main() -> int:
    import json
    from engineering_os.analytics.db import connect

    with connect() as connection:
        result = run_checks(connection)
    print(json.dumps(result, default=str))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

