# 20260225 progress report

The vulnerability testing via Braktooth cannot take place until we have the ESP32 device.

### btmon_feature_extractor now uses `hcitool info` for extracting LMP features

LMP features are represented as bitmasks when running `hcitool info`. For reconnaissance vulnerabilities, the program checks if the following features are available.

- LE Supported (Controller): Page 0, 4th byte, 6th bit
- LE Supported (Host): Page 1, 0th byte, 1st bit
- Simultaneous LE and BR/EDR to Same Device Capable (Controller): Page 0, 6th byte, 1st bit
- Simultaneous LE and BR/EDR to Same Device Capable (Host): Page 1, 0th byte, 2nd bit
- Secure Simple Pairing (Controller Support): Page 0, 6th byte, 3rd bit
- Secure Simple Pairing (Host Support): Page 1, 0th byte, 0th bit
- Secure Connections (Controller Support): Page 2, 1st byte, 0th bit
- Secure Connections (Host Support): Page 1, 0th byte, 3rd bit

The locations for these bits were confirmed by Bluetooth Core Specification and `/usr/src/linux-headers-6.8.0-100-generic/net/bluetooth/hci.h`. (Ubuntu 22.04 6.8.0-100-generic)

### Preparing for integrating ESP32-ETHERNET-KIT-VE (Braktooth)

Running `requirements2.sh` failed due to lack of `net/ipx.h` in Linux kernels >= 5.15. Braktooth requires the file for its [Wi-Fi AP Fuzzer](https://github.com/Matheus-Garbelini/braktooth_esp32_bluetooth_classic_attacks?tab=readme-ov-file#31-running-experimental-fuzzers). Since BlueToolkit only uses `bin/bt_exploiter` binary, this is not needed for the testing purposes; the relevant part in the installation script (`cd src/drivers/wifi/rtl8812au && make -j4`) was commented out.

So far, all the necessary setup on the Ubuntu machine's side is complete. Now, we just need to set up the ESP32 KIT once it arrives by running the following commands:
```bash
source /usr/share/BlueToolkit/.venv/bin/activate

cd /usr/share/BlueToolkit/modules/tools/braktooth/release

sudo python3 firmware.py flash /dev/ttyUSB1
```