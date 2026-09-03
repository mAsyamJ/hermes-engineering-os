# Profile Topology

## Live topology (do not invent a parallel fleet)

Kanban orchestrator profile: `rp-release-orchestrator`.

Specialist profiles already present under `~/.hermes/profiles/`:

- rp-friend (gateway / dispatcher intended owner when unmasked)
- rp-android, rp-web, rp-backend-markets, rp-api-contract
- rp-qa-e2e, rp-review-security, rp-recovery-architect, rp-sre-release

Each profile is an isolation boundary with its own config, memories, sessions, skills copy, and credentials where configured.

## Rules

- One writer per profile — do not run concurrent agents against the same profile home.
- Do not copy private memories between profiles.
- Agent OS does **not** create researcher/builder/auditor profiles in this delivery; routing works in the default home and respects existing RetroPick isolation.
- Future shared curated skills may use `skills.external_dirs` with filesystem read-only protection — not enabled in this change.
