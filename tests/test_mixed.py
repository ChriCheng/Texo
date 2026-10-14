import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from PIL import Image

from main import ROOT, recognize


class MixedLayoutTests(unittest.TestCase):
    def test_formula_is_inserted_between_text_in_one_vision_line(self):
        from texo.mixed import recognize_mixed

        text = [{"text": "前 后", "box": [10, 10, 320, 30], "chars": [
            {"text": "前", "box": [10, 10, 30, 30]},
            {"text": " ", "box": [0, 0, 0, 0]},
            {"text": "后", "box": [300, 10, 320, 30]},
        ]}]
        formulas = [{"type": "embedding", "box": [100, 5, 200, 35]}]
        with patch("texo.mixed.detect_formulas", return_value=formulas), patch("texo.mixed.recognize_text", return_value=text):
            self.assertEqual(recognize_mixed(Image.new("RGB", (400, 50), "white"), lambda crop: "x_1"), "前 $x_1$ 后")

    def test_display_formula_keeps_its_place_and_no_result_is_reported(self):
        from texo.mixed import recognize_mixed

        text = [{"text": "之后", "box": [0, 100, 40, 120]}, {"text": "之前", "box": [0, 0, 40, 20]}]
        formulas = [{"type": "isolated", "box": [60, 40, 180, 80]}]
        with patch("texo.mixed.detect_formulas", return_value=formulas), patch("texo.mixed.recognize_text", return_value=text):
            self.assertEqual(recognize_mixed(Image.new("RGB", (200, 140), "white"), lambda crop: "x^2"), "之前\n\n$$x^2$$\n\n之后")
        with patch("texo.mixed.detect_formulas", return_value=[]), patch("texo.mixed.recognize_text", return_value=[]):
            with self.assertRaisesRegex(ValueError, "未识别出文字或公式"):
                recognize_mixed(Image.new("RGB", (200, 140), "white"), lambda crop: "")

    def test_unpositioned_characters_are_reported_instead_of_lost(self):
        from texo.mixed import recognize_mixed

        formula = [{"type": "embedding", "box": [100, 5, 200, 35]}]
        chars = [{"text": "前", "box": [10, 10, 30, 30]}, {"text": "后", "box": [300, 10, 320, 30]}]
        for candidate in (chars, [chars[0], {"text": "！", "box": [0, 0, 0, 0]}, chars[1]]):
            text = [{"text": "前！后", "box": [10, 10, 320, 30], "chars": candidate}]
            with self.subTest(chars=candidate), patch("texo.mixed.detect_formulas", return_value=formula), patch("texo.mixed.recognize_text", return_value=text):
                with self.assertRaisesRegex(ValueError, "无法定位部分文字"):
                    recognize_mixed(Image.new("RGB", (400, 50), "white"), lambda crop: "x_1")

    def test_tall_inline_formula_joins_the_nearest_text_row(self):
        from texo.mixed import recognize_mixed

        lines = [
            {"text": "上一行", "box": [0, 0, 300, 20]},
            {"text": "公式前", "box": [0, 25, 100, 45]},
            {"text": "公式后", "box": [250, 25, 320, 45]},
        ]
        formulas = [{"type": "embedding", "box": [110, 8, 240, 50]}]
        with patch("texo.mixed.detect_formulas", return_value=formulas), patch("texo.mixed.recognize_text", return_value=lines):
            result = recognize_mixed(Image.new("RGB", (400, 60), "white"), lambda crop: r"\frac{a}{b}")
            self.assertEqual(result, "上一行\n公式前 $\\frac{a}{b}$ 公式后")


@unittest.skipUnless(os.environ.get("TEXO_TEST_GUI") == "1" and (ROOT / "model/model.safetensors").is_file(), "requires local models and native macOS OCR")
class MixedRecognitionTests(unittest.TestCase):
    def test_real_chinese_inline_and_display_math_in_reading_order(self):
        result = recognize(ROOT / "tests/fixtures/mixed.png", mode="mixed")
        compact = "".join(result.split())
        self.assertEqual(compact, "若模型输出满足$x^{2}+y^{2}=z^{2}$则说明识别完成。下面是独立公式：$$x^{2}+y^{2}=z^{2}$$中文识别与公式识别均在本机完成。")
        self.assertFalse(result.endswith("\n"))

    def test_mixed_cli_outputs_chinese_without_a_trailing_newline(self):
        result = subprocess.run([sys.executable, str(ROOT / "main.py"), "--mode", "mixed", str(ROOT / "tests/fixtures/chinese.png")], capture_output=True, check=True, timeout=240)
        self.assertIn("中文识别测试", result.stdout.decode())
        self.assertFalse(result.stdout.endswith(b"\n"))


if __name__ == "__main__":
    unittest.main()
