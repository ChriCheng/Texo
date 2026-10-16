from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from texo.latex import normalize_latex


class LatexTests(unittest.TestCase):
    def test_arrow_alias_is_portable_to_obsidian(self):
        self.assertEqual(normalize_latex(r"x \larr y"), r"x \leftarrow y")

    def test_infinity_alias_is_portable_to_obsidian(self):
        self.assertEqual(normalize_latex(r"\sum_{n=0}^{\infin} n"), r"\sum_{n=0}^{\infty} n")

    def test_empty_set_alias_is_portable_to_office(self):
        self.assertEqual(normalize_latex(r"\Theta_0\cap\Theta_1=\empty"), r"\Theta_0\cap\Theta_1=\emptyset")

    def test_removes_only_surrounding_whitespace(self):
        self.assertEqual(normalize_latex(" \n\\text{a  b} x _ { i }\r\n"), r"\text{a  b} x _ { i }")

    def test_command_boundaries_and_truncated_content_are_preserved(self):
        for latex in [r"\larrfoo + \infinite", r"\\larr", r"\emptyset + \emptyFoo + \\empty", r"\theta_i-\eta\sum_{(x,y)\in B}\nabla_\theta\ell(f_{\theta_i}(x),y"]:
            with self.subTest(latex=latex):
                self.assertEqual(normalize_latex(latex), latex)


if __name__ == "__main__":
    unittest.main()
