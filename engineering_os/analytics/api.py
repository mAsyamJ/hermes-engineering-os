"""Read-only analytics HTTP API. No write routes. Fail-open to Hermes."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from typing import Any

from engineering_os.analytics.db import connect
from engineering_os.analytics.explain import explain_task
from engineering_os.analytics.quality import coverage_sql, run_checks


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
            _json(self, 404, {"detail": "not found"})
        except Exception as exc:
            _json(self, 200, {"status": "DEGRADED", "detail": f"{type(exc).__name__}: {exc}"})


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 9120), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
