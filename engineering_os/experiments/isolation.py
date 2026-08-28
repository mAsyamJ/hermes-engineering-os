"""Workspace / memory contamination detectors."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engineering_os.experiments.config_snapshot import hash_tree


def shared_paths(control: Path, candidate: Path) -> list[str]:
    if control.resolve() == candidate.resolve():
        return [str(control.resolve())]
    return []


def workspace_ok(control: Path, candidate: Path) -> dict[str, Any]:
    shared = shared_paths(control, candidate)
    return {
        "ok": not shared,
        "shared": shared,
        "control_hash": hash_tree(control)["tree_hash"] if control.exists() else None,
        "candidate_hash": hash_tree(candidate)["tree_hash"] if candidate.exists() else None,
    }


def memory_ok(control_ns: str | None, candidate_ns: str | None, *, fixture: bool) -> dict[str, Any]:
    if fixture:
        return {"ok": True, "mode": "fixture_executor", "state": "PASS"}
    if not control_ns or not candidate_ns:
        return {"ok": False, "mode": "unknown", "state": "BLOCKED_CAPABILITY"}
    if control_ns == candidate_ns:
        return {"ok": False, "mode": "shared_namespace", "state": "FAIL"}
    return {"ok": True, "mode": "isolated_namespace", "state": "PASS"}
