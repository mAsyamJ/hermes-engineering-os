"""PAG-2: IPC timeout, peer identity, atomic reservation, confirmatory freeze."""

from __future__ import annotations

import importlib.util
import os
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any

os.environ.setdefault("EOS_EVAL_SANDBOX", "inline")
os.environ["EOS_ADAPTATION_RUNTIME"] = tempfile.mkdtemp(prefix="eos-pag2-adapt-")
os.environ["EOS_EXPERIMENT_RUNTIME"] = tempfile.mkdtemp(prefix="eos-pag2-exp-")

from unittest.mock import patch

from engineering_os.adaptation.actuator import handle_request
from engineering_os.adaptation.approval_ed25519 import (
    CANONICAL_FIELDS,
    generate_approval_request,
    generate_ephemeral_keypair,
    sign_detached,
    verify_production_authorization,
)
from engineering_os.adaptation.ipc_client import request_spawn_resolution, strip_caller_authority
from engineering_os.adaptation.reserve import reset_memory, reserve_memory, reserve_sqlite
from engineering_os.experiments.budget_gate import require_budget_authorization
from engineering_os.experiments.budget_limits import HARD, SOFT, UNAVAILABLE, classify_budget
from engineering_os.experiments.definitions import load_id
from engineering_os.experiments.hard_runner import run_authorized_sequence
from engineering_os.experiments.paired_power import freeze_paired_horizon
from engineering_os.experiments.plan import plan_binary
from engineering_os.experiments.real_executor import run_isolated_real_unit

ROOT = Path(__file__).resolve().parents[2]
FAKE_SECRET = "FAKE_PAG2_SECRET_ABC123"
LIVE_PATCH = ROOT / "patches" / "hermes" / "live" / "0001-worker-spawn-transform-live.patch"
LIVE_PATCH_SHA256 = "51d4dd4d003143cdfea07d53668e8079f6d5163dc0a2777b3d5c3efd0001ecd4"


def _canary_state(**overrides):
    state = {
        "approval_id": "appr-a",
        "maximum_exposure": 1,
        "bindings": [
            {
                "mode": "CANARY",
                "state": "ACTIVE",
                "policy_hash": "ph",
                "policy_id": "p1",
                "spec": {
                    "policy_id": "p1",
                    "_policy_hash": "ph",
                    "selectors": {
                        "match": "ALL",
                        "conditions": [{"field": "board", "op": "EQ", "values": ["retropick-markets-release"]}],
                    },
                    "candidate": {"variant_id": "gpt-5.6-terra", "overrides": {"model": "gpt-5.6-terra"}},
                    "fallback": {"variant_id": "gpt-5.6-sol"},
                    "candidate_config_hash": "cand",
                },
            }
        ],
    }
    state.update(overrides)
    return state


class SampleSizeTests(unittest.TestCase):
    def test_v1_is_pilot_and_v2_is_conservative_freeze(self) -> None:
        eos = plan_binary(
            baseline_rate=0.20, mde=0.40, alpha=0.05, power=0.80, paired=True, discordance=0.50
        )
        frozen = freeze_paired_horizon(
            discordance=0.50, mde=0.40, alpha=0.05, power=0.80, eos_planner_n=int(eos["planned_n"])
        )
        self.assertEqual(int(eos["planned_n"]), 25)
        self.assertGreaterEqual(frozen["frozen_pairs"], frozen["eos_planner_n"])
        self.assertGreaterEqual(frozen["frozen_pairs"], frozen["connor_n"])
        self.assertGreaterEqual(frozen["frozen_pairs"], frozen["connor_continuity_n"])
        self.assertEqual(frozen["frozen_pairs"], 28)
        v1 = load_id("real-model-sol-vs-terra-v1")
        v2 = load_id("real-model-sol-vs-terra-v2")
        self.assertEqual(v1["sample_plan"]["planned_n"], 5)
        self.assertEqual(v2["sample_plan"]["planned_n"], 28)
        self.assertEqual(v2["budget"]["planned_max_units"], 56)
        self.assertEqual(v2["budget"]["max_llm_calls"], 0)
        classified = classify_budget(v2)
        hard_ids = {row["id"] for row in classified["hard"]}
        self.assertIn("max_units", hard_ids)
        self.assertIn("max_hermes_invocations", hard_ids)
        self.assertIn("max_wall_seconds_per_unit", hard_ids)
        self.assertIn("max_turns_per_unit", hard_ids)
        self.assertFalse(classified["quiet_flag_caps_turns"])
        self.assertTrue(any(row["enforcement"] == SOFT for row in classified["soft"]))
        self.assertTrue(any(row["enforcement"] == UNAVAILABLE for row in classified["unavailable"]))
        for row in classified["hard"]:
            self.assertEqual(row["enforcement"], HARD)


class IpcAndPeerTests(unittest.TestCase):
    def test_strip_caller_authority(self) -> None:
        cleaned = strip_caller_authority(
            {"task_id": "t1", "eligible": True, "candidate": "gpt-x", "exposure_remaining": 9}
        )
        self.assertEqual(cleaned, {"task_id": "t1"})

    def test_wrong_peer_is_baseline(self) -> None:
        reset_memory()
        result = handle_request(
            {
                "task_id": "t1",
                "task_context": {"board": "retropick-markets-release", "task_id": "t1", "eligible": True},
                "baseline": {"model": "gpt-5.6-sol"},
                "candidate": "gpt-5.6-terra",
            },
            peer_uid=1000,
            runtime_uid=2000,
            state=_canary_state(),
        )
        self.assertEqual(result["resolution"], "BASELINE")
        self.assertEqual(result["reason"], "PEER_REJECTED")

    def test_caller_claims_ignored_when_not_eligible(self) -> None:
        reset_memory()
        result = handle_request(
            {
                "task_id": "t1",
                "task_context": {"board": "other-board", "task_id": "t1", "eligible": True, "actuate": True},
                "baseline": {"model": "gpt-5.6-sol"},
                "candidate": "gpt-5.6-terra",
                "approval_valid": True,
            },
            peer_uid=2000,
            runtime_uid=2000,
            state=_canary_state(),
        )
        self.assertEqual(result["resolution"], "BASELINE")
        self.assertFalse(result["actuate"])

    def test_hung_actuator_times_out_without_thread_growth(self) -> None:
        tmp = Path(tempfile.mkdtemp()) / "hung.sock"
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(tmp))
        server.listen(1)

        def _accept_and_block() -> None:
            conn, _ = server.accept()
            time.sleep(2)
            conn.close()

        before = threading.active_count()
        t = threading.Thread(target=_accept_and_block, daemon=True)
        t.start()
        started = time.perf_counter()
        result = request_spawn_resolution(
            {"task_id": "t1"},
            {"model": "gpt-5.6-sol"},
            socket_path=str(tmp),
            timeout_s=0.05,
        )
        elapsed = time.perf_counter() - started
        self.assertEqual(result["resolution"], "BASELINE")
        self.assertLess(elapsed, 0.4)
        time.sleep(0.05)
        self.assertLessEqual(threading.active_count(), before + 2)
        server.close()


class ReservationTests(unittest.TestCase):
    def test_memory_cas_one_slot(self) -> None:
        reset_memory()
        a = reserve_memory(policy_hash="p", approval_id="a", unit_id="u1", maximum_exposure=1)
        b = reserve_memory(policy_hash="p", approval_id="a", unit_id="u2", maximum_exposure=1)
        self.assertTrue(a["reserved"])
        self.assertFalse(b["reserved"])
        self.assertEqual(b["reason"], "EXPOSURE_EXHAUSTED")

    def test_concurrent_sqlite_at_most_one(self) -> None:
        path = Path(tempfile.mkdtemp()) / "res.sqlite"
        results: list[dict] = []
        barrier = threading.Barrier(8)

        def _worker(i: int) -> None:
            barrier.wait()
            results.append(
                reserve_sqlite(
                    path,
                    policy_hash="p",
                    approval_id="a",
                    unit_id=f"u{i}",
                    maximum_exposure=1,
                )
            )

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(1 for row in results if row.get("reserved")), 1)

    def test_no_refund(self) -> None:
        path = Path(tempfile.mkdtemp()) / "res.sqlite"
        first = reserve_sqlite(path, policy_hash="p", approval_id="a", unit_id="u1", maximum_exposure=1)
        self.assertTrue(first["reserved"])
        second = reserve_sqlite(path, policy_hash="p", approval_id="a", unit_id="u2", maximum_exposure=1)
        self.assertFalse(second["reserved"])


class ApprovalBindingTests(unittest.TestCase):
    def test_runtime_identity_fields_are_canonical(self) -> None:
        for name in (
            "runtime_release_hash",
            "live_patch_hash",
            "actuator_contract_version",
            "trust_fingerprint",
        ):
            self.assertIn(name, CANONICAL_FIELDS)


class BudgetBindTests(unittest.TestCase):
    def test_v2_rejects_over_protocol_ceiling(self) -> None:
        definition = load_id("real-model-sol-vs-terra-v2")
        path = Path(os.environ["EOS_EXPERIMENT_RUNTIME"]) / "LLM_BUDGET_AUTHORIZATION"
        path.write_text(
            __import__("json").dumps(
                {
                    "protocol_id": definition["experiment_id"],
                    "protocol_hash": definition["_definition_hash"],
                    "max_units": 99,
                    "max_llm_calls": 99,
                    "control_model": "gpt-5.6-sol",
                    "candidate_model": "gpt-5.6-terra",
                    "scope": "BENCHMARK",
                    "expiry": "2027-01-01T00:00:00+00:00",
                    "created_by": "human-operator",
                }
            ),
            encoding="utf-8",
        )
        gate = require_budget_authorization(definition)
        self.assertFalse(gate["ok"])
        path.unlink()


class ExecutorHardLimitTests(unittest.TestCase):
    def test_per_unit_timeout_and_max_turns_argv(self) -> None:
        definition = load_id("real-model-sol-vs-terra-v2")
        captured: dict[str, Any] = {}

        class _Proc:
            returncode = 0
            stdout = "ok"
            stderr = ""

        def _run(argv, **kwargs):
            captured["argv"] = argv
            captured["timeout"] = kwargs.get("timeout")
            captured["env"] = kwargs.get("env")
            return _Proc()

        with patch("engineering_os.experiments.real_executor.subprocess.run", side_effect=_run):
            result = run_isolated_real_unit(
                {"unit_id": "u1", "case_id": "real-v1-bugfix", "variant_role": "CONTROL"},
                definition,
                {"max_llm_calls": 1},
            )
        self.assertIn("--max-turns", captured["argv"])
        self.assertEqual(captured["argv"][captured["argv"].index("--max-turns") + 1], "20")
        self.assertEqual(captured["timeout"], 720)
        self.assertEqual(captured["env"].get("HERMES_MAX_ITERATIONS"), "20")
        self.assertEqual(result["status"], "COMPLETE")
        self.assertNotIn(FAKE_SECRET, str(result))

    def test_live_cli_max_turns_priority_and_iteration_budget_stops(self) -> None:
        cli = Path("/home/ubuntu/.hermes/hermes-agent/cli.py").read_text(encoding="utf-8")
        self.assertIn('elif os.getenv("HERMES_MAX_ITERATIONS")', cli)
        constructor = cli[cli.find("if max_turns is not None") : cli.find("self.enabled_toolsets")]
        self.assertLess(constructor.find("if max_turns is not None"), constructor.find("HERMES_MAX_ITERATIONS"))
        parser = Path("/home/ubuntu/.hermes/hermes-agent/hermes_cli/_parser.py").read_text(encoding="utf-8")
        self.assertIn('"--max-turns"', parser)
        spec = importlib.util.spec_from_file_location(
            "iteration_budget",
            "/home/ubuntu/.hermes/hermes-agent/agent/iteration_budget.py",
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        budget = module.IterationBudget(3)
        self.assertTrue(budget.consume())
        self.assertTrue(budget.consume())
        self.assertTrue(budget.consume())
        self.assertFalse(budget.consume())
        self.assertEqual(budget.used, 3)

    def test_hard_runner_stops_before_extra_unit(self) -> None:
        definition = load_id("real-model-sol-vs-terra-v2")
        path = Path(os.environ["EOS_EXPERIMENT_RUNTIME"]) / "LLM_BUDGET_AUTHORIZATION"
        path.write_text(
            __import__("json").dumps(
                {
                    "protocol_id": definition["experiment_id"],
                    "protocol_hash": definition["_definition_hash"],
                    "max_units": 2,
                    "max_llm_calls": 2,
                    "control_model": "gpt-5.6-sol",
                    "candidate_model": "gpt-5.6-terra",
                    "scope": "BENCHMARK",
                    "expiry": "2027-01-01T00:00:00+00:00",
                    "created_by": "human-operator",
                }
            ),
            encoding="utf-8",
        )
        calls = {"n": 0}

        def _unit(*_args, **_kwargs):
            calls["n"] += 1
            return {"executed": True, "llm_calls": 1, "status": "COMPLETE"}

        with patch("engineering_os.experiments.hard_runner.execute_authorized_unit", side_effect=_unit):
            payload = run_authorized_sequence(
                [{"unit_id": "a"}, {"unit_id": "b"}, {"unit_id": "c"}],
                definition,
            )
        self.assertEqual(payload["status"], "HARD_STOP_UNITS")
        self.assertEqual(payload["units"], 2)
        self.assertEqual(calls["n"], 2)
        path.unlink()


class ProtectedTrustTests(unittest.TestCase):
    def test_caller_supplied_key_is_ignored_while_unprotected(self) -> None:
        keys = generate_ephemeral_keypair()
        request = generate_approval_request(
            recommendation_id="r",
            policy_id="p",
            policy_hash="h",
            policy_version="1",
            approval_stage="A",
            scope="PRODUCTION_CANARY",
            maximum_exposure=1,
            candidate_config_hash="c",
            fallback_hash="f",
            rollback_hash="rb",
            expiry="2027-01-01T00:00:00+00:00",
        )
        signature = sign_detached(request, keys["private"])
        payload = verify_production_authorization(request, signature, keys["public"])
        self.assertEqual(payload["status"], "BLOCKED_SECURITY_BOUNDARY")
        self.assertFalse(payload["granted"])
        self.assertTrue(payload["agent_replaceable"])

    def test_protected_path_uses_installed_key_not_caller_key(self) -> None:
        installed = generate_ephemeral_keypair()
        attacker = generate_ephemeral_keypair()
        request = generate_approval_request(
            recommendation_id="r",
            policy_id="p",
            policy_hash="h",
            policy_version="1",
            approval_stage="A",
            scope="PRODUCTION_CANARY",
            maximum_exposure=1,
            candidate_config_hash="c",
            fallback_hash="f",
            rollback_hash="rb",
            expiry="2027-01-01T00:00:00+00:00",
        )
        good = sign_detached(request, installed["private"])
        with patch(
            "engineering_os.adaptation.approval_ed25519.production_trust_anchor_status",
            return_value={
                "status": "PROTECTED_TRUST_PRESENT",
                "granted": False,
                "agent_replaceable": False,
            },
        ), patch(
            "engineering_os.adaptation.approval_ed25519.load_protected_public_key",
            return_value=installed["public"],
        ):
            ok = verify_production_authorization(request, good, attacker["public"])
            attacker_request = generate_approval_request(
                recommendation_id="r",
                policy_id="p",
                policy_hash="h",
                policy_version="1",
                approval_stage="A",
                scope="PRODUCTION_CANARY",
                maximum_exposure=1,
                candidate_config_hash="c",
                fallback_hash="f",
                rollback_hash="rb",
                expiry="2027-01-01T00:00:00+00:00",
            )
            bad = verify_production_authorization(
                attacker_request,
                sign_detached(attacker_request, attacker["private"]),
                attacker["public"],
            )
        self.assertTrue(ok.get("ok"), ok)
        self.assertTrue(ok["granted"])
        self.assertFalse(bad["ok"])


class LivePatchAndBoundaryTests(unittest.TestCase):
    def test_live_patch_hash_and_not_deployed(self) -> None:
        import hashlib

        digest = hashlib.sha256(LIVE_PATCH.read_bytes()).hexdigest()
        self.assertEqual(digest, LIVE_PATCH_SHA256)
        live_src = Path("/home/ubuntu/.hermes/hermes-agent/hermes_cli/kanban_db.py").read_text(encoding="utf-8")
        self.assertNotIn("transform_kanban_worker_spawn", live_src)
        self.assertNotIn("ThreadPoolExecutor", LIVE_PATCH.read_text(encoding="utf-8"))

    def test_boundary_verifier_not_fake_pass(self) -> None:
        proc = subprocess.run(
            [str(ROOT / "scripts/verify-operator-boundary.sh")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        status_line = next(line for line in proc.stdout.splitlines() if line.startswith("status="))
        self.assertEqual(status_line, "status=READY_FOR_HUMAN")
        self.assertIn("AUTH_AGENT_PASSWORDLESS_ROOT", proc.stdout)
        self.assertIn("AUTH_NO_HERMES_OP", proc.stdout)
        self.assertIn("AUTH_NO_HERMES_RUNTIME", proc.stdout)
        self.assertIn("AUTH_NO_HERMES_ACTUATOR", proc.stdout)
        self.assertIn("AUTH_GATEWAY_RUNS_AS_AGENT", proc.stdout)
        self.assertNotIn(FAKE_SECRET, proc.stdout)


class ShadowCanaryAndDeployTests(unittest.TestCase):
    def test_shadow_does_not_consume_exposure(self) -> None:
        reset_memory()
        shadow = _canary_state()
        shadow["bindings"][0]["mode"] = "SHADOW"
        first = handle_request(
            {
                "task_id": "t1",
                "task_context": {"board": "retropick-markets-release", "task_id": "t1"},
                "baseline": {"model": "gpt-5.6-sol"},
            },
            peer_uid=2000,
            runtime_uid=2000,
            state=shadow,
        )
        second = handle_request(
            {
                "task_id": "t2",
                "task_context": {"board": "retropick-markets-release", "task_id": "t2"},
                "baseline": {"model": "gpt-5.6-sol"},
            },
            peer_uid=2000,
            runtime_uid=2000,
            state=shadow,
        )
        self.assertFalse(first.get("actuate"))
        self.assertFalse(second.get("actuate"))
        self.assertNotIn("reservation", first)

    def test_canary_reserves_once_full_scope_stays_disabled(self) -> None:
        from engineering_os.adaptation.spawn_resolve import resolve_spawn_configuration

        reset_memory()
        first = handle_request(
            {
                "task_id": "t1",
                "task_context": {"board": "retropick-markets-release", "task_id": "t1"},
                "baseline": {"model": "gpt-5.6-sol"},
            },
            peer_uid=2000,
            runtime_uid=2000,
            state=_canary_state(),
        )
        second = handle_request(
            {
                "task_id": "t2",
                "task_context": {"board": "retropick-markets-release", "task_id": "t2"},
                "baseline": {"model": "gpt-5.6-sol"},
            },
            peer_uid=2000,
            runtime_uid=2000,
            state=_canary_state(),
        )
        self.assertEqual(first["resolution"], "CANDIDATE")
        self.assertTrue(first.get("actuate"))
        self.assertTrue(first.get("reservation", {}).get("reserved"))
        self.assertEqual(second["resolution"], "BASELINE")
        blocked = resolve_spawn_configuration(
            {"scope": "PRODUCTION_FULL", "environment": "production", "board": "retropick-markets-release"},
            {"model": "gpt-5.6-sol"},
            state=_canary_state(),
        )
        self.assertEqual(blocked["reason"], "PRODUCTION_ACTUATION_DISABLED")

    def test_deploy_tool_rejects_git_ref_and_ubuntu_install(self) -> None:
        import json
        import tempfile

        artifact = ROOT / "patches" / "hermes" / "live" / "0001-worker-spawn-transform-live.patch"
        tmp = Path(tempfile.mkdtemp())
        good = {
            "base_runtime_hash": "c0106e50e7ecedb3ce34e785d949725dc4e0e457",
            "artifact_sha256": LIVE_PATCH_SHA256,
            "affected_files": ["hermes_cli/kanban_db.py"],
            "affected_units": ["hermes-gateway.service"],
            "rollback_hash": "c0106e50e7ecedb3ce34e785d949725dc4e0e457",
            "expiry": "2027-01-01T00:00:00+00:00",
            "nonce": "n1",
        }
        manifest = tmp / "m.json"
        manifest.write_text(json.dumps(good), encoding="utf-8")
        tool = str(ROOT / "scripts/hermes-eos-deploy-tool.py")
        verify = subprocess.run(
            [tool, "verify", "--manifest", str(manifest), "--artifact", str(artifact)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(verify.returncode, 0, verify.stderr)
        bad = dict(good)
        bad["git_ref"] = "main"
        bad_path = tmp / "bad.json"
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        gitref = subprocess.run(
            [tool, "verify", "--manifest", str(bad_path), "--artifact", str(artifact)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(gitref.returncode, 0)
        install = subprocess.run(
            [tool, "install", "--manifest", str(manifest), "--artifact", str(artifact), "--signature", "00"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(install.returncode, 0)
        self.assertIn("ubuntu cannot invoke", (install.stderr + install.stdout).lower())


class RuntimeIdentityAndDisableTests(unittest.TestCase):
    def test_runtime_identity_mismatch_is_baseline(self) -> None:
        os.environ["HERMES_EOS_RUNTIME_RELEASE_HASH"] = "live-sha"
        state = _canary_state()
        state["runtime_identity"] = {
            "runtime_release_hash": "other-sha",
            "actuator_contract_version": "pag2-actuator-v1",
        }
        result = handle_request(
            {
                "task_id": "t1",
                "task_context": {"board": "retropick-markets-release", "task_id": "t1"},
                "baseline": {"model": "gpt-5.6-sol"},
            },
            peer_uid=2000,
            runtime_uid=2000,
            state=state,
        )
        self.assertEqual(result["resolution"], "BASELINE")
        self.assertIn("mismatch", result["reason"])
        os.environ.pop("HERMES_EOS_RUNTIME_RELEASE_HASH", None)

    def test_auto_disable_does_not_interrupt_running(self) -> None:
        from engineering_os.adaptation.rollback import apply_auto_disable

        payload = apply_auto_disable(
            {"binding_version": 3, "state": "ACTIVE", "mode": "CANARY"},
            reason="GUARDRAIL_FAIL",
        )
        self.assertEqual(payload["state"], "ROLLED_BACK")
        self.assertFalse(payload["interrupt_running"])
        self.assertFalse(payload["auto_promote"])
        self.assertFalse(payload["mutate_git"])

    def test_apply_artifact_roundtrip_in_isolated_git(self) -> None:
        import json
        import tempfile

        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "deploy_tool", ROOT / "scripts" / "hermes-eos-deploy-tool.py"
        )
        tool = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(tool)
        tmp = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", str(tmp)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp), "config", "user.email", "pag2@example.test"], check=True)
        subprocess.run(["git", "-C", str(tmp), "config", "user.name", "pag2"], check=True)
        (tmp / "note.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(tmp), "add", "note.txt"], check=True)
        subprocess.run(["git", "-C", str(tmp), "commit", "-m", "base"], check=True, capture_output=True)
        patch = tmp / "p.patch"
        patch.write_text(
            "diff --git a/note.txt b/note.txt\n"
            "--- a/note.txt\n"
            "+++ b/note.txt\n"
            "@@ -1 +1 @@\n"
            "-base\n"
            "+cand\n",
            encoding="utf-8",
        )
        tool.apply_artifact({}, patch, tmp)
        self.assertEqual((tmp / "note.txt").read_text(encoding="utf-8"), "cand\n")
        tool.reverse_artifact(patch, tmp)
        self.assertEqual((tmp / "note.txt").read_text(encoding="utf-8"), "base\n")


if __name__ == "__main__":
    unittest.main()
