# rogsoft LinkEase ASUSWRT Full Edition Design

Date: 2026-07-11

## Context

ASUSWRT currently has an existing Koolshare software center plugin in this repository:

- Module: `linkease`
- Web page: `linkease/webs/Module_linkease.asp`
- Runtime binary: `/koolshare/bin/link-ease`
- Legacy service port: `8897`
- Existing lite toggle: `linkease_simple`

The newer `rogsoft-BetterApps` plugin proved the `linkease-desktop` router UI runtime on ASUSWRT:

- Module: `betterapps`
- Runtime binary: `/koolshare/bin/BetterApps`
- UI entry: `/apps/`
- Runtime port: `19290`
- KaiPlus profile: `asusgo`
- Data root: `.linkease_data`
- Recycle root: `.linkease_recycle`

The product direction is to stop using BetterApps as an ASUSWRT plugin. The new full edition should be released as LinkEase itself. OpenWrt also uses LinkEase as the package identity, so this keeps the product name consistent across ASUSWRT and OpenWrt.

## Goals

1. Keep the ASUSWRT plugin identity as `linkease`.
2. Build the ASUSWRT full edition as the successor to the old LinkEase plugin, not as BetterApps.
3. Fold the proven BetterApps ASUSWRT runtime behavior into LinkEase.
4. Manage `linkease-desktop`, KaiPlus, and `apptunnel-client` from the LinkEase plugin lifecycle.
5. Preserve the old LinkEase 8897 entry where possible.
6. Support only `arm64/aarch64` in the first full edition.
7. Leave 32-bit ARM and low-memory devices on lite or old LinkEase paths for now.

## Non-Goals

1. Do not continue publishing an ASUSWRT BetterApps plugin.
2. Do not attempt 32-bit ARM full support in the first implementation.
3. Do not redesign the ASUSWRT software center UI beyond the controls required for full LinkEase.
4. Do not rewrite OpenWrt packaging as part of this ASUSWRT plugin change.

## Recommended Approach

Implement LinkEase full edition directly in `rogsoft_LinkEase`.

The module remains `linkease`, but its full runtime changes from the old `link-ease` binary to a managed bundle:

- `/koolshare/bin/linkease-desktop`
- `/koolshare/bin/apptunnel-client`
- `/koolshare/linkease/kaiplus`

The old BetterApps scripts are not copied as a separate plugin. Their useful logic is migrated into LinkEase naming, paths, dbus keys, and UI.

## Runtime Architecture

`linkease_config.sh` owns the full runtime lifecycle.

When `linkease_enable=1`, it starts:

1. `linkease-desktop`
   - Binary: `/koolshare/bin/linkease-desktop`
   - Host: `0.0.0.0`
   - Port: `19290`
   - Base path: `/apps/`
   - Edition: `router-lite` for the first ASUSWRT full build
   - KaiPlus enabled

2. `apptunnel-client`
   - Binary: `/koolshare/bin/apptunnel-client`
   - Device address: `:8897`
   - Local API socket: `/var/run/linkease.sock`

3. KaiPlus
   - Runtime binary: `/koolshare/linkease/kaiplus/bin/kaiplus_bin`
   - Static files: `/koolshare/linkease/kaiplus/www`
   - Defaults: `/koolshare/linkease/kaiplus/defaults`
   - System role: `asusgo`
   - Base path: `/apps/kaiplus/`
   - Internal address: `127.0.0.1:19291`

The ASUSWRT software center `/apps/` reverse proxy should point to:

```text
http://127.0.0.1:19290
```

This follows the behavior already proven in BetterApps.

## Data Paths

The full edition uses LinkEase-owned dbus names and data paths.

Preferred data source order:

1. `linkease_data_disk`, if set and valid.
2. `linkease_data_root_parent`, if set and valid.
3. Parent of `linkease_data_root`, when it ends with `/.linkease_data`.
4. Migrated BetterApps values:
   - `betterapps_data_disk`
   - `betterapps_data_root_parent`
   - parent of `betterapps_data_root` when it ends with `/.linkease_data`
5. Persisted bootstrap config under `/koolshare/linkease/data/bootstrap/system/data-root.json`.

When a valid disk is found:

```text
LINKEASE_DATA_ROOT=<disk>/.linkease_data
LINKEASE_RECYCLE_ROOT=<disk>/.linkease_recycle
USER_DATA_PATH=<disk>/.linkease_data/users/admin
SYSTEM_DATA_PATH=<disk>/.linkease_data/system
TEMP_PATH=<disk>/.linkease_data/tmp
KAIPLUS_HOME=<disk>/.linkease_data/kaiplus
```

When no disk is available, the UI can start in bootstrap mode:

```text
LINKEASE_BOOTSTRAP_FALLBACK=1
LINKEASE_DATA_ROOT=/koolshare/linkease/data/bootstrap
```

This matches the BetterApps bootstrap behavior while moving ownership to LinkEase.

## Install Behavior

`install.sh` should:

1. Validate the Koolshare ASUSWRT platform as it does today.
2. Validate first-edition full architecture as `aarch64` or `arm64`.
3. Stop old LinkEase processes before replacing files:
   - `link-ease`
   - `linkease-desktop`
   - `apptunnel-client`
   - `kaiplus_bin`
4. Remove BetterApps plugin files and software center metadata.
5. Copy LinkEase full files into `/koolshare`.
6. Install KaiPlus under `/koolshare/linkease/kaiplus`.
7. Install init links:
   - `/koolshare/init.d/S99linkease.sh`
   - `/koolshare/init.d/N99linkease.sh`
8. Set `softcenter_module_linkease_*` metadata.
9. Restart LinkEase if it was enabled before upgrade.

The install script should not leave a BetterApps module behind.

## Uninstall Behavior

`uninstall.sh` should stop and remove LinkEase full files:

- `/koolshare/bin/linkease-desktop`
- `/koolshare/bin/apptunnel-client`
- legacy `/koolshare/bin/link-ease`
- `/koolshare/linkease`
- LinkEase scripts, web page, icon, and init links

It should also remove known BetterApps leftovers and metadata, because full LinkEase supersedes BetterApps on ASUSWRT.

## UI Behavior

The ASUSWRT page remains `Module_linkease.asp`.

Controls:

- Enable/disable LinkEase.
- Keep a lite/legacy option visible only if the implementation can still route unsupported devices to lite behavior.
- Show full runtime status.
- Provide a primary entry for `/apps/`.
- Keep a secondary legacy LinkEase entry for `http://<lan-ip>:8897`.

Status should reflect both required processes:

- `linkease-desktop`
- `apptunnel-client`

The `/apps/api/v1/health` health check is useful for full UI readiness. Process checks are still needed because `apptunnel-client` is separate.

## Build Behavior

The repository should not depend on the old committed `link-ease` binary for full edition.

The build should support staging full ASUSWRT artifacts from a release bundle or explicit local paths:

- `linkease-desktop`
- `apptunnel-client`
- `kaiplus`

The first implementation can use an arm64-only full artifact. Unsupported architectures should fail clearly at install time.

The package remains:

```text
linkease.tar.gz
```

The metadata remains:

```text
module=linkease
home_url=Module_linkease.asp
```

## Migration

Migration must be idempotent.

On install:

1. Preserve `linkease_enable`.
2. Copy valid BetterApps data disk settings into LinkEase settings when LinkEase settings are empty.
3. Remove BetterApps software center registration.
4. Remove BetterApps init links and files.
5. Do not delete user data under `.linkease_data`.

This lets a router with BetterApps installed move to LinkEase full without losing selected disk state.

## Compatibility Policy

First full edition supports arm64 ASUSWRT targets only.

32-bit ARM and low-memory devices are not part of the first full build. They remain on the existing lite or old LinkEase path until there is a separate 32-bit build and verification plan.

The installer must make this explicit instead of installing unusable binaries.

## Testing Plan

Add focused contract tests before changing behavior:

1. `linkease_config.sh`
   - Uses `/koolshare/bin/linkease-desktop`.
   - Uses `/koolshare/bin/apptunnel-client`.
   - Exports `/apps/` and KaiPlus `asusgo` variables.
   - Resolves LinkEase data disk values.
   - Migrates BetterApps data disk values.
   - Starts and stops both full processes.

2. `install.sh`
   - Keeps module identity as `linkease`.
   - Rejects unsupported full architectures.
   - Removes BetterApps plugin files and metadata.
   - Installs KaiPlus into `/koolshare/linkease/kaiplus`.
   - Restarts LinkEase when previously enabled.

3. `uninstall.sh`
   - Removes full LinkEase files.
   - Cleans BetterApps leftovers.

4. `Module_linkease.asp`
   - Keeps safe script loading order.
   - Points full UI to `/apps/`.
   - Keeps the 8897 legacy link.

Verification commands:

```sh
python3 -m unittest discover -s tests -v
sh -n linkease/install.sh
sh -n linkease/uninstall.sh
sh -n linkease/scripts/linkease_config.sh
sh -n linkease/scripts/linkease_status.sh
python3 build.py
```

Router smoke test, when an arm64 ASUSWRT device is available:

1. Install `linkease.tar.gz`.
2. Confirm the software center shows LinkEase, not BetterApps.
3. Enable LinkEase.
4. Confirm `linkease-desktop`, `apptunnel-client`, and `kaiplus_bin` are running.
5. Confirm `/apps/` loads.
6. Confirm port `8897` is listening.
7. Confirm selected data disk persists through restart.
8. Uninstall and confirm files and metadata are removed.

## Risks

1. ASUSWRT devices vary in firmware behavior around `/apps/` reverse proxy and `nvram apps_port_forward`.
2. Old LinkEase users may expect the 8897 page to be the primary UI.
3. Full runtime memory use can exceed old 32-bit or low-memory devices.
4. The current repository has limited tests, so shell contract tests are required before changing runtime scripts.

## Acceptance Criteria

1. ASUSWRT package is still named `linkease`.
2. BetterApps is no longer installed or registered as a plugin.
3. On arm64 ASUSWRT, enabling LinkEase starts full runtime services.
4. `/apps/` opens LinkEase full UI.
5. `8897` remains available for legacy LinkEase access.
6. KaiPlus runs with the `asusgo` profile.
7. BetterApps data disk state is migrated when present.
8. Unsupported architectures fail clearly instead of installing broken binaries.
9. Local tests and shell syntax checks pass.
