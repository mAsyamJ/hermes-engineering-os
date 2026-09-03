# ADR: Hermes Agent OS Capability Control Plane

## Status

Accepted (2026-09-03). Implemented as subsystem of `/opt/hermes-engineering-os`.

## Problem

Hermes has many skills and a busy `~/.hermes` runtime home. Operators need capability-driven routing, progressive disclosure, safe missing-skill discovery, and a machine registry — without forking Hermes, reorganizing HERMES_HOME, or building a second Engineering OS / orchestrator.

## Current-state findings

- Hermes **v0.20.0 (2026.8.3)** at `~/.hermes/hermes-agent` @ `c0106e50`.
- Engineering OS at `/opt/hermes-engineering-os` is the canonical control-plane git repo and a **read-only** dashboard plugin.
- 87 installed `SKILL.md` files; hub lock empty; no skill-bundles; 10 `rp-*` profiles.
- Plugin hooks inject into the **user message** via `pre_llm_call` (not system prompt) — intentional for prompt-cache stability.
- `skills.create_dir` does **not** exist in 0.20.0; agent-created skills land in `~/.hermes/skills/`.
- `skills.write_approval` already true; `find-skills` uses `npx skills` (not Hermes hub).

## Decision

1. **Extend Engineering OS repo** with `agent_os/` — do not create `/opt/hermes-agent-os` or `~/.hermes/os`.
2. **Separate plugin** `agent-os-router` (symlink to `agent_os/plugin/`) so Engineering OS stays GET-only/hook-free and Agent OS can be disabled independently.
3. **Native skill SoT remains** `~/.hermes/skills/`. Registry is an index/control plane only.
4. **Deterministic classifier + scorer** first; LLM-of-LLMs routing rejected.
5. **Trust tiers T0–T4**; never `--force`; T3 never auto-install; use `tools.skills_guard` / Hub APIs.
6. **No Hermes core patch.**
7. **No new specialist profiles** in this change — document existing `rp-*` topology only.
8. **Observability**: fail-open `hermes.agent_os.*` attributes on existing `hermes_otel` spans — no second exporter.
9. **Learned skills**: category `learned/` under Hermes skills + git mirror; `skills.guard_agent_created: true`.

## Rejected alternatives

| Alternative | Why rejected |
|---|---|
| Reorganize `~/.hermes` | Breaks Hermes path expectations |
| Merge hooks into `engineering-os` | Violates read-only cockpit / AGENTS.md |
| System-prompt plugin section | Not supported; would bust prompt cache |
| `npx skills add` as installer | Wrong package manager for Hermes |
| Core patch for `create_dir` | Unsupported; not required |
| New profile fleet | Isolation already provided by `rp-*`; duplication risk |

## Rollback

`scripts/agent-os/rollback-agent-os.sh` disables the plugin and removes generated `SKILLS.md` only.

## Consequences

- Routing proven via golden unit tests without live LLM.
- Curated GitHub sources are seeded as registry stubs/capability nodes until per-skill Hub expansion + install.
- Bundles are emitted only when concrete skill IDs are installed (none required yet for missing Monad stack).
