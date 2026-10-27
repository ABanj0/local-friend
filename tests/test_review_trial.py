import copy
import hashlib
import json
import math
import os
from unittest.mock import Mock, patch

from local_agent import review_trial as trial
from local_agent.safety import Denied, Stopped

from .support import WorkspaceTest


def finding(line):
    return {'path': 'subject.py', 'line': line, 'message': 'Concrete defect at this location.'}


def fixture_rows(repeats=3):
    rows = []
    for case in trial.cases().values():
        for repeat in range(1, repeats + 1):
            source = {'path': 'subject.py', 'sha256': hashlib.sha256(case['source'].encode()).hexdigest(), 'version': '0' * 64}
            roles = {}
            parent = hashlib.sha256(f"{case['id']}-{repeat}-baseline".encode()).hexdigest()[:32]
            for name in trial.ROLES:
                roles[name] = {'id': hashlib.sha256(f"{case['id']}-{repeat}-{name}".encode()).hexdigest()[:32],
                    'parent': None if name == 'baseline' else parent, 'role': name, 'source': dict(source),
                    'report': {'status': 'findings' if case['lines'] else 'no_findings',
                               'findings': [finding(line) for line in case['lines']]},
                    'wall_seconds': 1, 'native': {'finish_reason': 'stop', 'generation_ns': 1_000_000,
                                                'prompt_tokens': 50}, 'usage': [4, 1_000_000]}
            rows.append({'case': case['id'], 'repeat': repeat, 'corpus': trial.digest(trial.cases()), 'execution': 'fixture',
                'protocol_version': trial.VERSION,
                'identity': {'identifier_sha256': 'a' * 64, 'weights_sha256': 'b' * 64,
                             'settings_sha256': 'c' * 64, 'server_version': '0.40.7'},
                'roles': roles, 'preparation_seconds': 0, 'compatibility_probes': 0,
                'second_pass_order': ['specialist', 'self_review'] if (list(trial.cases()).index(case['id']) + repeat) % 2 == 0 else ['self_review', 'specialist'],
                'grant': {'paths': ['subject.py'], 'model_calls': 3, 'child_model_calls': 1,
                          'max_output': 384, 'mutations': False, 'delegation': False}})
    return rows


class ReviewTrialTests(WorkspaceTest):
    def test_shipped_fixture_defects_fail_and_corrected_controls_pass(self):
        checked = trial.verify_fixtures()
        self.assertEqual(len(checked), 8)
        self.assertEqual(sum(row['original_failures'] > 0 for row in checked.values()), 6)
        self.assertTrue(all(row['corrected_failures'] == 0 for row in checked.values()))
        first = trial.cases()
        first['signed-change']['lines'].append(999)
        self.assertEqual(trial.cases()['signed-change']['lines'], [3])

    def test_reports_are_source_anchored_copied_and_non_authoritative(self):
        source = trial.cases()['two-defects']['source']
        value = {'status': 'findings', 'findings': [finding(3), finding(4)]}
        parsed = trial.report(json.dumps(value), source)
        parsed['findings'][0]['line'] = 1
        self.assertEqual(value['findings'][0]['line'], 3)
        self.assertEqual(trial.report({'status': 'inconclusive', 'findings': []}, source)['status'], 'inconclusive')

    def test_unknown_fields_duplicate_fields_and_malformed_reports_are_rejected(self):
        source = trial.cases()['two-defects']['source']
        bad = [None, {}, {'status': [], 'findings': []}, {'status': 'passed', 'findings': []},
               {'status': 'findings', 'findings': []}, {'status': 'no_findings', 'findings': [finding(1)]},
               {'status': 'no_findings', 'findings': [], 'command': 'test'},
               '{"status":"no_findings","status":"findings","findings":[]}', 'x' * 8193]
        for value in bad:
            with self.subTest(value=str(value)[:60]), self.assertRaises((ValueError, TypeError)):
                trial.report(value, source)
        for change in ({'path': '../outside.py'}, {'path': '.env'}, {'line': True}, {'line': 0},
                       {'line': 999}, {'message': 'x' * 241}, {'message': 'password=fixture-secret'},
                       {'message': 'bad\ncontrol'}, {'delegate': True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                trial.report({'status': 'findings', 'findings': [{**finding(2), **change}]}, source)
        with self.assertRaises(ValueError):
            trial.report({'status': 'findings', 'findings': [finding(2), finding(2)]}, source)

    def test_snapshot_refuses_hardlinks_scope_and_stop(self):
        target = self.policy.root / 'subject.py'
        target.write_text('def solve():\n    return 0\n')
        observed, _ = trial.snapshot(self.policy)
        self.assertEqual(observed['sha256'], hashlib.sha256(target.read_bytes()).hexdigest())
        original = trial.Coding.read

        def changed(adapter, path):
            result = original(adapter, path)
            target.write_text('def solve():\n    return 1\n')
            return result

        with patch.object(trial.Coding, 'read', changed), self.assertRaises(Denied):
            trial.snapshot(self.policy)
        alias = self.policy.root / 'alias.py'
        os.link(target, alias)
        try:
            with self.assertRaises(Denied):
                trial.snapshot(self.policy)
        finally:
            alias.unlink()
        self.policy.stop_event.set()
        with self.assertRaises(Stopped):
            trial.snapshot(self.policy)

    def test_role_inherits_exact_source_and_never_dispatches_model_tool_calls(self):
        case = trial.cases()['signed-change']
        (self.policy.root / 'subject.py').write_text(case['source'])
        model = Mock()
        model.chat.return_value = {'content': json.dumps({'status': 'findings', 'findings': [finding(3)]})}
        model.usage = [(4, 1000)]
        model.inference.return_value = {'calls': [{'finish_reason': 'stop'}]}
        parent, messages = trial.role_call(model, self.policy, case, 'baseline')
        child, _ = trial.role_call(model, self.policy, case, 'specialist', parent, expected=parent['source'])
        self.assertEqual(child['parent'], parent['id'])
        sent = model.chat.call_args.args[0]
        self.assertIn('untrusted_parent_report', json.loads(sent[1]['content']))
        self.assertIn('Required output JSON schema:', sent[0]['content'])
        self.assertEqual(json.loads(sent[1]['content'])['untrusted_source']['lines'][2],
                         {'line': 3, 'text': '        return value - delta'})
        self.assertNotIn('tools', model.chat.call_args.kwargs)
        self.assertEqual(model.chat.call_args.kwargs['schema'], trial.SCHEMA)
        model.chat.return_value = {'tool_calls': [{'function': {'name': 'write_file', 'arguments': {}}}]}
        with self.assertRaises(ValueError):
            trial.role_call(model, self.policy, case, 'self_review', parent, messages, parent['source'])
        self.assertEqual(list(self.policy.root.iterdir()), [self.policy.root / 'subject.py'])

    def test_changed_source_is_rejected_before_next_model_call(self):
        case = trial.cases()['signed-change']
        path = self.policy.root / 'subject.py'
        path.write_text(case['source'])
        expected = trial.snapshot(self.policy)[0]
        path.write_text('# replacement\n')
        model = Mock()
        with self.assertRaises(Denied):
            trial.role_call(model, self.policy, case, 'baseline', expected=expected)
        model.chat.assert_not_called()

    def test_change_during_compatibility_probe_never_reaches_source_inference(self):
        case = trial.cases()['signed-change']
        request = self.policy.root.parent / 'request.json'
        request.write_text(json.dumps({'config': 'unused-config.toml', 'case': case['id'], 'repeat': 1,
            'identity': {'fixture': True}, 'corpus': trial.digest(trial.cases()), 'protocol_version': trial.VERSION}))
        model = Mock()
        model.admit.side_effect = lambda **kwargs: (self.policy.root / 'subject.py').write_text('# replaced during probe')
        with patch.object(trial, 'load', return_value=copy.deepcopy(self.config)), \
                patch.object(trial, 'trial_identity', return_value={'fixture': True}), \
                patch.object(trial, 'Ollama', return_value=model), self.assertRaises(Denied):
            trial.worker(request)
        model.chat.assert_not_called()

    def test_missing_fixtures_and_simulation_cannot_establish_benefit(self):
        rows = fixture_rows()
        rows[0]['roles']['self_review']['report'] = {'status': 'no_findings', 'findings': []}
        simulated = trial.aggregate(rows)
        self.assertEqual(simulated['specialist_wins_over_self_review'], 1)
        self.assertFalse(simulated['location_benefit_observed'])
        self.assertFalse(simulated['live_location_gate_measured'])
        self.assertFalse(trial.aggregate(rows[:-1], execution='live')['location_benefit_observed'])
        incomplete = copy.deepcopy(rows)
        incomplete[0] = {'case': rows[0]['case'], 'repeat': 1, 'error': 'incomplete_worker'}
        self.assertFalse(trial.aggregate(incomplete, execution='live')['live_location_gate_measured'])

    def test_equal_budget_self_review_comparison_and_regressions_override_wins(self):
        rows = fixture_rows()
        rows[0]['roles']['self_review']['report'] = {'status': 'no_findings', 'findings': []}
        result = trial.aggregate(rows, execution='live')
        self.assertTrue(result['candidate_location_improvement'])
        self.assertFalse(result['location_benefit_observed'])
        rows[1]['roles']['specialist']['report'] = {'status': 'no_findings', 'findings': []}
        result = trial.aggregate(rows, execution='live')
        self.assertFalse(result['location_benefit_observed'])
        self.assertEqual(result['specialist_regressions'], 1)
        self.assertEqual(result['exact_location_pairs']['baseline'], 24)

    def test_bad_identity_grant_metrics_or_source_cannot_pass(self):
        modifications = [lambda row: row['roles']['specialist']['source'].update(sha256='f' * 64),
            lambda row: row['roles']['baseline']['source'].update(sha256='f' * 64),
            lambda row: row['roles']['specialist'].update(parent='f' * 32),
            lambda row: row['roles']['specialist'].update(wall_seconds=math.nan),
            lambda row: row['roles']['specialist'].update(usage=[0, 1]),
            lambda row: row['roles']['specialist'].update(native={'finish_reason': 'length'}),
            lambda row: row['grant'].update(delegation=True), lambda row: row['grant'].update(child_model_calls=4),
            lambda row: row['identity'].update(weights_sha256='f' * 64)]
        for mutate in modifications:
            with self.subTest(mutate=mutate):
                rows = fixture_rows()
                mutate(rows[0])
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    trial.aggregate(rows, execution='live')
        with self.assertRaises(ValueError):
            trial.aggregate(fixture_rows() + fixture_rows()[:1])
        for change in ({'repeat': True}, {'protocol_version': trial.VERSION - 1}):
            rows = fixture_rows()
            rows[0].update(change)
            with self.assertRaises(ValueError):
                trial.aggregate(rows)

    def test_parent_limits_are_narrowed_without_silent_expansion(self):
        selected = trial.options(self.config)
        self.assertLessEqual(selected['max_output'], self.config['model'].get('max_output', 2048))
        self.assertLessEqual(selected['timeout'], self.config['model']['timeout'])
        for setting in ({'max_steps': 2}, {'max_output': 32}):
            changed = copy.deepcopy(self.config)
            changed['model'].update(setting)
            with self.assertRaises(ValueError):
                trial.options(changed)
