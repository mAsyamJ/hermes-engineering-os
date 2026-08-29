#!/usr/bin/env bash
# Read-only operator-boundary verifier. NEVER alters users, SSH, sudoers,
# systemd ownership, or trust roots.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
status="PASS"
reasons=()

note() { reasons+=("$1"); }

agent_uid="$(id -u)"
agent_user="$(id -un)"
if [[ "$agent_user" != "ubuntu" || "$agent_uid" != "1000" ]]; then
  note "AUTH_AGENT_UID_UNEXPECTED:${agent_user}:${agent_uid}"
fi

sudo_out="$(sudo -n -l 2>/dev/null || true)"
if echo "$sudo_out" | rg -q 'NOPASSWD: ALL'; then
  note "AUTH_AGENT_PASSWORDLESS_ROOT"
  status="READY_FOR_HUMAN"
fi

if groups | rg -qw docker; then
  note "AUTH_AGENT_IN_DOCKER_GROUP"
  status="READY_FOR_HUMAN"
fi

# Proposed protected paths. Absence is AUTH_NO_PROTECTED_ACTUATOR, not a write.
protected_paths=(
  /etc/hermes-eos/approval-trust.pub
  /etc/hermes-eos/actuator.env
  /usr/local/lib/hermes-eos/approval-verifier
  /etc/systemd/system/hermes-eos-actuator.service
)
actuator_present=0
for path in "${protected_paths[@]}"; do
  if [[ -e "$path" ]]; then
    actuator_present=1
    if [[ -w "$path" ]]; then
      note "AUTH_TRUST_ROOT_WRITABLE:${path}"
      status="READY_FOR_HUMAN"
    fi
  fi
done
if [[ "$actuator_present" -eq 0 ]]; then
  note "AUTH_NO_PROTECTED_ACTUATOR"
  if [[ "$status" == "PASS" ]]; then
    status="READY_FOR_HUMAN"
  fi
fi

# Repo verifier is agent-owned by design until bootstrap.
if [[ -w "$ROOT/engineering_os/adaptation/approval_ed25519.py" ]]; then
  note "AUTH_VERIFIER_CODE_WRITABLE"
  if [[ "$status" == "PASS" ]]; then
    status="READY_FOR_HUMAN"
  fi
fi

user_unit="$HOME/.config/systemd/user/hermes-gateway-rp-friend.service"
if [[ -w "$user_unit" ]]; then
  note "AUTH_PROTECTED_UNIT_WRITABLE:${user_unit}"
  if [[ "$status" == "PASS" ]]; then
    status="READY_FOR_HUMAN"
  fi
fi

# Production private key must not exist on this VPS.
key_hits="$(find /opt/hermes-engineering-os /etc/hermes-eos /home/ubuntu/.hermes-eos \
  -type f \( -name '*approval*private*' -o -name 'production*.pem' -o -name 'ed25519_production*' \) \
  2>/dev/null || true)"
if [[ -n "${key_hits}" ]]; then
  note "AUTH_PRIVATE_KEY_ON_AGENT_HOST"
  status="BLOCKED"
fi
if [[ -n "${HERMES_CONTROL_PRODUCTION_APPROVAL_KEY:-}" ]]; then
  note "AUTH_PRIVATE_KEY_ON_AGENT_HOST:env"
  status="BLOCKED"
fi

# Public trust identity (optional). Missing is expected pre-bootstrap.
if [[ ! -e /etc/hermes-eos/approval-trust.pub ]]; then
  note "AUTH_PUBLIC_TRUST_IDENTITY_ABSENT"
fi

operator_users="$(getent passwd | awk -F: '$3>=1000 && $3<65534 && $1!="ubuntu" {print $1}' || true)"
if [[ -z "$operator_users" ]]; then
  note "AUTH_NO_OPERATOR_PRINCIPAL"
  if [[ "$status" == "PASS" ]]; then
    status="READY_FOR_HUMAN"
  fi
fi

gh_admin="unknown"
if command -v gh >/dev/null 2>&1; then
  perms="$(gh api repos/mAsyamJ/hermes-engineering-os --jq '.permissions.admin' 2>/dev/null || echo unknown)"
  protection="$(gh api repos/mAsyamJ/hermes-engineering-os/branches/main/protection --jq '.enabled' 2>/dev/null || echo missing)"
  if [[ "$perms" == "true" ]]; then
    note "AUTH_GITHUB_ADMIN_ON_AGENT"
    gh_admin="true"
    if [[ "$status" == "PASS" ]]; then
      status="READY_FOR_HUMAN"
    fi
  fi
  if [[ "$protection" == "missing" ]]; then
    note "AUTH_GITHUB_UNPROTECTED_MAIN"
  fi
fi

if [[ "$status" == "PASS" ]]; then
  # PASS only if ubuntu cannot escalate and a protected actuator exists.
  if printf '%s\n' "${reasons[@]}" | rg -q 'AUTH_AGENT_PASSWORDLESS_ROOT|AUTH_NO_PROTECTED_ACTUATOR|AUTH_NO_OPERATOR_PRINCIPAL'; then
    status="READY_FOR_HUMAN"
  fi
fi

echo "status=${status}"
echo "agent_uid=${agent_uid}"
echo "agent_user=${agent_user}"
echo "sudo_nopasswd_all=$(echo "$sudo_out" | rg -q 'NOPASSWD: ALL' && echo yes || echo no)"
echo "protected_actuator_present=${actuator_present}"
echo "github_admin=${gh_admin}"
echo "reasons:"
for r in "${reasons[@]}"; do
  echo "  ${r}"
done
exit 0
