# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""RP2040-Zero -> Pro Micro RP2350 over OEP v1 SWD: attach, power up, DPv3 identification, AP IDRs."""
import sys
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
from oep_client.v1 import host, link, target, arm
h = host.Host(link.SerialLink(sys.argv[1]).send); h.open(lease_ms=30000, force=True)
wire = arm.SwdWire(h)
print("scan:", wire.scan())
conn, dpidr, dormant = wire.attach()
print(f"attach: conn {conn} DPIDR {dpidr:#010x} dormant {dormant}")
adi = arm.ArmAdi(h, conn, adiv6=True)
print(f"power up: CTRL/STAT {adi.power_up():#010x}")
for bank, name in ((1, "DPIDR1"), (2, "BASEPTR0"), (3, "BASEPTR1")):
    adi.select(bank)
    print(f"  {name}: {adi.dp_read(0x0):#010x}")
adi.select(0)
for base in (0x0000, 0x2000, 0x4000, 0x6000, 0x8000, 0xA000, 0x80000):
    try:
        print(f"  AP @ {base:#07x}: IDR {adi.ap_read(base, 0xDFC):#010x} BASE {adi.ap_read(base, 0xDF8):#010x} CFG {adi.ap_read(base, 0xDF4):#010x}")
    except Exception as e:
        print(f"  AP @ {base:#07x}: {e}")
        adi.dp_write(arm.DP_ABORT, 0x1E)
wire.detach(conn); h.end()
