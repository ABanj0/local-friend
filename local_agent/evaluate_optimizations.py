"""Evaluate isolated Ollama settings and concise plans without changing app preferences."""
import argparse
import copy
import json
import math
import os
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError

from .agent import PLAN_SCHEMA, Agent
from .benchmark import cases, ensure_idle, gpu_snapshot, measure
from .config import load
from .evaluation import exact, read_json, require
from .evaluation_runner import digest, write_json
from .inference import PROBE_SCHEMA, InferenceOptions
from .model import Ollama
from .process import run_process
from .safety import Policy, Stopped, redact
from .tools import Tools


def probe_residency(model):
    rows = model.request('/api/ps').get('models')
    require(isinstance(rows, list) and len(rows) <= 1000, 'Invalid model residency observation')
    selected = [row for row in rows if isinstance(row, dict)
                and row.get('name', row.get('model')) == model.config['name']]
    require(len(selected) <= 1, 'Ambiguous model residency observation')
    row = selected[0] if selected else {}
    return {'loaded': bool(selected), 'context_length': row.get('context_length'),
            'size_vram': row.get('size_vram'), 'digest': row.get('digest'), 'other_models': len(rows) - len(selected)}


class ProbeContextModel(Ollama):
    """Experimental instance only; the production probe and global cache are unchanged."""
    def __init__(self, config, profile):
        require(profile in {'fixed_2048', 'configured'}, 'Unknown probe-context profile')
        super().__init__(config)
        self.profile, self.probes, self.main_payloads = profile, [], []

    def request(self, endpoint, payload=None):
        if endpoint != '/api/chat' or not isinstance(payload, dict) or payload.get('format') != PROBE_SCHEMA:
            if endpoint == '/api/chat' and isinstance(payload, dict):
                self.main_payloads.append(digest(payload))
            return super().request(endpoint, payload)
        sent = copy.deepcopy(payload)
        options = sent.get('options', {})
        require(set(options) == {'num_ctx', 'num_predict', 'temperature'}
                and type(options['num_ctx']) is int and options['num_ctx'] in {2048, self.options.context}
                and type(options['num_predict']) is int and options['num_predict'] == 64
                and options['temperature'] == 0 and not sent.get('tools')
                and sent.get('truncate') is False and sent.get('shift') is False
                and sent.get('stream') is False, 'Production probe contract changed')
        options['num_ctx'] = 2048 if self.profile == 'fixed_2048' else self.options.context
        normalized = copy.deepcopy(sent)
        normalized['options']['num_ctx'] = 2048
        began = time.perf_counter()
        response = super().request(endpoint, sent)
        self.probes.append({'requested_context': options['num_ctx'], 'normalized_payload_sha256': digest(normalized),
            'seconds': time.perf_counter() - began, 'state': probe_residency(self),
            'native': {key: response.get(key) for key in ('load_duration', 'eval_duration', 'eval_count',
                                                        'total_duration', 'done', 'done_reason')}})
        return response


def probe_settings(config):
    selected = dict(config['model'])
    options = InferenceOptions.from_config(selected)
    require(options.max_output >= 32, 'Probe trial requires at least32 configured output tokens')
    selected.update(max_output=min(options.max_output, 128), timeout=min(selected['timeout'], 30), thinking=False)
    return selected


def probe_identity(model):
    metadata = model.admit()
    return {'digest': metadata['digest'], 'server_version': metadata['server_version'],
            'settings_sha256': digest(asdict(model.options))}


def probe_context_worker(request_path):
    request = read_json(request_path)
    exact(request, {'config', 'profile', 'repeat', 'identity'})
    require(type(request['repeat']) is int and 1 <= request['repeat'] <= 6, 'Invalid probe repeat')
    config = load(request['config'])
    model = ProbeContextModel(probe_settings(config), request['profile'])
    require(probe_identity(model) == request['identity'], 'Probe trial model/settings changed')
    warm_model = Ollama(model.config)
    initial_state = probe_residency(warm_model)
    warm_body = {'model': model.config['name'], 'messages': [{'role': 'user', 'content': 'Reply OK.'}],
        'stream': False, 'truncate': False, 'shift': False, **model.options.payload()}
    warm_body['options']['num_predict'] = min(8, model.options.max_output)
    warm_started = time.monotonic()
    warmed = warm_model.request('/api/chat', warm_body)
    require(warmed.get('done') is True and warmed.get('done_reason') == 'stop'
            and not warmed.get('remote_model') and not warmed.get('remote_host'), 'Warm precondition failed')
    warm_state = probe_residency(warm_model)
    warm_seconds = time.monotonic() - warm_started
    _, task, expected = next(case for case in cases() if case[0] == 'counter_reasoning')
    started = time.monotonic()
    answer = model.chat(task['messages'], schema=task['format'])
    elapsed = time.monotonic() - started
    require(len(model.probes) == 1 and len(model.main_payloads) == 1 and model.probe_count == 1,
            'Unexpected probe/main inference count')
    require(probe_identity(model) == request['identity'], 'Probe trial identity changed after inference')
    return {'version': 1, 'execution': 'live', 'profile': model.profile, 'repeat': request['repeat'],
            'identity': request['identity'], 'context': model.options.context,
            'initial_state': initial_state, 'warm_state': warm_state, 'warm_seconds': warm_seconds,
            'correct': not answer.get('tool_calls') and json.loads(answer.get('content', '')) == expected,
            'request_seconds': elapsed, 'probe': model.probes[0], 'main_payload_sha256': model.main_payloads[0],
            'main_native': model.inference()['calls'][-1], 'main_state': probe_residency(model)}


def probe_context_report(rows, repeats=6, *, execution='fixture'):
    require(type(repeats) is int and 3 <= repeats <= 6 and execution in {'fixture', 'live'}, 'Invalid probe comparison')
    expected = {(profile, repeat) for profile in ('fixed_2048', 'configured') for repeat in range(1, repeats + 1)}
    seen, identities, mains, probes, latencies = set(), set(), set(), set(), {'fixed_2048': [], 'configured': []}
    observed, applied, correct, live = {}, True, True, True
    for row in rows:
        require(isinstance(row, dict) and type(row.get('repeat')) is int, 'Invalid probe row')
        key = (row.get('profile'), row['repeat'])
        require(key in expected and key not in seen, 'Unknown or duplicate probe sample')
        seen.add(key)
        if row.get('error'):
            continue
        first = 'fixed_2048' if row['repeat'] % 2 else 'configured'
        require(type(row.get('order_position')) is int and row['order_position'] == int(row['profile'] != first),
                'Unbalanced probe profile order')
        require(row.get('execution') in {'fixture', 'live'}, 'Invalid probe provenance')
        live = live and row['execution'] == 'live'
        identities.add(digest(row['identity']))
        for value in (row['process_seconds'], row['request_seconds'], row['warm_seconds']):
            require(type(value) in {int, float} and math.isfinite(value) and value >= 0, 'Invalid probe timing')
        context, probe = row['context'], row['probe']
        require(type(context) is int and 2048 <= context <= 32768, 'Invalid probe context')
        target = 2048 if row['profile'] == 'fixed_2048' else context
        applied = applied and type(probe['requested_context']) is int and probe['requested_context'] == target
        for state, size in ((row['warm_state'], context), (probe['state'], target), (row['main_state'], context)):
            applied = applied and (state.get('loaded') is True and type(state.get('context_length')) is int
                and state['context_length'] == size and type(state.get('size_vram')) is int and state['size_vram'] >= 0
                and state.get('digest') == row['identity']['digest'] and state.get('other_models') == 0)
        native = probe['native']
        require(native.get('done') is True and native.get('done_reason') == 'stop'
                and type(native.get('load_duration')) is int and native['load_duration'] >= 0
                and type(native.get('eval_count')) is int and 0 < native['eval_count'] <= 64
                and type(native.get('eval_duration')) is int and native['eval_duration'] > 0
                and row['main_native'].get('finish_reason') == 'stop'
                and type(row['main_native'].get('load_ns')) is int and row['main_native']['load_ns'] >= 0
                and type(row['main_native'].get('generation_ns')) is int and row['main_native']['generation_ns'] > 0,
                'Invalid probe native observation')
        mains.add(row['main_payload_sha256'])
        probes.add(probe['normalized_payload_sha256'])
        correct = correct and row['correct'] is True
        require(row['process_seconds'] >= row['warm_seconds'], 'Warm setup exceeds measured process time')
        latencies[row['profile']].append(row['process_seconds'] - row['warm_seconds'])
        observed[key] = row
    require(len(identities) <= 1 and len(mains) <= 1 and len(probes) <= 1, 'Probe comparison payload/identity mismatch')
    complete = seen == expected and len(observed) == len(expected)
    gains = [(observed['fixed_2048', repeat]['process_seconds'] - observed['fixed_2048', repeat]['warm_seconds'])
             - (observed['configured', repeat]['process_seconds'] - observed['configured', repeat]['warm_seconds'])
             for repeat in range(1, repeats + 1) if ('fixed_2048', repeat) in observed and ('configured', repeat) in observed]
    timings = {name: {'samples': len(values), 'p50': sorted(values)[math.ceil(.5 * len(values)) - 1] if values else None,
                     'p95': sorted(values)[math.ceil(.95 * len(values)) - 1] if values else None}
               for name, values in latencies.items()}
    candidate = (complete and applied and correct and all(row['context'] != 2048 for row in observed.values())
                 and sum(gain >= .2 for gain in gains) >= math.ceil(.8 * repeats)
                 and timings['configured']['p50'] <= .9 * timings['fixed_2048']['p50'])
    return {'version': 1, 'execution': execution, 'samples_expected': len(expected), 'samples_observed': len(observed),
            'coverage_complete': complete, 'applied_contexts_and_vram_observed': applied and complete,
            'microtask_all_correct': correct and complete, 'fresh_worker_without_warm_setup_seconds': timings,
            'paired_gain_seconds': gains, 'candidate_warm_improvement': bool(candidate),
            'warm_feasibility_benefit': bool(candidate and live and execution == 'live'),
            'cold_comparison_measured': False, 'broad_agent_quality_accepted': False, 'defaults_applied': False}


def probe_context_trials(config, destination, repeats=6):
    require(type(repeats) is int and 3 <= repeats <= 6, 'Use three to six probe repeats')
    ensure_idle(config)
    model = Ollama(probe_settings(config))
    from .studio.probes import run as owned_probe
    metadata = owned_probe('model', model.config, threading.Event(), timeout=8)
    metadata['settings_sha256'] = digest(asdict(model.options))
    destination.mkdir(parents=True, exist_ok=False)
    write_json(destination / 'manifest.json', {'identity': metadata, 'repeats': repeats,
        'context': model.options.context, 'gpu_before': gpu_snapshot(),
        'design': 'Warm precondition; fresh owned workers; alternate profile order. No service restart/unload.',
        'gate': 'All microtasks/context receipts; >=80% pairs gain>=0.2s and median>=10% faster; warm-only, no adoption.'})
    rows, policy, deadline = [], Policy(config, create=False), time.monotonic() + 600
    for repeat in range(1, repeats + 1):
        order = ('fixed_2048', 'configured') if repeat % 2 else ('configured', 'fixed_2048')
        for position, profile in enumerate(order):
            ensure_idle(config)
            directory = destination / f'{profile}-{repeat}'
            directory.mkdir()
            request = directory / 'request.json'
            write_json(request, {'config': str(Path(config['base']) / 'agent.toml'), 'profile': profile,
                                 'repeat': repeat, 'identity': metadata})
            try:
                require(time.monotonic() < deadline, 'Probe comparison deadline exceeded')
                started = time.monotonic()
                remaining = deadline - time.monotonic()
                require(remaining > 0, 'Probe comparison deadline exceeded')
                result = run_process([sys.executable, '-m', 'local_agent.evaluate_optimizations', '--probe-worker', str(request)],
                                     config['base'], policy, timeout=min(100, remaining))
                write_json(directory / 'process.json', result)
                require(result['exit_code'] == 0 and not result['truncated'], 'Probe worker incomplete')
                row = json.loads(result['output'])
                require(row.get('identity') == metadata and row.get('profile') == profile and row.get('repeat') == repeat,
                        'Probe worker identity mismatch')
                row.update(process_seconds=time.monotonic() - started, order_position=position)
            except (OSError, ValueError, KeyError, TypeError, TimeoutError):
                row = {'profile': profile, 'repeat': repeat, 'error': 'incomplete_measurement'}
            write_json(directory / 'observed.json', row)
            rows.append(row)
            print(json.dumps({'profile': profile, 'repeat': repeat, 'complete': 'error' not in row}), flush=True)
    summary = probe_context_report(rows, repeats, execution='live')
    write_json(destination / 'summary.json', summary)
    return summary


@contextmanager
def isolated_server(config, destination, flash, cache):
    """Own one server/job; never stop the desktop's service or write model settings."""
    executable = Path(config["base"]) / ".runtime/ollama/ollama.exe"
    if not executable.exists():
        raise RuntimeError("This evaluator requires the repository's portable Ollama installation")
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    environment = dict(os.environ, OLLAMA_HOST=f"127.0.0.1:{port}",
                       OLLAMA_MODELS=str(Path(config["base"]) / ".runtime/models"),
                       OLLAMA_NO_CLOUD="1", OLLAMA_NUM_PARALLEL="1", OLLAMA_MAX_LOADED_MODELS="1",
                       OLLAMA_KV_CACHE_TYPE=cache, OLLAMA_NOPRUNE="1")
    for proxy in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        environment.pop(proxy, None)  # Local-only trials need no proxy credentials in server logs.
    if flash is None:
        environment.pop("OLLAMA_FLASH_ATTENTION", None)
    else:
        environment["OLLAMA_FLASH_ATTENTION"] = "1" if flash else "0"
    model = Ollama(dict(config["model"], url=f"http://127.0.0.1:{port}"))
    with (destination / "server.log").open("wb") as log:
        process = subprocess.Popen([str(executable), "serve"], env=environment, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        job = None
        try:
            if os.name == "nt":
                from .windows_job import WindowsJob
                job = WindowsJob(process)
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Isolated Ollama exited; inspect its server.log")
                try:
                    Ollama(dict(model.config, timeout=1)).request("/api/version")
                except OSError:
                    time.sleep(0.2)
                    continue
                break
            else:
                raise RuntimeError("Isolated Ollama did not become ready")
            yield model
        finally:
            if job:
                job.close()
            elif process.poll() is None:
                process.terminate()
            process.wait(10)


def unload(model):
    model.request("/api/chat", {"model": model.config["name"], "messages": [], "keep_alive": 0})


def warm(model, context):
    model.request("/api/chat", {"model": model.config["name"], "stream": False, "think": False,
                               "messages": [{"role": "user", "content": "Reply OK."}],
                               "options": {"num_ctx": context, "num_predict": 8}})


def planning_trials(config, model):
    rows = []

    class MeasuredModel(Ollama):
        def chat(self, messages, tools=None, schema=None):
            if schema == PLAN_SCHEMA and self.config.get("concise"):
                messages = copy.deepcopy(messages)
                messages[-1]["content"] = (
                    "Return a JSON plan with at most 3 brief steps. Each step must be one short sentence. "
                    "Use tools to verify the outcome. Schema: " + json.dumps(PLAN_SCHEMA))
            start = time.monotonic()
            response = super().chat(messages, tools, schema)
            self.call_times.append({"planning": schema == PLAN_SCHEMA,
                                    "seconds": time.monotonic() - start})
            return response

    tasks = [
        ("readback", "Read marker.txt with read_file and report its exact contents. Do not modify anything.",
         "ORCHID-731-VERIFIED"),
        ("bug_review", ("Read counter.py. Identify the bug in increment and propose the corrected expression. "
         "Do not modify files or run commands."), "self.value + 1"),
    ]
    for repeat in range(2):
        for concise in ([False, True] if repeat == 0 else [True, False]):
            for name, objective, expected in tasks:
                ensure_idle(config)
                with tempfile.TemporaryDirectory(prefix="agent-perf-") as directory:
                    root = Path(directory)
                    (root / "marker.txt").write_text("ORCHID-731-VERIFIED", encoding="utf-8")
                    (root / "counter.py").write_text(
                        "class Counter:\n    def __init__(self):\n        self.value = 0\n"
                        "    def increment(self):\n        self.value = self.value - 1\n        return self.value\n",
                        encoding="utf-8")
                    settings = dict(model.config, concise=concise, context=8192)
                    runner = MeasuredModel(settings)
                    runner.call_times = []
                    policy_config = copy.deepcopy(config)
                    policy_config["paths"] = {"workspace": str(root), "state": str(root / "state")}
                    tools = Tools(Policy(policy_config))  # Mutations/commands remain denied.
                    try:
                        start = time.monotonic()
                        result = Agent(runner, tools, settings, notify=lambda _: None).run(objective)
                        elapsed = time.monotonic() - start
                    finally:
                        tools.close()
                    read = any(item["tool"] == "read_file" and item["ok"] for item in result.get("evidence", []))
                    report = result.get("report", "")
                    correct = expected in report if name == "readback" else any(
                        expression in report.replace(" ", "")
                        for expression in ("self.value+1", "self.value+=1"))
                    passed = result["status"] == "reported" and read and correct
                    row = {"case": name, "concise": concise, "repeat": repeat, "elapsed_seconds": elapsed,
                           "passed": passed, "status": result["status"], "calls": runner.call_times,
                           "metrics": runner.metrics()}
                    rows.append(row)
                    print("planning", json.dumps(row), flush=True)
    return rows


def evaluate_app_path(config, model, profile, save):
    # Primary service was initially unloaded and Studio was idle. Only unload the
    # model this evaluation loaded; never restart the user's service.
    try:
        profile["residency_trials"] = []
        for repeat in range(3):
            ensure_idle(config)
            unload(model)
            cold = measure(model, cases()[0], 8192, repeat + 731, 0.1)
            ensure_idle(config)
            hot = measure(model, cases()[0], 8192, repeat + 731, 0.1)
            profile["residency_trials"].append({"unloaded": cold, "loaded": hot})
            print("residency", repeat, cold["first_token_seconds"], hot["first_token_seconds"], flush=True)
            save()
        profile["planning_trials"] = planning_trials(config, model)
        save()
    finally:
        ensure_idle(config)
        unload(model)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--existing-only", action="store_true", help="Evaluate residency/plans through the running service")
    modes.add_argument('--probe-context', action='store_true', help='Warm-only probe comparison; no service unload/restart or default changes')
    parser.add_argument('--probe-worker', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.probe_worker:
        try:
            print(json.dumps(probe_context_worker(args.probe_worker), allow_nan=False))
            return 0
        except (Exception, Stopped) as error:  # noqa: BLE001 -- fixed categories, no peer exception data
            kind = type(error).__name__
            known = {'ValueError', 'TypeError', 'KeyError', 'TimeoutError', 'URLError', 'HTTPError',
                     'InferenceIncomplete', 'PermissionError', 'Stopped'}
            print(json.dumps({'error': 'Probe-context worker incomplete',
                              'failure_type': kind if kind in known else 'unclassified'}))
            return 2
    config = load()
    ensure_idle(config)
    if args.probe_context:
        destination = Path(config['base']) / '.runtime/probe-context-trials' / uuid.uuid4().hex
        summary = probe_context_trials(config, destination)
        print(json.dumps({'run': destination.name, **summary}, indent=2))
        return 0 if summary['coverage_complete'] else 1
    primary = Ollama(config["model"])
    if primary.request("/api/ps").get("models"):
        raise RuntimeError("Primary Ollama has a loaded model. Let it unload naturally before isolated GPU comparisons.")
    destination = Path(config["paths"]["workspace"]) / "benchmarks" / (
        "optimizations-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    destination.mkdir(parents=True)
    report = {"created": datetime.now(UTC).isoformat(), "model": config["model"]["name"],
              "profiles": [], "gpu_before": gpu_snapshot(), "applied_changes": []}

    def save():
        (destination / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    profiles = [("auto-f16", None, "f16"), ("off-f16", False, "f16"),
                ("on-f16", True, "f16"), ("on-q8", True, "q8_0")]
    if args.existing_only:
        profiles = []
    for name, flash, cache in profiles:
        ensure_idle(config)
        if primary.request("/api/ps").get("models"):
            raise RuntimeError("Primary model was loaded during evaluation; stop comparisons and let Studio finish.")
        folder = destination / name
        folder.mkdir()
        profile = {"name": name, "flash_requested": flash, "cache_requested": cache, "rows": []}
        report["profiles"].append(profile)
        try:
            with isolated_server(config, folder, flash, cache) as model:
                if name == "auto-f16":
                    evaluate_app_path(config, model, profile, save)
                for context in (8192, 32768):
                    warm(model, context)
                    for repeat in range(2):
                        for case in cases(True):
                            ensure_idle(config)
                            row = measure(model, case, context, repeat + 731, 0.1)
                            row["loaded"] = model.request("/api/ps").get("models", [])
                            profile["rows"].append(row)
                            save()
                            print(name, context, case[0], row["tokens_per_second"], row["passed"], flush=True)
                unload(model)
        except (OSError, ValueError, RuntimeError) as exc:
            profile["error"] = redact(str(exc))
            if isinstance(exc, HTTPError):
                profile["error"] += ": " + redact(exc.read(2000).decode(errors="replace"))
            print(name, profile["error"], flush=True)
        save()
    if not any(p.get("planning_trials") for p in report["profiles"]):
        ensure_idle(config)
        profile = {"name": "existing-service", "rows": []}
        report["profiles"].append(profile)
        try:
            evaluate_app_path(config, primary, profile, save)
        except (OSError, ValueError, RuntimeError) as exc:
            profile["error"] = redact(str(exc))
        save()
    report["gpu_after"] = gpu_snapshot()
    for profile in report["profiles"]:
        if not profile["rows"]:
            continue
        profile["median_speed"] = statistics.median(r["tokens_per_second"] for r in profile["rows"]
                                                     if r["case"] == "throughput")
    save()
    print(f"Saved {destination / 'results.json'}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
