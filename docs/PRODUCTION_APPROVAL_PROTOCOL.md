# Production Approval Protocol

Contract: `approval-ed25519-v1`  
PAR contract: `par-v1`

TEST authority remains `approve-hmac-sha256-v1-test` in
`engineering_os/adaptation/approval.py`. It cannot authorize `PRODUCTION_*`.

## Canonical binding

Deterministic JSON (`canonical_dumps`) over:

request_id, recommendation_id, policy_id, policy_hash, policy_version,
approval_stage, scope, maximum_exposure, candidate_config_hash, fallback_hash,
rollback_hash, expiry, nonce, created_at, contract_version.

## Verification

- Detached Ed25519 signature
- Signer identity
- Scope / class isolation
- Expiry
- Policy hash, stage, candidate hash, rollback hash, exposure
- Nonce ledger (replay → reject)

## Production status

`verify_production_authorization()` always returns
`BLOCKED_SECURITY_BOUNDARY` on this VPS. A correct signature over an
agent-replaceable trust root is still not a secure human grant.

No production signing private key may exist on an agent-readable filesystem.
Ephemeral keys are allowed only in unit tests and must be TEST/rehearsal class.
