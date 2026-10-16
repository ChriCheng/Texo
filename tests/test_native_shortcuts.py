from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == "darwin", "requires AppKit and Apple command line tools")
class NativeShortcutTests(unittest.TestCase):
    def test_native_shortcut_validation_without_ui_or_preferences(self):
        source = Path(__file__).with_name("native_shortcuts.m")
        with tempfile.TemporaryDirectory(prefix="texo-shortcuts-") as directory:
            executable = Path(directory) / "shortcuts"
            build = subprocess.run([
                "/usr/bin/xcrun", "clang", str(source), "-fobjc-arc", "-mmacosx-version-min=13.0",
                "-Wall", "-Wextra", "-Werror", "-framework", "AppKit", "-o", str(executable),
            ], capture_output=True, text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
