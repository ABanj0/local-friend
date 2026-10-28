import hashlib
import runpy
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

manifest = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/release-manifest.py'))


class ReleaseManifestTests(unittest.TestCase):
    def test_unsigned_bundle_prediction_hashes_tagged_contents_without_mutating_input(self):
        original = b'before__TAURI_BUNDLE_TYPE_VAR_UNKafter'
        expected = b'before__TAURI_BUNDLE_TYPE_VAR_NSSafter'
        record = manifest['nsis_tag_hash'](original, unsigned=True)
        self.assertEqual(record['status'], 'predicted')
        self.assertEqual(record['bytes'], len(expected))
        self.assertEqual(record['sha256'], hashlib.sha256(expected).hexdigest())
        self.assertNotEqual(record['sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(original, b'before__TAURI_BUNDLE_TYPE_VAR_UNKafter')

    def test_already_tagged_image_keeps_its_actual_digest(self):
        raw = b'before__TAURI_BUNDLE_TYPE_VAR_NSSafter'
        record = manifest['nsis_tag_hash'](raw, unsigned=True)
        self.assertEqual(record['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(record['derivation'], 'unsigned_build_input_already_nsis_tagged')

    def test_missing_mixed_and_repeated_markers_never_produce_a_payload_digest(self):
        for raw in [b'no marker', b'__TAURI_BUNDLE_TYPE_VAR_UNK' * 2,
                    b'__TAURI_BUNDLE_TYPE_VAR_NSS' * 2,
                    b'__TAURI_BUNDLE_TYPE_VAR_UNK__TAURI_BUNDLE_TYPE_VAR_NSS']:
            with self.subTest(raw=raw):
                record = manifest['nsis_tag_hash'](raw, unsigned=True)
                self.assertEqual(record['status'], 'unavailable')
                self.assertNotIn('sha256', record)

    def test_signed_or_uncertain_source_never_claims_a_deterministic_installed_hash(self):
        for value in (False, None, 1, 'true'):
            with self.subTest(value=value):
                record = manifest['nsis_tag_hash'](b'__TAURI_BUNDLE_TYPE_VAR_UNK', unsigned=value)
                self.assertEqual(record['status'], 'unavailable')
                self.assertNotIn('sha256', record)

    def test_actual_certificate_presence_blocks_prediction_before_transforming(self):
        image = SimpleNamespace(OPTIONAL_HEADER=SimpleNamespace(
            DATA_DIRECTORY=[None] * 4 + [SimpleNamespace(VirtualAddress=1, Size=100)]))
        context = unittest.mock.MagicMock()
        context.__enter__.return_value = image
        with (patch.object(Path, 'is_file', return_value=True),
              patch.object(Path, 'read_bytes', return_value=b'__TAURI_BUNDLE_TYPE_VAR_UNK'),
              patch.dict('sys.modules', {'pefile': SimpleNamespace(PE=lambda **kwargs: context)})):
            record = manifest['nsis_main_payload'](Path('fixture.exe'))
        self.assertEqual(record['status'], 'unavailable')
        self.assertNotIn('sha256', record)

    def test_missing_binary_and_missing_inspector_are_explicitly_unavailable(self):
        with patch.object(Path, 'is_file', return_value=False):
            self.assertEqual(manifest['nsis_main_payload'](Path('missing.exe'))['reason'], 'missing_main_binary')
        with (patch.object(Path, 'is_file', return_value=True), patch.dict('sys.modules', {'pefile': None})):
            self.assertEqual(manifest['nsis_main_payload'](Path('fixture.exe'))['reason'],
                             'PE_inspection_dependency_missing')
