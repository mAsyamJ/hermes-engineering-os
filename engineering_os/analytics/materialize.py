"""Deterministic analytics materializer. Fail-open toward Hermes."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from engineering_os.analytics import RULESET_VERSION
from engineering_os.analytics import adapters
from engineering_os.analytics.db import (
    advisory_unlock,
    connect,
    fetch_all,
    fetch_one,
    try_advisory_lock,
)
from engineering_os.analytics.normalize import canonical_hash, normalize_bundle
from engineering_os.analytics.rules import derive_outcome
from engineering_os.analytics.scope import load_scope
from engineering_os.models import EvidenceStatus
from integrations.github.local_git import resolve_repository_for_workspace

LOCK_KEY = 320260827


def _jsonb(value: Any) -> Any:
    from psycopg.types.json import Json

    return Json(value)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _gather(board: str, task_id: str) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    task = adapters.read_task(board, task_id)
    if task is None:
        return {"task": None, "board": board, "partial_source_failures": failures}
    runs = list(task.pop("runs", []) or [])
    events = list(task.pop("events", []) or [])
    comments = adapters.read_comment_authors(board, task_id)
    traces_evidence = adapters.phoenix_traces(task_id)
    traces = list(traces_evidence.data or []) if traces_evidence.status == EvidenceStatus.AVAILABLE else []
    if traces_evidence.status != EvidenceStatus.AVAILABLE:
        failures.append({"source": "phoenix", "detail": traces_evidence.detail or traces_evidence.status.value})
    git_payload: dict[str, Any] = {"evidence_quality": "UNKNOWN"}
    github_payload: dict[str, Any] = {"evidence_state": "UNKNOWN"}
    repository = None
    try:
        if task.get("workspace_path"):
            repository = resolve_repository_for_workspace(str(task["workspace_path"]))
    except KeyError:
        repository = None
    git_evidence = adapters.git_for_task(task)
    git_payload = dict(git_evidence.data or {})
    if git_evidence.status == EvidenceStatus.DEGRADED:
        failures.append({"source": "git", "detail": git_evidence.detail or "degraded"})
    github_evidence = adapters.github_for_task(task, repository)
    github_payload = dict(github_evidence.data or {})
    if github_evidence.status == EvidenceStatus.DEGRADED:
        failures.append({"source": "github", "detail": github_evidence.detail or "degraded"})
    return {
        "board": board,
        "task": task,
        "runs": runs,
        "events": events,
        "comments": comments,
        "traces": traces,
        "git": git_payload,
        "github": github_payload,
        "partial_source_failures": failures,
    }


def _upsert_task(connection: Any, board: str, task: dict[str, Any], source_hash: str) -> None:
    connection.execute(
        """
        INSERT INTO task_facts (
            board, task_id, title, status, assignee, created_at_source, started_at_source,
            completed_at_source, workspace_path, branch_name, profile, cohort, source_hash,
            ruleset_version
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (board, task_id) DO UPDATE SET
            title = EXCLUDED.title,
            status = EXCLUDED.status,
            assignee = EXCLUDED.assignee,
            created_at_source = EXCLUDED.created_at_source,
            started_at_source = EXCLUDED.started_at_source,
            completed_at_source = EXCLUDED.completed_at_source,
            workspace_path = EXCLUDED.workspace_path,
            branch_name = EXCLUDED.branch_name,
            profile = EXCLUDED.profile,
            cohort = EXCLUDED.cohort,
            source_hash = EXCLUDED.source_hash,
            ruleset_version = EXCLUDED.ruleset_version,
            materialized_at = NOW()
        """,
        (
            board,
            task["id"],
            task.get("title"),
            task.get("status"),
            task.get("assignee"),
            task.get("created_at"),
            task.get("started_at"),
            task.get("completed_at"),
            task.get("workspace_path"),
            task.get("branch_name"),
            task.get("assignee"),
            task.get("cohort"),
            source_hash,
            RULESET_VERSION,
        ),
    )


def _replace_children(connection: Any, board: str, task_id: str, bundle: dict[str, Any]) -> None:
    run_ids = [run["id"] for run in bundle.get("runs") or [] if run.get("id") is not None]
    if run_ids:
        connection.execute(
            "DELETE FROM run_model_usage WHERE board = %s AND run_id = ANY(%s)",
            (board, run_ids),
        )
        connection.execute(
            "DELETE FROM run_skill_usage WHERE board = %s AND run_id = ANY(%s)",
            (board, run_ids),
        )
    connection.execute("DELETE FROM run_facts WHERE board = %s AND task_id = %s", (board, task_id))
    for run in bundle.get("runs") or []:
        if run.get("id") is None:
            continue
        connection.execute(
            """
            INSERT INTO run_facts (
                board, run_id, task_id, profile, status, outcome, started_at_source,
                ended_at_source, qualifying, synthetic, source_hash
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (board, run_id) DO UPDATE SET
                status = EXCLUDED.status,
                outcome = EXCLUDED.outcome,
                started_at_source = EXCLUDED.started_at_source,
                ended_at_source = EXCLUDED.ended_at_source,
                qualifying = EXCLUDED.qualifying,
                synthetic = EXCLUDED.synthetic,
                source_hash = EXCLUDED.source_hash,
                materialized_at = NOW()
            """,
            (
                board,
                run["id"],
                task_id,
                run.get("profile"),
                run.get("status"),
                run.get("outcome"),
                run.get("started_at"),
                run.get("ended_at"),
                bool(run.get("qualifying")),
                bool(run.get("synthetic")),
                canonical_hash(run),
            ),
        )
    connection.execute(
        "DELETE FROM evidence_refs WHERE board = %s AND task_id = %s",
        (board, task_id),
    )
    for model in bundle.get("models") or []:
        if not model.get("model") or model.get("run_id") in (None, ""):
            continue
        try:
            run_id = int(model["run_id"])
        except (TypeError, ValueError):
            continue
        connection.execute(
            """
            INSERT INTO run_model_usage (board, run_id, model, provider, source, call_count)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (board, run_id, model, provider, source) DO UPDATE SET
                call_count = EXCLUDED.call_count
            """,
            (
                board,
                run_id,
                model["model"],
                model.get("provider") or "",
                model.get("source") or "trace",
                int(model.get("call_count") or 1),
            ),
        )
    for skill in bundle.get("skills") or []:
        if not skill.get("skill_name") or skill.get("run_id") in (None, ""):
            continue
        try:
            run_id = int(skill["run_id"])
        except (TypeError, ValueError):
            continue
        connection.execute(
            """
            INSERT INTO run_skill_usage (board, run_id, skill_name, source, call_count)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (board, run_id, skill_name, source) DO UPDATE SET
                call_count = EXCLUDED.call_count
            """,
            (
                board,
                run_id,
                skill["skill_name"],
                skill.get("source") or "span",
                int(skill.get("call_count") or 1),
            ),
        )
    for trace in bundle.get("traces") or []:
        if not trace.get("trace_id"):
            continue
        connection.execute(
            """
            INSERT INTO trace_facts (
                trace_id, board, task_id, run_id, session_id, llm_call_count, tool_call_count,
                error_count, trace_wall_seconds, llm_total_seconds, tool_total_seconds,
                token_prompt, token_completion, token_total, cost_status, phoenix_url,
                evidence_quality, source_hash
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (trace_id) DO UPDATE SET
                board = EXCLUDED.board,
                task_id = EXCLUDED.task_id,
                run_id = EXCLUDED.run_id,
                llm_call_count = EXCLUDED.llm_call_count,
                tool_call_count = EXCLUDED.tool_call_count,
                error_count = EXCLUDED.error_count,
                trace_wall_seconds = EXCLUDED.trace_wall_seconds,
                llm_total_seconds = EXCLUDED.llm_total_seconds,
                tool_total_seconds = EXCLUDED.tool_total_seconds,
                token_prompt = EXCLUDED.token_prompt,
                token_completion = EXCLUDED.token_completion,
                token_total = EXCLUDED.token_total,
                phoenix_url = EXCLUDED.phoenix_url,
                evidence_quality = EXCLUDED.evidence_quality,
                source_hash = EXCLUDED.source_hash,
                materialized_at = NOW()
            """,
            (
                trace["trace_id"],
                board,
                task_id,
                str(trace.get("hermes_kanban_run_id") or ""),
                trace.get("session_id"),
                trace.get("llm_calls"),
                trace.get("tool_calls"),
                trace.get("error_count"),
                trace.get("trace_wall_seconds"),
                trace.get("llm_total_seconds"),
                trace.get("tool_total_seconds"),
                trace.get("token_prompt"),
                trace.get("token_completion"),
                trace.get("token_total"),
                "UNKNOWN",
                trace.get("phoenix_url"),
                "AVAILABLE",
                canonical_hash(trace["trace_id"]),
            ),
        )
        connection.execute(
            """
            INSERT INTO evidence_refs (board, task_id, source, kind, ref, quality)
            VALUES (%s,%s,'phoenix','trace',%s,'AVAILABLE')
            ON CONFLICT (board, task_id, source, kind, ref) DO NOTHING
            """,
            (board, task_id, trace["trace_id"]),
        )
    git = bundle.get("git") or {}
    connection.execute(
        """
        INSERT INTO git_facts (
            board, task_id, repository_id, branch, commit_sha, dirty_at_observation,
            evidence_quality, source_hash
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (board, task_id) DO UPDATE SET
            repository_id = EXCLUDED.repository_id,
            branch = EXCLUDED.branch,
            commit_sha = EXCLUDED.commit_sha,
            dirty_at_observation = EXCLUDED.dirty_at_observation,
            evidence_quality = EXCLUDED.evidence_quality,
            source_hash = EXCLUDED.source_hash,
            materialized_at = NOW()
        """,
        (
            board,
            task_id,
            git.get("repository_id"),
            git.get("branch"),
            git.get("commit_sha"),
            git.get("dirty_at_observation"),
            git.get("evidence_quality") or "UNKNOWN",
            canonical_hash(git),
        ),
    )
    github = bundle.get("github") or {}
    connection.execute(
        """
        INSERT INTO github_facts (
            board, task_id, evidence_state, pr_number, pr_state, ci_conclusion, merged,
            detail, source_hash
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (board, task_id) DO UPDATE SET
            evidence_state = EXCLUDED.evidence_state,
            pr_number = EXCLUDED.pr_number,
            pr_state = EXCLUDED.pr_state,
            ci_conclusion = EXCLUDED.ci_conclusion,
            merged = EXCLUDED.merged,
            detail = EXCLUDED.detail,
            source_hash = EXCLUDED.source_hash,
            materialized_at = NOW()
        """,
        (
            board,
            task_id,
            github.get("evidence_state") or "UNKNOWN",
            github.get("pr_number"),
            github.get("pr_state"),
            github.get("ci_conclusion"),
            github.get("merged"),
            github.get("detail"),
            canonical_hash(github),
        ),
    )


def _write_outcome(connection: Any, board: str, task_id: str, outcome: dict[str, Any], source_hash: str) -> None:
    previous = fetch_one(
        connection,
        "SELECT final_outcome, source_hash, ruleset_version FROM task_outcomes WHERE board = %s AND task_id = %s",
        (board, task_id),
    )
    computed_at = _now()
    connection.execute(
        """
        INSERT INTO task_outcomes (
            board, task_id, ruleset_version, computed_at, lifecycle_state, verification_state,
            final_outcome, first_pass_state, retry_count, rework_status, rework_count,
            human_intervention_state, task_wall_seconds, run_wall_seconds, trace_wall_seconds,
            llm_total_seconds, tool_total_seconds, llm_call_count, tool_call_count, error_count,
            github_evidence_state, git_evidence_state, cost_status, skill_usage_status,
            model_usage_status, production_cohort, evidence_grade, reason, evidence, source_hash
        ) VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        )
        ON CONFLICT (board, task_id) DO UPDATE SET
            ruleset_version = EXCLUDED.ruleset_version,
            computed_at = EXCLUDED.computed_at,
            lifecycle_state = EXCLUDED.lifecycle_state,
            verification_state = EXCLUDED.verification_state,
            final_outcome = EXCLUDED.final_outcome,
            first_pass_state = EXCLUDED.first_pass_state,
            retry_count = EXCLUDED.retry_count,
            rework_status = EXCLUDED.rework_status,
            rework_count = EXCLUDED.rework_count,
            human_intervention_state = EXCLUDED.human_intervention_state,
            task_wall_seconds = EXCLUDED.task_wall_seconds,
            run_wall_seconds = EXCLUDED.run_wall_seconds,
            trace_wall_seconds = EXCLUDED.trace_wall_seconds,
            llm_total_seconds = EXCLUDED.llm_total_seconds,
            tool_total_seconds = EXCLUDED.tool_total_seconds,
            llm_call_count = EXCLUDED.llm_call_count,
            tool_call_count = EXCLUDED.tool_call_count,
            error_count = EXCLUDED.error_count,
            github_evidence_state = EXCLUDED.github_evidence_state,
            git_evidence_state = EXCLUDED.git_evidence_state,
            cost_status = EXCLUDED.cost_status,
            skill_usage_status = EXCLUDED.skill_usage_status,
            model_usage_status = EXCLUDED.model_usage_status,
            production_cohort = EXCLUDED.production_cohort,
            evidence_grade = EXCLUDED.evidence_grade,
            reason = EXCLUDED.reason,
            evidence = EXCLUDED.evidence,
            source_hash = EXCLUDED.source_hash
        """,
        (
            board,
            task_id,
            RULESET_VERSION,
            computed_at,
            outcome["lifecycle_state"],
            outcome["verification_state"],
            outcome["final_outcome"],
            outcome["first_pass_state"],
            outcome["retry_count"],
            outcome["rework_status"],
            outcome["rework_count"],
            outcome["human_intervention_state"],
            outcome["task_wall_seconds"],
            outcome["run_wall_seconds"],
            outcome["trace_wall_seconds"],
            outcome["llm_total_seconds"],
            outcome["tool_total_seconds"],
            outcome["llm_call_count"],
            outcome["tool_call_count"],
            outcome["error_count"],
            outcome["github_evidence_state"],
            outcome["git_evidence_state"],
            outcome["cost_status"],
            outcome["skill_usage_status"],
            outcome["model_usage_status"],
            outcome["production_cohort"],
            outcome["evidence_grade"],
            outcome["reason"],
            _jsonb(outcome["evidence"]),
            source_hash,
        ),
    )
    if (
        previous is None
        or previous["final_outcome"] != outcome["final_outcome"]
        or previous["source_hash"] != source_hash
        or previous["ruleset_version"] != RULESET_VERSION
    ):
        connection.execute(
            """
            INSERT INTO outcome_history (
                board, task_id, ruleset_version, computed_at, final_outcome, source_hash, reason
            ) VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                board,
                task_id,
                RULESET_VERSION,
                computed_at,
                outcome["final_outcome"],
                source_hash,
                outcome["reason"],
            ),
        )


def _restore_last_good_traces(connection: Any, board: str, task_id: str, raw: dict[str, Any]) -> None:
    failures = raw.get("partial_source_failures") or []
    if not any(item.get("source") == "phoenix" for item in failures):
        return
    rows = fetch_all(
        connection,
        "SELECT * FROM trace_facts WHERE board = %s AND task_id = %s",
        (board, task_id),
    )
    if not rows:
        return
    raw["traces"] = [
        {
            "trace_id": row["trace_id"],
            "hermes_kanban_run_id": row.get("run_id"),
            "session_id": row.get("session_id"),
            "llm_calls": row.get("llm_call_count"),
            "tool_calls": row.get("tool_call_count"),
            "error_count": row.get("error_count") or 0,
            "trace_wall_seconds": row.get("trace_wall_seconds"),
            "llm_total_seconds": row.get("llm_total_seconds"),
            "tool_total_seconds": row.get("tool_total_seconds"),
            "token_prompt": row.get("token_prompt"),
            "token_completion": row.get("token_completion"),
            "token_total": row.get("token_total"),
            "phoenix_url": row.get("phoenix_url"),
            "models": row.get("models") or [],
            "skills": row.get("skill_names") or [],
        }
        for row in rows
    ]


def materialize_task(
    connection: Any,
    board: str,
    task_id: str,
    scope: dict[str, Any],
    *,
    dry_run: bool,
    recompute: bool,
) -> dict[str, Any]:
    raw = _gather(board, task_id)
    if not dry_run:
        _restore_last_good_traces(connection, board, task_id, raw)
    if not raw.get("task"):
        return {"task_id": task_id, "board": board, "status": "missing"}
    bundle = normalize_bundle(raw, scope)
    outcome = derive_outcome(bundle, scope)
    source_hash = bundle["source_hash"]
    existing = fetch_one(
        connection,
        "SELECT source_hash FROM task_outcomes WHERE board = %s AND task_id = %s",
        (board, task_id),
    )
    unchanged = bool(existing and existing["source_hash"] == source_hash and not recompute)
    result = {
        "task_id": task_id,
        "board": board,
        "status": "unchanged" if unchanged else "changed",
        "final_outcome": outcome["final_outcome"],
        "reason": outcome["reason"],
        "partial_source_failures": bundle.get("partial_source_failures") or [],
        "production_cohort": outcome["production_cohort"],
        "source_hash": source_hash,
        "dry_run": dry_run,
    }
    if dry_run or unchanged:
        return result
    _upsert_task(connection, board, bundle["task"], source_hash)
    _replace_children(connection, board, task_id, bundle)
    _write_outcome(connection, board, task_id, outcome, source_hash)
    return result


def select_targets(args: argparse.Namespace, scope: dict[str, Any]) -> list[tuple[str, str]]:
    if args.task:
        boards = list(scope.get("included_boards") or []) + list(scope.get("canary_boards") or [])
        found: list[tuple[str, str]] = []
        for board in boards:
            if adapters.read_task(board, args.task):
                found.append((board, args.task))
        if not found:
            found = [(str((scope.get("included_boards") or ["retropick-markets-release"])[0]), args.task)]
        return found
    boards = list(scope.get("included_boards") or [])
    if args.canary:
        wanted = [str(item) for item in scope.get("canary_task_ids") or []]
        boards = list(dict.fromkeys(
            list(scope.get("canary_boards") or []) + list(scope.get("included_boards") or [])
        ))
        targets: list[tuple[str, str]] = []
        for task_id in wanted:
            for board in boards:
                if adapters.read_task(board, task_id):
                    targets.append((board, task_id))
                    break
        return targets
    since = None
    if args.since:
        try:
            since = int(args.since)
        except ValueError:
            since = None
    targets = []
    for board in boards:
        for task_id in adapters.iter_task_ids(board, since=since):
            targets.append((board, task_id))
    return targets


def run(args: argparse.Namespace) -> dict[str, Any]:
    scope = load_scope()
    if args.ruleset and args.ruleset != RULESET_VERSION:
        raise SystemExit(f"unsupported ruleset {args.ruleset}")
    materialization_id = str(uuid.uuid4())
    started = _now()
    mode = "dry-run" if args.dry_run else (
        "task" if args.task else "canary" if args.canary else "backfill" if args.backfill else "incremental"
    )
    result: dict[str, Any] = {
        "materialization_id": materialization_id,
        "started_at": started.isoformat(),
        "ruleset": RULESET_VERSION,
        "mode": mode,
        "tasks_scanned": 0,
        "tasks_changed": 0,
        "tasks_unchanged": 0,
        "errors": 0,
        "partial_source_failures": [],
        "status": "running",
        "tasks": [],
    }
    url = os.environ.get("ANALYTICS_DATABASE_URL")
    if not url and not args.dry_run:
        raise RuntimeError("ANALYTICS_DATABASE_URL is not set")
    if args.dry_run:
        targets = select_targets(args, scope)
        for board, task_id in targets:
            raw = _gather(board, task_id)
            if not raw.get("task"):
                result["errors"] += 1
                result["tasks"].append({"task_id": task_id, "status": "missing"})
                continue
            bundle = normalize_bundle(raw, scope)
            outcome = derive_outcome(bundle, scope)
            result["tasks_scanned"] += 1
            result["tasks_unchanged"] += 1
            result["tasks"].append(
                {
                    "task_id": task_id,
                    "board": board,
                    "final_outcome": outcome["final_outcome"],
                    "reason": outcome["reason"],
                    "dry_run": True,
                }
            )
        result["status"] = "success"
        result["ended_at"] = _now().isoformat()
        return result

    with connect() as connection:
        if not try_advisory_lock(connection):
            result["status"] = "locked"
            result["detail"] = "another materializer holds the advisory lock"
            return result
        try:
            connection.execute(
                """
                INSERT INTO materialization_runs (
                    materialization_id, started_at, ruleset_version, mode, status
                ) VALUES (%s,%s,%s,%s,'running')
                """,
                (materialization_id, started, RULESET_VERSION, mode),
            )
            connection.commit()
            targets = select_targets(args, scope)
            batch = int(scope.get("batch_size") or 10)
            for index, (board, task_id) in enumerate(targets, start=1):
                try:
                    item = materialize_task(
                        connection,
                        board,
                        task_id,
                        scope,
                        dry_run=args.dry_run,
                        recompute=args.recompute,
                    )
                    if not args.dry_run:
                        connection.commit()
                    result["tasks_scanned"] += 1
                    if item.get("status") == "changed":
                        result["tasks_changed"] += 1
                    else:
                        result["tasks_unchanged"] += 1
                    if item.get("partial_source_failures"):
                        result["partial_source_failures"].extend(item["partial_source_failures"])
                    result["tasks"].append(item)
                except Exception as exc:
                    connection.rollback()
                    result["errors"] += 1
                    result["tasks"].append(
                        {"task_id": task_id, "board": board, "status": "error", "detail": f"{type(exc).__name__}: {exc}"}
                    )
                if index % batch == 0:
                    time.sleep(0.05)
            ended = _now()
            status = "success" if result["errors"] == 0 else "partial"
            connection.execute(
                """
                UPDATE materialization_runs SET
                    ended_at = %s,
                    tasks_scanned = %s,
                    tasks_changed = %s,
                    tasks_unchanged = %s,
                    errors = %s,
                    partial_source_failures = %s,
                    status = %s
                WHERE materialization_id = %s
                """,
                (
                    ended,
                    result["tasks_scanned"],
                    result["tasks_changed"],
                    result["tasks_unchanged"],
                    result["errors"],
                    _jsonb(result["partial_source_failures"]),
                    status,
                    materialization_id,
                ),
            )
            boards = sorted({item.get("board") for item in result["tasks"] if item.get("board")})
            for board in boards:
                connection.execute(
                    """
                    INSERT INTO source_checkpoints (source, watermark, source_hash, materialization_id)
                    VALUES (%s,%s,%s,%s)
                    ON CONFLICT (source) DO UPDATE SET
                        watermark = EXCLUDED.watermark,
                        source_hash = EXCLUDED.source_hash,
                        materialization_id = EXCLUDED.materialization_id,
                        updated_at = NOW()
                    """,
                    (
                        f"hermes:board:{board}",
                        ended.isoformat(),
                        materialization_id,
                        materialization_id,
                    ),
                )
            connection.commit()
            result["status"] = status
            result["ended_at"] = ended.isoformat()
        finally:
            advisory_unlock(connection)
            connection.commit()
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="analytics-materialize")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--task")
    parser.add_argument("--since")
    parser.add_argument("--backfill", action="store_true")
    parser.add_argument("--canary", action="store_true")
    parser.add_argument("--recompute", action="store_true")
    parser.add_argument("--ruleset", default=RULESET_VERSION)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(args)
    if args.json or True:
        print(json.dumps(result, default=str))
    return 0 if result.get("status") in {"success", "locked"} or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
