# Hermes Engineering OS

Hermes Engineering OS is an upstream-first, read-only operator cockpit for the
existing Hermes Agent runtime. Hermes Kanban remains the only task lifecycle
authority. This repository adds evidence views and adapters; it does not own
tasks, retries, workers, scheduling, or worktrees.

Phase 1 provides:

- a native Hermes dashboard plugin;
- live read-only Hermes, Kanban, profile, worker, workspace, and plugin views;
- read-first local Git and GitHub evidence;
- explicit correlation namespaces;
- pinned upstream provenance and license controls;
- deterministic install, rescan, verification, and rollback scripts.

Operational entry points:

```bash
./scripts/verify.sh
./scripts/install-plugin.sh
./scripts/uninstall-plugin.sh
```

The live plugin is installed at `~/.hermes/plugins/engineering-os` as a guarded
symlink to this repository. Dashboard backend routes require a dashboard-only
restart after preflight. Hermes gateways must not be restarted for Phase 1.

