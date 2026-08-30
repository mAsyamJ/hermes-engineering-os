"""Bounded Unix-socket client. OS-level timeout. No ThreadPoolExecutor."""

from __future__ import annotations

import json
import os
import socket
from typing import Any

CALLER_AUTHORITY_KEYS = frozenset(
    {
        "eligible",
        "candidate",
        "production",
        "approval_valid",
        "exposure_remaining",
        "actuate",
        "resolution",
        "overrides",
    }
)
DEFAULT_TIMEOUT_S = 0.05
DEFAULT_SOCKET = os.environ.get("HERMES_EOS_ACTUATOR_SOCK", "/run/hermes-eos/actuator.sock")


def strip_caller_authority(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key not in CALLER_AUTHORITY_KEYS}


def baseline(reason: str, baseline_config: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "resolution": "BASELINE",
        "actuate": False,
        "overrides": {},
        "effective": dict(baseline_config or {}),
        "reason": reason,
        "mutated_kanban": False,
        "network": False,
    }


def request_spawn_resolution(
    snapshot: dict[str, Any],
    baseline_config: dict[str, Any],
    *,
    socket_path: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Send immutable task identity only. Fail open to BASELINE. No leftover threads."""
    path = socket_path or DEFAULT_SOCKET
    body = strip_caller_authority(dict(snapshot or {}))
    body["baseline"] = dict(baseline_config or {})
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout_s)
        sock.connect(path)
        sock.sendall(len(raw).to_bytes(4, "big") + raw)
        header = _recv_exact(sock, 4, timeout_s)
        if header is None:
            return baseline("IPC timeout", baseline_config)
        length = int.from_bytes(header, "big")
        if length <= 0 or length > 1_000_000:
            return baseline("malformed response", baseline_config)
        payload = _recv_exact(sock, length, timeout_s)
        if payload is None:
            return baseline("IPC timeout", baseline_config)
        data = json.loads(payload.decode("utf-8"))
        if not isinstance(data, dict):
            return baseline("malformed response", baseline_config)
        if data.get("resolution") != "CANDIDATE" or not data.get("actuate"):
            out = baseline(str(data.get("reason") or "BASELINE"), baseline_config)
            if data.get("would_resolution"):
                out["would_resolution"] = data.get("would_resolution")
            if data.get("would_reason"):
                out["would_reason"] = data.get("would_reason")
            if data.get("reason"):
                out["reason"] = data.get("reason")
            return out
        return data
    except (TimeoutError, socket.timeout, OSError, json.JSONDecodeError, ValueError) as exc:
        return baseline(f"{type(exc).__name__}", baseline_config)
    finally:
        try:
            sock.close()
        except OSError:
            pass


def _recv_exact(sock: socket.socket, n: int, timeout_s: float) -> bytes | None:
    buf = b""
    sock.settimeout(timeout_s)
    while len(buf) < n:
        try:
            chunk = sock.recv(n - len(buf))
        except (TimeoutError, socket.timeout):
            return None
        if not chunk:
            return None
        buf += chunk
    return buf
