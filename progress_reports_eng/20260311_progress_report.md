# 20260311 Progress Report

## Reconnaissance-Based Exploit Fixes (SC) and Custom Exploit Fixes (NiNo, Legacy Pairing)

Three exploits were failing with `Toolkit error⚠️` when running against target `64:7b:ce:bd:a5:2b`: `reconnaissance_SC_supported`, `custom_nino_check`, and `custom_legacy_pairing_second_check`. Each had distinct root causes.

### Root Cause Analysis

#### 1. `reconnaissance_SC_supported` — KeyError on recon data structure

Running `python3 bluekit_recon_based_check.py --case 1 --target 64:7b:ce:bd:a5:2b` directly revealed a `KeyError: 'sc'` at line 55 of `bluekit_recon_based_check.py`. The code accessed `features["sc"]`, but the new recon data format (produced by the rewritten `pybtool`-based `Recon` class) nests `sc` inside `pairing_features`:

```json
{
    "pairing_features": {
        "sc": true,
        "io_capabilities": "DisplayYesNo"
    }
}
```

The old recon system stored `sc` at the top level; the new one does not.

#### 2. `custom_nino_check` — stdout pollution preventing engine output parsing

The BlueToolkit engine captures exploit stdout and parses it with `ast.literal_eval`, expecting a dict like `{'return_code': X, 'return_data': '...'}` (produced by `report_vulnerable()` / `report_not_vulnerable()` / `report_error()` from `bluekit.report`). The `bluekit_nino_check.py` script had two problems:

- **`sudo` in child process**: Line 11 defined `HCITOOL_INFO = "sudo hcitool info {target}"`. When bluekit runs under `sudo`, the child shell spawned by `pexpect` does not inherit the sudo session, causing a password prompt timeout. This triggered `report_error()`, but the damage was already done by the second problem.

- **stdout pollution**: The script used `print()` for debug output (`print(INSTRUCTIONS)`, `print("Remove: ...")`, `print("Hcitool info: done")`, `print("Pair output: ...")`, `print("Connect output: ...")`) before the final `report_*()` call. The engine received all of this mixed into stdout, `ast.literal_eval` failed on the non-dict text, and `process_custom_output()` in `engine.py` fell through to the default branch (since the exploit name doesn't contain "braktooth"), returning `UNKNOWN_STATE`.

#### 3. `custom_legacy_pairing_second_check` — missing `get_hcidump` method

The script calls `recon.get_hcidump(target=target)` at line 13, but the new `Recon` class (rewritten to use `pybtool`) did not include the `start_hcidump`, `stop_hcidump`, or `get_hcidump` methods that existed in the old recon implementation. This caused `AttributeError: 'Recon' object has no attribute 'get_hcidump'`.

### Changes Made

#### `modules/tools/custom_exploits/bluekit_recon_based_check.py`

- Changed `features["sc"]` to `features["pairing_features"]["sc"]` on line 55 to match the new recon data structure

#### `modules/tools/custom_exploits/bluekit_nino_check.py`

- Removed `sudo` from `HCITOOL_INFO` command: changed `"sudo hcitool info {target}"` to `"hcitool info {target}"` (line 11), since bluekit already runs under `sudo`
- Changed all debug `print()` calls to `logging.info()` (lines 53, 58, 63, 76, 111) so only the `report_*()` dict output goes to stdout for the engine to parse

#### `bluekit/bluekit/recon.py` (in `~/BlueToolkit/bluekit/`)

- Added `import signal` and `import subprocess` to module imports
- Added three methods to the `Recon` class, ported from the old recon implementation:
  - `start_hcidump(self)` — spawns `hcidump -X` as a subprocess
  - `stop_hcidump(self, process)` — sends SIGINT to the hcidump process and returns captured output
  - `get_hcidump(self, target)` — starts hcidump, triggers a connection via `check_device_status(target)`, then stops hcidump and returns the output lines

### Result

After applying all changes:

- `reconnaissance_SC_supported` correctly reports `{"code": 1, "data": "Secure Connections supported"}`
- `custom_nino_check` and `custom_legacy_pairing_second_check` fixes applied, tests successful on Galaxy Note10+ 5G

### Galaxy Note10+ 5G - 64:7B:CE:BD:A5:2B

| Index | Exploit                                           | Result         | Data                                                                            |
|-------|---------------------------------------------------|----------------|---------------------------------------------------------------------------------|
|   1   | wrong_encapsulated_payload                        | Not vulnerable | 0                                                                               |
|   2   | invalid_max_slot                                  | Not vulnerable | 0                                                                               |
|   3   | au_rand_flooding                                  | Not vulnerable | 0                                                                               |
|   4   | invalid_timing_accuracy                           | Not vulnerable | 0                                                                               |
|   5   | internalblue_CVE_2018_19860_16_0b                 | Not tested     |                                                                                 |
|   6   | bleedingtooth_badvibes_cve_2020_24490             | Not vulnerable | 0                                                                               |
|   7   | sdp_unkown_element_type                           | Not vulnerable | 1                                                                               |
|   8   | lmp_invalid_transport                             | Not vulnerable | 0                                                                               |
|   9   | duplicated_iocap                                  | Not vulnerable | 0                                                                               |
|  10   | bleedingtooth_badkarma_cve_2020_12351             | Not tested     |                                                                                 |
|  11   | braktooth_knob                                    | Vulnerable     | KNOB Detected - Device accepted reduced encryption key size                     |
|  12   | blueborne_CVE_2017_1000250                        | Not vulnerable | 0                                                                               |
|  13   | repeated_host_connection                          | Not vulnerable | 0                                                                               |
|  14   | sdp_oversized_element_size                        | Not vulnerable | 0                                                                               |
|  15   | internalblue_knob                                 | Not tested     |                                                                                 |
|  16   | feature_response_flooding                         | Not vulnerable | 0                                                                               |
|  17   | custom_nino_check                                 | Vulnerable     | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated keys) |
|  18   | custom_legacy_pairing_second_check                | Not vulnerable | No PIN was requested                                                            |
|  19   | duplicated_encapsulated_payload                   | Not vulnerable | 0                                                                               |
|  20   | truncated_sco_link_request                        | Not vulnerable | 0                                                                               |
|  21   | reconnaissance_SSP_supported                      | Not vulnerable | SSP supported, secure cryptography is used, there might be a problem with Message Integrity |
|  22   | paging_scan_disable                               | Not vulnerable | 1                                                                               |
|  23   | reconnaissance_knob_ble                           | Not tested     |                                                                                 |
|  24   | lmp_overflow_dm1                                  | Not vulnerable | 0                                                                               |
|  25   | reconnaissance_SC_supported                       | Not vulnerable | Secure Connections supported                                                    |
|  26   | custom_insecure_numeric_comparison_implementation | Not tested     |                                                                                 |
|  27   | internalblue_CVE_2018_19860_20_17                 | Not tested     |                                                                                 |
|  28   | lmp_overflow_2dh1                                 | Not vulnerable | 0                                                                               |
|  29   | bleedingtooth_badchoice_cve_2020_12352            | Not vulnerable | 0                                                                               |
|  30   | invalid_feature_page_execution                    | Not vulnerable | 0                                                                               |
|  31   | internalblue_CVE_2018_5383_Invalid_second         | Not tested     |                                                                                 |
|  32   | lmp_auto_rate_overflow                            | Not vulnerable | 0                                                                               |
|  33   | reconnaissance_possible_BLUR                      | Vulnerable     | Possibly vulnerable to BLUR, needs testing                                      |
|  34   | invalid_setup_complete                            | Not vulnerable | 0                                                                               |
|  35   | truncated_lmp_accepted                            | Not vulnerable | 0                                                                               |
|  36   | internalblue_CVE_2018_19860_0a_00                 | Not tested     |                                                                                 |
|  37   | feature_req_ping_pong                             | Not vulnerable | 0                                                                               |
|  38   | lmp_max_slot_overflow                             | Not vulnerable | 0                                                                               |
|  39   | blueborne_CVE_2017_0785                           | Not vulnerable | 00000000                                                                        |
|  40   | blueborne_CVE_2017_1000251                        | Not vulnerable | 0                                                                               |
|  41   | custom_method_confusion_check                     | Not vulnerable | Device uses DisplayYesNo                                                        |

### Galaxy Note10 5G - 74:9E:F5:59:7A:56

| Index | Exploit                                           | Result         | Data                                                                                |
|-------|---------------------------------------------------|----------------|-------------------------------------------------------------------------------------|
|   1   | wrong_encapsulated_payload                        | Not vulnerable | 0                                                                                   |
|   2   | invalid_max_slot                                  | Not vulnerable | 0                                                                                   |
|   3   | au_rand_flooding                                  | Not vulnerable | 1                                                                                   |
|   4   | invalid_timing_accuracy                           | Not vulnerable | 0                                                                                   |
|   5   | internalblue_CVE_2018_19860_16_0b                 | Not tested     |                                                                                     |
|   6   | bleedingtooth_badvibes_cve_2020_24490             | Not vulnerable | 0                                                                                   |
|   7   | sdp_unkown_element_type                           | Not vulnerable | 0                                                                                   |
|   8   | lmp_invalid_transport                             | Not vulnerable | 0                                                                                   |
|   9   | duplicated_iocap                                  | Not vulnerable | 0                                                                                   |
|  10   | bleedingtooth_badkarma_cve_2020_12351             | Not tested     |                                                                                     |
|  11   | braktooth_knob                                    | Vulnerable     | KNOB Detected - Device accepted reduced encryption key size                         |
|  12   | blueborne_CVE_2017_1000250                        | Not vulnerable | 0                                                                                   |
|  13   | repeated_host_connection                          | Not vulnerable | 0                                                                                   |
|  14   | sdp_oversized_element_size                        | Not vulnerable | 0                                                                                   |
|  15   | internalblue_knob                                 | Not tested     |                                                                                     |
|  16   | feature_response_flooding                         | Not vulnerable | 0                                                                                   |
|  17   | custom_nino_check                                 | Vulnerable     | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated keys)  |
|  18   | custom_legacy_pairing_second_check                | Not vulnerable | No PIN was requested                                                                |
|  19   | duplicated_encapsulated_payload                   | Not vulnerable | 0                                                                                   |
|  20   | truncated_sco_link_request                        | Not vulnerable | 0                                                                                   |
|  21   | reconnaissance_SSP_supported                      | Not vulnerable | SSP supported, secure cryptography is used, there might be a problem with Message Integrity |
|  22   | paging_scan_disable                               | Not vulnerable | 0                                                                                   |
|  23   | reconnaissance_knob_ble                           | Not tested     |                                                                                     |
|  24   | lmp_overflow_dm1                                  | Not vulnerable | 0                                                                                   |
|  25   | reconnaissance_SC_supported                       | Not vulnerable | Secure Connections supported                                                        |
|  26   | custom_insecure_numeric_comparison_implementation | Not tested     |                                                                                     |
|  27   | internalblue_CVE_2018_19860_20_17                 | Not tested     |                                                                                     |
|  28   | lmp_overflow_2dh1                                 | Not vulnerable | 0                                                                                   |
|  29   | bleedingtooth_badchoice_cve_2020_12352            | Not vulnerable | 1                                                                                   |
|  30   | invalid_feature_page_execution                    | Not vulnerable | 0                                                                                   |
|  31   | internalblue_CVE_2018_5383_Invalid_second         | Not tested     |                                                                                     |
|  32   | lmp_auto_rate_overflow                            | Not vulnerable | 0                                                                                   |
|  33   | reconnaissance_possible_BLUR                      | Vulnerable     | Possibly vulnerable to BLUR, needs testing                                          |
|  34   | invalid_setup_complete                            | Not vulnerable | 0                                                                                   |
|  35   | truncated_lmp_accepted                            | Not vulnerable | 0                                                                                   |
|  36   | internalblue_CVE_2018_19860_0a_00                 | Not tested     |                                                                                     |
|  37   | feature_req_ping_pong                             | Not vulnerable | 0                                                                                   |
|  38   | lmp_max_slot_overflow                             | Not vulnerable | 0                                                                                   |
|  39   | blueborne_CVE_2017_0785                           | Not vulnerable | 00000000                                                                            |
|  40   | blueborne_CVE_2017_1000251                        | Not vulnerable | 0                                                                                   |
|  41   | custom_method_confusion_check                     | Not vulnerable | Device uses DisplayYesNo                                                            |


### Galaxy S7 - F8:E6:1A:CA:8F:70

| Index | Exploit                                           | Result         | Data                                                                                |
|-------|---------------------------------------------------|----------------|-------------------------------------------------------------------------------------|
|   1   | wrong_encapsulated_payload                        | Not vulnerable | 0                                                                                   |
|   2   | invalid_max_slot                                  | Not vulnerable | 3                                                                                   |
|   3   | au_rand_flooding                                  | Not vulnerable | 1                                                                                   |
|   4   | invalid_timing_accuracy                           | Not vulnerable | 0                                                                                   |
|   5   | internalblue_CVE_2018_19860_16_0b                 | Not tested     |                                                                                     |
|   6   | bleedingtooth_badvibes_cve_2020_24490             | Not vulnerable | 0                                                                                   |
|   7   | sdp_unkown_element_type                           | Not vulnerable | 0                                                                                   |
|   8   | lmp_invalid_transport                             | Not vulnerable | 0                                                                                   |
|   9   | duplicated_iocap                                  | Not vulnerable | 0                                                                                   |
|  10   | bleedingtooth_badkarma_cve_2020_12351             | Not tested     |                                                                                     |
|  11   | braktooth_knob                                    | Vulnerable     | KNOB Detected - Device accepted reduced encryption key size                         |
|  12   | blueborne_CVE_2017_1000250                        | Not vulnerable | 0                                                                                   |
|  13   | repeated_host_connection                          | Not vulnerable | 0                                                                                   |
|  14   | sdp_oversized_element_size                        | Not vulnerable | 0                                                                                   |
|  15   | internalblue_knob                                 | Not tested     |                                                                                     |
|  16   | feature_response_flooding                         | Not vulnerable | 0                                                                                   |
|  17   | custom_nino_check                                 | Vulnerable     | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated keys)  |
|  18   | custom_legacy_pairing_second_check                | Not vulnerable | No PIN was requested                                                                |
|  19   | duplicated_encapsulated_payload                   | Not vulnerable | 1                                                                                   |
|  20   | truncated_sco_link_request                        | Not vulnerable | 0                                                                                   |
|  21   | reconnaissance_SSP_supported                      | Not vulnerable | SSP supported, secure cryptography is used, there might be a problem with Message Integrity |
|  22   | paging_scan_disable                               | Not vulnerable | 0                                                                                   |
|  23   | reconnaissance_knob_ble                           | Not tested     |                                                                                     |
|  24   | lmp_overflow_dm1                                  | Not vulnerable | 0                                                                                   |
|  25   | reconnaissance_SC_supported                       | Not vulnerable | Secure Connections supported                                                        |
|  26   | custom_insecure_numeric_comparison_implementation | Not tested     |                                                                                     |
|  27   | internalblue_CVE_2018_19860_20_17                 | Not tested     |                                                                                     |
|  28   | lmp_overflow_2dh1                                 | Not vulnerable | 0                                                                                   |
|  29   | bleedingtooth_badchoice_cve_2020_12352            | Not vulnerable | 0                                                                                   |
|  30   | invalid_feature_page_execution                    | Not vulnerable | 0                                                                                   |
|  31   | internalblue_CVE_2018_5383_Invalid_second         | Not tested     |                                                                                     |
|  32   | lmp_auto_rate_overflow                            | Not vulnerable | 0                                                                                   |
|  33   | reconnaissance_possible_BLUR                      | Vulnerable     | Possibly vulnerable to BLUR, needs testing                                          |
|  34   | invalid_setup_complete                            | Not vulnerable | 0                                                                                   |
|  35   | truncated_lmp_accepted                            | Not vulnerable | 0                                                                                   |
|  36   | internalblue_CVE_2018_19860_0a_00                 | Not tested     |                                                                                     |
|  37   | feature_req_ping_pong                             | Not vulnerable | 3                                                                                   |
|  38   | lmp_max_slot_overflow                             | Not vulnerable | 0                                                                                   |
|  39   | blueborne_CVE_2017_0785                           | Not vulnerable | 00000000                                                                            |
|  40   | blueborne_CVE_2017_1000251                        | Not vulnerable | 0                                                                                   |
|  41   | custom_method_confusion_check                     | Not vulnerable | Device uses DisplayYesNo                                                            |

### soundcore Motion X600 - F4:2B:7D:2F:3E:5B

| Index | Exploit                                           | Result         | Data                                                                             |
|-------|---------------------------------------------------|----------------|----------------------------------------------------------------------------------|
|   1   | wrong_encapsulated_payload                        | Not vulnerable | 1                                                                                |
|   2   | invalid_max_slot                                  | Not vulnerable | 0                                                                                |
|   3   | au_rand_flooding                                  | Not vulnerable | 0                                                                                |
|   4   | invalid_timing_accuracy                           | Not vulnerable | 0                                                                                |
|   5   | internalblue_CVE_2018_19860_16_0b                 | Not tested     |                                                                                  |
|   6   | bleedingtooth_badvibes_cve_2020_24490             | Not tested     |                                                                                  |
|   7   | sdp_unkown_element_type                           | Not vulnerable | 0                                                                                |
|   8   | lmp_invalid_transport                             | Not vulnerable | 2                                                                                |
|   9   | duplicated_iocap                                  | Not vulnerable | 3                                                                                |
|  10   | bleedingtooth_badkarma_cve_2020_12351             | Not tested     |                                                                                  |
|  11   | braktooth_knob                                    | Not vulnerable | KNOB Rejected - Device secure, refused reduced key size                          |
|  12   | blueborne_CVE_2017_1000250                        | Not tested     |                                                                                  |
|  13   | repeated_host_connection                          | Not vulnerable | 1                                                                                |
|  14   | sdp_oversized_element_size                        | Not vulnerable | 0                                                                                |
|  15   | internalblue_knob                                 | Not tested     |                                                                                  |
|  16   | feature_response_flooding                         | Not vulnerable | 0                                                                                |
|  17   | custom_nino_check                                 | Vulnerable❗    | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key |
|  18   | custom_legacy_pairing_second_check                | Not vulnerable | No PIN was requested                                                             |
|  19   | duplicated_encapsulated_payload                   | Not vulnerable | 0                                                                                |
|  20   | truncated_sco_link_request                        | Not vulnerable | 3                                                                                |
|  21   | reconnaissance_SSP_supported                      | Not vulnerable | SSP supported, secure cryptography is used, there might be a problem with Messag |
|  22   | paging_scan_disable                               | Not vulnerable | 0                                                                                |
|  23   | reconnaissance_knob_ble                           | Not tested     |                                                                                  |
|  24   | lmp_overflow_dm1                                  | Not vulnerable | 2                                                                                |
|  25   | reconnaissance_SC_supported                       | Vulnerable❗    | Secure Connections not supported, but used ???                                   |
|  26   | custom_insecure_numeric_comparison_implementation | Not tested     |                                                                                  |
|  27   | internalblue_CVE_2018_19860_20_17                 | Not tested     |                                                                                  |
|  28   | lmp_overflow_2dh1                                 | Not vulnerable | 0                                                                                |
|  29   | bleedingtooth_badchoice_cve_2020_12352            | Not tested     |                                                                                  |
|  30   | invalid_feature_page_execution                    | Not vulnerable | 3                                                                                |
|  31   | internalblue_CVE_2018_5383_Invalid_second         | Not tested     |                                                                                  |
|  32   | lmp_auto_rate_overflow                            | Not vulnerable | 2                                                                                |
|  33   | reconnaissance_possible_BLUR                      | Not vulnerable | No LE supported, Cross transport attacks are not going to work                   |
|  34   | invalid_setup_complete                            | Not vulnerable | 0                                                                                |
|  35   | truncated_lmp_accepted                            | Not vulnerable | 0                                                                                |
|  36   | internalblue_CVE_2018_19860_0a_00                 | Not tested     |                                                                                  |
|  37   | feature_req_ping_pong                             | Not vulnerable | 0                                                                                |
|  38   | lmp_max_slot_overflow                             | Not vulnerable | 2                                                                                |
|  39   | blueborne_CVE_2017_0785                           | Not tested     |                                                                                  |
|  40   | blueborne_CVE_2017_1000251                        | Not tested     |                                                                                  |
|  41   | custom_method_confusion_check                     | Vulnerable❗    | Device capability is {}, susceptible to Method Confusion MitM                    |
