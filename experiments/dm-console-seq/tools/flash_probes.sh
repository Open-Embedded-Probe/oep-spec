#!/bin/bash
# Build and flash the three OEP probes. $1 = fault rate per mille (0 = none).
SP=${DMSEQ_WORK:-/tmp/dmseq-work}; mkdir -p "$SP"
HERE=$(cd "$(dirname "$0")" && pwd)
F=${1:-0}; X="compiler.cpp.extra_flags=-DOEP_CONSOLE_FAULT_PERMILLE=$F"
cd /home/mt/dev_oep/oep-probe-arduino/examples
(cd Esp32V003Probe && arduino-cli compile --profile esp32 --build-property "$X" --output-dir $SP/v003probe . >/dev/null 2>&1 && arduino-cli upload --profile esp32 -p /run/board-identify/by-id/esp32-d0wd-v3-0070070d9394 --input-dir $SP/v003probe . 2>&1 | grep -qE "Hard resetting" && echo "v003 ok" || echo "v003 FAILED") &
(cd Esp32P4X035Probe && arduino-cli compile --build-property "$X" --output-dir $SP/x035probe . >/dev/null 2>&1 && arduino-cli upload -p /run/board-identify/by-id/esp32-series-30eda0e31108 --input-dir $SP/x035probe . 2>&1 | grep -qE "Hard resetting" && echo "x035 ok" || echo "x035 FAILED") &
(cd Rp2350L103Probe && arduino-cli compile --profile rp2350 --build-property "$X" --output-dir $SP/l103probe . >/dev/null 2>&1 || echo "l103 build FAILED") &
wait
$HERE/picoflash.sh 13-1 /dev/serial/by-id/usb-SparkFun_ProMicro_RP2350_9489DD2AE0953650-if00 $SP/l103probe/Rp2350L103Probe.ino.uf2 2e8a:000f >/dev/null 2>&1
for i in 1 2 3 4 5; do ls /dev/serial/by-id/ | grep -q ProMicro && break; usbipd.exe attach --wsl --busid 13-1 >/dev/null 2>&1; sleep 3; done
ls /dev/serial/by-id/ | grep -q ProMicro && echo "l103 ok" || echo "l103 FAILED"
