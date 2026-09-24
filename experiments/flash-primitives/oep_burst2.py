# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""burst_obs on the Pico's L103: the host touches the DM with pauses (no console), then reads g_report from RAM."""
import pathlib, subprocess, sys, tempfile, time
REPO = pathlib.Path("/home/mt/dev_wch/ArduinoCore-CH32")
sys.path.insert(0, str(REPO / "tests" / "manual" / "oep_smoke"))
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
import oep_smoke, targets
from oep_client.v1 import target
S = pathlib.Path(sys.argv[1]); gaps = [float(g) for g in sys.argv[2].split(",")]
prof = targets.TARGETS["l103"]
NM = next((REPO / ".tools" / "xpack-riscv-none-elf-gcc").glob("*/bin/riscv-none-elf-nm"))
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    img = oep_smoke.build("burst_obs", prof["fqbn"], tmp / "a", lambda *_: None, source=S / "burst_obs",
                          defines=["-DOBS_BASE=0x40010800u", "-DOBS_A=13", "-DOBS_B=14", "-DOBS_EN=2", "-DOBS_PRINT=0"])
    elf = next(img.parent.glob("*.ino.elf"))
    addr = int(next(l.split()[0] for l in subprocess.run([str(NM), str(elf)], capture_output=True, text=True).stdout.splitlines()
                    if l.endswith(" g_report")), 16)
    bench = oep_smoke.Bench(prof["port"], prof)
    try:
        outcome, conn, dm = oep_smoke.program(bench, img.read_bytes(), prof, print)
        print("flashed:", outcome.verified, "reset:", dm.reset(confirm=True))
        for gap in gaps:
            for _ in range(6):
                time.sleep(gap)
                try: dm.dmi(dm.step_read(0x11))
                except Exception as e: print("  dmi read failed:", e)
            time.sleep(3)
            try:
                dm.halt()
                raw = dm.read_block(addr, 100)
                dm.resume()
                print(f"gap {gap * 1000:.0f} ms @ {addr:#x}: {raw[:24].hex()} | {raw.split(bytes(1))[0].decode(errors='replace')}")
            except Exception as e:
                print(f"gap {gap * 1000:.0f} ms: read failed {e}")
    finally:
        bench.close()
