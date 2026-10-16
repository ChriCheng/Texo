import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from texo.chinese import _native_helper, _pixel_box, recognize_text


class ChineseBoundaryTests(unittest.TestCase):
    def test_coordinates_flip_y_axis_and_clamp_to_image(self):
        self.assertEqual(_pixel_box([0.1, 0.2, 0.3, 0.4], (100, 200)), [10, 80, 40, 160])
        self.assertEqual(_pixel_box([-0.1, -0.1, 1.2, 1.2], (100, 200)), [0, 0, 100, 200])
        with self.assertRaises(ValueError):
            _pixel_box([0, float("nan"), 1, 1], (100, 200))

    def test_unsupported_platform_has_actionable_error(self):
        with patch("texo.chinese.sys.platform", "linux"):
            with self.assertRaisesRegex(RuntimeError, "macOS 13"):
                recognize_text(Image.new("RGB", (10, 10)))

    def test_native_errors_and_invalid_output_are_reported(self):
        image = Image.new("RGB", (10, 10), "white")
        outcomes = [
            (subprocess.TimeoutExpired("vision", 30), "超时"),
            (FileNotFoundError(), "无法启动"),
            (subprocess.CompletedProcess([], 1, "", "Vision error"), "Vision error"),
            (subprocess.CompletedProcess([], 0, "not json", ""), "无效结果"),
            (subprocess.CompletedProcess([], 0, '[{"text":"文字","box":[0,0,1]}]', ""), "无效结果"),
        ]
        for outcome, message in outcomes:
            with self.subTest(message=message), patch("texo.chinese._native_helper", return_value=Path("vision")), patch("texo.chinese.sys.platform", "darwin"):
                kwargs = {"side_effect": outcome} if isinstance(outcome, Exception) else {"return_value": outcome}
                with patch("texo.chinese.subprocess.run", **kwargs):
                    with self.assertRaisesRegex(RuntimeError, message):
                        recognize_text(image)

    def test_compilation_failure_has_actionable_error(self):
        for outcome, message in (
            (FileNotFoundError(), "xcode-select --install"),
            (subprocess.TimeoutExpired("swiftc", 240), "准备中文识别工具超时"),
            (subprocess.CompletedProcess([], 1, "", "compiler failure"), "compiler failure"),
        ):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory, patch("texo.chinese.ROOT", Path(directory)):
                kwargs = {"side_effect": outcome} if isinstance(outcome, Exception) else {"return_value": outcome}
                with patch("texo.chinese.subprocess.run", **kwargs):
                    with self.assertRaisesRegex(RuntimeError, message):
                        _native_helper()


@unittest.skipUnless(sys.platform == "darwin" and os.environ.get("TEXO_TEST_GUI") == "1", "requires native macOS Vision outside the command sandbox")
class NativeChineseTests(unittest.TestCase):
    def test_real_chinese_english_numbers_and_character_boxes(self):
        with Image.open(Path(__file__).with_name("fixtures") / "chinese.png") as image:
            lines = recognize_text(image)
            size = image.size
        expected = [
            "中文识别测试：这是一个离线文字识别工具。",
            "请核对公式中的上下标、箭头和粗体。",
            "Privacy 与效用：准确率 98.5%，损失为 0.125。",
        ]
        self.assertEqual([line["text"] for line in lines], expected)
        for line in lines:
            self.assertEqual("".join(char["text"] for char in line["chars"]), line["text"])
            for character in line["chars"]:
                left, top, right, bottom = character["box"]
                self.assertTrue(0 <= left <= right <= size[0])
                self.assertTrue(0 <= top <= bottom <= size[1])
                if not character["text"].isspace():
                    self.assertGreater(right, left)
                    self.assertGreater(bottom, top)
            visible = [char for char in line["chars"] if not char["text"].isspace()]
            self.assertLess(visible[0]["box"][0], visible[-1]["box"][0])


if __name__ == "__main__":
    unittest.main()
