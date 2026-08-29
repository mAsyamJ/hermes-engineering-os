"""Correlate assigned treatment to observed spawn / session / trace identity."""

from __future__ import annotations

from typing import Any

from engineering_os.experiments.config_snapshot import sha256_text


def identity_graph(parts: dict[str, Any]) -> dict[str, Any]:
    required = (
        "experiment_id",
        "assignment_id",
        "spawn_config_hash",
        "worker_argv",
        "session_id",
        "trace_id",
        "assigned_model",
        "observed_model",
    )
    missing = [key for key in required if not parts.get(key)]
    matched = str(parts.get("assigned_model") or "") == str(parts.get("observed_model") or "")
    return {
        "ok": not missing and matched,
        "missing": missing,
        "fidelity": "MATCHED" if matched and not missing else ("UNKNOWN" if missing else "NONCOMPLIANT"),
        "timestamp_only": False,
        "graph_hash": sha256_text("|".join(str(parts.get(key) or "") for key in required)),
        "parts": {key: parts.get(key) for key in required},
    }
