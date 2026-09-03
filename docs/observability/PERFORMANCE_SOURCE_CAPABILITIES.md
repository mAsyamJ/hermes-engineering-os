# Performance Source Capabilities

Gate 5.1. Captured 2026-08-28 against live `hermes_engineering`, Kanban, and
Phoenix-derived Phase 3 facts. Do not invent coverage the sources do not have.

Ratings: **SUPPORTED**, **PARTIAL**, **INSUFFICIENT_DATA**,
**UNSUPPORTED_EVIDENCE**, **BLOCKED_AUTH**.

## Production cohort (101)

| Dimension | Count | Rating |
|---|---:|---|
| Production tasks | 101 | SUPPORTED |
| Outcome-covered | 101 | SUPPORTED |
| Lifecycle known | 101 (78 DONE / 23 NOT_DONE) | SUPPORTED |
| Verification PASS/FAIL | 0 / 0 (21 UNKNOWN, 80 NA) | INSUFFICIENT_DATA |
| First-pass known | 74 (62 PASS / 12 FAIL / 10 UNKNOWN / 17 NA) | SUPPORTED (known denom) |
| Retry known | 91 (12 >0) | SUPPORTED |
| Rework known | 101 (1 DETECTED) | SUPPORTED |
| Human intervention DETECTED | 59 (42 UNKNOWN) | PARTIAL |
| Trace-covered | 0 | INSUFFICIENT_DATA |
| Model-covered | 0 | INSUFFICIENT_DATA |
| Single-model | 0 | INSUFFICIENT_DATA |
| Mixed-model | 0 | INSUFFICIENT_DATA |
| Skill-covered | 0 | INSUFFICIENT_DATA |
| Quality-evaluated (ELIGIBLE COMPLETE) | 0 | INSUFFICIENT_DATA |
| Cost-known | 0 | INSUFFICIENT_DATA / UNSUPPORTED_EVIDENCE to estimate |
| Profile name | 101 | SUPPORTED (name only) |
| Profile config version | 0 | UNSUPPORTED_EVIDENCE |
| Prompt / config hash | 0 | UNSUPPORTED_EVIDENCE |
| Explicit task labels | 0 | UNSUPPORTED_EVIDENCE |
| Git AVAILABLE | 0 | INSUFFICIENT_DATA |
| GitHub | 21 BLOCKED_AUTH | BLOCKED_AUTH |
| Repository_id known | 21 retropick / 80 null | PARTIAL |

Fixture model usage exists (1 run, mixed provider identity) and may validate
math only.

Do not implement a production metric whose denominator capability is undefined.
Zero evaluated quality coverage is INSUFFICIENT_DATA, not 0%.
