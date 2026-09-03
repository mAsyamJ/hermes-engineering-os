# License Adoption Report

Audit basis: exact repository revisions in `provenance/UPSTREAM_LOCK.yaml`.
This report records engineering policy, not legal advice.

## Approved adoption

- `NousResearch/hermes-example-plugins` is MIT. Narrow copies are permitted
  with the copyright and license notice retained.
- `DanWahlin/ai-agent-board` is MIT. Only the pure event-coalescing logic is
  modified and retained; the application runtime is not adopted.
- `dip497/hivemind` is MIT. Only the status-bus transition/replay logic is
  modified and retained; Electron, PTY, filesystem, and canvas systems are not
  adopted.

## Upstream dependency only

- `briancaffey/hermes-otel` is Apache-2.0. The existing installed plugin is the
  Phase 2 repair target. Phase 1 keeps a pristine pinned comparison checkout
  and vendors no OTel source.

## Design-only

- `saltbo/agent-kanban` is FSL-1.1-ALv2 at the pinned revision. Current-version
  source is not adopted because the competing-use restriction and per-version
  future-license date are not suitable for an unrestricted product vendor
  tree. General ideas may inform a clean implementation; no source, CSS,
  artwork, or expressive layout is copied.

## Excluded dependencies and assets

- AI Agent Board's React 19, Framer Motion, xterm, REST backend, WebSocket
  contract, task state, scheduler, PR mutation, and worktree ownership.
- Hivemind's Electron, `node-pty`, screen scraping, React Flow canvas,
  filesystem watchers, Git mutation, and desktop IPC.
- Strike Freedom theme YAML, remote artwork, names, and branded decorative
  presentation.
- All donor databases, servers, schedulers, workers, and orchestration loops.

