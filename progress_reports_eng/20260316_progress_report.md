# 20260316 Progress Report

## WhisperPair - CVE-2025-36911

This vulnerability targets devices which implement Google Fast Pair. Checking whether a given device uses Google Fast Pair can be known by running `bluetootlkit pair {target}` and seeing if it outputs UUID of `0xFE2C` (full 128-bit UUID for the Fast Pair characteristics follows `0000xxxx-0000-1000-8000-00805F9B34FB`).

The specification for Google Fast Pair necessitates ignoring pairing requests unless explicitly set to pairing mode. This check is not implemented by some manufacturers. So an attacker can forcibly pair with the victim accessory, possibly hijacking audio and tracking the device.

I implemented a check for WhisperPair on BlueToolkit by taking an [open-source test code for this vulnerability](https://github.com/Cedric-Martz/CVE-2025-36911_scan) to `/usr/share/BlueToolkit/modules/tools/custom_exploits/bluekit_whisper_check.py`. This is then referred to by a newly added YAML file for this check located in `/usr/share/BlueToolkit/exploits`:

```yaml
author: yso
bt_type: BREDR
bt_version_max: 5.4
bt_version_min: 4.0
command: 'python3 bluekit_whisperpair_check.py '
directory:
  change: true
  directory: modules/tools/custom_exploits
hardware: default
log_pull:
  from_directory: false
  in_command: false
mass_testing: true
max_timeout: 30
name: whisperpair_cve_2025_36911
parameters:
- help: Target MAC address
  is_target_param: true
  name: --target
  name_required: true
  parameter_connector: ' '
  required: true
  type: str
type: PoC
```

I can change the `bt_type` attribute to `BLE` for testing this on a BLE device. BlueToolkit successfully ran the PoC code, revealing that all the previously tested devices (Galaxy 10+ 5G, Galaxy 10 5G, Galaxy S7, iPhone 13 Pro, soundcore Motion X600).

## List of BT devices to purchase

| # | Device | Type | BT Version | BR/EDR | BLE | Google Fast Pair | Purchase (Korea) |
|---|--------|------|------------|--------|-----|------------------|-------------------|
| 1 | Google Pixel Buds Pro 2 | TWS Earbuds | 5.4 | O | O | O | [다나와](https://prod.danawa.com/info/?pcode=17861999) |
| 2 | Sony WH-1000XM5 | Over-ear Headphones | 5.2 | O | O | O | [쿠팡](https://www.coupang.com/np/search?q=%EC%86%8C%EB%8B%88+WH-1000XM5) |
| 3 | Jabra Elite 8 Active | TWS Earbuds | 5.3 | X | O | O | [쿠팡](https://www.coupang.com/np/search?q=Jabra+Elite+8+Active) |
| 4 | Soundcore Liberty 4 NC | TWS Earbuds | 5.3 | X | O | O | [쿠팡](https://www.coupang.com/np/search?q=Soundcore+Liberty+4+NC) |
| 5 | Nothing Ear (2) | TWS Earbuds | 5.3 | X | O | O | [쿠팡](https://www.coupang.com/np/search?q=Nothing+Ear+2) |
| 6 | OnePlus Buds 3 | TWS Earbuds | 5.3 | X | O | O | [쿠팡](https://www.coupang.com/np/search?q=OnePlus+Buds+3) |
| 7 | Marshall Minor IV | TWS Earbuds | 5.3 | X | O | O | [쿠팡](https://www.coupang.com/np/search?q=Marshall+Minor+IV) |
| 8 | JBL Flip 6 | Portable Speaker | 5.1 | O | O | O | [쿠팡](https://www.coupang.com/np/search?q=JBL+Flip+6) |
| 9 | Samsung Galaxy Buds3 Pro | TWS Earbuds | 5.4 | O | O | X (SmartThings) | [쿠팡](https://www.coupang.com/np/search?q=Galaxy+Buds3+Pro) |
| 10 | Samsung Galaxy Watch6 | Smartwatch | 5.3 | O | O | X | [쿠팡](https://www.coupang.com/np/search?q=Galaxy+Watch6) |
| 11 | Xiaomi Redmi Buds 5 Pro | TWS Earbuds | 5.3 | X | O | O | [쿠팡](https://www.coupang.com/np/search?q=Redmi+Buds+5+Pro) |
| 12 | Sony WF-1000XM5 | TWS Earbuds | 5.3 | O | O | O | [쿠팡](https://www.coupang.com/np/search?q=Sony+WF-1000XM5) |
| 13 | Logitech Zone True Wireless | TWS Earbuds (Enterprise) | 5.0 | X | O | X | [쿠팡](https://www.coupang.com/np/search?q=Logitech+Zone+True+Wireless) |
| 14 | Bose QC Ultra Headphones | Over-ear Headphones | 5.3 | O | O | O | [쿠팡](https://www.coupang.com/np/search?q=Bose+QC+Ultra+Headphones) |
| 15 | Samsung Galaxy A15 | Smartphone | 5.3 | O | O | X | [쿠팡](https://www.coupang.com/np/search?q=Galaxy+A15) |
| 16 | Raspberry Pi 5 | SBC (Dev Board) | 5.0 | O | O | X | [쿠팡](https://www.coupang.com/np/search?q=Raspberry+Pi+5) |
| 17 | Arduino Nano ESP32 | Dev Board | 4.2 | O | O | X | [쿠팡](https://www.coupang.com/np/search?q=Arduino+Nano+ESP32) |
| 18 | Xiaomi Mi Band 8 | Fitness Tracker | 5.1 | X | O | X | [쿠팡](https://www.coupang.com/np/search?q=Xiaomi+Mi+Band+8) |
| 19 | Sony PS5 DualSense | Game Controller | 5.1 | O | O | X | [쿠팡](https://www.coupang.com/np/search?q=DualSense+%EC%BB%A8%ED%8A%B8%EB%A1%A4%EB%9F%AC) |
| 20 | Tile Mate (2024) | BLE Tracker | 5.0 | X | O | X | [쿠팡](https://www.coupang.com/np/search?q=Tile+Mate) |
