#!/usr/bin/env bash
# Read-only operator-boundary verifier. NEVER alters users, SSH, sudoers,
# systemd ownership, or trust roots.
# PAG-2: full actuation TCB + four principals + SO_PEERCRED.
# GitHub admin is recorded and is NOT a local PASS blocker.
# PASS is never faked: missing principals or ubuntu-as-gateway stay READY_FOR_HUMAN.
set -euo pipefail

# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
# shellcheck source=pag2-inspect-ubuntu.sh
source "$ROOT/scripts/deployment/pag2-inspect-ubuntu.sh"
status="PASS"
reasons=()

note() { reasons+=("$1"); }
downgrade_ready() {
  if [[ "$status" != "BLOCKED" ]]; then
    status="READY_FOR_HUMAN"
  fi
}

# Always inspect ubuntu uid 1000. Caller identity is recorded separately so
# hermes-op running this script cannot be mistaken for the agent, and cannot
# be blocked by hermes-op's own recovery NOPASSWD ALL.
invoked_user="$(id -un)"
invoked_uid="$(id -u)"
agent_user="ubuntu"
agent_uid="$(getent passwd ubuntu | awk -F: '{print $3}')"
if [[ "$agent_uid" != "1000" ]]; then
  note "AUTH_AGENT_UID_UNEXPECTED:${agent_user}:${agent_uid}"
  downgrade_ready
fi

sudo_out="$(pag2_ubuntu_sudo_list)"
if echo "$sudo_out" | rg -q 'NOPASSWD: ALL'; then
  note "AUTH_AGENT_PASSWORDLESS_ROOT"
  downgrade_ready
fi

if pag2_ubuntu_in_docker; then
  note "AUTH_AGENT_IN_DOCKER_GROUP"
  downgrade_ready
fi

# Four principals. Absence is READY_FOR_HUMAN, never PASS.
hermes_op="$(getent passwd hermes-op || true)"
hermes_runtime="$(getent passwd hermes-runtime || true)"
hermes_actuator="$(getent passwd hermes-actuator || true)"
if [[ -z "$hermes_op" ]]; then
  note "AUTH_NO_HERMES_OP"
  downgrade_ready
else
  op_shell="$(echo "$hermes_op" | awk -F: '{print $7}')"
  if [[ "$op_shell" == *nologin* || "$op_shell" == *false* ]]; then
    note "AUTH_HERMES_OP_NOLOGIN"
    downgrade_ready
  fi
fi
if [[ -z "$hermes_runtime" ]]; then
  note "AUTH_NO_HERMES_RUNTIME"
  downgrade_ready
else
  rt_shell="$(echo "$hermes_runtime" | awk -F: '{print $7}')"
  if [[ "$rt_shell" != *nologin* && "$rt_shell" != *false* ]]; then
    note "AUTH_HERMES_RUNTIME_LOGIN_ENABLED"
    downgrade_ready
  fi
fi
if [[ -z "$hermes_actuator" ]]; then
  note "AUTH_NO_HERMES_ACTUATOR"
  downgrade_ready
else
  act_shell="$(echo "$hermes_actuator" | awk -F: '{print $7}')"
  if [[ "$act_shell" != *nologin* && "$act_shell" != *false* ]]; then
    note "AUTH_HERMES_ACTUATOR_LOGIN_ENABLED"
    downgrade_ready
  fi
fi

operator_users="$(getent passwd | awk -F: '$3>=1000 && $3<65534 && $1!="ubuntu" {print $1}' || true)"
if [[ -z "$operator_users" ]]; then
  note "AUTH_NO_OPERATOR_PRINCIPAL"
  downgrade_ready
fi

# Proposed / required protected TCB paths.
protected_paths=(
  /etc/hermes-eos/approval-trust.pub
  /etc/hermes-eos/actuator.env
  /usr/local/lib/hermes-eos/approval-verifier
  /usr/local/lib/hermes-eos/hermes-eos-deploy-tool.py
  /usr/local/lib/hermes-eos/scripts/verify-operator-boundary.sh
  /usr/local/lib/hermes-eos/scripts/pag2-inspect-ubuntu.sh
  /usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin/__init__.py
  /usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin/plugin.yaml
  /usr/local/lib/hermes-eos/engineering_os/adaptation/actuator.py
  /usr/local/lib/hermes-eos/actuator.py
  /etc/systemd/system/hermes-eos-actuator.service
  /etc/systemd/system/hermes-gateway.service
  /etc/systemd/system/hermes-gateway-rp-friend.service
  /usr/lib/hermes-runtime/hermes-agent
  /var/lib/hermes-runtime/home
  /run/hermes-eos
)
actuator_present=0
writable_trust=0
if [[ -e /usr/local/lib/hermes-eos/engineering_os/adaptation/actuator.py || -e /usr/local/lib/hermes-eos/actuator.py ]]; then
  actuator_present=1
fi
for path in "${protected_paths[@]}"; do
  if [[ -e "$path" ]]; then
    if pag2_ubuntu_writable "$path"; then
      note "AUTH_TRUST_ROOT_WRITABLE:${path}"
      writable_trust=1
      downgrade_ready
    fi
  fi
done
if [[ "$actuator_present" -eq 0 ]]; then
  note "AUTH_NO_PROTECTED_ACTUATOR"
  downgrade_ready
fi
if [[ ! -e /usr/local/lib/hermes-eos/hermes-eos-deploy-tool.py ]]; then
  note "AUTH_NO_PROTECTED_DEPLOY_TOOL"
  downgrade_ready
fi
if [[ ! -e /usr/local/lib/hermes-eos/scripts/verify-operator-boundary.sh || ! -e /usr/local/lib/hermes-eos/scripts/pag2-inspect-ubuntu.sh ]]; then
  note "AUTH_NO_PROTECTED_VERIFIER_SCRIPT"
  downgrade_ready
fi
if [[ ! -e /usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin/__init__.py || ! -e /usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin/plugin.yaml ]]; then
  note "AUTH_NO_PROTECTED_PLUGIN_SOURCE"
  downgrade_ready
fi
if [[ ! -e /usr/lib/hermes-runtime/hermes-agent ]]; then
  note "AUTH_NO_PROTECTED_RUNTIME_TREE"
  downgrade_ready
fi
if [[ ! -e /etc/hermes-eos/approval-trust.pub ]]; then
  note "AUTH_PUBLIC_TRUST_IDENTITY_ABSENT"
  downgrade_ready
fi
if [[ ! -e /etc/hermes-eos/actuator.env ]]; then
  note "AUTH_NO_ACTUATOR_ENV"
  downgrade_ready
fi

# Repo verifier is agent-owned by design. Only the protected copy counts for PASS.
if pag2_ubuntu_writable "$ROOT/engineering_os/adaptation/approval_ed25519.py"; then
  note "AUTH_VERIFIER_CODE_WRITABLE"
  if [[ ! -e /usr/local/lib/hermes-eos/approval-verifier ]]; then
    downgrade_ready
  fi
fi

user_unit="/home/ubuntu/.config/systemd/user/hermes-gateway-rp-friend.service"
user_enabled="$(pag2_ubuntu_unit_enabled hermes-gateway-rp-friend.service)"
if [[ "$user_enabled" == "UNKNOWN" ]]; then
  note "AUTH_USER_GATEWAY_STATE_UNREADABLE"
  downgrade_ready
elif [[ "$user_enabled" != "masked" && "$user_enabled" != "not-found" && -n "$user_enabled" ]]; then
  note "AUTH_USER_GATEWAY_NOT_MASKED:${user_enabled}"
  downgrade_ready
fi
if pag2_ubuntu_writable "$user_unit"; then
  note "AUTH_PROTECTED_UNIT_WRITABLE:${user_unit}"
  if [[ "$user_enabled" != "masked" ]]; then
    downgrade_ready
  fi
fi

# Production gateway identity: after H1 must be hermes-runtime, not ubuntu.
gateway_user="unknown"
if systemctl show hermes-gateway.service -p User --value >/dev/null 2>&1; then
  gateway_user="$(systemctl show hermes-gateway.service -p User --value 2>/dev/null || echo unknown)"
fi
if [[ "$gateway_user" == "ubuntu" || "$gateway_user" == "" || "$gateway_user" == "unknown" ]]; then
  # Fall back to currently running user-unit process.
  if pgrep -u ubuntu -f 'hermes_cli.main gateway run' >/dev/null 2>&1; then
    gateway_user="ubuntu"
  fi
fi
if [[ "$gateway_user" != "hermes-runtime" ]]; then
  note "AUTH_GATEWAY_RUNS_AS_AGENT:${gateway_user}"
  downgrade_ready
fi
if pgrep -u ubuntu -f 'hermes_cli.main gateway run' >/dev/null 2>&1; then
  note "AUTH_GATEWAY_RUNS_AS_AGENT:ubuntu-process"
  downgrade_ready
fi

# SO_PEERCRED must exist in the protected actuator, not only in the agent-writable repo.
so_peercred=0
for candidate in \
  /usr/local/lib/hermes-eos/engineering_os/adaptation/actuator.py \
  /usr/local/lib/hermes-eos/actuator.py \
  /usr/lib/hermes-eos/actuator.py
do
  if [[ -f "$candidate" ]] && rg -q 'SO_PEERCRED' "$candidate"; then
    so_peercred=1
  fi
done
if [[ "$so_peercred" -eq 0 ]]; then
  note "AUTH_NO_SO_PEERCRED_ACTUATOR"
  downgrade_ready
fi

if [[ -d /var/lib/hermes-runtime/home ]] && pag2_ubuntu_writable /var/lib/hermes-runtime/home; then
  note "AUTH_CREDENTIAL_HOME_AGENT_WRITABLE"
  downgrade_ready
fi
plugin_link="$(readlink -f /var/lib/hermes-runtime/home/profiles/rp-friend/plugins 2>/dev/null || true)"
if [[ -n "$plugin_link" ]] && echo "$plugin_link" | rg -q '^/home/ubuntu|^/opt/hermes-engineering-os'; then
  note "AUTH_PLUGIN_PATH_AGENT_WRITABLE:${plugin_link}"
  downgrade_ready
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

gh_admin="unknown"
if command -v gh >/dev/null 2>&1; then
  perms="$(gh api repos/mAsyamJ/hermes-engineering-os --jq '.permissions.admin' 2>/dev/null || echo unknown)"
  protection="$(gh api repos/mAsyamJ/hermes-engineering-os/branches/main/protection --jq '.enabled' 2>/dev/null || echo missing)"
  if [[ "$perms" == "true" ]]; then
    note "AUTH_GITHUB_ADMIN_ON_AGENT"
    gh_admin="true"
    # Recorded only. Git refs are not a local PASS blocker.
  fi
  if [[ "$protection" == "missing" ]]; then
    note "AUTH_GITHUB_UNPROTECTED_MAIN"
  fi
fi

# PASS requires every TCB item. Do not collapse GitHub notes into a fake PASS.
if [[ "$status" == "PASS" ]]; then
  if printf '%s\n' "${reasons[@]}" | rg -q 'AUTH_AGENT_PASSWORDLESS_ROOT|AUTH_NO_PROTECTED_ACTUATOR|AUTH_NO_OPERATOR_PRINCIPAL|AUTH_NO_HERMES_OP|AUTH_NO_HERMES_RUNTIME|AUTH_NO_HERMES_ACTUATOR|AUTH_GATEWAY_RUNS_AS_AGENT|AUTH_NO_SO_PEERCRED_ACTUATOR|AUTH_NO_PROTECTED_DEPLOY_TOOL|AUTH_NO_PROTECTED_VERIFIER_SCRIPT|AUTH_NO_PROTECTED_PLUGIN_SOURCE|AUTH_NO_PROTECTED_RUNTIME_TREE|AUTH_TRUST_ROOT_WRITABLE|AUTH_CREDENTIAL_HOME_AGENT_WRITABLE|AUTH_PLUGIN_PATH_AGENT_WRITABLE|AUTH_PUBLIC_TRUST_IDENTITY_ABSENT|AUTH_NO_ACTUATOR_ENV|AUTH_USER_GATEWAY_NOT_MASKED|AUTH_USER_GATEWAY_STATE_UNREADABLE|AUTH_AGENT_UID_UNEXPECTED'; then
    status="READY_FOR_HUMAN"
  fi
  if [[ "$writable_trust" -eq 1 ]]; then
    status="READY_FOR_HUMAN"
  fi
fi

echo "status=${status}"
echo "agent_uid=${agent_uid}"
echo "agent_user=${agent_user}"
echo "invoked_user=${invoked_user}"
echo "invoked_uid=${invoked_uid}"
echo "sudo_nopasswd_all=$(echo "$sudo_out" | rg -q 'NOPASSWD: ALL' && echo yes || echo no)"
echo "protected_actuator_present=${actuator_present}"
echo "hermes_op_present=$([[ -n "$hermes_op" ]] && echo yes || echo no)"
echo "hermes_runtime_present=$([[ -n "$hermes_runtime" ]] && echo yes || echo no)"
echo "hermes_actuator_present=$([[ -n "$hermes_actuator" ]] && echo yes || echo no)"
echo "gateway_user=${gateway_user}"
echo "so_peercred_protected=${so_peercred}"
echo "github_admin=${gh_admin}"
echo "reasons:"
for r in "${reasons[@]}"; do
  echo "  ${r}"
done
exit 0
