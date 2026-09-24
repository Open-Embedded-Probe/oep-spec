"""F4: program CH32X035 flash with a host-supplied RAM loader and the generic "run until halt".

The loader (x035_loader.S, 196 bytes) is placed at 0x20000000 once. Per page: one steps request
that block-writes the 256-byte page into a RAM buffer, then one run request (a0 = page, a1 = buffer,
mstatus = 0). Success = the hart stopped on done_ok with a0 == 0.

  usage: f4_loader.py PORT PAGES IMAGE LOADER_BIN [PAGES_PER_BATCH]
"""
import json
import struct
import sys
import time
from pathlib import Path

from oep_client.v0.__main__ import open_client
from oep_client.v0.flash_image import Target

KEYR, CTLR, MODEKEYR = 0x40022004, 0x40022010, 0x40022024
LOCK, FLOCK = 1 << 7, 1 << 15
BASE, PAGE = 0x08000000, 256
LOADER, BUFFER = 0x20000000, 0x20000400
DONE_OK, DONE_FAIL = 0x200000B0, 0x200000C0


def block(address, data):
    words = [int.from_bytes(data[i:i + 4], "little") for i in range(0, len(data), 4)]
    return struct.pack(f"<BIH{len(words)}I", 0x04, address, len(words), *words)


def run(pc, regs, timeout_ms=200):
    body = struct.pack("<IHB", pc, timeout_ms, len(regs))
    for regno, value in regs:
        body += struct.pack("<HI", regno, value)
    return body


port, pages, image_path, loader_path = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
per_batch = int(sys.argv[5]) if len(sys.argv) > 5 else 1
image = Path(image_path).read_bytes()[:pages * PAGE]
loader = Path(loader_path).read_bytes()
loader += b"\0" * (-len(loader) % 4)

client = open_client(port, 10.0)
target = Target(client)
target.preflight()
fn = client.find(0x0100, 0x00F0).function
mem = target.memory

if mem.read_word(CTLR) & (LOCK | FLOCK):
    for reg in (KEYR, MODEKEYR):
        mem.write(reg, (0x45670123).to_bytes(4, "little"))
        mem.write(reg, (0xCDEF89AB).to_bytes(4, "little"))

t0 = time.perf_counter()
client.call(fn, 0x01, block(LOADER, loader)).expect_success("load loader")
if mem.read(LOADER, len(loader)) != loader:
    sys.exit("loader did not read back")
load_s = time.perf_counter() - t0

t0 = time.perf_counter()
failures, elapsed_us = [], []
for first in range(0, pages, per_batch):
    batch = []
    for n in range(first, min(first + per_batch, pages)):
        page = BASE + n * PAGE
        batch.append((fn, 0x01, block(BUFFER, image[n * PAGE:(n + 1) * PAGE])))
        batch.append((fn, 0x02, run(LOADER, [(0x100A, page), (0x100B, BUFFER), (0x0300, 0)])))
    for i, resp in enumerate(client.pipeline(batch)):
        page = BASE + (first + i // 2) * PAGE
        if i % 2 == 0:
            if not resp.succeeded:
                failures.append({"page": hex(page), "step": "buffer", "detail": resp.detail})
            continue
        if len(resp.payload) < 13:
            failures.append({"page": hex(page), "step": "run", "resolution": resp.resolution, "detail": resp.detail})
            continue
        stopped, dpc, a0, us = struct.unpack("<BIII", resp.payload[:13])
        elapsed_us.append(us)
        if not (resp.succeeded and stopped and dpc == DONE_OK and a0 == 0):
            failures.append({"page": hex(page), "step": "run", "stopped": stopped, "dpc": hex(dpc), "a0": hex(a0)})
program_s = time.perf_counter() - t0

t0 = time.perf_counter()
back = mem.read_range(BASE, pages * PAGE)
verify_s = time.perf_counter() - t0
elapsed_us.sort()
print(json.dumps({"pages": pages, "pages_per_batch": per_batch, "match": back == image,
                  "loader_load_s": round(load_s, 3), "program_s": round(program_s, 3),
                  "per_page_ms": round(1000 * program_s / pages, 2), "verify_s": round(verify_s, 3),
                  "run_us_median": elapsed_us[len(elapsed_us) // 2] if elapsed_us else None,
                  "run_us_max": elapsed_us[-1] if elapsed_us else None,
                  "failures": failures[:5], "failure_count": len(failures)}, indent=1))
