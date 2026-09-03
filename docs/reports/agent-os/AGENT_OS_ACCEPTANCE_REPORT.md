# Agent OS Acceptance Report

**Stamp:** 2026-09-03T07:42Z  
**Verifier:** `scripts/agent-os/agent-os-verify.sh` + routing specialist selection + rollback proof

## Gates

| Gate | Result | Evidence |
|---|---|---|
| Routing proven (10 golden cases) | **PASS** | `tests/python/test_agent_os_router.py` 12/12 OK; live specialists selected for audit/Monad/AI/JTBD/startup/pitch/Next/Temporal |
| Skill discovery policy proven | **PASS** | T3 community auto-install refused; Hub search used; GitHub tree expansion recorded |
| Security policy proven | **PASS** | `mariano-aguero/...` **DANGEROUS** blocked (no `--force`); other T2 installs only after SAFE scan |
| Registry regeneration proven | **PASS** | Idempotent sha256; `~/.hermes/SKILLS.md` generated; 477 registry entries |
| Hermes health preserved | **PASS** | Dashboard `active`; skills list works; sessions/memories present; Hermes core untouched |
| Rollback proven | **PASS** | `rollback-agent-os.sh` disable/re-enable earlier in session |

## Runtime facts

- Hermes **v0.20.0 (2026.8.3)** / local `c0106e50`
- Plugin `agent-os-router` **enabled**
- Installed skills: **104** (was 87)
- Native bundles: **8** under `~/.hermes/skill-bundles/`
- `skills.guard_agent_created: true`
- Core patched: **No**
- Control plane: `/opt/hermes-engineering-os`

## Routing sample (post-install)

| Task | Selected |
|---|---|
| Solidity escrow audit | `solidity-security`, `web3-testing` |
| Payment escrow on Monad | `monad-wingman`, `solidity-security`, `web3-testing` |
| AI engineering math | `learn` |
| Interview → JTBD | `interview-to-jtbd` |
| Fatal assumption | `testing-business-ideas`, `grill-me` |
| Hackathon pitch | `made-to-stick` |
| Next.js production | `senior-frontend` (+ `nextjs-app-router-patterns` supporting) |
| Temporal workflows | `temporal-python-testing` |

## Bundles created (proven IDs only)

`monad-security`, `monad-contract-build`, `startup-validation`, `product-discovery`, `pitch-preparation`, `ai-engineering`, `frontend-production`, `web3-security-audit`

## Security evidence

- Blocked: `mariano-aguero/solidity-security-audit-skill` — skills-guard **DANGEROUS** (curl\|bash, supply-chain). Not force-installed.
- Allowed after SAFE scan: wshobson solidity-security/web3-testing, monad-wingman, interview-to-jtbd, testing-business-ideas, etc.

## Residual limitations (documented, non-blocking for completion bar)

1. `monskill` Hub fetch failed; Monad coverage via `why-monad` / `concepts` / `scaffold` / `monad-wingman`.
2. `nolly-studio/design-md` and `portdeveloper/monad-development` GitHub 404 at ingest time.
3. Phoenix/EOS OTel sink still exited (pre-existing); Agent OS uses fail-open `hermes.agent_os.*` span attributes only.
4. Not every aspirational bundle name from the original list was created — only those with proven installed members.
5. Hub labels many GitHub installs as `community` trust_level; Agent OS allowlist + scan gate still applied.

## Completion bar

ROUTING PROVEN + SKILL DISCOVERY PROVEN + SECURITY POLICY PROVEN + REGISTRY REGEN PROVEN + HERMES HEALTH PRESERVED + ROLLBACK PROVEN.
