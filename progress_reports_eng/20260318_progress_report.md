# Nexus 5 InternalBlue Setup & KNOB Testing — 2026-03-18

## Device Information

- **Model**: LG Nexus 5 (hammerhead), D821(H) 16GB (International variant)
- **HW revision**: rev_11
- **Bootloader**: HHZ20h
- **Baseband**: M8974A-2.0.50.2.30
- **Serial**: 04b7d0512524a642
- **Bluetooth chip**: Broadcom BCM4335C0 (chip ID: 0x6109, firmware 003.001.009)
- **Host machine**: Lenovo V15 G4 IRU, Ubuntu 22.04

## Setup Steps Completed

### 1. Bootloader Unlock

The device was in fastboot mode (Volume Down + Power). Bootloader was unlocked with `fastboot oem unlock`, wiping all data. Note: `adb` does not work in fastboot mode — use `fastboot devices` to verify the connection.

### 2. Android 6.0.1 Factory Image Flash

Flashed the official Google factory image `hammerhead-m4b30z` via `flash-all.sh`. The `userdata` partition formatting failed due to an outdated `mke2fs` bundled with Ubuntu's fastboot tools. Resolved by running `fastboot erase userdata` and `fastboot erase cache`, letting Android format on first boot.

### 3. Rooting with CF-Auto-Root

Used Chainfire's CF-Auto-Root for hammerhead. The download URL requires a browser (wget gets an HTML redirect page). After downloading the ZIP, flashed via:

```bash
sudo fastboot boot image/CF-Auto-Root-hammerhead-hammerhead-nexus5.img
```

This installed SuperSU automatically. Verified with `adb shell su -c "whoami"` returning `root`.

### 4. Debug Bluetooth Stack Installation

Pushed the prebuilt `bluetooth.default.so` from the InternalBlue repo (`android/android6_0_1/`) to the device:

```bash
adb push bluetooth.default.so /sdcard/bluetooth.default.so
adb shell 'su -c "mount -o remount,rw /system"'
adb shell 'su -c "cp /sdcard/bluetooth.default.so /system/lib/hw/bluetooth.default.so"'
adb shell 'su -c "chmod 644 /system/lib/hw/bluetooth.default.so"'
adb shell 'su -c "chown root:root /system/lib/hw/bluetooth.default.so"'
```

This prebuilt library has HCI forwarding and H4 Broadcom Diagnostics enabled, matching AOSP tag `android-6.0.1_r81`. Building from source (which requires 100GB AOSP tree) was not needed.

Enabled **Bluetooth HCI snoop log** in Developer Options.

### 5. BluetoothAssistant APK Build & Install

The BlueToolkit `install.sh` has a known bug (#17) — the BluetoothAssistant install path is broken. Built the APK manually using Gradle:

- Installed Android SDK command-line tools from Google (the `sdkmanager` from apt installs a VanillaIceCream preview SDK that doesn't work).
- Set up SDK at `~/android-sdk` with `platforms;android-34` and `build-tools;34.0.0`.
- Lowered `minSdk` from 24 to 23 in both `app/build.gradle` and `utilities/build.gradle` to support Android 6.0.1 (API 23).
- Built with `./gradlew assembleDebug` and installed via `adb install`.

Required permissions were granted manually:

```bash
adb shell pm grant xie.morrowind.tool.btassist android.permission.ACCESS_COARSE_LOCATION
adb shell pm grant xie.morrowind.tool.btassist android.permission.ACCESS_FINE_LOCATION
adb shell pm grant xie.morrowind.tool.btassist android.permission.WRITE_EXTERNAL_STORAGE
adb shell pm grant xie.morrowind.tool.btassist android.permission.READ_EXTERNAL_STORAGE
adb shell mkdir -p /storage/emulated/0/Documents
```

### 6. InternalBlue cmd2 Fix

InternalBlue CLI failed with `ImportError: cannot import name 'Fg' from 'cmd2'`. The BlueToolkit venv had cmd2 3.4.0, but InternalBlue needs 2.4.x. Fixed by installing into the venv directly:

```bash
/usr/share/BlueToolkit/.venv/bin/python -m pip install cmd2==2.4.2
```

### 7. Shell Script Fixes for BlueToolkit Exploits

Multiple issues found in the InternalBlue exploit shell scripts under `/usr/share/BlueToolkit/modules/tools/custom_exploits/`:

- **Missing shebang**: Scripts had no `#!/bin/bash` line. Fixed with `sed -i '1i#!/bin/bash'` for all `internalblue_*.sh` files.
- **Wrong Python path**: Scripts used `python3` but InternalBlue is installed in the BlueToolkit venv. Fixed with:
  ```bash
  sed -i 's|python3 \.\./internalblue|/usr/share/BlueToolkit/.venv/bin/python ../internalblue|g' internalblue_*.sh
  ```
- **KNOB PoC blocks**: The `KNOB_PoC.py` script opens an interactive CLI (`cmdloop()`), which blocks the shell script. Replaced with a custom non-interactive script (`knob_noninteractive.py`).

## KNOB Attack Testing

### How InternalBlue KNOB Works

The KNOB attack (CVE-2019-9506) exploits the Bluetooth encryption key negotiation. InternalBlue patches the Nexus 5's Broadcom firmware to always request a 1-byte encryption key. If the target device accepts this weak key and encryption succeeds, the target is vulnerable.

This is different from BrakTooth KNOB, which uses an ESP32 to intercept and modify LMP packets as an external attacker. Both test the same vulnerability but from different perspectives.

### Critical: Preventing False Positives

The initial Python script only checked if `Read Encryption Key Size` returned 1. This produced a **false positive** on the iPhone 13 Pro. HCI log analysis revealed:

- **Encryption Change event** had `Status: Unsupported LMP Parameter Value (0x20)` and `Encryption: Disabled (0x00)` — the iPhone **rejected** the weak key.
- Despite rejection, `Read Encryption Key Size` still returned 1 — this is just the proposed value left in the register, not an agreed-upon key.

The corrected script now checks **both conditions**:
1. `Read Encryption Key Size` returns 1
2. `Encryption Change` event has `Status: Success (0x00)` and `Encryption: Enabled`

Only when both are true is the target reported as vulnerable.

### Methodology

The reliable two-phase approach:

1. **Phase 1 — Pair normally** (no KNOB patch active): Complete SSP pairing with Numeric Comparison on both devices. This stores a link key.
2. **Phase 2 — Install KNOB patch and reconnect**: The KNOB firmware patch modifies key entropy negotiation. Triggering a reconnection reuses the stored link key, going straight to authentication → encryption. This is fast enough for the 0.1s polling to capture the key size.

Initial pairing with the KNOB patch active fails because the full SSP flow (IO capability exchange → NC → user confirm → link key generation) takes too long and the connection window is missed.

### Test Results

#### Samsung Galaxy Note10+ 5G (64:7B:CE:BD:A5:2B)

- **Bluetooth**: 5.0, Broadcom chip (firmware 002.002.008)
- **HCI evidence** (from `/tmp/knob_final.log`):
  - `Encryption Change`: `Status: Success (0x00)`, `Encryption: Enabled with E0 (0x01)`
  - `Read Encryption Key Size`: `Status: Success (0x00)`, `Key size: 1`
  - Connection disconnected ~2 seconds later with `Authentication Failure (0x05)`
- **Python script**: `Raw: 010814000c0001` — Status 0x00, Key size 1
- **Result**: **VULNERABLE** — accepted 1-byte encryption key with encryption enabled
- **Consistent with**: BrakTooth KNOB test result

#### iPhone 13 Pro (14:2D:4D:D8:3C:83)

- **HCI evidence** (from `/tmp/knob_iphone.log`):
  - `Encryption Change`: `Status: Unsupported LMP Parameter Value / Unsupported LL Parameter Value (0x20)`, `Encryption: Disabled (0x00)`
  - `Read Encryption Key Size`: `Status: Success (0x00)`, `Key size: 1`
  - Nexus 5 immediately disconnected after encryption failure
- **Initial Python script result**: Reported key size 1 — **FALSE POSITIVE**
- **Corrected result**: **NOT VULNERABLE** — iPhone rejected the 1-byte key at LMP level; encryption was never enabled

### Key Lesson

**Never rely solely on `Read Encryption Key Size`**. The HCI command can return a key size even when encryption failed. The `Encryption Change` event is the ground truth — check its status code and encryption mode before drawing conclusions. Always verify results against the raw btmon HCI dump.

## BlueToolkit Automation

### Architecture

The automation consists of three files:

1. **`knob_noninteractive.py`** — Python script that installs the KNOB firmware patch, monitors HCI Encryption Change events via callback, polls for key size, and reports results using BlueToolkit's `report_vulnerable()`, `report_not_vulnerable()`, and `report_error()` functions.

2. **`internalblue_KNOB.sh`** — Shell wrapper that handles BluetoothAssistant setup, calls the Python script, pulls HCI logs, and cleans up.

3. **`internalblue_knob.yaml`** — BlueToolkit exploit definition with `max_timeout: 120`.

### BlueToolkit Report Integration

The Python script uses BlueToolkit's standard report functions:

```python
from bluekit.report import report_not_vulnerable, report_vulnerable, report_error

# Encryption enabled + key size 1
report_vulnerable("KNOB Detected - Device accepted 1-byte encryption key (...)")

# Key size 1 but encryption rejected (false positive prevention)
report_not_vulnerable("KNOB Rejected - Key size 1 reported but encryption was NOT enabled (...)")

# Key size > 1
report_not_vulnerable("KNOB Rejected - Device negotiated N-byte key, refused reduced key size")

# Timeout or connection failure
report_error("error - Could not read encryption key size (...)")
```

### Installation

```bash
# Copy the non-interactive KNOB script
cp knob_noninteractive.py /usr/share/BlueToolkit/modules/tools/custom_exploits/
chmod +x /usr/share/BlueToolkit/modules/tools/custom_exploits/knob_noninteractive.py

# Replace the shell script
cp internalblue_KNOB.sh /usr/share/BlueToolkit/modules/tools/custom_exploits/
chmod +x /usr/share/BlueToolkit/modules/tools/custom_exploits/internalblue_KNOB.sh

# Replace the YAML (adds max_timeout: 120)
cp internalblue_knob.yaml /usr/share/BlueToolkit/exploits/
```

### Running via BlueToolkit

```bash
# Pre-pair the target from Nexus 5 Bluetooth settings first, then:
sudo bluekit -t <TARGET_MAC> -e internalblue_knob
```

### Running manually

```bash
cd /usr/share/BlueToolkit/modules/tools/custom_exploits
./internalblue_KNOB.sh <TARGET_MAC> /tmp/knob_output/
```

### Verifying results with btmon

Always cross-check the Python script's verdict against the raw HCI log:

```bash
adb pull /storage/self/primary/btsnoop_hci.log /tmp/knob_verify.log

# Check encryption status (ground truth)
btmon -r /tmp/knob_verify.log | grep -A8 "Encryption Change" | grep -v "Octet"

# Check key size
btmon -r /tmp/knob_verify.log | grep -A8 "Read Encryption Key Size" | grep -v "Octet"
```

Vulnerable: `Encryption: Enabled with E0 (0x01)` + `Key size: 1`
Not vulnerable: `Status: Unsupported LMP Parameter Value (0x20)` + `Encryption: Disabled`

## Known Issues & Workarounds

| Issue | Workaround |
|-------|-----------|
| `fastboot` not detecting device | Unplug/replug USB cable; prefer USB 2.0 ports |
| `mke2fs` failure during factory flash | Use `fastboot erase userdata` instead of format |
| CF-Auto-Root wget redirect | Download ZIP via browser |
| BluetoothAssistant `INSTALL_FAILED_OLDER_SDK` | Lower `minSdk` to 23 in both `app/build.gradle` and `utilities/build.gradle` |
| BluetoothAssistant permission denial | Manually `pm grant` location and storage permissions |
| BluetoothAssistant pairing unreliable | Pair manually from Nexus 5 Bluetooth settings; pre-pair before KNOB test |
| InternalBlue cmd2 import error | Pin `cmd2==2.4.2` in the BlueToolkit venv |
| Exploit `.sh` missing shebang | Add `#!/bin/bash` to first line |
| KNOB PoC blocks on interactive CLI | Use `knob_noninteractive.py` instead |
| Key size reading timeout | Poll at 0.1s intervals in background thread |
| KNOB false positive (key size 1 but encryption rejected) | Check Encryption Change event status via HCI callback before reporting |
| Fresh pairing fails with KNOB patch active | Pre-pair without patch, then run KNOB on reconnection |
| Unpairing devices between tests | Use `service call bluetooth_manager 10` or delete `bt_config.conf` |

## File Locations

| Item | Path |
|------|------|
| BlueToolkit install | `/usr/share/BlueToolkit/` |
| InternalBlue | `/usr/share/BlueToolkit/modules/tools/internalblue/` |
| Exploit YAMLs | `/usr/share/BlueToolkit/exploits/` |
| Exploit scripts | `/usr/share/BlueToolkit/modules/tools/custom_exploits/` |
| KNOB helper script | `/usr/share/BlueToolkit/modules/tools/custom_exploits/knob_noninteractive.py` |
| BluetoothAssistant | `/usr/share/BlueToolkit/modules/BluetoothAssistant/` |
| BlueToolkit venv | `/usr/share/BlueToolkit/.venv/` |
| BlueToolkit logs | `/usr/share/BlueToolkit/.logs/bluetoolkit.log` |
| HCI snoop logs | `/storage/self/primary/btsnoop_hci.log` (on device) |
| Android SDK | `~/android-sdk/` |