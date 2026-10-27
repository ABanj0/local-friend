import copy
import io
import os
from pathlib import Path
from unittest.mock import Mock, patch

from local_agent import evaluate_optimizations as evaluation
from local_agent.evaluate_optimizations import ProbeContextModel, isolated_server
from local_agent.inference import PROBE_SCHEMA
from local_agent.model import Ollama

from .support import WorkspaceTest


def probe_rows():
    rows = []
    for repeat in range(1, 7):
        for profile in ('fixed_2048', 'configured'):
            target = 2048 if profile == 'fixed_2048' else 8192
            state = {'loaded': True, 'context_length': 8192, 'size_vram': 6_000_000_000,
                     'digest': 'a' * 64, 'other_models': 0}
            first = 'fixed_2048' if repeat % 2 else 'configured'
            rows.append({'execution': 'fixture', 'profile': profile, 'repeat': repeat,
                'order_position': int(profile != first), 'identity': {'digest': 'a' * 64},
                'context': 8192, 'correct': True, 'request_seconds': 1, 'warm_seconds': 1,
                'process_seconds': 10 if profile == 'fixed_2048' else 4,
                'warm_state': dict(state), 'main_state': dict(state), 'main_payload_sha256': 'b' * 64,
                'main_native': {'finish_reason': 'stop', 'load_ns': 1, 'generation_ns': 1},
                'probe': {'requested_context': target, 'normalized_payload_sha256': 'c' * 64,
                    'state': {**state, 'context_length': target}, 'native': {'done': True, 'done_reason': 'stop',
                        'load_duration': 1, 'eval_count': 3, 'eval_duration': 1}}})
    return rows


class OptimizationEvaluationTests(WorkspaceTest):
    def test_probe_override_only_changes_context_and_preserves_caller_payload(self):
        original = {'model': self.config['model']['name'], 'stream': False, 'truncate': False, 'shift': False,
                    'think': False, 'keep_alive': '5m', 'options': {'num_ctx': 2048, 'num_predict': 64, 'temperature': 0},
                    'messages': [{'role': 'user', 'content': 'Return exactly {"ok":true}.'}], 'format': PROBE_SCHEMA}
        saved, sent, receipts = copy.deepcopy(original), [], []
        active_context = [8192]

        def request(client, endpoint, payload=None):
            if endpoint == '/api/ps':
                return {'models': [{'name': client.config['name'], 'digest': 'a' * 64,
                                    'context_length': active_context[0], 'size_vram': 6000}]}
            active_context[0] = payload['options']['num_ctx']
            sent.append(copy.deepcopy(payload))
            return {'done': True, 'done_reason': 'stop', 'eval_count': 3, 'eval_duration': 1,
                    'load_duration': 1, 'total_duration': 2, 'message': {'content': '{"ok":true}'}}

        with patch.object(Ollama, 'request', request):
            for profile in ('fixed_2048', 'configured'):
                client = ProbeContextModel({**self.config['model'], 'context': 8192}, profile)
                client.request('/api/chat', original)
                receipts.append(client.probes[0])
        self.assertEqual(original, saved)
        self.assertEqual([body['options']['num_ctx'] for body in sent], [2048, 8192])
        sent[1]['options']['num_ctx'] = 2048
        self.assertEqual(sent[0], sent[1])
        self.assertEqual(receipts[0]['normalized_payload_sha256'], receipts[1]['normalized_payload_sha256'])
        self.assertEqual([r['state']['context_length'] for r in receipts], [2048, 8192])

    def test_bad_probe_profile_or_widened_protected_probe_never_sends(self):
        with patch.object(Ollama, 'request') as request:
            with self.assertRaises(ValueError):
                ProbeContextModel(self.config['model'], 'unreviewed')
            client = ProbeContextModel(self.config['model'], 'configured')
            with self.assertRaises(ValueError):
                client.request('/api/chat', {'format': PROBE_SCHEMA, 'options': {'num_ctx': 2048, 'num_predict': 999}})
            request.assert_not_called()

    def test_fast_probe_uses_high_resolution_elapsed_time_even_with_coarse_deadline_clock(self):
        payload = {'model': self.config['model']['name'], 'stream': False, 'truncate': False, 'shift': False,
                   'options': {'num_ctx': 2048, 'num_predict': 64, 'temperature': 0}, 'format': PROBE_SCHEMA}
        reply = {'done': True, 'done_reason': 'stop', 'eval_count': 3, 'eval_duration': 1,
                 'load_duration': 1, 'total_duration': 2}
        client = ProbeContextModel(self.config['model'], 'configured')
        with (patch.object(Ollama, 'request', return_value=reply),
              patch.object(evaluation, 'probe_residency', return_value={}),
              patch.object(evaluation.time, 'monotonic', return_value=100),
              patch.object(evaluation.time, 'perf_counter', side_effect=[100, 100.0005])):
            client.request('/api/chat', payload)
        self.assertAlmostEqual(client.probes[0]['seconds'], .0005)

    def test_fixture_missing_state_or_bad_microtask_cannot_qualify_optimization(self):
        rows = probe_rows()
        result = evaluation.probe_context_report(rows, execution='live')
        self.assertTrue(result['candidate_warm_improvement'])
        self.assertFalse(result['warm_feasibility_benefit'])
        self.assertFalse(result['defaults_applied'])
        self.assertFalse(result['cold_comparison_measured'])
        self.assertFalse(result['broad_agent_quality_accepted'])
        for mutate in (lambda row: row.update(correct=False),
                       lambda row: row['probe']['state'].update(context_length=8192),
                       lambda row: row['main_state'].update(size_vram=None)):
            copied = copy.deepcopy(rows)
            mutate(copied[0])
            self.assertFalse(evaluation.probe_context_report(copied)['candidate_warm_improvement'])
        self.assertFalse(evaluation.probe_context_report(rows[:-1])['coverage_complete'])

    def test_duplicate_unbalanced_payload_and_nonfinite_timing_are_rejected(self):
        for mutate in (lambda row: row.update(order_position=1),
                       lambda row: row.update(main_payload_sha256='different'),
                       lambda row: row.update(process_seconds=float('nan')),
                       lambda row: row['probe']['native'].update(eval_count=65)):
            rows = probe_rows()
            mutate(rows[0])
            with self.assertRaises(ValueError):
                evaluation.probe_context_report(rows)
        with self.assertRaises(ValueError):
            evaluation.probe_context_report(probe_rows() + probe_rows()[:1])

    def test_probe_cli_never_enters_existing_server_or_unload_paths(self):
        with patch.object(evaluation, 'load', return_value=self.config), \
                patch.object(evaluation, 'ensure_idle'), \
                patch.object(evaluation, 'probe_context_trials', return_value={'coverage_complete': True}), \
                patch.object(evaluation, 'isolated_server') as isolated, \
                patch.object(evaluation, 'unload') as unload, patch('sys.stdout', new=io.StringIO()):
            self.assertEqual(evaluation.main(['--probe-context']), 0)
            isolated.assert_not_called()
            unload.assert_not_called()
        with patch('sys.stderr', new=io.StringIO()), self.assertRaises(SystemExit):
            evaluation.main(['--probe-context', '--existing-only'])

    def test_measurement_error_propagates_and_owned_server_is_cleaned_up(self):
        # Regression: an exception from the measurement must not be caught by the
        # server's readiness retry and cause a second yield/startup attempt.
        root = Path(self.temp.name)
        binary = root / ".runtime/ollama/ollama.exe"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"test fixture; never executed")
        self.config["base"] = str(root)
        process = Mock()
        process.poll.return_value = None
        job = Mock()
        with patch("local_agent.evaluate_optimizations.subprocess.Popen", return_value=process), \
                patch("local_agent.evaluate_optimizations.Ollama.request", return_value={}), \
                patch("local_agent.windows_job.WindowsJob", return_value=job), \
                self.assertRaisesRegex(OSError, "measurement failed"), \
                isolated_server(self.config, root, True, "q8_0"):
            raise OSError("measurement failed")
        process.wait.assert_called_once_with(10)
        if os.name == "nt":
            job.close.assert_called_once()
        else:
            process.terminate.assert_called_once()
