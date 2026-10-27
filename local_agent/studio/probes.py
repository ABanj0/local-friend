"""Fixed local metadata/observation children, bounded bytes, cancellation and ownership."""
import json
import math
import multiprocessing
import os
import queue
import threading
import time
from contextlib import ExitStack

from local_agent.model import Ollama
from local_agent.safety import Policy, Stopped
from local_agent.studio.directory_snapshot import observe
from local_agent.studio.manager import _discard_startup_process

MAX_REPLY = 65536


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate local probe field')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError('Nonfinite local probe value')


def child_main(pipe, kind, payload):
    try:
        if pipe.recv_bytes(16) != b'probe':
            return
        if kind == 'model':
            data = Ollama(payload).admit(tools=True)
            result = {key: data[key] for key in ('digest', 'server_version')}
        elif kind == 'directory' and set(payload) == {'config', 'path'}:
            data = observe(Policy(payload['config'], create=False), payload['path'])
            result = {key: data[key] for key in ('scope', 'fingerprint', 'complete', 'stop_reason', 'counts')}
        else:
            result = None
        body = json.dumps(result, ensure_ascii=True, allow_nan=False).encode()
        if len(body) > MAX_REPLY:
            raise ValueError('Local probe reply exceeds its limit')
        pipe.send_bytes(body)
    except (Exception, Stopped):  # noqa: BLE001 -- do not expose file contents or peer exception strings
        try:
            pipe.send_bytes(b'null')
        except (OSError, EOFError):
            pass
    finally:
        pipe.close()


def run(kind, payload, cancelled, *, timeout=8):
    if (kind not in {'model', 'directory'} or not isinstance(payload, dict)
            or type(timeout) not in {int, float} or not math.isfinite(timeout) or not 0 < timeout <= 8):
        raise ValueError('Unsupported local probe request')
    if cancelled.is_set():
        raise ValueError('Local observation was cancelled')
    context = multiprocessing.get_context('spawn')
    with ExitStack() as cleanup:
        parent, child = context.Pipe()
        cleanup.callback(parent.close)
        cleanup.callback(child.close)
        response = queue.Queue(maxsize=1)

        def receive():
            try:
                body = parent.recv_bytes(MAX_REPLY)
            except (OSError, EOFError, TypeError, ValueError):
                body = None
            response.put(body)

        reader = threading.Thread(target=receive, name='local-probe-reply', daemon=True)

        def close_reader():
            parent.close()
            if reader.ident is not None:
                reader.join(1)
                if reader.is_alive():
                    raise OSError('Local probe reader cleanup is incomplete')

        cleanup.callback(close_reader)  # Process/Job callbacks run before the reader is joined.
        process = context.Process(target=child_main, args=(child, kind, payload))
        cleanup.callback(_discard_startup_process, process)
        try:
            process.start()
            child.close()
            if os.name == 'nt':
                from local_agent.windows_job import WindowsJob

                class Handle:
                    _handle = process.sentinel

                job = WindowsJob(Handle())
                cleanup.callback(job.close)
            if cancelled.is_set():
                raise ValueError('Local observation was cancelled')
            reader.start()
            parent.send_bytes(b'probe')  # No file/network observation before ownership is established.
            deadline = time.monotonic() + timeout
            while not cancelled.is_set() and time.monotonic() < deadline:
                try:
                    body = response.get(timeout=.03)
                except queue.Empty:
                    continue
                if body is None:
                    break
                result = json.loads(body, object_pairs_hook=unique_object, parse_constant=invalid_constant)
                if not isinstance(result, dict):
                    break
                return result
        except (EOFError, OSError, ValueError, RecursionError):
            pass
    raise ValueError('Owned local observation unavailable, cancelled or timed out')
