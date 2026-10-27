"""Operator-invoked repair of installed configuration, never an agent/API capability."""
import argparse
import hashlib
import json
import os
import tomllib
import uuid
from pathlib import Path

from local_agent.file_ops import staging, windows_replace
from local_agent.review import fingerprint, require_unchanged
from local_agent.studio.ollama_runtime import configured_path


def configure(destination, executable, models):
    destination = Path(destination).absolute()
    if any(p.is_symlink() or p.is_junction() for p in (destination, *destination.parents)):
        raise ValueError('Configuration repair requires a regular path without links')
    before = fingerprint(destination, 65536)
    if before is None:
        raise ValueError('Launch installed Studio once to create agent.toml before configuration')
    raw = destination.read_bytes()
    require_unchanged(before[-1], hashlib.sha256(raw).hexdigest())
    values = tomllib.loads(raw.decode('utf-8-sig'))
    paths = {key: str(configured_path(str(value), destination.parent, key))
             for key, value in [('executable', executable), ('models', models)]}
    if Path(paths['executable']).name.casefold() != 'ollama.exe' or not Path(paths['executable']).is_file():
        raise ValueError('Select an existing ollama.exe')
    if not Path(paths['models']).is_dir():
        raise ValueError('Select the existing Ollama model directory')
    if 'ollama' in values:
        if values['ollama'] == paths:
            return None
        raise ValueError('[ollama] already exists; review its paths manually instead of overwriting it')
    newline = '\r\n' if b'\r\n' in raw else '\n'
    suffix = newline + '[ollama]' + newline + ''.join(
        f'{key} = {json.dumps(value, ensure_ascii=False)}{newline}' for key, value in paths.items())
    updated = raw + suffix.encode('utf-8')
    require_unchanged({**values, 'ollama': paths}, tomllib.loads(updated.decode('utf-8-sig')))
    backup = destination.with_name(destination.name + '.before-ollama-' + uuid.uuid4().hex + '.bak')
    with staging(destination) as staged:
        with staged.open('wb') as output:
            output.write(updated)
            output.flush()
            os.fsync(output.fileno())
        require_unchanged(before, fingerprint(destination, 65536))
        with backup.open('xb') as output:
            output.write(raw)
        require_unchanged(before, fingerprint(destination, 65536))
        if os.name == 'nt':
            windows_replace(destination, staged)
        else:
            os.chmod(staged, destination.stat().st_mode & 0o777)
            os.replace(staged, destination)
    return backup


def main():
    parser = argparse.ArgumentParser(description='Configure existing portable Ollama for installed Studio')
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--executable', required=True, type=Path)
    parser.add_argument('--models', required=True, type=Path)
    args = parser.parse_args()
    backup = configure(args.config, args.executable, args.models)
    print('Installed Ollama paths configured; original settings backed up. Restart Studio.' if backup
          else 'Installed Ollama paths already match. Restart Studio.')


if __name__ == '__main__':
    main()
