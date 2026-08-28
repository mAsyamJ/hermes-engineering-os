"""Read helpers for GET-only experiment API."""

from __future__ import annotations

from typing import Any

from engineering_os.analytics.db import connect
from engineering_os.experiments import CONTRACT_VERSION
from engineering_os.experiments.explain import explain
from engineering_os.experiments.persist import health
from engineering_os.experiments.quality import coverage_sql, run_checks


def _rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as connection:
        return list(connection.execute(sql, params).fetchall())


def coverage() -> dict[str, Any]:
    try:
        with connect() as connection:
            row = connection.execute(coverage_sql()).fetchone() or {}
            quality = run_checks(connection)
        return {"status": quality["status"], "coverage": dict(row), "violations": quality["violations"]}
    except Exception as exc:
        return {"status": "DEGRADED", "detail": f"{type(exc).__name__}: {exc}"}


def summary() -> dict[str, Any]:
    payload = health()
    try:
        cov = coverage()
        protocols = _rows(
            """
            SELECT p.experiment_id, p.protocol_version, p.state, p.scope, p.design,
                   p.treatment_dimension, p.pre_registration_hash, p.hypothesis,
                   p.primary_metric, p.sample_plan, r.conclusion, r.effect_estimate,
                   r.known_n, r.missing_n, r.validity, r.reason, r.computed_at
            FROM experiment_protocol_versions p
            LEFT JOIN experiment_results r ON r.protocol_id = p.protocol_id AND r.is_current
            ORDER BY p.frozen_at DESC NULLS LAST
            """
        )
        payload.update(
            {
                "coverage": cov.get("coverage"),
                "quality": cov.get("status"),
                "experiments": protocols,
                "contract_version": CONTRACT_VERSION,
                "auto_route": False,
                "promote": False,
            }
        )
        return payload
    except Exception as exc:
        payload["status"] = "DEGRADED"
        payload["detail"] = f"{type(exc).__name__}: {exc}"
        return payload


def protocol(experiment_id: str) -> dict[str, Any]:
    rows = _rows(
        "SELECT * FROM experiment_protocol_versions WHERE experiment_id = %s ORDER BY frozen_at DESC LIMIT 1",
        (experiment_id,),
    )
    if not rows:
        return {"status": "NOT_FOUND", "experiment_id": experiment_id}
    return {"status": "AVAILABLE", "data": rows[0], "auto_route": False}


def variants(experiment_id: str) -> dict[str, Any]:
    rows = _rows(
        """
        SELECT c.* FROM experiment_config_snapshots c
        JOIN experiment_protocol_versions p ON p.protocol_id = c.protocol_id
        WHERE p.experiment_id = %s
        ORDER BY c.variant_role
        """,
        (experiment_id,),
    )
    return {"status": "AVAILABLE", "data": rows}


def assignments(experiment_id: str) -> dict[str, Any]:
    rows = _rows(
        """
        SELECT a.* FROM experiment_assignments a
        JOIN experiment_protocol_versions p ON p.protocol_id = a.protocol_id
        WHERE p.experiment_id = %s
        ORDER BY a.unit_id
        """,
        (experiment_id,),
    )
    return {"status": "AVAILABLE", "data": rows}


def exposures(experiment_id: str) -> dict[str, Any]:
    rows = _rows(
        """
        SELECT e.* FROM experiment_exposures e
        JOIN experiment_protocol_versions p ON p.protocol_id = e.protocol_id
        WHERE p.experiment_id = %s
        ORDER BY e.unit_id
        """,
        (experiment_id,),
    )
    return {"status": "AVAILABLE", "data": rows}


def progress(experiment_id: str) -> dict[str, Any]:
    rows = _rows(
        """
        SELECT
          (SELECT COUNT(*) FROM experiment_assignments a WHERE a.protocol_id = p.protocol_id) AS assigned_n,
          (SELECT COUNT(*) FROM experiment_assignments a WHERE a.protocol_id = p.protocol_id AND a.execution_started_at IS NOT NULL) AS started_n,
          (SELECT COUNT(*) FROM experiment_observations o WHERE o.protocol_id = p.protocol_id AND o.role = 'primary') AS collected_n,
          (SELECT COUNT(*) FROM experiment_observations o WHERE o.protocol_id = p.protocol_id AND o.role = 'primary' AND o.known) AS known_n,
          p.state, p.sample_plan
        FROM experiment_protocol_versions p
        WHERE p.experiment_id = %s
        ORDER BY p.frozen_at DESC LIMIT 1
        """,
        (experiment_id,),
    )
    if not rows:
        return {"status": "NOT_FOUND"}
    return {"status": "AVAILABLE", "data": rows[0]}


def analysis(experiment_id: str) -> dict[str, Any]:
    rows = _rows(
        """
        SELECT r.*, p.experiment_id FROM experiment_results r
        JOIN experiment_protocol_versions p ON p.protocol_id = r.protocol_id
        WHERE p.experiment_id = %s AND r.is_current
        ORDER BY r.computed_at DESC LIMIT 1
        """,
        (experiment_id,),
    )
    if not rows:
        return {"status": "AVAILABLE", "conclusion": "NOT_STARTED", "data": None, "auto_route": False}
    row = rows[0]
    extras = row.get("extras") or {}
    if isinstance(extras, str):
        extras = {}
    if not extras.get("horizon_reached") and row.get("conclusion") in {
        "EVIDENCE_FOR_CANDIDATE",
        "EVIDENCE_AGAINST_CANDIDATE",
    }:
        row = dict(row)
        row["conclusion"] = "COLLECTING"
        row["blocked"] = "BLOCKED_HORIZON"
    return {"status": "AVAILABLE", "data": row, "auto_route": False, "promote": False}


def guardrails(experiment_id: str) -> dict[str, Any]:
    rows = _rows(
        """
        SELECT g.* FROM experiment_guardrail_events g
        JOIN experiment_protocol_versions p ON p.protocol_id = g.protocol_id
        WHERE p.experiment_id = %s
        ORDER BY g.recorded_at DESC
        """,
        (experiment_id,),
    )
    return {"status": "AVAILABLE", "data": rows}


def why(experiment_id: str) -> dict[str, Any]:
    return explain(experiment_id)
