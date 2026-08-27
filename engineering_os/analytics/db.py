"""Postgres helpers for derived analytics. Lazy-import psycopg."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

from engineering_os.analytics import ADVISORY_LOCK_KEY


def database_url(role: str = "default") -> str:
    if role == "migrate":
        url = os.environ.get("ANALYTICS_MIGRATE_DSN") or os.environ.get("ANALYTICS_DATABASE_URL")
    else:
        url = os.environ.get("ANALYTICS_DATABASE_URL")
    if not url:
        raise RuntimeError("ANALYTICS_DATABASE_URL is not set")
    return url


def _psycopg():
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row


@contextmanager
def connect(url: str | None = None, autocommit: bool = False) -> Iterator[Any]:
    psycopg, dict_row = _psycopg()
    connection = psycopg.connect(url or database_url(), row_factory=dict_row, autocommit=autocommit)
    try:
        yield connection
    finally:
        connection.close()


def try_advisory_lock(connection: Any, key: int = ADVISORY_LOCK_KEY) -> bool:
    row = connection.execute("SELECT pg_try_advisory_lock(%s) AS locked", (key,)).fetchone()
    return bool(row and row["locked"])


def advisory_unlock(connection: Any, key: int = ADVISORY_LOCK_KEY) -> None:
    connection.execute("SELECT pg_advisory_unlock(%s)", (key,))


def fetch_all(connection: Any, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return list(connection.execute(sql, params).fetchall())


def fetch_one(connection: Any, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    return connection.execute(sql, params).fetchone()
