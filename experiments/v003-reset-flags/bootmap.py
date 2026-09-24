# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""V003: which code sits at 0x0 right after an NRST release - user flash or the BOOT area (UIAPduino bootloader)?"""
import struct, sys
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
from oep_client.v1 import host, link, target
h = host.Host(link.SerialLink(sys.argv[1]).send)
h.open(lease_ms=10000, force=True)
wire = target.Wire(h, "oep.wire.swio")
for how in ("nrst", "ndmreset"):
    if how == "nrst":
        conn, pc0 = wire.attach_under_reset()
        dm = target.RiscvDm(h, conn)
    else:
        conn, _ = wire.attach(halt=True); dm = target.RiscvDm(h, conn); pc0 = dm.reset_halt()
    w = lambda a, n=16: dm.read_block(a, n)
    at0, user, boot = w(0x0), w(0x08000000), w(0x1FFFF000)
    ob = w(0x1FFFF800, 4)
    statr = w(0x4002200C, 1)
    rstsckr = w(0x40021024, 1)
    print(f"[{how}] pc0 {pc0:#x}  @0 {at0.hex()}  @user {user.hex()}  @boot {boot.hex()}")
    print(f"   OB {ob.hex()} (USER byte {ob[2]:#04x})  FLASH_STATR {struct.unpack('<I', statr)[0]:#010x}  RCC_RSTSCKR {struct.unpack('<I', rstsckr)[0]:#010x}")
    print(f"   @0 is {'USER' if at0 == user else 'BOOT' if at0 == boot else 'neither'}")
    dm.reset(confirm=True)
    wire.detach(conn)
h.end()
