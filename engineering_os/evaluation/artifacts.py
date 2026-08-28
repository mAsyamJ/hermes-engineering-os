"""Immutable evaluation artifact capture. Never mutates source workspaces."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from engineering_os.evaluation import MAX_ARTIFACT_BYTES, MAX_FILE_BYTES

SECRET_PATTERNS = [
    re.compile(r"FAKE_PHASE4_SECRET_[A-Z0-9]+"),
    re.compile(r"FAKE_PHASE3_SECRET_[A-Z0-9]+"),
    re.compile(r"(ghp_|github_pat_|gho_|ghu_|ghs_)[A-Za-z0-9_]{8,}"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"Bearer [A-Za-z0-9._~+/=-]{12,}"),
]
DENIED_NAMES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519", "credentials.json"}
DENIED_SUFFIXES = {".pem", ".sqlite", ".sqlite3", ".pyc"}
DENIED_DIRS = {"node_modules", ".git", ".cache", "__pycache__", ".turbo", "dist", "build"}


@dataclass
class CaptureResult:
    method: str
    content_hash: str
    size_bytes: int
    secret_scan_status: str
    base_commit: str | None = None
    candidate_commit: str | None = None
    patch_hash: str | None = None
    storage_path: str | None = None
    detail: str | None = None
    payload: bytes = field(default=b"", repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "content_hash": self.content_hash,
            "size_bytes": self.size_bytes,
            "secret_scan_status": self.secret_scan_status,
            "base_commit": self.base_commit,
            "candidate_commit": self.candidate_commit,
            "patch_hash": self.patch_hash,
            "storage_path": self.storage_path,
            "detail": self.detail,
        }


def _git(path: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=check,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _denied_path(rel: str) -> bool:
    parts = Path(rel).parts
    if any(part in DENIED_DIRS for part in parts):
        return True
    name = Path(rel).name
    if name in DENIED_NAMES or name.endswith(tuple(DENIED_SUFFIXES)):
        return True
    return False


def scan_bytes(payload: bytes) -> str:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = payload.decode("utf-8", "replace")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return "FAIL"
    return "PASS"


def scan_tree(root: Path) -> str:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root))
        if any(part in DENIED_DIRS for part in Path(rel).parts):
            continue
        if Path(rel).name in DENIED_NAMES or Path(rel).name.endswith(tuple(DENIED_SUFFIXES)):
            return "FAIL"
        if path.stat().st_size > MAX_FILE_BYTES:
            return "FAIL"
        if scan_bytes(path.read_bytes()) == "FAIL":
            return "FAIL"
    return "PASS"


def _hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def archive_commit(repo: Path, sha: str) -> CaptureResult:
    if not re.fullmatch(r"[0-9a-f]{7,40}", sha):
        raise ValueError("invalid sha")
    process = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar", sha],
        check=True,
        capture_output=True,
        timeout=60,
    )
    payload = process.stdout
    if len(payload) > MAX_ARTIFACT_BYTES:
        return CaptureResult(
            method="COMMIT_SNAPSHOT",
            content_hash="",
            size_bytes=len(payload),
            secret_scan_status="FAIL",
            candidate_commit=sha,
            detail="size_guard",
        )
    scan = _scan_tar(payload)
    digest = _hash_bytes(payload)
    return CaptureResult(
        method="COMMIT_SNAPSHOT",
        content_hash=digest,
        size_bytes=len(payload),
        secret_scan_status=scan,
        candidate_commit=sha,
        base_commit=sha,
        payload=payload,
        detail=None if scan == "PASS" else "secret_or_path_guard",
    )


def _scan_tar(payload: bytes) -> str:
    import io

    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
        total = 0
        for member in archive.getmembers():
            if member.isdir():
                continue
            name = member.name
            if any(part in DENIED_DIRS for part in Path(name).parts):
                continue
            if Path(name).name in DENIED_NAMES or Path(name).name.endswith(tuple(DENIED_SUFFIXES)):
                return "FAIL"
            if member.size > MAX_FILE_BYTES:
                return "FAIL"
            total += member.size
            if total > MAX_ARTIFACT_BYTES:
                return "FAIL"
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            data = extracted.read()
            if scan_bytes(data) == "FAIL":
                return "FAIL"
    return "PASS"


def capture_tracked_patch(workspace: Path, untracked_required: bool = False) -> CaptureResult:
    """Read-only base+tracked-diff. Does not archive untracked files."""
    head = _git(workspace, "rev-parse", "HEAD").stdout.strip()
    untracked = _git(workspace, "ls-files", "--others", "--exclude-standard").stdout.strip()
    if untracked and untracked_required:
        return CaptureResult(
            method="UNTRACKED_REQUIRED",
            content_hash="",
            size_bytes=0,
            secret_scan_status="UNKNOWN",
            candidate_commit=head,
            base_commit=head,
            detail="untracked_files_present",
        )
    porcelain = _git(workspace, "status", "--porcelain=v1", "-uno").stdout.strip()
    if not porcelain:
        return archive_commit(workspace, head)
    patch = subprocess.run(
        ["git", "-C", str(workspace), "diff", "--binary", "HEAD"],
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout
    patch_hash = _hash_bytes(patch)
    if scan_bytes(patch) == "FAIL":
        return CaptureResult(
            method="BASE_COMMIT_PLUS_TRACKED_PATCH",
            content_hash="",
            size_bytes=len(patch),
            secret_scan_status="FAIL",
            base_commit=head,
            patch_hash=patch_hash,
            detail="secret_in_patch",
        )
    base = archive_commit(workspace, head)
    if base.secret_scan_status != "PASS":
        return base
    payload = base.payload + b"\n--TRACKED-PATCH--\n" + patch
    return CaptureResult(
        method="BASE_COMMIT_PLUS_TRACKED_PATCH",
        content_hash=_hash_bytes(payload),
        size_bytes=len(payload),
        secret_scan_status="PASS",
        base_commit=head,
        candidate_commit=head,
        patch_hash=patch_hash,
        payload=payload,
    )


def extract_commit_tar(payload: bytes, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    import io

    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
        archive.extractall(dest, filter="data")


def materialize_capture(result: CaptureResult, dest: Path) -> None:
    if result.method == "COMMIT_SNAPSHOT":
        extract_commit_tar(result.payload, dest)
        return
    if result.method == "BASE_COMMIT_PLUS_TRACKED_PATCH":
        tar_part, patch_part = result.payload.split(b"\n--TRACKED-PATCH--\n", 1)
        extract_commit_tar(tar_part, dest)
        process = subprocess.run(
            ["git", "apply", "--unsafe-paths", "-p1"],
            input=patch_part,
            cwd=dest,
            capture_output=True,
            timeout=30,
        )
        if process.returncode != 0:
            # git archive has no .git; apply as unified diff onto files.
            _apply_unified(dest, patch_part.decode("utf-8", "replace"))
        return
    raise ValueError(result.method)


def _apply_unified(dest: Path, patch: str) -> None:
    """Minimal tracked-file apply for archive+diff without a git dir."""
    subprocess.run(
        ["patch", "-p1", "--forward", "--silent"],
        input=patch,
        cwd=dest,
        text=True,
        check=True,
        capture_output=True,
        timeout=30,
    )


def write_artifact(result: CaptureResult, root: Path) -> Path:
    if result.secret_scan_status != "PASS" or not result.content_hash:
        raise ValueError("refusing to store failed artifact")
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{result.content_hash}.bin"
    if not path.exists():
        path.write_bytes(result.payload)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    result.storage_path = str(path)
    return path


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if any(part in DENIED_DIRS for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix().encode()
        data = path.read_bytes()
        digest.update(rel)
        digest.update(b"\0")
        digest.update(str(len(data)).encode())
        digest.update(b"\0")
        digest.update(data)
    return digest.hexdigest()
