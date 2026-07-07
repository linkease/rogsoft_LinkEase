import py_compile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BuildScriptTest(unittest.TestCase):
    def test_build_script_compiles_with_python3(self):
        py_compile.compile(str(ROOT / "build.py"), doraise=True)


if __name__ == "__main__":
    unittest.main()
