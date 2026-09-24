"""F4 on CH32V003: the wlink RAM loader (moved from the v0 probe to the host) + block write + run-until-halt.

Loader at 0x20000000 (500 bytes, ebreak at +0x15c), input at 0x20000200, stack 0x20000800.
Per run: a0 = 0x1d (unlock, erase, program, verify), a1 = flash address, a2 = byte count, mstatus = 0.
Success = the hart stopped on the loader's ebreak; the full read-back at the end is the data proof.

  usage: f4_v003.py PORT IMAGE LOADER_BIN [BYTES_PER_RUN]
"""
import json
import struct
import sys
import time
from pathlib import Path

from oep_client.v0.__main__ import open_client
from oep_client.v0.flash_image import Target

BASE, PAGE = 0x08000000, 64
LOADER, INPUT, STACK, EBREAK = 0x20000000, 0x20000200, 0x20000800, 0x2000015C


def block(address, data):
    words = [int.from_bytes(data[i:i + 4], "little") for i in range(0, len(data), 4)]
    return struct.pack(f"<BIH{len(words)}I", 0x04, address, len(words), *words)


def run(pc, regs, timeout_ms=500):
    body = struct.pack("<IHB", pc, timeout_ms, len(regs))
    for regno, value in regs:
        body += struct.pack("<HI", regno, value)
    return body


port, image_path, loader_path = sys.argv[1], sys.argv[2], sys.argv[3]
per_run = int(sys.argv[4]) if len(sys.argv) > 4 else PAGE
image = Path(image_path).read_bytes()
loader = Path(loader_path).read_bytes()

client = open_client(port, 10.0)
target = Target(client)
target.preflight()
fn = client.find(0x0100, 0x00F0).function
mem = target.memory
max_block = (client.limits.max_frame - 32) // 4 * 4   # room for the request header and step header

t0 = time.perf_counter()
for off in range(0, len(loader), max_block):
    client.call(fn, 0x01, block(LOADER + off, loader[off:off + max_block])).expect_success("load loader")
if mem.read_range(LOADER, len(loader)) != loader:
    sys.exit("loader did not read back")
load_s = time.perf_counter() - t0

t0 = time.perf_counter()
failures, elapsed_us, requests = [], [], 0
for off in range(0, len(image), per_run):
    chunk = image[off:off + per_run]
    for b in range(0, len(chunk), max_block):
        client.call(fn, 0x01, block(INPUT + b, chunk[b:b + max_block])).expect_success("input")
        requests += 1
    resp = client.call(fn, 0x02, run(LOADER, [(0x100A, 0x1D), (0x100B, BASE + off), (0x100C, len(chunk)),
                                             (0x1002, STACK), (0x0300, 0)]))
    requests += 1
    stopped, dpc, a0, us = struct.unpack("<BIII", resp.payload[:13])
    elapsed_us.append(us)
    if not (resp.succeeded and stopped and dpc == EBREAK):
        failures.append({"address": hex(BASE + off), "stopped": stopped, "dpc": hex(dpc), "a0": hex(a0)})
program_s = time.perf_counter() - t0

t0 = time.perf_counter()
back = mem.read_range(BASE, len(image))
verify_s = time.perf_counter() - t0
elapsed_us.sort()
print(json.dumps({"bytes": len(image), "bytes_per_run": per_run, "match": back == image,
                  "loader_load_s": round(load_s, 3), "program_s": round(program_s, 3),
                  "requests": requests, "verify_s": round(verify_s, 3),
                  "run_us_median": elapsed_us[len(elapsed_us) // 2], "run_us_max": elapsed_us[-1],
                  "failures": failures[:5], "failure_count": len(failures)}, indent=1))
