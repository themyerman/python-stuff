"""Unit tests for basics scripts."""

import importlib.util
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def load_module(filename, module_name):
    """Load a module from a file path for testing."""
    module_path = BASE_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BasicsTests(unittest.TestCase):
    """Validate key utility behavior in basics scripts."""

    def test_add_function(self):
        mod = load_module("functions.py", "functions_mod")
        self.assertEqual(mod.add(2, 5), 7)
        self.assertEqual(mod.add(2), 12)

    def test_planet_validation(self):
        mod = load_module("planets.py", "planets_mod")
        self.assertEqual(mod.hello_planet("Earth"), "Hello earth")
        with self.assertRaises(mod.CosmicException):
            mod.hello_planet("Pluto")

    def test_square_helpers_match(self):
        mod = load_module("lists.py", "lists_mod")
        self.assertEqual(mod.get_squares(10), mod.get_squares_loop(10))

    def test_set_operation_intersection(self):
        mod = load_module("sets.py", "sets_mod")
        result = mod.set_operations({1, 2, 3}, {2, 3, 5}, {2, 3})
        self.assertEqual(result["intersection"], {2, 3})


if __name__ == "__main__":
    unittest.main()
