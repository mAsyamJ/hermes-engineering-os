# Adaptation Rollout

Shadow is mandatory before canary. Canary is not a Phase 6 experiment.

## Shadow

Input: structured task context (synthetic fixture contexts and/or read-only
Kanban metadata).

Output: `BASELINE` | `CANDIDATE` | `CONFLICT` | `NOT_ELIGIBLE`.

Stored: context, baseline actual config, would-be candidate, policy id/hash,
match reason, latency, conflict flag. No Kanban writes. No spawn. No claim
of candidate efficacy.

Production read-only shadow uses the existing Kanban `mode=ro` adapter.

## Canary plan

Required fields: scope, max_units, max_candidate_pct, max_concurrent_candidate
(default **1**), selection algorithm (`assign-hmac-sha256-v1` bucketing or
explicit allowlist), guardrails, fallback hash, expiry.

Selection is deterministic. No outcome-informed “easy task” picking.
A unit is never moved between candidate and baseline after execution starts.

## Exposure

Records task/unit, policy, selected config, fallback, resolution, started_at,
observed configuration, fidelity, outcome refs. Affects **new** eligible
executions only.

## Promotion

Canary success creates a `PROMOTION_REQUEST`. It does not activate a broader
binding. Approval B is required. Production Approval B is
`BLOCKED_APPROVAL_BOUNDARY`. There is no 5% → 25% → 100% automatic ladder.
