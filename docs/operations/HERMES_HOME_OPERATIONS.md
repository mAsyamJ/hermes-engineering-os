# HERMES_HOME Operations

This is not a cleanup guide. `ls ~/.hermes` looking busy is normal.

## Expected persistent paths

Identity/config: `SOUL.md`, `config.yaml`, `.env`, `auth.json`, `hermes_otel.yaml`  
State: `sessions/`, `memories/`, `state.db*`, `projects.db*`, `kanban.db*`, `verification_evidence.db*`, `cron/`  
Extensions: `skills/`, `plugins/`, `hooks/`, `profiles/`, `scripts/`  
Upstream: `hermes-agent/`

## Generated / projected

- `SKILLS.md` — Agent OS human projection of the machine registry. Regenerate; do not hand-edit.
- `skill-bundles/*.yaml` — native Hermes bundles (may be Agent-OS-emitted when skill IDs are proven).

## Caches (safe to clean when Hermes is idle)

`cache/`, `audio_cache/`, `image_cache/`, `*_models*_cache.json`, `models_dev_cache.json`, `context_length_cache.yaml`, profile-local caches.

Do **not** clean caches during architecture work unless diagnosing disk pressure.

## Logs / backups retention (recommendation only — not deleted in this goal)

- `config.yaml.bak.*`: keep latest 5; older are retention candidates.
- `logs/`, `dashboard.log`, `gateway-starts.log`: rotate/retain; do not wipe blindly.
- `/var/backups/hermes-engineering-os/`: keep Phase 0 / plugin install backups with `SHA256SUMS`.

## Never delete / never raw-cp

- Live `*.db` + `*-wal` + `*-shm` while processes may hold them.
- `auth.json`, `.env`, profile credentials.
- Profile directories while workers might run.

For DB snapshots: `sqlite3 <db> ".backup '<dest>'"`.

## Agent OS disable without losing Hermes

1. `hermes plugins disable agent-os-router`
2. Optionally remove generated `~/.hermes/SKILLS.md` and Agent-OS-emitted bundles only.
3. Leave `skills/`, sessions, memories, databases, Engineering OS plugin intact.

See [AGENT_OS_ROLLBACK.md](../agent-os/operations/AGENT_OS_ROLLBACK.md).
