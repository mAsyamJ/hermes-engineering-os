"""memory-snapshot-v1: secret-free, isolated experiment memory homes."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from engineering_os.experiments.config_snapshot import (
    SECRET_FILENAMES,
    canonical_dumps,
    hash_tree,
    sha256_text,
    strip_secrets,
)

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = "memory-snapshot-v1"
DENIED_NAMES = SECRET_FILENAMES | {
    "auth.lock",
    "id_ed25519",
    "id_rsa",
    "known_hosts",
    "id_ed25519.pub",
}
DENIED_DIRS = {"sessions", "cache", "logs", "sandbox", "sandboxes"}
SAFE_MEMORY_FILES = ("MEMORY.md", "USER.md")


def _runtime_root() -> Path:
    override = os.environ.get("EOS_EXPERIMENT_RUNTIME")
    path = Path(override) if override else Path(tempfile.gettempdir()) / "eos-par-memory"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _is_denied(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if path.name in DENIED_NAMES:
        return True
    return any(part in DENIED_DIRS for part in rel.parts)


def inventory_home(home: Path) -> dict[str, Any]:
    files: list[dict[str, str]] = []
    secrets: list[str] = []
    if home.is_dir():
        for path in sorted(home.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(home).as_posix()
            role = "secret" if _is_denied(path, home) else "safe"
            if role == "secret":
                secrets.append(rel)
            files.append({"path": rel, "role": role})
    return {
        "home": str(home),
        "files": files,
        "secret_paths": secrets,
        "contract": CONTRACT,
    }


def freeze_snapshot(
    *,
    memory_text: str = "",
    user_text: str = "",
    soul_text: str = "",
    config: dict[str, Any] | None = None,
    snapshot_id: str = "M0",
) -> dict[str, Any]:
    cleaned_config = strip_secrets(config or {"model": "baseline"})
    body = {
        "contract": CONTRACT,
        "snapshot_id": snapshot_id,
        "memory": memory_text,
        "user": user_text,
        "soul": soul_text,
        "config": cleaned_config,
    }
    encoded = canonical_dumps(body)
    digest = sha256_text(encoded)
    return {
        "contract": CONTRACT,
        "snapshot_id": snapshot_id,
        "hash": digest,
        "immutable": True,
        "canonical": encoded,
        "memory": memory_text,
        "user": user_text,
        "soul": soul_text,
        "config": cleaned_config,
    }


def materialize_home(snapshot: dict[str, Any], dest: Path) -> dict[str, Any]:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    memories = dest / "memories"
    memories.mkdir()
    (memories / "MEMORY.md").write_text(snapshot.get("memory") or "", encoding="utf-8")
    (memories / "USER.md").write_text(snapshot.get("user") or "", encoding="utf-8")
    if snapshot.get("soul"):
        (dest / "SOUL.md").write_text(str(snapshot["soul"]), encoding="utf-8")
    (dest / "config.yaml").write_text("# redacted experiment config\n", encoding="utf-8")
    tree = hash_tree(dest)
    return {"path": str(dest), "tree_hash": tree["tree_hash"], "files": tree["files"]}


def create_isolated_arms(snapshot: dict[str, Any], prefix: str | None = None) -> dict[str, Any]:
    root = _runtime_root() / (prefix or snapshot["snapshot_id"])
    if root.exists():
        shutil.rmtree(root)
    arm_a = materialize_home(snapshot, root / "arm-a")
    arm_b = materialize_home(snapshot, root / "arm-b")
    return {
        "root": str(root),
        "arm_a": arm_a,
        "arm_b": arm_b,
        "identical_initial_hash": arm_a["tree_hash"] == arm_b["tree_hash"],
        "snapshot_hash": snapshot["hash"],
        "contract": CONTRACT,
    }


def write_memory(home: Path, text: str) -> None:
    path = home / "memories" / "MEMORY.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def memory_hash(home: Path) -> str:
    return hash_tree(home / "memories")["tree_hash"]


def destroy_homes(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)


def production_memory_paths() -> list[Path]:
    return [
        Path("/home/ubuntu/.hermes/memories"),
        Path("/home/ubuntu/.hermes/profiles/rp-friend/memories"),
    ]


def production_memory_fingerprint() -> dict[str, str]:
    result: dict[str, str] = {}
    for path in production_memory_paths():
        if path.exists():
            result[str(path)] = hash_tree(path)["tree_hash"]
        else:
            result[str(path)] = "ABSENT"
    return result
