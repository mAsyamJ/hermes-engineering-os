# Experiment Assignment

Algorithm: `assign-hmac-sha256-v1`.

HMAC-SHA256(key=recorded seed, msg=`{alg}|{stratum}|{unit_id}`) sorts units
inside a stratum. Arms alternate from a recorded start bit. Python `hash()`
is not used. Assignment is independent of execution order and outcomes.

Blocked randomization uses operator-defined strata only (suite, explicit
difficulty). No NLP-inferred categories.

Paired design creates two units per case (`pair_id`) with both arms present.
Execution order is HMAC(`order|{pair_id}`).

Balance: |actual_ratio - planned| > 0.35 at n≥8 is a documented mismatch.
Small random imbalance does not auto-invalidate.

Assignment is stored before execution and is immutable after
`execution_started_at`.
