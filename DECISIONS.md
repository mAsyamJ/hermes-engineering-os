# Decisions

## Upstream adoption

- Official Hermes dashboard examples are copied as compatibility references.
- AI Agent Board event coalescing and Hivemind status replay are the only
  selectively modified donor logic.
- Agent Kanban remains design-only under FSL-1.1-ALv2.
- The installed `hermes_otel` plugin remains the Phase 2 repair target; no
  second OTel implementation is introduced.

## Runtime integration

- The product is a combined user plugin with no registered hooks or commands.
- Backend routes are GET-only and mounted by the existing dashboard process.
- Installation uses one external symlink so repository and live bytes are
  identical.
- Built-in plugin removal is not used because its handling of external symlink
  targets is unsafe for this deployment.

## GitHub

- Local Git and GitHub evidence are separate transports.
- Missing GitHub API authentication is represented as `BLOCKED_AUTH`, not a
  failed Phase 1 build.
- Only configured repositories may be inspected; browser-supplied paths are
  rejected.

## Deferred

- OTel dependency repair, Phoenix, and the dedicated analytics PostgreSQL
  server/databases/roles are Phase 2 or later.
- Interactive terminals, diff rendering, canvas editing, and lifecycle
  controls are deliberately excluded.

