import io
import json
import unittest
from unittest.mock import Mock

from local_agent.model import Ollama


class ModelMetricsTests(unittest.TestCase):
    def setUp(self):
        self.model = Ollama({"url": "http://127.0.0.1:11434", "name": "fixture",
                             "timeout": 5, "context": 2048, "max_output": 128, "temperature": 0.1})

    def test_weighted_speed_and_missing_statistics(self):
        self.assertIsNone(self.model.metrics())
        for invalid in ({}, {"done": False, "eval_count": 10, "eval_duration": 1},
                        {"done": True, "eval_count": -1, "eval_duration": 1}):
            self.model.record_usage(invalid)
        self.assertIsNone(self.model.metrics())
        self.model.record_usage({"done": True, "eval_count": 80, "eval_duration": 2_000_000_000})
        self.model.record_usage({"done": True, "eval_count": 20, "eval_duration": 3_000_000_000})
        self.assertEqual(self.model.metrics(), {"generated_tokens": 100, "tokens_per_second": 20,
                                                "model_calls": 2})

    def test_zero_duration_does_not_invent_speed(self):
        self.model.record_usage({"done": True, "eval_count": 3, "eval_duration": 0})
        self.assertIsNone(self.model.metrics()["tokens_per_second"])

    def test_truncated_stream_is_not_success(self):
        data = json.dumps({"message": {"content": "partial"}}).encode() + b"\n"
        self.model.opener = Mock()
        self.model.admit = Mock()
        self.model.opener.open.return_value = io.BytesIO(data)
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            list(self.model.stream_chat([]))
        self.assertIsNone(self.model.metrics())
