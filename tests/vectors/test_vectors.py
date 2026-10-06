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
    """tag(u8) len(u16) value, the one TLV form (core §2.2)."""
    out, i = [], 0
    while i < len(data):
        tag, n = data[i], struct.unpack_from("<H", data, i + 1)[0]
        i += 3
        out.append((tag, data[i:i + n]))
        assert len(data[i:i + n]) == n
        i += n
    return out


# core §1.2 (and the 必須 column of core §12): fn 0's ops every probe offers; plan_apply / plan_release only with a plan role
REQUIRED_FN0_OPS = ("confirm", "list", "describe", "open", "end", "keepalive", "lock_state", "subscribe", "unsubscribe")


def ops_set(value: bytes) -> set[int]:
    """The ops a describe common tag ops declares (core §7.4): base(u8), bitmap."""
    base = value[0]
    return {base + i for i in range(8 * (len(value) - 1)) if value[1 + i // 8] >> (i % 8) & 1}


def test_ops_examples_of_the_text():
    """core §7.4: riscv-dm with every op is 09 02 00 01 FF; with dmi, halt and resume only, 09 02 00 01 07."""
    ((tag, v),) = tlvs(bytes.fromhex("09020001ff"))
    assert tag == REG["describe_common"]["ops"] and ops_set(v) == set(range(1, 9))
    assert ops_set(tlvs(bytes.fromhex("0902000107"))[0][1]) == {1, 2, 3}


def test_crc_check_values_match_the_text():
    cases = {c["name"]: c for c in load("checks.json")["cases"]}
    digits = b"123456789"
    assert cases["crc16 123456789"]["crc"] == binascii.crc_hqx(digits, 0xFFFF) == 0x29B1      # transports §1
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
        role, corr, fn, op, session = struct.unpack_from("<BHHBI", msg)                        # one 10-byte header (core §4.1)
        assert (role, corr, fn, op, session) == (r["role"], r["corr"], r["fn"], r["op"], r["session_id"]) and role == 0x01
        assert msg[10:].hex() == r["payload_hex"]
    assert {r["session_id"] == 0 for r in v["requests"]} == {True, False}
    for a in v["answers"]:
        msg = bytes.fromhex(a["message_hex"])
        assert struct.unpack_from("<BHBB", msg) == (a["role"], a["corr"], a["resolution"], a["detail"])
        assert msg[5:].hex() == a["payload_hex"]
    for t in v["tlvs"]:
        ((tag, value),) = tlvs(bytes.fromhex(t["tlv_hex"]))
        assert tag == t["tag"]
        assert value == (bytes.fromhex(t["value_hex"]) if "value_hex" in t else bytes([t["value_byte"]]) * t["value_len"])
        assert len(bytes.fromhex(t["tlv_hex"])) == 3 + len(value)                              # one form, whatever the length


def test_confirm_exchanges():
    confirm_op = next(o["code"] for o in REG["interface"][0]["op"] if o["name"] == "confirm")
    ok, refused = load("confirm.json")["exchanges"]
    req = bytes.fromhex(ok["request_hex"])
    assert struct.unpack_from("<BHHBI", req) == (0x01, ok["request"]["corr"], 0, confirm_op, 0)
    assert req[10:] == b"OEP?" + bytes([ok["request"]["min_rev"], ok["request"]["max_rev"]])
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
            if tag == 0x01:
                return (tag,) + struct.unpack_from("<HBH", v)                                 # plan: fn, role, channel
            if tag == 0x04:
                return (tag, v[0])                                                             # slot: slot(u8)
            return (tag,) + struct.unpack_from("<H", v)                                        # label, idle: channel

        for tag, v in sent:
            if tag & 0x7F == 0x03:
                assert len(v) == 6                                                             # idle: one fixed form (probe settings §1)
                if v[2] <= 2:
                    assert v[3:] == b"\x02\x00\x00"                                           # an input idle carries kind 2 (default), value 0

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
                assert bytes([marker]) in req[10:]
            tlvs(payload[1:])
        else:
            assert payload == b""


def test_discovery_exchanges():
    """list (core §7.2), describe (core §7.3, §7.5) and the header refusals (core §4.3 order 1) of the example probe."""
    core = REG["interface"][0]
    ops = {o["name"]: o["code"] for o in core["op"]}
    v = load("discovery.json")
    lst, desc, past = v["exchanges"]
    for ex in v["exchanges"]:
        req, ans = bytes.fromhex(ex["request_hex"]), bytes.fromhex(ex["answer_hex"])
        assert req[0] == 0x01 and struct.unpack_from("<H", req, 1)[0] == ex["request"]["corr"]   # no lock needed (core §12)
        assert struct.unpack_from("<I", req, 6)[0] == 0                                          # session_id 0: no session (core §4.1)
        assert struct.unpack_from("<BHBB", ans) == (0x02, ex["answer"]["corr"], 0x01, 0)
        for key in ("request", "answer"):
            if f"{key}_serial_frame_hex" in ex:
                assert unframe_serial(bytes.fromhex(ex[f"{key}_serial_frame_hex"])) == bytes.fromhex(ex[f"{key}_hex"])

    req, ans = bytes.fromhex(lst["request_hex"]), bytes.fromhex(lst["answer_hex"])
    assert struct.unpack_from("<HB", req, 3) == (0, ops["list"])
    flags, first, plen = struct.unpack_from("<BHB", req, 10)
    assert (flags, first, plen) == (0, 0, 0) and len(req) == 14
    total, count = struct.unpack_from("<HB", ans, 5)
    i, entries = 8, []
    for _ in range(count):                                                                     # count x entry, no element len
        fn, inst, rev, eflags, nlen = struct.unpack_from("<HHBBB", ans, i)
        entries.append({"fn": fn, "instance": inst, "revision": rev, "flags": eflags,
                        "name": ans[i + 7:i + 7 + nlen].decode()})
        i += 7 + nlen
    assert i == len(ans) and total == len(entries) and entries == lst["answer"]["entries"]
    assert entries[0] == {"fn": 0, "instance": 0, "revision": core["revision"], "flags": 0, "name": "oep.core"}

    req, ans = bytes.fromhex(desc["request_hex"]), bytes.fromhex(desc["answer_hex"])
    assert struct.unpack_from("<HB", req, 3) == (0, ops["describe"]) and struct.unpack_from("<HH", req, 10) == (0, 0)
    assert len(req) == 14                                                                      # no TLV (core §7.3)
    assert ans[5] == desc["answer"]["more"] == 0
    t = core["tlv"]["describe"]
    got = tlvs(ans[6:])
    ops_tag = REG["describe_common"]["ops"]
    assert [tag for tag, _ in got] == [ops_tag, t["unit_id"], t["transport"], t["discoverable"], t["max_op_ms"]]
    offered = ops_set(got[0][1])
    assert sorted(offered) == desc["answer"]["ops"] and offered == {ops[n] for n in REQUIRED_FN0_OPS}   # core §1.2, no plan role
    got = got[1:]
    uid = got[0][1].decode()
    assert uid == desc["answer"]["unit_id"] and 1 <= len(uid) <= 32 and set(uid) <= set("abcdefghijklmnopqrstuvwxyz0123456789-")
    tr = desc["answer"]["transports"][0]
    assert got[1][1] == bytes([tr["index"], tr["kind"], tr["interface"]])
    assert tr["kind"] == core["enum"]["transport_kind"]["uart_bridge"]
    assert got[2][1] == bytes([desc["answer"]["discoverable"]])
    assert struct.unpack("<I", got[3][1])[0] == desc["answer"]["max_op_ms"]
    assert t["unit_id"] != 0x3F and t["transport"] != 0x3F

    req, ans = bytes.fromhex(past["request_hex"]), bytes.fromhex(past["answer_hex"])
    assert struct.unpack_from("<HH", req, 10) == (0, past["request"]["first"]) and past["request"]["first"] >= len(got) + 1
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
            assert fn == 0 and op not in defined and op not in offered                         # not set in ops (core §1.2)


def test_example_probe_answers_carry_what_the_core_requires():
    """Every completed confirm answer of the example probe carries TLV 0x01 transport (core §7.1), and its describe of
    fn 0 carries unit_id, transport and max_op_ms (core §1.2) and discoverable (core §7.5: 0 for a probe that does not
    enumerate with the project's USB VID:PID, as a UART bridge does not), with every op core §1.2 requires of fn 0 set in ops."""
    core = REG["interface"][0]
    t_confirm = core["tlv"]["confirm_answer"]["transport"]
    t = core["tlv"]["describe"]
    uart_bridge = core["enum"]["transport_kind"]["uart_bridge"]
    confirm_op = next(o["code"] for o in core["op"] if o["name"] == "confirm")
    describe_op = next(o["code"] for o in core["op"] if o["name"] == "describe")

    exchanges = [ex for name in ("confirm.json", "discovery.json") for ex in load(name)["exchanges"]]
    exchanges += load("refusals.json")["cases"]
    confirms = describes = 0
    for ex in exchanges:
        req, ans = bytes.fromhex(ex["request_hex"]), bytes.fromhex(ex["answer_hex"])
        if ans[3] != 0x01:                                                                     # only completed answers
            continue
        fn, op = struct.unpack_from("<HB", req, 3)
        if fn == 0 and op == confirm_op:
            confirms += 1
            got = dict(tlvs(ans[5 + 4 + 13:]))
            assert len(got.get(t_confirm, b"")) == 1, ex["name"]                              # core §7.1 "always attaches"
        elif fn == 0 and op == describe_op and struct.unpack_from("<H", req, 12)[0] == 0:
            describes += 1
            got = tlvs(ans[6:])
            tags = [tag for tag, _ in got]
            for name in ("unit_id", "transport", "max_op_ms", "discoverable"):
                assert t[name] in tags, (ex["name"], name)
            assert tags.count(REG["describe_common"]["ops"]) == 1, ex["name"]                  # every fn's describe (core §1.2)
            declared = ops_set(dict(got)[REG["describe_common"]["ops"]])                           # base(u8), bitmap (core §7.4)
            required = {o["code"] for o in core["op"] if o["name"] in REQUIRED_FN0_OPS}
            assert required <= declared, (ex["name"], sorted(required - declared))            # core §1.2: every required op is set
            assert tags.count(t["discoverable"]) == 1 and tags.count(t["max_op_ms"]) == 1
            kinds = [v[1] for tag, v in got if tag == t["transport"]]
            if all(k == uart_bridge for k in kinds):                                       # no USB port of its own
                assert dict(got)[t["discoverable"]] == b"\x00", ex["name"]
            ms = struct.unpack("<I", dict(got)[t["max_op_ms"]])[0]
            assert 1 <= ms <= REG["limits"]["max_op_ms_max"]
            restart = next(o["code"] for o in core["op"] if o["name"] == "restart")
            if restart in declared:                                                        # core §6.6, §7.5: required with restart
                assert tags.count(t["restart_max_ms"]) == 1, ex["name"]
                assert struct.unpack("<I", dict(got)[t["restart_max_ms"]])[0] >= REG["limits"]["restart_after_answer_ms"]
            else:                                                                          # a probe without restart does not send it
                assert t["restart_max_ms"] not in tags, ex["name"]
    assert confirms >= 1 and describes >= 1


def test_the_tool_still_gives_these_files():
    spec = importlib.util.spec_from_file_location("oepvectors1", ROOT / "tools" / "oepvectors1.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    for name, build in tool.FILES.items():
        assert (HERE / name).read_text(encoding="utf-8") == tool.render(build), name


def test_session_scenarios_follow_the_decision_table():
    """sessions.json (core §5.2, §6.2, §9): every step is one 10-byte-header request and its answer with the same corr; a resent request
    gets the same answer bytes; after end, the ended id is no_session; force hands the lock over."""
    reasons = {v: k for k, v in REG["reject_reasons"].items()}
    ops = {o["name"]: o["code"] for o in REG["interface"][0]["op"]}
    for sc in load("sessions.json")["scenarios"]:
        seen = {}
        ended = set()
        for st in sc["steps"]:
            req, ans = bytes.fromhex(st["request_hex"]), bytes.fromhex(st["answer_hex"])
            role, corr, fn, op, session = struct.unpack_from("<BHHBI", req)
            assert role == 0x01 and fn == 0 and ans[0] == 0x02 and ans[1:3] == req[1:3], st["note"]
            if req in seen:                                                                   # a resend: the same answer
                assert seen[req] == ans, st["note"]
            seen[req] = ans
            outcome = "completed" if ans[3] == 0x01 else reasons[ans[4]]
            if op == ops["open"]:
                assert len(req) >= 15                                                         # lease_ms(u32) force(u8) [TLV]
                if session == 0:
                    assert outcome == "malformed"
                if outcome == "completed":
                    assert len(ans) == 5 + 8                                                  # lease_ms(u32) boot_id(u32), no resumed
                    ended.discard(session)
            elif op == ops["end"] and outcome == "completed":
                ended.add(session)
            elif session in ended and op != ops["end"]:
                assert outcome in ("no_session", "locked"), st["note"]                       # nothing is resumed (core §6.4)
            if op == ops["keepalive"] and session == 0:
                assert outcome == "session_required"
            if outcome == "locked":
                assert len(ans) >= 9                                                          # remaining_ms(u32), [TLV owner]
                tlvs(ans[9:])


def _fixed_sequence(payload: bytes, size_of) -> int:
    """Walk count x element (core §2.3) and return the bytes used; size_of(payload, offset) is one element's size."""
    count, i = payload[0], 1
    for _ in range(count):
        i += size_of(payload, i)
    return i


def test_per_op_vectors_decode_exactly():
    """ops.json: every answer carries the request's corr, and the sequences of the answers are count x element with no element length,
    each element as its document gives it, the payload used to its end (core §2.3)."""
    v = load("ops.json")["cases"]
    by = {c["name"]: c for c in v}
    for c in v:
        req, ans = bytes.fromhex(c["request_hex"]), bytes.fromhex(c["answer_hex"])
        assert len(req) >= 10 and req[0] == 0x01 and ans[0] == 0x02 and ans[1:3] == req[1:3], c["name"]
        if ans[3] == 0x00:
            assert ans[4] in REG["reject_reasons"].values(), c["name"]
            if ans[4] == REG["reject_reasons"]["unavailable"]:
                tlvs(ans[5:])

    def pay(name):
        return bytes.fromhex(by[name]["answer_hex"])[5:]

    core = next(i for i in REG["interface"] if i["name"] == "oep.core")
    restart = next(o["code"] for o in core["op"] if o["name"] == "restart")
    for name in ("core restart: completed success, sent before the probe restarts", "core restart without a session: session_required",
                 "core restart while no session holds the lock: no_session", "core restart not offered (not set in ops)"):
        req = bytes.fromhex(by[name]["request_hex"])
        assert struct.unpack_from("<HB", req, 3) == (0, restart) and len(req) == 10, name              # fn 0, no fixed part (core §6.6)
    assert pay("core restart: completed success, sent before the probe restarts") == b""                 # completed success, no payload
    p = pay("rvswd connections: one connection with a target_id")
    assert p[0] == 0 and 1 + _fixed_sequence(p[1:], lambda b, i: 18 + b[i + 17]) == len(p)        # entry 18 bytes + tid
    p = pay("rvswd scan: one combination listed and found")
    assert p[0] == 1 and 1 + _fixed_sequence(p[1:], lambda b, i: 9) == len(p)                       # kind swdio swclk id
    assert pay("rvswd scan: count 0 with nothing left from skip") == b"\x00\x00"                  # tried 0, count 0 (debug §1)
    p = pay("console marks: one attach mark")
    assert 1 + _fixed_sequence(p[1:], lambda b, i: 22) == len(p)
    p = pay("console streams: one open stream")
    assert 1 + _fixed_sequence(p[1:], lambda b, i: 7) == len(p)
    p = pay("logic segments: one segment")
    assert 1 + _fixed_sequence(p[1:], lambda b, i: 37) == len(p)
    p = pay("probe.config state: one slot and one bind")
    i = 7                                                                                         # more state hash(u32) reason
    i += _fixed_sequence(p[i:], lambda b, j: 22 + b[j + 21])                                      # slot_state: 22 bytes + tid
    i += _fixed_sequence(p[i:], lambda b, j: 4)                                                   # bind_state
    assert i == len(p)
    p = pay("link source: 8 bytes, byte k = k & 0xFF")
    n = struct.unpack_from("<H", p)[0]
    assert p[2:2 + n] == bytes(k & 0xFF for k in range(n)) and len(p) == 2 + n
    p = pay("link source: more than fits, len = max_frame - 26")                                 # max_frame 1024 (oep-if-link §2)
    n = struct.unpack_from("<H", p)[0]
    assert n == 1024 - 5 - 2 - 19 == 1024 - REG["limits"]["link_source_overhead_bytes"]            # header, len, room for ignored (core §2.3)
    assert p[2:] == bytes(k & 0xFF for k in range(n))
