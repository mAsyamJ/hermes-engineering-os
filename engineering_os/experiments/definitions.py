"""Trusted experiment definition loader. Rejects shell, secrets, PRODUCTION, unknown fields."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engineering_os.experiments import (
    ACTIVATED_TREATMENTS,
    DESIGNS,
    PREPARED_TREATMENTS,
    SCOPES,
    TREATMENT_DIMENSIONS,
    V1_ALLOWED_SCOPES,
)
from engineering_os.experiments.config_snapshot import canonical_dumps, sha256_text, strip_secrets
from engineering_os.redaction import _SECRET_KEY, _SECRET_VALUE

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[2]
DEFINITIONS = ROOT / "experiments" / "definitions"

ALLOWED_TOP = frozenset(
    {
        "experiment_id",
        "version",
        "scope",
        "design",
        "treatment_dimension",
        "hypothesis",
        "expected_direction",
        "control",
        "candidate",
        "experimental_unit",
        "benchmark_suite",
        "assignment",
        "primary_metric",
        "secondary_metrics",
        "guardrails",
        "sample_plan",
        "analysis",
        "budget",
        "missingness",
        "invalidity",
        "cases",
    }
)
FORBIDDEN_KEYS = frozenset(
    {"command", "commands", "cmd", "exec", "shell", "bash", "script", "argv", "entrypoint"}
)
VARIANT_KEYS = frozenset({"variant_id", "variant_name", "artifact", "model", "profile", "prompt", "skills", "tools"})


class DefinitionError(ValueError):
    pass


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        raise DefinitionError("PyYAML is required to load experiment definitions")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise DefinitionError("definition must be a mapping")
    return data


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
        raise DefinitionError(f"secret-like key forbidden: {key}")
    if isinstance(value, dict):
        for k, item in value.items():
            _assert_no_secrets(item, str(k))
        return
    if isinstance(value, list):
        for item in value:
            _assert_no_secrets(item, key)
        return
    if isinstance(value, str) and _SECRET_VALUE.search(value):
        raise DefinitionError("secret-like value forbidden in definition")


def validate_raw(data: dict[str, Any], source: str = "") -> dict[str, Any]:
    unknown = set(data) - ALLOWED_TOP
    if unknown:
        raise DefinitionError(f"unknown fields: {sorted(unknown)}")
    keys = _walk_keys(data)
    forbidden = keys & FORBIDDEN_KEYS
    if forbidden:
        raise DefinitionError(f"executable fields forbidden: {sorted(forbidden)}")
    _assert_no_secrets(data)
    for required in (
        "experiment_id",
        "version",
        "scope",
        "design",
        "treatment_dimension",
        "hypothesis",
        "control",
        "candidate",
        "primary_metric",
        "guardrails",
        "sample_plan",
        "analysis",
        "assignment",
        "budget",
    ):
        if required not in data:
            raise DefinitionError(f"missing {required}")
    scope = data["scope"]
    if scope not in SCOPES:
        raise DefinitionError(f"invalid scope {scope}")
    if scope not in V1_ALLOWED_SCOPES:
        raise DefinitionError("PRODUCTION and NON_PRODUCTION execution are disabled in phase6-exp-v1")
    if scope == "PRODUCTION":
        raise DefinitionError("PRODUCTION experiment execution is disabled")
    if data["design"] not in DESIGNS:
        raise DefinitionError("invalid design")
    dim = data["treatment_dimension"]
    if dim not in TREATMENT_DIMENSIONS:
        raise DefinitionError("invalid treatment_dimension")
    if dim == "MULTI_FACTOR":
        raise DefinitionError("MULTI_FACTOR is not enabled in phase6-exp-v1")
    prepared = False
    if dim not in ACTIVATED_TREATMENTS:
        if dim in PREPARED_TREATMENTS and scope in V1_ALLOWED_SCOPES:
            prepared = True
        else:
            raise DefinitionError(f"treatment {dim} is documented but not activated in V1")
    primary = data["primary_metric"]
    if not isinstance(primary, dict) or "id" not in primary:
        raise DefinitionError("primary_metric.id required")
    if not data["guardrails"]:
        raise DefinitionError("guardrails required")
    plan = data["sample_plan"]
    if "planned_n" not in plan or "alpha" not in plan or "power" not in plan:
        raise DefinitionError("sample_plan requires planned_n, alpha, power")
    analysis = data["analysis"]
    if analysis.get("population") != "INTENTION_TO_TREAT":
        raise DefinitionError("primary analysis population must be INTENTION_TO_TREAT")
    if analysis.get("horizon") != "FIXED":
        raise DefinitionError("phase6-exp-v1 confirmatory experiments are FIXED-HORIZON")
    budget = data["budget"]
    if int(budget.get("max_llm_calls") or 0) != 0:
        raise DefinitionError("max_llm_calls must be 0 unless separately authorized")
    if float(budget.get("max_external_cost") or 0) != 0:
        raise DefinitionError("max_external_cost must be 0")
    for role in ("control", "candidate"):
        variant = data[role]
        extra = set(variant) - VARIANT_KEYS
        if extra:
            raise DefinitionError(f"{role} unknown fields: {sorted(extra)}")
        if "variant_id" not in variant:
            raise DefinitionError(f"{role}.variant_id required")
    assignment = data["assignment"]
    if assignment.get("algorithm") != "assign-hmac-sha256-v1":
        raise DefinitionError("assignment.algorithm must be assign-hmac-sha256-v1")
    if not assignment.get("seed"):
        raise DefinitionError("assignment.seed required")
    cleaned = strip_secrets(data)
    cleaned["_source"] = source
    cleaned["_execution"] = "PREPARED" if prepared else "ACTIVATED"
    cleaned["_definition_hash"] = sha256_text(canonical_dumps({k: v for k, v in cleaned.items() if not str(k).startswith("_")}))
    return cleaned


def load_path(path: Path) -> dict[str, Any]:
    return validate_raw(_load_yaml(path), source=str(path))


def load_id(experiment_id: str) -> dict[str, Any]:
    path = DEFINITIONS / f"{experiment_id}.yaml"
    if not path.is_file():
        raise DefinitionError(f"definition not found: {path}")
    loaded = load_path(path)
    if loaded["experiment_id"] != experiment_id:
        raise DefinitionError("experiment_id does not match filename")
    return loaded


def list_definitions() -> list[Path]:
    if not DEFINITIONS.is_dir():
        return []
    return sorted(DEFINITIONS.glob("*.yaml"))
