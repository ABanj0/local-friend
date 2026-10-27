"""Actual approved-tree observations; no scheduler, inference or automatic dispatch."""
import hashlib
import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

from local_agent.safety import Denied, Policy, Stopped
from local_agent.studio import directory_snapshot as snapshots

from .support import WorkspaceTest


class DirectorySnapshotTests(WorkspaceTest):
    def observe(self, path='.'):
        return snapshots.observe(self.policy, path)

    def test_empty_and_unicode_binary_files_are_stable_private_and_read_only(self):
        empty = self.observe()
        self.assertTrue(empty['complete'])
        self.assertEqual(empty['files'], [])
        self.assertEqual(self.observe()['fingerprint'], empty['fingerprint'])
        folder = self.policy.root / 'source'
        folder.mkdir()
        raw = b'\x00\xffPRIVATE-CONTENT-CANARY\r\n'
        target = folder / 'snow-\u2603.bin'
        target.write_bytes(raw)
        before = target.stat().st_mtime_ns
        observed = self.observe()
        self.assertTrue(observed['complete'])
        self.assertEqual(observed['files'][0]['path'], 'source/snow-\u2603.bin')
        self.assertEqual(observed['files'][0]['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(self.observe()['fingerprint'], observed['fingerprint'])
        self.assertNotIn('PRIVATE-CONTENT', json.dumps(observed))
        self.assertNotIn(str(self.policy.root), json.dumps(observed))
        self.assertEqual(target.read_bytes(), raw)
        self.assertEqual(target.stat().st_mtime_ns, before)
        self.assertFalse(self.approvals)

    def test_same_size_and_restored_timestamp_changes_still_change_content_fingerprint(self):
        target = self.policy.root / 'code.py'
        target.write_bytes(b'aaaa')
        first = self.observe()
        stamp = target.stat()
        target.write_bytes(b'bbbb')
        os.utime(target, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        second = self.observe()
        self.assertTrue(second['complete'])
        self.assertEqual(first['files'][0]['version'], second['files'][0]['version'])
        self.assertNotEqual(first['files'][0]['sha256'], second['files'][0]['sha256'])
        self.assertNotEqual(first['fingerprint'], second['fingerprint'])

    def test_creation_deletion_rename_and_identical_replacement_have_distinct_fingerprints(self):
        initial = self.observe()
        first = self.policy.root / 'a.py'
        first.write_bytes(b'fixed input')
        created = self.observe()
        renamed = self.policy.root / 'b.py'
        first.rename(renamed)
        moved = self.observe()
        saved = Path(self.temp.name) / 'saved-old.py'
        renamed.rename(saved)
        renamed.write_bytes(saved.read_bytes())
        recreated = self.observe()
        renamed.unlink()
        deleted = self.observe()
        self.assertEqual(initial['fingerprint'], deleted['fingerprint'])
        self.assertEqual(len({row['fingerprint'] for row in (initial, created, moved, recreated)}), 4)
        self.assertEqual(moved['files'][0]['sha256'], recreated['files'][0]['sha256'])
        self.assertNotEqual(moved['files'][0]['version'], recreated['files'][0]['version'])

    def test_selected_directory_has_no_cross_project_results_or_authority(self):
        for name in ('first', 'second'):
            folder = self.policy.root / name
            folder.mkdir()
            (folder / 'code.py').write_text(name, encoding='utf-8')
        result = self.observe('first')
        self.assertTrue(result['complete'])
        self.assertEqual([row['path'] for row in result['files']], ['first/code.py'])
        self.assertNotEqual(result['scope'], self.observe('second')['scope'])
        with patch.object(self.policy, 'path', side_effect=AssertionError('Invalid scope must not touch filesystem')):
            for path in (None, True, 5, '../outside', 'first\\code.py', '/absolute', 'first/./code.py', 'first/\u202e'):
                with self.subTest(path=path), self.assertRaises(Denied):
                    self.observe(path)

    def test_credentials_controls_dependencies_and_actual_agent_state_never_affect_snapshot(self):
        self.config['paths']['state'] = str(self.policy.root / 'private-internal-state')
        self.policy = Policy(self.config)
        for name in ('.git', '.aws', '.ssh', '.codex', '.agents', '.venv', 'node_modules', '__pycache__', 'dist'):
            folder = self.policy.root / name
            folder.mkdir()
            (folder / 'PRIVATE-CONTROL-CANARY').write_text('private')
        for name in ('.env', '.env.local', '.npmrc', 'private.key', 'private.pem'):
            (self.policy.root / name).write_text('PRIVATE-CREDENTIAL-CANARY')
        (self.policy.state / 'audit.jsonl').write_text('PRIVATE-STATE-CANARY')
        (self.policy.root / 'public.py').write_text('# selected source')
        observed = self.observe()
        self.assertTrue(observed['complete'])
        self.assertEqual([row['path'] for row in observed['files']], ['public.py'])
        (self.policy.state / 'new-event').write_text('owned output')
        (self.policy.root / '__pycache__' / 'new.pyc').write_bytes(b'cache')
        self.assertEqual(self.observe()['fingerprint'], observed['fingerprint'])
        self.assertNotIn('PRIVATE-', json.dumps(observed))
        for path in ('private-internal-state', '.env.local', 'node_modules', '.aws'):
            with self.subTest(path=path), self.assertRaises(Denied):
                self.observe(path)

    def test_hardlinked_alias_is_not_opened_or_included(self):
        outside = Path(self.temp.name) / 'outside-private.txt'
        outside.write_text('PRIVATE-OUTSIDE-CANARY')
        os.link(outside, self.policy.root / 'alias.txt')
        with patch.object(Path, 'open', side_effect=AssertionError('Links must not be read')):
            result = self.observe()
        self.assertTrue(result['complete'])
        self.assertEqual(result['files'], [])
        self.assertEqual(result['skipped']['denied'], 1)
        self.assertNotIn('PRIVATE-', json.dumps(result))

    def test_real_junction_never_reads_foreign_directory_and_cannot_be_requested_root(self):
        if os.name != 'nt':
            self.skipTest('Windows junction boundary')
        outside = Path(self.temp.name) / 'foreign'
        outside.mkdir()
        (outside / 'private.txt').write_text('PRIVATE-JUNCTION-CANARY')
        alias = self.policy.root / 'alias'
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(alias), str(outside)],
                                capture_output=True, text=True, timeout=5, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        with patch.object(Path, 'open', side_effect=AssertionError('Junctions must not be followed')):
            result = self.observe()
            with self.assertRaises(Denied):
                self.observe('alias')
        self.assertEqual(result['files'], [])
        self.assertEqual(result['skipped']['denied'], 1)

    def test_entry_file_byte_manifest_and_time_caps_are_explicitly_incomplete(self):
        for index in range(3):
            (self.policy.root / f'file{index}.py').write_bytes(b'12345678')
        for constant, value, reason in [('MAX_ENTRIES', 1, 'entry_limit'), ('MAX_FILES', 1, 'file_limit'),
                                       ('MAX_BYTES', 10, 'byte_limit'), ('MAX_MANIFEST', 1, 'manifest_limit'),
                                       ('TIME_LIMIT', 0, 'time_limit')]:
            with self.subTest(reason=reason), patch.object(snapshots, constant, value):
                result = self.observe()
                self.assertFalse(result['complete'])
                self.assertIsNone(result['fingerprint'])
                self.assertEqual(result['stop_reason'], reason)
                self.assertLessEqual(result['counts']['bytes_read'], result['limits']['bytes'])

    def test_oversized_unreadable_and_deep_inputs_do_not_become_complete_snapshots(self):
        target = self.policy.root / 'input.txt'
        target.write_bytes(b'x' * (snapshots.MAX_FILE + 1))
        result = self.observe()
        self.assertFalse(result['complete'])
        self.assertIsNone(result['fingerprint'])
        self.assertEqual(result['skipped']['oversized'], 1)
        target.write_bytes(b'small')
        with patch.object(Path, 'open', side_effect=PermissionError('PRIVATE-ERROR-CANARY')):
            result = self.observe()
        self.assertFalse(result['complete'])
        self.assertNotIn('PRIVATE-', json.dumps(result))
        target.unlink()
        (self.policy.root / 'child').mkdir()
        with patch.object(snapshots, 'MAX_DEPTH', 0):
            result = self.observe()
        self.assertFalse(result['complete'])
        self.assertEqual(result['skipped']['depth'], 1)

    def test_change_during_read_never_yields_valid_fingerprint(self):
        target = self.policy.root / 'changing.py'
        target.write_bytes(b'original')
        original_open = Path.open

        class Reader:
            def __init__(self, source):
                self.source = source

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.source.close()

            def fileno(self):
                return self.source.fileno()

            def read(self, size):
                data = self.source.read(size)
                with original_open(target, 'wb') as writer:
                    writer.write(b'changed and longer')
                return data

        with patch.object(Path, 'open', side_effect=lambda path, *args, **kwargs: Reader(original_open(path, *args, **kwargs)), autospec=True):
            observed = self.observe()
        self.assertFalse(observed['complete'])
        self.assertIsNone(observed['fingerprint'])
        self.assertFalse(observed['files'])

    def test_tree_change_after_enumeration_is_incomplete_and_does_not_delete_new_file(self):
        (self.policy.root / 'original.py').write_text('# source')
        original_scandir = os.scandir
        initial = self.policy.root.stat()

        class Entries:
            def __enter__(self):
                self.source = original_scandir(self.policy_root)
                return self

            def __exit__(self, *args):
                self.source.close()

            def __iter__(self):
                yield from list(self.source)
                (self.policy_root / 'late.py').write_text('# late arrival')
                # Directory timestamps need not distinguish the new namespace state.
                os.utime(self.policy_root, ns=(initial.st_atime_ns, initial.st_mtime_ns))

        entries = Entries()
        entries.policy_root = self.policy.root
        with patch.object(snapshots.os, 'scandir', return_value=entries):
            observed = self.observe()
        self.assertFalse(observed['complete'])
        self.assertIsNone(observed['fingerprint'])
        self.assertTrue((self.policy.root / 'late.py').exists())

    def test_validation_pass_shares_entry_budget_and_honors_stop(self):
        for name in ('a.py', 'b.py'):
            (self.policy.root / name).write_bytes(b'source')
        with patch.object(snapshots, 'MAX_ENTRIES', 3):
            result = self.observe()
        self.assertFalse(result['complete'])
        self.assertEqual(result['stop_reason'], 'entry_limit')
        self.assertEqual(result['counts']['entries'], 3)
        self.assertIsNone(result['fingerprint'])
        original = os.scandir
        calls = []

        def scanning(path):
            calls.append(path)
            if len(calls) == 2:
                self.policy.stop_event.set()
            return original(path)

        with patch.object(snapshots.os, 'scandir', side_effect=scanning), self.assertRaises(Stopped):
            self.observe()
        self.assertEqual(len(calls), 2)

    def test_directory_replacement_before_final_recheck_is_incomplete_even_for_identical_bytes(self):
        folder = self.policy.root / 'source'
        folder.mkdir()
        target = folder / 'code.py'
        target.write_bytes(b'original')
        original_path = self.policy.path
        checks = []

        def checked_path(value, **kwargs):
            if value == 'source':
                checks.append(value)
            if value == 'source' and len(checks) == 3:
                # Windows open file handles can prevent parent rename. Perform the
                # actual replacement after reads/scandir close, before final validation.
                folder.rename(folder.with_name('saved-source'))
                folder.mkdir()
                target.write_bytes(b'original')
            return original_path(value, **kwargs)

        with patch.object(self.policy, 'path', side_effect=checked_path):
            observed = self.observe('source')
        self.assertFalse(observed['complete'])
        self.assertIsNone(observed['fingerprint'])
        self.assertEqual(target.read_bytes(), b'original')
        self.assertEqual((self.policy.root / 'saved-source/code.py').read_bytes(), b'original')

    def test_hardlink_added_before_open_is_detected_before_reading_any_bytes(self):
        target = self.policy.root / 'source.py'
        target.write_bytes(b'private source')
        original_open = Path.open
        reads = []

        class Reader:
            def __init__(self, source):
                self.source = source

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.source.close()

            def fileno(self):
                return self.source.fileno()

            def read(self, size):
                reads.append(size)
                return self.source.read(size)

        def opening(path, *args, **kwargs):
            os.link(target, Path(self.temp.name) / 'late-alias.py')
            return Reader(original_open(path, *args, **kwargs))

        with patch.object(Path, 'open', side_effect=opening, autospec=True):
            observed = self.observe()
        self.assertEqual(reads, [])
        self.assertFalse(observed['complete'])
        self.assertIsNone(observed['fingerprint'])

    def test_wide_unicode_manifest_is_bounded_and_stop_prevents_scanning(self):
        for index in range(90):
            (self.policy.root / (str(index) + '\u2603' * 100 + '.txt')).write_bytes(b'')
        observed = self.observe()
        self.assertFalse(observed['complete'])
        self.assertEqual(observed['stop_reason'], 'manifest_limit')
        self.assertLessEqual(len(json.dumps(observed).encode('ascii')), 64 * 1024)
        self.policy.stop_event.set()
        with patch.object(snapshots.os, 'scandir', side_effect=AssertionError('Stop must precede observation')), self.assertRaises(Stopped):
            self.observe()
