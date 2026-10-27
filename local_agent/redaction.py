"""Bounded credential-pattern treatment shared by complete and streamed text.

This recognizes common textual labels, not arbitrary secrets or screenshot pixels.
Only up to 128 pending characters are retained; credential bodies are discarded.
"""
import re

KEYS = r"password|passwd|api[_-]?key|token|secret"
START = re.compile(r'"(?:' + KEYS + r')|(?:' + KEYS + r')|bearer|-----BEGIN ', re.IGNORECASE)
NEEDS_TREATMENT = re.compile(r'"?(?:' + KEYS + r')"?\s*[=:]|bearer\s|-----BEGIN ', re.IGNORECASE)
PRIVATE = re.compile(r"-----BEGIN [^-]{0,80}PRIVATE KEY-----", re.IGNORECASE)
END_PRIVATE = re.compile(r"-----END [^-]{0,80}PRIVATE KEY-----$", re.IGNORECASE)
LOOKBEHIND = 16
HEADER_LIMIT = 128


class StreamRedactor:
    def __init__(self):
        self.state = "text"
        self.buffer = ""
        self.header = ""
        self.tail = ""
        self.quote = '"'
        self.escaped = False
        self.closed = False
        self.bearer = False

    @property
    def buffered(self):
        return len(self.buffer) + len(self.header) + len(self.tail)

    def feed(self, text):
        if self.closed:
            raise ValueError("Redactor already finished")
        output = []
        for char in text:
            while True:
                if self.state == "text":
                    self.buffer += char
                    match = START.search(self.buffer)
                    if match:
                        output.append(self.buffer[:match.start()])
                        literal = match.group()
                        self.buffer = ""
                        if literal.startswith("-----"):
                            self.header = literal
                            self.state = "header"
                        else:
                            output.append(literal)
                            self.bearer = literal.lower() == "bearer"
                            self.state = ("key_quote" if literal.startswith('"') else
                                          "bearer_space" if literal.lower() == "bearer" else "separator")
                    elif len(self.buffer) > LOOKBEHIND:
                        output.append(self.buffer[:-LOOKBEHIND])
                        self.buffer = self.buffer[-LOOKBEHIND:]
                    break
                if self.state in {"separator", "colon", "bearer_space"}:
                    if char.isspace():
                        output.append(char)
                        if self.state == "bearer_space":
                            self.state = "value"
                        break
                    if self.state != "bearer_space" and char in (":" if self.state == "colon" else "=:"):
                        output.append(char)
                        self.state = "value"
                        break
                    self.state = "text"
                    continue
                if self.state == "key_quote":
                    if char == '"':
                        output.append(char)
                        self.state = "colon"
                        break
                    if char.isspace() or char in "=:":
                        self.state = "separator"  # Quoted prose can contain a plain assignment.
                        continue
                    self.state = "text"
                    continue
                if self.state == "value":
                    if char.isspace():
                        output.append(char)
                        break
                    if char in ",;":
                        self.state = "text"
                        continue
                    if char in "\"'":
                        output.extend((char, "[REDACTED]"))
                        self.quote, self.escaped, self.state = char, False, "quoted"
                        break
                    output.append("[REDACTED]")
                    self.state = "plain"
                    continue
                if self.state == "plain":
                    if char.isspace() or char in ",;" or self.bearer and char in "\"'":
                        self.state = "text"
                        continue
                    break
                if self.state == "quoted":
                    if self.escaped:
                        self.escaped = False
                    elif char == "\\":
                        self.escaped = True
                    elif char == self.quote:
                        output.append(char)
                        self.state = "text"
                    break
                if self.state == "header":
                    self.header += char
                    if self.header.endswith("-----"):
                        private = PRIVATE.fullmatch(self.header)
                        if private:
                            output.append("[REDACTED PRIVATE KEY]")
                        else:
                            # Treat labels inside other headers normally. Retain the
                            # final dashes so an adjacent/nested BEGIN is still detected.
                            output.append(self.header[0] + redact_text(self.header[1:-5]))
                            self.buffer = "-----"
                        self.state = "private" if private else "text"
                        self.header = ""
                    elif len(self.header) >= HEADER_LIMIT:
                        output.append("[REDACTED PRIVATE KEY]")
                        self.header = ""
                        self.state = "private"  # Abnormal incomplete header fails closed.
                    break
                if self.state == "private":
                    self.tail = (self.tail + char)[-HEADER_LIMIT:]
                    if char == "-" and END_PRIVATE.search(self.tail):
                        self.tail, self.state = "", "text"
                    break
        return "".join(output)

    def finish(self):
        self.closed = True
        result = "[REDACTED PRIVATE KEY]" if self.state == "header" else self.buffer
        self.buffer = self.header = self.tail = ""
        return result


def redact_text(text):
    text = str(text)
    if not NEEDS_TREATMENT.search(text):
        return text
    redactor = StreamRedactor()
    return redactor.feed(text) + redactor.finish()
