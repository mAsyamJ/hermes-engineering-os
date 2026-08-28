"""Persist adaptation control state into hermes_control. Fail-open toward Hermes."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from engineering_os.adaptation import (
    ADVISORY_LOCK_KEY,
    ANALYTICS_LOCK_KEY,
    CONTRACT_VERSION,
    EVALUATION_LOCK_KEY,
    EXPERIMENT_LOCK_KEY,
    PERFORMANCE_LOCK_KEY,
    PRODUCTION_APPROVAL,
    PRODUCTION_RECOMMENDATION,
    RUNTIME_INTEGRATION,
)
from engineering_os.adaptation.approval import (
    ApprovalError,
    approve_production,
    ensure_test_key,
    sign_test,
    verify_test,
)
from engineering_os.adaptation.audit import event as audit_event
from engineering_os.adaptation.canary import run_fixture_canary
from engineering_os.adaptation.compiler import compile_policy
from engineering_os.adaptation.db import (
    advisory_unlock,
    analytics_url,
    connect,
    fetch_all,
    fetch_one,
    jsonb,
    try_advisory_lock,
)
from engineering_os.adaptation.guardrails import canary_health, evaluate as eval_guardrails
from engineering_os.adaptation.recommend import recommend_from_result
from engineering_os.adaptation.resolver import (
    engage_kill_switch,
    load_cache,
    resolve_policy,
    write_cache,
)
from engineering_os.adaptation.schema import load_id, load_path
from engineering_os.adaptation.shadow import production_task_context, shadow_batch
from pathlib import Path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def advisory_held(connection: Any, key: int) -> bool:
    row = connection.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM pg_locks
            WHERE locktype = 'advisory' AND classid = 0 AND objid = %s AND granted
        ) AS held
        """,
        (key,),
    ).fetchone()
    return bool(row and row["held"])


def _lock(connection: Any) -> dict[str, Any] | None:
    if not try_advisory_lock(connection, ADVISORY_LOCK_KEY):
        return {"status": "locked", "contract_version": CONTRACT_VERSION, "detail": "adaptation lock held"}
    for key, name in (
        (ANALYTICS_LOCK_KEY, "analytics"),
        (EVALUATION_LOCK_KEY, "evaluation"),
        (PERFORMANCE_LOCK_KEY, "performance"),
        (EXPERIMENT_LOCK_KEY, "experiment"),
    ):
        if advisory_held(connection, key):
            advisory_unlock(connection, ADVISORY_LOCK_KEY)
            return {
                "status": "locked",
                "contract_version": CONTRACT_VERSION,
                "detail": f"{name} materialization in progress",
            }
    return None


def _audit(connection: Any, **kwargs: Any) -> None:
    row = audit_event(**kwargs)
    connection.execute(
        """
        INSERT INTO adaptation_audit_log (
            event_id, occurred_at, actor_class, actor_identity, action, object_type,
            object_id, previous_state_hash, new_state_hash, reason, source_evidence
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            row["event_id"],
            row["occurred_at"],
            row["actor_class"],
            row["actor_identity"],
            row["action"],
            row["object_type"],
            row["object_id"],
            row["previous_state_hash"],
            row["new_state_hash"],
            row["reason"],
            jsonb(row["source_evidence"]),
        ),
    )


def snapshot_contract(connection: Any) -> None:
    spec = {"contract_version": CONTRACT_VERSION, "auto_promote": False, "production_actuation": "DISABLED"}
    connection.execute(
        """
        INSERT INTO adaptation_contract_snapshots (contract_version, config_hash, spec)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        (CONTRACT_VERSION, CONTRACT_VERSION, jsonb(spec)),
    )


def load_experiment_result(experiment_id: str) -> dict[str, Any]:
    url = analytics_url()
    if not url:
        raise RuntimeError("ANALYTICS_DATABASE_URL is required to read Phase 6 results")
    with connect(url) as connection:
        row = fetch_one(
            connection,
            """
            SELECT p.experiment_id, p.protocol_version, p.state, p.scope, p.design,
                   p.treatment_dimension, p.pre_registration_hash, p.candidate_config_hash,
                   p.control_config_hash, p.phase6_contract, p.spec,
                   r.conclusion, r.reason, r.validity, r.effect_estimate, r.known_n, r.missing_n
            FROM experiment_protocol_versions p
            LEFT JOIN experiment_results r ON r.protocol_id = p.protocol_id AND r.is_current
            WHERE p.experiment_id = %s
            ORDER BY p.frozen_at DESC NULLS LAST
            LIMIT 1
            """,
            (experiment_id,),
        )
    if not row:
        raise RuntimeError(f"experiment not found: {experiment_id}")
    validity = row.get("validity") or {}
    if isinstance(validity, str):
        import json

        validity = json.loads(validity)
    return {
        "source": "phase6",
        "experiment_id": row["experiment_id"],
        "conclusion": row.get("conclusion"),
        "reason": row.get("reason") or "",
        "scope": row.get("scope"),
        "treatment_dimension": row.get("treatment_dimension"),
        "validity": validity,
        "guardrail_state": "PASS",
        "protocol_hash": row.get("pre_registration_hash"),
        "candidate_config_hash": row.get("candidate_config_hash"),
        "control_config_hash": row.get("control_config_hash"),
        "phase6_contract": row.get("phase6_contract"),
        "contamination": False,
        "state": row.get("state"),
    }


def recommend(experiment_id: str, *, actor: str = "operator") -> dict[str, Any]:
    result = load_experiment_result(experiment_id)
    payload = recommend_from_result(result)
    with connect() as connection:
        locked = _lock(connection)
        if locked:
            return locked
        try:
            snapshot_contract(connection)
            rec_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO adaptation_recommendations (
                    recommendation_id, experiment_id, protocol_hash, conclusion, classification,
                    state, treatment_dimension, scope, source, reason, production_promotable
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    rec_id,
                    experiment_id,
                    payload["source_result"].get("protocol_hash"),
                    result.get("conclusion"),
                    payload["classification"],
                    payload["state"],
                    result.get("treatment_dimension"),
                    result.get("scope"),
                    jsonb(payload["source_result"]),
                    payload["reason"],
                    payload["production_promotable"],
                ),
            )
            _audit(
                connection,
                action="recommendation",
                actor_class="operator",
                actor_identity=actor,
                object_type="recommendation",
                object_id=rec_id,
                new_state_hash=payload.get("recommendation_hash"),
                reason=payload["reason"],
                source_evidence={"experiment_id": experiment_id, "classification": payload["classification"]},
            )
            connection.commit()
            payload["recommendation_id"] = rec_id
            return payload
        finally:
            advisory_unlock(connection, ADVISORY_LOCK_KEY)


def _load_recommendation(connection: Any, recommendation_id: str) -> dict[str, Any] | None:
    return fetch_one(connection, "SELECT * FROM adaptation_recommendations WHERE recommendation_id::text = %s", (recommendation_id,))


def compile_and_store(recommendation_id: str, policy_ref: str, *, actor: str = "operator") -> dict[str, Any]:
    with connect() as connection:
        locked = _lock(connection)
        if locked:
            return locked
        try:
            rec = _load_recommendation(connection, recommendation_id)
            if not rec:
                return {"status": "not_found", "recommendation_id": recommendation_id}
            rec_payload = {
                "classification": rec["classification"],
                "state": rec["state"],
                "recommendation_hash": rec["protocol_hash"],
                "source_result": rec["source"],
                "experiment_id": rec["experiment_id"],
                "treatment_dimension": rec["treatment_dimension"],
                "scope": rec["scope"],
            }
            compiled = compile_policy(rec_payload, policy_ref)
            spec = compiled["spec"]
            connection.execute(
                """
                INSERT INTO adaptation_policy_bundles (
                    policy_id, policy_version, policy_hash, source_recommendation_id, spec,
                    candidate_config_hash, fallback_config_hash, scope, treatment_dimension
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (policy_hash) DO NOTHING
                """,
                (
                    compiled["policy_id"],
                    compiled["policy_version"],
                    compiled["policy_hash"],
                    rec["recommendation_id"],
                    jsonb(spec),
                    compiled["candidate_config_hash"],
                    compiled["fallback_config_hash"],
                    compiled["scope"],
                    compiled["treatment_dimension"],
                ),
            )
            _audit(
                connection,
                action="compile-policy",
                actor_class="operator",
                actor_identity=actor,
                object_type="policy",
                object_id=compiled["policy_hash"],
                new_state_hash=compiled["policy_hash"],
                reason="immutable bundle stored",
                source_evidence={"recommendation_id": recommendation_id, "policy_id": compiled["policy_id"]},
            )
            connection.commit()
            return compiled
        finally:
            advisory_unlock(connection, ADVISORY_LOCK_KEY)


def _bundle(connection: Any, policy_ref: str) -> dict[str, Any] | None:
    row = fetch_one(
        connection,
        """
        SELECT * FROM adaptation_policy_bundles
        WHERE policy_hash = %s OR policy_id = %s
        ORDER BY created_at DESC LIMIT 1
        """,
        (policy_ref, policy_ref),
    )
    return row


def request_approval(policy_ref: str, *, stage: str = "A", actor: str = "operator") -> dict[str, Any]:
    with connect() as connection:
        locked = _lock(connection)
        if locked:
            return locked
        try:
            bundle = _bundle(connection, policy_ref)
            if not bundle:
                return {"status": "not_found"}
            approval_id = str(uuid.uuid4())
            expires = _now() + timedelta(days=7)
            connection.execute(
                """
                INSERT INTO adaptation_approvals (
                    approval_id, recommendation_id, policy_hash, policy_version, stage,
                    approval_class, scope, max_exposure, expires_at, rollback_hash,
                    operator_identity, signature, algorithm, state
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    approval_id,
                    bundle.get("source_recommendation_id"),
                    bundle["policy_hash"],
                    bundle["policy_version"],
                    stage,
                    "TEST",
                    bundle["scope"],
                    (bundle["spec"] or {}).get("canary", {}).get("max_units") or 4,
                    expires,
                    bundle["fallback_config_hash"],
                    actor,
                    "",
                    "approve-hmac-sha256-v1-test",
                    "REQUESTED",
                ),
            )
            _audit(
                connection,
                action="request-approval",
                actor_class="operator",
                actor_identity=actor,
                object_type="approval",
                object_id=approval_id,
                new_state_hash=bundle["policy_hash"],
                reason=f"stage {stage} requested",
            )
            connection.commit()
            return {"status": "success", "approval_id": approval_id, "state": "REQUESTED", "stage": stage}
        finally:
            advisory_unlock(connection, ADVISORY_LOCK_KEY)


def approve_test(policy_ref: str, *, stage: str = "A", actor: str = "test-operator") -> dict[str, Any]:
    ensure_test_key()
    with connect() as connection:
        locked = _lock(connection)
        if locked:
            return locked
        try:
            bundle = _bundle(connection, policy_ref)
            if not bundle:
                return {"status": "not_found"}
            rec = _load_recommendation(connection, str(bundle.get("source_recommendation_id") or ""))
            expires = (_now() + timedelta(days=7)).isoformat()
            fields = {
                "stage": stage,
                "approval_class": "TEST",
                "recommendation_id": str(bundle.get("source_recommendation_id") or ""),
                "policy_hash": bundle["policy_hash"],
                "policy_version": bundle["policy_version"],
                "scope": bundle["scope"],
                "max_exposure": (bundle["spec"] or {}).get("canary", {}).get("max_units") or 4,
                "expires_at": expires,
                "rollback_hash": bundle["fallback_config_hash"],
                "operator_identity": actor,
            }
            try:
                signature = sign_test(fields)
            except ApprovalError as exc:
                return {"status": "rejected", "reason": str(exc), "granted": False}
            verified = verify_test(fields, signature)
            if not verified["ok"]:
                return {"status": "rejected", "reason": verified["reason"], "granted": False}
            approval_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO adaptation_approvals (
                    approval_id, recommendation_id, policy_hash, policy_version, stage,
                    approval_class, scope, max_exposure, expires_at, rollback_hash,
                    operator_identity, signature, algorithm, state
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    approval_id,
                    bundle.get("source_recommendation_id"),
                    bundle["policy_hash"],
                    bundle["policy_version"],
                    stage,
                    "TEST",
                    bundle["scope"],
                    fields["max_exposure"],
                    expires,
                    bundle["fallback_config_hash"],
                    actor,
                    signature,
                    "approve-hmac-sha256-v1-test",
                    "GRANTED",
                ),
            )
            if rec and stage == "A":
                connection.execute(
                    "UPDATE adaptation_recommendations SET state = %s WHERE recommendation_id = %s",
                    ("APPROVED_FOR_SHADOW", rec["recommendation_id"]),
                )
            _audit(
                connection,
                action="approve-test",
                actor_class="test",
                actor_identity=actor,
                object_type="approval",
                object_id=approval_id,
                new_state_hash=bundle["policy_hash"],
                reason=f"TEST stage {stage} granted",
                source_evidence={"stage": stage, "scope": bundle["scope"], "signature_present": True},
            )
            connection.commit()
            return {
                "status": "success",
                "approval_id": approval_id,
                "granted": True,
                "approval_class": "TEST",
                "stage": stage,
                "policy_hash": bundle["policy_hash"],
                "scope": bundle["scope"],
            }
        finally:
            advisory_unlock(connection, ADVISORY_LOCK_KEY)


def current_binding(connection: Any, binding_key: str = "default") -> dict[str, Any] | None:
    return fetch_one(
        connection,
        """
        SELECT * FROM adaptation_bindings
        WHERE binding_key = %s AND is_current
        ORDER BY binding_version DESC LIMIT 1
        """,
        (binding_key,),
    )


def _cas_insert(
    connection: Any,
    *,
    binding_key: str,
    policy_id: str | None,
    policy_hash: str | None,
    state: str,
    mode: str,
    expected_version: int,
) -> dict[str, Any]:
    current = current_binding(connection, binding_key)
    version = int((current or {}).get("binding_version") or 0)
    if version != expected_version:
        return {"status": "conflict", "reason": "CAS_MISMATCH", "binding_version": version}
    if current:
        connection.execute(
            "UPDATE adaptation_bindings SET is_current = FALSE WHERE binding_id = %s",
            (current["binding_id"],),
        )
    binding_id = str(uuid.uuid4())
    new_version = version + 1
    connection.execute(
        """
        INSERT INTO adaptation_bindings (
            binding_id, binding_key, policy_id, policy_hash, binding_version, state, mode, is_current
        ) VALUES (%s,%s,%s,%s,%s,%s,%s, TRUE)
        """,
        (binding_id, binding_key, policy_id, policy_hash, new_version, state, mode),
    )
    return {
        "status": "success",
        "binding_id": binding_id,
        "binding_version": new_version,
        "binding_version_before": version,
        "state": state,
        "mode": mode,
        "policy_hash": policy_hash,
    }


def _refresh_cache(connection: Any) -> dict[str, Any]:
    kill = fetch_one(connection, "SELECT engaged, reason FROM adaptation_kill_switch WHERE id = 1")
    rows = fetch_all(
        connection,
        """
        SELECT b.*, p.spec, p.candidate_config_hash, p.fallback_config_hash, p.policy_id AS bundle_policy_id
        FROM adaptation_bindings b
        LEFT JOIN adaptation_policy_bundles p ON p.policy_hash = b.policy_hash
        WHERE b.is_current
        """,
    )
    bindings = []
    for row in rows:
        spec = row.get("spec") or {}
        if isinstance(spec, str):
            import json

            spec = json.loads(spec)
        spec = dict(spec)
        spec["_policy_hash"] = row.get("policy_hash")
        spec["candidate_config_hash"] = row.get("candidate_config_hash")
        spec["fallback_config_hash"] = row.get("fallback_config_hash")
        bindings.append(
            {
                "policy_id": row.get("policy_id") or row.get("bundle_policy_id") or spec.get("policy_id"),
                "policy_hash": row.get("policy_hash"),
                "state": row.get("state"),
                "mode": row.get("mode"),
                "spec": spec,
                "selectors": spec.get("selectors"),
                "deny": spec.get("deny"),
            }
        )
    state = {"kill_switch": bool(kill and kill["engaged"]), "bindings": bindings}
    write_cache(state)
    if state["kill_switch"]:
        engage_kill_switch(str((kill or {}).get("reason") or "kill switch"))
    return state


def bind_policy(policy_ref: str, *, mode: str, actor: str = "operator", binding_key: str = "default") -> dict[str, Any]:
    with connect() as connection:
        locked = _lock(connection)
        if locked:
            return locked
        try:
            bundle = _bundle(connection, policy_ref)
            if not bundle:
                return {"status": "not_found"}
            current = current_binding(connection, binding_key)
            expected = int((current or {}).get("binding_version") or 0)
            payload = _cas_insert(
                connection,
                binding_key=binding_key,
                policy_id=bundle["policy_id"],
                policy_hash=bundle["policy_hash"],
                state="ACTIVE",
                mode=mode,
                expected_version=expected,
            )
            if payload.get("status") != "success":
                connection.rollback()
                return payload
            _audit(
                connection,
                action=f"bind-{mode.lower()}",
                actor_class="operator",
                actor_identity=actor,
                object_type="binding",
                object_id=payload["binding_id"],
                previous_state_hash=(current or {}).get("policy_hash"),
                new_state_hash=bundle["policy_hash"],
                reason=f"activate {mode}",
            )
            _refresh_cache(connection)
            connection.commit()
            return payload
        finally:
            advisory_unlock(connection, ADVISORY_LOCK_KEY)


def shadow_start(policy_ref: str, *, board: str | None = None, actor: str = "operator") -> dict[str, Any]:
    bound = bind_policy(policy_ref, mode="SHADOW", actor=actor)
    if bound.get("status") not in {"success", None} and bound.get("status") != "success":
        if bound.get("status") != "success":
            return bound
    state = load_cache()
    contexts: list[dict[str, Any]] = [
        {
            "task_id": "fixture-shadow-1",
            "board": "eos-phase6-exp",
            "task_class": "fixture",
            "environment": "fixture",
            "scope": "FIXTURE",
            "profile": "fixture",
        },
        {
            "task_id": "fixture-shadow-2",
            "board": "eos-phase6-exp",
            "task_class": "fixture",
            "environment": "fixture",
            "scope": "FIXTURE",
            "profile": "fixture",
        },
    ]
    production_n = 0
    if board:
        try:
            import os
            import sqlite3
            home = Path(os.environ.get("HERMES_HOME") or "/home/ubuntu/.hermes")
            db_path = home / "kanban" / "boards" / board / "kanban.db"
            if not db_path.is_file():
                db_path = Path("/home/ubuntu/.hermes/kanban/boards") / board / "kanban.db"
            if db_path.is_file():
                con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
                con.row_factory = sqlite3.Row
                try:
                    con.execute("PRAGMA query_only=ON")
                    tasks = [dict(row) for row in con.execute("SELECT id, status, assignee FROM tasks LIMIT 50")]
                finally:
                    con.close()
                prod_contexts = [production_task_context(task, board) for task in tasks]
                production_n = len(prod_contexts)
                contexts.extend(prod_contexts)
        except Exception as exc:
            production_n = 0
            contexts.append(
                {
                    "task_id": "production-shadow-unavailable",
                    "board": board,
                    "task_class": "production_kanban",
                    "environment": "production",
                    "scope": "PRODUCTION_SHADOW",
                    "error": f"{type(exc).__name__}",
                }
            )
    batch = shadow_batch(contexts, state)
    with connect() as connection:
        locked = _lock(connection)
        if locked:
            return locked
        try:
            bundle = _bundle(connection, policy_ref)
            for row in batch["decisions"]:
                connection.execute(
                    """
                    INSERT INTO adaptation_shadow_decisions (
                        decision_id, policy_hash, task_id, board, context, result, match_reason,
                        would_config_hash, actual_config_hash, conflict, latency_ms
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        str(uuid.uuid4()),
                        (bundle or {}).get("policy_hash") or row.get("policy_hash"),
                        row.get("task_id"),
                        row.get("board"),
                        jsonb(row.get("context") or {}),
                        row.get("result"),
                        row.get("match_reason"),
                        row.get("would_config_hash"),
                        row.get("actual_config_hash"),
                        row.get("conflict"),
                        row.get("latency_ms"),
                    ),
                )
            _audit(
                connection,
                action="shadow-start",
                actor_class="operator",
                actor_identity=actor,
                object_type="shadow",
                object_id=(bundle or {}).get("policy_hash"),
                new_state_hash=(bundle or {}).get("policy_hash"),
                reason="read-only shadow",
                source_evidence={"n": batch["n"], "would_change": batch["would_change"], "production_tasks": production_n},
            )
            connection.commit()
            batch["production_tasks"] = production_n
            batch["mutated"] = False
            batch["bind"] = bound
            return batch
        finally:
            advisory_unlock(connection, ADVISORY_LOCK_KEY)


def canary_start_fixture(policy_ref: str, *, actor: str = "operator") -> dict[str, Any]:
    bound = bind_policy(policy_ref, mode="CANARY", actor=actor)
    if bound.get("status") != "success":
        return bound
    with connect() as connection:
        bundle = _bundle(connection, policy_ref)
    if not bundle:
        return {"status": "not_found"}
    spec = bundle["spec"]
    if isinstance(spec, str):
        import json

        spec = json.loads(spec)
    spec = dict(spec)
    spec["_policy_hash"] = bundle["policy_hash"]
    spec["candidate_config_hash"] = bundle["candidate_config_hash"]
    spec["fallback_config_hash"] = bundle["fallback_config_hash"]
    state = load_cache()
    run = run_fixture_canary({"spec": spec, "policy_hash": bundle["policy_hash"]}, state=state, execute=True)
    guard = eval_guardrails(spec.get("guardrails") or [], run["exposures"], llm_calls=0)
    health = canary_health(guard, run["exposures"])
    auto_disabled = False
    with connect() as connection:
        locked = _lock(connection)
        if locked:
            return locked
        try:
            plan_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO adaptation_rollout_plans (plan_id, policy_hash, spec, state)
                VALUES (%s,%s,%s,%s)
                """,
                (plan_id, bundle["policy_hash"], jsonb(run["plan"]), health),
            )
            for row in run["exposures"]:
                connection.execute(
                    """
                    INSERT INTO adaptation_exposures (
                        exposure_id, policy_hash, unit_id, selected, candidate_config_hash,
                        fallback_config_hash, observed_config_hash, fidelity, outcome
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (policy_hash, unit_id) DO NOTHING
                    """,
                    (
                        str(uuid.uuid4()),
                        bundle["policy_hash"],
                        row["unit_id"],
                        row["selected"],
                        row.get("candidate_config_hash"),
                        row.get("fallback_config_hash"),
                        row.get("candidate_config_hash") if row["selected"] == "CANDIDATE" else row.get("fallback_config_hash"),
                        row.get("fidelity"),
                        jsonb(row.get("outcome") or {}),
                    ),
                )
            for ev in guard["events"]:
                connection.execute(
                    """
                        INSERT INTO adaptation_guardrail_events (event_id, policy_hash, metric_id, state, eval_window, evidence)
                        VALUES (%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        str(uuid.uuid4()),
                        bundle["policy_hash"],
                        ev.get("metric_id"),
                        ev.get("state"),
                        jsonb({"window": "canary"}),
                        jsonb(ev),
                    ),
                )
            if guard.get("auto_disable"):
                current = current_binding(connection)
                expected = int((current or {}).get("binding_version") or 0)
                disabled = _cas_insert(
                    connection,
                    binding_key="default",
                    policy_id=bundle["policy_id"],
                    policy_hash=bundle["policy_hash"],
                    state="DISABLED",
                    mode="DISABLED",
                    expected_version=expected,
                )
                connection.execute(
                    """
                    INSERT INTO adaptation_rollbacks (
                        rollback_id, policy_hash, from_state, to_state, trigger, reason,
                        binding_version_before, binding_version_after
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        str(uuid.uuid4()),
                        bundle["policy_hash"],
                        "ACTIVE",
                        "DISABLED",
                        "guardrail",
                        guard.get("reason"),
                        disabled.get("binding_version_before"),
                        disabled.get("binding_version"),
                    ),
                )
                auto_disabled = True
            _audit(
                connection,
                action="canary-start-fixture",
                actor_class="operator",
                actor_identity=actor,
                object_type="canary",
                object_id=bundle["policy_hash"],
                new_state_hash=bundle["policy_hash"],
                reason=health,
                source_evidence={
                    "candidate_n": run["candidate_n"],
                    "auto_disable": auto_disabled,
                    "health": health,
                },
            )
            _refresh_cache(connection)
            connection.commit()
            run["guardrails"] = guard
            run["health"] = health
            run["auto_disable"] = auto_disabled
            run["auto_promote"] = False
            run["bind"] = bound
            return run
        finally:
            advisory_unlock(connection, ADVISORY_LOCK_KEY)


def disable_policy(policy_ref: str, *, reason: str, trigger: str = "operator", actor: str = "operator") -> dict[str, Any]:
    with connect() as connection:
        locked = _lock(connection)
        if locked:
            return locked
        try:
            bundle = _bundle(connection, policy_ref)
            current = current_binding(connection)
            expected = int((current or {}).get("binding_version") or 0)
            payload = _cas_insert(
                connection,
                binding_key="default",
                policy_id=(bundle or {}).get("policy_id"),
                policy_hash=(bundle or {}).get("policy_hash") or (current or {}).get("policy_hash"),
                state="DISABLED",
                mode="DISABLED",
                expected_version=expected,
            )
            if payload.get("status") != "success":
                connection.rollback()
                return payload
            connection.execute(
                """
                INSERT INTO adaptation_rollbacks (
                    rollback_id, policy_hash, from_state, to_state, trigger, reason,
                    binding_version_before, binding_version_after
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(uuid.uuid4()),
                    payload.get("policy_hash"),
                    (current or {}).get("state"),
                    "DISABLED",
                    trigger,
                    reason,
                    payload.get("binding_version_before"),
                    payload.get("binding_version"),
                ),
            )
            _audit(
                connection,
                action="disable",
                actor_class="operator",
                actor_identity=actor,
                object_type="binding",
                object_id=payload.get("binding_id"),
                previous_state_hash=(current or {}).get("policy_hash"),
                new_state_hash=None,
                reason=reason,
            )
            _refresh_cache(connection)
            connection.commit()
            payload["interrupt_running"] = False
            return payload
        finally:
            advisory_unlock(connection, ADVISORY_LOCK_KEY)


def rollback_policy(policy_ref: str, *, reason: str, actor: str = "operator") -> dict[str, Any]:
    return disable_policy(policy_ref, reason=reason, trigger="rollback", actor=actor)


def promotion_request(policy_ref: str, *, actor: str = "operator") -> dict[str, Any]:
    with connect() as connection:
        locked = _lock(connection)
        if locked:
            return locked
        try:
            bundle = _bundle(connection, policy_ref)
            if not bundle:
                return {"status": "not_found"}
            last_guard = fetch_one(
                connection,
                """
                SELECT state FROM adaptation_guardrail_events
                WHERE policy_hash = %s ORDER BY created_at DESC LIMIT 1
                """,
                (bundle["policy_hash"],),
            )
            if last_guard and last_guard["state"] in {"FAIL", "UNKNOWN"}:
                return {
                    "status": "blocked",
                    "reason": "guardrail state blocks promotion",
                    "auto_promote": False,
                    "approval_b_required": True,
                }
            request_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO adaptation_approvals (
                    approval_id, recommendation_id, policy_hash, policy_version, stage,
                    approval_class, scope, max_exposure, expires_at, rollback_hash,
                    operator_identity, signature, algorithm, state
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    request_id,
                    bundle.get("source_recommendation_id"),
                    bundle["policy_hash"],
                    bundle["policy_version"],
                    "B",
                    "PRODUCTION" if str(bundle["scope"]).startswith("PRODUCTION") else "TEST",
                    bundle["scope"],
                    0,
                    _now() + timedelta(days=7),
                    bundle["fallback_config_hash"],
                    actor,
                    "",
                    "approve-hmac-sha256-v1" if str(bundle["scope"]).startswith("PRODUCTION") else "approve-hmac-sha256-v1-test",
                    "REQUESTED",
                ),
            )
            _audit(
                connection,
                action="promotion-request",
                actor_class="operator",
                actor_identity=actor,
                object_type="promotion",
                object_id=request_id,
                new_state_hash=bundle["policy_hash"],
                reason="canary success creates request only",
                source_evidence={"auto_promote": False},
            )
            connection.commit()
            blocked = approve_production() if str(bundle["scope"]).startswith("PRODUCTION") else None
            return {
                "status": "success",
                "promotion_request_id": request_id,
                "auto_promote": False,
                "activated": False,
                "approval_b_required": True,
                "production_approval": blocked or {"status": "TEST_SCOPE"},
            }
        finally:
            advisory_unlock(connection, ADVISORY_LOCK_KEY)


def disable_all(*, reason: str = "global kill switch", actor: str = "operator") -> dict[str, Any]:
    engage_kill_switch(reason)
    with connect() as connection:
        locked = _lock(connection)
        if locked:
            write_cache({"kill_switch": True, "bindings": load_cache().get("bindings") or []})
            return {"status": "success", "kill_switch": True, "locked": True, "resolution": "BASELINE"}
        try:
            connection.execute(
                "UPDATE adaptation_kill_switch SET engaged = TRUE, reason = %s, updated_at = NOW() WHERE id = 1",
                (reason,),
            )
            current = current_binding(connection)
            if current and current.get("mode") not in {"BASELINE", "DISABLED"}:
                _cas_insert(
                    connection,
                    binding_key="default",
                    policy_id=current.get("policy_id"),
                    policy_hash=current.get("policy_hash"),
                    state="DISABLED",
                    mode="DISABLED",
                    expected_version=int(current.get("binding_version") or 0),
                )
            _audit(
                connection,
                action="disable-all",
                actor_class="operator",
                actor_identity=actor,
                object_type="kill_switch",
                object_id="1",
                reason=reason,
            )
            _refresh_cache(connection)
            connection.commit()
            return {"status": "success", "kill_switch": True, "resolution": "BASELINE", "interrupt_running": False}
        finally:
            advisory_unlock(connection, ADVISORY_LOCK_KEY)


def health() -> dict[str, Any]:
    try:
        with connect() as connection:
            last = fetch_one(
                connection,
                "SELECT checkpoint_id, ended_at, status FROM adaptation_checkpoints ORDER BY started_at DESC LIMIT 1",
            )
            recs = fetch_one(connection, "SELECT COUNT(*) AS n FROM adaptation_recommendations")
            kill = fetch_one(connection, "SELECT engaged FROM adaptation_kill_switch WHERE id = 1")
        return {
            "status": "AVAILABLE",
            "source": "adaptation",
            "mode": "read-only",
            "contract_version": CONTRACT_VERSION,
            "last_checkpoint": last,
            "recommendations": (recs or {}).get("n"),
            "kill_switch": bool(kill and kill["engaged"]),
            "production_actuation": "DISABLED",
            "production_recommendation": PRODUCTION_RECOMMENDATION,
            "production_approval": PRODUCTION_APPROVAL,
            "runtime_integration": RUNTIME_INTEGRATION,
            "auto_promote": False,
        }
    except Exception as exc:
        return {
            "status": "DEGRADED",
            "source": "adaptation",
            "mode": "read-only",
            "contract_version": CONTRACT_VERSION,
            "detail": f"{type(exc).__name__}: {exc}",
            "production_actuation": "DISABLED",
            "fail_open_hermes": True,
        }


def refresh_cache() -> dict[str, Any]:
    with connect() as connection:
        return _refresh_cache(connection)
