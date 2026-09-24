"""The v1 draft console stream on a real probe, against DmSeqTest on the target (dm-console-seq experiment).

Attach without halting (the Monitor-only case), open a dmseq stream, read, echo a line, reset through
riscv-dm, read from the last reset mark, then end the session and keep reading without one.

  usage: v1_console_check.py PORT [WIRE_NAME]   (default oep.wire.rvswd; oep.wire.swio for the V003 probe)
"""
import sys
import time

from oep_client.v1 import host, link, target

lnk = link.SerialLink(sys.argv[1])
h = host.Host(lnk.send)
h.open(lease_ms=5000)
wire = target.Wire(h, sys.argv[2] if len(sys.argv) > 2 else "oep.wire.rvswd")
conn, _ = wire.attach(halt=False)
con = target.Console(h)
con.open(conn, target.Console.DMSEQ)
out = []


def text_since(position):
    data, pos = b"", position
    while True:
        start, more, gap, chunk = con.read_from(pos)
        data += chunk
        pos = start + len(chunk)
        if not more:
            return data, pos, gap


time.sleep(1.2)
data, pos, _ = text_since(0)
out.append(f"after 1.2 s: {data.count(b'dmseq READY')} READY lines, position {pos}")

con.write(b"E hello v1\n")
time.sleep(0.6)
data, pos, _ = text_since(pos)
out.append(f"echo: {'R hello v1' in data.decode(errors='replace')}")

dm = target.RiscvDm(h, conn)
res = h.request(dm.fn, dm.RESET, bytes([conn, 1]))
out.append(f"reset: {res.describe()} flags=0x{res.payload[0]:02x} attempts={res.payload[1]} pc=0x{int.from_bytes(res.payload[2:6], 'little'):x}")
time.sleep(1.2)
start, more, gap, after_reset = con.read(target.Console.FROM_MARK, 1)        # from the last reset mark
out.append(f"from the reset mark at {start}: {after_reset[:40]!r}")
out.append("marks: " + ", ".join(f"{target.MARK_NAMES.get(mk.kind, mk.kind)}@{mk.position}" for mk in con.marks()))

h.end()                                            # the stream keeps collecting without a session
reader = host.Host(lnk.send)                       # another host, no session at all
time.sleep(1.0)
lock_free = target.Console(reader)
start, more, gap, chunk = lock_free.read(target.Console.FROM_POSITION, pos)
out.append(f"lock-free read after the session ended: {len(chunk)} bytes from {start}, gap={gap}")
print("\n".join(out))
