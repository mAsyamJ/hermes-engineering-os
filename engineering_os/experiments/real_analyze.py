"""File-backed confirmatory analysis. Does not invent a winner."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from engineering_os.adaptation.recommend import recommend_from_result
from engineering_os.experiments.analyze import CONFIRMATORY, analyze
from engineering_os.experiments.validity import evaluate as evaluate_validity

ROOT = Path(__file__).resolve().parents[2]


def artifact_dir(protocol: dict[str, Any]) -> Path:
    override = os.environ.get("EOS_EXPERIMENT_RUNTIME")
    base = Path(override) if override else ROOT / ".runtime" / "experiments"
    path = base / str(protocol.get("experiment_id") or "unknown")
    path.mkdir(parents=True, exist_ok=True)
    return path


def persist_sequence(
    protocol: dict[str, Any],
    assignments: list[dict[str, Any]],
    results: list[dict[str, Any]],
    extra: dict[str, Any] | None = None,
) -> Path:
    dest = artifact_dir(protocol) / "sequence.json"
    body = {
        "experiment_id": protocol.get("experiment_id"),
        "protocol_hash": protocol.get("_definition_hash"),
        "assignments": assignments,
        "results": results,
        **(extra or {}),
    }
    dest.write_text(json.dumps(body, default=str, indent=2) + "\n", encoding="utf-8")
    return dest


def load_sequence(experiment: str) -> dict[str, Any]:
    override = os.environ.get("EOS_EXPERIMENT_RUNTIME")
    base = Path(override) if override else ROOT / ".runtime" / "experiments"
    path = Path(experiment)
    if path.suffix == ".json" and path.is_file():
        target = path
    else:
        target = base / experiment / "sequence.json"
    if not target.is_file():
        raise FileNotFoundError(target)
    return json.loads(target.read_text(encoding="utf-8"))


def observations_from_results(protocol: dict[str, Any], results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metric = str((protocol.get("primary_metric") or {}).get("id") or "phase4.quality_vector.tests")
    rows: list[dict[str, Any]] = []
    for result in results:
        vector = result.get("quality_vector") or {}
        value = result.get("primary_value") if "primary_value" in result else vector.get("tests")
        rows.append(
            {
                "unit_id": result.get("unit_id"),
                "metric_id": metric,
                "value": value,
                "known": value in {"PASS", "FAIL", 0, 1, True, False},
                "started": True,
            }
        )
    return rows


def validity_from_results(protocol: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, str]:
    memory_ok = all((row.get("memory_isolation") or {}).get("ok", True) for row in results) if results else False
    workspace_ok = all((row.get("workspace_isolation") or {}).get("ok", True) for row in results) if results else False
    known = sum(1 for row in results if (row.get("primary_value") or (row.get("quality_vector") or {}).get("tests")) in {"PASS", "FAIL"})
    evaluator_ok = any((row.get("quality_vector") or {}) for row in results)
    return evaluate_validity(
        {
            "scope": protocol.get("scope") or "BENCHMARK",
            "protocol_hash_ok": True,
            "assignment_ok": True,
            "config_ok": True,
            "environment_ok": True,
            "memory_isolated": memory_ok,
            "workspace_ok": workspace_ok,
            "coverage_ok": bool(results) and known == len(results),
            "evaluator_ok": evaluator_ok,
            "fidelity_required": True,
            "exposure_fidelity": "MATCHED",
        }
    )


def pag2_label(analysis: dict[str, Any], recommendation: dict[str, Any] | None = None) -> str:
    conclusion = str(analysis.get("conclusion") or "NOT_STARTED")
    if conclusion == "COLLECTING":
        return "COLLECTING"
    if conclusion == "INVALIDATED":
        return "INVALIDATED"
    rec = recommendation or {}
    if rec.get("production_promotable") and rec.get("classification") == "PRODUCTION_CANDIDATE":
        return "QUALIFIED_CANDIDATE"
    if conclusion in CONFIRMATORY or conclusion in {"INSUFFICIENT_DATA", "GUARDRAIL_FAILURE"}:
        return "VALID_NO_PROMOTION"
    return conclusion


def analyze_real_sequence(
    protocol: dict[str, Any],
    assignments: list[dict[str, Any]],
    results: list[dict[str, Any]],
    *,
    final: bool = True,
) -> dict[str, Any]:
    used = assignments[: len(results)]
    if not used or any(not row.get("variant_role") for row in used):
        analysis = {
            "conclusion": "COLLECTING",
            "reason": "assignments missing variant_role; confirmatory analysis not computed",
            "horizon_reached": False,
        }
        return {
            "status": "success",
            "analysis": analysis,
            "recommendation": {"auto_promote": False, "production_promotable": False},
            "pag2_label": "COLLECTING",
            "auto_promote": False,
            "promote": False,
        }
    observations = observations_from_results(protocol, results)
    validity = validity_from_results(protocol, results)
    security_fail = any((row.get("security_value") or (row.get("quality_vector") or {}).get("security")) == "FAIL" for row in results)
    guard = "FAIL" if security_fail else "PASS"
    analysis = analyze(
        protocol,
        used,
        observations,
        validity=validity,
        final=final,
        guardrail_state=guard,
    )
    wrapped = {
        **analysis,
        "source": "phase6",
        "scope": protocol.get("scope"),
        "treatment_dimension": protocol.get("treatment_dimension"),
        "experiment_id": protocol.get("experiment_id"),
        "protocol_hash": protocol.get("_definition_hash"),
        "real_hermes_inference": True,
        "fixture_validation_only": bool(protocol.get("fixture_validation_only")),
        "candidate_config_hash": ((protocol.get("candidate") or {}).get("config_hash")),
        "control_config_hash": ((protocol.get("control") or {}).get("config_hash")),
    }
    recommendation = recommend_from_result(wrapped)
    label = pag2_label(analysis, recommendation)
    return {
        "status": "success",
        "analysis": analysis,
        "recommendation": recommendation,
        "pag2_label": label,
        "auto_promote": False,
        "promote": False,
        "protocol_hash": protocol.get("_definition_hash"),
        "experiment_id": protocol.get("experiment_id"),
    }


def analyze_persisted(experiment: str, protocol: dict[str, Any], *, final: bool = True) -> dict[str, Any]:
    sequence = load_sequence(experiment)
    analyzed = analyze_real_sequence(
        protocol,
        list(sequence.get("assignments") or []),
        list(sequence.get("results") or []),
        final=final,
    )
    dest = artifact_dir(protocol) / "analysis.json"
    dest.write_text(json.dumps(analyzed, default=str, indent=2) + "\n", encoding="utf-8")
    return analyzed
