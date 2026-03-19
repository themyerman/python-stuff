"""Basic tests for python-building-tools scripts."""

import importlib.util
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def load_module(filename, name):
    """Load module from filename for testing."""
    path = BASE_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class BuildingToolsTests(unittest.TestCase):
    """Validate deterministic helper behavior."""

    def test_describe_arguments_safe(self):
        mod = load_module("arguments.py", "arguments_mod")
        mod.describe_arguments(["script.py"])

    def test_sub_returns_strings(self):
        mod = load_module("sub.py", "sub_mod")
        stdout, stderr = mod.run_ls_var()
        self.assertIsInstance(stdout, str)
        self.assertIsInstance(stderr, str)

    def test_freespace_returns_text(self):
        mod = load_module("sub-freespace.py", "freespace_mod")
        free = mod.get_free_space()
        self.assertTrue(isinstance(free, str) and len(free) > 0)


if __name__ == "__main__":
    unittest.main()
