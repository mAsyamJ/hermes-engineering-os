# Performance Comparability

A pairwise effect is computed only when left and right share:

- cohort semantics
- metric definition
- Phase 3 ruleset version
- Phase 4 contract when the metric is a quality rate
- compatible repository mix, or an explicit confounding label

States: COMPARABLE, CONFOUNDED, NOT_COMPARABLE, INSUFFICIENT_DATA.

Interpretation: INSUFFICIENT_DATA, NO_CLEAR_DIFFERENCE, OBSERVED_DIFFERENCE,
CONFOUNDED, NOT_COMPARABLE. Never WINNER / BEST / WORST.

If aggregating across heterogeneous repositories/profiles, the Simpson guard
attaches strata and refuses an unlabeled global claim when the sign reverses.

Configured comparison sets live in `config/performance-comparisons.yaml`.
No cartesian p-value fishing. No p-values in the default architecture.
