"""Assignment vs actual exposure. Fallback never reassigns ITT arm."""

from __future__ import annotations

from typing import Any

from engineering_os.experiments import FIDELITY


def classify(assigned_hash: str | None, observed_hash: str | None, *, observed_available: bool) -> str:
    if not observed_available or not observed_hash:
        return "UNKNOWN"
    if not assigned_hash:
        return "UNKNOWN"
    if assigned_hash == observed_hash:
        return "MATCHED"
    return "NONCOMPLIANT"


def record(
    assignment: dict[str, Any],
    observed_config_hash: str | None,
    observed_available: bool = True,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fidelity = classify(assignment.get("config_hash") or assignment.get("assigned_config_hash"), observed_config_hash, observed_available=observed_available)
    if fidelity not in FIDELITY:
        fidelity = "UNKNOWN"
    return {
        "unit_id": assignment["unit_id"],
        "assigned_variant_id": assignment["variant_id"],
        "assigned_variant_role": assignment["variant_role"],
        "observed_config_hash": observed_config_hash,
        "fidelity": fidelity,
        "itt_variant_role": assignment["variant_role"],
        "reassigned": False,
        **(extra or {}),
    }
