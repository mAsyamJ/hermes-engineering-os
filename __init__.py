"""Hermes Engineering OS combined plugin entry point."""

from __future__ import annotations

from typing import Any


def register(ctx: Any) -> None:
    """Keep gateway registration side-effect free.

    Phase 1 functionality is dashboard-side and read-only. The function exists
    so Hermes can validate the plugin without changing hooks, tools, commands,
    workers, schedules, or lifecycle ownership.
    """

    return None

