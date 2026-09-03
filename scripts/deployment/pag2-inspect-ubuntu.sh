# Shared ubuntu-identity inspectors for H1 verifier / postcheck.
# Source only. Never changes users, sudoers, units, or trust roots.
# Writability, sudo, docker membership, and user-unit enablement are
# properties of ubuntu (uid 1000), not of whoever invoked the script.
# hermes-op NOPASSWD ALL is required recovery, not an agent grant.

pag2_ubuntu_name() { echo ubuntu; }

pag2_can_impersonate_ubuntu() {
  if [[ "$(id -un)" == "ubuntu" ]]; then
    return 0
  fi
  if [[ "$(id -u)" -eq 0 ]]; then
    return 0
  fi
  sudo -n -u ubuntu -- true >/dev/null 2>&1
}

pag2_as_ubuntu() {
  if [[ "$(id -un)" == "ubuntu" ]]; then
    "$@"
    return
  fi
  if [[ "$(id -u)" -eq 0 ]]; then
    runuser -u ubuntu -- "$@"
    return
  fi
  sudo -n -u ubuntu -- "$@"
}

pag2_ubuntu_sudo_list() {
  if [[ "$(id -un)" == "ubuntu" ]]; then
    sudo -n -l 2>/dev/null || true
    return
  fi
  if [[ "$(id -u)" -eq 0 ]]; then
    sudo -l -U ubuntu 2>/dev/null || true
    return
  fi
  if sudo -n true >/dev/null 2>&1; then
    sudo -n -l -U ubuntu 2>/dev/null || true
    return
  fi
  echo ""
}

pag2_ubuntu_in_docker() {
  id -nG ubuntu 2>/dev/null | rg -qw docker
}

# Exit 0 if ubuntu can write the path. Missing path → not writable (1).
# If ubuntu cannot be impersonated, fail closed (treat as writable).
pag2_ubuntu_writable() {
  local path="$1"
  [[ -e "$path" ]] || return 1
  if [[ "$(id -un)" == "ubuntu" ]]; then
    [[ -w "$path" ]]
    return
  fi
  if ! pag2_can_impersonate_ubuntu; then
    return 0
  fi
  pag2_as_ubuntu test -w "$path"
}

pag2_ubuntu_unit_enabled() {
  local unit="$1"
  if [[ "$(id -un)" == "ubuntu" ]]; then
    systemctl --user is-enabled "$unit" 2>/dev/null || true
    return
  fi
  if [[ "$(id -u)" -eq 0 ]]; then
    systemctl --user -M ubuntu@ is-enabled "$unit" 2>/dev/null || true
    return
  fi
  if sudo -n true >/dev/null 2>&1; then
    sudo -n systemctl --user -M ubuntu@ is-enabled "$unit" 2>/dev/null || true
    return
  fi
  echo "UNKNOWN"
}
