"""Real durable schedule state and owned preflight/worker tests; no real model quality claim."""
import copy
import json
import multiprocessing
import os
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from unittest.mock import Mock, patch

from local_agent.safety import Denied
from local_agent.studio import migrations, model_probe, probes, schedules
from local_agent.studio.manager import Manager
from local_agent.studio.restore_gate import RestoreGate
from local_agent.studio.retention import Retention
from local_agent.studio.schedules import Scheduler, timing
from local_agent.studio.store import Store

from .inspection_support import InspectionProcessFixture
from .support import WorkspaceTest


def advance_crash(config, stamp, phase):
    manager = Manager(config)
    scheduler = Scheduler(manager, RestoreGate(), clock=lambda: stamp)
    original = schedules.work_queue.insert

    def fail(*args):
        original(*args)
        os._exit(71)

    if phase == 'before_commit':
        with patch.object(schedules.work_queue, 'insert', fail):
            scheduler.advance()
    else:
        scheduler.advance()
    os._exit(72)


class ScheduleFixture:
    def setUp(self):
        super().setUp()
        self.manager = Manager(self.config)
        self.addCleanup(self.manager.close)
        self.store = self.manager.store
        self.chat = self.store.conversation('Schedule fixture')
        (self.policy.root / 'a.py').write_text('# selected input\n', encoding='utf-8')
        self.clock = [time.time_ns() // 1_000_000]
        self.scheduler = Scheduler(self.manager, RestoreGate(), clock=lambda: self.clock[0])
        self.addCleanup(self.scheduler.stop)

    def create(self, **change):
        args = {'conversation': self.chat, 'objective': 'Inspect this file', 'model': self.config['model']['name'],
                'project': '.', 'files': ['a.py'], 'options': {}, 'interval_ms': 60000,
                'misfire': 'coalesce', 'timezone': 'America/Toronto'}
        args.update(change)
        return self.scheduler.create(**args)

    def due(self):
        self.clock[0] += 60000
        self.scheduler.advance()


class ScheduleTests(ScheduleFixture, WorkspaceTest):
    def test_claim_cannot_admit_changed_request_or_foreign_conversation_through_a_schedule_link(self):
        ident = self.create()
        self.due()
        claim = self.scheduler.queue.claim(scheduled_only=True)
        epoch = (self.manager.admission_epoch, self.scheduler.revision)
        with self.store.connection() as db:
            original = dict(db.execute('SELECT * FROM workflow_queue WHERE id=?', (claim.job,)).fetchone())
        data = json.loads(original['payload'])
        data['objective'] = 'Different work must not inherit this schedule authority'
        text = schedules.work_queue.encode(data)
        with self.store.connection() as db:
            db.execute('UPDATE workflow_queue SET payload=?,sha256=? WHERE id=?',
                (text, schedules.hashlib.sha256(text.encode()).hexdigest(), claim.job))
        with self.assertRaises(ValueError):
            self.scheduler.check_admission(claim, ident, epoch)
        other = self.store.conversation('Foreign queue conversation')
        with self.store.connection() as db:
            db.execute('UPDATE workflow_queue SET payload=?,sha256=?,conversation=? WHERE id=?',
                (original['payload'], original['sha256'], other, claim.job))
        with self.assertRaises(ValueError):
            self.scheduler.check_admission(claim, ident, epoch)
        self.assertEqual(self.store.tasks(), [])

    def test_malformed_latest_run_fields_are_not_published_as_private_or_valid_state(self):
        ident = self.create()
        self.due()
        job = self.scheduler.summary()['items'][0]['last']['id']
        from .inspection_support import spec_for
        spec = spec_for(self.config, self.store, self.chat, files=['a.py'])
        task = self.store.task(self.chat, 'inspection', self.config['model']['name'], profile='coding',
            project='.', scope_key=spec['scope'], inspection={'spec': spec, 'agent': None})
        self.store.complete(task, {'status': 'reported', 'report': 'Fixture'})
        with self.store.connection() as db:
            db.execute("UPDATE workflow_queue SET state='admitted',task=? WHERE id=?", (task, job))
        self.assertEqual(self.scheduler.summary()['items'][0]['status'], 'ready')
        for field in ('state', 'task_status', 'due_ms', 'next_ms'):
            with self.subTest(field=field):
                with self.store.connection() as db:
                    db.execute("UPDATE workflow_queue SET state='admitted' WHERE id=?", (job,))
                    db.execute("UPDATE tasks SET status='reported' WHERE id=?", (task,))
                    db.execute('UPDATE schedule_runs SET due_ms=? WHERE job=?', (self.clock[0], job))
                    db.execute('UPDATE interval_schedules SET next_ms=? WHERE id=?', (self.clock[0] + 60000, ident))
                    table, column, key = {'state': ('workflow_queue', 'state', 'id'),
                        'task_status': ('tasks', 'status', 'id'), 'due_ms': ('schedule_runs', 'due_ms', 'job'),
                        'next_ms': ('interval_schedules', 'next_ms', 'id')}[field]
                    value = 2**63 - 1 if field.endswith('_ms') else 'PRIVATE-INVALID-STATUS-CANARY'
                    target = task if field == 'task_status' else ident if field == 'next_ms' else job
                    db.execute(f'UPDATE {table} SET {column}=? WHERE {key}=?', (value, target))
                summary = self.scheduler.summary()
                self.assertEqual(summary['items'][0]['status'], 'invalid')
                self.assertNotIn('PRIVATE-INVALID', json.dumps(summary))

    def test_real_process_crash_rolls_back_or_preserves_slot_and_queue_together(self):
        self.create()
        self.clock[0] += 60000
        for phase in ('before_commit', 'after_commit'):
            process = multiprocessing.get_context('spawn').Process(target=advance_crash,
                args=(self.config, self.clock[0], phase))
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
            with self.store.connection() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM schedule_runs').fetchone()[0], 0 if phase == 'before_commit' else 1)
        self.scheduler.advance()
        with self.store.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM schedule_runs').fetchone()[0], 1)

    def test_elapsed_utc_boundaries_explicit_skip_coalesce_and_clock_backwards(self):
        for base in (0, 1772951400000, 1793511000000):  # Includes spring/autumn transition windows.
            self.assertEqual(timing(base, 60000, base - 1 if base else 0, 'coalesce'),
                             (None, base) if base else (0, 60000))
            self.assertEqual(timing(base, 60000, base + 180001, 'coalesce'), (base + 180000, base + 240000))
            self.assertEqual(timing(base, 60000, base + 180001, 'skip'), (None, base + 240000))
            self.assertEqual(timing(base, 60000, base + 59999, 'skip'), (base, base + 60000))
        for interval in (True, '60000', 59999, 2592000001):
            with self.assertRaises(ValueError):
                timing(0, interval, 0, 'coalesce')

    def test_duplicate_due_concurrent_restart_and_busy_slots_keep_one_pending(self):
        ident = self.create()
        self.clock[0] += 60000
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: self.scheduler.advance(), range(2)))
        self.assertEqual(len(self.scheduler.summary()['items']), 1)
        last = self.scheduler.summary()['items'][0]['last']
        self.assertEqual(last['state'], 'queued')
        other = Scheduler(self.manager, RestoreGate(), clock=lambda: self.clock[0])
        other.advance()
        self.clock[0] += 20 * 60000
        other.advance()
        self.assertEqual(other.summary()['items'][0]['last'], last)
        with self.store.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM schedule_runs').fetchone()[0], 1)
        self.scheduler.enabled(ident, False)
        self.assertEqual(self.scheduler.summary()['items'][0]['last']['state'], 'cancelled')
        self.clock[0] += 60000
        self.scheduler.advance()
        self.assertEqual(self.scheduler.summary()['items'][0]['last']['id'], last['id'])

    def test_due_and_queue_insert_roll_back_together_and_current_files_are_not_frozen(self):
        ident = self.create()
        before = self.scheduler.summary()['items'][0]['next_ms']
        self.clock[0] += 60000
        insert = schedules.work_queue.insert

        def fail(*args):
            insert(*args)
            raise sqlite3.OperationalError('Injected after queue insertion')

        with patch.object(schedules.work_queue, 'insert', fail), self.assertRaises(sqlite3.Error):
            self.scheduler.advance()
        self.assertEqual(self.scheduler.summary()['items'][0]['next_ms'], before)
        with self.store.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM workflow_queue').fetchone()[0], 0)
        (self.policy.root / 'a.py').write_text('# changed input is expected each interval\n', encoding='utf-8')
        self.scheduler.advance()
        self.assertEqual(self.scheduler.summary()['items'][0]['last']['state'], 'queued')
        self.assertEqual(self.scheduler.summary()['items'][0]['id'], ident)

    def test_scope_replacement_restored_store_stop_and_invalid_records_fail_closed(self):
        self.create()
        self.store.identity = uuid.uuid4().hex
        self.due()
        self.assertEqual(self.scheduler.summary()['items'][0]['status'], 'input_changed')
        self.assertEqual(self.store.tasks(), [])
        with self.store.connection() as db:
            db.execute("UPDATE interval_schedules SET payload='PRIVATE-MALFORMED-CANARY'")
        summary = self.scheduler.summary()
        self.assertEqual(summary['items'][0]['status'], 'invalid')
        self.assertNotIn('PRIVATE-MALFORMED', json.dumps(summary))
        with self.store.connection() as db:
            db.execute("UPDATE interval_schedules SET id='PRIVATE-CREDENTIAL-ID-CANARY'")
        self.assertEqual(self.scheduler.summary()['items'], [])
        self.assertNotIn('PRIVATE-', json.dumps(self.scheduler.summary()))
        (self.policy.state / 'STOP').touch()
        with self.assertRaises(Denied):
            self.scheduler.advance()

    def test_security_bounds_and_global_pause_survive_restart_but_disable_remains_available(self):
        for change in ({'timezone': 'Unknown/Zone'}, {'files': ['../outside']}, {'files': ['.env']},
                       {'options': {'endpoint': 'http://external'}}, {'misfire': 'replay_all'}):
            with self.assertRaises((ValueError, Denied)):
                self.create(**change)
        with patch.object(schedules, 'MAX_SCHEDULES', 0), self.assertRaises(ValueError):
            self.create()
        ident = self.create()
        self.scheduler.set_paused(True)
        other = Scheduler(self.manager, RestoreGate())
        self.assertTrue(other.summary()['paused'])
        self.scheduler.enabled(ident, False)
        with self.assertRaises(ValueError):
            self.scheduler.advance()
        self.scheduler.set_paused(False)
        self.assertFalse(other.summary()['paused'])

    def test_retention_protects_enabled_and_hashes_disabled_schedules_and_run_relationships(self):
        ident = self.create()
        self.due()
        with self.store.connection() as db:
            db.execute('UPDATE conversations SET created=1')
        retention = Retention(self.manager)
        retention.save({'older_than_days': 1, 'keep_recent': 0, 'batch_size': 20})
        self.assertEqual(retention.preview()['items'], [])
        self.scheduler.enabled(ident, False)
        preview = retention.preview()
        self.assertEqual(preview['counts']['interval_schedules'], 1)
        self.assertEqual(preview['counts']['schedule_runs'], 1)
        with self.store.connection() as db:
            db.execute('UPDATE interval_schedules SET next_ms=next_ms+1')
        with self.assertRaises(Denied):
            retention.apply(preview['id'], confirmed=True)
        preview = retention.preview()
        retention.apply(preview['id'], confirmed=True)
        with self.store.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM interval_schedules').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM schedule_runs').fetchone()[0], 0)

    def test_v6_upgrade_rollback_preserves_queue_and_history(self):
        path = self.policy.state / 'v6.sqlite3'
        required = {k: v for k, v in migrations.REQUIRED.items()
                    if k not in {'interval_schedules', 'schedule_runs', 'directory_watches', 'directory_runs', 'memory_indexes', 'memory_vectors', 'memory_file_sources', 'memory_file_chunks'}}
        with patch.object(migrations, 'MIGRATIONS', migrations.MIGRATIONS[:6]), \
                patch.object(migrations, 'SCHEMA_VERSION', 6), patch.object(migrations, 'REQUIRED', required):
            old = Store(path)
            chat = old.conversation('Retain old history')
            old.message(chat, 'user', 'Kept through schema upgrade')

        def fail(db):
            migrations.interval_schedules(db)
            raise RuntimeError('Injected after schedule DDL')

        with patch.object(migrations, 'MIGRATIONS', (*migrations.MIGRATIONS[:6], ('interval_schedules', fail))), \
                self.assertRaises(RuntimeError):
            Store(path)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 6)
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_schema WHERE name='interval_schedules'").fetchone())
        upgraded = Store(path)
        self.assertEqual(upgraded.identity, old.identity)
        self.assertEqual(upgraded.messages(chat)[0]['content'], 'Kept through schema upgrade')

    def test_replaced_root_is_disabled_without_mutation(self):
        directory = self.policy.root / 'project'
        directory.mkdir()
        (directory / 'a.py').write_text('# inspected', encoding='utf-8')
        chat = self.store.conversation('Other project')
        ident = self.create(conversation=chat, project='project')
        moved = self.policy.root / 'saved-project'
        directory.rename(moved)
        directory.mkdir()
        (directory / 'a.py').write_text('# new occupant', encoding='utf-8')
        self.due()
        self.assertEqual(next(row for row in self.scheduler.summary()['items'] if row['id'] == ident)['status'], 'input_changed')
        self.assertEqual(self.store.tasks(), [])

    def test_retention_rejects_cross_chat_run_links_and_preserves_both_histories(self):
        ident = self.create()
        self.due()
        self.scheduler.enabled(ident, False)
        other = self.store.conversation('Kept other schedule')
        linked = self.create(conversation=other)
        self.scheduler.enabled(linked, False)
        with self.store.connection() as db:
            db.execute('UPDATE conversations SET created=1')
            db.execute('UPDATE schedule_runs SET schedule=?', (linked,))
        retention = Retention(self.manager)
        retention.save({'older_than_days': 1, 'keep_recent': 0, 'batch_size': 20})
        with self.assertRaisesRegex(Denied, 'schedule relationships'):
            retention.preview([other])
        self.assertEqual(len(self.store.conversations()), 2)

    def test_timer_start_failure_is_visible_and_cleanup_remains_safe(self):
        with patch.object(threading.Thread, 'start', side_effect=RuntimeError('Injected start failure')), self.assertRaises(RuntimeError):
            self.scheduler.start()
        self.assertIsNone(self.scheduler.thread)
        self.scheduler.stop()


class ScheduleProcessTests(InspectionProcessFixture, WorkspaceTest):
    def test_preflight_constructor_failure_closes_both_real_pipe_ends(self):
        context = multiprocessing.get_context('spawn')
        parent, child = context.Pipe()
        fake = Mock()
        fake.Pipe.return_value = parent, child
        fake.Process.side_effect = RuntimeError('Injected constructor failure')
        with patch.object(probes.multiprocessing, 'get_context', return_value=fake), self.assertRaises(RuntimeError):
            model_probe.identity(self.config['model'], threading.Event())
        self.assertTrue(parent.closed and child.closed)
        self.assertEqual(self.requests, [])

    def test_preflight_job_failure_reaps_only_new_child_before_any_peer_request(self):
        if os.name != 'nt':
            self.skipTest('Windows ownership boundary')
        import psutil
        before = {child.pid for child in psutil.Process().children()}
        with patch('local_agent.windows_job.WindowsJob', side_effect=OSError('Injected Job failure')), self.assertRaises(ValueError):
            model_probe.identity(self.config['model'], threading.Event())
        self.assertEqual({child.pid for child in psutil.Process().children()} - before, set())
        self.assertEqual(self.requests, [])
        self.assertFalse(self.metadata_entered.is_set())

    def setUp(self):
        super().setUp()
        self.scheduler = Scheduler(self.manager, RestoreGate())
        self.manager.scheduler = self.scheduler
        self.addCleanup(self.scheduler.stop)
        self.ident = self.scheduler.create(self.chat, 'Inspect selected files', self.config['model']['name'], '.',
            ['a.py', 'b.py'], {}, 60000, 'coalesce', 'America/Toronto')

    def make_due(self):
        with self.store.connection() as db:
            db.execute('UPDATE interval_schedules SET next_ms=?', (time.time_ns() // 1_000_000 - 1,))

    def test_owned_metadata_and_real_worker_finish_one_read_only_run_without_replay(self):
        self.make_due()
        self.scheduler.tick()
        self.wait_until(lambda: not self.manager.running)
        row = self.scheduler.summary()['items'][0]
        self.assertEqual(row['last']['task_status'], 'reported')
        self.assertEqual({item['tool'] for item in self.store.journal(row['last']['task'])['operations']}, {'read_file'})
        self.scheduler.tick()
        self.assertEqual(len(self.store.tasks()), 1)
        self.assertFalse(self.manager.pending())
        choices = [request for request in self.requests if request.get('tools')]
        self.assertTrue(choices)
        self.assertEqual({tool['function']['name'] for request in choices for tool in request['tools']}, {'read_file'})

    def test_busy_queue_expired_owner_and_disabled_preflight_do_not_start_late(self):
        self.make_due()
        self.manager.running['busy'] = {'done': True}
        try:
            self.scheduler.tick()
            self.assertEqual(self.scheduler.summary()['items'][0]['last']['state'], 'queued')
        finally:
            self.manager.running.clear()
        gate, entered = threading.Event(), threading.Event()

        def delayed(*args, **kwargs):
            entered.set()
            gate.wait(3)
            return {'digest': 'a' * 64, 'server_version': '0.40.7'}

        with patch.object(model_probe, 'identity', delayed):
            thread = threading.Thread(target=self.scheduler.tick)
            thread.start()
            self.assertTrue(entered.wait(3))
            self.scheduler.enabled(self.ident, False)
            self.scheduler.enabled(self.ident, True)
            gate.set()
            thread.join(4)
            self.assertFalse(thread.is_alive())
        self.assertEqual(self.store.tasks(), [])
        self.assertEqual(self.scheduler.summary()['items'][0]['last']['state'], 'cancelled')

    def test_emergency_stop_persists_pause_and_shutdown_stops_timer_without_other_process_kills(self):
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(45)'])
        def close():
            if unrelated.poll() is None:
                unrelated.kill()
            unrelated.wait(3)
        self.addCleanup(close)
        self.make_due()
        self.scheduler.start()
        self.manager.close()
        self.assertTrue(self.scheduler.summary()['paused'])
        self.scheduler.tick()
        self.assertEqual(self.store.tasks(), [])
        self.manager.close(shutdown=True)
        self.assertFalse(self.scheduler.thread.is_alive())
        self.assertIsNone(unrelated.poll())

    def test_owned_metadata_cancellation_and_timeout_are_bounded_for_a_dripping_peer(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        class Drip(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                try:
                    for _ in range(40):
                        self.wfile.write(b'H')
                        self.wfile.flush()
                        time.sleep(.05)
                except ConnectionError:
                    pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Drip)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        config = {**copy.deepcopy(self.config['model']), 'url': f'http://127.0.0.1:{server.server_port}'}
        for cancelled in (False, True):
            event = threading.Event()
            if cancelled:
                event.set()
            started = time.monotonic()
            with self.assertRaises(ValueError):
                model_probe.identity(config, event, timeout=.4)
            self.assertLess(time.monotonic() - started, 4)

    def test_restore_freeze_counts_active_scheduler_preflight_and_shutdown_drains_it(self):
        self.metadata_gate.clear()
        self.make_due()
        self.scheduler.start()
        self.assertTrue(self.metadata_entered.wait(5))
        gate = self.scheduler.gate
        self.assertTrue(gate.enter())  # Represents the already authorized activation request.
        try:
            with self.assertRaises(TimeoutError), gate.freeze(timeout=.1):
                self.fail('Restore must not pass an active owned metadata probe')
        finally:
            gate.leave()
        self.manager.close(shutdown=True)
        self.metadata_gate.set()
        self.assertFalse(self.scheduler.thread.is_alive())
        self.assertEqual(gate.requests, 0)
        self.assertEqual(self.store.tasks(), [])
