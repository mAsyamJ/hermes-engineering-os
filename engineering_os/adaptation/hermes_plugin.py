"""Hermes plugin: OS-timeout IPC client only. No policy authority."""

from __future__ import annotations

import os

from engineering_os.adaptation.ipc_client import request_spawn_resolution, strip_caller_authority


def register(ctx) -> None:
    sock = os.environ.get("HERMES_EOS_ACTUATOR_SOCK", "/run/hermes-eos/actuator.sock")

    def transform_kanban_worker_spawn(**kwargs):
        snapshot = strip_caller_authority(dict(kwargs.get("task_snapshot") or kwargs))
        baseline = {
            "model": snapshot.get("model_override"),
            "provider": snapshot.get("provider_override"),
            "skills": snapshot.get("skills") or [],
        }
        result = request_spawn_resolution(snapshot, baseline, socket_path=sock, timeout_s=0.05)
        if result.get("resolution") == "CANDIDATE" and result.get("overrides"):
            return result["overrides"]
        return None

    ctx.register_hook("transform_kanban_worker_spawn", transform_kanban_worker_spawn)
