#!/usr/bin/env python3
"""Layout checker for Engineering OS repo + Hermes custom-artifact root rules."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve()
for p in [REPO, *REPO.parents]:
    if (p / "plugin.yaml").is_file() and (p / "agent_os").is_dir():
        REPO = p
        break

HERMES = Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")

# Generated allowlist for Hermes root: upstream + justified custom leftovers
HERMES_ROOT_ALLOW = {
    # identity / config
    "SOUL.md",
    "SKILLS.md",
    "config.yaml",
    "config.yaml.cbm-yaml.lock",
    ".env",
    "auth.json",
    "auth.lock",
    # state
    "state.db",
    "state.db-wal",
    "state.db-shm",
    "projects.db",
    "projects.db-wal",
    "projects.db-shm",
    "kanban.db",
    "kanban.db-wal",
    "kanban.db-shm",
    "kanban.db.dispatch.lock",
    "kanban.db.init.lock",
    "verification_evidence.db",
    "verification_evidence.db-wal",
    "verification_evidence.db-shm",
    "channel_directory.json",
    "context_length_cache.yaml",
    "models_dev_cache.json",
    "ollama_cloud_models_cache.json",
    "provider_models_cache.json",
    "tui-theme-boot.json",
    "web-ui-build-stamp.json",
    "hermes_otel.yaml",
    "dashboard.log",
    "gateway-starts.log",
    "gateway.lock",
    "gateway_state.json",
    # dirs
    "hermes-agent",
    "skills",
    "skill-bundles",
    "plugins",
    "profiles",
    "sessions",
    "memories",
    "cron",
    "hooks",
    "gateway",
    "kanban",
    "logs",
    "cache",
    "audio_cache",
    "image_cache",
    "state",
    "bin",
    "scripts",
    "pairing",
    "platforms",
    "sandboxes",
    "lsp",
    "node",
    "pending",
    "pending_messages",
    "backups",
    "extensions",
    # markers
    ".clean_shutdown",
    ".mcp-discovery.lock",
    ".scratch_tip_shown",
    ".update_check",
    ".codex_gpt55_autoraise_notice",
}

REPO_ROOT_ALLOW_FILES = {
    "README.md",
    "AGENTS.md",
    "ARCHITECTURE.md",
    "SECURITY.md",
    "DECISIONS.md",
    "OPERATIONS.md",
    "RUNBOOK.md",
    "TESTING.md",
    "UPGRADE.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "plugin.yaml",
    "pyproject.toml",
    "uv.lock",
    ".env.example",
    ".gitignore",
    "__init__.py",
}

REPO_ROOT_ALLOW_DIRS = {
    "agent_os",
    "engineering_os",
    "integrations",
    "dashboard",
    "deploy",
    "migrations",
    "migration",
    "config",
    "vendor",
    "provenance",
    "patches",
    "policies",
    "requirements",
    "upstream",
    "evidence",
    "experiments",
    "scripts",
    "bin",
    "tests",
    "docs",
    ".git",
    ".venv",
    ".cache",
    ".runtime",
    ".pytest_cache",
    "__pycache__",
}

AGENT_OS_ROOT_API = {
    "__init__.py",
    "classify.py",
    "router.py",
    "resolver.py",
    "schema.py",
    "inventory.py",
    "generate.py",
    "ingest_github.py",
    # lifecycle.py removed in favor of package
}


def main() -> int:
    failures: list[str] = []

    # Repo root
    for p in REPO.iterdir():
        name = p.name
        if name.startswith(".") and name not in {".env.example", ".gitignore", ".git", ".venv", ".cache", ".runtime", ".pytest_cache"}:
            # allow other dotfiles quietly? flag unknown non-standard
            if name not in REPO_ROOT_ALLOW_DIRS and name not in REPO_ROOT_ALLOW_FILES:
                continue
        if p.is_file():
            if name not in REPO_ROOT_ALLOW_FILES:
                if re.match(r"PHASE\d+_REPORT\.md$", name) or re.match(r"PAG\d+_REPORT\.md$", name):
                    failures.append(f"repo root report forbidden: {name}")
                elif name.endswith((".log", ".db", ".sqlite")):
                    failures.append(f"repo root artifact forbidden: {name}")
                elif name.endswith(".sh"):
                    failures.append(f"repo root script forbidden: {name}")
                elif name not in REPO_ROOT_ALLOW_FILES:
                    failures.append(f"repo root unexpected file: {name}")
        elif p.is_dir() and name not in REPO_ROOT_ALLOW_DIRS:
            failures.append(f"repo root unexpected dir: {name}")

    # docs
    for p in (REPO / "docs").glob("*.md"):
        if p.name != "README.md":
            failures.append(f"uncategorized docs file: docs/{p.name}")
    for cat in ("adaptation", "analytics", "evaluation", "experiments", "observability", "operations", "architecture", "agent-os", "reports", "reference"):
        d = REPO / "docs" / cat
        if d.is_dir() and not (d / "README.md").is_file():
            failures.append(f"missing category README: docs/{cat}/README.md")

    # scripts
    for p in (REPO / "scripts").iterdir():
        if p.is_file():
            failures.append(f"uncategorized script at scripts root: {p.name}")

    # agent_os package root: only approved API/shim files + known packages
    allowed_dirs = {"core", "registry", "lifecycle", "integrations", "policies", "bundles", "knowledge", "plugin", "__pycache__"}
    for p in (REPO / "agent_os").iterdir():
        if p.is_dir():
            if p.name not in allowed_dirs:
                failures.append(f"unexpected agent_os dir: {p.name}")
        elif p.is_file() and p.suffix == ".py":
            if p.name not in AGENT_OS_ROOT_API and p.name != "__init__.py":
                failures.append(f"unexpected agent_os root py: {p.name}")

    # Hermes custom artifacts: flag bak files / audit at root
    for p in HERMES.iterdir():
        name = p.name
        if name.startswith("config.yaml.bak") or name.endswith(".before-codex"):
            failures.append(f"hermes custom backup still at root: {name}")
        if name == "audit" and p.is_dir():
            failures.append("hermes audit/ still at root (expected extensions/audit)")
        if name not in HERMES_ROOT_ALLOW and not name.startswith("."):
            # unknown non-dot entry
            failures.append(f"hermes root not in allowlist: {name}")

    result = {"ok": not failures, "failures": failures}
    print(json.dumps(result, indent=2))
    out = REPO / "tests/evidence/layout-migration/layout-check-latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
