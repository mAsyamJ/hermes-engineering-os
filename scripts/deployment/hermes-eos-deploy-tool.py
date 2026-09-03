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



def _repo_root() -> Path:
    cur = Path(__file__).resolve().parent
    for p in [cur, *cur.parents]:
        if (p / "plugin.yaml").is_file() and (p / "pyproject.toml").is_file() and (p / "agent_os").is_dir():
            return p
    raise RuntimeError("repo root not found")
REPO = _repo_root()
def default_plugin_dir() -> Path:
    """H1 copies the hash-locked plugin into the TCB. Do not install from /opt after H1."""
    protected = Path("/usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin")
    if (protected / "__init__.py").is_file():
        return protected
    return REPO / "deploy" / "pag2" / "eos-actuation-plugin"


def verify_plugin_files(manifest: dict, plugin_dir: Path) -> None:
    files = manifest.get("plugin_files") or {}
    if not files:
        return
    for name, digest in files.items():
        path = plugin_dir / str(name)
        if not path.is_file():
            raise SystemExit(f"plugin file missing: {name}")
        if sha256_file(path) != str(digest):
            raise SystemExit(f"plugin file SHA256 mismatch: {name}")


def copy_plugin_files(manifest: dict, plugin_dir: Path, dest: Path) -> None:
    import shutil

    files = manifest.get("plugin_files") or {}
    if not files:
        return
    dest.mkdir(parents=True, exist_ok=True)
    for name in files:
        shutil.copy2(plugin_dir / str(name), dest / str(name))


def remove_plugin_files(dest: Path) -> None:
    import shutil

    if dest.is_dir():
        shutil.rmtree(dest)


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


def acting_principal(*, euid: int | None = None, sudo_user: str | None = None) -> str:
    """Identity that invoked the tool. root+sudo from hermes-op is hermes-op, not root."""
    uid = os.geteuid() if euid is None else euid
    sudo = os.environ.get("SUDO_USER") if sudo_user is None else sudo_user
    if uid == 0:
        return str(sudo or "root")
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return ""


def caller_is_ubuntu() -> bool:
    principal = acting_principal()
    return os.geteuid() == 1000 or principal == "ubuntu"


def require_hermes_op() -> None:
    if caller_is_ubuntu():
        raise SystemExit("ubuntu cannot invoke protected install/rollback")
    if acting_principal() != "hermes-op":
        raise SystemExit("install/rollback requires principal hermes-op")


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.is_file():
            return path
    return None


def verify_hashed_file(expected: str, candidates: list[Path], label: str) -> None:
    digest = str(expected or "")
    if not digest:
        return
    path = _first_existing(candidates)
    if path is None:
        raise SystemExit(f"{label} missing")
    if sha256_file(path) != digest:
        raise SystemExit(f"{label} SHA256 mismatch")


def verify_ipc_hashes(manifest: dict) -> None:
    ipc_env = os.environ.get("HERMES_EOS_IPC_CLIENT")
    transport_env = os.environ.get("HERMES_EOS_IPC_TRANSPORT")
    verify_hashed_file(
        str(manifest.get("ipc_client_sha256") or ""),
        [
            *([Path(ipc_env)] if ipc_env else []),
            Path("/usr/local/lib/hermes-eos/engineering_os/adaptation/hermes_plugin.py"),
            REPO / "engineering_os" / "adaptation" / "hermes_plugin.py",
        ],
        "ipc client",
    )
    verify_hashed_file(
        str(manifest.get("ipc_transport_sha256") or ""),
        [
            *([Path(transport_env)] if transport_env else []),
            Path("/usr/local/lib/hermes-eos/engineering_os/adaptation/ipc_client.py"),
            REPO / "engineering_os" / "adaptation" / "ipc_client.py",
        ],
        "ipc transport",
    )


def canonical_deploy_bytes(manifest: dict) -> bytes:
    payload = {key: manifest.get(key) for key in REQUIRED}
    payload["plugin_files"] = manifest.get("plugin_files") or {}
    payload["ipc_client_sha256"] = manifest.get("ipc_client_sha256") or ""
    payload["ipc_transport_sha256"] = manifest.get("ipc_transport_sha256") or ""
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def nonce_is_example(nonce: str) -> bool:
    text = str(nonce or "")
    return "example" in text or "not-authorizing" in text


def require_live_nonce(nonce: str) -> None:
    if nonce_is_example(nonce):
        raise SystemExit("example nonce cannot be installed")


def nonce_dir() -> Path:
    return Path(os.environ.get("HERMES_EOS_NONCE_DIR") or "/var/lib/hermes-actuator/deploy-nonces")


def consume_install_nonce(nonce: str) -> None:
    if not nonce:
        raise SystemExit("manifest nonce missing")
    directory = nonce_dir()
    directory.mkdir(parents=True, exist_ok=True)
    marker = directory / f"{nonce}.used"
    if marker.is_file():
        raise SystemExit("deploy nonce replay")
    marker.write_text("used\n", encoding="utf-8")


def require_rollback_allowed(nonce: str) -> None:
    if not nonce:
        raise SystemExit("manifest nonce missing")
    directory = nonce_dir()
    installed = directory / f"{nonce}.used"
    rolled = directory / f"{nonce}.rolled"
    if not installed.is_file():
        raise SystemExit("rollback requires a prior successful install of this nonce")
    if rolled.is_file():
        raise SystemExit("deploy rollback nonce replay")


def consume_rollback_nonce(nonce: str) -> None:
    require_rollback_allowed(nonce)
    (nonce_dir() / f"{nonce}.rolled").write_text("rolled\n", encoding="utf-8")


def verify_deploy_signature(manifest: dict, signature_hex: str, pub_path: Path) -> None:
    if not pub_path.is_file():
        raise SystemExit("trust pub missing; H1 public trust is required before H3")
    raw = pub_path.read_bytes().strip()
    if len(raw) == 32:
        pub = raw
    else:
        text = raw.decode("ascii", errors="ignore").strip().replace("\n", "")
        if len(text) != 64:
            raise SystemExit("trust pub is not a 32-byte/64-hex Ed25519 public key")
        pub = bytes.fromhex(text)
    try:
        sig = bytes.fromhex(signature_hex.strip())
    except ValueError as exc:
        raise SystemExit("signature is not hex") from exc
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        Ed25519PublicKey.from_public_bytes(pub).verify(sig, canonical_deploy_bytes(manifest))
    except Exception as exc:
        raise SystemExit("deploy signature mismatch") from exc


def apply_artifact(manifest: dict, artifact: Path, dest_root: Path) -> None:
    """Apply a content-hashed patch inside dest_root. Caller must already be hermes-op."""
    import subprocess

    dest = dest_root.expanduser().resolve()
    if not dest.is_dir():
        raise SystemExit(f"runtime tree missing: {dest}")
    git = ["git", "-c", f"safe.directory={dest}", "-C", str(dest)]
    check = subprocess.run(
        [*git, "apply", "--check", str(artifact)],
        check=False,
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        raise SystemExit(check.stderr or "git apply --check failed")
    applied = subprocess.run(
        [*git, "apply", str(artifact)],
        check=False,
        capture_output=True,
        text=True,
    )
    if applied.returncode != 0:
        raise SystemExit(applied.stderr or "git apply failed")


def rewrite_env_value(path: Path, key: str, value: str) -> None:
    if not path.is_file():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    found = False
    out: list[str] = []
    prefix = f"{key}="
    for line in lines:
        if line.startswith(prefix):
            out.append(f"{prefix}{value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{prefix}{value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def update_state_live_patch(path: Path, live_patch_hash: str) -> None:
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return
    ident = dict(data.get("runtime_identity") or {})
    ident["live_patch_hash"] = live_patch_hash
    ident["actuator_contract_version"] = ident.get("actuator_contract_version") or "pag2-actuator-v1"
    data["runtime_identity"] = ident
    data["auto_promote"] = False
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def ensure_plugin_enabled(config_path: Path, name: str) -> None:
    if not config_path.is_file():
        return
    text = config_path.read_text(encoding="utf-8")
    needle = f"    - {name}\n"
    if needle in text:
        return
    marker = "  enabled:\n"
    idx = text.find(marker)
    if idx < 0:
        return
    insert_at = idx + len(marker)
    config_path.write_text(text[:insert_at] + needle + text[insert_at:], encoding="utf-8")


def ensure_plugin_disabled(config_path: Path, name: str) -> None:
    if not config_path.is_file():
        return
    needle = f"    - {name}\n"
    text = config_path.read_text(encoding="utf-8")
    if needle not in text:
        return
    config_path.write_text(text.replace(needle, ""), encoding="utf-8")


def units_to_reload(manifest: dict) -> list[str]:
    """Actuator picks up LIVE_PATCH_HASH; gateways must load the spawn-transform."""
    units = ["hermes-eos-actuator.service"]
    seen = set(units)
    for unit in manifest.get("affected_units") or []:
        name = str(unit).strip()
        if not name.endswith(".service") and not name.endswith(".socket"):
            continue
        if "/" in name or ".." in name or " " in name:
            continue
        if name not in seen:
            units.append(name)
            seen.add(name)
    return units


def sync_runtime_identity(manifest: dict, *, installed: bool) -> None:
    """Bind live_patch_hash after H3 install; clear it on rollback. Never auto-promote."""
    patch = str(manifest.get("artifact_sha256") or "") if installed else ""
    env_path = Path(os.environ.get("HERMES_EOS_ACTUATOR_ENV") or "/etc/hermes-eos/actuator.env")
    state_path = Path(os.environ.get("HERMES_EOS_ACTUATOR_STATE") or "/var/lib/hermes-actuator/state.json")
    rewrite_env_value(env_path, "HERMES_EOS_LIVE_PATCH_HASH", patch)
    update_state_live_patch(state_path, patch)
    home = Path(os.environ.get("HERMES_EOS_RUNTIME_HOME") or "/var/lib/hermes-runtime/home")
    if installed:
        ensure_plugin_enabled(home / "config.yaml", "eos-actuation")
        ensure_plugin_enabled(home / "profiles" / "rp-friend" / "config.yaml", "eos-actuation")
    else:
        ensure_plugin_disabled(home / "config.yaml", "eos-actuation")
        ensure_plugin_disabled(home / "profiles" / "rp-friend" / "config.yaml", "eos-actuation")
    if os.environ.get("HERMES_EOS_SKIP_UNIT_RESTART") == "1" or os.geteuid() != 0:
        return
    import subprocess

    for unit in units_to_reload(manifest):
        subprocess.run(["systemctl", "try-reload-or-restart", unit], check=False)


def reverse_artifact(artifact: Path, dest_root: Path) -> None:
    import subprocess

    dest = dest_root.expanduser().resolve()
    reversed_ = subprocess.run(
        ["git", "-c", f"safe.directory={dest}", "-C", str(dest), "apply", "-R", str(artifact)],
        check=False,
        capture_output=True,
        text=True,
    )
    if reversed_.returncode != 0:
        raise SystemExit(reversed_.stderr or "git apply -R failed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes EOS hash-locked deploy tool")
    parser.add_argument("command", choices=("verify", "show", "canonical", "install", "rollback"))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--signature", default="")
    parser.add_argument("--plugin-dir", default="")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    verify_manifest(manifest, Path(args.artifact))
    plugin_dir = Path(args.plugin_dir) if args.plugin_dir else default_plugin_dir()
    verify_plugin_files(manifest, plugin_dir)
    verify_ipc_hashes(manifest)
    print("PASS: artifact hash matches manifest")
    print(f"base={manifest['base_runtime_hash']}")
    print(f"artifact={manifest['artifact_sha256']}")
    print(f"rollback={manifest['rollback_hash']}")
    if args.command == "show":
        print(json.dumps({k: manifest[k] for k in ("affected_files", "affected_units") if k in manifest}, indent=2))
        return 0
    if args.command == "verify":
        print("NOTE: install/rollback must be executed by hermes-op via the protected copy of this tool")
        return 0
    if args.command == "canonical":
        print(canonical_deploy_bytes(manifest).hex())
        print("Sign these bytes off-VPS. Change nonce away from the example before install.")
        return 0
    require_hermes_op()
    nonce = str(manifest.get("nonce") or "")
    require_live_nonce(nonce)
    if not args.signature:
        raise SystemExit("install/rollback requires a detached signature")
    pub = Path(os.environ.get("HERMES_EOS_TRUST_PUB") or "/etc/hermes-eos/approval-trust.pub")
    verify_deploy_signature(manifest, args.signature, pub)
    dest = Path(os.environ.get("HERMES_EOS_RUNTIME_ROOT") or "/usr/lib/hermes-runtime/hermes-agent")
    plugin_dest = Path(os.environ.get("HERMES_EOS_PLUGIN_ROOT") or "/var/lib/hermes-runtime/home/plugins/eos-actuation")
    if args.command == "install":
        apply_artifact(manifest, Path(args.artifact), dest)
        copy_plugin_files(manifest, plugin_dir, plugin_dest)
        consume_install_nonce(str(manifest.get("nonce") or ""))
        sync_runtime_identity(manifest, installed=True)
        print("PASS: install applied")
        return 0
    nonce = str(manifest.get("nonce") or "")
    require_rollback_allowed(nonce)
    reverse_artifact(Path(args.artifact), dest)
    if manifest.get("plugin_files"):
        remove_plugin_files(plugin_dest)
    consume_rollback_nonce(nonce)
    sync_runtime_identity(manifest, installed=False)
    print("PASS: rollback applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
