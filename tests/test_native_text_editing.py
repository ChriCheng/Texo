from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == "darwin", "requires AppKit")
class NativeTextEditingTests(unittest.TestCase):
    def test_offscreen_editor_commands_and_undo(self):
        source = Path(__file__).with_name("native_text_editing.m")
        with tempfile.TemporaryDirectory(prefix="texo-editing-") as directory:
            executable = Path(directory) / "text-editing"
            build = subprocess.run([
                "/usr/bin/xcrun", "clang", str(source), "-fobjc-arc", "-mmacosx-version-min=13.0",
                "-Wl,-export_dynamic", "-framework", "AppKit", "-o", str(executable),
            ], capture_output=True, text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
