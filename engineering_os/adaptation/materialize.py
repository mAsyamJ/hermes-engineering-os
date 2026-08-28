"""Incremental adaptation controller. Does not schedule Hermes tasks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from engineering_os.adaptation import ADVISORY_LOCK_KEY, CONTRACT_VERSION
from engineering_os.adaptation.db import advisory_unlock, connect, jsonb
from engineering_os.adaptation.persist import _lock, _refresh_cache
from engineering_os.adaptation.quality import run_checks


def run() -> dict[str, Any]:
    with connect() as connection:
        locked = _lock(connection)
        if locked:
            return locked
        started = datetime.now(timezone.utc)
        try:
            cache = _refresh_cache(connection)
            quality = run_checks(connection)
            connection.execute(
                """
                INSERT INTO adaptation_checkpoints (source, started_at, ended_at, status, detail)
                VALUES (%s, %s, NOW(), %s, %s)
                """,
                (
                    "timer",
                    started,
                    quality.get("status") or "success",
                    jsonb({"kill_switch": cache.get("kill_switch"), "quality": quality}),
                ),
            )
            connection.commit()
            return {
                "status": "success",
                "contract_version": CONTRACT_VERSION,
                "kill_switch": cache.get("kill_switch"),
                "quality": quality,
                "schedules_tasks": False,
            }
        finally:
            advisory_unlock(connection, ADVISORY_LOCK_KEY)


def main() -> int:
    import json

    print(json.dumps(run(), default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
