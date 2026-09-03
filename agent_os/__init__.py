"""Hermes Agent OS — capability control plane (index + router, not a second orchestrator)."""

from __future__ import annotations

from pathlib import Path

AGENT_OS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = AGENT_OS_ROOT.parent
REGISTRY_DIR = AGENT_OS_ROOT / "registry"
POLICIES_DIR = AGENT_OS_ROOT / "policies"
BUNDLES_DIR = AGENT_OS_ROOT / "bundles"
LEARNED_MIRROR = AGENT_OS_ROOT / "knowledge" / "skills" / "learned"

DEFAULT_HERMES_HOME = Path.home() / ".hermes"
CONTEXT_BUDGET_CHARS = 2000

__all__ = [
    "AGENT_OS_ROOT",
    "REPO_ROOT",
    "REGISTRY_DIR",
    "POLICIES_DIR",
    "BUNDLES_DIR",
    "LEARNED_MIRROR",
    "DEFAULT_HERMES_HOME",
    "CONTEXT_BUDGET_CHARS",
]
