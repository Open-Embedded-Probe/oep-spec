# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""Step 1: the call primitive, on a side-effect-free ROM function (rom_table_lookup). Ends with a chip reset."""
import sys
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
sys.path.insert(0, "/tmp/claude-1000/-home-mt-dev-wch-ArduinoCore-CH32/61e5ec37-4ccb-4073-946b-5f642a136a2b/scratchpad")
from oep_client.v1 import host, link, arm
import rp2350_rom as rom
h = host.Host(link.SerialLink(sys.argv[1]).send); h.open(lease_ms=30000, force=True)
wire = arm.SwdWire(h); conn, dpidr, _ = wire.attach()
adi = arm.ArmAdi(h, conn, adiv6=True); adi.power_up()
mem = arm.MemAp(adi, 0x2000, csw_clear=1 << 30)
core = rom.Core(mem)
st = core.halt()
print(f"halted: DHCSR {st:#010x} pc {core.reg(rom.R_PC):#010x} sp {core.reg(rom.R_SP):#010x} xpsr {core.reg(rom.R_XPSR):#010x}")
print(f"ROM magic @0x10: {mem.read32(0x10):#010x}, table_lookup ptr {mem.read32(0x14) >> 16:#06x}")
names = {"IF": "connect_internal_flash", "EX": "flash_exit_xip", "RE": "flash_range_erase", "RP": "flash_range_program",
         "FC": "flash_flush_cache", "CX": "flash_enter_cmd_xip", "GS": "get_sys_info", "RB": "reboot"}
found = {}
for c, name in names.items():
    found[c] = core.rom_lookup(rom.code(*c))
    print(f"  {c} {name:24s} -> {found[c]:#010x}")
print("all in ROM:", all(0 < v < 0x8000 for v in found.values()))
core.sys_reset()
wire.detach(conn); h.end()
