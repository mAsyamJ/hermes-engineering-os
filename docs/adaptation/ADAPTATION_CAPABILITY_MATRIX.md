# Adaptation Capability Matrix

Gate 7.1. Captured against live Hermes 0.20.0 / `c0106e50`, Engineering OS HEAD
at Gate 7.0, and Phase 6 experiment capabilities. Do not actuate a treatment
whose control path is undefined, unauthorized, or unqualified.

Ratings: **SUPPORTED**, **SUPPORTED_NON_PRODUCTION**, **SHADOW_ONLY**,
**BLOCKED_RUNTIME**, **BLOCKED_MEMORY**, **BLOCKED_EVIDENCE**,
**BLOCKED_RUNTIME_INTEGRATION**, **BLOCKED_CAPABILITY**.

| Dimension | Live Hermes seam | Production actuation | V1 Phase 7 |
|---|---|---|---|
| FIXTURE_ARTIFACT | Isolated fixture trees + Phase 4 evaluator | Not production | **activated** (shadow + fixture canary) |
| NONE | Identity / baseline | N/A | baseline resolver path |
| MODEL | kanban `model_override` → `-m/--provider` on **new** spawn | **BLOCKED_RUNTIME_INTEGRATION** + **BLOCKED_EVIDENCE** | documented, not actuated |
| PROFILE | task `assignee` → `-p` / `HERMES_HOME` | **BLOCKED_MEMORY** (shared profile); **BLOCKED_RUNTIME_INTEGRATION** | not actuated |
| SKILL | task `skills` → `--skills` | **BLOCKED_RUNTIME_INTEGRATION** + **BLOCKED_EVIDENCE** | not actuated |
| PROMPT/CONFIG | profile `SOUL.md` / `config.yaml` (not per-task) | **BLOCKED_RUNTIME** | not actuated |
| TOOLS | profile `platform_toolsets` | **BLOCKED_RUNTIME** | not actuated |
| Production RetroPick tasks | Kanban PATCH exists but is a second controller | **BLOCKED_RUNTIME_INTEGRATION** | **disabled** |

## Runtime notes

- Worker argv/env is immutable after `Popen`. Running tasks are never retargeted.
- Plugin hooks (`kanban_task_claimed`, `pre_llm_call`) cannot rewrite spawn
  config without a Hermes-core patch. Phase 7 does not patch Hermes core.
- Writing canonical Kanban rows to apply policy would make Engineering OS a
  pre-dispatch scheduler. That is forbidden. The resolver is a library used by
  shadow and the fixture executor only.
- rp-friend restart is **not required** and **not performed**.
- Production shadow is read-only Kanban metadata (existing `mode=ro` adapter).
  It does not change model, profile, skill, or prompt.

## Memory

Same production profile is **BLOCKED_CAPABILITY** / **BLOCKED_MEMORY**.
Dedicated empty profile is theoretically SUPPORTED_ISOLATED but is not
installed or used in Phase 7. AgentMemory and Graphiti are not installed.
