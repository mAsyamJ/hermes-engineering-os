# Evaluation Artifacts

Derived evidence stored only under Engineering OS control:

`/var/lib/hermes-engineering-os/evaluation-artifacts/` (mode 0700)

Not inside `/opt/retropick` or production worktrees.

## Methods

1. `COMMIT_SNAPSHOT` — `git archive --format=tar <sha>` from an allowlisted repository. Never `git checkout` of production.
2. `BASE_COMMIT_PLUS_TRACKED_PATCH` — archive of base SHA plus `git diff --binary HEAD` of tracked files.
3. Else no artifact.

## Recorded fields

artifact_id, repository, task id, run id if known, base commit, candidate
commit, patch hash, content hash (SHA-256 of canonical payload), created_at,
capture method, size, secret scan status.

## Guards

- Skip `.env`, credentials, `node_modules`, caches, database files, large binaries
- Untracked files are not archived unless the profile allowlists a path
- Max 20 MiB per file, 80 MiB per artifact
- Secret scan must PASS or capture becomes INSUFFICIENT_EVIDENCE
- Duplicate content hash reuses the same artifact_id

## Retention

Retain while an evaluation_run references the hash. Do not destructively
expire in Phase 4. Recreate from git SHA when the method is COMMIT_SNAPSHOT.
Tracked patches may not be recreatable if the source workspace is gone.
