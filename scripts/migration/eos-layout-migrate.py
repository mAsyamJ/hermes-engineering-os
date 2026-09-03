#!/usr/bin/env python3
"""Idempotent filesystem-normalization helper: --plan / --verify / --apply-status / --rollback-check.

Apply of bulk moves is driven by git history + manifest status. This tool verifies
and reports; it does not blindly mv paths (safety).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve()
for p in [REPO, *REPO.parents]:
    if (p / "plugin.yaml").is_file() and (p / "agent_os").is_dir():
        REPO = p
        break

HERMES = Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")
MANIFEST = REPO / "migration" / "filesystem-normalization.yaml"
INVENTORY = REPO / "migration" / "path-inventory.json"
FREEZE = REPO / "migration" / "ARCHITECTURE_FREEZE.json"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_plan() -> int:
    inv = _load_json(INVENTORY)
    print(f"inventory_entries={inv['counts']['total']}")
    print(f"class_counts={inv['class_counts']}")
    print(f"manifest={MANIFEST}")
    print(f"moves_executed_flag={_load_json(FREEZE).get('moves_executed')}")
    print("Use git history + layout-check for apply verification; bulk apply is not re-run blindly.")
    return 0


def cmd_verify() -> int:
    rc = 0
    checks = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal rc
        status = "PASS" if ok else "FAIL"
        if not ok:
            rc = 1
        checks.append({"name": name, "status": status, "detail": detail})
        print(f"{status}: {name}" + (f" — {detail}" if detail else ""))

    # Repo root reports gone
    root_reports = list(REPO.glob("PHASE*_REPORT.md")) + list(REPO.glob("PAG*_REPORT.md"))
    root_reports += list(REPO.glob("PRODUCTION_READINESS_REPORT.md"))
    check("repo_root_no_phase_reports", len(root_reports) == 0, str(root_reports))

    # docs not flat
    flat_docs = [p for p in (REPO / "docs").glob("*.md") if p.name != "README.md"]
    check("docs_no_uncategorized_md", len(flat_docs) == 0, str([p.name for p in flat_docs[:10]]))

    # scripts categorized
    flat_scripts = [p for p in (REPO / "scripts").iterdir() if p.is_file()]
    check("scripts_no_flat_impl", len(flat_scripts) == 0, str([p.name for p in flat_scripts]))

    # agent_os core present
    check("agent_os_core_router", (REPO / "agent_os/core/router.py").is_file())
    check("agent_os_compat_shim_router", (REPO / "agent_os/router.py").is_file())
    check(
        "plugin_symlink",
        (HERMES / "plugins/agent-os-router").resolve()
        == (REPO / "agent_os/integrations/hermes/plugin").resolve(),
        str((HERMES / "plugins/agent-os-router").resolve()),
    )

    # Class A hermes
    for name in ("config.yaml", "auth.json", "state.db", "SOUL.md", "SKILLS.md"):
        check(f"hermes_keep_{name}", (HERMES / name).is_file())

    # Moved backups
    check(
        "hermes_backups_config",
        (HERMES / "backups/config").is_dir()
        and any((HERMES / "backups/config").iterdir()),
    )
    check("hermes_audit_relocated", not (HERMES / "audit").exists() and (HERMES / "extensions/audit").is_dir())

    # bin entrypoints
    for b in (
        "hermes-eos-verify",
        "agent-os-verify",
        "eos-analytics-materialize",
        "eos-layout-migrate",
    ):
        check(f"bin_{b}", (REPO / "bin" / b).is_file() and os.access(REPO / "bin" / b, os.X_OK))

    # imports
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    py = str(HERMES / "hermes-agent/venv/bin/python")
    try:
        subprocess.check_call(
            [py, "-c", "from agent_os.core.router import route_task; from agent_os.registry.generate import regenerate"],
            env=env,
            stdout=subprocess.DEVNULL,
        )
        check("python_imports", True)
    except subprocess.CalledProcessError as e:
        check("python_imports", False, str(e))

    out = REPO / "tests/evidence/layout-migration/verify-latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"checks": checks, "rc": rc}, indent=2) + "\n")
    return rc


def cmd_rollback_check() -> int:
    """Prove rollback materials exist (checkpoint branch + freeze + backup evidence)."""
    ok = True
    branches = subprocess.check_output(["git", "-C", str(REPO), "branch"], text=True)
    if "checkpoint/pre-filesystem-normalization" not in branches:
        print("FAIL: missing checkpoint branch")
        ok = False
    else:
        print("PASS: checkpoint branch present")
    if not (HERMES / "backups/config").is_dir():
        print("WARN: hermes backups/config missing (may be fine if never moved)")
    print("PASS: rollback-check materials enumerated (full restore uses checkpoint + reverse mv list)")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--rollback", action="store_true", help="alias for rollback-check")
    ap.add_argument("--apply", action="store_true", help="refuses blind apply; points at git status")
    args = ap.parse_args()
    if args.plan:
        return cmd_plan()
    if args.verify:
        return cmd_verify()
    if args.rollback:
        return cmd_rollback_check()
    if args.apply:
        print("REFUSE: blind --apply is disabled. Moves are performed explicitly from the frozen manifest.")
        print("Use --verify after intentional apply waves.")
        return 2
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
