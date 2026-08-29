#!/usr/bin/env python3
"""Hash-locked deploy tool. Never trusts git refs. Does not run as ubuntu-writable code in production."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest(manifest: dict, artifact: Path) -> None:
    required = (
        "base_runtime_hash",
        "artifact_sha256",
        "affected_files",
        "affected_units",
        "rollback_hash",
    )
    missing = [key for key in required if not manifest.get(key)]
    if missing:
        raise SystemExit(f"manifest missing {missing}")
    actual = sha256_file(artifact)
    if actual != manifest["artifact_sha256"]:
        raise SystemExit("artifact SHA256 mismatch")
    if manifest.get("git_ref"):
        raise SystemExit("git refs are not a deployment authority")


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes EOS hash-locked deploy verifier")
    parser.add_argument("command", choices=("verify", "show"))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--artifact", required=True)
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    verify_manifest(manifest, Path(args.artifact))
    print("PASS: artifact hash matches manifest")
    print(f"base={manifest['base_runtime_hash']}")
    print(f"artifact={manifest['artifact_sha256']}")
    print(f"rollback={manifest['rollback_hash']}")
    if args.command == "show":
        print(json.dumps({k: manifest[k] for k in ("affected_files", "affected_units")}, indent=2))
    print("NOTE: install/rollback must be executed by hermes-op via the protected copy of this tool")
    return 0


if __name__ == "__main__":
    sys.exit(main())
