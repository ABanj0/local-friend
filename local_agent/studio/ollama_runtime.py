"""Trusted host configuration for a local Ollama service; never supplied by tool input."""
import os
import shutil
from pathlib import Path

from local_agent.model import Ollama


def configured_path(value, base, label):
    if type(value) is not str or not value.strip() or len(value) > 4096 or any(c in value for c in '\0\r\n'):
        raise ValueError(f'Set [ollama].{label} to a nonempty filesystem path in agent.toml')
    return (base / value).resolve()


def launch(config):
    # A failed status probe must not turn an invalid remote endpoint into a public bind.
    Ollama(config['model'])
    base = Path(config['base'])
    settings = config.get('ollama', {})
    if type(settings) is not dict or set(settings) - {'executable', 'models'}:
        raise ValueError('[ollama] supports only executable and models paths in agent.toml')
    local = base / '.runtime/ollama/ollama.exe'
    if 'executable' in settings:
        executable = configured_path(settings['executable'], base, 'executable')
        if executable.name.casefold() != 'ollama.exe' or not executable.is_file():
            raise ValueError('Configured [ollama].executable must point to an existing ollama.exe')
    else:
        found = shutil.which('ollama')
        candidates = [local]
        if found:
            candidates.append(Path(found))
        for variable, relative in [('LOCALAPPDATA', 'Programs/Ollama/ollama.exe'),
                                   ('ProgramFiles', 'Ollama/ollama.exe')]:
            if os.environ.get(variable):
                candidates.append(Path(os.environ[variable]) / relative)
        executable = next((p for p in candidates if p.is_file()), None)
        if executable is None:
            raise ValueError('Ollama executable not found. Install Ollama for Windows or set '
                             '[ollama].executable and [ollama].models in agent.toml; see docs/desktop.md.')
    env = dict(os.environ, OLLAMA_HOST=config['model']['url'], OLLAMA_NO_CLOUD='1', OLLAMA_NUM_PARALLEL='1')
    env.pop('LOCAL_AGENT_STUDIO_TOKEN', None)
    if 'models' in settings:
        models = configured_path(settings['models'], base, 'models')
        if not models.is_dir():
            raise ValueError('Configured [ollama].models must point to an existing model directory')
        env['OLLAMA_MODELS'] = str(models)
    elif executable == local:
        env['OLLAMA_MODELS'] = str(base / '.runtime/models')
    return [str(executable), 'serve'], env
