"""PAG-1 qualification: authority, budget, memory, preflight, data boundaries."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("EOS_EVAL_SANDBOX", "inline")
os.environ["EOS_ADAPTATION_RUNTIME"] = tempfile.mkdtemp(prefix="eos-pag1-adapt-")
os.environ["EOS_EXPERIMENT_RUNTIME"] = tempfile.mkdtemp(prefix="eos-pag1-exp-")

from engineering_os.adaptation.approval import sign_test, verify_test
from engineering_os.adaptation.approval_ed25519 import (
    generate_approval_request,
    generate_ephemeral_keypair,
    sign_detached,
    verify_bindings,
    verify_detached_signature,
    verify_production_authorization,
    verify_scope_class,
)
from engineering_os.adaptation.readiness import cells
from engineering_os.adaptation.recommend import recommend_from_result
from engineering_os.adaptation.spawn_resolve import resolve_spawn_configuration
from engineering_os.evaluation.engine import evaluate_trees
from engineering_os.evaluation.profiles import load_profile
from engineering_os.experiments.benchmarks import materialize_real_case
from engineering_os.experiments.budget_gate import require_budget_authorization
from engineering_os.experiments.definitions import load_id
from engineering_os.experiments.hermes_runner import run_real_unit
from engineering_os.experiments.memory_snapshot import (
    create_isolated_arms,
    destroy_homes,
    freeze_snapshot,
    memory_hash,
    production_memory_fingerprint,
    write_memory,
)

ROOT = Path(__file__).resolve().parents[2]
FAKE_SECRET = "FAKE_PAG1_SECRET_ABC123"
FAKE_APPROVAL = "FAKE_PAG1_APPROVAL_SECRET_ABC123"
CASES = (
    "real-v1-bugfix",
    "real-v1-feature",
    "real-v1-refactor",
    "real-v1-test-repair",
    "real-v1-config",
)


def _request(**overrides):
    payload = generate_approval_request(
        recommendation_id="rec-pag1",
        policy_id="policy-1",
        policy_hash="phash",
        policy_version="1",
        approval_stage="A",
        scope="BENCHMARK",
        maximum_exposure=1,
        candidate_config_hash="cand",
        fallback_hash="fall",
        rollback_hash="roll",
        expiry="2027-01-01T00:00:00+00:00",
    )
    payload.update(overrides)
    return payload


class AuthorityTests(unittest.TestCase):
    def test_boundary_verifier_ready_for_human(self) -> None:
        proc = subprocess.run(
            [str(ROOT / "scripts/verify-operator-boundary.sh")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        if "status=PASS" in proc.stdout:
            self.assertNotIn("AUTH_AGENT_PASSWORDLESS_ROOT", proc.stdout)
        else:
            self.assertIn("status=READY_FOR_HUMAN", proc.stdout)
            self.assertIn("AUTH_AGENT_PASSWORDLESS_ROOT", proc.stdout)
        self.assertNotIn(FAKE_SECRET, proc.stdout)
        self.assertNotIn(FAKE_APPROVAL, proc.stdout)

    def test_wrong_stage_and_recommendation_binding(self) -> None:
        keys = generate_ephemeral_keypair()
        request = _request()
        expected = {
            "policy_hash": request["policy_hash"],
            "scope": request["scope"],
            "approval_stage": request["approval_stage"],
            "recommendation_id": request["recommendation_id"],
            "candidate_config_hash": request["candidate_config_hash"],
            "rollback_hash": request["rollback_hash"],
            "maximum_exposure": request["maximum_exposure"],
        }
        self.assertTrue(verify_bindings(request, expected)["ok"])
        self.assertFalse(verify_bindings({**request, "approval_stage": "B"}, expected)["ok"])
        self.assertFalse(verify_bindings({**request, "recommendation_id": "other"}, expected)["ok"])
        sig = sign_detached(request, keys["private"])
        tampered = {**request, "policy_hash": "tampered"}
        self.assertFalse(verify_detached_signature(tampered, sig, keys["public"], consume=False)["ok"])

    def test_hmac_cannot_authorize_production(self) -> None:
        self.assertFalse(verify_scope_class(scope="PRODUCTION_CANARY", approval_class="TEST")["ok"])
        hmac_fields = {
            "stage": "A",
            "recommendation_id": "r",
            "policy_hash": "h",
            "policy_version": "1",
            "scope": "BENCHMARK",
            "max_exposure": 1,
            "expires_at": "2027-01-01T00:00:00+00:00",
            "rollback_hash": "rb",
            "operator_identity": "tester",
        }
        hmac_sig = sign_test(hmac_fields, key=FAKE_APPROVAL.encode())
        self.assertTrue(verify_test(hmac_fields, hmac_sig, key=FAKE_APPROVAL.encode())["ok"])
        request = _request()
        keys = generate_ephemeral_keypair()
        self.assertFalse(verify_detached_signature(request, hmac_sig, keys["public"], consume=False)["ok"])
        standing = verify_production_authorization()
        if standing["status"] == "PROTECTED_TRUST_PRESENT":
            self.assertFalse(standing.get("ok"))
            self.assertIn("request/signature missing", str(standing.get("reason") or ""))
        else:
            self.assertEqual(standing["status"], "BLOCKED_SECURITY_BOUNDARY")


class BudgetAndExperimentTests(unittest.TestCase):
    def test_missing_and_generic_yes_blocked(self) -> None:
        definition = load_id("real-model-sol-vs-terra-v1")
        gate = require_budget_authorization(definition)
        self.assertFalse(gate["ok"])
        blocked = run_real_unit({"unit_id": "u1"}, definition)
        self.assertFalse(blocked["executed"])
        self.assertEqual(blocked["llm_calls"], 0)
        path = Path(os.environ["EOS_EXPERIMENT_RUNTIME"]) / "LLM_BUDGET_AUTHORIZATION"
        path.write_text("yes\n", encoding="utf-8")
        invalid = require_budget_authorization(definition)
        self.assertFalse(invalid["ok"])
        self.assertEqual(invalid["status"], "INVALID")
        path.write_text(
            json.dumps(
                {
                    "protocol_id": definition["experiment_id"],
                    "protocol_hash": "deadbeef",
                    "max_units": 10,
                    "max_llm_calls": 10,
                    "control_model": "gpt-5.6-sol",
                    "candidate_model": "gpt-5.6-terra",
                    "scope": "BENCHMARK",
                    "expiry": "2027-01-01T00:00:00+00:00",
                    "created_by": "human-operator",
                }
            ),
            encoding="utf-8",
        )
        mismatch = require_budget_authorization(definition)
        self.assertFalse(mismatch["ok"])
        self.assertIn("hash", mismatch["reason"])
        path.unlink()

    def test_pag1_cannot_self_authorize(self) -> None:
        definition = load_id("real-model-sol-vs-terra-v1")
        path = Path(os.environ["EOS_EXPERIMENT_RUNTIME"]) / "LLM_BUDGET_AUTHORIZATION"
        path.write_text(
            json.dumps(
                {
                    "protocol_id": definition["experiment_id"],
                    "protocol_hash": definition["_definition_hash"],
                    "max_units": 10,
                    "max_llm_calls": 10,
                    "control_model": "gpt-5.6-sol",
                    "candidate_model": "gpt-5.6-terra",
                    "scope": "BENCHMARK",
                    "expiry": "2027-01-01T00:00:00+00:00",
                    "created_by": "pag1-automation",
                }
            ),
            encoding="utf-8",
        )
        gate = require_budget_authorization(definition)
        self.assertFalse(gate["ok"])
        path.unlink()

    def test_all_five_benchmarks_have_test_evaluator(self) -> None:
        work = Path(os.environ["EOS_EXPERIMENT_RUNTIME"]) / "pag1-eval"
        profile = load_profile("real-v1")
        for case_id in CASES:
            broken = materialize_real_case({"case_id": case_id, "tree": "broken"}, work / f"{case_id}-broken")
            golden = materialize_real_case({"case_id": case_id, "tree": "golden"}, work / f"{case_id}-golden")
            broken_eval = evaluate_trees(Path(broken["path"]), profile, baseline=Path(broken["path"]), eligibility="TEST_ELIGIBLE")
            golden_eval = evaluate_trees(Path(golden["path"]), profile, baseline=Path(golden["path"]), eligibility="TEST_ELIGIBLE")
            self.assertIn(broken_eval["quality_vector"]["tests"], {"PASS", "FAIL", "UNKNOWN"}, case_id)
            self.assertEqual(broken_eval["quality_vector"]["tests"], "FAIL", case_id)
            self.assertEqual(golden_eval["quality_vector"]["tests"], "PASS", case_id)


class MemoryAndSafetyTests(unittest.TestCase):
    def test_memory_isolation_secret_free(self) -> None:
        before = production_memory_fingerprint()
        snapshot = freeze_snapshot(memory_text="start", user_text="user", config={"model": "x", "api_key": FAKE_SECRET})
        self.assertNotIn(FAKE_SECRET, snapshot["canonical"])
        self.assertNotIn(FAKE_APPROVAL, snapshot["canonical"])
        arms = create_isolated_arms(snapshot, prefix="pag1-mem")
        self.assertTrue(arms["identical_initial_hash"])
        write_memory(Path(arms["arm_a"]["path"]), "arm-a-write")
        self.assertNotEqual(memory_hash(Path(arms["arm_a"]["path"])), memory_hash(Path(arms["arm_b"]["path"])))
        write_memory(Path(arms["arm_b"]["path"]), "arm-b-write")
        self.assertEqual(production_memory_fingerprint(), before)
        destroy_homes(Path(arms["root"]))
        self.assertEqual(production_memory_fingerprint(), before)

    def test_production_exposure_hard_reject(self) -> None:
        result = resolve_spawn_configuration(
            {"scope": "PRODUCTION_CANARY", "environment": "production"},
            {"model": "gpt-5.6-sol"},
        )
        self.assertEqual(result["resolution"], "BASELINE")
        self.assertFalse(result["actuate"])

    def test_no_clear_effect_cannot_recommend(self) -> None:
        rec = recommend_from_result(
            {
                "source": "phase6",
                "experiment_id": "real-model-sol-vs-terra-v1",
                "conclusion": "NO_CLEAR_EFFECT",
                "scope": "BENCHMARK",
                "treatment_dimension": "MODEL",
                "real_hermes_inference": True,
                "validity": {name: "PASS" for name in (
                    "PROTOCOL_INTEGRITY",
                    "ASSIGNMENT_INTEGRITY",
                    "CONFIG_INTEGRITY",
                    "ENVIRONMENT_INTEGRITY",
                    "EXPOSURE_FIDELITY",
                    "OUTCOME_COVERAGE",
                    "EVALUATOR_COMPATIBILITY",
                    "MEMORY_ISOLATION",
                    "WORKSPACE_ISOLATION",
                )},
                "guardrail_state": "PASS",
            }
        )
        self.assertNotEqual(rec["classification"], "PRODUCTION_CANDIDATE")
        self.assertFalse(rec.get("active_policy"))

    def test_historical_par_patch_preserved(self) -> None:
        historical = ROOT / "patches/hermes/0001-pre-worker-spawn-hook.patch"
        upstream = ROOT / "patches/hermes/upstream/0001-worker-spawn-transform.patch"
        self.assertTrue(historical.is_file())
        self.assertTrue(upstream.is_file())
        blob = historical.read_text(encoding="utf-8")
        self.assertIn("pre_worker_spawn", blob)
        self.assertNotIn("transform_kanban_worker_spawn", blob)

    def test_cells_independent_and_disabled(self) -> None:
        values = cells()
        self.assertEqual(values["production_adaptation"], "DISABLED")
        self.assertEqual(values["secure_human_authority"], "READY_FOR_OPERATOR_BOOTSTRAP")
        self.assertEqual(values["real_causal_evidence"], "BLOCKED_BUDGET")
        self.assertEqual(values["pag2_readiness"], "BLOCKED_EVIDENCE_AND_AUTHORITY")
        self.assertEqual(values["upstream_actuation"], "READY_FOR_UPSTREAM_SUBMISSION")
        self.assertFalse(values["live_patch_deployed"])
        self.assertNotEqual(values["secure_human_authority"], values["upstream_actuation"])

    def test_budget_authorization_status_is_not_redacted(self) -> None:
        from engineering_os.redaction import redact

        payload = redact(
            {
                "cells": {
                    "budget_authorization": "READY_FOR_BUDGET_AUTHORIZATION",
                    "authorization": "planted-secret",
                }
            }
        )
        self.assertEqual(
            payload["cells"]["budget_authorization"],
            "READY_FOR_BUDGET_AUTHORIZATION",
        )
        self.assertEqual(payload["cells"]["authorization"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
