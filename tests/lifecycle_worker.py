"""Spawnable protocol fault fixture; never loads a model or runs external actions."""
import threading
import time


def lifecycle_worker(pipe, config, mode, objective, history, current_message=None):
    if pipe.recv() != "start":
        return
    if objective == "not_ready":
        time.sleep(30)
        return
    lock = threading.Lock()
    stopped = threading.Event()

    def emit(kind, payload):
        with lock:
            pipe.send({"kind": kind, "payload": payload})

    if objective == "malformed":
        pipe.send({"kind": "result", "payload": {"status": "running"}})
        time.sleep(30)
        return
    emit("worker_ready", {})
    if objective == "no_heartbeat":
        time.sleep(30)
        return

    def heartbeat():
        while not stopped.wait(0.05):
            try:
                emit("heartbeat", {})
            except (EOFError, OSError):
                return

    threading.Thread(target=heartbeat, daemon=True).start()
    emit("phase", {"name": "tool"})
    if objective == "continual_progress":
        while True:
            emit("phase", {"name": "execution"})
            time.sleep(0.05)
    elif objective == "delayed_result":
        pipe.recv()
    elif objective == "nested_approvals":
        for ident in ("outer", "inner"):
            emit("approval", {"id": ident, "action": "fixture", "details": {}, "expires": time.time() + 5})
        replies = [pipe.recv(), pipe.recv()]
        if {reply["id"] for reply in replies} != {"outer", "inner"}:
            return
    elif objective == "bad_terminal":
        emit("result", {"status": "planned", "report": "Malformed plan", "plan": {"steps": []}})
        return
    emit("result", {"status": "reported", "report": "Protocol fixture completed"})
    stopped.set()
    pipe.close()
