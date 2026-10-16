from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == "darwin", "requires AppKit")
class NativeOfficeClipboardTests(unittest.TestCase):
    def test_private_pasteboard_content_and_failure_preservation(self):
        with tempfile.TemporaryDirectory(prefix="texo-office-") as directory:
            executable = Path(directory) / "clipboard"
            build = subprocess.run(["/usr/bin/xcrun", "clang", str(Path(__file__).with_name("native_clipboard.m")),
                                    "-fobjc-arc", "-framework", "AppKit", "-o", str(executable)],
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
