from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


@lru_cache(maxsize=1)
def _load_model(path):
    return cv2.dnn.readNetFromONNX(str(path))


def _decode_boxes(predictions, scale, padding, size):
    scores = predictions[:, 4:].max(axis=1)
    labels = predictions[:, 4:].argmax(axis=1)
    selected = scores >= 0.25
    boxes = predictions[selected, :4].copy()
    scores, labels = scores[selected], labels[selected]
    boxes[:, :2] -= boxes[:, 2:] / 2
    if not len(boxes):
        return []
    indices = cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), 0.25, 0.45)
    width, height = size
    dx, dy = padding
    results = []
    for index in np.asarray(indices).reshape(-1):
        x, y, w, h = boxes[index]
        # Keep edge pixels when converting fractional model coordinates to image crops.
        x1, y1 = np.floor((np.array([x, y]) - [dx, dy]) / scale).astype(int) - 2
        x2, y2 = np.ceil((np.array([x + w, y + h]) - [dx, dy]) / scale).astype(int) + 2
        box = [max(0, int(x1)), max(0, int(y1)), min(width, int(x2)), min(height, int(y2))]
        if box[2] > box[0] and box[3] > box[1]:
            results.append({"box": box, "type": ("embedding", "isolated")[labels[index]], "score": float(scores[index])})
    return sorted(results, key=lambda result: (result["box"][1], result["box"][0]))


def detect_formulas(image, model_path=None):
    if not isinstance(image, Image.Image) or min(image.size) < 1:
        raise ValueError("请提供有效的公式图片。")
    if model_path is None:
        local = Path(__file__).resolve().parents[2] / "model/mfd.onnx"
        cached = Path.home() / ".pix2text/1.1/mfd-1.5-onnx/pix2text-mfd-1.5.onnx"
        model_path = local if local.is_file() else cached
    model_path = Path(model_path).expanduser().resolve()
    if not model_path.is_file():
        raise FileNotFoundError("混排公式检测模型未下载。请运行 python scripts/python/hf_hub.py pull --mixed")

    width, height = image.size
    scale = min(768 / width, 768 / height)
    resized_width, resized_height = max(1, round(width * scale)), max(1, round(height * scale))
    dx, dy = (768 - resized_width) // 2, (768 - resized_height) // 2
    canvas = np.full((768, 768, 3), 114, dtype=np.uint8)
    canvas[dy:dy + resized_height, dx:dx + resized_width] = cv2.resize(np.asarray(image.convert("RGB")), (resized_width, resized_height))
    model = _load_model(model_path)
    model.setInput(canvas.transpose(2, 0, 1)[None].astype(np.float32) / 255)
    predictions = model.forward()[0].T
    return _decode_boxes(predictions, scale, (dx, dy), image.size)
