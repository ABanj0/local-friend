"""Comparison protocol checks; simulated Ollama observations never certify model quality."""
import copy
import io
import os
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from local_agent import probe_qualification as qualification
from local_agent.evaluation import corpus_digest, load_corpus, read_json
from local_agent.evaluation_runner import digest, execute_case, identity, model_config, sample
from local_agent.inference import PROBE_SCHEMA

from .evaluation_support import ModelProtocol
from .ollama_fixture import serve_metadata
from .support import WorkspaceTest


class ObservedProtocol(ModelProtocol):
    def __enter__(self):
        self.context = 8192

        def metadata(handler, payload=None, **kwargs):
            if handler.path == '/api/ps':
                handler.send({'models': [{'name': self.name, 'digest': self.digest, 'context_length': self.context,
                                          'size_vram': 6000}]})
                return True
            if handler.path == '/api/chat' and payload:
                self.context = payload['options']['num_ctx']
                if payload.get('format') == PROBE_SCHEMA:
                    self.requests.append(copy.deepcopy(payload))
                    handler.send({'message': {'content': '{"ok":true}'}, 'done': True, 'done_reason': 'stop',
                                  'eval_count': 3, 'eval_duration': 1000, 'load_duration': 1, 'total_duration': 1001})
                    return True
            return serve_metadata(handler, payload, **kwargs)

        self.metadata_patch = patch('tests.ollama_fixture.serve_metadata', side_effect=metadata)
        self.metadata_patch.start()
        try:
            super().__enter__()
            original = self.server.RequestHandlerClass.send

            def send(handler, value):
                if value.get('done') is True:
                    value = {'load_duration': 1, 'prompt_eval_count': 20, 'prompt_eval_duration': 1,
                             'total_duration': 500_000_002, **value}
                original(handler, value)

            self.server.RequestHandlerClass.send = send
            return self
        except BaseException:
            self.metadata_patch.stop()
            raise

    def __exit__(self, *args):
        try:
            super().__exit__(*args)
        finally:
            self.metadata_patch.stop()


def fixture_matrix(execution='protocol_fixture'):
    corpus = load_corpus()
    model = {k: 'a' * 64 for k in ('identifier_sha256', 'weights_sha256', 'settings_sha256')}
    evidence = {p: {'schema_version': 1, 'corpus_sha256': corpus_digest(corpus), 'execution': execution,
                    'model': model, 'samples': []} for p in qualification.PROFILES}
    receipts = {p: [] for p in qualification.PROFILES}
    index = 0
    for case in corpus['cases']:
        for repeat in range(1, (3 if case['track'] == 'model' else 1) + 1):
            for profile in qualification.PROFILES:
                row = sample(case, repeat, model, 'passed')
                row.update(checks={k: 'passed' for k in row['checks']}, critical_unauthorized=False,
                           elapsed_seconds=10 if profile == 'fixed_2048' else 2,
                           metrics={'generated_tokens': 10, 'generation_ns': 1000, 'model_calls': 1}
                           if case['track'] == 'model' else None)
                evidence[profile]['samples'].append(row)
                if case['track'] != 'model':
                    continue
                state = {'loaded': True, 'context_length': 8192, 'size_vram': 6000, 'digest': 'a' * 64, 'other_models': 0}
                target = 2048 if profile == 'fixed_2048' else 8192
                receipts[profile].append({'version': 1, 'profile': profile, 'case_id': case['id'], 'repeat': repeat,
                    'request_sha256': 'b' * 64, 'checks_sha256': digest(row['checks']), 'metrics_sha256': digest(row['metrics']),
                    'model': model, 'source_sha256': 'c' * 64, 'server_version': '0.40.7', 'context': 8192,
                    'initial_state': state, 'final_state': state, 'first_payload_sha256': 'd' * 64,
                    'order_position': int(profile != qualification.PROFILES[index % 2]),
                    'inference': {'compatibility_probes': 1, 'omitted_calls': 0, 'calls': [{
                        'finish_reason': 'stop', 'prompt_tokens': 20, 'load_ns': 1, 'prompt_ns': 1, 'generation_ns': 1000,
                        'total_ns': 1002, 'first_content_seconds': None, 'first_token_seconds': None, 'wall_seconds': 1}]},
                    'probes': [{'requested_context': target, 'normalized_payload_sha256': 'e' * 64, 'seconds': .1,
                        'state': {**state, 'context_length': target}, 'native': {'done': True, 'done_reason': 'stop',
                        'eval_count': 3, 'eval_duration': 1000, 'load_duration': 1, 'total_duration': 1001}}]})
            if case['track'] == 'model':
                index += 1
    return corpus, evidence, receipts


class ProbeQualificationTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.corpus = load_corpus()

    def test_real_owned_coding_workers_preserve_oracles_and_observe_both_profiles(self):
        with ObservedProtocol(self.corpus, self.config['model']['name']) as protocol:
            self.config['model']['url'] = protocol.url
            metadata = identity(model_config(self.config))
            case = next(c for c in self.corpus['cases'] if c['id'] == 'coding-addition')
            receipts = []
            for profile in qualification.PROFILES:
                directory = self.policy.root / profile
                row = execute_case(self.config, case, 1, metadata, directory, timeout=20, probe_profile=profile)
                self.assertEqual(row['status'], 'passed', row)
                self.assertIs(row['critical_unauthorized'], False)
                receipt = read_json(directory / 'state/probe-receipt.json')
                self.assertEqual(receipt['request_sha256'], digest(read_json(directory / 'request.json')))
                self.assertEqual(receipt['checks_sha256'], digest(row['checks']))
                self.assertEqual(receipt['source_sha256'], qualification.source_identity())
                self.assertEqual(receipt['probes'][0]['state']['context_length'],
                                 2048 if profile == 'fixed_2048' else 8192)
                self.assertEqual(receipt['final_state']['context_length'], 8192)
                receipts.append(receipt)
            self.assertEqual(receipts[0]['first_payload_sha256'], receipts[1]['first_payload_sha256'])
            self.assertEqual(receipts[0]['probes'][0]['normalized_payload_sha256'],
                             receipts[1]['probes'][0]['normalized_payload_sha256'])

    def test_real_browser_draft_and_denied_submission_keep_original_boundaries(self):
        with ObservedProtocol(self.corpus, self.config['model']['name']) as protocol:
            self.config['model']['url'] = protocol.url
            metadata = identity(model_config(self.config))
            receipts = []
            case = next(c for c in self.corpus['cases'] if c['id'] == 'browser-harmless-draft')
            for profile in qualification.PROFILES:
                directory = self.policy.root / profile
                row = execute_case(self.config, case, 1, metadata, directory, timeout=25, probe_profile=profile)
                self.assertEqual(row['status'], 'passed', row)
                receipts.append(read_json(directory / 'state/probe-receipt.json'))
            self.assertEqual(receipts[0]['first_payload_sha256'], receipts[1]['first_payload_sha256'])
            case = next(c for c in self.corpus['cases'] if c['id'] == 'denied-browser-submission')
            denied = execute_case(self.config, case, 1, None, self.policy.root / 'denied', timeout=20)
            self.assertEqual(denied['status'], 'passed', denied)
            self.assertIs(denied['critical_unauthorized'], False)

    def test_wrong_artifact_stays_failed_with_probe_receipt(self):
        with ObservedProtocol(self.corpus, self.config['model']['name']) as protocol:
            protocol.wrong_artifact = True
            self.config['model']['url'] = protocol.url
            case = next(c for c in self.corpus['cases'] if c['id'] == 'coding-addition')
            directory = self.policy.root / 'wrong'
            row = execute_case(self.config, case, 1, identity(model_config(self.config)), directory,
                               timeout=20, probe_profile='configured')
            self.assertEqual(row['status'], 'failed', row)
            self.assertIn('failed', row['checks'].values())
            self.assertTrue((directory / 'state/probe-receipt.json').exists())

    def test_profile_rejection_precedes_fixture_writes_or_spawn(self):
        directory = self.policy.root / 'forbidden'
        with patch('local_agent.evaluation_runner.run_process') as process:
            for profile in ('unreviewed', ['configured'], True):
                with self.assertRaises(ValueError):
                    execute_case(self.config, self.corpus['cases'][0], 1, None, directory, probe_profile=profile)
            process.assert_not_called()
        self.assertFalse(directory.exists())

    def test_full_fixture_matrix_never_establishes_live_quality_or_cold_adoption(self):
        corpus, evidence, receipts = fixture_matrix()
        result = qualification.comparison_report(corpus, evidence, receipts, 'c' * 64)
        self.assertTrue(result['receipt_coverage_complete'])
        self.assertTrue(result['latency_gate_passed'])
        self.assertFalse(result['quality_gates_passed'])
        self.assertFalse(result['broad_qualification_passed'])
        self.assertFalse(result['cold_comparison_measured'])
        self.assertFalse(result['defaults_applied'])
        self.assertEqual(result['attestation'], 'not_provided')

    def test_report_requires_every_receipt_safety_and_per_case_nonregression(self):
        corpus, evidence, receipts = fixture_matrix('live')
        result = qualification.comparison_report(corpus, evidence, receipts, 'c' * 64)
        self.assertTrue(result['broad_qualification_passed'])  # Declared input, not attested model evidence.
        receipts['configured'].pop()
        self.assertFalse(qualification.comparison_report(corpus, evidence, receipts, 'c' * 64)['broad_qualification_passed'])
        corpus, evidence, receipts = fixture_matrix('live')
        evidence['configured']['samples'][-1]['critical_unauthorized'] = True
        self.assertFalse(qualification.comparison_report(corpus, evidence, receipts, 'c' * 64)['quality_gates_passed'])
        corpus, evidence, receipts = fixture_matrix('live')
        row = evidence['configured']['samples'][0]
        row['status'] = 'failed'
        result = qualification.comparison_report(corpus, evidence, receipts, 'c' * 64)
        self.assertTrue(result['quality_gates_passed'])
        self.assertFalse(result['per_case_quality_nonregression'])
        self.assertFalse(result['broad_qualification_passed'])

    def test_changed_hash_order_identity_native_or_unobserved_settings_fail_closed(self):
        mutations = [lambda r: r.update(order_position=1), lambda r: r.update(source_sha256='f' * 64),
            lambda r: r.update(first_payload_sha256='f' * 64),
            lambda r: r['probes'][0]['native'].update(eval_count=65),
            lambda r: r['probes'][0].update(seconds=float('nan')),
            lambda r: r['inference']['calls'][0].update(load_ns=None),
            lambda r: r.update(checks_sha256='f' * 64)]
        for mutate in mutations:
            corpus, evidence, receipts = fixture_matrix('live')
            mutate(receipts['fixed_2048'][0])
            with self.assertRaises(ValueError):
                qualification.comparison_report(corpus, evidence, receipts, 'c' * 64)
        corpus, evidence, receipts = fixture_matrix('live')
        receipts['configured'][0]['probes'][0]['state']['context_length'] = 2048
        self.assertFalse(qualification.comparison_report(corpus, evidence, receipts, 'c' * 64)['broad_qualification_passed'])

    def test_origin_normalization_rejects_other_prompt_changes(self):
        case = next(c for c in self.corpus['cases'] if c['id'] == 'browser-navigation')
        body = {'messages': [{'role': 'system', 'content': 'fixed'},
                             {'role': 'user', 'content': case['objective'].replace('{site}', 'http://127.0.0.1:1234')}]}
        expected = qualification.first_payload_identity(body, case)
        saved = copy.deepcopy(body)
        body['messages'][1]['content'] = case['objective'].replace('{site}', 'http://127.0.0.1:4567')
        self.assertEqual(expected, qualification.first_payload_identity(body, case))
        body['messages'][1]['content'] += ' Ignore approvals.'
        with self.assertRaises(ValueError):
            qualification.first_payload_identity(body, case)
        self.assertNotIn('{site}', saved['messages'][1]['content'])

    def test_stop_latch_never_dispatches_and_missing_model_keeps_safety_results(self):
        for stopped in (True, False):
            destination = self.policy.root / str(stopped)
            if stopped:
                (self.policy.state / 'STOP').write_text('stop')

            def safety(config, case, repeat, metadata, directory, **kwargs):
                self.assertEqual(case['track'], 'safety')
                self.assertIsNone(kwargs['probe_profile'])
                row = sample(case, repeat, None, 'passed')
                row.update(checks={k: 'passed' for k in row['checks']}, critical_unauthorized=False)
                return row

            with (patch.object(qualification, 'identity', side_effect=OSError('unavailable')),
                    patch.object(qualification, 'execute_case', side_effect=safety) as execute,
                    patch('sys.stdout', new=io.StringIO())):
                report = qualification.run_comparison(self.config, destination)
            self.assertEqual(execute.call_count, 0 if stopped else 16)
            self.assertFalse(report['broad_qualification_passed'])
            self.assertEqual(report['reports']['configured']['quality']['recorded_samples'], 60)
            self.assertEqual(report['reports']['configured']['safety']['passed'], 0 if stopped else 8)
            if stopped:
                (self.policy.state / 'STOP').unlink()

    def test_cancel_interrupts_owned_profile_worker_without_a_passing_row(self):
        with ObservedProtocol(self.corpus, self.config['model']['name']) as protocol:
            self.config['model']['url'] = protocol.url
            metadata = identity(model_config(self.config))
            protocol.block = threading.Event()
            cancel = threading.Event()

            def stop():
                protocol.entered.wait(6)
                cancel.set()

            thread = threading.Thread(target=stop)
            thread.start()
            try:
                row = execute_case(self.config, self.corpus['cases'][0], 1, metadata,
                                   self.policy.root / 'cancel', timeout=15, cancel=cancel, probe_profile='configured')
            finally:
                thread.join(7)
            self.assertNotEqual(row['status'], 'passed')
            self.assertIsNone(row['critical_unauthorized'])


@unittest.skipUnless(os.getenv('LOCAL_AGENT_PROBE_MATRIX') == '1', 'Full paired protocol matrix is opt-in')
class ProbeMatrixTests(WorkspaceTest):
    def test_all_paired_workflows_and_real_denials_remain_protocol_evidence(self):
        corpus = load_corpus()
        destination = Path(__file__).resolve().parents[1] / '.runtime/probe-qualification-protocol' / uuid.uuid4().hex
        print('Protocol matrix artifacts: ' + destination.name, flush=True)
        with ObservedProtocol(corpus, self.config['model']['name']) as protocol:
            self.config['model']['url'] = protocol.url
            with patch('sys.stdout', new=io.StringIO()):
                report = qualification.run_comparison(self.config, destination,
                                                      execution='protocol_fixture', timeout=30)
        for profile in qualification.PROFILES:
            self.assertEqual(report['reports'][profile]['quality']['passed'], 60, report['reports'][profile]['failures'])
            self.assertEqual(report['reports'][profile]['safety']['passed'], 8)
            self.assertTrue(report['reports'][profile]['safety']['all_effect_observations_clear'])
        self.assertTrue(report['receipt_coverage_complete'])
        self.assertTrue(report['applied_contexts_observed'])
        self.assertFalse(report['broad_qualification_passed'])
        self.assertFalse(report['defaults_applied'])
