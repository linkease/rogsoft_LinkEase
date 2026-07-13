# rogsoft LinkEase Edition Selector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the ASUSWRT LinkEase simple-mode switch with Standard, Full, and Lite edition selection, and make Full open through `/apps/` reverse proxy when supported.

**Architecture:** Add `linkease_edition=standard|full|lite` as the primary dbus setting while preserving `linkease_simple` for compatibility. The ASP page owns edition selection and URL generation; `install.sh` owns initial migration/defaults; `linkease_config.sh` owns normalized runtime startup and reverse-proxy support reporting; `linkease_status.sh` reports edition-aware health.

**Tech Stack:** ASUSWRT/Koolshare shell scripts, dbus, nvram, ASP/JavaScript, Python `unittest`, existing `build.py` packaging.

## Global Constraints

- Use `rtk` before shell commands in this repo.
- Make code changes only in `/projects/workspace-linkease-ubuntu/linkease-github/rogsoft/rogsoft_LinkEase`.
- Keep KaiPlus split: LinkEase must not start, copy, chmod, remove, or embed KaiPlus runtime files.
- Keep KaiPlus direct port `8189` and base path `/apps/kaiplus/` unchanged.
- Keep LinkEase Full port `19290`, `apptunnel-client` legacy port `8897`, and Full base path `/apps/`.
- Standard and Lite must not start `linkease-desktop` or `apptunnel-client`.
- Full must start `linkease-desktop` and `apptunnel-client`.
- Fresh installs default to `linkease_edition=standard`.
- Preserve old `linkease_simple`: selected Lite writes `linkease_simple=1`; Standard and Full write `linkease_simple=0`.
- Full architecture limits must not block Standard/Lite installation when the legacy `link-ease` runtime is usable.
- Rebuild `linkease.tar.gz` and update `config.json.js` md5 after runtime/page changes.

---

## File Structure

- `linkease/webs/Module_linkease.asp`: edition selector UI, dbus read/write compatibility, Full URL builder, reverse-proxy warning.
- `linkease/install.sh`: default/migrate `linkease_edition`; relax Full-only architecture rejection into Full availability metadata.
- `linkease/scripts/linkease_config.sh`: normalize edition; start Standard, Full, or Lite runtime; report `/apps/` proxy support.
- `linkease/scripts/linkease_status.sh`: edition-aware status text and health checks.
- `tests/test_module_linkease_scripts.py`: ASP contract tests.
- `tests/test_install_uninstall_contract.py`: install/migration/architecture contract tests.
- `tests/test_linkease_config_contract.py`: runtime branching and proxy support contract tests.
- `config.json.js`: package md5 after rebuild.
- `linkease.tar.gz`: rebuilt ASUSWRT package.

---

### Task 1: ASP Edition Selector And Full URL Contract

**Files:**
- Modify: `tests/test_module_linkease_scripts.py`
- Modify: `linkease/webs/Module_linkease.asp`

**Interfaces:**
- Consumes: dbus keys `linkease_enable`, `linkease_edition`, `linkease_simple`, `linkease_apps_proxy_supported`, `linkease_apps_proxy_hint`.
- Produces: Browser functions `normalize_linkease_edition(value, simple)`, `set_linkease_edition(edition)`, `selected_linkease_edition()`, `build_full_url()`, `generate_link()`.

- [ ] **Step 1: Write failing ASP contract tests**

Add these tests to `tests/test_module_linkease_scripts.py`:

```python
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

    def test_full_url_uses_proxy_or_direct_port(self):
        expected = [
            'function current_browser_origin()',
            'return window.location.protocol + "//" + window.location.host;',
            'function linkease_full_proxy_supported()',
            'return dbus["linkease_apps_proxy_supported"] == "1";',
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
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
rtk python3 -m unittest tests.test_module_linkease_scripts -v
```

Expected: fails because `Module_linkease.asp` still has the old `linkease_simple` switch, hard-coded `var full_url = "/apps/";`, and no proxy hint.

- [ ] **Step 3: Implement the ASP page**

In `linkease/webs/Module_linkease.asp`, change the JavaScript config block to:

```js
        var r_lan_ipaddr = "<% nvram_get(lan_ipaddr); %>"
        var params_check = ["linkease_enable"];
        var params_input = ["linkease_edition"];
        var dbus = {}
```

Add these helper functions near `conf_to_obj()`:

```js
        function normalize_linkease_edition(edition, simple) {
            if (edition == "standard" || edition == "full" || edition == "lite") {
                return edition;
            }
            return simple == "1" ? "lite" : "standard";
        }

        function selected_linkease_edition() {
            var radios = document.getElementsByName("linkease_edition");
            for (var i = 0; i < radios.length; i++) {
                if (radios[i].checked) {
                    return radios[i].value;
                }
            }
            return "standard";
        }

        function set_linkease_edition(edition) {
            edition = normalize_linkease_edition(edition, "0");
            var radios = document.getElementsByName("linkease_edition");
            for (var i = 0; i < radios.length; i++) {
                radios[i].checked = radios[i].value == edition;
            }
        }
```

Update `conf_to_obj()` so it sets the radio selection:

```js
            set_linkease_edition(normalize_linkease_edition(dbus["linkease_edition"], dbus["linkease_simple"]));
```

Update `save()` after checkbox handling and before `showLoading()`:

```js
            dbus["linkease_edition"] = selected_linkease_edition();
            dbus["linkease_simple"] = dbus["linkease_edition"] == "lite" ? "1" : "0";
```

Add Full URL helpers before `generate_link()`:

```js
        function current_browser_origin() {
            return window.location.protocol + "//" + window.location.host;
        }

        function linkease_full_proxy_supported() {
            return dbus["linkease_apps_proxy_supported"] == "1";
        }

        function build_full_url() {
            if (linkease_full_proxy_supported()) {
                return current_browser_origin() + "/apps/";
            }
            return "http://" + r_lan_ipaddr + ":19290/apps/";
        }

        function update_proxy_hint() {
            var hint = E("linkease_proxy_hint");
            if (!hint) {
                return;
            }
            if (selected_linkease_edition() == "full" && !linkease_full_proxy_supported()) {
                hint.style.display = "";
            } else {
                hint.style.display = "none";
            }
        }
```

Update `generate_link()`:

```js
        function generate_link() {
            var webite = E("linkease_website");
            var linkease_guide = E("linkease_guide");
            var legacy = E("linkease_legacy");
            var full_url = build_full_url();
            var legacy_url = "http://" + r_lan_ipaddr + ":8897";
            webite.href = full_url;
            linkease_guide.href = full_url;
            legacy.href = legacy_url;
            update_proxy_hint();
            if (dbus["linkease_enable"] != "1") {
                webite.style.display = "none";
                linkease_guide.style.display = "none";
                legacy.style.display = "none";
            } else {
                webite.style.display = "";
                linkease_guide.style.display = "";
                legacy.style.display = "";
            }
        }
```

Replace the old simple switch row with:

```html
                                            <tr>
                                                <th>
                                                    <label>运行版本</label>
                                                </th>
                                                <td colspan="2">
                                                    <label><input type="radio" name="linkease_edition" value="standard" onclick="generate_link();"> Standard 版本</label>
                                                    <label style="margin-left:18px;"><input type="radio" name="linkease_edition" value="full" onclick="generate_link();"> Full 版本</label>
                                                    <label style="margin-left:18px;"><input type="radio" name="linkease_edition" value="lite" onclick="generate_link();"> 精简版本（内存小于512M推荐）</label>
                                                    <div id="linkease_proxy_hint" style="display:none;margin-top:8px;color:#FC0;">当前系统 httpd 不支持 /apps/ 反向代理，已使用端口直连。建议升级系统到最新版本以获得更好的访问体验。</div>
                                                </td>
                                            </tr>
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
rtk python3 -m unittest tests.test_module_linkease_scripts -v
```

Expected: all tests in `test_module_linkease_scripts.py` pass.

- [ ] **Step 5: Commit Task 1**

```bash
rtk git add tests/test_module_linkease_scripts.py linkease/webs/Module_linkease.asp
rtk git commit -m "feat: add linkease edition selector UI"
```

---

### Task 2: Install Defaults And Full Architecture Availability

**Files:**
- Modify: `tests/test_install_uninstall_contract.py`
- Modify: `linkease/install.sh`

**Interfaces:**
- Consumes: dbus keys `linkease_edition`, `linkease_simple`.
- Produces: install-time defaults and Full availability keys `linkease_full_supported`, `linkease_full_support_hint`.

- [ ] **Step 1: Write failing install tests**

Replace `test_install_rejects_non_arm64_full_runtime` with:

```python
    def test_install_records_full_arch_support_without_blocking_standard_lite(self):
        expected = [
            "detect_full_runtime_support()",
            "linkease_full_supported=1",
            "linkease_full_supported=0",
            "dbus set linkease_full_supported=",
            "dbus set linkease_full_support_hint=",
            "LinkEase Full 仅支持 arm64/aarch64",
        ]
        for item in expected:
            self.assertIn(item, self.install)
        self.assertNotIn("platform_arch_test", self.install)
        self.assertNotIn("LinkEase full首版仅支持arm64/aarch64", self.install)

    def test_install_initializes_edition_without_overwriting_existing_value(self):
        expected = [
            "init_linkease_edition()",
            'if [ -z "$(dbus get ${module}_edition)" ];then',
            'if [ "$(dbus get ${module}_simple)" = "1" ];then',
            "dbus set ${module}_edition=lite",
            "dbus set ${module}_edition=standard",
        ]
        for item in expected:
            self.assertIn(item, self.install)
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
rtk python3 -m unittest tests.test_install_uninstall_contract.InstallUninstallContractTest.test_install_records_full_arch_support_without_blocking_standard_lite tests.test_install_uninstall_contract.InstallUninstallContractTest.test_install_initializes_edition_without_overwriting_existing_value -v
```

Expected: fails because install still has `platform_arch_test` and no edition initializer.

- [ ] **Step 3: Implement install defaults**

Remove the call to `platform_arch_test` from `install()`.

Replace the `platform_arch_test()` function with:

```sh
detect_full_runtime_support(){
	local ARCH=$(uname -m)
	case "${ARCH}" in
		aarch64|arm64)
			dbus set linkease_full_supported=1
			dbus set linkease_full_support_hint=""
			;;
		*)
			dbus set linkease_full_supported=0
			dbus set linkease_full_support_hint="LinkEase Full 仅支持 arm64/aarch64，当前设备可继续使用 Standard 或精简版本。"
			;;
	esac
}
```

Add before `install_now()`:

```sh
init_linkease_edition(){
	if [ -z "$(dbus get ${module}_edition)" ];then
		if [ "$(dbus get ${module}_simple)" = "1" ];then
			dbus set ${module}_edition=lite
		else
			dbus set ${module}_edition=standard
		fi
	fi
}
```

Call both functions in `install_now()` before writing software-center metadata:

```sh
	detect_full_runtime_support
	init_linkease_edition
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
rtk python3 -m unittest tests.test_install_uninstall_contract -v
```

Expected: install/uninstall contract tests pass.

- [ ] **Step 5: Commit Task 2**

```bash
rtk git add tests/test_install_uninstall_contract.py linkease/install.sh
rtk git commit -m "feat: initialize linkease edition on install"
```

---

### Task 3: Runtime Edition Branching And Proxy Support Reporting

**Files:**
- Modify: `tests/test_linkease_config_contract.py`
- Modify: `linkease/scripts/linkease_config.sh`

**Interfaces:**
- Consumes: `linkease_edition`, `linkease_simple`, `linkease_enable`, `linkease_full_supported`.
- Produces: shell variables `LINKEASE_ACTIVE_EDITION`, dbus keys `linkease_apps_proxy_supported`, `linkease_apps_proxy_hint`.

- [ ] **Step 1: Write failing runtime contract tests**

Add these tests to `tests/test_linkease_config_contract.py`:

```python
    def test_runtime_normalizes_standard_full_lite_editions(self):
        expected = [
            "normalize_linkease_edition()",
            'standard|full|lite) echo "$linkease_edition" ;;',
            '[ "$linkease_simple" = "1" ] && echo lite || echo standard',
            'LINKEASE_ACTIVE_EDITION="$(normalize_linkease_edition)"',
            'dbus set linkease_edition="$LINKEASE_ACTIVE_EDITION"',
            'dbus set linkease_simple=1',
            'dbus set linkease_simple=0',
        ]
        for item in expected:
            self.assertIn(item, self.config)

    def test_runtime_has_separate_standard_full_lite_starters(self):
        expected = [
            "start_standard()",
            "start_full()",
            "start_lite()",
            "case \"$LINKEASE_ACTIVE_EDITION\" in",
            "standard)",
            "full)",
            "lite)",
            "start_standard",
            "start_full",
            "start_lite",
        ]
        for item in expected:
            self.assertIn(item, self.config)

    def test_full_reports_apps_proxy_support_and_lite_standard_do_not_start_full(self):
        expected = [
            "ensure_apps_forward()",
            "dbus set linkease_apps_proxy_supported=1",
            "dbus set linkease_apps_proxy_supported=0",
            "dbus set linkease_apps_proxy_hint=",
            "当前系统 httpd 不支持 /apps/ 反向代理",
        ]
        for item in expected:
            self.assertIn(item, self.config)

        standard_block = re.search(r"start_standard\\(\\)\\{([\\s\\S]*?)\\n\\}", self.config)
        lite_block = re.search(r"start_lite\\(\\)\\{([\\s\\S]*?)\\n\\}", self.config)
        self.assertIsNotNone(standard_block)
        self.assertIsNotNone(lite_block)
        self.assertNotIn("start_desktop", standard_block.group(1))
        self.assertNotIn("start_apptunnel", standard_block.group(1))
        self.assertNotIn("start_desktop", lite_block.group(1))
        self.assertNotIn("start_apptunnel", lite_block.group(1))
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
rtk python3 -m unittest tests.test_linkease_config_contract.LinkEaseConfigContractTest.test_runtime_normalizes_standard_full_lite_editions tests.test_linkease_config_contract.LinkEaseConfigContractTest.test_runtime_has_separate_standard_full_lite_starters tests.test_linkease_config_contract.LinkEaseConfigContractTest.test_full_reports_apps_proxy_support_and_lite_standard_do_not_start_full -v
```

Expected: fails because `linkease_config.sh` always starts Full.

- [ ] **Step 3: Implement runtime branching**

Add after constants:

```sh
LEGACY_BIN=/koolshare/bin/link-ease
LINKEASE_ACTIVE_EDITION=
```

Add edition helpers before `configure_data_paths`:

```sh
normalize_linkease_edition(){
	case "$linkease_edition" in
		standard|full|lite) echo "$linkease_edition" ;;
		*) [ "$linkease_simple" = "1" ] && echo lite || echo standard ;;
	esac
}

persist_active_edition(){
	LINKEASE_ACTIVE_EDITION="$(normalize_linkease_edition)"
	dbus set linkease_edition="$LINKEASE_ACTIVE_EDITION" >/dev/null 2>&1
	if [ "$LINKEASE_ACTIVE_EDITION" = "lite" ]; then
		dbus set linkease_simple=1 >/dev/null 2>&1
	else
		dbus set linkease_simple=0 >/dev/null 2>&1
	fi
}
```

Call before `configure_data_paths`:

```sh
persist_active_edition
```

Update `ensure_apps_forward()`:

```sh
ensure_apps_forward(){
	current_forward="$(nvram get apps_port_forward 2>/dev/null)"
	if [ "$current_forward" = "$APPS_PORT_FORWARD" ]; then
		dbus set linkease_apps_proxy_supported=1 >/dev/null 2>&1
		dbus set linkease_apps_proxy_hint="" >/dev/null 2>&1
		return 0
	fi
	if nvram set apps_port_forward="$APPS_PORT_FORWARD" >/dev/null 2>&1 && nvram commit >/dev/null 2>&1; then
		dbus set linkease_apps_proxy_supported=1 >/dev/null 2>&1
		dbus set linkease_apps_proxy_hint="" >/dev/null 2>&1
		logger "[软件中心]: 初始化LinkEase访问入口，稍后重启httpd！"
		schedule_httpd_restart
		return 0
	fi
	dbus set linkease_apps_proxy_supported=0 >/dev/null 2>&1
	dbus set linkease_apps_proxy_hint="当前系统 httpd 不支持 /apps/ 反向代理，建议升级系统到最新版本。" >/dev/null 2>&1
	return 0
}
```

Add runtime starters:

```sh
start_standard(){
	ensure_dirs || return 1
	kill_ee
	start-stop-daemon -S -q -b -x $LEGACY_BIN
	[ ! -L "/koolshare/init.d/S99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/S99linkease.sh
	[ ! -L "/koolshare/init.d/N99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/N99linkease.sh
}

start_full(){
	ensure_dirs || return 1
	ensure_apps_forward || return 1
	kill_ee
	start_desktop
	start_apptunnel
	[ ! -L "/koolshare/init.d/S99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/S99linkease.sh
	[ ! -L "/koolshare/init.d/N99linkease.sh" ] && ln -sf /koolshare/scripts/linkease_config.sh /koolshare/init.d/N99linkease.sh
}

start_lite(){
	export LINKEASE_SIMPLE=1
	start_standard
}

start_active_edition(){
	case "$LINKEASE_ACTIVE_EDITION" in
		standard)
			start_standard
			;;
		full)
			start_full
			;;
		lite)
			start_lite
			;;
	esac
}
```

Change startup branches to call `start_active_edition` instead of `start_ee`.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
rtk python3 -m unittest tests.test_linkease_config_contract -v
rtk sh -n linkease/scripts/linkease_config.sh
```

Expected: all config contract tests pass; shell syntax check exits 0.

- [ ] **Step 5: Commit Task 3**

```bash
rtk git add tests/test_linkease_config_contract.py linkease/scripts/linkease_config.sh
rtk git commit -m "feat: branch linkease runtime by edition"
```

---

### Task 4: Edition-Aware Status

**Files:**
- Modify: `tests/test_linkease_config_contract.py`
- Modify: `linkease/scripts/linkease_status.sh`

**Interfaces:**
- Consumes: `dbus get linkease_edition`, `dbus get linkease_apps_proxy_supported`.
- Produces: status text mentioning Standard, Full, or Lite.

- [ ] **Step 1: Write failing status tests**

Update `test_status_checks_full_processes_and_health_endpoint` and add:

```python
    def test_status_is_edition_aware(self):
        expected = [
            "eval `dbus export linkease`",
            "normalize_linkease_edition()",
            'case "$LINKEASE_ACTIVE_EDITION" in',
            "LinkEase Standard",
            "LinkEase Full",
            "LinkEase Lite",
            "当前系统未启用 /apps/ 反向代理，建议升级系统",
        ]
        for item in expected:
            self.assertIn(item, self.status)
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
rtk python3 -m unittest tests.test_linkease_config_contract.LinkEaseConfigContractTest.test_status_checks_full_processes_and_health_endpoint tests.test_linkease_config_contract.LinkEaseConfigContractTest.test_status_is_edition_aware -v
```

Expected: fails because status script only reports Full.

- [ ] **Step 3: Implement edition-aware status**

Replace `linkease/scripts/linkease_status.sh` with:

```sh
#!/bin/sh
eval `dbus export linkease`
source /koolshare/scripts/base.sh

normalize_linkease_edition(){
	case "$linkease_edition" in
		standard|full|lite) echo "$linkease_edition" ;;
		*) [ "$linkease_simple" = "1" ] && echo lite || echo standard ;;
	esac
}

LINKEASE_ACTIVE_EDITION="$(normalize_linkease_edition)"

legacy_pid="$(pidof link-ease)"
desktop_pid="$(pidof linkease-desktop)"
apptunnel_pid="$(pidof apptunnel-client)"
health_url="http://127.0.0.1:19290/apps/api/v1/health"

case "$LINKEASE_ACTIVE_EDITION" in
	standard)
		if [ -n "$legacy_pid" ]; then
			http_response "LinkEase Standard 运行正常"
		else
			http_response "LinkEase Standard 未运行"
		fi
		;;
	lite)
		if [ -n "$legacy_pid" ]; then
			http_response "LinkEase Lite 运行正常"
		else
			http_response "LinkEase Lite 未运行"
		fi
		;;
	full)
		if [ -z "$desktop_pid" ] && [ -z "$apptunnel_pid" ]; then
			http_response "LinkEase Full 未运行"
			exit 0
		fi
		if [ -z "$desktop_pid" ]; then
			http_response "【警告】：LinkEase Full 主服务未运行，apptunnel-client 运行中"
			exit 0
		fi
		if [ -z "$apptunnel_pid" ]; then
			http_response "【警告】：LinkEase Full 主服务运行中，旧版8897入口未运行"
			exit 0
		fi
		if command -v curl >/dev/null 2>&1; then
			if curl -fsS --connect-timeout 2 "$health_url" >/dev/null 2>&1; then
				if [ "$linkease_apps_proxy_supported" = "1" ]; then
					status_msg="LinkEase Full 运行正常，/apps/ 与8897入口已启动"
				else
					status_msg="LinkEase Full 运行正常，当前系统未启用 /apps/ 反向代理，建议升级系统"
				fi
			else
				status_msg="LinkEase Full 进程运行中，/apps/ 健康检查未就绪"
			fi
		else
			status_msg="LinkEase Full 进程运行中，未找到curl，跳过/apps/健康检查"
		fi
		http_response "$status_msg"
		;;
esac
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
rtk python3 -m unittest tests.test_linkease_config_contract -v
rtk sh -n linkease/scripts/linkease_status.sh
```

Expected: tests pass; shell syntax check exits 0.

- [ ] **Step 5: Commit Task 4**

```bash
rtk git add tests/test_linkease_config_contract.py linkease/scripts/linkease_status.sh
rtk git commit -m "feat: report linkease status by edition"
```

---

### Task 5: Full Verification, Packaging, And Deployment Prep

**Files:**
- Modify: `config.json.js`
- Modify: `linkease.tar.gz`

**Interfaces:**
- Consumes: existing `build.py --artifact-dir`.
- Produces: rebuilt package with updated md5.

- [ ] **Step 1: Run complete local verification**

Run:

```bash
rtk python3 -m unittest discover tests
rtk sh -n linkease/scripts/linkease_config.sh linkease/scripts/linkease_status.sh linkease/install.sh linkease/uninstall.sh
rtk git diff --check
```

Expected: all tests pass; all shell syntax checks exit 0; `git diff --check` prints no errors.

- [ ] **Step 2: Rebuild ASUSWRT package**

Run:

```bash
rtk python3 build.py --artifact-dir /projects/workspace-linkease-ubuntu/linkease-github/linkease-desktop/release-single/linkease
```

Expected: command prints `build done linkease.tar.gz md5=<new-md5>`.

- [ ] **Step 3: Validate tarball and md5**

Run:

```bash
rtk tar -tzf linkease.tar.gz | rg 'linkease/(webs/Module_linkease.asp|scripts/linkease_config.sh|scripts/linkease_status.sh|bin/linkease-desktop|bin/apptunnel-client|bin/link-ease)'
rtk md5sum linkease.tar.gz
rtk rg '"md5":' config.json.js
```

Expected: tarball contains the listed files; `md5sum` matches `config.json.js`.

- [ ] **Step 4: Clean build staging artifacts**

If build.py leaves expanded runtime artifacts in the source tree, remove only generated files and restore tracked placeholders:

```bash
rtk rm -rf __pycache__ tests/__pycache__
rtk git status --short
```

Expected: only intended tracked files remain modified: scripts, page, tests, `config.json.js`, and `linkease.tar.gz`.

- [ ] **Step 5: Commit package update**

```bash
rtk git add config.json.js linkease.tar.gz
rtk git commit -m "chore: rebuild linkease asus package"
```

- [ ] **Step 6: Final local verification before push/deploy**

Run:

```bash
rtk python3 -m unittest discover tests
rtk sh -n linkease/scripts/linkease_config.sh linkease/scripts/linkease_status.sh linkease/install.sh linkease/uninstall.sh
rtk git status --short
```

Expected: tests pass, shell syntax checks exit 0, and worktree is clean.

- [ ] **Step 7: Deploy to ASUS test router when requested**

Use the established test target:

```bash
rtk mkdir -p /tmp/linkease-linkease-deploy
rtk cp /projects/workspace-linkease-ubuntu/linkease-github/rogsoft/rogsoft_LinkEase/linkease.tar.gz /tmp/linkease-linkease-deploy/linkease.tar.gz
rtk ssh -p 2222 admin@192.168.3.247 'rm -rf /tmp/linkease-deploy /tmp/linkease; mkdir -p /tmp/linkease-deploy'
rtk scp -O -P 2222 /tmp/linkease-linkease-deploy/linkease.tar.gz admin@192.168.3.247:/tmp/linkease-deploy/
rtk ssh -p 2222 admin@192.168.3.247 'cd /tmp && tar -xzf /tmp/linkease-deploy/linkease.tar.gz -C /tmp && sh /tmp/linkease/install.sh >/tmp/linkease-deploy/install-linkease.log 2>&1; rc=$?; tail -n 120 /tmp/linkease-deploy/install-linkease.log; exit $rc'
```

Expected: installer exits 0 and reports LinkEase installation finished.

- [ ] **Step 8: Remote smoke checks when deployed**

Run:

```bash
rtk ssh -p 2222 admin@192.168.3.247 '
  echo "--- dbus ---";
  dbus get linkease_edition;
  dbus get linkease_simple;
  dbus get linkease_apps_proxy_supported;
  echo "--- page markers ---";
  egrep -n "linkease_edition|build_full_url|linkease_proxy_hint|Standard 版本|Full 版本|精简版本" /koolshare/webs/Module_linkease.asp | head -n 80;
  echo "--- processes ---";
  ps | egrep "(link-ease|linkease-desktop|apptunnel-client)" | grep -v grep || true;
  echo "--- ports ---";
  netstat -lntp 2>/dev/null | egrep "(8897|19290)" || true
'
```

Expected: page markers exist; runtime processes match the selected edition; Full has port `19290` and `8897` when selected.
