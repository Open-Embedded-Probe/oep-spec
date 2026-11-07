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


BITS = {"sample": 1, "any_high": 1, "any_low": 1, "change_latch": 2}


def read_logic_segment(data: bytes, n: int, R: int, kinds: list[str], ds: list[int], L: int):
    """-> (raw levels per raw channel (w = R), per reduced channel its values in interval order, per block the starts)."""
    pos, raws, vals, starts = 0, [[] for _ in range(R)], [[] for _ in kinds], []
    for first in range(0, n, L):
        r = min(L, n - first)
        rb = (r * R + 7) // 8
        raw = data[pos:pos + rb]
        pos += rb
        for i in range(r):
            for c in range(R):
                raws[c].append(bit(raw, i * R + c))
        counts = [(r + d - 1) // d for d in ds]
        S = kinds.count("change_latch")
        total = S + sum(k * BITS[kind] for k, kind in zip(counts, kinds))
        red = data[pos:pos + (total + 7) // 8]
        pos += (total + 7) // 8
        starts.append([bit(red, i) for i in range(S)])
        off = S
        for c, (kind, k) in enumerate(zip(kinds, counts)):
            b = BITS[kind]
            for j in range(k):
                vals[c].append(uint(red, off + j * b, b))
            off += k * b
    assert pos == len(data)
    return raws, vals, starts


def expect_values(kind: str, levels: str, D: int, before):
    """The values capture §1.3 gives a segment's channel (before: the level before the segment, or None)."""
    out, last = [], before
    for lo in range(0, len(levels), D):
        seg = [int(v) for v in levels[lo:lo + D]]
        if kind == "sample":
            out.append(seg[0])
        elif kind == "any_high":
            out.append(int(1 in seg))
        elif kind == "any_low":
            out.append(0 if 0 in seg else 1)
        else:
            ch = 0
            for v in seg:
                ch |= last is not None and v != last
                last = v
            out.append(seg[-1] | (ch << 1))
    return out


def test_logic_blocks_read_back():
    for case in DATA["logic_blocks"]:
        L, R, kinds, ds = case["L"], case["R"], case["kinds"], case["d"]
        assert set(kinds) <= set(IFACE["oep.fixture.logic"]["enum"]["logic_carriage"]), case["name"]
        prev_end = None
        for seg in case["segments"]:
            n = len((seg["raw"] + seg["reduced"])[0])
            raws, vals, starts = read_logic_segment(bytes.fromhex(seg["stream_hex"]), n, R, kinds, ds, L)
            assert ["".join(map(str, r)) for r in raws] == seg["raw"], case["name"]
            assert vals == seg["values"], case["name"]
            for c, levels in enumerate(seg["reduced"]):
                before = prev_end[c] if seg["contiguous"] and prev_end else None
                assert vals[c] == expect_values(kinds[c], levels, ds[c], before), case["name"]
                if kinds[c] == "change_latch":   # each block's start, and the bits' relation read from it alone
                    s_idx = [i for i, k in enumerate(kinds) if k == "change_latch"].index(c)
                    for blk, first in enumerate(range(0, n, L)):
                        want = (before if before is not None else int(levels[0])) if first == 0 else int(levels[first - 1])
                        assert starts[blk][s_idx] == want, case["name"]
                        last = starts[blk][s_idx]
                        per = L // ds[c]
                        for v in vals[c][blk * per:(blk + 1) * per]:
                            assert (v & 1) == last or v >> 1, case["name"]
                            last = v & 1
            prev_end = [int(ch[-1]) for ch in seg["reduced"]]


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
