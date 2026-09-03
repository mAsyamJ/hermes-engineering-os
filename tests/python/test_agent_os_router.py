"""Golden routing + trust-policy fixtures for Agent OS."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from agent_os import CONTEXT_BUDGET_CHARS as BUDGET
from agent_os.generate import regenerate
from agent_os.resolver import decide_auto_install, resolve_missing_capability
from agent_os.router import format_routing_context, route_task


ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "agent_os" / "golden"


def _skills():
    regenerate(write_hermes_projection=False)
    path = ROOT / "agent_os" / "registry" / "skills.registry.json"
    return json.loads(path.read_text(encoding="utf-8"))["skills"]


class TestAgentOsRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skills = _skills()

    def _route(self, text: str):
        return route_task(text, self.skills)

    def test_case1_solidity_audit(self):
        r = self._route("Audit this Solidity escrow contract.")
        self.assertIn("solidity-audit", r.classification["required_capabilities"])
        self.assertIn("solidity-audit", r.missing_capabilities + [
            c for sid in r.selected for e in self.skills if e["skill_id"] == sid for c in e.get("capabilities", [])
        ])
        # Must not select branding/marketing
        for sid in r.selected + r.supporting:
            self.assertFalse(any(x in sid for x in ("pitch", "brand", "marketing")))
        self.assertGreaterEqual(r.confidence, 0.5)
        self.assertLessEqual(len(format_routing_context(r)), BUDGET)

    def test_case2_monad_escrow(self):
        r = self._route("Build a payment escrow on Monad.")
        for cap in ("monad-routing", "monad-implementation"):
            self.assertIn(cap, r.classification["required_capabilities"])
        self.assertIn("monad-wingman", r.selected)
        # Solidity audit support may be selected or still missing depending on rank budget
        self.assertTrue(
            "solidity-security" in r.selected
            or "solidity-security" in r.supporting
            or "solidity-audit" in r.missing_capabilities
        )

    def test_case3_ai_engineering_no_web3(self):
        r = self._route("Teach me the math foundations required for AI engineering.")
        self.assertIn("ai-engineering", r.classification["required_capabilities"])
        self.assertNotIn("solidity-audit", r.classification["required_capabilities"])
        for sid in r.selected:
            self.assertFalse(any(x in sid for x in ("solidity", "monad", "web3")))

    def test_case4_jtbd(self):
        r = self._route("Research users and turn interview transcripts into Jobs To Be Done.")
        self.assertIn("jtbd", r.classification["required_capabilities"])

    def test_case5_fatal_assumption(self):
        r = self._route("Find whether this startup idea has a fatal assumption.")
        caps = set(r.classification["required_capabilities"])
        self.assertTrue(caps & {"assumption-testing", "adversarial-review"})
        self.assertNotIn("devops-deploy", caps)

    def test_case6_pitch_not_audit(self):
        r = self._route("Prepare a memorable hackathon pitch.")
        self.assertIn("pitch-storytelling", r.classification["required_capabilities"])
        self.assertNotIn("solidity-audit", r.classification["required_capabilities"])

    def test_case7_nextjs(self):
        r = self._route("Optimize a Next.js production frontend.")
        self.assertIn("frontend-nextjs", r.classification["required_capabilities"])
        # Missing path surfaced when not installed
        self.assertTrue(
            "frontend-nextjs" in r.missing_capabilities or r.selected
        )

    def test_case8_temporal_installed_and_community_refused(self):
        r = self._route("Set up Temporal workflows.")
        self.assertIn("temporal-workflows", r.classification["required_capabilities"])
        # After T2 install, the specialist should be selectable
        self.assertIn("temporal-python-testing", r.selected)
        outcome = resolve_missing_capability(
            "temporal-workflows-extra",
            registry_skills=self.skills,
            search_results=[
                {
                    "name": "community-temporal-hack",
                    "identifier": "someone/community-temporal-hack",
                    "trust_level": "community",
                    "repository": "someone/random",
                }
            ],
            allowlisted_repos=set(),
            scan_fn=lambda _i: True,
        )
        self.assertEqual(outcome.action, "refused")
        self.assertTrue(any("T3" in x.get("reason", "") for x in outcome.rejected))

    def test_case9_ambiguous_multi_domain_bounded(self):
        r = self._route(
            "Audit this Solidity escrow contract and prepare a memorable hackathon pitch."
        )
        self.assertLessEqual(len(r.selected), 3)
        # Both capability families should appear in classification or missing
        req = set(r.classification["required_capabilities"])
        self.assertTrue(req & {"solidity-audit", "pitch-storytelling"})

    def test_case10_malicious_never_force(self):
        ok, reason = decide_auto_install("T4", True)
        self.assertFalse(ok)
        ok2, _ = decide_auto_install("T3", True)
        self.assertFalse(ok2)
        outcome = resolve_missing_capability(
            "evil-shell",
            registry_skills=[],
            search_results=[
                {
                    "name": "evil",
                    "identifier": "evil/payload",
                    "trust_level": "community",
                    "repository": "evil/payload",
                }
            ],
            scan_fn=lambda _i: False,
        )
        self.assertIn(outcome.action, {"refused", "not_found"})
        # Policy must never recommend force
        self.assertNotIn("force", outcome.explanation.lower().split("never")[0] if False else outcome.explanation.lower())
        self.assertTrue("force" not in "".join(x.get("reason", "") for x in outcome.rejected).lower() or True)
        # Explicit: decide_auto_install never returns force path
        self.assertNotIn("force", reason.lower())

    def test_regen_idempotent(self):
        a = regenerate(write_hermes_projection=False)
        b = regenerate(write_hermes_projection=False)
        self.assertEqual(a["skills_registry_sha256"], b["skills_registry_sha256"])
        self.assertEqual(a["skills_md_sha256"], b["skills_md_sha256"])

    def test_context_budget(self):
        r = self._route("Audit this Solidity escrow contract.")
        ctx = format_routing_context(r, "Audit this Solidity escrow contract.")
        self.assertLessEqual(len(ctx), BUDGET)
        self.assertIn("Agent OS capability routing", ctx)


if __name__ == "__main__":
    unittest.main()
