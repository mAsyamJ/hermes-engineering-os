# Adaptation Security

- GET-only dashboard and sidecar APIs. POST/PUT/PATCH/DELETE → 405.
- No approval button. No `--yes` production grant.
- TEST HMAC cannot authorize PRODUCTION_* scopes.
- Production approval is `BLOCKED_CAPABILITY`.
- Policy YAML rejects executable keys.
- Control roles cannot connect to phoenix.
- Plant secret `FAKE_PHASE7_SECRET_ABC123` must not appear in bundles, dumps,
  audit API, UI, logs, backups, or Git.
- Approval signatures are omitted from `/adaptation/audit`.
