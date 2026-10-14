import contextlib
import io
from pathlib import Path
import runpy
import sys
import types
import unittest
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/python/hf_hub.py"


class HubDownloadTests(unittest.TestCase):
    def setUp(self):
        self.hub = types.ModuleType("huggingface_hub")
        for name in ("HfApi", "create_repo", "snapshot_download", "hf_hub_download"):
            setattr(self.hub, name, Mock())
        transformers = types.ModuleType("transformers")
        for name in ("AutoTokenizer", "VisionEncoderDecoderModel", "PreTrainedTokenizerFast"):
            setattr(transformers, name, Mock())
        self.modules = {"huggingface_hub": self.hub, "transformers": transformers, "task": None}

    def run_cli(self, *args):
        with patch.dict(sys.modules, self.modules), patch.object(sys, "argv", [str(SCRIPT), *args]):
            return runpy.run_path(str(SCRIPT), run_name="__main__")

    def test_help_does_not_import_training_task(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as result:
            self.run_cli("--help")
        self.assertEqual(result.exception.code, 0)
        self.assertIn("pull", output.getvalue())
        self.hub.snapshot_download.assert_not_called()

    def test_model_only_pull_excludes_training_and_onnx_files(self):
        self.run_cli("pull")
        self.hub.snapshot_download.assert_called_once_with(
            repo_id="alephpi/FormulaNet",
            local_dir="./model",
            ignore_patterns=["checkpoints/**", "onnx/**"],
        )

    def test_pull_with_useful_checkpoints_preserves_full_download(self):
        self.run_cli("pull", "--with_useful_ckpts")
        self.hub.snapshot_download.assert_called_once_with(
            repo_id="alephpi/FormulaNet", local_dir="./model"
        )

    def test_mixed_pull_adds_only_the_formula_detector(self):
        self.hub.hf_hub_download.return_value = "/cache/mfd.onnx"
        with patch("shutil.copyfile") as copy:
            self.run_cli("pull", "--mixed")
        self.hub.hf_hub_download.assert_called_once_with(
            repo_id="breezedeus/pix2text-mfd-1.5", filename="pix2text-mfd-1.5.onnx",
        )
        copy.assert_called_once_with("/cache/mfd.onnx", Path("model/mfd.onnx"))


if __name__ == "__main__":
    unittest.main()
