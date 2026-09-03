# Experiment Configuration Identity

Prospective snapshots hash canonical JSON (sorted keys) with SHA-256.

Captured where applicable: Hermes version/source SHA, declared model/provider,
profile name + redacted config hash, prompt/`SOUL.md` hash (text not stored),
skill tree hashes, tool-policy hash, benchmark artifact hash, evaluation
profile, `phase3-v1` / `phase4-eval-v1` / `phase5-perf-v1` / `phase6-exp-v1`,
environment fingerprint (OS, kernel, Python, sandbox image id).

Never persist `.env`, `auth.json`, provider keys, or values matching the
Engineering OS redaction denylist. Plant `FAKE_PHASE6_SECRET_ABC123` must not
appear in snapshots, DB, API, or UI.

Single-factor diff guard blocks undeclared dimension changes before READY.
