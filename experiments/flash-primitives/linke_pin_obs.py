# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""Each WCH-Link board: flash pin_idle_obs (the target watches its own debug pins), then run ch32rv's dmseq monitor
at two speeds and collect what the target saw while the link polled it. -> the link's idle levels per target."""
import pathlib, subprocess, sys, tempfile
REPO = pathlib.Path("/home/mt/dev_wch/ArduinoCore-CH32")
sys.path.insert(0, str(REPO / "tests" / "manual" / "oep_smoke"))
import oep_smoke
CH32RV = str(REPO / ".tools" / "ch32rv" / "0.10.0" / "ch32rv")
S = pathlib.Path(sys.argv[1])
BOARDS = {   # name: (board, probe serial, GPIO base, pin a, pin b, RCC_APB2PCENR bit, pin names)
    "l103": ("CH32L103", "0E028F0692F1", 0x40010800, 13, 14, 2, "PA13(SWDIO) PA14(SWCLK)"),
    "x035": ("CH32X035", "FC928F068181", 0x40011000, 18, 19, 4, "PC18 PC19"),
    "v203": ("CH32V203", "FBC18F0680B0", 0x40010800, 13, 14, 2, "PA13(SWDIO) PA14(SWCLK)"),
    "v307": ("CH32V307", "38EF8F06BDC2", 0x40010800, 13, 14, 2, "PA13(SWDIO) PA14(SWCLK)"),
    "v103": ("CH32V103", "434A124C5596", 0x40010800, 13, 14, 2, "PA13(SWDIO) PA14(SWCLK)"),
    "v003": ("CH32V003", "F90E8F067DFD", 0x40011400, 1, -1, 5, "PD1(SWIO)"),
    "v006": ("CH32V006", "497F8F06CE2F", 0x40011400, 1, -1, 5, "PD1(SWIO)"),
}
names = sys.argv[2].split(",") if len(sys.argv) > 2 else list(BOARDS)
SKETCH = sys.argv[3] if len(sys.argv) > 3 else "pin_idle_obs"
TAG = "BURST" if SKETCH == "burst_obs" else "OBS"
SPEEDS = sys.argv[4].split(",") if len(sys.argv) > 4 else ["low", "high"]
for name in names:
    board, serial, base, a, b, en, pins = BOARDS[name]
    print(f"=== {name} ({board}, link {serial}): a/b = {pins}", flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        try:
            img = oep_smoke.build(SKETCH, f"ch32-riscv-ug:ch32v:{board}:pnum=ANY", tmp, lambda *_: None,
                                  source=S / SKETCH,
                                  defines=[f"-DOBS_BASE={base:#x}u", f"-DOBS_A={a}", f"-DOBS_B={b}", f"-DOBS_EN={en}"])
        except Exception as e:
            print("  build failed:", str(e)[-400:]); continue
        elf = next(img.parent.glob("*.ino.elf"))
        r = subprocess.run([CH32RV, "--probe", f"serial:{serial}", "--yes", "flash", str(elf)], capture_output=True, text=True, timeout=120)
        print("  flash:", (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else r.returncode)
        for speed in SPEEDS:
            r = subprocess.run([CH32RV, "--probe", f"serial:{serial}", "--speed", speed, "--duration", "6",
                                "monitor", "--source", "dmseq"], capture_output=True, text=True, timeout=60)
            lines = [l for l in r.stdout.splitlines() if l.startswith(TAG)]
            print(f"  monitor {speed}: {len(lines)} lines")
            for l in lines[:12]: print("   ", l)
            if not lines: print("   ", (r.stdout + r.stderr).strip()[-300:])
