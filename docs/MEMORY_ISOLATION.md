# Memory Isolation

Contract: `memory-snapshot-v1`  
Implementation: `engineering_os/experiments/memory_snapshot.py`

A snapshot contains only non-secret memory/context: authored `MEMORY.md` /
`USER.md`, optional `SOUL.md`, redacted config. It is hashed with
`canonical_dumps` and immutable after freeze.

Both experiment arms receive equivalent starting copies under distinct
writable `HERMES_HOME` trees. Writes do not go to production memory or the
other arm. Credentials, SSH, GitHub tokens, sessions, and caches are
excluded.

PAR-8 gate: identical initial hash, A/B cross-write isolation, production
memories unchanged, planted secrets absent. Disposable homes are destroyed
after evidence capture.

Cognition isolation harness: **READY**. Production shared-profile use remains
forbidden for actuation.
