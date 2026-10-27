"""Explicit, transactional derived vectors for already saved, approved project notes.

No file ingestion, automatic saving, prompt injection or inference under Manager.lock.
"""
import hashlib
import json
import math
import re
import struct
import threading
import time
import uuid
from contextlib import contextmanager

from local_agent.embeddings import MAX_BATCH, EmbeddingError, Embeddings, normalized
from local_agent.retrieval import hybrid_rank, semantic_rank
from local_agent.safety import Denied
from local_agent.studio.memory import MAX_NOTES, validate_text
from local_agent.studio.memory_sources import UNSET, notes


def identity(value):
    if (type(value) is not dict
            or set(value) != {"model", "digest", "server_version", "dimensions", "query_format"}
            or type(value["model"]) is not str
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/:-]{0,199}", value["model"])
            or type(value["digest"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", value["digest"])
            or type(value["server_version"]) is not str
            or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][a-zA-Z0-9.-]+)?", value["server_version"])
            or type(value["dimensions"]) is not int or not 1 <= value["dimensions"] <= 4096
            or value["query_format"] != "project-note-instruct-v1"):
        raise ValueError("Memory index identity is invalid; reindex saved notes")
    return dict(value)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class MemoryIndex:
    def __init__(self, manager):
        self.manager = manager
        self.store = manager.store
        self.lease = threading.Lock()
        self.abort = threading.Event()
        self.active_client = None

    def cancel(self):
        """Called under the host lock; discard pending work and close only its HTTP client."""
        self.abort.set()
        if self.active_client is not None and callable(getattr(self.active_client, 'close', None)):
            self.active_client.close()

    @property
    def busy(self):
        return self.lease.locked()

    @contextmanager
    def operation(self):
        with self.manager.lock:
            self.guard()
            if not self.lease.acquire(blocking=False):
                raise ValueError("A memory embedding operation is already active")
            self.abort.clear()
        try:
            yield
        finally:
            with self.manager.lock:
                try:
                    self.cancel()
                finally:
                    self.active_client = None
                    self.lease.release()

    def guard(self, *, idle=True):
        if self.manager.shutdown_requested.is_set() or self.manager.restore_pending.is_set():
            raise Denied("Memory index is unavailable during shutdown or restore")
        if idle:
            self.manager.memory._idle()

    def snapshot(self, db, project, forbidden=(), *, idle=True, sources=UNSET, local_status=False):
        self.guard(idle=idle)
        scope = self.manager.memory.scope(project)
        if not local_status:
            self.manager.memory_sources.validate(db, project, sources)
        sizes = db.execute("SELECT length(text),length(CAST(text AS BLOB)) FROM memories WHERE scope=? LIMIT ?",
                           (scope, MAX_NOTES + 1)).fetchall()
        if len(sizes) > MAX_NOTES or any(r[0] > 4000 or r[1] > 8192 for r in sizes):
            raise ValueError("Saved notes exceed index input limits")
        rows = sorted(notes(db, scope), key=lambda r: r['id'])
        if len(rows) > MAX_NOTES:
            raise ValueError("Memory scope exceeds index capacity")
        for row in rows:
            validate_text(row["text"], forbidden)
            if digest(row["text"].encode()) != row["sha256"]:
                raise ValueError("Saved note hash changed; reconcile its source before indexing")
        epoch = db.execute("SELECT epoch FROM memory_domains WHERE scope=?", (scope,)).fetchone()
        manifest = digest(json.dumps([(r["id"], r["sha256"]) for r in rows], separators=(",", ":")).encode())
        return {"scope": scope, "rows": rows, "manifest": manifest, "epoch": epoch[0] if epoch else 0,
                "admission": self.manager.admission_epoch, "store": self.store.identity, 'sources': sources}

    def unchanged(self, db, project, saved, forbidden=()):
        current = self.snapshot(db, project, forbidden, sources=saved['sources'])
        if any(current[k] != saved[k] for k in ("scope", "manifest", "epoch", "admission", "store")):
            raise Denied("Project memory changed during inference; review and retry")
        return current

    @staticmethod
    def index(db, scope):
        size = db.execute("SELECT length(identity) FROM memory_indexes WHERE scope=?", (scope,)).fetchone()
        if size is not None and not 1 <= size[0] <= 2048:
            raise ValueError("Memory index metadata is invalid; reindex")
        row = db.execute("SELECT * FROM memory_indexes WHERE scope=?", (scope,)).fetchone()
        if row is None:
            raise ValueError("Project notes are not indexed; explicitly reindex first")
        row = dict(row)
        if type(row["identity"]) is not str or len(row["identity"]) > 2048:
            raise ValueError("Memory index metadata is invalid; reindex")
        row["identity"] = identity(json.loads(row["identity"]))
        if (type(row["generation"]) is not str or not re.fullmatch(r"[0-9a-f]{32}", row["generation"])
                or type(row["manifest"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", row["manifest"])
                or type(row["epoch"]) is not int or row["epoch"] < 0):
            raise ValueError("Memory index version metadata is invalid; reindex")
        return row

    @staticmethod
    def require_current(saved, index):
        if saved["manifest"] != index["manifest"] or saved["epoch"] != index["epoch"]:
            raise ValueError("Saved notes changed; explicitly reindex before semantic search")

    @staticmethod
    def enabled(db, scope):
        row = db.execute("SELECT value FROM metadata WHERE key=?", ('semantic_memory:' + scope,)).fetchone()
        index = db.execute("SELECT generation FROM memory_indexes WHERE scope=?", (scope,)).fetchone()
        return bool(row and index and row[0] == index[0])

    def set_enabled(self, project, enabled, *, confirmed=False):
        if type(enabled) is not bool or type(confirmed) is not bool:
            raise ValueError("Memory retrieval settings must be boolean")
        if enabled and confirmed is not True:
            raise Denied("Confirm using indexed project notes in future model tasks")
        with self.operation():
            sources = self.manager.memory_sources.prepare(project)
            with self.manager.lock, self.store.connection() as db:
                saved = self.snapshot(db, project, sources=sources)
                index = self.index(db, saved['scope']) if enabled else None
                if enabled:
                    self.require_current(saved, index)
            if enabled:
                client = self.client(index['identity']['model'], 15)
                try:
                    observed = identity(client.identity())
                except EmbeddingError:
                    if self.abort.is_set():
                        raise Denied('Memory retrieval change was cancelled') from None
                    raise ValueError('Local embedding model is unavailable; retrieval setting was preserved') from None
                if observed != index['identity']:
                    raise ValueError('Embedding model changed; reindex before enabling retrieval')
            self.manager.memory_sources.prepare(project)
            with self.manager.lock, self.store.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                self.unchanged(db, project, saved)
                if enabled and self.index(db, saved['scope'])['generation'] != index['generation']:
                    raise Denied('Memory index changed; review before enabling retrieval')
                db.execute('INSERT INTO metadata(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                           ('semantic_memory:' + saved['scope'], index['generation'] if enabled else 'disabled'))
        return {'automatic_retrieval': enabled}

    def status(self, project):
        with self.manager.lock, self.store.connection() as db:
            saved = self.snapshot(db, project, idle=False, local_status=True)
            automatic = self.enabled(db, saved['scope'])
            count = db.execute("SELECT count(*) FROM memory_vectors WHERE scope=?", (saved["scope"],)).fetchone()[0]
            try:
                index = self.index(db, saved["scope"])
            except ValueError:
                return {"state": "not_indexed", "notes": len(saved["rows"]), "vectors": count,
                        "model": None, "model_check": "not_checked", "automatic_retrieval": automatic}
            state = "locally_current" if (saved["manifest"] == index["manifest"]
                    and saved["epoch"] == index["epoch"] and count == len(saved["rows"])) else "reindex_required"
            return {"state": state, "notes": len(saved["rows"]), "vectors": count,
                    "model": index["identity"]["model"], "dimensions": index["identity"]["dimensions"],
                    "model_check": "not_checked", "automatic_retrieval": automatic}

    def client(self, model, seconds):
        if any(secret and secret in model for secret in getattr(self, 'forbidden', ())):
            raise Denied('Session credentials cannot be embedding model names')
        client = Embeddings(dict(self.manager.config["model"], name=model))
        client.deadline = time.monotonic() + seconds
        with self.manager.lock:
            if self.abort.is_set():
                if callable(getattr(client, 'close', None)):
                    client.close()
                raise Denied("Memory embedding operation was interrupted")
            self.active_client = client
        return client

    def reindex(self, project, model, *, confirmed=False, forbidden=()):
        with self.operation():
            return self._reindex(project, model, confirmed=confirmed, forbidden=forbidden)

    def _reindex(self, project, model, *, confirmed=False, forbidden=()):
        if confirmed is not True:
            raise Denied("Confirm embedding the explicitly saved project notes")
        if (type(model) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/:-]{0,199}", model)
                or any(secret and secret in model for secret in forbidden)):
            raise ValueError("Select an installed local embedding model")
        sources = self.manager.memory_sources.prepare(project)
        with self.manager.lock, self.store.connection() as db:
            saved = self.snapshot(db, project, forbidden, sources=sources)
            if not saved["rows"]:
                raise ValueError("Save project notes before indexing")
            previous = db.execute("SELECT generation FROM memory_indexes WHERE scope=?", (saved["scope"],)).fetchone()
            generation = previous[0] if previous else None
        client = self.client(model, 120)
        vectors = []
        try:
            observed = identity(client.identity())
            for offset in range(0, len(saved["rows"]), MAX_BATCH):
                with self.manager.lock:
                    self.guard()
                    if self.manager.admission_epoch != saved["admission"]:
                        raise Denied("Memory indexing was interrupted")
                batch = saved["rows"][offset:offset + MAX_BATCH]
                current, values = client.embed([r["text"] for r in batch])
                if identity(current) != observed or len(values) != len(batch):
                    raise ValueError("Embedding identity changed; discard and reindex")
                for row, vector in zip(batch, values, strict=True):
                    checked = normalized(vector, observed["dimensions"])
                    raw = struct.pack(f"<{len(checked)}f", *checked)
                    vectors.append((saved["scope"], row["id"], row["sha256"], raw, digest(raw)))
            if identity(client.identity()) != observed:
                raise ValueError("Embedding identity changed; discard and reindex")
        except EmbeddingError:
            if self.abort.is_set():
                raise Denied('Memory embedding operation was cancelled') from None
            raise ValueError("Local embedding failed; existing index was preserved") from None
        self.manager.memory_sources.prepare(project)
        with self.manager.lock, self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.unchanged(db, project, saved, forbidden)
            previous = db.execute("SELECT generation FROM memory_indexes WHERE scope=?", (saved["scope"],)).fetchone()
            if (previous[0] if previous else None) != generation:
                raise Denied("Another index was published; review before reindexing")
            db.execute("DELETE FROM memory_indexes WHERE scope=?", (saved["scope"],))
            db.execute("INSERT INTO memory_indexes VALUES (?,?,?,?,?,?)", (
                saved["scope"], json.dumps(observed, sort_keys=True), saved["manifest"], saved["epoch"],
                uuid.uuid4().hex, time.time()))
            db.executemany("INSERT INTO memory_vectors VALUES (?,?,?,?,?)", vectors)
        return {"indexed": len(vectors), "identity": observed, "automatic_retrieval": False}

    def search(self, project, query, *, forbidden=()):
        with self.operation():
            return self._search(project, query, forbidden=forbidden)

    def _search(self, project, query, *, forbidden=(), with_snapshot=False, sources=UNSET):
        if type(query) is not str or not query.strip() or len(query) > 500:
            raise ValueError("Semantic query must contain 1-500 characters")
        validate_text(query, forbidden)
        if sources is UNSET:
            sources = self.manager.memory_sources.prepare(project)
        with self.manager.lock, self.store.connection() as db:
            saved = self.snapshot(db, project, forbidden, sources=sources)
            index = self.index(db, saved["scope"])
            self.require_current(saved, index)
            dimension = index["identity"]["dimensions"]
            stored = db.execute("SELECT memory,source_sha256,vector_sha256,length(vector) FROM memory_vectors "
                                "WHERE scope=? LIMIT ?", (saved["scope"], MAX_NOTES + 1)).fetchall()
            expected = {r["id"]: r["sha256"] for r in saved["rows"]}
            if (len(stored) != len(expected) or any(r[0] not in expected or r[1] != expected[r[0]]
                    or r[3] != dimension * 4 for r in stored)):
                raise ValueError("Memory vectors are stale or malformed; reindex")
            vectors = {}
            for row in db.execute("SELECT memory,vector,vector_sha256 FROM memory_vectors WHERE scope=?", (saved["scope"],)):
                raw = row["vector"]
                if type(raw) is not bytes or digest(raw) != row["vector_sha256"]:
                    raise ValueError("Memory vector integrity failed; reindex")
                value = list(struct.unpack(f"<{dimension}f", raw))
                checked = normalized(value, dimension)
                if not math.isclose(sum(v * v for v in value), 1., abs_tol=1e-4):
                    raise ValueError("Memory vector normalization failed; reindex")
                vectors[row["memory"]] = checked
        client = self.client(index["identity"]["model"], 30)
        try:
            # Refuse stale model identity before sending the query text.
            if identity(client.identity()) != index["identity"]:
                raise ValueError("Embedding model changed; explicitly reindex before search")
            observed, query_vectors = client.embed([query], query=True)
            if identity(observed) != index["identity"] or len(query_vectors) != 1:
                raise ValueError("Embedding model changed; discard search and reindex")
            query_vector = normalized(query_vectors[0], dimension)
        except EmbeddingError:
            if self.abort.is_set():
                raise Denied('Memory embedding operation was cancelled') from None
            raise ValueError("Local embedding query failed; no semantic results available") from None
        self.manager.memory_sources.prepare(project)
        with self.manager.lock, self.store.connection() as db:
            self.unchanged(db, project, saved, forbidden)
            if self.index(db, saved["scope"])["generation"] != index["generation"]:
                raise Denied("Memory index changed during inference; review and retry")
            semantic = semantic_rank(saved["scope"], saved["rows"], vectors, query_vector)
            lexical = [r["id"] for r in self.manager.memory.search(project, query, sources=sources)]
            by_id = {r["id"]: r for r in saved["rows"]}
            rows = [by_id[ident] for ident in hybrid_rank(lexical, semantic)]
            return (rows, saved, index) if with_snapshot else rows
