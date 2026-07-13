# Task 1 Report

## Result

Defined the failing LinkEase-only contract tests for the ASUSWRT KaiPlus split.

## Test changes

- Replaced embedded KaiPlus runtime path and environment assertions with LinkEase-owned paths, `KAIPLUS_ENABLED=0`, and forbidden embedded KaiPlus exports.
- Added assertions for independent KaiPlus proxy resolution, including the default port `8189` and `/koolshare` executable/config discovery.
- Restricted LinkEase lifecycle, install, and uninstall expectations to LinkEase and apptunnel processes and files.
- Changed the build contract to stage only `linkease-desktop` and `apptunnel-client`, with no packaged `kaiplus` directory.

## Verification

Command:

```text
python3 -m unittest discover tests
```

Result: expected failure. The suite ran 27 tests and reported 6 failures and 1 error.

The failures identify the old embedded KaiPlus exports and lifecycle/install behavior, the missing `resolve_kaiplus_proxy_target` implementation, and `build.py` still requiring `artifact/kaiplus`.

`git diff --check` passed.

## Commit

Commit: `fcfbbe69f092bc7614111966ff5b30f1dba8e6a4` (`test: define rogsoft linkease kaiplus split contract`)

## Review Fixes

- Added install/uninstall deletion checks for literal and variable-derived external `.linkease_data` paths.
- Strengthened forbidden KaiPlus checks to catch quoted and variable-based forms such as `killall "$KAIPLUS_BIN"` and embedded path exports.
- Removed the unused `stat` import from `test_build_script.py`.
- Added tarball member inspection to ensure `linkease/kaiplus` is not packaged.

## Fix Verification

Command:

```text
python3 -m unittest discover tests
```

Result: expected failure because production code still contains the embedded KaiPlus contract. The suite ran 27 tests with 7 failures and 1 error. The error is `FileNotFoundError` from `build.py` still requiring `artifact/kaiplus`; failures cover the remaining embedded KaiPlus exports/process/install behavior and missing proxy resolver.

Command:

```text
git diff --check
```

Result: passed with exit code 0.

Additional check: `python3 -m py_compile tests/test_linkease_config_contract.py tests/test_install_uninstall_contract.py tests/test_build_script.py` passed, with no syntax/import errors.
