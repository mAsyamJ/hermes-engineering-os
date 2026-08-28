# Adaptation Recommendations

A recommendation is an **evidence-backed proposal**. Generating one is not
approval and does not activate a policy.

## Inputs

Only Phase 6 experiment results (conclusion, protocol, validity, guardrails,
treatment, config hashes). Phase 5 ranking is rejected as a source.

## Eligibility

Production-promotable requires **all** of:

- conclusion `EVIDENCE_FOR_CANDIDATE`
- not `FIXTURE_VALIDATION_ONLY`
- scope compatible with intended PRODUCTION_* policy
- required validity dimensions PASS
- guardrails PASS
- protocol frozen
- assignment / config / environment integrity PASS
- exposure fidelity and outcome coverage sufficient
- no material contamination
- real treatment type qualified in Phase 6 (not FIXTURE_ARTIFACT / NONE)

Current live results:

| Experiment | Conclusion | Recommendation |
|---|---|---|
| fixture-aa-v1 | NO_CLEAR_EFFECT | NOT_PROMOTABLE |
| fixture-known-effect-v1 | EVIDENCE_FOR_CANDIDATE + FIXTURE_VALIDATION_ONLY | TEST_ONLY |
| fixture-paired-v1 | EVIDENCE_FOR_CANDIDATE + FIXTURE_VALIDATION_ONLY | TEST_ONLY |

`INVALIDATED`, `EVIDENCE_AGAINST_CANDIDATE`, `GUARDRAIL_FAILURE`, and missing
required validity are `NOT_PROMOTABLE`.

`PRODUCTION_RECOMMENDATION` status at Phase 7 entry and completion:
**BLOCKED_EVIDENCE**.
