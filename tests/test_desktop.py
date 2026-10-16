from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from PIL import Image

from main import ROOT
from texo.desktop import NativeOCRWindow


class NativeDesktopTests(unittest.TestCase):
    def setUp(self):
        self.root, self.panel, self.statusbar = Mock(), Mock(), Mock()
        self.panel.get_mode.return_value = 0
        self.panel.get_format.return_value = 2
        self.panel.get_result.return_value = ""
        self.panel.set_result.side_effect = lambda text: setattr(self.panel.get_result, "return_value", text)
        for name, result in (("NativePopover", self.panel), ("StatusBar", self.statusbar), ("GlobalHotkey", Mock()), ("login_enabled", False)):
            patched = patch(f"texo.desktop.{name}", return_value=result)
            patched.start()
            self.addCleanup(patched.stop)
        self.window = NativeOCRWindow(self.root, ROOT / "model", Mock(), Mock())

    def test_start_keeps_panel_hidden_until_success_and_copies_before_show(self):
        self.panel.get_mode.return_value = 1
        self.window.open_image.return_value = Image.new("RGB", (24, 16), "red")
        self.window.recognize.return_value = "x^2\n"
        order = []
        self.root.clipboard_append.side_effect = lambda text: order.append(("copy", text))
        self.panel.show.side_effect = lambda: order.append(("show", None))
        with patch("texo.desktop.Thread", side_effect=lambda target, daemon: SimpleNamespace(start=target)):
            self.window.start("fixture", "测试")
        self.assertTrue(self.window.busy)
        self.panel.show.assert_not_called()
        self.root.clipboard_clear.assert_not_called()
        self.statusbar.set_progress.assert_called_with(-2, "正在识别 测试…")
        self.window.poll()
        self.assertFalse(self.window.busy)
        self.assertEqual(order, [("copy", "$$x^2$$"), ("show", None)])
        self.statusbar.set_progress.assert_called_with(-1)

    def test_result_classification_uses_formula_format_only_without_prose(self):
        for result, expected, mode in (("$$x^2$$\n", "$$x^2$$", 1), (r"$$\text{price \$5}$$", r"$$\text{price \$5}$$", 1), ("说明 $x^2$\n", "说明 $x^2$", 0), ("$$x$$\n\n$$y$$", "$$x$$\n\n$$y$$", 0)):
            with self.subTest(result=result):
                self.window.result_mode = 0
                self.window.events.put(("result", result, 1, None))
                self.window.poll()
                self.root.clipboard_append.assert_called_with(expected)
                self.assertEqual(self.window.result_mode, mode)
        self.panel.set_mode.assert_not_called()

    def test_explicit_view_during_clipboard_read_is_not_hidden_again(self):
        self.window.open_image.return_value = Image.new("RGB", (24, 16), "red")
        self.window.acquire(Mock(), "剪贴板图片")
        self.window.show()
        self.panel.hide.reset_mock()
        self.window.events.put(("image", "fixture", (False, "剪贴板图片"), None))
        with patch("texo.desktop.Thread"):
            self.window.poll()
        self.assertTrue(self.window.busy)
        self.panel.hide.assert_not_called()

    def test_saved_recognition_mode_is_respected_on_startup(self):
        self.panel.get_mode.return_value = 1
        window = NativeOCRWindow(self.root, ROOT / "model", Mock(), Mock())
        self.assertEqual(window.result_mode, 1)
        self.panel.set_mode.assert_not_called()

    def test_failed_recognition_does_not_copy_and_progress_stops(self):
        self.window.events.put(("progress", None, "正在识别公式…", None))
        self.window.events.put(("result", None, 0, "model failed"))
        self.window.poll()
        self.root.clipboard_clear.assert_not_called()
        self.statusbar.set_progress.assert_any_call(-2, "正在识别公式…")
        self.statusbar.set_progress.assert_called_with(-1)
        self.panel.show.assert_called_once_with()

    def test_menu_settings_update_the_panel_without_showing_it(self):
        self.window.events.put(12)
        self.window.events.put(21)
        self.window.poll()
        self.panel.set_format.assert_called_once_with(2)
        self.panel.set_mode.assert_called_once_with(1)
        self.panel.show.assert_not_called()

    def test_clipboard_failure_does_not_stop_the_event_loop(self):
        self.root.clipboard_append.side_effect = RuntimeError("clipboard unavailable")
        self.window.events.put(("result", "中文", 1, None))
        self.window.poll()
        self.panel.set_status.assert_called_with("复制失败：clipboard unavailable")
        self.panel.show.assert_called_once_with()
        self.root.after.assert_called_with(30, self.window.poll)

    def test_copy_follows_result_mode_and_preserves_markdown(self):
        self.panel.get_result.return_value = "中文 $x$\n"
        self.panel.get_mode.return_value = 1
        self.panel.get_format.return_value = 2
        self.window.copy()
        self.root.clipboard_append.assert_called_with("中文 $x$")
        self.window.result_mode = 1
        self.panel.get_result.return_value = "\\larr x\n"
        self.window.copy()
        self.root.clipboard_append.assert_called_with("$$\\leftarrow x$$")

    def test_recognition_can_be_reopened_but_capture_cannot(self):
        self.window.busy = True
        self.window.show()
        self.panel.show.assert_called_once_with()
        self.window.interaction_active = True
        self.window.show()
        self.panel.show.assert_called_once_with()

    def test_cancelled_or_failed_file_dialog_restores_interaction(self):
        self.window.start = Mock()
        for outcome in ("", RuntimeError("dialog failed")):
            with self.subTest(outcome=outcome), patch("tkinter.filedialog.askopenfilename") as dialog:
                if isinstance(outcome, Exception):
                    dialog.side_effect = outcome
                else:
                    dialog.return_value = outcome
                self.window.choose()
                self.assertNotIn("parent", dialog.call_args.kwargs)
                self.assertFalse(self.window.busy)
                self.assertFalse(self.window.interaction_active)
                self.panel.show.assert_called()
                self.panel.set_result.assert_not_called()
                self.window.start.assert_not_called()

    def test_cancellation_preserves_output_and_quit_releases_native_resources(self):
        self.window.interaction_active = self.window.busy = True
        self.window.events.put(("image", None, (False, "截图"), None))
        self.window.poll()
        self.assertFalse(self.window.busy)
        self.assertFalse(self.window.interaction_active)
        self.panel.set_result.assert_not_called()
        self.panel.show.assert_not_called()
        hotkeys = list(self.window.hotkeys)
        self.window.close(SimpleNamespace(widget=self.root))
        self.panel.close.assert_called_once_with()
        self.statusbar.close.assert_called_once_with()
        for hotkey in hotkeys:
            self.assertTrue(hotkey.close.called)
        self.assertEqual(self.window.hotkeys, [])

    def test_permission_error_resets_capture_state_and_allows_retry(self):
        self.panel.is_shown.return_value = True
        with patch("texo.desktop.capture_image", side_effect=RuntimeError("截图权限未开启。")) as capture, patch("texo.desktop.Thread", side_effect=lambda target, daemon: SimpleNamespace(start=target)):
            for _ in range(2):
                self.window.screenshot()
                self.assertTrue(self.window.busy)
                self.assertTrue(self.window.interaction_active)
                delay, start_worker = self.root.after.call_args.args
                self.assertEqual(delay, 200)
                start_worker()
                self.window.poll()
                self.assertFalse(self.window.busy)
                self.assertFalse(self.window.interaction_active)
                self.panel.set_status.assert_called_with("截图权限未开启。")
                self.panel.show.assert_called()
            self.assertEqual(capture.call_count, 2)
        self.panel.set_result.assert_not_called()


if __name__ == "__main__":
    unittest.main()
