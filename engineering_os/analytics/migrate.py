"""Versioned SQL migrations for hermes_engineering."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from engineering_os.analytics.db import connect, database_url

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations" / "analytics"


def apply(url: str | None = None) -> dict[str, object]:
    applied: list[str] = []
    skipped: list[str] = []
    with connect(url or database_url("migrate")) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        connection.commit()
        existing = {
            row["version"]
            for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
        }
        for path in sorted(MIGRATIONS.glob("*.sql")):
            version = path.stem
            if version in existing:
                skipped.append(version)
                continue
            sql = path.read_text(encoding="utf-8")
            statements = [item.strip() for item in sql.split(";") if item.strip()]
            for statement in statements:
                body = "\n".join(
                    line for line in statement.splitlines() if not line.lstrip().startswith("--")
                ).strip()
                if not body:
                    continue
                connection.execute(body)
            connection.commit()
            existing.add(version)
            applied.append(version)
    return {"applied": applied, "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = apply()
    if args.json:
        print(json.dumps(result))
    else:
        print("applied", result["applied"], "skipped", result["skipped"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
