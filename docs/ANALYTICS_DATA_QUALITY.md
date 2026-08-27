# Analytics Data Quality

`scripts/verify-analytics-data.sh` runs `engineering_os.analytics.quality`.

Invalid:

- outcome without task fact
- run without task fact
- negative durations
- first-pass PASS with `retry_count > 0`
- VERIFIED_SUCCESS without verification PASS
- human intervention stored as false/no/0

Coverage (production cohort) is a Phase 3 product: eligible tasks, git/github/trace/verifier rates, unknown first-pass, unknown intervention. UNKNOWN rows stay in the denominator.
