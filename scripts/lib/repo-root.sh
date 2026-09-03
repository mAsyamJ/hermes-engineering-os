# Resolve Engineering OS repository root (symlink-safe).
# shellcheck shell=bash
_eos_repo_root_from() {
  local start="$1"
  local dir
  dir="$(cd "$(dirname "$start")" && pwd -P)"
  while [[ "$dir" != "/" ]]; do
    if [[ -f "$dir/plugin.yaml" && -f "$dir/pyproject.toml" && -d "$dir/agent_os" ]]; then
      printf '%s\n' "$dir"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  echo "eos: could not locate repository root from $start" >&2
  return 1
}
