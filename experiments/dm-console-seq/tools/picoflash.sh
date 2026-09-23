#!/bin/bash
# Reflash a Pico over USB from WSL: 1200 bps touch -> BOOTSEL -> picotool -> back to the app.
# $1 = busid, $2 = the by-id serial node of the running app, $3 = uf2, $4 = BOOTSEL VID:PID
set -e
PT=~/.arduino15/internal/rp2040_pqt-picotool_5.0.0-9576866_0467333e39e4fa35/picotool
BUSID=$1; NODE=$2; UF2=$3; BOOTPID=$4
if [ -e "$NODE" ]; then
  uv run --quiet --with pyserial python - "$NODE" <<'PY'
import serial, sys, time
try:
    s = serial.Serial(sys.argv[1], 1200); s.dtr = False; time.sleep(0.2); s.close()
except Exception: pass
PY
  sleep 4
fi
usbipd.exe attach --wsl --busid "$BUSID" >/dev/null 2>&1 || true
sleep 3
SEL=$(lsusb | grep "$BOOTPID" | head -1 | sed 's/Bus 0*\([0-9]*\) Device 0*\([0-9]*\).*/--bus \1 --address \2/')
[ -z "$SEL" ] && { echo "no BOOTSEL device $BOOTPID"; exit 1; }
$PT load -x "$UF2" $SEL 2>&1 | tail -1
sleep 5
usbipd.exe attach --wsl --busid "$BUSID" >/dev/null 2>&1 || true
sleep 3
echo "done; nodes:"; ls /dev/serial/by-id/ | grep -i "rp2040\|promicro"
