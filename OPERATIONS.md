# Operations

## Services and ports

| Component | Port | Ownership |
|---|---:|---|
| Hermes dashboard and Engineering OS | `127.0.0.1:9119` | existing user service |
| Default Hermes gateway | existing configuration | no-touch |
| `rp-friend` gateway/dispatcher | existing configuration | no-touch |

Phase 1 adds no listener, daemon, container, PostgreSQL instance, or Phoenix
service.

## Health

```bash
./scripts/dashboard-request.py /api/plugins/engineering-os/health
systemctl --user status hermes-dashboard.service
```

The live dashboard should show GitHub API as `BLOCKED_AUTH` until `gh` is
authenticated. Observability should show dependency-degraded, fail-open status
until the existing OTel plugin is repaired in Phase 2.

## Capacity

Keep root usage below 75%, free space at or above 25 GiB, and the complete
product/upstream/build/browser footprint below 1 GiB. Upstream clones,
`node_modules`, browser binaries, and runtime fixtures are ignored and can be
recreated.

## Backups

Plugin mutations create `0700` timestamped directories under
`/var/backups/hermes-engineering-os`. They contain config, plugin state,
service PIDs, symlink state, and checksums. The Phase 0 checkpoint remains
`/var/backups/hermes-engineering-os/20260827T120255Z`.

