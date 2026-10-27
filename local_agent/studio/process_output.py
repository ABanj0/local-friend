"""Bounded, redacted in-memory output from a single owned service process."""
import codecs
import os
import subprocess
import threading

from local_agent.redaction import StreamRedactor


class ProcessOutput:
    LIMIT = 8192

    def __init__(self):
        self.lock = threading.RLock()
        self.text = ""
        self.proc = None
        self.job = None
        self.reader = None

    def snapshot(self):
        with self.lock:
            return {"output": self.text, "exit_code": self.proc.poll() if self.proc else None,
                    "owned": self.proc is not None}

    def append(self, text):
        with self.lock:
            self.text = (self.text + text)[-self.LIMIT:]

    def drain(self, pipe):
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        redactor = StreamRedactor()
        try:
            while chunk := pipe.read1(4096):
                self.append(redactor.feed(decoder.decode(chunk)))
            self.append(redactor.feed(decoder.decode(b"", final=True)))
        finally:
            self.append(redactor.finish())
            pipe.close()

    def start(self, argv, env):
        # Caller serializes start/stop; the output lock must stay available to drain.
        if self.proc and self.proc.poll() is None:
            return False
        self.close()
        self.reader = None
        self.append("\nStarting owned service.\n")
        self.proc = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            if os.name == "nt":
                from local_agent.windows_job import WindowsJob
                self.job = WindowsJob(self.proc)
            self.reader = threading.Thread(target=self.drain, args=(self.proc.stdout,), daemon=True)
            self.reader.start()
        except BaseException:
            self.close()
            raise
        return True

    def close(self):
        if self.job:
            self.job.close()
            self.job = None
        if self.proc:
            if self.proc.poll() is None:
                self.proc.terminate()
            try:
                self.proc.wait(3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(3)
            if self.reader and self.reader.ident is not None:
                self.reader.join(3)
                if self.reader.is_alive():
                    raise OSError("Owned service output did not close after process shutdown")
            elif self.proc.stdout:
                self.proc.stdout.close()
