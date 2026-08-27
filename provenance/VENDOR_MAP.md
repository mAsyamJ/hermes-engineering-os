# Vendor Adoption Map

Every tracked file under `vendor/` must have a `local_path` record below.

## COPIED

- local_path: `vendor/hermes-dashboard-base/LICENSE`
  upstream_repository: `NousResearch/hermes-example-plugins`
  upstream_path: `LICENSE`
  upstream_commit: `38fe0fb53eff98d477f807432e965429e665ca33`
  license: `MIT`
  adoption_type: `COPIED`
  modifications: `none`

- local_path: `vendor/hermes-dashboard-base/README.md`
  upstream_repository: `NousResearch/hermes-example-plugins`
  upstream_path: `example-dashboard/README.md`
  upstream_commit: `38fe0fb53eff98d477f807432e965429e665ca33`
  license: `MIT`
  adoption_type: `COPIED`
  modifications: `none`

- local_path: `vendor/hermes-dashboard-base/dashboard/manifest.json`
  upstream_repository: `NousResearch/hermes-example-plugins`
  upstream_path: `example-dashboard/dashboard/manifest.json`
  upstream_commit: `38fe0fb53eff98d477f807432e965429e665ca33`
  license: `MIT`
  adoption_type: `COPIED`
  modifications: `none`

- local_path: `vendor/hermes-dashboard-base/dashboard/dist/index.js`
  upstream_repository: `NousResearch/hermes-example-plugins`
  upstream_path: `example-dashboard/dashboard/dist/index.js`
  upstream_commit: `38fe0fb53eff98d477f807432e965429e665ca33`
  license: `MIT`
  adoption_type: `COPIED`
  modifications: `none`

- local_path: `vendor/hermes-dashboard-base/dashboard/plugin_api.py`
  upstream_repository: `NousResearch/hermes-example-plugins`
  upstream_path: `example-dashboard/dashboard/plugin_api.py`
  upstream_commit: `38fe0fb53eff98d477f807432e965429e665ca33`
  license: `MIT`
  adoption_type: `COPIED`
  modifications: `none`

- local_path: `vendor/cockpit/LICENSE`
  upstream_repository: `NousResearch/hermes-example-plugins`
  upstream_path: `LICENSE`
  upstream_commit: `38fe0fb53eff98d477f807432e965429e665ca33`
  license: `MIT`
  adoption_type: `COPIED`
  modifications: `none`

- local_path: `vendor/cockpit/README.md`
  upstream_repository: `NousResearch/hermes-example-plugins`
  upstream_path: `strike-freedom-cockpit/README.md`
  upstream_commit: `38fe0fb53eff98d477f807432e965429e665ca33`
  license: `MIT`
  adoption_type: `COPIED`
  modifications: `none`

- local_path: `vendor/cockpit/dashboard/manifest.json`
  upstream_repository: `NousResearch/hermes-example-plugins`
  upstream_path: `strike-freedom-cockpit/dashboard/manifest.json`
  upstream_commit: `38fe0fb53eff98d477f807432e965429e665ca33`
  license: `MIT`
  adoption_type: `COPIED`
  modifications: `none`

- local_path: `vendor/cockpit/dashboard/dist/index.js`
  upstream_repository: `NousResearch/hermes-example-plugins`
  upstream_path: `strike-freedom-cockpit/dashboard/dist/index.js`
  upstream_commit: `38fe0fb53eff98d477f807432e965429e665ca33`
  license: `MIT`
  adoption_type: `COPIED`
  modifications: `none`

- local_path: `vendor/ai-agent-board-ui/LICENSE`
  upstream_repository: `DanWahlin/ai-agent-board`
  upstream_path: `LICENSE`
  upstream_commit: `4f2965e72ad99e32e0375af837247cafb382f17c`
  license: `MIT`
  adoption_type: `COPIED`
  modifications: `none`

- local_path: `vendor/hivemind-ui/LICENSE`
  upstream_repository: `dip497/hivemind`
  upstream_path: `LICENSE`
  upstream_commit: `f4209b905c54342073822409f1da1a9f56da4981`
  license: `MIT`
  adoption_type: `COPIED`
  modifications: `none`

## MODIFIED

- local_path: `vendor/ai-agent-board-ui/event-coalescing.ts`
  upstream_repository: `DanWahlin/ai-agent-board`
  upstream_path: `packages/client/src/components/AgentPanel.tsx#L75-L168`
  upstream_commit: `4f2965e72ad99e32e0375af837247cafb382f17c`
  license: `MIT`
  adoption_type: `MODIFIED`
  modifications: `Hermes identifiers/types, sequence-safe grouping, generic noise filtering; removed ACP, .NET, task API, scheduler, and worktree assumptions`

- local_path: `vendor/hivemind-ui/agent-status-bus.ts`
  upstream_repository: `dip497/hivemind`
  upstream_path: `apps/desktop/src/renderer/src/agent-status-bus.ts`
  upstream_commit: `f4209b905c54342073822409f1da1a9f56da4981`
  license: `MIT`
  adoption_type: `MODIFIED`
  modifications: `Hermes profile/run events replace tile, PTY, Electron, scrape, notification, and inferred-completion state`

## PORT_REIMPLEMENTED / PATTERN_ONLY

- local_path: `dashboard/src/components/event-stream.ts`
  upstream_repository: `DanWahlin/ai-agent-board`
  upstream_path: `packages/client/src/components/{AgentPanel,TerminalView}.tsx`
  upstream_commit: `4f2965e72ad99e32e0375af837247cafb382f17c`
  license: `MIT`
  adoption_type: `PORT_REIMPLEMENTED`
  modifications: `host Hermes SDK, read-only events, no xterm or control actions`

- local_path: `dashboard/src/views/workspaces.ts`
  upstream_repository: `dip497/hivemind`
  upstream_path: `apps/desktop/src/renderer/src/{WorktreePicker,FrameNode,Canvas}.tsx`
  upstream_commit: `f4209b905c54342073822409f1da1a9f56da4981`
  license: `MIT`
  adoption_type: `PATTERN_ONLY`
  modifications: `fixed read-only repository to worktree to run hierarchy; no Electron, React Flow, lifecycle ownership, or persistence`

- local_path: `dashboard/src/views/tasks.ts`
  upstream_repository: `saltbo/agent-kanban`
  upstream_path: `apps/web/src/components/{TaskDetail,TaskCard}.tsx`
  upstream_commit: `82c082c5e3fcab75d33523e5b2b67df3716afc4a`
  license: `FSL-1.1-ALv2`
  adoption_type: `PATTERN_ONLY`
  modifications: `general information-density concept only; no source, CSS, assets, or layout copied`

