# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""The host's clocks against a crystal: the RP2350's TIMER0 (1 MHz from its 12 MHz XOSC), read over OEP v1 SWD."""
import sys, time
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
from oep_client.v1 import host, link, arm
h = host.Host(link.SerialLink(sys.argv[1]).send); h.open(lease_ms=60000, force=True)
wire = arm.SwdWire(h); conn, _, _ = wire.attach()
adi = arm.ArmAdi(h, conn, adiv6=True); adi.power_up()
mem = arm.MemAp(adi, 0x2000, csw_clear=1 << 30)
def sample():
    a = time.perf_counter(); t = mem.read32(0x400b0028); b = time.perf_counter()
    return t, (a + b) / 2, time.time(), b - a
window = float(sys.argv[2]) if len(sys.argv) > 2 else 20
for _ in range(2):
    t0, p0, r0, l0 = sample(); time.sleep(window); t1, p1, r1, l1 = sample()
    target_s = ((t1 - t0) & 0xFFFFFFFF) / 1e6
    print(f"crystal {target_s:.4f} s | perf_counter {p1 - p0:.4f} s ({(p1 - p0) / target_s:.4f}) | time.time {r1 - r0:.4f} s ({(r1 - r0) / target_s:.4f}) | read latency {max(l0, l1) * 1000:.1f} ms")
wire.detach(conn); h.end()
