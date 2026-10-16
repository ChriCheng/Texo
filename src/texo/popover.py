"""Native menu bar popover supplied by the embedded macOS launcher."""

import ctypes
import sys
from threading import current_thread, main_thread


_Callback = ctypes.CFUNCTYPE(None, ctypes.c_int)
_API = (
    ("TexoInstallPopover", [_Callback], ctypes.c_bool),
    ("TexoRemovePopover", [], None),
    ("TexoShowPopover", [], None),
    ("TexoHidePopover", [ctypes.c_bool], None),
    ("TexoPopoverShown", [], ctypes.c_bool),
    ("TexoPopoverSetImage", [ctypes.c_void_p, ctypes.c_size_t], None),
    ("TexoPopoverSetResult", [ctypes.c_char_p], None),
    ("TexoPopoverGetResult", [], ctypes.c_char_p),
    ("TexoPopoverSetStatus", [ctypes.c_char_p], None),
    ("TexoPopoverSetBusy", [ctypes.c_bool], None),
    ("TexoPopoverGetMode", [], ctypes.c_int),
    ("TexoPopoverSetMode", [ctypes.c_int], None),
    ("TexoPopoverSetResultMode", [ctypes.c_int], None),
    ("TexoPopoverGetFormat", [], ctypes.c_int),
    ("TexoPopoverSetFormat", [ctypes.c_int], None),
    ("TexoPopoverResetUndo", [], None),
    ("TexoPopoverSetCaptureShortcut", [ctypes.c_char_p], None),
    ("TexoCopyOffice", [ctypes.c_char_p, ctypes.c_char_p], ctypes.c_bool),
)


def _require_main_thread():
    if current_thread() is not main_thread():
        raise RuntimeError("菜单栏浮窗必须在主线程操作。")


class NativePopover:
    """Own the native view; callback must only enqueue events for Tk."""

    @staticmethod
    def available():
        if sys.platform != "darwin":
            return False
        try:
            library = ctypes.CDLL(None)
            for name, _arguments, _result in _API:
                getattr(library, name)
        except (OSError, AttributeError):
            return False
        return True

    def __init__(self, callback):
        _require_main_thread()
        if not self.available():
            raise RuntimeError("菜单栏浮窗仅支持从新版 Texo.app 启动。")
        self.library = ctypes.CDLL(None)
        for name, arguments, result in _API:
            function = getattr(self.library, name)
            function.argtypes, function.restype = arguments, result
        self.callback = _Callback(callback)
        self.installed = bool(self.library.TexoInstallPopover(self.callback))
        if not self.installed:
            raise RuntimeError("无法创建菜单栏浮窗，请先创建 Texo 菜单栏图标。")

    def show(self):
        _require_main_thread()
        if self.installed:
            self.library.TexoShowPopover()

    def hide(self, immediately=False):
        _require_main_thread()
        if self.installed:
            self.library.TexoHidePopover(immediately)

    def is_shown(self):
        _require_main_thread()
        return self.installed and bool(self.library.TexoPopoverShown())

    def set_image(self, png):
        _require_main_thread()
        if self.installed:
            buffer = ctypes.create_string_buffer(png)
            self.library.TexoPopoverSetImage(buffer, len(png))

    def set_result(self, text, reset_undo=False):
        _require_main_thread()
        if self.installed:
            self.library.TexoPopoverSetResult(text.encode("utf-8"))
            if reset_undo:
                self.reset_undo()

    def reset_undo(self):
        _require_main_thread()
        if self.installed:
            self.library.TexoPopoverResetUndo()

    def set_capture_shortcut(self, label):
        _require_main_thread()
        if self.installed:
            self.library.TexoPopoverSetCaptureShortcut(label.encode("utf-8"))

    def copy_office(self, payload):
        _require_main_thread()
        if not self.installed:
            return False
        return bool(self.library.TexoCopyOffice(payload["plain"].encode("utf-8"),
                                              payload["html"].encode("utf-8")))

    def get_result(self):
        _require_main_thread()
        if not self.installed:
            return ""
        return (self.library.TexoPopoverGetResult() or b"").decode("utf-8")

    def set_status(self, text):
        _require_main_thread()
        if self.installed:
            self.library.TexoPopoverSetStatus(text.encode("utf-8"))

    def set_busy(self, busy):
        _require_main_thread()
        if self.installed:
            self.library.TexoPopoverSetBusy(busy)

    def get_mode(self):
        _require_main_thread()
        return self.library.TexoPopoverGetMode() if self.installed else 0

    def set_mode(self, mode):
        _require_main_thread()
        if self.installed:
            self.library.TexoPopoverSetMode(mode)

    def set_result_mode(self, mode):
        _require_main_thread()
        if self.installed:
            self.library.TexoPopoverSetResultMode(mode)

    def get_format(self):
        _require_main_thread()
        return self.library.TexoPopoverGetFormat() if self.installed else 2

    def set_format(self, format):
        _require_main_thread()
        if self.installed:
            self.library.TexoPopoverSetFormat(format)

    def close(self):
        _require_main_thread()
        if self.installed:
            self.library.TexoRemovePopover()
            self.installed = False
