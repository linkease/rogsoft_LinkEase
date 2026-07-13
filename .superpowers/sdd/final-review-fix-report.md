# Final Review Fix Report

Date: 2026-07-13

## Fixed Findings

- Proxy support is conservative: successful `nvram` writes no longer mark `/apps/` as verified. Full keeps the `19290/apps/` direct fallback and an upgrade/direct-port hint.
- The edition UI consumes `linkease_full_supported` and `linkease_full_support_hint`. Selecting unavailable Full shows the reason and restores Standard before saving or linking.
- Primary management links use the Full URL only for supported Full; Standard and Lite use `http://<lan_ip>:8897`. The separate legacy entry remains.
- The firewall opens `19290` only for Full while retaining the legacy `8897` rule.

## TDD Evidence

- RED: the combined contract suite failed on all five new review contracts before implementation.
- RED: the direct-port wording test failed before the runtime hint was updated.
- GREEN: `rtk python3 -m unittest tests.test_module_linkease_scripts tests.test_linkease_config_contract -v` passed 26 tests.

## Verification

- `rtk sh -n linkease/scripts/linkease_config.sh` passed.
- `rtk git diff --check` passed.

## Scope

No package tarball or package metadata was changed. KaiPlus runtime handling remains untouched.
