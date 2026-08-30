"""PAG-2 production shadow / canary / rollback. Fail-closed before H1/H2/H3."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from engineering_os.adaptation.actuator import handle_request
from engineering_os.adaptation.ipc_client import request_spawn_resolution
from engineering_os.adaptation.rollback import apply_auto_disable
from engineering_os.adaptation.shadow import production_task_context, shadow_batch

CANARY_BOARD = "retropick-markets-release"
CANARY_WORKLOAD_ID = "pag2-canary-workload-1"
PROTECTED_KANBAN = Path("/usr/lib/hermes-runtime/hermes-agent/hermes_cli/kanban_db.py")


def readable_file(path: Path) -> bool:
    """True only if this process can stat a regular file. EACCES is not a grant."""
    try:
        return path.is_file()
    except OSError:
        return False


def repo_root() -> Path:
    return Path(os.environ.get("HERMES_EOS_REPO") or "/opt/hermes-engineering-os")


def verify_operator_script() -> Path:
    env = os.environ.get("HERMES_EOS_VERIFY_OPERATOR")
    if env:
        return Path(env)
    protected = Path("/usr/local/lib/hermes-eos/scripts/verify-operator-boundary.sh")
    if protected.is_file():
        return protected
    return repo_root() / "scripts" / "verify-operator-boundary.sh"


def experiment_runtime_dir() -> Path:
    override = os.environ.get("EOS_EXPERIMENT_RUNTIME")
    if override:
        return Path(override)
    return repo_root() / ".runtime" / "experiments"


def load_actuator_env(path: Path | None = None) -> dict[str, str]:
    env_path = path or Path(os.environ.get("HERMES_EOS_ACTUATOR_ENV") or "/etc/hermes-eos/actuator.env")
    env: dict[str, str] = {}
    if not env_path.is_file():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def live_runtime_identity() -> dict[str, str]:
    env = load_actuator_env()
    return {
        "runtime_release_hash": env.get("HERMES_EOS_RUNTIME_RELEASE_HASH") or "c0106e50e7ecedb3ce34e785d949725dc4e0e457",
        "live_patch_hash": env.get("HERMES_EOS_LIVE_PATCH_HASH") or "",
        "actuator_contract_version": "pag2-actuator-v1",
        "trust_fingerprint": env.get("HERMES_EOS_TRUST_FINGERPRINT") or "",
    }


def parse_h1_status(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("status="):
            return line.split("=", 1)[1].strip()
    return "UNKNOWN"


def read_h1_status() -> str:
    proc = subprocess.run(
        [str(verify_operator_script())],
        check=False,
        capture_output=True,
        text=True,
    )
    return parse_h1_status(proc.stdout or "")


def h3_live_seam_present(runtime_py: Path | None = None, plugin_py: Path | None = None) -> bool:
    path = runtime_py or PROTECTED_KANBAN
    plugin = plugin_py or Path("/var/lib/hermes-runtime/home/plugins/eos-actuation/__init__.py")
    if not readable_file(path) or "transform_kanban_worker_spawn" not in path.read_text(encoding="utf-8"):
        return False
    if not readable_file(plugin):
        return False
    return "hermes_plugin" in plugin.read_text(encoding="utf-8")


def flatten_approval_a_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Grant JSON may nest runtime_identity; signatures are over CANONICAL_FIELDS."""
    fields = {key: value for key, value in data.items() if key != "signature"}
    identity = dict(data.get("runtime_identity") or {})
    for key in ("runtime_release_hash", "live_patch_hash", "actuator_contract_version", "trust_fingerprint"):
        if not fields.get(key):
            fields[key] = identity.get(key) or ""
    if not fields.get("approval_stage"):
        fields["approval_stage"] = str(fields.get("stage") or "A")
    return fields


def approval_a_granted(path: Path | None = None) -> bool:
    """Runtime-bound Approval A. Agent-writable files and unsigned JSON are not grants."""
    granted = path or Path(os.environ.get("HERMES_EOS_APPROVAL_A") or "/var/lib/hermes-actuator/approval-a.granted")
    if not readable_file(granted):
        return False
    if os.access(granted, os.W_OK):
        return False
    try:
        data = json.loads(granted.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    if str(data.get("stage") or data.get("approval_stage") or "") != "A":
        return False
    try:
        if int(data.get("maximum_exposure") or 0) != 1:
            return False
    except (TypeError, ValueError):
        return False
    identity = dict(data.get("runtime_identity") or {})
    live = live_runtime_identity()
    release = str(identity.get("runtime_release_hash") or data.get("runtime_release_hash") or "")
    patch = str(identity.get("live_patch_hash") or data.get("live_patch_hash") or "")
    fingerprint = str(identity.get("trust_fingerprint") or data.get("trust_fingerprint") or "")
    contract = str(identity.get("actuator_contract_version") or data.get("actuator_contract_version") or "")
    if not live["live_patch_hash"] or patch != live["live_patch_hash"]:
        return False
    if live["trust_fingerprint"] and fingerprint != live["trust_fingerprint"]:
        return False
    if release != live["runtime_release_hash"]:
        return False
    if contract != "pag2-actuator-v1":
        return False
    signature = str(data.get("signature") or "")
    if not signature:
        return False
    from engineering_os.adaptation.approval_ed25519 import verify_production_authorization

    checked = verify_production_authorization(flatten_approval_a_fields(data), signature, consume=False)
    return bool(checked.get("granted"))


def present_approval_a_request() -> dict[str, Any]:
    """Bytes a human signs off-VPS. Does not grant. Does not write a file.

    Refuses until H3 has bound a non-empty live_patch_hash in actuator.env.
    """
    from engineering_os.adaptation.approval_ed25519 import canonical_bytes, generate_approval_request
    from engineering_os.experiments.definitions import load_id

    live = live_runtime_identity()
    if not live["live_patch_hash"] or not live["trust_fingerprint"]:
        return {
            "ok": False,
            "status": "BLOCKED_H3",
            "reason": "present Approval A after H3 so live_patch_hash and trust_fingerprint are bound",
            "grant": None,
            "canonical_hex": "",
        }
    protocol = load_id("real-model-sol-vs-terra-v2")
    release = live["runtime_release_hash"]
    patch = live["live_patch_hash"]
    fingerprint = live["trust_fingerprint"]
    request = generate_approval_request(
        recommendation_id="pag2-confirmatory-v2",
        policy_id="pag2-canary-sol-vs-terra",
        policy_hash=str(protocol.get("_definition_hash") or ""),
        policy_version="1",
        approval_stage="A",
        scope="PRODUCTION_CANARY",
        maximum_exposure=1,
        candidate_config_hash=str((protocol.get("candidate") or {}).get("model") or "gpt-5.6-terra"),
        fallback_hash=str((protocol.get("control") or {}).get("model") or "gpt-5.6-sol"),
        rollback_hash=release,
        expiry="2027-01-01T00:00:00+00:00",
        runtime_release_hash=release,
        live_patch_hash=patch,
        actuator_contract_version="pag2-actuator-v1",
        trust_fingerprint=fingerprint,
    )
    grant = dict(request)
    grant["stage"] = "A"
    grant["auto_promote"] = False
    grant["runtime_identity"] = {
        "runtime_release_hash": release,
        "live_patch_hash": patch,
        "actuator_contract_version": "pag2-actuator-v1",
        "trust_fingerprint": fingerprint,
    }
    return {
        "ok": True,
        "status": "READY_TO_SIGN",
        "grant": grant,
        "canonical_hex": canonical_bytes(request).hex(),
    }


def load_pag2_label(experiment_id: str = "real-model-sol-vs-terra-v2") -> str:
    path = experiment_runtime_dir() / experiment_id / "analysis.json"
    if not path.is_file():
        return "NOT_STARTED"
    data = json.loads(path.read_text(encoding="utf-8"))
    return str(data.get("pag2_label") or "NOT_STARTED")


def _blocked(reason: str, status: str) -> dict[str, Any]:
    return {
        "ok": False,
        "status": status,
        "reason": reason,
        "mutated": False,
        "actuate": False,
        "auto_promote": False,
        "exposure_consumed": 0,
    }


def production_ipc_probe(*, socket_path: str | None = None, timeout_s: float = 0.5) -> dict[str, Any]:
    """SO_PEERCRED / OS-timeout IPC check. Does not require a confirmatory candidate."""
    ipc = request_spawn_resolution(
        {
            "task_id": "pag2-ipc-probe",
            "task_context": {
                "task_id": "pag2-ipc-probe",
                "board": CANARY_BOARD,
                "environment": "production",
                "scope": "PRODUCTION_SHADOW",
            },
        },
        {"model": "gpt-5.6-sol"},
        socket_path=socket_path,
        timeout_s=timeout_s,
    )
    if ipc.get("reservation"):
        return _blocked("probe consumed a reservation", "FAIL_PROBE_CONSUMED_EXPOSURE")
    if ipc.get("actuate") or ipc.get("resolution") == "CANDIDATE":
        return _blocked("probe must not actuate", "FAIL_PROBE_ACTUATE")
    reason = str(ipc.get("reason") or "")
    dirty = " ".join(
        str(ipc.get(key) or "")
        for key in ("reason", "would_reason", "error")
    )
    if any(
        marker in dirty
        for marker in (
            "OSError",
            "Read-only file system",
            "Errno 30",
            "/usr/local/lib/hermes-eos/.runtime",
        )
    ):
        return {**_blocked(dirty, "FAIL"), "ipc": ipc}
    if reason == "PEER_REJECTED":
        return {**_blocked("SO_PEERCRED rejected this uid", "BLOCKED_PEER"), "ipc": ipc}
    if reason == "SHADOW_NO_ACTUATE":
        return {
            "ok": True,
            "status": "PASS",
            "reason": "IPC probe; no Kanban write; no exposure consume",
            "mutated": False,
            "actuate": False,
            "auto_promote": False,
            "exposure_consumed": 0,
            "ipc": ipc,
        }
    if reason in {"FileNotFoundError", "PermissionError", "ConnectionRefusedError"}:
        return {**_blocked(reason, "BLOCKED_IPC"), "ipc": ipc}
    if reason == "IPC timeout":
        return {
            "ok": True,
            "status": "PASS",
            "reason": "IPC timeout fail-open to BASELINE",
            "mutated": False,
            "actuate": False,
            "auto_promote": False,
            "exposure_consumed": 0,
            "ipc": ipc,
        }
    return {**_blocked(reason or "IPC probe failed", "FAIL"), "ipc": ipc}


def production_shadow(
    *,
    h1_status: str,
    pag2_label: str,
    tasks: list[dict[str, Any]] | None = None,
    state: dict[str, Any] | None = None,
    peer_uid: int = -1,
    runtime_uid: int = 0,
    transport: str = "inline",
    socket_path: str | None = None,
) -> dict[str, Any]:
    """Read-only would-select. Never consumes canary exposure. Requires H1 PASS."""
    if h1_status != "PASS":
        return _blocked("H1 verifier is not PASS", "BLOCKED_SECURITY_BOUNDARY")
    if pag2_label == "VALID_NO_PROMOTION":
        return {
            "ok": True,
            "status": "SKIPPED_NO_CANDIDATE",
            "reason": "VALID_NO_PROMOTION; production shadow is required only when a candidate exists",
            "mutated": False,
            "actuate": False,
            "auto_promote": False,
            "exposure_consumed": 0,
        }
    if pag2_label != "QUALIFIED_CANDIDATE":
        return _blocked(f"pag2_label={pag2_label}", "BLOCKED_EVIDENCE")
    contexts = list(tasks or [])
    if not contexts:
        contexts = [
            {
                "task_id": "pag2-shadow-probe",
                "board": CANARY_BOARD,
                "environment": "production",
                "scope": "PRODUCTION_SHADOW",
            }
        ]
    batch = shadow_batch(contexts, state)
    ipc = None
    if transport == "ipc":
        ipc = request_spawn_resolution(
            {"task_id": contexts[0].get("task_id") or "pag2-shadow-probe", "task_context": contexts[0]},
            {"model": "gpt-5.6-sol"},
            socket_path=socket_path,
            timeout_s=0.5,
        )
        if ipc.get("reservation"):
            return _blocked("shadow consumed a reservation", "FAIL_SHADOW_CONSUMED_EXPOSURE")
        if ipc.get("reason") == "PEER_REJECTED":
            return {
                **_blocked("SO_PEERCRED rejected this uid", "BLOCKED_PEER"),
                "ipc": ipc,
                "batch": batch,
            }
        if ipc.get("actuate") or ipc.get("resolution") == "CANDIDATE":
            return _blocked("shadow must not actuate", "FAIL_SHADOW_ACTUATE")
        return {
            "ok": True,
            "status": "PASS",
            "reason": "IPC shadow; no Kanban write; no exposure consume",
            "mutated": False,
            "actuate": False,
            "auto_promote": False,
            "exposure_consumed": 0,
            "batch": batch,
            "ipc": ipc,
        }
    if state is not None:
        ipc = handle_request(
            {
                "task_id": contexts[0].get("task_id") or "pag2-shadow-probe",
                "task_context": contexts[0],
                "baseline": {"model": "gpt-5.6-sol"},
            },
            peer_uid=peer_uid,
            runtime_uid=runtime_uid,
            state=state,
        )
        if ipc.get("reservation"):
            return _blocked("shadow consumed a reservation", "FAIL_SHADOW_CONSUMED_EXPOSURE")
    return {
        "ok": True,
        "status": "PASS",
        "reason": "read-only shadow; no Kanban write; no exposure consume",
        "mutated": False,
        "actuate": False,
        "auto_promote": False,
        "exposure_consumed": 0,
        "batch": batch,
        "ipc": ipc,
    }


def select_canary_task(natural_task_id: str | None) -> dict[str, Any]:
    task_id = str(natural_task_id or "").strip() or CANARY_WORKLOAD_ID
    workload = task_id == CANARY_WORKLOAD_ID or not natural_task_id
    return {
        "task_id": task_id,
        "board": CANARY_BOARD,
        "environment": "production",
        "scope": "PRODUCTION_CANARY",
        "canary_workload": workload,
    }


def production_canary(
    *,
    h1_status: str,
    pag2_label: str,
    h3_deployed: bool,
    approval_ok: bool,
    state: dict[str, Any],
    peer_uid: int,
    runtime_uid: int,
    natural_task_id: str | None = None,
    reserve_path: Any = None,
    transport: str = "inline",
    socket_path: str | None = None,
) -> dict[str, Any]:
    """One-task canary. Atomic exposure=1. Ubuntu peer is rejected by the actuator."""
    if h1_status != "PASS":
        return _blocked("H1 verifier is not PASS", "BLOCKED_SECURITY_BOUNDARY")
    if pag2_label != "QUALIFIED_CANDIDATE":
        return _blocked(f"canary requires QUALIFIED_CANDIDATE, got {pag2_label}", "BLOCKED_EVIDENCE")
    if not h3_deployed:
        return _blocked("H3 live seam not present on protected runtime", "BLOCKED_H3")
    if not approval_ok:
        return _blocked("Approval A not granted / runtime identity unbound", "BLOCKED_APPROVAL")
    context = select_canary_task(natural_task_id)
    if transport == "ipc":
        first = request_spawn_resolution(
            {"task_id": context["task_id"], "task_context": context},
            {"model": "gpt-5.6-sol"},
            socket_path=socket_path,
            timeout_s=0.5,
        )
        second = request_spawn_resolution(
            {
                "task_id": context["task_id"] + "-late",
                "task_context": {**context, "task_id": context["task_id"] + "-late"},
            },
            {"model": "gpt-5.6-sol"},
            socket_path=socket_path,
            timeout_s=0.5,
        )
        if first.get("reason") == "PEER_REJECTED":
            return {
                **_blocked("SO_PEERCRED rejected this uid", "BLOCKED_PEER"),
                "ipc": first,
            }
        reserved = first.get("resolution") == "CANDIDATE" and bool(first.get("actuate"))
        late_reserved = second.get("resolution") == "CANDIDATE" and bool(second.get("actuate"))
        if reserved and late_reserved:
            return _blocked("second canary unit reserved; exposure exceeded 1", "FAIL_EXPOSURE")
        return {
            "ok": reserved and not late_reserved,
            "status": "PASS" if reserved and not late_reserved else "FAIL",
            "reason": "IPC atomic exposure=1; later units BASELINE",
            "mutated": False,
            "actuate": bool(first.get("actuate")),
            "auto_promote": False,
            "exposure_consumed": 1 if reserved else 0,
            "canary_workload": context["canary_workload"],
            "task_id": context["task_id"],
            "first": first,
            "second": second,
        }
    if int(peer_uid) != int(runtime_uid):
        first = handle_request(
            {"task_id": "peer-check", "task_context": select_canary_task(natural_task_id), "baseline": {}},
            peer_uid=peer_uid,
            runtime_uid=runtime_uid,
            state=state,
            reserve_path=reserve_path,
        )
        return {
            "ok": False,
            "status": "BLOCKED_PEER",
            "reason": first.get("reason") or "PEER_REJECTED",
            "mutated": False,
            "actuate": False,
            "auto_promote": False,
            "exposure_consumed": 0,
            "ipc": first,
        }
    first = handle_request(
        {"task_id": context["task_id"], "task_context": context, "baseline": {"model": "gpt-5.6-sol"}},
        peer_uid=peer_uid,
        runtime_uid=runtime_uid,
        state=state,
        reserve_path=reserve_path,
    )
    second = handle_request(
        {
            "task_id": context["task_id"] + "-late",
            "task_context": {**context, "task_id": context["task_id"] + "-late"},
            "baseline": {"model": "gpt-5.6-sol"},
        },
        peer_uid=peer_uid,
        runtime_uid=runtime_uid,
        state=state,
        reserve_path=reserve_path,
    )
    reserved = bool(first.get("reservation", {}).get("reserved"))
    late_reserved = bool(second.get("reservation", {}).get("reserved"))
    if reserved and late_reserved:
        return _blocked("second canary unit reserved; exposure exceeded 1", "FAIL_EXPOSURE")
    return {
        "ok": reserved and not late_reserved and first.get("resolution") == "CANDIDATE",
        "status": "PASS" if reserved and not late_reserved else "FAIL",
        "reason": "atomic exposure=1; later units BASELINE",
        "mutated": False,
        "actuate": bool(first.get("actuate")),
        "auto_promote": False,
        "exposure_consumed": 1 if reserved else 0,
        "canary_workload": context["canary_workload"],
        "task_id": context["task_id"],
        "first": first,
        "second": second,
    }


def production_rollback(
    state: dict[str, Any],
    *,
    reason: str = "pag2 auto-disable",
    h1_status: str | None = None,
    persist_path: Path | None = None,
) -> dict[str, Any]:
    if h1_status is not None and h1_status != "PASS":
        return _blocked("H1 verifier is not PASS", "BLOCKED_SECURITY_BOUNDARY")
    live = dict(state or {})
    path = Path(persist_path) if persist_path is not None else None
    if path is not None and path.is_file():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            live = loaded
    binding = dict((live.get("bindings") or [{}])[0] if live.get("bindings") else {})
    payload = apply_auto_disable(binding, reason=reason)
    written = False
    if path is not None:
        if os.access(path.parent, os.W_OK) if path.parent.exists() else False:
            next_state = dict(live)
            bindings = list(next_state.get("bindings") or [binding])
            if bindings:
                bindings[0] = {
                    **dict(bindings[0]),
                    "state": "ROLLED_BACK",
                    "mode": "BASELINE",
                    "auto_promote": False,
                }
            next_state["bindings"] = bindings
            next_state["auto_promote"] = False
            next_state["maximum_exposure"] = int(next_state.get("maximum_exposure") or 1)
            path.write_text(json.dumps(next_state, indent=2) + "\n", encoding="utf-8")
            written = True
        else:
            return _blocked("cannot persist auto-disable to protected actuator state", "BLOCKED_WRITE")
    return {
        "ok": payload.get("status") == "success",
        "status": "PASS" if payload.get("status") == "success" else "FAIL",
        "reason": reason,
        "interrupt_running": False,
        "auto_promote": False,
        "persisted": written,
        "rollback": payload,
    }


def canary_binding(protocol: dict[str, Any]) -> dict[str, Any]:
    candidate = dict(protocol.get("candidate") or {})
    control = dict(protocol.get("control") or {})
    model = str(candidate.get("model") or "gpt-5.6-terra")
    policy_hash = str(protocol.get("_definition_hash") or "pag2-canary")
    return {
        "mode": "CANARY",
        "state": "ACTIVE",
        "policy_id": "pag2-canary-sol-vs-terra",
        "policy_hash": policy_hash,
        "auto_promote": False,
        "spec": {
            "policy_id": "pag2-canary-sol-vs-terra",
            "_policy_hash": policy_hash,
            "selectors": {
                "match": "ALL",
                "conditions": [{"field": "board", "op": "EQ", "values": [CANARY_BOARD]}],
            },
            "candidate": {
                "variant_id": candidate.get("variant_id") or "model-terra",
                "overrides": {"model": model},
            },
            "fallback": {
                "variant_id": control.get("variant_id") or "model-sol",
                "overrides": {"model": str(control.get("model") or "gpt-5.6-sol")},
            },
            "candidate_config_hash": model,
        },
    }


def bind_production_canary(
    *,
    h1_status: str,
    pag2_label: str,
    h3_deployed: bool,
    approval_ok: bool,
    persist_path: Path,
    protocol: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a maximum_exposure=1 CANARY binding. hermes-op only in production."""
    if h1_status != "PASS":
        return _blocked("H1 verifier is not PASS", "BLOCKED_SECURITY_BOUNDARY")
    if pag2_label != "QUALIFIED_CANDIDATE":
        return _blocked(f"canary bind requires QUALIFIED_CANDIDATE, got {pag2_label}", "BLOCKED_EVIDENCE")
    if not h3_deployed:
        return _blocked("H3 live seam not present on protected runtime", "BLOCKED_H3")
    if not approval_ok:
        return _blocked("Approval A not granted / runtime identity unbound", "BLOCKED_APPROVAL")
    path = Path(persist_path)
    parent = path.parent
    if not parent.exists() or not os.access(parent, os.W_OK):
        return _blocked("cannot persist canary binding to protected actuator state", "BLOCKED_WRITE")
    if protocol is None:
        from engineering_os.experiments.definitions import load_id

        protocol = load_id("real-model-sol-vs-terra-v2")
    analysis_file = experiment_runtime_dir() / str(protocol.get("experiment_id") or "real-model-sol-vs-terra-v2") / "analysis.json"
    if analysis_file.is_file():
        analyzed = json.loads(analysis_file.read_text(encoding="utf-8"))
        recorded = str(analyzed.get("protocol_hash") or "")
        current = str(protocol.get("_definition_hash") or "")
        if recorded and current and recorded != current:
            return _blocked("analysis protocol_hash does not match definition", "BLOCKED_EVIDENCE")
    current: dict[str, Any] = {}
    if path.is_file():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            current = loaded
    binding = canary_binding(protocol)
    next_state = dict(current)
    next_state["maximum_exposure"] = 1
    next_state["auto_promote"] = False
    next_state["bindings"] = [binding]
    path.write_text(json.dumps(next_state, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "status": "BOUND",
        "reason": "CANARY binding persisted; exposure max 1; auto_promote false",
        "mutated": True,
        "actuate": False,
        "auto_promote": False,
        "exposure_consumed": 0,
        "maximum_exposure": 1,
        "policy_id": binding["policy_id"],
    }
