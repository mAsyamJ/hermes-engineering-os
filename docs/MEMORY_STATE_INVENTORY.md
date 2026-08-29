# Memory State Inventory

Primary homes:

- Default gateway: `/home/ubuntu/.hermes`
- rp-friend: `/home/ubuntu/.hermes/profiles/rp-friend`

| Role | Examples |
|---|---|
| Configuration | `config.yaml`, `SOUL.md`, `hermes_otel.yaml` |
| Memory | `memories/MEMORY.md`, `memories/USER.md` |
| Skills | `skills/` |
| Credentials | `.env`, `auth.json` (paths only; never snapshot) |
| Session | `state.db`, `sessions/` |
| Cache | `cache/`, `*_models_cache.json` |
| Logs | `logs/` |

Do not copy production memories. Do not install AgentMemory or Graphiti.
`codebase-memory-mcp` is an adjunct hook, not experiment memory.
