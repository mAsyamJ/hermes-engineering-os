"""Atomic candidate-slot reservation. Lives inside the protected authority."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

_MEMORY_LOCK = threading.Lock()
_MEMORY: dict[str, list[str]] = {}


def _key(policy_hash: str, approval_id: str) -> str:
    return f"{policy_hash}\0{approval_id}"


def reserve_memory(
    *,
    policy_hash: str,
    approval_id: str,
    unit_id: str,
    maximum_exposure: int = 1,
) -> dict[str, Any]:
    """In-process CAS for tests. No refund."""
    if maximum_exposure < 1:
        return {"ok": False, "reserved": False, "reason": "invalid maximum_exposure"}
    with _MEMORY_LOCK:
        slot = _MEMORY.setdefault(_key(policy_hash, approval_id), [])
        if unit_id in slot:
            return {"ok": True, "reserved": True, "reason": "already_reserved", "index": slot.index(unit_id)}
        if len(slot) >= maximum_exposure:
            return {"ok": False, "reserved": False, "reason": "EXPOSURE_EXHAUSTED", "consumed": len(slot)}
        slot.append(unit_id)
        return {"ok": True, "reserved": True, "reason": "RESERVED", "index": len(slot) - 1, "consumed": len(slot)}


def consumed_memory(policy_hash: str, approval_id: str) -> int:
    with _MEMORY_LOCK:
        return len(_MEMORY.get(_key(policy_hash, approval_id), []))


def reset_memory() -> None:
    with _MEMORY_LOCK:
        _MEMORY.clear()


def reserve_sqlite(
    path: Path,
    *,
    policy_hash: str,
    approval_id: str,
    unit_id: str,
    maximum_exposure: int = 1,
) -> dict[str, Any]:
    """File-backed CAS using a unique slot index. No automatic refund."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5, isolation_level="IMMEDIATE")
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reservations (
                policy_hash TEXT NOT NULL,
                approval_id TEXT NOT NULL,
                slot_index INTEGER NOT NULL,
                unit_id TEXT NOT NULL,
                reserved_at REAL NOT NULL,
                PRIMARY KEY (policy_hash, approval_id, slot_index)
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS reservations_unit
            ON reservations (policy_hash, approval_id, unit_id)
            """
        )
        existing = conn.execute(
            """
            SELECT slot_index FROM reservations
            WHERE policy_hash=? AND approval_id=? AND unit_id=?
            """,
            (policy_hash, approval_id, unit_id),
        ).fetchone()
        if existing:
            return {"ok": True, "reserved": True, "reason": "already_reserved", "index": existing[0]}
        used = conn.execute(
            """
            SELECT COUNT(*) FROM reservations WHERE policy_hash=? AND approval_id=?
            """,
            (policy_hash, approval_id),
        ).fetchone()[0]
        if used >= maximum_exposure:
            return {"ok": False, "reserved": False, "reason": "EXPOSURE_EXHAUSTED", "consumed": used}
        try:
            conn.execute(
                """
                INSERT INTO reservations (policy_hash, approval_id, slot_index, unit_id, reserved_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (policy_hash, approval_id, used, unit_id, time.time()),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            return {"ok": False, "reserved": False, "reason": "EXPOSURE_EXHAUSTED"}
        return {"ok": True, "reserved": True, "reason": "RESERVED", "index": used, "consumed": used + 1}
    finally:
        conn.close()
