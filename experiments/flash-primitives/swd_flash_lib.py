# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""Program an RP2350 over OEP v1 SWD with the library modules (arm.CortexM + rp2350.Flash), verify, reboot.
    uv run swd_flash_lib.py <probe port> <image.bin> [--tidy-test-area]"""
import pathlib, sys, time
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
from oep_client.v1 import host, link, arm, rp2350
image = pathlib.Path(sys.argv[2]).read_bytes()
h = host.Host(link.SerialLink(sys.argv[1]).send); h.open(lease_ms=60000, force=True)
wire = arm.SwdWire(h); conn, dpidr, _ = wire.attach()
adi = arm.ArmAdi(h, conn, adiv6=True); adi.power_up()
mem = arm.MemAp(adi, 0x2000, csw_clear=1 << 30)
core = arm.CortexM(mem, rp2350.BKPT_AT, rp2350.STACK_TOP); core.halt()
t0 = time.monotonic()
ok = rp2350.program_and_verify(core, image, 0, log=lambda s: print("  " + s))
print(f"program + verify {len(image)} B: {'match' if ok else 'MISMATCH'} in {time.monotonic() - t0:.2f} s")
if "--tidy-test-area" in sys.argv:
    rp2350.Flash(core).program(0xF00000, b"\xff" * 8192)
    print("  test area at 0xF00000 back to erased")
rp2350.Rom(core).reboot()
wire.detach(conn); h.end()
