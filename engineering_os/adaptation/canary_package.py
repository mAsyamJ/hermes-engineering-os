"""Signed canary request package scaffold. Does not run production canary."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from engineering_os.adaptation.approval_ed25519 import generate_approval_request, request_hash
from engineering_os.experiments.config_snapshot import canonical_dumps, sha256_text, strip_secrets

ROOT = Path(__file__).resolve().parents[2]


def _runtime() -> Path:
    override = os.environ.get("EOS_ADAPTATION_RUNTIME")
    base = Path(override) if override else ROOT / ".runtime" / "adaptation"
    path = base / "requests"
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_package(
    *,
    recommendation_id: str,
    policy_id: str,
    policy_hash: str,
    policy_version: str,
    candidate_config_hash: str,
    fallback_hash: str,
    rollback_hash: str,
    scope: str = "PRODUCTION_CANARY",
    maximum_exposure: int = 1,
    max_concurrency: int = 1,
    expiry: str,
    evidence: dict[str, Any] | None = None,
    shadow: dict[str, Any] | None = None,
    guardrails: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request = generate_approval_request(
        recommendation_id=recommendation_id,
        policy_id=policy_id,
        policy_hash=policy_hash,
        policy_version=policy_version,
        approval_stage="A",
        scope=scope,
        maximum_exposure=maximum_exposure,
        candidate_config_hash=candidate_config_hash,
        fallback_hash=fallback_hash,
        rollback_hash=rollback_hash,
        expiry=expiry,
    )
    request_id = request["request_id"]
    dest = _runtime() / request_id
    dest.mkdir(parents=True, exist_ok=True)
    files = {
        "approval-request.json": canonical_dumps(request) + "\n",
        "policy-summary.txt": (
            f"policy_id={policy_id}\npolicy_hash={policy_hash}\nscope={scope}\n"
            f"max_exposure={maximum_exposure}\nmax_concurrency={max_concurrency}\n"
            f"expiry={expiry}\nrollback_hash={rollback_hash}\n"
        ),
        "experiment-evidence.json": canonical_dumps(strip_secrets(evidence or {"status": "BLOCKED_EVIDENCE"})) + "\n",
        "guardrails.json": canonical_dumps(strip_secrets(guardrails or {"state": "UNKNOWN"})) + "\n",
        "rollback-plan.json": canonical_dumps({"rollback_hash": rollback_hash, "interrupt_running": False}) + "\n",
        "production-shadow-report.json": canonical_dumps(
            strip_secrets(shadow or {"status": "BLOCKED_EVIDENCE", "mutated": False})
        )
        + "\n",
    }
    checksums: list[str] = []
    for name, text in files.items():
        (dest / name).write_text(text, encoding="utf-8")
        checksums.append(f"{sha256_text(text)}  {name}")
    (dest / "checksums.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    return {
        "status": "READY_SCAFFOLD" if (evidence or {}).get("status") == "PRODUCTION_EVIDENCE_READY" else "BLOCKED_EVIDENCE",
        "request_id": request_id,
        "path": str(dest),
        "request_hash": request.get("request_hash") or request_hash(request),
        "production_canary": "NOT_EXECUTED",
        "secrets": False,
    }
