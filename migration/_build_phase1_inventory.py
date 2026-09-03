#!/usr/bin/env python3
"""Phase 1 inventory + dependency graph builder. Read-only; writes migration/*.json."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path("/opt/hermes-engineering-os")
HERMES = Path("/home/ubuntu/.hermes")
OUT = REPO / "migration"

# --- Hermes home classification (from hermes_constants + authority map + live inspection) ---

HERMES_CLASS_A = {
    "SOUL.md",
    "SKILLS.md",
    "config.yaml",
    ".env",
    "auth.json",
    "auth.lock",
    "state.db",
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
    "gateway.lock",
    "gateway_state.json",
    "kanban",
    "kanban.db",
    "kanban.db.dispatch.lock",
    "kanban.db.init.lock",
    "projects.db",
    "channel_directory.json",
    "cache",
    "audio_cache",
    "image_cache",
    "pairing",
    "platforms",
    "sandboxes",
    "lsp",
    "node",
    "pending",
    "pending_messages",
    "logs",
    "state",
    "bin",
    "context_length_cache.yaml",
    "models_dev_cache.json",
    "ollama_cloud_models_cache.json",
    "provider_models_cache.json",
    "tui-theme-boot.json",
    "web-ui-build-stamp.json",
    "config.yaml.cbm-yaml.lock",
    ".clean_shutdown",
    ".mcp-discovery.lock",
    ".scratch_tip_shown",
    ".update_check",
    ".codex_gpt55_autoraise_notice",
}

# Durable OTel path is default at root but overridable via HERMES_OTEL_CONFIG
HERMES_CLASS_A_CONFIGURABLE = {
    "hermes_otel.yaml",  # DURABLE_CONFIG_PATH; KEEP_ROOT unless env set everywhere
    "verification_evidence.db",  # used by verify tooling; treat as fixed until proven otherwise
}

HERMES_ENGINEERING_OS_CANDIDATES = {
    "audit",
    "scripts",  # operator retropick scripts — OUR extension at home
    "dashboard.log",  # may be Hermes-written; verify before move
    "gateway-starts.log",
}

HERMES_BACKUP = {
    "config.yaml.bak.20260811_140009",
    "config.yaml.bak.20260817_101559",
    "config.yaml.bak.20260817_101633",
    "config.yaml.before-codex",
    ".env.before-codex",
}

REPO_ROOT_KEEP = {
    "README.md",
    "AGENTS.md",
    "ARCHITECTURE.md",
    "SECURITY.md",
    "DECISIONS.md",
    "OPERATIONS.md",
    "RUNBOOK.md",
    "TESTING.md",
    "UPGRADE.md",
    "plugin.yaml",
    "pyproject.toml",
    "uv.lock",
    ".env.example",
    ".gitignore",
    "__init__.py",
}

REPO_ROOT_REPORTS = {
    "PHASE1_REPORT.md": "docs/reports/phases/PHASE1_REPORT.md",
    "PHASE2_REPORT.md": "docs/reports/phases/PHASE2_REPORT.md",
    "PHASE3_REPORT.md": "docs/reports/phases/PHASE3_REPORT.md",
    "PHASE4_REPORT.md": "docs/reports/phases/PHASE4_REPORT.md",
    "PHASE5_REPORT.md": "docs/reports/phases/PHASE5_REPORT.md",
    "PHASE6_REPORT.md": "docs/reports/phases/PHASE6_REPORT.md",
    "PHASE7_REPORT.md": "docs/reports/phases/PHASE7_REPORT.md",
    "PAG1_REPORT.md": "docs/reports/pag/PAG1_REPORT.md",
    "PAG2_REPORT.md": "docs/reports/pag/PAG2_REPORT.md",
    "PRODUCTION_READINESS_REPORT.md": "docs/reports/production/PRODUCTION_READINESS_REPORT.md",
}

REPO_ROOT_DIRS_KEEP = {
    "agent_os",
    "engineering_os",
    "analytics",  # may not exist as top-level — skip if absent
    "evaluation",
    "experiments",
    "adaptation",
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
    "scripts",
    "tests",
    "docs",
    "bin",
}

DOC_PREFIX_MAP = [
    ("ADAPTATION_", "docs/adaptation/"),
    ("ANALYTICS_", "docs/analytics/"),
    ("EVALUATION_", "docs/evaluation/"),
    ("EVALUATOR_", "docs/evaluation/"),
    ("EXPERIMENT_", "docs/experiments/"),
    ("PERFORMANCE_", "docs/observability/"),  # perf docs often ops/obs; refined below
    ("OTEL_", "docs/observability/"),
    ("OBSERVABILITY_", "docs/observability/"),
    ("AGENT_OS_", "docs/agent-os/"),
    ("ADR-", "docs/architecture/decisions/"),
    ("HERMES_", "docs/operations/"),
    ("PRODUCTION_", "docs/operations/"),
    ("PHASE", "docs/reports/phases/"),
    ("PAG", "docs/reports/pag/"),
    ("PROFILE_", "docs/agent-os/profiles/"),
    ("SKILL_", "docs/agent-os/skills/"),
    ("CAPABILITY_", "docs/agent-os/"),
    ("HASH_LOCKED_", "docs/operations/deployment/"),
    ("MEMORY_", "docs/operations/"),
    ("SECURITY_", "docs/security/"),
]

# More precise doc destinations for known names
DOC_EXACT = {
    "HERMES_HOME_AUTHORITY_MAP.md": "docs/architecture/filesystem/HERMES_HOME_AUTHORITY_MAP.md",
    "HERMES_HOME_OPERATIONS.md": "docs/operations/HERMES_HOME_OPERATIONS.md",
    "HERMES_AGENT_OS.md": "docs/agent-os/HERMES_AGENT_OS.md",
    "ADR-HERMES-AGENT-OS.md": "docs/architecture/decisions/ADR-HERMES-AGENT-OS.md",
    "CAPABILITY_CONTROL_PLANE.md": "docs/agent-os/CAPABILITY_CONTROL_PLANE.md",
    "PROFILE_TOPOLOGY.md": "docs/agent-os/profiles/PROFILE_TOPOLOGY.md",
    "SKILL_SOURCE_POLICY.md": "docs/agent-os/skills/SKILL_SOURCE_POLICY.md",
    "AGENT_OS_ACCEPTANCE_REPORT.md": "docs/reports/agent-os/AGENT_OS_ACCEPTANCE_REPORT.md",
    "AGENT_OS_MIGRATION_REPORT.md": "docs/reports/agent-os/AGENT_OS_MIGRATION_REPORT.md",
    "AGENT_OS_BASELINE.md": "docs/reports/agent-os/AGENT_OS_BASELINE.md",
    "AGENT_OS_ROLLBACK.md": "docs/agent-os/operations/AGENT_OS_ROLLBACK.md",
}

SCRIPT_CATEGORY = {
    "agent-os-": "scripts/agent-os/",
    "adaptation-": "scripts/adaptation/",
    "adapt.sh": "scripts/adaptation/",
    "analytics-": "scripts/analytics/",
    "evaluation-": "scripts/evaluation/",
    "evaluate.sh": "scripts/evaluation/",
    "experiment-": "scripts/experiments/",
    "experiment.sh": "scripts/experiments/",
    "performance-": "scripts/observability/",
    "otel-": "scripts/observability/",
    "observability-": "scripts/observability/",
    "start-observability": "scripts/observability/",
    "stop-observability": "scripts/observability/",
    "restart-observability": "scripts/observability/",
    "verify-": "scripts/verification/",
    "verify.sh": "scripts/verification/",
    "pag2-": "scripts/deployment/",
    "h1-": "scripts/deployment/",
    "h2-": "scripts/deployment/",
    "h3-": "scripts/deployment/",
    "hermes-eos-deploy": "scripts/deployment/",
    "capture-": "scripts/maintenance/",
    "control-db-": "scripts/database/",
    "clone-upstreams": "scripts/maintenance/",
    "check-vendor": "scripts/maintenance/",
    "create-fixture": "scripts/maintenance/",
    "snapshot-boundaries": "scripts/verification/",
    "preflight-plugins": "scripts/verification/",
    "install-plugin": "scripts/deployment/",
    "uninstall-plugin": "scripts/deployment/",
    "install-agent-os": "scripts/agent-os/",
    "rollback-agent-os": "scripts/agent-os/",
    "dashboard-request": "scripts/maintenance/",
    "rescan-dashboard": "scripts/maintenance/",
}

AGENT_OS_MOVES = {
    "agent_os/classify.py": "agent_os/core/classifier.py",
    "agent_os/router.py": "agent_os/core/router.py",
    "agent_os/resolver.py": "agent_os/core/resolver.py",
    "agent_os/schema.py": "agent_os/registry/schema.py",
    "agent_os/inventory.py": "agent_os/registry/inventory.py",
    "agent_os/generate.py": "agent_os/registry/generate.py",
    "agent_os/ingest_github.py": "agent_os/registry/ingest/github.py",
    "agent_os/lifecycle.py": "agent_os/lifecycle/sync.py",
    "agent_os/plugin/": "agent_os/integrations/hermes/plugin/",
}

SYSTEMD_SCRIPTS = {
    "scripts/analytics/analytics-materialize.sh": "bin/eos-analytics-materialize",
    "scripts/evaluation/evaluate.sh": "bin/eos-evaluate",
    "scripts/experiments/experiment-materialize.sh": "bin/eos-experiments-materialize",
    "scripts/observability/performance-materialize.sh": "bin/eos-performance-materialize",
    "scripts/adaptation/adaptation-materialize.sh": "bin/eos-adaptation-materialize",
    "scripts/verification/verify.sh": "bin/hermes-eos-verify",
    "scripts/agent-os/agent-os-verify.sh": "bin/agent-os-verify",
}


def run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return ""


def file_type(p: Path) -> str:
    if p.is_symlink():
        return "symlink"
    if p.is_dir():
        return "directory"
    if p.suffix in {".db", ".sqlite"}:
        return "sqlite"
    if p.suffix in {".yaml", ".yml"}:
        return "yaml"
    if p.suffix == ".json":
        return "json"
    if p.suffix == ".md":
        return "markdown"
    if p.suffix == ".py":
        return "python"
    if p.suffix in {".sh", ".bash"}:
        return "shell"
    if p.suffix == ".log":
        return "log"
    if p.suffix == ".lock" or p.name.endswith(".lock"):
        return "lock"
    return "file"


def rg_files(pattern: str, roots: list[Path], glob: str | None = None) -> list[str]:
    cmd = ["rg", "-l", "--hidden", "-g", "!.git/**", "-g", "!.venv/**", "-g", "!**/venv/**",
           "-g", "!.runtime/**", "-g", "!**/node_modules/**", "-g", "!**/__pycache__/**",
           "-g", "!**/.pytest_cache/**", "-g", "!**/vendor/**", "-g", "!**/upstream/**",
           "-g", "!tests/evidence/**", "-g", "!evidence/**"]
    if glob:
        cmd.extend(["-g", glob])
    cmd.append(pattern)
    cmd.extend(str(r) for r in roots)
    out = run(cmd)
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def rg_count_refs(path_str: str) -> dict[str, list[str]]:
    """Find references to a path string across repo + systemd + hermes config-ish places."""
    needles = {path_str}
    # also basename for scripts
    name = Path(path_str).name
    if name and name != path_str:
        needles.add(name)
    hits: dict[str, list[str]] = {
        "hardcoded_references": [],
        "systemd_references": [],
        "documentation_references": [],
        "shell_references": [],
        "config_references": [],
        "plugin_references": [],
        "cron_references": [],
        "hook_references": [],
        "python_imports": [],
    }
    search_roots = [REPO, Path("/home/ubuntu/.config/systemd/user")]
    for needle in needles:
        if len(needle) < 4:
            continue
        files = rg_files(re.escape(needle), search_roots)
        for f in files:
            if f.endswith(".md"):
                hits["documentation_references"].append(f)
            elif f.endswith(".service") or f.endswith(".timer") or "/systemd/" in f:
                hits["systemd_references"].append(f)
            elif f.endswith(".sh") or f.endswith(".bash"):
                hits["shell_references"].append(f)
            elif f.endswith((".yaml", ".yml", ".toml", ".json", ".env.example")):
                hits["config_references"].append(f)
            elif "/plugins/" in f or f.endswith("plugin.yaml"):
                hits["plugin_references"].append(f)
            elif f.endswith(".py"):
                hits["hardcoded_references"].append(f)
            else:
                hits["hardcoded_references"].append(f)
    # dedupe
    for k in hits:
        hits[k] = sorted(set(hits[k]))[:50]
    return hits


def collect_python_imports() -> dict[str, list[str]]:
    """Map module file -> imported agent_os.* modules."""
    result: dict[str, list[str]] = {}
    for py in REPO.rglob("*.py"):
        if any(x in py.parts for x in (".venv", "venv", "__pycache__", ".runtime", "upstream", "vendor")):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"), filename=str(py))
        except SyntaxError:
            continue
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("agent_os") or alias.name.startswith("engineering_os"):
                        imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("agent_os") or node.module.startswith("engineering_os"):
                    imports.append(node.module)
        if imports:
            result[str(py)] = sorted(set(imports))
    return result


def script_destination(name: str) -> str | None:
    if name in ("__pycache__",) or name.endswith(".pyc"):
        return None
    for prefix, dest in SCRIPT_CATEGORY.items():
        if name == prefix or name.startswith(prefix):
            return dest + name
    return "scripts/maintenance/" + name


def doc_destination(name: str) -> str | None:
    if name in DOC_EXACT:
        return DOC_EXACT[name]
    # PERFORMANCE_* go to observability or evaluation — use performance folder under ops
    if name.startswith("PERFORMANCE_"):
        return "docs/observability/" + name
    if name.startswith("PHASE") and name.endswith("_ENTRY_CHECK.md"):
        return "docs/reports/phases/" + name
    for prefix, dest in DOC_PREFIX_MAP:
        if name.startswith(prefix):
            return dest + name
    # leftover flat docs -> reference
    return "docs/reference/" + name


def record(
    path: str,
    *,
    type_: str,
    owner: str,
    purpose: str,
    producer: str,
    readers: list[str],
    writers: list[str],
    migration_class: str,
    proposed_destination: str | None,
    compatibility_strategy: str,
    rollback_strategy: str,
    category: str,
    database_role: str = "none",
    runtime_mutability: str = "low",
    backup_method: str = "copy",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    refs = rg_count_refs(path) if Path(path).exists() or True else {}
    # Prefer relative path keys for repo paths
    key = path
    entry = {
        "path": key,
        "type": type_,
        "owner": owner,
        "purpose": purpose,
        "producer": producer,
        "readers": readers,
        "writers": writers,
        "hardcoded_references": refs.get("hardcoded_references", []),
        "config_references": refs.get("config_references", []),
        "systemd_references": refs.get("systemd_references", []),
        "cron_references": refs.get("cron_references", []),
        "hook_references": refs.get("hook_references", []),
        "plugin_references": refs.get("plugin_references", []),
        "python_imports": refs.get("python_imports", []),
        "shell_references": refs.get("shell_references", []),
        "documentation_references": refs.get("documentation_references", []),
        "database_role": database_role,
        "runtime_mutability": runtime_mutability,
        "backup_method": backup_method,
        "migration_class": migration_class,
        "proposed_destination": proposed_destination,
        "compatibility_strategy": compatibility_strategy,
        "rollback_strategy": rollback_strategy,
        "category": category,
        "status": "inventoried",
    }
    if extra:
        entry.update(extra)
    return entry


def invent_hermes() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for p in sorted(HERMES.iterdir(), key=lambda x: x.name):
        name = p.name
        # skip WAL/SHM siblings as separate inventory of parent DB — include them
        rel = str(p)
        if name in HERMES_CLASS_A or name.startswith("state.db"):
            mclass = "A"
            dest = None
            compat = "KEEP_FIXED"
            purpose = "Hermes upstream-required or canonical runtime path"
            owner = "hermes"
            cat = "UPSTREAM_FIXED"
            if name == "SKILLS.md":
                owner = "agent_os"
                purpose = "Generated Agent OS capability manifest projected into Hermes-required location"
                cat = "GENERATED"
                producer = "agent_os.generate"
            else:
                producer = "hermes"
            db_role = "primary" if name.endswith(".db") or name == "state.db" else "none"
            if name.endswith((".db-wal", ".db-shm")):
                db_role = "wal_sibling"
                mclass = "A"
                dest = None
                compat = "KEEP_FIXED"
            items.append(
                record(
                    rel,
                    type_=file_type(p),
                    owner=owner,
                    purpose=purpose,
                    producer=producer,
                    readers=["hermes-runtime", "dashboard", "plugins"],
                    writers=["hermes-runtime"] if name != "SKILLS.md" else ["agent_os.generate"],
                    migration_class=mclass,
                    proposed_destination=dest,
                    compatibility_strategy=compat,
                    rollback_strategy="n/a-keep",
                    category=cat,
                    database_role=db_role,
                    runtime_mutability="high" if db_role != "none" or name in {"sessions", "cron", "gateway"} else "medium",
                    backup_method="sqlite .backup" if db_role != "none" else "copy",
                )
            )
            continue

        if name in HERMES_CLASS_A_CONFIGURABLE:
            items.append(
                record(
                    rel,
                    type_=file_type(p),
                    owner="hermes_otel" if "otel" in name else "hermes",
                    purpose="Configurable but currently root-canonical durable path",
                    producer="operator/hermes",
                    readers=["hermes_otel plugin", "engineering_os"] if "otel" in name else ["verify"],
                    writers=["operator"],
                    migration_class="A",
                    proposed_destination=None,
                    compatibility_strategy="KEEP_FIXED",
                    rollback_strategy="n/a-keep",
                    category="UPSTREAM_CONFIGURABLE",
                    database_role="primary" if name.endswith(".db") else "none",
                    runtime_mutability="medium",
                    backup_method="sqlite .backup" if name.endswith(".db") else "copy",
                    extra={
                        "notes": "hermes_otel.yaml overridable via HERMES_OTEL_CONFIG; keep root until all consumers set env",
                    },
                )
            )
            continue

        if name in HERMES_BACKUP or name.startswith("config.yaml.bak"):
            items.append(
                record(
                    rel,
                    type_=file_type(p),
                    owner="hermes",
                    purpose="Historical config/env backup",
                    producer="hermes/operator",
                    readers=["operator"],
                    writers=["hermes config"],
                    migration_class="B",
                    proposed_destination=f"{HERMES}/backups/config/{name}",
                    compatibility_strategy="UPDATE_CONSUMERS_NONE_THEN_MOVE",
                    rollback_strategy="mv back to HERMES_HOME root",
                    category="GENERATED",
                    runtime_mutability="none",
                    backup_method="already-backup",
                )
            )
            continue

        if name in HERMES_ENGINEERING_OS_CANDIDATES:
            if name == "scripts":
                dest = f"{HERMES}/extensions/operator-scripts"
                purpose = "Operator local scripts (retropick); not Hermes core"
                owner = "USER"
                cat = "USER"
            elif name == "audit":
                dest = f"{HERMES}/extensions/audit"
                purpose = "Operator/Engineering audit scraps"
                owner = "ENGINEERING_OS"
                cat = "ENGINEERING_OS"
            elif name.endswith(".log"):
                dest = f"{HERMES}/logs/{name}"
                purpose = "Root-level log; candidate to nest under logs/ after writer proof"
                owner = "hermes"
                cat = "UPSTREAM_CONFIGURABLE"
            else:
                dest = None
                purpose = "candidate"
                owner = "UNKNOWN"
                cat = "UNKNOWN"
            # For logs: Class A keep until writer proven — classify C tentatively as KEEP with investigation
            mclass = "C" if name.endswith(".log") else "B"
            if name.endswith(".log"):
                dest = f"{HERMES}/logs/{name}"
                compat = "INVESTIGATE_WRITER_THEN_CONFIG_OR_KEEP"
                mclass = "C"
            else:
                compat = "UPDATE_CONSUMERS_THEN_MOVE"
            items.append(
                record(
                    rel,
                    type_=file_type(p),
                    owner=owner,
                    purpose=purpose,
                    producer=owner,
                    readers=["operator"],
                    writers=["operator/hermes"],
                    migration_class=mclass,
                    proposed_destination=dest,
                    compatibility_strategy=compat,
                    rollback_strategy="mv back",
                    category=cat,
                )
            )
            continue

        # WAL/SHM already handled if named state.db-*; projects etc.
        if name.endswith((".db-wal", ".db-shm")):
            items.append(
                record(
                    rel,
                    type_="sqlite_sidecar",
                    owner="hermes",
                    purpose="SQLite WAL/SHM sibling — must stay beside DB",
                    producer="sqlite",
                    readers=["hermes"],
                    writers=["sqlite"],
                    migration_class="A",
                    proposed_destination=None,
                    compatibility_strategy="KEEP_FIXED",
                    rollback_strategy="n/a",
                    category="UPSTREAM_FIXED",
                    database_role="wal_sibling",
                    runtime_mutability="high",
                    backup_method="with-parent-db",
                )
            )
            continue

        # Unknown
        items.append(
            record(
                rel,
                type_=file_type(p),
                owner="UNKNOWN",
                purpose="Unclassified top-level entry — KEEP_ROOT until proven",
                producer="unknown",
                readers=[],
                writers=[],
                migration_class="A",
                proposed_destination=None,
                compatibility_strategy="KEEP_FIXED",
                rollback_strategy="n/a",
                category="UNKNOWN",
            )
        )
    return items


def invent_repo_root() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    skip = {".git", ".venv", "__pycache__", ".pytest_cache", ".cache", ".runtime"}
    for p in sorted(REPO.iterdir(), key=lambda x: x.name):
        name = p.name
        if name in skip:
            continue
        rel = str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p)
        if name in REPO_ROOT_REPORTS:
            items.append(
                record(
                    str(p),
                    type_="markdown",
                    owner="ENGINEERING_OS",
                    purpose="Historical phase/PAG/production report — not root contract",
                    producer="engineering_os",
                    readers=["humans", "docs"],
                    writers=["humans"],
                    migration_class="B",
                    proposed_destination=str(REPO / REPO_ROOT_REPORTS[name]),
                    compatibility_strategy="git_mv_update_links",
                    rollback_strategy="git mv reverse",
                    category="ENGINEERING_OS",
                )
            )
            continue
        if name in REPO_ROOT_KEEP:
            items.append(
                record(
                    str(p),
                    type_=file_type(p),
                    owner="ENGINEERING_OS",
                    purpose="Deliberate repository root contract entry",
                    producer="engineering_os",
                    readers=["humans", "tools", "hermes-plugin"],
                    writers=["humans"],
                    migration_class="A",
                    proposed_destination=None,
                    compatibility_strategy="KEEP_FIXED",
                    rollback_strategy="n/a",
                    category="ENGINEERING_OS",
                )
            )
            continue
        if p.is_dir():
            items.append(
                record(
                    str(p),
                    type_="directory",
                    owner="ENGINEERING_OS",
                    purpose=f"Top-level implementation directory `{name}/`",
                    producer="engineering_os",
                    readers=["runtime", "tests", "docs"],
                    writers=["humans", "ci"],
                    migration_class="A",
                    proposed_destination=None,
                    compatibility_strategy="KEEP_FIXED",
                    rollback_strategy="n/a",
                    category="ENGINEERING_OS",
                    extra={"notes": "Internal reorg may occur under this directory (agent_os, scripts, docs)"},
                )
            )
            continue
        items.append(
            record(
                str(p),
                type_=file_type(p),
                owner="ENGINEERING_OS",
                purpose="Root file — review",
                producer="engineering_os",
                readers=[],
                writers=[],
                migration_class="A",
                proposed_destination=None,
                compatibility_strategy="KEEP_FIXED",
                rollback_strategy="n/a",
                category="ENGINEERING_OS",
            )
        )
    return items


def invent_docs() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    docs = REPO / "docs"
    for p in sorted(docs.iterdir()):
        if not p.is_file() or p.suffix != ".md":
            continue
        dest = doc_destination(p.name)
        # architecture/filesystem docs we will create stay / may already be nested later
        items.append(
            record(
                str(p),
                type_="markdown",
                owner="ENGINEERING_OS",
                purpose="Documentation currently in flat docs/",
                producer="engineering_os",
                readers=["humans"],
                writers=["humans"],
                migration_class="B",
                proposed_destination=str(REPO / dest) if dest else None,
                compatibility_strategy="git_mv_update_markdown_links",
                rollback_strategy="git mv reverse + restore links",
                category="ENGINEERING_OS",
            )
        )
    return items


def invent_scripts() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    scripts = REPO / "scripts"
    for p in sorted(scripts.iterdir()):
        if p.name == "__pycache__" or p.is_dir():
            continue
        dest = script_destination(p.name)
        public = None
        rel_script = f"scripts/{p.name}"
        if rel_script in SYSTEMD_SCRIPTS:
            public = SYSTEMD_SCRIPTS[rel_script]
            mclass = "C"  # systemd-bound until bin wrapper + unit update
            compat = "STABLE_WRAPPER_THEN_UPDATE_SYSTEMD"
        elif p.name in ("agent-os-verify.sh", "verify.sh"):
            mclass = "C"
            compat = "STABLE_WRAPPER"
            public = SYSTEMD_SCRIPTS.get(rel_script)
        else:
            mclass = "B"
            compat = "git_mv_update_callers"
        items.append(
            record(
                str(p),
                type_=file_type(p),
                owner="ENGINEERING_OS",
                purpose="Operational/verification script currently flat under scripts/",
                producer="engineering_os",
                readers=["operators", "systemd", "ci"],
                writers=["humans"],
                migration_class=mclass,
                proposed_destination=str(REPO / dest) if dest else None,
                compatibility_strategy=compat,
                rollback_strategy="git mv reverse + restore systemd",
                category="ENGINEERING_OS",
                extra={"public_entrypoint": public},
            )
        )
    return items


def invent_agent_os() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for old, new in AGENT_OS_MOVES.items():
        src = REPO / old.rstrip("/")
        items.append(
            record(
                str(src),
                type_="directory" if old.endswith("/") else "python",
                owner="AGENT_OS",
                purpose="Agent OS module pending package-boundary normalization",
                producer="agent_os",
                readers=["agent_os.plugin", "tests", "scripts"],
                writers=["humans"],
                migration_class="C",
                proposed_destination=str(REPO / new.rstrip("/")),
                compatibility_strategy="git_mv_plus_reexport_shim_at_old_path",
                rollback_strategy="git mv reverse + remove shims",
                category="AGENT_OS",
                extra={"shim_module": old.replace("/", ".").rstrip(".").removesuffix(".py") if old.endswith(".py") else None},
            )
        )
    # leave registry/, policies/, bundles/, knowledge/ as keep
    for keep in ("registry", "policies", "bundles", "knowledge"):
        p = REPO / "agent_os" / keep
        if p.exists():
            items.append(
                record(
                    str(p),
                    type_="directory",
                    owner="AGENT_OS",
                    purpose=f"Existing Agent OS `{keep}/` package boundary — keep",
                    producer="agent_os",
                    readers=["agent_os"],
                    writers=["agent_os", "humans"],
                    migration_class="A",
                    proposed_destination=None,
                    compatibility_strategy="KEEP_FIXED",
                    rollback_strategy="n/a",
                    category="AGENT_OS",
                )
            )
    return items


def build_graph(inventory: list[dict[str, Any]], py_imports: dict[str, list[str]]) -> dict[str, Any]:
    nodes = []
    edges = []
    for e in inventory:
        nodes.append(
            {
                "id": e["path"],
                "migration_class": e["migration_class"],
                "owner": e["owner"],
                "proposed_destination": e.get("proposed_destination"),
            }
        )
        for r in e.get("readers", []):
            edges.append({"from": e["path"], "to": r, "kind": "read_by"})
        for w in e.get("writers", []):
            edges.append({"from": w, "to": e["path"], "kind": "written_by"})
        for ref_key in (
            "systemd_references",
            "shell_references",
            "hardcoded_references",
            "documentation_references",
            "config_references",
            "plugin_references",
        ):
            for ref in e.get(ref_key, []):
                edges.append({"from": ref, "to": e["path"], "kind": ref_key})

    # Python import edges
    for src, mods in py_imports.items():
        for m in mods:
            edges.append({"from": src, "to": m, "kind": "python_import"})

    # Explicit systemd ExecStart edges
    systemd_edges = [
        ("/home/ubuntu/.config/systemd/user/hermes-eos-analytics.service", str(REPO / "scripts/analytics/analytics-materialize.sh")),
        ("/home/ubuntu/.config/systemd/user/hermes-eos-evaluate.service", str(REPO / "scripts/evaluation/evaluate.sh")),
        ("/home/ubuntu/.config/systemd/user/hermes-eos-experiments.service", str(REPO / "scripts/experiments/experiment-materialize.sh")),
        ("/home/ubuntu/.config/systemd/user/hermes-eos-performance.service", str(REPO / "scripts/observability/performance-materialize.sh")),
        ("/home/ubuntu/.config/systemd/user/hermes-dashboard.service", "/home/ubuntu/.local/bin/hermes"),
        (str(REPO / "deploy/adaptation/hermes-eos-adaptation.service"), str(REPO / "scripts/adaptation/adaptation-materialize.sh")),
    ]
    for frm, to in systemd_edges:
        edges.append({"from": frm, "to": to, "kind": "systemd_ExecStart", "evidence": "systemctl unit file"})

    # Plugin symlinks
    for plug in (HERMES / "plugins").iterdir():
        if plug.is_symlink():
            edges.append(
                {
                    "from": str(plug),
                    "to": str(plug.resolve()),
                    "kind": "plugin_symlink",
                    "evidence": "readlink",
                }
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "python_import_map": py_imports,
        "notes": [
            "Edges include systemd ExecStart from live unit files and deploy templates.",
            "Text-search references are capped per path; AST imports are authoritative for Python.",
            "No path in this graph has been moved; status is pre-migration.",
        ],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("Collecting Python imports...")
    py_imports = collect_python_imports()
    print(f"  {len(py_imports)} files with agent_os/engineering_os imports")

    print("Inventoring HERMES_HOME...")
    hermes_items = invent_hermes()
    print(f"  {len(hermes_items)} entries")

    print("Inventoring repo root...")
    root_items = invent_repo_root()
    print(f"  {len(root_items)} entries")

    print("Inventoring docs...")
    doc_items = invent_docs()
    print(f"  {len(doc_items)} entries")

    print("Inventoring scripts...")
    script_items = invent_scripts()
    print(f"  {len(script_items)} entries")

    print("Inventoring agent_os moves...")
    aos_items = invent_agent_os()
    print(f"  {len(aos_items)} entries")

    inventory = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hermes_home": str(HERMES),
        "repository": str(REPO),
        "hermes_version": "0.20.0",
        "phase": "1-inventory",
        "moves_executed": False,
        "counts": {
            "hermes_home": len(hermes_items),
            "repo_root": len(root_items),
            "docs": len(doc_items),
            "scripts": len(script_items),
            "agent_os": len(aos_items),
            "total": len(hermes_items) + len(root_items) + len(doc_items) + len(script_items) + len(aos_items),
        },
        "class_counts": {},
        "entries": hermes_items + root_items + doc_items + script_items + aos_items,
    }
    from collections import Counter

    inventory["class_counts"] = dict(Counter(e["migration_class"] for e in inventory["entries"]))

    inv_path = OUT / "path-inventory.json"
    inv_path.write_text(json.dumps(inventory, indent=2) + "\n")
    print(f"Wrote {inv_path} ({inventory['counts']['total']} entries)")

    print("Building dependency graph...")
    graph = build_graph(inventory["entries"], py_imports)
    graph_path = OUT / "path-dependency-graph.json"
    graph_path.write_text(json.dumps(graph, indent=2) + "\n")
    print(f"Wrote {graph_path} ({graph['node_count']} nodes, {graph['edge_count']} edges)")


if __name__ == "__main__":
    main()
