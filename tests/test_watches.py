"""Real SQLite debounce/trigger state and supervised workers with fixed model protocol fixtures."""
import json
import multiprocessing
import os
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from unittest.mock import patch

from local_agent.safety import Denied
from local_agent.studio import migrations, probes, watches, work_queue
from local_agent.studio.directory_snapshot import observe
from local_agent.studio.manager import Manager
from local_agent.studio.restore_gate import RestoreGate
from local_agent.studio.retention import Retention
from local_agent.studio.schedules import Scheduler
from local_agent.studio.store import Store

from .inspection_support import InspectionProcessFixture
from .support import WorkspaceTest


def accept_crash(config, ident, value, stamp, phase):
    manager = Manager(config)
    scheduler = Scheduler(manager, RestoreGate(), clock=lambda: stamp)
    original = work_queue.insert

    def fail(*args):
        original(*args)
        os._exit(71)

    if phase == 'before_commit':
        with patch.object(work_queue, 'insert', fail):
            scheduler.watches.accept(ident, value, (manager.admission_epoch, scheduler.revision), 0)
    else:
        scheduler.watches.accept(ident, value, (manager.admission_epoch, scheduler.revision), 0)
    os._exit(72)


class WatchFixture:
    def setUp(self):
        super().setUp()
        self.manager = Manager(self.config)
        self.addCleanup(self.manager.close)
        self.store = self.manager.store
        self.chat = self.store.conversation('Directory watch fixture')
        (self.policy.root / 'a.py').write_text('# selected code', encoding='utf-8')
        self.clock = [time.time_ns() // 1_000_000]
        self.scheduler = Scheduler(self.manager, RestoreGate(), clock=lambda: self.clock[0])
        self.addCleanup(self.scheduler.stop)
        self.watches = self.scheduler.watches

    def create(self, **changes):
        data = {'conversation': self.chat, 'objective': 'Inspect selected code', 'model': self.config['model']['name'],
                'project': '.', 'files': ['a.py'], 'options': {}, 'directory': '.', 'debounce_ms': 1000}
        data.update(changes)
        return self.watches.create(**data)

    def observed(self):
        data = observe(self.policy)
        return {key: data[key] for key in ('scope', 'fingerprint', 'complete', 'stop_reason', 'counts')}

    def accept(self, ident, value=None, *, epoch=None, revision=None):
        if revision is None:
            with self.store.connection() as db:
                revision = watches.load(db, ident)['revision']
        self.watches.accept(ident, value or self.observed(),
            epoch or (self.manager.admission_epoch, self.scheduler.revision), revision)

    def change(self, text='# changed code'):
        (self.policy.root / 'a.py').write_text(text, encoding='utf-8')

    def queued_change(self, ident):
        self.accept(ident)
        self.change()
        self.accept(ident)
        self.clock[0] += 1000
        self.accept(ident)


class WatchTests(WatchFixture, WorkspaceTest):
    def test_actual_process_crash_and_lost_commit_ack_preserve_one_generation_without_replay(self):
        ident = self.create()
        self.accept(ident)
        self.change()
        value = self.observed()
        self.accept(ident, value)
        self.clock[0] += 1000
        for phase in ('before_commit', 'after_commit'):
            process = multiprocessing.get_context('spawn').Process(target=accept_crash,
                args=(self.config, ident, value, self.clock[0], phase))
            process.start()
            process.join(8)
            try:
                self.assertFalse(process.is_alive())
                self.assertEqual(process.exitcode, 71 if phase == 'before_commit' else 72)
            finally:
                if process.is_alive():
                    process.kill()
                    process.join(3)
                process.close()
            self.assertEqual(self.watches.summary()['items'][0]['generation'], 0 if phase == 'before_commit' else 1)
        self.accept(ident, value)
        self.assertEqual(self.watches.summary()['items'][0]['generation'], 1)
        self.assertEqual(self.store.tasks(), [])

    def test_cross_chat_run_reference_blocks_retention_and_preserves_both_histories(self):
        ident = self.create()
        self.queued_change(ident)
        other = self.store.conversation('Kept foreign watch')
        linked = self.create(conversation=other)
        self.watches.enabled(ident, False)
        self.watches.enabled(linked, False)
        with self.store.connection() as db:
            db.execute('UPDATE conversations SET created=1')
            db.execute('UPDATE directory_runs SET watch=?', (linked,))
        service = Retention(self.manager)
        service.save({'older_than_days': 1, 'keep_recent': 0, 'batch_size': 20})
        with self.assertRaisesRegex(Denied, 'watch relationships'):
            service.preview([other])
        self.assertEqual(len(self.store.conversations()), 2)

    def test_cross_source_link_is_blocked_before_model_admission(self):
        ident = self.create()
        self.queued_change(ident)
        job = self.watches.summary()['items'][0]['last']['id']
        with self.store.connection() as db:
            queued = work_queue.load(db, job)
            schedule = 'd' * 32
            db.execute("INSERT INTO interval_schedules VALUES (?,?,?,?,1,60000,?,'coalesce','UTC','ready',?)",
                (schedule, self.chat, queued['payload'], queued['sha256'], self.clock[0] + 60000, self.clock[0]))
            db.execute('INSERT INTO schedule_runs VALUES (?,?,?)', (job, schedule, self.clock[0]))
        with patch('local_agent.studio.model_probe.identity', side_effect=AssertionError('Ambiguous source must not contact model')):
            self.scheduler.dispatch()
        self.assertEqual(self.scheduler.queue.summary(job)['state'], 'blocked')
        self.assertEqual(self.store.tasks(), [])

    def test_initial_baseline_and_matching_debounce_queue_one_durable_generation(self):
        ident = self.create()
        self.accept(ident)
        self.assertEqual(self.watches.summary()['items'][0]['status'], 'ready')
        self.assertEqual(self.store.tasks(), [])
        self.change()
        self.accept(ident)
        self.assertEqual(self.watches.summary()['items'][0]['status'], 'debouncing')
        self.clock[0] += 999
        self.accept(ident)
        self.assertIsNone(self.watches.summary()['items'][0]['last'])
        self.clock[0] += 1
        self.accept(ident)
        first = self.watches.summary()['items'][0]['last']
        self.assertEqual(first['state'], 'queued')
        restarted = Scheduler(self.manager, RestoreGate(), clock=lambda: self.clock[0])
        restarted.watches.accept(ident, self.observed(), (self.manager.admission_epoch, restarted.revision), 0)
        self.assertEqual(restarted.watches.summary()['items'][0]['last'], first)
        with self.store.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM directory_runs').fetchone()[0], 1)

    def test_incomplete_observation_resets_debounce_and_never_advances_baseline(self):
        ident = self.create()
        self.accept(ident)
        self.change()
        self.accept(ident)
        with self.store.connection() as db:
            baseline = watches.load(db, ident)['baseline']
        invalid = {**self.observed(), 'complete': False, 'fingerprint': None, 'stop_reason': 'time_limit'}
        self.clock[0] += 10000
        self.accept(ident, invalid)
        with self.store.connection() as db:
            row = watches.load(db, ident)
            self.assertEqual(row['baseline'], baseline)
            self.assertIsNone(row['candidate'])
        self.accept(ident)
        self.assertIsNone(self.watches.summary()['items'][0]['last'])
        self.assertEqual(self.watches.summary()['items'][0]['status'], 'debouncing')

    def test_pending_changes_coalesce_but_new_state_after_consumption_has_new_trigger(self):
        ident = self.create()
        self.queued_change(ident)
        first = self.watches.summary()['items'][0]['last']
        self.change('# second changed state')
        self.accept(ident)
        self.clock[0] += 1000
        self.accept(ident)
        self.assertEqual(self.watches.summary()['items'][0]['last'], first)
        self.scheduler.queue.cancel(first['id'])
        self.change('# third changed state')
        self.accept(ident)
        self.clock[0] += 1000
        self.accept(ident)
        second = self.watches.summary()['items'][0]
        self.assertEqual(second['generation'], 2)
        self.assertNotEqual(second['last']['id'], first['id'])

    def test_concurrent_observation_and_failed_insert_preserve_one_atomic_generation(self):
        ident = self.create()
        self.accept(ident)
        self.change()
        value = self.observed()
        self.accept(ident, value)
        self.clock[0] += 1000
        original = work_queue.insert

        def fail(*args):
            original(*args)
            raise sqlite3.OperationalError('Injected after trigger insertion')

        with patch.object(work_queue, 'insert', fail), self.assertRaises(sqlite3.Error):
            self.accept(ident, value)
        self.assertIsNone(self.watches.summary()['items'][0]['last'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: self.accept(ident, value), range(2)))
        self.assertEqual(self.watches.summary()['items'][0]['generation'], 1)
        with self.store.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM workflow_queue').fetchone()[0], 1)

    def test_disable_invalidates_old_observation_and_pending_claim_and_reenable_rebaselines(self):
        ident = self.create()
        self.queued_change(ident)
        claim = self.scheduler.queue.claim(automatic_only=True)
        epoch = (self.manager.admission_epoch, self.scheduler.revision)
        self.watches.enabled(ident, False)
        self.assertEqual(self.watches.summary()['items'][0]['last']['state'], 'cancelled')
        with self.assertRaises(ValueError):
            self.accept(ident, epoch=epoch, revision=0)
        with self.assertRaises(ValueError):
            self.watches.check_admission(claim, ident, epoch)
        self.watches.enabled(ident, True)
        self.scheduler.abort.clear()
        self.accept(ident)
        self.assertEqual(self.watches.summary()['items'][0]['status'], 'ready')
        self.assertEqual(self.watches.summary()['items'][0]['generation'], 1)

    def test_stop_pause_restore_identity_and_scope_changes_do_not_create_tasks(self):
        ident = self.create()
        self.scheduler.set_paused(True)
        with self.assertRaises(ValueError):
            self.accept(ident)
        self.scheduler.set_paused(False)
        self.scheduler.abort.clear()
        self.store.identity = uuid.uuid4().hex
        with self.assertRaises(ValueError):
            self.accept(ident)
        self.watches.poll()
        self.assertFalse(self.watches.summary()['items'][0]['enabled'])
        self.assertEqual(self.watches.summary()['items'][0]['status'], 'input_changed')
        (self.policy.state / 'STOP').touch()
        with self.assertRaises(Denied):
            self.create()
        self.assertEqual(self.store.tasks(), [])

    def test_forged_frame_payload_conversation_or_trigger_cannot_expand_authority(self):
        ident = self.create()
        for change in ({'scope': 'x' * 64}, {'complete': 1}, {'fingerprint': 'x'}, {'token': 'PRIVATE-CANARY'},
                       {'counts': {'entries': True, 'files': 0, 'attempted_files': 0, 'bytes_read': 0}}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.accept(ident, {**self.observed(), **change})
        self.queued_change(ident)
        claim = self.scheduler.queue.claim(automatic_only=True)
        other = self.store.conversation('Foreign queue context')
        with self.store.connection() as db:
            original = work_queue.load(db, claim.job)
        data = json.loads(original['payload'])
        data['objective'] = 'Changed pending work'
        text = work_queue.encode(data)
        for changes in ({'conversation': other}, {'request_key': 'c' * 64},
                        {'payload': text, 'sha256': watches.hashlib.sha256(text.encode()).hexdigest()}):
            with self.store.connection() as db:
                values = {key: original[key] for key in ('conversation', 'request_key', 'payload', 'sha256')}
                values.update(changes)
                db.execute('UPDATE workflow_queue SET conversation=?,request_key=?,payload=?,sha256=? WHERE id=?',
                           (*values.values(), claim.job))
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.watches.check_admission(claim, ident, (self.manager.admission_epoch, self.scheduler.revision))
        self.assertEqual(self.store.tasks(), [])

    def test_self_state_and_generated_cache_output_does_not_create_trigger(self):
        ident = self.create()
        self.accept(ident)
        cache = self.policy.root / '__pycache__'
        cache.mkdir()
        (cache / 'source.pyc').write_bytes(b'owned generated data')
        (self.policy.state / 'audit.jsonl').write_text('PRIVATE-AUDIT-CANARY')
        self.accept(ident)
        self.clock[0] += 2000
        self.accept(ident)
        self.assertIsNone(self.watches.summary()['items'][0]['last'])
        self.assertNotIn('PRIVATE-', json.dumps(self.watches.summary()))

    def test_security_bounds_and_malformed_saved_record_are_safe(self):
        for change in ({'directory': '../outside'}, {'directory': '.git'}, {'files': ['.env']},
                       {'debounce_ms': True}, {'debounce_ms': 999}, {'options': {'endpoint': 'remote'}}):
            with self.subTest(change=change), self.assertRaises((ValueError, Denied)):
                self.create(**change)
        with patch.object(watches, 'MAX_WATCHES', 0), self.assertRaises(ValueError):
            self.create()
        self.create()
        with self.store.connection() as db:
            db.execute("UPDATE directory_watches SET candidate='PRIVATE-MALFORMED-CANARY'")
        summary = self.watches.summary()
        self.assertEqual(summary['items'][0]['status'], 'invalid')
        self.assertNotIn('PRIVATE-', json.dumps(summary))
        with self.store.connection() as db:
            db.execute("UPDATE directory_watches SET id='PRIVATE-CREDENTIAL-ID-CANARY'")
        summary = self.watches.summary()
        self.assertEqual(summary['invalid_records'], 1)
        self.assertEqual(summary['items'], [])
        self.assertNotIn('PRIVATE-', json.dumps(summary))

    def test_enabled_watch_retention_and_exact_disabled_rows_cascade(self):
        ident = self.create()
        self.queued_change(ident)
        with self.store.connection() as db:
            db.execute('UPDATE conversations SET created=1')
        service = Retention(self.manager)
        service.save({'older_than_days': 1, 'keep_recent': 0, 'batch_size': 20})
        self.assertEqual(service.preview()['items'], [])
        self.watches.enabled(ident, False)
        preview = service.preview()
        self.assertEqual(preview['counts']['directory_watches'], 1)
        self.assertEqual(preview['counts']['directory_runs'], 1)
        with self.store.connection() as db:
            db.execute('UPDATE directory_watches SET next_ms=next_ms+1')
        with self.assertRaises(Denied):
            service.apply(preview['id'], confirmed=True)
        preview = service.preview()
        service.apply(preview['id'], confirmed=True)
        with self.store.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM directory_watches').fetchone()[0], 0)

    def test_v7_upgrade_rolls_back_ddl_and_preserves_prior_history_and_identity(self):
        path = self.policy.state / 'v7.sqlite3'
        required = {key: value for key, value in migrations.REQUIRED.items() if key not in {'directory_watches', 'directory_runs', 'memory_indexes', 'memory_vectors', 'memory_file_sources', 'memory_file_chunks'}}
        with patch.object(migrations, 'MIGRATIONS', migrations.MIGRATIONS[:7]), \
                patch.object(migrations, 'SCHEMA_VERSION', 7), patch.object(migrations, 'REQUIRED', required):
            old = Store(path)
            chat = old.conversation('Retained history')
            old.message(chat, 'user', 'Retain across migration')

        def fail(db):
            migrations.directory_watches(db)
            raise RuntimeError('Injected watch migration failure')

        with patch.object(migrations, 'MIGRATIONS', (*migrations.MIGRATIONS[:7], ('directory_watches', fail))), self.assertRaises(RuntimeError):
            Store(path)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 7)
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_schema WHERE name='directory_watches'").fetchone())
        current = Store(path)
        self.assertEqual(current.identity, old.identity)
        self.assertEqual(current.messages(chat)[0]['content'], 'Retain across migration')


class WatchProcessTests(InspectionProcessFixture, WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.scheduler = Scheduler(self.manager, RestoreGate())
        self.manager.scheduler = self.scheduler
        self.addCleanup(self.scheduler.stop)
        self.watches = self.scheduler.watches
        self.ident = self.watches.create(self.chat, 'Inspect selected files', self.config['model']['name'], '.',
            ['a.py', 'b.py'], {}, '.', 1000)

    def due(self):
        with self.store.connection() as db:
            db.execute('UPDATE directory_watches SET next_ms=0')

    def changed(self):
        (self.policy.root / 'a.py').write_text('def add(a,b):\n    return a+b+0\n', encoding='utf-8')
        self.due()
        self.scheduler.tick()
        with self.store.connection() as db:
            db.execute('UPDATE directory_watches SET next_ms=0,candidate_ms=candidate_ms-1000')

    def test_real_observation_and_inspection_worker_coordinate_one_read_only_generation(self):
        self.scheduler.tick()
        self.assertEqual(self.requests, [])
        self.assertEqual(self.watches.summary()['items'][0]['status'], 'ready')
        self.changed()
        self.scheduler.tick()
        self.wait_until(lambda: not self.manager.running)
        row = self.watches.summary()['items'][0]
        self.assertEqual(row['last']['task_status'], 'reported')
        self.assertEqual({op['tool'] for op in self.store.journal(row['last']['task'])['operations']}, {'read_file'})
        self.due()
        self.scheduler.tick()
        self.assertEqual(len(self.store.tasks()), 1)
        self.assertFalse(self.manager.pending())

    def test_disabled_late_observation_and_restore_drain_never_start_a_task(self):
        entered, gate = threading.Event(), threading.Event()
        original = probes.run

        def delayed(kind, *args, **kwargs):
            if kind == 'directory':
                entered.set()
                gate.wait(3)
            return original(kind, *args, **kwargs)

        with patch.object(probes, 'run', delayed):
            thread = threading.Thread(target=self.scheduler.tick)
            thread.start()
            self.assertTrue(entered.wait(3))
            self.watches.enabled(self.ident, False)
            gate.set()
            thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertFalse(self.watches.summary()['items'][0]['enabled'])
        self.assertEqual(self.store.tasks(), [])
