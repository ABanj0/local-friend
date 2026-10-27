"""Opt-in qualification of actual production retrieval; no quality tuning or fixtures."""
import hashlib
import json
import os
import time
import unittest
import uuid
from pathlib import Path

from local_agent.benchmark import ensure_idle
from local_agent.config import load
from local_agent.semantic_evaluation import corpus
from local_agent.studio.manager import Manager

from .support import WorkspaceTest


@unittest.skipUnless(os.environ.get('LIVE_MEMORY_ACCEPTANCE') == '1',
                     'Actual integrated file-memory qualification is opt-in')
class LiveMemoryAcceptanceTests(WorkspaceTest):
    def test_fixed_file_corpus_after_restart_recall_scope_citation_and_deletion(self):
        ensure_idle(load())
        data, corpus_hash = corpus()
        self.assertEqual(corpus_hash, '2108b57f57bedda4b0906f66e8448aaf02e4d1b64bcd5d93bb987ecb592ae30b')
        self.assertEqual(len(data['cases']), 32)
        output = Path('.runtime/memory-acceptance') / uuid.uuid4().hex
        output.mkdir(parents=True)
        report = {'version': 1, 'source': 'actual_production_memory_index', 'status': 'incomplete',
                  'corpus_sha256': corpus_hash, 'gate': data['gate'], 'observations': [], 'checks': {},
                  'test_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        manager = Manager(self.config)
        self.addCleanup(manager.close)
        started = time.monotonic()
        try:
            source_chat = manager.store.conversation('Fixed file memory corpus')
            other_chat = manager.store.conversation('Excluded project notes')
            (self.policy.root / 'other').mkdir()
            targets, originals, imported = {}, {}, []
            # Pair unchanged corpus notes into fixed900-character text chunks. Padding
            # is whitespace only; no identifiers/questions/answer hints are added.
            for offset in range(0, 32, 2):
                batch = data['cases'][offset:offset + 2]
                path = self.policy.root / f'facts-{offset // 2:02}.txt'
                raw = ''.join(case['note'].ljust(899) + '\n' for case in batch).encode()
                path.write_bytes(raw)
                originals[path.name] = raw
                preview = manager.memory_sources.preview('.', path.name)
                saved = manager.memory_sources.import_file('.', source_chat, path.name,
                    preview['sha256'], preview['version'], confirmed=True)
                imported.append(saved)
                for case in batch:
                    rows = manager.memory.search('.', case['literal'])
                    exact = [r for r in rows if r.get('file', {}).get('id') == saved['source']
                             and r['text'].strip() == case['note']]
                    self.assertEqual(len(exact), 1)
                    targets[case['id']] = exact[0]['id']
            for case in data['cases']:
                for suffix in data['distractor_suffixes']:
                    manager.memory.remember('.', source_chat, case['note'].split()[0] + ' ' + suffix + '.')
                manager.memory.remember('other', other_chat, case['note'])
            indexed = manager.memory_index.reindex('.', 'qwen3-embedding:0.6b', confirmed=True)
            self.assertEqual(indexed['indexed'], 96)
            report['identity'] = indexed['identity']
            manager.memory_index.set_enabled('.', True, confirmed=True)
            manager.close()
            manager = Manager(self.config)
            self.addCleanup(manager.close)
            self.assertTrue(manager.memory_index.status('.')['automatic_retrieval'])
            scope = manager.memory.scope('.')
            with manager.store.connection() as db:
                allowed = {r[0] for r in db.execute('SELECT id FROM memories WHERE scope=?', (scope,))}
            self.assertEqual(len(allowed), 96)
            for variant in ('literal', 'paraphrase'):
                for case in data['cases']:
                    self.assertLess(time.monotonic() - started, 240, 'Qualification exceeded its fixed budget')
                    lexical = manager.memory.search('.', case[variant])
                    related = manager.memory_index.search('.', case[variant])
                    lexical_ids, related_ids = {r['id'] for r in lexical}, {r['id'] for r in related}
                    report['observations'].append({'case': case['id'], 'variant': variant,
                        'lexical': targets[case['id']] in lexical_ids,
                        'hybrid': targets[case['id']] in related_ids,
                        'cross_project_results': len((lexical_ids | related_ids) - allowed)})
                    self.assertTrue(all(r['scope'] == scope for r in [*lexical, *related]))
                    self.assertTrue(all(r['id'] not in allowed for r in manager.memory.search('other', case[variant])))
            observations = report['observations']
            counts = {variant: {kind: sum(r[kind] for r in observations if r['variant'] == variant)
                                for kind in ('lexical', 'hybrid')} for variant in ('literal', 'paraphrase')}
            cross = sum(r['cross_project_results'] for r in observations)
            checks = report['checks']
            checks['quality'] = (counts['literal']['hybrid'] >= counts['literal']['lexical']
                and counts['paraphrase']['hybrid'] / 32 >= .9
                and (counts['paraphrase']['hybrid'] - counts['paraphrase']['lexical']) / 32 >= .1 and cross == 0)
            report.update(counts=counts, cross_project_results=cross,
                          misses={v: [r['case'] for r in observations if r['variant'] == v and not r['hybrid']]
                                  for v in ('literal', 'paraphrase')})

            consumer = manager.store.conversation('Restarted file consumer')
            task = manager.start(consumer, 'Which flag does the Atlas compiler require? Cite the saved source.',
                'chat', self.config['model']['name'],
                settings={'temperature': 0., 'thinking': False, 'max_output': 256})
            deadline = time.monotonic() + 90
            while manager.running and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertFalse(manager.running)
            row = manager.store.latest_task(consumer)
            self.assertEqual(row['id'], task)
            result = json.loads(row['result'])
            self.assertEqual(result['status'], 'reported')
            self.assertIn('lavender', result['report'].casefold())
            self.assertIn(targets['atlas'], result['memory_sources'])
            self.assertIn('memory:' + targets['atlas'], result['report'])
            note = manager.memory.search('.', ident=targets['atlas'])
            self.assertEqual(note['file']['sha256'], hashlib.sha256(originals['facts-00.txt']).hexdigest())
            self.assertEqual((note['file']['start_char'], note['file']['end_char']), (0, 900))
            self.assertEqual((note['file']['start_line'], note['file']['end_line']), (1, 1))
            checks['restart_chat_citation_and_provenance'] = True
            for name, raw in originals.items():
                self.assertEqual((self.policy.root / name).read_bytes(), raw)
            changed = self.policy.root / 'facts-00.txt'
            changed.write_text('This file was independently changed after the saved snapshot.\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                manager.start(consumer, 'Which Atlas flag?', 'chat', self.config['model']['name'])
            self.assertEqual(manager.store.latest_task(consumer)['id'], task)
            self.assertEqual(manager.store.messages(consumer, for_model=True), [])
            self.assertTrue(manager.store.messages(consumer))
            with manager.store.connection() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM memory_vectors WHERE scope=?', (scope,)).fetchone()[0], 94)
            self.assertEqual(next(s for s in manager.memory_sources.list('.')
                                  if s['id'] == imported[0]['source'])['state'], 'stale')
            manager.memory_index.set_enabled('.', False)
            self.assertNotIn(targets['atlas'], {r['id'] for r in manager.memory.search('.', 'Atlas')})
            checks['changed_source_exclusion_and_history'] = True
            manager.memory.forget('.', targets['atlas'], confirmed=True)
            self.assertEqual(len(manager.memory_sources.list('.')), 15)
            self.assertEqual(changed.read_text(encoding='utf-8'),
                             'This file was independently changed after the saved snapshot.\n')
            checks['whole_source_forget_preserves_original'] = True
            manager.memory.before_delete(source_chat)
            manager.store.delete_conversation(source_chat)
            with manager.store.connection() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM memory_vectors WHERE scope=?', (scope,)).fetchone()[0], 0)
                self.assertEqual(db.execute('SELECT count(*) FROM memories WHERE scope=?', (scope,)).fetchone()[0], 0)
            self.assertEqual(manager.memory_sources.list('.'), [])
            self.assertEqual(len(manager.memory.search('other')), 32)
            for name, raw in originals.items():
                if name != changed.name:
                    self.assertEqual((self.policy.root / name).read_bytes(), raw)
            checks['source_chat_cascade_and_other_project_preserved'] = True
            report['status'] = 'complete'
            report['gate_passed'] = all(checks.values())
            self.assertTrue(report['gate_passed'], f'Fixed integrated retrieval gate failed: {counts}; no tuning/retry')
        finally:
            manager.close()
            report['seconds'] = time.monotonic() - started
            with (output / 'report.json').open('x', encoding='utf-8') as stream:
                json.dump(report, stream, indent=2)
            print('Integrated file-memory qualification: ' + json.dumps({
                'report': str(output / 'report.json'), 'status': report['status'],
                'gate_passed': report.get('gate_passed', False), 'counts': report.get('counts'),
                'cross_project_results': report.get('cross_project_results')}))
