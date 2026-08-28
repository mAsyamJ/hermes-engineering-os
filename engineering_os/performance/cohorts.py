"""Versioned, hashable cohort definitions. No NLP on task titles."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "config" / "performance-cohorts.yaml"


def _yaml_load(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        raise RuntimeError("PyYAML required to load cohort config") from None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("performance-cohorts.yaml must be a mapping")
    return data


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_cohorts(path: Path | None = None) -> dict[str, Any]:
    return _yaml_load(path or DEFAULT_PATH)


def excluded_identity(config: dict[str, Any]) -> dict[str, set[str]]:
    return {
        "task_ids": {str(x) for x in (config.get("excluded_task_ids") or [])},
        "boards": {str(x) for x in (config.get("excluded_boards") or [])},
        "prefixes": {str(x) for x in (config.get("excluded_workspace_prefixes") or [])},
        "canaries": {str(x) for x in (config.get("canary_task_ids") or [])},
    }


def is_fixture_task(task: dict[str, Any], config: dict[str, Any]) -> bool:
    ident = excluded_identity(config)
    task_id = str(task.get("task_id") or "")
    board = str(task.get("board") or "")
    workspace = str(task.get("workspace_path") or "")
    if task.get("production_cohort") is False:
        return True
    if task_id in ident["task_ids"] or task_id in ident["canaries"]:
        return True
    if board in ident["boards"]:
        return True
    if any(workspace.startswith(prefix) for prefix in ident["prefixes"] if prefix):
        return True
    if str(task.get("evaluation_cohort") or "") == "fixture":
        return True
    return False


def matches_cohort(task: dict[str, Any], cohort: dict[str, Any], config: dict[str, Any]) -> tuple[bool, str]:
    """Return (eligible, exclusion_reason)."""
    fixture = is_fixture_task(task, config)
    if cohort.get("exclude_fixture", True) and fixture:
        return False, "fixture_excluded"
    if cohort.get("include_fixture") and not fixture:
        return False, "not_fixture"
    if cohort.get("production") is True and not task.get("production_cohort"):
        return False, "not_production"
    if cohort.get("production") is False and task.get("production_cohort") and not cohort.get("include_fixture"):
        return False, "production_excluded"
    boards = {str(x) for x in (cohort.get("boards") or [])}
    if boards and str(task.get("board") or "") not in boards:
        return False, "board_mismatch"
    wanted_model = cohort.get("model_attribution")
    if wanted_model and task.get("model_attribution") != wanted_model:
        return False, "model_attribution_mismatch"
    wanted_skill = cohort.get("skill_attribution")
    if wanted_skill and task.get("skill_attribution") != wanted_skill:
        return False, "skill_attribution_mismatch"
    return True, "included"


def cohort_members(
    tasks: Iterable[dict[str, Any]],
    cohort: dict[str, Any],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    members: list[dict[str, Any]] = []
    exclusions: list[dict[str, str]] = []
    for task in tasks:
        ok, reason = matches_cohort(task, cohort, config)
        if ok:
            members.append(task)
        else:
            exclusions.append(
                {
                    "board": str(task.get("board") or ""),
                    "task_id": str(task.get("task_id") or ""),
                    "reason": reason,
                }
            )
    return members, exclusions


def snapshot(cohort: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    definition = {
        "cohort_id": cohort["cohort_id"],
        "version": cohort.get("version") or "v1",
        "description": cohort.get("description") or "",
        "selector": {
            key: cohort.get(key)
            for key in (
                "production",
                "boards",
                "exclude_fixture",
                "include_fixture",
                "model_attribution",
                "skill_attribution",
            )
            if key in cohort
        },
        "exclusions": {
            "task_ids": sorted(excluded_identity(config)["task_ids"]),
            "boards": sorted(excluded_identity(config)["boards"]),
            "canaries": sorted(excluded_identity(config)["canaries"]),
        },
    }
    return {
        "cohort_id": cohort["cohort_id"],
        "cohort_version": cohort.get("version") or "v1",
        "config_hash": canonical_hash(definition),
        "definition": definition,
        "description": cohort.get("description") or "",
    }
