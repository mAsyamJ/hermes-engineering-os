# Agent OS Migration Report

**Date:** 2026-09-03  
**Control plane:** `/opt/hermes-engineering-os`  
**Runtime:** Hermes v0.20.0 @ `c0106e50`  
**Core patched:** No

## What changed

| Area | Change |
|---|---|
| Repo | Added `agent_os/` subsystem, docs, scripts, tests |
| Plugin | Symlink `~/.hermes/plugins/agent-os-router` → `agent_os/plugin/` |
| Config | Enabled `agent-os-router`; set `skills.guard_agent_created: true` |
| Generated | `~/.hermes/SKILLS.md` + `agent_os/registry/*` |
| Skills | +17 hub/GitHub specialists after SAFE scan (104 total) |
| Bundles | 8 native bundles in `~/.hermes/skill-bundles/` |
| HERMES_HOME layout | **Unchanged** (no reorganization) |
| SOUL.md | Unchanged (already identity-only) |
| Engineering OS plugin | Unchanged (still read-only cockpit) |

## Skill counts

| Metric | Before | After |
|---|---|---|
| Native `SKILL.md` (default home) | 87 | **104** |
| Registry entries | n/a | **477** (installed + curated stubs + GitHub tree expansion + capability seeds) |
| Native skill bundles | 0 | **8** |
| Dangerous installs forced | 0 | **0** (mariano audit blocked) |

## Curated sources ingested (GitHub tree)

356 SKILL.md paths discovered across allowlisted/on-demand repos (`tests/evidence/agent-os-github-skill-trees.json`). Per-skill rows merged into registry via `github-expanded.json`.

## Backups

- Phase 0: `/var/backups/hermes-engineering-os/agent-os-phase0-20260903T071743Z`
- Plugin installs / rollbacks under `/var/backups/hermes-engineering-os/agent-os-*`
- T2 install log: `tests/evidence/agent-os-t2-install-*.log`
