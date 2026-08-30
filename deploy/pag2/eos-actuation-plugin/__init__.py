"""Protected actuation plugin. Imports the IPC client from the H1 TCB tree."""

from __future__ import annotations

from typing import Any


def register(ctx: Any) -> None:
    from engineering_os.adaptation.hermes_plugin import register as register_ipc

    register_ipc(ctx)
