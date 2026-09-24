"""F5: program CH32X035 through the v1 draft only - session, oep.wire.rvswd, oep.target.riscv-dm.

Same host RAM loader as F4 (x035_loader.S); the probe offers nothing chip-specific. One request at a time
(no pipelining yet). With --reset the target is reset afterwards and must be seen running (a real image).

  usage: f5_v1.py PORT IMAGE LOADER_BIN [--reset]
"""
import json
import struct
import sys
import time
from pathlib import Path

from oep_client.v1 import host, link, target

KEYR, CTLR, MODEKEYR = 0x40022004, 0x40022010, 0x40022024
LOCK, FLOCK = 1 << 7, 1 << 15
BASE, PAGE = 0x08000000, 256
LOADER, BUFFER = 0x20000000, 0x20000400
DONE_OK = 0x200000B0

port, image_path, loader_path = sys.argv[1], sys.argv[2], sys.argv[3]
do_reset = "--reset" in sys.argv
image = Path(image_path).read_bytes()
image += b"\xff" * (-len(image) % PAGE)
loader = Path(loader_path).read_bytes()
loader += b"\0" * (-len(loader) % 4)

t_start = time.perf_counter()
h = host.Host(link.SerialLink(port).send)
info = target.confirm(h)
opened = h.open(lease_ms=5000)
wire = target.Wire(h)
found = wire.scan()
conn, dmstatus = wire.attach(halt=True)
dm = target.RiscvDm(h, conn)
t_ready = time.perf_counter()

if dm.read32(CTLR) & (LOCK | FLOCK):
    for reg in (KEYR, MODEKEYR):
        dm.write32(reg, 0x45670123)
        dm.write32(reg, 0xCDEF89AB)
dm.write_block(LOADER, loader)
if dm.read_block(LOADER, len(loader) // 4) != loader:
    sys.exit("loader did not read back")

t0 = time.perf_counter()
failures = []
for off in range(0, len(image), PAGE):
    dm.write_block(BUFFER, image[off:off + PAGE])
    stopped, dpc, a0, us = dm.run(LOADER, [(0x100A, BASE + off), (0x100B, BUFFER), (0x0300, 0)])
    if not (stopped and dpc == DONE_OK and a0 == 0):
        failures.append({"page": hex(BASE + off), "stopped": stopped, "dpc": hex(dpc), "a0": hex(a0)})
program_s = time.perf_counter() - t0

t0 = time.perf_counter()
back = b""
for off in range(0, len(image), 1000):
    n = min(1000, len(image) - off)
    back += dm.read_block(BASE + off, n // 4)
verify_s = time.perf_counter() - t0

reset = None
if do_reset:
    flags, attempts, pc = dm.reset(confirm=True)
    reset = {"flags": hex(flags), "attempts": attempts, "pc": hex(pc)}
wire.detach(conn)
h.end()
print(json.dumps({"confirm": {k: v for k, v in info.items() if k != "magic"}, "boot_id": hex(opened.boot_id),
                  "scan": [{"pins": f.pins, "dmstatus": hex(f.dmstatus)} for f in found], "attach_dmstatus": hex(dmstatus),
                  "bytes": len(image), "match": back == image, "setup_s": round(t_ready - t_start, 3),
                  "program_s": round(program_s, 3), "verify_s": round(verify_s, 3),
                  "total_s": round(time.perf_counter() - t_start, 3), "reset": reset,
                  "failures": failures[:5], "failure_count": len(failures)}, indent=1))
