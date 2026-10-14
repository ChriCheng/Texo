import ctypes
from functools import wraps
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from texo.macos import read_clipboard_image


def isolated_native_test(method):
    @wraps(method)
    def run(self):
        if os.environ.get("TEXO_NATIVE_CHILD") == "1":
            return method(self)
        # Recreating macOS Tk roots after ML imports can leave invalid Cocoa observers.
        result = subprocess.run(
            [sys.executable, "-m", "unittest", f"test_macos.GlobalHotkeyTests.{method.__name__}", "-v"],
            cwd=Path(__file__).resolve().parent,
            env={**os.environ, "TEXO_NATIVE_CHILD": "1"},
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    return run


class ClipboardTests(unittest.TestCase):
    def test_image_is_detached_from_clipboard_source(self):
        source = Image.new("RGB", (24, 16), "red")
        with patch("PIL.ImageGrab.grabclipboard", return_value=source):
            result = read_clipboard_image()
        source.close()
        self.assertEqual(result.size, (24, 16))
        self.assertEqual(result.getpixel((0, 0)), (255, 0, 0))

    def test_clipboard_without_image_has_actionable_error(self):
        for value in (None, ["/private/tmp/not-an-image.txt"]):
            with self.subTest(value=value), patch("PIL.ImageGrab.grabclipboard", return_value=value):
                with self.assertRaisesRegex(ValueError, "剪贴板中没有图片"):
                    read_clipboard_image()


class CaptureTests(unittest.TestCase):
    def test_capture_reads_image_and_removes_temporary_file(self):
        from texo.macos import capture_image

        captured_paths = []

        def run(command, **kwargs):
            from subprocess import CompletedProcess

            self.assertEqual(command[:3], ["/usr/sbin/screencapture", "-i", "-x"])
            path = Path(command[-1])
            captured_paths.append(path)
            Image.new("RGB", (30, 20), "blue").save(path)
            return CompletedProcess(command, 0, b"", b"")

        with patch("subprocess.run", side_effect=run):
            image = capture_image()
        self.assertEqual(image.getpixel((0, 0)), (0, 0, 255))
        self.assertFalse(captured_paths[0].exists())
        self.assertFalse(captured_paths[0].parent.exists())

    def test_cancel_returns_none_and_permission_failure_is_reported(self):
        from subprocess import CompletedProcess
        from texo.macos import capture_image

        with patch("subprocess.run", return_value=CompletedProcess([], 1, b"", b"")):
            self.assertIsNone(capture_image())
        with patch("subprocess.run", return_value=CompletedProcess([], 1, b"", b"could not create image from display")):
            with self.assertRaisesRegex(RuntimeError, "屏幕录制"):
                capture_image()


@unittest.skipUnless(sys.platform == "darwin" and os.environ.get("TEXO_TEST_GUI") == "1", "requires a macOS desktop session")
class GlobalHotkeyTests(unittest.TestCase):
    @isolated_native_test
    def test_global_shortcut_is_exclusive_and_released_on_close(self):
        import tkinter as tk
        from texo.macos import GlobalHotkey

        root = tk.Tk()
        root.withdraw()
        hotkey = None
        try:
            root.update()
            hotkey = GlobalHotkey(lambda: None)
            with self.assertRaisesRegex(RuntimeError, "⌘L"):
                GlobalHotkey(lambda: None)
            hotkey.close()
            hotkey.close()
            hotkey = GlobalHotkey(lambda: None)
        finally:
            if hotkey is not None:
                hotkey.close()
            root.destroy()

    @isolated_native_test
    def test_native_hotkey_event_is_dispatched_by_tk_event_loop(self):
        import tkinter as tk
        from texo.macos import GlobalHotkey

        root = tk.Tk()
        root.withdraw()
        notifications = []
        hotkey = GlobalHotkey(lambda: notifications.append("capture"))
        carbon = ctypes.CDLL("/System/Library/Frameworks/Carbon.framework/Carbon")
        ptr, uint, status = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int32
        for name, arguments, result in (
            ("CreateEvent", [ptr, uint, uint, ctypes.c_double, uint, ctypes.POINTER(ptr)], status),
            ("SetEventParameter", [ptr, uint, uint, ctypes.c_ulong, ptr], status),
            ("GetMainEventQueue", [], ptr),
            ("GetApplicationEventTarget", [], ptr),
            ("PostEventToQueue", [ptr, ptr, ctypes.c_int16], status),
            ("ReleaseEvent", [ptr], None),
        ):
            function = getattr(carbon, name)
            function.argtypes, function.restype = arguments, result
        event = ptr()
        try:
            self.assertEqual(carbon.CreateEvent(None, int.from_bytes(b"keyb", "big"), 5, 0, 0, ctypes.byref(event)), 0)
            identifier = (uint * 2)(int.from_bytes(b"TEXO", "big"), 1)
            self.assertEqual(carbon.SetEventParameter(event, int.from_bytes(b"----", "big"), int.from_bytes(b"hkid", "big"), ctypes.sizeof(identifier), identifier), 0)
            target = ptr(carbon.GetApplicationEventTarget())
            self.assertEqual(carbon.SetEventParameter(event, int.from_bytes(b"ptrg", "big"), int.from_bytes(b"etrg", "big"), ctypes.sizeof(target), ctypes.byref(target)), 0)
            self.assertEqual(carbon.PostEventToQueue(carbon.GetMainEventQueue(), event, 1), 0)
            deadline = time.monotonic() + 2
            while not notifications and time.monotonic() < deadline:
                root.update()
                time.sleep(0.01)
            self.assertEqual(notifications, ["capture"])
        finally:
            if event:
                carbon.ReleaseEvent(event)
            hotkey.close()
            root.destroy()


if __name__ == "__main__":
    unittest.main()
