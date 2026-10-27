"""Bounded local embeddings. Vector similarity is data, never an execution grant."""
import http.client
import io
import json
import math
import select
import socket
import threading
import time
from urllib.parse import urlsplit

from .inference import CapabilityCache
from .model import Ollama
from .safety import Denied, redact

MAX_BATCH = 16
MAX_INPUT_BYTES = 8192
MAX_RESPONSE = 2 * 1024 * 1024
MAX_DIMENSIONS = 4096
QUERY_INSTRUCTION = "Instruct: Retrieve the saved project note that answers the question.\nQuery: "


class EmbeddingError(RuntimeError):
    pass


class _ResponseReader(io.RawIOBase):
    """Poll an owned duplicate: Windows buffered recv may outlive shutdown()."""
    def __init__(self, owned_socket, cancelled, deadline):
        super().__init__()
        self.socket = owned_socket.dup()
        self.socket.setblocking(False)
        self.cancelled, self.deadline = cancelled, deadline

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            if self.cancelled.is_set():
                raise EmbeddingError("Embedding operation was cancelled")
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise EmbeddingError("Embedding operation exceeded its total time budget")
            ready, _, _ = select.select([self.socket], [], [], min(.025, remaining))
            if ready:
                try:
                    return self.socket.recv_into(buffer)
                except BlockingIOError:
                    continue

    def close(self):
        if not self.closed:
            self.socket.close()
        super().close()


class _ResponseSocket:
    def __init__(self, owned_socket, cancelled, deadline):
        self.socket, self.cancelled, self.deadline = owned_socket, cancelled, deadline

    def makefile(self, mode):
        if mode != "rb":
            raise ValueError("Embedding response is read-only binary data")
        return io.BufferedReader(_ResponseReader(self.socket, self.cancelled, self.deadline))


def normalized(vector, dimension=None):
    if (type(vector) is not list or not 1 <= len(vector) <= MAX_DIMENSIONS
            or dimension is not None and len(vector) != dimension
            or any(type(v) not in {int, float} or abs(v) > 1e6 or not math.isfinite(v)
                   for v in vector)):
        raise EmbeddingError("Embedding vector is malformed or has the wrong dimension")
    norm = math.sqrt(math.fsum(v * v for v in vector))
    if not math.isfinite(norm) or norm < 1e-12:
        raise EmbeddingError("Embedding vector has no usable magnitude")
    return [v / norm for v in vector]


def cosine(left, right):
    if len(left) != len(right) or not left:
        raise EmbeddingError("Embedding dimensions differ")
    return max(-1., min(1., math.fsum(a * b for a, b in zip(left, right, strict=True))))


class Embeddings(Ollama):
    def __init__(self, config):
        super().__init__(config)  # Reuse existing local endpoint/options validation.
        address = urlsplit(config["url"])
        if address.query or address.fragment:
            raise ValueError("Embedding endpoint cannot contain a query or fragment")
        self.host, self.port = address.hostname, address.port or 11434
        timeout = config["timeout"]
        if (type(timeout) not in {int, float} or timeout <= 0
                or type(timeout) is float and not math.isfinite(timeout)):
            raise ValueError("Embedding timeout must be finite and positive")
        self.timeout = float(min(timeout, 30))
        self.cache = CapabilityCache(ttl=0)
        self.last_show, self.receipts = None, []
        self.deadline = None  # Optional host-owned aggregate deadline across several requests.
        self.cancelled = threading.Event()
        self.socket_lock = threading.Lock()
        self.sockets = set()

    def close(self):
        """Interrupt only this client's requests; never stop the shared Ollama service."""
        with self.socket_lock:
            self.cancelled.set()
            for owned in self.sockets:
                try:
                    owned.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

    def request(self, endpoint, payload=None):
        if endpoint not in {"/api/tags", "/api/version", "/api/show", "/api/embed"}:
            raise EmbeddingError("Unsupported embedding transport operation")
        if self.cancelled.is_set():
            raise EmbeddingError("Embedding operation was cancelled")
        body = None if payload is None else json.dumps(payload, allow_nan=False, ensure_ascii=False).encode()
        if body is not None and len(body) > MAX_BATCH * (MAX_INPUT_BYTES + 256):
            raise EmbeddingError("Embedding request exceeds its byte limit")
        start = time.monotonic()
        budget = self.timeout if self.deadline is None else min(self.timeout, self.deadline - start)
        if budget <= 0:
            raise EmbeddingError("Embedding operation exceeded its total time budget")
        connection = http.client.HTTPConnection(self.host, self.port, timeout=budget)
        timer = None
        response = None
        owned_socket = None
        try:
            connection.connect()
            owned_socket = connection.sock
            with self.socket_lock:
                if self.cancelled.is_set():
                    raise EmbeddingError("Embedding operation was cancelled")
                self.sockets.add(owned_socket)

            def expire():
                try:
                    owned_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

            def response_factory(sock, *args, **kwargs):
                return http.client.HTTPResponse(_ResponseSocket(sock, self.cancelled, start + budget),
                                                *args, **kwargs)

            connection.response_class = response_factory
            timer = threading.Timer(max(.001, budget - (time.monotonic() - start)), expire)
            timer.daemon = True
            timer.start()
            connection.request("GET" if payload is None else "POST", endpoint, body=body,
                               headers={"Content-Type": "application/json", "Connection": "close"})
            if self.cancelled.is_set():
                raise EmbeddingError("Embedding operation was cancelled")
            response = connection.getresponse()
            if self.cancelled.is_set():
                raise EmbeddingError("Embedding operation was cancelled")
            if response.status != 200:
                # Do not expose server error messages, input, redirects or credentials.
                raise EmbeddingError("Local embedding request refused or unavailable")
            length = response.getheader("Content-Length")
            if length is not None and (not length.isdecimal() or int(length) > MAX_RESPONSE):
                raise EmbeddingError("Embedding response exceeds its byte limit")
            raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE or time.monotonic() - start > budget or self.cancelled.is_set():
                raise EmbeddingError("Embedding response exceeded its size or time budget")
            value = json.loads(raw)
            if type(value) is not dict:
                raise EmbeddingError("Embedding response must be an object")
            if endpoint == "/api/show":
                self.last_show = value
            return value
        except (OSError, ValueError, http.client.HTTPException):
            raise EmbeddingError("Local embedding transport failed or exceeded its budget") from None
        finally:
            if timer:
                timer.cancel()
            if response:
                response.close()
            connection.close()
            if owned_socket is not None:
                with self.socket_lock:
                    self.sockets.discard(owned_socket)

    def identity(self):
        _, metadata = self.cache.get(self)
        if "embedding" not in metadata["capabilities"]:
            raise EmbeddingError("Select an installed local embedding-capable model")
        info = self.last_show.get("model_info", {})
        dimensions = [v for k, v in info.items() if k.endswith(".embedding_length")] if type(info) is dict else []
        if (not dimensions or any(type(v) is not int or not 1 <= v <= MAX_DIMENSIONS for v in dimensions)
                or len(set(dimensions)) != 1):
            raise EmbeddingError("Embedding dimension is unavailable or ambiguous")
        return {"model": metadata["model"], "digest": metadata["digest"],
                "server_version": metadata["server_version"], "dimensions": dimensions[0],
                "query_format": "project-note-instruct-v1"}

    def embed(self, texts, *, query=False):
        if (type(texts) is not list or not 1 <= len(texts) <= MAX_BATCH
                or any(type(t) is not str or not t.strip()
                       or len(t.encode()) > MAX_INPUT_BYTES or "\0" in t for t in texts)):
            raise ValueError("Embedding batch must contain 1-16 bounded nonempty UTF-8 texts")
        if type(query) is not bool:
            raise ValueError("Embedding query mode must be boolean")
        if any(redact(t) != t for t in texts):
            raise Denied("Credentials are not embedding inputs")
        identity = self.identity()
        inputs = [QUERY_INSTRUCTION + t if query else t for t in texts]
        start = time.perf_counter()
        result = self.request("/api/embed", {"model": identity["model"], "input": inputs,
            "truncate": False, "keep_alive": "1m"})
        vectors = result.get("embeddings")
        if (result.get("model") != identity["model"] or type(vectors) is not list
                or len(vectors) != len(texts)):
            raise EmbeddingError("Embedding result has an invalid model or vector count")
        normalized_vectors = [normalized(v, identity["dimensions"]) for v in vectors]
        if self.identity() != identity:
            raise EmbeddingError("Embedding model changed during inference; discard and reindex")
        receipt = {"items": len(texts), "query": query, "wall_seconds": time.perf_counter() - start}
        for field in ("total_duration", "load_duration", "prompt_eval_count"):
            value = result.get(field)
            if type(value) is not int or not 0 <= value <= 10**15:
                raise EmbeddingError("Embedding native counters are missing or invalid")
            receipt[field] = value
        self.receipts.append(receipt)
        self.receipts = self.receipts[-256:]
        return identity, normalized_vectors
