"""Phase 6 data-quality invariants."""

from __future__ import annotations

from typing import Any

CHECKS = [
    (
        "post_outcome_assignment",
        """
        SELECT a.unit_id
        FROM experiment_assignments a
        JOIN experiment_observations o ON o.protocol_id = a.protocol_id AND o.unit_id = a.unit_id
        WHERE o.collected_at < a.assigned_at
        """,
    ),
    (
        "arm_mutation",
        """
        SELECT unit_id FROM experiment_assignments
        GROUP BY protocol_id, unit_id
        HAVING COUNT(DISTINCT variant_role) > 1
        """,
    ),
    (
        "double_arm_unit",
        """
        SELECT unit_id FROM experiment_assignments
        GROUP BY protocol_id, unit_id
        HAVING COUNT(*) > 1
        """,
    ),
    (
        "result_missing_versions",
        """
        SELECT result_id FROM experiment_results
        WHERE is_current AND (
            source_versions->>'phase6_contract' IS NULL
            OR source_versions->>'analysis_version' IS NULL
        )
        """,
    ),
    (
        "confirmatory_before_horizon",
        """
        SELECT result_id, conclusion FROM experiment_results
        WHERE is_current
          AND conclusion IN ('EVIDENCE_FOR_CANDIDATE','EVIDENCE_AGAINST_CANDIDATE')
          AND COALESCE((extras->>'horizon_reached')::boolean, false) = false
        """,
    ),
    (
        "fixture_in_production_result",
        """
        SELECT r.result_id
        FROM experiment_results r
        JOIN experiment_protocol_versions p ON p.protocol_id = r.protocol_id
        WHERE r.is_current AND p.scope = 'FIXTURE'
          AND r.extras->>'production_claim' = 'true'
        """,
    ),
    (
        "itt_reassigned",
        """
        SELECT e.unit_id
        FROM experiment_exposures e
        WHERE e.reassigned IS TRUE
        """,
    ),
    (
        "unknown_primary_dropped",
        """
        SELECT o.unit_id
        FROM experiment_observations o
        WHERE o.role = 'primary' AND o.known IS NULL
        """,
    ),
]


def run_checks(connection: Any) -> dict[str, Any]:
    violations = []
    for name, sql in CHECKS:
        try:
            rows = list(connection.execute(sql).fetchall())
        except Exception as exc:
            violations.append({"check": name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        if rows:
            violations.append({"check": name, "count": len(rows), "sample": dict(rows[0])})
    return {"status": "PASS" if not violations else "FAIL", "violations": violations}


def coverage_sql() -> str:
    return """
    SELECT
      (SELECT COUNT(*) FROM experiment_protocol_versions) AS protocols,
      (SELECT COUNT(*) FROM experiment_assignments) AS assignments,
      (SELECT COUNT(*) FROM experiment_observations) AS observations,
      (SELECT COUNT(*) FROM experiment_results WHERE is_current) AS current_results,
      (SELECT COUNT(*) FROM experiment_protocol_versions WHERE scope = 'PRODUCTION') AS production_protocols
    """


def main() -> int:
    import json
    from engineering_os.analytics.db import connect

    with connect() as connection:
        payload = run_checks(connection)
        payload["coverage"] = dict(connection.execute(coverage_sql()).fetchone() or {})
        payload["contract_version"] = "phase6-exp-v1"
    print(json.dumps(payload, default=str))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
