"""Drain authenticated HTTP requests before changing the next-start state selection."""
import threading
import time
from contextlib import contextmanager


class RestoreGate:
    def __init__(self):
        self.condition = threading.Condition()
        self.requests = 0
        self.exclusive = False
        self.pending = False

    def enter(self):
        with self.condition:
            if self.exclusive or self.pending:
                return False
            self.requests += 1
            return True

    def leave(self):
        with self.condition:
            self.requests -= 1
            self.condition.notify_all()

    @contextmanager
    def freeze(self, timeout=15):
        deadline = time.monotonic() + timeout
        with self.condition:
            if self.exclusive or self.pending:
                raise ValueError('Restore is already in progress; restart the backend if required')
            self.exclusive = True
            self.condition.notify_all()
        try:
            with self.condition:
                # The activation request itself is the one admitted request remaining.
                while self.requests > 1:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError('Wait for pending requests to finish before restoring')
                    self.condition.wait(remaining)
            yield
        finally:
            with self.condition:
                self.exclusive = False
                self.condition.notify_all()

    def require_restart(self):
        with self.condition:
            self.pending = True
