# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""Time from the reset vector to the top of setup() on the V003 (the window before a sketch can turn SWIO off)."""
import pathlib, sys, tempfile
REPO = pathlib.Path("/home/mt/dev_wch/ArduinoCore-CH32")
sys.path.insert(0, str(REPO / "tests" / "manual" / "oep_smoke"))
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
import oep_smoke, targets
from oep_client.v1 import ch32_flash, target
S = pathlib.Path(sys.argv[1])
prof = targets.TARGETS["v003"]
MSTATUS = 0x300
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    img = oep_smoke.build("setup_ebreak", prof["fqbn"], tmp / "a", print, source=S / "setup_ebreak")
    bench = oep_smoke.Bench(prof["port"], prof)
    try:
        outcome, conn, dm = oep_smoke.program(bench, img.read_bytes(), prof, print)
        print("flashed:", outcome.verified)
        bench.wire.detach(conn)
        for path in ("nrst", "ndmreset"):
            res = []
            for _ in range(5):
                if path == "nrst":
                    conn, pc0 = bench.wire.attach_under_reset()
                    dm = target.RiscvDm(bench.host, conn)
                else:
                    conn, _ = bench.wire.attach(halt=True)
                    dm = target.RiscvDm(bench.host, conn)
                    pc0 = dm.reset_halt()
                stopped, dpc, a0, us = dm.run(pc0, [], timeout_ms=1000)
                # overhead: run again straight onto the ebreak
                s2, d2, _, us0 = dm.run(dpc, [], timeout_ms=100)
                res.append((pc0, stopped, dpc, us, us0))
                bench.wire.detach(conn)
            print(path, [f"pc0 {p:#x} -> {'ebreak' if s else 'TIMEOUT'} {d:#x} in {u} us (overhead {o} us)" for p, s, d, u, o in res])
        conn, _ = bench.wire.attach(halt=True)
        dm = target.RiscvDm(bench.host, conn)
        dm.reset_halt()
        good = oep_smoke.build("core_api", prof["fqbn"], tmp / "b", print, defines=[f"-D{prof['define']}"])
        print("restore core_api:", ch32_flash.program(bench.host, dm, good.read_bytes(), ch32_flash.PROFILES["v003"]).verified, dm.reset(confirm=True))
        bench.wire.detach(conn)
    finally:
        bench.close()
