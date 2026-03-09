# 20260305 progress report

The Braktooth-based tests were successful after setting up ESP32-ETHERNET-KIT by running the following commands:
```bash
source /usr/share/BlueToolkit/.venv/bin/activate

cd /usr/share/BlueToolkit/modules/tools/braktooth/release

sudo python3 firmware.py flash /dev/ttyUSB1
```

However, for all the tested devices for today, `braktooth_knob` failed to be complete with the following error:
```bash
$ sudo bluekit -t {target} --report
...
braktooth_knob  | Toolkit error⚠️ | Error during extracting information from the regex |
...
```

We will have to look into this error in more detail.
