# Production Authority Threat Model

Re-audited 2026-08-29 during PAR-0. The Phase 7 snapshot is still current.

## Actor

Autonomous worker: `ubuntu` uid 1000 on `retropick-prod-01`.

- `(ALL) NOPASSWD: ALL` sudo (cloud-init)
- write access to `/opt/hermes-engineering-os` and `/home/ubuntu/.hermes`
- user systemd units (gateways, dashboard, EOS timers)
- Docker via sudo (ubuntu is not in the docker group)
- `gh` authenticated with **admin** on `mAsyamJ/hermes-engineering-os`

## Repository trust

- Public repo, default branch `main`
- No branch protection
- No GitHub Environments
- No rulesets
- Same-account GitHub approval is not a human boundary: the agent can change protections

## Can the autonomous agent...

| Action | Answer |
|---|---|
| Modify verifier code? | YES |
| Replace trusted keys? | YES |
| Restart verifier / user services? | YES |
| Replace control DB (sudo docker exec as admin)? | YES |
| Impersonate operator locally? | YES |
| Change sudo-owned files? | YES |
| Modify GitHub protections? | YES |
| Approve its own deployment? | YES, for any path entirely on this VPS |

If YES to any required production approval path, that path is **not secure**.

## Conclusion

Any approval mechanism entirely controlled by this VPS is self-attestation.
A local HMAC key, local `--approve`, agent Git commit, agent approval file,
root-owned verifier replaceable through sudo, or local public-key verifier
whose trusted key ubuntu can replace is **not** a secure human boundary.

Status: `BLOCKED_SECURITY_BOUNDARY` / `READY_FOR_OPERATOR_BOOTSTRAP`.
