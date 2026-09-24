import subprocess, sys, time
from oep_client.v1 import host, link, target, uiapduino

def hid_present():
    out = subprocess.run(["usbipd.exe", "list"], capture_output=True, text=True).stdout
    return "1209:b803" in out

h = host.Host(link.SerialLink(sys.argv[1]).send)
h.open(lease_ms=10000)
wire = target.Wire(h, "oep.wire.swio")
gpio = target.find(h, "oep.fixture.gpio")
print("before: HID 1209:b803 present =", hid_present())
uiapduino.enter_bootloader(h, wire, gpio, 23)
time.sleep(2.0)
print("after enter_bootloader: HID present =", hid_present())
uiapduino.normalize_user(h, wire)
time.sleep(2.0)
print("after normalize_user: HID present =", hid_present())
conn, _ = wire.attach(halt=False)
con = target.Console(h)
con.open(conn, target.Console.DMSEQ)
time.sleep(1.2)
start, more, gap, data = con.read(target.Console.FROM_MARK, 3)
print("console after normalize:", data.count(b"dmseq READY"), "READY lines")
h.end()
