# Experiment Validity

Validity is a set of independent flags, never a blended score.

| Dimension | PASS means |
|---|---|
| PROTOCOL_INTEGRITY | frozen hash matches stored protocol |
| ASSIGNMENT_INTEGRITY | deterministic assignment; no double-arm unit; documented balance rule |
| CONFIG_INTEGRITY | only declared treatment deltas |
| ENVIRONMENT_INTEGRITY | fingerprint matches freeze |
| MEMORY_ISOLATION | fixture executor or isolated profile; production profile reuse FAIL |
| WORKSPACE_ISOLATION | independent trees; no shared path |
| EXPOSURE_FIDELITY | assignment vs observed classified |
| OUTCOME_COVERAGE | missingness explicit; threshold respected |
| EVALUATOR_COMPATIBILITY | Phase 4 `phase4-eval-v1` fixture profile |

Confirmatory EVIDENCE_* requires required dimensions PASS. Fixture memory may
be PASS by construction. Agent-cognition experiments remain
BLOCKED_CAPABILITY until isolated memory is demonstrated.
