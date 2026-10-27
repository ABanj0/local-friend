"""Versioned continuations for selected-file, read-only agent inspections only."""
import copy
import hashlib
import json
import time
from dataclasses import asdict

from local_agent.agent import EMPTY_PROMPT, EXECUTE_PROMPT, SYSTEM, clean
from local_agent.coding import Coding
from local_agent.inference import InferenceOptions
from local_agent.model import Ollama
from local_agent.observability import hex_id
from local_agent.review import fingerprint
from local_agent.safety import Denied, Policy
from local_agent.studio.journal import digest, label, scope_key
from local_agent.tools import Tools

VERSION = 1
MAX_BYTES = 1024**2
MAX_ATTEMPTS = 3


class Paused(Exception):
    """Raised only after the supervisor commits a completed boundary and requests exit."""


def require(condition):
    if not condition:
        raise ValueError('Unsupported inspection checkpoint; start a fresh inspection')


def encode(value):
    try:
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
        require(len(value.encode()) <= MAX_BYTES)
        return value
    except (TypeError, OverflowError, RecursionError):
        raise ValueError('Inspection checkpoint exceeds its supported format or size') from None


def paths(value):
    require(isinstance(value, list) and 1 <= len(value) <= 8)
    require(all(isinstance(path, str) and label(path) == path for path in value))
    require(len({path.casefold() for path in value}) == len(value))
    return value


def prompt(spec):
    return (spec['objective'] + '\n\nRead-only inspection: only these explicitly selected project files may be read: '
            + json.dumps([item['path'] for item in spec['files']], ensure_ascii=False)
            + '. Do not change files or run commands. Report observations and limitations.')


def runtime(policy):
    return digest([VERSION, SYSTEM, EXECUTE_PROMPT, EMPTY_PROMPT,
                   Tools(policy, profile='coding', allowed_tools={'read_file'}).schemas])


def observe(policy, names):
    result, contents = [], {}
    for path in paths(names):
        policy.check_stop()
        policy.no_links(policy.root / path)
        target = policy.path(path)
        require(not target.is_relative_to(policy.state))
        before = fingerprint(target, 64000)
        require(before is not None)
        data = clean(Coding(policy).read(path))
        require(before == fingerprint(target, 64000))
        result.append({'path': path, 'sha256': before[-1], 'resource_version': digest(before[1:-1])})
        contents[path] = data
    return result, contents


def observe_worker(policy, spec):
    if scope_key(policy.root) != spec['scope']:
        raise Denied('Inspection project scope changed; start a fresh inspection')
    return observe(policy, [item['path'] for item in spec['files']])


def validate_spec(spec):
    require(isinstance(spec, dict) and set(spec) == {'version', 'runtime', 'store', 'scope', 'project',
        'epoch', 'objective', 'files', 'model', 'identity', 'options', 'max_steps', 'attempt', 'prior_reads'})
    require(type(spec['version']) is int and spec['version'] == VERSION)
    require(all(hex_id(spec[key], size) for key, size in [('runtime', 64), ('store', 32), ('scope', 64)]))
    require(isinstance(spec['project'], str) and label(spec['project'], project=True) == spec['project'])
    require(type(spec['epoch']) is int and spec['epoch'] >= 0)
    require(isinstance(spec['objective'], str) and 0 < len(spec['objective'].strip()) <= 12000
            and clean(spec['objective']) == spec['objective'])
    require(isinstance(spec['files'], list) and 1 <= len(spec['files']) <= 8)
    for item in spec['files']:
        require(isinstance(item, dict) and set(item) == {'path', 'sha256', 'resource_version'})
        require(hex_id(item['sha256'], 64) and hex_id(item['resource_version'], 64))
    paths([item['path'] for item in spec['files']])
    require(isinstance(spec['model'], str) and 0 < len(spec['model']) <= 200)
    identity = spec['identity']
    require(isinstance(identity, dict) and set(identity) == {'digest', 'server_version'})
    require(hex_id(identity['digest'], 64) and isinstance(identity['server_version'], str)
            and 0 < len(identity['server_version']) <= 100)
    require(isinstance(spec['options'], dict) and set(spec['options']) == set(InferenceOptions.__dataclass_fields__))
    InferenceOptions.from_config(spec['options'])
    require(type(spec['max_steps']) is int and 1 <= spec['max_steps'] <= 128)
    require(type(spec['attempt']) is int and 1 <= spec['attempt'] <= MAX_ATTEMPTS)
    require(type(spec['prior_reads']) is int and 0 <= spec['prior_reads'] <= 256)
    return spec


def validate_agent(value, spec, contents=None):
    """Only a fixed prompt and completed read_file call/result groups can be restored."""
    require(isinstance(value, dict) and set(value) == {
        'version', 'messages', 'evidence', 'failures', 'empty_responses', 'next_step'})
    require(type(value['version']) is int and value['version'] == VERSION)
    require(type(value['next_step']) is int and 1 <= value['next_step'] <= spec['max_steps'])
    require(type(value['failures']) is int and value['failures'] == 0
            and type(value['empty_responses']) is int and value['empty_responses'] == 0)
    messages = value['messages']
    require(isinstance(messages, list) and 6 <= len(messages) <= 1200)
    require(messages[:2] == [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': prompt(spec)}])
    require(isinstance(messages[2], dict) and set(messages[2]) == {'role', 'content'}
            and messages[2]['role'] == 'assistant' and isinstance(messages[2]['content'], str))
    try:
        plan = json.loads(messages[2]['content'])
        require(isinstance(plan, dict) and set(plan) == {'steps'} and isinstance(plan['steps'], list)
                and 1 <= len(plan['steps']) <= 30
                and all(isinstance(step, str) and 0 < len(step) <= 2000 for step in plan['steps']))
    except (ValueError, TypeError, RecursionError):
        raise ValueError('Unsupported inspection plan') from None
    require(messages[3] == {'role': 'user', 'content': EXECUTE_PROMPT})
    files = {item['path']: item for item in spec['files']}
    evidence, index, steps = [], 4, 0
    while index < len(messages):
        step = messages[index]
        steps += 1
        if step == {'role': 'user', 'content': EMPTY_PROMPT}:
            index += 1
            continue
        require(isinstance(step, dict) and set(step) == {'role', 'tool_calls'} and step['role'] == 'assistant')
        calls = step['tool_calls']
        require(isinstance(calls, list) and 1 <= len(calls) <= 8)
        index += 1
        for call in calls:
            require(isinstance(call, dict) and set(call) == {'function'})
            function = call['function']
            require(isinstance(function, dict) and set(function) == {'name', 'arguments'} and function['name'] == 'read_file')
            arguments = function['arguments']
            require(isinstance(arguments, dict) and set(arguments) == {'path'}
                    and isinstance(arguments['path'], str) and arguments['path'] in files)
            require(index < len(messages))
            message = messages[index]
            require(isinstance(message, dict) and set(message) == {'role', 'tool_name', 'content'}
                    and message['role'] == 'tool' and message['tool_name'] == 'read_file' and isinstance(message['content'], str))
            try:
                result = json.loads(message['content'])
                require(isinstance(result, dict) and set(result) == {'ok', 'untrusted_data'} and result['ok'] is True)
                data = result['untrusted_data']
                require(isinstance(data, dict) and set(data) == {'path', 'text', 'sha256'}
                        and data['path'] == arguments['path'] and data['sha256'] == files[arguments['path']]['sha256']
                        and isinstance(data['text'], str) and len(data['text'].encode()) <= 64000 and clean(data['text']) == data['text'])
                if contents is not None:
                    require(data == contents[arguments['path']])
            except (ValueError, TypeError, RecursionError):
                raise ValueError('Unsupported inspection observation') from None
            evidence.append({'tool': 'read_file', 'ok': True, 'exit_code': None})
            index += 1
    require(steps == value['next_step'] and evidence and evidence == value['evidence'])
    encode(value)
    return value


def load(db, task):
    row = db.execute('SELECT state,CASE WHEN length(cast(payload AS BLOB))<=? THEN payload END AS payload,'
                     'sha256,source_task,resumed_by FROM inspection_checkpoints WHERE task=?', (MAX_BYTES, task)).fetchone()
    if row is None:
        raise ValueError('This task has no supported inspection checkpoint')
    require(row['state'] in {'initial', 'ready', 'paused', 'consumed', 'closed'})
    require(isinstance(row['payload'], str) and hashlib.sha256(row['payload'].encode()).hexdigest() == row['sha256'])
    try:
        data = json.loads(row['payload'])
        require(isinstance(data, dict) and set(data) == {'spec', 'agent'})
        validate_spec(data['spec'])
        if data['agent'] is not None:
            validate_agent(data['agent'], data['spec'])
        else:
            require(row['state'] in {'initial', 'closed'})
    except (TypeError, KeyError, RecursionError):
        raise ValueError('Unsupported inspection checkpoint') from None
    return {**dict(row), 'data': data}


def guard(manager):
    Policy(manager.config, create=False).check_stop()
    if manager.running or manager.shutdown_requested.is_set() or manager.restore_pending.is_set():
        raise ValueError('Finish owned tasks and pending restart before starting or resuming an inspection')


def current(manager, spec):
    validate_spec(spec)
    base = Policy(manager.config, create=False)
    base.no_links(base.root / spec['project'])
    root = base.path(spec['project'])
    config = copy.deepcopy(manager.config)
    config['paths']['workspace'] = str(root)
    policy = Policy(config, create=False)
    if spec['store'] != manager.store.identity or spec['scope'] != scope_key(root):
        raise Denied('Inspection project or saved history changed; reconcile inputs and start a fresh inspection')
    if spec['runtime'] != runtime(policy) or spec['max_steps'] != manager.config['model']['max_steps']:
        raise Denied('Inspection version or execution limits changed; start a fresh inspection')
    observed, contents = observe(policy, [item['path'] for item in spec['files']])
    if observed != spec['files']:
        raise Denied('Inspection inputs changed; reconcile the current files and start a fresh inspection')
    return config, contents


def start(manager, conversation, objective, model, project, files, settings, *, queue_claim=None,
          preflight=None, admission_check=None):
    with manager.lock:
        guard(manager)
        require(preflight is None or queue_claim is not None)
        if admission_check:
            admission_check()
        admission = manager.admission_epoch
        require(label(project, project=True) == project)
        base = Policy(manager.config, create=False)
        base.no_links(base.root / project)
        root = base.path(project)
        config = copy.deepcopy(manager.config)
        config['paths']['workspace'] = str(root)
        config['model'].update({**settings, 'name': model})
        policy = Policy(config, create=False)
        observed, _ = observe(policy, files)
        with manager.store.connection() as db:
            manager.memory.bind(db, conversation, scope_key(root))
            row = db.execute('SELECT memory_epoch FROM conversations WHERE id=?', (conversation,)).fetchone()
            if row is None:
                raise KeyError('Conversation not found')
        spec = {'version': VERSION, 'runtime': runtime(policy), 'store': manager.store.identity,
                'scope': scope_key(root), 'project': project, 'epoch': row[0], 'objective': clean(objective),
                'files': observed, 'model': model, 'options': asdict(InferenceOptions.from_config(config['model'])),
                'max_steps': config['model']['max_steps'], 'attempt': 1, 'prior_reads': 0}
    identity = preflight if preflight is not None else Ollama(config['model']).admit(tools=True)
    spec['identity'] = {key: identity[key] for key in ('digest', 'server_version')}
    validate_spec(spec)
    with manager.lock:
        guard(manager)
        require(admission == manager.admission_epoch)
        if admission_check:
            admission_check()
        current(manager, spec)
        return manager.start(conversation, prompt(spec), 'inspection', model, project, spec['options'],
                             profile='coding', inspection={'spec': spec, 'agent': None}, queue_claim=queue_claim)


def resume(manager, task):
    with manager.lock, manager.store.connection() as db:
        guard(manager)
        admission = manager.admission_epoch
        saved = load(db, task)
        row = db.execute('SELECT conversation,status,mode FROM tasks WHERE id=?', (task,)).fetchone()
        require(row['mode'] == 'inspection' and row['status'] in {'interrupted', 'failed'}
                and saved['state'] in {'ready', 'paused'} and saved['resumed_by'] is None and saved['data']['agent'] is not None)
        data = copy.deepcopy(saved['data'])
        spec = data['spec']
        require(spec['attempt'] < MAX_ATTEMPTS and data['agent']['next_step'] < spec['max_steps'])
        config, contents = current(manager, spec)
        epoch = db.execute('SELECT memory_epoch FROM conversations WHERE id=?', (row['conversation'],)).fetchone()[0]
        if epoch != spec['epoch']:
            raise Denied('Inspection memory context changed; start a fresh inspection')
        validate_agent(data['agent'], spec, contents)
        if db.execute("SELECT 1 FROM operations WHERE task=? AND (tool<>'read_file' OR effect<>'read') LIMIT 1", (task,)).fetchone():
            raise Denied('Unsupported tool history cannot resume; reconcile outcomes and start a fresh task')
        config['model'].update({**spec['options'], 'name': spec['model']})
        conversation = row['conversation']
    identity = Ollama(config['model']).admit(tools=True)
    if spec['identity'] != {key: identity[key] for key in ('digest', 'server_version')}:
        raise Denied('Inspection model identity changed; start a fresh inspection')
    with manager.lock:
        guard(manager)
        require(admission == manager.admission_epoch)
        current(manager, spec)
        spec['attempt'] += 1
        spec['prior_reads'] = len(data['agent']['evidence'])
        return manager.start(conversation, prompt(spec), 'inspection', spec['model'], spec['project'], spec['options'],
            profile='coding', inspection=data, resume_from=(task, saved['sha256']))


def save(db, task, agent, *, paused=False):
    previous = load(db, task)
    require(previous['state'] in {'initial', 'ready'} and previous['resumed_by'] is None)
    data = previous['data']
    validate_agent(agent, data['spec'])
    require(data['agent'] is None or agent['next_step'] > data['agent']['next_step'])
    row = db.execute('SELECT status,mode FROM tasks WHERE id=?', (task,)).fetchone()
    require(row['status'] == 'running' and row['mode'] == 'inspection')
    step = db.execute('SELECT ordinal,state FROM execution_steps WHERE task=? ORDER BY ordinal DESC LIMIT 1', (task,)).fetchone()
    require(step is not None and step['ordinal'] == agent['next_step'] and step['state'] == 'completed')
    require(not db.execute("SELECT 1 FROM operations WHERE task=? AND (state<>'completed' OR tool<>'read_file' "
                           "OR effect<>'read' OR outcome<>'observed') LIMIT 1", (task,)).fetchone())
    calls = [call['function']['arguments'] for message in agent['messages']
             for call in message.get('tool_calls', [])][data['spec']['prior_reads']:]
    operations = db.execute('SELECT arguments_sha256 FROM operations WHERE task=? ORDER BY ordinal', (task,)).fetchall()
    require([row[0] for row in operations] == [digest(arguments) for arguments in calls])
    data['agent'] = agent
    payload = encode(data)
    db.execute('UPDATE inspection_checkpoints SET state=?,payload=?,sha256=?,updated=? WHERE task=?',
               ('paused' if paused else 'ready', payload, hashlib.sha256(payload.encode()).hexdigest(), time.time(), task))
    return {'version': VERSION, 'completed_step': agent['next_step'], 'pause_acknowledged': paused}


def summary(manager, task):
    with manager.lock, manager.store.connection() as db:
        metadata = db.execute('SELECT mode,status FROM tasks WHERE id=?', (task,)).fetchone()
        if metadata is None:
            raise KeyError('Task not found')
        if metadata['mode'] != 'inspection':
            return {'supported': False}
        try:
            record = load(db, task)
        except (ValueError, TypeError):
            return {'supported': True, 'state': 'invalid', 'can_pause': False, 'can_resume': False}
        agent, spec = record['data']['agent'], record['data']['spec']
        slot = manager.running.get(task)
        active = bool(slot and not slot['done'])
        visible_state = 'pausing' if record['state'] == 'paused' and slot else record['state']
        return {'supported': True, 'state': visible_state, 'version': VERSION,
                'completed_step': agent['next_step'] if agent else 0, 'attempt': spec['attempt'],
                'files': [item['path'] for item in spec['files']], 'source_task': record['source_task'],
                'project': spec['project'],
                'resumed_by': record['resumed_by'], 'pause_requested': bool(slot and slot.get('pause_requested')),
                'can_pause': bool(active and agent and record['state'] == 'ready' and not slot.get('pause_requested')),
                'can_resume': bool(not manager.running and metadata['status'] in {'failed', 'interrupted'}
                    and record['state'] in {'ready', 'paused'} and agent and agent['next_step'] < spec['max_steps']
                    and spec['attempt'] < MAX_ATTEMPTS)}


def pause(manager, task):
    with manager.lock:
        if not summary(manager, task).get('can_pause'):
            raise ValueError('Pause is available only after a completed inspection checkpoint')
        manager.running[task]['pause_requested'] = True
        manager.emit(task, 'progress', {'text': 'Pause requested. Waiting for the next completed read-only step boundary.'})
        return {'requested': True, 'paused': False}
