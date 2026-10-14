import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from main import OCRWindow, ROOT


@unittest.skipUnless(os.environ.get("TEXO_TEST_GUI") == "1", "requires a macOS desktop session")
class DesktopTests(unittest.TestCase):
    def test_select_recognize_copy_and_error_recovery(self):
        import tkinter as tk
        from PIL import Image

        root = tk.Tk()
        window = OCRWindow(root, ROOT / "model")
        try:
            previous_clipboard = root.clipboard_get()
        except tk.TclError:
            previous_clipboard = None

        def choose_and_wait(path):
            with patch("tkinter.filedialog.askopenfilename", return_value=str(path)):
                window.select_button.invoke()
            deadline = time.monotonic() + 30
            while window.select_button.cget("state") == "disabled":
                root.update()
                if time.monotonic() > deadline:
                    self.fail("desktop OCR did not finish within 30 seconds")
                time.sleep(0.01)

        try:
            root.update()
            self.assertTrue(root.winfo_viewable())
            choose_and_wait(ROOT / "tests/fixtures/simple.png")
            latex = window.output.get("1.0", "end-1c")
            self.assertEqual("".join(latex.split()), "x^{2}+y^{2}=z^{2}")
            self.assertEqual(window.copy_button.cget("state"), "normal")
            window.copy_button.invoke()
            self.assertEqual(root.clipboard_get(), latex)
            window.output.insert("end", "\n")
            for label, delimiter in (("LaTeX", ""), ("$LaTeX$", "$"), ("$$LaTeX$$", "$$")):
                window.copy_format.set(label)
                window.copy_button.invoke()
                self.assertEqual(root.clipboard_get(), f"{delimiter}{latex}{delimiter}")
            with Image.open(ROOT / "tests/fixtures/simple.png") as fixture:
                with patch("PIL.ImageGrab.grabclipboard", return_value=fixture):
                    window.clipboard_button.invoke()
                    deadline = time.monotonic() + 30
                    while window.busy:
                        root.update()
                        if time.monotonic() > deadline:
                            self.fail("clipboard OCR did not finish")
                        time.sleep(0.01)
            self.assertEqual(window.output.get("1.0", "end-1c"), latex)
            from subprocess import CompletedProcess

            with patch("subprocess.run", return_value=CompletedProcess([], 1, b"", b"")):
                window.capture_button.invoke()
                deadline = time.monotonic() + 5
                while window.busy:
                    root.update()
                    if time.monotonic() > deadline:
                        self.fail("cancelled capture did not restore the window")
                    time.sleep(0.01)
            self.assertTrue(root.winfo_viewable())
            self.assertIn("已取消截图", window.status.get())
            self.assertEqual(window.output.get("1.0", "end-1c"), latex)
            choose_and_wait(ROOT / "tests/fixtures/does-not-exist.png")
            self.assertIn("无法打开图片", window.status.get())
            self.assertEqual(window.copy_button.cget("state"), "disabled")
            with tempfile.TemporaryDirectory() as directory:
                blank = Path(directory) / "blank.png"
                Image.new("RGB", (100, 40), "white").save(blank)
                choose_and_wait(blank)
                self.assertIn("空白", window.status.get())
            choose_and_wait(ROOT / "tests/fixtures/simple.png")
            self.assertIn("识别完成", window.status.get())
        finally:
            root.clipboard_clear()
            if previous_clipboard is not None:
                root.clipboard_append(previous_clipboard)
            root.destroy()


if __name__ == "__main__":
    unittest.main()
