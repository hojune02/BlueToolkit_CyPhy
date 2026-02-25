# 20260219 Progress Report

## ESP32 Setup

When the ESP32 was first connected, Ubuntu did not recognize it due to a faulty USB-C cable. Therefore, I recommend preparing a properly functioning USB-C cable before attempting to connect the ESP32. The connected device is **ESP32-WROOM-32E**.

I followed the **Using hardware-based exploits** section of the BlueToolkit wiki to configure the device. The official wiki guide is as follows:

---

Braktooth

You need to buy the following hardware to be able to run the exploits: The installation is partially automated in the toolkit. Consult [https://github.com/Matheus-Garbelini/braktooth_esp32_bluetooth_classic_attacks](https://github.com/Matheus-Garbelini/braktooth_esp32_bluetooth_classic_attacks) repository for other information.

Once you have needed hardware:

* you need to connect it to your machine
* Then run the following command

```bash
ls -la /dev/tty*
```

* If you see /dev/ttyUSB0 and /dev/ttyUSB1 then the development board is connected and you can start writing to it
* To continue Braktooth installation run the following commands

```bash
chmod +x /usr/share/Btoolkit/installation/braktooth_additional_install.sh
/usr/share/Btoolkit/installation/braktooth_additional_install.sh
```

---

When I ran the `ls -la /dev/tty*` command, the ESP32 device appeared as `ttyUSB0`. However, when I checked `BlueToolkit/installation/braktooth_additional_install.sh`, I found the following command:

```bash
sudo python3 firmware.py flash /dev/ttyUSB1
```

I modified `ttyUSB1` to `ttyUSB0` in the command and then executed `braktooth_additional_install.sh`. However, errors continued to occur, and I eventually identified the root cause in the Ubuntu version I was using.

### Issue When Running Braktooth’s requirements2.sh

During Braktooth installation, the `rtl8812au` driver is required, but I confirmed that it no longer exists in Ubuntu 24.04. Therefore, I attempted to install and run Ubuntu 22.04 using `lxd`, and then reinstall BlueToolkit on that virtual image. However, both VirtualBox and `lxd` restrict access to the host machine’s Bluetooth and USB device information, which caused the attempt to fail.

Ultimately, I decided to reinstall Ubuntu 22.04 natively and reconfigure both BlueToolkit and Braktooth from scratch.
