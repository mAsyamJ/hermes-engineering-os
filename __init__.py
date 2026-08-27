"""Hermes Engineering OS combined plugin entry point."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def register(ctx: Any) -> None:
    """Dashboard plugin; optionally stamps Kanban identity onto OTel.

    No hooks, commands, or skills unless a dispatcher-spawned worker already
    has HERMES_KANBAN_* in the environment. In that case the explicit values
    are merged into OTEL_RESOURCE_ATTRIBUTES before hermes_otel initializes,
    and fail-open post_* attributes are registered as a second belt. Missing
    Kanban env (including preflight) stays side-effect-free.
    """
    try:
        from engineering_os.observability.correlation import apply_kanban_resource_attributes
        from engineering_os.observability.span_stamp import register_fail_open_stamps

        stamped = apply_kanban_resource_attributes()
        if stamped:
            register_fail_open_stamps(ctx, stamped)
    except Exception:
        return None
    return None
