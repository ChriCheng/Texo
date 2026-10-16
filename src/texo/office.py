"""Prepare local HTML/MathML for Office paste without touching the clipboard."""

from html import escape
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET


_MATH = re.compile(r"<math\b.*?</math>", re.DOTALL)
_HTML_TAGS = set("p br span div em strong code pre ul ol li blockquote hr h1 h2 h3 h4 h5 h6 table thead tbody tr th td del sup sub dl dt dd a".split())
_RESOURCES = {"img", "script", "style", "iframe", "object", "embed", "video", "audio", "source", "link", "meta", "base"}


class _OfficeHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.prose = [], []
        self.math_depth = 0

    def handle_starttag(self, tag, attributes):
        if tag == "img":
            self.handle_data(dict(attributes).get("alt", ""))
        if tag in _RESOURCES:
            return
        if tag == "math":
            self.math_depth += 1
        if self.math_depth or tag in _HTML_TAGS:
            # Office needs MathML attributes; HTML links/resources stay inert.
            attributes = attributes if self.math_depth else []
            encoded = "".join(f' {name}="{escape(value or "", quote=True)}"' for name, value in attributes
                              if name not in {"src", "srcset", "href", "xlink:href", "style"} and not name.startswith("on"))
            self.parts.append(f"<{tag}{encoded}>")

    def handle_endtag(self, tag):
        if tag not in _RESOURCES and (self.math_depth or tag in _HTML_TAGS) and tag not in {"br", "hr"}:
            self.parts.append(f"</{tag}>")
        if tag == "math":
            self.math_depth -= 1

    def handle_data(self, data):
        self.parts.append(escape(data))
        if not self.math_depth:
            self.prose.append(data)


def _pandoc():
    for candidate in (shutil.which("pandoc"), "/opt/homebrew/bin/pandoc", "/usr/local/bin/pandoc"):
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError("PPT 复制需要本机 Pandoc，未找到可执行文件。请先安装 Pandoc 后重试；剪贴板未修改。")


def _unwrap_latex(text):
    for opening, closing in (("$$", "$$"), ("$", "$"), (r"\(", r"\)"), (r"\[", r"\]")):
        if text.startswith(opening) and text.endswith(closing) and len(text) > len(opening) + len(closing):
            before_close = text[:-len(closing)]
            escapes = len(before_close) - len(before_close.rstrip("\\"))
            if escapes % 2 == 0:
                return text[len(opening):-len(closing)].strip()
    return text


def make_office_payload(text, pure_latex=False):
    """Return HTML with native MathML and the unchanged plain-text alternative.

    Callers must finish this conversion before replacing the clipboard. The
    HTML carries Chinese prose and native MathML; pure_latex accepts raw LaTeX
    or one of the four math wrappers. Import depends on the Office version.
    """
    plain = text.strip()
    if not plain:
        raise ValueError("结果为空，请先识别图片。")
    source = f"$$\n{_unwrap_latex(plain)}\n$$" if pure_latex else plain
    command = [_pandoc(), "--from=markdown+tex_math_dollars+tex_math_single_backslash+hard_line_breaks-raw_html-raw_tex",
               "--to=html5", "--mathml", "--wrap=none", "--fail-if-warnings", "--sandbox"]
    try:
        result = subprocess.run(command, input=source, text=True, capture_output=True, timeout=20)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("PPT 公式转换超时，剪贴板未修改。") from error
    except OSError as error:
        raise RuntimeError(f"无法运行 PPT 公式转换：{error}。剪贴板未修改。") from error
    if result.returncode:
        raise RuntimeError(f"PPT 公式转换失败，剪贴板未修改：{result.stderr.strip()[:600]}")
    fragment = _OfficeHTML()
    fragment.feed(result.stdout)
    fragment.close()
    body = "".join(fragment.parts).strip()
    if re.search(r"\$[^$\n]*?(?:\\[A-Za-z]+|[_^=])", "".join(fragment.prose)):
        raise RuntimeError("发现未转换的公式，请补齐数学标记并去掉标记内侧的空格；剪贴板未修改。")
    formulas = _MATH.findall(body)
    for formula in formulas:
        if ET.fromstring(formula).tag != "{http://www.w3.org/1998/Math/MathML}math":
            raise RuntimeError("PPT 公式转换未生成有效 MathML，剪贴板未修改。")
    if pure_latex and len(formulas) != 1:
        raise RuntimeError("PPT 公式转换未生成单个公式，剪贴板未修改。")
    html = '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>' + body + "</body></html>"
    return {"html": html, "plain": plain}
