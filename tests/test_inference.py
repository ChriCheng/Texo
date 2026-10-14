from pathlib import Path
import tempfile
import unittest

from PIL import Image

from main import ROOT, recognize


class InferenceTests(unittest.TestCase):
    def test_blank_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blank.png"
            Image.new("RGB", (100, 40), "white").save(path)
            with self.assertRaisesRegex(ValueError, "空白"):
                recognize(path)

    @unittest.skipUnless((ROOT / "model/model.safetensors").is_file(), "download model first")
    def test_real_formula_and_transparent_background(self):
        path = ROOT / "tests/fixtures/simple.png"
        expected = "x^{2}+y^{2}=z^{2}"
        self.assertEqual("".join(recognize(path).split()), expected)
        with Image.open(path) as source:
            pixel = source.getpixel((0, 0))
            self.assertEqual("".join(recognize(source).split()), expected)
            self.assertEqual(source.getpixel((0, 0)), pixel)
        with tempfile.TemporaryDirectory() as directory:
            transparent_path = Path(directory) / "transparent.png"
            with Image.open(path) as source:
                image = Image.new("RGBA", source.size, (0, 0, 0, 0))
                image.putalpha(source.convert("L").point(lambda value: 255 - value))
                image.save(transparent_path)
            self.assertEqual("".join(recognize(transparent_path).split()), expected)


if __name__ == "__main__":
    unittest.main()
