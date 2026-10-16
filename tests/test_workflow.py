from pathlib import Path
import subprocess
import sys
import unittest

from main import ROOT, format_result


class CopyFormatTests(unittest.TestCase):
    def test_three_copy_formats_have_no_trailing_newline(self):
        for delimiter, expected in (("", "x^2"), ("$", "$x^2$"), ("$$", "$$x^2$$")):
            with self.subTest(delimiter=delimiter):
                self.assertEqual(format_result("x^2\n", delimiter), expected)

    @unittest.skipUnless((ROOT / "model/model.safetensors").is_file(), "download model first")
    def test_cli_output_has_no_trailing_newline(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "main.py"), str(ROOT / "tests/fixtures/simple.png")],
            capture_output=True, check=True,
        )
        self.assertFalse(result.stdout.endswith(b"\n"))


if __name__ == "__main__":
    unittest.main()
