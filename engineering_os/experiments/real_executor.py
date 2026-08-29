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
from engineering_os.experiments.memory_snapshot import create_isolated_arms, freeze_snapshot


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
    env["HERMES_HOME"] = str(isolated_home)
    env.pop("HERMES_CONTROL_PRODUCTION_APPROVAL_KEY", None)
    if turns > 0:
        env["HERMES_MAX_ITERATIONS"] = str(turns)
    timeout = per_unit_wall_seconds(protocol)
    remaining = int(gate.get("remaining_wall_seconds") or 0)
    if remaining > 0:
        timeout = min(timeout, remaining)
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
    }
