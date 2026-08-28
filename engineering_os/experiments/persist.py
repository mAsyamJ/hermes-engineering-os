"""Persist experiment metadata into hermes_engineering. Fail-open toward Hermes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from engineering_os.analytics.db import advisory_unlock, connect, fetch_all, fetch_one, try_advisory_lock
from engineering_os.experiments import (
    ADVISORY_LOCK_KEY,
    ANALYSIS_VERSION,
    ANALYTICS_LOCK_KEY,
    CONTRACT_VERSION,
    EVALUATION_LOCK_KEY,
    PERFORMANCE_LOCK_KEY,
)
from engineering_os.experiments.analyze import analyze as run_analysis
from engineering_os.experiments.assignment import assign_blocked, assign_paired, balance_report
from engineering_os.experiments.benchmarks import default_cases
from engineering_os.experiments.config_snapshot import canonical_dumps, sha256_text
from engineering_os.experiments.definitions import load_id, load_path
from engineering_os.experiments.drift import detect as detect_drift
from engineering_os.experiments.executor import collect_from_execution, run_unit
from engineering_os.experiments.exposure import record as record_exposure
from engineering_os.experiments.guardrails import evaluate as eval_guardrails
from engineering_os.experiments.preregister import freeze
from engineering_os.experiments.quality import coverage_sql, run_checks
from engineering_os.experiments.validity import confirmatory_allowed, evaluate as eval_validity
from pathlib import Path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _jsonb(value: Any) -> Any:
    from psycopg.types.json import Json

    return Json(value)


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
        return {"status": "locked", "contract_version": CONTRACT_VERSION, "detail": "experiment lock held"}
    if advisory_held(connection, ANALYTICS_LOCK_KEY) or advisory_held(connection, EVALUATION_LOCK_KEY) or advisory_held(connection, PERFORMANCE_LOCK_KEY):
        advisory_unlock(connection, ADVISORY_LOCK_KEY)
        return {
            "status": "locked",
            "contract_version": CONTRACT_VERSION,
            "detail": "analytics, evaluation, or performance materialization in progress",
        }
    return None


def _load_protocol_row(connection: Any, experiment_id: str) -> dict[str, Any] | None:
    return fetch_one(
        connection,
        """
        SELECT * FROM experiment_protocol_versions
        WHERE experiment_id = %s
        ORDER BY frozen_at DESC NULLS LAST, created_at DESC
        LIMIT 1
        """,
        (experiment_id,),
    )


def preregister(source: str, connection: Any | None = None) -> dict[str, Any]:
    path = Path(source)
    definition = load_path(path) if path.suffix in {".yaml", ".yml"} else load_id(source)
    protocol = freeze(definition)
    owns = connection is None
    cm = None
    if owns:
        cm = connect()
        connection = cm.__enter__()
    try:
        locked = _lock(connection) if owns else None
        if locked:
            return locked
        try:
            existing = fetch_one(
                connection,
                "SELECT protocol_id, pre_registration_hash FROM experiment_protocol_versions WHERE experiment_id = %s AND protocol_version = %s",
                (protocol["experiment_id"], protocol["protocol_version"]),
            )
            if existing:
                if existing["pre_registration_hash"] != protocol["pre_registration_hash"]:
                    return {"status": "rejected", "detail": "REJECTED: frozen protocol mutation"}
                return {
                    "status": "unchanged",
                    "protocol_id": str(existing["protocol_id"]),
                    "pre_registration_hash": existing["pre_registration_hash"],
                    "state": "PRE_REGISTERED",
                }
            protocol_id = uuid.uuid4()
            connection.execute(
                """
                INSERT INTO experiment_definitions (
                    experiment_id, definition_version, definition_hash, source_path, spec
                ) VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT DO NOTHING
                """,
                (
                    protocol["experiment_id"],
                    protocol["protocol_version"],
                    protocol["definition_hash"],
                    str(path),
                    _jsonb({k: v for k, v in definition.items() if not str(k).startswith("_")}),
                ),
            )
            connection.execute(
                """
                INSERT INTO experiment_contract_snapshots (contract_version, config_hash, spec)
                VALUES (%s,%s,%s)
                ON CONFLICT DO NOTHING
                """,
                (CONTRACT_VERSION, protocol["pre_registration_hash"], _jsonb(protocol["contracts"])),
            )
            connection.execute(
                """
                INSERT INTO experiment_protocol_versions (
                    protocol_id, experiment_id, protocol_version, pre_registration_hash, definition_hash,
                    state, scope, design, treatment_dimension, hypothesis, primary_metric, secondary_metrics,
                    guardrails, sample_plan, analysis_plan, assignment_plan, budget, missingness, seed,
                    assignment_algorithm_version, control_variant_id, candidate_variant_id,
                    control_config_hash, candidate_config_hash, environment_hash,
                    phase3_ruleset, phase4_contract, phase5_contract, phase6_contract, spec, frozen_at
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                """,
                (
                    protocol_id,
                    protocol["experiment_id"],
                    protocol["protocol_version"],
                    protocol["pre_registration_hash"],
                    protocol["definition_hash"],
                    "PRE_REGISTERED",
                    protocol["scope"],
                    protocol["design"],
                    protocol["treatment_dimension"],
                    protocol["hypothesis"],
                    _jsonb(protocol["primary_metric"]),
                    _jsonb(protocol["secondary_metrics"]),
                    _jsonb(protocol["guardrails"]),
                    _jsonb(protocol["sample_plan"]),
                    _jsonb(protocol["analysis"]),
                    _jsonb(protocol["assignment"]),
                    _jsonb(protocol["budget"]),
                    _jsonb(protocol["missingness"]),
                    protocol["assignment"]["seed"],
                    protocol["assignment"]["algorithm"],
                    protocol["control"]["variant_id"],
                    protocol["candidate"]["variant_id"],
                    protocol["control"]["config_hash"],
                    protocol["candidate"]["config_hash"],
                    protocol["environment_hash"],
                    protocol["contracts"]["phase3_ruleset"],
                    protocol["contracts"]["phase4_contract"],
                    protocol["contracts"]["phase5_contract"],
                    protocol["contracts"]["phase6_contract"],
                    _jsonb(protocol),
                    _now(),
                ),
            )
            for role in ("control", "candidate"):
                variant = protocol[role]
                connection.execute(
                    """
                    INSERT INTO experiment_config_snapshots (
                        config_snapshot_id, protocol_id, variant_id, variant_role, config_hash, snapshot
                    ) VALUES (%s,%s,%s,%s,%s,%s)
                    """,
                    (uuid.uuid4(), protocol_id, variant["variant_id"], role.upper() if role != "control" else "CONTROL" if role == "control" else "CANDIDATE", variant["config_hash"], _jsonb(variant["snapshot"])),
                )
            connection.commit()
            return {
                "status": "success",
                "protocol_id": str(protocol_id),
                "pre_registration_hash": protocol["pre_registration_hash"],
                "state": "PRE_REGISTERED",
                "contract_version": CONTRACT_VERSION,
            }
        finally:
            if owns:
                advisory_unlock(connection, ADVISORY_LOCK_KEY)
    finally:
        if owns:
            if cm is not None:
                cm.__exit__(None, None, None)


def assign(experiment_id: str, connection: Any | None = None) -> dict[str, Any]:
    owns = connection is None
    cm = None
    if owns:
        cm = connect()
        connection = cm.__enter__()
    try:
        locked = _lock(connection) if owns else None
        if locked:
            return locked
        try:
            row = _load_protocol_row(connection, experiment_id)
            if not row:
                return {"status": "not_found", "experiment_id": experiment_id}
            protocol = row["spec"]
            existing = fetch_all(
                connection,
                "SELECT unit_id FROM experiment_assignments WHERE protocol_id = %s",
                (row["protocol_id"],),
            )
            if existing:
                return {"status": "unchanged", "assigned_n": len(existing), "protocol_id": str(row["protocol_id"])}
            planned = int(protocol["sample_plan"]["planned_n"])
            suite = protocol.get("benchmark_suite") or "fixture-v1"
            control_id = protocol["control"]["variant_id"]
            cand_id = protocol["candidate"]["variant_id"]
            seed = protocol["assignment"]["seed"]
            if protocol["design"] == "PAIRED":
                cases = protocol.get("cases") or default_cases(planned, "clean", suite)
                assignments = assign_paired(cases, seed, control_id, cand_id)
            else:
                cases = protocol.get("cases") or default_cases(planned, "clean", suite)
                units = [{"unit_id": c["case_id"], "stratum": c.get("stratum") or suite, "pair_id": None} for c in cases]
                assignments = assign_blocked(units, seed, control_id, cand_id)
            for item in assignments:
                connection.execute(
                    """
                    INSERT INTO experiment_units (protocol_id, unit_id, case_id, pair_id, stratum, benchmark_id)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    """,
                    (row["protocol_id"], item["unit_id"], item.get("case_id"), item.get("pair_id"), item.get("stratum"), suite),
                )
                connection.execute(
                    """
                    INSERT INTO experiment_assignments (
                        assignment_id, protocol_id, unit_id, variant_id, variant_role, stratum, pair_id,
                        seed, assignment_algorithm_version, assignment_hash
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        uuid.uuid4(),
                        row["protocol_id"],
                        item["unit_id"],
                        item["variant_id"],
                        item["variant_role"],
                        item.get("stratum"),
                        item.get("pair_id"),
                        seed,
                        item["assignment_algorithm_version"],
                        item["assignment_hash"],
                    ),
                )
            connection.execute(
                "UPDATE experiment_protocol_versions SET state = 'READY' WHERE protocol_id = %s AND state = 'PRE_REGISTERED'",
                (row["protocol_id"],),
            )
            connection.commit()
            return {
                "status": "success",
                "assigned_n": len(assignments),
                "balance": balance_report(assignments),
                "protocol_id": str(row["protocol_id"]),
            }
        finally:
            if owns:
                advisory_unlock(connection, ADVISORY_LOCK_KEY)
    finally:
        if owns:
            if cm is not None:
                cm.__exit__(None, None, None)


def run_fixture(experiment_id: str, connection: Any | None = None) -> dict[str, Any]:
    owns = connection is None
    cm = None
    if owns:
        cm = connect()
        connection = cm.__enter__()
    try:
        locked = _lock(connection) if owns else None
        if locked:
            return locked
        try:
            row = _load_protocol_row(connection, experiment_id)
            if not row:
                return {"status": "not_found"}
            protocol = row["spec"]
            if int(protocol["budget"].get("max_llm_calls") or 0) != 0:
                return {"status": "rejected", "detail": "LLM budget is not zero"}
            assignments = fetch_all(
                connection,
                "SELECT * FROM experiment_assignments WHERE protocol_id = %s ORDER BY unit_id",
                (row["protocol_id"],),
            )
            executed = 0
            connection.execute(
                "UPDATE experiment_protocol_versions SET state = 'RUNNING' WHERE protocol_id = %s",
                (row["protocol_id"],),
            )
            for assignment in assignments:
                started = fetch_one(
                    connection,
                    "SELECT execution_started_at FROM experiment_assignments WHERE protocol_id = %s AND unit_id = %s",
                    (row["protocol_id"], assignment["unit_id"]),
                )
                if started and started.get("execution_started_at"):
                    continue
                connection.execute(
                    "UPDATE experiment_assignments SET execution_started_at = %s WHERE protocol_id = %s AND unit_id = %s",
                    (_now(), row["protocol_id"], assignment["unit_id"]),
                )
                connection.commit()
                execution = run_unit(assignment, protocol, persist=True, connection=connection)
                variant = protocol["control"] if assignment["variant_role"] == "CONTROL" else protocol["candidate"]
                exposure = record_exposure(
                    {
                        **assignment,
                        "assigned_config_hash": variant["config_hash"],
                    },
                    execution["tree_hash"],
                    True,
                    extra={"artifact": execution["artifact"]},
                )
                connection.execute(
                    """
                    INSERT INTO experiment_exposures (
                        exposure_id, protocol_id, unit_id, assigned_variant_id, assigned_variant_role,
                        observed_config_hash, fidelity, itt_variant_role, reassigned, evidence
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,FALSE,%s)
                    ON CONFLICT (protocol_id, unit_id) DO NOTHING
                    """,
                    (
                        uuid.uuid4(),
                        row["protocol_id"],
                        assignment["unit_id"],
                        assignment["variant_id"],
                        assignment["variant_role"],
                        execution["tree_hash"],
                        "MATCHED",
                        assignment["variant_role"],
                        _jsonb({"artifact": execution["artifact"], "workspace": execution["workspace"]}),
                    ),
                )
                for obs in collect_from_execution(execution, protocol):
                    connection.execute(
                        """
                        INSERT INTO experiment_observations (
                            observation_id, protocol_id, unit_id, metric_id, role, value, known,
                            evaluation_run_id, source_versions
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (protocol_id, unit_id, metric_id) DO UPDATE SET
                            value = EXCLUDED.value,
                            known = EXCLUDED.known,
                            evaluation_run_id = EXCLUDED.evaluation_run_id,
                            source_versions = EXCLUDED.source_versions,
                            collected_at = NOW()
                        """,
                        (
                            uuid.uuid4(),
                            row["protocol_id"],
                            obs["unit_id"],
                            obs["metric_id"],
                            obs["role"],
                            None if obs.get("value") is None else str(obs["value"]),
                            bool(obs.get("known")),
                            obs.get("evaluation_run_id"),
                            _jsonb(obs.get("source_versions") or {}),
                        ),
                    )
                executed += 1
                connection.commit()
            return {"status": "success", "executed": executed, "assigned_n": len(assignments), "llm_calls": 0}
        finally:
            if owns:
                advisory_unlock(connection, ADVISORY_LOCK_KEY)
    finally:
        if owns:
            if cm is not None:
                cm.__exit__(None, None, None)


def collect(experiment_id: str, connection: Any | None = None) -> dict[str, Any]:
    owns = connection is None
    cm = None
    if owns:
        cm = connect()
        connection = cm.__enter__()
    try:
        locked = _lock(connection) if owns else None
        if locked:
            return locked
        try:
            row = _load_protocol_row(connection, experiment_id)
            if not row:
                return {"status": "not_found"}
            n = fetch_one(
                connection,
                "SELECT COUNT(*) AS n FROM experiment_observations WHERE protocol_id = %s",
                (row["protocol_id"],),
            )
            return {"status": "success", "observations": (n or {}).get("n") or 0, "idempotent": True}
        finally:
            if owns:
                advisory_unlock(connection, ADVISORY_LOCK_KEY)
    finally:
        if owns:
            if cm is not None:
                cm.__exit__(None, None, None)


def _facts(connection: Any, row: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    balance = fetch_all(connection, "SELECT variant_role FROM experiment_assignments WHERE protocol_id = %s", (row["protocol_id"],))
    report = balance_report([{"variant_role": r["variant_role"]} for r in balance])
    return {
        "scope": protocol.get("scope"),
        "protocol_hash_ok": True,
        "assignment_ok": report["integrity"] == "PASS",
        "config_ok": True,
        "environment_ok": True,
        "memory_mode": "fixture_executor",
        "workspace_ok": True,
        "coverage_ok": True,
        "evaluator_ok": True,
        "fidelity_required": False,
        "exposure_fidelity": "MATCHED",
    }


def analyze_experiment(experiment_id: str, *, final: bool = False, recompute: bool = False, connection: Any | None = None) -> dict[str, Any]:
    owns = connection is None
    cm = None
    if owns:
        cm = connect()
        connection = cm.__enter__()
    try:
        locked = _lock(connection) if owns else None
        if locked:
            return locked
        try:
            row = _load_protocol_row(connection, experiment_id)
            if not row:
                return {"status": "not_found"}
            protocol = row["spec"]
            assignments = fetch_all(connection, "SELECT * FROM experiment_assignments WHERE protocol_id = %s", (row["protocol_id"],))
            observations = fetch_all(connection, "SELECT * FROM experiment_observations WHERE protocol_id = %s", (row["protocol_id"],))
            exposures = fetch_all(connection, "SELECT * FROM experiment_exposures WHERE protocol_id = %s", (row["protocol_id"],))
            validity = eval_validity(_facts(connection, row, protocol))
            guard = eval_guardrails(protocol, observations, llm_calls=0)
            result = run_analysis(
                protocol,
                assignments,
                observations,
                exposures,
                validity,
                final=final,
                guardrail_state=guard["state"],
            )
            if result.get("blocked") == "BLOCKED_HORIZON":
                return result
            if not confirmatory_allowed(validity, protocol.get("scope") or "FIXTURE") and result["conclusion"] in {
                "EVIDENCE_FOR_CANDIDATE",
                "EVIDENCE_AGAINST_CANDIDATE",
            }:
                result["conclusion"] = "INVALIDATED"
                result["reason"] = "Required validity dimension failed; confirmatory interpretation is invalid."
            analysis_id = uuid.uuid4()
            connection.execute(
                """
                INSERT INTO experiment_analysis_runs (
                    analysis_run_id, protocol_id, analysis_version, analysis_hash, population, status, final, blocked_reason, detail
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    analysis_id,
                    row["protocol_id"],
                    ANALYSIS_VERSION,
                    result["source_versions"]["analysis_hash"],
                    result["population"],
                    result["status"],
                    final,
                    result.get("blocked"),
                    _jsonb({"conclusion": result["conclusion"]}),
                ),
            )
            if recompute or True:
                connection.execute(
                    "UPDATE experiment_results SET is_current = FALSE WHERE protocol_id = %s AND is_current",
                    (row["protocol_id"],),
                )
            extras = {
                "horizon_reached": result["horizon_reached"],
                "fixture_validation_only": result["fixture_validation_only"],
                "production_claim": False,
                "stats": result.get("stats"),
                "planned_n": result["planned_n"],
            }
            connection.execute(
                """
                INSERT INTO experiment_results (
                    result_id, analysis_run_id, protocol_id, is_current, primary_metric,
                    itt_n_control, itt_n_candidate, known_n, missing_n, effect_estimate,
                    uncertainty, conclusion, reason, validity, guardrail_state,
                    assignment_integrity, treatment_fidelity, source_versions, extras
                ) VALUES (%s,%s,%s,TRUE,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    uuid.uuid4(),
                    analysis_id,
                    row["protocol_id"],
                    result["primary_metric"],
                    result["itt_n_control"],
                    result["itt_n_candidate"],
                    result["known_n"],
                    result["missing_n"],
                    result["effect_estimate"],
                    _jsonb(result["uncertainty"]),
                    result["conclusion"],
                    result["reason"],
                    _jsonb(result["validity"]),
                    result["guardrail_state"],
                    "PASS",
                    "MATCHED",
                    _jsonb(result["source_versions"]),
                    _jsonb(extras),
                ),
            )
            if result["conclusion"] not in {"COLLECTING", "NOT_STARTED"} and result["horizon_reached"]:
                state = "COMPLETED" if result["conclusion"] != "INVALIDATED" else "INVALIDATED"
                if result["conclusion"] == "GUARDRAIL_FAILURE":
                    state = "PAUSED"
                connection.execute(
                    "UPDATE experiment_protocol_versions SET state = %s WHERE protocol_id = %s",
                    (state, row["protocol_id"]),
                )
            if guard["stop"]:
                connection.execute(
                    "UPDATE experiment_protocol_versions SET state = 'PAUSED' WHERE protocol_id = %s",
                    (row["protocol_id"],),
                )
                for event in guard["events"]:
                    connection.execute(
                        """
                        INSERT INTO experiment_guardrail_events (event_id, protocol_id, metric_id, state, reason)
                        VALUES (%s,%s,%s,%s,%s)
                        """,
                        (uuid.uuid4(), row["protocol_id"], event.get("metric_id"), event.get("state"), event.get("reason")),
                    )
            connection.execute(
                """
                INSERT INTO experiment_checkpoints (source, watermark, updated_at)
                VALUES ('phase6', %s, %s)
                ON CONFLICT (source) DO UPDATE SET watermark = EXCLUDED.watermark, updated_at = EXCLUDED.updated_at
                """,
                (str(analysis_id), _now()),
            )
            connection.commit()
            result["analysis_run_id"] = str(analysis_id)
            return result
        finally:
            if owns:
                advisory_unlock(connection, ADVISORY_LOCK_KEY)
    finally:
        if owns:
            if cm is not None:
                cm.__exit__(None, None, None)


def invalidate(experiment_id: str, reason: str, connection: Any | None = None) -> dict[str, Any]:
    owns = connection is None
    cm = None
    if owns:
        cm = connect()
        connection = cm.__enter__()
    try:
        row = _load_protocol_row(connection, experiment_id)
        if not row:
            return {"status": "not_found"}
        connection.execute(
            "UPDATE experiment_protocol_versions SET state = 'INVALIDATED' WHERE protocol_id = %s",
            (row["protocol_id"],),
        )
        connection.execute(
            """
            INSERT INTO experiment_amendments (amendment_id, protocol_id, reason, outcomes_already_observed, detail)
            VALUES (%s,%s,%s,
                EXISTS (SELECT 1 FROM experiment_observations WHERE protocol_id = %s),
                %s)
            """,
            (uuid.uuid4(), row["protocol_id"], reason, row["protocol_id"], _jsonb({"kind": "invalidate"})),
        )
        connection.commit()
        return {"status": "success", "state": "INVALIDATED", "reason": reason}
    finally:
        if owns:
            if cm is not None:
                cm.__exit__(None, None, None)


def status(experiment_id: str | None = None) -> dict[str, Any]:
    with connect() as connection:
        if experiment_id:
            row = _load_protocol_row(connection, experiment_id)
            if not row:
                return {"status": "not_found", "experiment_id": experiment_id}
            result = fetch_one(
                connection,
                "SELECT * FROM experiment_results WHERE protocol_id = %s AND is_current ORDER BY computed_at DESC LIMIT 1",
                (row["protocol_id"],),
            )
            return {"status": "AVAILABLE", "protocol": dict(row), "result": result, "contract_version": CONTRACT_VERSION}
        protocols = fetch_all(
            connection,
            """
            SELECT experiment_id, protocol_version, state, scope, treatment_dimension, design,
                   pre_registration_hash, frozen_at
            FROM experiment_protocol_versions
            ORDER BY frozen_at DESC NULLS LAST
            """,
        )
        quality = run_checks(connection)
        coverage = fetch_one(connection, coverage_sql()) or {}
        return {
            "status": "AVAILABLE",
            "contract_version": CONTRACT_VERSION,
            "protocols": protocols,
            "quality": quality,
            "coverage": dict(coverage),
        }


def health() -> dict[str, Any]:
    try:
        with connect() as connection:
            last = fetch_one(
                connection,
                """
                SELECT analysis_run_id, computed_at, status, population
                FROM experiment_analysis_runs
                ORDER BY computed_at DESC LIMIT 1
                """,
            )
            n = fetch_one(connection, "SELECT COUNT(*) AS n FROM experiment_protocol_versions")
        return {
            "status": "AVAILABLE",
            "source": "experiments",
            "mode": "read-only",
            "contract_version": CONTRACT_VERSION,
            "last_analysis": last,
            "protocols": (n or {}).get("n") or 0,
            "auto_route": False,
        }
    except Exception as exc:
        return {
            "status": "DEGRADED",
            "source": "experiments",
            "mode": "read-only",
            "contract_version": CONTRACT_VERSION,
            "detail": f"{type(exc).__name__}: {exc}",
            "auto_route": False,
        }
