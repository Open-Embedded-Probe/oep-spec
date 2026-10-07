"""The test vectors of tests/vectors/ agree with themselves and with the rules of the text.

The checks here use other code than tools/oepvectors1.py where Python has it (binascii) and decode what the tool
encoded, so a mistake in the tool does not pass unseen. The last test runs the tool's --check.
"""

import binascii
import importlib.util
import json
import struct
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REG = tomllib.loads((ROOT / "registry" / "oep-v1.toml").read_text(encoding="utf-8"))
CORE = REG["core"]                  # fn 0: the core has no name and is not in list (core §0)


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
REQUIRED_FN0_OPS = ("confirm", "list", "describe", "clock", "open", "end", "keepalive", "lock_state")


def ops_set(value: bytes) -> set[int]:
    """The ops a describe common tag ops declares (core §7.4): base(u8), bitmap."""
    base = value[0]
    return {base + i for i in range(8 * (len(value) - 1)) if value[1 + i // 8] >> (i % 8) & 1}


def test_ops_examples_of_the_text():
    """core §7.4: riscv-dm with every op is 09 02 00 01 FF; with dmi, halt and resume only, 09 02 00 01 07."""
    ((tag, v),) = tlvs(bytes.fromhex("09020001ff"))
    assert tag == REG["describe_common"]["ops"] and ops_set(v) == set(range(1, 9))
    assert ops_set(tlvs(bytes.fromhex("0902000107"))[0][1]) == {1, 2, 3}


def valid_ops(value: bytes) -> bool:
    """core §7.4, written out separately from the tool: base and a bitmap of 1 byte or more, not past op 0xFF."""
    if len(value) < 2:
        return False
    nbytes = len(value) - 1
    return value[0] + 8 * nbytes <= 0x100


def test_ops_encoding_boundaries():
    """ops_encoding.json: valid values decode to their set; invalid ones break the length or the 0xFF bound (core §7.4)."""
    cases = load("ops_encoding.json")["cases"]
    assert {c["valid"] for c in cases} == {True, False}
    for c in cases:
        v = bytes.fromhex(c["value_hex"])
        assert valid_ops(v) == c["valid"], c["name"]
        if not c["valid"]:
            assert c["ops"] is None
            continue
        assert sorted(ops_set(v)) == c["ops"], c["name"]
    lengths = {len(bytes.fromhex(c["value_hex"])) for c in cases}
    assert {2, 33, 1, 34} <= lengths                                                             # both ends of 2-33 and just outside
    assert any(c["valid"] and int(c["value_hex"][:2], 16) + 8 * (len(c["value_hex"]) // 2 - 1) == 256 for c in cases)


def test_every_ops_in_the_vectors_is_valid():
    """Every describe in the vectors carries a valid ops (core §7.4)."""
    ops_tag = REG["describe_common"]["ops"]
    for name in ("discovery.json",):
        for ex in load(name)["exchanges"]:
            req, ans = bytes.fromhex(ex["request_hex"]), bytes.fromhex(ex["answer_hex"])
            if struct.unpack_from("<B", req, 5)[0] == next(o["code"] for o in CORE["op"] if o["name"] == "describe") and len(ans) > 6:
                for tag, value in tlvs(ans[6:]):
                    if tag == ops_tag:
                        assert valid_ops(value), ex["name"]


def test_crc_check_values_match_the_text():
    cases = {c["name"]: c for c in load("checks.json")["cases"]}
    digits = b"123456789"
    assert cases["crc16 123456789"]["crc"] == binascii.crc_hqx(digits, 0xFFFF) == 0x29B1      # transports §1
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
    confirm_op = next(o["code"] for o in CORE["op"] if o["name"] == "confirm")
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
    assert tlvs(ans[9 + 13:]) == [(0x01, bytes([a["transport"]]))]                                  # transport only (core §7.1); the time is clock's
    assert set(CORE["tlv"]["confirm_answer"]) == {"transport"}
    assert len(req) <= REG["constants"]["min_max_frame"] and len(ans) <= REG["constants"]["min_max_frame"]   # core §7.1
    ans = bytes.fromhex(refused["answer_hex"])
    assert struct.unpack_from("<BHBB", ans) == (0x02, 2, 0x00, REG["reject_reasons"]["unsupported"])
    assert ans[5] == 0x00 and tlvs(ans[6:]) == [(0x01, bytes(refused["answer"]["supported"]))]


def test_refusals_answer_their_requests():
    reasons = REG["reject_reasons"]
    for c in load("refusals.json")["cases"]:
        req, ans = bytes.fromhex(c["request_hex"]), bytes.fromhex(c["answer_hex"])
        assert ans[0] == 0x02 and ans[1:3] == req[1:3], c["name"]                                 # same corr
        payload = ans[5:]
        if c["answer"] == "completed success":
            assert ans[3:5] == bytes([0x01, 0x00]) and payload == b""                               # an unknown non-critical TLV is ignored (core §2.3)
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
    core = CORE
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
    assert struct.unpack_from("<H", req, 10)[0] == 0 and len(req) == 12                       # first(u16) only (core §7.2)
    total, count = struct.unpack_from("<HB", ans, 5)
    i, entries = 8, []
    for _ in range(count):                                                                     # count x entry, no element len
        fn, inst, rev, eflags, nlen = struct.unpack_from("<HHBBB", ans, i)
        entries.append({"fn": fn, "instance": inst, "revision": rev, "flags": eflags,
                        "name": ans[i + 7:i + 7 + nlen].decode()})
        i += 7 + nlen
    assert i == len(ans) and total == len(entries) and entries == lst["answer"]["entries"]
    assert entries == [] and total == 0                                                        # fn 0 is never listed (core §7.2)

    req, ans = bytes.fromhex(desc["request_hex"]), bytes.fromhex(desc["answer_hex"])
    assert struct.unpack_from("<HB", req, 3) == (0, ops["describe"]) and struct.unpack_from("<HH", req, 10) == (0, 0)
    assert len(req) == 14                                                                      # no TLV (core §7.3)
    assert ans[5] == desc["answer"]["more"] == 0
    t = core["tlv"]["describe"]
    got = tlvs(ans[6:])
    ops_tag = REG["describe_common"]["ops"]
    assert [tag for tag, _ in got] == [ops_tag, t["unit_id"], t["transport"], t["max_op_ms"]]
    offered = ops_set(got[0][1])
    assert sorted(offered) == desc["answer"]["ops"] and offered == {ops[n] for n in REQUIRED_FN0_OPS}   # core §1.2, no plan role
    got = got[1:]
    uid = got[0][1].decode()
    assert uid == desc["answer"]["unit_id"] and 1 <= len(uid) <= 32 and set(uid) <= set("abcdefghijklmnopqrstuvwxyz0123456789-")
    tr = desc["answer"]["transports"][0]
    assert got[1][1] == bytes([tr["index"], tr["kind"], tr["interface"]])
    assert tr["kind"] == core["enum"]["transport_kind"]["uart_bridge"]
    assert struct.unpack("<I", got[2][1])[0] == desc["answer"]["max_op_ms"]
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
    fn 0 carries unit_id, transport and max_op_ms (core §1.2), with every op core §1.2 requires of fn 0 set in ops."""
    core = CORE
    t_confirm = core["tlv"]["confirm_answer"]["transport"]
    t = core["tlv"]["describe"]
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
            for name in ("unit_id", "transport", "max_op_ms"):
                assert t[name] in tags, (ex["name"], name)
            assert tags.count(REG["describe_common"]["ops"]) == 1, ex["name"]                  # every fn's describe (core §1.2)
            declared = ops_set(dict(got)[REG["describe_common"]["ops"]])                           # base(u8), bitmap (core §7.4)
            required = {o["code"] for o in core["op"] if o["name"] in REQUIRED_FN0_OPS}
            assert required <= declared, (ex["name"], sorted(required - declared))            # core §1.2: every required op is set
            assert tags.count(t["max_op_ms"]) == 1
            ms = struct.unpack("<I", dict(got)[t["max_op_ms"]])[0]
            assert 1 <= ms <= REG["limits"]["max_op_ms_max"]
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
    ops = {o["name"]: o["code"] for o in CORE["op"]}
    assert ops["clock"] == 0x04 and not next(o["lock"] for o in CORE["op"] if o["name"] == "clock")     # core §12: no lock
    clocks = {"no session": 0, "held, session_id 0": 0, "held, its own id": 0}
    for sc in load("sessions.json")["scenarios"]:
        seen = {}
        ended = set()
        held = False
        last_uptime = -1
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
            if op == ops["clock"]:
                assert len(req) == 10, st["note"]                                                  # no fixed part (core §7.7)
                if session == 0:
                    assert outcome == "completed", st["note"]                                       # no session needed (core §4.1, §6.3)
                if outcome == "completed":
                    assert len(ans) == 5 + 12, st["note"]                                         # boot_id(u32) uptime_ns(u64)
                    boot_id, uptime = struct.unpack_from("<IQ", ans, 5)
                    assert boot_id == 0x12345678 and uptime >= last_uptime, st["note"]            # one boot: the clock does not decrease (core §2.6a)
                    last_uptime = uptime
                    clocks["held, its own id" if session else "held, session_id 0" if held else "no session"] += 1
            if op == ops["open"] and outcome == "completed":
                held = True
            elif op == ops["end"] and outcome == "completed":
                held = False
            if outcome == "locked":
                assert len(ans) >= 9                                                          # remaining_ms(u32), [TLV owner]
                tlvs(ans[9:])
    assert all(clocks.values()), clocks                                                       # clock without a session and with one open


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

    iface = {i["name"]: i for i in REG["interface"]}
    restart = next(o["code"] for o in iface["oep.probe.restart"]["op"] if o["name"] == "restart")
    for c in v:
        if c["name"].startswith("restart"):
            req = bytes.fromhex(c["request_hex"])
            assert c["fns"] == {"11": "oep.probe.restart"}                                             # never fn 0 (oep-if-restart)
            assert struct.unpack_from("<HB", req, 3) == (11, restart) and len(req) == 10, c["name"]   # no fixed part (oep-if-restart §1)
    assert pay("restart: completed success, sent before the probe restarts") == b""                      # completed success, no payload
    plan_ops = {o["name"]: o["code"] for o in iface["oep.probe.plan"]["op"]}
    ra = iface["oep.probe.plan"]["tlv"]["plan_apply"]["role_assignment"]
    for c in v:
        if c["name"].startswith("plan_"):
            req = bytes.fromhex(c["request_hex"])
            fn, opc = struct.unpack_from("<HB", req, 3)
            assert fn == 10 and c["fns"]["10"] == "oep.probe.plan" and opc in plan_ops.values(), c["name"]
            if opc == plan_ops["plan_apply"]:
                ((tag, value),) = tlvs(req[10:])
                assert tag & 0x7F == ra and len(value) == 5                                        # fn role channel (oep-if-plan §2.1)
    assert pay("plan_apply: gpio role 1 on channel 3") == b"" and pay("plan_release: fn 2") == b""
    sub, unsub = REG["constants"]["op_subscribe"], REG["constants"]["op_unsubscribe"]
    assert (sub, unsub) == (0x30, 0x32)
    logic = {o["name"]: o["code"] for o in iface["oep.fixture.logic"]["op"]}
    assert logic["subscribe"] == sub and logic["unsubscribe"] == unsub                           # the reserved numbers (core §11.3)
    assert "subscribe" not in {o["name"] for o in CORE["op"]}                                   # fn 0 sends no notifications
    for c in v:
        if "subscribe" in c["name"]:
            req = bytes.fromhex(c["request_hex"])
            fn, opc = struct.unpack_from("<HB", req, 3)
            assert fn != 0 and opc in (sub, unsub), c["name"]
            assert len(req) == (10 + 6 if opc == sub else 10), c["name"]                            # no target fn in the request
    assert pay("logic subscribe: min_bytes 1024, max_delay_ms 20") == b""
    p = pay("rvswd connections: one connection with a target_id")
    assert p[0] == 0 and 1 + _fixed_sequence(p[1:], lambda b, i: 18 + b[i + 17]) == len(p)        # entry 18 bytes + tid
    p = pay("rvswd scan: one combination listed and found")
    assert p[0] == 1 and 1 + _fixed_sequence(p[1:], lambda b, i: 9) == len(p)                       # kind swdio swclk id
    assert pay("rvswd scan: count 0 with nothing left from skip") == b"\x00\x00"                  # tried 0, count 0 (debug §1)
    p = pay("console marks: one attach mark")
    assert 1 + _fixed_sequence(p[1:], lambda b, i: 22) == len(p)
    p = pay("console streams: one open stream")
    assert 1 + _fixed_sequence(p[1:], lambda b, i: 7) == len(p)
    for c in v:
        if c["name"].startswith("console streams"):
            assert len(bytes.fromhex(c["request_hex"])) == 10 + 2, c["name"]                       # first(u16) (console §1)
    serials = {}
    for c in v:
        if c["name"].startswith("console marks"):
            p = pay(c["name"])
            assert 1 + _fixed_sequence(p[1:], lambda b, i: 22) == len(p) and len(p) + 5 <= 64, c["name"]      # max_frame 64
            serials[c["name"]] = (p[0], [struct.unpack_from("<I", p, 2 + 22 * k)[0] for k in range(p[1])])
    first = serials["console marks: from_serial included, more 1"]
    assert first == (1, [5, 6]) and serials["console marks: the next page from the last serial + 1"] == (0, [7, 8])   # last + 1
    assert serials["console marks: a pushed-out from_serial starts at the oldest kept"] == first                    # paging 3
    assert serials["console marks: from_serial = next, no marks and more 0"] == (0, [])                             # paging 2
    p = pay("logic segments: one segment")
    assert 1 + _fixed_sequence(p[1:], lambda b, i: 37) == len(p)
    assert pay("logic segments: from_serial = serial_done, no segments and more 0") == b"\x00\x00"   # common §1.3 paging 2
    got = dict(tlvs(pay("logic configure: one-shot, the required answer set")))
    ca = iface["oep.fixture.logic"]["tlv"]["configure_answer"]
    assert set(got) == {ca["actual_rate"], ca["layout"], ca["actual_samples"], ca["blocking_ms"]}     # mode 1: no actual_segments (§3.3)
    num, den = struct.unpack("<II", got[ca["actual_rate"]])
    assert num >= 1 and den >= 1 and got[ca["layout"]][1] + 2 == len(got[ca["layout"]])              # w C pos[C]
    p = pay("capture-group start: the group's and each track's new generation")
    n = p[16]                                                                                     # blocking_ms start_ns generation n
    assert len(p) == 17 + 6 * n and n == 2
    fns = [struct.unpack_from("<H", p, 17 + 6 * k)[0] for k in range(n)]
    assert len(set(fns)) == n                                                                     # each bound fn once (§4.1)
    for name, data in (("spi-target read_rx: 12 bits, MSB first, a partial last byte", "c0b0"),
                       ("spi-target read_rx: 12 bits, LSB first, a partial last byte", "030d")):
        assert pay(name) == bytes.fromhex("000c0000000200" + data), name                          # pending bits count data (fixture §4)
    assert "start_answer" not in iface["oep.fixture.capture-group"].get("tlv", {})                # no generations TLV any more
    p = pay("probe.config state: one slot and one bind")
    i = 7                                                                                         # more state hash(u32) reason
    i += _fixed_sequence(p[i:], lambda b, j: 12)                                                  # slot_state: slot state connection last_try_at_ns
    i += _fixed_sequence(p[i:], lambda b, j: 2)                                                   # bind_state: port flow
    assert i == len(p)
    p = pay("probe.config state: wifi connected on entry 0")
    assert p[1:7] == bytes(6) and p[7:9] == b"\x00\x00"                                         # no save, n_slots 0, n_binds 0
    ((tag, value),) = tlvs(p[9:])
    assert tag == iface["oep.probe.config"]["tlv"]["state_answer"]["wifi"] and len(value) == 8   # state entry reason rssi ipv4
    wifi = iface["oep.probe.config"]["tlv"]["item"]["wifi"]
    ((tag, value),) = tlvs(pay("probe.config get: the wifi entry without its passphrase")[5:])
    assert tag == wifi and value[-1] == 0xFF and len(value) == 3 + value[1]                      # pass_len 0xFF, nothing after (§1.4)
    sent = tlvs(bytes.fromhex(by["probe.config set: wifi entry 0 with a passphrase"]["request_hex"])[10:])[0][1]
    secret = sent[3 + sent[1]:]
    assert len(secret) == sent[2 + sent[1]] >= 8
    for c in v:                                                                                  # the passphrase is in no answer
        assert secret not in bytes.fromhex(c["answer_hex"]), c["name"]
    back = bytes.fromhex(by["probe.config set: get's wifi item sent back keeps the passphrase"]["request_hex"])[10:]
    assert tlvs(back) == [(wifi, value)]                                                         # get's item, sent back as it is
    assert pay("probe.config set: get's wifi item sent back keeps the passphrase") == pay("probe.config set: wifi entry 0 with a passphrase")
    p = pay("link source: 8 bytes, byte k = k & 0xFF")
    n = struct.unpack_from("<H", p)[0]
    assert p[2:2 + n] == bytes(k & 0xFF for k in range(n)) and len(p) == 2 + n
    p = pay("link source: more than fits, len = max_frame - 7")                                  # max_frame 1024 (oep-if-link §2)
    n = struct.unpack_from("<H", p)[0]
    assert n == 1024 - 5 - 2                                                                      # the answer's header and len
    assert p[2:] == bytes(k & 0xFF for k in range(n))


def test_capture_events_carry_their_generation():
    """ops.json events: the capture events' fixed parts end with generation(u32) (oep-if-capture §3.4, §4.2)."""
    iface = {i["name"]: i for i in REG["interface"]}
    fixed = {("oep.fixture.logic", "stopped"): 6, ("oep.fixture.logic", "triggered"): 20,
             ("oep.fixture.capture-group", "stopped"): 6, ("oep.fixture.capture-group", "triggered"): 14}
    events = load("ops.json")["events"]
    assert events
    for e in events:
        f = bytes.fromhex(e["event_hex"])
        role, fn, _seq, kind = struct.unpack_from("<BHHB", f)
        name = e["fns"][str(fn)]
        (ev,) = [k for k, v in iface[name]["event"].items() if v == kind]
        assert role == REG["roles"]["event"] and len(f) == 6 + fixed[(name, ev)], e["name"]   # no TLV in these
        assert struct.unpack_from("<I", f, len(f) - 4)[0] == e["generation"], e["name"]
