"""Repeatable local inference microbenchmarks; never execute model-generated tools/code."""
import argparse
import json
import shutil
import sqlite3
import statistics
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request

from .config import load
from .model import Ollama
from .studio.state_owner import database_path


def ensure_idle(config):
    database = database_path(config)
    if database.exists():
        db = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
        try:
            active = db.execute("SELECT count(*) FROM tasks WHERE status IN ('running','waiting')").fetchone()[0]
        finally:
            db.close()
        if active:
            raise RuntimeError("Studio has an active task. Finish/cancel it before benchmarking.")


def gpu_snapshot():
    executable = shutil.which("nvidia-smi")
    if not executable:
        return None
    try:
        result = subprocess.run([executable, "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                                 "--format=csv,noheader,nounits"], capture_output=True, text=True,
                                timeout=5, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def cases(long_context=False):
    result = [
        ("throughput", {"messages": [{"role": "user", "content":
            "Explain how to implement and test a Python counter with increment, decrement, and reset. "
            "Write a detailed explanation of at least 400 words; do not use tools."}]}, None),
        ("counter_reasoning", {"messages": [{"role": "user", "content":
            "Counter starts at 0. Increment adds 1, decrement subtracts 1, reset sets 0. "
            "Return JSON values for the initial value, after increment, after another increment, "
            "after decrement, and after reset, in that order."}],
            "format": {"type": "object", "properties": {"values": {"type": "array", "items": {"type": "integer"}}},
                       "required": ["values"], "additionalProperties": False}}, {"values": [0, 1, 2, 1, 0]}),
        ("tool_contract", {"messages": [{"role": "user", "content":
            "Use command to run the configured test profile in counter-demo. Call the tool; do not describe it."}],
            "tools": [{"type": "function", "function": {"name": "command",
                "description": "Run an approved command profile in a workspace-relative directory.",
                "parameters": {"type": "object", "properties": {
                    "name": {"type": "string", "enum": ["test", "lint", "build"]},
                    "cwd": {"type": "string"}}, "required": ["name", "cwd"], "additionalProperties": False}}}]},
         {"name": "command", "arguments": {"name": "test", "cwd": "counter-demo"}}),
    ]
    if long_context:
        records = [f"Record {i:03d}: reference code ITEM-{i * 7919 + 101:07d}; category ordinary; status archived."
                   for i in range(300)]
        expected = {str(i): f"ITEM-{i * 7919 + 101:07d}" for i in (0, 149, 299)}
        result.append(("long_context_retrieval", {
            "messages": [{"role": "user", "content": "Read these records:\n" + "\n".join(records) +
                '\nReturn only JSON mapping keys "0", "149", "299" to their exact reference codes.'}],
            "format": {"type": "object", "properties": {key: {"type": "string"} for key in expected},
                       "required": list(expected), "additionalProperties": False}}, expected))
    return result


def measure(model, case, context, seed, temperature):
    name, fields, expected = case
    payload = {"model": model.config["name"], "think": False, "stream": name == "throughput",
               "keep_alive": "5m", "options": {"num_ctx": context, "num_predict": 192,
                   "temperature": temperature, "seed": seed}, **fields}
    start = time.monotonic()
    first = None
    if payload["stream"]:
        request = Request(model.config["url"] + "/api/chat", data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"})
        final = None
        with model.opener.open(request, timeout=model.config["timeout"]) as response:
            for line in response:
                chunk = json.loads(line)
                if chunk.get("error"):
                    raise RuntimeError(chunk["error"])
                if first is None and chunk.get("message", {}).get("content"):
                    first = time.monotonic() - start
                if chunk.get("done"):
                    final = chunk
                    break
        if final is None:
            raise RuntimeError("Incomplete streamed response")
        passed = None  # Throughput text is not an objectively scored quality test.
    else:
        final = model.request("/api/chat", payload)
        message = final.get("message", {})
        if name in {"counter_reasoning", "long_context_retrieval"}:
            try:
                passed = json.loads(message.get("content", "")) == expected
            except ValueError:
                passed = False
        else:
            calls = message.get("tool_calls", [])
            passed = len(calls) == 1 and calls[0].get("function", {}).get("name") == expected["name"] and calls[0]["function"].get("arguments") == expected["arguments"]
    elapsed = time.monotonic() - start
    count, duration = final.get("eval_count"), final.get("eval_duration")
    return {"case": name, "context": context, "seed": seed, "temperature": temperature,
            "passed": passed, "elapsed_seconds": elapsed, "first_token_seconds": first,
            "tokens_per_second": count * 1e9 / duration if count is not None and duration else None,
            **{key: final.get(key) for key in ("eval_count", "eval_duration", "prompt_eval_count",
                "prompt_eval_duration", "prompt_eval_cached_count", "load_duration", "total_duration", "done_reason")}}


def summarize(rows):
    result = []
    for context in sorted({r["context"] for r in rows}):
        group = [r for r in rows if r["context"] == context]
        throughput = [r for r in group if r["case"] == "throughput"]
        scored = [r for r in group if r["passed"] is not None]
        result.append({"context": context,
                       "median_tokens_per_second": statistics.median(r["tokens_per_second"] for r in throughput),
                       "median_first_token_seconds": statistics.median(r["first_token_seconds"] for r in throughput),
                       "median_elapsed_seconds": statistics.median(r["elapsed_seconds"] for r in throughput),
                       "passed": sum(r["passed"] for r in scored), "scored": len(scored)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contexts", nargs="+", type=int, default=[32768, 8192, 4096])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--long-context", action="store_true", help="Also score retrieval from 300 synthetic records")
    args = parser.parse_args()
    if args.repeats < 1 or any(c < 2048 or c > 32768 for c in args.contexts):
        parser.error("Use repeats >= 1 and contexts between 2048 and 32768")
    if not 0 <= args.temperature <= 2:
        parser.error("Temperature must be between 0 and 2")
    if args.long_context and min(args.contexts) < 8192:
        parser.error("The long-context case requires contexts of at least 8192")
    config = load()
    ensure_idle(config)
    model = Ollama(config["model"])
    report = {"date": datetime.now(UTC).isoformat(), "model": config["model"]["name"],
              "version": model.request("/api/version"), "initial_loaded": model.request("/api/ps"),
              "gpu_before": gpu_snapshot(), "rows": [],
              "limits": "Synthetic microbenchmark; no generated code/tool execution, browser or vision evaluation. "
                        "Optional long-context retrieval covers 300 synthetic records, not full-window repository understanding. "
                        "Warmups excluded. Changing context can reload the model. GPU snapshots are not peak measurements."}
    destination = Path(config["paths"]["workspace"]) / "benchmarks" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination.mkdir(parents=True, exist_ok=False)
    output = destination / "results.json"
    try:
        for repeat in range(args.repeats):
            order = args.contexts if repeat % 2 == 0 else list(reversed(args.contexts))
            for context in order:
                ensure_idle(config)
                model.request("/api/chat", {"model": config["model"]["name"], "stream": False, "think": False,
                    "messages": [{"role": "user", "content": "Reply OK."}],
                    "options": {"num_ctx": context, "num_predict": 8, "temperature": args.temperature}})
                for case in cases(args.long_context):
                    ensure_idle(config)
                    row = measure(model, case, context, 731 + repeat, args.temperature)
                    row["loaded"] = model.request("/api/ps").get("models", [])
                    report["rows"].append(row)
                    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
                    print(json.dumps({k: row[k] for k in ("case", "context", "passed", "tokens_per_second", "first_token_seconds")}), flush=True)
        report["summary"] = summarize(report["rows"])
    finally:
        original = next((item for item in report["initial_loaded"].get("models", [])
                         if item.get("name") == config["model"]["name"]), None)
        if original and original.get("context_length"):
            try:
                ensure_idle(config)
                model.request("/api/chat", {"model": config["model"]["name"], "stream": False, "think": False,
                    "messages": [{"role": "user", "content": "Reply OK."}],
                    "options": {"num_ctx": original["context_length"], "num_predict": 8}})
                report["restored_context"] = original["context_length"]
            except (RuntimeError, OSError, ValueError) as exc:
                report["restore_error"] = str(exc)
        report["gpu_after"] = gpu_snapshot()
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Saved {output}", flush=True)
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
