"""Persist evaluation runs into hermes_engineering. Fail-open toward Hermes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from engineering_os.evaluation import CONTRACT_VERSION
from engineering_os.evaluation.engine import identity_hash


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _jsonb(value: Any) -> Any:
    from psycopg.types.json import Json

    return Json(value)


def persist_run(connection: Any, payload: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    identity = identity_hash(payload)
    existing = connection.execute(
        "SELECT evaluation_run_id FROM evaluation_runs WHERE identity_hash = %s AND is_current",
        (identity,),
    ).fetchone()
    if existing and not meta.get("recompute"):
        return {"status": "unchanged", "evaluation_run_id": existing["evaluation_run_id"], "identity_hash": identity}
    if existing and meta.get("recompute"):
        connection.execute(
            "UPDATE evaluation_runs SET is_current = FALSE WHERE identity_hash = %s",
            (identity,),
        )
    run_id = uuid.uuid4()
    candidate = payload.get("candidate_artifact") or {}
    baseline = payload.get("baseline_artifact") or {}
    artifact_id = meta.get("candidate_artifact_id")
    connection.execute(
        """
        INSERT INTO evaluation_runs (
            evaluation_run_id, board, task_id, kanban_run_id, cohort, eligibility,
            eligibility_reason, execution_status, contract_version, profile_id,
            profile_version, profile_hash, candidate_artifact_id, baseline_artifact_id,
            candidate_artifact_hash, baseline_artifact_hash, trace_id, is_current,
            identity_hash, started_at, ended_at, detail
        ) VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s,%s,%s,%s
        )
        """,
        (
            run_id,
            meta.get("board") or "eos-phase4-eval",
            meta.get("task_id") or "unknown",
            meta.get("kanban_run_id"),
            meta.get("cohort") or "fixture",
            payload.get("eligibility"),
            payload.get("reason") or meta.get("eligibility_reason") or "",
            payload.get("execution_status") or "COMPLETE",
            CONTRACT_VERSION,
            payload.get("profile_id"),
            payload.get("profile_version"),
            payload.get("profile_hash"),
            artifact_id,
            meta.get("baseline_artifact_id"),
            candidate.get("content_hash") or payload.get("candidate_tree_hash"),
            baseline.get("content_hash") or payload.get("baseline_tree_hash"),
            meta.get("trace_id"),
            identity,
            _now(),
            _now(),
            payload.get("reason"),
        ),
    )
    for key, result in (payload.get("results") or {}).items():
        evaluator_id, _, subject = key.partition(":")
        if not subject:
            subject = "candidate"
        connection.execute(
            """
            INSERT INTO evaluation_results (
                evaluation_run_id, evaluator_id, evaluator_version, category, subject,
                verdict, sandbox_tier, command, exit_code, duration_ms, tests_discovered,
                tests_passed, tests_failed, timeout, metrics, evidence
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                run_id,
                evaluator_id,
                "1",
                evaluator_id.split(".", 1)[-1].upper(),
                subject,
                result.get("verdict"),
                result.get("sandbox_tier") or "A",
                json_command(result.get("command")),
                result.get("exit_code"),
                result.get("duration_ms"),
                result.get("tests_discovered"),
                result.get("tests_passed"),
                result.get("tests_failed"),
                bool(result.get("timeout")),
                _jsonb({k: result.get(k) for k in ("resource_failure", "timeout")}),
                _jsonb({k: result.get(k) for k in ("stdout", "stderr", "detail") if result.get(k) is not None}),
            ),
        )
    for evaluator_id, classification in (payload.get("comparisons") or {}).items():
        connection.execute(
            """
            INSERT INTO evaluation_comparisons (evaluation_run_id, evaluator_id, classification)
            VALUES (%s,%s,%s)
            """,
            (run_id, evaluator_id, classification),
        )
    connection.execute(
        """
        INSERT INTO evaluation_summaries (evaluation_run_id, summary_state, quality_vector, reason)
        VALUES (%s,%s,%s,%s)
        """,
        (
            run_id,
            payload.get("summary_state"),
            _jsonb(payload.get("quality_vector") or {}),
            payload.get("reason") or "",
        ),
    )
    connection.execute(
        """
        INSERT INTO evaluation_evidence (evaluation_run_id, kind, ref, quality, body)
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (evaluation_run_id, kind, ref) DO NOTHING
        """,
        (
            run_id,
            "contract",
            CONTRACT_VERSION,
            "AVAILABLE",
            payload.get("reason"),
        ),
    )
    return {"status": "changed", "evaluation_run_id": str(run_id), "identity_hash": identity}


def json_command(command: Any) -> str | None:
    if command is None:
        return None
    if isinstance(command, list):
        return " ".join(str(item) for item in command)
    return str(command)


def persist_artifact(connection: Any, capture: dict[str, Any], meta: dict[str, Any]) -> str | None:
    digest = capture.get("content_hash")
    if not digest:
        return None
    existing = connection.execute(
        "SELECT artifact_id FROM evaluation_artifacts WHERE content_hash = %s",
        (digest,),
    ).fetchone()
    if existing:
        return str(existing["artifact_id"])
    artifact_id = uuid.uuid4()
    connection.execute(
        """
        INSERT INTO evaluation_artifacts (
            artifact_id, repository_id, board, task_id, kanban_run_id, method,
            base_commit, candidate_commit, patch_hash, content_hash, size_bytes,
            secret_scan_status, capture_detail, storage_path
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            artifact_id,
            meta.get("repository_id"),
            meta.get("board"),
            meta.get("task_id"),
            meta.get("kanban_run_id"),
            capture.get("method"),
            capture.get("base_commit"),
            capture.get("candidate_commit"),
            capture.get("patch_hash"),
            digest,
            capture.get("size_bytes") or 0,
            capture.get("secret_scan_status"),
            _jsonb({"detail": capture.get("detail")}),
            capture.get("storage_path"),
        ),
    )
    return str(artifact_id)


def persist_projection(connection: Any, evaluation_run_id: Any, result: dict[str, Any]) -> None:
    """Secondary Phoenix projection status. Canonical store remains hermes_engineering."""
    connection.execute(
        """
        INSERT INTO evaluation_projections (evaluation_run_id, target, status, identifier, detail)
        VALUES (%s, 'phoenix', %s, %s, %s)
        ON CONFLICT (evaluation_run_id) DO UPDATE
          SET status = EXCLUDED.status,
              identifier = EXCLUDED.identifier,
              detail = EXCLUDED.detail,
              updated_at = NOW()
        """,
        (
            evaluation_run_id,
            result.get("status") or "PENDING",
            result.get("identifier") or "phase4-eval-v1",
            result.get("detail") or result.get("status"),
        ),
    )
