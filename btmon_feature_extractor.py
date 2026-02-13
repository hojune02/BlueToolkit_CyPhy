#!/usr/bin/env python3
"""
btmon_feature_extractor.py

Extracts LMP features of a remote Bluetooth device by:
1. Starting btmon in the background to capture HCI events
2. Running hcitool info to trigger Read Remote Supported/Extended Features
3. Parsing btmon output for feature labels AND Bluetooth version
4. Writing results in bluing_lmp.log-compatible format

TARGET-AWARE PARSING:
  btmon captures ALL HCI traffic including LE advertising from nearby devices.
  This script extracts only the HCI blocks that reference the target MAC
  address. A "block" is text that starts with a line beginning with > or <,
  contains the target MAC somewhere inside, and ends just before the next
  line beginning with > or <. Only the matched blocks are saved to
  btmon_raw.log and used for feature/version parsing.

The output is compatible with:
  - bluekit_recon_based_check.py's find_and_extract_data()
  - recon.py's determine_bluetooth_version()

Usage:
    sudo python3 btmon_feature_extractor.py -t AA:BB:CC:DD:EE:FF
    sudo python3 btmon_feature_extractor.py -t AA:BB:CC:DD:EE:FF -o /path/to/output.log
    sudo python3 btmon_feature_extractor.py -t AA:BB:CC:DD:EE:FF --retries 5 --timeout 20
"""

import argparse
import os
import re
import signal
import subprocess
import sys
import time

# ---------------------------------------------------------------------------
# Feature labels as they appear in btmon decoded output.
#
# IMPORTANT: btmon label strings differ from bluing output strings.
# These mappings were verified against btmon ver 5.72 output.
#
# Page 0: "Read Remote Supported Features" event
# Pages 1+: "Read Remote Extended Features" event
# ---------------------------------------------------------------------------

# btmon label (exact) -> bluing_lmp.log compatible output key
FEATURE_LABEL_MAP = {
    # ---- Page 0 (Read Remote Supported Features) ----
    "LE Supported (Controller)":
        "LE Supported (Controller)",
    "Simultaneous LE and BR/EDR (Controller)":
        "Simultaneous LE and BR/EDR to Same Device Capable (Controller)",
    "Secure Simple Pairing":
        "Secure Simple Pairing (Controller Support)",

    # ---- Page 1 (Read Remote Extended Features, Host) ----
    # btmon prints these WITHOUT "to Same Device Capable" for page 1
    "Secure Simple Pairing (Host Support)":
        "Secure Simple Pairing (Host Support)",
    "LE Supported (Host)":
        "LE Supported (Host)",
    "Simultaneous LE and BR/EDR (Host)":
        "Simultaneous LE and BR/EDR to Same Device Capable (Host)",

    "Secure Connections (Host Support)":
        "Secure Connections (Host Support)",

    # ---- Page 2 (Read Remote Extended Features, Controller) ----
    "Secure Connections (Controller Support)":
        "Secure Connections (Controller Support)",
}

# All output keys and their default values
ALL_FEATURES = {
    "LE Supported (Controller)": False,
    "LE Supported (Host)": False,
    "Simultaneous LE and BR/EDR to Same Device Capable (Controller)": False,
    "Simultaneous LE and BR/EDR to Same Device Capable (Host)": False,
    "Secure Simple Pairing (Controller Support)": False,
    "Secure Simple Pairing (Host Support)": False,
    "Secure Connections (Controller Support)": False,
    "Secure Connections (Host Support)": False,
}

# ---------------------------------------------------------------------------
# Fallback: decode features from raw hex bytes
# ---------------------------------------------------------------------------

PAGE0_BITS = {
    "LE Supported (Controller)":                                        (4, 0x40),
    "Secure Simple Pairing (Controller Support)":                       (6, 0x08),
    "Simultaneous LE and BR/EDR to Same Device Capable (Controller)":   (6, 0x40),
}

PAGE1_BITS = {
    "Secure Simple Pairing (Host Support)":                             (0, 0x01),
    "LE Supported (Host)":                                              (0, 0x02),
    "Simultaneous LE and BR/EDR to Same Device Capable (Host)":         (0, 0x04),
    "Secure Connections (Host Support)":                                 (0, 0x08),
}

PAGE2_BITS = {
    "Secure Connections (Controller Support)":                           (1, 0x01),
}


def decode_features_from_hex(page_num, hex_bytes, features):
    """Decode feature bits from raw hex bytes for a given page number."""
    if page_num == 0:
        bit_map = PAGE0_BITS
    elif page_num == 1:
        bit_map = PAGE1_BITS
    elif page_num == 2:
        bit_map = PAGE2_BITS
    else:
        return

    for feature_key, (byte_idx, mask) in bit_map.items():
        if byte_idx < len(hex_bytes) and (hex_bytes[byte_idx] & mask):
            features[feature_key] = True


def discover_target_mac(btmon_text, target):
    """
    Extract only HCI blocks from btmon output that reference the target MAC.

    btmon output is structured as blocks separated by header lines.
    A new block starts at any line that is a boundary:
      - Lines starting with '>' or '<' (HCI event/command direction markers)
      - Lines starting with 'hcitool[', 'btmon[', or '[PID]:' (tool output)
      - Lines starting with '@ ' (MGMT events)

    This function keeps only blocks whose text contains the target MAC.
    The pattern conceptually is:
        starts with > or <  ...  contains target  ...  ends at next > or <

    Returns the concatenated text of all matched blocks.
    """
    lines = btmon_text.splitlines()

    # Split into blocks. A new block starts at any "boundary" line.
    blocks = []
    current_block = []
    for line in lines:
        stripped = line.lstrip()
        is_boundary = False
        if stripped:
            # HCI direction markers
            if stripped[0] in '<>':
                is_boundary = True
            # Tool/daemon output lines (e.g. "hcitool[1422392]: ...")
            elif (stripped.startswith(('hcitool[', 'btmon['))
                  or re.match(r'^\[\d+\]:', stripped)):
                is_boundary = True
            # MGMT events (e.g. "@ MGMT Event: ...")
            elif stripped.startswith('@ '):
                is_boundary = True

        if is_boundary:
            if current_block:
                blocks.append(current_block)
            current_block = [line]
        else:
            current_block.append(line)
    if current_block:
        blocks.append(current_block)

    # Keep blocks that contain the target MAC address
    target_upper = target.upper()
    matched_blocks = []
    for block in blocks:
        block_text = "\n".join(block)
        if target_upper in block_text.upper():
            matched_blocks.append(block_text)

    if matched_blocks:
        print("[+] Found {} btmon block(s) matching target {}".format(
            len(matched_blocks), target))
    else:
        print("[!] No btmon blocks matched target {}, "
              "will process all events".format(target))

    return "\n".join(matched_blocks)


def parse_btmon_output_targeted(filtered_text, features):
    """
    Parse filtered btmon text (already limited to target-relevant blocks)
    and extract LMP features and the Bluetooth version.

    Feature detection:
      - Label matching: each line is checked against FEATURE_LABEL_MAP keys.
      - Hex fallback: if a "Features:" hex line is found without any label
        matches in the same block, the raw bytes are decoded.

    Version detection:
      - Looks for "LMP version: Bluetooth X.Y (0xNN)" in the text.

    Returns the Bluetooth version string (e.g. "4.2") or None.
    """
    lines = filtered_text.splitlines()
    bt_version = None

    # --- Extract Bluetooth version ---
    for line in lines:
        vm = re.search(
            r'LMP [Vv]ersion:\s*Bluetooth\s+(\d+\.\d+)\s*\(', line
        )
        if vm:
            bt_version = vm.group(1)
            break

    # --- Extract features via label matching ---
    for line in lines:
        stripped = line.strip()
        for btmon_label, output_key in FEATURE_LABEL_MAP.items():
            if stripped == btmon_label or stripped.startswith(btmon_label):
                features[output_key] = True

    # --- Hex fallback: decode Features: hex lines if label match missed ---
    # Process per-block: find "Page: N/M" + "Features: 0x..." pairs
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        # Detect page number (e.g. "Page: 0/2", "Page: 1/2")
        pm = re.match(r'Page:\s*(\d+)/\d+', stripped)
        if pm:
            page_num = int(pm.group(1))
            # Look for "Features:" line nearby (within next 3 lines)
            for j in range(i + 1, min(len(lines), i + 4)):
                fm = re.match(
                    r'Features:\s+((?:0x[0-9a-fA-F]{2}\s*)+)',
                    lines[j].strip()
                )
                if fm:
                    hex_vals = [int(x, 16) for x in fm.group(1).split()]
                    if not all(b == 0 for b in hex_vals):
                        decode_features_from_hex(page_num, hex_vals, features)
                    break
        i += 1

    return bt_version


def write_bluing_format(features, bt_version, output_path):
    """
    Write features in bluing_lmp.log compatible format.

    The file must contain:
    1. A version line matching: "Bluetooth Core Specification X.Y "
       (required by recon.py determine_bluetooth_version() regex:
        REGEX_BT_VERSION = "Bluetooth Core Specification [0-9]{1}(\\.){0,1}[0-9]{0,1} "
        Then: output.split(" ")[3] extracts the version number.
        On "Bluetooth Core Specification 4.2 (LMP)":
          split(" ") -> ["Bluetooth","Core","Specification","4.2","(LMP)"]
                                                             ^^^^ index 3
       )
    2. Feature lines: "Key: True" / "Key: False"
       (required by bluekit_recon_based_check.py find_and_extract_data())
    """
    with open(output_path, 'w') as f:
        # Version section
        if bt_version:
            f.write("Version: Bluetooth Core Specification {} (LMP)\n".format(bt_version))
        else:
            f.write("Version: unknown\n")

        f.write("\n")
        f.write("LMP features\n")
        f.write("\n")
        f.write("Extended LMP features\n")
        f.write("\n")

        # Feature lines
        for key, val in features.items():
            f.write("{}: {}\n".format(key, val))

    print("[+] Features written to {}".format(output_path))


def _get_connection_handle(target):
    """
    Get the ACL connection handle for the target device from hcitool con.

    Returns the handle as an integer, or None if not connected.
    """
    try:
        result = subprocess.run(
            ["hcitool", "con"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if target.upper() in line.upper():
                m = re.search(r'handle\s+(\d+)', line)
                if m:
                    return int(m.group(1))
    except Exception:
        pass
    return None


def _send_read_remote_extended_features(handle, page_num):
    """
    Send HCI Read Remote Extended Features command for a specific page.

    HCI command: OGF=0x01 OCF=0x001c
    Parameters: Connection_Handle (2 bytes LE) + Page_Number (1 byte)
    """
    # Handle as 2 bytes little-endian
    handle_lo = handle & 0xFF
    handle_hi = (handle >> 8) & 0xFF
    cmd = [
        "hcitool", "cmd", "0x01", "0x001c",
        "0x{:02x}".format(handle_lo),
        "0x{:02x}".format(handle_hi),
        "0x{:02x}".format(page_num),
    ]
    print("[*] Sending Read Remote Extended Features page {} "
          "(handle={})".format(page_num, handle))
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    except Exception as e:
        print("[!] Failed to send extended features request: {}".format(e))


def _stop_btmon(btmon_proc):
    """Stop btmon and collect its output."""
    try:
        os.killpg(os.getpgid(btmon_proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        stdout, stderr = btmon_proc.communicate(timeout=5)
        return stdout.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        btmon_proc.kill()
        stdout, stderr = btmon_proc.communicate()
        return stdout.decode("utf-8", errors="replace")


def run_btmon_capture(target, timeout=15, retries=10):
    """
    Run btmon + hcitool to capture remote device features.

    Strategy:
      1. Start btmon to capture HCI events.
      2. Create a persistent ACL connection with hcitool cc.
      3. Use hcitool info to trigger page-0 supported features and
         page-1 extended features.
      4. While still connected, proactively request extended feature
         pages 2 and 3 via raw HCI commands (hcitool cmd). The
         controller will return an error for non-existent pages, which
         is harmless — this avoids needing to inspect btmon output
         mid-stream to discover how many pages exist.
      5. Disconnect, collect btmon output, filter to target blocks.
      6. Retry if not all pages were captured.

    Returns (btmon_output, filtered_text):
      btmon_output  – full raw btmon text (accumulated across retries)
      filtered_text – concatenated target-matching blocks
    """
    btmon_output = ""
    filtered_text = ""

    # Maximum extended feature page to request proactively.
    # Most devices have 2 pages (0-based: page 0 via Supported Features,
    # pages 1-2 via Extended Features). Page 3 is very rare but harmless
    # to request — the controller returns an error if it doesn't exist.
    MAX_EXTENDED_PAGE = 3

    for attempt in range(1, retries + 1):
        print("[*] Attempt {}/{}: capturing features for {}".format(attempt, retries, target))

        # --- Start btmon ---
        try:
            btmon_proc = subprocess.Popen(
                ["btmon"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
        except FileNotFoundError:
            print("[-] btmon not found. Install bluez: sudo apt install bluez")
            sys.exit(1)

        time.sleep(1)

        # --- Create persistent connection ---
        print("[*] Creating ACL connection to {} ...".format(target))
        handle = None
        try:
            subprocess.run(
                ["hcitool", "cc", target],
                capture_output=True, text=True,
                timeout=timeout
            )
            time.sleep(1)
            handle = _get_connection_handle(target)
            if handle is not None:
                print("[+] Connected (handle={})".format(handle))
            else:
                print("[!] hcitool cc succeeded but no handle found")
        except subprocess.TimeoutExpired:
            print("[!] hcitool cc timed out ({}s)".format(timeout))
        except FileNotFoundError:
            print("[-] hcitool not found. Install bluez: sudo apt install bluez")
            _stop_btmon(btmon_proc)
            sys.exit(1)

        if handle is not None:
            # --- Trigger Read Remote Supported Features (page 0) ---
            # hcitool info on an already-connected device triggers the
            # feature exchange without creating a second connection.
            print("[*] Running hcitool info {} ...".format(target))
            try:
                subprocess.run(
                    ["hcitool", "info", target],
                    capture_output=True, text=True,
                    timeout=timeout
                )
                print("[+] hcitool info completed")
            except subprocess.TimeoutExpired:
                print("[!] hcitool info timed out ({}s)".format(timeout))
            except Exception as e:
                print("[!] hcitool info error: {}".format(e))

            # Brief pause to let the controller complete page 1 exchange
            time.sleep(0.5)

            # Re-check handle (hcitool info may have disconnected)
            handle = _get_connection_handle(target)
            if handle is None:
                # Reconnect
                print("[*] Connection dropped after info, reconnecting...")
                try:
                    subprocess.run(
                        ["hcitool", "cc", target],
                        capture_output=True, text=True,
                        timeout=timeout
                    )
                    time.sleep(1)
                    handle = _get_connection_handle(target)
                except Exception:
                    pass

            if handle is not None:
                # --- Proactively request extended feature pages 2..N ---
                print("[*] Requesting extended feature pages 2..{} "
                      "(handle={})".format(MAX_EXTENDED_PAGE, handle))
                for pg in range(2, MAX_EXTENDED_PAGE + 1):
                    _send_read_remote_extended_features(handle, pg)
                    time.sleep(0.5)

                # Wait for responses
                time.sleep(1)
            else:
                print("[!] Could not re-establish connection for extra pages")

        # --- Disconnect ---
        try:
            subprocess.run(
                ["hcitool", "dc", target],
                capture_output=True, text=True,
                timeout=5
            )
        except Exception:
            pass

        # --- Stop btmon and collect output ---
        time.sleep(0.5)
        btmon_output += _stop_btmon(btmon_proc)

        # Filter to only blocks that reference the target MAC
        filtered_text = discover_target_mac(btmon_output, target)

        # Check that filtered blocks contain ALL required feature pages
        all_captured, status_msg = _check_all_feature_pages(filtered_text)

        if all_captured:
            print("[+] {}".format(status_msg))
            break
        else:
            print("[!] {}, retrying...".format(status_msg))
            time.sleep(2)

    return btmon_output, filtered_text


def _check_all_feature_pages(filtered_text):
    """
    Check whether the filtered btmon text contains all required feature data.

    Requirements:
      1. "Read Remote Supported Features" must be present (page 0).
      2. "Read Remote Extended Features" must be present (pages 1+).
      3. ALL extended feature pages must be captured. btmon prints
         "Page: X/Y" where Y is the max page number. We need pages
         1/Y through Y/Y to all be present.

    Returns (ok, message):
      ok      – True if all pages are captured
      message – human-readable status string
    """
    has_supported = "Read Remote Supported Features" in filtered_text
    has_extended = "Read Remote Extended Features" in filtered_text

    if not has_supported and not has_extended:
        return False, "No feature events captured for target"

    if not has_supported:
        return False, "Missing Read Remote Supported Features (page 0)"

    if not has_extended:
        return False, "Missing Read Remote Extended Features (pages 1+)"

    # Parse all "Page: X/Y" lines to find max page and which pages we have
    page_matches = re.findall(r'Page:\s*(\d+)/(\d+)', filtered_text)
    if not page_matches:
        # Extended features header exists but no Page: X/Y lines found;
        # accept what we have
        return True, "Feature data captured (Supported + Extended)"

    # Determine the max page number and collect captured pages
    max_page = max(int(m[1]) for m in page_matches)
    captured_pages = set(int(m[0]) for m in page_matches)
    expected_pages = set(range(1, max_page + 1))  # pages 1 through max_page
    missing_pages = expected_pages - captured_pages

    if missing_pages:
        return False, ("Feature data incomplete: have pages {}, "
                       "missing page(s) {} out of 1..{}".format(
                           sorted(captured_pages), sorted(missing_pages), max_page))

    return True, ("Feature data captured (Supported + Extended pages "
                  "1..{})".format(max_page))


def main():
    parser = argparse.ArgumentParser(
        description="Extract LMP features of a remote Bluetooth device using btmon"
    )
    parser.add_argument(
        "-t", "--target", required=True, type=str,
        help="Target Bluetooth MAC address"
    )
    parser.add_argument(
        "-o", "--output", required=False, type=str, default=None,
        help="Output file path (default: bluing_lmp.log in BlueToolkit recon dir)"
    )
    parser.add_argument(
        "--timeout", required=False, type=int, default=15,
        help="Timeout in seconds for hcitool info (default: 15)"
    )
    parser.add_argument(
        "--retries", required=False, type=int, default=3,
        help="Number of connection attempts (default: 3)"
    )
    parser.add_argument(
        "--dump-btmon", required=False, action="store_true",
        help="Also dump raw btmon output to btmon_raw.log"
    )
    args = parser.parse_args()

    if os.geteuid() != 0:
        print("[-] This script must be run as root (sudo)")
        sys.exit(1)

    target = args.target

    if args.output:
        output_path = args.output
    else:
        recon_dir = "/usr/share/BlueToolkit/data/tests/{}/recon".format(target)
        os.makedirs(recon_dir, exist_ok=True)
        output_path = os.path.join(recon_dir, "bluing_lmp.log")

    print("=" * 60)
    print("btmon Feature Extractor")
    print("Target:  {}".format(target))
    print("Output:  {}".format(output_path))
    print("=" * 60)

    features = dict(ALL_FEATURES)

    btmon_text, filtered_text = run_btmon_capture(
        target,
        timeout=args.timeout,
        retries=args.retries
    )

    if not btmon_text.strip():
        print("[-] No btmon output captured. Is the Bluetooth adapter up?")
        print("    Try: sudo hciconfig hci0 up")
        sys.exit(1)

    if args.dump_btmon:
        dump_path = os.path.join(os.path.dirname(output_path), "btmon_raw.log")
        with open(dump_path, 'w') as f:
            f.write(filtered_text)
        print("[+] Filtered btmon output saved to {}".format(dump_path))

    if not filtered_text.strip():
        print("[-] No btmon blocks matched the target MAC address.")
        print("    The device may not have responded. Try putting it in pairing mode.")
        print("    Tip: try running 'sudo hcitool info {}' manually first".format(target))
        # Fall back to full btmon text as last resort
        filtered_text = btmon_text

    # Parse features AND version from the filtered text
    bt_version = parse_btmon_output_targeted(filtered_text, features)

    if bt_version:
        print("[+] Bluetooth version detected: {}".format(bt_version))
    else:
        print("[!] Could not determine Bluetooth version from btmon output")

    # Print summary
    print("")
    print("=" * 60)
    print("Extracted Features for {}:".format(target))
    print("=" * 60)
    if bt_version:
        print("  Version: Bluetooth Core Specification {} (LMP)".format(bt_version))
    else:
        print("  Version: unknown")
    print("")
    for key, val in features.items():
        status = "✓" if val else "✗"
        print("  [{}] {}: {}".format(status, key, val))
    print("=" * 60)

    # Write output
    write_bluing_format(features, bt_version, output_path)

    supported_count = sum(1 for v in features.values() if v)
    print("")
    print("[+] Done. {}/{} features detected as supported.".format(
        supported_count, len(features)
    ))

    if bt_version is None:
        print("[!] WARNING: Bluetooth version not detected.")
        print("    determine_bluetooth_version() will fall back to hciinfo.log.")

    if supported_count == 0:
        print("[!] WARNING: No features detected. Possible causes:")
        print("    - Device returned all-zero features (Chipsguide/budget chipsets)")
        print("    - Device was not fully connected (try putting it in pairing mode)")
        print("    - hcitool info timed out on all attempts")
        print("    Tip: try running 'sudo hcitool info {}' manually first".format(target))


if __name__ == "__main__":
    main()