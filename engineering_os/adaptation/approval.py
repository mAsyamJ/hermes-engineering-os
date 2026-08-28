"""TEST-only HMAC approval. Production grant is BLOCKED_CAPABILITY."""

from __future__ import annotations

import hmac
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engineering_os.adaptation import (
    PRODUCTION_APPROVAL,
    PRODUCTION_APPROVAL_ALG,
    PRODUCTION_SCOPES,
    TEST_APPROVAL_ALG,
    TEST_SCOPES,
)
from engineering_os.experiments.config_snapshot import sha256_text

ROOT = Path(__file__).resolve().parents[2]


def test_key_path() -> Path:
    override = os.environ.get("EOS_ADAPTATION_RUNTIME")
    base = Path(override) if override else ROOT / ".runtime" / "adaptation"
    return base / "keys" / "test-approval.key"


TEST_KEY_PATH = test_key_path()


class ApprovalError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_message(fields: dict[str, Any]) -> str:
    parts = [
        str(fields.get("algorithm") or ""),
        str(fields.get("stage") or ""),
        str(fields.get("approval_class") or ""),
        str(fields.get("recommendation_id") or ""),
        str(fields.get("policy_hash") or ""),
        str(fields.get("policy_version") or ""),
        str(fields.get("scope") or ""),
        str(fields.get("max_exposure") or ""),
        str(fields.get("expires_at") or ""),
        str(fields.get("rollback_hash") or ""),
        str(fields.get("operator_identity") or ""),
    ]
    return "|".join(parts)


def test_key() -> bytes:
    override = os.environ.get("HERMES_CONTROL_TEST_APPROVAL_KEY")
    if override:
        return override.encode("utf-8")
    path = test_key_path()
    if path.is_file():
        return path.read_bytes().strip()
    raise ApprovalError("TEST approval key is not initialized")


def ensure_test_key() -> Path:
    path = test_key_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_bytes(os.urandom(32).hex().encode("ascii"))
        path.chmod(0o600)
    return path


def sign_test(fields: dict[str, Any], key: bytes | None = None) -> str:
    payload = dict(fields)
    payload["algorithm"] = TEST_APPROVAL_ALG
    payload["approval_class"] = "TEST"
    if payload.get("scope") in PRODUCTION_SCOPES:
        raise ApprovalError("TEST approval cannot authorize production scope")
    if payload.get("scope") not in TEST_SCOPES:
        raise ApprovalError(f"TEST approval scope not allowed: {payload.get('scope')}")
    if payload.get("approval_class") != "TEST":
        raise ApprovalError("TEST signer cannot emit PRODUCTION class")
    digest = hmac.new(key or test_key(), canonical_message(payload).encode("utf-8"), hashlib.sha256).hexdigest()
    return digest


def verify_test(fields: dict[str, Any], signature: str, key: bytes | None = None) -> dict[str, Any]:
    payload = dict(fields)
    payload.setdefault("algorithm", TEST_APPROVAL_ALG)
    payload.setdefault("approval_class", "TEST")
    if payload.get("scope") in PRODUCTION_SCOPES:
        return {"ok": False, "reason": "TEST key cannot authorize production"}
    if payload.get("approval_class") != "TEST":
        return {"ok": False, "reason": "approval class mismatch"}
    if payload.get("algorithm") != TEST_APPROVAL_ALG:
        return {"ok": False, "reason": "algorithm mismatch"}
    expires = payload.get("expires_at")
    if expires:
        try:
            when = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if when < _now():
                return {"ok": False, "reason": "approval expired"}
        except ValueError:
            return {"ok": False, "reason": "invalid expiry"}
    expected = hmac.new(key or test_key(), canonical_message(payload).encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return {"ok": False, "reason": "signature mismatch"}
    return {"ok": True, "reason": "TEST approval valid"}


def approve_production(_fields: dict[str, Any] | None = None) -> dict[str, Any]:
    key = os.environ.get("HERMES_CONTROL_PRODUCTION_APPROVAL_KEY")
    if key:
        # A production key present on the autonomous worker is not a secure boundary.
        return {
            "status": "BLOCKED_APPROVAL_BOUNDARY",
            "classification": PRODUCTION_APPROVAL,
            "algorithm": PRODUCTION_APPROVAL_ALG,
            "reason": "production key on autonomous worker is not a secure human boundary",
            "granted": False,
        }
    return {
        "status": "BLOCKED_APPROVAL_BOUNDARY",
        "classification": PRODUCTION_APPROVAL,
        "algorithm": PRODUCTION_APPROVAL_ALG,
        "reason": "no secure human production approval boundary exists on this VPS",
        "granted": False,
    }


def approval_fingerprint(signature: str) -> str:
    return sha256_text(signature)[:16]
