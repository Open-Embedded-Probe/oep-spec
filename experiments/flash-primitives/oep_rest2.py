# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""rest_obs (OBS_PRINT=0) on the Pico's L103: reset, rest `rest` s attached, one DMI read, wait, halt, read g_line."""
import pathlib, subprocess, sys, tempfile, time
REPO = pathlib.Path("/home/mt/dev_wch/ArduinoCore-CH32")
sys.path.insert(0, str(REPO / "tests" / "manual" / "oep_smoke"))
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
import oep_smoke, targets
from oep_client.v1 import target
S = pathlib.Path(sys.argv[1]); label = sys.argv[2]
prof = targets.TARGETS["l103"]
NM = next((REPO / ".tools" / "xpack-riscv-none-elf-gcc").glob("*/bin/riscv-none-elf-nm"))
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    img = oep_smoke.build("rest_obs", prof["fqbn"], tmp / "a", lambda *_: None, source=S / "rest_obs",
                          defines=["-DOBS_BASE=0x40010800u", "-DOBS_A=13", "-DOBS_B=14", "-DOBS_EN=2", "-DOBS_PRINT=0"])
    elf = next(img.parent.glob("*.ino.elf"))
    syms = {l.split()[2]: int(l.split()[0], 16) for l in subprocess.run([str(NM), str(elf)], capture_output=True, text=True).stdout.splitlines() if len(l.split()) == 3}
    addr = syms["g_line"]
    bench = oep_smoke.Bench(prof["port"], prof)
    try:
        outcome, conn, dm = oep_smoke.program(bench, img.read_bytes(), prof, lambda *_: None)
        print(f"[{label}] flashed {outcome.verified}")
        for rest in (0.1, 0.5, 2.0, 2.0):
            print("   reset", dm.reset(confirm=True))
            time.sleep(rest)
            for _ in range(3):
                try: dm.dmi(dm.step_read(0x11))
                except Exception as e: print("   dmi read after rest failed:", e)
                time.sleep(0.1)
            time.sleep(0.5)
            try:
                dm.halt()
                raw = dm.read_block(addr, 105)
                import struct
                beat, now, ch = (struct.unpack("<I", dm.read_block(syms[n], 1))[0] for n in ("g_beat", "g_now", "g_changes"))
                ph, rl, gn = (struct.unpack("<I", dm.read_block(syms[x], 1))[0] for x in ("g_phase", "g_rest_level", "g_n"))
                vals = dm.read_block(syms["_ZL3val"], 8) if "_ZL3val" in syms else b""
                print(f"    beat {beat} now {now} changes {ch} phase {ph} rest_level {rl} burst_n {gn} val {list(vals[:32])}")
                print(f"  rest {rest} s -> {raw.split(bytes(1))[0].decode(errors='replace') or '(empty)'}")
            except Exception as e:
                print(f"  rest {rest} s -> read failed: {e}")
        dm.reset(confirm=True)
    finally:
        bench.close()
