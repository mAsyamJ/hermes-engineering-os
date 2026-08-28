"""Constrained policy YAML schema. No executable expressions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engineering_os.adaptation import (
    CONTRACT_VERSION,
    FORBIDDEN_KEYS,
    PHASE3_CONTRACT,
    PHASE4_CONTRACT,
    PHASE5_CONTRACT,
    PHASE6_CONTRACT,
    SCOPES,
    SELECTOR_FIELDS,
    SELECTOR_OPS,
    V1_ACTUATION_SCOPES,
)
from engineering_os.experiments.config_snapshot import canonical_dumps, sha256_text, strip_secrets
from engineering_os.redaction import _SECRET_KEY, _SECRET_VALUE

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = ROOT / "policies" / "adaptation"

ALLOWED_TOP = frozenset(
    {
        "policy_id",
        "policy_version",
        "source_recommendation",
        "source_experiment",
        "treatment_dimension",
        "scope",
        "selectors",
        "candidate",
        "fallback",
        "shadow",
        "canary",
        "guardrails",
        "rollback",
        "approval",
        "expiry",
        "contracts",
        "deny",
    }
)
VARIANT_KEYS = frozenset({"variant_id", "variant_name", "artifact", "config_hash", "snapshot"})


class PolicyError(ValueError):
    pass


def _walk_keys(value: Any, found: set[str] | None = None) -> set[str]:
    found = found or set()
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(str(key))
            _walk_keys(item, found)
    elif isinstance(value, list):
        for item in value:
            _walk_keys(item, found)
    return found


def _assert_no_secrets(value: Any, key: str = "") -> None:
    if _SECRET_KEY.search(key):
        raise PolicyError(f"secret-like key forbidden: {key}")
    if isinstance(value, dict):
        for k, item in value.items():
            _assert_no_secrets(item, str(k))
        return
    if isinstance(value, list):
        for item in value:
            _assert_no_secrets(item, key)
        return
    if isinstance(value, str) and _SECRET_VALUE.search(value):
        raise PolicyError("secret-like value forbidden in policy")


def _require_contracts(contracts: dict[str, Any]) -> None:
    expected = {
        "phase3": PHASE3_CONTRACT,
        "phase4": PHASE4_CONTRACT,
        "phase5": PHASE5_CONTRACT,
        "phase6": PHASE6_CONTRACT,
        "phase7": CONTRACT_VERSION,
    }
    for key, version in expected.items():
        if contracts.get(key) != version:
            raise PolicyError(f"contracts.{key} must be {version}")


def _validate_selectors(selectors: dict[str, Any]) -> None:
    if not isinstance(selectors, dict):
        raise PolicyError("selectors must be a mapping")
    match = selectors.get("match") or "ALL"
    if match not in {"ALL", "ANY"}:
        raise PolicyError("selectors.match must be ALL or ANY")
    conditions = selectors.get("conditions")
    if not isinstance(conditions, list) or not conditions:
        raise PolicyError("selectors.conditions required")
    for cond in conditions:
        if not isinstance(cond, dict):
            raise PolicyError("selector condition must be a mapping")
        extra = set(cond) - {"field", "op", "values"}
        if extra:
            raise PolicyError(f"unknown selector fields: {sorted(extra)}")
        if cond.get("field") not in SELECTOR_FIELDS:
            raise PolicyError(f"unknown selector field {cond.get('field')}")
        if cond.get("op") not in SELECTOR_OPS:
            raise PolicyError(f"unknown selector op {cond.get('op')}")
        values = cond.get("values")
        if not isinstance(values, list) or not values:
            raise PolicyError("selector values required")
        if any(not isinstance(item, (str, int, bool)) for item in values):
            raise PolicyError("selector values must be scalars")


def validate_raw(data: dict[str, Any], source: str = "") -> dict[str, Any]:
    unknown = set(data) - ALLOWED_TOP
    if unknown:
        raise PolicyError(f"unknown fields: {sorted(unknown)}")
    forbidden = _walk_keys(data) & FORBIDDEN_KEYS
    if forbidden:
        raise PolicyError(f"executable fields forbidden: {sorted(forbidden)}")
    _assert_no_secrets(data)
    for required in (
        "policy_id",
        "policy_version",
        "treatment_dimension",
        "scope",
        "selectors",
        "candidate",
        "fallback",
        "guardrails",
        "rollback",
        "canary",
        "contracts",
    ):
        if required not in data:
            raise PolicyError(f"missing {required}")
    if data["scope"] not in SCOPES:
        raise PolicyError(f"invalid scope {data['scope']}")
    if data["scope"] not in V1_ACTUATION_SCOPES and data["scope"] != "PRODUCTION_SHADOW":
        raise PolicyError(f"scope {data['scope']} is not actuable in phase7-adapt-v1")
    _validate_selectors(data["selectors"])
    _require_contracts(data["contracts"])
    if not data["guardrails"]:
        raise PolicyError("guardrails required")
    rollback = data["rollback"]
    if not isinstance(rollback, dict) or not rollback.get("target"):
        raise PolicyError("rollback.target required")
    canary = data["canary"]
    if int(canary.get("max_concurrent_candidate") or 1) < 1:
        raise PolicyError("max_concurrent_candidate must be >= 1")
    if int(canary.get("max_llm_calls") or 0) != 0:
        raise PolicyError("max_llm_calls must be 0")
    for role in ("candidate", "fallback"):
        variant = data[role]
        extra = set(variant) - VARIANT_KEYS
        if extra:
            raise PolicyError(f"{role} unknown fields: {sorted(extra)}")
        if "variant_id" not in variant:
            raise PolicyError(f"{role}.variant_id required")
    cleaned = strip_secrets(data)
    cleaned["_source"] = source
    body = {k: v for k, v in cleaned.items() if not str(k).startswith("_")}
    cleaned["_policy_hash"] = sha256_text(canonical_dumps(body))
    return cleaned


def load_path(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise PolicyError("PyYAML is required to load policies")
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise PolicyError("policy must be a mapping")
    return validate_raw(data, source=str(path))


def load_id(policy_id: str) -> dict[str, Any]:
    path = POLICY_DIR / f"{policy_id}.yaml"
    if not path.is_file():
        matches = sorted(POLICY_DIR.glob(f"{policy_id}*.yaml"))
        if len(matches) == 1:
            path = matches[0]
        elif not matches:
            raise PolicyError(f"policy not found: {policy_id}")
        else:
            raise PolicyError(f"ambiguous policy id: {policy_id}")
    return load_path(path)
