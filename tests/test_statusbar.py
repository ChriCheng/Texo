import gc
from pathlib import Path
from queue import SimpleQueue
import sys
from threading import Thread
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import weakref

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from texo.statusbar import StatusBar


class StatusBarTests(unittest.TestCase):
    def test_callback_is_retained_and_events_can_be_queued_until_close(self):
        native_callback = []
        library = SimpleNamespace(
            TexoInstallStatusItem=Mock(side_effect=lambda callback: native_callback.append(weakref.ref(callback)) or True),
            TexoRemoveStatusItem=Mock(),
            TexoSetLoginEnabled=Mock(),
            TexoActivateApplication=Mock(),
        )
        events = SimpleQueue()
        with patch("texo.statusbar.sys.platform", "darwin"), patch("texo.statusbar.ctypes.CDLL", return_value=library):
            statusbar = StatusBar(events.put)
            library.TexoInstallStatusItem.reset_mock()
            gc.collect()
            self.assertIsNotNone(native_callback[0]())
            native_callback[0]()(3)
            self.assertEqual(events.get_nowait(), 3)
            statusbar.set_login_enabled(True)
            statusbar.activate()
            statusbar.close()
            statusbar.close()
            statusbar.set_login_enabled(False)
            statusbar.activate()
        library.TexoSetLoginEnabled.assert_called_once_with(True)
        library.TexoActivateApplication.assert_called_once_with()
        library.TexoRemoveStatusItem.assert_called_once_with()

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


if __name__ == "__main__":
    unittest.main()
