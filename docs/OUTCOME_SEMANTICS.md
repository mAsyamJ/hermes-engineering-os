# Outcome Semantics

Ruleset version: **phase3-v1**

Every stored value is an OBSERVED FACT (directly supported by a source) or a
DERIVED FACT (computed by a versioned rule). Derived rows record
`ruleset_version`, `computed_at`, evidence references, reason, and evidence
quality.

UNKNOWN is a first-class state. UNKNOWN is never coerced to FALSE. GitHub
`BLOCKED_AUTH` is not GitHub evidence failure.

## Rule IDs

| ID | Field | Inputs | UNKNOWN | NOT_APPLICABLE | Fixture | Recompute |
|---|---|---|---|---|---|---|
| R1 | task eligibility | board, workspace, task id, scope yaml | missing task row → skip | boards not in scope | excluded boards stay cohort=fixture | same |
| R2 | production cohort | R1 + repo allowlist | workspace missing → production=false unless included board and not excluded | disposable repo | fixture board never production | same |
| R3 | qualifying run | task_runs + spawned events | runs unreadable | no runs | synthetic zero-duration excluded | same |
| R4 | lifecycle_state | tasks.status, completed_at | task unreadable | — | same rules | same |
| R5 | verification_state | github CI, typed `objective_result` | no typed verifier | github null and no verifier | N/A when disposable github null | same |
| R6 | final_outcome | R4 + R5 | lifecycle UNKNOWN | — | same | history row if changed |
| R7 | first_pass_state | ordered qualifying runs | runs unclassifiable | zero qualifying runs | same | same |
| R8 | retry_count | qualifying failures before first success | runs unclassifiable | — | same | same |
| R9 | rework | reopen events after completion | events unreadable | — | same | same |
| R10 | human_intervention | attributable events + comment authors | no attributable evidence | — | never false | same |
| R11 | durations | source clocks by dimension | clock missing | — | same; never sum unlike clocks | same |
| R12 | LLM/tool/error/token | Phoenix spans | trace missing | — | same | same |
| R13 | model usage | span models + overrides as intent only | no span models | — | same | same |
| R14 | skill usage | skill spans only | no skill spans | — | task.skills is not usage | same |
| R15 | git evidence | allowlisted rev-parse | no workspace/branch | disposable fixture without git | same | same |
| R16 | github evidence | adapter state | unknown transport | github null | BLOCKED_AUTH live | same |
| R17 | cost | none in Phase 3 | always UNKNOWN | — | same | same |

## R1 Eligibility

A task is eligible for a materialization mode when:

- `--task` names it, or
- `--backfill` / incremental scans `included_boards` from
  `config/analytics-scope.yaml`

Excluded boards, excluded workspace prefixes, and excluded task ids are never
the production cohort. They may be materialized with `cohort=fixture` for canary.

`t_phase2obs` is a Phoenix correlation id, not a Kanban row. It is not a
`task_facts` key.

## R3 Qualifying run

A `task_runs` row qualifies when any of:

- a `spawned` event exists for that `run_id`
- `started_at` and `ended_at` exist and differ

Synthetic closes (`started_at == ended_at`) are excluded. Order:
`started_at ASC NULLS LAST, id ASC`.

## R4 Lifecycle

- `DONE` if `status` in `{done, archived}`
- `NOT_DONE` otherwise when the row is readable
- `UNKNOWN` if the task cannot be read

Kanban DONE is lifecycle completion only.

## R5 Verification

PASS or FAIL only from:

1. GitHub check conclusion when `github_evidence_state=AVAILABLE`, or
2. run metadata exact key `objective_result` ∈ `{PASS, FAIL}`

Otherwise UNKNOWN. NOT_APPLICABLE when the mapped repository has `github: null`
and no typed verifier exists.

GitHub `BLOCKED_AUTH` ⇒ verification UNKNOWN, not FAIL.

## R6 Final outcome

- `VERIFIED_SUCCESS`: lifecycle DONE and verification PASS
- `COMPLETED_UNVERIFIED`: lifecycle DONE and verification UNKNOWN or NOT_APPLICABLE
- `VERIFIED_FAILURE`: verification FAIL
- `INCOMPLETE`: lifecycle NOT_DONE
- `UNKNOWN`: lifecycle UNKNOWN

## R7 First pass

- `PASS`: first qualifying run outcome is `completed` (or run status `done` with
  outcome completed/empty success close)
- `FAIL`: first qualifying run outcome ∈ `{crashed, timed_out, failed, spawn_failed, gave_up}`
- `NOT_APPLICABLE`: zero qualifying runs
- `UNKNOWN`: first run exists but cannot be classified

## R8 Retry

`retry_count` is the number of qualifying runs with failure outcomes **before**
the first qualifying success. It is **not** `number_of_runs - 1`. Null if R3 is
UNKNOWN.

## R9 Rework

If events were read:

- count reopen-after-completion cycles from `status` done→non-done,
  `review_reopened`, `descendant_invalidated`, `changes_requested` after review,
  or a qualifying run starting after `completed_at`
- `rework_status=DETECTED` when count > 0 else `NOT_DETECTED`

If events could not be read: `rework_status=UNKNOWN`, `rework_count` null.

## R10 Human intervention

`DETECTED` only from attributable evidence: event kinds `commented`, `status`
(dashboard), `edited`, `promoted_manual`, `unblocked`, `assigned` with
non-auto source, `archived`, `review_reopened`, `model_override_set`, or a
`task_comments.author` row.

Otherwise `UNKNOWN`. Never store false. Absence of evidence is not absence of
humans.

## R11 Durations

Separate clocks: `task_wall_seconds`, `run_wall_seconds` (sum of qualifying
runs), `trace_wall_seconds`, `llm_total_seconds`, `tool_total_seconds`.
Do not add incompatible dimensions.

## Success statement for live VPS

With GitHub `BLOCKED_AUTH` and no typed `objective_result`, production `done`
tasks materialize as **COMPLETED_UNVERIFIED**. That is the correct objective
result, not a materializer failure.
