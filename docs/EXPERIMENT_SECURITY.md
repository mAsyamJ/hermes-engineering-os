# Experiment Security

- GET-only dashboard and sidecar routes. POST/PUT/PATCH/DELETE return 405.
- Trusted YAML definitions reject unknown fields, shell/command keys, and
  secret-like values.
- Config snapshots redact credentials. Plant `FAKE_PHASE6_SECRET_ABC123`
  must not leak (`scripts/experiment-privacy-test.sh`).
- Fixture executor does not invoke Hermes inference.
- No production routing, promotion, or profile/skill/prompt mutation.
- Postgres remains unpublished. Writer cannot CONNECT to `phoenix`.
