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
SD_LISTEN_FDS_START = 3


def inherited_listen_socket() -> socket.socket | None:
    """Use systemd socket activation when LISTEN_FDS is present. Never steal fd 3 otherwise."""
    try:
        count = int(os.environ.get("LISTEN_FDS") or 0)
    except ValueError:
        return None
    if count < 1:
        return None
    pid_raw = os.environ.get("LISTEN_PID") or ""
    if pid_raw:
        try:
            if int(pid_raw) not in {0, os.getpid()}:
                return None
        except ValueError:
            return None
    return socket.fromfd(SD_LISTEN_FDS_START, socket.AF_UNIX, socket.SOCK_STREAM)


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
    identity = bind_runtime_identity(state)
    if not identity["ok"]:
        return baseline(str(identity["reason"]), baseline_config)
    cleaned = strip_caller_authority(payload)
    # Re-check nested authority smuggling
    for key in CALLER_AUTHORITY_KEYS:
        cleaned.pop(key, None)
    context = dict(cleaned.get("task_context") or cleaned)
    for key in CALLER_AUTHORITY_KEYS:
        context.pop(key, None)
    if not context.get("task_id") and cleaned.get("task_id"):
        context["task_id"] = cleaned["task_id"]
    if str(context.get("scope") or "") == "PRODUCTION_SHADOW":
        decision = resolve_spawn_configuration(context, baseline_config, state=state)
        out = baseline("SHADOW_NO_ACTUATE", baseline_config)
        out["would_resolution"] = decision.get("resolution")
        out["would_reason"] = decision.get("reason")
        out["reason"] = "SHADOW_NO_ACTUATE"
        out["actuator_contract"] = ACTUATOR_CONTRACT
        return out
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


def live_runtime_identity() -> dict[str, str]:
    return {
        "runtime_release_hash": os.environ.get("HERMES_EOS_RUNTIME_RELEASE_HASH") or "",
        "live_patch_hash": os.environ.get("HERMES_EOS_LIVE_PATCH_HASH") or "",
        "actuator_contract_version": ACTUATOR_CONTRACT,
        "trust_fingerprint": os.environ.get("HERMES_EOS_TRUST_FINGERPRINT") or "",
    }


def bind_runtime_identity(state: dict[str, Any] | None) -> dict[str, Any]:
    """If Approval A bound runtime identity, require an exact match. Unbound tests may omit it."""
    expected = dict((state or {}).get("runtime_identity") or {})
    keys = ("runtime_release_hash", "live_patch_hash", "actuator_contract_version", "trust_fingerprint")
    if not any(str(expected.get(key) or "") for key in keys):
        return {"ok": True, "reason": "unbound"}
    live = live_runtime_identity()
    for key in keys:
        want = str(expected.get(key) or "")
        if want and want != str(live.get(key) or ""):
            return {"ok": False, "reason": f"{key} mismatch"}
    return {"ok": True, "reason": "runtime identity bound"}


def load_protected_state() -> dict[str, Any]:
    path = os.environ.get("HERMES_EOS_ACTUATOR_STATE") or "/var/lib/hermes-actuator/state.json"
    if not os.path.isfile(path):
        return {"bindings": [], "maximum_exposure": 1}
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {"bindings": []}


def resolve_runtime_uid() -> int:
    override = os.environ.get("HERMES_EOS_RUNTIME_UID")
    if override:
        return int(override)
    import pwd

    return int(pwd.getpwnam("hermes-runtime").pw_uid)


def serve_forever(
    socket_path: str,
    *,
    runtime_uid: int,
    state: dict[str, Any] | None = None,
    stop: threading.Event | None = None,
    reserve_path: Any = None,
    listen_socket: socket.socket | None = None,
    reload_state: bool = False,
) -> None:
    systemd_sock = listen_socket if listen_socket is not None else inherited_listen_socket()
    owned = systemd_sock is None
    if systemd_sock is not None:
        server = systemd_sock
    else:
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
                live_state = load_protected_state() if reload_state else state
                result = handle_request(
                    payload if isinstance(payload, dict) else {},
                    peer_uid=peer_uid,
                    runtime_uid=runtime_uid,
                    state=live_state,
                    reserve_path=reserve_path,
                )
                blob = json.dumps(result).encode("utf-8")
                try:
                    conn.sendall(len(blob).to_bytes(4, "big") + blob)
                except OSError:
                    pass
    finally:
        server.close()
        if owned and os.path.exists(socket_path):
            os.unlink(socket_path)


def main() -> int:
    sock = os.environ.get("HERMES_EOS_ACTUATOR_SOCK") or "/run/hermes-eos/actuator.sock"
    reserve = os.environ.get("HERMES_EOS_RESERVE_SQLITE") or "/var/lib/hermes-actuator/reservations.sqlite"
    serve_forever(
        sock,
        runtime_uid=resolve_runtime_uid(),
        state=None,
        reload_state=True,
        reserve_path=reserve,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
