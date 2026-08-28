"""Quality vector derivation. No canonical numeric score."""

from __future__ import annotations

from typing import Any

from engineering_os.evaluation.compare import classify
from engineering_os.evaluation.semantics import DIMENSIONS


def _verdict(results: dict[str, dict[str, Any]], evaluator_id: str, subject: str) -> str:
    row = results.get(f"{evaluator_id}:{subject}") or results.get(evaluator_id) or {}
    return str(row.get("verdict") or "NOT_APPLICABLE")


def derive_vector(
    results: dict[str, dict[str, Any]],
    comparisons: dict[str, str],
    eligibility: str,
    execution_status: str,
    github_state: str | None = None,
) -> dict[str, Any]:
    if eligibility == "INSUFFICIENT_EVIDENCE":
        vector = {name: "UNKNOWN" if name != "ci" else (github_state or "UNKNOWN") for name in DIMENSIONS}
        vector["acceptance"] = "UNKNOWN"
        return {
            "summary_state": "INSUFFICIENT_EVIDENCE",
            "quality_vector": vector,
            "reason": "no immutable candidate artifact; historical workspace bytes were not scored",
        }
    if execution_status == "ERROR":
        vector = {name: "UNKNOWN" for name in DIMENSIONS}
        return {
            "summary_state": "ERROR",
            "quality_vector": vector,
            "reason": "evaluation execution error",
        }
    tests = _verdict(results, "repo.tests", "candidate")
    build = _verdict(results, "repo.build", "candidate")
    lint = _verdict(results, "repo.lint", "candidate")
    typecheck = _verdict(results, "repo.typecheck", "candidate")
    security = _verdict(results, "repo.security", "candidate")
    architecture = _verdict(results, "repo.architecture_policy", "candidate")
    scope = _verdict(results, "repo.scope_policy", "candidate")
    acceptance = _verdict(results, "task.acceptance_checks", "candidate")
    ci = _verdict(results, "github.ci", "candidate")
    if github_state:
        ci = github_state
    regression = comparisons.get("repo.tests") or comparisons.get("repo.build") or "UNKNOWN"
    if tests == "PASS" and build in {"PASS", "NOT_APPLICABLE"}:
        correctness = "PASS"
    elif tests == "FAIL" or build == "FAIL":
        correctness = "FAIL"
    elif tests in {"NOT_APPLICABLE", "UNKNOWN"} and build == "PASS":
        correctness = "UNKNOWN"
    else:
        correctness = tests if tests != "NOT_APPLICABLE" else build
    vector = {
        "correctness": correctness,
        "build": build,
        "tests": tests,
        "regression": regression,
        "lint": lint,
        "typecheck": typecheck,
        "security": security,
        "architecture": architecture,
        "scope": scope,
        "acceptance": acceptance,
        "ci": ci,
    }
    if regression == "INTRODUCED_FAILURE" or correctness == "FAIL":
        summary = "VERIFIED_FAIL"
        reason = "candidate failed an objective evaluator relative to baseline or itself"
    elif correctness == "PASS" and regression in {"UNCHANGED_PASS", "FIXED_FAILURE", "NOT_APPLICABLE", "UNKNOWN"}:
        if any(vector[key] == "FAIL" for key in ("security", "architecture", "scope")):
            summary = "VERIFIED_FAIL"
            reason = "policy evaluator failed"
        elif any(vector[key] in {"UNKNOWN", "WARN"} for key in ("lint", "typecheck", "acceptance", "ci")):
            summary = "PARTIAL"
            reason = "core tests/build passed; some dimensions UNKNOWN/WARN/NA"
        else:
            summary = "VERIFIED_PASS"
            reason = "deterministic build/tests passed without introduced failures"
    else:
        summary = "PARTIAL"
        reason = "mixed or incomplete evaluator coverage"
    return {"summary_state": summary, "quality_vector": vector, "reason": reason}


DATA_QUALITY_CHECKS = [
    (
        "result_without_artifact",
        """
        SELECT r.evaluation_run_id FROM evaluation_runs r
        JOIN evaluation_results x ON x.evaluation_run_id = r.evaluation_run_id
        WHERE r.candidate_artifact_hash IS NULL
          AND r.eligibility IN ('ELIGIBLE', 'TEST_ELIGIBLE')
          AND x.verdict IN ('PASS', 'FAIL')
        """,
    ),
    (
        "pass_from_crash",
        """
        SELECT id FROM evaluation_results
        WHERE verdict = 'PASS' AND (metrics->>'timeout')::text = 'true'
        """,
    ),
    (
        "historical_scored_without_evidence",
        """
        SELECT evaluation_run_id FROM evaluation_runs
        WHERE eligibility = 'INSUFFICIENT_EVIDENCE'
          AND evaluation_run_id IN (
            SELECT evaluation_run_id FROM evaluation_results WHERE verdict IN ('PASS', 'FAIL')
          )
        """,
    ),
    (
        "phoenix_marked_canonical",
        """
        SELECT evaluation_run_id FROM evaluation_projections
        WHERE status = 'CANONICAL'
        """,
    ),
]


def run_checks(connection: Any) -> dict[str, Any]:
    violations = []
    for name, sql in DATA_QUALITY_CHECKS:
        rows = list(connection.execute(sql).fetchall())
        if rows:
            violations.append({"check": name, "count": len(rows), "sample": rows[:5]})
    return {"status": "FAIL" if violations else "PASS", "violations": violations}


def coverage_sql() -> str:
    return """
    SELECT
      COUNT(*) FILTER (WHERE cohort = 'production') AS production_tasks_seen,
      COUNT(*) FILTER (WHERE cohort = 'production' AND eligibility = 'ELIGIBLE') AS eligible,
      COUNT(*) FILTER (WHERE cohort = 'production' AND execution_status = 'COMPLETE'
                       AND eligibility IN ('ELIGIBLE','TEST_ELIGIBLE')) AS evaluated,
      COUNT(*) FILTER (WHERE eligibility = 'INSUFFICIENT_EVIDENCE') AS insufficient_evidence,
      COUNT(*) FILTER (WHERE eligibility IN ('NOT_APPLICABLE','EXCLUDED')) AS unsupported,
      COUNT(*) FILTER (WHERE s.summary_state = 'VERIFIED_PASS') AS verified_pass,
      COUNT(*) FILTER (WHERE s.summary_state = 'VERIFIED_FAIL') AS verified_fail,
      COUNT(*) FILTER (WHERE s.summary_state = 'PARTIAL') AS partial,
      COUNT(*) FILTER (WHERE s.summary_state = 'ERROR') AS error
    FROM evaluation_runs r
    LEFT JOIN evaluation_summaries s ON s.evaluation_run_id = r.evaluation_run_id
    WHERE r.is_current
    """


def main() -> int:
    import json
    from engineering_os.analytics.db import connect

    with connect() as connection:
        result = run_checks(connection)
        result["coverage"] = dict(connection.execute(coverage_sql()).fetchone() or {})
    print(json.dumps(result, default=str))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
