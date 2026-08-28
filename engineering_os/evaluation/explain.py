"""WHY explanation for evaluation results."""

from __future__ import annotations

from typing import Any

from engineering_os.analytics.db import connect, fetch_one
from engineering_os.evaluation import CONTRACT_VERSION


def explain_evaluation(evaluation_run_id: str, connection: Any | None = None) -> dict[str, Any]:
    def _load(conn: Any) -> dict[str, Any]:
        run = fetch_one(
            conn,
            "SELECT * FROM evaluation_runs WHERE evaluation_run_id = %s",
            (evaluation_run_id,),
        )
        if not run:
            return {"status": "NOT_FOUND", "evaluation_run_id": evaluation_run_id}
        results = list(
            conn.execute(
                "SELECT * FROM evaluation_results WHERE evaluation_run_id = %s ORDER BY evaluator_id, subject",
                (evaluation_run_id,),
            ).fetchall()
        )
        comparisons = list(
            conn.execute(
                "SELECT * FROM evaluation_comparisons WHERE evaluation_run_id = %s",
                (evaluation_run_id,),
            ).fetchall()
        )
        summary = fetch_one(
            conn,
            "SELECT * FROM evaluation_summaries WHERE evaluation_run_id = %s",
            (evaluation_run_id,),
        )
        evidence = list(
            conn.execute(
                "SELECT * FROM evaluation_evidence WHERE evaluation_run_id = %s",
                (evaluation_run_id,),
            ).fetchall()
        )
        projection = fetch_one(
            conn,
            "SELECT * FROM evaluation_projections WHERE evaluation_run_id = %s",
            (evaluation_run_id,),
        )
        artifact = None
        if run.get("candidate_artifact_id"):
            artifact = fetch_one(
                conn,
                "SELECT * FROM evaluation_artifacts WHERE artifact_id = %s",
                (run["candidate_artifact_id"],),
            )
        return {
            "status": "AVAILABLE",
            "contract_version": CONTRACT_VERSION,
            "run": run,
            "summary": summary,
            "results": results,
            "comparisons": comparisons,
            "evidence": evidence,
            "artifact": artifact,
            "projection": projection,
            "canonical_store": "hermes_engineering",
        }

    if connection is not None:
        return _load(connection)
    with connect() as conn:
        return _load(conn)


def explain_task(board: str, task_id: str) -> dict[str, Any]:
    with connect() as conn:
        run = fetch_one(
            conn,
            """
            SELECT * FROM evaluation_runs
            WHERE board = %s AND task_id = %s AND is_current
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (board, task_id),
        )
        if not run:
            return {"status": "NOT_FOUND", "board": board, "task_id": task_id}
        payload = explain_evaluation(str(run["evaluation_run_id"]), connection=conn)
        payload["board"] = board
        payload["task_id"] = task_id
        return payload
