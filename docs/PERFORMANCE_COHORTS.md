# Performance Cohorts

Trusted definitions: `config/performance-cohorts.yaml`.

Each cohort has `cohort_id`, `version`, human-readable description, and a
SHA-256 `config_hash` of the selector plus exclusion lists.

V1 selectors: production flag, board, fixture exclusion, model attribution
type, skill attribution type. No title NLP.

`math_fixtures` is for statistical validation only (`ui_default: false`).
Fixture/canary task ids and boards never populate production dashboards.
