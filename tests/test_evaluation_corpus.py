"""Corpus/scoring contracts. Simulated rows never establish actual model quality."""
import copy
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from local_agent.evaluation import (
    LIMIT,
    aggregate,
    corpus_digest,
    load_corpus,
    main,
    read_json,
    relative_path,
    validate_corpus,
    verify_case,
)
from local_agent.tools import Tools

from .support import WorkspaceTest


def rows_for(corpus, execution="protocol_fixture"):
    """Explicit unit-test observations, not a real execution adapter."""
    identity = {"identifier_sha256": "1" * 64, "weights_sha256": "2" * 64,
                "settings_sha256": "3" * 64}
    return {"schema_version": 1, "corpus_sha256": corpus_digest(corpus),
            "execution": execution, "model": identity,
            "samples": [{"case_id": case["id"], "repeat": repeat, "status": "passed",
                         "checks": {check["id"]: "passed" for check in case["checks"]},
                         "critical_unauthorized": False, "elapsed_seconds": 1,
                         "model": identity if case["track"] == "model" else None,
                         "metrics": {"generated_tokens": 10, "generation_ns": 500_000_000,
                                     "model_calls": 2} if case["track"] == "model" else None}
                        for case in corpus["cases"]
                        for repeat in range(1, (3 if case["track"] == "model" else 1) + 1)]}


def positive_observations(case, policy):
    """Set up expected observations for oracle unit tests, without running an agent."""
    for path, text in case["seed_files"].items():
        target = policy.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="")
    observations = []
    browser = {"origin": "http://127.0.0.1:8123", "tabs": {}, "submissions": 0}
    for check in case["checks"]:
        kind = check["kind"]
        if kind in {"file_text", "file_json", "python_ast"}:
            target = policy.root / check["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(check["expected"]) if kind == "file_json" else check["expected"]
            target.write_text(text, encoding="utf-8", newline="")
        elif kind in {"tool_success", "tool_error"}:
            observations.append({"tool": check["tool"], "ok": kind == "tool_success",
                                 "error": check.get("expected")})
        elif kind == "approval_denied":
            observations.append({"approval": check["action"], "approved": False})
        elif kind == "browser_tabs":
            for tab in check["expected"]:
                browser["tabs"].setdefault(tab, {})
        elif kind in {"browser_path", "browser_value"}:
            tab = browser["tabs"].setdefault(check["tab"], {})
            if kind == "browser_path":
                tab["url"] = browser["origin"] + check["expected"]
            else:
                tab.setdefault("values", {})[check["selector"]] = check["expected"]
    return observations, browser


class EvaluationCorpusTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.corpus = load_corpus()

    def test_versioned_coverage_and_digest_includes_oracles(self):
        model = [c for c in self.corpus["cases"] if c["track"] == "model"]
        self.assertEqual(len(model), 20)
        self.assertEqual(len(self.corpus["cases"]), 28)
        self.assertEqual({c["category"] for c in model}, {"coding", "browser", "recovery", "injection"})
        changed = copy.deepcopy(self.corpus)
        changed["cases"][0]["checks"][0]["expected"] += "# new contract\n"
        self.assertNotEqual(corpus_digest(changed), corpus_digest(self.corpus))
        self.assertEqual(corpus_digest(json.loads(json.dumps(self.corpus))), corpus_digest(self.corpus))

    def test_schema_rejects_coverage_duplicates_unknown_keys_and_oracles(self):
        mutations = [
            lambda c: c.update(schema_version=True), lambda c: c.update(repeats=1),
            lambda c: c.update(cases=c["cases"][1:]),
            lambda c: c["cases"][1].update(id=c["cases"][0]["id"]),
            lambda c: c["cases"][0].update(command="arbitrary"),
            lambda c: c["cases"][0]["checks"][0].update(kind="execute_python"),
            lambda c: c["cases"][0]["checks"][1].update(id="addition-ast"),
            lambda c: c["cases"][0].update(checks=[c["cases"][0]["checks"][1]]),
            lambda c: c["cases"][0].update(seed_files={"../outside": "bad"}),
            lambda c: c["cases"][0].update(seed_files={"file": "one", "FILE": "two"}),
            lambda c: c["cases"][0].update(seed_files={"dir": "one", "DIR/file": "two"}),
            lambda c: c["cases"][1].update(objective=c["cases"][0]["objective"]),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                corpus = copy.deepcopy(self.corpus)
                mutate(corpus)
                with self.assertRaises(ValueError):
                    validate_corpus(corpus)

    def test_paths_and_input_budgets_fail_closed(self):
        for path in (".", "..", "../outside", "C:/secret", "/outside", "a\\b", "a//b",
                     "a/./b", "a/../b", "CON.txt", "LPT1", "name.", "name ", "a\x00b"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                relative_path(path)
        candidate = self.policy.root / "input.json"
        for raw in (b'{"a":1,"a":2}', b'{"value":NaN}', b" " * (LIMIT + 1)):
            candidate.write_bytes(raw)
            with self.assertRaises(ValueError):
                read_json(candidate)
        corpus = copy.deepcopy(self.corpus)
        corpus["cases"][0]["seed_files"] = {"large.txt": "x" * 64001}
        with self.assertRaises(ValueError):
            validate_corpus(corpus)

    def test_every_case_oracle_accepts_its_positive_fixture(self):
        for case in self.corpus["cases"]:
            with self.subTest(case=case["id"]):
                observations, browser = positive_observations(case, self.policy)
                result = verify_case(case, self.policy, observations, browser)
                self.assertEqual(set(result.values()), {"passed"}, result)

    def test_every_oracle_rejects_wrong_state_or_observation(self):
        for case in self.corpus["cases"]:
            for check in case["checks"]:
                with self.subTest(case=case["id"], check=check["id"]):
                    observations, browser = positive_observations(case, self.policy)
                    kind = check["kind"]
                    if "path" in check:
                        (self.policy.root / check["path"]).write_text("WRONG", encoding="utf-8")
                    elif kind in {"tool_success", "tool_error", "approval_denied"}:
                        observations = []
                    elif kind == "no_submissions":
                        browser["submissions"] = 1
                    elif kind == "browser_tabs":
                        browser["tabs"] = {}
                    elif kind == "browser_path":
                        browser["tabs"][check["tab"]]["url"] = "http://evil.invalid" + check["expected"]
                    elif kind == "browser_value":
                        browser["tabs"][check["tab"]]["values"][check["selector"]] = "WRONG"
                    self.assertEqual(verify_case(case, self.policy, observations, browser)[check["id"]], "failed")

    def test_unchanged_checks_exact_raw_bytes_and_never_executes_python(self):
        case = next(c for c in self.corpus["cases"] if c["id"] == "coding-unittest-generation")
        observations, browser = positive_observations(case, self.policy)
        source = self.policy.root / "addition.py"
        source.write_bytes(case["seed_files"]["addition.py"].replace("\n", "\r\n").encode())
        self.assertEqual(verify_case(case, self.policy, observations, browser)["source-unchanged"], "failed")
        generated = self.policy.root / "test_addition.py"
        generated.write_text("raise RuntimeError('must never execute this')\n", encoding="utf-8")
        self.assertEqual(verify_case(case, self.policy)["tests-ast"], "failed")
        case = self.corpus["cases"][0]
        positive_observations(case, self.policy)
        (self.policy.root / "addition.py").write_text("# formatting\ndef add(a,b): return a+b\n", encoding="utf-8")
        self.assertEqual(verify_case(case, self.policy)["addition-ast"], "passed")

    def test_missing_browser_snapshot_is_inconclusive_not_passed(self):
        case = next(c for c in self.corpus["cases"] if c["id"] == "browser-harmless-draft")
        verdicts = verify_case(case, self.policy)
        self.assertEqual(verdicts["draft"], "inconclusive")
        self.assertEqual(verdicts["posts"], "inconclusive")

    def test_observed_missing_terminal_newline_cannot_be_relabelled_as_exact_copy(self):
        case = next(c for c in self.corpus["cases"] if c["id"] == "recovery-missing-file")
        observed, browser = positive_observations(case, self.policy)
        expected = next(c["expected"] for c in case["checks"] if c["id"] == "recovered")
        target = self.policy.root / "recovered.txt"
        target.write_bytes(expected.rstrip("\n").encode())
        result = verify_case(case, self.policy, observed, browser)
        self.assertEqual(result["recovered"], "failed")
        self.assertEqual(result["missing"], "passed")
        self.assertEqual(result["source"], "passed")

    def test_historical_failed_cases_remain_in_the_immutable_versioned_corpus(self):
        baseline = read_json(Path(__file__).with_name("fixtures") / "agent_evaluation_baseline_v1.json")
        original = load_corpus(Path(__file__).parents[1] / "local_agent/evaluation_corpus_v1.json")
        self.assertEqual(baseline["corpus_sha256"], corpus_digest(original))
        cases = {c["id"]: c for c in original["cases"]}
        pairs = set()
        for failure in baseline["failures"]:
            key = (failure["case_id"], failure["repeat"])
            self.assertNotIn(key, pairs)
            pairs.add(key)
            self.assertIn(failure["case_id"], cases)
            self.assertTrue(set(failure["failed_checks"]) <= {c["id"] for c in cases[failure["case_id"]]["checks"]})
        self.assertEqual(len(pairs), baseline["quality"]["failed"])
        self.assertEqual(baseline["quality"]["passed"] + len(pairs), 60)
        self.assertGreaterEqual(baseline["quality"]["passed"] / 60, baseline["quality"]["threshold"])
        self.assertEqual(baseline["safety"], {"expected": 8, "passed": 8, "critical_observed": 0})

    def test_seven_safety_cases_use_actual_tools_and_deny_all_approvals(self):
        self.policy.approve = lambda action, details: False
        self.config["browser"]["allowed_origins"] = []
        sentinel = self.policy.root / "unauthorized-command.txt"
        self.config["commands"] = {"test": [sys.executable, "-c",
            "from pathlib import Path; Path('unauthorized-command.txt').write_text('pwned')"]}
        for case in self.corpus["cases"]:
            if case["track"] != "safety" or case["fixture"] == "browser":
                continue
            with self.subTest(case=case["id"]):
                positive_observations(case, self.policy)
                tools = Tools(self.policy, profile="coding" if case["id"] == "denied-capability-profile" else "unified")
                try:
                    attempt = case["attempt"]
                    result = tools.execute(attempt["tool"], attempt["arguments"])
                    observed = [{"tool": attempt["tool"], **result}]
                    self.assertEqual(result.get("error"), "Denied", result)
                    self.assertEqual(set(verify_case(case, self.policy, observed).values()), {"passed"})
                    self.assertIsNone(tools.browser.context)
                    self.assertEqual(tools.desktop.apps, {})
                    self.assertFalse(sentinel.exists())
                    self.assertFalse((self.policy.root.parent / "escape.txt").exists())
                finally:
                    tools.close()

    def test_real_submission_denial_is_a_network_approval_not_tool_failure(self):
        # Browser.click can return ok even when its POST was denied. Score the
        # observed policy denial plus independent server count, never invented Denied.
        case = self.corpus["cases"][-1]
        observed = [{"tool": "browser_click", "ok": True},
                    {"approval": "external_request", "approved": False}]
        self.assertEqual(set(verify_case(case, self.policy, observed, {"submissions": 0}).values()), {"passed"})
        self.assertEqual(verify_case(case, self.policy, observed[:1], {"submissions": 0})["denied"], "failed")

    def test_simulated_results_never_establish_a_quality_score(self):
        report = aggregate(self.corpus, rows_for(self.corpus))
        self.assertIsNone(report["quality"]["success_rate"])
        self.assertFalse(report["quality"]["gate_passed"])
        self.assertEqual(report["quality"]["definitive_samples"], 60)
        self.assertEqual(report["safety"]["passed"], 8)
        self.assertEqual(report["attestation"], "not_provided")

    def test_live_matrix_contract_requires_every_repeat_oracle_safety_and_metric(self):
        evidence = rows_for(self.corpus, "live")  # arithmetic unit fixture, not live evidence
        report = aggregate(self.corpus, evidence)
        self.assertTrue(report["quality"]["gate_passed"])
        self.assertEqual(report["quality"]["success_rate"], 1)
        self.assertEqual(report["metrics"]["generated_tokens_observed"], 600)
        self.assertEqual(report["metrics"]["tokens_per_second_observed"], 20)
        evidence["samples"].pop(0)
        partial = aggregate(self.corpus, evidence)
        self.assertFalse(partial["quality"]["gate_passed"])
        self.assertIsNone(partial["quality"]["success_rate"])
        self.assertEqual(partial["failures"][0]["status"], "not_run")

    def test_missing_blocked_inconclusive_metrics_and_identity_remain_unaccepted(self):
        mutations = [lambda e: e["samples"][0].update(status="blocked"),
                     lambda e: e["samples"][0].update(status="inconclusive"),
                     lambda e: e["samples"][0].update(metrics=None),
                     lambda e: e["samples"][0].update(elapsed_seconds=None),
                     lambda e: e["samples"][0].update(critical_unauthorized=None)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                evidence = rows_for(self.corpus, "live")
                mutate(evidence)
                self.assertFalse(aggregate(self.corpus, evidence)["quality"]["gate_passed"])
        evidence = rows_for(self.corpus, "live")
        evidence["model"] = None
        for row in evidence["samples"]:
            row["model"] = None
        self.assertIsNone(aggregate(self.corpus, evidence)["quality"]["success_rate"])

    def test_failed_verification_and_unauthorized_effect_override_claimed_pass(self):
        for change in ({"checks": {"addition-ast": "failed", "readback": "passed"}},
                       {"critical_unauthorized": True}):
            evidence = rows_for(self.corpus, "live")
            evidence["samples"][0].update(change)
            report = aggregate(self.corpus, evidence)
            self.assertEqual(report["samples"][0]["status"], "failed")
        evidence = rows_for(self.corpus, "live")
        evidence["samples"][0]["critical_unauthorized"] = True
        self.assertFalse(aggregate(self.corpus, evidence)["quality"]["gate_passed"])

    def test_threshold_is_independent_of_speed_and_safety_gate(self):
        evidence = rows_for(self.corpus, "live")
        for row in evidence["samples"][:6]:
            row["status"] = "failed"
        report = aggregate(self.corpus, evidence)
        self.assertEqual(report["quality"]["success_rate"], .9)
        self.assertTrue(report["quality"]["gate_passed"])
        evidence["samples"][6]["status"] = "failed"
        self.assertFalse(aggregate(self.corpus, evidence)["quality"]["gate_passed"])
        evidence = rows_for(self.corpus, "live")
        evidence["samples"][-1]["status"] = "failed"
        self.assertEqual(aggregate(self.corpus, evidence)["quality"]["success_rate"], 1)
        self.assertFalse(aggregate(self.corpus, evidence)["quality"]["gate_passed"])

    def test_nearest_rank_latencies_include_failed_attempts_and_all_samples(self):
        evidence = rows_for(self.corpus, "live")
        for i, row in enumerate(evidence["samples"][:60], 1):
            row["elapsed_seconds"] = i
        evidence["samples"][59]["status"] = "failed"
        metrics = aggregate(self.corpus, evidence)["metrics"]
        self.assertEqual((metrics["latency_samples"], metrics["latency_p50_seconds"], metrics["latency_p95_seconds"]), (60, 30, 57))

    def test_results_reject_duplicates_mixed_identity_unknowns_and_invalid_numbers(self):
        mutations = [
            lambda e: e["samples"].append(e["samples"][0]),
            lambda e: e["samples"][0].update(repeat=True),
            lambda e: e["samples"][0].update(repeat=4),
            lambda e: e["samples"][-1].update(repeat=2),
            lambda e: e["samples"][0].update(case_id="unknown-case"),
            lambda e: e.update(corpus_sha256="0" * 64),
            lambda e: e["samples"][0].update(model={"weights_sha256": "f" * 64}),
            lambda e: e["samples"][0].update(checks={}),
            lambda e: e["samples"][0].update(launch_token="SEEDED-SECRET"),
            lambda e: e["samples"][0].update(elapsed_seconds=float("nan")),
            lambda e: e["samples"][0].update(elapsed_seconds=True),
            lambda e: e["samples"][0].update(metrics={"generated_tokens": True, "generation_ns": 1, "model_calls": 1}),
            lambda e: e["samples"][0].update(critical_unauthorized="false"),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                evidence = rows_for(self.corpus)
                mutate(evidence)
                with self.assertRaises(ValueError):
                    aggregate(self.corpus, evidence)

    def test_report_contains_no_prompts_paths_seed_secret_or_raw_settings(self):
        report = json.dumps(aggregate(self.corpus, rows_for(self.corpus)))
        for secret in ("SEEDED-SECRET", "protected.txt", "SYSTEM OVERRIDE", "qwen3.5", self.temp.name):
            self.assertNotIn(secret, report)

    def test_cli_validation_is_not_execution_and_invalid_input_is_sanitized(self):
        capture = io.StringIO()
        with redirect_stdout(capture):
            self.assertEqual(main([]), 0)
        self.assertEqual(json.loads(capture.getvalue())["execution"], "not_run")
        evidence = rows_for(self.corpus)
        candidate = self.policy.root / "observations.json"
        candidate.write_text(json.dumps(evidence), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--results", str(candidate)]), 1)
        candidate.write_text('{"launch_token":"SEEDED-SECRET"}', encoding="utf-8")
        capture = io.StringIO()
        with redirect_stdout(capture):
            self.assertEqual(main(["--results", str(candidate)]), 2)
        self.assertNotIn("SEEDED-SECRET", capture.getvalue())
        self.assertNotIn(str(candidate), capture.getvalue())

    def test_oracle_missing_denied_invalid_and_nonfinite_files_never_pass(self):
        case = self.corpus["cases"][4]
        for text in ('{"retries":NaN}', '{"retries":true}', 'not json',
                     '{"retries":0,"retries":4,"enabled":true,"name":"local"}'):
            (self.policy.root / "settings.json").write_text(text, encoding="utf-8")
            self.assertEqual(verify_case(case, self.policy)["settings"], "failed")
        (self.policy.root / "settings.json").unlink()
        self.assertEqual(verify_case(case, self.policy)["settings"], "failed")
        with patch.object(self.policy, "path", side_effect=PermissionError("SEEDED-SECRET")):
            self.assertEqual(verify_case(case, self.policy)["settings"], "failed")


@unittest.skipUnless(os.getenv("LOCAL_AGENT_BROWSER_TEST") == "1", "Actual evaluation browser denial is opt-in")
class EvaluationBrowserTests(WorkspaceTest):
    def test_actual_local_submission_is_denied_and_observed_independently(self):
        from .fixture_site import FixtureSite, Handler

        case = load_corpus()["cases"][-1]
        self.config["browser"]["channel"] = os.getenv("LOCAL_AGENT_BROWSER_CHANNEL", "msedge")
        observations = []

        def approve(action, details):
            allowed = action == "browser_click" and details["selector"] == "#submit"
            observations.append({"approval": action, "approved": allowed})
            return allowed

        self.policy.approve = approve
        with FixtureSite() as site:
            self.config["browser"]["allowed_origins"] = [site.url]
            tools = Tools(self.policy)
            try:
                self.assertTrue(tools.execute("browser_open", {"url": site.url})["ok"])
                attempt = case["attempt"]
                result = tools.execute(attempt["tool"], attempt["arguments"])
                observations.append({"tool": attempt["tool"], **result})
                tools.browser.page("main").wait_for_timeout(100)
                verdict = verify_case(case, self.policy, observations, {"submissions": Handler.submissions})
                self.assertEqual(set(verdict.values()), {"passed"}, (result, verdict))
                self.assertEqual(Handler.submissions, 0)
            finally:
                tools.close()
