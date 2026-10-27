"""Validated local generation options and bounded, identity-keyed admission metadata."""
import copy
import math
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

PROBE_SCHEMA = {"type": "object", "properties": {"ok": {"const": True}},
                "required": ["ok"], "additionalProperties": False}


@dataclass(frozen=True)
class InferenceOptions:
    context: int = 8192
    temperature: float = 0.1
    max_output: int = 2048
    thinking: bool | str | None = False
    keep_alive: str | int = "5m"

    @classmethod
    def from_config(cls, config):
        values = {key: config[key] for key in cls.__dataclass_fields__ if key in config}
        if values.get("thinking") == "default":
            values["thinking"] = None  # TOML has no null literal.
        selected = cls(**values)
        for key, minimum, maximum in (("context", 2048, 32768), ("max_output", 1, 32768)):
            value = getattr(selected, key)
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"{key} must be an integer from {minimum} to {maximum}")
        if (type(selected.temperature) not in {int, float} or not math.isfinite(selected.temperature)
                or not 0 <= selected.temperature <= 2):
            raise ValueError("temperature must be a finite number from 0 to 2")
        thinking = selected.thinking
        if thinking is not None and type(thinking) is not bool and not (
                isinstance(thinking, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", thinking)):
            raise ValueError("thinking must be a boolean, a supported named level, or null for model default")
        keep = selected.keep_alive
        if type(keep) is int:
            seconds = keep
        elif isinstance(keep, str) and re.fullmatch(r"0|[1-9][0-9]{0,3}[sm]", keep):
            seconds = 0 if keep == "0" else int(keep[:-1]) * (60 if keep.endswith("m") else 1)
        else:
            raise ValueError("keep_alive must be 0 or a duration such as 60s or 5m")
        if not 0 <= seconds <= 3600:
            raise ValueError("keep_alive must be between zero and one hour")
        return selected

    def payload(self):
        return {"think": self.thinking, "keep_alive": self.keep_alive,
                "options": {"num_ctx": self.context, "temperature": self.temperature, "num_predict": self.max_output}}


class InferenceIncomplete(RuntimeError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__("Model output reached its token limit; response is incomplete" if reason == "length"
                         else "Model response has no verified normal finish; response is incomplete")


def supported_thinking(value, values):
    return value is None or any(type(value) is type(item) and value == item for item in values)


class CapabilityCache:
    """No prompt/content persistence; fresh tags/version on every admission, short TTL."""
    def __init__(self, ttl=60, limit=32, clock=time.monotonic):
        self.ttl, self.limit, self.clock = ttl, limit, clock
        self.lock = threading.RLock()
        self.items = OrderedDict()

    def get(self, model):
        response = model.request("/api/tags")
        tags = response.get("models") if isinstance(response, dict) else None
        if not isinstance(tags, list) or len(tags) > 10000:
            raise ValueError("Ollama installed-model metadata is invalid")
        installed = next((item for item in tags if isinstance(item, dict) and item.get("name") == model.config["name"]), None)
        if installed is None:
            raise ValueError("Select an installed local model")
        response = model.request("/api/version")
        version = response.get("version") if isinstance(response, dict) else None
        digest = installed.get("digest")
        if (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][a-zA-Z0-9.-]+)?", version)):
            raise ValueError("Ollama model identity/version metadata is unavailable; update or reconnect Ollama")
        key = (model.config["url"].rstrip("/"), model.config["name"], digest, version)
        if installed.get("remote_model") or installed.get("remote_host"):
            raise ValueError("Cloud or remote models are not permitted; select an installed local model")
        with self.lock:
            now = self.clock()
            for other in list(self.items):
                if now - self.items[other][0] >= self.ttl or other[:2] == key[:2] and other != key:
                    del self.items[other]
            if key not in self.items:
                show = model.request("/api/show", {"model": model.config["name"]})
                if not isinstance(show, dict) or not isinstance(show.get("details"), dict):
                    raise ValueError("Model details are invalid")
                if show.get("remote_model") or show.get("remote_host") or show["details"].get("format") != "gguf":
                    raise ValueError("Model metadata does not establish local GGUF inference; remote models are not permitted")
                capabilities = show.get("capabilities")
                if (not isinstance(capabilities, list) or len(capabilities) > 32
                        or not all(isinstance(item, str) and re.fullmatch(r"[a-z_]{1,32}", item) for item in capabilities)):
                    raise ValueError("Model capability metadata is unavailable")
                controls = show.get("thinking", {})
                if not isinstance(controls, dict):
                    raise ValueError("Model thinking metadata is invalid")
                thinking = controls.get("values", [])
                if (not isinstance(thinking, list) or len(thinking) > 16 or not all(type(v) is bool
                        or isinstance(v, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", v) for v in thinking)):
                    raise ValueError("Model thinking metadata is invalid")
                self.items[key] = (now, {"model": key[1], "digest": digest, "server_version": version,
                    "capabilities": sorted(set(capabilities)), "thinking_values": thinking,
                    "schema_probe": "not_probed", "source": "local_ollama_metadata", "ttl_seconds": self.ttl})
                while len(self.items) > self.limit:
                    self.items.popitem(last=False)
            self.items.move_to_end(key)
            return key, copy.deepcopy(self.items[key][1])

    def schema(self, key, probe):
        with self.lock:
            item = self.items.get(key)
            if item is None:
                raise ValueError("Model capabilities changed; retry admission")
            metadata = item[1]
            if metadata["schema_probe"] == "not_probed":
                # A short structured response is a compatibility check, never a tool grant.
                metadata["schema_probe"] = "passed" if probe() else "failed"
            if metadata["schema_probe"] != "passed":
                raise ValueError("Model failed the bounded structured-output compatibility probe")
            return copy.deepcopy(metadata)


CAPABILITIES = CapabilityCache()
