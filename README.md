# BlueToolkit_CyPhy

## Table of Contents

[1. Purpose](#purpose)

[2. Debugging & Stabilising BlueToolkit](#debugging--stabilising-bluetoolkit)

[3. Setting Up ESP32 for Braktooth](#setting-up-esp32-for-braktooth)

## Purpose

This project aims at stabilising the performance of [BlueToolkit](https://github.com/sgxgsx/BlueToolkit), an extensible Bluetooth Classic vulnerability testing framework. 

Also, the original research paper only considers examining Bluetooth vulnerabilities in automobile devices. This project strived to conduct the same vulnerability testing on various IT devices, including speakers and smartphones. 

Project members: Hojune Kim (Undergraduate Intern at [KAIST CyPhy Lab](https://www.cyphy.kaist.ac.kr/))

## Debugging & Stabilising BlueToolkit

The progress in debugging and stabilising the testing environment using BlueToolkit is documented under `progress_reports_eng/` (English) and `progress_reports_kor/` (Korean). The naming format is `{date}_Progress_Report.md` for the English version, and `{date}_진행현황.md` for the Korean version. This README briefly goes through key changes in the framework here, and the relevant details can be found in the progress reports.

Please note that the project had started off by using Ubuntu 24.04, which was then downgraded to 22.04 for ensuring compatibility with 

### `reconnect.sh`

`reconnect.sh` is used for checking connectivity to the target device. The original `reconnect.sh` from the BlueToolkit repository has the following features:

- It uses `NoInputNoOutput` as its agent instead of `on`.
- It uses fire-and-forget method for connecting and removing the target device.

For some IT devices, bluetooth connectivity cannot be established when the agent is `NoInputNoOutput`. Moreover, fire-and-forget calls for `bluetoothctl connect` and `bluetoothctl remove` often resulted in a race condition, hindering Bluetooth connection. 

The updated version for `reconnect.sh` in this repository uses `on` as default agent, and run the `bluetoothctl` commands sequentially to prevent any race condition.

### `bluekit_nino_check.py`

Testing for `custom_nino_check` vulnerability failed continuously due to instability of running `hcitool info` (output was not guaranteed to be the same every run) and one-time attempt for `bluetoothctl pair`, both of which could fail silently and cause regex parsing error. 

To address this issue, the updates on `bluekit_nino_check.py` were made so that it tries to run `hcitool info` until it succeeds.

For `bluetoothctl pair`, observations on target devices showed that if they have `custom_nino_check` vulnerability, it will accept the pairing request by `bluekit_nino_check.py`. The program was changed to generate correct response to this case for `bluekit_nino_check_2204.py`. 

`bluekit_nino_check_2404.py` was used before downgrading the Ubuntu version to 22.04, and hence deprecated for the project. It was uploaded onto the repository for archiving purposes.

### `btmon_feature_extractor.py`

`bluing` is used by BlueToolkit for collecting LMP (Link Management Protocol) features. One critical issue faced during the project setup was that `bluing` dependency is no longer open-source and available for use. 

This problem was resolved in two different ways for Ubuntu 22.04 and 24.04:

- In Ubuntu 22.04, `hcitool info` command runs relatively in a stable manner, listing out all the bitmasks for LMP features consistently. `btmon_feature_extractor_2204.py` uses this information to parse and extract LMP features from the hex values directly, creating `bluing_lmp.log` for running `reconnaissance`-related vulnerabilities. (Note that it was named in a misleading way, since it does not use `btmon`. This is because the file was originally created when the project took place on an Ubuntu 24.04 machine, where I actually used `btmon`)
- In Ubuntu 24.04, `sudo btmon` command reliably lists out all the LMP features of the target device. The LMP features fetched by `btmon` was parsed to create `bluing_lmp.log` for the target device.

Note that `btmon_feature_extractor.py` is run only once by `reconnect.sh`, when there is no `bluing_lmp.log` (LMP feature info) for the target device (this is the case when it is the first time connecting to the device using BlueToolkit).

---

## Setting Up ESP32 for Braktooth

Testing for Braktooth vulnerabilities requires an [ESP32-WROVER-KIT-VE (the link points at an online store listed in the official Braktooth github repository)](https://www.digikey.sg/en/products/detail/espressif-systems/ESP32-ETHERNET-KIT-VE/13414972).


### Braktooth Setup

The setup for Braktooth in BlueToolkit is partially automated by `braktooth_additional_install.sh`. Running the script led to several issues:

- `wget https://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2_amd64.deb` resulted in downloading `...ubuntu2_amd64.db`, not `...ubuntu2.20_amd64.db`. The installation script uses `...ubuntu2.20_amd64.db` for `dpkg` and `rm -f` commands, which fails since such file does not exist. These commands were fixed to correctly install and remove `...ubuntu2_amd64.db`.
- Running `requirements2.sh` failed due to lack of `net/ipx.h` in Linux kernels >= 5.15. Braktooth requires the file for its [Wi-Fi AP Fuzzer](https://github.com/Matheus-Garbelini/braktooth_esp32_bluetooth_classic_attacks?tab=readme-ov-file#31-running-experimental-fuzzers). Since BlueToolkit only uses `bin/bt_exploiter` binary, this is not needed for the testing purposes; the relevant part in the installation script (`cd src/drivers/wifi/rtl8812au && make -j4`) was commented out:
```bash
...
else
	# Minimal Ubuntu Packages to run binary WDissector and Wireshark distribution
	sudo apt install g++ libglib2.0-dev  libqt5multimedia5 libsnappy1v5 libsmi2ldbl libc-ares2 libnl-route-3-200 \
	libfreetype6 graphviz libtbb-dev libxss1 libnss3 libspandsp2 libsbc1 libbrotli1 libnghttp2-14 libasound2 psmisc sshpass \
	libpulse0 libasound2 libpcre2-dev -y
	# Wi-Fi requirements
	sudo apt install dnsmasq net-tools iptables linux-headers-$(uname -r) -y
	sudo cp src/drivers/wifi/rtl8812au/85-nm-unmanaged.rules /etc/udev/rules.d/85-nm-unmanaged.rules
	sudo udevadm control --reload-rules && udevadm trigger
	# cd src/drivers/wifi/rtl8812au/
	# make -j4

	# Evaluation packages
	sudo python3 -m pip install numpy pandas python-pcapng==1.0 matplotlib
	sudo apt install expect-dev
fi
...
```
