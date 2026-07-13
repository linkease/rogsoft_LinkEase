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
        self.assertIn('var management_url = build_management_url();', self.html)
        self.assertIn('webite.href = management_url;', self.html)
        self.assertIn('id="linkease_website"', self.html)
        self.assertIn('打开LinkEase', self.html)

    def test_legacy_8897_entry_is_kept(self):
        self.assertIn('var legacy_url = "http://" + r_lan_ipaddr + ":8897";', self.html)
        self.assertIn('legacy.href = legacy_url;', self.html)
        self.assertIn('id="linkease_legacy"', self.html)
        self.assertIn('旧版入口', self.html)

    def test_management_links_follow_the_selected_edition(self):
        self.assertNotIn(':8897/guide/index.html', self.html)
        expected = [
            'function build_management_url()',
            'if (selected_linkease_edition() == "full" && linkease_full_supported()) {',
            'return build_full_url();',
            'return "http://" + r_lan_ipaddr + ":8897";',
            'linkease_guide.href = management_url;',
        ]
        for item in expected:
            self.assertIn(item, self.html)

    def test_edition_selector_replaces_simple_switch(self):
        expected = [
            'var params_check = ["linkease_enable"];',
            'var params_input = ["linkease_edition"];',
            'function normalize_linkease_edition(edition, simple)',
            'function selected_linkease_edition()',
            'function set_linkease_edition(edition)',
            'name="linkease_edition"',
            'value="standard"',
            'value="full"',
            'value="lite"',
            'Standard 版本',
            'Full 版本',
            '精简版本（内存小于512M推荐）',
        ]
        for item in expected:
            self.assertIn(item, self.html)
        self.assertNotIn('<label>精简版（内存小于512M推荐）</label>', self.html)
        self.assertNotIn('id="linkease_simple" class="switch"', self.html)

    def test_edition_save_preserves_legacy_simple_key(self):
        expected = [
            'dbus["linkease_edition"] = selected_linkease_edition();',
            'dbus["linkease_simple"] = dbus["linkease_edition"] == "lite" ? "1" : "0";',
            'set_linkease_edition(normalize_linkease_edition(dbus["linkease_edition"], dbus["linkease_simple"]));',
        ]
        for item in expected:
            self.assertIn(item, self.html)

    def test_edition_radio_group_is_not_read_as_single_input(self):
        self.assertNotIn('E("linkease_edition").value', self.html)
        self.assertNotIn('E(params_input[i]).value', self.html)

    def test_full_url_uses_proxy_or_direct_port(self):
        expected = [
            'function current_browser_origin()',
            'return window.location.protocol + "//" + window.location.host;',
            'function linkease_full_proxy_supported()',
            'if (typeof dbus["linkease_httpd_proxy_running"] != "undefined") {',
            'return dbus["linkease_httpd_proxy_running"] == "1";',
            'function build_full_url()',
            'return current_browser_origin() + "/apps/";',
            'return "http://" + r_lan_ipaddr + ":19290/apps/";',
        ]
        for item in expected:
            self.assertIn(item, self.html)

    def test_full_proxy_upgrade_hint_is_present(self):
        expected = [
            'id="linkease_proxy_hint"',
            '当前系统 httpd 不支持 /apps/ 反向代理',
            '建议升级系统到最新版本',
            'E("linkease_proxy_hint").style.display',
        ]
        for item in expected:
            self.assertIn(item, self.html)

    def test_unsupported_full_selection_warns_and_falls_back_to_standard(self):
        expected = [
            'function linkease_full_supported()',
            'return dbus["linkease_full_supported"] == "1";',
            'function update_full_support_hint(force)',
            'dbus["linkease_full_support_hint"]',
            '需要开启并启用 usb2jffs',
            'function handle_linkease_edition_change()',
            'if (selected_linkease_edition() == "full" && !linkease_full_supported()) {',
            'set_linkease_edition("standard");',
            'update_full_support_hint(true);',
            'onclick="handle_linkease_edition_change();"',
            'id="linkease_full_support_hint"',
        ]
        for item in expected:
            self.assertIn(item, self.html)


if __name__ == "__main__":
    unittest.main()
