"""Bounded exact-review retention, real cascades and preservation of unrelated state."""
import hashlib
import json
import sqlite3
import time
from unittest import skipUnless
from unittest.mock import patch

from local_agent.safety import Denied
from local_agent.studio import retention
from local_agent.studio.manager import Manager

from . import studio_support as fixtures
from .support import WorkspaceTest


class RetentionTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.manager = Manager(self.config)
        self.addCleanup(self.manager.close)
        self.store = self.manager.store
        self.service = retention.Retention(self.manager)
        self.service.save({'older_than_days': 1, 'keep_recent': 0, 'batch_size': 20})

    def old(self, title='Old conversation', days=120):
        chat = self.store.conversation(title)
        self.age(chat, days)
        return chat

    def age(self, chat, days=120):
        stamp = time.time() - days * 86400
        with self.store.connection() as db:
            for table in ('conversations', 'messages', 'tasks', 'memories'):
                field = 'id' if table == 'conversations' else 'conversation'
                db.execute(f'UPDATE {table} SET created=? WHERE {field}=?', (stamp, chat))
            db.execute('UPDATE goals SET created=?,updated=? WHERE conversation=?', (stamp, stamp, chat))
            db.execute('UPDATE events SET created=? WHERE task IN (SELECT id FROM tasks WHERE conversation=?)', (stamp, chat))

    def test_settings_persist_independently_and_saving_never_deletes(self):
        chat = self.old()
        self.store.preferences({'model': 'fixture', 'temperature': .2})
        policy = {'older_than_days': 30, 'keep_recent': 4, 'batch_size': 2}
        self.assertEqual(self.service.save(policy), {'policy': policy, 'automatic': False})
        self.assertEqual(retention.Retention(self.manager).settings()['policy'], policy)
        self.assertEqual(self.store.conversations()[0]['id'], chat)
        self.assertEqual(self.store.preferences(), {'model': 'fixture', 'temperature': .2})
        for invalid in ({**policy, 'batch_size': True}, {**policy, 'keep_recent': -1},
                        {**policy, 'older_than_days': '30'}, {**policy, 'path': '../outside'}):
            with self.assertRaises(ValueError):
                self.service.save(invalid)

    def test_activity_recent_selection_unfinished_goals_pending_uploads_and_tasks_are_protected(self):
        eligible = self.old('Eligible')
        selected = self.old('Selected')
        recent = self.old('Recent old conversation', days=20)
        fresh = self.old('Fresh activity')
        self.store.message(fresh, 'user', 'Fresh message')
        goal_chat = self.old('Active goal')
        self.store.create_goal(goal_chat, 'Do not prune unfinished work')
        self.age(goal_chat)
        pending = self.old('Pending attachment')
        self.store.attachment(pending, {'name': 'pending.txt', 'mime': 'text/plain', 'data': b'keep', 'text': 'keep'})
        running = self.old('Unreconciled task')
        self.store.task(running, 'agent', 'fixture')
        self.age(running)
        invalid = self.old('Invalid timestamp')
        with self.store.connection() as db:
            db.execute("UPDATE conversations SET created='invalid' WHERE id=?", (invalid,))
        self.service.save({'older_than_days': 1, 'keep_recent': 2, 'batch_size': 20})
        preview = self.service.preview([selected])
        self.assertEqual([row['id'] for row in preview['items']], [eligible])
        self.assertNotIn(recent, [row['id'] for row in preview['items']])
        self.assertEqual(len(self.store.conversations()), 8)

    def test_preview_is_read_only_bounded_and_does_not_expose_bodies_or_paths(self):
        chats = [self.old(f'Old {i}') for i in range(3)]
        for chat in chats:
            self.store.message(chat, 'user', 'PRIVATE-BODY-CANARY')
            self.age(chat)
        self.service.save({'older_than_days': 1, 'keep_recent': 0, 'batch_size': 2})
        preview = self.service.preview()
        self.assertEqual(len(preview['items']), 2)
        self.assertTrue(preview['more'])
        self.assertEqual(preview['counts']['messages'], 2)
        self.assertEqual(len(self.store.conversations()), 3)
        self.assertNotIn('PRIVATE-BODY', json.dumps(preview))
        self.assertNotIn(str(self.policy.root), json.dumps(preview))
        result = self.service.apply(preview['id'], confirmed=True)
        self.assertEqual(result['deleted'], 2)
        self.assertEqual(len(self.store.conversations()), 1)
        with self.assertRaises(ValueError):
            self.service.apply(preview['id'], confirmed=True)
        self.assertEqual(len(self.service.preview()['items']), 1)

    def test_same_length_edits_and_new_activity_reject_consumed_preview_without_deletion(self):
        chat = self.old('Title one')
        self.store.message(chat, 'user', 'old')
        self.age(chat)
        preview = self.service.preview()
        self.store.rename_conversation(chat, 'Title two')
        with self.assertRaises(Denied):
            self.service.apply(preview['id'], confirmed=True)
        with self.assertRaises(ValueError):
            self.service.apply(preview['id'], confirmed=True)
        preview = self.service.preview()
        self.store.message(chat, 'user', 'New active content')
        with self.assertRaises(Denied):
            self.service.apply(preview['id'], confirmed=True)
        self.assertEqual(self.store.conversations()[0]['id'], chat)

    def test_same_size_binary_changes_are_not_hidden_by_unchanged_timestamps(self):
        chat = self.old()
        item = self.store.attachment(chat, {'name': 'binary', 'mime': 'application/octet-stream', 'data': b'aa', 'text': None})
        self.store.message(chat, 'user', 'Old upload', attachment_ids=[item['id']])
        self.age(chat)
        preview = self.service.preview()
        with self.store.connection() as db:
            db.execute('UPDATE attachments SET data=? WHERE id=?', (b'bb', item['id']))
        with self.assertRaises(Denied):
            self.service.apply(preview['id'], confirmed=True)
        self.assertEqual(self.store.attachments(chat, ids=[item['id']], include_data=True)[0]['data'], b'bb')

    def test_atomic_cascades_memory_context_reset_and_project_backup_generation_preservation(self):
        chat = self.old('Old memory source')
        note = self.manager.memory.remember('.', chat, text='PRIVATE-NOTE-CANARY')
        attachment = self.store.attachment(chat, {'name': 'old.bin', 'mime': 'application/octet-stream', 'data': b'old', 'text': None})
        self.store.message(chat, 'user', 'Old message', attachment_ids=[attachment['id']])
        goal = self.store.create_goal(chat, 'Completed goal')
        self.store.set_goal_plan(goal['id'], ['Done'])
        self.store.goal_step(chat, 0, True)
        self.store.finish_goal(chat, 'completed')
        task = self.store.task(chat, 'agent', 'fixture', goal=goal['id'])
        with self.store.connection() as db:
            db.execute("INSERT INTO execution_steps VALUES ('step',?,1,'completed','observed',1,2)", (task,))
            db.execute("INSERT INTO operations VALUES ('op',?,'step',1,'read_file','read',?,'[]','completed','observed','[]',1,2)", (task, 'a' * 64))
        self.store.verification(task, {'id': 'b' * 32, 'kind': 'artifact', 'version': 1,
            'path': 'old.txt', 'expected_bytes': 0, 'expected_sha256': hashlib.sha256(b'').hexdigest(),
            'observed_bytes': 0, 'observed_sha256': hashlib.sha256(b'').hexdigest(), 'resource_version': 'c' * 64,
            'observation': 'read', 'status': 'passed', 'reason': 'content_matches'})
        self.store.finish(task, 'reported', {'report': 'Old result'})
        self.age(chat)
        kept = self.store.conversation('Kept chat')
        self.manager.memory.remember('.', kept, text='Kept note')
        self.store.message(kept, 'user', 'Visible transcript remains')
        self.assertTrue(self.store.messages(kept, for_model=True))
        files = [self.policy.root / 'project.txt', self.policy.state / 'backups' / 'saved.sqlite3',
                 self.policy.state / 'restore-staging' / 'generation' / 'studio.sqlite3']
        for path in files:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'PRESERVE-FILE')
        self.manager.emit(task, 'progress', {'text': 'Old event'})
        self.age(chat)
        preview = self.service.preview([kept])
        self.assertEqual(preview['counts']['memories'], 1)
        self.assertEqual(preview['counts']['context_recipients'], 1)
        self.assertEqual(preview['counts']['verifications'], 1)
        result = self.service.apply(preview['id'], confirmed=True)
        self.assertEqual(result['deleted'], 1)
        self.assertEqual([row['id'] for row in self.store.conversations()], [kept])
        self.assertFalse(self.store.messages(kept, for_model=True))
        self.assertEqual(self.store.messages(kept)[0]['content'], 'Visible transcript remains')
        self.assertNotIn(note['id'], [row['id'] for row in self.manager.memory.search('.')])
        with self.store.connection() as db:
            for table in ('tasks', 'events', 'goals', 'attachments', 'verifications', 'operations', 'execution_steps'):
                self.assertEqual(db.execute(f'SELECT count(*) FROM {table}').fetchone()[0], 0, table)
            self.assertIsNotNone(db.execute('SELECT value FROM metadata WHERE key=?', (retention.RECEIPT_KEY,)).fetchone())
        self.assertFalse(any(event.get('task') == task for event in self.manager.live_events))
        for path in files:
            self.assertEqual(path.read_bytes(), b'PRESERVE-FILE')

    def test_second_delete_failure_rolls_back_entire_batch_and_consumes_review(self):
        chats = [self.old('Old A'), self.old('Old B')]
        preview = self.service.preview()
        original = self.store.delete_conversation_in
        calls = []

        def fail_later(db, ident):
            calls.append(ident)
            if len(calls) == 2:
                raise sqlite3.OperationalError('PRIVATE-ERROR-CANARY')
            return original(db, ident)

        with patch.object(self.store, 'delete_conversation_in', fail_later), self.assertRaises(ValueError) as failure:
            self.service.apply(preview['id'], confirmed=True)
        self.assertNotIn('PRIVATE-ERROR', str(failure.exception))
        self.assertEqual({row['id'] for row in self.store.conversations()}, set(chats))
        with self.assertRaises(ValueError):
            self.service.apply(preview['id'], confirmed=True)

    def test_limits_expiry_settings_change_and_restart_never_delete(self):
        chat = self.old()
        for field, value in [('MAX_BYTES', 1), ('MAX_ROWS', 0), ('TIMEOUT', -1)]:
            with patch.object(retention, field, value), self.assertRaises(ValueError):
                self.service.preview()
        self.assertEqual(self.service.previews, {})
        with patch.object(retention, 'TTL', -1):
            preview = self.service.preview()
        with self.assertRaises(ValueError):
            self.service.apply(preview['id'], confirmed=True)
        preview = self.service.preview()
        with self.assertRaises(ValueError):
            retention.Retention(self.manager).apply(preview['id'], confirmed=True)
        self.service.save({'older_than_days': 2, 'keep_recent': 0, 'batch_size': 1})
        with self.assertRaises(ValueError):
            self.service.apply(preview['id'], confirmed=True)
        for _ in range(8):
            self.service.preview()
        with self.assertRaisesRegex(ValueError, 'Too many'):
            self.service.preview()
        self.assertEqual(self.store.conversations()[0]['id'], chat)

    def test_denial_active_cleanup_shutdown_pending_restart_and_stop_preserve_data(self):
        chat = self.old()
        preview = self.service.preview()
        for value in (False, None, 1, 'true'):
            with self.assertRaises(Denied):
                self.service.apply(preview['id'], confirmed=value)
        for state in ({'done': False}, {'done': True}, {'done': True, 'persist_error': 'private'}):
            self.manager.running['owner'] = state
            try:
                with self.assertRaises(ValueError):
                    self.service.preview()
                with self.assertRaises(ValueError):
                    self.service.apply(preview['id'], confirmed=True)
            finally:
                self.manager.running.clear()
        for event in (self.manager.shutdown_requested, self.manager.restore_pending):
            event.set()
            with self.assertRaises(ValueError):
                self.service.preview()
            event.clear()
        (self.policy.state / 'STOP').touch()
        with self.assertRaises(Denied):
            self.service.apply(preview['id'], confirmed=True)
        self.assertEqual(self.store.conversations()[0]['id'], chat)

    def test_unsupported_trigger_and_cross_conversation_sources_cannot_authorize_effects(self):
        chat = self.old()
        other = self.store.conversation('Other source')
        message = self.store.message(other, 'user', 'Other body')
        item = self.store.attachment(chat, {'name': 'bad', 'mime': 'text/plain', 'data': b'old', 'text': 'old'})
        with self.store.connection() as db:
            db.execute('UPDATE attachments SET message=? WHERE id=?', (message, item['id']))
        with self.assertRaises(Denied):
            self.service.preview()
        with self.store.connection() as db:
            db.execute('DELETE FROM attachments WHERE id=?', (item['id'],))
            db.execute("CREATE TRIGGER unexpected AFTER DELETE ON conversations BEGIN DELETE FROM messages; END")
        with self.assertRaises(Denied):
            self.service.preview()
        self.assertEqual(len(self.store.conversations()), 2)


@skipUnless(fixtures.HAS_API, 'Install desktop dependencies')
class RetentionAPITests(fixtures.StudioAPIFixture, WorkspaceTest):
    def test_auth_origin_strict_policy_preview_and_confirmation(self):
        manager = self.client.app.state.manager
        chat = manager.store.conversation('API old chat')
        with manager.store.connection() as db:
            db.execute('UPDATE conversations SET created=1 WHERE id=?', (chat,))
        policy = {'older_than_days': 1, 'keep_recent': 0, 'batch_size': 2}
        for path, body in [('/retention/policy', policy), ('/retention/preview', {}),
                           ('/retention/apply', {'preview': 'a' * 32, 'confirmed': True})]:
            self.assertEqual(self.client.post(path, json=body).status_code, 401)
            self.assertEqual(self.client.post(path, headers={**self.headers, 'Origin': 'https://bad.invalid'}, json=body).status_code, 403)
        self.assertEqual(self.client.get('/retention').status_code, 401)
        self.assertEqual(self.client.post('/retention/policy', headers=self.headers, json={**policy, 'batch_size': True}).status_code, 422)
        self.assertEqual(self.client.post('/retention/policy', headers=self.headers, json={**policy, 'path': '../outside'}).status_code, 422)
        self.assertEqual(self.client.post('/retention/policy', headers=self.headers, json=policy).status_code, 200)
        preview = self.client.post('/retention/preview', headers=self.headers, json={'protected': []}).json()
        for confirmed, expected in [(False, 403), ('true', 422), (1, 422)]:
            self.assertEqual(self.client.post('/retention/apply', headers=self.headers,
                json={'preview': preview['id'], 'confirmed': confirmed}).status_code, expected)
        self.assertEqual(self.client.post('/retention/apply', headers=self.headers,
            json={'preview': preview['id'], 'confirmed': True, 'conversations': ['forged']}).status_code, 422)
        response = self.client.post('/retention/apply', headers=self.headers,
            json={'preview': preview['id'], 'confirmed': True})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['deleted'], 1)
        self.assertEqual(manager.store.conversations(), [])


class RetentionProcessTests(fixtures.StudioProcessFixture, WorkspaceTest):
    def test_owned_approval_wait_blocks_retention_and_denial_keeps_agent_scope(self):
        service = retention.Retention(self.manager)
        service.save({'older_than_days': 1, 'keep_recent': 0, 'batch_size': 2})
        old = self.manager.store.conversation('Old fixture')
        with self.manager.store.connection() as db:
            db.execute('UPDATE conversations SET created=1 WHERE id=?', (old,))
        task = self.manager.start(self.conversation, 'Create reviewed file', 'agent', 'fixture')
        self.wait_until(lambda: bool(self.manager.pending()))
        with self.assertRaises(ValueError):
            service.preview()
        request = self.manager.pending()[0]
        self.manager.approve(task, request['id'], False)
        self.wait_until(lambda: not self.manager.running)
        preview = service.preview()
        self.assertEqual([item['id'] for item in preview['items']], [old])
        service.apply(preview['id'], confirmed=True)
        self.assertEqual(self.manager.store.tasks()[0]['status'], 'blocked')
        self.assertFalse((self.policy.root / 'review.txt').exists())
