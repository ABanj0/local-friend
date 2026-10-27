"""Windows accessibility first; coordinate input is an explicitly approved fallback."""
import ctypes
import io
import os
import time
from ctypes import wintypes
from pathlib import PureWindowsPath

from .captures import Captures
from .safety import Denied


def process_image(pid):
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                             wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = api.OpenProcess(0x1000, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not api.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        return buffer.value
    finally:
        api.CloseHandle(handle)


def approved_image(app, executable, actual):
    expected, candidate = PureWindowsPath(executable), PureWindowsPath(actual)
    if candidate == expected:
        return True
    # The Windows launcher can hand off to the Microsoft Store package.
    system_notepad = PureWindowsPath(os.environ.get("WINDIR", r"C:\Windows")) / "System32/notepad.exe"
    packages = PureWindowsPath(os.environ.get("ProgramFiles", r"C:\Program Files")) / "WindowsApps"
    if app != "notepad" or expected != system_notepad or not candidate.is_relative_to(packages):
        return False
    parts = candidate.relative_to(packages).parts
    return (len(parts) == 3 and parts[0].lower().startswith("microsoft.windowsnotepad_")
            and parts[1].lower() == "notepad" and parts[2].lower() == "notepad.exe")


def choose_new_window(windows, previous_handles, app, executable, image_lookup=process_image):
    matches = []
    for window in windows:
        if window.handle in previous_handles or not window.is_visible():
            continue
        try:
            if approved_image(app, executable, image_lookup(window.process_id())):
                matches.append(window)
        except (OSError, RuntimeError):
            continue  # Exited or inaccessible process: never infer its identity from title.
    if len(matches) > 1:
        raise Denied("Several new application windows appeared; cannot identify one safely")
    return matches[0] if matches else None


class Desktop:
    def __init__(self, policy, capture=None):
        self.policy = policy
        self.apps = {}
        self.window_handles = {}
        self.backends = {}
        self.capture = capture
        self.captures = None

    def launch(self, app):
        executable = self.policy.config["desktop"]["applications"].get(app)
        if not executable:
            raise Denied("Application is not approved in agent.toml")
        self.policy.confirm("desktop_launch", {"app": app, "executable": executable})
        from pywinauto import Desktop as WindowsDesktop
        from pywinauto.application import Application
        # Enumerate native handles first: UIA enumeration can hang on unrelated providers.
        desktop = WindowsDesktop(backend="win32")
        previous = {window.handle for window in desktop.windows()}
        Application(backend="uia").start('"' + executable + '"', timeout=15)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            self.policy.check_stop()
            window = choose_new_window(desktop.windows(), previous, app, executable)
            if window is not None:
                actual = process_image(window.process_id())
                classic_notepad = (app == "notepad" and PureWindowsPath(actual) == PureWindowsPath(executable)
                                   and window.class_name() == "Notepad")
                backend = "win32" if classic_notepad else "uia"
                application = Application(backend=backend).connect(handle=window.handle)
                application.window(handle=window.handle).wait("visible", timeout=5)
                self.apps[app] = application
                self.window_handles[app] = window.handle
                self.backends[app] = backend
                return self.inspect(app)
            time.sleep(0.2)
        raise RuntimeError("No new approved application window appeared within 15 seconds. "
                           "Run in an unlocked desktop session. If Notepad reused a window, "
                           "save your work and close Notepad before rerunning the desktop test.")

    def window(self, app):
        self.policy.check_stop()
        if app not in self.apps:
            raise Denied("Launch the approved application first")
        root = self.window_handles[app]
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.IsWindow.argtypes = [wintypes.HWND]
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user32.GetAncestor.restype = wintypes.HWND
        if not user32.IsWindow(root):
            raise Denied("The approved application window has closed; launch it again")
        foreground = user32.GetForegroundWindow()
        # Only follow owned modal dialogs (e.g. Save As), never a different document window.
        handle = foreground if foreground and user32.GetAncestor(foreground, 3) == root else root
        return self.apps[app].window(handle=handle)

    def inspect(self, app):
        window = self.window(app)
        controls = []
        for item in window.descendants()[:150]:
            info = item.element_info
            controls.append({"name": info.name,
                             "automation_id": str(getattr(info, "automation_id", getattr(info, "control_id", ""))),
                             "control_type": getattr(info, "control_type", None) or item.class_name()})
        return {"app": app, "backend": self.backends[app], "title": window.window_text(), "controls": controls}

    def control(self, app, automation_id, control_type, action, text=""):
        if action not in {"click", "write", "read"}:
            raise ValueError("Supported accessibility actions: click, write, read")
        window = self.window(app)
        if self.backends[app] == "win32":
            control = window.child_window(control_id=int(automation_id), class_name=control_type)
        else:
            control = window.child_window(auto_id=automation_id, control_type=control_type)
        if action != "read":
            self.policy.confirm("desktop_" + action, {"app": app, "automation_id": automation_id,
                                "control_type": control_type, "text": text})
        if action == "click":
            if self.backends[app] == "win32":
                control.wrapper_object().click()
            else:
                control.wrapper_object().invoke()
        elif action == "write":
            control.wrapper_object().set_edit_text(text)
        return {"text": control.window_text()[:12000]}

    def input(self, app, action, text="", keys="", x=0, y=0):
        if action not in {"text", "hotkey", "click"}:
            raise ValueError("Supported input actions: text, hotkey, click")
        window = self.window(app)
        self.policy.confirm("desktop_input", {"app": app, "action": action, "text": text,
                            "keys": keys, "x": x, "y": y,
                            "warning": "Desktop input can affect files or external accounts."})
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.2
        window.set_focus()
        self.policy.check_stop()
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetForegroundWindow.restype = wintypes.HWND
        if user32.GetForegroundWindow() != window.handle:
            raise Denied("Could not verify focus on approved application")
        if action == "text":
            # UIA handles Unicode; this fallback intentionally accepts ASCII only.
            if not text.isascii():
                raise ValueError("Use desktop_control write for Unicode text")
            pyautogui.write(text, interval=0.01)
        elif action == "hotkey":
            pyautogui.hotkey(*keys.split("+"))
        else:
            rect = window.rectangle()
            if not (0 <= x < rect.width() and 0 <= y < rect.height()):
                raise Denied("Click must be inside approved application window")
            pyautogui.click(rect.left + x, rect.top + y)
        return {"app": app, "action": action, "performed": True}

    def screenshot(self, app):
        self.policy.confirm("desktop_screenshot", {"app": app})
        output = io.BytesIO()
        self.window(app).capture_as_image().save(output, format="PNG")
        if self.capture:
            return {"image_path": self.capture(output.getvalue())}
        if self.captures is None:
            self.captures = Captures(self.policy.state)
        return {"image_path": self.captures.write(output.getvalue())}

    def close(self):
        if self.captures:
            self.captures.close()
