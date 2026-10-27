import copy
import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request

from local_agent.studio.ollama_runtime import launch

from .studio_socket_support import StudioSocketFixture
from .studio_support import StudioAPIFixture
from .support import WorkspaceTest


class OllamaRuntimeTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.config['base'] = self.temp.name
        self.binary = Path(self.temp.name) / 'portable/ollama.exe'
        self.binary.parent.mkdir()
        self.binary.write_bytes(b'not executed by discovery tests')
        self.models = Path(self.temp.name) / 'weights'
        self.models.mkdir()

    def test_installed_base_reuses_explicit_portable_binary_and_models_without_path(self):
        self.config['ollama'] = {'executable': str(self.binary), 'models': str(self.models)}
        before = copy.deepcopy(self.config)
        with patch.dict(os.environ, {'LOCAL_AGENT_STUDIO_TOKEN': 'private-session-token'}):
            argv, env = launch(self.config)
        self.assertEqual(argv, [str(self.binary), 'serve'])
        self.assertEqual(env['OLLAMA_MODELS'], str(self.models))
        self.assertEqual(env['OLLAMA_HOST'], self.config['model']['url'])
        self.assertEqual(env['OLLAMA_NO_CLOUD'], '1')
        self.assertNotIn('LOCAL_AGENT_STUDIO_TOKEN', env)
        self.assertEqual(self.config, before)

    def test_relative_paths_resolve_against_configuration_not_working_directory(self):
        self.config['ollama'] = {'executable': 'portable/ollama.exe', 'models': 'weights'}
        argv, env = launch(self.config)
        self.assertEqual(argv[0], str(self.binary))
        self.assertEqual(env['OLLAMA_MODELS'], str(self.models))

    def test_repository_portable_precedes_path_and_retains_repository_store(self):
        local = Path(self.temp.name) / '.runtime/ollama/ollama.exe'
        local.parent.mkdir(parents=True)
        local.write_bytes(b'not executed')
        with patch('local_agent.studio.ollama_runtime.shutil.which', return_value=str(self.binary)):
            argv, env = launch(self.config)
        self.assertEqual(argv[0], str(local))
        self.assertEqual(env['OLLAMA_MODELS'], str(Path(self.temp.name) / '.runtime/models'))

    def test_standard_user_install_is_found_without_path_and_preserves_environment_models(self):
        root = Path(self.temp.name) / 'user'
        standard = root / 'Programs/Ollama/ollama.exe'
        standard.parent.mkdir(parents=True)
        standard.write_bytes(b'not executed')
        with (patch('local_agent.studio.ollama_runtime.shutil.which', return_value=None),
              patch.dict(os.environ, {'LOCALAPPDATA': str(root), 'OLLAMA_MODELS': str(self.models)})):
            argv, env = launch(self.config)
        self.assertEqual(argv[0], str(standard))
        self.assertEqual(env['OLLAMA_MODELS'], str(self.models))

    def test_path_install_and_explicit_models_preserve_precedence(self):
        self.config['ollama'] = {'models': str(self.models)}
        with patch('local_agent.studio.ollama_runtime.shutil.which', return_value=str(self.binary)):
            argv, env = launch(self.config)
        self.assertEqual(argv[0], str(self.binary))
        self.assertEqual(env['OLLAMA_MODELS'], str(self.models))

    def test_invalid_explicit_path_does_not_fall_back_to_another_binary(self):
        for value in ['missing.exe', 'portable', 'portable/ollama.exe --serve', '', None, ['ollama'], 'bad\npath']:
            with self.subTest(value=value):
                self.config['ollama'] = {'executable': value}
                with (patch('local_agent.studio.ollama_runtime.shutil.which', return_value=str(self.binary)),
                      self.assertRaises(ValueError)):
                    launch(self.config)

    def test_bad_model_directory_unknown_settings_and_remote_bind_are_rejected(self):
        for settings in [{'models': 'missing'}, {'models': ''}, {'argv': ['anything']}, ['anything']]:
            with self.subTest(settings=settings):
                self.config['ollama'] = settings
                with self.assertRaises(ValueError):
                    launch(self.config)
        self.config['ollama'] = {'executable': str(self.binary)}
        for url in ['http://0.0.0.0:11434', 'http://example.com', 'http://user:secret@127.0.0.1:11434']:
            self.config['model']['url'] = url
            with self.assertRaises(ValueError):
                launch(self.config)

    def test_missing_binary_has_actionable_installed_configuration_guidance(self):
        with (patch('local_agent.studio.ollama_runtime.shutil.which', return_value=None),
              patch.dict(os.environ, {'LOCALAPPDATA': self.temp.name, 'ProgramFiles': self.temp.name}),
              self.assertRaisesRegex(ValueError, r'\[ollama\].executable')):
            launch(self.config)


class OllamaRuntimeAPITests(StudioAPIFixture, WorkspaceTest):
    def test_authenticated_start_uses_only_trusted_config_and_does_not_accept_body_paths(self):
        binary = Path(self.temp.name) / 'ollama.exe'
        binary.write_bytes(b'not executed')
        models = Path(self.temp.name) / 'models'
        models.mkdir()
        self.config['ollama'] = {'executable': str(binary), 'models': str(models)}
        with (patch('local_agent.studio.api.Ollama.request', side_effect=OSError('offline')),
              patch('local_agent.studio.process_output.ProcessOutput.start', return_value=True) as start):
            self.assertEqual(self.client.post('/models/start').status_code, 401)
            response = self.client.post('/models/start', headers=self.headers, json={'executable': 'untrusted.exe'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(start.call_args.args[0], [str(binary), 'serve'])
        self.assertEqual(start.call_args.args[1]['OLLAMA_MODELS'], str(models))

    def test_invalid_runtime_never_spawns_and_existing_service_never_resolves_or_stops_it(self):
        self.config['ollama'] = {'executable': 'missing.exe'}
        with (patch('local_agent.studio.api.Ollama.request', side_effect=OSError('offline')),
              patch('local_agent.studio.process_output.ProcessOutput.start') as start):
            response = self.client.post('/models/start', headers=self.headers)
        self.assertEqual(response.status_code, 400)
        start.assert_not_called()
        with (patch('local_agent.studio.api.Ollama.request', return_value={'models': []}),
              patch('local_agent.studio.api.ollama_launch') as discover):
            response = self.client.post('/models/start', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['started'])
        discover.assert_not_called()


@unittest.skipUnless(os.environ.get('LIVE_OLLAMA_RUNTIME') == '1', 'Actual portable Ollama startup is opt-in')
class LiveOllamaRuntimeTests(StudioSocketFixture, WorkspaceTest):
    def start_backend(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            self.model_port = listener.getsockname()[1]
        root = Path.cwd()
        source = self.socket_config.read_text(encoding='utf-8')
        source = source.replace('http://127.0.0.1:11434', f'http://127.0.0.1:{self.model_port}')
        source += '\n[ollama]\nexecutable = ' + json.dumps(str(root / '.runtime/ollama/ollama.exe'))
        source += '\nmodels = ' + json.dumps(str(root / '.runtime/models')) + '\n'
        self.socket_config.write_text(source, encoding='utf-8')
        super().start_backend()

    def test_portable_start_from_installed_base_and_owned_shutdown(self):
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(60)'],
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.addCleanup(unrelated.wait, 5)
        self.addCleanup(unrelated.terminate)
        self.assertFalse(self.http('/models')['running'])
        request = Request(f'http://127.0.0.1:{self.port}/models/start', data=b'{}',
            headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
        with self.opener.open(request, timeout=5) as response:
            self.assertTrue(json.load(response)['started'])
        deadline = time.monotonic() + 15
        status = self.http('/models')
        while not status['running'] and time.monotonic() < deadline:
            time.sleep(.1)
            status = self.http('/models')
        self.assertTrue(status['running'], 'Configured portable service never became ready')
        observed = {'service_started': True, 'model_names': [m['name'] for m in status['models']],
            'model_store_access_denied': 'Access is denied' in status['diagnostics']['output'],
            'inference_tested': False}
        self.stop_backend()
        with socket.socket() as probe:
            probe.settimeout(1)
            self.assertNotEqual(probe.connect_ex(('127.0.0.1', self.model_port)), 0)
        self.assertIsNone(unrelated.poll())
        print('Actual configured Ollama startup: ' + json.dumps(observed))
