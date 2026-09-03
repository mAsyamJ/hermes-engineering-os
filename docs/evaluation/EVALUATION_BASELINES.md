# Evaluation Baselines

Never guess from timestamps.

Order: profile explicit ref → task `base_commit` → `git merge-base` when both
SHAs are known → else `MISSING_BASELINE` (comparison UNKNOWN).

Fixture profile uses `parent_commit`. RetroPick profile records
`merge_base_default_branch` but Tier C is not executed in Phase 4.

Raw baseline and candidate results are stored independently, then classified
as UNCHANGED_PASS / INTRODUCED_FAILURE / FIXED_FAILURE / UNCHANGED_FAILURE /
UNKNOWN.
