"""Fixed corpus, host scope and quality-evidence provenance contracts."""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from local_agent.semantic_evaluation import CORPUS, corpus, evaluate, hybrid_rank, semantic_rank
from tests.support import WorkspaceTest


class SemanticEvaluationTests(WorkspaceTest):
    def test_fixed_corpus_keeps_existing_literal_baseline_and_hash(self):
        data, digest = corpus()
        baseline = json.loads(Path("tests/fixtures/memory_recall_v1.json").read_text(encoding="utf-8"))
        self.assertEqual([(c["note"], c["literal"]) for c in data["cases"]],
                         [(c["note"], c["question"]) for c in baseline])
        self.assertEqual(len(data["cases"]), 32)
        self.assertEqual(digest, hashlib.sha256(CORPUS.read_bytes()).hexdigest())
        self.assertEqual(digest, "2108b57f57bedda4b0906f66e8448aaf02e4d1b64bcd5d93bb987ecb592ae30b")

    def test_invalid_corpus_bounds_types_duplicates_and_gate_changes(self):
        original, _ = corpus()
        bad = []
        for key, value in (("version", True), ("fusion", "other"), ("cases", []),
                           ("distractor_suffixes", ["a"]), ("unexpected", 1)):
            bad.append({**original, key: value})
        for field, value in (("literal_no_loss", 1), ("cross_project_results", False),
                             ("recall_at_5", .8)):
            bad.append({**original, "gate": {**original["gate"], field: value}})
        duplicate = copy.deepcopy(original)
        duplicate["cases"][-1] = duplicate["cases"][0]
        bad.append(duplicate)
        path = Path(self.temp.name) / "corpus.json"
        for value in bad:
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.subTest(keys=list(value)), self.assertRaises(ValueError):
                corpus(path)
        path.write_bytes(b" " * 128001)
        with self.assertRaises(ValueError):
            corpus(path)

    def test_scope_filters_before_vectors_are_accessed(self):
        rows = [{"id": "outside", "scope": "other"}, {"id": "mine", "scope": "current"}]
        # No outside vector exists: scope must be applied before similarity calculation.
        self.assertEqual(semantic_rank("current", rows, {"mine": [1., 0.]}, [1., 0.]), ["mine"])
        self.assertEqual(semantic_rank("empty", rows, {}, [1., 0.]), [])
        for scope in ("", None, True):
            with self.assertRaises(ValueError):
                semantic_rank(scope, rows, {}, [1., 0.])

    def test_fixed_hybrid_fusion_is_bounded_deterministic_and_semantic_breaks_ties(self):
        self.assertEqual(hybrid_rank(["lexical"], ["semantic"]), ["semantic", "lexical"])
        self.assertEqual(hybrid_rank(["a", "b"], ["b", "c"]), ["b", "a", "c"])
        self.assertEqual(len(hybrid_rank(list("abcde"), list("fghij"))), 5)
        self.assertEqual(hybrid_rank([], []), [])
        for left, right in ((["a", "a"], []), ([], list("abcdef"))):
            with self.assertRaises(ValueError):
                hybrid_rank(left, right)

    def test_protocol_fixture_can_meet_checks_but_never_establish_quality_or_overwrite(self):
        data, _ = corpus()
        indices = {text: index for index, case in enumerate(data["cases"])
                   for text in (case["note"], case["literal"], case["paraphrase"])}

        class Fixture:
            def __init__(self, config):
                self.receipts = []

            def identity(self):
                return {"model": "fixture", "digest": "a" * 64, "dimensions": 33,
                        "server_version": "0.40.7", "query_format": "project-note-instruct-v1"}

            def embed(self, texts, *, query=False):
                vectors = []
                for text in texts:
                    vector = [0.] * 33
                    vector[indices.get(text, 32)] = 1.
                    vectors.append(vector)
                return self.identity(), vectors

        self.config["base"] = Path(self.temp.name)
        result, destination = evaluate(self.config, client_factory=Fixture)
        self.assertEqual(result["source"], "protocol_fixture")
        self.assertTrue(result["checks_met"])
        self.assertFalse(result["gate_passed"])
        self.assertFalse(result["production_enabled"])
        self.assertEqual(result["cross_project_results"], 0)
        self.assertEqual(result["counts"]["paraphrase"]["hybrid"], 32)
        saved = (destination / "report.json").read_bytes()
        with self.assertRaises(FileExistsError):
            evaluate(self.config, output=destination, client_factory=Fixture)
        self.assertEqual(saved, (destination / "report.json").read_bytes())
        report = saved.decode()
        self.assertNotIn(data["cases"][0]["note"], report)
        self.assertNotIn("input", result["source_sha256"])

    def test_failed_measurement_retains_incomplete_report_and_closes_manager(self):
        class Broken:
            def __init__(self, config):
                pass

            def identity(self):
                raise RuntimeError("private failure contents")

        self.config["base"] = Path(self.temp.name)
        base = self.config["base"] / ".runtime" / "semantic-evaluations"
        with self.assertRaises(RuntimeError):
            evaluate(self.config, client_factory=Broken)
        path, = list(base.glob("*/report.json"))
        report = json.loads(path.read_text())
        self.assertEqual(report["status"], "incomplete")
        self.assertNotIn("gate_passed", report)
        self.assertNotIn("private failure", path.read_text())
        with (patch("local_agent.semantic_evaluation.ensure_idle", side_effect=ValueError("active")),
              self.assertRaises(ValueError)):
            evaluate(self.config)
        self.assertEqual(len(list(base.glob("*/report.json"))), 1)
