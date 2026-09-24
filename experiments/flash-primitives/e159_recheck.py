# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""E159 re-check on the X035 (P4 probe): after reset-halt + resume, and after a plain reset, does millis() run?"""
import pathlib, re, sys, tempfile, time
REPO = pathlib.Path("/home/mt/dev_wch/ArduinoCore-CH32")
sys.path.insert(0, str(REPO / "tests" / "manual" / "oep_smoke"))
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
import oep_smoke, targets
from oep_client.v1 import target
S = pathlib.Path(sys.argv[1]); name = sys.argv[2] if len(sys.argv) > 2 else "x035"
prof = targets.TARGETS[name]
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    img = oep_smoke.build("millis_print", prof["fqbn"], tmp / "a", print, source=S / "millis_print")
    bench = oep_smoke.Bench(prof["port"], prof)
    try:
        outcome, conn, dm = oep_smoke.program(bench, img.read_bytes(), prof, print)
        print("flashed:", outcome.verified)
        console = target.Console(bench.host)
        console.open(conn, target.Console.DMSEQ)
        io = target.ConsoleIO(console)
        def sample(wait=0.6):
            io.read(4096); time.sleep(wait)
            text = b""
            for _ in range(10):
                chunk = io.read(4096)
                if not chunk: break
                text += chunk
            vals = [int(v) for v in re.findall(rb"T (\d+)", text)]
            return vals
        for mode in ("reset_halt+resume", "reset"):
            ok, bad = 0, []
            for i in range(20):
                if mode == "reset":
                    dm.reset(confirm=False)
                else:
                    dm.reset_halt(); dm.resume()
                vals = sample()
                if len(vals) >= 5 and vals[-1] - vals[0] >= 150 and all(b > a for a, b in zip(vals, vals[1:])):
                    ok += 1
                else:
                    bad.append(vals[:3] + (["..."] if len(vals) > 3 else []) + vals[-2:])
            print(f"{mode}: millis running {ok}/20; bad samples {bad[:4]}")
    finally:
        bench.close()
