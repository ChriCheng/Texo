from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from main import ROOT
from texo.desktop import NativeOCRWindow


class NativeDesktopTests(unittest.TestCase):
    def setUp(self):
        self.root, self.panel, self.statusbar = Mock(), Mock(), Mock()
        for name, result in (("NativePopover", self.panel), ("StatusBar", self.statusbar), ("GlobalHotkey", Mock()), ("login_enabled", False)):
            patched = patch(f"texo.desktop.{name}", return_value=result)
            patched.start()
            self.addCleanup(patched.stop)
        self.window = NativeOCRWindow(self.root, ROOT / "model", Mock(), Mock())

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


if __name__ == "__main__":
    unittest.main()
