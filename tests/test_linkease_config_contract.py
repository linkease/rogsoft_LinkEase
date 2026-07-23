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
        self.assertIn("FULL_BIN=/koolshare/bin/linkease-full", self.config)
        self.assertNotIn("DESKTOP_BIN=/koolshare/bin/linkease-desktop", self.config)
        self.assertNotIn("APPTUNNEL_BIN=/koolshare/bin/apptunnel-client", self.config)
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
            "export LINKEASE_EDITION=nas-full",
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
        self.assertNotIn("APPTUNNEL_PORT=8897", self.config)
        self.assertNotIn("LINKEASE_LOCAL_API=/var/run/linkease.sock", self.config)
        self.assertNotIn("start_apptunnel", self.config)

    def test_data_path_resolution_prefers_linkease_then_betterapps_then_bootstrap(self):
        markers = [
            "resolve_linkease_data_disk()",
            'if [ -n "$linkease_data_disk" ] && [ -d "$linkease_data_disk" ]; then',
            'if [ -n "$betterapps_data_disk" ] && [ -d "$betterapps_data_disk" ]; then',
            'LINKEASE_DATA_ROOT=${LINKEASE_DATA_DISK}/.linkease_data',
            'LINKEASE_RECYCLE_ROOT=${LINKEASE_DATA_DISK}/.linkease_recycle',
            'LINKEASE_DATA_ROOT=${APP_DIR}/data/bootstrap',
            'MOUNTREMOTE_SOCKET_DIR=/tmp/linkease-mr-sockets',
            "persist_migrated_betterapps_disk",
        ]
        for marker in markers:
            self.assertIn(marker, self.config)

        linkease_index = self.config.index('if [ -n "$linkease_data_disk" ] && [ -d "$linkease_data_disk" ]; then')
        betterapps_index = self.config.index('if [ -n "$betterapps_data_disk" ] && [ -d "$betterapps_data_disk" ]; then')
        bootstrap_index = self.config.index('LINKEASE_DATA_ROOT=${APP_DIR}/data/bootstrap')
        self.assertLess(linkease_index, betterapps_index)
        self.assertLess(betterapps_index, bootstrap_index)

    def test_apptunnel_mountremote_real_runner_is_configured_for_asuswrt(self):
        expected = [
            "export MOUNTREMOTE_MODE=real",
            "export MOUNTREMOTE_LINKREMOTE_AGENT_BINARY=${LINKREMOTE_AGENT_BIN}",
            "export MOUNTREMOTE_SMBD_BINARY=${LINKMOUNT_BIN}",
            "export MOUNTREMOTE_WORK_DIR=${LINKEASE_DATA_ROOT}/mountremote-runtime",
            "export MOUNTREMOTE_SOCKET_DIR=/tmp/linkease-mr-sockets",
            "export MOUNTREMOTE_SAMBA_DIR=${MOUNTREMOTE_SOCKET_DIR}/samba",
            "modprobe cifs >/dev/null 2>&1 || true",
        ]
        for item in expected:
            self.assertIn(item, self.config)
        self.assertNotIn("export MOUNTREMOTE_SYSTEM_COMMAND_HELPER", self.config)

    def test_process_lifecycle_manages_only_desktop_and_apptunnel(self):
        expected = [
            "killall linkease-full",
            "killall linkmount_bin",
            "killall ld-musl-aarch64.so.1",
            "start_full_binary",
            "load_iptables",
            "del_iptables",
        ]
        for item in expected:
            self.assertIn(item, self.config)
        self.assertNotIn("start_kaiplus", self.config)
        self.assert_no_forbidden_kaiplus_runtime_targets(self.config)

    def test_standard_and_full_starts_stop_linkeaselite_runtime(self):
        stopper = re.search(r"stop_linkeaselite_runtime\(\)\{([\s\S]*?)\n\}", self.config)
        self.assertIsNotNone(stopper)
        self.assertIn("killall linkease-lite", stopper.group(1))
        self.assertIn("dbus set linkeaselite_enable=0", stopper.group(1))

        kill_ee = re.search(r"kill_ee\(\)\{([\s\S]*?)\n\}", self.config)
        self.assertIsNotNone(kill_ee)
        self.assertNotIn("linkease-lite", kill_ee.group(1))

        for starter_name, started_binary in (
            ("start_standard", "start_standard_binary"),
            ("start_full", "start_full_binary"),
        ):
            starter = re.search(rf"{starter_name}\(\)\{{([\s\S]*?)\n\}}", self.config)
            self.assertIsNotNone(starter)
            block = starter.group(1)
            self.assertIn("stop_linkeaselite_runtime", block)
            self.assertLess(block.index("stop_linkeaselite_runtime"), block.index(started_binary))

    def test_full_transition_starts_standard_and_full_processes(self):
        self.assertIn("start_standard_binary()", self.config)
        start_full = re.search(r"start_full\(\)\{([\s\S]*?)\n\}", self.config)
        self.assertIsNotNone(start_full)
        block = start_full.group(1)
        self.assertIn("start_standard_binary", block)
        self.assertIn("start_full_binary", block)
        self.assertLess(block.index("start_standard_binary"), block.index("start_full_binary"))

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
            "pidof linkease-full",
            "http://127.0.0.1:19290/apps/api/v1/health",
            "LinkEase Full",
            "http_response",
        ]
        for item in expected:
            self.assertIn(item, self.status)

    def test_status_is_edition_aware(self):
        expected = [
            "eval `dbus export linkease`",
            "normalize_linkease_edition()",
            'case "$LINKEASE_ACTIVE_EDITION" in',
            "LinkEase Standard",
            "LinkEase Full",
            "httpd_proxy_capable()",
            "httpd_proxy_running()",
            "detect_apps_proxy_state",
            "当前系统 httpd 不支持 /apps/ 反向代理",
            "当前系统 httpd proxy 未运行",
            "已使用19290端口直连",
        ]
        for item in expected:
            self.assertIn(item, self.status)
        self.assertNotIn("LinkEase Lite", self.status)
        self.assertNotIn("lite)", self.status)

    def test_iptables_cleanup_is_busybox_safe(self):
        expected = [
            "clean_iptables_port()",
            "iptables -D INPUT -p tcp --dport $1 -j ACCEPT",
            "STANDARD_PORT=8897",
            "clean_iptables_port ${STANDARD_PORT}",
            "clean_iptables_port ${DESKTOP_PORT}",
        ]
        for item in expected:
            self.assertIn(item, self.config)
        self.assertIn(
            "iptables -t filter -I INPUT -p tcp --dport ${STANDARD_PORT} -j ACCEPT",
            self.config,
        )
        self.assertNotIn('grep "${DESKTOP_PORT}\\\\|${APPTUNNEL_PORT}"', self.config)
        self.assertNotIn("linkease_clean_iptables.sh", self.config)

    def test_runtime_normalizes_standard_full_editions(self):
        expected = [
            "normalize_linkease_edition()",
            "standard|full)",
            'echo "$linkease_edition"',
            'LINKEASE_ACTIVE_EDITION="$(normalize_linkease_edition)"',
            'dbus set linkease_edition="$LINKEASE_ACTIVE_EDITION"',
            'dbus set linkease_simple=0',
        ]
        for item in expected:
            self.assertIn(item, self.config)
        self.assertNotIn("echo lite", self.config)

    def test_runtime_falls_back_to_standard_when_full_is_unsupported(self):
        normalized_edition = re.search(
            r"normalize_linkease_edition\(\)\{([\s\S]*?)\n\}", self.config
        )
        self.assertIsNotNone(normalized_edition)
        self.assertIn(
            'if [ "$linkease_edition" = "full" ] && [ "$linkease_full_supported" != "1" ]; then',
            normalized_edition.group(1),
        )
        self.assertIn("echo standard", normalized_edition.group(1))

    def test_full_runtime_requires_usb2jffs_ready(self):
        expected = [
            "detect_usb2jffs_ready()",
            "full_memory_ready()",
            "FULL_MIN_MEM_KB=900000",
            "usb2jffs_is_enabled()",
            "is_usb_jffs_running()",
            "/proc/meminfo",
            "dbus get usb2jffs_enable",
            "dbus get usb2jffs_mount",
            "/proc/mounts",
            'dbus set linkease_usb2jffs_ready=1',
            'dbus set linkease_usb2jffs_ready=0',
            "需要开启并启用 usb2jffs",
            "detect_full_runtime_support",
            'dbus set linkease_full_supported=0',
            "LinkEase Full 使用 ARM32 通用二进制",
            "LinkEase Full 需要 1GB 以上内存",
        ]
        for item in expected:
            self.assertIn(item, self.config)

        startup_order = [
            "detect_full_runtime_support",
            "persist_active_edition",
            "configure_data_paths",
        ]
        positions = [self.config.index(item) for item in startup_order]
        self.assertEqual(positions, sorted(positions))

    def test_runtime_sets_go_memory_limits_before_starting_binaries(self):
        expected = [
            "default_standard_gomemlimit()",
            "default_full_gomemlimit()",
            "apply_go_memory_limits()",
            "export GOMEMLIMIT=",
            "export GOGC=",
            "ulimit -v unlimited",
            "linkease_gomemlimit",
            "linkease_full_gomemlimit",
            "256MiB",
            "384MiB",
        ]
        for item in expected:
            self.assertIn(item, self.config)

        for starter in ("start_standard", "start_full"):
            block = re.search(r"%s\(\)\{([\s\S]*?)\n\}" % starter, self.config)
            self.assertIsNotNone(block)
            launch_call = "start_standard_binary" if starter == "start_standard" else "start_full_binary"
            self.assertIn("apply_go_memory_limits", block.group(1))
            self.assertIn("ulimit -v unlimited", block.group(1))
            self.assertLess(block.group(1).index("apply_go_memory_limits"), block.group(1).index(launch_call))
            self.assertLess(block.group(1).index("ulimit -v unlimited"), block.group(1).index(launch_call))

    def test_runtime_has_separate_standard_full_starters(self):
        expected = [
            "start_standard()",
            "start_full()",
            'case "$LINKEASE_ACTIVE_EDITION" in',
            "standard)",
            "full)",
            "start_standard",
            "start_full",
        ]
        for item in expected:
            self.assertIn(item, self.config)
        self.assertNotIn("start_lite()", self.config)
        self.assertNotIn("lite)", self.config)

    def test_full_detects_httpd_proxy_state_and_standard_does_not_start_full(self):
        expected = [
            "ensure_apps_forward()",
            "detect_apps_proxy_state()",
            "httpd_proxy_capable()",
            "httpd_proxy_running()",
            "/usr/sbin/httpd -C proxy",
            "ps | grep '[h]ttpd-proxy'",
            'current_forward="$(nvram get apps_port_forward 2>/dev/null)"',
            'dbus set linkease_httpd_proxy_capable="$proxy_capable"',
            'dbus set linkease_httpd_proxy_running="$proxy_running"',
            'dbus set linkease_httpd_proxy_backend="$proxy_backend"',
            "dbus set linkease_apps_proxy_supported=1",
            'dbus set linkease_apps_proxy_hint=""',
            "dbus set linkease_apps_proxy_supported=0",
            "dbus set linkease_apps_proxy_hint=",
            "当前系统 httpd 不支持 /apps/ 反向代理",
            "当前系统 httpd proxy 未运行",
            '已使用${DESKTOP_PORT}端口直连',
            "wait_httpd_proxy_running",
        ]
        for item in expected:
            self.assertIn(item, self.config)
        self.assertNotIn('apps_health_url="http://127.0.0.1/apps/api/v1/health"', self.config)

        start_full = re.search(r"start_full\(\)\{([\s\S]*?)\n\}", self.config)
        self.assertIsNotNone(start_full)
        block = start_full.group(1)
        self.assertLess(block.index("ensure_apps_forward"), block.index("start_full_binary"))
        self.assertLess(block.index("start_full_binary"), block.index("detect_apps_proxy_state"))

        standard_block = re.search(r"start_standard\(\)\{([\s\S]*?)\n\}", self.config)
        self.assertIsNotNone(standard_block)
        self.assertNotIn("start_full_binary", standard_block.group(1))

    def test_desktop_firewall_rule_is_gated_to_full_edition(self):
        load_iptables = re.search(r"load_iptables\(\)\{([\s\S]*?)\n\}", self.config)
        self.assertIsNotNone(load_iptables)
        block = load_iptables.group(1)
        self.assertIn('if [ "$LINKEASE_ACTIVE_EDITION" = "full" ]; then', block)
        self.assertIn(
            "iptables -t filter -I INPUT -p tcp --dport ${DESKTOP_PORT} -j ACCEPT",
            block,
        )
        self.assertNotIn("APPTUNNEL_PORT", block)


if __name__ == "__main__":
    unittest.main()
