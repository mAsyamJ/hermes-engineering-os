#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$ROOT/.runtime/fixture-repo"

if [[ -e "$TARGET" && ! -d "$TARGET/.git" ]]; then
  echo "refusing to replace non-fixture path: $TARGET" >&2
  exit 1
fi
rm -rf "$TARGET"
mkdir -p "$TARGET"
cp -a "$ROOT/tests/fixtures/tiny-repo/." "$TARGET/"
git init -b main "$TARGET" >/dev/null
(
  cd "$TARGET"
  git add README.md
  GIT_AUTHOR_NAME=fixture GIT_AUTHOR_EMAIL=fixture@example.invalid \
  GIT_COMMITTER_NAME=fixture GIT_COMMITTER_EMAIL=fixture@example.invalid \
  GIT_AUTHOR_DATE=2026-01-01T00:00:00Z GIT_COMMITTER_DATE=2026-01-01T00:00:00Z \
    git commit -m "fixture: initial state" >/dev/null
  git branch fixture/task-t_00000000
)
echo "PASS: disposable fixture repository created at $TARGET"

