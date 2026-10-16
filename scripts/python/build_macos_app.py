"""Build a small macOS app that uses this checkout's existing Python and models."""

import argparse
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import sysconfig
import tempfile


ROOT = Path(__file__).resolve().parents[2]
BUNDLE_ID = "com.chricheng.texo"


def build(output):
    if sys.platform != "darwin":
        raise RuntimeError("应用封装目前仅支持 macOS。")
    if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        raise RuntimeError("请在项目目录运行 .venv/bin/python scripts/python/build_macos_app.py")
    include = Path(sysconfig.get_path("include"))
    library = Path(sysconfig.get_config_var("LIBDIR") or "")
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    for path in (include / "Python.h", library / f"libpython{python_version}.dylib"):
        if not path.is_file():
            raise RuntimeError(f"缺少本机 Python 开发运行库：{path}。请使用包含开发文件的 Python 重建 .venv。")
    if not (ROOT / "model/model.safetensors").is_file():
        raise RuntimeError("公式模型未下载，请先运行 .venv/bin/python scripts/python/hf_hub.py pull --mixed")
    source, statusbar, popover, icon = ROOT / "scripts/macos/launcher.m", ROOT / "scripts/macos/statusbar.m", ROOT / "scripts/macos/popover.m", ROOT / "assets/Texo.icns"
    shortcuts, clipboard = ROOT / "scripts/macos/shortcuts.m", ROOT / "scripts/macos/clipboard.m"
    for path in (source, statusbar, popover, shortcuts, clipboard, icon, ROOT / "assets/svg/status-icon.svg"):
        if not path.is_file():
            raise RuntimeError(f"应用封装文件缺失：{path}。请更新项目后重试。")

    output = Path(output).expanduser().absolute()
    if output.suffix != ".app" or output.is_symlink():
        raise RuntimeError("输出路径必须是以 .app 结尾的普通应用目录。")
    if output.exists():
        try:
            with (output / "Contents/Info.plist").open("rb") as handle:
                previous = plistlib.load(handle)
            same_app = isinstance(previous, dict) and previous.get("CFBundleIdentifier") == BUNDLE_ID and previous.get("TexoProjectRoot") == str(ROOT)
        except (OSError, ValueError):
            same_app = False
        if not same_app:
            raise RuntimeError(f"拒绝覆盖其他应用或项目：{output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="texo-app-", dir=output.parent) as directory:
        staged = Path(directory) / "Texo.app"
        executable = staged / "Contents/MacOS/Texo"
        executable.parent.mkdir(parents=True)
        resources = staged / "Contents/Resources"
        resources.mkdir()
        shutil.copy2(icon, resources / "Texo.icns")
        info = {
            "CFBundleInfoDictionaryVersion": "6.0",
            "CFBundleIdentifier": BUNDLE_ID,
            "CFBundleName": "Texo",
            "CFBundleDisplayName": "Texo",
            "CFBundleExecutable": "Texo",
            "CFBundlePackageType": "APPL",
            "CFBundleIconFile": "Texo.icns",
            "CFBundleShortVersionString": "1.1",
            "CFBundleVersion": "2",
            "LSMinimumSystemVersion": "13.0",
            "LSMultipleInstancesProhibited": True,
            "LSUIElement": True,
            "NSHighResolutionCapable": True,
            "NSScreenCaptureUsageDescription": "Texo 仅在你主动截图识别时读取所选屏幕区域。",
            "TexoProjectRoot": str(ROOT),
        }
        with (staged / "Contents/Info.plist").open("wb") as handle:
            plistlib.dump(info, handle)
        commands = (
            ["/usr/bin/xcrun", "clang", str(source), str(statusbar), str(popover), str(shortcuts), str(clipboard), "-O2", "-fobjc-arc", "-mmacosx-version-min=13.0", f"-I{include}", f"-L{library}", f"-lpython{python_version}", f"-Wl,-rpath,{library}", "-Wl,-export_dynamic", "-framework", "Foundation", "-framework", "AppKit", "-o", str(executable)],
            ["/usr/bin/codesign", "--force", "--sign", "-", "--identifier", BUNDLE_ID, str(staged)],
        )
        for command in commands:
            try:
                subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
            except FileNotFoundError as error:
                raise RuntimeError("缺少 Apple 命令行工具，请运行 xcode-select --install 后重试。") from error
            except subprocess.TimeoutExpired as error:
                raise RuntimeError("构建应用超时，请稍后重试。") from error
            except subprocess.CalledProcessError as error:
                raise RuntimeError(f"构建应用失败：{(error.stderr or str(error)).strip()[-1200:]}") from error

        backup = output.parent / f".{output.name}.{Path(directory).name}.backup"
        if output.exists():
            output.rename(backup)
        try:
            staged.rename(output)
        except OSError:
            if backup.exists():
                backup.rename(output)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".local/Texo.app")
    args = parser.parse_args()
    try:
        output = build(args.output)
    except (OSError, RuntimeError) as error:
        parser.exit(1, f"Texo: {error}\n")
    print(f"已构建 {output}")


if __name__ == "__main__":
    main()
