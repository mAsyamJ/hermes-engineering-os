# Experiment Capability Matrix

Gate 6.1. Captured against live Hermes 0.20.0 / `c0106e50`, Engineering OS HEAD
at Gate 6.0, and Phase 5 source capabilities. Do not activate a treatment
whose control path or exposure verification is undefined.

Ratings: **SUPPORTED**, **SUPPORTED_ISOLATED**, **PARTIAL**, **UNSUPPORTED**,
**BLOCKED_MEMORY_ISOLATION**, **BLOCKED_RUNTIME**, **INSUFFICIENT_DATA**.

| Dimension | Control | Exposure verification | V1 execution |
|---|---|---|---|
| FIXTURE_ARTIFACT | SUPPORTED (isolated fixture trees) | SUPPORTED (tree hash vs assigned artifact) | **activated** |
| NONE (A/A) | SUPPORTED (identical snapshots) | SUPPORTED | **activated** |
| MODEL | SUPPORTED (`hermes -m/--provider`) | PARTIAL (`llm.model_name` on new workers; production coverage 0) | documented, **not activated** (budget 0) |
| PROFILE | SUPPORTED_ISOLATED (new `HERMES_HOME`) | UNSUPPORTED_EVIDENCE historically; hashable prospectively | not activated |
| PROMPT/CONFIG | SUPPORTED (hash `SOUL.md` + redacted config) | UNSUPPORTED_EVIDENCE historically | not activated |
| SKILL | SUPPORTED (tree hash) | PARTIAL (skill spans if present) | not activated |
| TOOLS | SUPPORTED (hash `platform_toolsets`) | PARTIAL | not activated |
| Production RetroPick tasks | BLOCKED_RUNTIME | INSUFFICIENT_DATA | **disabled** |

Memory: same production profile is **BLOCKED_MEMORY_ISOLATION**. Dedicated empty
profile is SUPPORTED_ISOLATED. Fixture executor never loads Hermes memory: PASS
by construction.

Kanban experiment board can coexist without `--switch` and without rp-friend
restart. V1 does not create dispatcher-claimed tasks.

rp-friend restart: **not required** and **not performed**.
