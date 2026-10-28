"""Operator-only installed native retry/fallback check; never an API or agent tool."""
import argparse
import hashlib
import json
import os
import queue
import socket
import stat
import sys
import threading
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from local_agent.native_diagnostics import existing_studio, no_links
from local_agent.studio.process_output import ProcessOutput

PORT = 17861


class CheckFailed(Exception):
    """Only fixed reason codes, never raw process output or user input."""


class PortGuard:
    """Reserve loopback exclusively; never accept/read a request or credential."""

    def __init__(self, port=PORT):
        self.socket = socket.socket()
        try:
            if os.name == 'nt':
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            self.socket.bind(('127.0.0.1', port))
            self.socket.listen(16)
        except BaseException:
            self.close()
            raise

    def close(self):
        self.socket.close()


class Attempts:
    def __init__(self):
        self.wall = time.time()
        self.clock = time.monotonic()
        self.rows = []

    def observe(self, children):
        now = time.monotonic() - self.clock
        current = {(pid, born) for pid, born in children}
        for row in self.rows:
            if row['ended'] is None and (row['pid'], row['created']) not in current:
                row['ended'] = round(now, 6)
        for pid, born in children:
            if any((row['pid'], row['created']) == (pid, born) for row in self.rows):
                continue
            if len(self.rows) >= 5:
                raise CheckFailed('unexpected_extra_attempt')
            relative = born - self.wall
            if not 0 <= relative <= now + .5:
                raise CheckFailed('process_clock_changed')
            self.rows.append({'pid': pid, 'created': born, 'began': round(relative, 6), 'ended': None})

    def backoff(self):
        if len(self.rows) != 4 or any(row['ended'] is None for row in self.rows):
            raise CheckFailed('four_failed_attempts_not_observed')
        gaps = [round(right['began'] - left['ended'], 6)
                for left, right in zip(self.rows, self.rows[1:])]
        if any(gap < limit - .15 for gap, limit in zip(gaps, (1, 2, 4))):
            raise CheckFailed('retry_started_too_early')
        return gaps


def binary_hash(path):
    # Windows lstat marks *.exe executable, while fstat may omit those permission bits.
    # Require regular/single-link data on both handles; compare identity/content separately.
    def identity(info):
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 128 * 1024**2:
            raise CheckFailed('unsafe_installed_binary')
        return info.st_dev, info.st_ino, info.st_nlink, info.st_size, info.st_mtime_ns

    before = identity(path.lstat())
    digest = hashlib.sha256()
    total = 0
    with path.open('rb') as stream:
        if identity(os.fstat(stream.fileno())) != before:
            raise CheckFailed('installed_binary_changed')
        while chunk := stream.read(1024**2):
            total += len(chunk)
            if total > 128 * 1024**2:
                raise CheckFailed('unsafe_installed_binary')
            digest.update(chunk)
        if identity(os.fstat(stream.fileno())) != before:
            raise CheckFailed('installed_binary_changed')
    if identity(path.lstat()) != before or total != before[3]:
        raise CheckFailed('installed_binary_changed')
    return {'bytes': total, 'sha256': digest.hexdigest()}


def installed(root):
    directory = Path(os.environ['LOCALAPPDATA']) / 'Local Agent Studio'
    manifest = json.loads((root / 'dist/release-manifest.json').read_text(encoding='utf-8-sig'))
    expected = manifest.get('expected_nsis_main_payload', {})
    if expected.get('status') != 'predicted':
        raise CheckFailed('missing_installed_payload_expectation')
    backend = next((value for name, value in manifest['artifacts'].items()
                    if name.replace('\\', '/') == 'dist/agent-backend.exe'), None)
    if backend is None:
        raise CheckFailed('missing_backend_expectation')
    hashes = {}
    for name, wanted in [('local-agent-studio.exe', expected), ('agent-backend.exe', backend)]:
        path = directory / name
        if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
            raise CheckFailed('linked_installed_binary')
        observed = binary_hash(path)
        if observed != {'bytes': wanted['bytes'], 'sha256': wanted['sha256']}:
            raise CheckFailed('installed_binary_manifest_mismatch')
        hashes[name] = observed['sha256']
    return directory / 'local-agent-studio.exe', hashes


def sample(native, attempts, *, allow_exit=False):
    import psutil
    if native.proc.poll() is not None:
        attempts.observe([])
        if not allow_exit:
            raise CheckFailed('native_exited_before_check_finished')
        return
    try:
        children = psutil.Process(native.proc.pid).children()
    except psutil.NoSuchProcess:
        if not allow_exit:
            raise CheckFailed('native_exited_before_check_finished') from None
        children = []
    identities = []
    for child in children:
        try:
            if child.name() == 'agent-backend.exe':
                identities.append((child.pid, child.create_time()))
        except psutil.NoSuchProcess:
            continue  # A short-lived backend disappearing is not a native-window exit.
    attempts.observe(identities)


def wait_for(predicate, native, attempts, deadline, *, allow_exit=False):
    while time.monotonic() < deadline:
        sample(native, attempts, allow_exit=allow_exit)
        if predicate():
            return
        time.sleep(.025)
    raise CheckFailed('observation_deadline')


def confirm(word, message, native, attempts, deadline, *, allow_exit=False):
    answers = queue.Queue(maxsize=1)

    def read():
        try:
            answers.put(input(message + '\nType ' + word + ' here: ').strip())
        except (EOFError, OSError):
            answers.put(None)

    threading.Thread(target=read, daemon=True).start()
    wait_for(lambda: not answers.empty(), native, attempts, deadline, allow_exit=allow_exit)
    if answers.get() != word:
        raise CheckFailed('owner_confirmation_missing')


def descendants(proc):
    import psutil
    try:
        return [(p.pid, p.create_time()) for p in psutil.Process(proc.pid).children(recursive=True)]
    except psutil.NoSuchProcess:
        return []


def alive(identity):
    import psutil
    try:
        return psutil.Process(identity[0]).create_time() == identity[1]
    except psutil.NoSuchProcess:
        return False


def owned_listener(native):
    import psutil
    owned = {pid for pid, _ in descendants(native.proc)}
    return any(c.status == psutil.CONN_LISTEN and c.laddr.ip == '127.0.0.1'
               and c.laddr.port == PORT and c.pid in owned
               for c in psutil.net_connections(kind='tcp'))


def run(root, *, exercise=False, seconds=240):
    if type(exercise) is not bool or type(seconds) is not int or not 60 <= seconds <= 300:
        raise ValueError('Duration must be an integer from 60 to 300 seconds')
    root = Path(root).resolve()
    no_links(root, root / '.runtime')
    case = root / '.runtime' / ('native-recovery-' + uuid.uuid4().hex)
    case.mkdir(parents=True)
    report = {'version': 1, 'scope': 'installed_native_retry_fallback', 'status': 'blocked',
              'native_acceptance': 'not_verified', 'reason': None, 'exercise_requested': exercise,
              'owner_observations': [], 'attempts': [], 'owned_cleanup': False,
              'raw_output_exported': False, 'webview_profile_retained': True}
    native, sentinel, guard = ProcessOutput(), ProcessOutput(), None
    attempts = Attempts()
    try:
        if existing_studio():
            raise CheckFailed('existing_studio_preserved')
        executable, hashes = installed(root)
        report['installed_sha256'] = hashes
        guard = PortGuard()
        if not exercise:
            report['status'] = 'ready'
        else:
            deadline = time.monotonic() + seconds
            env = dict(os.environ)
            env.pop('LOCAL_AGENT_STUDIO_TOKEN', None)
            env.pop('WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS', None)
            env['WEBVIEW2_USER_DATA_FOLDER'] = str(case / 'webview')
            # Independent of the native job; verifies Python preservation on normal close.
            sentinel.start([sys.executable, '-c', 'import time; time.sleep(360)'], env)
            if any(binary_hash(executable.with_name(name))['sha256'] != digest
                   for name, digest in hashes.items()):
                raise CheckFailed('installed_binary_changed')
            native.start([str(executable)], env)
            print('Observing real native startup failures; no task is submitted.', flush=True)
            wait_for(lambda: len(attempts.rows) == 4 and all(r['ended'] is not None for r in attempts.rows),
                     native, attempts, deadline)
            report['retry_gap_lower_bounds_seconds'] = attempts.backoff()
            quiet = time.monotonic() + 6
            wait_for(lambda: time.monotonic() >= quiet, native, attempts, deadline)
            if len(attempts.rows) != 4:
                raise CheckFailed('retry_budget_not_exhausted')
            confirm('FALLBACK', 'Check Studio shows Port 17861 is occupied and Restart backend.',
                    native, attempts, deadline)
            if len(attempts.rows) != 4:
                raise CheckFailed('retry_budget_not_exhausted')
            report['owner_observations'].append('port_collision_diagnostics_and_manual_fallback')
            guard.close()
            guard = None
            confirm('CONNECTED', 'Now click Restart backend in Studio. Wait for Connected locally.',
                    native, attempts, deadline)
            if len(attempts.rows) != 5 or attempts.rows[-1]['ended'] is not None or not owned_listener(native):
                raise CheckFailed('manual_restart_not_observed')
            report['owner_observations'].append('manual_restart_connected')
            owned = descendants(native.proc)
            confirm('CLOSED', 'Close this test Studio using X. Do not submit tasks.', native, attempts,
                    deadline, allow_exit=True)
            wait_for(lambda: native.proc.poll() is not None and not any(alive(p) for p in owned),
                     native, attempts, deadline, allow_exit=True)
            if sentinel.proc.poll() is not None:
                raise CheckFailed('independent_python_exited')
            report['normal_close_owned_descendants_exited_before_fixture_cleanup'] = True
            report['independent_python_preserved'] = True
            report['status'] = 'passed'
            report['native_acceptance'] = 'retry_fallback_and_normal_close_only'
    except CheckFailed as exc:
        report['reason'] = str(exc)
    except Exception:  # noqa: BLE001 -- no raw exception/paths/logs/credentials in report
        report['reason'] = 'check_failed'
    finally:
        cleanup_ok = True
        try:
            if guard:
                guard.close()
        except Exception:  # noqa: BLE001 -- still close both owned jobs
            cleanup_ok = False
        for owner in (native, sentinel):
            try:
                owner.close()
            except Exception:  # noqa: BLE001 -- attempt all owned cleanup independently
                cleanup_ok = False
        report['owned_cleanup'] = cleanup_ok and all(owner.proc is None or owner.proc.poll() is not None
                                                    for owner in (native, sentinel))
        if not report['owned_cleanup']:
            report['status'], report['reason'] = 'blocked', 'owned_cleanup_failed'
            report['native_acceptance'] = 'not_verified'
    report['attempts'] = [{key: row[key] for key in ('pid', 'began', 'ended')} for row in attempts.rows]
    data = json.dumps(report, indent=2)
    if len(data.encode()) > 16384:
        raise ValueError('Report exceeds fixed budget')
    path = case / 'report.json'
    no_links(root, path)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(data + '\n')
    return report, path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exercise', action='store_true', help='Launch an owned installed test window')
    parser.add_argument('--seconds', type=int, default=240)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    report, path = run(root, exercise=args.exercise, seconds=args.seconds)
    print(json.dumps({'report': str(path.relative_to(root)), **report}))
    return 0 if report['status'] in {'ready', 'passed'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
