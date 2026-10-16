import ctypes
import gc
from pathlib import Path
from queue import SimpleQueue
import sys
from threading import Thread
import unittest
from unittest.mock import Mock, patch
import weakref

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from texo.popover import NativePopover


class NativePopoverTests(unittest.TestCase):
    def setUp(self):
        self.library = Mock()
        self.library.TexoInstallPopover.return_value = True
        self.platform = patch("texo.popover.sys.platform", "darwin")
        self.loader = patch("texo.popover.ctypes.CDLL", return_value=self.library)
        self.platform.start()
        self.loader.start()
        self.addCleanup(self.platform.stop)
        self.addCleanup(self.loader.stop)

    def test_callback_survives_gc_and_cleanup_is_idempotent(self):
        events = SimpleQueue()
        popover = NativePopover(events.put)
        callback = weakref.ref(self.library.TexoInstallPopover.call_args.args[0])
        self.library.TexoInstallPopover.reset_mock()
        gc.collect()
        self.assertIsNotNone(callback())
        callback()(7)
        self.assertEqual(events.get_nowait(), 7)
        popover.close()
        popover.close()
        popover.show()
        self.assertFalse(popover.is_shown())
        self.library.TexoRemovePopover.assert_called_once_with()
        self.library.TexoShowPopover.assert_not_called()

    def test_unicode_and_binary_image_cross_native_boundary_unchanged(self):
        popover = NativePopover(lambda event: None)
        text = "中文与公式 $x^2$"
        popover.set_result(text)
        self.library.TexoPopoverSetResult.assert_called_once_with(text.encode("utf-8"))
        self.library.TexoPopoverGetResult.return_value = text.encode("utf-8")
        self.assertEqual(popover.get_result(), text)
        popover.set_status("识别完成")
        self.library.TexoPopoverSetStatus.assert_called_once_with("识别完成".encode("utf-8"))
        png = b"\x89PNG\x00\x01\x00"
        popover.set_image(png)
        buffer, length = self.library.TexoPopoverSetImage.call_args.args
        self.assertEqual(ctypes.string_at(buffer, length), png)
        popover.close()

    def test_mode_and_copy_format_can_be_synchronized_from_the_menu(self):
        popover = NativePopover(lambda event: None)
        self.library.TexoPopoverGetMode.return_value = 1
        self.library.TexoPopoverGetFormat.return_value = 2
        self.assertEqual(popover.get_mode(), 1)
        self.assertEqual(popover.get_format(), 2)
        popover.set_mode(1)
        popover.set_format(0)
        self.library.TexoPopoverSetMode.assert_called_once_with(1)
        self.library.TexoPopoverSetFormat.assert_called_once_with(0)
        popover.close()
        popover.set_format(1)
        self.library.TexoPopoverSetFormat.assert_called_once_with(0)

    def test_missing_launcher_symbols_explains_how_to_start(self):
        with patch("texo.popover.ctypes.CDLL", return_value=object()):
            self.assertFalse(NativePopover.available())
            with self.assertRaisesRegex(RuntimeError, "新版 Texo.app"):
                NativePopover(lambda event: None)

    def test_worker_thread_cannot_write_native_view(self):
        popover = NativePopover(lambda event: None)
        failures = []

        def write():
            try:
                popover.set_result("工作线程")
            except RuntimeError as error:
                failures.append(str(error))

        worker = Thread(target=write)
        worker.start()
        worker.join()
        self.assertEqual(len(failures), 1)
        self.assertIn("主线程", failures[0])
        self.library.TexoPopoverSetResult.assert_not_called()
        popover.close()

    def test_copy_format_changes_require_the_main_thread(self):
        popover = NativePopover(lambda event: None)
        failures = []

        def change_format():
            try:
                popover.set_format(2)
            except RuntimeError as error:
                failures.append(str(error))

        worker = Thread(target=change_format)
        worker.start()
        worker.join()
        self.assertEqual(len(failures), 1)
        self.assertIn("主线程", failures[0])
        self.library.TexoPopoverSetFormat.assert_not_called()
        popover.close()


if __name__ == "__main__":
    unittest.main()
