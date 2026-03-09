# 20260226 progress report

## `custom_nino_check` setup

The vulnerability lies in the fact that the victim device accepts unauthenticated pairing from a peripheral device. Therefore, it is essential to set up the attacking device (Ubuntu 22.04) in this case as a peripheral, before running `custom_nino_check` testing. This can be done by ensuring that `discoverable` and `pairable` options are turned on:

```bash
bluetoothctl discoverable on
bluetoothctl pairable on
```

Also, for iPhone 13 Pro and M1 Macbook Pro, one needs to forget the attacking device first before running `custom_nino_check`. The exact reason as to why this is the case is not yet clear. After running the setup commands above and forgetting the attacking device, `custom_nino_check` against an iPhone 13 Pro and a M1 Macbook Pro could be done successfuly.

## General recommendation when running `bluekit`

It is possible to encounter performance instability issue when running `bluekit`. Although the exact mechanism behind this has not been closely evaluated, a temporary solution for addressing this issue is to run the following commands before trying `bluekit` again:

```bash
sudo systemctl restart bluetooth
bluetoothctl power on
bluetoothctl scan on
bluetoothctl discoverable on
bluetoothctl pairable on
```

After running these commands, you can check that the device is now ready to run `bluekit` by running `sudo hcitool info {target_mac}`, confirming that the command correctly fetches the target device's information.

## Results for attacks thus far

# Bluetooth Vulnerability Report

### Macbook Pro M1 - F8:4D:89:80:79:C6

| Index | Exploit | Result | Data |
|-------|---------|--------|------|
| 1 | reconnaissance_SC_supported | Not vulnerable | Secure Connections supported |
| 2 | reconnaissance_SSP_supported | Not vulnerable | SSP supported, secure cryptography is used, there might be a problem with Messag |
| 3 | reconnaissance_possible_BLUR | Vulnerable❗ | Possibly vulnerable to BLUR, needs testing |
| 4 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 5 | custom_nino_check | Vulnerable❗ | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key |
| 6 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 7 | wrong_encapsulated_payload | Not tested | |
| 8 | invalid_max_slot | Not tested | |
| 9 | au_rand_flooding | Not tested | |
| 10 | invalid_timing_accuracy | Not tested | |
| 11 | internalblue_CVE_2018_19860_16_0b | Not tested | |
| 12 | bleedingtooth_badvibes_cve_2020_24490 | Not tested | |
| 13 | sdp_unkown_element_type | Not tested | |
| 14 | lmp_invalid_transport | Not tested | |
| 15 | duplicated_iocap | Not tested | |
| 16 | bleedingtooth_badkarma_cve_2020_12351 | Not tested | |
| 17 | braktooth_knob | Not tested | |
| 18 | blueborne_CVE_2017_1000250 | Not tested | |
| 19 | repeated_host_connection | Not tested | |
| 20 | sdp_oversized_element_size | Not tested | |
| 21 | internalblue_knob | Not tested | |
| 22 | feature_response_flooding | Not tested | |
| 23 | duplicated_encapsulated_payload | Not tested | |
| 24 | truncated_sco_link_request | Not tested | |
| 25 | paging_scan_disable | Not tested | |
| 26 | lmp_overflow_dm1 | Not tested | |
| 27 | custom_insecure_numeric_comparison_implementation | Not tested | |
| 28 | internalblue_CVE_2018_19860_20_17 | Not tested | |
| 29 | lmp_overflow_2dh1 | Not tested | |
| 30 | bleedingtooth_badchoice_cve_2020_12352 | Not tested | |
| 31 | invalid_feature_page_execution | Not tested | |
| 32 | internalblue_CVE_2018_5383_Invalid_second | Not tested | |
| 33 | lmp_auto_rate_overflow | Not tested | |
| 34 | invalid_setup_complete | Not tested | |
| 35 | truncated_lmp_accepted | Not tested | |
| 36 | internalblue_CVE_2018_19860_0a_00 | Not tested | |
| 37 | feature_req_ping_pong | Not tested | |
| 38 | lmp_max_slot_overflow | Not tested | |
| 39 | blueborne_CVE_2017_0785 | Not tested | |
| 40 | blueborne_CVE_2017_1000251 | Not tested | |

---

### BZ-SL30 - F4:4E:FD:C4:85:08

| Index | Exploit | Result | Data |
|-------|---------|--------|------|
| 1 | reconnaissance_SC_supported | Vulnerable❗ | No Secure Connections supported |
| 2 | reconnaissance_SSP_supported | Not vulnerable | SSP supported, secure cryptography is used, there might be a problem with Messag |
| 3 | reconnaissance_possible_BLUR | Not vulnerable | No LE supported, Cross transport attacks are not going to work |
| 4 | bleedingtooth_badchoice_cve_2020_12352 | Not vulnerable | 0 |
| 5 | bleedingtooth_badvibes_cve_2020_24490 | Not vulnerable | 0 |
| 6 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 7 | custom_nino_check | Vulnerable❗ | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key |
| 8 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 9 | blueborne_CVE_2017_1000251 | Not vulnerable | 0 |
| 10 | blueborne_CVE_2017_0785 | Not vulnerable | Target device OS is not Android |
| 11 | blueborne_CVE_2017_1000250 | Not vulnerable | 0 |
| 12 | wrong_encapsulated_payload | Not tested | |
| 13 | invalid_max_slot | Not tested | |
| 14 | au_rand_flooding | Not tested | |
| 15 | invalid_timing_accuracy | Not tested | |
| 16 | internalblue_CVE_2018_19860_16_0b | Not tested | |
| 17 | sdp_unkown_element_type | Not tested | |
| 18 | lmp_invalid_transport | Not tested | |
| 19 | duplicated_iocap | Not tested | |
| 20 | bleedingtooth_badkarma_cve_2020_12351 | Not tested | |
| 21 | braktooth_knob | Not tested | |
| 22 | repeated_host_connection | Not tested | |
| 23 | sdp_oversized_element_size | Not tested | |
| 24 | internalblue_knob | Not tested | |
| 25 | feature_response_flooding | Not tested | |
| 26 | duplicated_encapsulated_payload | Not tested | |
| 27 | truncated_sco_link_request | Not tested | |
| 28 | paging_scan_disable | Not tested | |
| 29 | lmp_overflow_dm1 | Not tested | |
| 30 | custom_insecure_numeric_comparison_implementation | Not tested | |
| 31 | internalblue_CVE_2018_19860_20_17 | Not tested | |
| 32 | lmp_overflow_2dh1 | Not tested | |
| 33 | invalid_feature_page_execution | Not tested | |
| 34 | internalblue_CVE_2018_5383_Invalid_second | Not tested | |
| 35 | lmp_auto_rate_overflow | Not tested | |
| 36 | invalid_setup_complete | Not tested | |
| 37 | truncated_lmp_accepted | Not tested | |
| 38 | internalblue_CVE_2018_19860_0a_00 | Not tested | |
| 39 | feature_req_ping_pong | Not tested | |
| 40 | lmp_max_slot_overflow | Not tested | |

---

### soundcore Motion X600 - F4:2B:7D:2F:3E:5B

| Index | Exploit | Result | Data |
|-------|---------|--------|------|
| 1 | reconnaissance_SC_supported | Vulnerable❗ | No Secure Connections supported |
| 2 | reconnaissance_SSP_supported | Vulnerable❗ | SSP not supported |
| 3 | reconnaissance_possible_BLUR | Not vulnerable | No LE supported, Cross transport attacks are not going to work |
| 4 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 5 | custom_nino_check | Vulnerable❗ | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key |
| 6 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 7 | wrong_encapsulated_payload | Not tested | |
| 8 | invalid_max_slot | Not tested | |
| 9 | au_rand_flooding | Not tested | |
| 10 | invalid_timing_accuracy | Not tested | |
| 11 | internalblue_CVE_2018_19860_16_0b | Not tested | |
| 12 | bleedingtooth_badvibes_cve_2020_24490 | Not tested | |
| 13 | sdp_unkown_element_type | Not tested | |
| 14 | lmp_invalid_transport | Not tested | |
| 15 | duplicated_iocap | Not tested | |
| 16 | bleedingtooth_badkarma_cve_2020_12351 | Not tested | |
| 17 | braktooth_knob | Not tested | |
| 18 | blueborne_CVE_2017_1000250 | Not tested | |
| 19 | repeated_host_connection | Not tested | |
| 20 | sdp_oversized_element_size | Not tested | |
| 21 | internalblue_knob | Not tested | |
| 22 | feature_response_flooding | Not tested | |
| 23 | duplicated_encapsulated_payload | Not tested | |
| 24 | truncated_sco_link_request | Not tested | |
| 25 | paging_scan_disable | Not tested | |
| 26 | lmp_overflow_dm1 | Not tested | |
| 27 | custom_insecure_numeric_comparison_implementation | Not tested | |
| 28 | internalblue_CVE_2018_19860_20_17 | Not tested | |
| 29 | lmp_overflow_2dh1 | Not tested | |
| 30 | bleedingtooth_badchoice_cve_2020_12352 | Not tested | |
| 31 | invalid_feature_page_execution | Not tested | |
| 32 | internalblue_CVE_2018_5383_Invalid_second | Not tested | |
| 33 | lmp_auto_rate_overflow | Not tested | |
| 34 | invalid_setup_complete | Not tested | |
| 35 | truncated_lmp_accepted | Not tested | |
| 36 | internalblue_CVE_2018_19860_0a_00 | Not tested | |
| 37 | feature_req_ping_pong | Not tested | |
| 38 | lmp_max_slot_overflow | Not tested | |
| 39 | blueborne_CVE_2017_0785 | Not tested | |
| 40 | blueborne_CVE_2017_1000251 | Not tested | |

---

### Galaxy S7 - E4:FA:ED:EF:09:F4

| Index | Exploit | Result | Data |
|-------|---------|--------|------|
| 1 | reconnaissance_SC_supported | Not vulnerable | Secure Connections supported |
| 2 | reconnaissance_SSP_supported | Not vulnerable | SSP supported, secure cryptography is used, there might be a problem with Messag |
| 3 | reconnaissance_possible_BLUR | Vulnerable❗ | Possibly vulnerable to BLUR, needs testing |
| 4 | bleedingtooth_badchoice_cve_2020_12352 | Not vulnerable | 0 |
| 5 | bleedingtooth_badvibes_cve_2020_24490 | Not vulnerable | 0 |
| 6 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 7 | custom_nino_check | Vulnerable❗ | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key |
| 8 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 9 | blueborne_CVE_2017_1000251 | Not vulnerable | 0 |
| 10 | blueborne_CVE_2017_0785 | Not vulnerable | 00000000 |
| 11 | blueborne_CVE_2017_1000250 | Not vulnerable | 0 |
| 12 | wrong_encapsulated_payload | Not tested | |
| 13 | invalid_max_slot | Not tested | |
| 14 | au_rand_flooding | Not tested | |
| 15 | invalid_timing_accuracy | Not tested | |
| 16 | internalblue_CVE_2018_19860_16_0b | Not tested | |
| 17 | sdp_unkown_element_type | Not tested | |
| 18 | lmp_invalid_transport | Not tested | |
| 19 | duplicated_iocap | Not tested | |
| 20 | bleedingtooth_badkarma_cve_2020_12351 | Not tested | |
| 21 | braktooth_knob | Not tested | |
| 22 | repeated_host_connection | Not tested | |
| 23 | sdp_oversized_element_size | Not tested | |
| 24 | internalblue_knob | Not tested | |
| 25 | feature_response_flooding | Not tested | |
| 26 | duplicated_encapsulated_payload | Not tested | |
| 27 | truncated_sco_link_request | Not tested | |
| 28 | paging_scan_disable | Not tested | |
| 29 | lmp_overflow_dm1 | Not tested | |
| 30 | custom_insecure_numeric_comparison_implementation | Not tested | |
| 31 | internalblue_CVE_2018_19860_20_17 | Not tested | |
| 32 | lmp_overflow_2dh1 | Not tested | |
| 33 | invalid_feature_page_execution | Not tested | |
| 34 | internalblue_CVE_2018_5383_Invalid_second | Not tested | |
| 35 | lmp_auto_rate_overflow | Not tested | |
| 36 | invalid_setup_complete | Not tested | |
| 37 | truncated_lmp_accepted | Not tested | |
| 38 | internalblue_CVE_2018_19860_0a_00 | Not tested | |
| 39 | feature_req_ping_pong | Not tested | |
| 40 | lmp_max_slot_overflow | Not tested | |

---

### Galaxy S7 - 94:76:B7:FF:1D:3C

| Index | Exploit | Result | Data |
|-------|---------|--------|------|
| 1 | reconnaissance_SC_supported | Not vulnerable | Secure Connections supported |
| 2 | reconnaissance_SSP_supported | Not vulnerable | SSP supported, secure cryptography is used, there might be a problem with Messag |
| 3 | reconnaissance_possible_BLUR | Vulnerable❗ | Possibly vulnerable to BLUR, needs testing |
| 4 | bleedingtooth_badchoice_cve_2020_12352 | Not vulnerable | 0 |
| 5 | bleedingtooth_badvibes_cve_2020_24490 | Not vulnerable | 0 |
| 6 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 7 | custom_nino_check | Vulnerable❗ | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key |
| 8 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 9 | blueborne_CVE_2017_1000251 | Not vulnerable | 0 |
| 10 | blueborne_CVE_2017_0785 | Not vulnerable | 00000000 |
| 11 | blueborne_CVE_2017_1000250 | Not vulnerable | 0 |
| 12 | wrong_encapsulated_payload | Not tested | |
| 13 | invalid_max_slot | Not tested | |
| 14 | au_rand_flooding | Not tested | |
| 15 | invalid_timing_accuracy | Not tested | |
| 16 | internalblue_CVE_2018_19860_16_0b | Not tested | |
| 17 | sdp_unkown_element_type | Not tested | |
| 18 | lmp_invalid_transport | Not tested | |
| 19 | duplicated_iocap | Not tested | |
| 20 | bleedingtooth_badkarma_cve_2020_12351 | Not tested | |
| 21 | braktooth_knob | Not tested | |
| 22 | repeated_host_connection | Not tested | |
| 23 | sdp_oversized_element_size | Not tested | |
| 24 | internalblue_knob | Not tested | |
| 25 | feature_response_flooding | Not tested | |
| 26 | duplicated_encapsulated_payload | Not tested | |
| 27 | truncated_sco_link_request | Not tested | |
| 28 | paging_scan_disable | Not tested | |
| 29 | lmp_overflow_dm1 | Not tested | |
| 30 | custom_insecure_numeric_comparison_implementation | Not tested | |
| 31 | internalblue_CVE_2018_19860_20_17 | Not tested | |
| 32 | lmp_overflow_2dh1 | Not tested | |
| 33 | invalid_feature_page_execution | Not tested | |
| 34 | internalblue_CVE_2018_5383_Invalid_second | Not tested | |
| 35 | lmp_auto_rate_overflow | Not tested | |
| 36 | invalid_setup_complete | Not tested | |
| 37 | truncated_lmp_accepted | Not tested | |
| 38 | internalblue_CVE_2018_19860_0a_00 | Not tested | |
| 39 | feature_req_ping_pong | Not tested | |
| 40 | lmp_max_slot_overflow | Not tested | |

---

### Galaxy Note10 5G - 74:9E:F5:59:7A:56

| Index | Exploit | Result | Data |
|-------|---------|--------|------|
| 1 | reconnaissance_SC_supported | Not vulnerable | Secure Connections supported |
| 2 | reconnaissance_SSP_supported | Not vulnerable | SSP supported, secure cryptography is used, there might be a problem with Messag |
| 3 | reconnaissance_possible_BLUR | Vulnerable❗ | Possibly vulnerable to BLUR, needs testing |
| 4 | bleedingtooth_badchoice_cve_2020_12352 | Not vulnerable | 0 |
| 5 | bleedingtooth_badvibes_cve_2020_24490 | Not vulnerable | 0 |
| 6 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 7 | custom_nino_check | Vulnerable❗ | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key |
| 8 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 9 | blueborne_CVE_2017_1000251 | Not vulnerable | 0 |
| 10 | blueborne_CVE_2017_0785 | Not vulnerable | 00000000 |
| 11 | blueborne_CVE_2017_1000250 | Not vulnerable | 0 |
| 12 | wrong_encapsulated_payload | Not tested | |
| 13 | invalid_max_slot | Not tested | |
| 14 | au_rand_flooding | Not tested | |
| 15 | invalid_timing_accuracy | Not tested | |
| 16 | internalblue_CVE_2018_19860_16_0b | Not tested | |
| 17 | sdp_unkown_element_type | Not tested | |
| 18 | lmp_invalid_transport | Not tested | |
| 19 | duplicated_iocap | Not tested | |
| 20 | bleedingtooth_badkarma_cve_2020_12351 | Not tested | |
| 21 | braktooth_knob | Not tested | |
| 22 | repeated_host_connection | Not tested | |
| 23 | sdp_oversized_element_size | Not tested | |
| 24 | internalblue_knob | Not tested | |
| 25 | feature_response_flooding | Not tested | |
| 26 | duplicated_encapsulated_payload | Not tested | |
| 27 | truncated_sco_link_request | Not tested | |
| 28 | paging_scan_disable | Not tested | |
| 29 | lmp_overflow_dm1 | Not tested | |
| 30 | custom_insecure_numeric_comparison_implementation | Not tested | |
| 31 | internalblue_CVE_2018_19860_20_17 | Not tested | |
| 32 | lmp_overflow_2dh1 | Not tested | |
| 33 | invalid_feature_page_execution | Not tested | |
| 34 | internalblue_CVE_2018_5383_Invalid_second | Not tested | |
| 35 | lmp_auto_rate_overflow | Not tested | |
| 36 | invalid_setup_complete | Not tested | |
| 37 | truncated_lmp_accepted | Not tested | |
| 38 | internalblue_CVE_2018_19860_0a_00 | Not tested | |
| 39 | feature_req_ping_pong | Not tested | |
| 40 | lmp_max_slot_overflow | Not tested | |

---

### Galaxy Note10+ 5G - 64:7B:CE:AF:39:63

| Index | Exploit | Result | Data |
|-------|---------|--------|------|
| 1 | reconnaissance_SC_supported | Not vulnerable | Secure Connections supported |
| 2 | reconnaissance_SSP_supported | Not vulnerable | SSP supported, secure cryptography is used, there might be a problem with Messag |
| 3 | reconnaissance_possible_BLUR | Vulnerable❗ | Possibly vulnerable to BLUR, needs testing |
| 4 | bleedingtooth_badchoice_cve_2020_12352 | Not vulnerable | 0 |
| 5 | bleedingtooth_badvibes_cve_2020_24490 | Not vulnerable | 0 |
| 6 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 7 | custom_nino_check | Vulnerable❗ | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key |
| 8 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 9 | blueborne_CVE_2017_1000251 | Not vulnerable | 0 |
| 10 | blueborne_CVE_2017_0785 | Not vulnerable | 00000000 |
| 11 | blueborne_CVE_2017_1000250 | Not vulnerable | 0 |
| 12 | wrong_encapsulated_payload | Not tested | |
| 13 | invalid_max_slot | Not tested | |
| 14 | au_rand_flooding | Not tested | |
| 15 | invalid_timing_accuracy | Not tested | |
| 16 | internalblue_CVE_2018_19860_16_0b | Not tested | |
| 17 | sdp_unkown_element_type | Not tested | |
| 18 | lmp_invalid_transport | Not tested | |
| 19 | duplicated_iocap | Not tested | |
| 20 | bleedingtooth_badkarma_cve_2020_12351 | Not tested | |
| 21 | braktooth_knob | Not tested | |
| 22 | repeated_host_connection | Not tested | |
| 23 | sdp_oversized_element_size | Not tested | |
| 24 | internalblue_knob | Not tested | |
| 25 | feature_response_flooding | Not tested | |
| 26 | duplicated_encapsulated_payload | Not tested | |
| 27 | truncated_sco_link_request | Not tested | |
| 28 | paging_scan_disable | Not tested | |
| 29 | lmp_overflow_dm1 | Not tested | |
| 30 | custom_insecure_numeric_comparison_implementation | Not tested | |
| 31 | internalblue_CVE_2018_19860_20_17 | Not tested | |
| 32 | lmp_overflow_2dh1 | Not tested | |
| 33 | invalid_feature_page_execution | Not tested | |
| 34 | internalblue_CVE_2018_5383_Invalid_second | Not tested | |
| 35 | lmp_auto_rate_overflow | Not tested | |
| 36 | invalid_setup_complete | Not tested | |
| 37 | truncated_lmp_accepted | Not tested | |
| 38 | internalblue_CVE_2018_19860_0a_00 | Not tested | |
| 39 | feature_req_ping_pong | Not tested | |
| 40 | lmp_max_slot_overflow | Not tested | |

---

### Galaxy Note10+ 5G - 64:7B:CE:A9:C0:AB

| Index | Exploit | Result | Data |
|-------|---------|--------|------|
| 1 | reconnaissance_SC_supported | Not vulnerable | Secure Connections supported |
| 2 | reconnaissance_SSP_supported | Not vulnerable | SSP supported, secure cryptography is used, there might be a problem with Messag |
| 3 | reconnaissance_possible_BLUR | Vulnerable❗ | Possibly vulnerable to BLUR, needs testing |
| 4 | bleedingtooth_badchoice_cve_2020_12352 | Not vulnerable | 0 |
| 5 | bleedingtooth_badvibes_cve_2020_24490 | Not vulnerable | 0 |
| 6 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 7 | custom_nino_check | Vulnerable❗ | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key |
| 8 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 9 | blueborne_CVE_2017_1000251 | Not vulnerable | 0 |
| 10 | blueborne_CVE_2017_0785 | Not vulnerable | 00000000 |
| 11 | blueborne_CVE_2017_1000250 | Not vulnerable | 0 |
| 12 | wrong_encapsulated_payload | Not tested | |
| 13 | invalid_max_slot | Not tested | |
| 14 | au_rand_flooding | Not tested | |
| 15 | invalid_timing_accuracy | Not tested | |
| 16 | internalblue_CVE_2018_19860_16_0b | Not tested | |
| 17 | sdp_unkown_element_type | Not tested | |
| 18 | lmp_invalid_transport | Not tested | |
| 19 | duplicated_iocap | Not tested | |
| 20 | bleedingtooth_badkarma_cve_2020_12351 | Not tested | |
| 21 | braktooth_knob | Not tested | |
| 22 | repeated_host_connection | Not tested | |
| 23 | sdp_oversized_element_size | Not tested | |
| 24 | internalblue_knob | Not tested | |
| 25 | feature_response_flooding | Not tested | |
| 26 | duplicated_encapsulated_payload | Not tested | |
| 27 | truncated_sco_link_request | Not tested | |
| 28 | paging_scan_disable | Not tested | |
| 29 | lmp_overflow_dm1 | Not tested | |
| 30 | custom_insecure_numeric_comparison_implementation | Not tested | |
| 31 | internalblue_CVE_2018_19860_20_17 | Not tested | |
| 32 | lmp_overflow_2dh1 | Not tested | |
| 33 | invalid_feature_page_execution | Not tested | |
| 34 | internalblue_CVE_2018_5383_Invalid_second | Not tested | |
| 35 | lmp_auto_rate_overflow | Not tested | |
| 36 | invalid_setup_complete | Not tested | |
| 37 | truncated_lmp_accepted | Not tested | |
| 38 | internalblue_CVE_2018_19860_0a_00 | Not tested | |
| 39 | feature_req_ping_pong | Not tested | |
| 40 | lmp_max_slot_overflow | Not tested | |

---

### iPhone 13 Pro - 14:2D:4D:D8:3C:83

| Index | Exploit | Result | Data |
|-------|---------|--------|------|
| 1 | reconnaissance_SC_supported | Not vulnerable | Secure Connections supported |
| 2 | reconnaissance_SSP_supported | Not vulnerable | SSP supported, secure cryptography is used, there might be a problem with Messag |
| 3 | reconnaissance_possible_BLUR | Vulnerable❗ | Possibly vulnerable to BLUR, needs testing |
| 4 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 5 | custom_nino_check | Vulnerable❗ | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key |
| 6 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 7 | wrong_encapsulated_payload | Not tested | |
| 8 | invalid_max_slot | Not tested | |
| 9 | au_rand_flooding | Not tested | |
| 10 | invalid_timing_accuracy | Not tested | |
| 11 | internalblue_CVE_2018_19860_16_0b | Not tested | |
| 12 | bleedingtooth_badvibes_cve_2020_24490 | Not tested | |
| 13 | sdp_unkown_element_type | Not tested | |
| 14 | lmp_invalid_transport | Not tested | |
| 15 | duplicated_iocap | Not tested | |
| 16 | bleedingtooth_badkarma_cve_2020_12351 | Not tested | |
| 17 | braktooth_knob | Not tested | |
| 18 | blueborne_CVE_2017_1000250 | Not tested | |
| 19 | repeated_host_connection | Not tested | |
| 20 | sdp_oversized_element_size | Not tested | |
| 21 | internalblue_knob | Not tested | |
| 22 | feature_response_flooding | Not tested | |
| 23 | duplicated_encapsulated_payload | Not tested | |
| 24 | truncated_sco_link_request | Not tested | |
| 25 | paging_scan_disable | Not tested | |
| 26 | lmp_overflow_dm1 | Not tested | |
| 27 | custom_insecure_numeric_comparison_implementation | Not tested | |
| 28 | internalblue_CVE_2018_19860_20_17 | Not tested | |
| 29 | lmp_overflow_2dh1 | Not tested | |
| 30 | bleedingtooth_badchoice_cve_2020_12352 | Not tested | |
| 31 | invalid_feature_page_execution | Not tested | |
| 32 | internalblue_CVE_2018_5383_Invalid_second | Not tested | |
| 33 | lmp_auto_rate_overflow | Not tested | |
| 34 | invalid_setup_complete | Not tested | |
| 35 | truncated_lmp_accepted | Not tested | |
| 36 | internalblue_CVE_2018_19860_0a_00 | Not tested | |
| 37 | feature_req_ping_pong | Not tested | |
| 38 | lmp_max_slot_overflow | Not tested | |
| 39 | blueborne_CVE_2017_0785 | Not tested | |
| 40 | blueborne_CVE_2017_1000251 | Not tested | |
