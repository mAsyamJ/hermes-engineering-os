"""Isolated real-model unit runner. Never mutates RetroPick or production memory."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from engineering_os.experiments.benchmarks import materialize_real_case
from engineering_os.experiments.exposure_identity import identity_graph
from engineering_os.experiments.memory_snapshot import create_isolated_arms, freeze_snapshot


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
    env = dict(os.environ)
    env["HERMES_HOME"] = str(Path(arms["arm_a"]["path"]))
    env.pop("HERMES_CONTROL_PRODUCTION_APPROVAL_KEY", None)
    proc = subprocess.run(
        argv,
        cwd=materialized["path"],
        env=env,
        capture_output=True,
        text=True,
        timeout=int(protocol.get("budget", {}).get("max_wall_seconds") or 7200),
        check=False,
    )
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
    return {
        "executed": True,
        "llm_calls": 1,
        "status": "COMPLETE" if proc.returncode == 0 else "FAILED",
        "returncode": proc.returncode,
        "workspace": materialized["path"],
        "memory_root": arms["root"],
        "identity": graph,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }
