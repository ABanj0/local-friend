import tomllib
from pathlib import Path

from local_agent.studio.ollama_config import configure

from .support import WorkspaceTest


class OllamaConfigTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.target = Path(self.temp.name) / 'agent.toml'
        self.original = b'# user settings\r\n[model]\r\nname="kept"\r\n[paths]\r\nworkspace="kept"\r\n'
        self.target.write_bytes(self.original)
        self.binary = Path(self.temp.name) / "portable engine's files" / 'ollama.exe'
        self.binary.parent.mkdir()
        self.binary.write_bytes(b'not executed')
        self.models = Path(self.temp.name) / 'model files'
        self.models.mkdir()

    def test_appends_paths_preserves_existing_bytes_backs_up_and_is_idempotent(self):
        backup = configure(self.target, self.binary, self.models)
        self.assertEqual(backup.read_bytes(), self.original)
        self.assertTrue(self.target.read_bytes().startswith(self.original))
        data = tomllib.loads(self.target.read_text(encoding='utf-8'))
        self.assertEqual(data['model'], {'name': 'kept'})
        self.assertEqual(data['ollama'], {'executable': str(self.binary), 'models': str(self.models)})
        self.assertIsNone(configure(self.target, self.binary, self.models))
        self.assertEqual(len(list(self.target.parent.glob('*.bak'))), 1)

    def test_existing_different_section_is_never_overwritten(self):
        self.target.write_bytes(self.original + b'\r\n[ollama]\r\nexecutable="other"\r\n')
        before = self.target.read_bytes()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            configure(self.target, self.binary, self.models)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(list(self.target.parent.glob('*.bak')))

    def test_missing_config_or_runtime_makes_no_changes(self):
        for config, binary, models in [(self.target.parent / 'missing.toml', self.binary, self.models),
                                       (self.target, self.binary.parent / 'missing.exe', self.models),
                                       (self.target, self.binary, self.models / 'missing')]:
            with self.subTest(config=config, binary=binary, models=models), self.assertRaises(ValueError):
                configure(config, binary, models)
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertFalse(list(self.target.parent.glob('*.bak')))

    def test_hardlinked_configuration_is_refused(self):
        import os

        from local_agent.safety import Denied
        alias = self.target.parent / 'alias.toml'
        os.link(self.target, alias)
        with self.assertRaises(Denied):
            configure(self.target, self.binary, self.models)
        self.assertEqual(alias.read_bytes(), self.original)
