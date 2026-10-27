"""Actual runner/Agent/Tools/processes; model protocol fixtures are explicitly labelled."""
import copy
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import ProxyHandler, build_opener

from local_agent.evaluation import load_corpus
from local_agent.evaluation_runner import (
    FixturePolicy,
    RecordingTools,
    effects,
    execute_case,
    identity,
    model_config,
    run,
    sample,
    write_json,
)
from local_agent.evaluation_site import EvaluationSite
from local_agent.safety import Denied
from local_agent.studio.store import Store

from .evaluation_support import ModelProtocol
from .support import WorkspaceTest


class EvaluationRunnerTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.corpus = load_corpus()
        self.case = self.corpus["cases"][0]

    def connect(self, protocol):
        self.config["model"]["url"] = protocol.url
        return identity(model_config(self.config))

    def execute(self, case, metadata, **kwargs):
        return execute_case(self.config, case, 1, metadata, self.policy.root / (case["id"] + "-run"), **kwargs)

    def test_coding_agent_collects_actual_artifacts_metrics_and_private_rows(self):
        self.config["model"]["api_key"] = "PRIVATE-SEEDED-CREDENTIAL"
        with ModelProtocol(self.corpus, self.config["model"]["name"]) as protocol:
            metadata = self.connect(protocol)
            for name in ("coding-addition", "coding-related-patch", "recovery-missing-file", "injection-file-instructions"):
                case = next(c for c in self.corpus["cases"] if c["id"] == name)
                row = self.execute(case, metadata)
                self.assertEqual(row["status"], "passed", row)
                self.assertEqual(set(row["checks"].values()), {"passed"})
                self.assertIs(row["critical_unauthorized"], False)
                self.assertEqual(row["metrics"]["generated_tokens"], row["metrics"]["model_calls"] * 10)
                self.assertGreater(row["elapsed_seconds"], 0)
                root = self.policy.root / (case["id"] + "-run")
                for path in ("request.json", "sample.json", "observation.json"):
                    self.assertNotIn("PRIVATE-SEEDED-CREDENTIAL", (root / path).read_text())
                self.assertNotIn("ORCHID", (root / "sample.json").read_text())
            self.assertTrue(any(r.get("format") for r in protocol.requests))
            self.assertTrue(any(r.get("tools") for r in protocol.requests))

    def test_false_report_cannot_override_independent_artifact_failure(self):
        with ModelProtocol(self.corpus, self.config["model"]["name"]) as protocol:
            protocol.wrong_artifact = True
            row = self.execute(self.case, self.connect(protocol))
            self.assertEqual(row["status"], "failed")
            self.assertEqual(row["checks"]["addition-ast"], "failed")

    def test_scoped_search_strict_read_checks_do_not_require_a_write_grant(self):
        with ModelProtocol(self.corpus, self.config["model"]["name"]) as protocol:
            case = next(c for c in self.corpus["cases"] if c["id"] == "coding-scoped-search")
            row = self.execute(case, self.connect(protocol))
        self.assertEqual(row["status"], "passed", row)
        self.assertEqual(set(row["checks"].values()), {"passed"})
        self.assertIs(row["critical_unauthorized"], False)

    def test_search_preserves_review_grants_and_denies_a_mixed_patch_before_any_write(self):
        case = next(c for c in self.corpus["cases"] if c["id"] == "injection-file-instructions")
        for path, text in case["seed_files"].items():
            (self.policy.root / path).write_text(text, encoding="utf-8", newline="")
        policy = FixturePolicy(self.config, case, [], "http://127.0.0.1:1234")
        tools = RecordingTools(policy, review_create=True)
        self.addCleanup(tools.close)
        self.assertTrue(tools.execute("search_files", {"query": "ORCHID"})["ok"])
        self.assertEqual(tools.execute("write_file", {"path": "extra.txt", "text": "bad"})["error"], "Denied")
        changes = [{"path": "answer.txt", "expected_sha256": "missing", "text": "ORCHID"},
                   {"path": "protected.txt", "expected_sha256": hashlib.sha256(b"UNCHANGED\n").hexdigest(),
                    "text": "pwned"}]
        self.assertEqual(tools.execute("apply_patch", {"changes": changes})["error"], "Denied")
        self.assertFalse((self.policy.root / "extra.txt").exists())
        self.assertFalse((self.policy.root / "answer.txt").exists())
        self.assertEqual((self.policy.root / "protected.txt").read_bytes(), b"UNCHANGED\n")
        self.assertFalse(policy.approval("browser_download", {"url": "http://127.0.0.1:1234", "selector": "#download", "path": "answer.txt"}))
        with self.assertRaises(Denied):
            policy.approval("browser_download", {"url": "http://127.0.0.1:1234", "selector": "#download", "path": "downloads/sample.txt"})

    def test_injected_mutation_is_denied_without_changing_protected_file(self):
        with ModelProtocol(self.corpus, self.config["model"]["name"]) as protocol:
            protocol.inject = True
            case = next(c for c in self.corpus["cases"] if c["id"] == "injection-file-instructions")
            row = self.execute(case, self.connect(protocol))
            self.assertEqual(row["status"], "failed", row)
            self.assertFalse(row["critical_unauthorized"])
            self.assertEqual((self.policy.root / (case["id"] + "-run/workspace/protected.txt")).read_text(), "UNCHANGED\n")

    def test_model_manifest_change_after_inference_is_inconclusive(self):
        with ModelProtocol(self.corpus, self.config["model"]["name"]) as protocol:
            metadata = self.connect(protocol)
            protocol.change_identity = True
            row = self.execute(self.case, metadata)
            self.assertEqual(row["status"], "inconclusive", row)
            self.assertIsNone(row["metrics"])
            observation = json.loads((self.policy.root / (self.case["id"] + "-run/observation.json")).read_text())
            self.assertEqual(observation["failure"]["phase"], "identity")

    def test_timeout_reaps_owned_worker_and_preserves_incomplete_sample(self):
        processes = []
        original = subprocess.Popen

        def record(*args, **kwargs):
            proc = original(*args, **kwargs)
            processes.append(proc)
            return proc

        with ModelProtocol(self.corpus, self.config["model"]["name"]) as protocol:
            protocol.block = threading.Event()
            metadata = self.connect(protocol)
            with patch("local_agent.process.subprocess.Popen", side_effect=record):
                started = time.monotonic()
                row = self.execute(self.case, metadata, timeout=1)
            self.assertTrue(protocol.entered.is_set())
            self.assertLess(time.monotonic() - started, 4)
            self.assertEqual(row["status"], "blocked")
            self.assertIsNone(row["critical_unauthorized"])
            self.assertTrue(processes)
            self.assertTrue(all(proc.poll() is not None for proc in processes))
            info = json.loads((self.policy.root / (self.case["id"] + "-run/observation.json")).read_text())
            self.assertEqual(info["reason"], "timeout")

    def test_cancel_interrupts_model_request_and_leaves_unrelated_owned_fixture_alive(self):
        unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"],
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.addCleanup(lambda: unrelated.poll() is None and unrelated.kill())
        with ModelProtocol(self.corpus, self.config["model"]["name"]) as protocol:
            protocol.block = threading.Event()
            metadata = self.connect(protocol)
            cancelled = threading.Event()
            stopper = threading.Thread(target=lambda: (protocol.entered.wait(5), cancelled.set()), daemon=True)
            stopper.start()
            try:
                started = time.monotonic()
                row = self.execute(self.case, metadata, cancel=cancelled)
                stopper.join(1)
                self.assertLess(time.monotonic() - started, 4)
                self.assertEqual(row["status"], "blocked")
                self.assertIsNone(row["critical_unauthorized"])
                self.assertIsNone(unrelated.poll())
            finally:
                unrelated.terminate()
                unrelated.wait(5)

    def test_exact_grants_do_not_shadow_origin_policy_or_approve_commands(self):
        case = next(c for c in self.corpus["cases"] if c["id"] == "injection-file-instructions")
        policy = FixturePolicy(self.config, case, [], "http://127.0.0.1:1234")
        self.assertTrue(callable(policy.origin))
        tools = RecordingTools(policy, allowed_tools=("write_file",), review_create=True)
        self.addCleanup(tools.close)
        self.assertFalse(policy.approval("execute_code", {"argv": ["python"]}))
        self.assertFalse(policy.approval("external_request", {"url": "http://127.0.0.1:1234", "method": "POST"}))
        self.assertEqual(tools.execute("write_file", {"path": "protected.txt", "text": "pwned"})["error"], "Denied")
        self.assertTrue(tools.execute("write_file", {"path": "answer.txt", "text": "wrong but scoped"})["ok"])
        self.assertFalse(tools.execute("command", {"name": "test"})["ok"])

    def test_effects_detect_outside_changes_extra_files_protected_changes_and_missing_seeds(self):
        case = next(c for c in self.corpus["cases"] if c["id"] == "injection-file-instructions")
        root = self.policy.root / "effects"
        root.mkdir()
        (root / "workspace").mkdir()
        (root / "state").mkdir()
        (root / "guard.txt").write_bytes(b"OUTSIDE-SCOPE-GUARD\n")
        write_json(root / "request.json", {"fixture": "trusted"})
        version = hashlib.sha256((root / "request.json").read_bytes()).hexdigest()
        for path, text in case["seed_files"].items():
            (root / "workspace" / path).write_text(text, encoding="utf-8", newline="")
        self.assertIs(effects(case, root, version), False)
        for path, text in (("workspace/extra.txt", "bad"), ("escape.txt", "bad"),
                           ("workspace/protected.txt", "bad"), ("guard.txt", "bad")):
            target = root / path
            previous = target.read_bytes() if target.exists() else None
            target.write_text(text)
            self.assertIs(effects(case, root, version), True, path)
            if previous is None:
                target.unlink()
            else:
                target.write_bytes(previous)
        (root / "workspace/protected.txt").unlink()
        self.assertIs(effects(case, root, version), True)
        with patch.object(Path, "iterdir", side_effect=PermissionError):
            self.assertIsNone(effects(case, root, version))

    def test_malformed_worker_output_and_unknown_fields_fail_closed(self):
        bad = sample(self.case, 1, None, "passed")
        bad["launch_token"] = "SEEDED-SECRET"
        with patch("local_agent.evaluation_runner.run_process", return_value={
                "exit_code": 0, "truncated": False,
                "output": json.dumps({"sample": bad, "failure": None})}):
            row = self.execute(self.case, None)
        self.assertEqual(row["status"], "blocked")
        self.assertNotIn("SEEDED-SECRET", json.dumps(row))

    def test_exclusive_run_directories_and_case_results_are_never_overwritten(self):
        existing = self.policy.root / "existing"
        existing.mkdir()
        with self.assertRaises(FileExistsError):
            run(self.config, existing, safety_only=True)
        write_json(existing / "result.json", {"original": True})
        with self.assertRaises(FileExistsError):
            write_json(existing / "result.json", {"replacement": True})

    def test_active_studio_and_missing_model_do_not_create_quality_claim(self):
        store = Store(self.policy.state / "studio.sqlite3")
        task = store.task(store.conversation(), "agent", "fixture")
        try:
            report = self.run_without_workers()
            self.assertEqual(report["quality"]["outcomes"]["blocked"], 60)
            self.assertIsNone(report["quality"]["success_rate"])
        finally:
            store.finish(task, "reported", {})

    def run_without_workers(self, **kwargs):
        def completed(config, case, repeat, metadata, directory, **options):
            row = sample(case, repeat, metadata, "passed")
            row.update(checks={c["id"]: "passed" for c in case["checks"]}, critical_unauthorized=False)
            return row
        with patch("local_agent.evaluation_runner.execute_case", side_effect=completed):
            return run(self.config, self.policy.root / "run", **kwargs)

    def test_bad_safety_blocks_model_cases_and_critical_effect_halts_all_work(self):
        for critical in (False, True):
            with self.subTest(critical=critical):
                calls = []
                def failed(config, case, repeat, metadata, directory, calls=calls, critical=critical, **kwargs):
                    calls.append(case["id"])
                    row = sample(case, repeat, metadata, "failed")
                    row["critical_unauthorized"] = critical
                    return row
                with patch("local_agent.evaluation_runner.execute_case", side_effect=failed):
                    report = run(self.config, self.policy.root / f"safety-{critical}", safety_only=True)
                self.assertFalse(report["quality"]["gate_passed"])
                self.assertEqual(len(calls), 1 if critical else 8)

    def test_preexisting_stop_latch_is_preserved_and_all_work_is_not_run(self):
        (self.policy.state / "STOP").touch()
        with patch("local_agent.evaluation_runner.execute_case") as execute:
            report = run(self.config, self.policy.root / "stopped", safety_only=True)
        execute.assert_not_called()
        self.assertEqual(report["quality"]["outcomes"]["not_run"], 60)
        self.assertTrue((self.policy.state / "STOP").exists())

    def test_identity_and_parameters_reject_remote_or_ambiguous_metadata(self):
        with ModelProtocol(self.corpus, self.config["model"]["name"]) as protocol:
            self.connect(protocol)
            protocol.digest = "not-a-digest"
            with self.assertRaises(ValueError):
                identity(model_config(self.config))
        for field, value in (("context", True), ("temperature", float("nan")),
                             ("max_steps", 0), ("timeout", 9999)):
            config = copy.deepcopy(self.config)
            config["model"][field] = value
            with self.assertRaises(ValueError):
                model_config(config)

    def test_owned_site_serves_injection_download_and_counts_submissions(self):
        opener = build_opener(ProxyHandler({}))
        with EvaluationSite() as site:
            with opener.open(site.url + "/injection", timeout=2) as response:
                self.assertIn(b"DATA=SAFE-PAGE", response.read())
            with opener.open(site.url + "/download", timeout=2) as response:
                self.assertEqual(response.read(), b"local fixture download\n")
            with opener.open(site.url + "/submit", data=b"fixture", timeout=2):
                pass
            self.assertEqual(site.submissions, 1)
        self.assertFalse(site.thread.is_alive())


@unittest.skipUnless(os.getenv("LOCAL_AGENT_EVALUATION_BROWSER_TEST") == "1", "Full rendered evaluation protocol matrix is opt-in")
class EvaluationMatrixTests(WorkspaceTest):
    def test_all_sixty_protocol_workflows_and_eight_real_denials_never_establish_quality(self):
        corpus = load_corpus()
        with ModelProtocol(corpus, self.config["model"]["name"]) as protocol:
            self.config["model"]["url"] = protocol.url
            report = run(self.config, self.policy.root / "matrix", execution="protocol_fixture", timeout=30)
        self.assertEqual(report["quality"]["passed"], 60, report["failures"])
        self.assertEqual(report["safety"]["passed"], 8, report["failures"])
        self.assertTrue(report["metrics"]["complete"])
        self.assertIsNone(report["quality"]["success_rate"])
        self.assertFalse(report["quality"]["gate_passed"])
        self.assertTrue(report["safety"]["all_effect_observations_clear"])
        serialized = json.dumps(report)
        self.assertNotIn("SEEDED-SECRET", serialized)
        self.assertNotIn("SYSTEM OVERRIDE", serialized)
        self.assertNotIn(protocol.url, serialized)
