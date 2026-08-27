"""Read-only access to the canonical Hermes Kanban database."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from hermes_cli import kanban_db

_DENIED = {
    sqlite3.SQLITE_INSERT,
    sqlite3.SQLITE_UPDATE,
    sqlite3.SQLITE_DELETE,
    sqlite3.SQLITE_CREATE_INDEX,
    sqlite3.SQLITE_CREATE_TABLE,
    sqlite3.SQLITE_CREATE_TEMP_INDEX,
    sqlite3.SQLITE_CREATE_TEMP_TABLE,
    sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
    sqlite3.SQLITE_CREATE_TEMP_VIEW,
    sqlite3.SQLITE_CREATE_TRIGGER,
    sqlite3.SQLITE_CREATE_VIEW,
    sqlite3.SQLITE_DROP_INDEX,
    sqlite3.SQLITE_DROP_TABLE,
    sqlite3.SQLITE_DROP_TEMP_INDEX,
    sqlite3.SQLITE_DROP_TEMP_TABLE,
    sqlite3.SQLITE_DROP_TEMP_TRIGGER,
    sqlite3.SQLITE_DROP_TEMP_VIEW,
    sqlite3.SQLITE_DROP_TRIGGER,
    sqlite3.SQLITE_DROP_VIEW,
    sqlite3.SQLITE_ALTER_TABLE,
    sqlite3.SQLITE_ATTACH,
    sqlite3.SQLITE_DETACH,
    sqlite3.SQLITE_PRAGMA,
    sqlite3.SQLITE_REINDEX,
    sqlite3.SQLITE_TRANSACTION,
}


def _authorizer(action: int, _arg1: str, _arg2: str, _db: str, _trigger: str) -> int:
    return sqlite3.SQLITE_DENY if action in _DENIED else sqlite3.SQLITE_OK


def database_path(board: str | None = None) -> Path:
    return kanban_db.kanban_db_path(board=board).resolve()


def connect_read_only(path: Path | None = None, board: str | None = None) -> sqlite3.Connection:
    target = (path or database_path(board)).resolve()
    if not target.is_file():
        raise FileNotFoundError(target)
    connection = sqlite3.connect(
        f"file:{target.as_posix()}?mode=ro",
        uri=True,
        timeout=2.0,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    connection.set_authorizer(_authorizer)
    return connection


def _decode_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _rows(connection: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    result = []
    for row in connection.execute(sql, params).fetchall():
        item = dict(row)
        for key in ("payload", "metadata", "skills"):
            if key in item:
                item[key] = _decode_json(item[key])
        result.append(item)
    return result


def list_tasks(limit: int = 200, board: str | None = None) -> list[dict[str, Any]]:
    with connect_read_only(board=board) as connection:
        return _rows(
            connection,
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        )


def get_task(task_id: str, board: str | None = None) -> dict[str, Any] | None:
    with connect_read_only(board=board) as connection:
        rows = _rows(connection, "SELECT * FROM tasks WHERE id = ?", (task_id,))
        if not rows:
            return None
        task = rows[0]
        task["runs"] = _rows(
            connection,
            "SELECT * FROM task_runs WHERE task_id = ? ORDER BY started_at DESC LIMIT 100",
            (task_id,),
        )
        task["events"] = _rows(
            connection,
            "SELECT * FROM task_events WHERE task_id = ? ORDER BY id DESC LIMIT 300",
            (task_id,),
        )
        return task


def list_runs(limit: int = 200, board: str | None = None) -> list[dict[str, Any]]:
    with connect_read_only(board=board) as connection:
        return _rows(
            connection,
            "SELECT * FROM task_runs ORDER BY started_at DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        )


def get_run(run_id: int, board: str | None = None) -> dict[str, Any] | None:
    with connect_read_only(board=board) as connection:
        rows = _rows(connection, "SELECT * FROM task_runs WHERE id = ?", (run_id,))
        if not rows:
            return None
        run = rows[0]
        run["events"] = _rows(
            connection,
            "SELECT * FROM task_events WHERE run_id = ? ORDER BY id LIMIT 500",
            (run_id,),
        )
        return run


def summary(board: str | None = None) -> dict[str, Any]:
    path = database_path(board)
    with connect_read_only(path) as connection:
        statuses = {
            row["status"]: row["count"]
            for row in connection.execute(
                "SELECT status, COUNT(*) AS count FROM tasks GROUP BY status"
            ).fetchall()
        }
        run_statuses = {
            row["status"]: row["count"]
            for row in connection.execute(
                "SELECT status, COUNT(*) AS count FROM task_runs GROUP BY status"
            ).fetchall()
        }
    return {
        "board": board or kanban_db.get_current_board(),
        "database": str(path),
        "tasks_by_status": statuses,
        "runs_by_status": run_statuses,
    }

