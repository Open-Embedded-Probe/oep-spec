# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""Can the host win the V003's reset window with fixture.gpio on NRST plus a plain attach (no attach-under-reset)?
The target runs firmware that turns SWIO into a GPIO (swio_off), so a plain attach only works inside the window."""
import pathlib, struct, sys, tempfile, time
REPO = pathlib.Path("/home/mt/dev_wch/ArduinoCore-CH32")
sys.path.insert(0, str(REPO / "tests" / "manual" / "oep_smoke"))
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
import oep_smoke, targets
from oep_client.v0 import codec
from oep_client.v1 import host, link, target, uiapduino
S = pathlib.Path(sys.argv[1])
prof = targets.TARGETS["v003"]
LOW, REL = uiapduino.GPIO_OPEN_DRAIN_LOW, uiapduino.GPIO_OPEN_DRAIN_RELEASE
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    if "--no-flash" not in sys.argv:
        bad = oep_smoke.build("swio_off", prof["fqbn"], tmp / "a", print, source=S / "swio_off")
        bench = oep_smoke.Bench(prof["port"], prof)
        outcome, conn, dm = oep_smoke.program(bench, bad.read_bytes(), prof, print)
        print("flashed swio_off:", outcome.verified)
        try: dm.reset(confirm=False)
        except Exception: pass
        try: bench.wire.detach(conn)
        except Exception: pass
        bench.close(); import gc; del bench, dm; gc.collect()
    lk = link.SerialLink(prof["port"])
    hst = host.Host(lk.send)
    hst.open(lease_ms=15000, force=True)
    wire = target.Wire(hst, prof["wire"])
    nrst = target.probe_labels(hst)["NRST"]
    gpio_fn = target.find(hst, "oep.fixture.gpio")
    cfg = lambda mode: codec.FixtureGpioConfigureRequest(channel=nrst, mode=mode).pack()
    def check(label):
        try:
            conn, st = wire.attach(halt=True)
            print(f"  {label}: plain attach WORKS dmstatus {st:#x}"); wire.detach(conn)
        except Exception as e:
            print(f"  {label}: plain attach fails ({e})")
    check("baseline (no reset)")
    for trial in range(5):
        hst.request(gpio_fn, codec.FIXTURE_GPIO_OP_CONFIGURE, cfg(LOW)); time.sleep(0.02)
        t0 = time.perf_counter()
        hst.request(gpio_fn, codec.FIXTURE_GPIO_OP_CONFIGURE, cfg(REL))
        t1 = time.perf_counter()
        r = hst.request(wire.fn, wire.ATTACH, bytes([1]))
        t2 = time.perf_counter()
        out = "WORKS" if r.succeeded else "fails"
        if r.succeeded:
            conn = r.payload[0]; dm = target.RiscvDm(hst, conn)
            try: out += f" RSTSCKR {dm.read32(0x40021024):#x}"
            except Exception as e: out += f" ({e})"
            wire.detach(conn)
        print(f"A{trial} sequential: release reply {1000*(t1-t0):.1f} ms, attach reply {1000*(t2-t1):.1f} ms -> {out}")
    for trial in range(5):
        hst.request(gpio_fn, codec.FIXTURE_GPIO_OP_CONFIGURE, cfg(LOW)); time.sleep(0.02)
        t0 = time.perf_counter()
        res = hst.pipeline([(gpio_fn, codec.FIXTURE_GPIO_OP_CONFIGURE, cfg(REL)), (wire.fn, wire.ATTACH, bytes([1]))],
                           exchange=lambda msgs: lk.exchange(msgs, 2, 512))
        t1 = time.perf_counter()
        out = "WORKS" if res[1].succeeded else "fails"
        if res[1].succeeded: wire.detach(res[1].payload[0])
        print(f"B{trial} pipelined: {1000*(t1-t0):.1f} ms -> {out}")
    check("after trials")
    hst.end()
