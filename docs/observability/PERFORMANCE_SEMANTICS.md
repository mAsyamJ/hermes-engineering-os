# Performance Semantics

Contract: **phase5-perf-v1**. Observational. Does not establish causality.

Phase 3 answers what happened. Phase 4 answers how well an artifact passed
objective verification. Phase 5 answers: under comparable conditions, what
performance differences are actually supported by the available evidence?

## Hierarchy

observation → metric → aggregate → comparison → insight

Recommendations, routing, and winner badges are out of scope.

## Population

Default production population is `task_outcomes.production_cohort = true` on
board `retropick-markets-release`, excluding fixture/canary identities listed
in `config/performance-cohorts.yaml`.

## UNKNOWN / NA / INSUFFICIENT_DATA

UNKNOWN is first-class and never coerced to failure. NOT_APPLICABLE is
distinct. INSUFFICIENT_DATA is not failure. Coverage (known_n / population_n)
is required on every metric.

## Lineage

Every aggregate stores `phase5-perf-v1`, the Phase 3 ruleset version, the
Phase 4 contract version when quality metrics apply, cohort id/version/hash,
and `computed_at`.

## Language

Allowed: "within this cohort, A had a higher observed first-pass estimate than B."

Forbidden: "A caused better performance." "Use model A." "BEST MODEL."
