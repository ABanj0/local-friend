import inspect
import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from local_agent.coding import Coding
from local_agent.studio.store import Store
from local_agent.tool_spec import PROFILES
from local_agent.tools import Tools

from .ollama_fixture import metadata_response
from .studio_support import StudioAPIFixture, StudioProcessFixture
from .support import WorkspaceTest


class ToolSpecTests(WorkspaceTest):
    def test_versioned_schema_and_defaults_match_all_existing_adapters(self):
        tools = Tools(self.policy)
        self.addCleanup(tools.close)
        self.assertEqual(len(tools.registry), 22)
        self.assertEqual({spec.category for spec in tools.registry.values()}, {"coding", "browser", "desktop"})
        for name, spec in tools.registry.items():
            self.assertEqual(spec.name, name)
            self.assertEqual(spec.version, 1)
            schema = spec.schema()["function"]["parameters"]
            self.assertFalse(schema["additionalProperties"])
            values = {}
            for argument in spec.arguments:
                if argument.required:
                    values[argument.name] = ([{field.name: "fixture" for field in argument.item_fields}]
                        if argument.item_fields else argument.choices[0] if argument.choices else "fixture")
                else:
                    self.assertEqual(argument.default,
                                     inspect.signature(spec.handler).parameters[argument.name].default)
                    self.assertNotIn("default", schema["properties"][argument.name])
            self.assertEqual(dict(spec.validate(values)), dict(spec.signature.bind(**values).arguments) |
                             {a.name: a.default for a in spec.arguments if not a.required})
        json.dumps(tools.schemas)

    def test_registry_and_profiles_are_immutable_and_schemas_are_independent(self):
        tools = Tools(self.policy)
        with self.assertRaises(TypeError):
            tools.registry["shell"] = tools.registry["command"]
        with self.assertRaises(FrozenInstanceError):
            tools.registry["files"].version = 2
        with self.assertRaises(TypeError):
            PROFILES["browser"] = frozenset({"coding"})
        schemas = tools.schemas
        schemas[0]["function"]["name"] = "shell"
        self.assertEqual(tools.schemas[0]["function"]["name"], "files")

    def test_malformed_arguments_and_disallowed_category_never_invoke_adapter(self):
        called = []

        def write(coding, path, text):
            called.append((path, text))
            return {}

        with patch.object(Coding, "write", write):
            tools = Tools(self.policy)
            for arguments in (None, [], {"path": "x"}, {"path": 2, "text": "x"},
                              {"path": "x", "text": "x", "profile": "unified"}):
                self.assertEqual(tools.execute("write_file", arguments)["error"], "TypeError")
            narrowed = Tools(self.policy, profile="browser")
            self.assertEqual(narrowed.execute("write_file", {"path": "x", "text": "x"})["error"], "Denied")
        self.assertFalse(called)
        self.assertFalse(self.approvals)

    def test_command_enum_is_checked_before_adapter_including_empty_profiles(self):
        called = []

        def command(coding, name, cwd="."):
            called.append(name)
            return {}

        with patch.object(Coding, "command", command):
            tools = Tools(self.policy)
            self.assertEqual(tools.execute("command", {"name": "arbitrary shell"})["error"], "Denied")
            self.config["commands"] = {}
            tools = Tools(self.policy)
            self.assertEqual(tools.registry["command"].schema()["function"]["parameters"]["properties"]["name"]["enum"], [])
            self.assertEqual(tools.execute("command", {"name": "test"})["error"], "Denied")
        self.assertFalse(called)

    def test_integer_arguments_reject_bools_and_strings(self):
        tools = Tools(self.policy)
        for value in (True, "1", 1.5, None):
            result = tools.execute("desktop_input", {"app": "notepad", "action": "click", "x": value})
            self.assertEqual(result["error"], "TypeError", result)
        self.assertFalse(self.approvals)

    def test_profiles_filter_schema_and_trusted_allowlist_only_narrows(self):
        for profile, permitted in PROFILES.items():
            tools = Tools(self.policy, profile=profile)
            names = {schema["function"]["name"] for schema in tools.schemas}
            self.assertEqual(names, {name for name, spec in tools.registry.items() if spec.category in permitted})
        tools = Tools(self.policy, profile="coding", allowed_tools=(name for name in ("files", "browser_open")))
        self.assertEqual([schema["function"]["name"] for schema in tools.schemas], ["files"])
        self.assertEqual(tools.execute("browser_open", {"url": "https://example.com"})["error"], "Denied")
        for invalid in ("root", None, []):
            with self.assertRaises(ValueError):
                Tools(self.policy, profile=invalid)

    def test_malformed_tool_names_are_normalized(self):
        tools = Tools(self.policy)
        for name in ({}, [], 2, None, "shell"):
            self.assertEqual(tools.execute(name, {})["error"], "Denied")


class ProfileProcessTests(StudioProcessFixture, WorkspaceTest):
    def test_cli_supervisor_propagates_selected_profile(self):
        config = Path(self.temp.name) / "cli.toml"
        source = Path("agent.toml").read_text(encoding="utf-8")
        source = source.replace('workspace = "workspace"', 'workspace = "work"')
        source = source.replace('state = ".runtime/state"', 'state = "state"')
        source = source.replace("http://127.0.0.1:11434", self.config["model"]["url"])
        source = source.replace(f'name = "{self.config["model"]["name"]}"', 'name = "fixture"')
        config.write_text(source, encoding="utf-8")
        result = subprocess.run([sys.executable, "-m", "local_agent", "--config", str(config),
                                 "run", "Write the file", "--profile", "browser"],
                                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("outside the selected capability profile", result.stdout)
        self.assertNotIn("Approval required", result.stdout)
        self.assertFalse((self.policy.root / "review.txt").exists())

    def test_browser_profile_denies_coding_and_regeneration_cannot_widen_it(self):
        for regenerate in (False, True):
            task = self.manager.start(self.conversation, "Write a file", "agent", "fixture",
                                      profile="unified" if regenerate else "browser", regenerate=regenerate)
            self.wait_until(lambda: not self.manager.running)
            row = next(row for row in self.manager.tasks() if row["id"] == task)
            self.assertEqual(row["profile"], "browser")
            self.assertEqual(row["status"], "blocked")
            self.assertFalse(self.manager.pending())
            self.assertFalse((self.policy.root / "review.txt").exists())
        tool_requests = [request for request in self.requests if request.get("tools")]
        self.assertTrue(tool_requests)
        self.assertTrue(all(tool["function"]["name"].startswith("browser_")
                            for request in tool_requests for tool in request["tools"]))
        reopened = Store(self.manager.store.path)
        self.assertTrue(all(task["profile"] == "browser" for task in reopened.tasks()))

    def test_coding_profile_preserves_real_approval_and_dispatch(self):
        task = self.manager.start(self.conversation, "Write a file", "agent", "fixture", profile="coding")
        self.wait_until(lambda: bool(self.manager.pending()))
        approval = self.manager.pending()[0]
        self.manager.approve(task, approval["id"], True)
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual(self.manager.tasks()[0]["profile"], "coding")
        self.assertEqual(self.manager.tasks()[0]["status"], "reported")
        self.assertEqual((self.policy.root / "review.txt").read_text(), "reviewed")

    def test_invalid_profile_and_non_coding_shortcut_fail_before_task_creation(self):
        for mode, profile in (("agent", "invalid"), ("test", "browser"), ("diff", "desktop")):
            with self.assertRaises(ValueError):
                self.manager.start(self.conversation, "Do a task", mode, "fixture", profile=profile)
        self.assertFalse(self.manager.store.tasks())
        self.assertFalse(self.manager.running)


class ProfileAPITests(StudioAPIFixture, WorkspaceTest):
    def test_profiles_require_authentication_and_valid_choice(self):
        conversation = self.client.post("/conversations", headers=self.headers, json={}).json()["id"]
        body = {"conversation": conversation, "objective": "Inspect", "mode": "agent", "model": "fixture", "profile": "root"}
        self.assertEqual(self.client.post("/tasks", json=body).status_code, 401)
        self.assertEqual(self.client.post("/tasks", headers=self.headers, json=body).status_code, 422)

    def test_profile_is_forwarded_by_tasks_and_slash_commands(self):
        conversation = self.client.post("/conversations", headers=self.headers, json={}).json()["id"]
        body = {"conversation": conversation, "objective": "Inspect", "mode": "agent", "model": "fixture", "profile": "coding"}
        with (patch("local_agent.studio.api.Ollama.request", side_effect=metadata_response),
              patch.object(self.client.app.state.manager, "start", return_value="task") as start):
            for path, objective in (("/tasks", "Inspect"), ("/slash", "/agent Inspect")):
                response = self.client.post(path, headers=self.headers, json={**body, "objective": objective})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(start.call_args.kwargs["profile"], "coding")


class ProfileMigrationTests(WorkspaceTest):
    def test_legacy_tasks_keep_history_with_unified_profile(self):
        path = self.policy.state / "legacy-profile.sqlite3"
        with closing(sqlite3.connect(path)) as db, db:
            db.executescript("""
                CREATE TABLE conversations(id TEXT PRIMARY KEY,title TEXT NOT NULL,created REAL NOT NULL);
                INSERT INTO conversations VALUES ('chat','Existing',1);
                CREATE TABLE tasks(id TEXT PRIMARY KEY,conversation TEXT NOT NULL,mode TEXT NOT NULL,
                    status TEXT NOT NULL,model TEXT NOT NULL,created REAL NOT NULL,result TEXT);
                INSERT INTO tasks VALUES ('task','chat','agent','reported','fixture',1,'old result');
            """)
        store = Store(path)
        row = store.tasks()[0]
        self.assertEqual(row["profile"], "unified")
        self.assertEqual(row["result"], "old result")
        self.assertEqual(store.conversations()[0]["title"], "Existing")
