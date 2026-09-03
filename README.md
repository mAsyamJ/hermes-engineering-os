# Hermes Engineering OS

Canonical overview (5W+1H, C4, live vs intended, capability matrix):
[docs/agent-os/HERMES_AGENT_OS.md](docs/agent-os/HERMES_AGENT_OS.md).

Hermes Engineering OS is an upstream-first, read-only operator cockpit for the
existing Hermes Agent runtime. Hermes Kanban remains the only task lifecycle
authority. This repository adds evidence views and adapters; it does not own
tasks, retries, workers, scheduling, or worktrees.

Phases 1–7, PAR, PAG-1, and PAG-2 autonomous work are in this tree.
Production adaptation stays **DISABLED**. Start with the overview above, not
the Phase 1 list alone.

Phase 1 still provides:

- a native Hermes dashboard plugin;
- live read-only Hermes, Kanban, profile, worker, workspace, and plugin views;
- read-first local Git and GitHub evidence;
- explicit correlation namespaces;
- pinned upstream provenance and license controls;
- deterministic install, rescan, verification, and rollback scripts.

Operational entry points:

```bash
./bin/hermes-eos-verify
./scripts/deployment/install-plugin.sh
./scripts/deployment/uninstall-plugin.sh
```

The live plugin is installed at `~/.hermes/plugins/engineering-os` as a guarded
symlink to this repository. Dashboard backend routes require a dashboard-only
restart after preflight. Hermes gateways must not be restarted for Phase 1.

## Documentation

See the [documentation map](docs/README.md).
