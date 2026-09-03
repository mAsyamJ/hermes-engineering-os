# Evaluation Capability Matrix

Gate 4.1. Captured 2026-08-27 against live Kanban, `hermes_engineering`,
allowlisted Git, GitHub CLI, and repository configs. Do not implement
repository evaluation commands beyond this matrix.

Ratings: **SUPPORTED**, **SUPPORTED_WITH_SANDBOX**, **PARTIAL**,
**BLOCKED_EVIDENCE**, **BLOCKED_AUTH**, **BLOCKED_RESOURCE**,
**BLOCKED_ENVIRONMENT**, **UNSUPPORTED**.

## Historical production cohort (101)

| Evidence | Rating | Notes |
|---|---|---|
| Exact candidate commit | BLOCKED_EVIDENCE | `git_facts.commit_sha` is null for all 103 rows |
| Reproducible run workspace | BLOCKED_EVIDENCE | current worktrees are not run-bound artifacts |
| Trace | BLOCKED_EVIDENCE | 0 production trace metrics; `DEFAULT_GATEWAY_OTEL=DEFERRED` |
| CI | BLOCKED_AUTH | 21 BLOCKED_AUTH; 0 AVAILABLE |
| Structured acceptance criteria | UNSUPPORTED | free-text only; no typed mapping |
| Repository association | PARTIAL | workspaces exist under `/opt/retropick`, `.worktrees`, `/opt/worktrees`, Kanban workspaces |

**Eligible historical production tasks: 0.** Expected. Not a framework failure.

## Fixture repository

Path: `/opt/hermes-engineering-os/.runtime/fixture-repo` (disposable).
Tracked template: `tests/fixtures/tiny-repo/` (README only) plus Phase 4
`tests/evaluation/fixture_src/`.

| Evaluator | Rating | Notes |
|---|---|---|
| build | SUPPORTED_WITH_SANDBOX | `python3 -m compileall src` |
| tests | SUPPORTED_WITH_SANDBOX | `python3 -m unittest discover -s tests` |
| regression | SUPPORTED_WITH_SANDBOX | same command on baseline + candidate |
| lint | SUPPORTED_WITH_SANDBOX | `python3 scripts/lint.py` (deterministic, no network) |
| typecheck | SUPPORTED_WITH_SANDBOX | `python3 scripts/typecheck.py` (`ast.parse`) |
| architecture_policy | SUPPORTED | encoded forbidden import prefixes |
| scope_policy | SUPPORTED | encoded forbidden paths |
| security | SUPPORTED | path/secret guards; no `npm audit` |
| acceptance | UNSUPPORTED | fixture has no structured criteria |
| CI | NOT_APPLICABLE | `github: null` |
| Android / Go / pnpm | UNSUPPORTED | fixture is Python |

## RetroPick (`/opt/retropick`)

Authoritative commands from `package.json` and `.github/workflows/ci.yml`:

- `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`
- `go -C apps/backend build ./...`, `go -C apps/backend test ./...`
- CI extras: gitlink, OpenAPI/AsyncAPI drift, graphify, Playwright, Postgres migrations

| Evaluator | Rating | Notes |
|---|---|---|
| build (full turbo/pnpm) | BLOCKED_RESOURCE | node_modules + Playwright would violate storage headroom |
| tests (full `pnpm test`) | BLOCKED_RESOURCE | same |
| tests (`go test ./...`) | BLOCKED_ENVIRONMENT | no vendor/; GOPROXY requires network; some tests need Postgres. Must not use production DBs |
| lint / typecheck | BLOCKED_RESOURCE | requires pnpm install |
| regression | PARTIAL | comparable only if both artifacts run the same supported evaluator |
| scope_policy | SUPPORTED | Tier A path rules in profile |
| architecture_policy | PARTIAL | only explicit profile rules; no LLM architecture guess |
| security (`npm audit`) | UNSUPPORTED | network-varying; time-varying; forbidden as immutable correctness |
| CI | BLOCKED_AUTH | non-blocking |
| in-place evaluation of `/opt/retropick` | UNSUPPORTED | mutating commands forbidden on production tree |

Stage 4.14 task-linked RetroPick canary: **DEFERRED_INSUFFICIENT_EVIDENCE**.

## RetroPick Android (`/opt/retropick-android`)

`package.json` scripts: `next` build/dev, `eslint .`. Gradle 8.13. No
`.github/workflows`.

| Evaluator | Rating |
|---|---|
| eslint / Next build / Gradle | BLOCKED_RESOURCE |
| CI | UNSUPPORTED (no workflows) + GitHub BLOCKED_AUTH |

## Sandbox / toolchain inventory (host)

| Tool | Present | Phase 4 use |
|---|---|---|
| `hermes-eos-analytics:phase3` | yes, `sha256:6a01af80fa2d…` 368MB | controller + candidate image (no extra pull) |
| Python 3.11 in image / 3.12 host | yes | fixture evaluators |
| Go 1.26.5 host / module cache 468M | yes | not copied into candidate; RetroPick go DEFERRED |
| Node 22 / pnpm 10 | yes on host | not installed in candidate |
| OpenJDK 21 | yes | Android DEFERRED |
| Docker socket | host only | never in candidate |
| Root free | 22.81 GiB | must stay ≥20 GiB |

## Evaluator registry decisions used by phase4-eval-v1

Implement only matrix-supported paths. Mark RetroPick Tier C as
`BLOCKED_RESOURCE` / `BLOCKED_ENVIRONMENT` in `retropick.yaml` rather than
inventing a slim substitute CI. Fixture Python evaluators qualify the engine.
