# Filesystem Root Contracts

**Status:** Phase 1 architecture freeze (no moves executed)
**Authoritative inputs:** live `~/.hermes`, `/opt/hermes-engineering-os`, Hermes Agent v0.20.0, systemd user units, `migration/path-inventory.json`

Correctness beats aesthetics. A remaining root entry is acceptable when it is part of an actual runtime or public contract.

---

## A. HERMES_HOME Root Contract

**Home:** `/home/ubuntu/.hermes` (default when `HERMES_HOME` unset)

### Goal

Keep the root as small as possible **without** violating Hermes. Do not create fake cleanliness by relocating upstream-owned state behind fragile symlinks.

### Allowed at root

1. **Canonical Hermes-required files** resolved via `get_hermes_home()` / helpers in `hermes_constants.py`, including at minimum:
   - `config.yaml`, `.env`
   - `auth.json`, `auth.lock`
   - `SOUL.md`
   - `state.db` (+ `-wal`/`-shm`)
   - `channel_directory.json`
2. **Canonical Hermes-required directories**, including:
   - `hermes-agent/`, `skills/`, `skill-bundles/`, `plugins/`, `profiles/`
   - `sessions/`, `memories/`, `cron/`, `hooks/`
   - `gateway/`, `kanban/`, `logs/`, `cache/`, `state/`
   - `pairing/`, `platforms/`, `sandboxes/`, `lsp/`, `node/`
   - `pending/`, `pending_messages/`, `bin/`, media caches
3. **Intentional global documents / projections Hermes or Agent OS write at root:**
   - `SOUL.md`
   - `SKILLS.md` (Agent OS generated projection into Hermes-visible location)
4. **Upstream-default durable configs that live at root today:**
   - `hermes_otel.yaml` (override: `HERMES_OTEL_CONFIG`)
   - `kanban.db*`, `projects.db*`, `verification_evidence.db*`
   - gateway lock/state files, model catalog caches, UI stamps
5. **Unavoidable runtime contracts** (locks, heartbeats, shutdown markers)

### Not a reason to move

- “`ls` looks busy”
- Desire for nested `state/state/` or `cache/cache/`
- Cosmetic alignment with Engineering OS repo layout

### May relocate only after Class B proof

Operator/Engineering extensions that do **not** need a root path, for example:

- `config.yaml.bak.*`, `config.yaml.before-codex`, `.env.before-codex` → proposed `~/.hermes/backups/config/`
- `audit/` → proposed `~/.hermes/extensions/audit/`
- `scripts/` (operator retropick helpers) → proposed `~/.hermes/extensions/operator-scripts/`
- Root logs (`dashboard.log`, `gateway-starts.log`) → only after writer path proof; prefer nest under existing `logs/` **or KEEP_ROOT**

### Forbidden techniques for Hermes state

- Symlinking live SQLite DBs, WAL/SHM, locks, sockets, auth files
- Patching Hermes core to achieve prettier `ls`
- Moving `state.db`, `auth.json`, or `skills/` for aesthetics

### Ontology rule

Reuse Hermes’ existing directories (`state/`, `cache/`, `logs/`, `plugins/`) before inventing parallel trees. Avoid `state/state/`, `runtime/runtime/`, `cache/cache/`.

Full per-entry map: [hermes-home-map.md](hermes-home-map.md).

---

## B. Engineering OS Repository Root Contract

**Repository:** `/opt/hermes-engineering-os`

### Goal

Root is intentionally sparse. Semantic subdirectories are the norm; root files are exceptional public contracts.

### Allowed root files

| Entry | Role |
|---|---|
| `README.md` | Concise entry; links to `docs/reports/agent-os/README.md` |
| `AGENTS.md` | Agent/operator hard rules |
| `ARCHITECTURE.md` | High-level system architecture entrypoint |
| `SECURITY.md` | Security contract |
| `DECISIONS.md` | Decision log (root entrypoint; detailed ADRs under docs) |
| `OPERATIONS.md` / `RUNBOOK.md` / `TESTING.md` / `UPGRADE.md` | High-level ops entrypoints (detail under `docs/operations/`) |
| `LICENSE` | If/when present |
| `CHANGELOG.md` / `CONTRIBUTING.md` | If/when present |
| `.gitignore`, `.env.example` | Tooling / secrets hygiene |
| `pyproject.toml`, `uv.lock` | Python project + lock |
| `plugin.yaml` | **Required** at repo root: Hermes loads `engineering-os` from plugin home = repo root |
| `__init__.py` | Combined plugin `register()` for engineering-os |

### Allowed root directories (live-adapted)

| Directory | Role |
|---|---|
| `agent_os/` | Agent OS capability control plane |
| `engineering_os/` | Core EOS Python package |
| `integrations/` | External adapters |
| `dashboard/` | Dashboard plugin + UI |
| `deploy/` | systemd/compose/PAG units |
| `migrations/` | **SQL** migrations (analytics/control) |
| `migration/` | **Filesystem IA** control plane (inventory, manifests) — singular, distinct from SQL |
| `config/` | Scope/repository YAML |
| `experiments/` | Experiment definitions |
| `policies/` | Adaptation policies |
| `patches/` | Upstream patches |
| `provenance/` | Vendor/upstream lock notices |
| `requirements/` | Pin constraints |
| `vendor/` | Vendored bases |
| `upstream/` | Pinned upstream clones |
| `evidence/` | Historical phase evidence (not source) |
| `scripts/` | Implementation scripts (categorized after migration) |
| `bin/` | Stable operator entrypoints (created in apply phase) |
| `tests/` | Tests + evidence |
| `docs/` | Categorized documentation |

Do **not** manufacture empty domains (`analytics/`, `evaluation/`, `adaptation/` at repo root) when those packages already live under `engineering_os/`.

### Forbidden at root after migration

- `PHASE*_REPORT.md`, `PAG*_REPORT.md`, `PRODUCTION_READINESS_REPORT.md`
- Random `.log`, `.db`, generated evidence
- One-off uncategorized shell scripts
- Duplicate “misc/”, “old/”, “final/” dumping grounds

### Plugin path contracts (stable)

- `~/.hermes/plugins/engineering-os` → `/opt/hermes-engineering-os` (repo root)
- `~/.hermes/plugins/agent-os-router` → `/opt/hermes-engineering-os/agent_os/plugin` (or post-move `agent_os/integrations/hermes/plugin` with symlink/update)

Target layout detail: [repository-layout.md](repository-layout.md).
