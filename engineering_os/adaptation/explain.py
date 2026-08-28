"""WHY explanations for recommendations, policies, and decisions."""

from __future__ import annotations

from typing import Any

from engineering_os.adaptation.db import connect, fetch_one
from engineering_os.redaction import redact


def explain(object_id: str) -> dict[str, Any]:
    with connect() as connection:
        rec = fetch_one(
            connection,
            "SELECT * FROM adaptation_recommendations WHERE recommendation_id::text = %s",
            (object_id,),
        )
        if rec:
            return redact(
                {
                    "status": "AVAILABLE",
                    "kind": "recommendation",
                    "why": {
                        "experiment_id": rec.get("experiment_id"),
                        "conclusion": rec.get("conclusion"),
                        "classification": rec.get("classification"),
                        "state": rec.get("state"),
                        "reason": rec.get("reason"),
                        "production_promotable": rec.get("production_promotable"),
                        "active_policy": False,
                    },
                }
            )
        pol = fetch_one(
            connection,
            """
            SELECT policy_id, policy_version, policy_hash, scope, treatment_dimension,
                   candidate_config_hash, fallback_config_hash, source_recommendation_id
            FROM adaptation_policy_bundles
            WHERE policy_id = %s OR policy_hash = %s
            ORDER BY created_at DESC LIMIT 1
            """,
            (object_id, object_id),
        )
        if pol:
            return redact({"status": "AVAILABLE", "kind": "policy", "why": pol})
        sh = fetch_one(
            connection,
            "SELECT * FROM adaptation_shadow_decisions WHERE decision_id::text = %s OR task_id = %s LIMIT 1",
            (object_id, object_id),
        )
        if sh:
            return redact({"status": "AVAILABLE", "kind": "shadow", "why": sh, "efficacy_claim": False})
    return {"status": "NOT_FOUND", "id": object_id}
