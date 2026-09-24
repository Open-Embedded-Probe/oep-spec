# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""V003 probe (classic ESP32, CH340, COBS+CRC) at one UART rate: DMI round trip, block read, a 14 KB flash + verify,
and the link's CRC error / resend counts. The probe firmware is built for that rate (experiment build)."""
import json, os, sys, time
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
from oep_client.v1 import host, link, target, ch32_flash
port, baud = sys.argv[1], int(sys.argv[2])
lk = link.SerialLink(port)
lk.stream.baudrate = baud
time.sleep(0.3); lk.stream.reset_input_buffer()
h = host.Host(lk.send)
res = {"baud": baud}
try:
    h.open(lease_ms=60000, force=True)
    wire = target.Wire(h, "oep.wire.swio")
    conn, _ = wire.attach(halt=True)
    dm = target.RiscvDm(h, conn)
    t0 = time.perf_counter()
    for _ in range(50): dm.dmi(dm.step_read(0x11))
    res["dmi_rtt_ms"] = round((time.perf_counter() - t0) / 50 * 1000, 2)
    t0 = time.perf_counter()
    n = 0
    for _ in range(8): n += len(dm.read_block(0x08000000, 120)) // 4 * 4
    dt = time.perf_counter() - t0
    res["read_kib_s"] = round(n / 1024 / dt, 1)
    dm.reset_halt()
    image = os.urandom(14 * 1024)
    t0 = time.perf_counter()
    r = ch32_flash.program(h, dm, image, ch32_flash.PROFILES["v003"])
    res["flash_14k_s"] = round(time.perf_counter() - t0, 2)
    res["verified"] = r.verified
    res["timings"] = r.timings
    wire.detach(conn)
    h.end()
except Exception as e:
    res["error"] = f"{type(e).__name__}: {e}"
res["crc_errors"] = lk.corrupt
res["resends"] = lk.retries
print(json.dumps(res))
