"""Field provenance tags and registry schemas (lightweight, no external deps)."""

from __future__ import annotations

from typing import Any, Literal

FieldKind = Literal["DERIVED", "CURATED", "UNKNOWN"]

REQUIRED_SKILL_KEYS = (
    "skill_id",
    "display_name",
    "description",
    "native_path",
    "source",
    "source_type",
    "trust_tier",
    "install_state",
    "capabilities",
    "domains",
    "task_types",
    "triggers",
    "negative_triggers",
    "when_to_use",
    "when_not_to_use",
    "field_kinds",
)


def tagged(value: Any, kind: FieldKind) -> dict[str, Any]:
    return {"value": value, "kind": kind}


def validate_skill_entry(entry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_SKILL_KEYS:
        if key not in entry:
            errors.append(f"missing:{key}")
    tier = entry.get("trust_tier")
    if tier not in {None, "T0", "T1", "T2", "T3", "T4"} and not (
        isinstance(tier, dict) and tier.get("value") in {"T0", "T1", "T2", "T3", "T4"}
    ):
        # allow plain string tiers
        if isinstance(tier, str) and tier in {"T0", "T1", "T2", "T3", "T4"}:
            pass
        elif not isinstance(tier, str):
            errors.append("invalid:trust_tier")
    return errors


def flatten_value(field: Any) -> Any:
    if isinstance(field, dict) and "value" in field and "kind" in field and len(field) <= 3:
        return field["value"]
    return field
