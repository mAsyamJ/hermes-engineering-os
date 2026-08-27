"""Explain a derived outcome without LLM judgment."""

from __future__ import annotations

import argparse
import json
from typing import Any

from engineering_os.analytics.db import connect, fetch_one


def explain_task(board: str, task_id: str, connection: Any | None = None) -> dict[str, Any]:
    def _load(conn: Any) -> dict[str, Any]:
        outcome = fetch_one(
            conn,
            "SELECT * FROM task_outcomes WHERE board = %s AND task_id = %s",
            (board, task_id),
        )
        if not outcome:
            return {"task": task_id, "board": board, "status": "NOT_FOUND"}
        task = fetch_one(
            conn,
            "SELECT * FROM task_facts WHERE board = %s AND task_id = %s",
            (board, task_id),
        )
        runs = list(
            conn.execute(
                "SELECT * FROM run_facts WHERE board = %s AND task_id = %s ORDER BY started_at_source, run_id",
                (board, task_id),
            ).fetchall()
        )
        traces = list(
            conn.execute(
                "SELECT * FROM trace_facts WHERE board = %s AND task_id = %s",
                (board, task_id),
            ).fetchall()
        )
        git = fetch_one(
            conn, "SELECT * FROM git_facts WHERE board = %s AND task_id = %s", (board, task_id)
        )
        github = fetch_one(
            conn, "SELECT * FROM github_facts WHERE board = %s AND task_id = %s", (board, task_id)
        )
        return {
            "task": task_id,
            "board": board,
            "final_outcome": outcome["final_outcome"],
            "reason": outcome["reason"],
            "lifecycle_state": outcome["lifecycle_state"],
            "verification_state": outcome["verification_state"],
            "first_pass_state": outcome["first_pass_state"],
            "retry_count": outcome["retry_count"],
            "rework_status": outcome["rework_status"],
            "human_intervention_state": outcome["human_intervention_state"],
            "ruleset": outcome["ruleset_version"],
            "computed_at": outcome["computed_at"],
            "evidence": outcome["evidence"],
            "facts": {
                "task": task,
                "runs": runs,
                "traces": traces,
                "git": git,
                "github": github,
            },
        }

    if connection is not None:
        return _load(connection)
    with connect() as conn:
        return _load(conn)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    parser.add_argument("--board", default="retropick-markets-release")
    args = parser.parse_args()
    print(json.dumps(explain_task(args.board, args.task_id), default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
