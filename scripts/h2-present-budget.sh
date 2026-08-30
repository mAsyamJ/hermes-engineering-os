#!/usr/bin/env bash
# Present H2 HARD vs SOFT vs UNAVAILABLE. Never writes LLM_BUDGET_AUTHORIZATION.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
echo "HUMAN ACTION REQUIRED — H2"
echo
python3 -m engineering_os.experiments budget-limits real-model-sol-vs-terra-v2
echo
echo "Reply phrase (exact):"
echo "AUTHORIZE EXPERIMENT fa1b83d8583f832ac8ed15f456f12f9856aca1b26689d8859f1d6e5a7e3a870a WITH THE ABOVE HARD LIMITS"
echo
echo "Do not copy experiments/templates/LLM_BUDGET_AUTHORIZATION.example.json."
echo "After H1 status=PASS and the exact phrase, persist with:"
echo "  scripts/h2-write-authorization.sh '<created_by>' '<rfc3339-expiry>'"
echo "Track B does not route production Kanban."
