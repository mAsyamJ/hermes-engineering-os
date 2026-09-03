# OTel Schema (hermes-otel c76bea84)

Observer fields are taken from Hermes hook signatures. Opaque IDs are not parsed except `session_id_from_turn_id`, which splits Hermes' documented `turn_id` format `"<session_id>:<task_id>:<hex>"` on the first colon — that is an explicit upstream helper, not a heuristic correlation to Kanban IDs.

## Span hierarchy

```
session / agent (root)
  └── llm.*
        ├── api.*          (HTTP attempt; tokens live here)
        └── tool.*         (sibling under the LLM turn, or nested via span context)
  └── subagent.*           (when delegation occurs)
        └── child session root (linked or nested)
```

Integration tests in pinned upstream verify Session → LLM → API → Tool parent/child via `InMemorySpanExporter` (`tests/integration/test_span_hierarchy.py`, `test_session_lifecycle.py`, `test_subagent_hierarchy.py`). Gate 2.1: 656 passed including those.

## Hermes observer identifiers (explicit)

| Hook | Explicit IDs |
|---|---|
| `on_session_start` / `on_session_end` | `session_id` |
| `pre_llm_call` / `post_llm_call` | `session_id` |
| `pre_api_request` / `post_api_request` / `api_request_error` | `task_id` (runtime), `session_id` |
| `pre_tool_call` / `post_tool_call` | `task_id` (runtime), `tool_name` |
| `subagent_start` / `subagent_stop` | `child_session_id`, `parent_session_id` |
| approval hooks | `turn_id` (session recovered by documented split) |

`task_id` on API/tool hooks is **`hermes.runtime.task_id`**. It is not `HERMES_KANBAN_TASK`.

## Plugin attributes (selected)

See also upstream `website/docs/reference/span-attributes.md`.

Resource: `service.name`, `service.version`, `openinference.project.name`, plus `OTEL_RESOURCE_ATTRIBUTES` merged by the OTel SDK `Resource.create()`, plus config `resource_attributes` / `global_tags`.

Session: `hermes.session.id`, `session.id`, `hermes.session.kind`, turn summary `hermes.turn.*`.

LLM: `llm.model_name`, `llm.provider`, `input.value` / `output.value` (privacy-gated).

API: `llm.token_count.*`, `gen_ai.usage.*`, `http.duration_ms`, error `error.type`, `hermes.retry.count`.

Tool: `tool.name`, `gen_ai.tool.call.id` (runtime task_id), `hermes.tool.outcome`.

Subagent: `hermes.subagent.child_session_id`, `hermes.subagent.parent_session_id`. Supported by upstream; NA only if a live Hermes version lacks the hook.

## Fail-open / Noop

If OpenTelemetry packages are missing or `init()` cannot enable a backend, `tracer.is_enabled` is false and hooks return immediately (`tests/unit/test_tracer_noop.py`). Batch export uses `BatchSpanProcessor` with independent worker threads; enqueue is non-blocking. Missing Phoenix does not raise into Hermes.

## Secrets

Default capture: conversation history off. Phase 2 production policy turns `capture_previews` off so `input.value` / `output.value` / prompt bodies are never set. Tool command/target metadata still flow (upstream privacy mode). `HERMES_OTEL_DEBUG` is not left enabled.
