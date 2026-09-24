import subprocess, sys, time
from oep_client.v1 import host, link, target, uiapduino
hid = lambda: "1209:b803" in subprocess.run(["usbipd.exe", "list"], capture_output=True, text=True).stdout
h = host.Host(link.SerialLink(sys.argv[1]).send)
h.open(lease_ms=20000)
wire = target.Wire(h, "oep.wire.swio")
gpio = target.find(h, "oep.fixture.gpio")
def clear():
    conn, _ = wire.attach(halt=True); dm = target.RiscvDm(h, conn); dm.write32(0x40021024, 1 << 24); dm.resume(); wire.detach(conn)
# 1: flags cleared, no NRST given -> must refuse
clear()
try:
    uiapduino.enter_bootloader(h, wire)
    print("1 no flag, no NRST: entered (unexpected)")
except uiapduino.NeedsPinReset as e:
    print("1 no flag, no NRST: refused:", str(e)[:60])
# 2: flags cleared, NRST given -> pulse path
print("2 no flag, NRST given:", uiapduino.enter_bootloader(h, wire, gpio, 23), "HID", (time.sleep(2.0), hid())[1])
uiapduino.normalize_user(h, wire); time.sleep(2.0)
print("  back to user mode: HID", hid(), " PINRSTF still set:", uiapduino.pin_reset_flag(h, wire))
# 3: the pin reset's flag is still there (normalize_user is a software reset, no RMVF) -> SWIO only, no NRST given
print("3 flag left over, no NRST given:", uiapduino.enter_bootloader(h, wire), "HID", (time.sleep(2.0), hid())[1])
uiapduino.normalize_user(h, wire); time.sleep(2.0)
print("  back to user mode: HID", hid())
h.end()
