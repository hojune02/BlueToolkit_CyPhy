# 20260309 Progress Report

## Braktooth KNOB Exploit Fix

When running `sudo bluekit -t 64:7B:CE:BD:A5:2B -e braktooth_knob`, the test consistently failed with `Toolkit error⚠️ | Error during extracting information from the regex`. Running the exploit manually with `sudo bin/bt_exploiter --host-port=/dev/ttyUSB1 --target=64:7B:CE:BD:A5:2B --exploit=knob` confirmed the device was vulnerable (`[Modules] KNOB Detected!!! Device vulnerable`), meaning the issue was in BlueToolkit's handling of the exploit output, not the exploit itself. This issue was not device-specific and affected all targets.

### Root Cause Analysis

Three problems were identified:

1. **Missing output wrapper**: The BlueToolkit engine expects all PoC-type exploits to output a structured line in the format `BLUEEXPLOITER DATA: code=X, data=...` (defined in `bluekit/bluekit/constants.py`). Working PoC exploits (e.g. `custom_nino_check`) use a Python wrapper that calls `report_vulnerable()` / `report_not_vulnerable()` from `bluekit.report` to produce this line. However, `braktooth_knob.yaml` was calling the raw `bt_exploiter` binary directly, which outputs `[Modules] KNOB Detected!!!` — a format the engine's regex cannot parse.

2. **Broken wrapper script**: A wrapper script `bluekit_knob.py` already existed in `modules/tools/custom_exploits/` but contained multiple bugs preventing it from functioning: a typo (`proc.waite()` instead of `proc.communicate()`), an undefined variable (`data` instead of `output`), a missing `import re`, an incorrect regex pattern (`KNOB is detected` vs the actual `KNOB Detected`), a mismatched function name in `__main__` (`check_CVE_2018` instead of `check_for_CVE_2018`), and no calls to `report_vulnerable()` upon successful detection.

3. **Process never terminates**: After detecting KNOB, `bt_exploiter` enters an infinite retry/reconnection loop and never exits. Using `proc.communicate()` waits for process termination, so it always timed out regardless of timeout duration.

### Changes Made

#### `bluekit/exploits/braktooth_knob.yaml`

- Changed `command` from `./bin/bt_exploiter --host-port=/dev/ttyUSB1 --exploit=knob --random_bdaddress` to `python3 bluekit_knob.py`, routing through the wrapper script
- Changed `directory.directory` from `modules/tools/braktooth/wdissector` to `modules/tools/custom_exploits`, so the wrapper script is found at runtime
- Changed `parameter_connector` from `=` to `" "`, matching the wrapper's argparse-style argument format (`--target 64:7B:CE:BD:A5:2B` instead of `--target=64:7B:CE:BD:A5:2B`)
- Added `max_timeout: 120` to give the engine sufficient time for the exploit to complete

#### `modules/tools/custom_exploits/bluekit_knob.py`

- Added missing `import re`
- Fixed `proc.waite()` typo to `proc.communicate()`
- Fixed undefined variable `data` to `output`
- Fixed regex from `b'KNOB is detected'` to `b'KNOB Detected'` to match actual `bt_exploiter` output
- Added `report_vulnerable()` and `report_not_vulnerable()` calls to produce the `BLUEEXPLOITER DATA:` output the engine requires
- Fixed `__main__` function call from `check_CVE_2018` to `check_for_CVE_2018`
- Used absolute path for `bt_exploiter` binary and added `cwd` parameter to `subprocess.Popen` so braktooth runs from its own directory
- Gave `directory` parameter a default value of `''` to prevent `TypeError` when called without it
- Replaced `proc.communicate(timeout=90)` with line-by-line stdout reading. This was the final and most critical fix: `bt_exploiter` never exits after detecting KNOB (it enters a retry loop), so `communicate()` always timed out. The new approach reads output incrementally, detects the `KNOB Detected` pattern immediately, calls `report_vulnerable()`, and kills the process

### Result

After applying all changes, `sudo bluekit -t 64:7B:CE:BD:A5:2B -e braktooth_knob` now correctly reports:

```json
{
      "code": 2,
      "data": "KNOB Detected - Device accepted reduced encryption key size"
}
