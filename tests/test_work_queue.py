"""Durable admission leases, actual SQLite crash boundaries and supervised read-only tasks."""
import hashlib
import json
import multiprocessing
import os
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import patch

from local_agent.safety import Denied
from local_agent.studio import inspection, work_queue
from local_agent.studio.manager import Manager
from local_agent.studio.retention import Retention
from local_agent.studio.state_owner import database_path
from local_agent.studio.store import Store
from local_agent.studio.work_queue import Claim, WorkQueue

from .inspection_support import InspectionProcessFixture, spec_for
from .support import WorkspaceTest


def admission_crash(config, chat, spec, claim, phase):
    store = Store(database_path(config))
    attach = work_queue.attach

    def crash(db, claimed, task):
        if phase == 'after_attach':
            attach(db, claimed, task)
        os._exit(71)

    if phase == 'after_commit':
        store.task(chat, 'inspection', spec['model'], profile='coding', project='.', scope_key=spec['scope'],
            inspection={'spec': spec, 'agent': None}, queue_claim=claim)
        os._exit(72)
    with patch.object(work_queue, 'attach', crash):
        store.task(chat, 'inspection', spec['model'], profile='coding', project='.', scope_key=spec['scope'],
            inspection={'spec': spec, 'agent': None}, queue_claim=claim)


class WorkQueueTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.manager = Manager(self.config)
        self.addCleanup(self.manager.close)
        self.store = self.manager.store
        self.chat = self.store.conversation('Queue fixture')
        for name in ('a.py', 'b.py'):
            (self.policy.root / name).write_text('# Selected safe input\n', encoding='utf-8')
        self.spec = spec_for(self.config, self.store, self.chat)
        self.queue = WorkQueue(self.store, self.config, self.manager.event_epoch)

    def enqueue(self, key='a' * 64, **changes):
        data = {'objective': self.spec['objective'], 'model': self.spec['model'], 'project': '.',
                'files': ['a.py', 'b.py'], 'settings': self.spec['options']}
        data.update(changes)
        return self.queue.enqueue(key, self.chat, **data)

    def admit(self, claim, *, spec=None):
        spec = spec or self.spec
        return self.store.task(self.chat, 'inspection', spec['model'], profile='coding',
            project=spec['project'], scope_key=spec['scope'], inspection={'spec': spec, 'agent': None}, queue_claim=claim)

    def test_duplicate_trigger_survives_store_restart_and_different_payload_cannot_rebind_it(self):
        first = self.enqueue()
        self.assertEqual(self.enqueue(), first)
        restarted = WorkQueue(Store(self.store.path), self.config, uuid.uuid4().hex)
        self.assertEqual(restarted.enqueue('a' * 64, self.chat, self.spec['objective'], self.spec['model'], '.',
                                         ['a.py', 'b.py'], self.spec['options']), first)
        with self.assertRaises(ValueError):
            self.enqueue(objective='Different authority')
        self.assertEqual(self.store.tasks(), [])
        self.assertTrue(self.queue.cancel(first['id']))
        self.assertEqual(self.enqueue()['state'], 'cancelled')
        self.assertIsNone(self.queue.claim())

    def test_concurrent_delivery_and_claim_have_one_winner_and_tokens_are_private(self):
        barrier = threading.Barrier(2)

        def enqueue(_):
            barrier.wait(3)
            return self.enqueue()

        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(enqueue, range(2)))
        self.assertEqual(rows[0]['id'], rows[1]['id'])
        other = WorkQueue(self.store, self.config, uuid.uuid4().hex)
        barrier = threading.Barrier(2)

        def claim(queue):
            barrier.wait(3)
            return queue.claim()

        with ThreadPoolExecutor(max_workers=2) as pool:
            leases = list(pool.map(claim, (self.queue, other)))
        self.assertEqual(sum(value is not None for value in leases), 1)
        lease = next(value for value in leases if value)
        self.assertNotIn(lease.token, repr(lease))
        summary = self.queue.summary(lease.job)
        self.assertNotIn(lease.token, json.dumps(summary))
        self.assertNotIn('payload', summary)
        with self.store.connection() as db:
            stored = dict(db.execute('SELECT * FROM workflow_queue').fetchone())
        self.assertNotIn(lease.token, json.dumps(stored))

    def test_expired_claim_is_replaced_and_old_owner_token_cannot_admit_release_or_read_new_claim(self):
        self.enqueue()
        clock = [work_queue.now_ms()]
        first = WorkQueue(self.store, self.config, self.manager.event_epoch, clock=lambda: clock[0])
        second = WorkQueue(self.store, self.config, uuid.uuid4().hex, clock=lambda: clock[0])
        lease = first.claim(seconds=1)
        self.assertIsNone(second.claim())
        clock[0] += 1000
        with patch.object(work_queue, 'now_ms', return_value=clock[0]), self.assertRaises(ValueError):
            self.admit(lease)
        replacement = second.claim()
        self.assertNotEqual(lease.token, replacement.token)
        with self.assertRaises(ValueError):
            self.admit(lease)
        with self.assertRaises(ValueError):
            first.release(lease, retry=True)
        with self.assertRaises(ValueError):
            first.request(replacement)
        self.assertEqual(second.request(replacement)['objective'], self.spec['objective'])
        self.assertEqual(self.store.tasks(), [])

    def test_admission_is_atomic_bound_to_exact_request_and_never_requeued_after_restart(self):
        item = self.enqueue()
        lease = self.queue.claim()
        for key, value in [('objective', 'Changed instruction'), ('model', 'different-model')]:
            with self.assertRaises(ValueError):
                self.admit(lease, spec={**self.spec, key: value})
        with self.assertRaises(ValueError):
            self.admit(replace(lease, token='0' * 64))
        with patch.object(work_queue, 'attach', side_effect=sqlite3.OperationalError('Injected atomic failure')), self.assertRaises(sqlite3.Error):
            self.admit(lease)
        self.assertEqual(self.store.tasks(), [])
        self.assertEqual(self.queue.summary(item['id'])['state'], 'leased')
        barrier = threading.Barrier(2)

        def admit(_):
            barrier.wait(3)
            try:
                return self.admit(lease)
            except (ValueError, sqlite3.Error):
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            admitted = list(pool.map(admit, range(2)))
        self.assertEqual(sum(task is not None for task in admitted), 1)
        task = next(task for task in admitted if task)
        self.assertEqual(self.queue.summary(item['id'])['task'], task)
        self.assertEqual(self.queue.summary(item['id'])['state'], 'admitted')
        with self.assertRaises(ValueError):
            self.admit(lease)
        self.assertFalse(self.queue.cancel(item['id']))
        self.store.recover()
        self.assertEqual(self.store.tasks()[0]['status'], 'interrupted')
        self.assertIsNone(self.queue.claim())

    def test_lost_commit_acknowledgement_retains_admitted_task_and_cannot_requeue_it(self):
        item = self.enqueue()
        lease = self.queue.claim()
        original = self.store.connection

        @contextmanager
        def lost_ack():
            with original() as db:
                yield db
            raise OSError('Injected lost task-commit acknowledgement')

        with patch.object(self.store, 'connection', lost_ack), self.assertRaises(OSError):
            self.admit(lease)
        self.assertEqual(self.queue.summary(item['id'])['state'], 'admitted')
        self.assertEqual(len(self.store.tasks()), 1)
        task = self.store.tasks()[0]['id']
        self.assertEqual(self.queue.summary(item['id'])['task'], self.store.tasks()[0]['id'])
        with self.assertRaises(ValueError):
            self.queue.release(lease, retry=True)
        self.store.recover()
        self.assertEqual(self.store.tasks()[0]['status'], 'interrupted')
        self.assertIsNone(self.queue.claim())
        with self.store.connection() as db:
            db.execute('DELETE FROM events WHERE task=?', (task,))
            db.execute('DELETE FROM tasks WHERE id=?', (task,))
        self.assertIsNone(self.queue.summary(item['id'])['task'])
        self.assertEqual(self.queue.summary(item['id'])['state'], 'admitted')
        self.assertIsNone(self.queue.claim())

    def test_release_conflict_cancel_and_stop_do_not_execute_and_ordinary_modes_cannot_consume_claim(self):
        item = self.enqueue()
        lease = self.queue.claim()
        self.queue.release(lease, retry=True)
        with self.assertRaises(ValueError):
            self.queue.request(lease)
        lease = self.queue.claim()
        with self.assertRaises(ValueError):
            self.store.task(self.chat, 'agent', self.spec['model'], queue_claim=lease)
        (self.policy.state / 'STOP').touch()
        with self.assertRaises(Denied):
            self.queue.claim()
        with self.assertRaises(Denied):
            self.enqueue('b' * 64)
        self.assertTrue(self.queue.cancel(item['id']))  # Stop never prevents cancelling pending work.
        with self.assertRaises(ValueError):
            self.admit(lease)
        self.assertEqual(self.store.tasks(), [])

    def test_bounds_types_private_state_and_malformed_items_fail_without_exposure_or_scope_expansion(self):
        for change in ({'files': ['../outside']}, {'files': ['.env']}, {'files': []},
                       {'settings': {'command': 'unrestricted'}}, {'settings': {'context': True}}):
            with self.assertRaises((ValueError, Denied)):
                self.enqueue(**change)
        with patch.object(work_queue, 'MAX_ITEMS', 0), self.assertRaises(ValueError):
            self.enqueue()
        with patch.object(work_queue, 'MAX_TOTAL_BYTES', 0), self.assertRaises(ValueError):
            self.enqueue()
        for seconds in (0, 31, True, '15'):
            with self.assertRaises(ValueError):
                self.queue.claim(seconds=seconds)
        item = self.enqueue()
        text = '{"credential":"PRIVATE-QUEUE-CANARY"}'
        with self.store.connection() as db:
            db.execute('UPDATE workflow_queue SET payload=?,sha256=? WHERE id=?',
                       (text, hashlib.sha256(text.encode()).hexdigest(), item['id']))
        self.assertIsNone(self.queue.claim())
        with self.store.connection() as db:
            self.assertEqual(db.execute('SELECT state FROM workflow_queue').fetchone()[0], 'blocked')
        with self.assertRaises(ValueError) as error:
            self.queue.summary(item['id'])
        self.assertNotIn('PRIVATE-QUEUE', str(error.exception))

    def test_restored_store_identity_cannot_admit_an_old_queued_request(self):
        item = self.enqueue()
        self.store.identity = 'b' * 32  # Represents fresh identity after validated restore.
        self.assertIsNone(self.queue.claim())
        self.assertEqual(self.queue.summary(item['id'])['state'], 'blocked')
        self.assertEqual(self.store.tasks(), [])

    def test_actual_process_crash_before_and_after_atomic_admission_preserves_single_consumer(self):
        for phase in ('before_attach', 'after_attach', 'after_commit'):
            item = self.enqueue(hashlib.sha256(phase.encode()).hexdigest())
            lease = self.queue.claim()
            proc = multiprocessing.get_context('spawn').Process(
                target=admission_crash, args=(self.config, self.chat, self.spec, lease, phase))
            proc.start()
            proc.join(8)
            try:
                self.assertFalse(proc.is_alive())
                self.assertEqual(proc.exitcode, 72 if phase == 'after_commit' else 71)
            finally:
                if proc.is_alive():
                    proc.kill()
                    proc.join(3)
                proc.close()
            state = self.queue.summary(item['id'])
            if phase == 'after_commit':
                self.assertEqual(state['state'], 'admitted')
                self.store.recover()
                self.assertEqual(len(self.store.tasks()), 1)
                self.assertEqual(self.store.tasks()[0]['status'], 'interrupted')
                self.assertIsNone(self.queue.claim())
            else:
                self.assertEqual(state['state'], 'leased')
                self.assertEqual(self.store.tasks(), [])
                self.queue.cancel(item['id'])

    def test_retention_protects_pending_and_hashes_cancelled_rows_and_denies_cross_chat_link(self):
        item = self.enqueue()
        service = Retention(self.manager)
        service.save({'older_than_days': 1, 'keep_recent': 0, 'batch_size': 20})
        with self.store.connection() as db:
            db.execute('UPDATE conversations SET created=1')
        self.assertEqual(service.preview()['items'], [])
        self.queue.cancel(item['id'])
        preview = service.preview()
        self.assertEqual(preview['counts']['workflow_queue'], 1)
        other = self.store.conversation('Kept')
        task = self.store.task(other, 'agent', self.spec['model'])
        self.store.finish(task, 'reported', {})
        with self.store.connection() as db:
            db.execute('UPDATE workflow_queue SET task=? WHERE id=?', (task, item['id']))
        with self.assertRaisesRegex(Denied, 'queue relationships'):
            service.preview([other])
        with self.store.connection() as db:
            db.execute('UPDATE workflow_queue SET task=NULL WHERE id=?', (item['id'],))
        service.apply(preview['id'], confirmed=True)
        with self.store.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM workflow_queue').fetchone()[0], 0)


class WorkQueueProcessTests(InspectionProcessFixture, WorkspaceTest):
    def test_actual_queued_inspection_admits_one_worker_and_read_only_tools_with_no_lease_secret_in_events(self):
        queue = WorkQueue(self.store, self.config, self.manager.event_epoch)
        row = queue.enqueue('a' * 64, self.chat, 'Explain these files', self.config['model']['name'], '.', ['a.py', 'b.py'], {})
        lease = queue.claim()
        request = queue.request(lease)
        task = inspection.start(self.manager, self.chat, request['objective'], request['model'], request['project'],
                                request['files'], request['options'], queue_claim=lease)
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual(queue.summary(row['id'])['task'], task)
        self.assertEqual(self.store.tasks()[0]['status'], 'reported')
        self.assertEqual({op['tool'] for op in self.store.journal(task)['operations']}, {'read_file'})
        self.assertFalse(self.manager.pending())
        self.assertNotIn(lease.token, json.dumps(self.store.events()))
        with self.assertRaises(ValueError):
            inspection.start(self.manager, self.chat, request['objective'], request['model'], '.',
                             request['files'], request['options'], queue_claim=lease)
        self.assertEqual(len(self.store.tasks()), 1)

    def test_busy_shutdown_wrong_owner_and_cancelled_claim_never_create_a_second_task(self):
        queue = WorkQueue(self.store, self.config, self.manager.event_epoch)
        row = queue.enqueue('a' * 64, self.chat, 'Explain these files', self.config['model']['name'], '.', ['a.py', 'b.py'], {})
        lease = queue.claim()
        spec = spec_for(self.config, self.store, self.chat)
        kwargs = {'inspection': {'spec': spec, 'agent': None}, 'queue_claim': lease, 'profile': 'coding'}
        self.manager.running['busy'] = {'done': True}
        try:
            with self.assertRaises(ValueError):
                self.manager.start(self.chat, inspection.prompt(spec), 'inspection', spec['model'], **kwargs)
        finally:
            self.manager.running.clear()
        self.manager.shutdown_requested.set()
        with self.assertRaises(OSError):
            self.manager.start(self.chat, inspection.prompt(spec), 'inspection', spec['model'], **kwargs)
        self.manager.shutdown_requested.clear()
        wrong = {**kwargs, 'queue_claim': Claim(lease.job, uuid.uuid4().hex, lease.token)}
        with self.assertRaises(ValueError):
            self.manager.start(self.chat, inspection.prompt(spec), 'inspection', spec['model'], **wrong)
        self.assertTrue(queue.cancel(row['id']))
        with self.assertRaises(ValueError):
            self.manager.start(self.chat, inspection.prompt(spec), 'inspection', spec['model'], **kwargs)
        self.assertFalse(self.manager.running)
        self.assertEqual(self.store.tasks(), [])
