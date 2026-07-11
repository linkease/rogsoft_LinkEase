import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "linkease" / "scripts" / "linkease_config.sh"
STATUS = ROOT / "linkease" / "scripts" / "linkease_status.sh"


class LinkEaseConfigContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = CONFIG.read_text(encoding="utf-8")
        cls.status = STATUS.read_text(encoding="utf-8")

    def test_full_runtime_paths_are_linkease_owned(self):
        self.assertIn("DESKTOP_BIN=/koolshare/bin/linkease-desktop", self.config)
        self.assertIn("APPTUNNEL_BIN=/koolshare/bin/apptunnel-client", self.config)
        self.assertIn("APP_DIR=/koolshare/linkease", self.config)
        self.assertIn("KAIPLUS_BIN=${APP_DIR}/kaiplus/bin/kaiplus_bin", self.config)
        self.assertIn("KAIPLUS_DEFAULTS_DIR=${APP_DIR}/kaiplus/defaults", self.config)

    def test_full_runtime_exports_apps_and_asusgo_environment(self):
        expected = [
            "export SERVER_HOST=0.0.0.0",
            "export SERVER_PORT=${DESKTOP_PORT}",
            "export SERVER_BASE_PATH=/apps/",
            "export LINKEASE_EDITION=router-lite",
            "export KAIPLUS_ENABLED=1",
            "export KAIPLUS_SYSTEM_ROLE=asusgo",
            "export KAIPLUS_BASE_PATH=/apps/kaiplus/",
            "export KAIPLUS_ADDR=127.0.0.1:19291",
            "export KAIPLUS_PROXY_TARGET=http://127.0.0.1:19291",
            "export REASONIX_CREDENTIALS_STORE=file",
        ]
        for item in expected:
            self.assertIn(item, self.config)

    def test_apptunnel_preserves_legacy_entry_and_local_api_socket(self):
        self.assertIn("APPTUNNEL_PORT=8897", self.config)
        self.assertIn("LINKEASE_LOCAL_API=/var/run/linkease.sock", self.config)
        pattern = re.compile(
            r"start-stop-daemon -S -q -b -m -p \\$APPTUNNEL_PID_FILE "
            r"-x \\$APPTUNNEL_BIN -- --deviceAddr :\\$APPTUNNEL_PORT --localApi \\$LINKEASE_LOCAL_API"
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

    def test_process_lifecycle_manages_desktop_apptunnel_and_kaiplus(self):
        expected = [
            "killall linkease-desktop",
            "killall apptunnel-client",
            "killall kaiplus_bin",
            "start_desktop",
            "start_apptunnel",
            "start_kaiplus",
            "-x $KAIPLUS_BIN",
            "load_iptables",
            "del_iptables",
        ]
        for item in expected:
            self.assertIn(item, self.config)

    def test_apps_forward_is_linkease_owned(self):
        self.assertIn('APPS_PORT_FORWARD="http://127.0.0.1:${DESKTOP_PORT}"', self.config)
        self.assertIn("ensure_apps_forward()", self.config)
        self.assertIn('nvram set apps_port_forward="$APPS_PORT_FORWARD"', self.config)
        self.assertIn("初始化LinkEase访问入口", self.config)

    def test_status_checks_full_processes_and_health_endpoint(self):
        expected = [
            "pidof linkease-desktop",
            "pidof apptunnel-client",
            "pidof kaiplus_bin",
            "http://127.0.0.1:19290/apps/api/v1/health",
            "LinkEase full",
        ]
        for item in expected:
            self.assertIn(item, self.status)


if __name__ == "__main__":
    unittest.main()
