"""Trusted evaluation profile loader. Task text cannot add argv."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIR = ROOT / "config" / "evaluation-profiles"


def _scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _parse_simple(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, result)]
    pending_key: str | None = None
    pending_indent = 0
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while stack and indent <= stack[-1][0] and stack[-1][0] >= 0:
            stack.pop()
        parent = stack[-1][1]
        if line.startswith("- "):
            item = line[2:].strip()
            if isinstance(parent, list):
                if item == "{}":
                    parent.append({})
                elif ":" in item and not item.startswith("["):
                    key, value = item.split(":", 1)
                    parent.append({key.strip(): _scalar(value.strip())})
                else:
                    parent.append(_scalar(item))
            elif pending_key is not None and isinstance(parent, dict):
                seq: list[Any] = []
                parent[pending_key] = seq
                stack.append((pending_indent, seq))
                seq.append(_scalar(item))
                pending_key = None
            continue
        if line.endswith(":"):
            key = line[:-1].strip()
            if isinstance(parent, dict):
                parent[key] = {}
                pending_key = key
                pending_indent = indent
                stack.append((indent, parent[key]))
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                parsed = [_scalar(part.strip()) for part in inner.split(",") if part.strip()] if inner else []
                if isinstance(parent, dict):
                    parent[key] = parsed
            elif value == "":
                if isinstance(parent, dict):
                    parent[key] = {}
                    stack.append((indent, parent[key]))
            else:
                if isinstance(parent, dict):
                    parent[key] = _scalar(value)
            pending_key = None
    return result


def load_profile(profile_id: str, directory: Path | None = None) -> dict[str, Any]:
    target = (directory or PROFILE_DIR) / f"{profile_id}.yaml"
    if not target.is_file():
        raise FileNotFoundError(profile_id)
    text = target.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
    except ImportError:
        data = _parse_simple(text)
    if not isinstance(data, dict) or data.get("profile_id") != profile_id:
        raise ValueError(f"profile {profile_id} is invalid")
    data["config_hash"] = hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()
    return data


def list_profiles(directory: Path | None = None) -> list[dict[str, Any]]:
    root = directory or PROFILE_DIR
    rows = []
    for path in sorted(root.glob("*.yaml")):
        rows.append(load_profile(path.stem, directory=root))
    return rows


def approved_command(profile: dict[str, Any], name: str) -> list[str] | None:
    commands = profile.get("commands") or {}
    argv = commands.get(name)
    if argv is None:
        return None
    if isinstance(argv, str):
        raise ValueError("profile commands must be argv lists, not shell strings")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
        raise ValueError(f"invalid command {name}")
    return [str(item) for item in argv]
