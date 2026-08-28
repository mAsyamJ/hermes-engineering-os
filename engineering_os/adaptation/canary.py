"""Bounded fixture canary. Not a Phase 6 experiment. No Hermes dispatcher."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import hashlib
import hmac

from engineering_os.adaptation.resolver import resolve_policy
from engineering_os.experiments.benchmarks import materialize_case
from engineering_os.evaluation.engine import evaluate_trees
from engineering_os.evaluation.profiles import load_profile

ROOT = Path(__file__).resolve().parents[2]


def _work_root() -> Path:
    override = os.environ.get("EOS_ADAPTATION_RUNTIME")
    path = Path(override) if override else Path(tempfile.gettempdir()) / "eos-adaptation"
    path.mkdir(parents=True, exist_ok=True)
    return path


def eligible(unit_id: str, seed: str, max_candidate_pct: float) -> bool:
    digest = hmac.new(seed.encode("utf-8"), f"canary|{unit_id}".encode("utf-8"), hashlib.sha256).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    return bucket < float(max_candidate_pct)


def plan_canary(policy: dict[str, Any]) -> dict[str, Any]:
    spec = policy.get("spec") or policy
    canary = spec.get("canary") or {}
    return {
        "status": "success",
        "policy_id": spec.get("policy_id") or policy.get("policy_id"),
        "policy_hash": spec.get("_policy_hash") or policy.get("policy_hash"),
        "scope": spec.get("scope"),
        "max_units": int(canary.get("max_units") or 4),
        "max_candidate_pct": float(canary.get("max_candidate_pct") or 1.0),
        "max_concurrent_candidate": int(canary.get("max_concurrent_candidate") or 1),
        "selection": canary.get("selection") or "assign-hmac-sha256-v1",
        "seed": canary.get("seed") or f"{spec.get('policy_id')}-canary",
        "guardrails": spec.get("guardrails") or [],
        "fallback_config_hash": (spec.get("fallback") or {}).get("config_hash"),
        "expiry": canary.get("expiry"),
        "auto_promote": False,
    }


def execute_unit(
    unit_id: str,
    artifact: str,
    *,
    persist_eval: bool = False,
) -> dict[str, Any]:
    os.environ.setdefault("EOS_EVAL_SANDBOX", "inline")
    work = _work_root() / "canary" / unit_id.replace(":", "_")
    if work.exists():
        shutil.rmtree(work)
    materialize_case({"artifact": artifact}, work)
    profile = load_profile("fixture")
    payload = evaluate_trees(
        work,
        profile,
        baseline=work,
        eligibility="TEST_ELIGIBLE",
        github_state="NOT_APPLICABLE",
    )
    vector = payload.get("quality_vector") or {}
    return {
        "unit_id": unit_id,
        "artifact": artifact,
        "quality_vector": vector,
        "llm_call_count": 0,
        "evaluation": payload if persist_eval else {"quality_vector": vector},
    }


def run_fixture_canary(
    policy: dict[str, Any],
    *,
    units: list[str] | None = None,
    state: dict[str, Any] | None = None,
    execute: bool = True,
) -> dict[str, Any]:
    spec = policy.get("spec") or policy
    planned = plan_canary(policy)
    seed = planned["seed"]
    max_pct = planned["max_candidate_pct"]
    max_units = planned["max_units"]
    max_conc = planned["max_concurrent_candidate"]
    unit_ids = units or [f"u{i}" for i in range(max_units)]
    unit_ids = unit_ids[:max_units]
    exposures: list[dict[str, Any]] = []
    concurrent = 0
    for unit_id in unit_ids:
        context = {
            "task_id": unit_id,
            "board": (spec.get("selectors") or {}).get("conditions", [{}])[0].get("values", ["fixture"])[0]
            if False
            else "eos-phase6-exp",
            "task_class": "fixture",
            "environment": "fixture",
            "scope": spec.get("scope") or "FIXTURE",
            "profile": "fixture",
        }
        # Prefer first EQ board selector if present.
        for cond in (spec.get("selectors") or {}).get("conditions") or []:
            if cond.get("field") == "board" and cond.get("values"):
                context["board"] = str(cond["values"][0])
            if cond.get("field") == "task_class" and cond.get("values"):
                context["task_class"] = str(cond["values"][0])
            if cond.get("field") == "environment" and cond.get("values"):
                context["environment"] = str(cond["values"][0])
        decision = resolve_policy(context, state)
        selected = "BASELINE"
        artifact = ((spec.get("fallback") or {}).get("artifact")) or "clean"
        if (
            decision.get("result") == "CANDIDATE"
            and decision.get("resolution") == "CANDIDATE"
            and eligible(unit_id, seed, max_pct)
            and concurrent < max_conc
        ):
            selected = "CANDIDATE"
            artifact = ((spec.get("candidate") or {}).get("artifact")) or "clean"
            concurrent += 1
        outcome: dict[str, Any] = {}
        if execute:
            outcome = execute_unit(unit_id, artifact)
        exposures.append(
            {
                "unit_id": unit_id,
                "selected": selected,
                "artifact": artifact,
                "policy_hash": spec.get("_policy_hash") or policy.get("policy_hash"),
                "candidate_config_hash": (spec.get("candidate") or {}).get("config_hash"),
                "fallback_config_hash": (spec.get("fallback") or {}).get("config_hash"),
                "resolution": decision,
                "outcome": outcome,
                "fidelity": "MATCHED" if execute else "UNKNOWN",
                "llm_call_count": 0,
            }
        )
    return {
        "status": "success",
        "plan": planned,
        "exposures": exposures,
        "candidate_n": sum(1 for row in exposures if row["selected"] == "CANDIDATE"),
        "baseline_n": sum(1 for row in exposures if row["selected"] == "BASELINE"),
        "max_concurrent_observed": concurrent,
        "auto_promote": False,
    }
