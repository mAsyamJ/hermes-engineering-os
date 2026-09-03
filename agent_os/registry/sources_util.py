"""Helpers for curated sources."""

from __future__ import annotations

from pathlib import Path

import yaml

from agent_os import REGISTRY_DIR


def load_sources() -> dict:
    path = REGISTRY_DIR / "sources.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def allowlisted_repos() -> set[str]:
    out: set[str] = set()
    for src in load_sources().get("sources") or []:
        if src.get("trust_tier") == "T2" and src.get("repository"):
            out.add(src["repository"])
    return out


def source_tier_for_repo(repository: str) -> str:
    for src in load_sources().get("sources") or []:
        if src.get("repository") == repository:
            return str(src.get("trust_tier") or "T3")
    return "T3"
