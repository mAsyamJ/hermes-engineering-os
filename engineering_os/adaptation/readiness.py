"""Independent PAR readiness cells. Never collapse into one green status."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engineering_os.adaptation import (
    APPROVAL_A_STATUS,
    APPROVAL_B_STATUS,
    CANARY_PACKAGE_STATUS,
    LLM_BUDGET_STATUS,
    MEMORY_ISOLATION,
    PAR_CONTRACT,
    PRODUCTION_ACTUATION,
    PRODUCTION_APPROVAL,
    PRODUCTION_RECOMMENDATION,
    PRODUCTION_SHADOW_STATUS,
    REAL_CAUSAL_EVIDENCE,
    RUNTIME_ACTUATION,
    RUNTIME_INTEGRATION,
    SECURE_HUMAN_AUTHORITY,
)
from engineering_os.adaptation.approval_ed25519 import production_trust_anchor_status
from engineering_os.experiments.budget_gate import budget_authorization_status

ROOT = Path(__file__).resolve().parents[2]


def _patch_present() -> bool:
    return (ROOT / "patches" / "hermes" / "0001-pre-worker-spawn-hook.patch").is_file()


def cells() -> dict[str, Any]:
    trust = production_trust_anchor_status()
    budget = budget_authorization_status()
    return {
        "secure_human_authority": SECURE_HUMAN_AUTHORITY,
        "runtime_actuation": RUNTIME_ACTUATION if _patch_present() else RUNTIME_INTEGRATION,
        "memory_isolation": MEMORY_ISOLATION,
        "real_causal_evidence": REAL_CAUSAL_EVIDENCE,
        "production_shadow": PRODUCTION_SHADOW_STATUS,
        "approval_a": APPROVAL_A_STATUS,
        "canary_package": CANARY_PACKAGE_STATUS,
        "approval_b": APPROVAL_B_STATUS,
        "production_adaptation": PRODUCTION_ACTUATION,
        "human_approval_boundary": PRODUCTION_APPROVAL,
        "production_evidence": PRODUCTION_RECOMMENDATION,
        "runtime_integration_live": RUNTIME_INTEGRATION,
        "llm_budget": budget.get("status") or LLM_BUDGET_STATUS,
        "trust_anchor": trust,
        "live_patch_deployed": False,
        "official_pre_spawn_seam": "NOT_FOUND",
        "contract_version": PAR_CONTRACT,
        "phase7_contract": "phase7-adapt-v1",
    }


def cell(name: str) -> dict[str, Any]:
    mapping = cells()
    aliases = {
        "authority": "secure_human_authority",
        "runtime": "runtime_actuation",
        "memory": "memory_isolation",
        "evidence": "real_causal_evidence",
        "canary": "canary_package",
    }
    key = aliases.get(name, name)
    if key not in mapping:
        return {"status": "NOT_FOUND", "cell": name}
    return {
        "status": "AVAILABLE",
        "cell": key,
        "value": mapping[key],
        "cells": {name: mapping[name] for name in (
            "secure_human_authority",
            "runtime_actuation",
            "memory_isolation",
            "real_causal_evidence",
            "production_shadow",
            "approval_a",
            "canary_package",
            "approval_b",
            "production_adaptation",
        )},
        "collapsed": False,
        "production_adaptation": PRODUCTION_ACTUATION,
    }
