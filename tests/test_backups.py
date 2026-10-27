"""Real SQLite snapshots, private-data boundaries, refusal and publication failures."""
import hashlib
import json
import os
import sqlite3
import threading
from contextlib import closing
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

from local_agent.safety import Denied
from local_agent.studio import backups
from local_agent.studio.manager import Manager
from local_agent.studio.migrations import REQUIRED
from local_agent.studio.store import Store

from . import studio_support as fixtures
from .inspection_support import seed_closed_checkpoint
from .support import WorkspaceTest


class BackupTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.manager = Manager(self.config)
        self.addCleanup(self.manager.close)
        self.store = self.manager.store
        self.chat = self.store.conversation('Private backup fixture')
        self.root = self.policy.state / 'backups'

    def create(self):
        return backups.create(self.manager, confirmed=True)

    def test_snapshot_preserves_every_table_wal_and_binary_data_in_fresh_store(self):
        attachment = self.store.attachment(self.chat, {'name': 'note.bin', 'mime': 'application/octet-stream',
            'data': b'\x00\xffPRIVATE-BACKUP-BYTES', 'text': None})
        self.store.message(self.chat, 'user', 'Unicode café \u65e5\u672c', attachment_ids=[attachment['id']])
        self.store.preferences({'model': 'fixture', 'context': 8192})
        goal = self.store.create_goal(self.chat, 'Keep explicit goal')
        self.store.set_goal_plan(goal['id'], ['Verify snapshot'])
        self.manager.memory.remember('.', self.chat, text='The fixture color is amber')
        task = self.store.task(self.chat, 'agent', 'fixture', goal=goal['id'])
        with self.store.connection() as db:
            db.execute("INSERT INTO execution_steps VALUES ('step',?,1,'completed','observed',1,2)", (task,))
            db.execute("INSERT INTO operations VALUES ('op',?,'step',1,'read_file','read',?,'[]',"
                       "'completed','observed','[]',1,2)", (task, 'a' * 64))
        self.store.event(task, 'progress', {'text': 'Retained event'})
        self.store.verification(task, {'id': 'b' * 32, 'kind': 'artifact', 'version': 1,
            'path': 'example.txt', 'expected_bytes': 0, 'expected_sha256': hashlib.sha256(b'').hexdigest(),
            'observed_bytes': 0, 'observed_sha256': hashlib.sha256(b'').hexdigest(),
            'resource_version': 'c' * 64, 'observation': 'read', 'status': 'passed', 'reason': 'content_matches'})
        self.assertEqual(len(self.store.verifications(task)), 1)
        self.store.finish(task, 'reported', {'report': 'Retained result'})
        seed_closed_checkpoint(self.config, self.store, self.chat)
        (self.policy.root / 'project-only.txt').write_text('PROJECT-EXCLUDED')
        (self.policy.state / 'preview.png').write_bytes(b'SCREEN-EXCLUDED')
        with closing(sqlite3.connect(self.store.path)) as live:
            live.execute('PRAGMA wal_autocheckpoint=0')
            live.execute("UPDATE conversations SET title='Committed in WAL' WHERE id=?", (self.chat,))
            live.commit()
            self.assertGreater((self.policy.state / 'studio.sqlite3-wal').stat().st_size, 0)
            tables = [*REQUIRED, 'schema_migrations', 'sqlite_sequence']
            before = {t: live.execute(f'SELECT * FROM {t} ORDER BY rowid').fetchall() for t in tables}
            self.assertTrue(all(before.values()), 'Every preserved table must have an actual fixture row')
            result = self.create()
            path = self.root / result['filename']
            with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as saved:
                self.assertEqual(backups.validate(saved), self.store.identity)
                for table in tables:
                    self.assertEqual(saved.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall(), before[table], table)
                self.assertEqual(saved.execute('PRAGMA journal_mode').fetchone()[0], 'delete')
        self.assertEqual(path.stat().st_nlink, 1)
        self.assertEqual(result['bytes'], path.stat().st_size)
        self.assertEqual(result['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual({p.name for p in self.root.iterdir()}, {result['filename']})
        self.assertFalse(result['encrypted'])
        self.assertNotIn('Private', json.dumps(result))
        self.assertNotIn(str(self.policy.state), json.dumps(result))
        # Opening the snapshot independently needs neither the original WAL nor manager.
        copied = self.policy.state / 'fresh-state' / 'studio.sqlite3'
        copied.parent.mkdir()
        copied.write_bytes(path.read_bytes())
        reopened = Store(copied)
        self.assertEqual(reopened.identity, self.store.identity)
        self.assertEqual(reopened.conversations()[0]['title'], 'Committed in WAL')
        self.assertEqual(reopened.attachments(self.chat, ids=[attachment['id']], include_data=True)[0]['data'],
                         b'\x00\xffPRIVATE-BACKUP-BYTES')

    def test_confirmation_owner_shutdown_and_stop_refuse_without_files(self):
        for value in (None, False, 1, 'true'):
            with self.assertRaises(Denied):
                backups.create(self.manager, confirmed=value)
        for status in ({'done': False}, {'done': True, 'persist_error': 'private'}, {'done': True}):
            self.manager.running['owner'] = status
            try:
                with self.assertRaisesRegex(ValueError, 'active task'):
                    self.create()
            finally:
                self.manager.running.clear()
        self.manager.shutdown_requested.set()
        with self.assertRaisesRegex(ValueError, 'shutting down'):
            self.create()
        self.manager.shutdown_requested.clear()
        (self.policy.state / 'STOP').touch()
        with self.assertRaises(Denied):
            self.create()
        self.assertFalse(self.root.exists())

    def test_size_deadline_and_validation_failure_remove_only_owned_partial(self):
        for field, value, error in [('MAX_BYTES', 4096, ValueError), ('TIMEOUT', -1, TimeoutError)]:
            with patch.object(backups, field, value), self.assertRaises(error):
                self.create()
            self.assertEqual(list(self.root.iterdir()), [])
        with patch.object(backups, 'validate', side_effect=ValueError('Validation failed')), self.assertRaises(ValueError):
            self.create()
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(self.store.conversations()[0]['title'], 'Private backup fixture')

    def test_invalid_schema_history_identity_and_references_never_publish_or_repair(self):
        mutations = ["PRAGMA user_version=99", "DELETE FROM schema_migrations WHERE version=4",
                     "UPDATE metadata SET value='invalid' WHERE key='store_id'",
                     "INSERT INTO messages(id,conversation,role,content,created) VALUES ('orphan','absent','user','private',1)"]
        for index, mutation in enumerate(mutations):
            manager = Manager({**self.config, 'paths': {**self.config['paths'],
                                                     'state': str(self.policy.state / f'invalid-{index}')}})
            try:
                with closing(sqlite3.connect(manager.store.path)) as db, db:
                    db.execute(mutation)
                before = manager.store.path.read_bytes()
                with self.assertRaises((ValueError, sqlite3.DatabaseError)):
                    backups.create(manager, confirmed=True)
                self.assertEqual(manager.store.path.read_bytes(), before)
                self.assertEqual(list((manager.store.path.parent / 'backups').iterdir()), [])
            finally:
                manager.close()

    def test_existing_name_and_storage_capacity_never_overwrite_or_delete(self):
        self.root.mkdir()
        winner = self.root / ('a' * 32 + '.sqlite3')
        winner.write_bytes(b'SAVED-COPY-CANARY')
        with patch.object(backups.uuid, 'uuid4', return_value=SimpleNamespace(hex='a' * 32)), self.assertRaises(FileExistsError):
            self.create()
        self.assertEqual(winner.read_bytes(), b'SAVED-COPY-CANARY')
        for index in range(19):
            (self.root / f'unknown-{index}').touch()
        with self.assertRaisesRegex(ValueError, 'full'):
            self.create()
        self.assertEqual(len(list(self.root.iterdir())), 20)

    def test_hardlinked_source_is_not_read(self):
        alias = self.policy.state / 'alias.sqlite3'
        os.link(self.store.path, alias)
        with patch.object(backups.sqlite3, 'connect', side_effect=AssertionError('Must not open linked input')), self.assertRaises(Denied):
            self.create()
        self.assertFalse(self.root.exists())
        alias.unlink()

    def test_inventory_and_inspection_are_scoped_bounded_and_never_certify_schema(self):
        self.assertEqual(backups.inventory(self.manager)['items'], [])
        saved = self.create()
        inspected = backups.inspect(self.manager, saved['id'])
        self.assertEqual(inspected['sha256'], saved['sha256'])
        self.assertNotIn('schema_version', inspected)
        (self.root / 'PRIVATE-UNKNOWN-FILENAME').write_text('SECRET-CONTENT')
        listing = backups.inventory(self.manager)
        self.assertEqual([r['id'] for r in listing['items']], [saved['id']])
        self.assertEqual(listing['entries'], 2)
        self.assertNotIn('PRIVATE-UNKNOWN', json.dumps(listing))
        self.assertNotIn('SECRET-CONTENT', json.dumps(listing))
        with self.assertRaises(ValueError):
            backups.inspect(self.manager, '../outside')
        with self.assertRaises(KeyError):
            backups.inspect(self.manager, 'f' * 32)
        alias = self.root / ('e' * 32 + '.sqlite3')
        os.link(self.root / saved['filename'], alias)
        self.assertEqual(backups.inventory(self.manager)['items'], [])
        with self.assertRaises(Denied):
            backups.inspect(self.manager, 'e' * 32)
        alias.unlink()
        with patch.object(backups, 'MAX_BYTES', 1), self.assertRaises(Denied):
            backups.inspect(self.manager, saved['id'])
        with patch.object(backups, 'TIMEOUT', -1), self.assertRaises(TimeoutError):
            backups.inspect(self.manager, saved['id'])
        for i in range(25):
            (self.root / f'unknown-{i}').touch()
        listing = backups.inventory(self.manager)
        self.assertTrue(listing['incomplete'])
        self.assertEqual(listing['entries'], 21)
        self.assertLessEqual(len(listing['items']), 20)

    def test_same_process_concurrent_backups_are_distinct_and_valid(self):
        results, errors = [], []

        def run():
            try:
                results.append(self.create())
            except (OSError, ValueError, sqlite3.Error, Denied) as exc:
                errors.append(exc)

        workers = [threading.Thread(target=run) for _ in range(2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(5)
            self.assertFalse(worker.is_alive())
        self.assertFalse(errors, errors)
        self.assertEqual(len({r['id'] for r in results}), 2)
        for result in results:
            with closing(sqlite3.connect(self.root / result['filename'])) as db:
                self.assertEqual(backups.validate(db), self.store.identity)

    def test_uncommitted_wal_changes_are_excluded_and_later_commit_is_backed_up(self):
        with closing(sqlite3.connect(self.store.path)) as writer:
            writer.execute('BEGIN IMMEDIATE')
            writer.execute("UPDATE conversations SET title='Not yet committed' WHERE id=?", (self.chat,))
            first = self.create()
            with closing(sqlite3.connect(self.root / first['filename'])) as db:
                self.assertEqual(db.execute('SELECT title FROM conversations').fetchone()[0], 'Private backup fixture')
            writer.commit()
            second = self.create()
            with closing(sqlite3.connect(self.root / second['filename'])) as db:
                self.assertEqual(db.execute('SELECT title FROM conversations').fetchone()[0], 'Not yet committed')

    def test_failed_publication_and_preexisting_partial_preserve_foreign_files(self):
        with patch.object(backups.os, 'link', side_effect=OSError('Publication failed')), self.assertRaises(OSError):
            self.create()
        self.assertEqual(list(self.root.iterdir()), [])
        partial = self.root / ('.' + 'd' * 32 + '.partial')
        partial.write_bytes(b'UNKNOWN-PARTIAL-ENTRY')
        with patch.object(backups.uuid, 'uuid4', return_value=SimpleNamespace(hex='d' * 32)), self.assertRaises(FileExistsError):
            self.create()
        self.assertEqual(partial.read_bytes(), b'UNKNOWN-PARTIAL-ENTRY')
        self.assertEqual(list(self.root.iterdir()), [partial])


@skipUnless(fixtures.HAS_API, 'Install desktop dependencies')
class BackupAPITests(fixtures.StudioAPIFixture, WorkspaceTest):
    def test_auth_origin_strict_confirmation_and_no_destination_authority(self):
        for headers, expected in [({}, 401), ({**self.headers, 'Origin': 'https://untrusted.invalid'}, 403)]:
            self.assertEqual(self.client.post('/backups', headers=headers, json={'confirmed': True}).status_code, expected)
        self.assertEqual(self.client.get('/backups').status_code, 401)
        self.assertEqual(self.client.get('/backups', headers=self.headers).json()['items'], [])
        self.assertEqual(self.client.post('/backups', headers=self.headers, json={}).status_code, 403)
        for body in ({'confirmed': 1}, {'confirmed': 'true'}, {'confirmed': True, 'path': '../outside.db'},
                     {'confirmed': True, 'destination': 'C:\\private.db'}):
            self.assertEqual(self.client.post('/backups', headers=self.headers, json=body).status_code, 422)
        manager = self.client.app.state.manager
        manager.store.conversation('PRIVATE-API-CHAT')
        response = self.client.post('/backups', headers=self.headers, json={'confirmed': True})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn('PRIVATE-API-CHAT', response.text)
        self.assertNotIn(str(self.policy.state), response.text)
        self.assertEqual(response.json()['bytes'], (self.policy.state / 'backups' / response.json()['filename']).stat().st_size)


class BackupProcessTests(fixtures.StudioProcessFixture, WorkspaceTest):
    def test_real_approval_wait_refuses_backup_and_denial_does_not_execute(self):
        task = self.manager.start(self.conversation, 'Create reviewed file', 'agent', 'fixture')
        self.wait_until(lambda: bool(self.manager.pending()))
        with self.assertRaisesRegex(ValueError, 'active task'):
            backups.create(self.manager, confirmed=True)
        approval = self.manager.pending()[0]
        self.manager.approve(task, approval['id'], False)
        self.wait_until(lambda: not self.manager.running)
        self.assertFalse((self.policy.root / 'review.txt').exists())
        result = backups.create(self.manager, confirmed=True)
        with closing(sqlite3.connect(self.policy.state / 'backups' / result['filename'])) as db:
            self.assertEqual(db.execute('SELECT status FROM tasks WHERE id=?', (task,)).fetchone()[0], 'blocked')
