"""Read the V003 flash in fixed-size requests and compare with an image (transport check)."""
import sys, time
from pathlib import Path
from oep_client.v0.__main__ import open_client
from oep_client.v0.flash_image import Target
port, image, chunk = sys.argv[1], Path(sys.argv[2]).read_bytes(), int(sys.argv[3])
client = open_client(port, 3.0); t = Target(client); t.preflight()
t0 = time.perf_counter(); out = bytearray()
for off in range(0, len(image), chunk):
    out += t.memory.read(0x08000000 + off, min(chunk, len(image) - off))
print(f"chunk {chunk}: {time.perf_counter() - t0:.3f} s, match {bytes(out) == image}")
