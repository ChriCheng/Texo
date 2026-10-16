from PIL import ImageDraw

from texo.chinese import recognize_text
from texo.detection import detect_formulas


def same_line(a, b):
    overlap = min(a[3], b[3]) - max(a[1], b[1])
    return overlap > 0.5 * min(a[3] - a[1], b[3] - b[1])


def nearest_text_row(rows, box):
    return min(
        (row for row in rows if row[0]["type"] == "text" and same_line(box, row[0]["box"])),
        key=lambda row: abs(row[0]["box"][1] + row[0]["box"][3] - box[1] - box[3]),
        default=None,
    )


def recognize_mixed(image, recognize_formula, progress=None):
    if progress:
        progress(None, "正在检测公式…")
    formulas = detect_formulas(image)
    if progress:
        progress(1 / (len(formulas) + 2), f"检测完成 · {len(formulas)} 个公式")
    masked = image.copy()
    draw = ImageDraw.Draw(masked)
    parts = []
    for index, formula in enumerate(formulas):
        box = formula["box"]
        draw.rectangle(box, fill="white")
        if progress:
            progress(None, f"正在识别公式 {index + 1}/{len(formulas)}…")
        latex = recognize_formula(image.crop(box))
        if progress:
            progress((index + 2) / (len(formulas) + 2), f"已识别 {index + 1}/{len(formulas)} 个公式")
        delimiter = "$$" if formula["type"] == "isolated" else "$"
        parts.append({**formula, "text": f"{delimiter}{latex.strip()}{delimiter}"})

    # shortcut: Single-column reading order; use page layout detection for columns/tables.
    rows = []
    if progress:
        progress(None, "正在识别文字…")
    for line in sorted(recognize_text(masked), key=lambda line: line["box"][1]):
        part = {**line, "type": "text"}
        row = nearest_text_row(rows, part["box"])
        if row is None:
            rows.append([part])
        else:
            row.append(part)
    for part in parts:
        row = nearest_text_row(rows, part["box"]) if part["type"] == "embedding" else None
        if row is None:
            rows.append([part])
        else:
            row.append(part)
    output = []
    for row in sorted(rows, key=lambda row: row[0]["box"][1]):
        fragments = [p for p in row if p["type"] != "text"]
        for line in (p for p in row if p["type"] == "text"):
            cuts = sorted((f["box"][0] + f["box"][2]) / 2 for f in fragments
                          if f["type"] == "embedding" and line["box"][0] < (f["box"][0] + f["box"][2]) / 2 < line["box"][2])
            if not cuts:
                fragments.append(line)
                continue
            chars = line.get("chars", [])
            if "".join(c["text"] for c in chars) != line["text"] or any(
                not c["text"].isspace() and (c["box"][2] <= c["box"][0] or c["box"][3] <= c["box"][1]) for c in chars
            ):
                raise ValueError("无法定位部分文字，请缩小截图范围后重试。")
            chunks = [{"text": "", "boxes": []} for _ in range(len(cuts) + 1)]
            bucket = 0
            for char in chars:
                box = char["box"]
                if box[2] > box[0] and box[3] > box[1]:
                    bucket = sum(cut < (box[0] + box[2]) / 2 for cut in cuts)
                    chunks[bucket]["boxes"].append(box)
                chunks[bucket]["text"] += char["text"]
            for chunk in chunks:
                if chunk["text"].strip() and chunk["boxes"]:
                    boxes = chunk["boxes"]
                    fragments.append({"type": "text", "text": chunk["text"].strip(), "box": [
                        min(b[0] for b in boxes), min(b[1] for b in boxes),
                        max(b[2] for b in boxes), max(b[3] for b in boxes),
                    ]})
        text = " ".join(p["text"].strip() for p in sorted(fragments, key=lambda p: p["box"][0]))
        output.append(f"\n{text}\n" if row[0]["type"] == "isolated" else text)
    result = "\n".join(output).strip()
    if not result:
        raise ValueError("未识别出文字或公式，请检查图片并重新裁剪。")
    if progress:
        progress(1, "混排识别完成")
    return result
