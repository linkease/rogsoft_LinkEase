import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PAGE = ROOT / "linkease" / "webs" / "Module_linkease.asp"


class ModuleLinkEaseScriptOrderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = MODULE_PAGE.read_text(encoding="utf-8-sig")

    def test_jquery_loads_before_state_and_disk_functions(self):
        jquery = self.html.index('src="/js/jquery.js"')
        state = self.html.index('src="/state.js"')
        disk = self.html.index('src="/disk_functions.js"')

        self.assertLess(jquery, state)
        self.assertLess(state, disk)

    def test_jquery_load_temporarily_hides_amd_define(self):
        guard_pattern = re.compile(
            r"__linkease_amd_define[\s\S]+?"
            r"window\.define\s*=\s*undefined[\s\S]+?"
            r'src="/js/jquery\.js"[\s\S]+?'
            r"window\.define\s*=\s*window\.__linkease_amd_define[\s\S]+?"
            r'src="/state\.js"',
            re.MULTILINE,
        )

        self.assertRegex(self.html, guard_pattern)


if __name__ == "__main__":
    unittest.main()
