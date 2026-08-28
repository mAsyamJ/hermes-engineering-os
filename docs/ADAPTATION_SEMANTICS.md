# Adaptation Semantics

Contract: **phase7-adapt-v1**

Phase 7 is controlled progressive delivery for AI-agent **configuration
policies**. It is not unrestricted autonomous optimization.

Pipeline:

```
qualified Phase 6 result
  → recommendation (proposal)
  → human approval boundary
  → immutable policy bundle
  → shadow (no actuation)
  → bounded canary
  → guardrails
  → promotion request or auto-disable + rollback
```

## Failure semantics

- Adaptation infrastructure failure → **Hermes continues** (fail-open to Hermes).
- Candidate policy cannot be validated → **do not apply candidate** (fail-closed
  for adaptation) → baseline Hermes behavior.

## Recommendation

An evidence-backed proposal. Not an active policy. Created only from Phase 6
results. Phase 5 observational ranking cannot create a recommendation.

States: `DRAFT`, `EVIDENCE_VALIDATED`, `NOT_PROMOTABLE`, `APPROVAL_REQUIRED`,
`APPROVED_FOR_SHADOW`, `REJECTED`, `SUPERSEDED`.

Classifications: `TEST_ONLY`, `NOT_PROMOTABLE`, `PRODUCTION_CANDIDATE`.

## Policy

Git-tracked YAML under `policies/adaptation/` compiled to an immutable bundle
with a SHA-256 policy hash. Change requires a new version. No arbitrary
commands, eval, or LLM fields.

## Approval

Hash-bound, scope-bound, expiry-bound. Approval A = shadow/canary.
Approval B = broader promotion. TEST class cannot authorize PRODUCTION_*.
Production grant is `BLOCKED_APPROVAL_BOUNDARY`.

## Shadow

Resolver computes what **would** be selected. Records decision. Does not
mutate Hermes, Kanban, or running tasks.

## Canary

Bounded future fixture/non-production units. Default max concurrent candidate
executions: 1. Not a replacement Phase 6 experiment. No production canary
in V1.

## Guardrails

Deterministic Phase 3/4 evidence. Critical FAIL → auto-disable.
Critical UNKNOWN → no further promotion. Auto-promotion is forbidden.

## Rollback

Predefined fallback hash. Atomic CAS on the active binding. Future-only.
Does not kill running tasks, reset Git, or delete evidence.

## Scope tiers

`FIXTURE`, `BENCHMARK`, `NON_PRODUCTION`, `PRODUCTION_SHADOW`,
`PRODUCTION_CANARY`, `PRODUCTION_BOUNDED`, `PRODUCTION_FULL`.

V1 qualification uses FIXTURE / BENCHMARK / NON_PRODUCTION.
PRODUCTION_SHADOW may read metadata only.
PRODUCTION_CANARY and above remain disabled.
