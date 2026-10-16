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
        self.panel.set_format.side_effect = lambda value: setattr(self.panel.get_format, "return_value", value)
        self.panel.get_result.return_value = ""
        self.panel.set_result.side_effect = lambda text, **options: setattr(self.panel.get_result, "return_value", text)
        self.statusbar.get_shortcuts.return_value = [
            dict(key_code=37, modifiers=256, label="⌘L"),
            dict(key_code=41, modifiers=768, label="⌘⇧;"),
        ]
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
        self.statusbar.set_progress.assert_called_with(0, "正在识别 测试…")
        self.window.poll()
        self.assertFalse(self.window.busy)
        self.assertEqual(order, [("copy", "$$x^2$$"), ("show", None)])
        self.panel.reset_undo.assert_called_once_with()
        self.statusbar.set_progress.assert_called_with(-1)

    def test_result_classification_uses_formula_format_only_without_prose(self):
        for result, expected, mode in (("$$x^2$$\n", "$$x^2$$", 1), (r"$$\text{price \$5}$$", r"$$\text{price \$5}$$", 1), ("说明 $x^2$\n", "说明 $x^2$", 0), ("$$x$$\n\n$$y$$", "$$x$$\n\n$$y$$", 0), ("$", "$", 0)):
            with self.subTest(result=result):
                self.window.result_mode = 0
                self.window.events.put(("result", result, 1, None))
                self.window.poll()
                self.root.clipboard_append.assert_called_with(expected)
                self.assertEqual(self.window.result_mode, mode)
        self.panel.set_mode.assert_not_called()

    def test_capture_selection_does_not_start_conversion_progress(self):
        self.window.screenshot()
        self.assertTrue(self.window.interaction_active)
        self.statusbar.set_progress.assert_not_called()

    def test_formula_result_display_matches_selected_copy_format(self):
        self.window.result_mode = 1
        self.window.events.put(("result", "x^2\n", 1, None))
        self.window.poll()
        self.assertEqual(self.panel.get_result(), "$$x^2$$")
        self.root.clipboard_append.assert_called_with(self.panel.get_result())

    def test_changing_format_rewraps_edited_result_and_copy_matches_display(self):
        self.window.result_mode = 1
        self.panel.get_result.return_value = r"$$x + \text{price \$5}$$" + "\n"
        for index, expected in ((0, r"x + \text{price \$5}"), (1, r"$x + \text{price \$5}$"), (2, r"$$x + \text{price \$5}$$")):
            with self.subTest(index=index):
                self.window.events.put(index + 10)
                self.window.poll()
                self.assertEqual(self.panel.get_result(), expected)
                self.window.copy()
                self.assertEqual(self.panel.get_result(), expected)
                self.root.clipboard_append.assert_called_with(expected)
        self.panel.show.assert_not_called()

    def test_format_change_preserves_mixed_markdown(self):
        text = "中文 $x$\n\n$$y$$"
        self.panel.get_result.return_value = text
        self.window.events.put(10)
        self.window.poll()
        self.assertEqual(self.panel.get_result(), text)

    def test_empty_formula_does_not_copy_or_accumulate_delimiters(self):
        self.window.result_mode = 1
        for text in ("", "\n", "$$", "$$$$"):
            with self.subTest(text=text):
                self.panel.get_result.return_value = text
                self.assertFalse(self.window.copy())
                self.assertEqual(self.panel.get_result(), "")
        self.root.clipboard_clear.assert_not_called()

    def test_unknown_progress_does_not_reset_completed_stages(self):
        self.window.events.put(("progress", 0.5, "已完成检测", None))
        self.window.events.put(("progress", None, "正在识别公式…", None))
        self.window.poll()
        self.statusbar.set_progress.assert_called_once_with(0.5, "已完成检测")
        self.panel.set_status.assert_called_with("正在识别公式…")

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
        self.statusbar.set_progress.assert_called_once_with(-1)
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

    def test_shortcut_settings_release_keys_and_cancel_restores_saved_bindings(self):
        previous = list(self.window.hotkeys)
        self.window.open_shortcut_settings()
        self.assertTrue(self.window.shortcuts_active)
        self.assertEqual(self.window.hotkeys, [])
        self.panel.hide.assert_called_once_with(immediately=True)
        for key in previous:
            self.assertTrue(key.close.called)
        self.window.cancel_shortcut_settings()
        self.assertFalse(self.window.shortcuts_active)
        self.assertEqual(len(self.window.hotkeys), 2)
        self.statusbar.commit_shortcuts.assert_not_called()

    def test_reopening_shortcut_settings_preserves_the_active_draft(self):
        self.window.open_shortcut_settings()
        self.statusbar.reset_mock()
        self.panel.reset_mock()
        self.window.open_shortcut_settings()
        self.window.show()
        self.assertEqual(self.statusbar.show_shortcut_settings.call_count, 2)
        self.statusbar.get_shortcuts.assert_not_called()
        self.statusbar.commit_shortcuts.assert_not_called()
        self.panel.show.assert_not_called()
        self.assertTrue(self.window.shortcuts_active)
        self.assertEqual(self.window.hotkeys, [])

    def test_shortcut_registration_failure_keeps_saved_settings(self):
        self.window.open_shortcut_settings()
        candidate = [dict(key_code=0, modifiers=2304, label="⌥⌘A"), dict(key_code=1, modifiers=2304, label="⌥⌘S")]
        self.statusbar.get_shortcuts.side_effect = lambda draft=False: candidate if draft else self.statusbar.get_shortcuts.return_value
        partial = Mock()
        with patch("texo.desktop.GlobalHotkey", side_effect=[partial, RuntimeError("快捷键已占用")]):
            self.window.save_shortcut_settings()
        partial.close.assert_called_once_with()
        self.assertEqual(self.window.hotkeys, [])
        self.assertTrue(self.window.shortcuts_active)
        self.statusbar.commit_shortcuts.assert_not_called()
        self.statusbar.set_shortcut_error.assert_called_once_with("快捷键已占用")
        with patch("texo.desktop.GlobalHotkey", side_effect=[Mock(), Mock()]) as register:
            self.window.cancel_shortcut_settings()
            self.window.cancel_shortcut_settings()
        self.assertEqual(register.call_count, 2)
        self.assertEqual(len(self.window.hotkeys), 2)
        self.assertFalse(self.window.shortcuts_active)

    def test_failed_shortcut_commit_releases_candidates_and_cancel_recovers(self):
        self.window.open_shortcut_settings()
        self.statusbar.commit_shortcuts.return_value = False
        candidates = [Mock(), Mock()]
        with patch("texo.desktop.GlobalHotkey", side_effect=candidates):
            self.window.save_shortcut_settings()
        for key in candidates:
            key.close.assert_called_once_with()
        self.assertTrue(self.window.shortcuts_active)
        self.assertFalse(self.window.hotkeys)
        self.window.cancel_shortcut_settings()
        self.assertEqual(len(self.window.hotkeys), 2)

    def test_saved_shortcuts_update_caption_only_after_both_register(self):
        self.window.open_shortcut_settings()
        candidate = [dict(key_code=0, modifiers=2304, label="⌥⌘A"), dict(key_code=1, modifiers=2304, label="⌥⌘S")]
        self.statusbar.get_shortcuts.return_value = candidate
        self.window.save_shortcut_settings()
        self.statusbar.get_shortcuts.assert_called_with(draft=True)
        self.statusbar.commit_shortcuts.assert_called_once_with()
        self.panel.set_capture_shortcut.assert_called_with("⌥⌘A")
        self.assertFalse(self.window.shortcuts_active)

    def test_ppt_copy_uses_current_edited_text_and_native_rich_clipboard(self):
        self.panel.get_result.return_value = "中文 $x^2$"
        payload = dict(plain="中文 $x^2$", html="<p>中文 <math>x</math></p>")
        with patch("texo.office.make_office_payload", return_value=payload) as convert, patch("texo.desktop.Thread", side_effect=lambda target, daemon: SimpleNamespace(start=target)):
            self.window.copy_ppt()
            self.window.poll()
        convert.assert_called_once_with("中文 $x^2$", pure_latex=False)
        self.panel.copy_office.assert_called_once_with(payload)
        self.root.clipboard_clear.assert_not_called()
        self.assertFalse(self.window.busy)

    def test_failed_ppt_conversion_does_not_touch_clipboard(self):
        self.panel.get_result.return_value = "中文 $x^2$"
        with patch("texo.office.make_office_payload", side_effect=RuntimeError("无法转换公式")), patch("texo.desktop.Thread", side_effect=lambda target, daemon: SimpleNamespace(start=target)):
            self.window.copy_ppt()
            self.window.poll()
        self.panel.copy_office.assert_not_called()
        self.root.clipboard_clear.assert_not_called()
        self.assertFalse(self.window.busy)
        self.panel.set_status.assert_called_with("PPT 复制失败：无法转换公式")

    def test_native_ppt_write_failure_is_reported_without_claiming_preservation(self):
        self.panel.copy_office.return_value = False
        self.window.events.put(("office", {}, None, None))
        self.window.poll()
        self.panel.set_status.assert_called_with("PPT 复制失败：无法写入剪贴板，请重试。")
        self.root.after.assert_called_with(30, self.window.poll)

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
