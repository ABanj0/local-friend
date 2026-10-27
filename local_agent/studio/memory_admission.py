"""Host-owned semantic recall preflight; snapshots never confer tool permissions."""
import hashlib
import json
from dataclasses import dataclass

from local_agent.safety import Denied
from local_agent.studio.memory_sources import UNSET

MODES = frozenset({'chat', 'plan', 'agent', 'coding', 'browser', 'desktop'})


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, sort_keys=True).encode()).hexdigest()


def history_version(manager, conversation):
    rows = manager.store.messages(conversation, for_model=True)
    latest = manager.store.latest_task(conversation)
    with manager.store.connection() as db:
        chat = db.execute('SELECT memory_scope,memory_epoch FROM conversations WHERE id=?', (conversation,)).fetchone()
    if chat is None:
        raise KeyError('Conversation not found')
    version = digest({'messages': [(r['id'], r['role'], r['content']) for r in rows],
                      'memory': tuple(chat), 'latest': {k: latest[k] for k in ('id', 'mode', 'profile')} if latest else None})
    return version, rows, latest


@dataclass(frozen=True)
class PreparedRecall:
    owner: object
    conversation: str
    objective: str
    history: str
    snapshot: dict
    generation: str
    ids: tuple


def prepare(manager, conversation, project, objective, mode, regenerate=False, *, sources=UNSET):
    if mode not in MODES:
        return None
    index = manager.memory_index
    if sources is UNSET:
        sources = manager.memory_sources.prepare(project)
    with manager.lock, manager.store.connection() as db:
        # Existing keyword users do not perform metadata admission or inference.
        if not db.execute("SELECT 1 FROM metadata WHERE key GLOB 'semantic_memory:*' LIMIT 1").fetchone():
            return None
        scope = manager.memory.scope(project)
        if not index.enabled(db, scope):
            return None
        index.guard()
        manager.memory.bind(db, conversation, scope)
        version, history, latest = history_version(manager, conversation)
        if regenerate:
            if latest and latest['mode'] not in MODES:
                return None  # Manager retains its dedicated shortcut-regeneration refusal.
            original = next((r for r in reversed(history) if r['role'] == 'user'), None)
            if original is None:
                raise ValueError('No user message to regenerate')
            objective = original['content']
        if type(objective) is not str or not objective.strip():
            raise ValueError('Enter a message')
    with index.operation():
        rows, saved, published = index._search(project, objective[:500],
            forbidden=getattr(index, 'forbidden', ()), with_snapshot=True, sources=sources)
        with manager.lock, manager.store.connection() as db:
            if not index.enabled(db, saved['scope']) or history_version(manager, conversation)[0] != version:
                raise Denied('Conversation or memory selection changed during recall; review and retry')
            manager.memory.bind(db, conversation, saved['scope'])
        return PreparedRecall(index, conversation, digest(objective), version, saved,
                              published['generation'], tuple(row['id'] for row in rows))


def validate(manager, prepared, conversation, project, objective):
    """Called under admission lock, before creating a task or saving its new message."""
    if not isinstance(prepared, PreparedRecall) or prepared.owner is not manager.memory_index:
        raise Denied('A current host-owned memory preflight is required')
    if (prepared.conversation != conversation or prepared.objective != digest(objective)
            or history_version(manager, conversation)[0] != prepared.history):
        raise Denied('Conversation changed during recall; review and retry')
    with manager.store.connection() as db:
        current = manager.memory_index.unchanged(db, project, prepared.snapshot)
        index = manager.memory_index.index(db, current['scope'])
        if index['generation'] != prepared.generation or not manager.memory_index.enabled(db, current['scope']):
            raise Denied('Memory selection changed during recall; review and retry')
        by_id = {row['id']: row for row in current['rows']}
        if len(prepared.ids) > 5 or len(set(prepared.ids)) != len(prepared.ids) or any(i not in by_id for i in prepared.ids):
            raise Denied('Memory preflight contains invalid source references')
        return [by_id[i] for i in prepared.ids]
