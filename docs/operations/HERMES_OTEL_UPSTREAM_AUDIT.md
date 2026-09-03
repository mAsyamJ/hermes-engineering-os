# hermes-otel Upstream Audit

Pinned: 2026-08-27  
Gate 2.1: **PASS**

## Identity

| Field | Value |
|---|---|
| Upstream | https://github.com/briancaffey/hermes-otel.git |
| SHA | `c76bea8434e6cc8b51c835bb57c514a5eb71e857` |
| Checkout | `/opt/hermes-engineering-os/upstream/hermes-otel` |
| Installed plugin | `/home/ubuntu/.hermes/plugins/hermes_otel` |
| License | Apache-2.0 |
| License sha256 | `43e9d7fc433a06ad130162fa77c108088fb04369a651a386eb2ff2b0cf85817f` |
| Plugin version (plugin.yaml) | `1.0` |
| Package version (pyproject) | `0.1.0` |

## Installed vs pristine

Compared every non-cache file under the installed plugin with `upstream/hermes-otel/hermes_otel`:

- installed files: 44
- upstream package files: 44
- only-installed: 0
- only-upstream: 0
- content diffs: 0

The installed plugin is byte-identical to the pinned package. It was **not** overwritten.

## Dependencies (authoritative from pinned source)

Runtime (`plugin.yaml` / `requirements.txt` / `pyproject.toml`):

- `opentelemetry-api<2`
- `opentelemetry-sdk<2`
- `opentelemetry-exporter-otlp-proto-http<2`

Optional: `langsmith`, `pyyaml` (env/defaults work without pyyaml).  
Dev extra: pytest, coverage, black, ruff, pyyaml, OTel packages.  
E2E extra: requests, openai.

Pinned `uv.lock` for isolated tests: OpenTelemetry **1.41.0** (protobuf 6.x). That lock is **not** used in the production Hermes venv because production already has `protobuf==7.35.1`.

## Tests (isolated)

Environment: `/opt/hermes-engineering-os/.runtime/hermes-otel-uv`  
Command: `uv sync --extra dev --extra e2e && uv run --extra dev pytest --tb=short`

| Tier | Result |
|---|---|
| UNIT + INTEGRATION | **656 passed**, 15 deselected (e2e/smoke), coverage 91.92% (≥85%) |
| Phoenix E2E | deferred to Stage 2.4 |
| Production venv | **unchanged** |

Evidence: `evidence/phase2/hermes-otel-upstream-pytest.txt`

## Kanban correlation in upstream

hermes-otel does **not** read `HERMES_KANBAN_TASK`, `HERMES_KANBAN_RUN_ID`, `HERMES_KANBAN_BOARD`, or `HERMES_KANBAN_WORKSPACE`. Correlation is Engineering OS glue (Stage 2.9), not an upstream patch.

## Gate 2.1

**PASS.** Upstream SHA pinned, license recorded, installed-vs-upstream understood, unit+integration PASS, no production mutation.
