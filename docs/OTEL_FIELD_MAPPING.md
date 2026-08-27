# OTel Field Mapping

Canonical Engineering OS names versus hermes-otel / Hermes observer fields.
Correlation is asserted only from explicit evidence.

| Canonical name | Source | hermes-otel attribute | Notes |
|---|---|---|---|
| `hermes.kanban.task_id` | env `HERMES_KANBAN_TASK` | resource/span `hermes.kanban.task_id` | **Not** native to hermes-otel. Stamped by Engineering OS `register()` into `OTEL_RESOURCE_ATTRIBUTES` before hermes-otel `Resource.create()`. |
| `hermes.kanban.run_id` | env `HERMES_KANBAN_RUN_ID` | `hermes.kanban.run_id` | Integer string from dispatcher. Distinct from Kanban task id. |
| `hermes.kanban.board` | env `HERMES_KANBAN_BOARD` | `hermes.kanban.board` | Board slug. |
| `hermes.kanban.workspace` | env `HERMES_KANBAN_WORKSPACE` | `hermes.kanban.workspace` | Worker workspace path. |
| `hermes.runtime.task_id` | observer `task_id` on API/tool hooks | `gen_ai.tool.call.id` (tools); span key `api:{task_id}` | Never equal-by-coincidence to Kanban task id. |
| `hermes.session.id` | observer `session_id` | `hermes.session.id`, `session.id`, `gen_ai.conversation.id` | |
| `hermes.turn.id` | observer `turn_id` where present | recovered session via documented `session_id_from_turn_id` | Format `<session_id>:<task_id>:<hex>`. The middle segment is runtime task id. |
| `hermes.api_request.id` | observer `task_id` on `pre_api_request` | span name `api.*`, key `api:{task_id}` | |
| `hermes.tool_call.id` | observer `task_id` on `pre_tool_call` | `gen_ai.tool.call.id` | |
| `otel.trace_id` | OTel SDK | span context `trace_id` | |
| `otel.span_id` | OTel SDK | span context `span_id` | |
| `git.commit_sha` | Engineering OS Git adapter | not an OTel field in Phase 2 | Explicit workspace/branch mapping only. |
| `github.pr_number` | GitHub API | not an OTel field | May be `BLOCKED_AUTH`. |

## Non-interchangeable namespaces

`hermes.kanban.task_id` (`t_<hex>`) ≠ `hermes.runtime.task_id` ≠ `hermes.kanban.run_id` (integer) ≠ `hermes.session.id` ≠ `otel.trace_id`.

Missing evidence is `UNKNOWN`. No heuristic join on similar strings.
