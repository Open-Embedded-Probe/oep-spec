# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial>=3.5"]
# ///
"""EXPERIMENT host for the sequenced DM console: program a prebuilt DmSeqTest image through
an OEP probe, open target.console with the given framing, and check RUN and ECHO byte for byte."""
import argparse, difflib, pathlib, random, re, sys, time

REPO = pathlib.Path("/home/mt/dev_wch/ArduinoCore-CH32")
sys.path.insert(0, str(REPO / "tests" / "manual" / "oep_smoke"))
sys.path.insert(0, "/home/mt/dev_oep/oep-client-python/src")
from targets import TARGETS                      # noqa: E402


def expected_run() -> str:
    return "".join(f"L{i:02d} " + "a" * (i % 9 + 1) + " 2.00 deadbeef 0123456\n" for i in range(40))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--bin", required=True)
    ap.add_argument("--framing", type=int, required=True)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--echo", type=int, default=20)
    a = ap.parse_args()
    from oep_client.v0.__main__ import open_client
    from oep_client.v0 import codec
    from oep_client.v0.flash_image import Target, program_image
    from oep_client.v0.services import TargetConsole
    prof = TARGETS[a.target]
    client = open_client(prof["port"], 3.0)
    target = Target(client)
    img = pathlib.Path(a.bin).read_bytes()
    for attempt in range(5):
        try:
            program_image(target, img)
            break
        except Exception:
            if attempt == 4:
                raise
            if attempt == 2:
                try:
                    target.control.reset_report(3)
                except Exception:
                    pass
            time.sleep(0.5)
    fn = client.find(*codec.DEF_TARGET_CONSOLE[:2])
    con = TargetConsole(client, fn.function)
    for attempt in range(4):
        try:
            con.configure(True, a.framing)
            break
        except Exception:
            if attempt == 3:
                raise
            time.sleep(0.3)
    buf = ""
    alltext = ""                     # everything received, never reset: checked line by line at the end
    expected = []                    # what must appear, in order, between banner lines

    def pump():
        nonlocal buf, alltext
        d = con.read(512)
        if d:
            text = d.decode("latin-1")
            buf += text
            alltext += text

    def wait(tok, t):
        end = time.monotonic() + t
        while time.monotonic() < end:
            if tok in buf:
                return True
            pump()
            time.sleep(0.005)
        return tok in buf

    def wait_re(pat, t):
        rx = re.compile(pat)
        end = time.monotonic() + t
        while time.monotonic() < end:
            if rx.search(buf):
                return True
            pump()
            time.sleep(0.005)
        return bool(rx.search(buf))

    ok_all = True
    if not wait("dmseq READY", 10):
        print("no banner:", repr(buf[-200:]))
        sys.exit(2)
    exp = expected_run()
    for r in range(a.rounds):
        expected.extend(l.replace("\n", "\r\n") if False else l for l in exp.splitlines(True))
        expected.append(re.compile(r"END reposts=\d+ timeouts=\d+\r\n"))
        buf = ""
        t0 = time.monotonic()
        con.write(b"RUN\n")
        if not wait_re(r"END reposts=\d+ timeouts=\d+\r\n", 60):
            print(f"run {r}: no END", repr(buf[-300:]))
            ok_all = False
            continue
        dt = time.monotonic() - t0
        body = buf[:buf.index("END ")]
        body = "".join(l for l in body.splitlines(True) if l != "dmseq READY\r\n")
        tail = buf[buf.index("END "):].splitlines()[0]
        same = body == exp
        ok_all &= same
        print(f"run {r}: {'OK ' if same else 'BAD'} {len(exp)} B in {dt:.2f} s ({len(exp)/dt:.0f} B/s)  {tail}")
        if not same:
            for line in list(difflib.unified_diff(exp.splitlines(), body.splitlines(), lineterm="", n=0))[:12]:
                print("   ", line)
    rnd = random.Random(1)
    bad = 0
    t0 = time.monotonic()
    for i in range(a.echo):
        text = "".join(rnd.choice("abcdefghij0123456789==ee  ") for _ in range(rnd.randint(1, 40)))
        buf = ""
        expected.append(f"R {text}\r\n")
        con.write(f"E {text}\n".encode())
        if not wait(f"R {text}\r\n", 10):
            bad += 1
            got = [l for l in buf.splitlines() if l.startswith("R ") or l.startswith("? ")]
            if bad <= 3:
                print(f"   echo {i}: sent {text!r} got {got[:2]!r}")
    print(f"echo: {a.echo - bad}/{a.echo} OK in {time.monotonic() - t0:.2f} s")
    ok_all &= bad == 0
    # Restart the target while we are attached and polling: its first frames carry SYN again,
    # and nothing it prints from here may be lost or doubled (no timeout can excuse it).
    restart_at = len(alltext)
    con.write(b"RESTART\n")
    end = time.monotonic() + 3
    while time.monotonic() < end:
        pump()
        time.sleep(0.005)
    after = alltext[restart_at:].splitlines(True)
    after_ok = bool(after) and all(l == "dmseq READY\r\n" for l in after if l.endswith("\n"))
    print(f"restart: {sum(1 for l in after if l == 'dmseq READY' + chr(13) + chr(10))} banners after RESTART, "
          f"{'all exact' if after_ok else 'NOT exact: ' + repr([l for l in after if l != 'dmseq READY' + chr(13) + chr(10)][:3])}")
    ok_all &= after_ok
    alltext = alltext[:restart_at]
    # Strict: every line received is either an exact banner or the next expected line. A
    # duplicated or lost frame anywhere - banners included - shows up here.
    time.sleep(0.3)
    pump()
    lines = alltext.splitlines(True)
    if lines and not lines[-1].endswith("\n"):
        lines.pop()                  # a banner still arriving
    # Before we attached the target may have timed out and dropped output, legitimately; the
    # check starts at the first exact banner.
    first = next((i for i, l in enumerate(lines) if l == "dmseq READY\r\n"), 0)
    lines = lines[first:]
    it = iter(expected)
    want = next(it, None)
    strict = []
    for n, line in enumerate(lines):
        if line == "dmseq READY\r\n":
            continue
        ok = want is not None and (want.fullmatch(line) if hasattr(want, "fullmatch") else line == want)
        if ok:
            want = next(it, None)
        else:
            strict.append((n, line))
    if want is not None:
        strict.append((-1, f"missing from here: {want!r}"))
    print(f"strict: {len(lines)} lines, {len(strict)} unexpected")
    for n, line in strict[:6]:
        print(f"    line {n}: {line!r}")
    ok_all &= not strict
    d = getattr(con.status(), "dropped", 0)
    print(f"probe: dropped={d & 1023} dups={(d >> 10) & 1023} crc_bad={(d >> 20) & 1023}"
          if a.framing >= 2 else f"probe: dropped={d}")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
