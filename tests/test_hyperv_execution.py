"""Execution contracts. Simulated controllers never establish live VM isolation."""
import copy
import json
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from local_agent.coding import Coding
from local_agent.execution import descriptor, selected
from local_agent.hyperv_control import Settings
from local_agent.hyperv_execution import inputs, lease_path, read_lease, recover
from local_agent.safety import Denied, Policy


def configuration(directory):
    root = Path(directory)
    workspace, state, storage = root / "project", root / "state", root / "vm"
    for path in (workspace, state, storage):
        path.mkdir()
    identity, hosts = root / "identity", root / "known_hosts"
    identity.write_bytes(b"fixture only, never used for authentication")
    hosts.write_bytes(b"fixture")
    return {"paths": {"workspace": str(workspace), "state": str(state)},
            "commands": {"test": ["{python}", "-m", "unittest", "discover", "-s", ".", "-v"]},
            "coding_execution": {"backend": "hyperv", "vm_id": str(uuid.uuid4()), "owner_id": str(uuid.uuid4()),
                                 "checkpoint_id": str(uuid.uuid4()), "switch_id": str(uuid.uuid4()),
                                 "storage": str(storage), "host_ip": "172.28.192.1", "ssh_user": "studiotest",
                                 "identity_file": str(identity), "known_hosts": str(hosts),
                                 "python": r"C:\Users\StudioTest\python\python.exe",
                                 "guest_root": r"C:\Users\StudioTest\LocalAgentSandbox", "inputs": ["*.py"]}}


class ExecutionSelectionTests(unittest.TestCase):
    def test_missing_setting_labels_actual_host_scope_and_retains_dispatch(self):
        self.assertEqual(selected({}), "trusted_host")
        self.assertEqual(descriptor({})["label"], "Trusted host execution")
        self.assertFalse(descriptor({})["isolation_required"])
        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(temporary)
            config.pop("coding_execution")
            coding = Coding(Policy(config))
            with patch.object(coding.execution, "_command", return_value={"exit_code": 4}) as command:
                self.assertEqual(coding.command("test"), {"exit_code": 4})
                command.assert_called_once_with("test", ".")

    def test_unknown_malformed_and_misconfigured_backends_never_choose_host(self):
        for setting in (None, True, [], {"backend": []}, {"backend": "unknown"}, {"backend": "trusted_host", "vm": "typo"}):
            with self.subTest(setting=setting), self.assertRaises(Denied):
                selected({"coding_execution": setting})
        with patch("local_agent.hyperv_control.os", SimpleNamespace(name="posix")), self.assertRaisesRegex(Denied, "no host fallback"):
            Settings.parse({"coding_execution": {"backend": "hyperv"}})

    def test_descriptor_requires_validation_and_contains_no_connection_credentials(self):
        value = descriptor({"coding_execution": {"backend": "hyperv", "identity_file": "PRIVATE"}})
        self.assertTrue(value["isolation_required"])
        self.assertIn("validated", value["label"])
        self.assertNotIn("PRIVATE", json.dumps(value))


class VMInputTests(unittest.TestCase):
    def test_freeze_exact_crlf_unicode_bytes_and_selected_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(temporary);policy = Policy(config)
            (policy.root / "tests").mkdir()
            content = "# café\r\nvalue=1\r\n".encode()
            (policy.root / "tests/test_value.py").write_bytes(content)
            (policy.root / "unselected.txt").write_text("not selected")
            frozen, cwd = inputs(policy, ["tests/*.py"], "tests")
            self.assertEqual(cwd, "tests")
            self.assertEqual(set(frozen), {"tests/test_value.py"})
            self.assertEqual(frozen["tests/test_value.py"]["raw"], content)

    def test_missing_sensitive_hardlinked_and_oversize_inputs_fail_without_partial_stage(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(temporary);policy = Policy(config)
            with self.assertRaises(Denied):
                inputs(policy, ["*.py"], ".")
            (policy.root / ".env.py").write_text("SECRET=fixture")
            with self.assertRaises(Denied):
                inputs(policy, ["*.py"], ".")
            (policy.root / ".env.py").unlink()
            source = policy.root / "test_value.py";source.write_text("value=1")
            os.link(source, policy.root / "test_alias.py")
            with self.assertRaises(Denied):
                inputs(policy, ["*.py"], ".")
            (policy.root / "test_alias.py").unlink()
            source.write_bytes(b"x" * (256 * 1024 + 1))
            with self.assertRaises((Denied, ValueError)):
                inputs(policy, ["*.py"], ".")


@unittest.skipUnless(os.name == "nt", "Hyper-V configuration is Windows-only")
class VMConfigurationTests(unittest.TestCase):
    def test_fixed_ssh_client_environment_and_internal_stdin_preserve_repo_environment_filter(self):
        from local_agent.process import run_process
        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(temporary);policy = Policy(config)
            with patch("local_agent.process.subprocess.Popen") as spawn, self.assertRaises(ValueError):
                run_process([sys.executable, "-V"], policy.root, policy, windows_ssh=True)
            spawn.assert_not_called()
            ssh = str(Path(os.environ["WINDIR"]) / "System32/OpenSSH/ssh.exe")
            result = run_process([ssh, "-V"], policy.root, policy, windows_ssh=True)
            self.assertEqual(result['exit_code'], 0)
            self.assertIn('OpenSSH', result['output'])
            with tempfile.TemporaryFile() as stream:
                stream.write(b'stdin-fixture');stream.seek(0)
                result = run_process([sys.executable, '-c', 'import sys,os;print(sys.stdin.read());print("PROGRAMDATA" in os.environ)'],
                                     policy.root, policy, stdin=stream)
            self.assertEqual(result['exit_code'], 0)
            self.assertIn('stdin-fixture', result['output'])
            self.assertIn('False', result['output'])

    def test_system_ssh_supports_windows_servicing_links_without_widening_input_or_key_rules(self):
        from local_agent.hyperv_control import regular
        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(temporary);coding = Coding(Policy(config))
            command = coding.execution._ssh("172.28.192.11", 'print("probe")')
            self.assertIn("StrictHostKeyChecking=yes", command)
            self.assertIn("IdentityAgent=none", command)
            self.assertIn("NUL", command)
            self.assertNotIn("SendEnv", " ".join(command))
            key = Path(config['coding_execution']['identity_file'])
            os.link(key, key.with_name('alias'))
            with self.assertRaises(Denied):
                regular(key)
            with self.assertRaises(Denied):
                regular(key, serviced_system_file=True)

    def test_strict_identity_network_account_paths_patterns_and_time_budgets(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(temporary)
            self.assertEqual(Settings.parse(config).timeout, 60)
            cases = {"vm_id": "ambiguous", "host_ip": "example.com", "ssh_user": "user;command",
                     "python": r"C:\Windows\python.exe", "guest_root": r"\\host\share",
                     "inputs": ["../*.py"], "timeout": True, "boot_timeout": 999}
            for key, invalid in cases.items():
                changed = copy.deepcopy(config);changed["coding_execution"][key] = invalid
                with self.subTest(key=key), self.assertRaises(Denied):
                    Settings.parse(changed)
            for invalid in (["**/*.py"], ["tests/*/*.py"], [".ssh/*.py"]):
                changed = copy.deepcopy(config);changed["coding_execution"]["inputs"] = invalid
                if invalid == [".ssh/*.py"]:
                    (Path(config["paths"]["workspace"]) / ".ssh").mkdir()
                    (Path(config["paths"]["workspace"]) / ".ssh/secret.py").write_text("fixture")
                    with self.assertRaises(Denied):
                        inputs(Policy(changed), Settings.parse(changed).inputs, ".")
                else:
                    with self.assertRaises(Denied):
                        Settings.parse(changed)

    def test_denial_and_changed_review_never_prepare_or_run_a_vm(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(temporary)
            source = Path(config["paths"]["workspace"]) / "test_value.py";source.write_text("value=1")
            for change in (False, True):
                def approval(action, details, change=change):
                    self.assertEqual(action, "execute_code")
                    self.assertEqual(details["backend"], "hyperv")
                    self.assertEqual(len(details["inputs"]), 1)
                    if change:
                        source.write_text("value=2")
                    return change
                coding = Coding(Policy(config, approval))
                with patch.object(coding.execution.controller, "call", return_value={"state": "Off"}) as control:
                    with self.assertRaises(Denied):
                        coding.command("test")
                    control.assert_called_once_with("inspect")
                self.assertFalse(lease_path(coding.execution.settings).exists())

    def test_unsupported_git_background_or_command_profiles_never_run_on_host(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(temporary);coding = Coding(Policy(config, lambda *_: True))
            config["commands"]["unsafe"] = ["powershell.exe", "-Command", "Write-Output fixture"]
            with patch("local_agent.coding.run_process") as host:
                for action in (lambda: coding.git("status"), lambda: coding.start("test"), lambda: coding.command("unsafe")):
                    with self.assertRaises(Denied):
                        action()
                host.assert_not_called()

    def test_live_lease_other_owner_and_pid_reuse_recovery_bound_to_exact_vm(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(temporary);settings = Settings.parse(config)
            value = {"vm_id": settings.vm_id, "run_id": "a" * 32, "pid": 12345, "created": 456}
            lease_path(settings).write_text(json.dumps(value))
            with patch("local_agent.hyperv_execution.Controller") as control:
                with patch("local_agent.hyperv_execution.process_identity", return_value=456):
                    recover(config)
                control.assert_not_called()
                recover(config, owner=54321)
                control.assert_not_called()
                with patch("local_agent.hyperv_execution.process_identity", return_value=789):
                    recover(config, owner=12345)
                control.assert_called_once_with(settings, "a" * 32)
                control.return_value.call.assert_called_once_with("stop")
            self.assertFalse(lease_path(settings).exists())

    def test_malformed_or_cross_vm_lease_never_stops_anything(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(temporary);settings = Settings.parse(config)
            for text in ('{"private":"fixture"}', json.dumps({"vm_id": str(uuid.uuid4()), "run_id": "a" * 32, "pid": 1, "created": 2})):
                lease_path(settings).write_text(text)
                with patch("local_agent.hyperv_execution.Controller") as control:
                    with self.assertRaises(Denied):
                        read_lease(settings)
                    with self.assertRaises(Denied):
                        recover(config)
                    control.assert_not_called()
