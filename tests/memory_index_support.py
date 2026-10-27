"""Non-discoverable saved-note/index protocol fixture; never quality evidence."""
import copy
from unittest.mock import patch

from local_agent.studio.manager import Manager


class EmbeddingProtocol:
    def __init__(self, owner):
        self.owner = owner

    def identity(self):
        self.owner.calls.append('identity')
        return copy.deepcopy(self.owner.ident)

    def embed(self, texts, *, query=False):
        self.owner.calls.append(('embed', list(texts), query))
        if self.owner.on_embed:
            self.owner.on_embed(texts, query)
        return copy.deepcopy(self.owner.ident), [[1., 0.] for _ in texts]


class MemoryIndexFixture:
    def setUp(self):
        super().setUp()
        self.manager = Manager(self.config)
        self.addCleanup(self.manager.close)
        self.index = self.manager.memory_index
        self.chat = self.manager.store.conversation()
        self.note = self.manager.memory.remember('.', self.chat, 'Atlas compiler requires lavender flags.')
        (self.policy.root / 'other').mkdir()
        self.ident = {'model': 'fixture', 'digest': 'a' * 64, 'server_version': '0.40.7',
                      'dimensions': 2, 'query_format': 'project-note-instruct-v1'}
        self.calls = []
        self.on_embed = None
        self.protocol = EmbeddingProtocol(self)
        self.client_patch = patch('local_agent.studio.memory_index.Embeddings', return_value=self.protocol)
        self.client_patch.start()
        self.addCleanup(self.client_patch.stop)

    def build(self):
        return self.index.reindex('.', 'fixture', confirmed=True)

    def counts(self):
        with self.manager.store.connection() as db:
            return tuple(db.execute(f'SELECT count(*) FROM {t}').fetchone()[0]
                         for t in ('memory_indexes', 'memory_vectors'))
