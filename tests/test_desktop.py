from unittest.mock import Mock

from local_agent.desktop import approved_image, choose_new_window
from local_agent.safety import Denied

from .support import WorkspaceTest


class DesktopWindowTests(WorkspaceTest):
    executable = r"C:\Windows\System32\notepad.exe"
    store = r"C:\Program Files\WindowsApps\Microsoft.WindowsNotepad_11.0_x64__8wekyb3d8bbwe\Notepad\Notepad.exe"

    def window(self, handle, pid):
        window = Mock(handle=handle)
        window.process_id.return_value = pid
        return window

    def test_store_handoff_new_window_is_found(self):
        window = self.window(12, 200)
        result = choose_new_window([window], {11}, "notepad", self.executable, lambda _: self.store)
        self.assertIs(result, window)

    def test_existing_notepad_is_never_attached(self):
        result = choose_new_window([self.window(11, 200)], {11}, "notepad", self.executable,
                                   lambda _: self.store)
        self.assertIsNone(result)

    def test_hidden_ime_and_tooltip_windows_are_ignored(self):
        hidden = self.window(13, 200)
        hidden.is_visible.return_value = False
        visible = self.window(12, 200)
        self.assertIs(choose_new_window([hidden, visible], set(), "notepad", self.executable,
                                       lambda _: self.executable), visible)

    def test_title_or_executable_basename_is_insufficient(self):
        self.assertFalse(approved_image("notepad", self.executable, r"C:\unapproved\notepad.exe"))
        self.assertFalse(approved_image("other", self.executable, self.store))

    def test_ambiguous_windows_are_rejected(self):
        with self.assertRaises(Denied):
            choose_new_window([self.window(11, 100), self.window(12, 200)], set(),
                              "notepad", self.executable, lambda _: self.store)

    def test_delayed_window_can_be_discovered(self):
        self.assertIsNone(choose_new_window([], set(), "notepad", self.executable))
        window = self.window(12, 200)
        self.assertIs(choose_new_window([window], set(), "notepad", self.executable,
                                       lambda _: self.executable), window)
