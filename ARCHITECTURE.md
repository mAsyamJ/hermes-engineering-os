# Architecture

Hermes Engineering OS is one combined user plugin. Its gateway registration is
side-effect-free; runtime behavior lives in authenticated dashboard routes.

```text
Hermes runtime ─┐
Hermes Kanban ──┼─> read-only adapters ─> GET-only FastAPI router ─> SDK IIFE
profiles/runs ──┤
allowlisted Git ┤
GitHub API ─────┘             BLOCKED_AUTH is a valid evidence state
```

## Authority boundaries

- Hermes owns sessions, tasks, runs, workers, scheduling, retries, profiles,
  worktrees, dispatch, and persistence.
- The canonical lifecycle identifier is `hermes.kanban.task_id`.
- Runtime task IDs, Kanban run IDs, sessions, turns, API requests, tool calls,
  Git SHAs, GitHub objects, and OTel IDs remain distinct typed dimensions.
- Correlation is emitted only from explicit metadata or unambiguous evidence.

## Read paths

- Kanban opens SQLite with `mode=ro`, `PRAGMA query_only=ON`, parameterized SQL,
  and a write-denying authorizer.
- Git commands use fixed argument vectors against `config/repositories.json`.
- GitHub CLI/API access is bounded and never reads or returns tokens.
- Plugin inventory runs in a timeout-protected subprocess; enabled plugins are
  not imported into the dashboard adapter.

## Dashboard

`dashboard/dist/index.js` is a classic IIFE using the host's
`window.__HERMES_PLUGIN_SDK__` React instance and `fetchJSON`. It provides
Overview, Tasks, Runs, Agents, Plugins, GitHub, Workspaces, and Observability
views plus a read-only footer slot.

No React copy, backend server, database, daemon, WebSocket, PTY, or task control
is bundled.

