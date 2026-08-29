"""Protected adaptation actuator. SO_PEERCRED. Caller authority ignored."""

from __future__ import annotations

import json
import os
import socket
import struct
import threading
from typing import Any

from engineering_os.adaptation.ipc_client import CALLER_AUTHORITY_KEYS, baseline, strip_caller_authority
from engineering_os.adaptation.reserve import reserve_memory, reserve_sqlite
from engineering_os.adaptation.spawn_resolve import resolve_spawn_configuration

SO_PEERCRED = getattr(socket, "SO_PEERCRED", 17)
UCRED_FMT = "3i"
UCRED_SIZE = struct.calcsize(UCRED_FMT)
ACTUATOR_CONTRACT = "pag2-actuator-v1"


def peer_credentials(conn: socket.socket) -> tuple[int, int, int] | None:
    try:
        raw = conn.getsockopt(socket.SOL_SOCKET, SO_PEERCRED, UCRED_SIZE)
        pid, uid, gid = struct.unpack(UCRED_FMT, raw)
        return int(pid), int(uid), int(gid)
    except OSError:
        return None


def handle_request(
    payload: dict[str, Any],
    *,
    peer_uid: int,
    runtime_uid: int,
    state: dict[str, Any] | None = None,
    reserve_path: Any = None,
) -> dict[str, Any]:
    """Resolve from protected state. Ignore caller-supplied authority fields."""
    baseline_config = dict(payload.get("baseline") or {})
    if int(peer_uid) != int(runtime_uid):
        return baseline("PEER_REJECTED", baseline_config)
    cleaned = strip_caller_authority(payload)
    # Re-check nested authority smuggling
    for key in CALLER_AUTHORITY_KEYS:
        cleaned.pop(key, None)
    context = dict(cleaned.get("task_context") or cleaned)
    for key in CALLER_AUTHORITY_KEYS:
        context.pop(key, None)
    if not context.get("task_id") and cleaned.get("task_id"):
        context["task_id"] = cleaned["task_id"]
    decision = resolve_spawn_configuration(context, baseline_config, state=state)
    if decision.get("resolution") != "CANDIDATE" or not decision.get("actuate"):
        return decision
    approval_id = str((state or {}).get("approval_id") or context.get("approval_id") or "none")
    policy_hash = str(decision.get("policy_hash") or "")
    unit_id = str(context.get("task_id") or context.get("unit_id") or "")
    maximum_exposure = int((state or {}).get("maximum_exposure") or 1)
    if reserve_path is not None:
        slot = reserve_sqlite(
            reserve_path,
            policy_hash=policy_hash,
            approval_id=approval_id,
            unit_id=unit_id,
            maximum_exposure=maximum_exposure,
        )
    else:
        slot = reserve_memory(
            policy_hash=policy_hash,
            approval_id=approval_id,
            unit_id=unit_id,
            maximum_exposure=maximum_exposure,
        )
    if not slot.get("reserved"):
        return baseline(str(slot.get("reason") or "EXPOSURE_EXHAUSTED"), baseline_config)
    decision["reservation"] = slot
    decision["actuator_contract"] = ACTUATOR_CONTRACT
    return decision


def serve_forever(
    socket_path: str,
    *,
    runtime_uid: int,
    state: dict[str, Any] | None = None,
    stop: threading.Event | None = None,
) -> None:
    if os.path.exists(socket_path):
        os.unlink(socket_path)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(socket_path)
    os.chmod(socket_path, 0o660)
    server.listen(16)
    server.settimeout(0.2)
    try:
        while stop is None or not stop.is_set():
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue
            with conn:
                cred = peer_credentials(conn)
                peer_uid = cred[1] if cred else -1
                try:
                    header = conn.recv(4)
                    length = int.from_bytes(header, "big") if header else 0
                    raw = b""
                    while length > 0 and len(raw) < length:
                        raw += conn.recv(length - len(raw))
                    payload = json.loads(raw.decode("utf-8")) if raw else {}
                except Exception:
                    payload = {}
                result = handle_request(payload if isinstance(payload, dict) else {}, peer_uid=peer_uid, runtime_uid=runtime_uid, state=state)
                blob = json.dumps(result).encode("utf-8")
                try:
                    conn.sendall(len(blob).to_bytes(4, "big") + blob)
                except OSError:
                    pass
    finally:
        server.close()
        if os.path.exists(socket_path):
            os.unlink(socket_path)
