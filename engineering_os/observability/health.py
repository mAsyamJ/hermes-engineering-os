"""Observability component health without exposing credentials."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from typing import Any

from . import phoenix_client

OTEL_PLUGIN = Path.home() / ".hermes/plugins/hermes_otel"


def _docker_state(name: str) -> str:
    try:
        process = subprocess.run(
            [
                "sudo",
                "-n",
                "docker",
                "inspect",
                "-f",
                "{{.State.Status}}",
                name,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=4,
        )
    except (OSError, subprocess.SubprocessError):
        return "DOWN"
    if process.returncode != 0:
        return "DOWN"
    status = process.stdout.strip()
    if status == "running":
        return "HEALTHY"
    return "DOWN"


def snapshot() -> dict[str, Any]:
    try:
        sdk = importlib.util.find_spec("opentelemetry.sdk") is not None
    except (ModuleNotFoundError, ValueError, ImportError):
        sdk = False
    phoenix_up = phoenix_client.ui_reachable()
    postgres = _docker_state("hermes-eos-postgres")
    phoenix_container = _docker_state("hermes-eos-phoenix")
    if phoenix_up:
        phoenix_status = "HEALTHY"
    elif phoenix_container == "HEALTHY":
        phoenix_status = "DEGRADED"
    else:
        phoenix_status = "DOWN"
    otel_status = "ACTIVE" if sdk else "DEGRADED"
    overall = "AVAILABLE"
    if not sdk or phoenix_status != "HEALTHY" or postgres != "HEALTHY":
        overall = "DEGRADED"
    traces: list[dict[str, Any]] = []
    last = None
    detail = None
    if phoenix_up:
        try:
            traces = phoenix_client.summarize_traces(limit=15)
            last = traces[0] if traces else None
        except Exception as exc:
            overall = "DEGRADED"
            detail = f"{type(exc).__name__}: {exc}"
            phoenix_status = "DEGRADED"
    else:
        detail = "Phoenix UI unreachable"
    return {
        "status": overall,
        "fail_open": True,
        "source": "existing:hermes_otel",
        "hermes_otel": {
            "installed": OTEL_PLUGIN.is_dir(),
            "version": "1.0",
            "status": otel_status,
            "sdk_available": sdk,
        },
        "phoenix": phoenix_status,
        "postgresql": postgres,
        "export": "OTLP/HTTP http://127.0.0.1:6006/v1/traces",
        "last_trace": last,
        "recent_traces": traces,
        "phoenix_url": phoenix_client.PHOENIX_BASE,
        "detail": detail,
    }
