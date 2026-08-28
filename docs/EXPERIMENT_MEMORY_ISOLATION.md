# Experiment Memory Isolation

Hermes built-in memory is file-backed `MEMORY.md` / `USER.md` per
`HERMES_HOME`. Same profile is shared writable memory:
**BLOCKED_MEMORY_ISOLATION**.

Isolation requires a dedicated experiment profile with empty memories.
`--ignore-rules` is PARTIAL (the memory tool may still write). True freeze of
production memory without copy is UNSUPPORTED.

Do not copy, delete, or rewrite production memory
(`/home/ubuntu/.hermes/profiles/rp-friend/memories/` and
`/home/ubuntu/.hermes/memories/`).

Phase 6 V1 confirmatory agent-cognition experiments are not enabled.
The fixture executor never loads Hermes memory: isolation PASS by construction.

Cross-arm fixture: shared namespace FAIL; isolated namespaces PASS;
fixture mode NA/PASS.
