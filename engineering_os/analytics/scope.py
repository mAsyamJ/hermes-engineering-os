"""Load analytics cohort configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCOPE_PATH = ROOT / "config" / "analytics-scope.yaml"


def load_scope(path: Path | None = None) -> dict[str, Any]:
    target = path or SCOPE_PATH
    text = target.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except ImportError:
        return _parse_simple_yaml(text)
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError("analytics-scope.yaml must be a mapping")
    return data


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Minimal subset parser so unit tests do not require PyYAML."""
    result: dict[str, Any] = {}
    current_list: str | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("  - "):
            if current_list is None:
                continue
            result.setdefault(current_list, []).append(_scalar(line[4:].strip()))
            continue
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_list = key if value == "" else None
            if value == "":
                result[key] = []
            else:
                result[key] = _scalar(value)
                current_list = None
    return result


def _scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    return value


def cohort_for(task: dict[str, Any], scope: dict[str, Any]) -> str:
    board = str(task.get("board") or "")
    task_id = str(task.get("id") or task.get("task_id") or "")
    workspace = str(task.get("workspace_path") or "")
    excluded_boards = {str(item) for item in scope.get("excluded_boards") or []}
    excluded_ids = {str(item) for item in scope.get("excluded_task_ids") or []}
    prefixes = [str(item) for item in scope.get("excluded_workspace_prefixes") or []]
    if board in excluded_boards or task_id in excluded_ids:
        return "fixture"
    if any(workspace.startswith(prefix) for prefix in prefixes if prefix):
        return "fixture"
    if board in {str(item) for item in scope.get("included_boards") or []}:
        return "production"
    return "excluded"


def is_production(task: dict[str, Any], scope: dict[str, Any]) -> bool:
    return cohort_for(task, scope) == "production"
