import ctypes
import subprocess
import sys
import tempfile
from pathlib import Path
from threading import current_thread, main_thread

from PIL import Image, ImageGrab


def read_clipboard_image():
    image = ImageGrab.grabclipboard()
    if not isinstance(image, Image.Image):
        raise ValueError("剪贴板中没有图片，请先按 ⌘⇧⌃4 截取公式。")
    return image.copy()


def capture_image():
    with tempfile.TemporaryDirectory(prefix="texo-capture-") as directory:
        path = Path(directory) / "formula.png"
        result = subprocess.run(
            ["/usr/sbin/screencapture", "-i", "-x", str(path)],
            capture_output=True,
        )
        if result.returncode and result.stderr.strip():
            raise RuntimeError("截图失败，请在系统设置的「隐私与安全性 → 屏幕录制」中允许启动 Texo 的终端。")
        if not path.exists():
            return None
        with Image.open(path) as source:
            return source.copy()


class _EventType(ctypes.Structure):
    _fields_ = [("event_class", ctypes.c_uint32), ("event_kind", ctypes.c_uint32)]


class _HotkeyID(ctypes.Structure):
    _fields_ = [("signature", ctypes.c_uint32), ("identifier", ctypes.c_uint32)]


class GlobalHotkey:
    """Own global ⌘L until close(); callback must only enqueue work for Tk."""

    def __init__(self, callback):
        if sys.platform != "darwin":
            raise RuntimeError("全局 ⌘L 快捷键仅支持 macOS。")
        if current_thread() is not main_thread():
            raise RuntimeError("全局 ⌘L 快捷键必须在主线程注册。")
        self.carbon = ctypes.CDLL("/System/Library/Frameworks/Carbon.framework/Carbon")
        ptr = ctypes.c_void_p
        uint = ctypes.c_uint32
        status = ctypes.c_int32
        handler_type = ctypes.CFUNCTYPE(status, ptr, ptr, ptr)
        for name, arguments, result in (
            ("GetApplicationEventTarget", [], ptr),
            ("InstallEventHandler", [ptr, handler_type, uint, ctypes.POINTER(_EventType), ptr, ctypes.POINTER(ptr)], status),
            ("RegisterEventHotKey", [uint, uint, _HotkeyID, ptr, uint, ctypes.POINTER(ptr)], status),
            ("GetEventParameter", [ptr, uint, uint, ptr, ctypes.c_ulong, ptr, ptr], status),
            ("UnregisterEventHotKey", [ptr], status),
            ("RemoveEventHandler", [ptr], status),
        ):
            function = getattr(self.carbon, name)
            function.argtypes, function.restype = arguments, result
        self.hotkey = ptr()
        self.handler = ptr()

        def handle(_handler, event, _user_data):
            identifier = _HotkeyID()
            result = self.carbon.GetEventParameter(
                event, int.from_bytes(b"----", "big"), int.from_bytes(b"hkid", "big"),
                None, ctypes.sizeof(identifier), None, ctypes.byref(identifier),
            )
            if result or identifier.signature != int.from_bytes(b"TEXO", "big") or identifier.identifier != 1:
                return -9874  # eventNotHandledErr: leave other applications' hotkeys alone.
            callback()
            return 0

        self.callback = handler_type(handle)
        target = self.carbon.GetApplicationEventTarget()
        event_type = _EventType(int.from_bytes(b"keyb", "big"), 5)
        result = self.carbon.InstallEventHandler(target, self.callback, 1, ctypes.byref(event_type), None, ctypes.byref(self.handler))
        if not result:
            result = self.carbon.RegisterEventHotKey(
                37, 1 << 8, _HotkeyID(int.from_bytes(b"TEXO", "big"), 1), target, 1, ctypes.byref(self.hotkey),
            )
        if result:
            self.close()
            raise RuntimeError(f"无法注册全局 ⌘L，可能已被其他程序占用（macOS {result}）。")

    def close(self):
        if current_thread() is not main_thread():
            raise RuntimeError("全局 ⌘L 快捷键必须在主线程释放。")
        if self.hotkey:
            self.carbon.UnregisterEventHotKey(self.hotkey)
            self.hotkey = ctypes.c_void_p()
        if self.handler:
            self.carbon.RemoveEventHandler(self.handler)
            self.handler = ctypes.c_void_p()
