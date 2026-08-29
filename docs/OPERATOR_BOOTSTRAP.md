# Operator Bootstrap

Human-only. Autonomous agents must not execute these steps.

Order is mandatory: create new human access first. Never remove current access first.

## 1. Create new human administrator access

- Precondition: existing ubuntu SSH session works; you have a second key you control off-VPS.
- Action: add a new administrator identity (new user or additional SSH key for a human-only account) using a process you can reverse.
- Verification: open a **separate SSH session** as that identity. Confirm `sudo -n true` or an equivalent admin check succeeds in that session.
- Rollback: remove only the new identity. Do not touch ubuntu.
- Lockout prevention: keep the original ubuntu session open until the new session is proven.

## 2. Verify admin capability in the new session

- Precondition: step 1 verification passed.
- Action: from the new session, inspect sudoers, systemd, and Docker without changing ubuntu.
- Verification: new session can read `/etc/sudoers` (via sudo) and restart a **non-production** test unit if you create one.
- Rollback: none required.
- Lockout prevention: ubuntu access unchanged.

## 3. Create protected actuation user/service

- Precondition: step 2 passed; two working admin sessions.
- Action: create an actuation identity whose files ubuntu cannot write **after** sudo is reduced. Do not place the production private key on this VPS.
- Verification: ubuntu cannot write the actuation unit or trust file without sudo; after sudo reduction, ubuntu cannot write them at all.
- Rollback: delete the new identity; ubuntu remains admin.
- Lockout prevention: do not reduce ubuntu yet.

## 4. Verify operator access again

- Precondition: actuation identity exists.
- Action: reconnect the separate admin session.
- Verification: admin still works; ubuntu still works.
- Rollback: restore any mistaken file modes.
- Lockout prevention: both sessions still open.

## 5. Only then consider reducing agent privilege

- Precondition: steps 1–4 verified twice.
- Action: replace `NOPASSWD: ALL` with a narrow allowlist **or** remove ubuntu sudo.
- Verification: new admin session still has sudo; ubuntu can still do required Engineering OS work; you can still log in.
- Rollback: restore previous sudoers from a copy taken before the edit, using the new admin session.
- Lockout prevention: never edit sudoers from the only remaining admin session.

Privilege-boundary change is outside autonomous execution scope.
