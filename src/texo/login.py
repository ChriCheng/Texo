"""Per-user login startup through LaunchServices, without a resident helper."""

import os
from pathlib import Path
import plistlib
import subprocess
import tempfile

LABEL = "com.chricheng.texo.login"
AGENT_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _app_path(app_path):
    return Path(app_path if app_path is not None else os.environ.get("TEXO_APP_BUNDLE") or "/Applications/Texo.app").expanduser().absolute()


def _arguments(app_path):
    return ["/usr/bin/open", "-g", str(app_path), "--args", "--background"]


def _existing(app_path):
    if AGENT_PATH.is_symlink():
        raise RuntimeError(f"启动项是符号链接，未作修改：{AGENT_PATH}")
    if not AGENT_PATH.exists():
        return None, None
    try:
        content = AGENT_PATH.read_bytes()
        data = plistlib.loads(content)
    except (OSError, ValueError, TypeError) as error:
        raise RuntimeError(f"无法读取已有启动项，未作修改：{AGENT_PATH}") from error
    if not isinstance(data, dict) or data.get("Label") != LABEL or data.get("ProgramArguments") != _arguments(app_path):
        raise RuntimeError(f"已有启动项不属于此 Texo 应用，未作修改：{AGENT_PATH}")
    return content, data


def _write(content):
    AGENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=AGENT_PATH.parent, prefix=f".{LABEL}.", suffix=".tmp", delete=False) as file:
        temporary = Path(file.name)
        try:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
            os.replace(temporary, AGENT_PATH)
        finally:
            temporary.unlink(missing_ok=True)


def _launchctl(*arguments):
    try:
        return subprocess.run(["/bin/launchctl", *arguments], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"无法更新 Texo 登录启动项：{error}") from error


def _check(result):
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or str(result.returncode)
        raise RuntimeError(f"无法更新 Texo 登录启动项：{detail}")


def login_enabled(app_path=None):
    """Return whether this app's persistent login entry is enabled."""
    _, data = _existing(_app_path(app_path))
    return data is not None and data.get("RunAtLoad") is True


def set_login_enabled(enabled, app_path=None):
    """Update only Texo's own entry; changing this never terminates Texo."""
    app_path = _app_path(app_path)
    previous, _ = _existing(app_path)
    if enabled and (app_path.suffix != ".app" or not app_path.is_dir()):
        raise RuntimeError(f"找不到 Texo.app，请先安装应用：{app_path}")
    if not enabled and previous is None:
        return
    domain = f"gui/{os.getuid()}"
    target = f"{domain}/{LABEL}"
    loaded = _launchctl("print", target).returncode == 0
    if enabled:
        _write(plistlib.dumps({"Label": LABEL, "ProgramArguments": _arguments(app_path), "RunAtLoad": True}))
        if not loaded:
            try:
                _check(_launchctl("bootstrap", domain, str(AGENT_PATH)))
            except Exception:
                if previous is None:
                    AGENT_PATH.unlink()
                else:
                    _write(previous)
                raise
    else:
        if loaded:
            _check(_launchctl("bootout", target))
        AGENT_PATH.unlink()
