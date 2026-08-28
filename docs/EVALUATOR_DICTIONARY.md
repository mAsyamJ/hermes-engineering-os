# Evaluator Dictionary

Contract: **phase4-eval-v1**. Every dimension below is independently
explainable. NOT_APPLICABLE is used when the dimension does not apply.
Do not coerce that to PASS.

## repo.build

| State | Meaning |
|---|---|
| PASS | approved build/compile command exited 0 in the qualified sandbox |
| FAIL | command exited non-zero without timeout/crash classification |
| WARN | not used in v1 |
| UNKNOWN | command could not be observed |
| NOT_APPLICABLE | profile has no build command |
| Evidence | argv from profile, exit, duration, log digest |
| Tier | C |
| Baseline | same command on baseline artifact |
| Failure | ERROR/timeout bounded; Hermes unaffected |

Build PASS does not imply tests, security, or architecture PASS.

## repo.tests

Stores command, exit, discovered/passed/failed when parsed, duration,
timeout, baseline and candidate outcomes separately.

| PASS | approved test command exited 0 |
| FAIL | non-zero without infrastructure ERROR |
| UNKNOWN | output unparsable or not run |
| NOT_APPLICABLE | no test command |

Does not claim test-quality or mutation coverage. Tier C.

## repo.regression

Derived from baseline vs candidate tests (or build if tests NA).

| UNCHANGED_PASS | both PASS |
| INTRODUCED_FAILURE | baseline PASS, candidate FAIL |
| FIXED_FAILURE | baseline FAIL, candidate PASS |
| UNCHANGED_FAILURE | both FAIL |
| UNKNOWN | either side UNKNOWN/ERROR/missing |

Tier A derivation after Tier C runs.

## repo.lint / repo.typecheck

Record baseline violations, candidate violations, new, fixed.
Pre-existing lint does not FAIL the candidate unless the candidate
introduced new violations (v1 default) or the profile says otherwise.

## repo.security

Deterministic path/secret/static rules from the profile only.
`npm audit` and other network vulnerability DBs are UNSUPPORTED.
Offline insufficient → UNKNOWN.

## repo.architecture_policy / repo.scope_policy

Only explicit machine-readable rules (forbidden imports, forbidden paths).
No LLM architecture guess. File-count-alone is not “too broad.”

## task.acceptance_checks

Structured machine-verifiable criteria only. Free-text → UNKNOWN /
UNSUPPORTED. No LLM requirement judging.

## github.ci

AVAILABLE / BLOCKED_AUTH / NOT_FOUND / NOT_APPLICABLE / UNKNOWN.
BLOCKED_AUTH does not fail the candidate. Local evaluators continue.

## llm.judge

EXPERIMENTAL, DISABLED. Interface and fakes only. Must not affect the
canonical quality vector. No API spend.
