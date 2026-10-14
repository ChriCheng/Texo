import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from texo import login


class LoginStartupTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.app = self.directory / "Texo.app"
        self.app.mkdir()
        self.agent = self.directory / "LaunchAgents" / f"{login.LABEL}.plist"
        setting = patch.object(login, "AGENT_PATH", self.agent)
        setting.start()
        self.addCleanup(setting.stop)
        environment = patch.dict(os.environ, {"TEXO_APP_BUNDLE": str(self.app)})
        environment.start()
        self.addCleanup(environment.stop)
        self.domain = f"gui/{os.getuid()}"
        self.target = f"{self.domain}/{login.LABEL}"

    def result(self, returncode=0, stderr=""):
        return subprocess.CompletedProcess([], returncode, "", stderr)

    def test_enable_writes_login_agent_and_bootstraps_without_keepalive(self):
        with patch("texo.login.subprocess.run", side_effect=[self.result(113), self.result()]) as run:
            login.set_login_enabled(True)
        self.assertTrue(login.login_enabled())
        data = plistlib.loads(self.agent.read_bytes())
        self.assertEqual(data["Label"], login.LABEL)
        self.assertEqual(data["ProgramArguments"], ["/usr/bin/open", "-g", str(self.app), "--args", "--background"])
        self.assertIs(data["RunAtLoad"], True)
        self.assertNotIn("KeepAlive", data)
        self.assertEqual([call.args[0] for call in run.call_args_list], [
            ["/bin/launchctl", "print", self.target],
            ["/bin/launchctl", "bootstrap", self.domain, str(self.agent)],
        ])

    def test_already_loaded_agent_is_not_bootstrapped_twice(self):
        with patch("texo.login.subprocess.run", return_value=self.result()) as run:
            login.set_login_enabled(True, self.app)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][1], "print")
        self.assertTrue(login.login_enabled(self.app))

    def test_disable_unloads_agent_and_removes_only_its_plist(self):
        with patch("texo.login.subprocess.run", side_effect=[self.result(113), self.result()]):
            login.set_login_enabled(True)
        with patch("texo.login.subprocess.run", side_effect=[self.result(), self.result()]) as run:
            login.set_login_enabled(False)
        self.assertFalse(login.login_enabled())
        self.assertFalse(self.agent.exists())
        self.assertEqual(run.call_args_list[-1].args[0], ["/bin/launchctl", "bootout", self.target])
        with patch("texo.login.subprocess.run") as run:
            login.set_login_enabled(False)
        run.assert_not_called()

    def test_failed_bootstrap_restores_existing_file_or_removes_new_file(self):
        for previous in (None, plistlib.dumps({
            "Label": login.LABEL,
            "ProgramArguments": ["/usr/bin/open", "-g", str(self.app), "--args", "--background"],
            "RunAtLoad": False,
        })):
            with self.subTest(previous=previous):
                self.agent.parent.mkdir(exist_ok=True)
                if previous is not None:
                    self.agent.write_bytes(previous)
                with patch("texo.login.subprocess.run", side_effect=[self.result(113), self.result(5, "bootstrap denied")]):
                    with self.assertRaisesRegex(RuntimeError, "bootstrap denied"):
                        login.set_login_enabled(True)
                self.assertFalse(login.login_enabled())
                if previous is None:
                    self.assertFalse(self.agent.exists())
                else:
                    self.assertEqual(self.agent.read_bytes(), previous)
                self.assertEqual(list(self.agent.parent.glob(".*.tmp")), [])

    def test_failed_bootout_preserves_enabled_setting(self):
        with patch("texo.login.subprocess.run", side_effect=[self.result(113), self.result()]):
            login.set_login_enabled(True)
        previous = self.agent.read_bytes()
        with patch("texo.login.subprocess.run", side_effect=[self.result(), self.result(5, "bootout denied")]):
            with self.assertRaisesRegex(RuntimeError, "bootout denied"):
                login.set_login_enabled(False)
        self.assertEqual(self.agent.read_bytes(), previous)
        self.assertTrue(login.login_enabled())

    def test_disable_unloaded_agent_removes_next_login_setting_without_bootout(self):
        with patch("texo.login.subprocess.run", side_effect=[self.result(113), self.result()]):
            login.set_login_enabled(True)
        with patch("texo.login.subprocess.run", return_value=self.result(113)) as run:
            login.set_login_enabled(False)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][1], "print")
        self.assertFalse(self.agent.exists())

    def test_bootstrap_timeout_removes_new_setting(self):
        with patch("texo.login.subprocess.run", side_effect=[self.result(113), subprocess.TimeoutExpired("launchctl", 10)]):
            with self.assertRaisesRegex(RuntimeError, "启动项"):
                login.set_login_enabled(True)
        self.assertFalse(self.agent.exists())

    def test_unrelated_malformed_and_symlink_plists_are_untouched(self):
        self.agent.parent.mkdir()
        for content in (b"not a plist", plistlib.dumps({"Label": "another.app"}), plistlib.dumps({
            "Label": login.LABEL, "ProgramArguments": ["/usr/bin/open", "/Applications/Other.app"],
        })):
            with self.subTest(content=content):
                self.agent.write_bytes(content)
                for enabled in (False, True):
                    with patch("texo.login.subprocess.run") as run:
                        with self.assertRaisesRegex(RuntimeError, "启动项"):
                            login.set_login_enabled(enabled)
                    run.assert_not_called()
                    self.assertEqual(self.agent.read_bytes(), content)
                with self.assertRaisesRegex(RuntimeError, "启动项"):
                    login.login_enabled()
        self.agent.unlink()
        destination = self.directory / "untouched.plist"
        destination.write_bytes(b"untouched")
        self.agent.symlink_to(destination)
        with self.assertRaisesRegex(RuntimeError, "启动项"):
            login.set_login_enabled(False)
        self.assertTrue(self.agent.is_symlink())
        self.assertEqual(destination.read_bytes(), b"untouched")

    def test_missing_application_does_not_write_login_agent(self):
        with patch("texo.login.subprocess.run") as run:
            with self.assertRaisesRegex(RuntimeError, "Texo.app"):
                login.set_login_enabled(True, self.directory / "Missing.app")
        run.assert_not_called()
        self.assertFalse(self.agent.exists())


if __name__ == "__main__":
    unittest.main()
