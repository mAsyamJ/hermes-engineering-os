#!/usr/bin/env bash
# Isolated restore rehearsal. Never writes live Hermes, Kanban, or sudoers.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
src="${1:-}"
if [[ -z "$src" ]]; then
  src="$(ls -1d "$ROOT/.runtime/pag2-backup/"*/ 2>/dev/null | tail -n 1 || true)"
fi
if [[ -z "$src" || ! -d "$src" ]]; then
  echo "NO_BACKUP: run scripts/pag2-backup.sh first (secret-free summary only)"
  exit 0
fi
work="$(mktemp -d /tmp/pag2-restore-rehearsal.XXXXXX)"
trap 'rm -rf "$work"' EXIT
cp -a "$src"/. "$work/"
if rg -q "FAKE_PAG2_SECRET_ABC123|BEGIN OPENSSH PRIVATE|production-approval.ed25519" "$work" 2>/dev/null; then
  echo "FAIL: backup rehearsal found secret material" >&2
  exit 1
fi
test -f "$work/summary.txt"
echo "REHEARSAL_PASS work=$work src=$src"
echo "NOTE: this does not restore live DB or units."
