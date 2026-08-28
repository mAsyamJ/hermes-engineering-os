# Experiment Semantics (`phase6-exp-v1`)

Phase 6 answers: when one controlled variable changes and other important
conditions are held constant, is there a measurable difference?

It does **not** answer observational Phase 5 rankings. `causal=false` remains
on Performance APIs. Experiment conclusions are protocol-scoped and never
auto-applied.

## Identity

Every result stores `phase3-v1`, `phase4-eval-v1`, `phase5-perf-v1`, and
`phase6-exp-v1`.

## States

DRAFT → VALIDATED → PRE_REGISTERED → READY → RUNNING → PAUSED | COMPLETED |
CANCELLED | INVALIDATED.

PRE_REGISTERED means definition, variant, primary metric, analysis, sample
plan, guardrails, seed, and assignment algorithm hashes are locked.

## Conclusions

NOT_STARTED, COLLECTING, INSUFFICIENT_DATA, INVALIDATED, NO_CLEAR_EFFECT,
EVIDENCE_FOR_CANDIDATE, EVIDENCE_AGAINST_CANDIDATE, GUARDRAIL_FAILURE.

Never WINNER / LOSER / BEST. Never auto-route.

## Single-factor default

V1 allows NONE (A/A) and FIXTURE_ARTIFACT. MULTI_FACTOR is rejected. MODEL /
PROFILE / PROMPT / SKILL / TOOLS are documented, not activated.

## Assignment vs exposure

Separate facts. Fallback does not rewrite ITT assignment. Primary analysis is
INTENTION_TO_TREAT. Per-protocol is secondary.
