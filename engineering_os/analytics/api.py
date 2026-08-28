"""Read-only analytics HTTP API. No write routes. Fail-open to Hermes."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from typing import Any

from engineering_os.analytics.db import connect
from engineering_os.analytics.explain import explain_task
from engineering_os.analytics.quality import coverage_sql, run_checks
from engineering_os.evaluation import CONTRACT_VERSION
from engineering_os.evaluation.explain import explain_evaluation, explain_task as explain_evaluation_task
from engineering_os.evaluation.profiles import list_profiles
from engineering_os.evaluation.quality import coverage_sql as evaluation_coverage_sql
from engineering_os.evaluation.quality import run_checks as evaluation_run_checks
from engineering_os.evaluation.registry import definitions as evaluator_definitions
from engineering_os.performance import CONTRACT_VERSION as PERF_CONTRACT
from engineering_os.performance.explain import explain_aggregate, explain_task as explain_performance_task
from engineering_os.performance.quality import coverage_sql as performance_coverage_sql
from engineering_os.performance.quality import run_checks as performance_run_checks
from engineering_os.experiments import api as experiments_api
from engineering_os.experiments.persist import health as experiments_health


def _json(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:
    body = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _query(path: str) -> tuple[str, dict[str, list[str]]]:
    parsed = urlparse(path)
    return parsed.path, parse_qs(parsed.query)


def _health() -> dict[str, Any]:
    try:
        with connect() as connection:
            last = connection.execute(
                """
                SELECT materialization_id, ended_at, status, tasks_scanned, tasks_changed, errors
                FROM materialization_runs
                WHERE status IN ('success', 'partial')
                ORDER BY ended_at DESC NULLS LAST
                LIMIT 1
                """
            ).fetchone()
            count = connection.execute("SELECT COUNT(*) AS n FROM task_outcomes").fetchone()
        return {
            "status": "AVAILABLE",
            "source": "analytics",
            "mode": "read-only",
            "last_materialization": last,
            "task_outcomes": (count or {}).get("n"),
        }
    except Exception as exc:
        return {
            "status": "DEGRADED",
            "source": "analytics",
            "mode": "read-only",
            "detail": f"{type(exc).__name__}: {exc}",
        }


def _coverage() -> dict[str, Any]:
    with connect() as connection:
        row = connection.execute(coverage_sql()).fetchone() or {}
        quality = run_checks(connection)
    return {"status": quality["status"], "coverage": dict(row), "violations": quality["violations"]}


def _summary() -> dict[str, Any]:
    health = _health()
    try:
        coverage = _coverage()
        with connect() as connection:
            recent = list(
                connection.execute(
                    """
                    SELECT o.task_id, o.board, t.status, o.final_outcome, o.evidence_grade,
                           o.github_evidence_state, o.git_evidence_state, o.retry_count,
                           o.first_pass_state, o.lifecycle_state, t.title
                    FROM task_outcomes o
                    JOIN task_facts t ON t.board = o.board AND t.task_id = o.task_id
                    WHERE o.production_cohort
                    ORDER BY o.computed_at DESC
                    LIMIT 25
                    """
                ).fetchall()
            )
    except Exception as exc:
        return {
            **health,
            "status": "DEGRADED" if health.get("status") == "AVAILABLE" else health.get("status"),
            "detail": f"{type(exc).__name__}: {exc}",
            "recent": [],
        }
    return {
        **health,
        "coverage": coverage.get("coverage"),
        "quality": coverage.get("status"),
        "recent": recent,
    }


def _tasks(query: dict[str, list[str]]) -> dict[str, Any]:
    limit = min(max(int((query.get("limit") or ["50"])[0]), 1), 200)
    offset = max(int((query.get("offset") or ["0"])[0]), 0)
    cohort = (query.get("cohort") or ["production"])[0]
    with connect() as connection:
        if cohort == "all":
            rows = list(
                connection.execute(
                    """
                    SELECT o.*, t.status, t.title
                    FROM task_outcomes o
                    JOIN task_facts t ON t.board = o.board AND t.task_id = o.task_id
                    ORDER BY o.computed_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                ).fetchall()
            )
        else:
            rows = list(
                connection.execute(
                    """
                    SELECT o.*, t.status, t.title
                    FROM task_outcomes o
                    JOIN task_facts t ON t.board = o.board AND t.task_id = o.task_id
                    WHERE o.production_cohort = TRUE
                    ORDER BY o.computed_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                ).fetchall()
            )
    return {"status": "AVAILABLE", "data": rows, "limit": limit, "offset": offset}


def _run(board: str, run_id: int) -> dict[str, Any]:
    with connect() as connection:
        run = connection.execute(
            "SELECT * FROM run_facts WHERE board = %s AND run_id = %s",
            (board, run_id),
        ).fetchone()
        if not run:
            return {"status": "NOT_FOUND", "board": board, "run_id": run_id}
        traces = list(
            connection.execute(
                "SELECT * FROM trace_facts WHERE board = %s AND run_id = %s",
                (board, str(run_id)),
            ).fetchall()
        )
        models = list(
            connection.execute(
                "SELECT * FROM run_model_usage WHERE board = %s AND run_id = %s",
                (board, run_id),
            ).fetchall()
        )
        skills = list(
            connection.execute(
                "SELECT * FROM run_skill_usage WHERE board = %s AND run_id = %s",
                (board, run_id),
            ).fetchall()
        )
    return {"status": "AVAILABLE", "run": run, "traces": traces, "models": models, "skills": skills}


def _materialization() -> dict[str, Any]:
    with connect() as connection:
        rows = list(
            connection.execute(
                """
                SELECT * FROM materialization_runs
                ORDER BY started_at DESC
                LIMIT 20
                """
            ).fetchall()
        )
    return {"status": "AVAILABLE", "data": rows}


def _evaluations_health() -> dict[str, Any]:
    try:
        with connect() as connection:
            last = connection.execute(
                """
                SELECT evaluation_run_id, ended_at, execution_status, eligibility
                FROM evaluation_runs
                WHERE is_current
                ORDER BY ended_at DESC NULLS LAST
                LIMIT 1
                """
            ).fetchone()
            count = connection.execute("SELECT COUNT(*) AS n FROM evaluation_runs").fetchone()
        return {
            "status": "AVAILABLE",
            "source": "evaluation",
            "mode": "read-only",
            "contract_version": CONTRACT_VERSION,
            "last_evaluation": last,
            "evaluation_runs": (count or {}).get("n"),
            "canonical_store": "hermes_engineering",
        }
    except Exception as exc:
        return {
            "status": "DEGRADED",
            "source": "evaluation",
            "mode": "read-only",
            "detail": f"{type(exc).__name__}: {exc}",
        }


def _evaluations_coverage() -> dict[str, Any]:
    with connect() as connection:
        row = connection.execute(evaluation_coverage_sql()).fetchone() or {}
        quality = evaluation_run_checks(connection)
    return {"status": quality["status"], "coverage": dict(row), "violations": quality["violations"]}


def _evaluations_recent() -> dict[str, Any]:
    with connect() as connection:
        rows = list(
            connection.execute(
                """
                SELECT r.evaluation_run_id, r.task_id, r.board, r.eligibility, r.execution_status,
                       r.profile_id, r.candidate_artifact_hash, s.summary_state, s.quality_vector
                FROM evaluation_runs r
                LEFT JOIN evaluation_summaries s ON s.evaluation_run_id = r.evaluation_run_id
                WHERE r.is_current
                ORDER BY r.started_at DESC
                LIMIT 25
                """
            ).fetchall()
        )
    return {"status": "AVAILABLE", "data": rows}


def _evaluations_summary() -> dict[str, Any]:
    health = _evaluations_health()
    try:
        coverage = _evaluations_coverage()
        recent = _evaluations_recent()
    except Exception as exc:
        return {
            **health,
            "status": "DEGRADED",
            "detail": f"{type(exc).__name__}: {exc}",
            "recent": [],
        }
    return {**health, "coverage": coverage.get("coverage"), "quality": coverage.get("status"), "recent": recent.get("data")}


def _limit_offset(query: dict[str, list[str]]) -> tuple[int, int]:
    limit = min(max(int((query.get("limit") or ["50"])[0]), 1), 200)
    offset = max(int((query.get("offset") or ["0"])[0]), 0)
    return limit, offset


def _performance_health() -> dict[str, Any]:
    try:
        with connect() as connection:
            last = connection.execute(
                """
                SELECT materialization_id, ended_at, status, aggregates_written, comparisons_written, errors
                FROM performance_materialization_runs
                WHERE status IN ('success', 'partial')
                ORDER BY ended_at DESC NULLS LAST
                LIMIT 1
                """
            ).fetchone()
            count = connection.execute(
                "SELECT COUNT(*) AS n FROM performance_aggregates WHERE is_current"
            ).fetchone()
        return {
            "status": "AVAILABLE",
            "source": "performance",
            "mode": "read-only",
            "contract_version": PERF_CONTRACT,
            "last_materialization": last,
            "current_aggregates": (count or {}).get("n"),
            "causal": False,
        }
    except Exception as exc:
        return {
            "status": "DEGRADED",
            "source": "performance",
            "mode": "read-only",
            "contract_version": PERF_CONTRACT,
            "detail": f"{type(exc).__name__}: {exc}",
        }


def _performance_coverage() -> dict[str, Any]:
    try:
        with connect() as connection:
            row = connection.execute(performance_coverage_sql()).fetchone() or {}
            quality = performance_run_checks(connection)
        return {"status": quality["status"], "coverage": dict(row), "violations": quality["violations"]}
    except Exception as exc:
        return {"status": "DEGRADED", "detail": f"{type(exc).__name__}: {exc}"}


def _performance_rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as connection:
        return list(connection.execute(sql, params).fetchall())


def _performance_summary() -> dict[str, Any]:
    health = _performance_health()
    try:
        coverage = _performance_coverage()
        outcomes = _performance_rows(
            """
            SELECT metric_id, population_n, known_n, unknown_n, na_n, coverage, value,
                   evidence_tier, interpretation, contract_version, computed_at, extras
            FROM performance_aggregates
            WHERE is_current AND cohort_id = 'production_all' AND dimension_type = 'cohort'
            ORDER BY metric_id
            """
        )
        insights = _performance_rows(
            """
            SELECT kind, body, causal, computed_at
            FROM performance_insights WHERE is_current
            ORDER BY computed_at DESC LIMIT 20
            """
        )
        failures = _performance_rows(
            """
            SELECT dimension_value AS label,
                   COALESCE((extras->>'count')::int, (extras->>'task_count')::int, 0) AS count,
                   population_n, known_n, unknown_n, coverage, value, unit,
                   evidence_tier, extras, computed_at, contract_version, cohort_id
            FROM performance_aggregates
            WHERE is_current AND dimension_type = 'failure' AND cohort_id = 'production_all'
            ORDER BY COALESCE((extras->>'count')::int, (extras->>'task_count')::int, 0) DESC
            """
        )
        profiles = _performance_rows(
            """
            SELECT dimension_value, metric_id, population_n, known_n, unknown_n,
                   coverage, value, evidence_tier, interpretation, contract_version
            FROM performance_aggregates
            WHERE is_current AND cohort_id = 'production_all'
              AND dimension_type = 'profile_name'
              AND metric_id = 'lifecycle_completion_rate'
            ORDER BY population_n DESC
            """
        )
        comparisons = _performance_rows(
            """
            SELECT comparison_set, metric_id, left_identity, right_identity,
                   left_n, right_n, left_estimate, right_estimate, absolute_difference,
                   relative_difference, left_tier, right_tier, comparability,
                   confounding_status, interpretation, computed_at
            FROM performance_comparisons
            WHERE is_current AND left_identity NOT LIKE 'prior:%%'
            ORDER BY metric_id, left_identity, right_identity
            LIMIT 20
            """
        )
        trends = _performance_rows(
            """
            SELECT comparison_set, metric_id, left_identity, right_identity,
                   left_n, right_n, left_estimate, right_estimate, interpretation,
                   confounding_status, computed_at
            FROM performance_comparisons
            WHERE is_current AND left_identity LIKE 'prior:%%'
            ORDER BY computed_at DESC
            LIMIT 20
            """
        )
    except Exception as exc:
        return {**health, "status": "DEGRADED", "detail": f"{type(exc).__name__}: {exc}"}
    return {
        **health,
        "coverage": coverage.get("coverage"),
        "quality": coverage.get("status"),
        "metrics": outcomes,
        "failures": failures,
        "profiles": profiles,
        "comparisons": comparisons,
        "trends": trends,
        "insights": insights,
        "ranking": None,
        "causal": False,
    }


def _performance_filtered(dimension: str | None, query: dict[str, list[str]]) -> dict[str, Any]:
    limit, offset = _limit_offset(query)
    metric = (query.get("metric") or [None])[0]
    cohort = (query.get("cohort") or ["production_all"])[0]
    clauses = ["is_current", "cohort_id = %s"]
    params: list[Any] = [cohort]
    if dimension:
        clauses.append("dimension_type = %s")
        params.append(dimension)
    if metric:
        clauses.append("metric_id = %s")
        params.append(metric)
    where = " AND ".join(clauses)
    rows = _performance_rows(
        f"""
        SELECT * FROM performance_aggregates
        WHERE {where}
        ORDER BY metric_id, dimension_value
        LIMIT %s OFFSET %s
        """,
        tuple(params + [limit, offset]),
    )
    return {
        "status": "AVAILABLE",
        "contract_version": PERF_CONTRACT,
        "data": rows,
        "limit": limit,
        "offset": offset,
        "causal": False,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802
        _json(self, 405, {"detail": "analytics API is read-only"})

    def do_PUT(self) -> None:  # noqa: N802
        _json(self, 405, {"detail": "analytics API is read-only"})

    def do_PATCH(self) -> None:  # noqa: N802
        _json(self, 405, {"detail": "analytics API is read-only"})

    def do_DELETE(self) -> None:  # noqa: N802
        _json(self, 405, {"detail": "analytics API is read-only"})

    def do_GET(self) -> None:  # noqa: N802
        path, query = _query(self.path)
        try:
            if path in {"/", "/summary"}:
                _json(self, 200, _summary())
                return
            if path == "/health":
                _json(self, 200, _health())
                return
            if path == "/coverage":
                _json(self, 200, _coverage())
                return
            if path == "/tasks":
                _json(self, 200, _tasks(query))
                return
            if path.startswith("/tasks/"):
                task_id = path.split("/", 2)[-1]
                board = (query.get("board") or ["retropick-markets-release"])[0]
                payload = explain_task(board, task_id)
                status = 404 if payload.get("status") == "NOT_FOUND" else 200
                _json(self, status, payload)
                return
            if path.startswith("/runs/"):
                run_id = int(path.rsplit("/", 1)[-1])
                board = (query.get("board") or ["retropick-markets-release"])[0]
                payload = _run(board, run_id)
                status = 404 if payload.get("status") == "NOT_FOUND" else 200
                _json(self, status, payload)
                return
            if path == "/materialization":
                _json(self, 200, _materialization())
                return
            if path in {"/evaluations", "/evaluations/health"}:
                _json(self, 200, _evaluations_health() if path.endswith("health") else _evaluations_summary())
                return
            if path == "/evaluations/coverage":
                _json(self, 200, _evaluations_coverage())
                return
            if path == "/evaluations/recent":
                _json(self, 200, _evaluations_recent())
                return
            if path == "/evaluations/profiles":
                _json(self, 200, {"status": "AVAILABLE", "data": list_profiles()})
                return
            if path == "/evaluations/evaluators":
                _json(
                    self,
                    200,
                    {
                        "status": "AVAILABLE",
                        "contract_version": CONTRACT_VERSION,
                        "data": evaluator_definitions(),
                    },
                )
                return
            if path.startswith("/evaluations/tasks/"):
                task_id = path.rsplit("/", 1)[-1]
                board = (query.get("board") or ["retropick-markets-release"])[0]
                payload = explain_evaluation_task(board, task_id)
                status = 404 if payload.get("status") == "NOT_FOUND" else 200
                _json(self, status, payload)
                return
            if path.startswith("/evaluations/runs/"):
                run_id = path.rsplit("/", 1)[-1]
                payload = explain_evaluation(run_id)
                status = 404 if payload.get("status") == "NOT_FOUND" else 200
                _json(self, status, payload)
                return
            if path.startswith("/evaluations/artifacts/"):
                artifact_id = path.rsplit("/", 1)[-1]
                with connect() as connection:
                    row = connection.execute(
                        "SELECT * FROM evaluation_artifacts WHERE artifact_id::text = %s OR content_hash = %s",
                        (artifact_id, artifact_id),
                    ).fetchone()
                status = 404 if not row else 200
                _json(self, status, {"status": "AVAILABLE" if row else "NOT_FOUND", "data": row})
                return
            if path in {"/performance", "/performance/summary"}:
                _json(self, 200, _performance_summary())
                return
            if path == "/performance/health":
                _json(self, 200, _performance_health())
                return
            if path == "/performance/coverage":
                _json(self, 200, _performance_coverage())
                return
            if path == "/performance/cohorts":
                _json(
                    self,
                    200,
                    {
                        "status": "AVAILABLE",
                        "data": _performance_rows(
                            """
                            SELECT DISTINCT cohort_id, cohort_version, cohort_hash
                            FROM performance_aggregates WHERE is_current
                            ORDER BY cohort_id
                            """
                        ),
                    },
                )
                return
            if path == "/performance/metrics":
                _json(self, 200, _performance_filtered(None, query))
                return
            if path == "/performance/models":
                _json(self, 200, _performance_filtered("model", query))
                return
            if path == "/performance/profiles":
                _json(self, 200, _performance_filtered("profile_name", query))
                return
            if path == "/performance/skills":
                _json(self, 200, _performance_filtered("skill", query))
                return
            if path == "/performance/failures":
                _json(
                    self,
                    200,
                    {
                        "status": "AVAILABLE",
                        "data": _performance_rows(
                            """
                            SELECT dimension_value AS label,
                                   COALESCE((extras->>'count')::int, (extras->>'task_count')::int, 0) AS count,
                                   population_n, known_n, unknown_n,
                                   coverage, value, unit, evidence_tier, extras, computed_at,
                                   contract_version, cohort_id
                            FROM performance_aggregates
                            WHERE is_current AND dimension_type = 'failure'
                            ORDER BY COALESCE((extras->>'count')::int, (extras->>'task_count')::int, 0) DESC
                            """
                        ),
                    },
                )
                return
            if path == "/performance/trends":
                _json(
                    self,
                    200,
                    {
                        "status": "AVAILABLE",
                        "data": _performance_rows(
                            """
                            SELECT * FROM performance_comparisons
                            WHERE is_current AND left_identity LIKE 'prior:%%'
                            ORDER BY computed_at DESC LIMIT 50
                            """
                        ),
                    },
                )
                return
            if path == "/performance/comparisons":
                limit, offset = _limit_offset(query)
                _json(
                    self,
                    200,
                    {
                        "status": "AVAILABLE",
                        "contract_version": PERF_CONTRACT,
                        "data": _performance_rows(
                            """
                            SELECT comparison_id, comparison_set, metric_id, left_identity, right_identity,
                                   left_n, right_n, left_estimate, right_estimate, absolute_difference,
                                   relative_difference, uncertainty, coverage, left_tier, right_tier,
                                   comparability, confounding_status, interpretation, strata, computed_at,
                                   contract_version
                            FROM performance_comparisons
                            WHERE is_current
                            ORDER BY metric_id, left_identity, right_identity
                            LIMIT %s OFFSET %s
                            """,
                            (limit, offset),
                        ),
                        "ranking": None,
                    },
                )
                return
            if path == "/performance/insights":
                _json(
                    self,
                    200,
                    {
                        "status": "AVAILABLE",
                        "data": _performance_rows(
                            """
                            SELECT kind, body, causal, computed_at
                            FROM performance_insights WHERE is_current
                            ORDER BY computed_at DESC LIMIT 100
                            """
                        ),
                    },
                )
                return
            if path.startswith("/performance/tasks/"):
                task_id = path.rsplit("/", 1)[-1]
                board = (query.get("board") or ["retropick-markets-release"])[0]
                payload = explain_performance_task(board, task_id)
                status = 404 if payload.get("status") == "NOT_FOUND" else 200
                _json(self, status, payload)
                return
            if path == "/performance/why":
                payload = explain_aggregate(
                    (query.get("metric") or ["lifecycle_completion_rate"])[0],
                    (query.get("cohort") or ["production_all"])[0],
                    (query.get("dimension_type") or ["cohort"])[0],
                    (query.get("dimension_value") or [None])[0],
                )
                _json(self, 200, payload)
                return
            if path in {"/experiments", "/experiments/health"}:
                _json(self, 200, experiments_health() if path.endswith("health") else experiments_api.summary())
                return
            if path == "/experiments/coverage":
                _json(self, 200, experiments_api.coverage())
                return
            if path.startswith("/experiments/"):
                rest = path[len("/experiments/") :]
                experiment_id, sep, suffix = rest.partition("/")
                if not sep:
                    payload = experiments_api.why(experiment_id)
                    status = 404 if payload.get("status") == "NOT_FOUND" else 200
                    _json(self, status, payload)
                    return
                mapping = {
                    "protocol": experiments_api.protocol,
                    "variants": experiments_api.variants,
                    "assignments": experiments_api.assignments,
                    "exposures": experiments_api.exposures,
                    "progress": experiments_api.progress,
                    "analysis": experiments_api.analysis,
                    "guardrails": experiments_api.guardrails,
                    "explain": experiments_api.why,
                }
                handler = mapping.get(suffix)
                if handler:
                    payload = handler(experiment_id)
                    status = 404 if payload.get("status") == "NOT_FOUND" else 200
                    _json(self, status, payload)
                    return
            _json(self, 404, {"detail": "not found"})
        except Exception as exc:
            _json(self, 200, {"status": "DEGRADED", "detail": f"{type(exc).__name__}: {exc}"})


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 9120), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
