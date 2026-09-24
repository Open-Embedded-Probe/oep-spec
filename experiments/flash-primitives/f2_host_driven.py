"""F2: program CH32X035 flash from the host with nothing but v0 target.memory read/write.

The flash-controller sequence is the one the v0 probe runs inside (OepCh32Dm.cpp), moved to the host:
unlock -> per page: erase, BUFRST, per word (store word, CTLR = FTPG|BUFLOAD, STATR not busy), start, wait.

  mode a: every request waits for its response
  mode b: the per-word requests of one page go out pipelined; the STATR reads are checked afterwards
"""
import json
import sys
import time
from pathlib import Path

from oep_client.v0 import codec
from oep_client.v0.__main__ import open_client
from oep_client.v0.flash_image import Target

KEYR, STATR, CTLR, ADDR, MODEKEYR = 0x40022004, 0x4002200C, 0x40022010, 0x40022014, 0x40022024
FTPG, FTER, BUFLOAD, BUFRST, STRT, LOCK, FLOCK = 1 << 16, 1 << 17, 1 << 18, 1 << 19, 1 << 6, 1 << 7, 1 << 15
MODE_MASK = FTPG | FTER | BUFLOAD | BUFRST | STRT | 0x7
BASE, PAGE = 0x08000000, 256

port, mode, pages, image_path = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
image = Path(image_path).read_bytes()[:pages * PAGE]

client = open_client(port, 10.0)
target = Target(client)
target.preflight()                          # attaches and halts, as the v0 program path does
mem = target.memory
fn = mem.function
requests = {"write": 0, "read": 0}


def w32(address, value):
    requests["write"] += 1
    mem.write(address, value.to_bytes(4, "little"))


def r32(address):
    requests["read"] += 1
    return mem.read_word(address)


def wait_idle(what):
    for _ in range(4000):
        status = r32(STATR)
        if not status & 1:
            if status & 0x10:
                raise RuntimeError(f"{what}: write-protect error, STATR={status:#x}")
            return
    raise RuntimeError(f"{what}: still busy")


def arm(page, mode_bits):
    for _ in range(3):
        w32(CTLR, mode_bits)
        w32(ADDR, page)
        if (r32(CTLR) & MODE_MASK) == mode_bits and r32(ADDR) == page:
            return
    raise RuntimeError(f"arm {page:#x} {mode_bits:#x} did not stick")


def unlock():
    if r32(CTLR) & (LOCK | FLOCK):
        for reg in (KEYR, MODEKEYR):
            w32(reg, 0x45670123)
            w32(reg, 0xCDEF89AB)
    if r32(CTLR) & (LOCK | FLOCK):
        raise RuntimeError("flash stays locked")


def write_req(address, value):
    return (fn, codec.TARGET_MEMORY_OP_WRITE,
            codec.TargetMemoryWriteRequest(address=address, data=value.to_bytes(4, "little")).pack())


def read_req(address):
    return (fn, codec.TARGET_MEMORY_OP_READ, codec.TargetMemoryReadRequest(address=address, length=4).pack())


def load_buffer_sequential(page, data):
    for off in range(0, PAGE, 4):
        w32(page + off, int.from_bytes(data[off:off + 4], "little"))
        w32(CTLR, FTPG | BUFLOAD)
        wait_idle("bufload")


def load_buffer_pipelined(page, data):
    batch = []
    for off in range(0, PAGE, 4):
        batch += [write_req(page + off, int.from_bytes(data[off:off + 4], "little")),
                  write_req(CTLR, FTPG | BUFLOAD), read_req(STATR)]
    responses = client.pipeline(batch)
    requests["write"] += 2 * (PAGE // 4)
    requests["read"] += PAGE // 4
    for i, response in enumerate(responses):
        body = response.expect_success("pipelined flash step")
        if i % 3 == 2:
            status = int.from_bytes(codec.TargetMemoryReadResult.unpack(body).data, "little")
            if status & 1:
                raise RuntimeError(f"bufload still busy at word {i // 3} of {page:#x}")


load = load_buffer_sequential if mode == "a" else load_buffer_pipelined

t0 = time.perf_counter()
unlock()
for n in range(pages):
    page = BASE + n * PAGE
    data = image[n * PAGE:(n + 1) * PAGE]
    arm(page, FTER)
    w32(CTLR, FTER | STRT)
    wait_idle("erase")
    w32(CTLR, 0)
    w32(CTLR, FTPG)
    w32(CTLR, FTPG | BUFRST)
    wait_idle("bufrst")
    load(page, data)
    arm(page, FTPG)
    w32(CTLR, FTPG | STRT)
    wait_idle("program")
    w32(CTLR, 0)
program_s = time.perf_counter() - t0

t0 = time.perf_counter()
back = mem.read_range(BASE, pages * PAGE)
verify_s = time.perf_counter() - t0
print(json.dumps({"mode": mode, "pages": pages, "match": back == image, "program_s": round(program_s, 3),
                  "per_page_ms": round(1000 * program_s / pages, 2), "verify_s": round(verify_s, 3),
                  "requests": requests}, indent=1))
