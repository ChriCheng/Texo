from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.python import build_macos_app as app


class AppBundleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "Texo project"
        self.include = self.root / "runtime/include"
        self.library = self.root / "runtime/lib"
        for path in (
            self.include / "Python.h",
            self.library / f"libpython{sys.version_info.major}.{sys.version_info.minor}.dylib",
            self.root / "model/model.safetensors",
            self.root / "scripts/macos/launcher.m",
            self.root / "scripts/macos/statusbar.m",
            self.root / "scripts/macos/popover.m",
            self.root / "scripts/macos/shortcuts.m",
            self.root / "scripts/macos/clipboard.m",
            self.root / "assets/Texo.icns",
            self.root / "assets/svg/status-icon.svg",
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture")
        for target, value in (
            ("ROOT", self.root),
            ("sys.platform", "darwin"),
            ("sys.prefix", str(self.root / ".venv")),
        ):
            mocked = patch(f"scripts.python.build_macos_app.{target}", value)
            mocked.start()
            self.addCleanup(mocked.stop)
        for name, value in (("get_path", str(self.include)), ("get_config_var", str(self.library))):
            mocked = patch(f"scripts.python.build_macos_app.sysconfig.{name}", return_value=value)
            mocked.start()
            self.addCleanup(mocked.stop)
        self.output = self.root / "Texo.app"

    def compile_success(self, command, **kwargs):
        if "-o" in command:
            Path(command[command.index("-o") + 1]).write_bytes(b"native launcher")
        return subprocess.CompletedProcess(command, 0, "", "")

    def test_bundle_uses_current_runtime_without_copying_models(self):
        with patch.object(app.subprocess, "run", side_effect=self.compile_success):
            app.build(self.output)
            app.build(self.output)
        with (self.output / "Contents/Info.plist").open("rb") as handle:
            info = plistlib.load(handle)
        self.assertEqual(info["TexoProjectRoot"], str(self.root))
        self.assertEqual(info["CFBundleIdentifier"], "com.chricheng.texo")
        self.assertTrue(info["LSMultipleInstancesProhibited"])
        self.assertTrue(info["LSUIElement"])
        self.assertEqual(info["LSMinimumSystemVersion"], "13.0")
        self.assertEqual({str(path.relative_to(self.output)) for path in self.output.rglob("*") if path.is_file()}, {
            "Contents/Info.plist", "Contents/MacOS/Texo", "Contents/Resources/Texo.icns",
        })

    def test_missing_runtime_has_actionable_error(self):
        with patch.object(app.sys, "prefix", str(self.root / "other-env")):
            with self.assertRaisesRegex(RuntimeError, r"\.venv/bin/python"):
                app.build(self.output)
        (self.include / "Python.h").unlink()
        with self.assertRaisesRegex(RuntimeError, "Python.h"):
            app.build(self.output)
        self.assertFalse(self.output.exists())

    def test_existing_unrelated_app_is_never_overwritten(self):
        self.output.mkdir(parents=True)
        marker = self.output / "keep.txt"
        marker.write_text("keep")
        with self.assertRaisesRegex(RuntimeError, "拒绝覆盖"):
            app.build(self.output)
        self.assertEqual(marker.read_text(), "keep")
        (self.output / "Contents").mkdir()
        with (self.output / "Contents/Info.plist").open("wb") as handle:
            plistlib.dump(["invalid app metadata"], handle)
        with self.assertRaisesRegex(RuntimeError, "拒绝覆盖"):
            app.build(self.output)
        self.assertEqual(marker.read_text(), "keep")

    def test_compile_failure_preserves_previous_app(self):
        with patch.object(app.subprocess, "run", side_effect=self.compile_success):
            app.build(self.output)
        marker = self.output / "previous.txt"
        marker.write_text("previous")
        failure = subprocess.CalledProcessError(1, "clang", stderr="compiler failure")
        with patch.object(app.subprocess, "run", side_effect=failure):
            with self.assertRaisesRegex(RuntimeError, "compiler failure"):
                app.build(self.output)
        self.assertEqual(marker.read_text(), "previous")

    def test_failed_swap_restores_previous_app(self):
        with patch.object(app.subprocess, "run", side_effect=self.compile_success):
            app.build(self.output)
        marker = self.output / "previous.txt"
        marker.write_text("previous")
        rename = Path.rename

        def fail_new_app(path, target):
            if path.name == "Texo.app" and path.parent.name.startswith("texo-app-"):
                raise OSError("swap failed")
            return rename(path, target)

        with patch.object(app.subprocess, "run", side_effect=self.compile_success), patch.object(Path, "rename", fail_new_app):
            with self.assertRaisesRegex(OSError, "swap failed"):
                app.build(self.output)
        self.assertEqual(marker.read_text(), "previous")


if __name__ == "__main__":
    unittest.main()
