"""Operator-only native acceptance: closing Studio must preserve independent Ollama."""
import argparse
import hashlib
import http.client
import json
import os
import re
import runpy
import socket
import sys
import threading
import time
import tomllib
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from local_agent.review import fingerprint, require_unchanged
from local_agent.studio.ollama_runtime import launch
from local_agent.studio.process_output import ProcessOutput

# Reuse the tested operator's package identity, native observation and console contracts.
# Neither script is imported by the application, an API endpoint or the tool registry.
RECOVERY = runpy.run_path(str(Path(__file__).with_name('native-recovery-check.py')))
CheckFailed = RECOVERY['CheckFailed']
PORT = 11434


def configuration():
    path = Path(os.environ['LOCALAPPDATA']) / 'local.agent.studio/agent.toml'
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise CheckFailed('linked_configuration')
    before = fingerprint(path, 65536)
    with path.open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise CheckFailed('configuration_too_large')
    require_unchanged(before[-1], hashlib.sha256(raw).hexdigest())
    require_unchanged(before, fingerprint(path, 65536))
    config = tomllib.loads(raw.decode('utf-8-sig'))
    config['base'] = str(path.parent)
    # This experiment observes the default literal listener only, without redirects/DNS.
    if config['model']['url'].rstrip('/') != 'http://127.0.0.1:11434':
        raise CheckFailed('nondefault_model_endpoint')
    return config


def listener():
    import psutil
    rows = [c for c in psutil.net_connections(kind='tcp')
            if c.status == psutil.CONN_LISTEN and c.laddr.port == PORT]
    if not rows:
        return None
    if len(rows) != 1 or rows[0].laddr.ip != '127.0.0.1' or not rows[0].pid:
        raise CheckFailed('unrecognized_model_listener')
    process = psutil.Process(rows[0].pid)
    if process.name().casefold() != 'ollama.exe':
        raise CheckFailed('unrecognized_model_listener')
    return process.pid, process.create_time()


def healthy():
    """Fixed GET only; bounded bytes and absolute timer, no proxy or redirect handling."""
    connection = http.client.HTTPConnection('127.0.0.1', PORT, timeout=1)
    timer = None
    try:
        connection.connect()
        peer = connection.sock

        def expire():
            try:
                peer.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        timer = threading.Timer(2, expire)
        timer.daemon = True
        timer.start()
        connection.request('GET', '/api/version', headers={'Connection': 'close'})
        response = connection.getresponse()
        raw = response.read(4097)
        if response.status != 200 or len(raw) > 4096:
            return False
        value = json.loads(raw)
        return (type(value) is dict and type(value.get('version')) is str
                and re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}(?:[-+][\w.-]{1,64})?',
                                 value['version']) is not None)
    except (OSError, ValueError, http.client.HTTPException):
        return False
    finally:
        if timer:
            timer.cancel()
        connection.close()


class SharedModel:
    def __init__(self):
        self.owner = ProcessOutput()
        self.identity = None
        self.fixture_started = False

    def prepare(self, config, deadline):
        self.identity = listener()
        if self.identity is None:
            argv, env = launch(config)
            self.fixture_started = True
            self.owner.start(argv, env)
            while time.monotonic() < deadline:
                if self.owner.proc.poll() is not None:
                    raise CheckFailed('model_fixture_exited')
                observed = listener()
                if observed is not None:
                    owned = RECOVERY['descendants'](self.owner.proc)
                    import psutil
                    owned.append((self.owner.proc.pid, psutil.Process(self.owner.proc.pid).create_time()))
                    if observed not in owned:
                        raise CheckFailed('model_listener_ownership_changed')
                    self.identity = observed
                    break
                time.sleep(.05)
            if self.identity is None:
                raise CheckFailed('model_start_deadline')
        self.verify()

    def verify(self):
        if (self.identity is None or listener() != self.identity
                or not RECOVERY['alive'](self.identity) or not healthy()
                or listener() != self.identity):
            raise CheckFailed('independent_model_not_healthy')

    def close(self):
        # An existing service was never assigned to this owner/job and cannot be stopped here.
        self.owner.close()


def run(root, *, exercise=False, seconds=180):
    if type(exercise) is not bool or type(seconds) is not int or not 60 <= seconds <= 300:
        raise ValueError('Duration must be an integer from 60 to 300 seconds')
    root = Path(root).resolve()
    case = root / '.runtime' / ('native-shared-model-' + uuid.uuid4().hex)
    RECOVERY['no_links'](root, case)
    case.mkdir(parents=True)
    report = {'version': 1, 'scope': 'installed_native_independent_ollama_preservation',
              'status': 'blocked', 'reason': None, 'native_acceptance': 'not_verified',
              'exercise_requested': exercise, 'owner_observations': [],
              'owned_cleanup': False, 'raw_output_exported': False,
              'webview_profile_retained': True}
    native, model = ProcessOutput(), SharedModel()
    attempts = RECOVERY['Attempts']()
    try:
        if RECOVERY['existing_studio']():
            raise CheckFailed('existing_studio_preserved')
        executable, hashes = RECOVERY['installed'](root)
        report['installed_sha256'] = hashes
        config = configuration()
        # Reserve and release once for a preflight collision check. Never accept requests.
        try:
            guard = RECOVERY['PortGuard']()
        except OSError:
            raise CheckFailed('backend_port_unavailable') from None
        guard.close()
        if not exercise:
            model.identity = listener()
            if model.identity is None:
                launch(config)  # Validate the trusted launch without starting it.
            else:
                model.verify()
            report['status'] = 'ready'
        else:
            deadline = time.monotonic() + seconds
            model.prepare(config, min(deadline, time.monotonic() + 20))
            report['independent_model_source'] = 'fixture' if model.fixture_started else 'existing'
            report['model_identity'] = {'pid': model.identity[0], 'created': model.identity[1]}
            env = dict(os.environ)
            env.pop('LOCAL_AGENT_STUDIO_TOKEN', None)
            env.pop('WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS', None)
            env['WEBVIEW2_USER_DATA_FOLDER'] = str(case / 'webview')
            for name, digest in hashes.items():
                if RECOVERY['binary_hash'](executable.with_name(name))['sha256'] != digest:
                    raise CheckFailed('installed_binary_changed')
            # Recheck before launching; refuse a concurrent owner instance rather than focus it.
            if RECOVERY['existing_studio']():
                raise CheckFailed('existing_studio_preserved')
            native.start([str(executable)], env)
            report['native_pid'] = native.proc.pid
            RECOVERY['confirm']('CONNECTED', 'Wait for Connected locally in this test Studio. '
                                'Do not submit tasks.', native, attempts, deadline)
            if len(attempts.rows) != 1 or not RECOVERY['owned_listener'](native):
                raise CheckFailed('native_connection_not_observed')
            owned = RECOVERY['descendants'](native.proc)
            if model.identity in owned:
                raise CheckFailed('model_is_not_independent')
            model.verify()
            report['owner_observations'].append('connected_locally')
            RECOVERY['confirm']('CLOSED', 'Close this test Studio using X.', native, attempts,
                                deadline, allow_exit=True)
            RECOVERY['wait_for'](lambda: native.proc.poll() is not None
                                 and not any(RECOVERY['alive'](p) for p in owned),
                                 native, attempts, deadline, allow_exit=True)
            model.verify()
            report['owner_observations'].append('normal_window_close')
            report['owned_descendants_exited_before_fixture_cleanup'] = True
            report['independent_ollama_same_identity_listener_and_health'] = True
            report['status'], report['native_acceptance'] = 'passed', 'independent_ollama_normal_close_only'
    except CheckFailed as exc:
        report['reason'] = str(exc)
    except Exception:  # noqa: BLE001 -- never export raw config, errors, output or credentials
        report['reason'] = 'check_failed'
    finally:
        cleaned = True
        for owner in (native, model):
            try:
                owner.close()
            except Exception:  # noqa: BLE001 -- attempt both independent owned jobs
                cleaned = False
        report['owned_cleanup'] = cleaned and all(
            owner.proc is None or owner.proc.poll() is not None for owner in (native, model.owner))
        if not report['owned_cleanup']:
            report.update(status='blocked', reason='owned_cleanup_failed', native_acceptance='not_verified')
    data = json.dumps(report, indent=2)
    if len(data.encode()) > 16384:
        raise ValueError('Report exceeds fixed budget')
    path = case / 'report.json'
    RECOVERY['no_links'](root, path)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(data + '\n')
    return report, path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exercise', action='store_true', help='Launch an owned installed test window')
    parser.add_argument('--seconds', type=int, default=180)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    report, path = run(root, exercise=args.exercise, seconds=args.seconds)
    print(json.dumps({'report': str(path.relative_to(root)), **report}))
    return 0 if report['status'] in {'ready', 'passed'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
