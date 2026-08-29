#!/usr/bin/env python3
"""Hash-locked deploy tool. Never trusts git refs.

verify/show: anyone may check hashes.
install/rollback: refused for ubuntu (uid 1000). After H1, only the
protected copy invoked by hermes-op may apply an artifact, and only after
hash + signature + expiry/nonce checks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = (
    "base_runtime_hash",
    "artifact_sha256",
    "affected_files",
    "affected_units",
    "rollback_hash",
    "expiry",
    "nonce",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest(manifest: dict, artifact: Path) -> None:
    missing = [key for key in REQUIRED if not manifest.get(key)]
    if missing:
        raise SystemExit(f"manifest missing {missing}")
    actual = sha256_file(artifact)
    if actual != manifest["artifact_sha256"]:
        raise SystemExit("artifact SHA256 mismatch")
    if manifest.get("git_ref") or manifest.get("git_commit") or manifest.get("branch"):
        raise SystemExit("git refs are not a deployment authority")
    expiry = str(manifest.get("expiry") or "")
    try:
        when = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit("manifest expiry invalid") from exc
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if when < datetime.now(timezone.utc):
        raise SystemExit("manifest expired")


def caller_is_ubuntu() -> bool:
    try:
        name = pwd.getpwuid(os.geteuid()).pw_name
    except KeyError:
        name = ""
    return os.geteuid() == 1000 or name == "ubuntu"


def require_hermes_op() -> None:
    if caller_is_ubuntu():
        raise SystemExit("ubuntu cannot invoke protected install/rollback")
    try:
        name = pwd.getpwuid(os.geteuid()).pw_name
    except KeyError:
        name = ""
    if name != "hermes-op":
        raise SystemExit("install/rollback requires principal hermes-op")


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes EOS hash-locked deploy tool")
    parser.add_argument("command", choices=("verify", "show", "install", "rollback"))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--signature", default="")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    verify_manifest(manifest, Path(args.artifact))
    print("PASS: artifact hash matches manifest")
    print(f"base={manifest['base_runtime_hash']}")
    print(f"artifact={manifest['artifact_sha256']}")
    print(f"rollback={manifest['rollback_hash']}")
    if args.command == "show":
        print(json.dumps({k: manifest[k] for k in ("affected_files", "affected_units")}, indent=2))
        return 0
    if args.command == "verify":
        print("NOTE: install/rollback must be executed by hermes-op via the protected copy of this tool")
        return 0
    require_hermes_op()
    if not args.signature:
        raise SystemExit("install/rollback requires a detached signature")
    raise SystemExit("apply path is only enabled in the protected hermes-op copy after H1")


if __name__ == "__main__":
    sys.exit(main())
