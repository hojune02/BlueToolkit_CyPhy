# 20260213 Progress Report

## Previous Status

We successfully ran `custom_nino_check` on speaker devices and Samsung mobile devices, excluding iPhones.

Today's key progress includes:
- Successfully ran `custom_nino_check` against the iPhone 13 Pro.
- Successfully ran the following three vulnerability checks that previously could not be executed due to the `bluing` dependency:
    - reconnaissance_SC_supported
    - reconnaissance_SSP_supported
    - reconnaissance_possible_BLUR

## custom_nino_check - Successful Vulnerability Verification Against iPhone 13 Pro

Originally, the internal operation of custom_nino_check was to sequentially execute the following commands inside `reconnect.sh`:

```bash
bt-agent -c NoInputNoOutput
bluetoothctl remove {target}
sudo hcitool scan
sudo hcitool info {target}
bluetoothctl pair {target}
bluetoothctl connect {target} # If this succeeds, the device is Vulnerable
bluetoothctl remove {target}
```

We removed the second step, `bluetoothctl remove {target}`, and after doing so, the regex parsing error that had only occurred when running `custom_nino_check` against iPhones no longer appeared. The pairing request now properly shows up on the iPhone screen, confirming that the vulnerability exists. Note that the iPhone must first forget the laptop running BlueToolkit before executing `custom_nino_check`. Otherwise, the regex parsing error will occur again.

Report for target device:

| Index | Exploit | Result | Data |
|---|---|---|---|
| 1 | reconnaissance_SC_supported | Error⚠️ | There is no lmp file from recon script |
| 2 | reconnaissance_SSP_supported | Error⚠️ | There is no lmp file from recon script |
| 3 | reconnaissance_possible_BLUR | Error⚠️ | There is no lmp file from recon script |
| 4 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 5 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 6 | custom_nino_check | Vulnerable❗ | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key) |
| 7 | paging_scan_disable | Not tested | |
| 8 | invalid_feature_page_execution | Not tested | |
| 9 | duplicated_encapsulated_payload | Not tested | |
| 10 | bleedingtooth_badchoice_cve_2020_12352 | Not tested | |
| 11 | blueborne_CVE_2017_1000250 | Not tested | |
| 12 | feature_req_ping_pong | Not tested | |
| 13 | lmp_invalid_transport | Not tested | |
| 14 | truncated_lmp_accepted | Not tested | |
| 15 | feature_response_flooding | Not tested | |
| 16 | blueborne_CVE_2017_0785 | Not tested | |
| 17 | truncated_sco_link_request | Not tested | |
| 18 | bleedingtooth_badkarma_cve_2020_12351 | Not tested | |
| 19 | internalblue_CVE_2018_19860_20_17 | Not tested | |
| 20 | internalblue_CVE_2018_5383_Invalid_second | Not tested | |
| 21 | sdp_unkown_element_type | Not tested | |
| 22 | internalblue_CVE_2018_19860_0a_00 | Not tested | |
| 23 | internalblue_CVE_2018_19860_16_0b | Not tested | |
| 24 | repeated_host_connection | Not tested | |
| 25 | blueborne_CVE_2017_1000251 | Not tested | |
| 26 | internalblue_knob | Not tested | |
| 27 | wrong_encapsulated_payload | Not tested | |
| 28 | lmp_overflow_2dh1 | Not tested | |
| 29 | braktooth_knob | Not tested | |
| 30 | lmp_auto_rate_overflow | Not tested | |
| 31 | bleedingtooth_badvibes_cve_2020_24490 | Not tested | |
| 32 | invalid_timing_accuracy | Not tested | |
| 33 | sdp_oversized_element_size | Not tested | |
| 34 | custom_insecure_numeric_comparison_implementation | Not tested | |
| 35 | invalid_max_slot | Not tested | |
| 36 | duplicated_iocap | Not tested | |
| 37 | au_rand_flooding | Not tested | |
| 38 | lmp_overflow_dm1 | Not tested | |
| 39 | lmp_max_slot_overflow | Not tested | |
| 40 | invalid_setup_complete | Not tested | |

## Replacing the bluing Dependency: btmon

The three `reconnaissance`-related vulnerabilities required LMP (Link Manager Protocol) information from the target remote device. The LMP information that BlueToolkit needs includes device information such as Secure Simple Pairing and Secure Connections. We confirmed that BlueToolkit obtains this information through `bluing`, parses it, and then uses it for vulnerability analysis. Therefore, we sought to replace `bluing` by finding another CLI command capable of obtaining LMP information, and we found `btmon`.

We created `btmon_feature_extractor.py` inside `/usr/share/BlueToolkit` to save the LMP information obtained from `btmon` in the same output format as `bluing`. This program only runs when the target device's `bluing_lmp.log` does not exist. In other words, `btmon_feature_extractor.py` only operates the first time BlueToolkit is run against a target device.

`btmon_feature_extractor.py` operates in the following order:

- Run `btmon` to collect surrounding Bluetooth information.
- Extract only the logs that contain the target device's MAC address from the collected information.
- Analyze the obtained logs, and if all of the following information is included, terminate execution and save the results to `/usr/share/BlueToolkit/data/tests/{target_mac}/bluing_lmp.log`.
    - LE Supported (Controller)
    - LE Supported (Host)
    - Simultaneous LE and BR/EDR to Same Device Capable (Controller)
    - Simultaneous LE and BR/EDR to Same Device Capable (Host)
    - Secure Simple Pairing (Controller Support)
    - Secure Simple Pairing (Host Support)
    - Secure Connections (Controller Support)
    - Secure Connections (Host Support)
- If not all information is present, run `btmon` again and repeat the process.

We confirmed that once all the required information is saved in the target device's `bluing_lmp.log`, the `reconnaissance`-related vulnerabilities operate correctly.

### Attack Execution Results Including `reconnaissance`: Galaxy S7 and iPhone 13 Pro

#### Galaxy S7 - F8:E6:1A:CA:8F:70

Report for target device:

| Index | Exploit | Result | Data |
|---|---|---|---|
| 1 | reconnaissance_SC_supported | Not vulnerable | Secure Connections supported |
| 2 | reconnaissance_SSP_supported | Not vulnerable | SSP supported, secure cryptography is used, there might be a problem with Message |
| 3 | reconnaissance_possible_BLUR | Vulnerable❗ | Possibly vulnerable to BLUR, needs testing |
| 4 | bleedingtooth_badvibes_cve_2020_24490 | Not vulnerable | 0 |
| 5 | bleedingtooth_badchoice_cve_2020_12352 | Not vulnerable | 0 |
| 6 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 7 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 8 | custom_nino_check | Vulnerable❗ | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key) |
| 9 | blueborne_CVE_2017_0785 | Not vulnerable | 00000000 |
| 10 | blueborne_CVE_2017_1000251 | Not vulnerable | 0 |
| 11 | blueborne_CVE_2017_1000250 | Not vulnerable | 0 |
| 12 | paging_scan_disable | Not tested | |
| 13 | invalid_feature_page_execution | Not tested | |
| 14 | duplicated_encapsulated_payload | Not tested | |
| 15 | feature_req_ping_pong | Not tested | |
| 16 | lmp_invalid_transport | Not tested | |
| 17 | truncated_lmp_accepted | Not tested | |
| 18 | feature_response_flooding | Not tested | |
| 19 | truncated_sco_link_request | Not tested | |
| 20 | bleedingtooth_badkarma_cve_2020_12351 | Not tested | |
| 21 | internalblue_CVE_2018_19860_20_17 | Not tested | |
| 22 | internalblue_CVE_2018_5383_Invalid_second | Not tested | |
| 23 | sdp_unkown_element_type | Not tested | |
| 24 | internalblue_CVE_2018_19860_0a_00 | Not tested | |
| 25 | internalblue_CVE_2018_19860_16_0b | Not tested | |
| 26 | repeated_host_connection | Not tested | |
| 27 | internalblue_knob | Not tested | |
| 28 | wrong_encapsulated_payload | Not tested | |
| 29 | lmp_overflow_2dh1 | Not tested | |
| 30 | braktooth_knob | Not tested | |
| 31 | lmp_auto_rate_overflow | Not tested | |
| 32 | invalid_timing_accuracy | Not tested | |
| 33 | sdp_oversized_element_size | Not tested | |
| 34 | custom_insecure_numeric_comparison_implementation | Not tested | |
| 35 | invalid_max_slot | Not tested | |
| 36 | duplicated_iocap | Not tested | |
| 37 | au_rand_flooding | Not tested | |
| 38 | lmp_overflow_dm1 | Not tested | |
| 39 | lmp_max_slot_overflow | Not tested | |
| 40 | invalid_setup_complete | Not tested | |

#### iPhone 13 Pro - 14:2D:4D:D8:3C:83

Report for target device:

| Index | Exploit | Result | Data |
|---|---|---|---|
| 1 | reconnaissance_SC_supported | Not vulnerable | Secure Connections supported |
| 2 | reconnaissance_SSP_supported | Not vulnerable | SSP supported, secure cryptography is used, there might be a problem with Message |
| 3 | reconnaissance_possible_BLUR | Vulnerable❗ | Possibly vulnerable to BLUR, needs testing |
| 4 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 5 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 6 | custom_nino_check | Vulnerable❗ | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key) |
| 7 | paging_scan_disable | Not tested | |
| 8 | invalid_feature_page_execution | Not tested | |
| 9 | duplicated_encapsulated_payload | Not tested | |
| 10 | bleedingtooth_badchoice_cve_2020_12352 | Not tested | |
| 11 | blueborne_CVE_2017_1000250 | Not tested | |
| 12 | feature_req_ping_pong | Not tested | |
| 13 | lmp_invalid_transport | Not tested | |
| 14 | truncated_lmp_accepted | Not tested | |
| 15 | feature_response_flooding | Not tested | |
| 16 | blueborne_CVE_2017_0785 | Not tested | |
| 17 | truncated_sco_link_request | Not tested | |
| 18 | bleedingtooth_badkarma_cve_2020_12351 | Not tested | |
| 19 | internalblue_CVE_2018_19860_20_17 | Not tested | |
| 20 | internalblue_CVE_2018_5383_Invalid_second | Not tested | |
| 21 | sdp_unkown_element_type | Not tested | |
| 22 | internalblue_CVE_2018_19860_0a_00 | Not tested | |
| 23 | internalblue_CVE_2018_19860_16_0b | Not tested | |
| 24 | repeated_host_connection | Not tested | |
| 25 | blueborne_CVE_2017_1000251 | Not tested | |
| 26 | internalblue_knob | Not tested | |
| 27 | wrong_encapsulated_payload | Not tested | |
| 28 | lmp_overflow_2dh1 | Not tested | |
| 29 | braktooth_knob | Not tested | |
| 30 | lmp_auto_rate_overflow | Not tested | |
| 31 | bleedingtooth_badvibes_cve_2020_24490 | Not tested | |
| 32 | invalid_timing_accuracy | Not tested | |
| 33 | sdp_oversized_element_size | Not tested | |
| 34 | custom_insecure_numeric_comparison_implementation | Not tested | |
| 35 | invalid_max_slot | Not tested | |
| 36 | duplicated_iocap | Not tested | |
| 37 | au_rand_flooding | Not tested | |
| 38 | lmp_overflow_dm1 | Not tested | |
| 39 | lmp_max_slot_overflow | Not tested | |
| 40 | invalid_setup_complete | Not tested | |
