"""Operator-facing WHY payloads. No promotion actions."""

from __future__ import annotations

from typing import Any

from engineering_os.analytics.db import connect, fetch_one


def explain(experiment_id: str, protocol_version: str | None = None) -> dict[str, Any]:
    with connect() as connection:
        protocol = fetch_one(
            connection,
            """
            SELECT * FROM experiment_protocol_versions
            WHERE experiment_id = %s
              AND (%s IS NULL OR protocol_version = %s)
            ORDER BY frozen_at DESC NULLS LAST
            LIMIT 1
            """,
            (experiment_id, protocol_version, protocol_version),
        )
        if not protocol:
            return {"status": "NOT_FOUND", "experiment_id": experiment_id}
        result = fetch_one(
            connection,
            """
            SELECT * FROM experiment_results
            WHERE protocol_id = %s AND is_current
            ORDER BY computed_at DESC
            LIMIT 1
            """,
            (protocol["protocol_id"],),
        )
        progress = fetch_one(
            connection,
            """
            SELECT COUNT(*) AS assigned_n,
                   COUNT(*) FILTER (WHERE variant_role = 'CONTROL') AS control_n,
                   COUNT(*) FILTER (WHERE variant_role = 'CANDIDATE') AS candidate_n
            FROM experiment_assignments
            WHERE protocol_id = %s
            """,
            (protocol["protocol_id"],),
        )
    return {
        "status": "AVAILABLE",
        "experiment_id": experiment_id,
        "protocol_hash": protocol.get("pre_registration_hash"),
        "treatment_dimension": protocol.get("treatment_dimension"),
        "sample_plan": protocol.get("sample_plan"),
        "assignments": progress,
        "result": result,
        "auto_route": False,
        "promote": False,
        "why": {
            "hypothesis": protocol.get("hypothesis"),
            "primary_metric": protocol.get("primary_metric"),
            "conclusion": (result or {}).get("conclusion") or "NOT_STARTED",
            "reason": (result or {}).get("reason"),
            "effect": (result or {}).get("effect_estimate"),
            "uncertainty": (result or {}).get("uncertainty"),
            "validity": (result or {}).get("validity"),
            "missingness": {
                "assigned_n": (result or {}).get("itt_n_control"),
                "known_n": (result or {}).get("known_n"),
                "missing_n": (result or {}).get("missing_n"),
            },
        },
    }
