"""capture_formats.json, read back with a decoder written from the text (capture §1.3 / §1.4 / §3.8 / §3.9 / §4.4), not from the
generator: every stream gives back what its inputs say."""
import json
import struct
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = json.loads((ROOT / "tests/vectors/capture_formats.json").read_text())
REG = tomllib.loads((ROOT / "registry/oep-v1.toml").read_text())
IFACE = {i["name"]: i for i in REG["interface"]}


def bit(data: bytes, j: int) -> int:
    return (data[j // 8] >> (j % 8)) & 1


def uint(data: bytes, j: int, n: int) -> int:
    return sum(bit(data, j + k) << k for k in range(n))


def read_logic_segment(data: bytes, n: int, R: int, ds: list[int], L: int):
    """-> (raw levels per raw channel, per events channel a list of blocks' (start_level, fallback raw | events))."""
    E = len(ds)
    nb = (E + 7) // 8
    pos, raws, evs = 0, [[] for _ in range(R)], [[] for _ in range(E)]
    for first in range(0, n, L):
        r = min(L, n - first)
        fb = [bit(data[pos:pos + nb], e) for e in range(E)]
        start = [bit(data[pos + nb:pos + 2 * nb], e) for e in range(E)]
        count = struct.unpack_from("<I", data, pos + 2 * nb)[0]
        pos += 2 * nb + 4
        cols = list(range(R)) + [("fb", e) for e in range(E) if fb[e]]
        wb = len(cols)
        rb = (r * wb + 7) // 8
        raw = data[pos:pos + rb]
        pos += rb
        got = {e: [] for e in range(E)}
        for i in range(count):
            t, e, st = struct.unpack_from("<HBB", data, pos + 4 * i)
            got[e].append((t, st >> 7, st & 0x7F))
        pos += 4 * count
        for i in range(r):
            for k, c in enumerate(cols):
                v = bit(raw, i * wb + k)
                if isinstance(c, int):
                    raws[c].append(v)
                else:
                    evs[c[1]].append(("raw", v))
        for e in range(E):
            if not fb[e]:
                evs[e].append(("block", start[e], r, got[e]))
    assert pos == len(data)
    return raws, evs


def expect_ticks(levels: str, first: int, r: int, D: int, before: int):
    out, last = [], before
    for t in range((r + D - 1) // D):
        c = 0
        for i in range(t * D, min((t + 1) * D, r)):
            v = int(levels[first + i])
            c += v != last
            last = v
        if c:
            out.append((t, last, min(c, 127)))
    return out


def test_logic_blocks_read_back():
    for case in DATA["logic_blocks"]:
        L, R, ds = case["L"], case["R"], case["events_d"]
        prev_end = None
        for seg in case["segments"]:
            n = len((seg["raw"] + seg["events"])[0])
            raws, evs = read_logic_segment(bytes.fromhex(seg["stream_hex"]), n, R, ds, L)
            assert ["".join(map(str, r)) for r in raws] == seg["raw"], case["name"]
            for e, levels in enumerate(seg["events"]):
                before = prev_end[e] if seg["contiguous"] and prev_end else int(levels[0])
                first, items = 0, evs[e]
                k = 0
                while first < n:
                    r = min(L, n - first)
                    item = items[k]
                    if item[0] == "raw":
                        got = "".join(str(items[k + i][1]) for i in range(r))
                        assert got == levels[first:first + r], case["name"]
                        k += r
                    else:
                        _, start, rr, ticks = item
                        assert start == before and rr == r, case["name"]
                        assert ticks == expect_ticks(levels, first, r, ds[e], before), case["name"]
                        assert len(ticks) * 4 <= L // 8, f"{case['name']}: fallback was required"
                        k += 1
                    before = int(levels[first + r - 1])
                    first += r
            prev_end = [int(ch[-1]) for ch in seg["events"]]


def test_analog_blocks_read_back():
    for case in DATA["analog_blocks"]:
        data, b, L = bytes.fromhex(case["stream_hex"]), case["b"], case["L"]
        n, pos = len(case["channels"][0]), 0
        for first in range(0, n, L):
            r = min(L, n - first)
            for vals, kind, D in zip(case["channels"], case["kinds"], case["d"]):
                j = 0
                if kind == ["packed"]:
                    part = data[pos:pos + (r * b + 7) // 8]
                    assert [uint(part, i * b, b) for i in range(r)] == vals[first:first + r]
                    pos += (r * b + 7) // 8
                    continue
                sw = b + (D - 1).bit_length()
                per = (2 * b if "minmax" in kind else 0) + (sw if "sum" in kind else 0)
                k = (r + D - 1) // D
                part = data[pos:pos + (k * per + 7) // 8]
                for t in range(k):
                    seg = vals[first + t * D:first + min((t + 1) * D, r)]
                    if "minmax" in kind:
                        assert (uint(part, j, b), uint(part, j + b, b)) == (min(seg), max(seg))
                        j += 2 * b
                    if "sum" in kind:
                        assert uint(part, j, sw) == sum(seg)
                        j += sw
                pos += (k * per + 7) // 8
        assert pos == len(data), case["name"]


def test_state_timed_escape_is_not_a_sample():
    for case in DATA["state_timed"]:
        data, stride = bytes.fromhex(case["stream_hex"]), 4 + (case["w"] + 7) // 8
        deltas = [struct.unpack_from("<I", data, i)[0] for i in range(0, len(data), stride)]
        assert sum(d != 0xFFFFFFFF for d in deltas) == case["samples"]


def test_external_marks_and_headers():
    mark, chunk, pkt = DATA["external"]
    raw = bytes.fromhex(mark["bytes_hex"])
    assert len(raw) == 16 and raw[:4] == b"OEPX" and struct.unpack_from("<IHB", raw, 4) == (mark["generation"], mark["fn"], mark["format"])
    raw = bytes.fromhex(chunk["bytes_hex"])
    fn, ln = struct.unpack_from("<HH", raw)
    assert fn == chunk["fn"] and raw[4:4 + ln].hex() == chunk["data_hex"]
    raw = bytes.fromhex(pkt["bytes_hex"])
    assert struct.unpack_from("<QIHH", raw) == (pkt["position"], pkt["generation"], pkt["fn"], 0) and raw[16:].hex() == pkt["data_hex"]


def test_trigger_expressions_one_instant_per_term():
    group = IFACE["oep.fixture.capture-group"]
    bt, ce = group["tlv"]["bind"], group["enum"]["trigger_cond"]
    instant = {ce[k] for k in ("edge", "cross_up", "cross_down", "pulse", "analog_pulse", "timer", "serial")}
    crit = REG["constants"]["tag_critical"]
    for case in DATA["trigger_expressions"]:
        raw, pos, terms = bytes.fromhex(case["bind_tlvs_hex"]), 0, {}
        while pos < len(raw):
            tag, ln = raw[pos], struct.unpack_from("<H", raw, pos + 1)[0]
            v = raw[pos + 3:pos + 3 + ln]
            assert tag & crit, "every expression TLV is sent critical (§4.4)"
            if tag & 0x7F == bt["cond"]:
                stage, part, term, _src, _fn, _role, ctype = struct.unpack_from("<BBBBHBB", v)
                terms.setdefault((stage, part, term), []).append(ctype)
            pos += 3 + ln
        ok = all(sum(t in instant for t in ts) <= 1 for ts in terms.values())
        assert ok == case["accepted"], case["name"]
