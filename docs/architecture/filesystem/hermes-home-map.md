# HERMES_HOME Map

**Home:** `/home/ubuntu/.hermes`
**Hermes:** v0.20.0
**Generated:** 2026-09-03T08:16:29Z (Phase 1 inventory; no moves executed)

Principle: upstream compatibility is the norm. Only OUR unnecessary root clutter is a relocation candidate.
Cross-check: [HERMES_HOME_AUTHORITY_MAP.md](HERMES_HOME_AUTHORITY_MAP.md) (operational authority).

| Path | Purpose | Owner | Writer | Reader | Lifecycle | Fixed? | Safe relocate? | Proposed path | Mechanism | Class |
|---|---|---|---|---|---|---|---|---|---|---|
| `.clean_shutdown` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `.codex_gpt55_autoraise_notice` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `.env` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `.env.before-codex` | Historical config/env backup | hermes | hermes config | operator | none | no | yes-with-proof | `~/.hermes/backups/config/.env.before-codex` | UPDATE_CONSUMERS_NONE_THEN_MOVE | B |
| `.mcp-discovery.lock` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `.scratch_tip_shown` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `.update_check` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `SKILLS.md` | Generated Agent OS capability manifest projected into Hermes-required location | agent_os | agent_os.generate | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `SOUL.md` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `audio_cache` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `audit` | Operator/Engineering audit scraps | ENGINEERING_OS | operator/hermes | operator | low | no | yes-with-proof | `~/.hermes/extensions/audit` | UPDATE_CONSUMERS_THEN_MOVE | B |
| `auth.json` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `auth.lock` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `bin` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `cache` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `channel_directory.json` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `config.yaml` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `config.yaml.bak.20260811_140009` | Historical config/env backup | hermes | hermes config | operator | none | no | yes-with-proof | `~/.hermes/backups/config/config.yaml.bak.20260811_140009` | UPDATE_CONSUMERS_NONE_THEN_MOVE | B |
| `config.yaml.bak.20260817_101559` | Historical config/env backup | hermes | hermes config | operator | none | no | yes-with-proof | `~/.hermes/backups/config/config.yaml.bak.20260817_101559` | UPDATE_CONSUMERS_NONE_THEN_MOVE | B |
| `config.yaml.bak.20260817_101633` | Historical config/env backup | hermes | hermes config | operator | none | no | yes-with-proof | `~/.hermes/backups/config/config.yaml.bak.20260817_101633` | UPDATE_CONSUMERS_NONE_THEN_MOVE | B |
| `config.yaml.before-codex` | Historical config/env backup | hermes | hermes config | operator | none | no | yes-with-proof | `~/.hermes/backups/config/config.yaml.before-codex` | UPDATE_CONSUMERS_NONE_THEN_MOVE | B |
| `config.yaml.cbm-yaml.lock` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `context_length_cache.yaml` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `cron` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | high | yes | no | `—` | KEEP_FIXED | A |
| `dashboard.log` | Root-level log; candidate to nest under logs/ after writer proof | hermes | operator/hermes | operator | low | conditional | investigate | `~/.hermes/logs/dashboard.log` | INVESTIGATE_WRITER_THEN_CONFIG_OR_KEEP | C |
| `gateway` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | high | yes | no | `—` | KEEP_FIXED | A |
| `gateway-starts.log` | Root-level log; candidate to nest under logs/ after writer proof | hermes | operator/hermes | operator | low | conditional | investigate | `~/.hermes/logs/gateway-starts.log` | INVESTIGATE_WRITER_THEN_CONFIG_OR_KEEP | C |
| `gateway.lock` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `gateway_state.json` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `hermes-agent` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `hermes_otel.yaml` | Configurable but currently root-canonical durable path | hermes_otel | operator | hermes_otel plugin, engineering_os | medium | yes | no | `—` | KEEP_FIXED | A |
| `hooks` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `image_cache` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `kanban` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `kanban.db` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | high | yes | no | `—` | KEEP_FIXED | A |
| `kanban.db.dispatch.lock` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `kanban.db.init.lock` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `logs` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `lsp` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `memories` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `models_dev_cache.json` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `node` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `ollama_cloud_models_cache.json` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `pairing` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `pending` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `pending_messages` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `platforms` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `plugins` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `profiles` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `projects.db` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | high | yes | no | `—` | KEEP_FIXED | A |
| `provider_models_cache.json` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `sandboxes` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `scripts` | Operator local scripts (retropick); not Hermes core | USER | operator/hermes | operator | low | no | yes-with-proof | `~/.hermes/extensions/operator-scripts` | UPDATE_CONSUMERS_THEN_MOVE | B |
| `sessions` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | high | yes | no | `—` | KEEP_FIXED | A |
| `skill-bundles` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `skills` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `state` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `state.db` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | high | yes | no | `—` | KEEP_FIXED | A |
| `state.db-shm` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | high | yes | no | `—` | KEEP_FIXED | A |
| `state.db-wal` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | high | yes | no | `—` | KEEP_FIXED | A |
| `tui-theme-boot.json` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |
| `verification_evidence.db` | Configurable but currently root-canonical durable path | hermes | operator | verify | medium | yes | no | `—` | KEEP_FIXED | A |
| `web-ui-build-stamp.json` | Hermes upstream-required or canonical runtime path | hermes | hermes-runtime | hermes-runtime, dashboard, plugins | medium | yes | no | `—` | KEEP_FIXED | A |

## Summary

- Class A (keep): **54**
- Class B (relocatable after proof): **7**
- Class C (compatibility-bound / investigate): **2**

## SQLite policy

All root SQLite databases (`state.db`, `kanban.db`, `projects.db`, `verification_evidence.db`) and WAL/SHM siblings remain at their current paths. Do not symlink. Integrity at baseline: ok / wal.

## OTel note

`hermes_otel.yaml` defaults to `$HERMES_HOME/hermes_otel.yaml` (`DURABLE_CONFIG_PATH`) with override `HERMES_OTEL_CONFIG`. Phase 1 classification: **KEEP_ROOT** until every consumer sets the env.


## Apply updates (post Phase 1)

Executed Class-B moves:

| Old | New | Status |
|---|---|---|
| `config.yaml.bak.*` / `config.yaml.before-codex` / `.env.before-codex` | `~/.hermes/backups/config/` | moved |
| `audit/` | `~/.hermes/extensions/audit/` | moved |

Deliberately **not** moved (KEEP_ROOT): `dashboard.log`, `gateway-starts.log` (Hermes writer), `scripts/` (Hermes cron/scripts contract), `hermes_otel.yaml`, all SQLite DBs.
