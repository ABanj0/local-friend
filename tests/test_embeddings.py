"""Embedding protocol/security contracts. HTTP fixtures are not quality evidence."""
import copy
import json
import math
import os
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from local_agent.config import load
from local_agent.embeddings import (
    MAX_RESPONSE,
    QUERY_INSTRUCTION,
    EmbeddingError,
    Embeddings,
    cosine,
    normalized,
)
from local_agent.safety import Denied
from tests.ollama_fixture import metadata_response


class EmbeddingTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.change_identity = False
        self.result = {"model": "fixture", "embeddings": [[3., 4.]],
                       "total_duration": 100, "load_duration": 10, "prompt_eval_count": 3}
        self.show = {"capabilities": ["embedding"], "details": {"format": "gguf"},
                     "model_info": {"qwen3.embedding_length": 2}}
        self.special = None
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                self.respond(None)

            def do_POST(self):
                self.respond(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))

            def respond(self, payload):
                owner.calls.append((self.path, payload))
                if owner.special:
                    owner.special(self)
                    return
                if self.path == "/api/embed":
                    value = copy.deepcopy(owner.result)
                    if owner.change_identity:
                        owner.digest = "b" * 64
                elif self.path == "/api/show":
                    value = owner.show
                else:
                    value = metadata_response(self.path, payload, digest=owner.digest)
                data = json.dumps(value).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.digest = "a" * 64
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)
        self.config = dict(load()["model"], name="fixture",
                           url=f"http://127.0.0.1:{self.server.server_port}", timeout=2)
        self.client = Embeddings(self.config)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def test_real_http_payload_identity_normalization_and_bounded_receipts(self):
        identity, vectors = self.client.embed(["项目 note"], query=True)
        self.assertEqual(identity["digest"], "a" * 64)
        self.assertEqual(identity["dimensions"], 2)
        self.assertEqual(vectors, [[.6, .8]])
        request = next(payload for path, payload in self.calls if path == "/api/embed")
        self.assertEqual(request, {"model": "fixture", "input": [QUERY_INSTRUCTION + "项目 note"],
                                   "truncate": False, "keep_alive": "1m"})
        self.assertEqual(self.client.receipts[0]["prompt_eval_count"], 3)
        self.assertNotIn("input", self.client.receipts[0])
        self.assertGreater(self.client.receipts[0]["wall_seconds"], 0)
        self.assertEqual(sum(path == "/api/show" for path, _ in self.calls), 2)

    def test_invalid_inputs_never_contact_service(self):
        for texts in ([], "text", [""], ["\0"], [True], ["a"] * 17, ["é" * 4097]):
            with self.subTest(texts=str(texts)[:20]), self.assertRaises(ValueError):
                self.client.embed(texts)
        with self.assertRaises(ValueError):
            self.client.embed(["safe"], query=1)
        with self.assertRaises(Denied):
            self.client.embed(["password=private-example-secret"])
        self.assertEqual(self.calls, [])

    def test_local_endpoint_and_timeout_validation(self):
        for url in ("https://127.0.0.1", "http://example.com", "http://user:secret@localhost",
                    "http://localhost/?secret=x", "http://localhost/#x"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                Embeddings(dict(self.config, url=url))
        for timeout in (True, False, "3", float("nan"), float("inf"), 0, -1):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                Embeddings(dict(self.config, timeout=timeout))
        self.assertEqual(Embeddings(dict(self.config, timeout=60)).timeout, 30)
        self.assertEqual(Embeddings(dict(self.config, timeout=10**400)).timeout, 30)
        with self.assertRaises(EmbeddingError):
            self.client.request("/api/pull", {"model": "x"})
        self.assertEqual(self.calls, [])

    def test_incompatible_metadata_prevents_embedding(self):
        for info in ({}, {"qwen3.embedding_length": True}, {"qwen3.embedding_length": 4097},
                     {"qwen3.embedding_length": 2, "other.embedding_length": 3},
                     {"qwen3.embedding_length": 2, "other.embedding_length": "2"}):
            self.show["model_info"] = info
            with self.subTest(info=info), self.assertRaises(EmbeddingError):
                self.client.embed(["safe"])
        self.show["capabilities"] = ["completion"]
        with self.assertRaises(EmbeddingError):
            self.client.embed(["safe"])
        self.assertFalse(any(p == "/api/embed" for p, _ in self.calls))

    def test_changed_model_invalidates_entire_result(self):
        self.change_identity = True
        with self.assertRaisesRegex(EmbeddingError, "changed"):
            self.client.embed(["safe"])
        self.assertEqual(self.client.receipts, [])

    def test_bad_results_and_native_counters_never_create_receipts(self):
        for change in ({"model": "other"}, {"embeddings": []}, {"embeddings": [[1]]},
                       {"embeddings": [[0, 0]]}, {"embeddings": [[True, 1]]},
                       {"embeddings": [[float("nan"), 1]]}, {"total_duration": True},
                       {"load_duration": -1}, {"prompt_eval_count": None}):
            original = self.result
            self.result = {**original, **change}
            with self.subTest(change=change), self.assertRaises(EmbeddingError):
                self.client.embed(["safe"])
            self.result = original
        self.assertEqual(self.client.receipts, [])

    def test_redirect_errors_oversize_and_invalid_json_are_safe(self):
        def reply(status, body=b"", length=None):
            def send(handler):
                handler.send_response(status)
                handler.send_header("Location", "http://example.com/private")
                handler.send_header("Content-Length", str(len(body) if length is None else length))
                handler.end_headers()
                handler.wfile.write(body)
            return send
        for status, body, length in ((302, b"secret", None), (500, b"password=private", None),
                                     (200, b"{}", MAX_RESPONSE + 1), (200, b"{", None),
                                     (200, b"[]", None)):
            self.special = reply(status, body, length)
            with self.subTest(status=status, length=length), self.assertRaises(EmbeddingError) as caught:
                self.client.request("/api/tags")
            self.assertNotIn("private", str(caught.exception))
        self.assertEqual(len(self.calls), 5)

    def test_absolute_deadline_bounds_dripping_headers_and_body_without_stopping_server(self):
        for headers in (True, False):
            finished = threading.Event()

            def drip(handler, headers=headers, finished=finished):
                try:
                    if headers:
                        handler.wfile.write(b"HTTP/1.1 200 OK\r\nX-Slow: ")
                    else:
                        handler.send_response(200)
                        handler.send_header("Content-Length", "1000")
                        handler.end_headers()
                    for _ in range(40):
                        handler.wfile.write(b" ")
                        handler.wfile.flush()
                        time.sleep(.025)
                except OSError:
                    pass
                finally:
                    finished.set()

            self.client.timeout = .2
            self.special = drip
            start = time.monotonic()
            with self.assertRaises(EmbeddingError):
                self.client.request("/api/tags")
            self.assertLess(time.monotonic() - start, 1.)
            self.assertTrue(finished.wait(2))
            self.special = None
            self.client.timeout = 2
            self.assertIn("models", self.client.request("/api/tags"))

    def test_vector_math_rejects_invalid_values(self):
        for vector in ([], [True], [float("inf")], [float("nan")], [0], [1e7], [10**400], (1, 2)):
            with self.subTest(vector=vector), self.assertRaises(EmbeddingError):
                normalized(vector)
        self.assertAlmostEqual(cosine(normalized([3, 4]), normalized([3, 4])), 1.)
        with self.assertRaises(EmbeddingError):
            cosine([1.], [1., 2.])

    def test_expired_aggregate_deadline_prevents_network_access(self):
        self.client.deadline = time.monotonic() - 1
        with self.assertRaisesRegex(EmbeddingError, 'total time budget'):
            self.client.request('/api/tags')
        self.assertEqual(self.calls, [])

    def test_close_interrupts_owned_request_and_preserves_listener(self):
        entered, release = threading.Event(), threading.Event()
        errors = []

        def block(handler):
            handler.send_response(200)
            handler.send_header('Content-Length', '1000')
            handler.end_headers()
            entered.set()
            release.wait(3)

        def request():
            try:
                self.client.request('/api/tags')
            except EmbeddingError as exc:
                errors.append(exc)

        self.special = block
        thread = threading.Thread(target=request)
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            self.client.close()
            thread.join(1)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(errors), 1)
            self.assertEqual(self.client.sockets, set())
            self.special = None
            self.assertIn('models', Embeddings(self.config).request('/api/tags'))
            with self.assertRaisesRegex(EmbeddingError, 'cancelled'):
                self.client.request('/api/tags')
        finally:
            release.set()
            thread.join(3)


@unittest.skipUnless(os.environ.get("LIVE_EMBEDDINGS") == "1", "Actual embedding contract is opt-in")
class LiveEmbeddingTests(unittest.TestCase):
    def test_actual_local_model_identity_vectors_and_native_receipt(self):
        config = load()
        from local_agent.benchmark import ensure_idle
        ensure_idle(config)
        client = Embeddings(dict(config["model"], name="qwen3-embedding:0.6b"))
        identity, vectors = client.embed(["A blue notebook.", "A red notebook."])
        self.assertEqual(len(vectors), 2)
        self.assertEqual(len(vectors[0]), identity["dimensions"])
        self.assertTrue(all(math.isfinite(v) for vector in vectors for v in vector))
        self.assertAlmostEqual(sum(v * v for v in vectors[0]), 1.)
        self.assertGreater(client.receipts[0]["prompt_eval_count"], 0)
        print("Actual embedding contract:", json.dumps({"identity": identity, "timings": client.receipts}))
