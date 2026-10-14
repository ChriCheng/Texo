import argparse
from functools import lru_cache
import os
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from texo.latex import normalize_latex


def format_result(latex, delimiter=""):
    return f"{delimiter}{latex.strip()}{delimiter}"


@lru_cache(maxsize=1)
def load_model(model_dir):
    os.environ["NO_ALBUMENTATIONS_UPDATE"] = "1"
    import torch
    from transformers import AutoTokenizer, VisionEncoderDecoderModel
    import texo.utils.config  # Register Texo's custom encoder before loading weights.
    from texo.data.processor import EvalMERImageProcessor

    if not (model_dir / "model.safetensors").is_file():
        raise FileNotFoundError("模型未下载。请先运行 python scripts/python/hf_hub.py pull")
    torch.set_num_threads(min(4, torch.get_num_threads()))
    model = VisionEncoderDecoderModel.from_pretrained(model_dir, local_files_only=True).eval()
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    return model, tokenizer, EvalMERImageProcessor()


def open_image(source):
    from PIL import Image, ImageOps

    with (source.copy() if isinstance(source, Image.Image) else Image.open(source)) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
        background = Image.new("RGBA", image.size, "white")
        return Image.alpha_composite(background, image).convert("RGB")


def recognize(image_path, model_dir=ROOT / "model"):
    import torch

    image = open_image(image_path)
    low, high = image.convert("L").getextrema()
    if low == high:
        raise ValueError("图片为空白，请选择包含公式的图片。")
    model, tokenizer, processor = load_model(Path(model_dir).resolve())
    with torch.inference_mode():
        tokens = model.generate(pixel_values=processor(image).unsqueeze(0), do_sample=False)
    if tokens.shape[-1] >= model.generation_config.max_length:
        raise ValueError("公式超过模型输出长度限制，请裁剪成更小的公式后重试。")
    latex = normalize_latex(tokenizer.batch_decode(tokens, skip_special_tokens=True)[0])
    if not latex:
        raise ValueError("未识别出公式，请检查图片并重新裁剪。")
    return latex


class OCRWindow:
    def __init__(self, root, model_dir):
        import tkinter as tk
        from tkinter import ttk
        from tkinter.scrolledtext import ScrolledText

        self.root, self.model_dir = root, model_dir
        self.results = Queue()
        self.images = Queue()
        self.hotkey_events = Queue()
        self.busy = False
        root.title("Texo — 公式识别")
        root.geometry("900x560")
        root.minsize(850, 400)
        toolbar = tk.Frame(root)
        toolbar.pack(fill="x", padx=16, pady=16)
        self.select_button = tk.Button(toolbar, text="选择图片", command=self.choose)
        self.select_button.pack(side="left")
        self.clipboard_button = tk.Button(toolbar, text="识别剪贴板", command=self.clipboard)
        self.clipboard_button.pack(side="left", padx=8)
        self.capture_button = tk.Button(toolbar, text="截图识别 ⌘L", command=self.screenshot)
        self.capture_button.pack(side="left")
        self.copy_format = tk.StringVar(value="LaTeX")
        ttk.Combobox(toolbar, textvariable=self.copy_format, values=("LaTeX", "$LaTeX$", "$$LaTeX$$"), state="readonly", width=12).pack(side="left", padx=12)
        self.copy_button = tk.Button(toolbar, text="复制 LaTeX", command=self.copy, state="disabled")
        self.copy_button.pack(side="left", padx=12)
        self.status = tk.StringVar(value="选择图片、识别剪贴板，或按全局 ⌘L 截图；首次识别需要加载模型。")
        tk.Label(root, textvariable=self.status, anchor="w", wraplength=740).pack(fill="x", padx=16)
        self.preview = tk.Label(root)
        self.preview.pack(padx=16, pady=12)
        tk.Label(root, text="LaTeX", anchor="w").pack(fill="x", padx=16)
        self.output = ScrolledText(root, wrap="word", font=("Menlo", 14), height=8)
        self.output.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        from texo.macos import GlobalHotkey

        self.hotkey = None
        try:
            self.hotkey = GlobalHotkey(lambda: self.hotkey_events.put(True))
        except RuntimeError as error:
            self.status.set(str(error))
        root.bind("<Destroy>", self.close, add="+")
        root.after(100, self.poll_hotkey)

    def close(self, event):
        if event.widget is self.root and self.hotkey is not None:
            self.hotkey.close()
            self.hotkey = None

    def poll_hotkey(self):
        pressed = False
        while not self.hotkey_events.empty():
            self.hotkey_events.get_nowait()
            pressed = True
        if pressed and not self.busy:
            self.screenshot()
        self.root.after(100, self.poll_hotkey)

    def set_busy(self, busy):
        self.busy = busy
        for button in (self.select_button, self.clipboard_button, self.capture_button):
            button.config(state="disabled" if busy else "normal")
        has_result = bool(self.output.get("1.0", "end-1c").strip())
        self.copy_button.config(state="normal" if has_result and not busy else "disabled")

    def clipboard(self):
        from texo.macos import read_clipboard_image

        self.acquire(read_clipboard_image, "剪贴板图片")

    def screenshot(self):
        from texo.macos import capture_image

        self.acquire(capture_image, "临时截图", hide=True)

    def acquire(self, get_image, label, hide=False):
        if self.busy:
            return
        self.set_busy(True)
        self.status.set("请框选公式，按 Esc 取消。" if hide else "正在读取剪贴板图片…")
        if hide:
            self.root.withdraw()
            self.root.update_idletasks()
        images = self.images

        def worker():
            try:
                images.put((get_image(), None))
            except Exception as error:
                images.put((None, str(error)))

        Thread(target=worker, daemon=True).start()
        self.root.after(100, lambda: self.poll_image(label, hide))

    def poll_image(self, label, hidden):
        try:
            image, error = self.images.get_nowait()
        except Empty:
            self.root.after(100, lambda: self.poll_image(label, hidden))
            return
        if hidden:
            self.root.deiconify()
            self.root.lift()
        self.set_busy(False)
        if error:
            self.status.set(error)
        elif image is None:
            self.status.set("已取消截图，保留上次结果。")
        else:
            self.start(image, label)

    def choose(self):
        from tkinter import filedialog

        path = filedialog.askopenfilename(title="选择公式图片", filetypes=[("图片", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"), ("所有文件", "*")])
        if path:
            self.start(path)

    def start(self, path, label=None):
        from PIL import ImageTk

        if self.busy:
            return
        self.set_busy(True)
        self.output.delete("1.0", "end")
        self.preview.config(image="")
        try:
            image = open_image(path)
            preview = image.copy()
            preview.thumbnail((740, 180))
            self.preview_image = ImageTk.PhotoImage(preview)
            self.preview.config(image=self.preview_image)
        except Exception as error:
            self.status.set(f"无法打开图片：{error}")
            self.set_busy(False)
            return
        name = label or (Path(path).name if isinstance(path, (str, Path)) else "图片")
        self.status.set(f"正在识别 {name}…")
        results, model_dir = self.results, self.model_dir

        def worker():
            started = time.monotonic()
            try:
                results.put((recognize(image, model_dir), time.monotonic() - started, None))
            except Exception as error:
                results.put((None, 0, str(error)))

        Thread(target=worker, daemon=True).start()
        self.root.after(100, self.poll)

    def poll(self):
        try:
            latex, elapsed, error = self.results.get_nowait()
        except Empty:
            self.root.after(100, self.poll)
            return
        if error:
            self.status.set(f"识别失败：{error}")
        else:
            self.output.insert("1.0", latex)
            self.status.set(f"识别完成，用时 {elapsed:.2f} 秒。请核对结果后使用。")
        self.set_busy(False)

    def copy(self):
        latex = normalize_latex(self.output.get("1.0", "end-1c"))
        if not latex:
            self.status.set("结果为空，请先识别公式。")
            return
        delimiter = {"LaTeX": "", "$LaTeX$": "$", "$$LaTeX$$": "$$"}[self.copy_format.get()]
        self.root.clipboard_clear()
        self.root.clipboard_append(format_result(latex, delimiter))
        self.status.set("LaTeX 已复制。")


def main():
    parser = argparse.ArgumentParser(description="Texo: recognize a formula image, or open the desktop window.")
    parser.add_argument("image", nargs="?", type=Path, help="formula image; omit to open the desktop window")
    parser.add_argument("--model", type=Path, default=ROOT / "model", help="local model directory")
    args = parser.parse_args()
    if args.image:
        try:
            print(recognize(args.image, args.model), end="")
        except Exception as error:
            parser.exit(1, f"Texo: {error}\n")
    else:
        import tkinter as tk

        root = tk.Tk()
        OCRWindow(root, args.model)
        root.mainloop()


if __name__ == "__main__":
    main()
