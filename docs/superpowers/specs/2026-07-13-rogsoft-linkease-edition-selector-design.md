# rogsoft LinkEase Edition Selector Design

## Context

`rogsoft_LinkEase` is now the ASUSWRT/Koolshare package for LinkEase only. KaiPlus has been split into its own `rogsoft_KaiPlus` package, while LinkEase still owns LinkEase Desktop, `apptunnel-client`, the legacy `link-ease` binary, `/apps/` forwarding, and BetterApps migration cleanup.

The current LinkEase ASUS page still exposes `linkease_simple` as a boolean switch labeled:

```text
精简版（内存小于512M推荐）
```

That is no longer expressive enough. Users need to choose the runtime edition explicitly:

1. Standard version
2. Full version
3. Lite version

## Goals

1. Replace the boolean "simple" UX with an explicit edition selector.
2. Store the selected edition in a stable dbus key: `linkease_edition`.
3. Preserve compatibility with old `linkease_simple` users.
4. Make `linkease_config.sh` start the runtime that matches the selected edition.
5. For Full edition, prefer the new httpd reverse proxy path when available.
6. Fall back to direct LAN IP and Full port when reverse proxy support is unavailable.
7. Tell users to upgrade the system when their httpd does not support the better `/apps/` reverse proxy path.

## Non-Goals

1. Do not merge KaiPlus back into LinkEase.
2. Do not change KaiPlus direct port `8189` or base path `/apps/kaiplus/`.
3. Do not split LinkEase Standard, Full, and Lite into separate ASUSWRT packages.
4. Do not remove legacy `linkease_simple` immediately.
5. Do not delete user data under `.linkease_data`.

## Data Model

Introduce:

```sh
linkease_edition=standard|full|lite
```

Compatibility rules:

1. If `linkease_edition` is empty and `linkease_simple=1`, treat it as `lite`.
2. If `linkease_edition` is empty and `linkease_simple` is empty or `0`, treat it as `standard`.
3. Recommended default for fresh installs: `standard`.
4. On save, write both:
   - `linkease_edition=<selected>`
   - `linkease_simple=1` only when selected edition is `lite`; otherwise `0`

This keeps older scripts or user exports that still inspect `linkease_simple` from breaking.

## UI Design

Replace the existing `linkease_simple` switch row with an edition selector row:

```text
运行版本
[ Standard 版本 ] [ Full 版本 ] [ 精简版本 ]
```

The implementation can use ASUSWRT-friendly radio inputs or a select control. The control must be compact and consistent with the existing `FormTable` style.

Edition labels:

```text
Standard 版本
Full 版本
精简版本（内存小于512M推荐）
```

The page should keep the existing enable switch, status row, and management links.

For Full edition, show an additional hint when reverse proxy support is missing:

```text
当前系统 httpd 不支持 /apps/ 反向代理，已使用端口直连。建议升级系统到最新版本以获得更好的访问体验。
```

## Runtime Behavior

`linkease_config.sh` should normalize the selected edition before starting services:

```sh
normalize_linkease_edition(){
    case "$linkease_edition" in
        standard|full|lite) echo "$linkease_edition" ;;
        *) [ "$linkease_simple" = "1" ] && echo lite || echo standard ;;
    esac
}
```

The script should use the normalized edition for startup:

```text
standard -> start legacy Standard LinkEase runtime
full     -> start linkease-desktop and apptunnel-client
lite     -> start legacy LinkEase runtime with lite/simple compatibility enabled
```

The exact Standard and Lite command-line differences should follow the existing `link-ease` binary contract. If the current package only has a historical `linkease_simple` toggle and no separate binary, Lite should keep setting/exporting the compatibility value expected by `link-ease`.

Full edition continues to:

1. Start `linkease-desktop` on `0.0.0.0:19290`.
2. Start `apptunnel-client` on `8897`.
3. Export `SERVER_BASE_PATH=/apps/`.
4. Configure `apps_port_forward=http://127.0.0.1:19290`.
5. Detect the separately installed KaiPlus plugin and export `KAIPLUS_PROXY_TARGET` only when available.

Standard and Lite must not start `linkease-desktop` or `apptunnel-client`.

## Architecture Compatibility

The current package has an arm64/aarch64 gate because the first Full runtime only supported that architecture. With edition selection, installation must not reject the entire plugin only because Full is unavailable on a device.

Recommended behavior:

1. Standard and Lite follow the legacy `link-ease` binary support matrix.
2. Full requires `linkease-desktop` and `apptunnel-client` to be executable and compatible with the current architecture.
3. On unsupported Full architectures, keep the plugin installable, disable or warn on Full selection, and keep Standard/Lite usable.
4. If the final package cannot include a working legacy binary for a platform, the installer may still reject that platform with the existing platform message.

This matters because Lite is specifically intended for low-memory devices, and those are often the devices least likely to satisfy Full runtime assumptions.

## Full Edition URL Selection

The page should not hard-code `/apps/` as the only Full URL.

Add a browser-side URL builder:

```js
function current_browser_origin() {
    return window.location.protocol + "//" + window.location.host;
}

function build_full_url() {
    if (linkease_full_proxy_supported()) {
        return current_browser_origin() + "/apps/";
    }
    return "http://" + r_lan_ipaddr + ":19290/apps/";
}
```

The desired behavior:

1. If httpd supports reverse proxy, opening Full uses the current browser origin plus `/apps/`.
2. If httpd does not support reverse proxy, opening Full uses the router LAN IP and Full port.
3. The fallback still includes `/apps/`, because LinkEase Desktop is served with `SERVER_BASE_PATH=/apps/`.

## Reverse Proxy Capability

The runtime script already writes:

```sh
nvram set apps_port_forward="$APPS_PORT_FORWARD"
```

To make the browser decision reliable, expose capability/status through dbus fields updated by `linkease_config.sh`, for example:

```sh
linkease_apps_proxy_supported=1|0
linkease_apps_proxy_hint=<human readable hint>
```

Recommended detection order:

1. If setting `apps_port_forward` succeeds and the installed httpd supports that nvram contract, set `linkease_apps_proxy_supported=1`.
2. If the firmware/httpd is old or the contract cannot be verified, set `linkease_apps_proxy_supported=0`.
3. Do not fail Full startup only because reverse proxy is unavailable; use direct port fallback.

The exact httpd capability probe should be conservative. If the repo does not already have a reliable version probe, the first implementation can treat `apps_port_forward` write success as expected support, and still keep the direct-port fallback visible when health checks through `/apps/` fail.

## Install And Migration

`install.sh` should set default edition only when missing:

```sh
if [ -z "$(dbus get linkease_edition)" ]; then
    if [ "$(dbus get linkease_simple)" = "1" ]; then
        dbus set linkease_edition=lite
    else
        dbus set linkease_edition=standard
    fi
fi
```

BetterApps migration remains unchanged except where old values can help choose the initial edition. The install flow must continue removing old BetterApps plugin files without deleting user data.

## Status Display

`linkease_status.sh` should include the active edition in its message:

```text
LinkEase Standard 运行正常
LinkEase Full 运行正常，/apps/ 入口已启动
LinkEase Lite 运行正常
```

For Full edition with no reverse proxy support:

```text
LinkEase Full 运行正常，当前系统未启用 /apps/ 反向代理，建议升级系统
```

## Tests

Add or update contract tests for:

1. ASP page uses `linkease_edition` selector instead of editable/simple-only switch UX.
2. ASP page migrates old `linkease_simple` into selected edition.
3. ASP page builds Full URL from current browser origin when proxy is supported.
4. ASP page falls back to `http://<lan-ip>:19290/apps/` when proxy is unsupported.
5. ASP page displays the upgrade hint when proxy is unsupported.
6. `install.sh` initializes `linkease_edition` without overwriting an existing selection.
7. `install.sh` does not reject Standard/Lite users only because Full runtime is unavailable.
8. `linkease_config.sh` normalizes `standard|full|lite`.
9. Full starts `linkease-desktop` and `apptunnel-client`.
10. Standard and Lite do not start Full runtime processes.
11. Existing KaiPlus split behavior remains unchanged: LinkEase only exports `KAIPLUS_PROXY_TARGET` when KaiPlus is independently installed.

## Rollout

1. Implement tests first.
2. Update `Module_linkease.asp`.
3. Update install migration/defaults.
4. Update runtime script branching and proxy support dbus reporting.
5. Update status script.
6. Rebuild `linkease.tar.gz` and update `config.json.js` md5.
7. Deploy to the ASUS test router and verify:
   - Standard starts the expected legacy runtime.
   - Full opens through `/apps/` on new httpd.
   - Full falls back to LAN IP and `19290` when `/apps/` is unavailable.
   - Lite preserves old `linkease_simple` behavior.
