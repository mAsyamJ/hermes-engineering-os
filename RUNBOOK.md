# Runbook

## Verify

```bash
cd /opt/hermes-engineering-os
./scripts/verify.sh
```

## Install

The repository must be clean and all plugin checks must pass.

```bash
./scripts/install-plugin.sh
systemctl --user restart hermes-dashboard.service
./scripts/dashboard-request.py /api/plugins/engineering-os/health
```

Never restart either Hermes gateway.

## Rescan frontend manifests

```bash
./scripts/rescan-dashboard.sh
```

Rescan does not mount a new Python router. A first installation or backend file
change requires all-plugin preflight and a dashboard-only restart.

## Roll back

```bash
./scripts/uninstall-plugin.sh
systemctl --user restart hermes-dashboard.service
```

The uninstall script disables first, confirms the backend runtime gate is 404,
rescans, and unlinks only when the symlink resolves to this repository. Do not
run `hermes plugins remove engineering-os`.

## Observability stack

```bash
./scripts/start-observability.sh
./scripts/verify-observability.sh
./scripts/observability-db-backup.sh
./scripts/observability-db-verify.sh /var/backups/hermes-engineering-os/observability-<stamp>
./scripts/stop-observability.sh
```

Phoenix: `http://127.0.0.1:6006`. Never attach this compose project to RetroPick
networks or volumes. Restarting Phoenix or observability Postgres is allowed;
never restart either Hermes gateway for OTel.

## Analytics

```bash
./scripts/analytics-migrate.sh
./scripts/analytics-db-roles.sh
./scripts/analytics-materialize.sh --json
./scripts/analytics-explain.sh <task_id> [board]
./scripts/verify-analytics-data.sh
systemctl --user enable --now hermes-eos-analytics.timer
systemctl --user disable --now hermes-eos-analytics.timer
```

Analytics API: `http://127.0.0.1:9120` (loopback). Dashboard proxy:
`/api/plugins/engineering-os/analytics*`. Manual refresh is the materialize
script; disable the timer rather than the Kanban dispatcher.

## Evidence states

- `AVAILABLE`: authoritative read completed.
- `DEGRADED`: source failed or timed out; Hermes continues.
- `UNKNOWN`: explicit correlation evidence is absent.
- `BLOCKED_AUTH`: GitHub API credentials are unavailable or rejected.

