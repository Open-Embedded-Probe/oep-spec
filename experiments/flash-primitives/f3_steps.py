"""F3: program CH32X035 flash from the host with step lists (write32 / read32 / poll) run by the probe.

Same controller sequence as F2; the probe runs a list of steps per request instead of one access per
request. A poll with max_reads 1 doubles as an assertion: a mismatch stops the rest of that list.

  usage: f3_steps.py PORT PAGES IMAGE [PAGES_PER_BATCH]
"""
import json
import struct
import sys
import time
from pathlib import Path

from oep_client.v0.__main__ import open_client
from oep_client.v0.flash_image import Target

KEYR, STATR, CTLR, ADDR, MODEKEYR = 0x40022004, 0x4002200C, 0x40022010, 0x40022014, 0x40022024
FTPG, FTER, BUFLOAD, BUFRST, STRT, LOCK, FLOCK = 1 << 16, 1 << 17, 1 << 18, 1 << 19, 1 << 6, 1 << 7, 1 << 15
MODE_MASK = FTPG | FTER | BUFLOAD | BUFRST | STRT | 0x7
BASE, PAGE = 0x08000000, 256
MAX_STEPS_BYTES = 900        # a 1024-byte frame minus headers, with margin


def w(address, value):
    return struct.pack("<BII", 0x01, address, value)


def r(address):
    return struct.pack("<BI", 0x02, address)


def poll(address, mask, value, max_reads):
    return struct.pack("<BIIIH", 0x03, address, mask, value, max_reads)


def idle(max_reads=4000):
    # not busy, then (one read) no write-protect error
    return [poll(STATR, 0x01, 0, max_reads), poll(STATR, 0x10, 0, 1)]


def arm(page, mode):
    return [w(CTLR, mode), w(ADDR, page), poll(CTLR, MODE_MASK, mode, 1), poll(ADDR, 0xFFFFFFFF, page, 1)]


def page_steps(page, data):
    """The steps of one page, as a list of step byte strings."""
    steps = arm(page, FTER) + [w(CTLR, FTER | STRT)] + idle() + [w(CTLR, 0)]
    steps += [w(CTLR, FTPG), w(CTLR, FTPG | BUFRST)] + idle()
    for off in range(0, PAGE, 4):
        steps += [w(page + off, int.from_bytes(data[off:off + 4], "little")), w(CTLR, FTPG | BUFLOAD),
                  poll(STATR, 0x01, 0, 100)]
    steps += arm(page, FTPG) + [w(CTLR, FTPG | STRT)] + idle() + [w(CTLR, 0)]
    return steps


def pack_requests(steps):
    """Split a step list into request payloads under the frame limit (never inside a step)."""
    out, cur = [], b""
    for s in steps:
        if len(cur) + len(s) > MAX_STEPS_BYTES:
            out.append(cur)
            cur = b""
        cur += s
    if cur:
        out.append(cur)
    return out


port, pages, image_path = sys.argv[1], int(sys.argv[2]), sys.argv[3]
per_batch = int(sys.argv[4]) if len(sys.argv) > 4 else 1
image = Path(image_path).read_bytes()[:pages * PAGE]

client = open_client(port, 10.0)
target = Target(client)
target.preflight()
exp = client.find(0x0100, 0x00F0)
if exp is None:
    sys.exit("probe does not offer the experimental target primitives (0x0100:0x00f0)")
fn = exp.function
mem = target.memory

# unlock once, with plain v0 accesses (not part of the timing)
if mem.read_word(CTLR) & (LOCK | FLOCK):
    for reg in (KEYR, MODEKEYR):
        mem.write(reg, (0x45670123).to_bytes(4, "little"))
        mem.write(reg, (0xCDEF89AB).to_bytes(4, "little"))

t0 = time.perf_counter()
n_requests = 0
failures = []
for first in range(0, pages, per_batch):
    batch = []
    for n in range(first, min(first + per_batch, pages)):
        page = BASE + n * PAGE
        for payload in pack_requests(page_steps(page, image[n * PAGE:(n + 1) * PAGE])):
            batch.append((fn, 0x01, payload))
    n_requests += len(batch)
    for i, resp in enumerate(client.pipeline(batch)):
        if not resp.succeeded:
            done, status = struct.unpack_from("<HB", resp.payload) if len(resp.payload) >= 3 else (-1, -1)
            failures.append({"batch_first_page": first, "request": i, "resolution": resp.resolution,
                             "detail": resp.detail, "done": done, "status": status})
program_s = time.perf_counter() - t0

t0 = time.perf_counter()
back = mem.read_range(BASE, pages * PAGE)
verify_s = time.perf_counter() - t0
print(json.dumps({"pages": pages, "pages_per_batch": per_batch, "match": back == image,
                  "program_s": round(program_s, 3), "per_page_ms": round(1000 * program_s / pages, 2),
                  "requests": n_requests, "verify_s": round(verify_s, 3), "failures": failures[:5],
                  "failure_count": len(failures)}, indent=1))
