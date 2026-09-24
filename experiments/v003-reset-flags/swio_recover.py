# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""Destructive: flash a sketch that disables SWIO on the V003, show plain attach fails, recover through
attach_under_reset (NRST = probe default) by flashing core_api, show plain attach works again."""
import pathlib, sys, tempfile
REPO = pathlib.Path("/home/mt/dev_wch/ArduinoCore-CH32")
sys.path.insert(0, str(REPO / "tests" / "manual" / "oep_smoke"))
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
import oep_smoke, targets
from oep_client.v1 import ch32_flash, target
S = pathlib.Path(sys.argv[1])
prof = targets.TARGETS["v003"] if hasattr(targets, "TARGETS") else targets.JIGS["v003"]
log = print
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    bad = oep_smoke.build("swio_off", prof["fqbn"], tmp / "a", log, source=S / "swio_off")
    good = oep_smoke.build("core_api", prof["fqbn"], tmp / "b", log, defines=[f"-D{prof['define']}"])
    bench = oep_smoke.Bench(prof["port"], prof)
    try:
        if "--recover-only" not in sys.argv:
            outcome, conn, dm = oep_smoke.program(bench, bad.read_bytes(), prof, log)
            print("flashed swio_off:", outcome.verified)
            try: print("reset:", dm.reset(confirm=False))
            except Exception as e: print("reset after swio_off:", e)
            try: bench.wire.detach(conn)
            except Exception as e: print("detach:", e)
        try:
            conn, st = bench.wire.attach(halt=False)
            print(f"plain attach after swio_off: STILL WORKS dmstatus {st:#x}")
            bench.wire.detach(conn)
        except Exception as e:
            print("plain attach after swio_off: fails as expected:", e)
        conn = None
        if "--via-gpio" in sys.argv:
            lk = bench.host.send.__self__
            gpio_fn = target.find(bench.host, "oep.fixture.gpio")
            conn, st = target.attach_after_gpio_reset(bench.host, bench.wire, gpio_fn, bench.nrst,
                                                      lambda msgs: lk.exchange(msgs, 2, 512), tries=20)
            print(f"attach_after_gpio_reset: conn {conn} dmstatus {st:#x}")
            dm = target.RiscvDm(bench.host, conn)
            print("reset_halt dpc", hex(dm.reset_halt()))
        holds = [] if conn is not None else ([int(a.split("=")[1]) for a in sys.argv if a.startswith("--hold=")] or [20, 1, 5, 50, 100, 200, 2, 10, 500])
        for hold in holds:
            try:
                conn, dpc = bench.wire.attach_under_reset(hold_ms=hold)
                print(f"attach_under_reset hold {hold} ms: conn {conn} dpc {dpc:#x}")
                break
            except Exception as e:
                print(f"attach_under_reset hold {hold} ms: failed ({e})")
        if conn is None:
            raise SystemExit("attach_under_reset never took - recover through HID + NRST")
        dm = target.RiscvDm(bench.host, conn)
        outcome = ch32_flash.program(bench.host, dm, good.read_bytes(), ch32_flash.PROFILES[prof["flash"]])
        print("flashed core_api:", outcome.verified, "reset:", dm.reset(confirm=True))
        bench.wire.detach(conn)
        conn, st = bench.wire.attach(halt=False)
        print(f"plain attach after recovery: dmstatus {st:#x}")
        bench.wire.detach(conn)
    finally:
        bench.close()
