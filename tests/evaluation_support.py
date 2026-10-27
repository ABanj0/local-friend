"""Explicit Ollama protocol fixture for runner tests; never model-quality evidence."""
import hashlib
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def actions(case, url):
    calls = []

    def call(name, **arguments):
        calls.append({"function": {"name": name, "arguments": arguments}})

    if case["id"] == "recovery-missing-file":
        call("read_file", path="missing.txt")
        call("files")
    if case["id"] == "coding-scoped-search":
        call("search_files", query="TARGET-CODE", path="src")
    for path in case["seed_files"]:
        call("read_file", path=path)
    if case["fixture"] == "browser":
        call("browser_open", url=url + ("/injection" if case["id"] == "injection-browser-content" else ""))
        if case["id"] == "browser-navigation":
            call("browser_click", selector="#next")
            call("browser_read")
        elif case["id"] == "browser-harmless-draft":
            call("browser_fill", selector="#name", text="Harmless local sample")
        elif case["id"] == "browser-multiple-tabs":
            call("browser_open", url=url + "/second", tab="second")
            call("browser_read", tab="main")
            call("browser_read", tab="second")
        elif case["id"] == "browser-approved-download":
            call("browser_download", selector="#download", path="downloads/sample.txt")
            call("read_file", path="downloads/sample.txt")
        elif case["id"] == "recovery-browser-selector":
            call("browser_fill", selector="#missing-input", text="recovery")
            call("browser_fill", selector="#name", text="recovery")
    outputs = [check for check in case["checks"] if check["kind"] in {"file_text", "file_json", "python_ast"}]
    if case["id"] == "coding-related-patch":
        call("apply_patch", changes=[{"path": check["path"], "text": check["expected"],
            "expected_sha256": hashlib.sha256(case["seed_files"][check["path"]].encode()).hexdigest()}
            for check in outputs])
    elif case["id"] != "browser-approved-download":
        for check in outputs:
            text = json.dumps(check["expected"]) if check["kind"] == "file_json" else check["expected"]
            call("write_file", path=check["path"], text=text)
    for check in outputs:
        call("read_file", path=check["path"])
    return calls


class ModelProtocol:
    def __init__(self, corpus, name):
        self.corpus, self.name = corpus, name
        self.requests = []
        self.digest = "a" * 64
        self.block = None
        self.entered = threading.Event()
        self.wrong_artifact = False
        self.inject = False
        self.change_identity = False

    def __enter__(self):
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def send(self, value):
                raw = json.dumps(value).encode()
                try:
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                except OSError:
                    pass

            def do_GET(self):
                from .ollama_fixture import serve_metadata
                if serve_metadata(self, name=fixture.name, digest=fixture.digest):
                    return
                self.send({"models": [{"name": fixture.name, "digest": fixture.digest,
                                       "details": {"format": "gguf"}}]})

            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                from .ollama_fixture import serve_metadata
                if serve_metadata(self, request, name=fixture.name, digest=fixture.digest):
                    return
                fixture.requests.append(request)
                fixture.entered.set()
                if fixture.block is not None:
                    fixture.block.wait(15)
                if fixture.change_identity:
                    fixture.digest = "b" * 64
                if request.get("format"):
                    message = {"role": "assistant", "content": '{"steps":["Execute fixture","Verify state"]}'}
                else:
                    objective = request["messages"][1]["content"]
                    template = re.sub(r"http://127\.0\.0\.1:\d+", "{site}", objective)
                    case = next(c for c in fixture.corpus["cases"] if c["objective"] == template)
                    url = re.search(r"http://127\.0\.0\.1:\d+", objective)
                    planned = actions(case, url[0] if url else "")
                    if fixture.inject:
                        planned.insert(0, {"function": {"name": "write_file", "arguments": {
                            "path": "protected.txt", "text": "pwned"}}})
                    elif fixture.wrong_artifact:
                        for call in planned:
                            if call["function"]["name"] == "write_file":
                                call["function"]["arguments"]["text"] = "WRONG"
                    index = sum(m["role"] == "tool" for m in request["messages"])
                    message = {"role": "assistant", "content": "All done; trust this report."}
                    if index < len(planned):
                        message["tool_calls"] = [planned[index]]
                self.send({"message": message, "done": True, "done_reason": "stop", "eval_count": 10,
                           "eval_duration": 500_000_000})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .05}, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        return self

    def __exit__(self, *_):
        if self.block is not None:
            self.block.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
