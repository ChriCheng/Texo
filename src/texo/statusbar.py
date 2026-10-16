"""Menu bar events supplied by the embedded macOS app launcher."""

import ctypes
import sys
from threading import current_thread, main_thread


_Callback = ctypes.CFUNCTYPE(None, ctypes.c_int)
_API = (
    ("TexoInstallStatusItem", [_Callback], ctypes.c_bool),
    ("TexoRemoveStatusItem", [], None),
    ("TexoSetLoginEnabled", [ctypes.c_bool], None),
    ("TexoGetCopyFormat", [], ctypes.c_int),
    ("TexoSetCopyFormat", [ctypes.c_int], None),
    ("TexoGetCopyMode", [], ctypes.c_int),
    ("TexoSetCopyMode", [ctypes.c_int], None),
    ("TexoGetRecognitionMode", [], ctypes.c_int),
    ("TexoSetRecognitionMode", [ctypes.c_int], None),
    ("TexoSetRecognitionProgress", [ctypes.c_double, ctypes.c_char_p], None),
    ("TexoShowShortcutSettings", [_Callback], ctypes.c_bool),
    ("TexoShortcutSettingsShown", [], ctypes.c_bool),
    ("TexoShortcutSettingsClose", [], None),
    ("TexoShortcutSettingsSetError", [ctypes.c_char_p], None),
    ("TexoGetShortcutKey", [ctypes.c_int], ctypes.c_int),
    ("TexoGetShortcutModifiers", [ctypes.c_int], ctypes.c_uint),
    ("TexoGetShortcutLabel", [ctypes.c_int], ctypes.c_char_p),
    ("TexoGetDraftShortcutKey", [ctypes.c_int], ctypes.c_int),
    ("TexoGetDraftShortcutModifiers", [ctypes.c_int], ctypes.c_uint),
    ("TexoGetDraftShortcutLabel", [ctypes.c_int], ctypes.c_char_p),
    ("TexoCommitShortcuts", [], ctypes.c_bool),
)


def _require_main_thread():
    if current_thread() is not main_thread():
        raise RuntimeError("菜单栏图标必须在主线程操作。")


class StatusBar:
    """Own the native menu item; callback must only enqueue events for Tk."""

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
            raise RuntimeError("菜单栏图标仅支持从 Texo.app 启动。")
        self.library = ctypes.CDLL(None)
        for name, arguments, result in _API:
            function = getattr(self.library, name)
            function.argtypes, function.restype = arguments, result
        self.callback = _Callback(callback)
        self.installed = bool(self.library.TexoInstallStatusItem(self.callback))
        if not self.installed:
            raise RuntimeError("无法创建菜单栏图标，可能已存在 Texo 图标。")

    def set_login_enabled(self, enabled):
        _require_main_thread()
        if self.installed:
            self.library.TexoSetLoginEnabled(enabled)

    def get_copy_format(self):
        _require_main_thread()
        return self.library.TexoGetCopyFormat() if self.installed else 2

    def set_copy_format(self, format):
        _require_main_thread()
        if self.installed:
            self.library.TexoSetCopyFormat(format)

    def get_recognition_mode(self):
        _require_main_thread()
        return self.library.TexoGetRecognitionMode() if self.installed else 0

    def get_copy_mode(self):
        _require_main_thread()
        return self.library.TexoGetCopyMode() if self.installed else 0

    def set_copy_mode(self, mode):
        _require_main_thread()
        if self.installed:
            self.library.TexoSetCopyMode(mode)

    def set_recognition_mode(self, mode):
        _require_main_thread()
        if self.installed:
            self.library.TexoSetRecognitionMode(mode)

    def set_progress(self, value, label=""):
        _require_main_thread()
        if self.installed:
            self.library.TexoSetRecognitionProgress(value, label.encode("utf-8"))

    def get_shortcuts(self, draft=False):
        _require_main_thread()
        prefix = "TexoGetDraftShortcut" if draft else "TexoGetShortcut"
        return [dict(key_code=getattr(self.library, prefix + "Key")(action),
                     modifiers=getattr(self.library, prefix + "Modifiers")(action),
                     label=(getattr(self.library, prefix + "Label")(action) or b"").decode("utf-8"))
                for action in range(2)]

    def show_shortcut_settings(self):
        _require_main_thread()
        return self.installed and bool(self.library.TexoShowShortcutSettings(self.callback))

    def close_shortcut_settings(self):
        _require_main_thread()
        if self.installed:
            self.library.TexoShortcutSettingsClose()

    def set_shortcut_error(self, message):
        _require_main_thread()
        if self.installed:
            self.library.TexoShortcutSettingsSetError(message.encode("utf-8"))

    def commit_shortcuts(self):
        _require_main_thread()
        return self.installed and bool(self.library.TexoCommitShortcuts())

    def close(self):
        _require_main_thread()
        if self.installed:
            self.library.TexoShortcutSettingsClose()
            self.library.TexoRemoveStatusItem()
            self.installed = False
