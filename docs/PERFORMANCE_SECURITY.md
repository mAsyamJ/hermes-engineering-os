# Performance Security

Phase 5 stores IDs, counts, and aggregates. It must not copy raw prompts,
conversation bodies, source code, secrets, or environment values.

Plant: the string defined in `scripts/performance-privacy-test.sh`. Verify
absence via that script against dumps, API, logs, and git.

API remains GET-only. Postgres stays unpublished. Reader cannot write.
Writer cannot CONNECT to `phoenix`.
