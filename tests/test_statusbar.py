import gc
from pathlib import Path
from queue import SimpleQueue
import sys
from threading import Thread
import unittest
from unittest.mock import Mock, call, patch
import weakref

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from texo.statusbar import StatusBar


class StatusBarTests(unittest.TestCase):
    def test_callback_is_retained_and_events_can_be_queued_until_close(self):
        native_callback = []
        library = Mock()
        library.TexoInstallStatusItem.side_effect = lambda callback: native_callback.append(weakref.ref(callback)) or True
        events = SimpleQueue()
        with patch("texo.statusbar.sys.platform", "darwin"), patch("texo.statusbar.ctypes.CDLL", return_value=library):
            statusbar = StatusBar(events.put)
            library.TexoInstallStatusItem.reset_mock()
            gc.collect()
            self.assertIsNotNone(native_callback[0]())
            native_callback[0]()(3)
            self.assertEqual(events.get_nowait(), 3)
            statusbar.set_login_enabled(True)
            statusbar.close()
            statusbar.close()
            statusbar.set_login_enabled(False)
        library.TexoSetLoginEnabled.assert_called_once_with(True)
        library.TexoRemoveStatusItem.assert_called_once_with()

    def test_settings_and_unicode_progress_cross_native_boundary(self):
        library = Mock()
        library.TexoInstallStatusItem.return_value = True
        library.TexoGetCopyFormat.return_value = 2
        library.TexoGetRecognitionMode.return_value = 0
        with patch("texo.statusbar.sys.platform", "darwin"), patch("texo.statusbar.ctypes.CDLL", return_value=library):
            statusbar = StatusBar(lambda event: None)
            self.assertEqual(statusbar.get_copy_format(), 2)
            self.assertEqual(statusbar.get_recognition_mode(), 0)
            statusbar.set_copy_format(1)
            statusbar.set_recognition_mode(1)
            for value, label in ((0.25, "处理图片"), (-2, "识别公式"), (-1, "")):
                statusbar.set_progress(value, label)
            statusbar.close()
            statusbar.set_progress(0.5, "已关闭")
            statusbar.set_copy_format(0)
            statusbar.set_recognition_mode(0)
        library.TexoSetCopyFormat.assert_called_once_with(1)
        library.TexoSetRecognitionMode.assert_called_once_with(1)
        self.assertEqual(library.TexoSetRecognitionProgress.call_args_list, [
            call(0.25, "处理图片".encode("utf-8")),
            call(-2, "识别公式".encode("utf-8")),
            call(-1, b""),
        ])

    def test_unbundled_launcher_has_a_friendly_error(self):
        with patch("texo.statusbar.sys.platform", "darwin"), patch("texo.statusbar.ctypes.CDLL", return_value=object()):
            self.assertFalse(StatusBar.available())
            with self.assertRaisesRegex(RuntimeError, "Texo.app"):
                StatusBar(lambda event: None)

    def test_creation_requires_main_thread_before_native_call(self):
        failures = []

        def create():
            try:
                StatusBar(lambda event: None)
            except RuntimeError as error:
                failures.append(str(error))

        with patch("texo.statusbar.ctypes.CDLL") as library:
            worker = Thread(target=create)
            worker.start()
            worker.join()
        self.assertEqual(len(failures), 1)
        self.assertIn("主线程", failures[0])
        library.assert_not_called()

    def test_shortcut_preferences_and_settings_use_the_same_callback(self):
        library = Mock()
        library.TexoInstallStatusItem.return_value = True
        library.TexoGetShortcutKey.side_effect = [37, 41]
        library.TexoGetShortcutModifiers.side_effect = [256, 768]
        library.TexoGetShortcutLabel.side_effect = ["⌘L".encode(), "⌘⇧;".encode()]
        library.TexoGetDraftShortcutKey.side_effect = [40, 11]
        library.TexoGetDraftShortcutModifiers.side_effect = [2304, 2304]
        library.TexoGetDraftShortcutLabel.side_effect = ["⌥⌘K".encode(), "⌥⌘B".encode()]
        with patch("texo.statusbar.sys.platform", "darwin"), patch("texo.statusbar.ctypes.CDLL", return_value=library):
            statusbar = StatusBar(lambda event: None)
            self.assertEqual(statusbar.get_shortcuts()[0], dict(key_code=37, modifiers=256, label="⌘L"))
            self.assertEqual(statusbar.get_shortcuts(draft=True)[1], dict(key_code=11, modifiers=2304, label="⌥⌘B"))
            self.assertTrue(statusbar.show_shortcut_settings())
            library.TexoShowShortcutSettings.assert_called_once_with(statusbar.callback)
            statusbar.set_shortcut_error("快捷键已占用")
            library.TexoShortcutSettingsSetError.assert_called_once_with("快捷键已占用".encode())
            self.assertTrue(statusbar.commit_shortcuts())
            statusbar.close()
            self.assertFalse(statusbar.show_shortcut_settings())


if __name__ == "__main__":
    unittest.main()
