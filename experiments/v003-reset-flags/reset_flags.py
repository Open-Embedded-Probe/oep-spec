"""Which resets set RCC_RSTSCKR.PINRSTF on a CH32V003 (UIAPduino), with the v1 draft probe and RAM payloads.

The UIAPduino bootloader stays only when PINRSTF is set (wch-protocols E161); software cannot set it (read-only,
power-on value 0 per the RM). This checks the other resets without the probe's NRST line:

  iwdg     the independent watchdog runs out
  wwdg     the window watchdog resets at once
  pd7-low  the target drives its own PD7 (the NRST pad) low as a GPIO output
  boot     pd7-low, then the SWIO-only bootloader entry payload (E129) - no probe NRST at all

  usage: reset_flags.py PORT PAYLOAD_DIR [iwdg] [wwdg] [pd7-low] [boot]
"""
import struct
import subprocess
import sys
import time
from pathlib import Path

from oep_client.v1 import host, link, target, uiapduino

RSTSCKR, RMVF = 0x40021024, 1 << 24
NAMES = {31: "LPWRRSTF", 30: "WWDGRSTF", 29: "IWDGRSTF", 28: "SFTRSTF", 27: "PORRSTF", 26: "PINRSTF"}

port, payload_dir = sys.argv[1], Path(sys.argv[2])
tests = sys.argv[3:] or ["iwdg", "pd7-low"]
h = host.Host(link.SerialLink(port).send)
h.open(lease_ms=20000)
wire = target.Wire(h, "oep.wire.swio")


def words(name):
    data = (payload_dir / f"{name}.bin").read_bytes()
    data += b"\0" * (-len(data) % 4)
    return list(struct.unpack(f"<{len(data) // 4}I", data))


def decode(v):
    return [n for b, n in NAMES.items() if v >> b & 1] or ["none"]


def with_target(fn):
    conn, _ = wire.attach(halt=True)
    dm = target.RiscvDm(h, conn)
    try:
        return fn(dm)
    finally:
        dm.resume()
        wire.detach(conn)


def flags():
    return with_target(lambda dm: dm.read32(RSTSCKR))


def clear():
    with_target(lambda dm: dm.write32(RSTSCKR, RMVF))


def hid_present():
    return "1209:b803" in subprocess.run(["usbipd.exe", "list"], capture_output=True, text=True).stdout


print("now:", decode(flags()))
clear()
print("after RMVF:", decode(flags()))
for test in tests:
    clear()
    if test == "iwdg":
        uiapduino.run_payload(h, wire, words("iwdg_reset"))
        time.sleep(0.5)
        print("after an IWDG reset:", decode(flags()))
    elif test == "wwdg":
        uiapduino.run_payload(h, wire, words("wwdg_reset"))
        time.sleep(0.5)
        print("after a WWDG reset:", decode(flags()))
    elif test == "pd7-low":
        uiapduino.run_payload(h, wire, words("pd7_low"))
        time.sleep(0.5)
        print("after the target drove PD7 low:", decode(flags()))
    elif test == "boot":
        uiapduino.run_payload(h, wire, words("pd7_low"))
        time.sleep(0.3)
        print("  flags before the entry payload:", decode(flags()))
        uiapduino.run_payload(h, wire, uiapduino.PREPARE_BOOT)
        time.sleep(2.0)
        print("SWIO-only entry after a self pin reset: HID 1209:b803 present =", hid_present())
        uiapduino.normalize_user(h, wire)
        time.sleep(2.0)
        print("  after normalize_user: HID present =", hid_present())
h.end()
