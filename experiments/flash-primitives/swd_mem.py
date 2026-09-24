# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""MEM-AP through OEP v1 SWD on the RP2350 (core 0 AHB-AP @ 0x2000): reads, block vs single, a restored write, halt."""
import sys, time
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
from oep_client.v1 import host, link, target, arm
h = host.Host(link.SerialLink(sys.argv[1]).send); h.open(lease_ms=30000, force=True)
wire = arm.SwdWire(h)
conn, dpidr, _ = wire.attach()
adi = arm.ArmAdi(h, conn, adiv6=True)
adi.power_up()
mem = arm.MemAp(adi, 0x2000, csw_clear=1 << 30)   # secure: the RP2350 SRAM faults non-secure accesses
print("bootrom[0:4]:", [f"{w:#010x}" for w in mem.read_block(0x0, 4)])
print(f"SYSINFO CHIP_ID: {mem.read32(0x40000000):#010x}")
t0 = time.perf_counter()
block = mem.read_block(0x0, 2048)          # 8 KiB of boot ROM, eight 1 KiB boundaries
dt = time.perf_counter() - t0
singles = {a: mem.read32(a) for a in (0x3fc, 0x400, 0x404, 0x7fc, 0x800, 0x1ffc)}
bad = [f"{a:#x}" for a, v in singles.items() if block[a // 4] != v]
print(f"block read 8 KiB in {dt:.2f} s ({8 / dt:.1f} KiB/s); boundary words vs single reads: {'match' if not bad else 'MISMATCH ' + str(bad)}")
again = mem.read_block(0x0, 2048)
print("second block read:", "same" if again == block else "DIFFERENT")
RAM = 0x2007F3F0                           # 16 words across the 1 KiB boundary at 0x2007F400, saved and restored
old = mem.read_block(RAM, 16)
pattern = [0xa5a50000 + i for i in range(16)]
mem.write_block(RAM, pattern)
back = mem.read_block(RAM, 16)
mem.write_block(RAM, old)
print(f"SRAM write/read across a 1 KiB boundary: {'match' if back == pattern else 'MISMATCH'}; restored: {mem.read_block(RAM, 16) == old}")
DHCSR, DCRSR, DCRDR = 0xE000EDF0, 0xE000EDF4, 0xE000EDF8
mem.write32(DHCSR, 0xA05F0003)             # C_DEBUGEN | C_HALT
st = mem.read32(DHCSR)
mem.write32(DCRSR, 15)                     # read DebugReturnAddress (PC)
for _ in range(10):
    if mem.read32(DHCSR) & (1 << 16): break
pc = mem.read32(DCRDR)
mem.write32(DHCSR, 0xA05F0001)             # run
mem.write32(DHCSR, 0xA05F0000)             # and let go of debug
print(f"halt: DHCSR {st:#010x} (S_HALT {bool(st >> 17 & 1)}), PC {pc:#010x}; resumed, DHCSR now {mem.read32(DHCSR):#010x}")
wire.detach(conn); h.end()
