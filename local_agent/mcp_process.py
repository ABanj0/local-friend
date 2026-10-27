"""Start owned MCP processes suspended on Windows, then assign a Job before running."""
import ctypes
import os
import signal
import subprocess
from ctypes import wintypes

from .process import environment


def resume_owned(proc):
    class ThreadEntry(ctypes.Structure):
        _fields_ = [(name, wintypes.DWORD) for name in
                    ("size", "usage", "tid", "pid", "priority", "delta", "flags")]

    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    api.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    api.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(ThreadEntry)]
    api.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(ThreadEntry)]
    api.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenThread.restype = wintypes.HANDLE
    api.ResumeThread.argtypes = [wintypes.HANDLE]
    api.ResumeThread.restype = wintypes.DWORD
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = api.CreateToolhelp32Snapshot(4, 0)  # TH32CS_SNAPTHREAD
    if snapshot == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = ThreadEntry()
        entry.size = ctypes.sizeof(entry)
        valid = api.Thread32First(snapshot, ctypes.byref(entry))
        while valid:
            if entry.pid == proc.pid:
                thread = api.OpenThread(2, False, entry.tid)  # THREAD_SUSPEND_RESUME
                if not thread:
                    raise ctypes.WinError(ctypes.get_last_error())
                try:
                    if api.ResumeThread(thread) == 0xFFFFFFFF:
                        raise ctypes.WinError(ctypes.get_last_error())
                    return
                finally:
                    api.CloseHandle(thread)
            valid = api.Thread32Next(snapshot, ctypes.byref(entry))
        raise OSError("Owned suspended MCP thread was not found")
    finally:
        api.CloseHandle(snapshot)


def start(argv, cwd):
    proc = subprocess.Popen(argv, cwd=cwd, env=environment(), stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            creationflags=0x08000004 if os.name == "nt" else 0,
                            start_new_session=os.name != "nt")  # NO_WINDOW | SUSPENDED
    job = None
    try:
        if os.name == "nt":
            from .windows_job import WindowsJob
            job = WindowsJob(proc)
            resume_owned(proc)
        return proc, job
    except BaseException:
        finish(proc, job)
        raise


def finish(proc, job):
    try:
        if job:
            job.close()
        elif os.name != "nt":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=3)
        for stream in (proc.stdin, proc.stdout):
            if stream:
                try:
                    stream.close()
                except OSError:
                    pass
