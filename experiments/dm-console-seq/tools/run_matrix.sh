#!/bin/bash
# Build the DmSeqTest images and run every target x variant. $1 = tag for the result files.
# Variants: 1 = SerialDMDATA (framing 1), 2 = seq (framing 2), 3 = seq+CRC bitwise, 4 = seq+CRC table (both framing 3).
SP=${DMSEQ_WORK:-/tmp/dmseq-work}; mkdir -p "$SP"
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$SP/sb2/user/hardware/ch32-riscv-ug" && ln -sfn /home/mt/dev_wch/ArduinoCore-CH32 "$SP/sb2/user/hardware/ch32-riscv-ug/ch32v"
TAG=$1; FRAMINGS=${FRAMINGS:-"1 2 3"}; ROUNDS=${ROUNDS:-3}; ECHO=${ECHO:-20}
cd /home/mt/dev_wch/ArduinoCore-CH32; TC=$PWD/$(ls -d .tools/xpack-riscv-none-elf-gcc/*/bin | tail -1)
declare -A FQ=([x035]="ch32-riscv-ug:ch32v:CH32X035:pnum=ANY" [v003]="ch32-riscv-ug:ch32v:UIAPDUINO_V003_V14" [l103]="ch32-riscv-ug:ch32v:CH32L103:pnum=CH32L103C8T6")
for t in x035 v003 l103; do for v in $FRAMINGS; do case $v in 1) f="-DDMSEQ_BASELINE";; 2) f="-DDMSEQ_CRC=0";; 3) f="-DDMSEQ_CRC=1";; 4) f="-DDMSEQ_CRC=1 -DDMSEQ_CRC_TABLE=1";; esac
  ARDUINO_DIRECTORIES_USER=$SP/sb2/user arduino-cli compile --fqbn ${FQ[$t]} --build-property "compiler.path=$TC/" --build-property "compiler.cpp.extra_flags=$f" --build-path $SP/img-$t-$v $HERE/../DmSeqTest 2>&1 | grep -E "error"; done; done
rm -f $SP/$TAG-*.done
for t in x035 v003 l103; do ( for v in $FRAMINGS; do echo "### variant $v"; timeout 900 uv run $HERE/../dmseq_host.py --target $t --bin $SP/img-$t-$v/DmSeqTest.ino.bin --framing $([ $v = 4 ] && echo 3 || echo $v) --rounds $ROUNDS --echo $ECHO 2>&1 | grep -v "^Installed"; done > $SP/$TAG-$t.log; touch $SP/$TAG-$t.done ) & done
wait
for t in x035 v003 l103; do echo "======== $t"; cat $SP/$TAG-$t.log; done
