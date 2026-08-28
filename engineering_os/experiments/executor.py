"""Deterministic fixture executor. No Hermes LLM. No production worktrees."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from engineering_os.evaluation.engine import evaluate_trees
from engineering_os.evaluation.profiles import load_profile
from engineering_os.experiments import BOARD, RUNTIME_ROOT, TASK_PREFIX
from engineering_os.experiments.benchmarks import materialize_case
from engineering_os.experiments.config_snapshot import sha256_text
from engineering_os.experiments.isolation import workspace_ok

ROOT = Path(__file__).resolve().parents[2]


def _work_root() -> Path:
    override = os.environ.get("EOS_EXPERIMENT_RUNTIME")
    path = Path(override) if override else Path(tempfile.gettempdir()) / "eos-experiments"
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_unit(
    assignment: dict[str, Any],
    protocol: dict[str, Any],
    *,
    persist: bool = False,
    connection: Any = None,
) -> dict[str, Any]:
    os.environ.setdefault("EOS_EVAL_SANDBOX", "inline")
    role = assignment["variant_role"]
    variant = protocol["control"] if role == "CONTROL" else protocol["candidate"]
    artifact_name = (variant["snapshot"].get("artifact") or {}).get("name") or "clean"
    work = _work_root() / protocol["experiment_id"] / assignment["unit_id"].replace(":", "_")
    if work.exists():
        shutil.rmtree(work)
    materialized = materialize_case({"artifact": artifact_name}, work)
    sibling = work.parent / ("_other_" + assignment["unit_id"].replace(":", "_"))
    isolation = {"ok": True, "shared": []}
    if sibling.exists():
        isolation = workspace_ok(work, sibling)
    profile = load_profile("fixture")
    payload = evaluate_trees(
        work,
        profile,
        baseline=work,
        eligibility="TEST_ELIGIBLE",
        github_state="NOT_APPLICABLE",
    )
    vector = payload.get("quality_vector") or {}
    task_id = TASK_PREFIX + sha256_text(assignment["unit_id"])[:12]
    evaluation_run_id = None
    if persist and connection is not None:
        from engineering_os.evaluation.persist import persist_run

        stored = persist_run(
            connection,
            payload,
            {
                "board": BOARD,
                "task_id": task_id,
                "cohort": "fixture",
                "recompute": True,
            },
        )
        evaluation_run_id = stored.get("evaluation_run_id")
    return {
        "unit_id": assignment["unit_id"],
        "variant_role": role,
        "variant_id": assignment["variant_id"],
        "artifact": artifact_name,
        "workspace": str(work),
        "tree_hash": materialized["tree_hash"],
        "quality_vector": vector,
        "primary_value": vector.get("tests"),
        "build_value": vector.get("build"),
        "security_value": vector.get("security"),
        "architecture_value": vector.get("architecture"),
        "llm_calls": 0,
        "board": BOARD,
        "task_id": task_id,
        "evaluation_run_id": evaluation_run_id,
        "workspace_ok": isolation["ok"],
        "profile_hash": payload.get("profile_hash"),
        "contract_version": payload.get("contract_version"),
        "execution_status": payload.get("execution_status"),
        "started": True,
        "completed": payload.get("execution_status") == "COMPLETE",
    }


def collect_from_execution(execution: dict[str, Any], protocol: dict[str, Any]) -> list[dict[str, Any]]:
    versions = {
        "phase3_ruleset": protocol["contracts"]["phase3_ruleset"],
        "phase4_contract": protocol["contracts"]["phase4_contract"],
        "phase5_contract": protocol["contracts"]["phase5_contract"],
        "phase6_contract": protocol["contracts"]["phase6_contract"],
    }
    vector = execution.get("quality_vector") or {}
    rows = [
        {
            "unit_id": execution["unit_id"],
            "metric_id": protocol["primary_metric"]["id"],
            "role": "primary",
            "value": vector.get("tests"),
            "known": vector.get("tests") in {"PASS", "FAIL"},
            "started": True,
            "evaluation_run_id": execution.get("evaluation_run_id"),
            "source_versions": versions,
        }
    ]
    for spec in protocol.get("secondary_metrics") or []:
        key = spec["id"].rsplit(".", 1)[-1]
        rows.append(
            {
                "unit_id": execution["unit_id"],
                "metric_id": spec["id"],
                "role": "secondary",
                "value": vector.get(key),
                "known": vector.get(key) in {"PASS", "FAIL"},
                "started": True,
                "evaluation_run_id": execution.get("evaluation_run_id"),
                "source_versions": versions,
            }
        )
    for spec in protocol.get("guardrails") or []:
        if spec["id"] == "llm_call_count":
            rows.append(
                {
                    "unit_id": execution["unit_id"],
                    "metric_id": spec["id"],
                    "role": "guardrail",
                    "value": execution.get("llm_calls") or 0,
                    "known": True,
                    "started": True,
                    "source_versions": versions,
                }
            )
            continue
        key = spec["id"].rsplit(".", 1)[-1]
        rows.append(
            {
                "unit_id": execution["unit_id"],
                "metric_id": spec["id"],
                "role": "guardrail",
                "value": vector.get(key),
                "known": vector.get(key) is not None,
                "started": True,
                "evaluation_run_id": execution.get("evaluation_run_id"),
                "source_versions": versions,
            }
        )
    return rows
