# OTel Correlation

Engineering OS stamps canonical Kanban identity onto OpenTelemetry **resource**
attributes. hermes-otel does not read `HERMES_KANBAN_*`. Hermes already injects
those variables into dispatcher-spawned workers.

## Load order

Hermes loads user plugins with `sorted(iterdir())`. `engineering-os` therefore
registers **before** `hermes_otel`. `register()` merges:

| Environment | Resource attribute |
|---|---|
| `HERMES_KANBAN_TASK` | `hermes.kanban.task_id` |
| `HERMES_KANBAN_RUN_ID` | `hermes.kanban.run_id` (integer string) |
| `HERMES_KANBAN_BOARD` | `hermes.kanban.board` |
| `HERMES_KANBAN_WORKSPACE` | `hermes.kanban.workspace` |

When Hermes loads Engineering OS it is `hermes_plugins.engineering_os`, so
`register()` inserts the plugin root on `sys.path` before importing
`engineering_os.observability`. Span stamps look up the already-loaded
`hermes_plugins.hermes_otel.tracer` module rather than importing a second
`hermes_otel` package.

## Second belt

If Phoenix cannot filter resource attributes, Engineering OS also registers
fail-open `post_*` / `on_session_start` hooks **only when Kanban env is
present**. Those hooks call `span.set_attribute` and never raise. Plugin
preflight clears the environment, so `register()` stays hook-free there.

## Exact equality

Correlation is attribute equality only:

- `hermes.kanban.task_id` == Kanban `tasks.id` (`t_<hex>`)
- `hermes.kanban.run_id` == Kanban `task_runs.id` (integer)
- `hermes.session.id` / `session.id` == Hermes session
- `gen_ai.tool.call.id` == `hermes.runtime.task_id` (never Kanban)
- `otel.trace_id` == span context

Missing evidence is `UNKNOWN`. No string-resemblance joins.

## Worker config path

Kanban workers set `HERMES_HOME` to the **profile directory**. Put the same
privacy YAML at:

- `~/.hermes/hermes_otel.yaml` (default CLI)
- `~/.hermes/profiles/<assignee>/hermes_otel.yaml` (workers)

`OTEL_PHOENIX_ENDPOINT` is also accepted by hermes-otel. Do not restart
`rp-friend` just to inject it; new worker processes inherit or read YAML.
