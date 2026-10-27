"""Explicit Ollama metadata/schema-probe protocol responses, never real-model evidence."""
import json

from local_agent.inference import PROBE_SCHEMA


def metadata_response(path, payload=None, *, name="fixture", digest="a" * 64):
    if path == "/api/version":
        return {"version": "0.40.7"}
    if path == "/api/tags":
        return {"models": [{"name": name, "digest": digest, "details": {"format": "gguf"}}]}
    if path == "/api/ps":
        return {"models": []}
    if path == "/api/show":
        return {"capabilities": ["completion", "tools", "vision", "thinking"],
                "thinking": {"values": [False, True], "default": True}, "details": {"format": "gguf"}}
    if payload and payload.get("format") == PROBE_SCHEMA:
        return {"message": {"role": "assistant", "content": '{"ok":true}'}, "done": True, "done_reason": "stop"}
    return None


def serve_metadata(handler, payload=None, **kwargs):
    response = metadata_response(handler.path, payload, **kwargs)
    if response is None:
        return False
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.end_headers()
    handler.wfile.write(json.dumps(response).encode())
    return True
