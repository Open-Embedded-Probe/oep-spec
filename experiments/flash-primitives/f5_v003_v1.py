"""F5 on CH32V003: the v1 draft only (session, oep.wire.swio, oep.target.riscv-dm) and the wlink RAM loader.

Same shape as WCH-LinkE: one mass-erase run (flags 0x03), then program-only runs (0x09) of BYTES_PER_RUN.
Blocks are split to the probe's frame (512 bytes here). With --reset the target must be seen running.

  usage: f5_v003_v1.py PORT IMAGE LOADER_BIN [BYTES_PER_RUN] [--reset]
"""
import json
import struct
import sys
import time
from pathlib import Path

from oep_client.v1 import host, link, target

BASE, PAGE = 0x08000000, 64
LOADER, INPUT, STACK, EBREAK = 0x20000000, 0x20000200, 0x20000800, 0x2000015C

args = [a for a in sys.argv[1:] if not a.startswith("--")]
port, image_path, loader_path = args[0], args[1], args[2]
per_run = int(args[3]) if len(args) > 3 else 1024
do_reset = "--reset" in sys.argv
image = Path(image_path).read_bytes()
image += b"\xff" * (-len(image) % PAGE)
loader = Path(loader_path).read_bytes()

t_start = time.perf_counter()
h = host.Host(link.SerialLink(port, timeout=5.0).send)
info = target.confirm(h)
block = (info["max_frame"] - 5 - 6 - 4 - 1 - 4) // 4 * 4     # result/request headers, session, conn, address
h.open(lease_ms=10000)
wire = target.Wire(h, "oep.wire.swio")
conn, _ = wire.attach(halt=True)
dm = target.RiscvDm(h, conn)


def write(address, data):
    for off in range(0, len(data), block):
        dm.write_block(address + off, data[off:off + block])


def read(address, length):
    out = b""
    for off in range(0, length, block):
        out += dm.read_block(address + off, min(block, length - off) // 4)
    return out


def run(flags, address, length):
    return dm.run(LOADER, [(0x100A, flags), (0x100B, address), (0x100C, length), (0x1002, STACK), (0x0300, 0)],
                  timeout_ms=1000)


write(LOADER, loader)
if read(LOADER, len(loader)) != loader:
    sys.exit("loader did not read back")
t0 = time.perf_counter()
failures = []
stopped, dpc, _, _ = run(0x03, BASE, 0)                           # unlock + mass erase
if not (stopped and dpc == EBREAK):
    sys.exit(f"mass erase did not stop on the ebreak: dpc={dpc:#x}")
for off in range(0, len(image), per_run):
    chunk = image[off:off + per_run]
    write(INPUT, chunk)
    stopped, dpc, a0, _ = run(0x09, BASE + off, len(chunk))       # unlock + program
    if not (stopped and dpc == EBREAK):
        failures.append({"address": hex(BASE + off), "stopped": stopped, "dpc": hex(dpc)})
program_s = time.perf_counter() - t0
t0 = time.perf_counter()
back = read(BASE, len(image))
verify_s = time.perf_counter() - t0
reset = None
if do_reset:
    flags, attempts, pc = dm.reset(confirm=True)
    reset = {"flags": hex(flags), "pc": hex(pc)}
wire.detach(conn)
h.end()
print(json.dumps({"bytes": len(image), "block": block, "match": back == image, "program_s": round(program_s, 3),
                  "verify_s": round(verify_s, 3), "total_s": round(time.perf_counter() - t_start, 3),
                  "reset": reset, "failures": failures[:5], "failure_count": len(failures)}, indent=1))
