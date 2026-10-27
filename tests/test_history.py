"""Real SQLite cursor boundaries, scoped metadata, migration and authenticated API."""
import base64
import json
import sqlite3
import threading
import unittest
from unittest.mock import patch

from local_agent.studio import migrations
from local_agent.studio.history import MAX_EXPORT_BYTES, decode_cursor, export_markdown, page
from local_agent.studio.manager import Manager
from local_agent.studio.store import Store

from . import studio_support as fixtures
from .support import WorkspaceTest


class HistoryTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.store = Store(self.policy.state / 'history.db')

    def seed(self, count=231):
        with self.store.connection() as db:
            for index in range(count):
                ident = f'chat-{index}'
                db.execute('INSERT INTO conversations(id,title,created) VALUES (?,?,?)',
                           (ident, f'History {index}', index // 7))
                db.execute('INSERT INTO messages(id,conversation,role,content,created) VALUES (?,?,?,?,?)',
                           (f'message-{index}', 'chat-0', 'user', str(index), index // 7))
                db.execute('INSERT INTO tasks(id,conversation,mode,status,model,created,result) '
                           'VALUES (?,?,?,?,?,?,?)',
                           (f'task-{index}', 'chat-0', 'agent', 'reported', 'fixture', index // 7, 'SECRET-RESULT'))

    def collect(self, kind, **scope):
        collected, cursor = [], None
        while True:
            result = page(self.store, kind, cursor=cursor, limit=17, **scope)
            self.assertLessEqual(len(result['items']), 17)
            collected += list(reversed(result['items'])) if kind == 'messages' else result['items']
            cursor = result['next']
            if cursor is None:
                return collected

    def test_all_three_histories_pass_200_rows_without_duplicates_or_timestamp_gaps(self):
        self.seed()
        for kind, prefix in (('conversations', 'chat'), ('messages', 'message'), ('tasks', 'task')):
            with self.subTest(kind=kind):
                items = self.collect(kind, **({'conversation': 'chat-0'} if kind == 'messages' else {}))
                self.assertEqual([item['id'] for item in items], [f'{prefix}-{i}' for i in reversed(range(231))])
                self.assertEqual(len({item['id'] for item in items}), 231)
        self.assertTrue(all('result' not in item for item in self.collect('tasks')))

    def test_export_includes_entire_visible_transcript_metadata_and_exact_utf8_bytes(self):
        chat = self.store.conversation('Complete Unicode export')
        other = self.store.conversation('Foreign')
        attachment = self.store.attachment(chat, {'name': 'note.txt', 'mime': 'text/plain',
                                                 'data': b'PRIVATE_ATTACHMENT_BODY', 'text': 'PRIVATE_ATTACHMENT_BODY'})
        for index in range(125):
            self.store.message(chat, 'user', f'Message {index}: café', attachment_ids=[attachment['id']] if index == 0 else [])
        self.store.message(other, 'user', 'FOREIGN-EXPORT-CANARY')
        with self.store.connection() as db:
            db.execute('UPDATE conversations SET memory_epoch=1 WHERE id=?', (chat,))
        result = export_markdown(self.store, chat)
        self.assertTrue(result['complete'])
        self.assertEqual(result['message_count'], 125)
        self.assertEqual(result['bytes'], len(result['markdown'].encode('utf-8')))
        self.assertIn('Message 0: café', result['markdown'])
        self.assertIn('Message 124: café', result['markdown'])
        self.assertIn('Attachment: note.txt (1 KiB)', result['markdown'])
        self.assertNotIn('PRIVATE_ATTACHMENT_BODY', result['markdown'])
        self.assertNotIn('FOREIGN-EXPORT-CANARY', result['markdown'])
        self.assertEqual(self.store.messages(chat, for_model=True), [])

    def test_export_rejects_both_limits_and_missing_scope_without_partial_result(self):
        chat = self.store.conversation()
        with self.store.connection() as db:
            db.executemany('INSERT INTO messages(id,conversation,role,content,created) VALUES (?,?,?,?,?)',
                           [(f'export-{i}', chat, 'user', 'small', i) for i in range(5001)])
        with self.assertRaisesRegex(ValueError, '5,000-message limit; no partial'):
            export_markdown(self.store, chat)
        large = self.store.conversation()
        self.store.message(large, 'user', 'x' * MAX_EXPORT_BYTES)
        with self.assertRaisesRegex(ValueError, '8 MiB UTF-8 limit; no partial'):
            export_markdown(self.store, large)
        with self.assertRaises(KeyError):
            export_markdown(self.store, "missing' OR 1=1 --")

    def test_export_snapshot_excludes_a_concurrent_message_and_title_change(self):
        from contextlib import contextmanager

        chat = self.store.conversation('Snapshot title')
        self.store.message(chat, 'user', 'Snapshot message')
        connection = self.store.connection
        injected = []

        @contextmanager
        def observed_connection():
            with connection() as db:
                def trace(sql):
                    if sql.startswith('SELECT id,role,content FROM messages') and not injected:
                        injected.append(True)
                        with connection() as writer:
                            writer.execute('UPDATE conversations SET title=? WHERE id=?', ('New title', chat))
                            writer.execute('INSERT INTO messages(id,conversation,role,content,created) VALUES (?,?,?,?,?)',
                                           ('concurrent', chat, 'user', 'CONCURRENT-MESSAGE', 9999999999))
                db.set_trace_callback(trace)
                yield db

        with patch.object(self.store, 'connection', observed_connection):
            result = export_markdown(self.store, chat)
        self.assertEqual(injected, [True])
        self.assertEqual(result['message_count'], 1)
        self.assertIn('# Snapshot title', result['markdown'])
        self.assertNotIn('CONCURRENT-MESSAGE', result['markdown'])
        self.assertIn('CONCURRENT-MESSAGE', export_markdown(self.store, chat)['markdown'])

    def test_preview_reads_only_requested_blob_rows_and_rejects_scope_before_materialization(self):
        from contextlib import contextmanager

        chat = self.store.conversation()
        other = self.store.conversation()
        with self.store.connection() as db:
            db.executemany('INSERT INTO attachments VALUES (?,?,NULL,?,?,?,?,?)',
                           [(f'blob-{i}', chat, 'small.txt', 'text/plain', b'body', 'body', 4) for i in range(100)])
        connection = self.store.connection
        observed = []

        @contextmanager
        def metered_connection():
            with connection() as db:
                factory = db.row_factory

                def meter(cursor, row):
                    if 'data' in {column[0] for column in cursor.description}:
                        observed.append(row[0])
                    return factory(cursor, row)

                db.row_factory = meter
                yield db

        with patch.object(self.store, 'connection', metered_connection):
            rows = self.store.attachments(chat, ids=['blob-27'], include_data=True)
            self.assertEqual(rows[0]['data'], b'body')
            self.assertEqual(observed, ['blob-27'])
            observed.clear()
            self.assertEqual(self.store.attachments(chat, ids=[], include_data=True), [])
            with self.assertRaises(ValueError):
                self.store.attachments(other, ids=['blob-27'], include_data=True)
            with self.assertRaises(ValueError):
                self.store.attachments(chat, ids=['blob-27', 'blob-27'], include_data=True)
            self.assertEqual(observed, [])

    def test_cursor_survives_restart_and_deleted_pivot_and_does_not_repeat_newer_insert(self):
        self.seed(12)
        initial = page(self.store, 'conversations', limit=4)
        pivot = initial['items'][-1]['id']
        self.store.delete_conversation(pivot)
        self.store.conversation('New head')
        self.store = Store(self.store.path)
        older = page(self.store, 'conversations', cursor=initial['next'], limit=100)
        self.assertEqual([item['id'] for item in older['items']], [f'chat-{i}' for i in reversed(range(8))])
        self.assertIsNone(older['next'])

    def test_invalid_sizes_and_scopes_fail_closed(self):
        for limit in (0, -1, 101, True, 1.2, '5', None):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                page(self.store, 'tasks', limit=limit)
        for kind, arguments in (('sqlite_schema', {}), ('messages', {}), ('tasks', {'query': 'x'}),
                                ('conversations', {'conversation': 'chat'}),
                                ('conversations', {'query': 'x' * 121})):
            with self.subTest(kind=kind, arguments=arguments), self.assertRaises(ValueError):
                page(self.store, kind, **arguments)
        with self.assertRaises(KeyError):
            page(self.store, 'messages', conversation="missing' OR 1=1 --")

    def test_cursor_domain_and_malformed_values_are_rejected(self):
        self.seed(4)
        cursor = page(self.store, 'conversations', limit=1)['next']
        for kind, arguments in (('tasks', {}), ('conversations', {'query': 'History'}),
                                ('messages', {'conversation': 'chat-0'})):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                page(self.store, kind, cursor=cursor, **arguments)
        other = Store(self.policy.state / 'other.db')
        with self.assertRaises(ValueError):
            page(other, 'conversations', cursor=cursor)
        domain = (self.store.identity, 'conversations', '', '')
        for cursor in ('', '?', 'a' * 2049, True, 23, 'not base64', '\ud800'):
            with self.subTest(cursor=repr(cursor)), self.assertRaises(ValueError):
                decode_cursor(cursor, domain)
        for version, created, row in ((True, 1, 1), (2, 1, 1), (1, float('inf'), 1),
                                      (1, True, 1), (1, [], 1), (1, 1, True), (1, 1, -1), (1, 1, 2**63)):
            raw = json.dumps([version, *domain, created, row]).encode()
            cursor = base64.urlsafe_b64encode(raw).decode()
            with self.subTest(value=raw), self.assertRaises(ValueError):
                decode_cursor(cursor, domain)

    def test_search_is_unicode_casefold_literal_and_bound_to_cursor(self):
        for name in ('Straße 100%', 'STRASSE_100', 'Straße extra', 'unrelated'):
            self.store.conversation(name)
        self.assertEqual(len(self.collect('conversations', query='STRASSE')), 3)
        self.assertEqual([row['title'] for row in self.collect('conversations', query='%')], ['Straße 100%'])
        self.assertEqual(page(self.store, 'conversations', query="' OR 1=1 --")['items'], [])

    def test_message_pages_preserve_metrics_attachments_and_forget_epoch_is_display_only(self):
        chat = self.store.conversation()
        foreign = self.store.conversation()
        attachment = self.store.attachment(chat, {'name': 'local.txt', 'mime': 'text/plain',
                                                 'data': b'LOCAL-BYTES', 'text': 'LOCAL-BYTES'})
        message = self.store.message(chat, 'assistant', 'kept transcript', {'generated_tokens': 4}, [attachment['id']])
        self.store.message(foreign, 'user', 'FOREIGN-CANARY')
        with self.store.connection() as db:
            db.execute('UPDATE conversations SET memory_epoch=1 WHERE id=?', (chat,))
        items = page(self.store, 'messages', conversation=chat)['items']
        self.assertEqual([item['id'] for item in items], [message])
        self.assertEqual(items[0]['metrics'], {'generated_tokens': 4})
        self.assertEqual(items[0]['attachments'], [attachment])
        self.assertNotIn('LOCAL-BYTES', json.dumps(items))
        self.assertNotIn('FOREIGN-CANARY', json.dumps(items))
        self.assertEqual(self.store.messages(chat, for_model=True), [])

    def test_task_conversation_scope_and_empty_pages(self):
        self.seed(4)
        self.assertEqual(len(page(self.store, 'tasks', conversation='chat-0')['items']), 4)
        self.assertEqual(page(self.store, 'tasks', conversation='chat-1')['items'], [])
        empty = Store(self.policy.state / 'empty.db')
        self.assertEqual(page(empty, 'conversations')['items'], [])
        self.assertIsNone(page(empty, 'tasks')['next'])
        message_cursor = page(self.store, 'messages', conversation='chat-0', limit=1)['next']
        with self.assertRaises(ValueError):
            page(self.store, 'messages', conversation='chat-1', cursor=message_cursor)

    def test_activity_always_keeps_owned_slots_outside_latest_fifty_without_result_bodies(self):
        self.seed(231)
        manager = Manager.__new__(Manager)  # Explicit metadata-only ownership fixture; no processes created.
        manager.store, manager.lock = self.store, threading.RLock()
        manager.running = {'task-0': {'done': False}, 'task-1': {'done': True, 'persist_error': 'PRIVATE-ERROR'}}
        rows = manager.activity_tasks()
        self.assertEqual(len(rows), 52)
        by_id = {row['id']: row for row in rows}
        self.assertIn('task-0', by_id)
        self.assertEqual(by_id['task-1']['runtime_state'], 'storage')
        self.assertNotIn('PRIVATE-ERROR', json.dumps(rows))
        self.assertTrue(all('result' not in row and 'memory_refs' not in row for row in rows))
        manager.running['task-1'].pop('persist_error')
        self.assertEqual(manager.task_metadata('task-1')['runtime_state'], 'cleanup')
        with self.assertRaises(KeyError):
            manager.task_metadata("missing' OR 1=1 --")

    def test_next_page_uses_index_without_offset_or_temporary_order_sort(self):
        self.seed(30)
        with self.store.connection() as db:
            for kind, sql, args in (
                ('conversations', ('SELECT id FROM conversations WHERE (created,rowid)<(?,?) '
                 'ORDER BY created DESC,rowid DESC LIMIT 10'), (2, 15)),
                ('messages', ('SELECT id FROM messages WHERE conversation=? AND (created,rowid)<(?,?) '
                 'ORDER BY created DESC,rowid DESC LIMIT 10'), ('chat-0', 2, 15)),
                ('tasks', ('SELECT id FROM tasks WHERE conversation=? AND (created,rowid)<(?,?) '
                 'ORDER BY created DESC,rowid DESC LIMIT 10'), ('chat-0', 2, 15)),
            ):
                detail = ' '.join(row[3] for row in db.execute('EXPLAIN QUERY PLAN ' + sql, args))
                self.assertIn('SEARCH', detail, (kind, detail))
                self.assertIn('INDEX', detail, (kind, detail))
                self.assertNotIn('TEMP B-TREE', detail, (kind, detail))

    def test_v3_upgrade_preserves_identity_data_and_adds_indexes_transactionally(self):
        path = self.policy.state / 'v3.db'
        with patch.object(migrations, 'MIGRATIONS', migrations.MIGRATIONS[:3]), \
                patch.object(migrations, 'SCHEMA_VERSION', 3), \
                patch.object(migrations, 'REQUIRED', {key: value for key, value in migrations.REQUIRED.items()
                                                    if key not in {'inspection_checkpoints', 'workflow_queue', 'interval_schedules', 'schedule_runs', 'directory_watches', 'directory_runs', 'memory_indexes', 'memory_vectors', 'memory_file_sources', 'memory_file_chunks'}}):
            old = Store(path)
            chat = old.conversation('Retained v3')
            old.message(chat, 'user', 'Retained message')
            old.preferences({'model': 'retained'})
        upgraded = Store(path)
        self.assertEqual(upgraded.identity, old.identity)
        self.assertEqual(upgraded.messages(chat)[0]['content'], 'Retained message')
        self.assertEqual(upgraded.preferences(), {'model': 'retained'})
        with upgraded.connection() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], migrations.SCHEMA_VERSION)
            self.assertEqual(db.execute("SELECT count(*) FROM sqlite_schema WHERE type='index' AND name LIKE '%_history'")
                             .fetchone()[0], 5)
        failed_path = self.policy.state / 'rollback-v3.db'
        with patch.object(migrations, 'MIGRATIONS', migrations.MIGRATIONS[:3]), \
                patch.object(migrations, 'SCHEMA_VERSION', 3), \
                patch.object(migrations, 'REQUIRED', {key: value for key, value in migrations.REQUIRED.items()
                                                    if key not in {'inspection_checkpoints', 'workflow_queue', 'interval_schedules', 'schedule_runs', 'directory_watches', 'directory_runs', 'memory_indexes', 'memory_vectors', 'memory_file_sources', 'memory_file_chunks'}}):
            Store(failed_path)

        def failure(db):
            migrations.history_paging(db)
            raise RuntimeError('Injected index migration failure')

        with patch.object(migrations, 'MIGRATIONS', (*migrations.MIGRATIONS[:3], ('history_paging', failure))), \
                self.assertRaises(RuntimeError):
            Store(failed_path)
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(failed_path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 3)
            self.assertEqual(db.execute("SELECT count(*) FROM sqlite_schema WHERE name LIKE '%_history'").fetchone()[0], 0)


@unittest.skipUnless(fixtures.HAS_API, 'Requires Studio API dependencies')
class HistoryAPITests(fixtures.StudioAPIFixture, WorkspaceTest):
    def test_bounded_activity_and_task_metadata_are_authenticated_and_never_read_result_columns(self):
        from contextlib import contextmanager

        store = self.client.app.state.manager.store
        chat = store.conversation()
        tasks = [store.task(chat, 'agent', 'fixture') for _ in range(205)]
        for task in tasks:
            store.finish(task, 'reported', {'report': 'PRIVATE-RESULT-BLOB'})
        connection = store.connection
        result_reads = []

        @contextmanager
        def guarded_connection():
            with connection() as db:
                def authorize(action, table, column, _database, _trigger):
                    if action == sqlite3.SQLITE_READ and table == 'tasks' and column == 'result':
                        result_reads.append(column)
                        return sqlite3.SQLITE_DENY
                    return sqlite3.SQLITE_OK
                db.set_authorizer(authorize)
                yield db

        routes = ('/activity', f'/history/tasks/{tasks[0]}', '/history/tasks?limit=50')
        with patch.object(store, 'connection', guarded_connection):
            for route in routes:
                self.assertEqual(self.client.get(route).status_code, 401)
                self.assertEqual(self.client.get(route, headers={**self.headers, 'Origin': 'https://foreign.invalid'})
                                 .status_code, 403)
                response = self.client.get(route, headers=self.headers)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn('PRIVATE-RESULT-BLOB', response.text)
            value = self.client.get('/activity', headers=self.headers).json()
            self.assertEqual(len(value['tasks']), 50)
            self.assertEqual(value['approvals'], [])
            self.assertEqual(self.client.get('/history/tasks/missing', headers=self.headers).status_code, 404)
        self.assertEqual(result_reads, [])
        legacy = self.client.get('/tasks', headers=self.headers).json()['tasks']
        self.assertEqual(len(legacy), 200)
        self.assertIn('result', legacy[0])

    def test_history_support_routes_do_not_materialize_full_transcripts_for_existence(self):
        store = self.client.app.state.manager.store
        chat = store.conversation()
        store.message(chat, 'user', 'Retained transcript')
        with patch.object(store, 'messages', side_effect=AssertionError('Full transcript must not be loaded')):
            for suffix in ('goal', 'attachments'):
                self.assertEqual(self.client.get(f'/conversations/{chat}/{suffix}', headers=self.headers).status_code, 200)
                self.assertEqual(self.client.get(f'/conversations/missing/{suffix}', headers=self.headers).status_code, 404)
            uploaded = self.client.post(f'/conversations/{chat}/attachments?name=small.txt',
                                        content=b'small note', headers=self.headers)
            self.assertEqual(uploaded.status_code, 200)

    def test_export_authentication_origin_scope_and_completeness(self):
        store = self.client.app.state.manager.store
        chat = store.conversation('API export')
        for index in range(65):
            store.message(chat, 'user', str(index))
        route = f'/history/conversations/{chat}/export'
        self.assertEqual(self.client.get(route).status_code, 401)
        self.assertEqual(self.client.get(route, headers={**self.headers, 'Origin': 'https://foreign.invalid'})
                         .status_code, 403)
        response = self.client.get(route, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['message_count'], 65)
        self.assertTrue(response.json()['complete'])
        self.assertEqual(self.client.get('/history/conversations/missing/export', headers=self.headers).status_code, 404)
        with patch('local_agent.studio.history.MAX_EXPORT_MESSAGES', 1):
            rejected = self.client.get(route, headers=self.headers)
        self.assertEqual(rejected.status_code, 400)
        self.assertNotIn('markdown', rejected.json())

    def test_authentication_origin_and_validation_on_all_history_routes(self):
        for route in ('/history/conversations', '/history/tasks', '/history/conversations/missing/messages'):
            self.assertEqual(self.client.get(route).status_code, 401)
            self.assertEqual(self.client.get(route, headers={**self.headers, 'Origin': 'https://foreign.invalid'})
                             .status_code, 403)
            for params in ({'limit': 0}, {'limit': 101}, {'limit': 'true'}, {'cursor': 'x' * 2049}):
                self.assertEqual(self.client.get(route, params=params, headers=self.headers).status_code, 422)

    def test_real_pages_scope_cursor_and_legacy_endpoints_remain_compatible(self):
        store = self.client.app.state.manager.store
        chats = [store.conversation(f'API {i}') for i in range(5)]
        store.message(chats[0], 'user', 'visible')
        store.task(chats[0], 'chat', 'fixture')
        first = self.client.get('/history/conversations?limit=2', headers=self.headers).json()
        self.assertEqual(len(first['items']), 2)
        second = self.client.get('/history/conversations', params={'limit': 2, 'cursor': first['next']},
                                 headers=self.headers).json()
        self.assertFalse({r['id'] for r in first['items']} & {r['id'] for r in second['items']})
        self.assertEqual(self.client.get('/history/tasks', params={'cursor': first['next']},
                                        headers=self.headers).status_code, 400)
        self.assertEqual(self.client.get('/history/conversations/missing/messages', headers=self.headers).status_code, 404)
        items = self.client.get(f'/history/conversations/{chats[0]}/messages', headers=self.headers).json()['items']
        self.assertEqual(items[0]['content'], 'visible')
        self.assertNotIn('result', self.client.get('/history/tasks', headers=self.headers).json()['items'][0])
        self.assertIsInstance(self.client.get('/conversations', headers=self.headers).json(), list)
        self.assertIsInstance(self.client.get(f'/conversations/{chats[0]}/messages', headers=self.headers).json(), list)

    def test_single_conversation_metadata_is_authenticated_minimal_and_missing_safe(self):
        store = self.client.app.state.manager.store
        chat = store.conversation('Metadata title')
        route = f'/history/conversations/{chat}'
        self.assertEqual(self.client.get(route).status_code, 401)
        value = self.client.get(route, headers=self.headers).json()
        self.assertEqual(set(value), {'id', 'title', 'created'})
        self.assertEqual(value['id'], chat)
        self.assertEqual(value['title'], 'Metadata title')
        self.assertEqual(self.client.get('/history/conversations/missing', headers=self.headers).status_code, 404)
