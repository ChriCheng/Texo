from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from texo.detection import _decode_boxes, detect_formulas

MODEL = ROOT / "model/mfd.onnx"
if not MODEL.is_file():
    MODEL = Path.home() / ".pix2text/1.1/mfd-1.5-onnx/pix2text-mfd-1.5.onnx"


class DetectionTests(unittest.TestCase):
    def test_padding_scale_clipping_and_overlapping_detections(self):
        predictions = np.array([
            [110, 70, 220, 100, 0.9, 0.1],
            [110, 70, 220, 100, 0.8, 0.2],
            [110, 70, 220, 100, 0.1, 0.1],
        ], dtype=np.float32)
        results = _decode_boxes(predictions, 2, (10, 20), (100, 40))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["box"], [0, 0, 100, 40])
        self.assertEqual(results[0]["type"], "embedding")
        self.assertAlmostEqual(results[0]["score"], 0.9, places=6)

    def test_empty_and_outside_candidates_do_not_create_invalid_crops(self):
        for predictions in (np.empty((0, 6), dtype=np.float32), np.array([[900, 900, 4, 4, 0.1, 0.9]], dtype=np.float32)):
            with self.subTest(predictions=predictions.tolist()):
                self.assertEqual(_decode_boxes(predictions, 1, (0, 0), (100, 40)), [])

    def test_missing_model_has_download_instruction(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError, "hf_hub.py pull --mixed"):
                detect_formulas(Image.new("RGB", (100, 40), "white"), Path(directory) / "missing.onnx")

    def test_invalid_image_is_rejected(self):
        for image in (None, Image.new("RGB", (0, 40))):
            with self.subTest(image=image):
                with self.assertRaisesRegex(ValueError, "有效"):
                    detect_formulas(image)

    @unittest.skipUnless(MODEL.is_file(), "download mixed OCR model first")
    def test_real_blank_image_has_no_formulas(self):
        self.assertEqual(detect_formulas(Image.new("RGB", (400, 180), "white"), MODEL), [])

    @unittest.skipUnless(MODEL.is_file(), "download mixed OCR model first")
    def test_real_formula_detects_isolated_region_without_mutating_source(self):
        with Image.open(ROOT / "tests/fixtures/simple.png") as image:
            original = image.tobytes()
            results = detect_formulas(image, MODEL)
            self.assertEqual(image.tobytes(), original)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["type"], "isolated")
            self.assertEqual(results[0]["box"], [0, 0, *image.size])
            self.assertGreater(results[0]["score"], 0.8)

    @unittest.skipUnless(MODEL.is_file(), "download mixed OCR model first")
    def test_real_mixed_image_keeps_text_outside_formula_regions(self):
        with Image.open(ROOT / "tests/fixtures/mixed.png") as image:
            results = detect_formulas(image, MODEL)
        self.assertEqual([result["type"] for result in results], ["embedding", "isolated"])
        for result, expected in zip(results, ([260, 20, 695, 80], [300, 160, 735, 256])):
            with self.subTest(kind=result["type"]):
                self.assertTrue(all(abs(actual - target) <= 20 for actual, target in zip(result["box"], expected)), result)
                self.assertGreater(result["score"], 0.6)


if __name__ == "__main__":
    unittest.main()
