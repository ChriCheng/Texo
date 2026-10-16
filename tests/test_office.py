from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from texo.office import make_office_payload


def math_nodes(payload):
    return [ET.fromstring(source) for source in re.findall(r"<math\b.*?</math>", payload["html"], re.DOTALL)]


class TextContent(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.tags = []

    def handle_data(self, data):
        self.text.append(data)

    def handle_starttag(self, tag, attributes):
        self.tags.append((tag, dict(attributes)))


class OfficePayloadTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("pandoc"), "requires the local Pandoc converter")
    def test_mixed_chinese_math_and_lines_are_rich_content_in_order(self):
        source = "若满足 $x^2+\\frac{1}{2}=y$，则继续。\n第二行。\n\n$$\\theta_{i+1} \\leftarrow \\theta_i-\\eta$$\n末行。\n"
        payload = make_office_payload(source)
        self.assertEqual(payload["plain"], source.rstrip())
        self.assertEqual(len(math_nodes(payload)), 2)
        self.assertIn('<math display="inline"', payload["html"])
        self.assertIn('<math display="block"', payload["html"])
        self.assertIn("<mfrac>", payload["html"])
        self.assertIn("<br", payload["html"])
        for first, second in (("若满足", "<math"), ("</math>", "，则继续。"), ("第二行。", "display=\"block\""), ("display=\"block\"", "末行。")):
            self.assertLess(payload["html"].index(first), payload["html"].index(second))

    @unittest.skipUnless(shutil.which("pandoc"), "requires the local Pandoc converter")
    def test_all_four_math_delimiters_and_pure_latex_are_converted(self):
        for source in (r"$x^2$", r"$$x^2$$", r"\(x^2\)", r"\[x^2\]"):
            with self.subTest(source=source):
                payload = make_office_payload(source)
                math = math_nodes(payload)[0]
                self.assertEqual(math.tag, "{http://www.w3.org/1998/Math/MathML}math")
                self.assertIsNotNone(math.find(".//{http://www.w3.org/1998/Math/MathML}msup"))
        pure = make_office_payload(r"\frac{a}{b}", pure_latex=True)
        self.assertEqual(pure["plain"], r"\frac{a}{b}")
        self.assertIn("<mfrac>", pure["html"])

    @unittest.skipUnless(shutil.which("pandoc"), "requires the local Pandoc converter")
    def test_pure_formula_accepts_current_copy_wrappers_without_double_wrapping(self):
        formula = r"\frac{a}{b}+\text{cost \$5}"
        for source in (formula, f"${formula}$", f"$${formula}$$", rf"\({formula}\)", rf"\[{formula}\]"):
            with self.subTest(source=source):
                payload = make_office_payload(source, pure_latex=True)
                math = math_nodes(payload)[0]
                self.assertEqual(len(math.findall(".//{http://www.w3.org/1998/Math/MathML}mfrac")), 1)
                self.assertEqual(math.find(".//{http://www.w3.org/1998/Math/MathML}annotation").text.strip(), formula)

    @unittest.skipUnless(shutil.which("pandoc"), "requires the local Pandoc converter")
    def test_raw_html_and_remote_resources_are_not_executable_or_fetchable(self):
        source = '<script>alert(1)</script>\n![远程图](https://example.com/a.png)\n[链接](https://example.com/) $x$'
        payload = make_office_payload(source)
        parser = TextContent()
        parser.feed(payload["html"])
        self.assertFalse(any(tag in {"script", "img", "iframe", "object", "embed"} for tag, attrs in parser.tags))
        self.assertFalse(any("src" in attrs or "href" in attrs for tag, attrs in parser.tags))
        self.assertIn("<script>alert(1)</script>", "".join(parser.text))
        self.assertIn("远程图", "".join(parser.text))

    @unittest.skipUnless(shutil.which("pandoc"), "requires the local Pandoc converter")
    def test_unsupported_formula_fails_instead_of_copying_unrendered_source(self):
        with self.assertRaisesRegex(RuntimeError, "公式|转换"):
            make_office_payload(r"前文 $\thiscommanddoesnotexist{x}$ 后文")

    @unittest.skipUnless(shutil.which("pandoc"), "requires the local Pandoc converter")
    def test_unconverted_math_fails_but_prose_and_currency_remain_valid(self):
        for source in (r"若满足 $ x^2+\frac{1}{2} $ 则继续。", r"若满足 $x^2+\frac{1}{2} 则继续。", "目标 $x_i=1"):
            with self.subTest(source=source):
                with self.assertRaisesRegex(RuntimeError, "公式.*剪贴板未修改"):
                    make_office_payload(source)
        for source in ("纯中文正文。\n第二行。", "价格 $100", r"价格 \$100"):
            with self.subTest(source=source):
                payload = make_office_payload(source)
                self.assertEqual(payload["plain"], source)
                self.assertEqual(math_nodes(payload), [])
                self.assertEqual(set(payload), {"plain", "html"})

    def test_blank_input_and_converter_failure_report_errors_before_returning_payload(self):
        with self.assertRaisesRegex(ValueError, "为空"):
            make_office_payload(" \n")
        with patch("texo.office.subprocess.run", side_effect=subprocess.TimeoutExpired("pandoc", 20)):
            with self.assertRaisesRegex(RuntimeError, "超时"):
                make_office_payload("中文 $x$")

    def test_finder_launch_resolves_homebrew_without_shell_path(self):
        converted = subprocess.CompletedProcess([], 0, "<p>中文</p>", "")
        with patch("texo.office.shutil.which", return_value=None), patch("texo.office.Path.is_file", return_value=True), patch("texo.office.os.access", return_value=True), patch("texo.office.subprocess.run", return_value=converted) as run:
            payload = make_office_payload("中文")
        self.assertEqual(run.call_args.args[0][0], "/opt/homebrew/bin/pandoc")
        self.assertEqual(payload["plain"], "中文")

    def test_missing_converter_never_returns_a_partial_payload(self):
        with patch("texo.office.shutil.which", return_value=None), patch("texo.office.Path.is_file", return_value=False), patch("texo.office.subprocess.run") as run:
            with self.assertRaisesRegex(RuntimeError, "Pandoc.*剪贴板未修改"):
                make_office_payload("中文 $x$")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
