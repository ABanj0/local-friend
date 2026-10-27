import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    submissions = 0

    def log_message(self, *_):
        pass

    def do_GET(self):
        if self.path == "/download":
            self.send_response(200)
            self.send_header("Content-Disposition", 'attachment; filename="sample.txt"')
            body = b"local fixture download\n"
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            body = (b'<title>Agent fixture</title><h1>Local Agent Test</h1>'
                    b'<a id="next" href="/second">Second page</a>'
                    b'<a id="download" href="/download">Download</a>'
                    b'<form method="POST" action="/submit"><label>Name <input id="name" name="name"></label>'
                    b'<button id="submit" type="submit">Submit</button></form>')
            if self.path == "/second":
                body += b"<p id='result'>Second page verified</p>"
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        type(self).submissions += 1
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"submitted")


class FixtureSite:
    def __enter__(self):
        Handler.submissions = 0
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
