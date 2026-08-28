"""CLI: engineering-os evaluation. Never mutates Hermes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from engineering_os.analytics.db import advisory_unlock, connect, try_advisory_lock
from engineering_os.evaluation import ADVISORY_LOCK_KEY, CONTRACT_VERSION
from engineering_os.evaluation import eligibility as eligibility_lib
from engineering_os.evaluation.engine import evaluate_trees, identity_hash
from engineering_os.evaluation.explain import explain_task
from engineering_os.evaluation.persist import persist_run
from engineering_os.evaluation.profiles import load_profile
from engineering_os.evaluation.quality import coverage_sql, run_checks
from engineering_os.evaluation.registry import definitions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="engineering-os-evaluate")
    parser.add_argument("--task")
    parser.add_argument("--board", default="retropick-markets-release")
    parser.add_argument("--profile")
    parser.add_argument("--artifact")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--recompute", action="store_true")
    parser.add_argument("--explain", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--trees-candidate", type=Path)
    parser.add_argument("--trees-baseline", type=Path)
    return parser


def _insufficient_row(task_id: str, board: str, reason: str, cohort: str) -> dict[str, Any]:
    from engineering_os.evaluation.semantics import DIMENSIONS

    return {
        "contract_version": CONTRACT_VERSION,
        "profile_id": "none",
        "profile_version": "0",
        "profile_hash": "none",
        "eligibility": "INSUFFICIENT_EVIDENCE",
        "execution_status": "COMPLETE",
        "results": {},
        "comparisons": {},
        "summary_state": "INSUFFICIENT_EVIDENCE",
        "quality_vector": {name: "UNKNOWN" for name in DIMENSIONS},
        "reason": reason,
        "candidate_tree_hash": f"insufficient:{board}:{task_id}",
    }


def incremental(connection: Any, args: argparse.Namespace) -> dict[str, Any]:
    from engineering_os.analytics.db import fetch_all

    result: dict[str, Any] = {
        "status": "success",
        "tasks_scanned": 0,
        "tasks_evaluated": 0,
        "insufficient": 0,
        "unchanged": 0,
        "errors": 0,
        "contract_version": CONTRACT_VERSION,
    }
    if not try_advisory_lock(connection, ADVISORY_LOCK_KEY):
        result["status"] = "locked"
        return result
    try:
        rows = fetch_all(
            connection,
            """
            SELECT t.board, t.task_id, t.cohort, t.workspace_path, t.branch_name,
                   g.commit_sha, g.evidence_quality, g.repository_id, o.github_evidence_state
            FROM task_facts t
            JOIN task_outcomes o USING (board, task_id)
            LEFT JOIN git_facts g USING (board, task_id)
            """,
        )
        for row in rows:
            result["tasks_scanned"] += 1
            decision = eligibility_lib.classify_task(
                {
                    "id": row["task_id"],
                    "workspace_path": row["workspace_path"],
                    "branch_name": row["branch_name"],
                    "repository_id": row.get("repository_id"),
                },
                git={
                    "commit_sha": row.get("commit_sha"),
                    "evidence_quality": row.get("evidence_quality"),
                    "repository_id": row.get("repository_id"),
                },
                cohort=row["cohort"],
            )
            if decision["eligibility"] in {"ELIGIBLE", "TEST_ELIGIBLE"} and row.get("commit_sha"):
                result["tasks_evaluated"] += 1
                continue
            payload = _insufficient_row(
                row["task_id"],
                row["board"],
                decision["reason"],
                row["cohort"],
            )
            if args.dry_run:
                result["insufficient"] += 1
                continue
            persisted = persist_run(
                connection,
                payload,
                {
                    "board": row["board"],
                    "task_id": row["task_id"],
                    "cohort": row["cohort"],
                    "recompute": args.recompute,
                    "eligibility_reason": decision["reason"],
                },
            )
            if persisted.get("status") == "unchanged":
                result["unchanged"] += 1
            else:
                result["insufficient"] += 1
            connection.commit()
        connection.execute(
            """
            INSERT INTO evaluation_checkpoints (source, watermark, source_hash)
            VALUES ('evaluation:incremental', NOW()::text, %s)
            ON CONFLICT (source) DO UPDATE SET watermark = EXCLUDED.watermark, updated_at = NOW()
            """,
            (result.get("status"),),
        )
        connection.commit()
        return result
    finally:
        advisory_unlock(connection, ADVISORY_LOCK_KEY)
        connection.commit()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.explain and args.task:
        print(json.dumps(explain_task(args.board, args.task), default=str, indent=2))
        return 0
    if args.trees_candidate:
        profile = load_profile(args.profile or "fixture")
        payload = evaluate_trees(
            args.trees_candidate,
            profile,
            baseline=args.trees_baseline,
        )
        print(json.dumps(payload, default=str, indent=2 if not args.json else None))
        return 0
    with connect() as connection:
        if args.incremental:
            result = incremental(connection, args)
            if args.json:
                print(json.dumps(result, default=str))
            else:
                print(result)
            return 0 if result.get("status") in {"success", "locked"} else 1
        if args.task:
            from engineering_os.analytics.db import fetch_one

            row = fetch_one(
                connection,
                """
                SELECT t.*, g.commit_sha, g.evidence_quality, g.repository_id
                FROM task_facts t
                LEFT JOIN git_facts g USING (board, task_id)
                WHERE t.board = %s AND t.task_id = %s
                """,
                (args.board, args.task),
            )
            decision = eligibility_lib.classify_task(
                row,
                git=row or {},
                cohort=(row or {}).get("cohort") or "production",
            )
            payload = _insufficient_row(args.task, args.board, decision["reason"], "production")
            payload["eligibility"] = decision["eligibility"]
            if args.dry_run:
                print(json.dumps({"dry_run": True, **decision, **payload}, default=str))
                return 0
            persisted = persist_run(
                connection,
                payload,
                {"board": args.board, "task_id": args.task, "recompute": args.recompute},
            )
            connection.commit()
            print(json.dumps({"decision": decision, **persisted}, default=str))
            return 0
        coverage = connection.execute(coverage_sql()).fetchone()
        quality_status = run_checks(connection)
        print(
            json.dumps(
                {
                    "status": "AVAILABLE",
                    "contract_version": CONTRACT_VERSION,
                    "coverage": coverage,
                    "quality": quality_status,
                    "evaluators": [
                        {k: item[k] for k in ("evaluator_id", "evaluator_version", "category", "sandbox_tier")}
                        for item in definitions()
                    ],
                },
                default=str,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
