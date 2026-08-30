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

    def test_h2_write_requires_h1_and_exact_phrase(self) -> None:
        from engineering_os.experiments.budget_gate import H2_AUTHORIZE_PHRASE, write_h2_authorization

        definition = load_id("real-model-sol-vs-terra-v2")
        blocked = write_h2_authorization(
            phrase=H2_AUTHORIZE_PHRASE,
            created_by="human-operator",
            expiry="2027-01-01T00:00:00+00:00",
            h1_status="READY_FOR_HUMAN",
            protocol=definition,
        )
        self.assertEqual(blocked["status"], "BLOCKED_SECURITY_BOUNDARY")
        wrong = write_h2_authorization(
            phrase="yes",
            created_by="human-operator",
            expiry="2027-01-01T00:00:00+00:00",
            h1_status="PASS",
            protocol=definition,
        )
        self.assertEqual(wrong["status"], "PHRASE_MISMATCH")
        auto = write_h2_authorization(
            phrase=H2_AUTHORIZE_PHRASE,
            created_by="pag1-bot",
            expiry="2027-01-01T00:00:00+00:00",
            h1_status="PASS",
            protocol=definition,
        )
        self.assertEqual(auto["status"], "INVALID")
        path = Path(os.environ["EOS_EXPERIMENT_RUNTIME"]) / "LLM_BUDGET_AUTHORIZATION"
        if path.exists():
            path.unlink()
        ok = write_h2_authorization(
            phrase=H2_AUTHORIZE_PHRASE,
            created_by="human-operator",
            expiry="2027-01-01T00:00:00+00:00",
            h1_status="PASS",
            protocol=definition,
        )
        self.assertTrue(ok["ok"])
        self.assertTrue(path.is_file())
        again = write_h2_authorization(
            phrase=H2_AUTHORIZE_PHRASE,
            created_by="human-operator",
            expiry="2027-01-01T00:00:00+00:00",
            h1_status="PASS",
            protocol=definition,
        )
        self.assertEqual(again["status"], "EXISTS")
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
            captured.setdefault("calls", []).append({"argv": argv, "timeout": kwargs.get("timeout"), "env": kwargs.get("env")})
            if "chat" in argv or any(str(part).endswith("hermes") for part in argv[:1]):
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

        try:
            with patch("engineering_os.experiments.hard_runner.execute_authorized_unit", side_effect=_unit):
                payload = run_authorized_sequence(
                    [{"unit_id": "a"}, {"unit_id": "b"}, {"unit_id": "c"}],
                    definition,
                )
            self.assertEqual(payload["status"], "HARD_STOP_UNITS")
            self.assertEqual(payload["units"], 2)
            self.assertEqual(calls["n"], 2)
            self.assertFalse(payload.get("auto_promote"))
        finally:
            path.unlink(missing_ok=True)

    def test_confirmatory_assignments_are_56_units_over_five_templates(self) -> None:
        from engineering_os.experiments.hard_runner import assignments_from_protocol

        definition = load_id("real-model-sol-vs-terra-v2")
        rows = assignments_from_protocol(definition)
        self.assertEqual(len(rows), 56)
        self.assertEqual(sum(1 for row in rows if row["variant_role"] == "CONTROL"), 28)
        allowed = {
            "real-v1-bugfix",
            "real-v1-feature",
            "real-v1-refactor",
            "real-v1-test-repair",
            "real-v1-config",
        }
        self.assertTrue(set(row["case_id"] for row in rows) <= allowed)
        self.assertEqual(len({row["pair_id"] for row in rows}), 28)

    def test_run_real_cli_is_blocked_without_authorization(self) -> None:
        from io import StringIO

        from engineering_os.experiments.cli import main

        auth = Path(os.environ["EOS_EXPERIMENT_RUNTIME"]) / "LLM_BUDGET_AUTHORIZATION"
        if auth.exists():
            auth.unlink()
        buf = StringIO()
        with patch("sys.stdout", buf):
            rc = main(["run-real", "real-model-sol-vs-terra-v2"])
        self.assertEqual(rc, 1)
        self.assertIn("READY_FOR_BUDGET_AUTHORIZATION", buf.getvalue())
        self.assertIn('"executed": false', buf.getvalue())

    def test_pag2_labels_do_not_invent_a_winner(self) -> None:
        from engineering_os.experiments.real_analyze import analyze_real_sequence, pag2_label

        self.assertEqual(pag2_label({"conclusion": "COLLECTING"}), "COLLECTING")
        self.assertEqual(pag2_label({"conclusion": "INVALIDATED"}), "INVALIDATED")
        self.assertEqual(pag2_label({"conclusion": "NO_CLEAR_EFFECT"}), "VALID_NO_PROMOTION")
        self.assertEqual(pag2_label({"conclusion": "EVIDENCE_AGAINST_CANDIDATE"}), "VALID_NO_PROMOTION")
        self.assertEqual(
            pag2_label(
                {"conclusion": "EVIDENCE_FOR_CANDIDATE"},
                {"production_promotable": True, "classification": "PRODUCTION_CANDIDATE"},
            ),
            "QUALIFIED_CANDIDATE",
        )
        self.assertEqual(
            pag2_label({"conclusion": "EVIDENCE_FOR_CANDIDATE"}, {"production_promotable": False}),
            "VALID_NO_PROMOTION",
        )
        definition = load_id("real-model-sol-vs-terra-v2")
        tiny = dict(definition)
        tiny["sample_plan"] = dict(definition["sample_plan"], planned_n=1)
        assignments = [
            {"unit_id": "p:control", "pair_id": "p", "variant_role": "CONTROL"},
            {"unit_id": "p:candidate", "pair_id": "p", "variant_role": "CANDIDATE"},
        ]
        iso = {"ok": True, "state": "PASS"}
        results = [
            {
                "unit_id": "p:control",
                "primary_value": "FAIL",
                "quality_vector": {"tests": "FAIL", "security": "PASS"},
                "memory_isolation": iso,
                "workspace_isolation": iso,
            },
            {
                "unit_id": "p:candidate",
                "primary_value": "FAIL",
                "quality_vector": {"tests": "FAIL", "security": "PASS"},
                "memory_isolation": iso,
                "workspace_isolation": iso,
            },
        ]
        payload = analyze_real_sequence(tiny, assignments, results, final=True)
        self.assertIn(payload["pag2_label"], {"VALID_NO_PROMOTION", "COLLECTING"})
        self.assertNotEqual(payload["pag2_label"], "QUALIFIED_CANDIDATE")
        self.assertEqual(payload["protocol_hash"], tiny["_definition_hash"])
        self.assertFalse(payload["auto_promote"])
        self.assertFalse(payload["recommendation"].get("auto_promote"))

    def test_analyze_persisted_writes_analysis_json(self) -> None:
        import json

        from engineering_os.experiments.real_analyze import analyze_persisted, artifact_dir, persist_sequence

        definition = load_id("real-model-sol-vs-terra-v2")
        assignments = [
            {"unit_id": "p:control", "pair_id": "p", "variant_role": "CONTROL"},
            {"unit_id": "p:candidate", "pair_id": "p", "variant_role": "CANDIDATE"},
        ]
        iso = {"ok": True, "state": "PASS"}
        results = [
            {
                "unit_id": "p:control",
                "primary_value": "FAIL",
                "quality_vector": {"tests": "FAIL", "security": "PASS"},
                "memory_isolation": iso,
                "workspace_isolation": iso,
            },
            {
                "unit_id": "p:candidate",
                "primary_value": "FAIL",
                "quality_vector": {"tests": "FAIL", "security": "PASS"},
                "memory_isolation": iso,
                "workspace_isolation": iso,
            },
        ]
        persist_sequence(definition, assignments, results)
        payload = analyze_persisted(definition["experiment_id"], definition, final=True)
        path = artifact_dir(definition) / "analysis.json"
        self.assertTrue(path.is_file())
        written = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(written["pag2_label"], payload["pag2_label"])
        self.assertEqual(written["protocol_hash"], definition["_definition_hash"])
        self.assertFalse(written["auto_promote"])

    def test_isolated_unit_evaluates_primary_and_leaves_production_memory(self) -> None:
        definition = load_id("real-model-sol-vs-terra-v2")
        from engineering_os.experiments.memory_snapshot import production_memory_fingerprint

        before = production_memory_fingerprint()

        class _Proc:
            returncode = 0
            stdout = "ok"
            stderr = ""

        with patch("engineering_os.experiments.real_executor.subprocess.run", return_value=_Proc()):
            result = run_isolated_real_unit(
                {"unit_id": "eval-1", "case_id": "real-v1-bugfix", "variant_role": "CONTROL"},
                definition,
                {"max_llm_calls": 1},
            )
        self.assertIn(result["primary_value"], {"PASS", "FAIL"})
        self.assertTrue((result["memory_isolation"] or {}).get("production_unchanged"))
        self.assertTrue((result["workspace_isolation"] or {}).get("workspace_not_production"))
        self.assertEqual(production_memory_fingerprint(), before)
        from engineering_os.experiments.memory_snapshot import production_memory_paths
        from engineering_os.experiments.real_executor import _workspace_not_production

        names = [str(path) for path in production_memory_paths()]
        self.assertIn("/var/lib/hermes-runtime/home/memories", names)
        self.assertIn("/home/ubuntu/.hermes/memories", names)
        self.assertFalse(_workspace_not_production(Path("/var/lib/hermes-runtime/home")))
        self.assertFalse(_workspace_not_production(Path("/usr/lib/hermes-runtime/hermes-agent")))

    def test_isolated_hermes_home_is_profile_and_does_not_copy_auth(self) -> None:
        definition = load_id("real-model-sol-vs-terra-v2")
        captured: dict[str, Any] = {}

        class _Proc:
            returncode = 0
            stdout = "ok"
            stderr = ""

        def _run(argv, **kwargs):
            env = kwargs.get("env") or {}
            if env.get("HERMES_HOME"):
                captured["env"] = env
            return _Proc()

        fake_auth = Path(tempfile.mkdtemp()) / "auth.json"
        fake_auth.write_text("{}\n", encoding="utf-8")
        with patch("engineering_os.experiments.real_executor._production_codex_auth", return_value=fake_auth):
            with patch("engineering_os.experiments.real_executor.subprocess.run", side_effect=_run):
                result = run_isolated_real_unit(
                {"unit_id": "auth-bridge-1", "case_id": "real-v1-bugfix", "variant_role": "CONTROL"},
                definition,
                {"max_llm_calls": 1},
            )
        self.assertTrue(result.get("executed"), result)
        home = Path(captured["env"]["HERMES_HOME"])
        self.assertEqual(home.parent.name, "profiles")
        memory_root = Path(result["memory_root"])
        self.assertFalse((memory_root / "arm-a" / "auth.json").exists())
        self.assertFalse((memory_root / "arm-b" / "auth.json").exists())
        self.assertTrue((home / "config.yaml").is_file() or home.is_symlink())

    def test_serve_forever_rejects_non_runtime_peer(self) -> None:
        from engineering_os.adaptation.actuator import serve_forever
        from engineering_os.adaptation.ipc_client import request_spawn_resolution

        tmp = Path(tempfile.mkdtemp()) / "act.sock"
        stop = threading.Event()
        thread = threading.Thread(
            target=serve_forever,
            kwargs={"socket_path": str(tmp), "runtime_uid": -1, "stop": stop},
            daemon=True,
        )
        thread.start()
        for _ in range(50):
            if tmp.exists():
                break
            time.sleep(0.02)
        self.assertTrue(tmp.exists())
        result = {"reason": "ConnectionRefusedError"}
        for _ in range(50):
            result = request_spawn_resolution(
                {"task_id": "t-peer"},
                {"model": "gpt-5.6-sol"},
                socket_path=str(tmp),
                timeout_s=1.0,
            )
            if result.get("reason") != "ConnectionRefusedError":
                break
            time.sleep(0.02)
        stop.set()
        thread.join(timeout=2)
        self.assertEqual(result["resolution"], "BASELINE")
        self.assertEqual(result["reason"], "PEER_REJECTED")

    def test_ipc_probe_does_not_require_candidate_and_does_not_actuate(self) -> None:
        from engineering_os.adaptation.actuator import serve_forever
        from engineering_os.adaptation.pag2_ops import production_ipc_probe

        missing = production_ipc_probe(socket_path="/tmp/pag2-no-such-actuator.sock", timeout_s=0.2)
        self.assertEqual(missing["status"], "BLOCKED_IPC")
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["exposure_consumed"], 0)

        tmp = Path(tempfile.mkdtemp()) / "probe.sock"
        stop = threading.Event()
        thread = threading.Thread(
            target=serve_forever,
            kwargs={"socket_path": str(tmp), "runtime_uid": os.getuid(), "stop": stop},
            daemon=True,
        )
        thread.start()
        for _ in range(50):
            if tmp.exists():
                break
            time.sleep(0.02)
        self.assertTrue(tmp.exists())
        payload = {"status": "BLOCKED_IPC"}
        for _ in range(50):
            payload = production_ipc_probe(socket_path=str(tmp), timeout_s=1.0)
            if payload.get("status") != "BLOCKED_IPC":
                break
            time.sleep(0.02)
        stop.set()
        thread.join(timeout=2)
        self.assertEqual(payload["status"], "PASS", payload)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["actuate"])
        self.assertEqual(payload["exposure_consumed"], 0)
        self.assertIsNone((payload.get("ipc") or {}).get("reservation"))
        self.assertEqual((payload.get("ipc") or {}).get("reason"), "SHADOW_NO_ACTUATE")
        would = str((payload.get("ipc") or {}).get("would_reason") or "")
        self.assertNotIn("OSError", would)
        self.assertNotIn("Read-only", would)

    def test_protected_production_path_never_writes_tcb(self) -> None:
        from engineering_os.adaptation import paths as adapt_paths
        from engineering_os.adaptation.pag2_ops import production_ipc_probe
        from engineering_os.adaptation.resolver import resolve_policy

        recorded: list[str] = []
        orig = Path.mkdir

        def spy(self: Path, *args: Any, **kwargs: Any) -> None:
            recorded.append(str(self))
            if str(self).startswith("/usr/local/lib/hermes-eos"):
                raise OSError(30, "Read-only file system")
            if str(self).startswith("/var/lib/hermes-actuator"):
                return None
            return orig(self, *args, **kwargs)

        prev_adapt = os.environ.get("EOS_ADAPTATION_RUNTIME")
        prev_state = os.environ.get("HERMES_EOS_ACTUATOR_STATE")
        try:
            os.environ.pop("EOS_ADAPTATION_RUNTIME", None)
            os.environ.pop("HERMES_EOS_ACTUATOR_RUNTIME", None)
            os.environ["HERMES_EOS_ACTUATOR_STATE"] = "/var/lib/hermes-actuator/state.json"
            os.environ["EOS_ADAPTATION_RUNTIME"] = "/usr/local/lib/hermes-eos/.runtime"
            refused = adapt_paths.adaptation_runtime_dir(create=False)
            self.assertEqual(refused, adapt_paths.ACTUATOR_ADAPTATION)
            os.environ.pop("EOS_ADAPTATION_RUNTIME", None)
            with patch.object(Path, "mkdir", spy):
                with patch.object(adapt_paths, "package_root", return_value=Path("/usr/local/lib/hermes-eos")):
                    path = adapt_paths.adaptation_runtime_dir(create=True)
                    self.assertEqual(path, adapt_paths.ACTUATOR_ADAPTATION)
                    decision = resolve_policy(
                        {
                            "board": "retropick-markets-release",
                            "scope": "PRODUCTION_SHADOW",
                            "environment": "production",
                        },
                        state={"bindings": []},
                    )
            self.assertNotIn("OSError", str(decision.get("reason") or ""))
            self.assertFalse(any(item.startswith("/usr/local/lib/hermes-eos") for item in recorded), recorded)
        finally:
            if prev_adapt is None:
                os.environ.pop("EOS_ADAPTATION_RUNTIME", None)
            else:
                os.environ["EOS_ADAPTATION_RUNTIME"] = prev_adapt
            if prev_state is None:
                os.environ.pop("HERMES_EOS_ACTUATOR_STATE", None)
            else:
                os.environ["HERMES_EOS_ACTUATOR_STATE"] = prev_state

        with patch(
            "engineering_os.adaptation.pag2_ops.request_spawn_resolution",
            return_value={
                "resolution": "BASELINE",
                "actuate": False,
                "reason": "SHADOW_NO_ACTUATE",
                "would_reason": "OSError: [Errno 30] Read-only file system: '/usr/local/lib/hermes-eos/.runtime'",
                "reservation": None,
            },
        ):
            blocked = production_ipc_probe(socket_path="/tmp/unused.sock", timeout_s=0.1)
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["status"], "FAIL")
        self.assertEqual(blocked["exposure_consumed"], 0)
        self.assertIn("Read-only file system", blocked["reason"])

    def test_serve_forever_inherited_listen_socket(self) -> None:
        from engineering_os.adaptation.actuator import serve_forever
        from engineering_os.adaptation.ipc_client import request_spawn_resolution

        tmp = Path(tempfile.mkdtemp()) / "inh.sock"
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(tmp))
        listener.listen(16)
        stop = threading.Event()
        thread = threading.Thread(
            target=serve_forever,
            kwargs={
                "socket_path": str(tmp),
                "runtime_uid": -1,
                "stop": stop,
                "listen_socket": listener,
            },
            daemon=True,
        )
        thread.start()
        result = request_spawn_resolution(
            {"task_id": "t-inh"},
            {"model": "gpt-5.6-sol"},
            socket_path=str(tmp),
            timeout_s=1.0,
        )
        stop.set()
        thread.join(timeout=2)
        self.assertEqual(result["resolution"], "BASELINE")
        self.assertEqual(result["reason"], "PEER_REJECTED")


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
        self.assertFalse(payload.get("granted"))
        if payload["status"] == "PROTECTED_TRUST_PRESENT":
            self.assertFalse(payload.get("ok"))
        else:
            self.assertEqual(payload["status"], "BLOCKED_SECURITY_BOUNDARY")
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

    def test_h1_cutover_refuses_ubuntu_and_uses_ubuntu_machine(self) -> None:
        script = (ROOT / "scripts/h1-cutover.sh").read_text(encoding="utf-8")
        self.assertIn('SUDO_USER:-}" != "hermes-op"', script)
        self.assertIn("systemctl --user -M ubuntu@", script)
        self.assertIn("safe.directory", script)
        self.assertIn("a+rX,go-w", script)
        self.assertIn("SMOKE_OK", script)
        self.assertIn("runuser -u hermes-runtime", script)
        self.assertIn("state.json", script)
        self.assertIn("deploy-nonces", script)
        self.assertIn("verify-operator-boundary.sh", script)
        self.assertIn("pag2-inspect-ubuntu.sh", script)
        self.assertIn("eos-actuation-plugin", script)
        preflight = (ROOT / "scripts/h1-preflight-ssh.sh").read_text(encoding="utf-8")
        self.assertIn("hermes-op", preflight)
        self.assertIn("passwordauthentication no", preflight)
        self.assertIn("/usr/local/lib/hermes-eos/scripts/", script)
        self.assertIn('readlink -f "$LIVE/venv/bin/python"', script)
        self.assertIn("EOS_ADAPTATION_RUNTIME=/var/lib/hermes-actuator/adaptation", script)
        self.assertIn("/var/lib/hermes-actuator/adaptation", script)
        unit = (ROOT / "deploy/pag2/hermes-eos-actuator.service").read_text(encoding="utf-8")
        self.assertIn("EOS_ADAPTATION_RUNTIME=/var/lib/hermes-actuator/adaptation", unit)
        self.assertIn("ReadWritePaths=/var/lib/hermes-actuator /run/hermes-eos", unit)
        self.assertIn("--exclude .cache", script)
        postcheck = (ROOT / "scripts/h1-postcheck.sh").read_text(encoding="utf-8")
        self.assertIn("except FileNotFoundError:", postcheck)
        self.assertIn("not ubuntu-visible (0750)", postcheck)
        self.assertIn("=== disk preflight", script)
        self.assertIn("ubuntu gateways left running", script)
        self.assertIn('stop --job-mode=replace-irreversibly "$unit"', script)
        self.assertLess(script.find("=== disk preflight"), script.find("=== drain and STOP ubuntu user gateways"))
        self.assertNotIn("stat -c '%U %a %n' /var/lib/hermes-runtime/home/.env /var/lib/hermes-runtime/home/auth.json", script)
        sudoers_op = (ROOT / "deploy/pag2/sudoers-hermes-op").read_text(encoding="utf-8")
        sudoers_agent = (ROOT / "deploy/pag2/sudoers-ubuntu").read_text(encoding="utf-8")
        self.assertIn("hermes-op ALL=(ALL) NOPASSWD: ALL", sudoers_op)
        active = [
            line.strip()
            for line in sudoers_agent.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        self.assertEqual(active, [])
        proc = subprocess.run(
            ["sudo", "-n", str(ROOT / "scripts/h1-cutover.sh")],
            check=False,
            capture_output=True,
            text=True,
        )
        denied = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, denied)
        self.assertTrue("REFUSED" in denied or "password is required" in denied, denied)
        self.assertNotIn("CUTOVER_DONE", proc.stdout)
        runtime = subprocess.run(
            ["sudo", "-n", str(ROOT / "scripts/pag2-as-runtime.sh"), "pag2-shadow"],
            check=False,
            capture_output=True,
            text=True,
        )
        runtime_out = runtime.stdout + runtime.stderr
        self.assertNotEqual(runtime.returncode, 0)
        self.assertTrue("REFUSED" in runtime_out or "password is required" in runtime_out, runtime_out)

    def test_boundary_verifier_not_fake_pass(self) -> None:
        proc = subprocess.run(
            [str(ROOT / "scripts/verify-operator-boundary.sh")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        status_line = next(line for line in proc.stdout.splitlines() if line.startswith("status="))
        if status_line == "status=PASS":
            self.assertNotIn("AUTH_AGENT_PASSWORDLESS_ROOT", proc.stdout)
            self.assertNotIn("AUTH_GATEWAY_RUNS_AS_AGENT", proc.stdout)
        else:
            self.assertEqual(status_line, "status=READY_FOR_HUMAN")
            self.assertIn("AUTH_AGENT_PASSWORDLESS_ROOT", proc.stdout)
            if not Path("/usr/lib/hermes-runtime/hermes-agent").exists():
                self.assertIn("AUTH_NO_HERMES_RUNTIME", proc.stdout)
            if not Path("/usr/local/lib/hermes-eos/scripts/verify-operator-boundary.sh").exists():
                self.assertIn("AUTH_NO_PROTECTED_VERIFIER_SCRIPT", proc.stdout)
            if not Path("/usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin/__init__.py").exists():
                self.assertIn("AUTH_NO_PROTECTED_PLUGIN_SOURCE", proc.stdout)
            if "hermes_op_present=no" in proc.stdout:
                self.assertIn("AUTH_NO_HERMES_OP", proc.stdout)
            else:
                self.assertIn("hermes_op_present=yes", proc.stdout)
                self.assertNotIn("AUTH_NO_HERMES_OP\n", proc.stdout)
        self.assertNotIn(FAKE_SECRET, proc.stdout)
        self.assertIn("invoked_user=", proc.stdout)
        self.assertIn("agent_user=ubuntu", proc.stdout)
        inspect = (ROOT / "scripts/pag2-inspect-ubuntu.sh").read_text(encoding="utf-8")
        self.assertIn("sudo -n -l -U ubuntu", inspect)
        self.assertIn("systemctl --user -M ubuntu@", inspect)
        self.assertIn("id -nG ubuntu", inspect)
        verifier = (ROOT / "scripts/verify-operator-boundary.sh").read_text(encoding="utf-8")
        self.assertIn("pag2-inspect-ubuntu.sh", verifier)
        self.assertIn("pag2_ubuntu_sudo_list", verifier)
        self.assertNotIn('user_unit="$HOME/.config/systemd/user/', verifier)


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

        spec = importlib.util.spec_from_file_location("deploy_tool_h3", ROOT / "scripts" / "hermes-eos-deploy-tool.py")
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        self.assertEqual(mod.acting_principal(euid=0, sudo_user="hermes-op"), "hermes-op")
        self.assertEqual(mod.acting_principal(euid=0, sudo_user="ubuntu"), "ubuntu")
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        priv = Ed25519PrivateKey.generate()
        pub = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        pub_path = tmp / "trust.pub"
        pub_path.write_text(pub.hex() + "\n", encoding="utf-8")
        sig = priv.sign(mod.canonical_deploy_bytes(good)).hex()
        mod.verify_deploy_signature(good, sig, pub_path)
        with self.assertRaises(SystemExit):
            mod.verify_deploy_signature(good, "00" * 64, pub_path)
        nonce_tmp = tmp / "nonces"
        os.environ["HERMES_EOS_NONCE_DIR"] = str(nonce_tmp)
        mod.consume_install_nonce("n1")
        with self.assertRaises(SystemExit):
            mod.consume_install_nonce("n1")
        mod.consume_rollback_nonce("n1")
        with self.assertRaises(SystemExit):
            mod.consume_rollback_nonce("n1")
        with self.assertRaises(SystemExit):
            mod.consume_rollback_nonce("never-installed")

    def test_repo_plugin_does_not_register_spawn_hook(self) -> None:
        root = (ROOT / "__init__.py").read_text(encoding="utf-8")
        self.assertNotIn("transform_kanban_worker_spawn", root)
        wrapper = (ROOT / "deploy" / "pag2" / "eos-actuation-plugin" / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("hermes_plugin", wrapper)

    def test_h3_requires_hook_and_protected_plugin(self) -> None:
        from engineering_os.adaptation.pag2_ops import h3_live_seam_present

        tmp = Path(tempfile.mkdtemp())
        hook = tmp / "kanban_db.py"
        plugin = tmp / "__init__.py"
        hook.write_text("transform_kanban_worker_spawn = True\n", encoding="utf-8")
        self.assertFalse(h3_live_seam_present(hook, tmp / "missing.py"))
        plugin.write_text("from engineering_os.adaptation.hermes_plugin import register as register_ipc\n", encoding="utf-8")
        self.assertTrue(h3_live_seam_present(hook, plugin))

    def test_h3_manifest_plugin_hashes(self) -> None:
        import hashlib
        import json

        manifest = json.loads((ROOT / "deploy" / "pag2" / "h3-live-patch.manifest.example.json").read_text(encoding="utf-8"))
        plugin = ROOT / "deploy" / "pag2" / "eos-actuation-plugin"
        for name, digest in manifest["plugin_files"].items():
            actual = hashlib.sha256((plugin / name).read_bytes()).hexdigest()
            self.assertEqual(actual, digest, name)
        ipc = hashlib.sha256((ROOT / "engineering_os" / "adaptation" / "hermes_plugin.py").read_bytes()).hexdigest()
        self.assertEqual(ipc, manifest["ipc_client_sha256"])
        transport = hashlib.sha256((ROOT / "engineering_os" / "adaptation" / "ipc_client.py").read_bytes()).hexdigest()
        self.assertEqual(transport, manifest["ipc_transport_sha256"])
        spec = importlib.util.spec_from_file_location(
            "pag2_h3_default_plugin",
            ROOT / "scripts" / "hermes-eos-deploy-tool.py",
        )
        tool = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(tool)
        chosen = tool.default_plugin_dir()
        protected_plugin = Path("/usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin")
        if protected_plugin.is_dir():
            self.assertEqual(chosen, protected_plugin)
        else:
            self.assertEqual(chosen, plugin)
        present = (ROOT / "scripts" / "h3-present-deploy.sh").read_text(encoding="utf-8")
        self.assertIn("/usr/local/lib/hermes-eos/hermes-eos-deploy-tool.py", present)
        self.assertIn("eos-actuation-plugin", present)
        self.assertIn("try-reload-or-restart", (ROOT / "scripts" / "hermes-eos-deploy-tool.py").read_text(encoding="utf-8"))
        verifier = (ROOT / "scripts" / "verify-operator-boundary.sh").read_text(encoding="utf-8")
        self.assertIn("AUTH_NO_PROTECTED_PLUGIN_SOURCE", verifier)

    def test_agent_writable_approval_file_is_not_a_grant(self) -> None:
        from engineering_os.adaptation.pag2_ops import approval_a_granted

        fake = Path(tempfile.mkdtemp()) / "approval-a.granted"
        fake.write_text("yes\n", encoding="utf-8")
        self.assertFalse(approval_a_granted(fake))
        self.assertFalse(approval_a_granted(Path("/no/such/approval-a.granted")))
        denied = Path(tempfile.mkdtemp())
        try:
            os.chmod(denied, 0o000)
            self.assertFalse(approval_a_granted(denied / "approval-a.granted"))
        finally:
            os.chmod(denied, 0o700)

    def test_unsigned_approval_a_is_not_a_grant(self) -> None:
        from engineering_os.adaptation.pag2_ops import approval_a_granted

        fake = Path(tempfile.mkdtemp()) / "approval-a.granted"
        fake.write_text(
            '{"stage":"A","maximum_exposure":1,'
            '"runtime_identity":{"runtime_release_hash":'
            '"c0106e50e7ecedb3ce34e785d949725dc4e0e457",'
            '"actuator_contract_version":"pag2-actuator-v1"}}\n',
            encoding="utf-8",
        )
        fake.chmod(0o444)
        self.assertFalse(approval_a_granted(fake))

    def test_approval_a_present_matches_canonical_bytes_and_does_not_consume(self) -> None:
        from engineering_os.adaptation.approval_ed25519 import (
            canonical_bytes,
            sign_detached,
            verify_detached_signature,
            verify_production_authorization,
        )
        from engineering_os.adaptation.pag2_ops import flatten_approval_a_fields, present_approval_a_request

        blocked = present_approval_a_request()
        self.assertFalse(blocked.get("ok"))
        self.assertEqual(blocked.get("status"), "BLOCKED_H3")
        env = Path(tempfile.mkdtemp()) / "actuator.env"
        env.write_text(
            "HERMES_EOS_RUNTIME_RELEASE_HASH=c0106e50e7ecedb3ce34e785d949725dc4e0e457\n"
            "HERMES_EOS_LIVE_PATCH_HASH=51d4dd4d003143cdfea07d53668e8079f6d5163dc0a2777b3d5c3efd0001ecd4\n"
            "HERMES_EOS_TRUST_FINGERPRINT=abcdabcdabcdabcd\n",
            encoding="utf-8",
        )
        previous = os.environ.get("HERMES_EOS_ACTUATOR_ENV")
        os.environ["HERMES_EOS_ACTUATOR_ENV"] = str(env)
        try:
            presented = present_approval_a_request()
            grant = presented["grant"]
            self.assertTrue(presented.get("ok"))
            self.assertEqual(grant["stage"], "A")
            self.assertEqual(int(grant["maximum_exposure"]), 1)
            self.assertEqual(grant["approval_stage"], "A")
            self.assertEqual(
                grant["runtime_identity"]["runtime_release_hash"],
                "c0106e50e7ecedb3ce34e785d949725dc4e0e457",
            )
            self.assertEqual(
                grant["runtime_identity"]["live_patch_hash"],
                "51d4dd4d003143cdfea07d53668e8079f6d5163dc0a2777b3d5c3efd0001ecd4",
            )
            self.assertEqual(presented["canonical_hex"], canonical_bytes(grant).hex())
            keys = generate_ephemeral_keypair()
            signature = sign_detached(grant, keys["private"])
            first = verify_detached_signature(grant, signature, keys["public"], consume=False)
            second = verify_detached_signature(grant, signature, keys["public"], consume=False)
            self.assertTrue(first.get("ok"), first)
            self.assertTrue(second.get("ok"), second)
            with patch(
                "engineering_os.adaptation.approval_ed25519.production_trust_anchor_status",
                return_value={
                    "status": "PROTECTED_TRUST_PRESENT",
                    "granted": False,
                    "agent_replaceable": False,
                },
            ), patch(
                "engineering_os.adaptation.approval_ed25519.load_protected_public_key",
                return_value=keys["public"],
            ):
                once = verify_production_authorization(
                    flatten_approval_a_fields(grant), signature, consume=False
                )
                twice = verify_production_authorization(
                    flatten_approval_a_fields(grant), signature, consume=False
                )
            self.assertTrue(once.get("granted"), once)
            self.assertTrue(twice.get("granted"), twice)
            empty = Path(tempfile.mkdtemp()) / "approval-a.granted"
            empty.write_text(
                '{"stage":"A","maximum_exposure":1,"signature":"' + "00" * 64 + '",'
                '"runtime_identity":{"runtime_release_hash":'
                '"c0106e50e7ecedb3ce34e785d949725dc4e0e457",'
                '"live_patch_hash":"","actuator_contract_version":"pag2-actuator-v1",'
                '"trust_fingerprint":"abcdabcdabcdabcd"}}\n',
                encoding="utf-8",
            )
            empty.chmod(0o444)
            from engineering_os.adaptation.pag2_ops import approval_a_granted

            self.assertFalse(approval_a_granted(empty))
        finally:
            if previous is None:
                os.environ.pop("HERMES_EOS_ACTUATOR_ENV", None)
            else:
                os.environ["HERMES_EOS_ACTUATOR_ENV"] = previous


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

    def test_shadow_scope_does_not_consume_exposure(self) -> None:
        reset_memory()
        shadow = handle_request(
            {
                "task_id": "s1",
                "task_context": {
                    "board": "retropick-markets-release",
                    "task_id": "s1",
                    "scope": "PRODUCTION_SHADOW",
                    "environment": "production",
                },
                "baseline": {"model": "gpt-5.6-sol"},
            },
            peer_uid=2000,
            runtime_uid=2000,
            state=_canary_state(),
        )
        self.assertEqual(shadow["reason"], "SHADOW_NO_ACTUATE")
        self.assertFalse(shadow.get("actuate"))
        self.assertIsNone(shadow.get("reservation"))
        self.assertEqual(shadow.get("would_resolution"), "CANDIDATE")
        canary = handle_request(
            {
                "task_id": "c1",
                "task_context": {
                    "board": "retropick-markets-release",
                    "task_id": "c1",
                    "scope": "PRODUCTION_CANARY",
                    "environment": "production",
                },
                "baseline": {"model": "gpt-5.6-sol"},
            },
            peer_uid=2000,
            runtime_uid=2000,
            state=_canary_state(),
        )
        self.assertTrue(canary.get("reservation", {}).get("reserved"))

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

    def test_deploy_tool_syncs_live_patch_identity(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "deploy_tool", ROOT / "scripts" / "hermes-eos-deploy-tool.py"
        )
        tool = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(tool)
        tmp = Path(tempfile.mkdtemp())
        env = tmp / "actuator.env"
        state = tmp / "state.json"
        home = tmp / "home"
        (home / "profiles" / "rp-friend").mkdir(parents=True)
        env.write_text("HERMES_EOS_LIVE_PATCH_HASH=\n", encoding="utf-8")
        state.write_text('{"auto_promote":false,"runtime_identity":{"live_patch_hash":""}}\n', encoding="utf-8")
        (home / "config.yaml").write_text("plugins:\n  enabled:\n    - hermes_otel\n", encoding="utf-8")
        (home / "profiles" / "rp-friend" / "config.yaml").write_text(
            "plugins:\n  enabled:\n    - hermes_otel\n", encoding="utf-8"
        )
        os.environ["HERMES_EOS_ACTUATOR_ENV"] = str(env)
        os.environ["HERMES_EOS_ACTUATOR_STATE"] = str(state)
        os.environ["HERMES_EOS_RUNTIME_HOME"] = str(home)
        os.environ["HERMES_EOS_SKIP_UNIT_RESTART"] = "1"
        manifest = {
            "artifact_sha256": "51d4dd4d003143cdfea07d53668e8079f6d5163dc0a2777b3d5c3efd0001ecd4",
            "affected_units": ["hermes-gateway.service", "hermes-gateway-rp-friend.service"],
        }
        tool.sync_runtime_identity(manifest, installed=True)
        self.assertIn("51d4dd4d003143cdfea07d53668e8079f6d5163dc0a2777b3d5c3efd0001ecd4", env.read_text(encoding="utf-8"))
        self.assertIn("51d4dd4d", state.read_text(encoding="utf-8"))
        self.assertIn("eos-actuation", (home / "config.yaml").read_text(encoding="utf-8"))
        self.assertEqual(
            tool.units_to_reload(manifest),
            [
                "hermes-eos-actuator.service",
                "hermes-gateway.service",
                "hermes-gateway-rp-friend.service",
            ],
        )
        self.assertEqual(tool.units_to_reload({"affected_units": ["../evil.service", "nope"]}), ["hermes-eos-actuator.service"])
        tool.sync_runtime_identity(manifest, installed=False)
        self.assertIn("HERMES_EOS_LIVE_PATCH_HASH=\n", env.read_text(encoding="utf-8"))
        self.assertNotIn("eos-actuation", (home / "config.yaml").read_text(encoding="utf-8"))
        self.assertNotIn("eos-actuation", (home / "profiles" / "rp-friend" / "config.yaml").read_text(encoding="utf-8"))
        src = (ROOT / "scripts" / "hermes-eos-deploy-tool.py").read_text(encoding="utf-8")
        self.assertIn("try-reload-or-restart", src)
        self.assertNotIn('["systemctl", "try-restart", "hermes-eos-actuator.service"]', src)
        os.environ.pop("HERMES_EOS_ACTUATOR_ENV", None)
        os.environ.pop("HERMES_EOS_ACTUATOR_STATE", None)
        os.environ.pop("HERMES_EOS_RUNTIME_HOME", None)
        os.environ.pop("HERMES_EOS_SKIP_UNIT_RESTART", None)

    def test_example_nonce_and_canonical_bytes(self) -> None:
        import json
        import tempfile
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "deploy_tool", ROOT / "scripts" / "hermes-eos-deploy-tool.py"
        )
        tool = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(tool)
        self.assertTrue(tool.nonce_is_example("pag2-h3-example-nonce-not-authorizing"))
        self.assertFalse(tool.nonce_is_example("pag2-h3-live-1"))
        with self.assertRaises(SystemExit) as ctx:
            tool.require_live_nonce("pag2-h3-example-nonce-not-authorizing")
        self.assertIn("example nonce", str(ctx.exception))
        tool.require_live_nonce("pag2-h3-live-1")
        manifest = json.loads((ROOT / "deploy" / "pag2" / "h3-live-patch.manifest.example.json").read_text(encoding="utf-8"))
        blob = tool.canonical_deploy_bytes(manifest)
        self.assertTrue(blob.startswith(b"{"))
        proc = subprocess.run(
            [
                "python3",
                str(ROOT / "scripts" / "hermes-eos-deploy-tool.py"),
                "canonical",
                "--manifest",
                str(ROOT / "deploy" / "pag2" / "h3-live-patch.manifest.example.json"),
                "--artifact",
                str(ROOT / "patches" / "hermes" / "live" / "0001-worker-spawn-transform-live.patch"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(blob.hex(), proc.stdout)
        bad_ipc = dict(manifest)
        bad_ipc["ipc_client_sha256"] = "00" * 32
        bad_path = Path(tempfile.mkdtemp()) / "bad-ipc.json"
        bad_path.write_text(json.dumps(bad_ipc), encoding="utf-8")
        mismatch = subprocess.run(
            [
                "python3",
                str(ROOT / "scripts" / "hermes-eos-deploy-tool.py"),
                "verify",
                "--manifest",
                str(bad_path),
                "--artifact",
                str(ROOT / "patches" / "hermes" / "live" / "0001-worker-spawn-transform-live.patch"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertIn("ipc client", (mismatch.stderr + mismatch.stdout).lower())

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


class Pag2OpsTests(unittest.TestCase):
    def test_shadow_and_canary_fail_closed_without_h1(self) -> None:
        from engineering_os.adaptation.pag2_ops import production_canary, production_rollback, production_shadow

        shadow = production_shadow(h1_status="READY_FOR_HUMAN", pag2_label="QUALIFIED_CANDIDATE")
        self.assertEqual(shadow["status"], "BLOCKED_SECURITY_BOUNDARY")
        self.assertFalse(shadow["ok"])
        canary = production_canary(
            h1_status="READY_FOR_HUMAN",
            pag2_label="QUALIFIED_CANDIDATE",
            h3_deployed=True,
            approval_ok=True,
            state=_canary_state(),
            peer_uid=2000,
            runtime_uid=2000,
        )
        self.assertEqual(canary["status"], "BLOCKED_SECURITY_BOUNDARY")
        rollback = production_rollback({"bindings": [{"state": "ACTIVE"}]}, h1_status="READY_FOR_HUMAN")
        self.assertEqual(rollback["status"], "BLOCKED_SECURITY_BOUNDARY")

    def test_bind_canary_fail_closed_then_persists_when_gated(self) -> None:
        import json

        from engineering_os.adaptation.pag2_ops import bind_production_canary, canary_binding
        from engineering_os.experiments.definitions import load_id

        tmp = Path(tempfile.mkdtemp()) / "state.json"
        blocked = bind_production_canary(
            h1_status="READY_FOR_HUMAN",
            pag2_label="QUALIFIED_CANDIDATE",
            h3_deployed=True,
            approval_ok=True,
            persist_path=tmp,
        )
        self.assertEqual(blocked["status"], "BLOCKED_SECURITY_BOUNDARY")
        self.assertFalse(tmp.exists())
        evidence = bind_production_canary(
            h1_status="PASS",
            pag2_label="VALID_NO_PROMOTION",
            h3_deployed=True,
            approval_ok=True,
            persist_path=tmp,
        )
        self.assertEqual(evidence["status"], "BLOCKED_EVIDENCE")
        protocol = load_id("real-model-sol-vs-terra-v2")
        ok = bind_production_canary(
            h1_status="PASS",
            pag2_label="QUALIFIED_CANDIDATE",
            h3_deployed=True,
            approval_ok=True,
            persist_path=tmp,
            protocol=protocol,
        )
        self.assertEqual(ok["status"], "BOUND")
        self.assertFalse(ok["auto_promote"])
        self.assertEqual(ok["maximum_exposure"], 1)
        written = json.loads(tmp.read_text(encoding="utf-8"))
        self.assertEqual(written["bindings"][0]["mode"], "CANARY")
        self.assertEqual(written["maximum_exposure"], 1)
        self.assertFalse(written["auto_promote"])
        self.assertEqual(canary_binding(protocol)["spec"]["candidate"]["overrides"]["model"], "gpt-5.6-terra")

    def test_pag2_ops_reads_repo_artifacts_not_tcb_parent(self) -> None:
        import json

        from engineering_os.adaptation.pag2_ops import (
            bind_production_canary,
            experiment_runtime_dir,
            load_pag2_label,
            verify_operator_script,
        )

        fake = Path(tempfile.mkdtemp())
        analysis = fake / "real-model-sol-vs-terra-v2" / "analysis.json"
        analysis.parent.mkdir(parents=True)
        analysis.write_text(
            json.dumps({"pag2_label": "QUALIFIED_CANDIDATE", "protocol_hash": "deadbeef"}) + "\n",
            encoding="utf-8",
        )
        script = fake / "verify.sh"
        script.write_text("#!/bin/bash\necho status=PASS\n", encoding="utf-8")
        previous_runtime = os.environ.get("EOS_EXPERIMENT_RUNTIME")
        os.environ["EOS_EXPERIMENT_RUNTIME"] = str(fake)
        os.environ["HERMES_EOS_VERIFY_OPERATOR"] = str(script)
        try:
            self.assertEqual(experiment_runtime_dir(), fake)
            self.assertEqual(verify_operator_script(), script)
            self.assertEqual(load_pag2_label(), "QUALIFIED_CANDIDATE")
            protocol = load_id("real-model-sol-vs-terra-v2")
            mismatch = bind_production_canary(
                h1_status="PASS",
                pag2_label="QUALIFIED_CANDIDATE",
                h3_deployed=True,
                approval_ok=True,
                persist_path=fake / "state.json",
                protocol=protocol,
            )
            self.assertEqual(mismatch["status"], "BLOCKED_EVIDENCE")
        finally:
            if previous_runtime is None:
                os.environ.pop("EOS_EXPERIMENT_RUNTIME", None)
            else:
                os.environ["EOS_EXPERIMENT_RUNTIME"] = previous_runtime
            os.environ.pop("HERMES_EOS_VERIFY_OPERATOR", None)

    def test_shadow_skips_when_no_candidate(self) -> None:
        from engineering_os.adaptation.pag2_ops import production_shadow

        payload = production_shadow(h1_status="PASS", pag2_label="VALID_NO_PROMOTION")
        self.assertEqual(payload["status"], "SKIPPED_NO_CANDIDATE")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["exposure_consumed"], 0)

    def test_shadow_pass_does_not_consume_exposure(self) -> None:
        from engineering_os.adaptation.pag2_ops import production_shadow

        reset_memory()
        shadow = _canary_state()
        shadow["bindings"][0]["mode"] = "SHADOW"
        payload = production_shadow(
            h1_status="PASS",
            pag2_label="QUALIFIED_CANDIDATE",
            tasks=[{"task_id": "t-shadow", "board": "retropick-markets-release"}],
            state=shadow,
            peer_uid=2000,
            runtime_uid=2000,
        )
        self.assertEqual(payload["status"], "PASS")
        self.assertFalse(payload["actuate"])
        self.assertEqual(payload["exposure_consumed"], 0)
        self.assertIsNone((payload.get("ipc") or {}).get("reservation"))

    def test_canary_requires_h3_then_reserves_once_with_workload_fallback(self) -> None:
        from engineering_os.adaptation.pag2_ops import production_canary, select_canary_task

        blocked = production_canary(
            h1_status="PASS",
            pag2_label="QUALIFIED_CANDIDATE",
            h3_deployed=False,
            approval_ok=True,
            state=_canary_state(),
            peer_uid=2000,
            runtime_uid=2000,
        )
        self.assertEqual(blocked["status"], "BLOCKED_H3")
        reset_memory()
        payload = production_canary(
            h1_status="PASS",
            pag2_label="QUALIFIED_CANDIDATE",
            h3_deployed=True,
            approval_ok=True,
            state=_canary_state(),
            peer_uid=2000,
            runtime_uid=2000,
            natural_task_id=None,
        )
        self.assertEqual(payload["status"], "PASS")
        self.assertTrue(payload["canary_workload"])
        self.assertEqual(payload["task_id"], "pag2-canary-workload-1")
        self.assertEqual(payload["exposure_consumed"], 1)
        self.assertFalse(payload["auto_promote"])
        self.assertEqual(select_canary_task("t_natural")["canary_workload"], False)

    def test_ubuntu_peer_cannot_canary(self) -> None:
        from engineering_os.adaptation.pag2_ops import production_canary

        reset_memory()
        payload = production_canary(
            h1_status="PASS",
            pag2_label="QUALIFIED_CANDIDATE",
            h3_deployed=True,
            approval_ok=True,
            state=_canary_state(),
            peer_uid=1000,
            runtime_uid=2000,
        )
        self.assertEqual(payload["status"], "BLOCKED_PEER")
        self.assertEqual(payload["exposure_consumed"], 0)

    def test_ipc_canary_uses_so_peercred_not_inline_state(self) -> None:
        from engineering_os.adaptation.actuator import serve_forever
        from engineering_os.adaptation.pag2_ops import production_canary, production_shadow

        tmp = Path(tempfile.mkdtemp()) / "pag2-ipc.sock"
        stop = threading.Event()
        thread = threading.Thread(
            target=serve_forever,
            kwargs={"socket_path": str(tmp), "runtime_uid": -1, "state": _canary_state(), "stop": stop},
            daemon=True,
        )
        thread.start()
        for _ in range(50):
            if tmp.exists():
                break
            time.sleep(0.02)
        self.assertTrue(tmp.exists())
        from engineering_os.adaptation.ipc_client import request_spawn_resolution

        for _ in range(50):
            probe = request_spawn_resolution(
                {"task_id": "warm"},
                {"model": "gpt-5.6-sol"},
                socket_path=str(tmp),
                timeout_s=0.5,
            )
            if probe.get("reason") != "ConnectionRefusedError":
                break
            time.sleep(0.02)
        canary = production_canary(
            h1_status="PASS",
            pag2_label="QUALIFIED_CANDIDATE",
            h3_deployed=True,
            approval_ok=True,
            state={},
            peer_uid=os.getuid(),
            runtime_uid=-1,
            transport="ipc",
            socket_path=str(tmp),
        )
        shadow = production_shadow(
            h1_status="PASS",
            pag2_label="QUALIFIED_CANDIDATE",
            transport="ipc",
            socket_path=str(tmp),
        )
        stop.set()
        thread.join(timeout=2)
        self.assertEqual(canary["status"], "BLOCKED_PEER")
        self.assertEqual(canary["exposure_consumed"], 0)
        self.assertEqual(shadow["status"], "BLOCKED_PEER")
        self.assertEqual(shadow["exposure_consumed"], 0)

    def test_rollback_does_not_interrupt_running(self) -> None:
        import json

        from engineering_os.adaptation.pag2_ops import production_rollback

        payload = production_rollback({"bindings": [{"state": "ACTIVE", "mode": "CANARY", "binding_version": 3}]})
        self.assertEqual(payload["status"], "PASS")
        self.assertFalse(payload["interrupt_running"])
        self.assertFalse(payload["auto_promote"])
        tmp = Path(tempfile.mkdtemp()) / "state.json"
        persisted = production_rollback(
            {"bindings": [{"state": "ACTIVE", "mode": "CANARY", "binding_version": 3}]},
            persist_path=tmp,
        )
        self.assertTrue(persisted["persisted"])
        self.assertEqual(json.loads(tmp.read_text(encoding="utf-8"))["bindings"][0]["mode"], "BASELINE")

        existing = Path(tempfile.mkdtemp()) / "live-state.json"
        existing.write_text(
            json.dumps(
                {
                    "maximum_exposure": 1,
                    "auto_promote": False,
                    "runtime_identity": {"runtime_release_hash": "c0106e50"},
                    "bindings": [{"state": "ACTIVE", "mode": "CANARY", "policy_id": "keep-me"}],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        from_disk = production_rollback({}, persist_path=existing)
        self.assertTrue(from_disk["persisted"])
        restored = json.loads(existing.read_text(encoding="utf-8"))
        self.assertEqual(restored["bindings"][0]["mode"], "BASELINE")
        self.assertEqual(restored["runtime_identity"]["runtime_release_hash"], "c0106e50")
        self.assertFalse(restored["auto_promote"])
        self.assertEqual(restored["maximum_exposure"], 1)

    def test_pag2_status_is_read_only_and_honest(self) -> None:
        proc = subprocess.run(
            [str(ROOT / "scripts/pag2-status.sh")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("auto_promote=false", proc.stdout)
        self.assertIn("live_spawn_hook=ABSENT", proc.stdout)
        if "h1=PASS" in proc.stdout.splitlines():
            self.assertIn("next=HUMAN ACTION REQUIRED — H2", proc.stdout)
        else:
            self.assertIn("h1=READY_FOR_HUMAN", proc.stdout)
            self.assertIn("next=HUMAN ACTION REQUIRED — H1", proc.stdout)
        self.assertIn("protected_spawn_hook=ABSENT", proc.stdout)
        self.assertNotIn(FAKE_SECRET, proc.stdout)


if __name__ == "__main__":
    unittest.main()
