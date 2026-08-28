"""Versioned evaluator registry. Commands never come from task text."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from engineering_os.evaluation import CONTRACT_VERSION


def _hash(spec: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def definitions() -> list[dict[str, Any]]:
    rows = [
        {
            "evaluator_id": "repo.build",
            "evaluator_version": "1",
            "category": "BUILD",
            "sandbox_tier": "C",
            "supports_baseline": True,
            "supports_candidate": True,
            "command_key": "build",
            "description": "Approved repository build/compile command",
        },
        {
            "evaluator_id": "repo.tests",
            "evaluator_version": "1",
            "category": "TESTS",
            "sandbox_tier": "C",
            "supports_baseline": True,
            "supports_candidate": True,
            "command_key": "tests",
            "description": "Approved repository test command",
        },
        {
            "evaluator_id": "repo.regression",
            "evaluator_version": "1",
            "category": "REGRESSION",
            "sandbox_tier": "A",
            "supports_baseline": True,
            "supports_candidate": True,
            "command_key": None,
            "description": "Derived baseline vs candidate test/build comparison",
        },
        {
            "evaluator_id": "repo.lint",
            "evaluator_version": "1",
            "category": "LINT",
            "sandbox_tier": "C",
            "supports_baseline": True,
            "supports_candidate": True,
            "command_key": "lint",
            "description": "Approved lint command; pre-existing issues are not automatic FAIL",
        },
        {
            "evaluator_id": "repo.typecheck",
            "evaluator_version": "1",
            "category": "TYPECHECK",
            "sandbox_tier": "C",
            "supports_baseline": True,
            "supports_candidate": True,
            "command_key": "typecheck",
            "description": "Approved typecheck/static parse command",
        },
        {
            "evaluator_id": "repo.scope_policy",
            "evaluator_version": "1",
            "category": "SCOPE_POLICY",
            "sandbox_tier": "A",
            "supports_baseline": False,
            "supports_candidate": True,
            "command_key": None,
            "description": "Encoded path policies on the candidate patch/tree",
        },
        {
            "evaluator_id": "repo.architecture_policy",
            "evaluator_version": "1",
            "category": "ARCHITECTURE_POLICY",
            "sandbox_tier": "A",
            "supports_baseline": False,
            "supports_candidate": True,
            "command_key": None,
            "description": "Encoded import/layer policies",
        },
        {
            "evaluator_id": "repo.security",
            "evaluator_version": "1",
            "category": "SECURITY",
            "sandbox_tier": "B",
            "supports_baseline": False,
            "supports_candidate": True,
            "command_key": None,
            "description": "Deterministic secret/path guards; no network audit",
        },
        {
            "evaluator_id": "task.acceptance_checks",
            "evaluator_version": "1",
            "category": "ACCEPTANCE_CRITERIA",
            "sandbox_tier": "A",
            "supports_baseline": False,
            "supports_candidate": True,
            "command_key": None,
            "description": "Structured acceptance criteria only",
        },
        {
            "evaluator_id": "github.ci",
            "evaluator_version": "1",
            "category": "CI_EVIDENCE",
            "sandbox_tier": "A",
            "supports_baseline": False,
            "supports_candidate": True,
            "command_key": None,
            "description": "Normalized CI evidence including BLOCKED_AUTH",
        },
        {
            "evaluator_id": "llm.judge",
            "evaluator_version": "1",
            "category": "EXPERIMENTAL",
            "sandbox_tier": "A",
            "supports_baseline": False,
            "supports_candidate": True,
            "command_key": None,
            "disabled": True,
            "description": "Disabled LLM judge interface; fakes only",
        },
    ]
    for row in rows:
        row["contract_version"] = CONTRACT_VERSION
        row["impl_hash"] = _hash({k: row[k] for k in row if k != "impl_hash"})
        row["config_hash"] = row["impl_hash"]
    return rows


def by_id(evaluator_id: str) -> dict[str, Any]:
    matches = [item for item in definitions() if item["evaluator_id"] == evaluator_id]
    if len(matches) != 1:
        raise KeyError(evaluator_id)
    return matches[0]
