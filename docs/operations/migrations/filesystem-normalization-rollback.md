# Filesystem Normalization — Rollback

**Scope:** Restore pre-normalization layout for `/opt/hermes-engineering-os` and selected `$HERMES_HOME` Class-B moves without destroying post-migration runtime writes.

## What rollback is not

`git reset --hard` alone is insufficient: `$HERMES_HOME` state, systemd user units, and plugin symlinks live outside Git.

## Materials

| Material | Location |
|---|---|
| Git checkpoint | local branch `checkpoint/pre-filesystem-normalization` @ baseline HEAD |
| Baseline evidence | `tests/evidence/layout-migration/baseline-20260903T081109Z/` |
| Manifest | `migration/filesystem-normalization.yaml` |
| Path map | `migration/path-map.yaml` |
| Hermes config backups | `~/.hermes/backups/config/` (moved artifacts; originals preserved there) |

## Repository rollback (code/docs/scripts)

1. Ensure no critical uncommitted secrets.
2. Create a safety tag/branch of current apply tip:
   `git branch backup/filesystem-normalization-applied`
3. Reset working tree to checkpoint **or** reverse `git mv` using `path-map.yaml` old←new for Class B/C repo paths.
4. Prefer reverse `git mv` when post-migration commits must be preserved selectively.
5. Restore plugin symlink if needed:
   `ln -sfn /opt/hermes-engineering-os/agent_os/plugin /home/ubuntu/.hermes/plugins/agent-os-router`
   (compat shim path) **or** keep canonical `agent_os/integrations/hermes/plugin` if only docs/scripts roll back.
6. Restore systemd `ExecStart` to previous `scripts/*.sh` paths from baseline unit dumps under evidence, then `systemctl --user daemon-reload`.

## HERMES_HOME rollback (Class-B only)

Moved items:

- `~/.hermes/backups/config/*` ← reverse to `~/.hermes/` root if operators require old names
- `~/.hermes/extensions/audit/` ← reverse to `~/.hermes/audit/`

Do **not** reverse Class A paths (`state.db`, `auth.json`, `kanban.db`, etc.).

### Databases

No SQLite databases were relocated. Rollback must not `mv` WAL/SHM siblings or invent DB symlinks.

If future DB moves occur: use SQLite `.backup` to a rollback snapshot before reverse; account for post-migration writes by merging or accepting forward-only data (document operator choice).

## Verification after rollback

```bash
bin/eos-layout-migrate --verify   # may fail intentionally if rolled back
bin/agent-os-verify
systemctl --user is-active hermes-dashboard
# SQLite integrity on Class A DBs
```

## Post-migration writes

Runtime data created after apply (sessions, SKILLS.md regenerations, cron executions) remains under Class A paths and must be preserved when rolling back only layout/docs/scripts.
