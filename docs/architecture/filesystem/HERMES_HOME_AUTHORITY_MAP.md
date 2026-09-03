# HERMES_HOME Authority Map

**Home:** `/home/ubuntu/.hermes`  
**Principle:** This directory is Hermes **operating state**, not a git monorepo. Do not initialize git here. Do not reorganize for aesthetics.

Authority hierarchy for Hermes behavior: live filesystem → executed version → matching source → official docs → assumptions (forbidden when evidence exists).

| Path | Category | Owner | Purpose | Source of truth? | Persistent? | Manual mutate? | Safe delete? | Expected writer | Backup | Regeneration |
|---|---|---|---|---|---|---|---|---|---|---|
| `SOUL.md` | identity | operator / Hermes | Global persona | Yes (identity) | yes | careful | no | human / rare | copy+checksum | rewrite only with intent |
| `config.yaml` | canonical configuration | Hermes CLI | Runtime config | Yes | yes | via `hermes config` | no | hermes config / setup | timestamped copy | migrate/check |
| `config.yaml.bak.*` | backups | Hermes | Prior configs | historical | yes | no | retention policy only | hermes | already backups | n/a |
| `.env` | credentials | operator | Secrets | Yes | yes | careful | no | hermes auth / human | private only | re-auth |
| `auth.json` / `auth.lock` | credentials | Hermes | OAuth tokens | Yes | yes | no | no | hermes auth | never in git | re-auth |
| `hermes-agent/` | upstream source/runtime | Hermes install | Checkout + venv | Yes for code | yes | no (Agent OS) | no | hermes update | git | reinstall |
| `bin/` | upstream/runtime | install | Wrappers | derived | yes | no | no | install | n/a | reinstall |
| `skills/` | procedural memory | Hermes | Native skill SoT | **Yes** | yes | via hub/skill_manage | per-skill | hermes skills / agent | hub lock + files | reinstall/hub |
| `skills/.hub/` | extensions + provenance | Hermes hub | lock/taps/quarantine | Yes for hub state | yes | no | quarantine only | hub | lock.json | hub repair |
| `skill-bundles/` | extensions | Hermes / Agent OS | Native bundles | Yes when present | yes | via `hermes bundles` | bundle YAML only | hermes bundles | copy YAML | regenerate |
| `plugins/` | extensions | operator | Plugin installs/symlinks | Yes | yes | careful | plugin-specific | hermes plugins | list --json | reinstall |
| `hooks/` | extensions | operator | Shell hooks | optional | yes | yes | yes if unused | human | copy | recreate |
| `profiles/` | orchestration isolation | Hermes | Per-bot homes | Yes per profile | yes | no concurrent writers | no | hermes profile | per-profile | recreate profile |
| `memories/` | procedural/user memory | Hermes | MEMORY/USER | Yes | yes | gated | no | memory tool | copy MD | none |
| `sessions/` | mutable persistent state | Hermes | Session transcripts | Yes | yes | no | no | runtime | rare | none |
| `cron/` | orchestration | Hermes | Jobs + DBs | Yes | yes | careful | no | cron/gateway | jobs.json copy; sqlite `.backup` | recreate jobs |
| `gateway*` / `gateway/` | orchestration | Hermes | Gateway lock/state | Yes | yes | no | no | gateway | state json copy | restart (operator) |
| `kanban*` / `kanban/` | orchestration | Hermes | Task lifecycle | **Yes** | yes | no | no | kanban/dispatcher | sqlite `.backup` | none |
| `projects.db*` | mutable persistent state | Hermes | Projects | Yes | yes | no | no | Hermes | sqlite `.backup` | none |
| `state.db*` | mutable persistent state | Hermes | Runtime state | Yes | yes | no | no | Hermes | sqlite `.backup` | none |
| `verification_evidence.db*` | observability/evidence | Hermes / verify | Verification store | Yes | yes | no | no | verify tools | sqlite `.backup` | none |
| `hermes_otel.yaml` | observability | operator | OTel plugin config | Yes | yes | careful | no | human | copy | rewrite |
| `audit/` | observability | operator | Audit scraps | derived | yes | yes | retention | human/tools | optional | regenerate |
| `logs/` / `dashboard.log` | observability | Hermes | Logs | derived | yes | no | retention | runtime | optional | rotate |
| `cache/` / `audio_cache/` / `image_cache/` | caches/derived | Hermes | Media/cache | no | derived | no | yes if cold | runtime | no | regenerate |
| `*_models*_cache.json` / `models_dev_cache.json` | caches/derived | Hermes | Model catalogs | no | derived | no | yes | runtime | no | refresh |
| `context_length_cache.yaml` | caches/derived | Hermes | Context lengths | no | derived | no | yes | runtime | no | refresh |
| `pending/` / `pending_messages/` | mutable state | Hermes | Pending writes/msgs | Yes | yes | via approve cmds | after review | write_approval | careful | clear after process |
| `pairing/` / `platforms/` / `sandboxes/` / `lsp/` / `node/` | runtime support | Hermes | Platform/LSP/node | mixed | yes | no | carefully | runtime/install | rare | reinstall |
| `scripts/` | extensions | operator | Local scripts | local | yes | yes | yes | human | copy | recreate |
| `SKILLS.md` (Agent OS) | generated artifacts | Agent OS | Human capability manifest | **No** (projection) | regenerated | **do not hand-edit** | yes | agent_os generator | checksum | regenerate |
| `tui-theme-boot.json` / `web-ui-build-stamp.json` | derived | Hermes | UI stamps | no | derived | no | yes | UI | no | rebuild |

## Ownership model

- **Hermes runtime** owns sessions, skills loader, hub, bundles, profiles, Kanban, cron, auth.
- **Engineering OS** (`plugins/engineering-os`) is a read-only cockpit — not an orchestrator.
- **Agent OS** (`plugins/agent-os-router`) indexes and routes capabilities; it does **not** replace the native skill store or Kanban.
