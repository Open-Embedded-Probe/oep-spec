"""The test vectors of tests/vectors/ agree with themselves and with the rules of the text.

The checks here use other code than tools/oepvectors1.py where Python has it (binascii, zlib) and decode what the tool
encoded, so a mistake in the tool does not pass unseen. The last test runs the tool's --check.
"""

import binascii
import importlib.util
import json
import struct
import tomllib
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REG = tomllib.loads((ROOT / "registry" / "oep-v1.toml").read_text(encoding="utf-8"))


def load(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def crc8_table() -> list[int]:
    table = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = ((c << 1) ^ 0x07) & 0xFF if c & 0x80 else (c << 1) & 0xFF
        table.append(c)
    return table


CRC8 = crc8_table()


def crc8(data: bytes) -> int:
    c = 0xFF
    for b in data:
        c = CRC8[c ^ b]
    return c


def cobs_decode(raw: bytes) -> bytes:
    out, i = bytearray(), 0
    while i < len(raw):
        code = raw[i]
        assert code != 0 and i + code <= len(raw), "COBS block runs past the end"
        out += raw[i + 1:i + code]
        i += code
        if code != 0xFF and i < len(raw):
            out.append(0)
    return bytes(out)


def unframe_serial(frame: bytes) -> bytes:
    assert frame[0] == 0 and frame[-1] == 0 and 0 not in frame[1:-1]
    data = cobs_decode(frame[1:-1])
    body, crc = data[:-2], struct.unpack("<H", data[-2:])[0]
    assert binascii.crc_hqx(body, 0xFFFF) == crc
    return body


def tlvs(data: bytes) -> list[tuple[int, bytes]]:
    out, i = [], 0
    while i < len(data):
        tag, n = data[i], data[i + 1]
        i += 2
        if n == 0xFF:
            n = struct.unpack_from("<H", data, i)[0]
            i += 2
            assert n >= 255, "long form used for a short value"
        out.append((tag, data[i:i + n]))
        assert len(data[i:i + n]) == n
        i += n
    return out


def test_crc_check_values_match_the_text():
    cases = {c["name"]: c for c in load("checks.json")["cases"]}
    digits = b"123456789"
    assert cases["crc16 123456789"]["crc"] == binascii.crc_hqx(digits, 0xFFFF) == 0x29B1      # core §3.1
    assert cases["crc32 123456789"]["crc"] == zlib.crc32(digits) == 0xCBF43926                # core §5.2
    assert cases["crc8 123456789"]["crc"] == crc8(digits) == 0xFB                             # dmseq CRC-8
    assert cases["crc8 one zero byte"]["crc"] == crc8(b"\x00") == 0xF3
    for c in cases.values():
        assert bytes.fromhex(c["input_hex"]) in (digits, b"\x00")


def test_dmseq_example_words_match_the_text():
    words = load("checks.json")["dmseq_words"]
    for w in words:
        assert w["crc"] == crc8(bytes([w["byte0"]]) + bytes.fromhex(w["payload_hex"]))
        assert w["data0"] == w["byte0"] | w["crc"] << 8
    assert [w["data0"] for w in words] == [0x00003298, 0x0000F300]                           # dmseq "Byte order"
    assert words[0]["byte0"] == 0x80 | 0x10 | 0x08                                             # T, A = 1, SYN; S = 0, N = 0


def test_cobs_vectors_decode_back():
    v = load("cobs.json")
    for c in v["encode"] + v["decode_also_accepts"]:
        assert cobs_decode(bytes.fromhex(c["encoded_hex"])) == bytes.fromhex(c["data_hex"]), c["name"]
    for c in v["encode"]:
        enc = bytes.fromhex(c["encoded_hex"])
        assert 0 not in enc
        data = bytes.fromhex(c["data_hex"])
        if len(data) == 254 and 0 not in data:
            assert enc[0] == 0xFF and len(enc) == 255                                          # no empty block after it
    for f in v["frames"]:
        frame = bytes.fromhex(f["frame_hex"])
        assert unframe_serial(frame) == bytes.fromhex(f["message_hex"])
        assert binascii.crc_hqx(bytes.fromhex(f["message_hex"]), 0xFFFF) == f["crc16"]


def test_headers_parse_to_their_fields():
    v = load("headers.json")
    for r in v["requests"]:
        msg = bytes.fromhex(r["message_hex"])
        role, corr, fn, op = struct.unpack_from("<BHHB", msg)
        assert (role, corr, fn, op) == (r["role"], r["corr"], r["fn"], r["op"])
        if role & 0x80:
            assert struct.unpack_from("<I", msg, 6)[0] == r["session_id"] and msg[10:].hex() == r["payload_hex"]
        else:
            assert r["session_id"] is None and msg[6:].hex() == r["payload_hex"]
    for a in v["answers"]:
        msg = bytes.fromhex(a["message_hex"])
        assert struct.unpack_from("<BHBB", msg) == (a["role"], a["corr"], a["resolution"], a["detail"])
        assert msg[5:].hex() == a["payload_hex"]
    for t in v["tlvs"]:
        ((tag, value),) = tlvs(bytes.fromhex(t["tlv_hex"]))
        assert tag == t["tag"]
        assert value == (bytes.fromhex(t["value_hex"]) if "value_hex" in t else bytes([t["value_byte"]]) * t["value_len"])
        assert (bytes.fromhex(t["tlv_hex"])[1] == 0xFF) == (len(value) >= 255)                 # the unique encoding


def test_confirm_exchanges():
    confirm_op = next(o["code"] for o in REG["interface"][0]["op"] if o["name"] == "confirm")
    ok, refused = load("confirm.json")["exchanges"]
    req = bytes.fromhex(ok["request_hex"])
    assert struct.unpack_from("<BHHB", req) == (0x01, ok["request"]["corr"], 0, confirm_op)
    assert req[6:] == b"OEP?" + bytes([ok["request"]["min_rev"], ok["request"]["max_rev"]])
    assert unframe_serial(bytes.fromhex(ok["request_serial_frame_hex"])) == req
    lf = bytes.fromhex(ok["request_length_frame_hex"])
    assert struct.unpack_from("<H", lf)[0] == len(req) and lf[2:] == req
    ans = bytes.fromhex(ok["answer_hex"])
    assert unframe_serial(bytes.fromhex(ok["answer_serial_frame_hex"])) == ans
    assert struct.unpack_from("<BHBB", ans) == (0x02, 1, 0x01, 0)
    a = ok["answer"]
    assert ans[5:9] == b"OEP!"
    assert struct.unpack_from("<BBHIBI", ans, 9) == (a["revision"], a["flags"], a["max_frame"], a["window"], a["max_inflight"], a["boot_id"])
    assert tlvs(ans[9 + 13:]) == [(0x01, bytes([a["transport"]]))]
    assert len(req) <= REG["constants"]["min_max_frame"] and len(ans) <= REG["constants"]["min_max_frame"]   # core §7.1
    ans = bytes.fromhex(refused["answer_hex"])
    assert struct.unpack_from("<BHBB", ans) == (0x02, 2, 0x00, REG["reject_reasons"]["unsupported"])
    assert ans[5] == 0x00 and tlvs(ans[6:]) == [(0x01, bytes(refused["answer"]["supported"]))]


def test_probe_config_canonical_form_and_hash():
    for case in load("probe_config_hash.json")["cases"]:
        sent = [(i["tag"], bytes.fromhex(i["value_hex"])) for i in case["items_sent"]]

        def key(item):
            tag, v = item
            fields = struct.unpack_from("<HBH", v) if tag == 0x01 else struct.unpack_from("<H", v)
            return (tag,) + fields

        order = sorted(((t & 0x7F, v) for t, v in sent), key=key)
        assert [(i["tag"], i["value_hex"]) for i in case["canonical_order"]] == [(t, v.hex()) for t, v in order]
        canonical = bytes.fromhex(case["canonical_hex"])
        assert tlvs(canonical) == order
        assert case["hash"] == zlib.crc32(canonical)


def test_refusals_answer_their_requests():
    reasons = REG["reject_reasons"]
    for c in load("refusals.json")["cases"]:
        req, ans = bytes.fromhex(c["request_hex"]), bytes.fromhex(c["answer_hex"])
        assert ans[0] == 0x02 and ans[1:3] == req[1:3], c["name"]                                 # same corr
        payload = ans[5:]
        if c["answer"] == "completed success":
            assert ans[3:5] == bytes([0x01, 0x00])
            ignored = dict(tlvs(payload))[0x7F]
            assert all(tag & 0x80 == 0 for tag in ignored)
            continue
        assert ans[3] == 0x00 and ans[4] == reasons[c["answer"]], c["name"]
        if c["answer"] == "unsupported":
            marker = payload[0]
            assert marker == 0x00 or marker & 0x80, "the tag as received of a critical TLV, or 0x00"
            if marker:
                body = req[10:] if req[0] & 0x80 else req[6:]
                assert bytes([marker]) in body
            tlvs(payload[1:])
        else:
            assert payload == b""


def test_discovery_exchanges():
    """list (core §7.2), describe (core §7.3, §7.5) and the header refusals (core §4.3 order 1) of the smallest probe."""
    core = REG["interface"][0]
    ops = {o["name"]: o["code"] for o in core["op"]}
    v = load("discovery.json")
    lst, desc, past = v["exchanges"]
    for ex in v["exchanges"]:
        req, ans = bytes.fromhex(ex["request_hex"]), bytes.fromhex(ex["answer_hex"])
        assert req[0] == 0x01 and struct.unpack_from("<H", req, 1)[0] == ex["request"]["corr"]   # no lock needed (core §12)
        assert struct.unpack_from("<BHBB", ans) == (0x02, ex["answer"]["corr"], 0x01, 0)
        for key in ("request", "answer"):
            if f"{key}_serial_frame_hex" in ex:
                assert unframe_serial(bytes.fromhex(ex[f"{key}_serial_frame_hex"])) == bytes.fromhex(ex[f"{key}_hex"])

    req, ans = bytes.fromhex(lst["request_hex"]), bytes.fromhex(lst["answer_hex"])
    assert struct.unpack_from("<HB", req, 3) == (0, ops["list"])
    flags, first, plen = struct.unpack_from("<BHB", req, 6)
    assert (flags, first, plen) == (0, 0, 0) and len(req) == 10
    total, count = struct.unpack_from("<HB", ans, 5)
    i, entries = 8, []
    for _ in range(count):
        n = ans[i]
        fn, inst, rev, eflags, nlen = struct.unpack_from("<HHBBB", ans, i + 1)
        entries.append({"fn": fn, "instance": inst, "revision": rev, "flags": eflags,
                        "name": ans[i + 8:i + 8 + nlen].decode()})
        assert n == 7 + nlen
        i += 1 + n
    assert i == len(ans) and total == len(entries) and entries == lst["answer"]["entries"]
    assert entries[0] == {"fn": 0, "instance": 0, "revision": core["revision"], "flags": 0, "name": "oep.core"}

    req, ans = bytes.fromhex(desc["request_hex"]), bytes.fromhex(desc["answer_hex"])
    assert struct.unpack_from("<HB", req, 3) == (0, ops["describe"]) and struct.unpack_from("<HH", req, 6) == (0, 0)
    assert len(req) == 10                                                                      # no TLV (core §7.3)
    assert ans[5] == desc["answer"]["more"] == 0
    t = core["tlv"]["describe"]
    got = tlvs(ans[6:])
    assert [tag for tag, _ in got] == [t["unit_id"], t["transport"], t["max_op_ms"]]          # the mandatory three (core §1.2)
    uid = got[0][1].decode()
    assert uid == desc["answer"]["unit_id"] and 1 <= len(uid) <= 32 and set(uid) <= set("abcdefghijklmnopqrstuvwxyz0123456789-")
    tr = desc["answer"]["transports"][0]
    assert got[1][1] == bytes([tr["index"], tr["kind"], tr["interface"]])
    assert tr["kind"] == core["enum"]["transport_kind"]["uart_bridge"]
    assert struct.unpack("<I", got[2][1])[0] == desc["answer"]["max_op_ms"]
    assert t["unit_id"] != 0x3F and t["transport"] != 0x3F

    req, ans = bytes.fromhex(past["request_hex"]), bytes.fromhex(past["answer_hex"])
    assert struct.unpack_from("<HH", req, 6) == (0, past["request"]["first"]) and past["request"]["first"] >= len(got)
    assert ans[5:] == b"\x00"                                                                 # more 0, no TLVs (core §7.3)

    reasons = REG["reject_reasons"]
    defined = {o["code"] for o in core["op"]}
    for c in v["refusals"]:
        req, ans = bytes.fromhex(c["request_hex"]), bytes.fromhex(c["answer_hex"])
        corr, fn, op = struct.unpack_from("<HHB", req, 1)
        assert (corr, fn, op) == (c["request"]["corr"], c["request"]["fn"], c["request"]["op"]) and req[0] == 0x01
        assert ans == struct.pack("<BHBB", 0x02, corr, 0x00, reasons[c["answer"]])           # no payload (core §4.3)
        if c["answer"] == "unknown_function":
            assert fn not in [e["fn"] for e in entries]
        else:
            assert fn == 0 and op not in defined


def test_the_tool_still_gives_these_files():
    spec = importlib.util.spec_from_file_location("oepvectors1", ROOT / "tools" / "oepvectors1.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    for name, build in tool.FILES.items():
        assert (HERE / name).read_text(encoding="utf-8") == tool.render(build), name
