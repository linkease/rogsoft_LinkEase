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

    def test_full_ui_primary_entry_uses_apps_proxy(self):
        self.assertIn('var full_url = "/apps/";', self.html)
        self.assertIn('webite.href = full_url;', self.html)
        self.assertIn('id="linkease_website"', self.html)
        self.assertIn('打开LinkEase', self.html)

    def test_legacy_8897_entry_is_kept(self):
        self.assertIn('var legacy_url = "http://" + r_lan_ipaddr + ":8897";', self.html)
        self.assertIn('legacy.href = legacy_url;', self.html)
        self.assertIn('id="linkease_legacy"', self.html)
        self.assertIn('旧版入口', self.html)

    def test_config_center_uses_apps_not_legacy_guide(self):
        self.assertNotIn(':8897/guide/index.html', self.html)
        self.assertIn('linkease_guide.href = full_url;', self.html)


if __name__ == "__main__":
    unittest.main()
