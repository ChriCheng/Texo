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


def recognize(image_path, model_dir=ROOT / "model"):
    import torch
    from PIL import Image, ImageOps

    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
        background = Image.new("RGBA", image.size, "white")
        image = Image.alpha_composite(background, image).convert("RGB")
    low, high = image.convert("L").getextrema()
    if low == high:
        raise ValueError("图片为空白，请选择包含公式的图片。")
    model, tokenizer, processor = load_model(Path(model_dir).resolve())
    with torch.inference_mode():
        tokens = model.generate(pixel_values=processor(image).unsqueeze(0), do_sample=False)
    if tokens.shape[-1] >= model.generation_config.max_length:
        raise ValueError("公式超过模型输出长度限制，请裁剪成更小的公式后重试。")
    latex = tokenizer.batch_decode(tokens, skip_special_tokens=True)[0].strip()
    if not latex:
        raise ValueError("未识别出公式，请检查图片并重新裁剪。")
    return latex


class OCRWindow:
    def __init__(self, root, model_dir):
        import tkinter as tk
        from tkinter.scrolledtext import ScrolledText

        self.root, self.model_dir = root, model_dir
        self.results = Queue()
        root.title("Texo — 公式识别")
        root.geometry("800x540")
        root.minsize(600, 400)
        toolbar = tk.Frame(root)
        toolbar.pack(fill="x", padx=16, pady=16)
        self.select_button = tk.Button(toolbar, text="选择公式图片", command=self.choose)
        self.select_button.pack(side="left")
        self.copy_button = tk.Button(toolbar, text="复制 LaTeX", command=self.copy, state="disabled")
        self.copy_button.pack(side="left", padx=12)
        self.status = tk.StringVar(value="选择一张公式图片开始；首次识别需要加载模型。")
        tk.Label(root, textvariable=self.status, anchor="w", wraplength=740).pack(fill="x", padx=16)
        self.preview = tk.Label(root)
        self.preview.pack(padx=16, pady=12)
        tk.Label(root, text="LaTeX", anchor="w").pack(fill="x", padx=16)
        self.output = ScrolledText(root, wrap="word", font=("Menlo", 14), height=8)
        self.output.pack(fill="both", expand=True, padx=16, pady=(4, 16))

    def choose(self):
        from tkinter import filedialog

        path = filedialog.askopenfilename(title="选择公式图片", filetypes=[("图片", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"), ("所有文件", "*")])
        if path:
            self.start(path)

    def start(self, path):
        from PIL import Image, ImageOps, ImageTk

        self.select_button.config(state="disabled")
        self.copy_button.config(state="disabled")
        self.output.delete("1.0", "end")
        self.preview.config(image="")
        try:
            with Image.open(path) as source:
                preview = ImageOps.exif_transpose(source).convert("RGBA")
                preview.thumbnail((740, 180))
                self.preview_image = ImageTk.PhotoImage(preview)
            self.preview.config(image=self.preview_image)
        except Exception as error:
            self.status.set(f"无法打开图片：{error}")
            self.select_button.config(state="normal")
            return
        self.status.set(f"正在识别 {Path(path).name}…")

        def worker():
            started = time.monotonic()
            try:
                self.results.put((recognize(path, self.model_dir), time.monotonic() - started, None))
            except Exception as error:
                self.results.put((None, 0, str(error)))

        Thread(target=worker, daemon=True).start()
        self.root.after(100, self.poll)

    def poll(self):
        try:
            latex, elapsed, error = self.results.get_nowait()
        except Empty:
            self.root.after(100, self.poll)
            return
        self.select_button.config(state="normal")
        if error:
            self.status.set(f"识别失败：{error}")
        else:
            self.output.insert("1.0", latex)
            self.copy_button.config(state="normal")
            self.status.set(f"识别完成，用时 {elapsed:.2f} 秒。请核对结果后使用。")

    def copy(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.output.get("1.0", "end-1c"))
        self.status.set("LaTeX 已复制。")


def main():
    parser = argparse.ArgumentParser(description="Texo: recognize a formula image, or open the desktop window.")
    parser.add_argument("image", nargs="?", type=Path, help="formula image; omit to open the desktop window")
    parser.add_argument("--model", type=Path, default=ROOT / "model", help="local model directory")
    args = parser.parse_args()
    if args.image:
        try:
            print(recognize(args.image, args.model))
        except Exception as error:
            parser.exit(1, f"Texo: {error}\n")
    else:
        import tkinter as tk

        root = tk.Tk()
        OCRWindow(root, args.model)
        root.mainloop()


if __name__ == "__main__":
    main()
