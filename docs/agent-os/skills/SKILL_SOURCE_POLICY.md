# Skill Source Policy

- **Native SoT:** `~/.hermes/skills/` (and profile-local skills dirs).
- **Hub install:** `hermes skills install <id> -y` only — never `--force`, never `npx skills add` for Hermes.
- **Inspect:** prefer `hermes_cli.skills_hub.inspect_skill` / `tools.skills_hub` over parsing Rich CLI.
- **Search:** `hermes skills search … --json` when scripting.
- **Taps:** `hermes skills tap add <repo>` for T2 allowlisted sources.
- **Curated seed list:** `agent_os/registry/sources.yaml` (per-repo stubs until expanded).
- **Agent OS registry:** index only — `agent_os/registry/skills.registry.json`.
- **Generated human view:** `~/.hermes/SKILLS.md` + `agent_os/registry/SKILLS.md`.
- **Learned skills:** `~/.hermes/skills/learned/` + mirror `agent_os/knowledge/skills/learned/`.
- **find-skills skill:** remain installed but is the npx ecosystem helper; Agent OS resolver does not use it as the Hermes installer.
