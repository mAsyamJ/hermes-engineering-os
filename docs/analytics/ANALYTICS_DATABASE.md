# Analytics Database

Derived store only. Canonical task truth remains Hermes Kanban SQLite.

## Location

- Server: existing `hermes-eos-postgres` (Postgres 16.15), no host port
- Database: `hermes_engineering`
- Phoenix database: untouched (`phoenix`, 65 user tables)

## Chosen connectivity

**Architecture B:** analytics processes run on Docker network `hermes-eos-observability`.

- `hermes-eos-analytics-api` listens on `127.0.0.1:9120` (GET-only)
- One-shot `analytics-materialize` profile uses the writer DSN
- Postgres remains unpublished on the host

Rejected:

- Publishing Postgres on `0.0.0.0`
- Unix-socket bind-mount to the host (`local all all trust` would leak)
- Giving the dashboard `docker.sock`
- Installing `psycopg` into the Hermes venv
- Last-resort loopback `127.0.0.1:5435:5432` (not required; sidecar qualified)

## Roles

| Role | Use |
|---|---|
| `hermes_engineering` | owner / migrations |
| `hermes_engineering_writer` | materializer DML, no DDL, no CONNECT to `phoenix` |
| `hermes_engineering_reader` | SELECT only; dashboard sidecar |
| `eos_admin` | bootstrap superuser, never used at analytics runtime |

Passwords live in `deploy/observability/.env` mode `0600` and are not committed.

## Schema

Versioned SQL in `migrations/analytics/`. Apply with `scripts/analytics/analytics-migrate.sh`.
Re-run is safe (`IF NOT EXISTS` + `schema_migrations`).

## Rollback

Stop the sidecar and timer. `DROP SCHEMA public CASCADE` on `hermes_engineering` only as last resort. Restore from `pg_dump`. Never drop `phoenix`.
