# rogsoft ASUSWRT LinkEase and KaiPlus Split Design

Date: 2026-07-12

## Context

The ASUSWRT/Koolshare plugin workspace contains two independent rogsoft repositories:

- `rogsoft_LinkEase`
- `rogsoft_KaiPlus`

`rogsoft_LinkEase` already contains the LinkEase full plugin skeleton. It was adapted from the old `rogsoft-BetterApps` implementation and currently still treats KaiPlus as embedded LinkEase runtime content:

- `linkease_config.sh` exports `KAIPLUS_ENABLED=1`.
- KaiPlus runtime paths point under `/koolshare/linkease/kaiplus`.
- LinkEase install copies `/tmp/linkease/kaiplus` into `/koolshare/linkease/kaiplus`.
- LinkEase uninstall stops and removes `kaiplus_bin`.
- Tests assert the embedded KaiPlus contract.

`rogsoft_KaiPlus` exists but currently has no plugin implementation. The old source of the KaiPlus ASUSWRT runtime is:

```text
/projects/workspace-linkease-ubuntu/linkease-github/linkease-desktop/rogsoft-BetterApps/betterapps/kaiplus
```

OpenWrt has already moved to separate LinkEase and KaiPlus packages. ASUSWRT should follow the same product model.

## Goals

1. Split KaiPlus into its own ASUSWRT/Koolshare plugin in `rogsoft_KaiPlus`.
2. Keep LinkEase and KaiPlus installable and removable independently.
3. Remove embedded KaiPlus runtime ownership from `rogsoft_LinkEase`.
4. Let LinkEase Desktop show and open KaiPlus when the KaiPlus plugin is installed.
5. Preserve the direct KaiPlus route:

```text
http://<router-ip>:8189/apps/kaiplus/
```

6. Preserve the LinkEase Desktop reverse-proxy route:

```text
http://<router-ip>:<LinkEase Desktop port>/apps/kaiplus/
```

7. Keep ASUSWRT behavior aligned with OpenWrt where practical.
8. Keep migration from old BetterApps and the current embedded LinkEase full builds safe and idempotent.

## Non-Goals

1. Do not make LinkEase depend on the KaiPlus package.
2. Do not make KaiPlus depend on the LinkEase package.
3. Do not continue publishing BetterApps as the ASUSWRT product identity.
4. Do not add a new LinkEase Desktop app registry mechanism in this first split if the existing embedded `kaiplusassets` registry is enough for the icon.
5. Do not support 32-bit ASUSWRT full runtime in this first split.
6. Do not remove user data under `.linkease_data` during migration or uninstall.

## Recommended Approach

Use weak coupling, matching the OpenWrt split.

`rogsoft_KaiPlus` owns the KaiPlus service, files, ASUSWRT page, dbus keys, firewall rule, and direct port `8189`.

`rogsoft_LinkEase` owns only LinkEase Desktop and `apptunnel-client`. At Desktop startup it detects whether the KaiPlus plugin appears installed and then exports:

```sh
KAIPLUS_ENABLED=0
KAIPLUS_PROXY_TARGET=http://127.0.0.1:<kaiplus-port>
```

This keeps packages independent while allowing LinkEase Desktop to serve `/apps/kaiplus/` through the existing reverse proxy.

## LinkEase Plugin Changes

`rogsoft_LinkEase` should stop owning KaiPlus runtime files.

Remove or update these embedded-runtime behaviors:

- Do not require a staged `kaiplus` directory in `build.py`.
- Do not copy `/tmp/linkease/kaiplus` into `/koolshare/linkease/kaiplus`.
- Do not chmod `/koolshare/linkease/kaiplus/bin/kaiplus_bin`.
- Do not export `KAIPLUS_BIN`, `KAIPLUS_STATIC_DIR`, `KAIPLUS_DEFAULTS_DIR`, `KAIPLUS_HOME`, `KAIPLUS_ADDR`, or `KAIPLUS_BASE_PATH`.
- Do not start or stop KaiPlus as part of the LinkEase service lifecycle.
- Do not remove `/koolshare/kaiplus` or `/koolshare/bin/kaiplus_bin` in LinkEase uninstall.

Retain these LinkEase responsibilities:

- Start `linkease-desktop` on `0.0.0.0:19290`.
- Start `apptunnel-client` on the legacy `8897` entry.
- Keep `/apps/` forwarded to LinkEase Desktop.
- Keep LinkEase data root migration from old BetterApps dbus keys.
- Remove old BetterApps plugin files and metadata during LinkEase install.

Add a KaiPlus proxy resolver:

```sh
resolve_kaiplus_proxy_target() {
    KAIPLUS_PROXY_TARGET=""
    [ -x /koolshare/scripts/kaiplus_config.sh ] || return 0
    [ -x /koolshare/bin/kaiplus_bin ] || return 0

    kaiplus_port="$(dbus get kaiplus_port 2>/dev/null)"
    case "$kaiplus_port" in
        ''|*[!0-9]*) kaiplus_port=8189 ;;
    esac
    if [ "$kaiplus_port" -lt 1 ] 2>/dev/null || [ "$kaiplus_port" -gt 65535 ] 2>/dev/null; then
        kaiplus_port=8189
    fi

    KAIPLUS_PROXY_TARGET="http://127.0.0.1:${kaiplus_port}"
}
```

`linkease_config.sh` should call this before starting `linkease-desktop`.

## KaiPlus Plugin Design

`rogsoft_KaiPlus` should be a normal Koolshare plugin with module name `kaiplus`.

Expected package layout:

```text
kaiplus/
  install.sh
  uninstall.sh
  version
  bin/
    kaiplus_bin
  helpers/
    kaiplus_workspace_tool
  www/
    index.html
    assets/...
    logo.svg
  defaults/
    profiles/asusgo/...
  res/
    icon-kaiplus.png
  scripts/
    kaiplus_config.sh
    kaiplus_status.sh
  webs/
    Module_kaiplus.asp
```

Install destinations:

```text
/koolshare/bin/kaiplus_bin
/koolshare/kaiplus/helpers/kaiplus_workspace_tool
/koolshare/kaiplus/www
/koolshare/kaiplus/defaults
/koolshare/res/icon-kaiplus.png
/koolshare/scripts/kaiplus_config.sh
/koolshare/scripts/kaiplus_status.sh
/koolshare/webs/Module_kaiplus.asp
/koolshare/scripts/uninstall_kaiplus.sh
```

Runtime command:

```sh
/koolshare/bin/kaiplus_bin kaiplus-web \
  --addr "0.0.0.0:${KAIPLUS_PORT}" \
  --data-dir "$KAIPLUS_HOME" \
  --static-dir /koolshare/kaiplus/www \
  --defaults-dir /koolshare/kaiplus/defaults \
  --base-path "$KAIPLUS_BASE_PATH" \
  --system-role asusgo
```

Default runtime values:

```text
KAIPLUS_PORT=8189
KAIPLUS_BASE_PATH=/apps/kaiplus/
KAIPLUS_SYSTEM_ROLE=asusgo
REASONIX_CREDENTIALS_STORE=file
```

## KaiPlus Data Paths

KaiPlus should use dbus keys owned by `kaiplus`:

```text
kaiplus_enable
kaiplus_port
kaiplus_base_path
kaiplus_data_disk
kaiplus_data_root_parent
kaiplus_data_root
```

Preferred data source order:

1. `kaiplus_data_disk`, if set and valid.
2. `kaiplus_data_root_parent`, if set and valid.
3. Parent of `kaiplus_data_root`, when it ends with `/kaiplus` or `/.linkease_data/kaiplus`.
4. Existing LinkEase data disk keys, if valid:
   - `linkease_data_disk`
   - `linkease_data_root_parent`
   - parent of `linkease_data_root` when it ends with `/.linkease_data`
5. Existing BetterApps data disk keys, if valid:
   - `betterapps_data_disk`
   - `betterapps_data_root_parent`
   - parent of `betterapps_data_root` when it ends with `/.linkease_data`
6. Bootstrap fallback under `/koolshare/kaiplus/data/bootstrap`.

When a disk is available:

```text
KAIPLUS_HOME=<disk>/.linkease_data/kaiplus
```

When no disk is available:

```text
KAIPLUS_HOME=/koolshare/kaiplus/data/bootstrap/kaiplus
```

The plugin must create:

```text
$KAIPLUS_HOME/workspace
$KAIPLUS_HOME/cache
$KAIPLUS_HOME/config
$KAIPLUS_HOME/state
```

## KaiPlus Lifecycle

`kaiplus_config.sh` should:

1. Load dbus keys with `dbus export kaiplus`.
2. Normalize port and base path, defaulting to `8189` and `/apps/kaiplus/`.
3. Prepare data directories and helper token state.
4. Start `kaiplus_bin kaiplus-web` through `start-stop-daemon`.
5. Add init links:
   - `/koolshare/init.d/S99kaiplus.sh`
   - `/koolshare/init.d/N99kaiplus.sh`
6. Add an INPUT firewall rule for the configured port.
7. Stop only `kaiplus_bin` and remove only KaiPlus pid/firewall state on disable.

`uninstall.sh` should:

- Stop `kaiplus_bin`.
- Remove KaiPlus scripts, web page, icon, init links, and runtime files.
- Remove `softcenter_module_kaiplus_*` metadata.
- Remove `kaiplus_enable`, `kaiplus_version`, and runtime dbus keys.
- Preserve user data under external `.linkease_data` disks.
- Remove only bootstrap data under `/koolshare/kaiplus` when uninstalling plugin-owned files.

## Cross-Plugin Refresh

KaiPlus install, uninstall, enable, and disable may optionally refresh LinkEase Desktop when LinkEase is installed and enabled:

```sh
if [ "$(dbus get linkease_enable)" = "1" ] && [ -x /koolshare/scripts/linkease_config.sh ]; then
    ACTION=start sh /koolshare/scripts/linkease_config.sh start >/dev/null 2>&1 || true
fi
```

This is still weak coupling: KaiPlus does not require LinkEase, and LinkEase does not require KaiPlus. It only lets the LinkEase Desktop icon/proxy state update quickly after KaiPlus changes.

## Build Behavior

`rogsoft_LinkEase/build.py` should stage only:

- `linkease-desktop`
- `apptunnel-client`

The old full artifact may still contain a `kaiplus/` directory, but the LinkEase build should ignore it.

`rogsoft_KaiPlus/build.py` should stage:

- `kaiplus_bin`
- `kaiplus_workspace_tool`
- `www`
- `defaults`

The KaiPlus build can support either:

1. A local artifact directory containing these files.
2. A release tarball URL plus sha256.

The first implementation can mirror the existing LinkEase build style and require `--artifact-dir`, then add release download support later.

## UI Behavior

LinkEase page:

- Remains `Module_linkease.asp`.
- Opens `/apps/`.
- Reports `linkease-desktop` and `apptunnel-client` status.
- Does not report or manage KaiPlus process state.

KaiPlus page:

- Uses `Module_kaiplus.asp`.
- Has an enable toggle.
- Shows process status for `kaiplus_bin`.
- Shows the configured direct URL:

```text
http://<lan-ip>:8189/apps/kaiplus/
```

- Allows port and data disk/path settings if consistent with existing rogsoft UI patterns.

## Testing

`rogsoft_LinkEase` tests should change to assert:

- LinkEase no longer requires or copies `kaiplus`.
- LinkEase does not export embedded KaiPlus runtime variables.
- LinkEase exports `KAIPLUS_ENABLED=0`.
- LinkEase resolves `KAIPLUS_PROXY_TARGET` from an installed KaiPlus plugin.
- LinkEase uninstall does not remove `/koolshare/kaiplus` or `/koolshare/bin/kaiplus_bin`.
- Build script does not require `artifact_dir/kaiplus`.

`rogsoft_KaiPlus` tests should assert:

- Plugin identity is `kaiplus`.
- Install copies runtime files to `/koolshare/bin/kaiplus_bin` and `/koolshare/kaiplus`.
- Config defaults to port `8189`, base path `/apps/kaiplus/`, and role `asusgo`.
- Config starts `kaiplus-web` with `--base-path`.
- Status checks `kaiplus_bin` and direct URL.
- Uninstall removes plugin files but preserves external `.linkease_data` user data.
- Build script stages binary, helper, `www`, and `defaults`.

## Migration

Migration must be idempotent.

From old BetterApps:

- LinkEase install continues to remove BetterApps plugin files and migrate selected disk dbus values into LinkEase keys when empty.
- KaiPlus install can reuse BetterApps or LinkEase selected disk to keep `KAIPLUS_HOME` at `<disk>/.linkease_data/kaiplus`.
- No install script deletes `.linkease_data`.

From current embedded LinkEase full:

- KaiPlus install can copy or reuse data from existing `<disk>/.linkease_data/kaiplus`.
- KaiPlus install should not depend on `/koolshare/linkease/kaiplus` remaining present.
- Future LinkEase install stops removing `kaiplus_bin`, so upgrading LinkEase after installing KaiPlus will not kill the independent service.

## Acceptance Criteria

1. Installing LinkEase alone starts LinkEase Desktop and `apptunnel-client`; `/apps/` works.
2. Installing KaiPlus alone starts KaiPlus on `8189`; `/apps/kaiplus/` works directly.
3. Installing both shows KaiPlus in LinkEase Desktop and opens it through `/apps/kaiplus/`.
4. Uninstalling LinkEase does not uninstall KaiPlus.
5. Uninstalling KaiPlus does not uninstall LinkEase.
6. Old BetterApps files are removed by LinkEase migration without deleting external user data.
7. Tests pass in both rogsoft repositories.
