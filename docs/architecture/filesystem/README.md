# Filesystem Architecture

Phase 1 freeze artifacts for Hermes Engineering OS filesystem normalization.

| Document | Purpose |
|---|---|
| [root-contract.md](root-contract.md) | HERMES_HOME + repository root contracts |
| [repository-layout.md](repository-layout.md) | Target repository layout (adapted to live modules) |
| [hermes-home-map.md](hermes-home-map.md) | Per-entry `$HERMES_HOME` ownership + migration class |
| [HERMES_HOME_AUTHORITY_MAP.md](HERMES_HOME_AUTHORITY_MAP.md) | Existing operational authority map (still at flat docs path until apply) |

Control plane: `/opt/hermes-engineering-os/migration/` (inventory, dependency graph, manifests).

**No file moves have been executed in Phase 0–1.**
