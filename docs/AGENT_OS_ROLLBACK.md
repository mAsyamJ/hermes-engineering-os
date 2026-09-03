# Agent OS Rollback

## Disable without destroying Hermes

```bash
./scripts/rollback-agent-os.sh
# optional: ./scripts/rollback-agent-os.sh --remove-symlink
```

This:

1. `hermes plugins disable agent-os-router`
2. Removes generated `~/.hermes/SKILLS.md` (backed up under `/var/backups/...`)
3. Leaves native `skills/`, sessions, memories, databases, cron, profiles, auth, Engineering OS plugin intact

## Re-enable

```bash
./scripts/install-agent-os-plugin.sh
```

## Config keys introduced

- `plugins.enabled` includes `agent-os-router`
- `skills.guard_agent_created: true`

Restore prior config from Phase 0 / plugin-install backups under `/var/backups/hermes-engineering-os/` if needed (`cp` YAML only; do not raw-copy live SQLite).
