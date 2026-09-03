# Agent OS Baseline (Phase 0)

**Stamp:** 20260903T071743Z  
**Backup:** `/var/backups/hermes-engineering-os/agent-os-phase0-20260903T071743Z`  
**Evidence JSON:** [tests/evidence/agent-os-baseline-20260903T071743Z.json](../../../tests/evidence/agent-os-baseline-20260903T071743Z.json)

No destructive work was performed. Secrets were not copied into reports.

## Runtime

| Fact | Value |
|---|---|
| whoami / hostname | `ubuntu` / `Ubuntu-VPS-Clone` |
| HOME | `/home/ubuntu` |
| HERMES_HOME env | unset (effective home `/home/ubuntu/.hermes`) |
| `which hermes` | `/home/ubuntu/.local/bin/hermes` |
| Version | Hermes Agent **v0.20.0 (2026.8.3)** |
| Install dir | `/home/ubuntu/.hermes/hermes-agent` |
| Method | git |
| Python | 3.11.15 (Hermes venv) |
| hermes-agent HEAD | `c0106e50` |
| origin/main (at stamp) | drifted; local +1 carried commit |
| Dirty | `package-lock.json` only |
| Core patched for Agent OS | **No** (default: no core patch) |

## Control plane

| Fact | Value |
|---|---|
| Canonical repo | `/opt/hermes-engineering-os` |
| HEAD | `5cc9055` |
| Remote | `git@github.com:mAsyamJ/hermes-engineering-os.git` |
| Working tree at baseline | clean |

## Health

| Surface | State |
|---|---|
| `hermes-dashboard.service` | **active** (PID 449, `:9119`) |
| Default / rp-friend gateways | **not running** (masked in prior EOS overview) |
| SQLite integrity | kanban / projects / state / verification_evidence / cron DBs: **ok** |
| Sessions / memories | 32 / 4 |

## Checksums (safe files)

| Path | sha256 |
|---|---|
| `~/.hermes/config.yaml` | `815ccad255efe63846f1f2ad1498dd9154d1a73db4a245c8813ae45fda233f6b` |
| `~/.hermes/SOUL.md` | `29993087d2d7a0fb9f71c589f878b3c5b28c67f61765d51a13f9740fcf82e189` |

## Extension inventory

- **Plugins (dirs):** `engineering-os` → `/opt/hermes-engineering-os`, `hermes_otel`, `superpowers`
- **Enabled (config):** engineering-os, hermes_otel, superpowers
- **Hooks dir:** empty (shell hook in config: codebase-memory-mcp `pre_llm_call`)
- **Profiles:** rp-android, rp-api-contract, rp-backend-markets, rp-friend, rp-qa-e2e, rp-recovery-architect, rp-release-orchestrator, rp-review-security, rp-sre-release, rp-web
- **Skill `SKILL.md` count (default home):** **87**
- **skill-bundles dir:** absent
- **Hub lock installed:** `{}`
- **Taps:** `[]`
- **skills.write_approval:** true
- **skills.guard_agent_created:** unset (default false)
- **skills.external_dirs:** unset

## Backup / recovery evidence

- Timestamped copies of config/SOUL/otel/gateway/cron YAML/JSON under the backup directory with `SHA256SUMS`.
- SQLite: integrity checked; no raw db/WAL/SHM copy (consistent snapshot not required for Phase 0).
- `auth.json` / `.env` **not** backed up into reports.

## Authority note

`~/.hermes` is runtime state, not a monorepo. See [HERMES_HOME_AUTHORITY_MAP.md](../../architecture/filesystem/HERMES_HOME_AUTHORITY_MAP.md).
