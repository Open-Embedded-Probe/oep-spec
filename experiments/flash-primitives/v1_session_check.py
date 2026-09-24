"""Session rules on a real v1 draft probe: two hosts (two session ids) over one port."""
import random, sys, time
from oep_client.v1 import host, link, target

send = link.SerialLink(sys.argv[1]).send
a, b = host.Host(send, rng=random.Random(1)), host.Host(send, rng=random.Random(2))
out = []
a.open(lease_ms=800)
wire = target.Wire(a)
try:
    b.session = 0x0BAD0BAD
    target.Wire(b).scan()
except host.Locked as e:
    out.append(f"B while A holds: locked, {e.remaining_ms} ms left")
out.append(f"B lock-free list while locked: fn {target.find(b, 'oep.target.riscv-dm')}")
try:
    b.request(wire.fn, wire.SCAN, locked=False)
except host.Rejected as e:
    out.append(f"B scan without a session id: {e}")
time.sleep(1.0)                                   # A's lease lapses
out.append(f"A after its lease lapsed, same id: scan found {len(wire.scan())} (resumed)")
a.end()
try:
    target.Wire(b).scan()
except host.NoSession as e:
    out.append(f"B with an unknown id on a free lock: {e}")
b.open()
b.end()
try:
    wire.scan()
except host.NoSession as e:
    out.append(f"A's saved id after B opened: {e} (someone came in between)")
print("\n".join(out))
