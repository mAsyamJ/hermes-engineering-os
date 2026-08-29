"""Production approval protocol approval-ed25519-v1.

Implements request generation, detached-signature verification, and replay
protection. Production grant remains BLOCKED_SECURITY_BOUNDARY until a trust
anchor exists outside autonomous-agent authority. TEST HMAC stays in approval.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engineering_os.adaptation import (
    APPROVAL_ED25519_ALG,
    PAR_CONTRACT,
    PRODUCTION_SCOPES,
    TEST_APPROVAL_ALG,
    TEST_SCOPES,
)
from engineering_os.experiments.config_snapshot import canonical_dumps, sha256_text

ROOT = Path(__file__).resolve().parents[2]
PROTECTED_TRUST_PUB = Path("/etc/hermes-eos/approval-trust.pub")
PROTECTED_VERIFIER = Path("/usr/local/lib/hermes-eos/approval-verifier")
AGENT_UID = 1000
CANONICAL_FIELDS = (
    "request_id",
    "recommendation_id",
    "policy_id",
    "policy_hash",
    "policy_version",
    "approval_stage",
    "scope",
    "maximum_exposure",
    "candidate_config_hash",
    "fallback_hash",
    "rollback_hash",
    "expiry",
    "nonce",
    "created_at",
    "contract_version",
    "runtime_release_hash",
    "live_patch_hash",
    "actuator_contract_version",
    "trust_fingerprint",
)

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
    )

    _HAS_CRYPTO = True
except ImportError:  # pragma: no cover
    Ed25519PrivateKey = None  # type: ignore[assignment]
    Ed25519PublicKey = None  # type: ignore[assignment]
    _HAS_CRYPTO = False


class ProtocolError(ValueError):
    pass


def runtime_dir() -> Path:
    override = os.environ.get("EOS_ADAPTATION_RUNTIME")
    base = Path(override) if override else ROOT / ".runtime" / "adaptation"
    path = base / "nonces"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_request(fields: dict[str, Any]) -> dict[str, str]:
    payload = {key: str(fields.get(key) or "") for key in CANONICAL_FIELDS}
    payload.setdefault("contract_version", PAR_CONTRACT)
    return payload


def canonical_bytes(fields: dict[str, Any]) -> bytes:
    return canonical_dumps(canonical_request(fields)).encode("utf-8")


def request_hash(fields: dict[str, Any]) -> str:
    return sha256_text(canonical_dumps(canonical_request(fields)))


def generate_approval_request(
    *,
    recommendation_id: str,
    policy_id: str,
    policy_hash: str,
    policy_version: str,
    approval_stage: str,
    scope: str,
    maximum_exposure: int,
    candidate_config_hash: str,
    fallback_hash: str,
    rollback_hash: str,
    expiry: str,
    runtime_release_hash: str = "",
    live_patch_hash: str = "",
    actuator_contract_version: str = "",
    trust_fingerprint: str = "",
) -> dict[str, Any]:
    created = _now().replace(microsecond=0).isoformat()
    request = canonical_request(
        {
            "request_id": secrets.token_hex(16),
            "recommendation_id": recommendation_id,
            "policy_id": policy_id,
            "policy_hash": policy_hash,
            "policy_version": policy_version,
            "approval_stage": approval_stage,
            "scope": scope,
            "maximum_exposure": maximum_exposure,
            "candidate_config_hash": candidate_config_hash,
            "fallback_hash": fallback_hash,
            "rollback_hash": rollback_hash,
            "expiry": expiry,
            "nonce": secrets.token_hex(16),
            "created_at": created,
            "contract_version": PAR_CONTRACT,
            "runtime_release_hash": runtime_release_hash,
            "live_patch_hash": live_patch_hash,
            "actuator_contract_version": actuator_contract_version,
            "trust_fingerprint": trust_fingerprint,
        }
    )
    request["algorithm"] = APPROVAL_ED25519_ALG
    request["request_hash"] = request_hash(request)
    return request


def generate_ephemeral_keypair() -> dict[str, bytes]:
    if not _HAS_CRYPTO:
        raise ProtocolError("cryptography is required for protocol rehearsal keys")
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    return {
        "private": private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()),
        "public": public.public_bytes(Encoding.Raw, PublicFormat.Raw),
    }


def sign_detached(fields: dict[str, Any], private_key: bytes) -> str:
    if not _HAS_CRYPTO:
        raise ProtocolError("cryptography is required to sign approval-ed25519-v1")
    if fields.get("algorithm") and fields.get("algorithm") != APPROVAL_ED25519_ALG:
        raise ProtocolError("TEST HMAC cannot sign approval-ed25519-v1")
    if fields.get("algorithm") == TEST_APPROVAL_ALG:
        raise ProtocolError("TEST algorithm cannot produce production protocol signatures")
    key = Ed25519PrivateKey.from_private_bytes(private_key)
    signature = key.sign(canonical_bytes(fields))
    return signature.hex()


def _parse_expiry(value: str) -> datetime | None:
    if not value:
        return None
    try:
        when = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when


def nonce_seen(nonce: str) -> bool:
    if not nonce:
        return False
    path = runtime_dir() / f"{nonce}.used"
    return path.is_file()


def consume_nonce(nonce: str) -> None:
    path = runtime_dir() / f"{nonce}.used"
    path.write_text(str(time.time()), encoding="utf-8")
    path.chmod(0o600)


def verify_detached_signature(
    fields: dict[str, Any],
    signature: str,
    public_key: bytes,
    *,
    consume: bool = True,
    expected_signer: str | None = None,
    signer_id: str | None = None,
) -> dict[str, Any]:
    payload = canonical_request(fields)
    algorithm = str(fields.get("algorithm") or APPROVAL_ED25519_ALG)
    if algorithm == TEST_APPROVAL_ALG:
        return {"ok": False, "reason": "TEST HMAC cannot satisfy approval-ed25519-v1"}
    if algorithm != APPROVAL_ED25519_ALG:
        return {"ok": False, "reason": "algorithm mismatch"}
    if expected_signer and signer_id and expected_signer != signer_id:
        return {"ok": False, "reason": "wrong signer"}
    expires = _parse_expiry(payload["expiry"])
    if expires is None:
        return {"ok": False, "reason": "invalid expiry"}
    if expires < _now():
        return {"ok": False, "reason": "approval expired"}
    nonce = payload["nonce"]
    if nonce_seen(nonce):
        return {"ok": False, "reason": "replay"}
    if not _HAS_CRYPTO:
        return {"ok": False, "reason": "cryptography backend unavailable"}
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(bytes.fromhex(signature), canonical_bytes(payload))
    except Exception:
        return {"ok": False, "reason": "signature mismatch"}
    if consume:
        consume_nonce(nonce)
    return {"ok": True, "reason": "detached signature valid", "request_hash": request_hash(payload)}


def verify_scope_class(*, scope: str, approval_class: str) -> dict[str, Any]:
    if approval_class == "TEST" and scope in PRODUCTION_SCOPES:
        return {"ok": False, "reason": "TEST credential cannot authorize production"}
    if approval_class == "TEST" and scope not in TEST_SCOPES:
        return {"ok": False, "reason": f"TEST scope not allowed: {scope}"}
    if approval_class == "PRODUCTION" and scope not in PRODUCTION_SCOPES:
        return {"ok": False, "reason": "PRODUCTION class cannot be used for test scopes"}
    return {"ok": True, "reason": "scope class ok"}


def verify_bindings(request: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    for key in (
        "policy_hash",
        "scope",
        "approval_stage",
        "recommendation_id",
        "candidate_config_hash",
        "rollback_hash",
        "maximum_exposure",
        "runtime_release_hash",
        "live_patch_hash",
        "actuator_contract_version",
        "trust_fingerprint",
    ):
        if str(request.get(key) or "") != str(expected.get(key) or ""):
            return {"ok": False, "reason": f"{key} mismatch"}
    return {"ok": True, "reason": "bindings match"}


def _owned_by_agent(path: Path) -> bool:
    try:
        return path.stat().st_uid == AGENT_UID
    except OSError:
        return True


def _agent_can_write(path: Path) -> bool:
    try:
        if os.access(path, os.W_OK):
            return True
        if os.access(path.parent, os.W_OK):
            return True
    except OSError:
        return True
    return _owned_by_agent(path)


def trust_paths_protected() -> bool:
    """True only when ubuntu cannot replace the installed public trust or verifier."""
    if not PROTECTED_TRUST_PUB.is_file() or not PROTECTED_VERIFIER.exists():
        return False
    if _agent_can_write(PROTECTED_TRUST_PUB) or _agent_can_write(PROTECTED_VERIFIER):
        return False
    return True


def load_protected_public_key() -> bytes | None:
    if not trust_paths_protected():
        return None
    try:
        raw = PROTECTED_TRUST_PUB.read_bytes().strip()
    except OSError:
        return None
    if len(raw) == 32:
        return raw
    text = raw.decode("ascii", errors="ignore").strip().replace("\n", "")
    if len(text) == 64 and all(char in "0123456789abcdefABCDEF" for char in text):
        return bytes.fromhex(text)
    if _HAS_CRYPTO and (b"BEGIN" in raw):
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        try:
            return load_pem_public_key(raw).public_bytes(Encoding.Raw, PublicFormat.Raw)
        except Exception:
            return None
    return None


def production_trust_anchor_status() -> dict[str, Any]:
    """Honest classification. Agent-writable material is never a production grant."""
    if os.environ.get("HERMES_CONTROL_PRODUCTION_APPROVAL_KEY"):
        return {
            "status": "BLOCKED_SECURITY_BOUNDARY",
            "granted": False,
            "reason": "production key on autonomous worker is not a secure human boundary",
            "agent_replaceable": True,
        }
    if not trust_paths_protected():
        return {
            "status": "BLOCKED_SECURITY_BOUNDARY",
            "granted": False,
            "reason": "no off-VPS operator trust anchor is registered; local verifiers are agent-replaceable",
            "agent_replaceable": True,
            "algorithm": APPROVAL_ED25519_ALG,
        }
    return {
        "status": "PROTECTED_TRUST_PRESENT",
        "granted": False,
        "reason": "protected public trust is installed; signatures still required",
        "agent_replaceable": False,
        "algorithm": APPROVAL_ED25519_ALG,
        "trust_fingerprint": fingerprint_public_key(load_protected_public_key() or b""),
    }


def verify_production_authorization(
    fields: dict[str, Any] | None = None,
    signature: str | None = None,
    public_key: bytes | None = None,
) -> dict[str, Any]:
    """Never grants from caller-supplied or agent-replaceable keys.

    The public_key argument is ignored. Only /etc/hermes-eos/approval-trust.pub
    is used, and only when ubuntu cannot write that file or the protected verifier.
    """
    _ = public_key
    payload = dict(production_trust_anchor_status())
    payload.update({"ok": False, "classification": "PRODUCTION", "algorithm": APPROVAL_ED25519_ALG})
    if payload.get("agent_replaceable") or payload.get("status") != "PROTECTED_TRUST_PRESENT":
        return payload
    if not fields or not signature:
        payload["reason"] = "protected trust present but request/signature missing"
        return payload
    key = load_protected_public_key()
    if not key:
        payload["status"] = "BLOCKED_SECURITY_BOUNDARY"
        payload["reason"] = "protected trust file unreadable or not a public key"
        payload["agent_replaceable"] = True
        return payload
    checked = verify_detached_signature(fields, signature, key, consume=True)
    if not checked.get("ok"):
        payload["reason"] = checked.get("reason") or "signature rejected"
        return payload
    payload.update({"ok": True, "granted": True, "reason": "protected detached signature valid"})
    return payload


def fingerprint_public_key(public_key: bytes) -> str:
    return hashlib.sha256(public_key).hexdigest()[:16]
