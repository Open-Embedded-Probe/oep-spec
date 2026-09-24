# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""Leave the RVSWD bus idle for d, then look: is a hart halted before the pause still halted at the same dpc (the DM
kept its state), or running again (the DM reset)? The probe's own idle rule (SWCLK low or both high) is a build option."""
import sys, time
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
from oep_client.v1 import host, link, target
port, label = sys.argv[1], sys.argv[2]
h = host.Host(link.SerialLink(port).send)
h.open(lease_ms=60000, force=True)
wire = target.Wire(h, "oep.wire.rvswd")
try:
    conn, st = wire.attach(halt=True)
except Exception as e:
    print(f"[{label}] attach failed: {e}"); sys.exit()
dm = target.RiscvDm(h, conn)
def dpc():
    done, r = dm.dmi(dm.step_write(0x16, 0x700) + dm.step_write(0x17, 0x002207b1) + dm.step_read(0x04) + dm.step_read(0x11))
    return r[0], r[1]
rows = []
for d in (0.001, 0.005, 0.02, 0.1, 0.5, 2.0):
    kept = 0; notes = set()
    for _ in range(5):
        try:
            dm.halt()
            pc0, _ = dpc()
            time.sleep(d)
            done, r = dm.dmi(dm.step_read(0x11))
            status = r[0]
            pc1, _ = dpc()
            if status & (1 << 9) and pc1 == pc0: kept += 1
            else: notes.add(f"st {status:#x} pc {pc0:#x}->{pc1:#x}")
        except Exception as e:
            notes.add(f"err {e}")
    rows.append(f"  idle {d * 1000:7.1f} ms: halted+same dpc {kept}/5 {sorted(notes)[:2]}")
print(f"[{label}] attach dmstatus {st:#x}")
print("\n".join(rows))
dm.reset(confirm=True)
wire.detach(conn)
h.end()
