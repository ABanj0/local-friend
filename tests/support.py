import tempfile
import unittest
from pathlib import Path

from local_agent.config import load
from local_agent.safety import Policy


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.config = load()
        self.config["paths"] = {"workspace": str(root / "work"), "state": str(root / "state")}
        self.approvals = []
        self.allow = True

        def approve(action, details):
            self.approvals.append((action, details))
            return self.allow

        self.policy = Policy(self.config, approve)
