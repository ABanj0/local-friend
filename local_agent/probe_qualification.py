"""Development-only matched agent comparison; never changes production defaults/services."""
import argparse
import copy
import hashlib
import json
import math
import re
import threading
import time
import uuid
from pathlib import Path

from .benchmark import ensure_idle
from .config import load
from .evaluate_optimizations import ProbeContextModel, probe_residency
from .evaluation import DIGEST, aggregate, corpus_digest, exact, load_corpus, read_json, require
from .evaluation_runner import (
    digest,
    execute_case,
    identity,
    model_config,
    sample,
    worker,
    write_json,
)
from .safety import Stopped

PROFILES = ('fixed_2048', 'configured')
SOURCE_FILES = ('agent.py', 'tools.py', 'tool_spec.py', 'safety.py', 'model.py', 'inference.py',
                'context.py', 'evaluation.py', 'evaluation_runner.py', 'evaluate_optimizations.py',
                'probe_qualification.py')


def source_identity():
    root = Path(__file__).parent
    return digest({name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in SOURCE_FILES})


def first_payload_identity(payload, case):
    """Normalize only the trusted fixture origin in the initial, exact objective."""
    body = copy.deepcopy(payload)
    actual = body['messages'][1]['content']
    if case['fixture'] == 'browser':
        origins = set(re.findall(r'http://127\.0\.0\.1:[0-9]{1,5}', actual))
        require(len(origins) == 1, 'Ambiguous fixture origin')
        actual = actual.replace(next(iter(origins)), '{site}')
    require(actual == case['objective'], 'Initial evaluation objective changed')
    body['messages'][1]['content'] = actual
    return digest(body)


def qualification_worker(request_path, profile):
    require(profile in PROFILES, 'Invalid probe profile')
    request_path = Path(request_path)
    request = read_json(request_path)
    case = next(c for c in load_corpus()['cases'] if c['id'] == request['case_id'])
    require(case['track'] == 'model', 'Probe comparison requires a model case')
    sources, clients = source_identity(), []

    class MeasuredModel(ProbeContextModel):
        def __init__(self, selected):
            super().__init__(selected, profile)
            self.first_payload_sha256 = None
            self.initial_state = probe_residency(self)
            self.before_metadata = self.admit()
            clients.append(self)

        def request(self, endpoint, payload=None):
            from .agent import PLAN_SCHEMA
            if (endpoint == '/api/chat' and isinstance(payload, dict) and payload.get('format') == PLAN_SCHEMA
                    and self.first_payload_sha256 is None):
                self.first_payload_sha256 = first_payload_identity(payload, case)
            return super().request(endpoint, payload)

    failures = []
    row = worker(request_path, failures, model_factory=MeasuredModel)
    require(len(clients) == 1, 'Missing or multiple agent model clients')
    client = clients[0]
    after = client.admit()
    require(source_identity() == sources and after['digest'] == client.before_metadata['digest']
            == request['model']['weights_sha256']
            and after['server_version'] == client.before_metadata['server_version'], 'Qualification identity changed')
    # Lives inside the owned state directory; the existing effects oracle stays unchanged.
    write_json(request_path.parent / 'state/probe-receipt.json', {
        'version': 1, 'profile': profile, 'case_id': case['id'], 'repeat': request['repeat'],
        'request_sha256': digest(request), 'checks_sha256': digest(row['checks']),
        'metrics_sha256': digest(row['metrics']), 'model': request['model'], 'source_sha256': sources,
        'server_version': after['server_version'], 'context': client.options.context,
        'initial_state': client.initial_state, 'final_state': probe_residency(client),
        'first_payload_sha256': client.first_payload_sha256, 'probes': client.probes,
        'inference': {key: client.inference()[key] for key in ('calls', 'compatibility_probes', 'omitted_calls')}})
    return {'sample': row, 'failure': failures[-1] if failures else None}


def comparison_report(corpus, evidence, receipts, sources):
    exact(evidence, PROFILES)
    exact(receipts, PROFILES)
    require(isinstance(sources, str) and DIGEST.fullmatch(sources), 'Invalid source identity')
    reports = {profile: aggregate(corpus, evidence[profile]) for profile in PROFILES}
    require(evidence[PROFILES[0]]['model'] == evidence[PROFILES[1]]['model'], 'Mixed comparison models')
    expected = [(c['id'], repeat) for c in corpus['cases'] if c['track'] == 'model' for repeat in range(1, 4)]
    checked, contexts, probe_hashes, versions, payloads = {}, set(), set(), set(), {}
    receipts_valid = True
    for profile in PROFILES:
        require(isinstance(receipts[profile], list) and len(receipts[profile]) <= len(expected), 'Invalid receipt count')
        samples = {(s['case_id'], s['repeat']): s for s in reports[profile]['samples'] if s['track'] == 'model'}
        seen = set()
        for receipt in receipts[profile]:
            exact(receipt, {'version', 'profile', 'case_id', 'repeat', 'request_sha256', 'checks_sha256',
                'metrics_sha256', 'model', 'source_sha256', 'server_version', 'context', 'initial_state',
                'final_state', 'first_payload_sha256', 'probes', 'inference', 'order_position'})
            key = (receipt['case_id'], receipt['repeat'])
            require(key in expected and key not in seen and type(receipt['repeat']) is int, 'Unknown or duplicate receipt')
            seen.add(key)
            row = samples[key]
            first = PROFILES[expected.index(key) % 2]
            require(type(receipt['order_position']) is int and receipt['order_position'] == int(profile != first),
                    'Comparison order changed')
            require(type(receipt['version']) is int and receipt['version'] == 1 and receipt['profile'] == profile
                    and receipt['model'] == evidence[profile]['model'] and receipt['source_sha256'] == sources
                    and receipt['checks_sha256'] == digest(row['checks'])
                    and receipt['metrics_sha256'] == digest(row['metrics']), 'Receipt identity mismatch')
            require(all(isinstance(receipt[k], str) and DIGEST.fullmatch(receipt[k])
                        for k in ('request_sha256', 'first_payload_sha256')), 'Missing request observation')
            require(isinstance(receipt['server_version'], str)
                    and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:[-+][a-zA-Z0-9.-]+)?', receipt['server_version']),
                    'Invalid server version')
            versions.add(receipt['server_version'])
            context = receipt['context']
            require(type(context) is int and 2048 <= context <= 32768, 'Invalid context')
            contexts.add(context)
            payloads.setdefault(key, set()).add(receipt['first_payload_sha256'])
            probes = receipt['probes']
            require(isinstance(probes, list) and 1 <= len(probes) <= 64, 'Missing or excessive schema probes')
            inference = receipt['inference']
            exact(inference, {'calls', 'compatibility_probes', 'omitted_calls'})
            require(type(inference['compatibility_probes']) is int
                    and inference['compatibility_probes'] == len(probes)
                    and type(inference['omitted_calls']) is int and inference['omitted_calls'] == 0
                    and isinstance(inference['calls'], list) and 1 <= len(inference['calls']) <= 128,
                    'Incomplete main inference observations')
            for call in inference['calls']:
                exact(call, {'finish_reason', 'prompt_tokens', 'load_ns', 'prompt_ns', 'generation_ns',
                             'total_ns', 'first_content_seconds', 'first_token_seconds', 'wall_seconds'})
                require(call['finish_reason'] == 'stop'
                        and all(type(call[k]) is int and 0 <= call[k] <= 86_400_000_000_000
                                for k in ('prompt_tokens', 'load_ns', 'prompt_ns', 'generation_ns', 'total_ns'))
                        and type(call['wall_seconds']) in {int, float} and math.isfinite(call['wall_seconds'])
                        and 0 < call['wall_seconds'] <= 3600
                        and all(call[k] is None or type(call[k]) in {int, float}
                                and math.isfinite(call[k]) and 0 <= call[k] <= call['wall_seconds']
                                for k in ('first_content_seconds', 'first_token_seconds')),
                        'Invalid main native observations')
            target = 2048 if profile == 'fixed_2048' else context
            for probe in probes:
                exact(probe, {'requested_context', 'normalized_payload_sha256', 'seconds', 'state', 'native'})
                require(probe['requested_context'] == target and type(probe['requested_context']) is int,
                        'Probe override not applied')
                require(isinstance(probe['normalized_payload_sha256'], str)
                        and DIGEST.fullmatch(probe['normalized_payload_sha256']), 'Invalid probe hash')
                probe_hashes.add(probe['normalized_payload_sha256'])
                native = probe['native']
                exact(native, {'load_duration', 'eval_duration', 'eval_count', 'total_duration', 'done', 'done_reason'})
                require(native['done'] is True and native['done_reason'] == 'stop'
                        and type(native['eval_count']) is int and 1 <= native['eval_count'] <= 64
                        and all(type(native[k]) is int and 0 <= native[k] <= 86_400_000_000_000
                                for k in ('load_duration', 'eval_duration', 'total_duration')),
                        'Invalid native probe observation')
                require(type(probe['seconds']) in {int, float} and math.isfinite(probe['seconds'])
                        and 0 < probe['seconds'] <= 3600, 'Invalid probe duration')
            for state, applied in [(p['state'], target) for p in probes] + [(receipt['final_state'], context)]:
                exact(state, {'loaded', 'context_length', 'size_vram', 'digest', 'other_models'})
                receipts_valid &= (state['loaded'] is True and type(state['context_length']) is int
                    and state['context_length'] == applied and type(state['size_vram']) is int
                    and state['size_vram'] >= 0 and state['digest'] == row['model']['weights_sha256']
                    and type(state['other_models']) is int and state['other_models'] == 0)
            checked[profile, key] = row
    require(len(contexts) <= 1 and len(versions) <= 1 and len(probe_hashes) <= 1
            and all(len(hashes) == 1 for hashes in payloads.values()), 'Comparison inputs/settings changed')
    complete = len(checked) == len(expected) * 2
    pairs = [(checked['fixed_2048', key], checked['configured', key]) for key in expected
             if ('fixed_2048', key) in checked and ('configured', key) in checked]
    gains = [a['elapsed_seconds'] - b['elapsed_seconds'] for a, b in pairs
             if a['elapsed_seconds'] is not None and b['elapsed_seconds'] is not None]
    base, candidate = (reports[p] for p in PROFILES)
    quality = all(report['quality']['gate_passed'] for report in reports.values())
    nonregression = all(sum(s['status'] == 'passed' for s in candidate['samples'] if s['case_id'] == case['id'])
                        >= sum(s['status'] == 'passed' for s in base['samples'] if s['case_id'] == case['id'])
                        for case in corpus['cases'] if case['track'] == 'model')
    latency = (len(gains) == len(expected) and sum(gain >= .2 for gain in gains) >= math.ceil(.8 * len(expected))
               and candidate['metrics']['latency_p50_seconds'] <= .9 * base['metrics']['latency_p50_seconds'])
    return {'version': 1, 'reports': reports, 'receipt_coverage_complete': complete,
        'applied_contexts_observed': receipts_valid and complete, 'paired_gain_seconds': gains,
        'quality_gates_passed': quality, 'per_case_quality_nonregression': nonregression,
        'latency_gate_passed': bool(latency),
        'broad_qualification_passed': bool(complete and receipts_valid and quality and nonregression and latency
                                         and contexts != {2048}),
        'cold_comparison_measured': False, 'defaults_applied': False,
        'attestation': 'not_provided', 'residency_condition': 'ambient_not_controlled_cold'}


def run_comparison(config, destination, *, execution='live', timeout=120, cancel=None):
    require(execution in {'live', 'protocol_fixture'}, 'Invalid execution provenance')
    require(type(timeout) in {int, float} and math.isfinite(timeout) and 1 <= timeout <= 180, 'Invalid case timeout')
    cancel = cancel if cancel is not None else threading.Event()
    corpus, sources = load_corpus(), source_identity()
    selected = model_config(config)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    metadata, preflight = None, 'blocked'
    try:
        ensure_idle(config)
        metadata = identity(selected)
        preflight = 'observed'
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        pass  # Keep deterministic safety checks and explicit unrun model rows.
    write_json(destination / 'manifest.json', {'version': 1, 'corpus_sha256': corpus_digest(corpus),
        'source_sha256': sources, 'model': metadata, 'preflight': preflight, 'execution': execution,
        'profiles': list(PROFILES), 'case_timeout_seconds': timeout, 'global_seconds': 3600,
        'gate': 'Both existing >=90% quality gates and all safety; no per-case loss; >=80% pairs gain>=0.2s, median>=10% faster.',
        'control': 'Ambient residency, fixed case/repeat alternating order; no seed/prompt/default/service change.'})
    evidence = {p: {'schema_version': 1, 'corpus_sha256': corpus_digest(corpus), 'model': metadata,
                   'execution': execution, 'samples': []} for p in PROFILES}
    receipts, halted, safety_failed = {p: [] for p in PROFILES}, False, False
    deadline, pair = time.monotonic() + 3600, 0
    for case in sorted(corpus['cases'], key=lambda c: c['track'] != 'safety'):
        for repeat in range(1, (3 if case['track'] == 'model' else 1) + 1):
            order = PROFILES if pair % 2 == 0 else PROFILES[::-1]
            if case['track'] == 'model':
                pair += 1
            for position, profile in enumerate(order):
                stopped = cancel.is_set() or (Path(config['paths']['state']) / 'STOP').exists()
                halted = halted or stopped or time.monotonic() >= deadline
                directory = destination / profile / f"{case['id']}-{repeat}"
                row = sample(case, repeat, metadata, 'not_run')
                if not halted and not (case['track'] == 'model' and (safety_failed or metadata is None)):
                    try:
                        ensure_idle(config)
                    except (OSError, RuntimeError):
                        halted = True
                    if not halted:
                        remaining = deadline - time.monotonic()
                        if remaining >= 1:
                            row = execute_case(config, case, repeat, metadata, directory,
                                timeout=min(timeout, remaining), cancel=cancel,
                                probe_profile=profile if case['track'] == 'model' else None)
                            receipt_path = directory / 'state/probe-receipt.json'
                            if case['track'] == 'model' and receipt_path.exists():
                                receipt = read_json(receipt_path)
                                require(receipt['request_sha256'] == digest(read_json(directory / 'request.json')),
                                        'Request/receipt mismatch')
                                receipt['order_position'] = position
                                receipts[profile].append(receipt)
                        else:
                            halted = True
                if case['track'] == 'safety' and row['status'] != 'passed':
                    safety_failed = True
                halted = halted or row['critical_unauthorized'] is True
                evidence[profile]['samples'].append(row)
                print(json.dumps({'profile': profile, 'case_id': case['id'], 'repeat': repeat,
                                  'status': row['status']}), flush=True)
    require(source_identity() == sources, 'Comparison source changed')
    write_json(destination / 'observations.json', evidence)
    write_json(destination / 'receipts.json', receipts)
    report = comparison_report(corpus, evidence, receipts, sources)
    write_json(destination / 'report.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='agent.toml')
    parser.add_argument('--worker', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--profile', choices=PROFILES, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.worker:
            print(json.dumps(qualification_worker(args.worker, args.profile), allow_nan=False))
            return 0
        require(args.profile is None, 'Profile is worker-only')
        config = load(args.config)
        destination = Path(config['base']) / '.runtime/probe-qualification' / uuid.uuid4().hex
        report = run_comparison(config, destination)
        print(json.dumps({'run': destination.name, **{k: v for k, v in report.items() if k != 'reports'}}, indent=2))
        return 0 if report['broad_qualification_passed'] else 1
    except (Exception, Stopped, KeyboardInterrupt):  # noqa: BLE001 -- fixed error, no prompts/paths/peer exception text
        print('{"error":"Probe qualification incomplete; inspect owned run artifacts"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
