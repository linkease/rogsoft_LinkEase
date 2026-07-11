# rogsoft LinkEase ASUSWRT Full Edition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the ASUSWRT Koolshare plugin from legacy LinkEase/BetterApps split packaging into a single `linkease` full edition that runs `linkease-desktop`, `apptunnel-client`, and KaiPlus on arm64 ASUSWRT.

**Architecture:** Keep the software center module identity as `linkease`. Replace the old single `link-ease` process lifecycle with a LinkEase-owned full runtime lifecycle: `linkease-desktop` serves `/apps/` on port `19290`, `apptunnel-client` preserves the legacy `8897` entry, and KaiPlus runs from `/koolshare/linkease/kaiplus` with the `asusgo` profile. The installer migrates BetterApps state and removes BetterApps plugin files, while unsupported full architectures fail clearly.

**Tech Stack:** POSIX shell for Koolshare scripts, ASUSWRT dbus/nvram helpers, Python 3 `unittest` contract tests, Python packaging script `build.py`, tarball packaging.

---

## File Structure

- Modify `build.py`: stage full runtime artifacts into the `linkease` package before creating `linkease.tar.gz`.
- Modify `config.json.js`: add full artifact metadata fields while keeping `module=linkease`.
- Modify `linkease/install.sh`: validate arm64 full support, stop old and new processes, migrate BetterApps state, remove BetterApps plugin files, install full runtime files.
- Modify `linkease/uninstall.sh`: stop full runtime processes and remove LinkEase plus BetterApps leftovers.
- Modify `linkease/scripts/linkease_config.sh`: own `linkease-desktop`, `apptunnel-client`, KaiPlus env, data root resolution, `/apps/` reverse proxy, and firewall rules.
- Modify `linkease/scripts/linkease_status.sh`: report full runtime health for `linkease-desktop` and `apptunnel-client`.
- Modify `linkease/webs/Module_linkease.asp`: make `/apps/` the primary full entry and keep `8897` as legacy entry.
- Add or modify `tests/test_linkease_config_contract.py`: contract tests for runtime env, process lifecycle, data path, and BetterApps migration.
- Add or modify `tests/test_install_uninstall_contract.py`: contract tests for installer/uninstaller full behavior.
- Modify `tests/test_module_linkease_scripts.py`: extend ASP UI contract tests.
- Modify `tests/test_build_script.py`: extend build script tests for full artifact staging.

## Task 1: Add Runtime Script Contract Tests

**Files:**
- Create: `tests/test_linkease_config_contract.py`
- Test: `linkease/scripts/linkease_config.sh`
- Test: `linkease/scripts/linkease_status.sh`

- [ ] **Step 1: Write failing config/status contract tests**

Create `tests/test_linkease_config_contract.py` with:

```python
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

    def test_process_lifecycle_manages_desktop_apptunnel_and_kaiplus(self):
        expected = [
            "killall linkease-desktop",
            "killall apptunnel-client",
            "killall kaiplus_bin",
            "start_desktop",
            "start_apptunnel",
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
            "http://127.0.0.1:19290/apps/api/v1/health",
            "LinkEase full",
        ]
        for item in expected:
            self.assertIn(item, self.status)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_linkease_config_contract -v
```

Expected: fails because current scripts still reference `/koolshare/bin/link-ease`, old `linkease_simple`, and do not define full runtime paths.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_linkease_config_contract.py
git commit -m "test: cover linkease full runtime contract"
```

## Task 2: Implement Full Runtime Lifecycle Scripts

**Files:**
- Modify: `linkease/scripts/linkease_config.sh`
- Modify: `linkease/scripts/linkease_status.sh`
- Test: `tests/test_linkease_config_contract.py`

- [ ] **Step 1: Replace `linkease_config.sh` with full runtime lifecycle**

Replace the file body with this shell script:

```sh
#!/bin/sh
eval `dbus export linkease`
eval `dbus export betterapps`
source /koolshare/scripts/base.sh
alias echo_date='echo $(date +%Y年%m月%d日\ %X):'

DESKTOP_BIN=/koolshare/bin/linkease-desktop
APPTUNNEL_BIN=/koolshare/bin/apptunnel-client
DESKTOP_PID_FILE=/var/run/linkease-desktop.pid
APPTUNNEL_PID_FILE=/var/run/linkease-apptunnel.pid
DESKTOP_PORT=19290
APPTUNNEL_PORT=8897
LINKEASE_LOCAL_API=/var/run/linkease.sock
APP_DIR=/koolshare/linkease
APPS_PORT_FORWARD="http://127.0.0.1:${DESKTOP_PORT}"

export SERVER_HOST=0.0.0.0
export SERVER_PORT=${DESKTOP_PORT}
export SERVER_MODE=release
export SERVER_BASE_PATH=/apps/
export LINKEASE_EDITION=router-lite
export KAIPLUS_ENABLED=1
export KAIPLUS_BIN=${APP_DIR}/kaiplus/bin/kaiplus_bin
export KAIPLUS_STATIC_DIR=${APP_DIR}/kaiplus/www
export KAIPLUS_DEFAULTS_DIR=${APP_DIR}/kaiplus/defaults
export KAIPLUS_SYSTEM_ROLE=asusgo
export KAIPLUS_BASE_PATH=/apps/kaiplus/
export KAIPLUS_ADDR=127.0.0.1:19291
export KAIPLUS_PROXY_TARGET=http://127.0.0.1:19291
export KAIPLUS_WORKSPACE_TOOL_BINARY=${APP_DIR}/kaiplus/helpers/kaiplus_workspace_tool
export KAIPLUS_WORKSPACE_TOOL_INSTALL_DIR=${APP_DIR}/kaiplus/helpers
export REASONIX_CREDENTIALS_STORE=file

read_persisted_data_disk(){
	persisted_config=${APP_DIR}/data/bootstrap/system/data-root.json
	[ -f "$persisted_config" ] || return 0
	persisted_data_disk="$(sed -n 's/.*"selectedDisk"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$persisted_config" | head -n 1)"
	if [ -n "$persisted_data_disk" ] && [ -d "$persisted_data_disk" ]; then
		resolved_data_disk="$persisted_data_disk"
	fi
}

persist_migrated_betterapps_disk(){
	[ -n "$resolved_data_disk" ] || return 0
	[ -n "$migrated_from_betterapps" ] || return 0
	[ -n "$linkease_data_disk" ] && return 0
	dbus set linkease_data_disk="$resolved_data_disk" >/dev/null 2>&1
}

resolve_linkease_data_disk(){
	resolved_data_disk=""
	migrated_from_betterapps=""

	if [ -n "$linkease_data_disk" ] && [ -d "$linkease_data_disk" ]; then
		resolved_data_disk="$linkease_data_disk"
		return 0
	fi

	if [ -n "$linkease_data_root_parent" ] && [ -d "$linkease_data_root_parent" ]; then
		resolved_data_disk="$linkease_data_root_parent"
		return 0
	fi

	case "$linkease_data_root" in
	*/.linkease_data)
		resolved_data_disk="${linkease_data_root%/.linkease_data}"
		if [ -n "$resolved_data_disk" ] && [ -d "$resolved_data_disk" ]; then
			return 0
		fi
		resolved_data_disk=""
		;;
	esac

	if [ -n "$betterapps_data_disk" ] && [ -d "$betterapps_data_disk" ]; then
		resolved_data_disk="$betterapps_data_disk"
		migrated_from_betterapps=1
		return 0
	fi

	if [ -n "$betterapps_data_root_parent" ] && [ -d "$betterapps_data_root_parent" ]; then
		resolved_data_disk="$betterapps_data_root_parent"
		migrated_from_betterapps=1
		return 0
	fi

	case "$betterapps_data_root" in
	*/.linkease_data)
		resolved_data_disk="${betterapps_data_root%/.linkease_data}"
		if [ -n "$resolved_data_disk" ] && [ -d "$resolved_data_disk" ]; then
			migrated_from_betterapps=1
			return 0
		fi
		resolved_data_disk=""
		;;
	esac

	read_persisted_data_disk
	return 0
}

configure_data_paths(){
	resolve_linkease_data_disk
	persist_migrated_betterapps_disk

	if [ -n "$resolved_data_disk" ]; then
		export LINKEASE_BOOTSTRAP_FALLBACK=0
		export LINKEASE_DATA_DISK="$resolved_data_disk"
		export LINKEASE_DATA_ROOT=${LINKEASE_DATA_DISK}/.linkease_data
		export LINKEASE_RECYCLE_ROOT=${LINKEASE_DATA_DISK}/.linkease_recycle
	else
		export LINKEASE_BOOTSTRAP_FALLBACK=1
		export LINKEASE_DATA_DISK=
		export LINKEASE_DATA_ROOT=${APP_DIR}/data/bootstrap
		export LINKEASE_RECYCLE_ROOT=
	fi

	export USER_DATA_PATH=${LINKEASE_DATA_ROOT}/users/admin
	export SYSTEM_DATA_PATH=${LINKEASE_DATA_ROOT}/system
	export TEMP_PATH=${LINKEASE_DATA_ROOT}/tmp
	export KAIPLUS_HOME=${LINKEASE_DATA_ROOT}/kaiplus
}

configure_data_paths

ensure_dirs(){
	if [ "$LINKEASE_BOOTSTRAP_FALLBACK" = "1" ]; then
		mkdir -p "$USER_DATA_PATH" "$SYSTEM_DATA_PATH" "$TEMP_PATH" "$KAIPLUS_HOME"
	else
		mkdir -p "$USER_DATA_PATH" "$SYSTEM_DATA_PATH" "$TEMP_PATH" "$KAIPLUS_HOME" "$LINKEASE_RECYCLE_ROOT"
	fi
}

schedule_httpd_restart(){
	(sleep 3; service restart_httpd >/dev/null 2>&1) &
}

ensure_apps_forward(){
	current_forward="$(nvram get apps_port_forward 2>/dev/null)"
	[ "$current_forward" = "$APPS_PORT_FORWARD" ] && return 0
	nvram set apps_port_forward="$APPS_PORT_FORWARD" >/dev/null 2>&1 || return 1
	nvram commit >/dev/null 2>&1 || return 1
	logger "[软件中心]: 初始化LinkEase访问入口，稍后重启httpd！"
	schedule_httpd_restart
}

start_desktop(){
	start-stop-daemon -S -q -b -m -p $DESKTOP_PID_FILE -x $DESKTOP_BIN
}

start_apptunnel(){
	start-stop-daemon -S -q -b -m -p $APPTUNNEL_PID_FILE -x $APPTUNNEL_BIN -- --deviceAddr :$APPTUNNEL_PORT --localApi $LINKEASE_LOCAL_API
}

start_ee(){
	ensure_dirs || return 1
	ensure_apps_forward || return 1
	kill_ee
	start_desktop
	start_apptunnel
	[ ! -L "/koolshare/init.d/S99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/S99linkease.sh
	[ ! -L "/koolshare/init.d/N99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/N99linkease.sh
}

kill_ee(){
	killall link-ease >/dev/null 2>&1
	killall linkease-desktop >/dev/null 2>&1
	killall apptunnel-client >/dev/null 2>&1
	killall kaiplus_bin >/dev/null 2>&1
	rm -f $DESKTOP_PID_FILE $APPTUNNEL_PID_FILE >/dev/null 2>&1
}

load_iptables(){
	iptables -S | grep "${DESKTOP_PORT}\\|${APPTUNNEL_PORT}" | sed 's/-A/iptables -D/g' > /tmp/linkease_clean_iptables.sh && chmod 777 /tmp/linkease_clean_iptables.sh && /tmp/linkease_clean_iptables.sh && rm /tmp/linkease_clean_iptables.sh >/dev/null 2>&1
	iptables -t filter -I INPUT -p tcp --dport ${DESKTOP_PORT} -j ACCEPT >/dev/null 2>&1
	iptables -t filter -I INPUT -p tcp --dport ${APPTUNNEL_PORT} -j ACCEPT >/dev/null 2>&1
}

del_iptables(){
	iptables -S | grep "${DESKTOP_PORT}\\|${APPTUNNEL_PORT}" | sed 's/-A/iptables -D/g' > /tmp/linkease_clean_iptables.sh && chmod 777 /tmp/linkease_clean_iptables.sh && /tmp/linkease_clean_iptables.sh && rm /tmp/linkease_clean_iptables.sh >/dev/null 2>&1
}

case $ACTION in
start)
	if [ "$linkease_enable" == "1" ];then
		logger "[软件中心]: 启动LinkEase插件！"
		kill_ee
		start_ee
		load_iptables
	else
		logger "[软件中心]: LinkEase插件未开启，不启动！"
	fi
	;;
start_nat)
	load_iptables
	;;
*)
	if [ "$linkease_enable" == "1" ];then
		kill_ee
		start_ee
		load_iptables
		http_response "$1"
	else
		kill_ee
		del_iptables
		http_response "$1"
	fi
	;;
esac
```

- [ ] **Step 2: Replace `linkease_status.sh` with full status logic**

Use this file content:

```sh
#!/bin/sh

desktop_pid="$(pidof linkease-desktop)"
apptunnel_pid="$(pidof apptunnel-client)"
health_url="http://127.0.0.1:19290/apps/api/v1/health"

if [ -z "$desktop_pid" ] && [ -z "$apptunnel_pid" ]; then
	echo "LinkEase full 未运行"
	exit 0
fi

if [ -z "$desktop_pid" ]; then
	echo "【警告】：LinkEase full 主服务未运行，apptunnel-client 运行中"
	exit 0
fi

if [ -z "$apptunnel_pid" ]; then
	echo "【警告】：LinkEase full 主服务运行中，旧版8897入口未运行"
	exit 0
fi

if command -v curl >/dev/null 2>&1; then
	if curl -fsS --connect-timeout 2 "$health_url" >/dev/null 2>&1; then
		echo "LinkEase full 运行正常，/apps/ 与8897入口已启动"
	else
		echo "LinkEase full 进程运行中，/apps/ 健康检查未就绪"
	fi
else
	echo "LinkEase full 进程运行中，未找到curl，跳过/apps/健康检查"
fi
```

- [ ] **Step 3: Run syntax and contract tests**

Run:

```bash
sh -n linkease/scripts/linkease_config.sh
sh -n linkease/scripts/linkease_status.sh
python3 -m unittest tests.test_linkease_config_contract -v
python3 -m unittest discover -s tests -v
```

Expected: all commands pass. The `mise` trust warning may appear in this worktree and can be ignored if Python tests pass.

- [ ] **Step 4: Commit runtime lifecycle changes**

```bash
git add linkease/scripts/linkease_config.sh linkease/scripts/linkease_status.sh
git commit -m "feat: run linkease full services on asuswrt"
```

## Task 3: Add Installer and Uninstaller Contract Tests

**Files:**
- Create: `tests/test_install_uninstall_contract.py`
- Test: `linkease/install.sh`
- Test: `linkease/uninstall.sh`

- [ ] **Step 1: Write failing installer/uninstaller tests**

Create `tests/test_install_uninstall_contract.py` with:

```python
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "linkease" / "install.sh"
UNINSTALL = ROOT / "linkease" / "uninstall.sh"


class LinkEaseInstallUninstallContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.install = INSTALL.read_text(encoding="utf-8")
        cls.uninstall = UNINSTALL.read_text(encoding="utf-8")

    def test_install_keeps_linkease_identity_and_full_binary_names(self):
        self.assertIn("module=${DIR##*/}", self.install)
        self.assertIn('local TITLE="易有云"', self.install)
        self.assertIn("DESKTOP_BIN=linkease-desktop", self.install)
        self.assertIn("APPTUNNEL_BIN=apptunnel-client", self.install)
        self.assertIn("APP_DIR=/koolshare/linkease", self.install)

    def test_install_rejects_non_arm64_full_runtime(self):
        self.assertIn("platform_arch_test()", self.install)
        self.assertIn("uname -m", self.install)
        self.assertIn("aarch64", self.install)
        self.assertIn("arm64", self.install)
        self.assertIn("LinkEase full首版仅支持arm64/aarch64", self.install)

    def test_install_stops_legacy_and_full_processes(self):
        for process in ["link-ease", "linkease-desktop", "apptunnel-client", "kaiplus_bin"]:
            self.assertIn(f"killall {process}", self.install)

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

    def test_uninstall_removes_full_and_betterapps_leftovers(self):
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
        ]
        for item in expected:
            self.assertIn(item, self.uninstall)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_install_uninstall_contract -v
```

Expected: fails because current installer still installs only `link-ease`, has no arm64 full gate, and does not migrate BetterApps state.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_install_uninstall_contract.py
git commit -m "test: cover linkease full install contract"
```

## Task 4: Implement Install and Uninstall Migration

**Files:**
- Modify: `linkease/install.sh`
- Modify: `linkease/uninstall.sh`
- Test: `tests/test_install_uninstall_contract.py`

- [ ] **Step 1: Update installer constants and architecture gate**

In `linkease/install.sh`, add these constants after `module=${DIR##*/}`:

```sh
DESKTOP_BIN=linkease-desktop
APPTUNNEL_BIN=apptunnel-client
APP_DIR=/koolshare/linkease
```

Add this function before `platform_test()`:

```sh
platform_arch_test(){
	local ARCH=$(uname -m)
	case "$ARCH" in
		aarch64|arm64)
			echo_date "CPU架构：${ARCH}，符合LinkEase full首版安装要求！"
			;;
		*)
			echo_date "LinkEase full首版仅支持arm64/aarch64，当前架构：${ARCH}"
			echo_date "32位ARM和低内存设备请继续使用lite或旧版LinkEase。"
			exit_install 1
			;;
	esac
}
```

Call it in `install()` after `platform_test`:

```sh
install(){
	get_model
	get_fw_type
	platform_test
	platform_arch_test
	install_now
}
```

- [ ] **Step 2: Add BetterApps cleanup and dbus migration functions**

Add these functions before `install_now()`:

```sh
remove_betterapps_legacy(){
	rm -rf /koolshare/init.d/*betterapps.sh
	rm -rf /koolshare/init.d/*BetterApps.sh
	rm -rf /koolshare/bin/BetterApps
	rm -rf /koolshare/betterapps
	rm -rf /koolshare/res/icon-betterapps.png
	rm -rf /koolshare/res/icon-BetterApps.png
	rm -rf /koolshare/scripts/betterapps*.sh
	rm -rf /koolshare/scripts/BetterApps*.sh
	rm -rf /koolshare/webs/Module_betterapps.asp
	rm -rf /koolshare/webs/Module_BetterApps.asp
	rm -rf /koolshare/scripts/uninstall_betterapps.sh
	rm -rf /koolshare/scripts/uninstall_BetterApps.sh

	dbus remove betterapps_enable
	dbus remove BetterApps_enable
	dbus remove betterapps_version
	dbus remove BetterApps_version
	dbus remove softcenter_module_betterapps_version
	dbus remove softcenter_module_betterapps_install
	dbus remove softcenter_module_betterapps_name
	dbus remove softcenter_module_betterapps_title
	dbus remove softcenter_module_betterapps_description
	dbus remove softcenter_module_BetterApps_version
	dbus remove softcenter_module_BetterApps_install
	dbus remove softcenter_module_BetterApps_name
	dbus remove softcenter_module_BetterApps_title
	dbus remove softcenter_module_BetterApps_description
}

migrate_dbus_value_if_empty(){
	local SRC_KEY=$1
	local DST_KEY=$2
	local DST_VAL=$(dbus get "$DST_KEY")
	local SRC_VAL=$(dbus get "$SRC_KEY")
	if [ -z "$DST_VAL" ] && [ -n "$SRC_VAL" ]; then
		dbus set "$DST_KEY=$SRC_VAL"
	fi
}

migrate_betterapps_dbus(){
	migrate_dbus_value_if_empty betterapps_data_disk linkease_data_disk
	migrate_dbus_value_if_empty betterapps_data_root_parent linkease_data_root_parent
	migrate_dbus_value_if_empty betterapps_data_root linkease_data_root
}
```

- [ ] **Step 3: Update install file copy and process stop behavior**

Inside `install_now()`, replace the old process stop block with:

```sh
	local ENABLE=$(dbus get ${module}_enable)
	if [ "${ENABLE}" == "1" -o -n "$(pidof link-ease)" -o -n "$(pidof ${DESKTOP_BIN})" -o -n "$(pidof ${APPTUNNEL_BIN})" ];then
		echo_date "安装前先关闭${TITLE}插件，以保证更新成功！"
		killall link-ease >/dev/null 2>&1
		killall ${DESKTOP_BIN} >/dev/null 2>&1
		killall ${APPTUNNEL_BIN} >/dev/null 2>&1
		killall kaiplus_bin >/dev/null 2>&1
	fi
```

Immediately after removing init links, call migration and cleanup:

```sh
	find /koolshare/init.d -name "*${module}.sh" | xargs rm -rf >/dev/null 2>&1
	migrate_betterapps_dbus
	remove_betterapps_legacy
```

Replace the KaiPlus copy block with:

```sh
	if [ -d "/tmp/${module}/kaiplus" ];then
		rm -rf /koolshare/linkease/kaiplus
		mkdir -p /koolshare/linkease
		cp -rf /tmp/${module}/kaiplus /koolshare/linkease/
	fi
```

Replace chmod lines for binaries with:

```sh
	chmod 755 /koolshare/bin/${DESKTOP_BIN} >/dev/null 2>&1
	chmod 755 /koolshare/bin/${APPTUNNEL_BIN} >/dev/null 2>&1
	chmod 755 /koolshare/bin/link-ease >/dev/null 2>&1 || true
	chmod 755 /koolshare/linkease/kaiplus/bin/kaiplus_bin >/dev/null 2>&1 || true
	chmod 755 /koolshare/linkease/kaiplus/helpers/kaiplus_workspace_tool >/dev/null 2>&1 || true
	find /koolshare/linkease/kaiplus/defaults -type f -path '*/scripts/*' -exec chmod 755 {} \; >/dev/null 2>&1 || true
```

- [ ] **Step 4: Replace `uninstall.sh` cleanup with full cleanup**

Update `linkease/uninstall.sh` to include:

```sh
#!/bin/sh
source /koolshare/scripts/base.sh

cd /tmp
killall link-ease >/dev/null 2>&1
killall linkease-desktop >/dev/null 2>&1
killall apptunnel-client >/dev/null 2>&1
killall kaiplus_bin >/dev/null 2>&1

rm -rf /koolshare/init.d/*linkease.sh
rm -rf /koolshare/init.d/*LinkEase.sh
rm -rf /koolshare/bin/linkease-desktop
rm -rf /koolshare/bin/apptunnel-client
rm -rf /koolshare/bin/link-ease
rm -rf /koolshare/bin/linkease-plugins
rm -rf /koolshare/bin/linkease-media
rm -rf /koolshare/bin/heif-converter
rm -rf /koolshare/linkease
rm -rf /koolshare/res/icon-linkease.png
rm -rf /koolshare/scripts/linkease*.sh
rm -rf /koolshare/webs/Module_linkease.asp
rm -rf /koolshare/scripts/uninstall_linkease.sh
rm -rf /tmp/linkease*

rm -rf /koolshare/init.d/*betterapps.sh
rm -rf /koolshare/init.d/*BetterApps.sh
rm -rf /koolshare/bin/BetterApps
rm -rf /koolshare/betterapps
rm -rf /koolshare/res/icon-betterapps.png
rm -rf /koolshare/res/icon-BetterApps.png
rm -rf /koolshare/scripts/betterapps*.sh
rm -rf /koolshare/scripts/BetterApps*.sh
rm -rf /koolshare/webs/Module_betterapps.asp
rm -rf /koolshare/webs/Module_BetterApps.asp
rm -rf /koolshare/scripts/uninstall_betterapps.sh
rm -rf /koolshare/scripts/uninstall_BetterApps.sh
rm -rf /tmp/betterapps*
rm -rf /tmp/BetterApps*

dbus remove linkease_enable
dbus remove linkease_version
dbus remove softcenter_module_linkease_version
dbus remove softcenter_module_linkease_install
dbus remove softcenter_module_linkease_name
dbus remove softcenter_module_linkease_title
dbus remove softcenter_module_linkease_description

dbus remove betterapps_enable
dbus remove BetterApps_enable
dbus remove betterapps_version
dbus remove BetterApps_version
dbus remove softcenter_module_betterapps_version
dbus remove softcenter_module_betterapps_install
dbus remove softcenter_module_betterapps_name
dbus remove softcenter_module_betterapps_title
dbus remove softcenter_module_betterapps_description
dbus remove softcenter_module_BetterApps_version
dbus remove softcenter_module_BetterApps_install
dbus remove softcenter_module_BetterApps_name
dbus remove softcenter_module_BetterApps_title
dbus remove softcenter_module_BetterApps_description
```

- [ ] **Step 5: Run syntax and contract tests**

Run:

```bash
sh -n linkease/install.sh
sh -n linkease/uninstall.sh
python3 -m unittest tests.test_install_uninstall_contract -v
python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit installer changes**

```bash
git add linkease/install.sh linkease/uninstall.sh
git commit -m "feat: install linkease full asus runtime"
```

## Task 5: Update ASUSWRT Web UI Contracts and Page

**Files:**
- Modify: `tests/test_module_linkease_scripts.py`
- Modify: `linkease/webs/Module_linkease.asp`

- [ ] **Step 1: Add failing UI contract tests**

Append these tests to `ModuleLinkEaseScriptOrderTest` in `tests/test_module_linkease_scripts.py`:

```python
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
```

- [ ] **Step 2: Run UI tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_module_linkease_scripts -v
```

Expected: fails because the page still points primary links to `8897`.

- [ ] **Step 3: Update `generate_link()` in ASP page**

Replace the current `generate_link()` function with:

```javascript
        function generate_link() {
            var webite = E("linkease_website");
            var guide = E("linkease_guide");
            var legacy = E("linkease_legacy");
            var full_url = "/apps/";
            var legacy_url = "http://" + r_lan_ipaddr + ":8897";
            webite.href = full_url;
            guide.href = full_url;
            legacy.href = legacy_url;
            if (dbus["linkease_enable"] != "1") {
                webite.style.display = "none";
                guide.style.display = "none";
                legacy.style.display = "none";
            } else {
                webite.style.display = "";
                guide.style.display = "";
                legacy.style.display = "";
            }
        }
```

In the management link row, change the labels to:

```html
                                                    <a type="button" id="linkease_guide" class="linkease_btn"
                                                        target="_blank">配置中心</a>
                                                    <a type="button" id="linkease_website" class="linkease_btn" href=""
                                                        target="_blank">打开LinkEase</a>
                                                    <a type="button" id="linkease_legacy" class="linkease_btn" href=""
                                                        target="_blank">旧版入口</a>
```

- [ ] **Step 4: Run UI and full test suite**

Run:

```bash
python3 -m unittest tests.test_module_linkease_scripts -v
python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit UI changes**

```bash
git add tests/test_module_linkease_scripts.py linkease/webs/Module_linkease.asp
git commit -m "feat: point linkease ui to full apps entry"
```

## Task 6: Add Full Artifact Staging to Build Script

**Files:**
- Modify: `tests/test_build_script.py`
- Modify: `build.py`
- Modify: `config.json.js`

- [ ] **Step 1: Add failing build script tests**

Replace `tests/test_build_script.py` with:

```python
import json
import py_compile
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BuildScriptTest(unittest.TestCase):
    def test_build_script_compiles_with_python3(self):
        py_compile.compile(str(ROOT / "build.py"), doraise=True)

    def test_config_keeps_linkease_identity_and_declares_full_artifacts(self):
        config = json.loads((ROOT / "config.json.js").read_text(encoding="utf-8"))
        self.assertEqual(config["module"], "linkease")
        self.assertEqual(config["home_url"], "Module_linkease.asp")
        self.assertIn("full_artifact_url", config)
        self.assertIn("full_artifact_sha256", config)

    def test_build_module_can_stage_full_artifacts_from_directory(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("linkease_build", ROOT / "build.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp) / "repo"
            artifact_dir = Path(temp) / "artifact"
            temp_root.mkdir()
            artifact_dir.mkdir()

            for name in ["build.py", "config.json.js"]:
                (temp_root / name).write_bytes((ROOT / name).read_bytes())
            module_dir = temp_root / "linkease"
            module_dir.mkdir()
            for child in ["install.sh", "uninstall.sh"]:
                (module_dir / child).write_text("#!/bin/sh\n", encoding="utf-8")
            for child in ["bin", "scripts", "webs", "res"]:
                (module_dir / child).mkdir()
            (module_dir / "version").write_text("0.0.0\n", encoding="utf-8")

            (artifact_dir / "linkease-desktop").write_text("desktop", encoding="utf-8")
            (artifact_dir / "apptunnel-client").write_text("apptunnel", encoding="utf-8")
            (artifact_dir / "kaiplus").mkdir()
            (artifact_dir / "kaiplus" / "bin").mkdir(parents=True)
            (artifact_dir / "kaiplus" / "bin" / "kaiplus_bin").write_text("kai", encoding="utf-8")

            conf = module.build_module(root=temp_root, artifact_dir=artifact_dir, skip_download=True)

            self.assertEqual(conf["module"], "linkease")
            self.assertTrue((module_dir / "bin" / "linkease-desktop").is_file())
            self.assertTrue((module_dir / "bin" / "apptunnel-client").is_file())
            self.assertTrue((module_dir / "kaiplus" / "bin" / "kaiplus_bin").is_file())

            with tarfile.open(temp_root / "linkease.tar.gz", "r:gz") as tf:
                names = set(tf.getnames())
            self.assertIn("linkease/bin/linkease-desktop", names)
            self.assertIn("linkease/bin/apptunnel-client", names)
            self.assertIn("linkease/kaiplus/bin/kaiplus_bin", names)
```

- [ ] **Step 2: Run build tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_build_script -v
```

Expected: fails because `build.py` has no `artifact_dir` or `skip_download` support and config does not declare full artifact fields.

- [ ] **Step 3: Update config metadata**

Add these fields to `config.json.js` while keeping valid JSON:

```json
    "full_artifact_url": "https://github.com/linkease/linkease-desktop/releases/download/prebuild/linkease-asus-full-arm64-v3.0.0.tar.gz",
    "full_artifact_sha256": "6ae7ddbe28ca07e9e2a51476b0ae7ffdef1d1fa3d4f9b48260be700c1fff0833"
```

Release jobs can override these values with `--full-artifact-url` and `--full-artifact-sha256` when publishing a different artifact.

- [ ] **Step 4: Add artifact staging support to `build.py`**

Add these constants near the top:

```python
FULL_ARTIFACT_FIELDS = ("full_artifact_url", "full_artifact_sha256")
FULL_BINARIES = ("linkease-desktop", "apptunnel-client")
```

Add these helpers:

```python
def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def copy_tree(src, dst):
    src = Path(src)
    dst = Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def stage_full_artifacts(module_dir, artifact_dir):
    module_dir = Path(module_dir)
    artifact_dir = Path(artifact_dir)
    bin_dir = module_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    for binary in FULL_BINARIES:
        src = artifact_dir / binary
        if not src.is_file():
            raise FileNotFoundError(f"missing full runtime binary: {src}")
        dst = bin_dir / binary
        shutil.copy2(src, dst)
        make_executable(dst)

    kaiplus_src = artifact_dir / "kaiplus"
    if not kaiplus_src.is_dir():
        raise FileNotFoundError(f"missing kaiplus directory: {kaiplus_src}")
    copy_tree(kaiplus_src, module_dir / "kaiplus")
    for script in (module_dir / "kaiplus").glob("defaults/**/scripts/*"):
        if script.is_file():
            make_executable(script)
```

Update `build_module` signature to:

```python
def build_module(root=None, artifact_dir=None, full_artifact_url=None, full_artifact_sha256=None, skip_download=False):
```

Inside `build_module`, before writing version and packaging:

```python
    if artifact_dir:
        stage_full_artifacts(root / module, artifact_dir)
    elif not skip_download:
        raise ValueError("full artifact staging requires --artifact-dir or an implemented release download")
```

Update `main()` parser with:

```python
    parser.add_argument("--artifact-dir", help="Directory containing linkease-desktop, apptunnel-client, and kaiplus")
    parser.add_argument("--full-artifact-url", help="Release artifact URL recorded into config metadata")
    parser.add_argument("--full-artifact-sha256", help="Release artifact sha256 recorded into config metadata")
    parser.add_argument("--skip-download", action="store_true", help="Skip release artifact download; useful for tests")
```

Call:

```python
    conf = build_module(
        artifact_dir=args.artifact_dir,
        full_artifact_url=args.full_artifact_url,
        full_artifact_sha256=args.full_artifact_sha256,
        skip_download=args.skip_download,
    )
```

- [ ] **Step 5: Run build tests**

Run:

```bash
python3 -m unittest tests.test_build_script -v
python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit build changes**

```bash
git add build.py config.json.js tests/test_build_script.py
git commit -m "build: stage linkease full asus artifacts"
```

## Task 7: Package Verification and Final Checks

**Files:**
- Read: all modified files
- Generated locally: `linkease.tar.gz`

- [ ] **Step 1: Build a local artifact staging directory from existing arm64 outputs**

If the existing `linkease-desktop` worktree is available, prepare a staging directory:

```bash
rm -rf /tmp/linkease-asus-full-arm64
mkdir -p /tmp/linkease-asus-full-arm64
cp /var/tmp/agentflow-dev/linkos-um/bc32-work-for-asus/linkease-desktop/release-openwrt/work/aarch64/linkease-desktop /tmp/linkease-asus-full-arm64/linkease-desktop
cp /var/tmp/agentflow-dev/linkos-um/bc32-work-for-asus/linkease-desktop/release-openwrt/work/aarch64/apptunnel-client /tmp/linkease-asus-full-arm64/apptunnel-client
cp -a /var/tmp/agentflow-dev/linkos-um/bc32-work-for-asus/linkease-desktop/release-openwrt/work/aarch64/kaiplus /tmp/linkease-asus-full-arm64/kaiplus
```

Expected: `/tmp/linkease-asus-full-arm64` contains the two binaries and `kaiplus`.

- [ ] **Step 2: Run complete local verification**

Run:

```bash
sh -n linkease/install.sh
sh -n linkease/uninstall.sh
sh -n linkease/scripts/linkease_config.sh
sh -n linkease/scripts/linkease_status.sh
python3 -m unittest discover -s tests -v
python3 build.py --artifact-dir /tmp/linkease-asus-full-arm64 --skip-download
tar -tzf linkease.tar.gz | grep -E '^(linkease/)?(linkease/bin/linkease-desktop|linkease/bin/apptunnel-client|linkease/kaiplus/)'
```

Expected:

- Shell syntax checks pass.
- Python tests pass.
- `python3 build.py` prints `build done linkease.tar.gz`.
- Tar listing includes `linkease/bin/linkease-desktop`, `linkease/bin/apptunnel-client`, and `linkease/kaiplus/`.

- [ ] **Step 3: Inspect package metadata**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
conf = json.loads(Path("config.json.js").read_text(encoding="utf-8"))
print(conf["module"])
print(conf["home_url"])
print(conf["title"])
print(conf["version"])
print(conf["md5"])
PY
```

Expected:

```text
linkease
Module_linkease.asp
易有云
2.17.5
```

Then run:

```bash
python3 - <<'PY'
import json
import re
from pathlib import Path
conf = json.loads(Path("config.json.js").read_text(encoding="utf-8"))
assert re.fullmatch(r"[0-9a-f]{32}", conf["md5"]), conf["md5"]
print("md5 ok")
PY
```

- [ ] **Step 4: Commit generated metadata if `config.json.js` md5 changed**

If `python3 build.py` updates only `config.json.js` md5 and `linkease/version`, commit source metadata but do not commit `linkease.tar.gz` unless this repository intentionally tracks release tarballs.

Run:

```bash
git status --short
```

If `config.json.js` or `linkease/version` changed:

```bash
git add config.json.js linkease/version
git commit -m "chore: update linkease package metadata"
```

- [ ] **Step 5: Final status**

Run:

```bash
git status --short --branch
git log --oneline -6
```

Expected: worktree clean or only generated release artifacts ignored/untracked by explicit choice. Recent commits show tests, runtime, install, UI, build, and optional metadata commits.

## Self-Review Notes

Spec coverage:

- Module identity remains `linkease`: covered in Tasks 3, 4, 6, and 7.
- BetterApps no longer installed or registered: covered in Tasks 3 and 4.
- Full runtime starts `linkease-desktop`, `apptunnel-client`, and KaiPlus: covered in Tasks 1 and 2.
- `/apps/` full UI and 8897 legacy entry: covered in Tasks 1, 2, and 5.
- KaiPlus `asusgo`: covered in Tasks 1 and 2.
- BetterApps data disk migration: covered in Tasks 1, 3, and 4.
- Unsupported architecture clear failure: covered in Tasks 3 and 4.
- Tests and local package verification: covered in Tasks 1 through 7.

No unresolved placeholders are intentionally left in this plan. Release metadata has concrete default values and can be overridden by release automation.
