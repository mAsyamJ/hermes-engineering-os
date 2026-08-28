"""Isolated candidate execution. Docker socket is never given to the candidate."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engineering_os.evaluation import LOG_LIMIT_BYTES, SANDBOX_IMAGE


@dataclass
class SandboxResult:
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timeout: bool
    resource_failure: bool
    image: str
    network: str
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "timeout": self.timeout,
            "resource_failure": self.resource_failure,
            "image": self.image,
            "network": self.network,
            "detail": self.detail,
        }


def _bound(text: str | bytes) -> str:
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    if len(text.encode("utf-8")) <= LOG_LIMIT_BYTES:
        return text
    encoded = text.encode("utf-8")[-LOG_LIMIT_BYTES:]
    return encoded.decode("utf-8", "replace")


def sanitized_env() -> dict[str, str]:
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "LANG": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": "/work",
    }


def run_inline(argv: list[str], tree: Path, timeout_seconds: int = 60) -> SandboxResult:
    """Test helper. Production Tier C uses docker."""
    started = time.monotonic()
    try:
        process = subprocess.run(
            argv,
            cwd=str(tree),
            env=sanitized_env() | {"PYTHONPATH": str(tree)},
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        duration = int((time.monotonic() - started) * 1000)
        return SandboxResult(
            exit_code=process.returncode,
            stdout=_bound(process.stdout),
            stderr=_bound(process.stderr),
            duration_ms=duration,
            timeout=False,
            resource_failure=False,
            image="inline",
            network="none",
        )
    except subprocess.TimeoutExpired as exc:
        duration = int((time.monotonic() - started) * 1000)
        return SandboxResult(
            exit_code=None,
            stdout=_bound(exc.stdout or b""),
            stderr=_bound(exc.stderr or b""),
            duration_ms=duration,
            timeout=True,
            resource_failure=False,
            image="inline",
            network="none",
            detail="timeout",
        )


def docker_available() -> bool:
    process = subprocess.run(
        ["sudo", "-n", "docker", "info"],
        capture_output=True,
        timeout=8,
    )
    return process.returncode == 0


def run_docker(
    argv: list[str],
    tree: Path,
    timeout_seconds: int = 60,
    memory: str = "512m",
    cpus: str = "1",
    pids: int = 128,
    image: str = SANDBOX_IMAGE,
) -> SandboxResult:
    if not docker_available():
        return SandboxResult(
            exit_code=None,
            stdout="",
            stderr="",
            duration_ms=0,
            timeout=False,
            resource_failure=False,
            image=image,
            network="none",
            detail="docker_unavailable",
        )
    with tempfile.TemporaryDirectory(prefix="eos-eval-") as tmp:
        work = Path(tmp) / "input"
        shutil.copytree(tree, work, dirs_exist_ok=True)
        command = [
            "sudo",
            "-n",
            "docker",
            "run",
            "--rm",
            "--pull",
            "never",
            "--network",
            "none",
            "--user",
            "65534:65534",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=64m",
            "--tmpfs",
            "/work:rw,exec,nosuid,nodev,size=256m",
            "--mount",
            f"type=bind,src={work},dst=/input,ro=true",
            "-w",
            "/work",
            "--memory",
            memory,
            "--memory-swap",
            memory,
            "--cpus",
            cpus,
            "--pids-limit",
            str(pids),
            "--security-opt",
            "no-new-privileges",
            "--cap-drop",
            "ALL",
            "--env",
            "PATH=/usr/local/bin:/usr/bin:/bin",
            "--env",
            "HOME=/tmp",
            "--env",
            "LANG=C",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--env",
            "PYTHONPATH=/work",
            image,
            "sh",
            "-c",
            'cp -a /input/. /work/ && exec "$@"',
            "sh",
            *argv,
        ]
        started = time.monotonic()
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                timeout=timeout_seconds + 15,
            )
            duration = int((time.monotonic() - started) * 1000)
            stdout = _bound(process.stdout)
            stderr = _bound(process.stderr)
            timeout = process.returncode in {124, 137}
            resource = process.returncode in {137, 139} or "MemoryError" in stderr
            detail = None
            if process.returncode == 125 or (
                process.returncode not in {0, None}
                and (
                    "Unable to find image" in stderr
                    or "Unable to find a source image" in stderr
                    or "pull access denied" in stderr
                )
            ):
                detail = "sandbox_runner_failure"
            return SandboxResult(
                exit_code=process.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration,
                timeout=timeout,
                resource_failure=resource,
                image=image,
                network="none",
                detail=detail,
            )
        except subprocess.TimeoutExpired as exc:
            duration = int((time.monotonic() - started) * 1000)
            return SandboxResult(
                exit_code=None,
                stdout=_bound(exc.stdout or b""),
                stderr=_bound(exc.stderr or b""),
                duration_ms=duration,
                timeout=True,
                resource_failure=False,
                image=image,
                network="none",
                detail="host_timeout",
            )


def run_command(
    argv: list[str],
    tree: Path,
    timeout_seconds: int = 60,
    mode: str | None = None,
) -> SandboxResult:
    selected = mode or os.environ.get("EOS_EVAL_SANDBOX", "docker")
    if selected == "inline":
        return run_inline(argv, tree, timeout_seconds=timeout_seconds)
    return run_docker(argv, tree, timeout_seconds=timeout_seconds)
