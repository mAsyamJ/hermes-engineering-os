"""Lifecycle helpers — dirty flag + debounce to avoid regen loops."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from agent_os import REGISTRY_DIR

_LOCK = threading.Lock()
_DIRTY_PATH = REGISTRY_DIR / ".registry.dirty"
_LAST_REGEN_PATH = REGISTRY_DIR / ".last_regen"
_MIN_INTERVAL_S = 2.0


def mark_dirty(reason: str = "") -> None:
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"dirty": True, "reason": reason, "ts": time.time()}
    _DIRTY_PATH.write_text(json.dumps(payload), encoding="utf-8")


def is_dirty() -> bool:
    return _DIRTY_PATH.exists()


def regenerate_if_dirty(*, force: bool = False) -> dict | None:
    with _LOCK:
        if not force and not is_dirty():
            return None
        now = time.time()
        if _LAST_REGEN_PATH.exists():
            try:
                last = float(_LAST_REGEN_PATH.read_text().strip())
            except ValueError:
                last = 0.0
            if now - last < _MIN_INTERVAL_S and not force:
                return None
        # Import lazily to avoid circular imports at module load
        from agent_os.registry.generate import regenerate

        evidence = regenerate(write_hermes_projection=True)
        _LAST_REGEN_PATH.write_text(str(now), encoding="utf-8")
        if _DIRTY_PATH.exists():
            _DIRTY_PATH.unlink()
        return evidence
