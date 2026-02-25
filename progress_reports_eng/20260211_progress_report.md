# 20260211 Progress Report

## Previous Status

Running BlueToolkit itself was resolved by downgrading the Python version to 3.10 and reinstalling `setuptools` with a lower version:
```bash
(.venv) (base) cyphy@cyphy-Lenovo-V15:~$ sudo bluekit -h
usage: bluekit [-h] [-t TARGET] [-l] [-c] [-ct] [-ch] [-v VERBOSITY] [-ex EXCLUDEEXPLOITS [EXCLUDEEXPLOITS ...]]
               [-e EXPLOITS [EXPLOITS ...]] [-r] [-re] [-rej] [-hh HARDWARE [HARDWARE ...]]
               ...

positional arguments:
  rest

options:
  -h, --help            show this help message and exit
  -t TARGET, --target TARGET
                        target MAC address
...
```
However, when attempting to run attacks, there was an issue where the connection to the target device kept dropping. This issue was resolved today, and this file was created to document the resolution process.

## Problem Resolution

### 1. Issue in `reconnect.sh` inside `bluekit`

`bluekit` is the CLI tool used by BlueToolkit. There is a `reconnect.sh` file responsible for device connections, and the original file on GitHub is as follows:

```sh
#!/bin/bash

mac=$1 # DEH-4400BT
...
rfkill unblock bluetooth

bluetoothctl -- power on
bluetoothctl -- discoverable on
bluetoothctl -- pairable on
bluetoothctl -- agent NoInputNoOutput    # if you delete this part it will pair as normal, one would need to accept pairing only on the device (test)
bluetoothctl -- default-agent
bluetoothctl -- remove $mac
sudo hcitool info $mac
bluetoothctl -- trust $mac
bluetoothctl -- connect $mac
bluetoothctl -- remove $mac
bluetoothctl -- disconnect
...
```

This file was the main cause of the persistent connection drops. The problematic points were:

- The bluetoothctl agent was set to NoInputNoOutput, but some devices reject connections from devices whose agent is set to NoInputNoOutput.
- The `bluetoothctl --` commands are used consecutively in a fire-and-forget manner, which can cause a race condition between `connect` and `remove`. This results in the connection being terminated immediately after establishment, without any chance to verify the connection status.

Therefore, `/usr/share/BlueToolkit/bluekit/bluekit/reconnect.sh` was modified as shown below, and after that, the connection status check command `sudo -E PATH=$PATH bluekit -t AA:BB:CC:DD:EE:FF -ct` worked correctly:

```sh
#!/bin/bash
mac=$1

rfkill unblock bluetooth

# Use a single bluetoothctl session with heredoc
bluetoothctl <<EOF
power on
discoverable on
pairable on
agent on
default-agent
disconnect $mac
remove $mac
trust $mac
connect $mac
EOF

# Wait for connection to establish
sleep 5

# Clean up
bluetoothctl <<EOF
disconnect $mac
EOF

...

```

### 2. Issue with the `hcitool info` command

After resolving the connection issue, when attempting to run attacks by specifying exploits, the following error occurred repeatedly.

```bash
(.venv) (base) cyphy@cyphy-Lenovo-V15:~$ sudo -E env PATH=$PATH bluekit -t F4:2B:7D:2F:3E:5B -e bleedingtooth_badchoice bleedingtooth_badkarma bleedingtooth_badvibes blueborne_CVE_2017_0785 blueborne_CVE_2017_1000250 blueborne_CVE_2017_1000251 custom_insecure_numeric_comparison_implementation custom_legacy_pairing_second_check custom_method_confusion_check custom_nino_check
/usr/share/BlueToolkit/data/tests/F4:2B:7D:2F:3E:5B/recon/hciinfo.log
Traceback (most recent call last):
  ...
  File "/usr/share/BlueToolkit/.venv/lib/python3.12/site-packages/bluekit/recon.py", line 82, in determine_bluetooth_version
    output = mm.search(text).group()
             ^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'group'
```

It first reads the `hciinfo.log` for the connected device (in this case F4:2B:7D:2F:3E:5B), and the error occurred because NoneType data was read at that point.

After bluekit connects to the device, it needs to run `hcitool info` to check the LMP version of the connected device, but the command output sometimes includes this information and sometimes does not. In the example below, you can see that the same command produces different results:

```bash
(base) cyphy@cyphy-Lenovo-V15:~$ sudo hcitool info F4:2B:7D:2F:3E:5B
Requesting information ...
	BD Address:  F4:2B:7D:2F:3E:5B
	OUI Company: Chipsguide technology CO.,LTD. (F4-2B-7D)
	Features: 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00

(base) cyphy@cyphy-Lenovo-V15:~$ sudo hcitool info F4:2B:7D:2F:3E:5B
Requesting information ...
	BD Address:  F4:2B:7D:2F:3E:5B
	OUI Company: Chipsguide technology CO.,LTD. (F4-2B-7D)
	Features: 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00

(base) cyphy@cyphy-Lenovo-V15:~$ sudo hcitool info F4:2B:7D:2F:3E:5B
Requesting information ...
	BD Address:  F4:2B:7D:2F:3E:5B
	OUI Company: Chipsguide technology CO.,LTD. (F4-2B-7D)
	LMP Version: 5.3 (0xc) LMP Subversion: 0x682
	Manufacturer: Actions (Zhuhai) Technology Co., Limited (992)
	Features page 0: 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
```

Since the output of `hcitool info` is saved directly to the device's `hciinfo.log`, as an immediate workaround, the `hcitool info` command was run manually until the LMP version information appeared, and the result was copied and pasted directly.

Additionally, the `run_recon` function in `recon.py` inside bluekit was modified to retry the `hcitool info` command up to 5 times until the result includes the LMP version information.

### Summary of Changes

- Changed the `bluetoothctl` `agent` used in `reconnect.sh` from `NoInputNoOutput` to `on`. Also resolved the race condition between `bluetoothctl connect` and `bluetoothctl remove` -> Connection is no longer rejected and is maintained.
- The attack could not run because the target device's `hciinfo.log` did not contain LMP version information. Resolved by manually running the `hcitool info` command and copying and pasting the output that included the LMP version.
- Modified the `run_recon` function to retry the command up to 5 times until the LMP version information is included.

### Attack Results
The attack targets were two speaker devices and one Samsung phone. First, the entire attack execution and result output process for the Samsung phone is shown, followed by summarized result tables for the two speaker devices below:

#### Galaxy S7: F8:E6:1A:CA:8F:70

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
Testing exploits:   9%|█████████████████▋                                                                                                                                                                                | 1/11 [00:11<01:53, 11.38s/it]The target device is not available. Try restoring the connectivity. After that enter 1 of the following commands: continue, backup:
continue
Trying to verify connectivity again
Successful check - Device connectivity is checked
Successful check - Device connectivity is checked
Testing exploits:  18%|███████████████████████████████████▎                                                                                                                                                              | 2/11 [00:30<02:21, 15.76s/it]Successful check - Device connectivity is checked
b'BLUEEXPLOITER DATA: code=0, data=There is no lmp file from recon script\n'
Testing exploits:  27%|████████████████████████████████████████████████████▉                                                                                                                                             | 3/11 [00:36<01:30, 11.34s/it]The target device is not available. Try restoring the connectivity. After that enter 1 of the following commands: continue, backup:
continue
Trying to verify connectivity again
Successful check - Device connectivity is checked
b'BLUEEXPLOITER DATA: code=1, data=00000000\n'
Testing exploits:  36%|██████████████████████████████████████████████████████████████████████▌                                                                                                                           | 4/11 [00:55<01:42, 14.64s/it]Successful check - Device connectivity is checked
Testing exploits:  45%|████████████████████████████████████████████████████████████████████████████████████████▏                                                                                                         | 5/11 [01:11<01:30, 15.08s/it]Successful check - Device connectivity is checked
b'BLUEEXPLOITER DATA: code=0, data=There is no lmp file from recon script\n'
Testing exploits:  55%|█████████████████████████████████████████████████████████████████████████████████████████████████████████▊                                                                                        | 6/11 [01:18<01:00, 12.11s/it]Successful check - Device connectivity is checked
Successful check - Device connectivity is checked
Testing exploits:  64%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████▍                                                                      | 7/11 [01:31<00:50, 12.65s/it]Successful check - Device connectivity is checked
Testing exploits:  73%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████                                                     | 8/11 [01:59<00:51, 17.32s/it]The target device is not available. Try restoring the connectivity. After that enter 1 of the following commands: continue, backup:
continue
Trying to verify connectivity again
Successful check - Device connectivity is checked
b'BLUEEXPLOITER DATA: code=1, data=No PIN was requested\n'
Testing exploits:  82%|██████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████▋                                   | 9/11 [02:18<00:35, 17.98s/it]The target device is not available. Try restoring the connectivity. After that enter 1 of the following commands: continue, backup:
continue
Trying to verify connectivity again
Successful check - Device connectivity is checked
b'BLUEEXPLOITER DATA: code=0, data=There is no lmp file from recon script\n'
Testing exploits:  91%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████▍                 | 10/11 [02:30<00:16, 16.07s/it]Successful check - Device connectivity is checked
b"BLUEEXPLOITER DATA: code=1, data=Device didn't show its capabilities, most likely Legacy Pairing\n"
Testing exploits: 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 11/11 [02:43<00:00, 14.91s/it]
(.venv) (base) cyphy@cyphy-Lenovo-V15:~$ sudo -E env PATH=$PATH bluekit -t F8:E6:1A:CA:8F:70 --report

Report for target device:

+-------+---------------------------------------------------+-----------------+-----------------------------------------------------------------+
| Index | Exploit                                           | Result          | Data                                                            |
+-------+---------------------------------------------------+-----------------+-----------------------------------------------------------------+
|   1   | reconnaissance_SC_supported                       | Error⚠️         | There is no lmp file from recon script                          |
|   2   | reconnaissance_SSP_supported                      | Error⚠️         | There is no lmp file from recon script                          |
|   3   | reconnaissance_possible_BLUR                      | Error⚠️         | There is no lmp file from recon script                          |
|   4   | bleedingtooth_badvibes_cve_2020_24490             | Vulnerable❗     | 10                                                              |
|   5   | bleedingtooth_badchoice_cve_2020_12352            | Not vulnerable  | 0                                                               |
|   6   | custom_legacy_pairing_second_check                | Not vulnerable  | No PIN was requested                                            |
|   7   | custom_method_confusion_check                     | Not vulnerable  | Device didn't show its capabilities, most likely Legacy Pairing |
|   8   | custom_nino_check                                 | Toolkit error⚠️ | Error during extracting information from the regex              |
|   9   | blueborne_CVE_2017_0785                           | Not vulnerable  | 00000000                                                        |
|  10   | blueborne_CVE_2017_1000251                        | Not vulnerable  | 0                                                               |
|  11   | blueborne_CVE_2017_1000250                        | Not vulnerable  | 0                                                               |
|  12   | paging_scan_disable                               | Not tested      |                                                                 |
|  13   | invalid_feature_page_execution                    | Not tested      |                                                                 |
|  14   | duplicated_encapsulated_payload                   | Not tested      |                                                                 |
|  15   | feature_req_ping_pong                             | Not tested      |                                                                 |
|  16   | lmp_invalid_transport                             | Not tested      |                                                                 |
|  17   | truncated_lmp_accepted                            | Not tested      |                                                                 |
|  18   | feature_response_flooding                         | Not tested      |                                                                 |
|  19   | truncated_sco_link_request                        | Not tested      |                                                                 |
|  20   | bleedingtooth_badkarma_cve_2020_12351             | Not tested      |                                                                 |
|  21   | internalblue_CVE_2018_19860_20_17                 | Not tested      |                                                                 |
|  22   | internalblue_CVE_2018_5383_Invalid_second         | Not tested      |                                                                 |
|  23   | sdp_unkown_element_type                           | Not tested      |                                                                 |
|  24   | internalblue_CVE_2018_19860_0a_00                 | Not tested      |                                                                 |
|  25   | internalblue_CVE_2018_19860_16_0b                 | Not tested      |                                                                 |
|  26   | repeated_host_connection                          | Not tested      |                                                                 |
|  27   | internalblue_knob                                 | Not tested      |                                                                 |
|  28   | wrong_encapsulated_payload                        | Not tested      |                                                                 |
|  29   | lmp_overflow_2dh1                                 | Not tested      |                                                                 |
|  30   | braktooth_knob                                    | Not tested      |                                                                 |
|  31   | lmp_auto_rate_overflow                            | Not tested      |                                                                 |
|  32   | invalid_timing_accuracy                           | Not tested      |                                                                 |
|  33   | sdp_oversized_element_size                        | Not tested      |                                                                 |
|  34   | custom_insecure_numeric_comparison_implementation | Not tested      |                                                                 |
|  35   | invalid_max_slot                                  | Not tested      |                                                                 |
|  36   | duplicated_iocap                                  | Not tested      |                                                                 |
|  37   | au_rand_flooding                                  | Not tested      |                                                                 |
|  38   | lmp_overflow_dm1                                  | Not tested      |                                                                 |
|  39   | lmp_max_slot_overflow                             | Not tested      |                                                                 |
|  40   | invalid_setup_complete                            | Not tested      |                                                                 |
+-------+---------------------------------------------------+-----------------+-----------------------------------------------------------------+

```

#### soundcore motion X600: F4:2B:7D:2F:3E:5B

```bash
(.venv) (base) cyphy@cyphy-Lenovo-V15:~$ sudo -E env PATH=$PATH bluekit -t F4:2B:7D:2F:3E:5B --report

Report for target device:

+-------+---------------------------------------------------+-----------------+-----------------------------------------------------------------+
| Index | Exploit                                           | Result          | Data                                                            |
+-------+---------------------------------------------------+-----------------+-----------------------------------------------------------------+
|   1   | reconnaissance_SC_supported                       | Error⚠️         | There is no lmp file from recon script                          |
|   2   | reconnaissance_SSP_supported                      | Error⚠️         | There is no lmp file from recon script                          |
|   3   | reconnaissance_possible_BLUR                      | Error⚠️         | There is no lmp file from recon script                          |
|   4   | custom_legacy_pairing_second_check                | Not vulnerable  | No PIN was requested                                            |
|   5   | custom_method_confusion_check                     | Not vulnerable  | Device didn't show its capabilities, most likely Legacy Pairing |
|   6   | custom_nino_check                                 | Toolkit error⚠️ | Error during extracting information from the regex              |
|   7   | paging_scan_disable                               | Not tested      |                                                                 |
|   8   | invalid_feature_page_execution                    | Not tested      |                                                                 |
|   9   | duplicated_encapsulated_payload                   | Not tested      |                                                                 |
|  10   | bleedingtooth_badchoice_cve_2020_12352            | Not tested      |                                                                 |
|  11   | blueborne_CVE_2017_1000250                        | Not tested      |                                                                 |
|  12   | feature_req_ping_pong                             | Not tested      |                                                                 |
|  13   | lmp_invalid_transport                             | Not tested      |                                                                 |
|  14   | truncated_lmp_accepted                            | Not tested      |                                                                 |
|  15   | feature_response_flooding                         | Not tested      |                                                                 |
|  16   | blueborne_CVE_2017_0785                           | Not tested      |                                                                 |
|  17   | truncated_sco_link_request                        | Not tested      |                                                                 |
|  18   | bleedingtooth_badkarma_cve_2020_12351             | Not tested      |                                                                 |
|  19   | internalblue_CVE_2018_19860_20_17                 | Not tested      |                                                                 |
|  20   | internalblue_CVE_2018_5383_Invalid_second         | Not tested      |                                                                 |
|  21   | sdp_unkown_element_type                           | Not tested      |                                                                 |
|  22   | internalblue_CVE_2018_19860_0a_00                 | Not tested      |                                                                 |
|  23   | internalblue_CVE_2018_19860_16_0b                 | Not tested      |                                                                 |
|  24   | repeated_host_connection                          | Not tested      |                                                                 |
|  25   | blueborne_CVE_2017_1000251                        | Not tested      |                                                                 |
|  26   | internalblue_knob                                 | Not tested      |                                                                 |
|  27   | wrong_encapsulated_payload                        | Not tested      |                                                                 |
|  28   | lmp_overflow_2dh1                                 | Not tested      |                                                                 |
|  29   | braktooth_knob                                    | Not tested      |                                                                 |
|  30   | lmp_auto_rate_overflow                            | Not tested      |                                                                 |
|  31   | bleedingtooth_badvibes_cve_2020_24490             | Not tested      |                                                                 |
|  32   | invalid_timing_accuracy                           | Not tested      |                                                                 |
|  33   | sdp_oversized_element_size                        | Not tested      |                                                                 |
|  34   | custom_insecure_numeric_comparison_implementation | Not tested      |                                                                 |
|  35   | invalid_max_slot                                  | Not tested      |                                                                 |
|  36   | duplicated_iocap                                  | Not tested      |                                                                 |
|  37   | au_rand_flooding                                  | Not tested      |                                                                 |
|  38   | lmp_overflow_dm1                                  | Not tested      |                                                                 |
|  39   | lmp_max_slot_overflow                             | Not tested      |                                                                 |
|  40   | invalid_setup_complete                            | Not tested      |                                                                 |
+-------+---------------------------------------------------+-----------------+-----------------------------------------------------------------+
```
#### britz BZ-SL30: F4:4E:FD:C4:85:08

```bash
(.venv) (base) cyphy@cyphy-Lenovo-V15:~$ sudo -E env PATH=$PATH bluekit -t F4:4E:FD:C4:85:08 -ex reconnaissance_SC_supported reconnaissance_SSP_supported reconnaissance_possible_BLUR
/usr/share/BlueToolkit/data/tests/F4:4E:FD:C4:85:08/recon/hciinfo.log
Recon data found - /usr/share/BlueToolkit/data/tests/F4:4E:FD:C4:85:08/recon/bluing_lmp.log
Target Bluetooth version: 4.2
Skipping all exploits and hardware that do not support this version
There are 8 out of 40 exploits available.

Running the following exploits: ['bleedingtooth_badchoice_cve_2020_12352', 'blueborne_CVE_2017_1000250', 'blueborne_CVE_2017_0785', 'custom_nino_check', 'blueborne_CVE_2017_1000251', 'bleedingtooth_badvibes_cve_2020_24490', 'custom_legacy_pairing_second_check', 'custom_method_confusion_check']
Testing exploits:   0%|                                              | 0/8 [00:00<?, ?it/s]Device is offline
The target device is not available. Try restoring the connectivity. After that enter 1 of the following commands: continue, backup:
continue
...
(.venv) (base) cyphy@cyphy-Lenovo-V15:~$ sudo -E env PATH=$PATH bluekit -t F4:4E:FD:C4:85:08 --report

Report for target device:

+-------+---------------------------------------------------+----------------+-----------------------------------------------------------------+
| Index | Exploit                                           | Result         | Data                                                            |
+-------+---------------------------------------------------+----------------+-----------------------------------------------------------------+
|   1   | bleedingtooth_badvibes_cve_2020_24490             | Vulnerable❗    | 10                                                              |
|   2   | bleedingtooth_badchoice_cve_2020_12352            | Not vulnerable | 0                                                               |
|   3   | custom_legacy_pairing_second_check                | Not vulnerable | No PIN was requested                                            |
|   4   | custom_method_confusion_check                     | Not vulnerable | Device didn't show its capabilities, most likely Legacy Pairing |
|   5   | custom_nino_check                                 | Error⚠️        | Couldn't connect to a device, error while connecting            |
|   6   | blueborne_CVE_2017_0785                           | Not vulnerable | Target device OS is not Android                                 |
|   7   | blueborne_CVE_2017_1000251                        | Not vulnerable | 0                                                               |
|   8   | blueborne_CVE_2017_1000250                        | Not vulnerable | 2                                                               |
|   9   | paging_scan_disable                               | Not tested     |                                                                 |
|  10   | invalid_feature_page_execution                    | Not tested     |                                                                 |
|  11   | duplicated_encapsulated_payload                   | Not tested     |                                                                 |
|  12   | feature_req_ping_pong                             | Not tested     |                                                                 |
|  13   | lmp_invalid_transport                             | Not tested     |                                                                 |
|  14   | reconnaissance_SC_supported                       | Not tested     |                                                                 |
|  15   | truncated_lmp_accepted                            | Not tested     |                                                                 |
|  16   | feature_response_flooding                         | Not tested     |                                                                 |
|  17   | truncated_sco_link_request                        | Not tested     |                                                                 |
|  18   | bleedingtooth_badkarma_cve_2020_12351             | Not tested     |                                                                 |
|  19   | internalblue_CVE_2018_19860_20_17                 | Not tested     |                                                                 |
|  20   | internalblue_CVE_2018_5383_Invalid_second         | Not tested     |                                                                 |
|  21   | reconnaissance_SSP_supported                      | Not tested     |                                                                 |
|  22   | sdp_unkown_element_type                           | Not tested     |                                                                 |
|  23   | internalblue_CVE_2018_19860_0a_00                 | Not tested     |                                                                 |
|  24   | internalblue_CVE_2018_19860_16_0b                 | Not tested     |                                                                 |
|  25   | repeated_host_connection                          | Not tested     |                                                                 |
|  26   | internalblue_knob                                 | Not tested     |                                                                 |
|  27   | wrong_encapsulated_payload                        | Not tested     |                                                                 |
|  28   | lmp_overflow_2dh1                                 | Not tested     |                                                                 |
|  29   | braktooth_knob                                    | Not tested     |                                                                 |
|  30   | lmp_auto_rate_overflow                            | Not tested     |                                                                 |
|  31   | invalid_timing_accuracy                           | Not tested     |                                                                 |
|  32   | sdp_oversized_element_size                        | Not tested     |                                                                 |
|  33   | custom_insecure_numeric_comparison_implementation | Not tested     |                                                                 |
|  34   | invalid_max_slot                                  | Not tested     |                                                                 |
|  35   | duplicated_iocap                                  | Not tested     |                                                                 |
|  36   | au_rand_flooding                                  | Not tested     |                                                                 |
|  37   | reconnaissance_possible_BLUR                      | Not tested     |                                                                 |
|  38   | lmp_overflow_dm1                                  | Not tested     |                                                                 |
|  39   | lmp_max_slot_overflow                             | Not tested     |                                                                 |
|  40   | invalid_setup_complete                            | Not tested     |                                                                 |
+-------+---------------------------------------------------+----------------+-----------------------------------------------------------------+

```

### `bluekit` Commands Used

#### Run all exploits except those with bluing dependencies (exploits depending on ESP32 and Nexus 5 are automatically excluded):
```bash
sudo -E env PATH=$PATH bluekit -t AA:BB:CC:DD:EE:FF -ex reconnaissance_SC_supported reconnaissance_SSP_supported reconnaissance_possible_BLUR
```
