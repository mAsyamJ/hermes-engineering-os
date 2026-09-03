#!/usr/bin/env bash
# Create native Hermes skill bundles ONLY for proven installed skill IDs.
set -euo pipefail
HERMES=hermes
mkdir -p /home/ubuntu/.hermes/skill-bundles
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
TRACK="$ROOT/agent_os/bundles"

create_bundle() {
  local name="$1"; shift
  local desc="$1"; shift
  echo "==== bundle $name"
  # Delete existing to recreate deterministically
  "$HERMES" bundles delete "$name" -y 2>/dev/null || true
  "$HERMES" bundles create "$name" -d "$desc" "$@"
  # Track copy in control plane
  if [[ -f "/home/ubuntu/.hermes/skill-bundles/${name}.yaml" ]]; then
    cp --preserve=mode,timestamps "/home/ubuntu/.hermes/skill-bundles/${name}.yaml" "$TRACK/${name}.yaml"
  fi
}

# Verify members exist as SKILL.md somehow
need() {
  local id="$1"
  find /home/ubuntu/.hermes/skills -type d -name "$id" | head -1 | grep -q .
}

for id in solidity-security web3-testing monad-wingman why-monad scaffold concepts \
          testing-business-ideas idea-validation grill-me interview-to-jtbd \
          made-to-stick storybrand learn nextjs-app-router-patterns senior-frontend \
          temporal-python-testing; do
  if ! need "$id"; then
    echo "MISSING required skill dir: $id" >&2
    find /home/ubuntu/.hermes/skills -iname "*${id}*" | head
  fi
done

create_bundle monad-security "Monad + Solidity security review set" \
  --skill solidity-security --skill web3-testing --skill monad-wingman --skill why-monad

create_bundle monad-contract-build "Build contracts on Monad" \
  --skill monad-wingman --skill scaffold --skill concepts --skill web3-testing

create_bundle startup-validation "Test fatal assumptions / validate startup ideas" \
  --skill testing-business-ideas --skill idea-validation --skill grill-me

create_bundle product-discovery "Interview → JTBD" \
  --skill interview-to-jtbd

create_bundle pitch-preparation "Memorable pitch / story" \
  --skill made-to-stick --skill storybrand

create_bundle ai-engineering "AI engineering learning path" \
  --skill learn

create_bundle frontend-production "Next.js / frontend production" \
  --skill nextjs-app-router-patterns --skill senior-frontend

create_bundle web3-security-audit "Web3/Solidity audit + testing" \
  --skill solidity-security --skill web3-testing

"$HERMES" bundles list
ls "$TRACK"
