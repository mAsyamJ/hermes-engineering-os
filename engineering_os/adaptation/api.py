"""Read helpers for GET-only adaptation API."""

from __future__ import annotations

from typing import Any

from engineering_os.adaptation import (
    CONTRACT_VERSION,
    MEMORY_ISOLATION,
    PRODUCTION_APPROVAL,
    PRODUCTION_RECOMMENDATION,
    RUNTIME_INTEGRATION,
)
from engineering_os.adaptation.db import connect, fetch_all, fetch_one
from engineering_os.adaptation.persist import health
from engineering_os.adaptation.explain import explain as explain_object
from engineering_os.redaction import redact


def _rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as connection:
        return fetch_all(connection, sql, params)


def readiness() -> dict[str, Any]:
    payload = health()
    payload.update(
        {
            "contract_version": CONTRACT_VERSION,
            "production_evidence": PRODUCTION_RECOMMENDATION,
            "human_approval_boundary": PRODUCTION_APPROVAL,
            "memory_isolation": MEMORY_ISOLATION,
            "runtime_actuation": RUNTIME_INTEGRATION,
            "production_adaptation": "DISABLED",
            "fixture_qualification": "SEPARATE",
            "auto_promote": False,
            "deploy_now": False,
        }
    )
    return redact(payload)


def recommendations() -> dict[str, Any]:
    try:
        rows = _rows("SELECT * FROM adaptation_recommendations ORDER BY created_at DESC LIMIT 100")
        return {"status": "AVAILABLE", "data": redact(rows), "production_promotable": False}
    except Exception as exc:
        return {"status": "DEGRADED", "detail": f"{type(exc).__name__}: {exc}"}


def recommendation(recommendation_id: str) -> dict[str, Any]:
    rows = _rows("SELECT * FROM adaptation_recommendations WHERE recommendation_id::text = %s", (recommendation_id,))
    if not rows:
        return {"status": "NOT_FOUND", "recommendation_id": recommendation_id}
    return {"status": "AVAILABLE", "data": redact(rows[0])}


def policies() -> dict[str, Any]:
    try:
        rows = _rows(
            """
            SELECT policy_id, policy_version, policy_hash, scope, treatment_dimension,
                   candidate_config_hash, fallback_config_hash, created_at
            FROM adaptation_policy_bundles ORDER BY created_at DESC LIMIT 100
            """
        )
        return {"status": "AVAILABLE", "data": redact(rows)}
    except Exception as exc:
        return {"status": "DEGRADED", "detail": f"{type(exc).__name__}: {exc}"}


def policy(policy_id: str) -> dict[str, Any]:
    rows = _rows(
        """
        SELECT policy_id, policy_version, policy_hash, scope, treatment_dimension,
               candidate_config_hash, fallback_config_hash, spec, created_at
        FROM adaptation_policy_bundles
        WHERE policy_id = %s OR policy_hash = %s
        ORDER BY created_at DESC LIMIT 1
        """,
        (policy_id, policy_id),
    )
    if not rows:
        return {"status": "NOT_FOUND", "policy_id": policy_id}
    return {"status": "AVAILABLE", "data": redact(rows[0])}


def shadow() -> dict[str, Any]:
    try:
        rows = _rows("SELECT * FROM adaptation_shadow_decisions ORDER BY created_at DESC LIMIT 200")
        return {"status": "AVAILABLE", "data": redact(rows), "mutated": False}
    except Exception as exc:
        return {"status": "DEGRADED", "detail": f"{type(exc).__name__}: {exc}"}


def canaries() -> dict[str, Any]:
    try:
        rows = _rows("SELECT * FROM adaptation_rollout_plans ORDER BY created_at DESC LIMIT 50")
        exposures = _rows("SELECT policy_hash, selected, COUNT(*) AS n FROM adaptation_exposures GROUP BY 1,2")
        return {"status": "AVAILABLE", "plans": redact(rows), "exposures": redact(exposures), "auto_promote": False}
    except Exception as exc:
        return {"status": "DEGRADED", "detail": f"{type(exc).__name__}: {exc}"}


def guardrails() -> dict[str, Any]:
    try:
        rows = _rows("SELECT * FROM adaptation_guardrail_events ORDER BY created_at DESC LIMIT 200")
        return {"status": "AVAILABLE", "data": redact(rows), "auto_promote": False}
    except Exception as exc:
        return {"status": "DEGRADED", "detail": f"{type(exc).__name__}: {exc}"}


def rollbacks() -> dict[str, Any]:
    try:
        rows = _rows("SELECT * FROM adaptation_rollbacks ORDER BY created_at DESC LIMIT 100")
        return {"status": "AVAILABLE", "data": redact(rows)}
    except Exception as exc:
        return {"status": "DEGRADED", "detail": f"{type(exc).__name__}: {exc}"}


def audit() -> dict[str, Any]:
    try:
        rows = _rows(
            """
            SELECT event_id, occurred_at, actor_class, actor_identity, action, object_type,
                   object_id, previous_state_hash, new_state_hash, reason
            FROM adaptation_audit_log ORDER BY occurred_at DESC LIMIT 200
            """
        )
        return {"status": "AVAILABLE", "data": redact(rows)}
    except Exception as exc:
        return {"status": "DEGRADED", "detail": f"{type(exc).__name__}: {exc}"}


def summary() -> dict[str, Any]:
    payload = readiness()
    try:
        payload["recommendations"] = recommendations().get("data") or []
        payload["policies"] = policies().get("data") or []
        payload["shadow"] = {"n": len(shadow().get("data") or [])}
        payload["canaries"] = canaries()
        payload["rollbacks"] = rollbacks().get("data") or []
        return payload
    except Exception as exc:
        payload["status"] = "DEGRADED"
        payload["detail"] = f"{type(exc).__name__}: {exc}"
        return payload


def why(object_id: str) -> dict[str, Any]:
    try:
        return redact(explain_object(object_id))
    except Exception as exc:
        return {"status": "DEGRADED", "detail": f"{type(exc).__name__}: {exc}"}
