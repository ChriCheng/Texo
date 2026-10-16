import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name("vision.swift")


def _native_helper():
    directory = ROOT / ".local" / "bin"
    binary = directory / "texo-vision"
    if binary.is_file() and binary.stat().st_mtime_ns >= SOURCE.stat().st_mtime_ns:
        return binary
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="vision-build-", dir=directory) as build:
        temporary = Path(build) / "texo-vision"
        try:
            result = subprocess.run(
                ["/usr/bin/xcrun", "swiftc", str(SOURCE), "-module-cache-path", str(ROOT / ".local" / "swift-cache"), "-o", str(temporary)],
                capture_output=True, text=True, timeout=240,
            )
        except FileNotFoundError as error:
            raise RuntimeError("中文识别需要 Apple 命令行工具，请运行 xcode-select --install 后重试。") from error
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("首次准备中文识别工具超时，请稍后重试。") from error
        if result.returncode:
            raise RuntimeError(f"无法准备中文识别工具，请检查 Apple 命令行工具：{result.stderr.strip()[-1200:]}")
        os.replace(temporary, binary)
    return binary


def _pixel_box(box, size):
    if len(box) != 4 or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in box):
        raise ValueError("无效的文字坐标")
    x, y, width, height = box
    if width < 0 or height < 0:
        raise ValueError("无效的文字坐标")
    image_width, image_height = size
    values = (x * image_width, (1 - y - height) * image_height, (x + width) * image_width, (1 - y) * image_height)
    return [max(0, min(limit, round(value))) for value, limit in zip(values, (image_width, image_height, image_width, image_height))]


def recognize_text(image):
    """Return Vision lines and source-ordered character boxes in PIL pixel coordinates."""
    if sys.platform != "darwin":
        raise RuntimeError("中文识别目前仅支持 macOS 13 或更新版本。")
    binary = _native_helper()
    with tempfile.TemporaryDirectory(prefix="texo-text-") as directory:
        path = Path(directory) / "image.png"
        image.save(path, "PNG")
        try:
            result = subprocess.run([str(binary), str(path)], capture_output=True, text=True, timeout=30)
        except (FileNotFoundError, PermissionError) as error:
            raise RuntimeError("无法启动中文识别工具，请重启 Texo 后重试。") from error
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("中文识别超时，请裁剪成更小的图片后重试。") from error
    if result.returncode:
        raise RuntimeError(f"中文识别失败：{result.stderr.strip()[-1200:] or 'Vision 无法读取图片，请重启 Texo 后重试。'}")
    try:
        lines = json.loads(result.stdout)
        if not isinstance(lines, list):
            raise ValueError("无效的识别结果")
        for line in lines:
            if not isinstance(line["text"], str):
                raise ValueError("无效的识别文字")
            line["box"] = _pixel_box(line["box"], image.size)
            for character in line["chars"]:
                if not isinstance(character["text"], str):
                    raise ValueError("无效的识别文字")
                character["box"] = _pixel_box(character["box"], image.size)
        return lines
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeError("中文识别返回了无效结果，请重试。") from error
