"""Isolated real-model unit runner. Never mutates RetroPick or production memory."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from engineering_os.experiments.benchmarks import materialize_real_case
from engineering_os.experiments.budget_limits import per_unit_wall_seconds, planned_turns
from engineering_os.experiments.exposure_identity import identity_graph
from engineering_os.experiments.isolation import memory_ok, workspace_ok
from engineering_os.experiments.memory_snapshot import (
    create_isolated_arms,
    freeze_snapshot,
    production_memory_fingerprint,
)


def _production_codex_auth() -> Path:
    return Path.home() / ".hermes" / "auth.json"


def _profile_hermes_home(work: Path, isolated_home: Path, unit_id: str) -> Path:
    """Point HERMES_HOME at a profile path so Codex can read existing OAuth.

    Isolated memory trees must not contain auth.json. Hermes only falls back
    to the global store when HERMES_HOME is ``<root>/profiles/<name>``.
    """
    root = work / "hermes-root"
    profiles = root / "profiles"
    profiles.mkdir(parents=True, exist_ok=True)
    prod = _production_codex_auth()
    link = root / "auth.json"
    if prod.is_file():
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(prod.resolve())
    profile = profiles / str(unit_id or "unit").replace(":", "_")
    if profile.exists() or profile.is_symlink():
        if profile.is_dir() and not profile.is_symlink():
            shutil.rmtree(profile)
        else:
            profile.unlink()
    profile.symlink_to(isolated_home.resolve())
    return profile


def _write_isolated_config(home: Path, turns: int) -> None:
    """Parent-loop cap plus disable delegation so subagent budgets cannot leak."""
    if turns <= 0:
        return
    (home / "config.yaml").write_text(
        "agent:\n"
        f"  max_turns: {turns}\n"
        "  disabled_toolsets:\n"
        "    - delegation\n",
        encoding="utf-8",
    )


def run_isolated_real_unit(
    assignment: dict[str, Any],
    protocol: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:
    work = Path(os.environ.get("EOS_EXPERIMENT_RUNTIME") or "/tmp/eos-experiments")
    unit_dir = work / "real-units" / str(assignment.get("unit_id") or "unit").replace(":", "_")
    if unit_dir.exists():
        shutil.rmtree(unit_dir)
    case_id = str(assignment.get("case_id") or assignment.get("stratum") or "")
    materialized = materialize_real_case({"case_id": case_id, "tree": "broken"}, unit_dir / "workspace")
    snapshot = freeze_snapshot(memory_text="", user_text="", config={"model": assignment.get("assigned_model")})
    arms = create_isolated_arms(snapshot, prefix=f"real-{assignment.get('unit_id')}")
    role = assignment.get("variant_role") or "CONTROL"
    model = (protocol["control"] if role == "CONTROL" else protocol["candidate"])["model"]
    turns = planned_turns(protocol)
    isolated_home = Path(arms["arm_a"]["path"])
    _write_isolated_config(isolated_home, turns)
    if not _production_codex_auth().is_file():
        return {
            "executed": False,
            "llm_calls": 0,
            "status": "BLOCKED_PROVIDER_AUTH",
            "reason": "Codex OAuth store missing; isolated homes do not receive auth.json",
            "unit_id": assignment.get("unit_id"),
            "pair_id": assignment.get("pair_id"),
            "variant_role": role,
            "case_id": case_id,
            "memory_root": arms["root"],
        }
    hermes_home = _profile_hermes_home(work, isolated_home, str(assignment.get("unit_id") or "unit"))
    argv = [
        "/home/ubuntu/.local/bin/hermes",
        "--cli",
        "-m",
        str(model),
        "--provider",
        "openai-codex",
        "chat",
        "-q",
        f"Fix the repository at {materialized['path']} so tests pass. Do not use production paths.",
        "-Q",
    ]
    if turns > 0:
        argv.extend(["--max-turns", str(turns)])
    env = dict(os.environ)
    env["HERMES_HOME"] = str(hermes_home)
    env.pop("HERMES_CONTROL_PRODUCTION_APPROVAL_KEY", None)
    if turns > 0:
        env["HERMES_MAX_ITERATIONS"] = str(turns)
    timeout = per_unit_wall_seconds(protocol)
    remaining = int(gate.get("remaining_wall_seconds") or 0)
    if remaining > 0:
        timeout = min(timeout, remaining)
    production_before = production_memory_fingerprint()
    timed_out = False
    try:
        proc = subprocess.run(
            argv,
            cwd=materialized["path"],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        returncode = proc.returncode
        stdout_tail = (proc.stdout or "")[-2000:]
        stderr_tail = (proc.stderr or "")[-2000:]
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = -9
        stdout_tail = ((exc.stdout or b"") if isinstance(exc.stdout, (bytes, bytearray)) else (exc.stdout or ""))[-2000:]
        stderr_tail = ((exc.stderr or b"") if isinstance(exc.stderr, (bytes, bytearray)) else (exc.stderr or ""))[-2000:]
        if isinstance(stdout_tail, bytes):
            stdout_tail = stdout_tail.decode("utf-8", errors="replace")
        if isinstance(stderr_tail, bytes):
            stderr_tail = stderr_tail.decode("utf-8", errors="replace")
    observed = str(model)
    graph = identity_graph(
        {
            "experiment_id": protocol.get("experiment_id"),
            "assignment_id": assignment.get("assignment_id") or assignment.get("unit_id"),
            "spawn_config_hash": assignment.get("spawn_config_hash") or "isolated",
            "worker_argv": argv,
            "session_id": assignment.get("session_id") or "isolated",
            "trace_id": assignment.get("trace_id") or "isolated",
            "assigned_model": model,
            "observed_model": observed,
        }
    )
    status = "TIMEOUT" if timed_out else ("COMPLETE" if returncode == 0 else "FAILED")
    os.environ.setdefault("EOS_EVAL_SANDBOX", "inline")
    from engineering_os.evaluation.engine import evaluate_trees
    from engineering_os.evaluation.profiles import load_profile

    workspace = Path(materialized["path"])
    payload = evaluate_trees(
        workspace,
        load_profile("real-v1"),
        baseline=workspace,
        eligibility="TEST_ELIGIBLE",
    )
    vector = payload.get("quality_vector") or {}
    production_after = production_memory_fingerprint()
    other_home = Path(arms["arm_b"]["path"])
    memory = memory_ok(str(isolated_home), str(other_home), fixture=False)
    memory["production_unchanged"] = production_before == production_after
    memory["production_before"] = production_before
    memory["production_after"] = production_after
    if not memory["production_unchanged"]:
        memory["ok"] = False
        memory["state"] = "FAIL"
        memory["reason"] = "production memory fingerprint changed"
    isolation = workspace_ok(workspace, other_home)
    isolation["workspace_not_production"] = _workspace_not_production(workspace)
    isolation["home_not_production"] = _workspace_not_production(isolated_home)
    if not isolation["workspace_not_production"] or not isolation["home_not_production"]:
        isolation["ok"] = False
    return {
        "executed": True,
        "llm_calls": 1,
        "status": status,
        "returncode": returncode,
        "timed_out": timed_out,
        "timeout_seconds": timeout,
        "workspace": materialized["path"],
        "memory_root": arms["root"],
        "identity": graph,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "argv": argv,
        "unit_id": assignment.get("unit_id"),
        "pair_id": assignment.get("pair_id"),
        "variant_role": role,
        "case_id": case_id,
        "quality_vector": vector,
        "primary_value": vector.get("tests"),
        "build_value": vector.get("build"),
        "security_value": vector.get("security"),
        "evaluation_status": payload.get("execution_status"),
        "memory_isolation": memory,
        "workspace_isolation": isolation,
        "identical_initial_hash": arms.get("identical_initial_hash"),
    }


def _workspace_not_production(path: Path) -> bool:
    resolved = path.resolve()
    forbidden = (
        Path("/opt/retropick"),
        Path("/opt/retropick-android"),
        Path("/home/ubuntu/.hermes"),
        Path("/var/lib/hermes-runtime"),
        Path("/usr/lib/hermes-runtime"),
    )
    for root in forbidden:
        try:
            resolved.relative_to(root.resolve())
            return False
        except ValueError:
            continue
    return True
