# Adaptation Approval Boundary

Gate 7.2. Honest classification of human authorization on this VPS.

## Production human approval

**Classification: BLOCKED_CAPABILITY**

The autonomous worker runs as `ubuntu` (uid 1000) with:

- write access to `/opt/hermes-engineering-os` and `/home/ubuntu/.hermes`
- `NOPASSWD: ALL` sudo (cloud-init), including `sudo docker exec` as `eos_admin`
- `gh` authenticated with admin on `mAsyamJ/hermes-engineering-os`
- all Hermes units as **user** systemd services the agent can restart
- no separate operator user, hardware token, GitHub environment, or branch protection

A local CLI `--approve`, an agent-created file, an agent Git commit, or a
root-owned verifier the agent can `sudo` replace is **self-attestation**.
It is not a secure human boundary.

`adapt approve` (production) therefore returns `BLOCKED_APPROVAL_BOUNDARY`
and does not grant any PRODUCTION_* scope.

## Test approval

**Classification: TEST_ONLY**

Algorithm: `approve-hmac-sha256-v1-test`

Key path: `.runtime/adaptation/keys/test-approval.key` (gitignored, mode 0600)

The HMAC message binds:

`algorithm|stage|approval_class|recommendation_id|policy_hash|policy_version|scope|max_exposure|expiry|rollback_hash|operator`

`approval_class` is always `TEST`. Allowed scopes:

- FIXTURE
- BENCHMARK
- NON_PRODUCTION

The verifier **rejects** TEST signatures when scope is any of:

- PRODUCTION_SHADOW
- PRODUCTION_CANARY
- PRODUCTION_BOUNDED
- PRODUCTION_FULL

A TEST key cannot authorize production even if an operator passes `--yes`.
There is no production key on this VPS. Production algorithm
`approve-hmac-sha256-v1` is defined but has no key → blocked.

## Two stages

| Stage | Authorizes | Does not authorize |
|---|---|---|
| Approval A | shadow + bounded fixture/non-production canary | broader promotion, production |
| Approval B | wider NON_PRODUCTION (test) or production (blocked) | automatic scope expansion |

Successful canary does not imply Approval B.

## Future secure boundaries (not implemented)

A secure production boundary would require an off-VPS signer, a Unix user
the agent cannot impersonate **and** cannot sudo into, or GitHub Environment
required reviewers with org rules preventing admin bypass. None of these
exist here. Phase 7 does not fake them.
