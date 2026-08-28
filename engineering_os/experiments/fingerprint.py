"""Privacy-safe environment fingerprints. No secrets, no hostname."""

from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Any

from engineering_os.evaluation import SANDBOX_IMAGE, SANDBOX_IMAGE_ID
from engineering_os.experiments.config_snapshot import snapshot


def hermes_identity() -> dict[str, Any]:
    agent = Path("/home/ubuntu/.hermes/hermes-agent")
    version = None
    source_sha = None
    pyproject = agent / "pyproject.toml"
    if pyproject.is_file():
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            if line.startswith("version"):
                version = line.split("=", 1)[-1].strip().strip("\"'")
                break
    git_head = agent / ".git" / "HEAD"
    if git_head.is_file():
        text = git_head.read_text(encoding="utf-8").strip()
        if text.startswith("ref:"):
            ref = agent / ".git" / text.split(" ", 1)[1].strip()
            if ref.is_file():
                source_sha = ref.read_text(encoding="utf-8").strip()
        else:
            source_sha = text
    return {"hermes_version": version, "hermes_source_sha": source_sha}


def environment_fingerprint() -> dict[str, Any]:
    parts = {
        "os": platform.system(),
        "kernel": platform.release(),
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "sandbox_image": SANDBOX_IMAGE,
        "sandbox_image_id": SANDBOX_IMAGE_ID,
        "hostname_omitted": True,
        "env_omitted": True,
        **hermes_identity(),
        "eval_sandbox_mode": os.environ.get("EOS_EVAL_SANDBOX", "docker"),
    }
    return snapshot(parts)
