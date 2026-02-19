#!/bin/bash

mac=$1 # DEH-4400BT

#if [ "$1" = "off" ]; then
#    bluetoothctl -- disconnect
#    exit $?
#fi

# turn on bluetooth in case it's off
rfkill unblock bluetooth

# bluetoothctl -- power on
# bluetoothctl -- discoverable on
# bluetoothctl -- pairable on
# bluetoothctl -- agent on   # if you delete this part it will pair as normal, one would need to accept pairing only on the device (test)
# bluetoothctl -- default-agent
# bluetoothctl -- remove $mac
# sudo hcitool info $mac
# bluetoothctl -- trust $mac
# bluetoothctl -- connect $mac
# sleep 2
# bluetoothctl -- remove $mac
# bluetoothctl -- disconnect

bluetoothctl <<EOF
power on
discoverable on
pairable on
agent on
default-agent
trust $mac
connect $mac
EOF

sleep 2

logfile="/usr/share/BlueToolkit/data/tests/$mac/recon/bluing_lmp.log"

if [ ! -f "$logfile" ]; then
    echo "[+] LMP log not found. Running feature extractor..."
    sudo python3 /usr/share/BlueToolkit/btmon_feature_extractor.py -t "$mac" --dump-btmon
else
    echo "[+] LMP log already exists. Skipping feature extraction."
fi


sleep 2

bluetoothctl <<EOF
disconnect $mac
remove $mac
EOF


#exit 0

# Use it as default output for PulseAudio

#sink=$(pactl list short sinks | grep bluez | awk '{print $2}')

#if [ -n "$sink" ]; then
#    pacmd set-default-sink "$sink" && echo "OK default sink : $sink"
#else
#    echo could not find bluetooth sink
#    exit 1
#fi