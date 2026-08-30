"""Adaptation runtime paths. Protected TCB is never a write target."""

from __future__ import annotations

import os
from pathlib import Path

PROTECTED_TCB = Path("/usr/local/lib/hermes-eos")
ACTUATOR_STATE_DIR = Path("/var/lib/hermes-actuator")
ACTUATOR_ADAPTATION = ACTUATOR_STATE_DIR / "adaptation"
REPO_ADAPTATION = Path(".runtime") / "adaptation"


def package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def is_protected_tcb(root: Path | None = None) -> bool:
    target = (root or package_root()).resolve()
    return target == PROTECTED_TCB or str(target).startswith(str(PROTECTED_TCB) + "/")


def under_protected_tcb(path: Path) -> bool:
    text = os.path.normpath(os.fspath(path))
    tcb = str(PROTECTED_TCB)
    return text == tcb or text.startswith(tcb + "/")


def adaptation_runtime_dir(*, create: bool = True) -> Path:
    """Mutable adaptation state. Never create or return a TCB path."""
    env = os.environ.get("EOS_ADAPTATION_RUNTIME")
    if env:
        path = Path(env)
    elif os.environ.get("HERMES_EOS_ACTUATOR_RUNTIME"):
        path = Path(os.environ["HERMES_EOS_ACTUATOR_RUNTIME"])
    elif os.environ.get("HERMES_EOS_ACTUATOR_STATE"):
        path = Path(os.environ["HERMES_EOS_ACTUATOR_STATE"]).resolve().parent / "adaptation"
    elif is_protected_tcb():
        path = ACTUATOR_ADAPTATION
    else:
        path = package_root() / REPO_ADAPTATION
    if under_protected_tcb(path):
        path = ACTUATOR_ADAPTATION
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path
