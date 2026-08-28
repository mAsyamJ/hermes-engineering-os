# Adaptation Operations

CLI: `scripts/adapt.sh <command>` (docker compose profile `adaptation`).

Useful commands: `recommend`, `compile-policy`, `approve-test`, `shadow-start`,
`canary-start-fixture`, `disable`, `rollback`, `promotion-request`,
`disable-all`, `status`.

`adapt approve` (production) returns `BLOCKED_APPROVAL_BOUNDARY`.

Timer: `hermes-eos-adaptation.timer` runs `scripts/adaptation-materialize.sh`
with advisory lock `720260827`. It does not schedule Hermes tasks.

Emergency: `scripts/adapt.sh disable-all` engages the kill switch file and
row. Future resolver calls return baseline. Running tasks are not killed.

`systemctl --user disable --now hermes-eos-adaptation.timer` stops the
controller only.
