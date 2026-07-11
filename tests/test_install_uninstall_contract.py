import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "linkease" / "install.sh"
UNINSTALL = ROOT / "linkease" / "uninstall.sh"


class InstallUninstallContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.install = INSTALL.read_text(encoding="utf-8")
        cls.uninstall = UNINSTALL.read_text(encoding="utf-8")

    def test_install_keeps_module_identity_and_full_binary_names(self):
        expected = [
            "module=${DIR##*/}",
            'local TITLE="易有云"',
            "DESKTOP_BIN=linkease-desktop",
            "APPTUNNEL_BIN=apptunnel-client",
            "APP_DIR=/koolshare/linkease",
        ]
        for item in expected:
            self.assertIn(item, self.install)

    def test_install_rejects_non_arm64_full_runtime(self):
        expected = [
            "platform_arch_test()",
            "uname -m",
            "aarch64",
            "arm64",
            "LinkEase full首版仅支持arm64/aarch64",
        ]
        for item in expected:
            self.assertIn(item, self.install)

    def test_install_stops_legacy_and_full_processes(self):
        expected = [
            "killall link-ease",
            "killall ${DESKTOP_BIN}",
            "killall ${APPTUNNEL_BIN}",
            "killall kaiplus_bin",
        ]
        for item in expected:
            self.assertIn(item, self.install)

    def test_install_cleans_betterapps_plugin_and_metadata(self):
        expected = [
            "remove_betterapps_legacy()",
            "/koolshare/bin/BetterApps",
            "/koolshare/betterapps",
            "Module_betterapps.asp",
            "softcenter_module_betterapps",
            "softcenter_module_BetterApps",
            "betterapps_enable",
            "BetterApps_enable",
            "dbus remove betterapps_version",
            "dbus remove BetterApps_version",
        ]
        for item in expected:
            self.assertIn(item, self.install)

    def test_install_migrates_betterapps_disk_keys_to_linkease_keys(self):
        expected = [
            "migrate_betterapps_dbus()",
            "betterapps_data_disk",
            "linkease_data_disk",
            "betterapps_data_root_parent",
            "linkease_data_root_parent",
            "betterapps_data_root",
            "linkease_data_root",
        ]
        for item in expected:
            self.assertIn(item, self.install)

    def test_install_copies_full_runtime_and_kaiplus(self):
        expected = [
            "cp -rf /tmp/${module}/bin/* /koolshare/bin/",
            "rm -rf /koolshare/linkease/kaiplus",
            "cp -rf /tmp/${module}/kaiplus /koolshare/linkease/",
            "chmod 755 /koolshare/bin/${DESKTOP_BIN}",
            "chmod 755 /koolshare/bin/${APPTUNNEL_BIN}",
            "chmod 755 /koolshare/linkease/kaiplus/bin/kaiplus_bin",
        ]
        for item in expected:
            self.assertIn(item, self.install)

    def test_uninstall_removes_full_linkease_and_betterapps_leftovers(self):
        expected = [
            "killall linkease-desktop",
            "killall apptunnel-client",
            "killall kaiplus_bin",
            "rm -rf /koolshare/bin/linkease-desktop",
            "rm -rf /koolshare/bin/apptunnel-client",
            "rm -rf /koolshare/bin/link-ease",
            "rm -rf /koolshare/linkease",
            "rm -rf /koolshare/bin/BetterApps",
            "rm -rf /koolshare/betterapps",
            "dbus remove betterapps_enable",
            "dbus remove BetterApps_enable",
            "dbus remove linkease_version",
            "dbus remove betterapps_version",
            "dbus remove BetterApps_version",
        ]
        for item in expected:
            self.assertIn(item, self.uninstall)


if __name__ == "__main__":
    unittest.main()
