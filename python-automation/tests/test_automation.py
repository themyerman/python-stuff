"""Tests for deterministic python-automation utilities."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "Source Code"


def load_module(file_path, module_name):
    """Load module from a concrete file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class AutomationTests(unittest.TestCase):
    """Validate folder picker and file splitter behavior."""

    def test_pick_directory(self):
        mod = load_module(SOURCE_DIR / "organizeDirectory.py", "organize_mod")
        self.assertEqual(mod.pick_directory(".txt"), "DOCUMENTS")
        self.assertEqual(mod.pick_directory(".unknown"), "MISC")

    def test_split_results_file(self):
        mod = load_module(SOURCE_DIR / "fileIO.py", "fileio_mod")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "inputFile.txt"
            src.write_text("a b P\nc d F\n", encoding="utf-8")
            pass_file = base / "PassFile.txt"
            fail_file = base / "FailFile.txt"
            mod.split_results_file(src, pass_file, fail_file)
            self.assertIn("a b P", pass_file.read_text(encoding="utf-8"))
            self.assertIn("c d F", fail_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
