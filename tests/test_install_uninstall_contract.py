import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "linkease" / "install.sh"
UNINSTALL = ROOT / "linkease" / "uninstall.sh"


def joined(*parts):
    return "".join(parts)


class InstallUninstallContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.install = INSTALL.read_text(encoding="utf-8")
        cls.uninstall = UNINSTALL.read_text(encoding="utf-8")

    def assert_no_external_linkease_data_deletion(self, script):
        data_reference = re.compile(
            r"(?:\.linkease_data|LINKEASE_DATA_(?:ROOT|DISK)|"
            r"(?:linkease|betterapps)_data_(?:disk|root|root_parent))",
            re.IGNORECASE,
        )
        destructive = re.compile(r"\b(?:rm|rmdir)\b|\bfind\b.*\s-delete\b")
        deletion_lines = [
            line for line in script.splitlines() if destructive.search(line)
        ]
        for line in deletion_lines:
            self.assertIsNone(
                data_reference.search(line),
                "destructive command may remove external .linkease_data: %s" % line,
            )

        assigned_external_data_vars = set()
        for line in script.splitlines():
            match = re.match(
                r"^\s*(?:local\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line
            )
            if match and data_reference.search(match.group(2)):
                assigned_external_data_vars.add(match.group(1))
        for variable in assigned_external_data_vars:
            variable_reference = re.compile(r"\$\{?%s\}?" % re.escape(variable))
            for line in deletion_lines:
                self.assertIsNone(
                    variable_reference.search(line),
                    "destructive command may remove external data via %s: %s"
                    % (variable, line),
                )

    def assert_no_forbidden_kaiplus_runtime_targets(self, script):
        commands = r"(?:start-stop-daemon|killall|kill|mv|install|cp|rm|mkdir|chmod|find)"
        targets = (
            r"(?:kaiplus_bin|/koolshare/kaiplus|"
            r"/koolshare/linkease/"
            r"kaiplus|\$\{?KAIPLUS_"
            r"BIN\}?|\$\{?KAIPLUS_"
            r"HOME\}?)"
        )
        self.assertNotRegex(
            script,
            rf"(?im)\b{commands}\b[^\n]*{targets}",
        )
        kaiplus_sources = r"/tmp/(?:\$\{?module\}?|linkease)/kaiplus(?:[\s/'\"]|$)"
        self.assertNotRegex(
            script,
            rf"(?im)\bcp\b[^\n]*{kaiplus_sources}",
        )

    def test_forbidden_kaiplus_source_copies_reject_variable_destinations(self):
        forbidden_copy = joined("cp -rf /tmp/${module}/", "kaiplus ${DEST_DIR}/")
        with self.assertRaises(AssertionError):
            self.assert_no_forbidden_kaiplus_runtime_targets(forbidden_copy)

        forbidden_linkease_copy = "cp -rf /tmp/linkease/kaiplus \"${DEST_DIR}/\""
        with self.assertRaises(AssertionError):
            self.assert_no_forbidden_kaiplus_runtime_targets(forbidden_linkease_copy)

    def test_install_keeps_module_identity_and_full_binary_names(self):
        expected = [
            "module=${DIR##*/}",
            'local TITLE="易有云"',
            "FULL_BIN=linkease-full",
            "APP_DIR=/koolshare/linkease",
            "LINKMOUNT_BIN_DIR=${APP_DIR}/linkmount_bin",
        ]
        for item in expected:
            self.assertIn(item, self.install)

    def test_install_records_full_support_without_blocking_standard(self):
        expected = [
            "detect_full_runtime_support()",
            "detect_usb2jffs_ready()",
            "full_memory_ready()",
            "/proc/meminfo",
            "usb2jffs_is_enabled()",
            "is_usb_jffs_running()",
            "dbus get usb2jffs_enable",
            "dbus get usb2jffs_mount",
            'dbus set linkease_usb2jffs_ready=',
            "linkease_full_supported=1",
            "linkease_full_supported=0",
            "dbus set linkease_full_supported=",
            "dbus set linkease_full_support_hint=",
            "LinkEase Full 使用 ARM32 通用二进制",
            "LinkEase Full 需要 1GB 以上内存",
            "需要开启并启用 usb2jffs",
        ]
        for item in expected:
            self.assertIn(item, self.install)
        self.assertNotIn("platform_arch_test", self.install)
        self.assertNotIn("LinkEase full首版仅支持arm64/aarch64", self.install)

    def test_install_initializes_edition_without_overwriting_existing_value(self):
        expected = [
            "init_linkease_edition()",
            'if [ -z "$(dbus get ${module}_edition)" ];then',
            "dbus set ${module}_edition=standard",
            "dbus set ${module}_simple=0",
        ]
        for item in expected:
            self.assertIn(item, self.install)
        self.assertNotIn("dbus set ${module}_edition=lite", self.install)

    def test_install_stops_legacy_and_full_linkease_processes_only(self):
        expected = [
            "killall link-ease",
            "killall ${FULL_BIN}",
            "killall apptunnel-client",
            "killall linkremote-agent",
            "killall hostlink",
            "rm -rf /koolshare/bin/link-ease",
            "rm -rf /koolshare/bin/linkease-desktop",
            "rm -rf /koolshare/bin/apptunnel-client",
        ]
        for item in expected:
            self.assertIn(item, self.install)
        self.assert_no_forbidden_kaiplus_runtime_targets(self.install)

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

    def test_install_copies_full_runtime_without_kaiplus(self):
        expected = [
            "cp -rf /tmp/${module}/bin/* /koolshare/bin/",
            "cp -rf /tmp/${module}/linkmount_bin ${APP_DIR}/",
            "cp -rf /tmp/${module}/runtime ${APP_DIR}/",
            "chmod 755 /koolshare/bin/${FULL_BIN}",
            "chmod 755 /koolshare/bin/apptunnel-client",
            "chmod 755 /koolshare/bin/linkremote-agent",
            "chmod 755 /koolshare/bin/hostlink",
            "chmod 755 /koolshare/bin/heif-converter",
            "chmod 755 ${LINKMOUNT_BIN_DIR}/linkmount_bin",
            "chmod 755 /koolshare/scripts/mountremote-*.sh",
        ]
        for item in expected:
            self.assertIn(item, self.install)
        forbidden = [
            joined("rm -rf /koolshare/linkease/", "kaiplus"),
            joined("cp -rf /tmp/${module}/", "kaiplus /koolshare/linkease/"),
            joined("chmod 755 /koolshare/linkease/", "kaiplus/bin/kaiplus_bin"),
            joined(
                "chmod 755 /koolshare/linkease/",
                "kaiplus/helpers/kaiplus_workspace_tool",
            ),
        ]
        for item in forbidden:
            self.assertNotIn(item, self.install)
        self.assert_no_forbidden_kaiplus_runtime_targets(self.install)
        self.assert_no_external_linkease_data_deletion(self.install)

    def test_uninstall_removes_full_linkease_and_betterapps_leftovers_without_kaiplus(self):
        expected = [
            "killall linkease-full",
            "killall apptunnel-client",
            "killall linkremote-agent",
            "killall hostlink",
            "rm -rf /koolshare/bin/linkease-full",
            "rm -rf /koolshare/bin/link-ease",
            "rm -rf /koolshare/bin/apptunnel-client",
            "rm -rf /koolshare/bin/linkremote-agent",
            "rm -rf /koolshare/bin/hostlink",
            "rm -rf /koolshare/linkease",
            "rm -rf /koolshare/scripts/mountremote-*.sh",
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
        self.assert_no_forbidden_kaiplus_runtime_targets(self.uninstall)
        self.assert_no_external_linkease_data_deletion(self.uninstall)


if __name__ == "__main__":
    unittest.main()
