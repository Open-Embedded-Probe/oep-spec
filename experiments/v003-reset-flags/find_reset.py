# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""Search a probe's channels for the target's reset line (attach under reset through each, dpc == 0 is the hit)."""
import sys, time
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
from oep_client.v1 import host, link, target
port, wire_name, cands = sys.argv[1], sys.argv[2], [int(c) for c in sys.argv[3].split(",")]
h = host.Host(link.SerialLink(port).send)
h.open(lease_ms=30000, force=True)
wire = target.Wire(h, wire_name)
print("labels:", target.probe_labels(h))
for rnd in range(6):
    t0 = time.perf_counter()
    print(f"round {rnd}: hits {wire.find_reset_line(cands)} in {time.perf_counter() - t0:.1f} s", {c: ([f"{x:#x}" if x is not None else "fail" for x in v] if isinstance(v, list) else "rej") for c, v in wire.last_search.items()})
conn, _ = wire.attach(halt=False)
print("target still alive, reset:", target.RiscvDm(h, conn).reset(confirm=True))
wire.detach(conn)
h.end()
