"""Bounded command pipe capture and the durable output-event contract."""
import codecs
import threading
import time

from .redaction import StreamRedactor

LIMIT = 16_000
MAX_PARTS = 64


class OutputPublisher:
    """One bounded delta stream; callers serialize publish calls for their command."""
    def __init__(self, output, sink, ident, *, max_parts=MAX_PARTS):
        self.output, self.sink, self.ident = output, sink, ident
        self.max_parts = max_parts
        self.sent, self.parts, self.last_emit = 0, 0, 0
        self.failed = False
        self.closed = False

    def publish(self, reason="running", *, final=False, exit_code=None):
        text, truncated = self.output.snapshot()
        if self.closed or self.sink is None or self.failed:
            self.closed |= final
            return
        if not final and self.parts and (self.parts >= self.max_parts - 1
                or time.monotonic() - self.last_emit < .2 or len(text) == self.sent):
            return
        self.parts += 1
        payload = {"command_id": self.ident, "part": self.parts, "text": text[self.sent:], "truncated": truncated,
                   "finished": final, "exit_code": exit_code if final else None,
                   "reason": reason if final else "running"}
        try:
            self.sink(payload)
        except BaseException:
            self.failed = True
            raise
        self.sent, self.last_emit = len(text), time.monotonic()
        self.closed = final


class CommandOutput:
    def __init__(self, *, sanitize=True):
        self.lock = threading.Lock()
        self.data = b""
        self.truncated = False
        self.full = False
        self.failed = False
        self.sanitize = sanitize

    def snapshot(self):
        with self.lock:
            return self.data.decode("utf-8"), self.truncated

    def append(self, text):
        with self.lock:
            if self.full:
                return
            raw = text.encode("utf-8")
            remaining = LIMIT - len(self.data)
            self.data += raw[:remaining].decode("utf-8", "ignore").encode("utf-8")
            self.truncated |= len(raw) > remaining
            self.full = len(raw) > remaining

    def drain(self, pipe):
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        redactor, received = StreamRedactor() if self.sanitize else None, 0
        try:
            while chunk := pipe.read1(4096):
                # Keep draining beyond the raw prefix without retaining data on disk/RAM.
                eligible = chunk[:max(0, LIMIT - received)]
                received += len(chunk)
                if received > LIMIT:
                    with self.lock:
                        self.truncated = True
                if eligible:
                    text = decoder.decode(eligible)
                    self.append(redactor.feed(text) if redactor else text)
        except OSError:
            self.failed = True
        finally:
            text = decoder.decode(b"", final=True)
            self.append(redactor.feed(text) if redactor else text)
            if redactor:
                self.append(redactor.finish())
            pipe.close()


def accept_event(payload, states):
    """Validate before storing a worker frame; state changes only after full validation."""
    fields = {"command_id", "part", "text", "truncated", "finished", "exit_code", "reason", "profile"}
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ValueError("Invalid command output fields")
    ident, part, text = payload["command_id"], payload["part"], payload["text"]
    if (not isinstance(ident, str) or len(ident) != 32 or any(c not in "0123456789abcdef" for c in ident)
            or type(part) is not int or not 1 <= part <= MAX_PARTS or not isinstance(text, str)
            or type(payload["truncated"]) is not bool or type(payload["finished"]) is not bool
            or not isinstance(payload["profile"], str) or not 1 <= len(payload["profile"]) <= 128):
        raise ValueError("Invalid command output identity or types")
    code, finished, reason = payload["exit_code"], payload["finished"], payload["reason"]
    if (not isinstance(reason, str) or reason not in {"running", "completed", "cancelled", "timeout", "output_error", "failed"}
            or finished == (reason == "running") or (not finished and code is not None)
            or code is not None and type(code) is not int or reason == "completed" and code is None):
        raise ValueError("Invalid command output outcome")
    previous, size, closed, profile = states.get(ident, (0, 0, False, payload["profile"]))
    size += len(text.encode("utf-8"))
    if (closed or part != previous + 1 or size > LIMIT or payload["profile"] != profile
            or part == MAX_PARTS and not finished or ident not in states and len(states) >= 256):
        raise ValueError("Command output sequence or budget exceeded")
    states[ident] = (part, size, finished, profile)
