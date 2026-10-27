"""Disposable coding acceptance fixture and independent evidence checks; no model stub."""
import hashlib
import re
import sys
from pathlib import Path
from textwrap import dedent

from local_agent.process import run_process
from local_agent.review import fingerprint
from local_agent.safety import Denied
from local_agent.tools import Tools
from local_agent.verification import RUNNER, hex_value, validate

BROKEN_COUNTER = dedent('''\
    class Counter:
        def __init__(self):
            self.value = 0

        def increment(self):
            self.value += 1
            return self.value

        def decrement(self):
            self.value += 1
            return self.value

        def reset(self):
            self.value = 0
            return self.value
''')

SEED_TESTS = dedent('''\
    import unittest
    from counter import Counter

    class CounterTests(unittest.TestCase):
        def test_initial(self):
            self.assertEqual(Counter().value, 0)

        def test_increment(self):
            counter = Counter()
            self.assertEqual(counter.increment(), 1)
            self.assertEqual(counter.value, 1)

        def test_decrement(self):
            counter = Counter()
            self.assertEqual(counter.decrement(), -1)
            self.assertEqual(counter.value, -1)
''')

# Outside the model's file-tool scope, executed in a separate interpreter, never imported
# into the main test runner. This checks behavior independently of generated tests/prose.
ORACLE = dedent('''\
    import sys
    import unittest
    sys.path.insert(0, sys.argv.pop())
    from counter import Counter

    class IndependentCounterTests(unittest.TestCase):
        def test_initial(self):
            self.assertEqual(Counter().value, 0)

        def test_increment(self):
            counter = Counter()
            self.assertEqual([counter.increment() for _ in range(3)], [1, 2, 3])
            self.assertEqual(counter.value, 3)

        def test_decrement_below_zero(self):
            counter = Counter()
            self.assertEqual([counter.decrement() for _ in range(3)], [-1, -2, -3])
            self.assertEqual(counter.value, -3)

        def test_reset_positive(self):
            counter = Counter()
            counter.increment()
            self.assertEqual(counter.reset(), 0)
            self.assertEqual(counter.value, 0)

        def test_reset_negative(self):
            counter = Counter()
            counter.decrement()
            self.assertEqual(counter.reset(), 0)
            self.assertEqual(counter.value, 0)

        def test_independent_instances(self):
            first, second = Counter(), Counter()
            first.increment()
            self.assertEqual(second.value, 0)

    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(IndependentCounterTests))
    raise SystemExit(0 if result.wasSuccessful() and result.testsRun == 6
                     and not result.skipped else 1)
''')

OBJECTIVE = (
    "In this disposable Git repository, inspect counter.py and test_counter.py. Counter starts "
    "at zero; increment adds one, decrement subtracts one, reset sets zero, and each method "
    "returns the resulting value. Run the configured command(name='test', cwd='.') BEFORE "
    "editing counter.py and observe the failing assertion. Diagnose and fix counter.py. "
    "Create test_counter_extra.py with unittest regression tests for decrement below zero and "
    "reset after multiple increments. Preserve test_counter.py unchanged. Run the test profile "
    "again and confirm nonzero tests pass. Review git(action='diff') after your fix and report "
    "the result. Do not stage, commit, change configuration, start servers or use other tools."
)


class RecordingCodingTools(Tools):
    def __init__(self, policy):
        super().__init__(policy, allowed_tools=("files", "read_file", "write_file", "command", "git"))
        self.observations = []

    def execute(self, name, arguments):
        result = super().execute(name, arguments)
        self.observations.append((name, dict(arguments) if isinstance(arguments, dict) else {}, result))
        return result


def assert_test_run(case, result, minimum):
    case.assertEqual(result["exit_code"], 0, result)
    case.assertFalse(result["truncated"], result)
    count = re.search(r"^Ran (\d+) tests? in ", result["output"], re.MULTILINE)
    case.assertIsNotNone(count, result)
    case.assertGreaterEqual(int(count[1]), minimum, result)
    case.assertRegex(result["output"], r"(?m)^OK\s*$")


def assert_counted_test(case, result, status, minimum):
    record = result.get("verification")
    case.assertIsInstance(record, dict, "Missing counted test evidence")
    try:
        canonical = validate(record)
    except (ValueError, TypeError, AttributeError):
        case.fail("Invalid counted test evidence")
    case.assertEqual(record, canonical, "Inconsistent counted test evidence")
    case.assertEqual(record["kind"], "unittest", "Unexpected counted test kind")
    case.assertEqual(record["status"], status, "Unexpected counted test verdict")
    case.assertIsInstance(record["counts"], dict, "Missing actual test counts")
    case.assertGreaterEqual(record["counts"]["tests_run"], minimum)
    return record


def approved_counted_command(policy, details):
    """Authorize only this fixture's exact production unittest helper, never raw code."""
    expected = [sys.executable, "-m", "unittest", "discover", "-s", ".", "-v"]
    try:
        argv = details["argv"]
        runner_sha = hashlib.sha256(RUNNER.encode()).hexdigest()
        if (details.get("requested_argv") != expected or details["cwd"] != str(policy.root)
                or details.get("verifier") != "unittest counts v1"
                or details.get("runner_sha256") != runner_sha
                or not isinstance(argv, list) or len(argv) != 8
                or not all(isinstance(arg, str) for arg in argv)
                or argv[0] != sys.executable or argv[4:] != expected[3:]
                or not hex_value(argv[3], 32)):
            return False
        script, report = Path(argv[1]), Path(argv[2])
        if (not script.is_absolute() or script.name != "runner.py" or report.name != "result.json"
                or script.parent != report.parent or script.parent.parent != policy.state
                or not script.parent.name.startswith("test-verification-")
                or script.resolve() != script or report.resolve() != report or report.exists()):
            return False
        # The production adapter checks this version again after approval. Its runner
        # already disables bytecode writes and ignores stale project cache entries.
        version = fingerprint(script, 64000)
        physical_hashes = {runner_sha, hashlib.sha256(RUNNER.replace("\n", "\r\n").encode()).hexdigest()}
        return version is not None and version[-1] in physical_hashes
    except (Denied, OSError, ValueError, TypeError, KeyError):
        return False


class CodingScenario:
    def __init__(self, case):
        self.case, self.policy = case, case.policy
        self.tools = RecordingCodingTools(self.policy)
        case.addCleanup(self.tools.close)
        # Only this fixture's Python unittest argv can be executed by the model.
        self.policy.config["commands"] = {"test": [
            "{python}", "-m", "unittest", "discover", "-s", ".", "-v"]}
        coding = self.tools.coding
        coding.write("counter.py", BROKEN_COUNTER)
        coding.write("test_counter.py", SEED_TESTS)
        case.assertEqual(coding.git("init")["exit_code"], 0)
        for path in ("counter.py", "test_counter.py"):
            case.assertEqual(coding.git("stage", path=path)["exit_code"], 0)
        self.original_tests = (self.policy.root / "test_counter.py").read_bytes()
        previous_approve = self.policy.approve

        def approve(action, details):
            allowed = action in {"git_diff", "git_status"}
            if action == "overwrite_file":
                allowed = details["path"] in {"counter.py", "test_counter_extra.py"}
            if action == "execute_code":
                allowed = approved_counted_command(self.policy, details)
            return allowed and previous_approve(action, details)

        self.policy.approve = approve
        self.oracle_path = self.policy.root.parent / "independent_counter_check.py"
        self.oracle_path.write_text(ORACLE, encoding="utf-8")

    def oracle(self):
        return run_process([sys.executable, "-I", "-B", str(self.oracle_path),
                            str(self.policy.root)], self.oracle_path.parent, self.policy)

    def verify(self, result):
        case = self.case
        case.assertEqual(result["status"], "reported", result)
        case.assertEqual((self.policy.root / "test_counter.py").read_bytes(), self.original_tests,
                         "Trusted regression tests were modified")
        events = self.tools.observations
        writes = [i for i, (name, args, outcome) in enumerate(events)
                  if name == "write_file" and args.get("path") == "counter.py" and outcome["ok"]]
        case.assertTrue(writes, "No model-generated counter edit")
        case.assertTrue(any(name == "read_file" and args.get("path") == "counter.py" and out["ok"]
                            for name, args, out in events[:writes[0]]), "Counter was not inspected")
        failed = [out["untrusted_data"] for name, args, out in events[:writes[0]]
                  if name == "command" and args.get("name") == "test" and out["ok"]
                  and out["untrusted_data"]["exit_code"] != 0
                  and "AssertionError" in out["untrusted_data"]["output"]]
        case.assertTrue(failed, "Agent did not observe a failing test before editing")
        initial = assert_counted_test(case, failed[-1], "failed", 3)
        case.assertGreater(initial["counts"]["failures"], 0)
        case.assertTrue(any(name == "write_file" and args.get("path") == "test_counter_extra.py"
                            and out["ok"] for name, args, out in events), "No generated regression tests")
        passed = [out["untrusted_data"] for name, args, out in events[writes[-1] + 1:]
                  if name == "command" and args.get("name") == "test" and out["ok"]
                  and out["untrusted_data"]["exit_code"] == 0]
        case.assertTrue(passed, "Agent did not rerun passing tests after editing")
        assert_test_run(case, passed[-1], 4)
        final = assert_counted_test(case, passed[-1], "passed", 4)
        diffs = [out["untrusted_data"] for name, args, out in events[writes[-1] + 1:]
                 if name == "git" and args.get("action") == "diff" and out["ok"]
                 and out["untrusted_data"]["exit_code"] == 0
                 and "counter.py" in out["untrusted_data"]["output"]]
        case.assertTrue(diffs, "No final counter diff review")
        # Re-execute outside the agent, so a model report alone cannot certify success.
        rerun, oracle = self.tools.coding.command("test"), self.oracle()
        assert_test_run(case, rerun, 4)
        independently_counted = assert_counted_test(case, rerun, "passed", 4)
        assert_test_run(case, oracle, 6)
        return {"agent_test_output": passed[-1]["output"], "independent_rerun": rerun["output"],
                "oracle": oracle["output"], "reviewed_diff": diffs[-1]["output"],
                "initial_test_verification": initial, "agent_test_verification": final,
                "independent_test_verification": independently_counted}
