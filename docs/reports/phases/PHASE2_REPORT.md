# Phase 2 Implementation Report

Status: **COMPLETE**  
Completed: 2026-08-27  
Product repository: `/opt/hermes-engineering-os`  
Do not start Phase 3 from this report.

## Delivered

- Pinned `hermes-otel` `c76bea84` remains byte-identical to the installed plugin.
- Active Hermes venv received OpenTelemetry **1.44.0** (not lockfile 1.41.0) so
  `protobuf==7.35.1` is preserved.
- Dedicated observability Postgres + Phoenix 20.4.0 on loopback `:6006`,
  isolated network/volume, no Collector, no RetroPick attach.
- Engineering OS stamps explicit `HERMES_KANBAN_*` onto
  `OTEL_RESOURCE_ATTRIBUTES` before hermes-otel `Resource.create()`, and onto
  live hermes-otel spans via fail-open `post_*` hooks when Kanban env is
  present. Preflight stays hook-free.
- GET-only `/observability*` APIs and UI read Phoenix GraphQL. Kanban remains
  canonical. Observability is derived and fail-open.
- Disposable board `eos-phase2-obs` plus fixture-repo smoke (LLM, `read_file`,
  `terminal`). `rp-friend` PID **924** was not restarted.

## Live state

| Item | Value |
|---|---|
| Engineering OS HEAD after local commits | see git log |
| Dashboard | `127.0.0.1:9119` PID `5715` (dashboard-only restart) |
| Default gateway | PID `2381797` unchanged |
| `rp-friend` | PID `924` unchanged |
| Phoenix | `HEALTHY` `127.0.0.1:6006` |
| Observability Postgres | `HEALTHY`, no host port |
| `/observability` | `AVAILABLE`, `fail_open: true` |
| GitHub API | `BLOCKED_AUTH` (non-blocking) |
| Production Kanban | `retropick-markets-release` 101 tasks, 0 running |
| Storage | 23.5 GiB free, 67.1% used |
| hermes_engineering DB | empty Phase 3 substrate |

## Reload classification

| Key | Result |
|---|---|
| `DISPOSABLE_RUNTIME_OTEL` | **PASS** |
| `RP_FRIEND_WORKER_OTEL` | **PASS** (child workers / profile `HERMES_HOME`; no PID 924 restart) |
| `DEFAULT_GATEWAY_OTEL` | **DEFERRED** |
| Dashboard-only restart | **PASS** (`4021289` → `5715`) |

## Correlation evidence (exact equality)

| Field | Smoke CLI (`t_phase2obs`) | Worker-env (`t_d1c34420`) |
|---|---|---|
| `hermes.kanban.task_id` | `t_phase2obs` | `t_d1c34420` |
| `hermes.kanban.run_id` | `9001` | `2` |
| `hermes.kanban.board` | `eos-phase2-obs` | `eos-phase2-obs` |
| session | `20260827_165321_b93fb7` | `20260827_170441_968c90` |
| `otel.trace_id` | `a218d17c27cf6dae855ead23e20389d1` | `3c6a188a33999ef09cf0bc74c2cae76b` |
| spans | `llm.*`, `tool.read_file`, `tool.terminal` | stamped session root + LLM |

Runtime `task_id` remains `gen_ai.tool.call.id`, not the Kanban id.

## Stage gates

| Gate | Result |
|---|---|
| 2.0 entry freeze | PASS |
| 2.1 isolated hermes-otel pytest 656 | PASS |
| 2.2 venv OTel 1.44.0 | PASS (pre-existing certifi mismatch recorded) |
| 2.3 schema docs | PASS |
| 2.4 ephemeral Phoenix E2E | PASS |
| 2.5–2.8 dedicated Postgres+Phoenix persist | PASS (`ba6cc2d4d520b3a31008f282b95240ab`) |
| 2.9–2.10 correlation | PASS |
| 2.11 real Hermes smoke | PASS |
| 2.12–2.14 fail-open | PASS (Hermes exit 0; EOS `DEGRADED`) |
| 2.15 privacy | PASS (`FAKE_PHASE2_SECRET_ABC123` not in Phoenix/API) |
| 2.16–2.17 EOS API/UI | PASS |
| 2.18 reload classification | PASS / DEFERRED as table above |
| 2.19 plugin regression | PASS (preflight, 13 hermes_otel hooks, live views) |
| 2.20 production boundary | PASS (Git HEAD/porcelain vs 2.0; Docker excl. `hermes-eos-*`; gateway PIDs) |
| 2.21 resource | PASS (≥20 GiB, used < 80%; Phoenix ~402 MiB, PG ~37 MiB) |
| 2.22 backup/restore | PASS isolated (`restored_user_tables=65`) |
| 2.23 docs | PASS |
| 2.24 local commits | PASS (no push) |

## Non-blocking leftovers

- GitHub API `BLOCKED_AUTH`
- Hermes source `package-lock.json` dirty (do not repair)
- `uv pip check` certifi pin mismatch (do not change certifi)
- Rehearsal `markets-api` unhealthy (pre-existing)
- Metrics OTLP `/v1/metrics` 405 on Phoenix 20.4.0; traces ingest without Collector
- Default gateway process still predates OTel repair (`DEFAULT_GATEWAY_OTEL=DEFERRED`)

## Production invariants held

- No RetroPick source edits; Git HEAD unchanged
- No restart of `hermes-gateway` or `hermes-gateway-rp-friend`
- No Collector, AgentMemory, Graphiti, Hivemind, AI Agent Board, Agent Kanban
- Phoenix Elastic License 2.0 recorded; source not vendored
