"""Drift detection. Any hit blocks new candidate exposure."""

from __future__ import annotations

from typing import Any

from engineering_os.adaptation import CONTRACT_VERSION
from engineering_os.adaptation.compiler import hash_bundle
from engineering_os.adaptation.schema import load_path
from pathlib import Path


def detect(
    *,
    stored_bundle: dict[str, Any],
    approval: dict[str, Any] | None,
    experiment: dict[str, Any] | None = None,
    source_path: str | Path | None = None,
    runtime_capability: str | None = None,
) -> dict[str, Any]:
    events: list[dict[str, str]] = []
    spec = stored_bundle.get("spec") or stored_bundle
    stored_hash = stored_bundle.get("policy_hash") or spec.get("_policy_hash")
    if source_path:
        live = load_path(Path(source_path))
        live_hash = live.get("_policy_hash")
        if live_hash != stored_hash:
            events.append({"kind": "POLICY_FILE_MODIFIED", "detail": "git policy hash != stored bundle"})
    recomputed = hash_bundle({k: v for k, v in spec.items() if not str(k).startswith("_")})
    if stored_hash and recomputed != stored_hash:
        events.append({"kind": "POLICY_HASH_MISMATCH", "detail": "bundle hash drift"})
    contracts = spec.get("contracts") or {}
    if contracts.get("phase7") and contracts.get("phase7") != CONTRACT_VERSION:
        events.append({"kind": "CONTRACT_VERSION_CHANGED", "detail": str(contracts.get("phase7"))})
    if experiment:
        if experiment.get("state") == "INVALIDATED" or experiment.get("conclusion") == "INVALIDATED":
            events.append({"kind": "SOURCE_EXPERIMENT_INVALIDATED", "detail": experiment.get("experiment_id") or ""})
        cand = experiment.get("candidate_config_hash")
        if cand and spec.get("candidate") and spec["candidate"].get("config_hash") and cand != spec["candidate"]["config_hash"]:
            events.append({"kind": "CANDIDATE_CONFIG_HASH_CHANGED", "detail": cand})
        ctrl = experiment.get("control_config_hash")
        if ctrl and spec.get("fallback") and spec["fallback"].get("config_hash") and ctrl != spec["fallback"]["config_hash"]:
            events.append({"kind": "FALLBACK_CONFIG_HASH_CHANGED", "detail": ctrl})
    if approval:
        if not approval.get("ok") and approval.get("reason"):
            events.append({"kind": "APPROVAL_INVALID", "detail": str(approval.get("reason"))})
        if approval.get("policy_hash") and stored_hash and approval["policy_hash"] != stored_hash:
            events.append({"kind": "APPROVAL_HASH_MISMATCH", "detail": "approval bound to different policy hash"})
        if approval.get("expired"):
            events.append({"kind": "APPROVAL_EXPIRED", "detail": str(approval.get("expires_at") or "")})
    if runtime_capability and runtime_capability.startswith("BLOCKED") and spec.get("scope", "").startswith("PRODUCTION"):
        events.append({"kind": "RUNTIME_CAPABILITY_CHANGED", "detail": runtime_capability})
    disable = bool(events)
    return {
        "drift": disable,
        "events": events,
        "block_candidate": disable,
        "silent": False,
    }
