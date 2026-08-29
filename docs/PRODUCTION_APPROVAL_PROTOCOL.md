# Production Approval Protocol

Contract: `approval-ed25519-v1`  
PAR contract: `par-v1`

TEST authority remains `approve-hmac-sha256-v1-test` in
`engineering_os/adaptation/approval.py`. It cannot authorize `PRODUCTION_*`.

## Canonical binding

Deterministic JSON (`canonical_dumps`) over:

request_id, recommendation_id, policy_id, policy_hash, policy_version,
approval_stage, scope, maximum_exposure, candidate_config_hash, fallback_hash,
rollback_hash, expiry, nonce, created_at, contract_version,
runtime_release_hash, live_patch_hash, actuator_contract_version,
trust_fingerprint.

## Verification

- Detached Ed25519 signature
- Signer identity
- Scope / class isolation
- Expiry
- Policy hash, stage, candidate hash, rollback hash, exposure
- Runtime identity (release hash, live patch hash, actuator contract, trust fingerprint)
- Nonce ledger (replay → reject)
- Caller-supplied `public_key` is **ignored**. Only
  `/etc/hermes-eos/approval-trust.pub` is used, and only when ubuntu cannot
  write that file or `/usr/local/lib/hermes-eos/approval-verifier`.

## Production status

Until H1 installs a **protected** public trust (not agent-writable),
`verify_production_authorization()` returns `BLOCKED_SECURITY_BOUNDARY`.
A correct signature over an agent-replaceable trust root is still not a
secure human grant. After H1, verification uses the protected file only
and fail-closes if that file is agent-writable.

No production signing private key may exist on an agent-readable filesystem.
Ephemeral keys are allowed only in unit tests and must be TEST/rehearsal class.
