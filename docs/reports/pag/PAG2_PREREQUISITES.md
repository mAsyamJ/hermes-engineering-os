# PAG-2 prerequisites

PAG-1 does not run production shadow, live actuation deployment, or canary.

PAG-2 **READY** only when every item is true:

1. PAG-1 framework remains complete and honest
2. Production adaptation still DISABLED; exposures still 0
3. `SECURE_AUTHORITY = READY` (human bootstrap done; boundary verifier PASS)
4. Production private key still absent from this VPS; only public trust installed
5. `approval-ed25519-v1` still PASS; TEST HMAC still cannot authorize production
6. `REAL_CAUSAL_EVIDENCE = QUALIFIED` with conclusion `EVIDENCE_FOR_CANDIDATE`
   and all Phase 6 validity gates PASS — **or** an explicit record that no
   candidate should proceed
7. A real production-eligible recommendation exists and is **not** activated
8. Upstream actuation patch is still PR-ready (or an official seam replaced it)
   and is **not** live until a separate deploy gate
9. Live Hermes unpatched until that deploy gate
10. Memory isolation still PASS for the treatment
11. rp-friend / default gateway still healthy; RetroPick trees unmutated by EOS

If real evidence is `BLOCKED_BUDGET` or `NO_CLEAR_EFFECT`, PAG-2 is
`BLOCKED_EVIDENCE` (or `BLOCKED_EVIDENCE_AND_AUTHORITY` when bootstrap is also
pending). Do not use production shadow as a shortcut around evidence.
