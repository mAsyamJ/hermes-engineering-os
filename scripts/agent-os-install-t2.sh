#!/usr/bin/env bash
# Install a narrow allowlisted T2 specialist set. NEVER passes --force.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
LOG="$ROOT/tests/evidence/agent-os-t2-install-$(date -u +%Y%m%dT%H%M%SZ).log"
HERMES=hermes

install_one() {
  local id="$1"
  shift || true
  echo "==== INSTALL $id $*" | tee -a "$LOG"
  set +e
  "$HERMES" skills install "$id" "$@" -y 2>&1 | tee -a "$LOG"
  local rc=${PIPESTATUS[0]}
  set -e
  echo "exit=$rc" | tee -a "$LOG"
  # Only fail if we actually force-installed (message text mentioning --force is OK)
  if rg -q "Force-installed despite" "$LOG"; then
    echo "REFUSING: force install occurred" >&2
    exit 2
  fi
  return 0
}

# T2 allowlisted / official-adjacent specialists for routing fixtures
# NOTE: mariano-aguero solidity-security-audit-skill is intentionally omitted —
# native skills-guard returned DANGEROUS (curl|bash etc). Do not --force.
# Prefer wshobson solidity-security + web3-testing for audit routing.
install_one "nimitbhargava/testing-business-ideas-skill/skills/testing-business-ideas"
install_one "https://raw.githubusercontent.com/lowwwbank/interview-to-jtbd/main/SKILL.md" --name interview-to-jtbd
install_one "therealharpaljadeja/monskills/skills/monskill"
install_one "0x70626a/monad-wingman/skills/monad-wingman"
install_one "EmersonBraun/skills/idea-validation"
install_one "EmersonBraun/skills/senior-frontend"
install_one "wshobson/agents/plugins/blockchain-web3/skills/solidity-security"
install_one "wshobson/agents/plugins/blockchain-web3/skills/web3-testing"
install_one "wshobson/agents/plugins/frontend-mobile-development/skills/nextjs-app-router-patterns"
install_one "wshobson/agents/plugins/backend-development/skills/temporal-python-testing"
install_one "rohitg00/ai-engineering-from-scratch/skills/learn" --name ai-engineering-learn
install_one "getagentseal/founder-playbook/made-to-stick"
install_one "getagentseal/founder-playbook/storybrand"

echo "LOG=$LOG"
find /home/ubuntu/.hermes/skills -name SKILL.md | wc -l | tee -a "$LOG"
