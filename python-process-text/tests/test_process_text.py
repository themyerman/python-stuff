"""Basic tests for python-process-text scripts."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
CODE_DIR = BASE_DIR / "code"


def load_module(filename, name):
    """Load module from python file path."""
    path = CODE_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ProcessTextTests(unittest.TestCase):
    """Validate deterministic utility behavior."""

    def test_open_spark_preview(self):
        mod = load_module("open_spark.py", "open_spark_mod")
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "sample.txt"
            f.write_text("abcdef", encoding="utf-8")
            self.assertEqual(mod.read_preview(f, length=3), "abc")


if __name__ == "__main__":
    unittest.main()
