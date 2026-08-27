# Analytics Source Capabilities

Gate 3.1. Captured against live Hermes Kanban, Phoenix GraphQL 20.4.0,
allowlisted Git, and GitHub CLI on 2026-08-27. Metrics must not be designed
beyond this matrix.

Ratings: **SUPPORTED** (adapter can return the field), **PARTIAL** (field exists
but is incomplete, dropped, or needs derivation), **UNSUPPORTED**,
**BLOCKED_AUTH**.

## Hermes Kanban

Live files:

- `/home/ubuntu/.hermes/kanban/boards/retropick-markets-release/kanban.db`
- `/home/ubuntu/.hermes/kanban/boards/eos-phase2-obs/kanban.db`
- `/home/ubuntu/.hermes/kanban.db` (empty default)

Tables used: `tasks`, `task_runs`, `task_events`, `task_comments` (author only).
`task_links` / `task_attachments` are not analytics inputs.

| Desired metric | Rating | Notes |
|---|---|---|
| Lifecycle | SUPPORTED | `tasks.status`, `created_at`, `started_at`, `completed_at` |
| Attempt ordering | PARTIAL | no `attempt_number`; order by `started_at, id` |
| Qualifying run | PARTIAL | derive from spawned events / non-zero duration; `worker_pid` is often NULL |
| Retry | PARTIAL | multiple `task_runs` + failure outcomes |
| Rework | PARTIAL | `status`, `review_reopened`, `changes_requested`, `descendant_invalidated` |
| Human intervention | PARTIAL | attributable event kinds + `task_comments.author`; cannot prove absence |
| Task wall duration | SUPPORTED | unix seconds `started_at`/`completed_at` |
| Run wall duration | SUPPORTED | `task_runs.started_at`/`ended_at` |
| Profile / workspace | SUPPORTED | `assignee`, `workspace_path`, `branch_name`, `workspace_kind` |
| Typed objective verifier | UNSUPPORTED | `metadata.tests_run` / `verification` / `gates` are free-text; not a typed contract |
| Comment bodies / task body | UNSUPPORTED by design | never copied into analytics |

Phase 2 dashboard reads the current board only and caps lists at 500. Analytics
must pass `board=` and page through all in-scope tasks.

## Phoenix (GraphQL, not internal SQL)

Supported client: Engineering OS `engineering_os.observability.phoenix_client`
posting to `http://127.0.0.1:6006/graphql`. Phoenix 20.4.0. Pin unchanged.

| Desired metric | Rating | Notes |
|---|---|---|
| Trace / span ids | SUPPORTED | `context.traceId` / `spanId` |
| Kanban correlation | SUPPORTED | `hermes.kanban.task_id` / `run_id` / `board` |
| LLM / tool counts | PARTIAL | span name prefixes `llm.` `api.` `tool.` |
| Model / provider | SUPPORTED | `llm.model_name` `llm.provider`; multiple models possible |
| Tokens | PARTIAL | present on span attributes; Phase 2 client dropped them; Phase 3 picks them |
| Skill spans | PARTIAL | `skill.*` / `hermes.skill.name` if emitted; otherwise UNKNOWN |
| Errors | PARTIAL | GraphQL `statusCode` plus `error.type` |
| Span / trace timing | PARTIAL | `startTime` `endTime` `latencyMs` |
| Cost | UNSUPPORTED | hermes-otel cost is a metric; Phoenix `/v1/metrics` is 405 |

Do not query Phoenix Postgres tables. Do not install `phoenix.client.Client`.
Do not upgrade Phoenix for Phase 3.

## Git (allowlisted, fixed argv)

| Desired metric | Rating | Notes |
|---|---|---|
| Repo / remote / dirty | SUPPORTED | `config/repositories.json` only |
| Historical branch SHA | PARTIAL | Phase 2 used current HEAD only; Phase 3 adds `rev-parse` of the task branch |
| Working tree mutation | UNSUPPORTED by design | no checkout, no write |

## GitHub

| Desired metric | Rating | Notes |
|---|---|---|
| API authentication | BLOCKED_AUTH | `gh auth status` fails; legitimate evidence state |
| PR / checks / merge | BLOCKED_AUTH live | adapters must return BLOCKED_AUTH without treating it as failure |
| CI conclusion | BLOCKED_AUTH live | never convert to FAIL |

## Capability decisions used by phase3-v1

- Verification on the live VPS is UNKNOWN unless a future GitHub session is
  AVAILABLE with a check conclusion, or run metadata contains the exact typed
  key `objective_result` in `{PASS, FAIL}`.
- Free-text `tests_run` / `verification` blobs are **not** parsed into pass/fail.
- Cost is always UNKNOWN in Phase 3.
- Skill usage is UNKNOWN unless Phoenix skill spans exist. Task `skills` JSON is
  force-load intent, not usage.
