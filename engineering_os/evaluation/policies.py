"""Tier A policy evaluators. No candidate process execution."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Iterable

from engineering_os.evaluation.artifacts import DENIED_DIRS, DENIED_NAMES, scan_tree


def iter_python_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        if any(part in {".git", "__pycache__"} for part in path.parts):
            continue
        yield path


def architecture_policy(tree: Path, profile: dict[str, Any]) -> dict[str, Any]:
    prefixes = list((profile.get("policies") or {}).get("forbidden_import_prefixes") or [])
    if not prefixes:
        return {"verdict": "NOT_APPLICABLE", "detail": "no architecture rules encoded"}
    hits: list[str] = []
    for path in iter_python_files(tree):
        try:
            tree_ast = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            return {"verdict": "UNKNOWN", "detail": f"unreadable {path.name}"}
        for node in ast.walk(tree_ast):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes):
                    hits.append(f"{path.name}:{name}")
    if hits:
        return {"verdict": "FAIL", "detail": ",".join(hits[:20]), "findings": hits}
    return {"verdict": "PASS", "detail": "no forbidden imports"}


def scope_policy(changed_paths: list[str], profile: dict[str, Any]) -> dict[str, Any]:
    forbidden = list((profile.get("policies") or {}).get("forbidden_paths") or [])
    if not forbidden:
        return {"verdict": "NOT_APPLICABLE", "detail": "no scope rules encoded"}
    hits = []
    for path in changed_paths:
        for rule in forbidden:
            if path == rule or path.startswith(rule) or re.search(rule, path):
                hits.append(path)
    if hits:
        return {"verdict": "FAIL", "detail": ",".join(hits[:20]), "findings": hits}
    return {"verdict": "PASS", "detail": "changed paths within policy"}


def security_policy(tree: Path, profile: dict[str, Any]) -> dict[str, Any]:
    extra = list((profile.get("policies") or {}).get("secret_path_globs") or [])
    for path in tree.rglob("*"):
        if not path.is_file():
            continue
        if any(part in DENIED_DIRS for part in path.parts):
            continue
        if path.name in DENIED_NAMES:
            return {"verdict": "FAIL", "detail": f"denied path {path.name}"}
        if extra and any(path.match(glob) for glob in extra):
            return {"verdict": "FAIL", "detail": f"profile-denied path {path.name}"}
    scan = scan_tree(tree)
    if scan == "FAIL":
        return {"verdict": "FAIL", "detail": "secret_or_denied_content"}
    return {"verdict": "PASS", "detail": "no deterministic secret/path hits"}


def acceptance_checks(task: dict[str, Any] | None) -> dict[str, Any]:
    metadata = (task or {}).get("metadata") if isinstance(task, dict) else None
    if not isinstance(metadata, dict):
        return {
            "verdict": "UNKNOWN",
            "detail": "no structured machine-verifiable acceptance criteria",
        }
    checks = metadata.get("acceptance_checks")
    if not isinstance(checks, list) or not checks:
        return {
            "verdict": "UNKNOWN",
            "detail": "acceptance criteria are free-form or absent",
        }
    return {"verdict": "UNKNOWN", "detail": "structured checks present but no mapper in phase4-eval-v1"}
