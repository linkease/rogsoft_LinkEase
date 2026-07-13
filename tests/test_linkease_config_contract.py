import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "linkease" / "scripts" / "linkease_config.sh"
STATUS = ROOT / "linkease" / "scripts" / "linkease_status.sh"


def joined(*parts):
    return "".join(parts)


class LinkEaseConfigContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = CONFIG.read_text(encoding="utf-8")
        cls.status = STATUS.read_text(encoding="utf-8")

    def test_full_runtime_paths_are_linkease_owned_without_embedded_kaiplus(self):
        self.assertIn("DESKTOP_BIN=/koolshare/bin/linkease-desktop", self.config)
        self.assertIn("APPTUNNEL_BIN=/koolshare/bin/apptunnel-client", self.config)
        self.assertIn("APP_DIR=/koolshare/linkease", self.config)
        forbidden = [
            joined("KAIPLUS_", "BIN=${APP_DIR}/kaiplus/bin/kaiplus_bin"),
            joined("KAIPLUS_", "STATIC_DIR=${APP_DIR}/kaiplus/www"),
            joined("KAIPLUS_", "DEFAULTS_DIR=${APP_DIR}/kaiplus/defaults"),
            joined("KAIPLUS_", "ADDR=127.0.0.1:19291"),
            "KAIPLUS_BASE_PATH=/apps/kaiplus/",
            joined("KAIPLUS_", "HOME=${LINKEASE_DATA_ROOT}/kaiplus"),
        ]
        for item in forbidden:
            self.assertNotIn(item, self.config)
        self.assertNotRegex(
            self.config,
            r"(?m)^\s*(?:export\s+)?KAIPLUS_(?:BIN|STATIC_DIR|DEFAULTS_DIR|HOME|ADDR|BASE_PATH)(?:\s*=|\s*$)",
        )

    def test_full_runtime_exports_apps_and_disables_embedded_kaiplus(self):
        expected = [
            "export SERVER_HOST=0.0.0.0",
            "export SERVER_PORT=${DESKTOP_PORT}",
            "export SERVER_BASE_PATH=/apps/",
            "export LINKEASE_EDITION=router-lite",
            "export KAIPLUS_ENABLED=0",
        ]
        for item in expected:
            self.assertIn(item, self.config)
        self.assertNotIn(joined("export KAIPLUS_ENABLED=", "1"), self.config)
        self.assertNotIn("export REASONIX_CREDENTIALS_STORE=file", self.config)

    def test_linkease_detects_independent_kaiplus_for_proxy_only(self):
        expected = [
            "resolve_kaiplus_proxy_target()",
            'KAIPLUS_PROXY_TARGET=""',
            "[ -x /koolshare/scripts/kaiplus_config.sh ] || return 0",
            "[ -x /koolshare/bin/kaiplus_bin ] || return 0",
            'kaiplus_port="$(dbus get kaiplus_port 2>/dev/null)"',
            "kaiplus_port=8189",
            'KAIPLUS_PROXY_TARGET="http://127.0.0.1:${kaiplus_port}"',
            "resolve_kaiplus_proxy_target",
            'export KAIPLUS_PROXY_TARGET="${KAIPLUS_PROXY_TARGET}"',
        ]
        for item in expected:
            self.assertIn(item, self.config)

    def test_apptunnel_preserves_legacy_entry_and_local_api_socket(self):
        self.assertIn("APPTUNNEL_PORT=8897", self.config)
        self.assertIn("LINKEASE_LOCAL_API=/var/run/linkease.sock", self.config)
        pattern = re.compile(
            r"start-stop-daemon -S -q -b -m -p \$APPTUNNEL_PID_FILE "
            r"-x \$APPTUNNEL_BIN -- --deviceAddr :\$APPTUNNEL_PORT --localApi \$LINKEASE_LOCAL_API"
        )
        self.assertRegex(self.config, pattern)

    def test_data_path_resolution_prefers_linkease_then_betterapps_then_bootstrap(self):
        markers = [
            "resolve_linkease_data_disk()",
            'if [ -n "$linkease_data_disk" ] && [ -d "$linkease_data_disk" ]; then',
            'if [ -n "$betterapps_data_disk" ] && [ -d "$betterapps_data_disk" ]; then',
            'LINKEASE_DATA_ROOT=${LINKEASE_DATA_DISK}/.linkease_data',
            'LINKEASE_RECYCLE_ROOT=${LINKEASE_DATA_DISK}/.linkease_recycle',
            'LINKEASE_DATA_ROOT=${APP_DIR}/data/bootstrap',
            "persist_migrated_betterapps_disk",
        ]
        for marker in markers:
            self.assertIn(marker, self.config)

        linkease_index = self.config.index('if [ -n "$linkease_data_disk" ] && [ -d "$linkease_data_disk" ]; then')
        betterapps_index = self.config.index('if [ -n "$betterapps_data_disk" ] && [ -d "$betterapps_data_disk" ]; then')
        bootstrap_index = self.config.index('LINKEASE_DATA_ROOT=${APP_DIR}/data/bootstrap')
        self.assertLess(linkease_index, betterapps_index)
        self.assertLess(betterapps_index, bootstrap_index)

    def test_process_lifecycle_manages_only_desktop_and_apptunnel(self):
        expected = [
            "killall linkease-desktop",
            "killall apptunnel-client",
            "start_desktop",
            "start_apptunnel",
            "load_iptables",
            "del_iptables",
        ]
        for item in expected:
            self.assertIn(item, self.config)
        self.assertNotIn("start_kaiplus", self.config)
        self.assert_no_forbidden_kaiplus_runtime_targets(self.config)

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

    def test_apps_forward_is_linkease_owned(self):
        self.assertIn('APPS_PORT_FORWARD="http://127.0.0.1:${DESKTOP_PORT}"', self.config)
        self.assertIn("ensure_apps_forward()", self.config)
        self.assertIn('nvram set apps_port_forward="$APPS_PORT_FORWARD"', self.config)
        self.assertIn("初始化LinkEase访问入口", self.config)

    def test_status_checks_full_processes_and_health_endpoint(self):
        expected = [
            "source /koolshare/scripts/base.sh",
            "pidof linkease-desktop",
            "pidof apptunnel-client",
            "http://127.0.0.1:19290/apps/api/v1/health",
            "LinkEase full",
            "http_response",
        ]
        for item in expected:
            self.assertIn(item, self.status)

    def test_iptables_cleanup_is_busybox_safe(self):
        expected = [
            "clean_iptables_port()",
            "iptables -D INPUT -p tcp --dport $1 -j ACCEPT",
            "clean_iptables_port ${DESKTOP_PORT}",
            "clean_iptables_port ${APPTUNNEL_PORT}",
        ]
        for item in expected:
            self.assertIn(item, self.config)
        self.assertNotIn('grep "${DESKTOP_PORT}\\\\|${APPTUNNEL_PORT}"', self.config)
        self.assertNotIn("linkease_clean_iptables.sh", self.config)


if __name__ == "__main__":
    unittest.main()
