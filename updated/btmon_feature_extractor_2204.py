#!/usr/bin/env python3
"""
btmon_feature_extractor.py

Extracts LMP features of a remote Bluetooth device by:

  Mode 1 (--hcitool-only, DEFAULT):
    Parse `hcitool info` output directly for LMP version and feature hex bytes.
    Works on Ubuntu 22.04 (BlueZ 5.64) and 24.04 (BlueZ 5.72+).
    Does NOT require btmon.

  Mode 2 (--btmon):
    Original btmon-based capture with label matching + hex fallback.
    Best with BlueZ 5.72+ (Ubuntu 24.04).

The output is compatible with:
  - bluekit_recon_based_check.py's find_and_extract_data()
  - recon.py's determine_bluetooth_version()

Usage:
    sudo python3 btmon_feature_extractor.py -t AA:BB:CC:DD:EE:FF
    sudo python3 btmon_feature_extractor.py -t AA:BB:CC:DD:EE:FF --btmon
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
# Decode features from raw hex bytes (used by BOTH modes)
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


# ===========================================================================
# MODE 1: hcitool-only (default) — works on Ubuntu 22.04 and 24.04
# ===========================================================================

def run_hcitool_capture(target, timeout=15, retries=3):
    """
    Extract LMP features using only hcitool (no btmon needed).

    Strategy:
      1. `hcitool info <target>` prints LMP version and feature page hex.
      2. If page 0 only, use `hcitool cc` + raw HCI commands to request
         extended feature pages.
      3. Parse all output for version and feature hex bytes.

    hcitool info output format (all BlueZ versions):
        BD Address:  XX:XX:XX:XX:XX:XX
        Device Name: SomeDevice
        LMP Version: 4.2 (0x8) LMP Subversion: 0xNNNN
        Manufacturer: Company (NNN)
        Features page 0: 0xbf 0xee 0x0d 0xfe 0xdb 0xff 0x7b 0x87
        Features page 1: 0x0f 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        Features page 2: 0x77 0x03 0x00 0x00 0x00 0x00 0x00 0x00

    Returns (raw_output, features_dict, bt_version).
    """
    raw_output = ""
    features = dict(ALL_FEATURES)
    bt_version = None
    pages_found = {}

    for attempt in range(1, retries + 1):
        print("[*] Attempt {}/{}: hcitool info {} ...".format(
            attempt, retries, target))

        try:
            result = subprocess.run(
                ["hcitool", "info", target],
                capture_output=True, text=True,
                timeout=timeout
            )
            output = result.stdout + result.stderr
            raw_output += output + "\n"

            if result.returncode != 0 and not output.strip():
                print("[!] hcitool info failed (rc={}), retrying...".format(
                    result.returncode))
                time.sleep(2)
                continue

        except subprocess.TimeoutExpired:
            print("[!] hcitool info timed out ({}s), retrying...".format(timeout))
            time.sleep(2)
            continue
        except FileNotFoundError:
            print("[-] hcitool not found. Install bluez: sudo apt install bluez")
            sys.exit(1)

        # --- Parse LMP Version ---
        vm = re.search(r'LMP\s+Version:\s*(\d+\.\d+)\s*\(', output)
        if vm:
            bt_version = vm.group(1)
            print("[+] LMP Version: {}".format(bt_version))

        # --- Parse Feature pages ---
        # Matches: "Features page N: 0xNN 0xNN ..."
        for m in re.finditer(
            r'Features\s+page\s+(\d+):\s+((?:0x[0-9a-fA-F]{2}\s*)+)',
            output
        ):
            page_num = int(m.group(1))
            hex_vals = [int(x, 16) for x in m.group(2).split()]
            pages_found[page_num] = hex_vals
            print("[+] Found feature page {}: {}".format(
                page_num,
                " ".join("0x{:02x}".format(b) for b in hex_vals)
            ))

        if pages_found:
            break
        else:
            print("[!] No feature pages in output, retrying...")
            time.sleep(2)

    # --- If hcitool info only returned page 0, try to get extended pages ---
    if 0 in pages_found and 1 not in pages_found:
        print("[*] Only page 0 found, requesting extended pages via HCI...")
        ext_pages = _request_extended_pages_hcitool(target, timeout)
        pages_found.update(ext_pages)

    # --- Decode all pages ---
    for page_num, hex_vals in sorted(pages_found.items()):
        decode_features_from_hex(page_num, hex_vals, features)

    return raw_output, features, bt_version


def _request_extended_pages_hcitool(target, timeout=15):
    """
    Request extended feature pages by creating an ACL connection
    and sending raw HCI Read Remote Extended Features commands.

    Returns dict of {page_num: [hex_bytes]} from btmon output.
    Falls back to empty dict if btmon is not available.
    """
    pages = {}

    # Check if btmon is available for capturing responses
    btmon_available = True
    try:
        subprocess.run(["which", "btmon"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        btmon_available = False
        print("[!] btmon not available, cannot request extended pages")
        return pages

    # Start btmon to capture responses
    try:
        btmon_proc = subprocess.Popen(
            ["btmon"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
    except Exception:
        return pages

    time.sleep(0.5)

    # Create connection
    handle = None
    try:
        subprocess.run(
            ["hcitool", "cc", target],
            capture_output=True, text=True, timeout=timeout
        )
        time.sleep(0.5)
        handle = _get_connection_handle(target)
    except Exception:
        pass

    if handle is not None:
        print("[+] Connected (handle={})".format(handle))
        for pg in range(1, 4):  # pages 1, 2, 3
            _send_read_remote_extended_features(handle, pg)
            time.sleep(0.5)
        time.sleep(1)

        # Disconnect
        try:
            subprocess.run(
                ["hcitool", "dc", target],
                capture_output=True, text=True, timeout=5
            )
        except Exception:
            pass
    else:
        print("[!] Could not establish connection for extended pages")

    # Collect btmon output
    time.sleep(0.5)
    btmon_text = _stop_btmon(btmon_proc)

    # Parse extended feature pages from btmon
    # Look for "Page: X/Y" + "Features: 0xNN ..." patterns
    lines = btmon_text.splitlines()
    for i, line in enumerate(lines):
        pm = re.match(r'\s*Page:\s*(\d+)/(\d+)', line)
        if pm:
            page_num = int(pm.group(1))
            for j in range(i + 1, min(len(lines), i + 4)):
                fm = re.match(
                    r'\s*Features:\s+((?:0x[0-9a-fA-F]{2}\s*)+)',
                    lines[j]
                )
                if fm:
                    hex_vals = [int(x, 16) for x in fm.group(1).split()]
                    if not all(b == 0 for b in hex_vals):
                        pages[page_num] = hex_vals
                        print("[+] Extended page {} from btmon: {}".format(
                            page_num,
                            " ".join("0x{:02x}".format(b) for b in hex_vals)
                        ))
                    break

    return pages


# ===========================================================================
# MODE 2: btmon-based capture (original method, best with BlueZ 5.72+)
# ===========================================================================

def discover_target_mac(btmon_text, target):
    """
    Extract only HCI blocks from btmon output that reference the target MAC.
    """
    lines = btmon_text.splitlines()

    blocks = []
    current_block = []
    for line in lines:
        stripped = line.lstrip()
        is_boundary = False
        if stripped:
            if stripped[0] in '<>':
                is_boundary = True
            elif (stripped.startswith(('hcitool[', 'btmon['))
                  or re.match(r'^\[\d+\]:', stripped)):
                is_boundary = True
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
    Parse filtered btmon text and extract LMP features and Bluetooth version.
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
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        pm = re.match(r'Page:\s*(\d+)/\d+', stripped)
        if pm:
            page_num = int(pm.group(1))
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


def _get_connection_handle(target):
    """Get the ACL connection handle for the target device."""
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
    """Send HCI Read Remote Extended Features command for a specific page."""
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
    """Run btmon + hcitool to capture remote device features (original mode)."""
    btmon_output = ""
    filtered_text = ""
    MAX_EXTENDED_PAGE = 3

    for attempt in range(1, retries + 1):
        print("[*] Attempt {}/{}: capturing features for {}".format(
            attempt, retries, target))

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

        print("[*] Creating ACL connection to {} ...".format(target))
        handle = None
        try:
            subprocess.run(
                ["hcitool", "cc", target],
                capture_output=True, text=True, timeout=timeout
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
            print("[-] hcitool not found.")
            _stop_btmon(btmon_proc)
            sys.exit(1)

        if handle is not None:
            print("[*] Running hcitool info {} ...".format(target))
            try:
                subprocess.run(
                    ["hcitool", "info", target],
                    capture_output=True, text=True, timeout=timeout
                )
                print("[+] hcitool info completed")
            except subprocess.TimeoutExpired:
                print("[!] hcitool info timed out ({}s)".format(timeout))
            except Exception as e:
                print("[!] hcitool info error: {}".format(e))

            time.sleep(0.5)
            handle = _get_connection_handle(target)
            if handle is None:
                print("[*] Connection dropped after info, reconnecting...")
                try:
                    subprocess.run(
                        ["hcitool", "cc", target],
                        capture_output=True, text=True, timeout=timeout
                    )
                    time.sleep(1)
                    handle = _get_connection_handle(target)
                except Exception:
                    pass

            if handle is not None:
                print("[*] Requesting extended feature pages 2..{} "
                      "(handle={})".format(MAX_EXTENDED_PAGE, handle))
                for pg in range(2, MAX_EXTENDED_PAGE + 1):
                    _send_read_remote_extended_features(handle, pg)
                    time.sleep(0.5)
                time.sleep(1)
            else:
                print("[!] Could not re-establish connection for extra pages")

        try:
            subprocess.run(
                ["hcitool", "dc", target],
                capture_output=True, text=True, timeout=5
            )
        except Exception:
            pass

        time.sleep(0.5)
        btmon_output += _stop_btmon(btmon_proc)
        filtered_text = discover_target_mac(btmon_output, target)

        all_captured, status_msg = _check_all_feature_pages(filtered_text)
        if all_captured:
            print("[+] {}".format(status_msg))
            break
        else:
            print("[!] {}, retrying...".format(status_msg))
            time.sleep(2)

    return btmon_output, filtered_text


def _check_all_feature_pages(filtered_text):
    """Check whether the filtered btmon text contains all required feature data."""
    has_supported = "Read Remote Supported Features" in filtered_text
    has_extended = "Read Remote Extended Features" in filtered_text

    if not has_supported and not has_extended:
        return False, "No feature events captured for target"
    if not has_supported:
        return False, "Missing Read Remote Supported Features (page 0)"
    if not has_extended:
        return False, "Missing Read Remote Extended Features (pages 1+)"

    page_matches = re.findall(r'Page:\s*(\d+)/(\d+)', filtered_text)
    if not page_matches:
        return True, "Feature data captured (Supported + Extended)"

    max_page = max(int(m[1]) for m in page_matches)
    captured_pages = set(int(m[0]) for m in page_matches)
    expected_pages = set(range(1, max_page + 1))
    missing_pages = expected_pages - captured_pages

    if missing_pages:
        return False, ("Feature data incomplete: have pages {}, "
                       "missing page(s) {} out of 1..{}".format(
                           sorted(captured_pages), sorted(missing_pages),
                           max_page))

    return True, ("Feature data captured (Supported + Extended pages "
                  "1..{})".format(max_page))


# ===========================================================================
# Output
# ===========================================================================

def write_bluing_format(features, bt_version, output_path):
    """Write features in bluing_lmp.log compatible format."""
    with open(output_path, 'w') as f:
        if bt_version:
            f.write("Version: Bluetooth Core Specification {} (LMP)\n".format(
                bt_version))
        else:
            f.write("Version: unknown\n")

        f.write("\n")
        f.write("LMP features\n")
        f.write("\n")
        f.write("Extended LMP features\n")
        f.write("\n")

        for key, val in features.items():
            f.write("{}: {}\n".format(key, val))

    print("[+] Features written to {}".format(output_path))


# ===========================================================================
# Main
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Extract LMP features of a remote Bluetooth device"
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
        help="Timeout in seconds for hcitool (default: 15)"
    )
    parser.add_argument(
        "--retries", required=False, type=int, default=3,
        help="Number of connection attempts (default: 3)"
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--hcitool-only", action="store_true", default=True,
        help="Use hcitool info parsing only — no btmon (DEFAULT, works on "
             "Ubuntu 22.04 and 24.04)"
    )
    mode_group.add_argument(
        "--btmon", action="store_true", default=False,
        help="Use btmon-based capture (original mode, best with BlueZ 5.72+)"
    )

    parser.add_argument(
        "--dump-btmon", required=False, action="store_true",
        help="Also dump raw output to btmon_raw.log"
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
    print("Mode:    {}".format("btmon" if args.btmon else "hcitool-only"))
    print("=" * 60)

    features = dict(ALL_FEATURES)

    if args.btmon:
        # ---- Original btmon mode ----
        btmon_text, filtered_text = run_btmon_capture(
            target, timeout=args.timeout, retries=args.retries
        )

        if not btmon_text.strip():
            print("[-] No btmon output captured. Is the Bluetooth adapter up?")
            print("    Try: sudo hciconfig hci0 up")
            sys.exit(1)

        if args.dump_btmon:
            dump_path = os.path.join(os.path.dirname(output_path),
                                     "btmon_raw.log")
            with open(dump_path, 'w') as f:
                f.write(filtered_text)
            print("[+] Filtered btmon output saved to {}".format(dump_path))

        if not filtered_text.strip():
            print("[-] No btmon blocks matched the target MAC address.")
            filtered_text = btmon_text

        bt_version = parse_btmon_output_targeted(filtered_text, features)

    else:
        # ---- hcitool-only mode (DEFAULT) ----
        raw_output, features, bt_version = run_hcitool_capture(
            target, timeout=args.timeout, retries=args.retries
        )

        if args.dump_btmon:
            dump_path = os.path.join(os.path.dirname(output_path),
                                     "hcitool_raw.log")
            with open(dump_path, 'w') as f:
                f.write(raw_output)
            print("[+] Raw hcitool output saved to {}".format(dump_path))

    # --- Print summary ---
    if bt_version:
        print("[+] Bluetooth version detected: {}".format(bt_version))
    else:
        print("[!] Could not determine Bluetooth version")

    print("")
    print("=" * 60)
    print("Extracted Features for {}:".format(target))
    print("=" * 60)
    if bt_version:
        print("  Version: Bluetooth Core Specification {} (LMP)".format(
            bt_version))
    else:
        print("  Version: unknown")
    print("")
    for key, val in features.items():
        status = "✓" if val else "✗"
        print("  [{}] {}: {}".format(status, key, val))
    print("=" * 60)

    # --- Write output ---
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
        print("    - Device returned all-zero features")
        print("    - Device was not fully connected (try pairing mode)")
        print("    - hcitool info timed out on all attempts")
        print("    Tip: run 'sudo hcitool info {}' manually first".format(
            target))


if __name__ == "__main__":
    main()