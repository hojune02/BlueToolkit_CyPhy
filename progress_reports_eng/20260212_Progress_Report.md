# 20260212 Progress Report

## Previous Status

We successfully executed attacks against two speaker devices and one Samsung mobile phone (Galaxy S7) using BlueToolkit.

However, among the custom exploits, the `custom_nino_check` vulnerability check was not executed due to errors and issues with `hcitool` itself. Today, we resolved this issue, excluding the iPhone target attack. This document was created to organize the resolution process and results.

All newly conducted attacks after successfully running `custom_nino_check` are summarized under the [Today's Attack Execution Results](#todays-attack-execution-results) subsection below for your reference.

## Resolving the `custom_nino_check` Issue (Excluding iPhone)

### Error during extracting information from regex

First, looking at the previous day's attack results, there were cases where the `custom_nino_check` vulnerability check was impossible due to regex extraction errors.

BlueToolkit generates errors when the output does not follow the regex patterns defined in `constant.py`:

```python
REGEX_EXPLOIT_OUTPUT_DATA = b"BLUEEXPLOITER DATA:.*\n"
REGEX_EXPLOIT_OUTPUT_DATA_CODE = b" code=[0-4],"
REGEX_EXPLOIT_OUTPUT_DATA_DATA = b", data=.*"
```

The engine captures your script's stdout, then searches for a line like:
```
BLUEEXPLOITER DATA: code=2, data=Vulnerable to NiNo attack
```

To follow this format, bluekit uses designated output functions: `report_vulnerable()`, `report_not_vulnerable()`, and `report_error`.

With this in mind, examining `/usr/share/BlueToolkit/modules/tools/custom_exploits/bluekit_nino_check.py` inside BlueToolkit reveals cases where the `report_...` functions described above are not used, causing the output to not match the regex. Therefore, we added at least one `report` function to all such branches to ensure the output conforms to the regex.

### Instability of hcitool scan and hcitool info

As mentioned in yesterday's status report, `hcitool` sometimes produces different outputs when running the same command, or needs to be run multiple times until the desired output is obtained. In `bluekit_nino_check.py`, the program flow requires the results of both `hcitool scan` and `hcitool info`, but since both commands were only executed once, there were cases where the vulnerability analysis was terminated because the desired output was not obtained.

Therefore, we resolved this issue by modifying `hcitool scan` so that its output does not affect the program flow, and changing `hcitool info` to run repeatedly until the desired result is obtained:

```python
def check_nino(target):
...
 # Running a scan to find the target device
        try:
            command = subprocess.Popen(HCITOOL_SCAN, stdout=subprocess.PIPE, shell=True, preexec_fn=os.setsid)         # for some reason doesn't accept tokenized exploit_command (leads to a bug)
            pid = command.pid
            command.wait(timeout=30)
            output = command.communicate()[0].decode()
        except subprocess.TimeoutExpired as e:
            for child in psutil.Process(pid).children(recursive=True):
                child.kill()
            os.killpg(os.getpgid(command.pid), signal.SIGTERM)
            time.sleep(1)
            output = "" # Ensure output is defined
            report_error("Scan timed out while scanning for devices")

        if output is not None: # and target in output: <-- commented out to prevent hcitool.info from affecting the program flow
            time.sleep(1)
            logging.info("stage this")

            # Required to get information about the device, otherwise won't connect

            while True:
                try:
                # We have to run hcitool info {target} regardless of the result, in order to pair with the target.
                    subprocess.check_output(HCITOOL_INFO.format(target=target), shell=True)
                    print("Successfully running hcitool info")
                    break
                except subprocess.CalledProcessError as e:
                    time.sleep(2) # Even if it fails, we proceed to pairing
...
```
### Failure of bluetoothctl pair

After entering all hcitool-related commands, `bluetoothctl pair` is executed. Since pairing was only attempted once, the vulnerability analysis would terminate if it failed. Therefore, we changed it to attempt Bluetooth pairing up to 10 times:

```python
# Pair with the target device
            for _ in range(10):
                try:
                    subprocess.check_output(BLUETOOTHCTL_PAIR.format(target=target), shell=True)
                    break
                except subprocess.CalledProcessError as e:
                    time.sleep(2)
                    # logging.info("nino_check.py -> Error pairing with the device: {}".format(e.output))
                    # report_error("Couldn't pair with a device, error while pairing")
                    # #return
```

### Summary of Changes to bluekit_nino_check.py

- Modified code to produce output conforming to BlueToolkit's regex format in all cases.
- Due to the instability of `hcitool info` and `hcitool scan`, changed the code to ignore the result of `hcitool scan` and to run `hcitool info` repeatedly until the desired result is obtained.
- Changed `bluetoothctl pair` command to attempt up to 10 times to ensure pairing.

### Result

Successfully executed the `custom_nino_check` attack against the Samsung mobile device (Galaxy S7). The attack execution log is attached below:

```bash
(.venv) (base) cyphy@cyphy-Lenovo-V15:~$ sudo -E env PATH=$PATH bluekit -t F8:E6:1A:CA:8F:70
/usr/share/BlueToolkit/data/tests/F8:E6:1A:CA:8F:70/recon/hciinfo.log
Recon data found - /usr/share/BlueToolkit/data/tests/F8:E6:1A:CA:8F:70/recon/bluing_lmp.log
Target Bluetooth version: 4.2
Skipping all exploits and hardware that do not support this version
There are 11 out of 40 exploits available.

Running the following exploits: ['bleedingtooth_badchoice_cve_2020_12352', 'blueborne_CVE_2017_1000250', 'reconnaissance_SC_supported', 'blueborne_CVE_2017_0785', 'custom_nino_check', 'reconnaissance_SSP_supported', 'blueborne_CVE_2017_1000251', 'bleedingtooth_badvibes_cve_2020_24490', 'custom_legacy_pairing_second_check', 'reconnaissance_possible_BLUR', 'custom_method_confusion_check']
Testing exploits:   0%|                                                                                                                                                                                                          | 0/11 [00:00<?, ?it/s]Successful check - Device connectivity is checked
Successful check - Device connectivity is checked
Testing exploits:   9%|█████████████████▋                                                                                                                                                                                | 1/11 [00:12<02:04, 12.45s/it]Successful check - Device connectivity is checked
Traceback (most recent call last):
  File "/usr/share/BlueToolkit/modules/tools/blueborne/CVE-2017-1000250/CVE-2017-1000250.py", line 19, in <module>
    exploit_cve_2017_1000250(args.target)
  File "/usr/share/BlueToolkit/modules/tools/blueborne/CVE-2017-1000250/CVE-2017-1000250.py", line 8, in exploit_cve_2017_1000250
    bt = BluetoothL2CAPSocket(target)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/share/BlueToolkit/.venv/lib/python3.12/site-packages/scapy/layers/bluetooth.py", line 3244, in __init__
    s.connect((bt_address, 0))
ConnectionRefusedError: [Errno 111] Connection refused
Successful check - Device connectivity is checked
Testing exploits:  18%|███████████████████████████████████▎                                                                                                                                                              | 2/11 [00:24<01:47, 11.95s/it]Successful check - Device connectivity is checked
b'BLUEEXPLOITER DATA: code=0, data=There is no lmp file from recon script\n'
Testing exploits:  27%|████████████████████████████████████████████████████▉                                                                                                                                             | 3/11 [00:29<01:11,  8.90s/it]Successful check - Device connectivity is checked
b'BLUEEXPLOITER DATA: code=1, data=00000000\n'
Testing exploits:  36%|██████████████████████████████████████████████████████████████████████▌                                                                                                                           | 4/11 [00:35<00:54,  7.82s/it]Successful check - Device connectivity is checked
Can't create connection: Connection timed out
b'BLUEEXPLOITER DATA: code=2, data=Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated keys)\n'
Testing exploits:  45%|████████████████████████████████████████████████████████████████████████████████████████▏                                                                                                         | 5/11 [01:12<01:49, 18.24s/it]Successful check - Device connectivity is checked
b'BLUEEXPLOITER DATA: code=0, data=There is no lmp file from recon script\n'
Testing exploits:  55%|█████████████████████████████████████████████████████████████████████████████████████████████████████████▊                                                                                        | 6/11 [01:17<01:09, 13.81s/it]Successful check - Device connectivity is checked
connect: Connection refused
Successful check - Device connectivity is checked
Testing exploits:  64%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████▍                                                                      | 7/11 [01:28<00:51, 12.98s/it]Successful check - Device connectivity is checked
Successful check - Device connectivity is checked
Testing exploits:  73%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████                                                     | 8/11 [01:59<00:56, 18.79s/it]Successful check - Device connectivity is checked
b'BLUEEXPLOITER DATA: code=1, data=No PIN was requested\n'
Testing exploits:  82%|██████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████▋                                   | 9/11 [02:12<00:33, 16.74s/it]Successful check - Device connectivity is checked
b'BLUEEXPLOITER DATA: code=0, data=There is no lmp file from recon script\n'
Testing exploits:  91%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████▍                 | 10/11 [02:17<00:13, 13.19s/it]Successful check - Device connectivity is checked
b"BLUEEXPLOITER DATA: code=1, data=Device didn't show its capabilities, most likely Legacy Pairing\n"
Testing exploits: 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 11/11 [02:29<00:00, 13.61s/it]
(.venv) (base) cyphy@cyphy-Lenovo-V15:~$ sudo -E env PATH=$PATH bluekit -t F8:E6:1A:CA:8F:70 --report

Report for target device:

+-------+---------------------------------------------------+----------------+----------------------------------------------------------------------------------+
| Index | Exploit                                           | Result         | Data                                                                             |
+-------+---------------------------------------------------+----------------+----------------------------------------------------------------------------------+
|   1   | reconnaissance_SC_supported                       | Error⚠️        | There is no lmp file from recon script                                           |
|   2   | reconnaissance_SSP_supported                      | Error⚠️        | There is no lmp file from recon script                                           |
|   3   | reconnaissance_possible_BLUR                      | Error⚠️        | There is no lmp file from recon script                                           |
|   4   | bleedingtooth_badvibes_cve_2020_24490             | Not vulnerable | 0                                                                                |
|   5   | bleedingtooth_badchoice_cve_2020_12352            | Not vulnerable | 0                                                                                |
|   6   | custom_legacy_pairing_second_check                | Not vulnerable | No PIN was requested                                                             |
|   7   | custom_method_confusion_check                     | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing                  |
|   8   | custom_nino_check                                 | Vulnerable❗    | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key |
|   9   | blueborne_CVE_2017_0785                           | Not vulnerable | 00000000                                                                         |
|  10   | blueborne_CVE_2017_1000251                        | Not vulnerable | 0                                                                                |
|  11   | blueborne_CVE_2017_1000250                        | Not vulnerable | 0                                                                                |
|  12   | paging_scan_disable                               | Not tested     |                                                                                  |
|  13   | invalid_feature_page_execution                    | Not tested     |                                                                                  |
|  14   | duplicated_encapsulated_payload                   | Not tested     |                                                                                  |
|  15   | feature_req_ping_pong                             | Not tested     |                                                                                  |
|  16   | lmp_invalid_transport                             | Not tested     |                                                                                  |
|  17   | truncated_lmp_accepted                            | Not tested     |                                                                                  |
|  18   | feature_response_flooding                         | Not tested     |                                                                                  |
|  19   | truncated_sco_link_request                        | Not tested     |                                                                                  |
|  20   | bleedingtooth_badkarma_cve_2020_12351             | Not tested     |                                                                                  |
|  21   | internalblue_CVE_2018_19860_20_17                 | Not tested     |                                                                                  |
|  22   | internalblue_CVE_2018_5383_Invalid_second         | Not tested     |                                                                                  |
|  23   | sdp_unkown_element_type                           | Not tested     |                                                                                  |
|  24   | internalblue_CVE_2018_19860_0a_00                 | Not tested     |                                                                                  |
|  25   | internalblue_CVE_2018_19860_16_0b                 | Not tested     |                                                                                  |
|  26   | repeated_host_connection                          | Not tested     |                                                                                  |
|  27   | internalblue_knob                                 | Not tested     |                                                                                  |
|  28   | wrong_encapsulated_payload                        | Not tested     |                                                                                  |
|  29   | lmp_overflow_2dh1                                 | Not tested     |                                                                                  |
|  30   | braktooth_knob                                    | Not tested     |                                                                                  |
|  31   | lmp_auto_rate_overflow                            | Not tested     |                                                                                  |
|  32   | invalid_timing_accuracy                           | Not tested     |                                                                                  |
|  33   | sdp_oversized_element_size                        | Not tested     |                                                                                  |
|  34   | custom_insecure_numeric_comparison_implementation | Not tested     |                                                                                  |
|  35   | invalid_max_slot                                  | Not tested     |                                                                                  |
|  36   | duplicated_iocap                                  | Not tested     |                                                                                  |
|  37   | au_rand_flooding                                  | Not tested     |                                                                                  |
|  38   | lmp_overflow_dm1                                  | Not tested     |                                                                                  |
|  39   | lmp_max_slot_overflow                             | Not tested     |                                                                                  |
|  40   | invalid_setup_complete                            | Not tested     |                                                                                  |
+-------+---------------------------------------------------+----------------+----------------------------------------------------------------------------------+

```

## Today's Attack Execution Results

The vulnerability analysis conducted today targeted all vulnerabilities that do not require an ESP32 or Nexus 5. Since each device has a different Bluetooth version, the actual number of vulnerability analyses executed varies by device.

Some helpful notes for running the attacks: first, running `sudo systemctl restart bluetooth` before executing bluekit can resolve some errors and connection issues. Also, during sequential attack execution, the connection may drop intermittently. In such cases, you can check whether the device's `hciinfo.log` only shows "Requesting information ...". If no information is present, you can run `sudo hcitool info [target]` from another terminal to obtain the information and manually copy and paste it.

The attack results for all devices show 3 vulnerabilities with errors, which are vulnerabilities that have a bluing dependency issue. For the iPhone target attack, in addition to these, the `custom_nino_check` vulnerability execution failed, which will be investigated further at a later time. Also, looking at the attacks on the two Galaxy S7 devices, vulnerabilities were found only in one device (2 vulnerabilities). Why such a difference occurs despite having the same model and Bluetooth specification needs to be determined through repeated attack execution. Please refer to the table and logs below for the attack results:

### Final Summary Table

| Device Name | Device MAC Address | LMP (Bluetooth) Version | Number of Attempted Vulnerabilities | Number of Errored Vulnerabilities | Not Vulnerable Count | Vulnerable Count | Additional Notes |
|---|---|---|---|---|---|---|---|
| Galaxy S7 | F8:E6:1A:CA:8F:70 | 4.2 | 11 | 3 | 7 | 1 | |
| soundcore motion X600 | F4:2B:7D:2F:3E:5B | 4.2 | 6 | 3 | 2 | 1 | |
| Britz BZ-SL30 | F4:4E:FD:C4:85:08 | 4.2 | 11 | 3 | 7 | 1 | |
| Galaxy Note10 5G | 74:9E:F5:59:7A:56 | 5.0 | 11 | 3 | 7 | 1 | |
| Galaxy Note10+ 5G | 64:7B:CE:AF:39:63 | 5.0 | 11 | 3 | 7 | 1 | |
| Galaxy Note10+ 5G | 64:7B:CE:A9:C0:AB | 5.0 | 11 | 3 | 7 | 1 | |
| iPhone 13 Pro | 14:2D:4D:D8:3C:83 | 5.3 | 6 | 4 | 2 | 0 | `custom_nino_check` error occurred |
| Galaxy S7 | 94:76:B7:FF:1D:3C | 4.2 | 11 | 3 | 6 | 2 | Requires further investigation |

### Logs

#### Galaxy S7 - F8:E6:1A:CA:8F:70

LMP Version 4.2

Report for target device:

| Index | Exploit | Result | Data |
|---|---|---|---|
| 1 | reconnaissance_SC_supported | Error⚠️ | There is no lmp file from recon script |
| 2 | reconnaissance_SSP_supported | Error⚠️ | There is no lmp file from recon script |
| 3 | reconnaissance_possible_BLUR | Error⚠️ | There is no lmp file from recon script |
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


#### soundcore motion X600 - F4:2B:7D:2F:3E:5B

LMP Version 4.2

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

#### Britz BZ-SL30 - F4:4E:FD:C4:85:08

LMP Version 4.2

Report for target device:

| Index | Exploit | Result | Data |
|---|---|---|---|
| 1 | reconnaissance_SC_supported | Error⚠️ | There is no lmp file from recon script |
| 2 | reconnaissance_SSP_supported | Error⚠️ | There is no lmp file from recon script |
| 3 | reconnaissance_possible_BLUR | Error⚠️ | There is no lmp file from recon script |
| 4 | bleedingtooth_badvibes_cve_2020_24490 | Not vulnerable | 1 |
| 5 | bleedingtooth_badchoice_cve_2020_12352 | Not vulnerable | 0 |
| 6 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 7 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 8 | custom_nino_check | Vulnerable❗ | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key) |
| 9 | blueborne_CVE_2017_0785 | Not vulnerable | Target device OS is not Android |
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

#### Galaxy Note10 5G - 74:9E:F5:59:7A:56

LMP Version 5.0

Report for target device:

| Index | Exploit | Result | Data |
|---|---|---|---|
| 1 | reconnaissance_SC_supported | Error⚠️ | There is no lmp file from recon script |
| 2 | reconnaissance_SSP_supported | Error⚠️ | There is no lmp file from recon script |
| 3 | reconnaissance_possible_BLUR | Error⚠️ | There is no lmp file from recon script |
| 4 | bleedingtooth_badvibes_cve_2020_24490 | Not vulnerable | 1 |
| 5 | bleedingtooth_badchoice_cve_2020_12352 | Not vulnerable | 0 |
| 6 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 7 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 8 | custom_nino_check | Vulnerable❗ | Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated key) |
| 9 | blueborne_CVE_2017_0785 | Not vulnerable | 00000000 |
| 10 | blueborne_CVE_2017_1000251 | Not vulnerable | 1 |
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

#### Galaxy Note10+ 5G - 64:7B:CE:AF:39:63

Report for target device: 5.0

| Index | Exploit | Result | Data |
|---|---|---|---|
| 1 | reconnaissance_SC_supported | Error⚠️ | There is no lmp file from recon script |
| 2 | reconnaissance_SSP_supported | Error⚠️ | There is no lmp file from recon script |
| 3 | reconnaissance_possible_BLUR | Error⚠️ | There is no lmp file from recon script |
| 4 | bleedingtooth_badvibes_cve_2020_24490 | Not vulnerable | 1 |
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

#### Galaxy Note10+ 5G - 64:7B:CE:A9:C0:AB

LMP Version 5.0

Report for target device:

| Index | Exploit | Result | Data |
|---|---|---|---|
| 1 | reconnaissance_SC_supported | Error⚠️ | There is no lmp file from recon script |
| 2 | reconnaissance_SSP_supported | Error⚠️ | There is no lmp file from recon script |
| 3 | reconnaissance_possible_BLUR | Error⚠️ | There is no lmp file from recon script |
| 4 | bleedingtooth_badvibes_cve_2020_24490 | Not vulnerable | 1 |
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

LMP Version 5.3

Report for target device:

| Index | Exploit | Result | Data |
|---|---|---|---|
| 1 | reconnaissance_SC_supported | Error⚠️ | There is no lmp file from recon script |
| 2 | reconnaissance_SSP_supported | Error⚠️ | There is no lmp file from recon script |
| 3 | reconnaissance_possible_BLUR | Error⚠️ | There is no lmp file from recon script |
| 4 | custom_legacy_pairing_second_check | Not vulnerable | No PIN was requested |
| 5 | custom_method_confusion_check | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
| 6 | custom_nino_check | Toolkit error⚠️ | Error during extracting information from the regex |
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

#### Galaxy S7 - 94:76:B7:FF:1D:3C

LMP Version 4.2

Report for target device:

| Index | Exploit | Result | Data |
|---|---|---|---|
| 1 | reconnaissance_SC_supported | Error⚠️ | There is no lmp file from recon script |
| 2 | reconnaissance_SSP_supported | Error⚠️ | There is no lmp file from recon script |
| 3 | reconnaissance_possible_BLUR | Error⚠️ | There is no lmp file from recon script |
| 4 | bleedingtooth_badvibes_cve_2020_24490 | Vulnerable❗ | 10 |
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
