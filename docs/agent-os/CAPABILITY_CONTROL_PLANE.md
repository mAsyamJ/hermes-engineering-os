# Capability Control Plane

Canonical ADR: [ADR-HERMES-AGENT-OS.md](../architecture/decisions/ADR-HERMES-AGENT-OS.md).

This is **not** a replacement for [HERMES_AGENT_OS.md](HERMES_AGENT_OS.md) (VPS platform overview).

## What it is

A git-tracked subsystem under `/opt/hermes-engineering-os/agent_os/` plus Hermes plugin `agent-os-router` that:

- inventories native skills;
- maintains a machine registry + generated `SKILLS.md`;
- classifies tasks and ranks capabilities deterministically;
- discovers missing skills via Hermes Hub APIs under trust policy;
- emits compact `pre_llm_call` routing hints (&lt; 2000 chars).

## What it is not

- Not a second Kanban/orchestrator.
- Not a second skill database.
- Not a Hermes core fork.
- Not a second OTel stack.

## Quick commands

```bash
./scripts/agent-os/install-agent-os-plugin.sh
./bin/agent-os-verify
PYTHONPATH=/opt/hermes-engineering-os \
  /home/ubuntu/.hermes/hermes-agent/venv/bin/python -c 'from agent_os.registry.generate import regenerate; print(regenerate())'
./scripts/agent-os/rollback-agent-os.sh
```

## Layout

See `agent_os/` — `generate.py`, `router.py`, `resolver.py`, `plugin/`, `registry/`, `policies/`.
