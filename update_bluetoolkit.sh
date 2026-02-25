#!/bin/bash

set -e  # Exit immediately if a command fails

BLUEKIT_BASE="/usr/share/BlueToolkit"
UPDATED_DIR="./updated"

echo "[*] Starting BlueToolkit update script..."

# ---- Check Ubuntu Version ----
if [ -f /etc/os-release ]; then
    . /etc/os-release
    UBUNTU_VERSION="$VERSION_ID"
else
    echo "[!] Cannot detect OS version."
    exit 1
fi

echo "[*] Detected Ubuntu version: $UBUNTU_VERSION"

if [[ "$UBUNTU_VERSION" != "22.04" && "$UBUNTU_VERSION" != "24.04" ]]; then
    echo "[!] Unsupported Ubuntu version. Only 22.04 and 24.04 are supported."
    exit 1
fi

# ---- Common Replacements ----
echo "[*] Replacing reconnect.sh..."
sudo cp -f "$UPDATED_DIR/reconnect.sh" \
    "$BLUEKIT_BASE/bluekit/bluekit/reconnect.sh"

echo "[*] Replacing verifyconn.py..."
sudo cp -f "$UPDATED_DIR/verifyconn.py" \
    "$BLUEKIT_BASE/.venv/lib/bluekit/verifyconn.py"

# ---- Ubuntu 22.04 Specific ----
if [[ "$UBUNTU_VERSION" == "22.04" ]]; then
    echo "[*] Applying Ubuntu 22.04 specific updates..."

    # Replace content but keep filename
    sudo cp -f "$UPDATED_DIR/bluekit_nino_check_2204.py" \
        "$BLUEKIT_BASE/modules/tools/custom_exploits/bluekit_nino_check.py"

    # Add btmon_feature_extractor
    sudo cp -f "$UPDATED_DIR/btmon_feature_extractor_2204.py" \
        "$BLUEKIT_BASE/btmon_feature_extractor.py"

# ---- Ubuntu 24.04 Specific ----
elif [[ "$UBUNTU_VERSION" == "24.04" ]]; then
    echo "[*] Applying Ubuntu 24.04 specific updates..."

    # Replace content but keep filename
    sudo cp -f "$UPDATED_DIR/bluekit_nino_check_2404.py" \
        "$BLUEKIT_BASE/modules/tools/custom_exploits/bluekit_nino_check.py"

    # Add btmon_feature_extractor
    sudo cp -f "$UPDATED_DIR/btmon_feature_extractor_2404.py" \
        "$BLUEKIT_BASE/btmon_feature_extractor.py"
fi

echo "[✓] Update completed successfully."