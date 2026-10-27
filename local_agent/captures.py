"""Owned transient PNGs with a durable registry and process-lifetime lease.

No directory sweep or legacy filename pattern can authorize deletion. Recovery only
removes recorded file identities after acquiring the abandoned run's lease.
"""
import os
import re
import sqlite3
import stat
import uuid
from contextlib import contextmanager
from pathlib import Path

from .safety import Denied

MAX_CAPTURE = 8_000_000
IDENT = re.compile(r"[0-9a-f]{32}")


def identity(info):
    return str(info.st_dev), str(info.st_ino)


def lock(stream):
    stream.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)


class Captures:
    def registry(self, state):
        self.state = Path(state).resolve()
        self.root = self.state / "captures"
        self.check(self.root)
        self.root.mkdir(exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, dev TEXT, ino TEXT);
                CREATE TABLE IF NOT EXISTS files (run TEXT REFERENCES runs(id) ON DELETE CASCADE,
                    name TEXT, dev TEXT, ino TEXT, PRIMARY KEY(run,name));
            """)

    def check(self, path):
        if not path.is_relative_to(self.state):
            raise Denied("Capture path is outside the state directory")
        current = self.state
        for part in ("", *path.relative_to(self.state).parts):
            current /= part
            try:
                info = current.lstat()
            except FileNotFoundError:
                continue
            if (stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400
                    or stat.S_ISREG(info.st_mode) and info.st_nlink != 1):
                raise Denied("Capture paths cannot contain links or reparse points")

    @contextmanager
    def connection(self):
        path = self.root / "index.sqlite3"
        self.check(path)
        db = sqlite3.connect(path, timeout=0.2)
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def __init__(self, state, run=None):
        self.registry(state)
        self.closed = False
        self.owner = run is None
        self.run = run or uuid.uuid4().hex
        if not isinstance(self.run, str) or not IDENT.fullmatch(self.run):
            raise Denied("Invalid capture run")
        self.path = self.root / self.run
        self.check(self.path)
        if self.owner:
            self.path.mkdir()
            self.lease = (self.path / "lease").open("x+b")
            try:
                self.lease.write(b"1")
                self.lease.flush()
                lock(self.lease)
                self.lease_id = identity(os.fstat(self.lease.fileno()))
                with self.connection() as db:
                    db.execute("INSERT INTO runs VALUES (?,?,?)", (self.run, *self.lease_id))
            except BaseException:
                self.lease.close()
                (self.path / "lease").unlink()
                self.path.rmdir()
                raise
        else:
            self.check(self.path / "lease")
            with self.connection() as db:
                row = db.execute("SELECT dev,ino FROM runs WHERE id=?", (self.run,)).fetchone()
            if row is None or tuple(row) != identity((self.path / "lease").lstat()):
                raise Denied("Unknown capture owner")

    def write(self, data):
        if self.closed or not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) > MAX_CAPTURE:
            raise ValueError("Capture must be a PNG no larger than 8,000,000 bytes")
        name = uuid.uuid4().hex + ".png"
        path = self.path / name
        self.check(path)
        with path.open("xb") as output:
            # Record identity before pixels: an interrupted write is still safely owned.
            expected = identity(os.fstat(output.fileno()))
            try:
                with self.connection() as db:
                    db.execute("INSERT INTO files VALUES (?,?,?,?)", (self.run, name, *expected))
            except BaseException:
                output.close()
                if identity(path.lstat()) == expected:
                    path.unlink()  # Compensate only the empty file this call created.
                raise
            output.write(data)
        return str(path)

    def file(self, path):
        path = Path(path)
        if path.parent != self.path or path.suffix != ".png" or not IDENT.fullmatch(path.stem):
            raise Denied("Image is not an owned capture")
        self.check(path)
        with self.connection() as db:
            row = db.execute("SELECT dev,ino FROM files WHERE run=? AND name=?",
                             (self.run, path.name)).fetchone()
        if row is None:
            raise Denied("Image is not a registered capture")
        if path.exists() and tuple(row) != identity(path.lstat()):
            raise Denied("Capture identity changed; refusing to read or delete it")
        return path, tuple(row)

    def read(self, path):
        path, expected = self.file(path)
        with path.open("rb") as source:
            if identity(os.fstat(source.fileno())) != expected:
                raise Denied("Capture identity changed")
            data = source.read(MAX_CAPTURE + 1)
        self.file(path)
        if len(data) > MAX_CAPTURE:
            raise ValueError("Capture exceeds the byte budget")
        return data

    def remove(self, path):
        path, _ = self.file(path)
        path.unlink(missing_ok=True)
        with self.connection() as db:
            db.execute("DELETE FROM files WHERE run=? AND name=?", (self.run, path.name))

    def consume(self, path):
        try:
            return self.read(path)
        finally:
            self.remove(path)

    def close(self):
        if self.closed:
            return
        with self.connection() as db:
            names = [row[0] for row in db.execute("SELECT name FROM files WHERE run=?", (self.run,))]
        for name in names:
            self.remove(self.path / name)
        if self.owner:
            lease_path = self.path / "lease"
            self.check(lease_path)
            if lease_path.exists() and identity(lease_path.lstat()) != self.lease_id:
                raise Denied("Capture lease identity changed")
            self.lease.close()
            lease_path.unlink(missing_ok=True)
            if self.path.exists():
                self.path.rmdir()  # Never recursively remove unexpected files.
            with self.connection() as db:
                db.execute("DELETE FROM runs WHERE id=?", (self.run,))
        self.closed = True

    @classmethod
    def recover(cls, state):
        registry = cls.__new__(cls)
        registry.registry(state)
        with registry.connection() as db:
            rows = list(db.execute("SELECT id,dev,ino FROM runs"))
        errors = []
        for run, dev, ino in rows:
            try:
                if not isinstance(run, str) or not IDENT.fullmatch(run):
                    raise Denied("Invalid capture registry record")
                item = cls.__new__(cls)
                item.state, item.root = registry.state, registry.root
                item.run, item.path = run, registry.root / run
                item.owner, item.closed, item.lease_id = True, False, (dev, ino)
                item.check(item.path / "lease")
                if not item.path.exists():
                    with item.connection() as db:
                        db.execute("DELETE FROM runs WHERE id=?", (run,))
                    continue
                if not (item.path / "lease").exists():
                    item.path.rmdir()  # Only an empty, recorded directory is removable.
                    with item.connection() as db:
                        db.execute("DELETE FROM runs WHERE id=?", (run,))
                    continue
                item.lease = (item.path / "lease").open("r+b")
                try:
                    try:
                        lock(item.lease)
                    except (PermissionError, BlockingIOError):
                        continue  # Another process still owns this run; never stop it.
                    item.close()
                finally:
                    item.lease.close()
            except (OSError, sqlite3.Error, Denied):
                errors.append(run)
        return errors
