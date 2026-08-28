# Evaluation Data Quality

Invariants (see `engineering_os/evaluation/quality.py` and
`scripts/verify-evaluation-data.sh`):

- PASS/FAIL results require an artifact when eligibility is ELIGIBLE/TEST_ELIGIBLE
- PASS cannot come from a timed-out evaluator
- INSUFFICIENT_EVIDENCE runs must not have PASS/FAIL results
- Phoenix projection must never be marked CANONICAL
- Different profile versions cannot be compared as one evaluation identity
- Candidate commands must come from the approved profile

UNKNOWN and NOT_APPLICABLE are valid. Zeros in coverage are valid.
