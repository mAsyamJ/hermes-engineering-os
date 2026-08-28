"""Safe non-secret prospective configuration snapshots."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from engineering_os.redaction import _SECRET_KEY, _SECRET_VALUE

SECRET_FILENAMES = {".env", "auth.json", "credentials.json", "id_rsa", "id_ed25519"}
DENIED_KEYS = re.compile(
    r"(token|secret|password|authorization|api[_-]?key|cookie|credential|private[_-]?key)",
    re.IGNORECASE,
)


def canonical_dumps(value: Any) -> str:
    return json.dumps(_normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return float(f"{value:.12g}")
    return str(value)


def strip_secrets(value: Any, key: str = "") -> Any:
    if DENIED_KEYS.search(key) or _SECRET_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): strip_secrets(v, str(k)) for k, v in value.items() if str(k) not in SECRET_FILENAMES}
    if isinstance(value, list):
        return [strip_secrets(item, key) for item in value]
    if isinstance(value, str):
        return _SECRET_VALUE.sub("[REDACTED]", value)
    return value


def snapshot(parts: dict[str, Any]) -> dict[str, Any]:
    cleaned = strip_secrets(parts)
    encoded = canonical_dumps(cleaned)
    return {
        "snapshot": cleaned,
        "config_hash": sha256_text(encoded),
        "canonical": encoded,
    }


def hash_file(path: Path) -> str | None:
    if not path.is_file() or path.name in SECRET_FILENAMES:
        return None
    return sha256_bytes(path.read_bytes())


def hash_tree(root: Path) -> dict[str, Any]:
    files: list[dict[str, str]] = []
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name in SECRET_FILENAMES:
                continue
            rel = path.relative_to(root).as_posix()
            files.append({"path": rel, "sha256": sha256_bytes(path.read_bytes())})
    return {"files": files, "tree_hash": sha256_text(canonical_dumps(files))}


def variant_snapshot(
    *,
    variant_id: str,
    variant_name: str,
    treatment_dimension: str,
    model: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
    prompt: dict[str, Any] | None = None,
    skills: dict[str, Any] | None = None,
    tools: dict[str, Any] | None = None,
    artifact: dict[str, Any] | None = None,
    environment: dict[str, Any] | None = None,
    contracts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parts = {
        "variant_id": variant_id,
        "variant_name": variant_name,
        "treatment_dimension": treatment_dimension,
        "model": model or {},
        "profile": profile or {},
        "prompt": prompt or {},
        "skills": skills or {},
        "tools": tools or {},
        "artifact": artifact or {},
        "environment": environment or {},
        "contracts": contracts or {},
    }
    result = snapshot(parts)
    result["variant_id"] = variant_id
    result["variant_name"] = variant_name
    result["treatment_dimension"] = treatment_dimension
    return result
