# Evaluation Semantics

Contract version: **phase4-eval-v1**

Phase 3 (`phase3-v1`) answers what objectively resulted from an execution.
Phase 4 answers how well an engineering artifact satisfied objective
verifiable criteria. Phase 4 is another derived layer. It never mutates
Hermes lifecycle.

UNKNOWN is first-class. Missing evidence is not FAIL. Kanban DONE is not
verified quality. GitHub `BLOCKED_AUTH` is not candidate failure.

## Evaluation target

An evaluation identifies all of:

- canonical task ID (when known)
- canonical Kanban run ID (when known)
- candidate artifact hash
- baseline artifact hash (or missing)
- candidate/baseline commit SHA when known
- repository id
- profile id + version + config hash
- evaluator id + version + impl hash
- contract `phase4-eval-v1`

Results must not migrate to a different artifact when a workspace changes.

## Eligibility

| State | Meaning |
|---|---|
| ELIGIBLE | reproducible candidate artifact can be captured from allowlisted evidence |
| TEST_ELIGIBLE | fixture/canary cohort intentionally evaluated |
| INSUFFICIENT_EVIDENCE | no immutable candidate (typical historical production) |
| NOT_APPLICABLE | repository or category unsupported |
| EXCLUDED | out of evaluation scope |

Lack of evaluation is not failure.

## Execution status

PENDING, RUNNING, COMPLETE, PARTIAL, ERROR, STALE, LOCKED.

## Evaluator verdicts

PASS, FAIL, WARN, UNKNOWN, NOT_APPLICABLE, BLOCKED_AUTH,
BLOCKED_RESOURCE, BLOCKED_ENVIRONMENT, ERROR.

## Artifact identity

Preferred: `COMMIT_SNAPSHOT` of an exact SHA via `git archive`.
Next: `BASE_COMMIT_PLUS_TRACKED_PATCH`.
Else: no evaluable artifact → INSUFFICIENT_EVIDENCE.

Do not evaluate “whatever is in the workspace now” as an older run.

## Baseline comparison

Same profile, toolchain, argv, image, evaluator version for baseline and
candidate. Classifications: UNCHANGED_PASS, INTRODUCED_FAILURE,
FIXED_FAILURE, UNCHANGED_FAILURE, UNKNOWN.

Never guess baseline from timestamps.

## Quality vector

Independent dimensions. No canonical 0–100 score. No model leaderboard.

Summary state: VERIFIED_PASS, VERIFIED_FAIL, PARTIAL,
INSUFFICIENT_EVIDENCE, ERROR.

## Failure behavior

Evaluation failure is fail-open to Hermes, Phoenix ingest, Phase 3
analytics, rp-friend, and production repositories. Phoenix projection
failure does not invalidate canonical `hermes_engineering` results.

## Versioning

Same inputs + same evaluator/profile versions yield equivalent logical
results. Version bumps create a new current row; old rows remain history.
