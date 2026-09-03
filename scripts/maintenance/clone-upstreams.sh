#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
DEST="$ROOT/upstream"
mkdir -p "$DEST"

clone_pin() {
  local name="$1" url="$2" sha="$3"
  local target="$DEST/$name"
  if [[ ! -d "$target/.git" ]]; then
    git clone --depth=1 --filter=blob:none --no-checkout "$url" "$target"
  fi
  git -C "$target" fetch --depth=1 origin "$sha"
  git -C "$target" checkout --detach "$sha"
  test "$(git -C "$target" rev-parse HEAD)" = "$sha"
  test -z "$(git -C "$target" status --porcelain)"
}

clone_pin hermes-example-plugins https://github.com/NousResearch/hermes-example-plugins.git 38fe0fb53eff98d477f807432e965429e665ca33
clone_pin hermes-otel https://github.com/briancaffey/hermes-otel.git c76bea8434e6cc8b51c835bb57c514a5eb71e857
clone_pin ai-agent-board https://github.com/DanWahlin/ai-agent-board.git 4f2965e72ad99e32e0375af837247cafb382f17c
clone_pin hivemind https://github.com/dip497/hivemind.git f4209b905c54342073822409f1da1a9f56da4981
clone_pin agent-kanban https://github.com/saltbo/agent-kanban.git 82c082c5e3fcab75d33523e5b2b67df3716afc4a

echo "PASS: five upstream repositories match the lock"

