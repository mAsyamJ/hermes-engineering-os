# Operations

## Services and ports

| Component | Port | Ownership |
|---|---:|---|
| Hermes dashboard and Engineering OS | `127.0.0.1:9119` | existing user service |
| Default Hermes gateway | existing configuration | no-touch |
| `rp-friend` gateway/dispatcher | existing configuration | no-touch |
| Phoenix UI + OTLP HTTP | `127.0.0.1:6006` | `hermes-eos-phoenix` |
| Analytics API | `127.0.0.1:9120` | `hermes-eos-analytics-api` |
| Observability PostgreSQL | none on host | `hermes-eos-postgres` |

Phase 2 added the isolated `hermes-eos-*` containers, network, and volume.
Phase 4 adds sandboxed evaluation on the same unpublished Postgres, a GET-only
`/evaluations*` API, and `hermes-eos-evaluate.timer`. Phase 5 adds observational
performance intelligence (`phase5-perf-v1`), GET-only `/performance*`, and
`hermes-eos-performance.timer`.

## Health

```bash
./scripts/dashboard-request.py /api/plugins/engineering-os/health
systemctl --user status hermes-dashboard.service
```

The live dashboard should show GitHub API as `BLOCKED_AUTH` until `gh` is
authenticated. Observability should show Phoenix/Postgres `HEALTHY` when the
dedicated stack is up, and `DEGRADED` when it is not. Hermes itself must keep
running.

## Capacity

Keep root usage below 80%, free space at or above 20 GiB. If free space drops
under 20 GiB, block further analytics backfills. Phoenix default retention
should stay operator-controlled; do not enable destructive auto-delete until
the Phoenix-supported mechanism is proven.

## Backups

Observability dumps are owner-only `pg_dump` files under
`/var/backups/hermes-engineering-os/observability-*` (`phoenix.sql` and
`hermes_engineering.sql`). Restore is proven only against an isolated
throwaway container via `scripts/observability-db-verify.sh`, never onto the
live volume. Derived analytics can also be rebuilt with
`scripts/analytics-materialize.sh --backfill --recompute`.

