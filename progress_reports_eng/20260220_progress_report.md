# 20260220 Progress Report

## Braktooth Setup Error Related to `net/ipx.h`

After downgrading to Ubuntu 22.04 and changing the kernel version to 5.15, the error related to `net/ipx.h` during ESP32 setup still persisted. Completely resolving this issue would require downgrading the kernel to an even lower version, but doing so would require verifying whether BlueToolkit would still function properly under that kernel.

The `net/ipx.h` file is required to run the following Braktooth command:

```bash
sudo bin/wifi_ap_fuzzer # Start fuzzer without graphical interface
```

Noting that BlueToolkit does not use the above command, I excluded the setup of that specific tool and re-ran the installation. As a result, the installation completed successfully without errors.

---

## Verifying the Need for ESP32-WROVER-KIT

Braktooth uses the **ESP32-WROVER-KIT** board. When connected, both `/dev/ttyUSB0` and `/dev/ttyUSB1` are detected simultaneously on the Ubuntu machine. According to the Braktooth README, the required port is `/dev/ttyUSB1`.

However, the ESP device currently available in our lab (**ESP32-WROOM-32E**) is recognized only as `/dev/ttyUSB0` when connected to Ubuntu, which prevents Braktooth from running properly.

---

## Conclusion

Therefore, the current issues that need to be resolved are as follows:

* **Obtain an ESP32-WROVER-KIT.**
  The ESP32-WROOM-32E currently available in the lab does not support the required serial communication configuration for Braktooth. I found a GitHub issue discussing ESP32 compatibility, and it confirms that this cannot be resolved using only the existing ESP device.
  (Reference: [https://github.com/Matheus-Garbelini/braktooth_esp32_bluetooth_classic_attacks/issues/2#issuecomment-1039289299](https://github.com/Matheus-Garbelini/braktooth_esp32_bluetooth_classic_attacks/issues/2#issuecomment-1039289299))

  Therefore, acquiring an ESP32-WROVER-KIT appears to be the most reasonable solution. Although it has been discontinued, purchasing a used unit seems to be the best option. As an alternative, another GitHub issue suggests trying the **ESP32-ETHERNET-KIT-VE**:

  * [https://github.com/Matheus-Garbelini/braktooth_esp32_bluetooth_classic_attacks/issues/55](https://github.com/Matheus-Garbelini/braktooth_esp32_bluetooth_classic_attacks/issues/55)
  * [https://www.digikey.kr/ko/products/detail/espressif-systems/ESP32-ETHERNET-KIT-VE/13414972](https://www.digikey.kr/ko/products/detail/espressif-systems/ESP32-ETHERNET-KIT-VE/13414972)

* (Optional) Downgrade to a kernel version that includes `net/ipx.h` and reinstall Braktooth within BlueToolkit.
  This is not a high priority, since BlueToolkit does not use the `sudo bin/wifi_ap_fuzzer` functionality.
