"""Menu bar events supplied by the embedded macOS app launcher."""

import ctypes
import sys
from threading import current_thread, main_thread


class StatusBar:
    """Own the native menu item; callback must only enqueue events for Tk."""

    @staticmethod
    def available():
        if sys.platform != "darwin":
            return False
        try:
            library = ctypes.CDLL(None)
            for name in ("TexoInstallStatusItem", "TexoRemoveStatusItem", "TexoSetLoginEnabled", "TexoActivateApplication"):
                getattr(library, name)
        except (OSError, AttributeError):
            return False
        return True

    def __init__(self, callback):
        if current_thread() is not main_thread():
            raise RuntimeError("菜单栏图标必须在主线程创建。")
        if not self.available():
            raise RuntimeError("菜单栏图标仅支持从 Texo.app 启动。")
        self.library = ctypes.CDLL(None)
        callback_type = ctypes.CFUNCTYPE(None, ctypes.c_int)
        self.library.TexoInstallStatusItem.argtypes = [callback_type]
        self.library.TexoInstallStatusItem.restype = ctypes.c_bool
        self.library.TexoRemoveStatusItem.argtypes = []
        self.library.TexoRemoveStatusItem.restype = None
        self.library.TexoSetLoginEnabled.argtypes = [ctypes.c_bool]
        self.library.TexoSetLoginEnabled.restype = None
        self.library.TexoActivateApplication.argtypes = []
        self.library.TexoActivateApplication.restype = None
        self.callback = callback_type(callback)
        self.installed = bool(self.library.TexoInstallStatusItem(self.callback))
        if not self.installed:
            raise RuntimeError("无法创建菜单栏图标，可能已存在 Texo 图标。")

    def set_login_enabled(self, enabled):
        if current_thread() is not main_thread():
            raise RuntimeError("菜单栏选项必须在主线程更新。")
        if self.installed:
            self.library.TexoSetLoginEnabled(enabled)

    def activate(self):
        if current_thread() is not main_thread():
            raise RuntimeError("识别窗口必须在主线程激活。")
        if self.installed:
            self.library.TexoActivateApplication()

    def close(self):
        if current_thread() is not main_thread():
            raise RuntimeError("菜单栏图标必须在主线程释放。")
        if self.installed:
            self.library.TexoRemoveStatusItem()
            self.installed = False
