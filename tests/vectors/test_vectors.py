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


# core §1.2 (and the 必須 column of core §11): fn 0's ops every probe offers; plan_apply / plan_release only with a plan role
REQUIRED_FN0_OPS = ("confirm", "list", "describe", "clock", "open", "end", "keepalive", "lock_state")


def ops_set(value: bytes) -> set[int]:
    """The ops a describe common tag ops declares (core §7.4): base(u8), bitmap."""
    base = value[0]
    return {base + i for i in range(8 * (len(value) - 1)) if value[1 + i // 8] >> (i % 8) & 1}


def test_ops_examples_of_the_text():
    """core §7.4: riscv-dm ops at 0x10, with the common tag 0x07."""
    ((tag, v),) = tlvs(bytes.fromhex("07020010ff"))
    assert tag == REG["describe_common"]["ops"] and ops_set(v) == set(range(0x10, 0x18))
    assert ops_set(tlvs(bytes.fromhex("0702001007"))[0][1]) == {0x10, 0x11, 0x12}


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
    assert struct.unpack_from("<BHIBI", ans, 9) == (a["revision"], a["max_frame"], a["window"], a["max_inflight"], a["boot_id"])
    assert tlvs(ans[9 + 12:]) == [(0x01, bytes([a["transport"]]))]                                  # transport only (core §7.1); the time is clock's
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
        assert req[0] == 0x01 and struct.unpack_from("<H", req, 1)[0] == ex["request"]["corr"]   # no lock needed (core §11)
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
        fn, inst, rev, nlen = struct.unpack_from("<HHBB", ans, i)
        entries.append({"fn": fn, "instance": inst, "revision": rev,
                        "name": ans[i + 6:i + 6 + nlen].decode()})
        i += 6 + nlen
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
            got = dict(tlvs(ans[5 + 4 + 12:]))
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
    """sessions.json (core §5.1, §6.2, §9): every step is one 10-byte-header request and its answer with the same corr; a resent request
    gets the same answer bytes; after end, the ended id is no_session; force hands the lock over."""
    reasons = {v: k for k, v in REG["reject_reasons"].items()}
    ops = {o["name"]: o["code"] for o in CORE["op"]}
    assert ops["clock"] == 0x04 and not next(o["lock"] for o in CORE["op"] if o["name"] == "clock")     # core §11: no lock
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
            if req in seen and ans[3] == REG["resolutions"]["completed"]:                                                                   # a resend: the same answer
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
                assert len(req) == 10, st["note"]                                                  # no fixed part (core §7.6)
                if session == 0:
                    assert outcome == "completed", st["note"]                                       # no session needed (core §4.1, §6.3)
                if outcome == "completed":
                    assert len(ans) == 5 + 12, st["note"]                                         # boot_id(u32) uptime_ns(u64)
                    boot_id, uptime = struct.unpack_from("<IQ", ans, 5)
                    assert boot_id == 0x12345678 and uptime >= last_uptime, st["note"]            # one boot: the clock does not decrease (core §2.7)
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
                for tag,value in tlvs(req[10:]):
                    assert tag & 0x7F == ra and len(value) == 5                                    # fn role channel (oep-if-plan §2.1)
    assert pay("plan_apply: gpio role 1 on channel 3") == b"" and pay("plan_release: fn 2") == b""
    sub, unsub = REG["constants"]["op_subscribe"], REG["constants"]["op_unsubscribe"]
    assert (sub, unsub) == (0x01, 0x02)
    logic = {o["name"]: o["code"] for o in iface["oep.fixture.logic"]["op"]}
    assert logic["subscribe"] == sub and logic["unsubscribe"] == unsub                           # the reserved numbers (core §10.3)
    assert "subscribe" not in {o["name"] for o in CORE["op"]}                                   # fn 0 sends no notifications
    for c in v:
        if "subscribe" in c["name"]:
            req = bytes.fromhex(c["request_hex"])
            fn, opc = struct.unpack_from("<HB", req, 3)
            assert fn != 0 and opc in (sub, unsub), c["name"]
            assert len(req) == (10 + 6 if opc == sub else 10), c["name"]                            # no target fn in the request
    assert pay("logic subscribe: min_bytes 1024, max_delay_ms 20") == b""
    p = pay("rvswd connections: one connection with a target_id")
    assert p[0] == 0 and 1 + _fixed_sequence(p[1:], lambda b, i: 14 + b[i + 13]) == len(p)        # entry 14 bytes + tid; connection u32
    p = pay("rvswd scan: one combination listed and found")
    assert p[0] == 1 and 1 + _fixed_sequence(p[1:], lambda b, i: 9) == len(p)                       # kind swdio swclk id
    assert pay("rvswd scan: count 0 is malformed") == b""                  # tried 0, count 0 (debug §1)
    p = pay("console marks: one host mark")
    assert 1 + _fixed_sequence(p[1:], lambda b, i: 22) == len(p)
    p = pay("console streams: one open stream")
    assert 1 + _fixed_sequence(p[1:], lambda b, i: 9) == len(p)                                  # stream/connection u32, mechanism u8
    for c in v:
        if c["name"].startswith("console streams"):
            assert len(bytes.fromhex(c["request_hex"])) == 10 + 2, c["name"]                       # first(u16) (console §1)
    serials = {}
    for c in v:
        if c["name"].startswith("console marks") and bytes.fromhex(c['answer_hex'])[3] == 1:
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
    assert set(got) == {ca["actual_rate"], ca["layout"], ca["actual_samples"]}     # mode 1: no actual_segments (§3.3)
    num, den = struct.unpack("<II", got[ca["actual_rate"]])
    assert num >= 1 and den >= 1 and got[ca["layout"]][1] + 2 == len(got[ca["layout"]])              # w C pos[C]
    p = pay("capture-group start: the group's and each track's new generation")
    n = p[12]                                                                                     # start_ns generation n
    assert len(p) == 13 + 6 * n and n == 2
    fns = [struct.unpack_from("<H", p, 13 + 6 * k)[0] for k in range(n)]
    assert len(set(fns)) == n                                                                     # each bound fn once (§4.1)
    for name, data in (("spi-target read_rx: 12 bits, MSB first, a partial last byte", "c0b0"),
                       ("spi-target read_rx: 12 bits, LSB first, a partial last byte", "030d")):
        assert pay(name) == bytes.fromhex("000c0000000200" + data), name                          # pending bits count data (fixture §4)
    assert "start_answer" not in iface["oep.fixture.capture-group"].get("tlv", {})                # no generations TLV any more
    assert pay("probe.config state: no saved settings") == bytes(6)
    p = pay("link source: 8 bytes, byte k = k & 0xFF")
    n = struct.unpack_from("<H", p)[0]
    assert p[2:2 + n] == bytes(k & 0xFF for k in range(n)) and len(p) == 2 + n
    p = pay("link source: more than fits, len = max_frame - 7")                                  # max_frame 1024 (oep-if-link §2)
    n = struct.unpack_from("<H", p)[0]
    assert n == 1024 - 5 - 2                                                                      # the answer's header and len
    assert p[2:] == bytes(k & 0xFF for k in range(n))


def test_resource_ids_cross_u16_without_changing_function_or_correlation_width():
    cases = {case['name']: case for case in load('ops.json')['cases']}
    attach = bytes.fromhex(cases['rvswd attach: a resource ID above u16']['answer_hex'])
    assert attach[5:9] == b'\x00\x00\x01\x00'  # 65536, little endian u32.
    assert len(attach) == 18 and attach[9:13] == bytes.fromhex('82034000')
    transfer = bytes.fromhex(cases['arm-adi transfer: a connection ID above u16']['request_hex'])
    assert transfer[1:3] == b'\x59\x00' and transfer[3:5] == b'\x0f\x00'
    assert transfer[10:] == b'\x00\x00\x01\x00\x00\x00'  # Connection, then u16 n.
    streams = bytes.fromhex(cases['console streams: resource IDs above u16']['answer_hex'])
    assert streams[5:7] == b'\x00\x01'
    assert streams[7:11] == b'\x01\x00\x01\x00' and streams[11:15] == b'\x00\x00\x01\x00'
    assert len(streams) == 16 and streams[15] == 2
    assert REG['limits']['resource_id_bytes'] == 4 and REG['limits']['resource_id_max'] == 0xFFFFFFFF


def test_debug_fixed_attach_selection_and_cleanup_failure_shapes():
    cases = {row['name']: row for row in load('ops.json')['cases']}
    request = bytes.fromhex(cases['rvswd attach: a resource ID above u16']['request_hex'])
    assert len(request)==19 and struct.unpack_from('<BHHI',request,10)==(0,3,4,1000000)
    response = bytes.fromhex(cases['swd connections: read identity and supplied selector are distinct']['answer_hex'])
    assert len(response)==33 and response[5:7]==b'\0\1'
    assert struct.unpack_from('<IHHIBBI',response,7)==(65536,1,2,1000000,2,4,0x2BA01477)
    assert tlvs(response[25:])==[(1,struct.pack('<BI',0,0x01000001))]
    # A write may complete before restoration fails; done does not imply success.
    response = bytes.fromhex(cases['riscv-dm write_block: memory written but cleanup lost the line']['answer_hex'])
    assert response[3:]==b'\1\2'+struct.pack('<HB',2,2)
    response = bytes.fromhex(cases['riscv-dm dmi: connection closed after incomplete cleanup']['answer_hex'])
    assert response[3:5]==bytes([0,REG['reject_reasons']['no_resource']])
    response = bytes.fromhex(cases['spi-target arm: preparation failed with no fixed result']['answer_hex'])
    assert len(response)==5 and response[3:]==b'\1\1'


def test_capture_minimal_reply_and_analog_diagnostics_fit_frame64():
    cases={row['name']:row for row in load('ops.json')['cases']}
    response=bytes.fromhex(cases['logic start: bounded CPU capture finishes before the reply']['answer_hex'])
    assert response[5:]==struct.pack('<I',1) and len(response)==9
    row=cases['logic read: maximum u16 request, response constrained by frame']
    request,response=bytes.fromhex(row['request_hex']),bytes.fromhex(row['answer_hex'])
    assert len(request)==24 and struct.unpack_from('<IQH',request,10)==(1,0,65535)
    assert len(response)==64 and struct.unpack_from('<QBH',response,5)==(0,0,48)
    assert response[16:]==bytes(range(48))
    for count,size in ((1,51),(2,64)):
        response=bytes.fromhex(cases[f'analog configure: {count} roles and one nonzero skew without optional diagnostics']['answer_hex'])
        decoded=tlvs(response[5:]);assert len(response)==size
        assert {tag for tag,_ in decoded}=={0x50,0x51,0x52,0x55,0x57}
        assert [struct.unpack('<Bii',value) for tag,value in decoded if tag==0x55]==[(role,0,1000000) for role in range(count)]
        assert len([v for t,v in decoded if t==0x57])==1
    row=cases['logic start: generation exhausted without clearing current data']
    assert bytes.fromhex(row['answer_hex'])[5:]==bytes.fromhex('01010002')


def test_settings_counted_container_and_change_counter_shapes():
    cases={row['name']:row for row in load('ops.json')['cases']}
    response=bytes.fromhex(cases['probe.config get: count separates items from response extensions']['answer_hex'])
    more,generation,count=struct.unpack_from('<BIB',response,5)
    assert (more,generation,count)==(0,2,1)
    # Decode count records, then the extension tail separately.
    tag,size=struct.unpack_from('<BH',response,11)
    assert tag==3 and size==3 and struct.unpack_from('<HB',response,14)==(4,0)
    assert tlvs(response[17:])==[(0x7f,b'x')]
    request=bytes.fromhex(cases['probe.config set: item bit7 ignored for known idle']['request_hex'])
    assert request[10:]==bytes.fromhex('01830300040000')
    request=bytes.fromhex(cases['probe.config unset: fixed channel key']['request_hex'])
    assert request[10:]==bytes.fromhex('01070400')
    request=bytes.fromhex(cases['probe.config set: longest label fits frame64']['request_hex'])
    assert len(request)==48 and request[10]==1 and request[-32:]==b'L'*32
    response=bytes.fromhex(cases['probe.config state: independent valid items restored despite invalid label']['answer_hex'])
    assert struct.unpack_from('<BIB',response,5)==(3,0,2)


def test_link_current_phase_query_is_distinct_from_cached_speed_success():
    rows={r['name']:r for r in load('ops.json')['cases']}
    raw=bytes.fromhex(rows['link port_state: cached try success no longer describes the route']['answer_hex'])
    assert len(raw)==10 and struct.unpack_from('<IB',raw,5)==(115200,0)
    raw=bytes.fromhex(rows['link port_state: session-ended fallback waits for old frame']['answer_hex'])
    assert struct.unpack_from('<IB',raw,5)==(921600,3)


def test_minimal_console_has_no_unused_flags_or_required_mark_write():
    cases = {case['name']: case for case in load('ops.json')['cases']}
    opened = bytes.fromhex(cases['console open: RX-only SDI without flags']['answer_hex'])
    assert opened[5:] == b'\x01\x00\x01\x00' and len(opened) == 9
    for name in ('console marks: absent on RX-only console','console write: absent on RX-only console'):
        result = bytes.fromhex(cases[name]['answer_hex'])
        assert result[3:] == bytes([0,REG['reject_reasons']['unknown_operation']])
    for name in ('console read: from3 without marks is unsupported',
                 'console write: SDI is unsupported even if other mechanisms can write'):
        result = bytes.fromhex(cases[name]['answer_hex'])
        assert result[3:] == bytes([0,REG['reject_reasons']['unsupported'],0])


def test_plan_lifetime_and_explicit_uart_initialization_vectors():
    cases = {case['name']:case for case in load('ops.json')['cases']}
    for name in ('plan_apply: GPIO addition preserves an existing output',
                 'plan_apply: identical configured UART is unchanged'):
        result=bytes.fromhex(cases[name]['answer_hex'])
        assert result[3:] == b'\x01\x00'
    for name in ('plan_apply: configured UART channel change is refused',
                 'plan_apply: active capture channel change is refused'):
        result=bytes.fromhex(cases[name]['answer_hex'])
        assert result[3:5] == bytes([0,REG['reject_reasons']['unavailable']])
        assert tlvs(result[5:]) == [(1,b'\x06')]
    status=bytes.fromhex(cases['UART status: unconfigured has no implicit baud']['answer_hex'])
    assert status[5:] == bytes(5)
    empty=bytes.fromhex(cases['UART read: unconfigured is empty at its retained position']['answer_hex'])
    assert struct.unpack('<QBH',empty[5:]) == (7,0,0)
    zero=bytes.fromhex(cases['UART configure: zero baud is malformed']['answer_hex'])
    assert zero[3:] == bytes([0,REG['reject_reasons']['malformed']])


def test_output_idle_admission_vectors():
    cases = {case['name']: case for case in load('ops.json')['cases']}
    for interface in ('oep.fixture.uart', 'oep.fixture.i2c-target', 'oep.fixture.spi-target'):
        case = cases[f'plan_apply: {interface} refuses output idle']
        request = bytes.fromhex(case['request_hex'])
        assignments = [struct.unpack('<HBH', value) for tag, value in tlvs(request[10:]) if tag == 0x10]
        assert (5, 1, 3) in assignments
        result = bytes.fromhex(case['answer_hex'])
        assert result[3:5] == bytes([0, REG['reject_reasons']['unavailable']])
        assert tlvs(result[5:]) == [(1, bytes([5])), (2, struct.pack('<H', 3))]
    result = bytes.fromhex(cases['plan_apply: GPIO accepts output idle without changing level']['answer_hex'])
    assert result[3:] == bytes([1, 0])


def test_raw_reset_halt_wait_is_one_frame_with_haltreq_preserved():
    case = next(c for c in load('ops.json')['cases'] if c['name'] == 'riscv-dm dmi: reset and halt wait in one request')
    request = bytes.fromhex(case['request_hex'])
    assert len(request) <= 64
    connection, count = struct.unpack_from('<IH', request, 10)
    assert connection == 1
    at, control, waited = 16, 0, False
    for _ in range(count):
        kind, address = struct.unpack_from('<BB', request, at)
        if kind == 1:
            _, _, control = struct.unpack_from('<BBI', request, at)
            assert address == 0x10
            if control & (1 << 28):  # ackhavereset must preserve haltreq before the wait.
                assert control & (1 << 31) and not waited
            at += 6
        else:
            assert kind == 3 and address == 0x11
            _, _, mask, value, reads = struct.unpack_from('<BBIIH', request, at)
            assert mask == value == (1 << 9) and reads > 0  # allhalted.
            assert control & (1 << 31) and not control & 2  # haltreq, ndmreset released.
            waited = True
            at += 12
    assert at == len(request) and waited and control == 1
    result = bytes.fromhex(case['answer_hex'])
    assert result[3:5] == bytes([1, 0])
    assert struct.unpack('<HBHI', result[5:]) == (count, 0, 1, 1 << 9)


def test_pending_port_speed_step_boundaries():
    cases = {case['name']: case for case in load('ops.json')['cases']}
    for step in (0, 1, 2):
        for reason in ('verify', 'idle'):
            name = (f'link port_speed: verify fallback pending refuses step {step}' if reason == 'verify'
                    else f'link port_speed: idle fallback pending applies step {step} after cancellation')
            case = cases[name]
            request, result = bytes.fromhex(case['request_hex']), bytes.fromhex(case['answer_hex'])
            assert struct.unpack_from('<IBH', request, 10) == (921600, step, 2000)
            if reason == 'idle' and step == 2:
                assert result[3:5] == bytes([1, 0])
                assert struct.unpack('<I', result[5:]) == (115200,)
            else:
                assert result[3:5] == bytes([0, REG['reject_reasons']['unavailable']])
                assert tlvs(result[5:]) == [(1, bytes([6]))]
    ended = bytes.fromhex(cases['link port_speed: ended session checked before pending phase']['answer_hex'])
    assert ended[3:] == bytes([0, REG['reject_reasons']['no_session']])


def test_config_item_conflicts_are_usage_restrictions():
    cases = {case['name']: case for case in load('ops.json')['cases']}
    for name in ('disable conflicts with existing idle', 'idle conflicts with existing disable', 'disable and idle conflict in one set'):
        case = cases[f'probe.config set: {name}']
        request, result = bytes.fromhex(case['request_hex']), bytes.fromhex(case['answer_hex'])
        count = request[10]
        items = tlvs(request[11:])
        assert len(items) == count and count in (1, 2)
        assert len({(tag, struct.unpack_from('<H', value)[0]) for tag, value in items}) == count
        assert all(len(value) == (3 if tag == 3 else 2) for tag, value in items)
        assert result[3:5] == bytes([0, REG['reject_reasons']['unavailable']])
        assert tlvs(result[5:]) == [(1, bytes([5])), (2, struct.pack('<H', 4))]


def test_capture_events_carry_their_generation():
    """ops.json events: the capture events' fixed parts end with generation(u32) (oep-if-capture §3.4, §4.2)."""
    iface = {i["name"]: i for i in REG["interface"]}
    fixed = {("oep.fixture.logic", "stopped"): 6, ("oep.fixture.logic", "triggered"): 20,
             ("oep.fixture.capture-group", "stopped"): 6}
    events = load("ops.json")["events"]
    assert events
    for e in events:
        f = bytes.fromhex(e["event_hex"])
        role, fn, _seq, kind = struct.unpack_from("<BHHB", f)
        name = e["fns"][str(fn)]
        (ev,) = [k for k, v in iface[name]["event"].items() if v == kind]
        assert role == REG["roles"]["event"] and len(f) == 6 + fixed[(name, ev)], e["name"]   # no TLV in these
        assert struct.unpack_from("<I", f, len(f) - 4)[0] == e["generation"], e["name"]


def unpack_samples(stream: bytes, w: int, pos: list[int], count: int) -> list[str]:
    """capture §1.1, read the other way round: channel k of sample i is stream bit i*w + pos[k] (bit j = byte j // 8, bit j % 8)."""
    bit = lambda j: stream[j >> 3] >> (j & 7) & 1
    return ["".join(str(bit(i * w + p)) for i in range(count)) for p in pos]


def test_logic_layout_streams_decode_back():
    """logic_layout.json: the stream is ceil(N*w / 8) bytes and gives back every channel's levels (capture §1.1)."""
    cases = load("logic_layout.json")["cases"]
    assert any(c["w"] % 8 and 8 % c["w"] for c in cases)                                      # a w that is not a power of 2
    for c in cases:
        stream, w, n = bytes.fromhex(c["stream_hex"]), c["w"], c["samples"]
        assert 1 <= w <= 128 and len(set(c["pos"])) == len(c["pos"]) and all(p < w for p in c["pos"]), c["name"]
        assert len(stream) == (n * w + 7) // 8, c["name"]
        assert unpack_samples(stream, w, c["pos"], n) == c["channels"], c["name"]
    assert next(c for c in cases if c["w"] == 3)["stream_hex"] == "598480"                    # capture §1.1, the w = 3 example


def test_a_segment_with_dropped_data_is_not_handed_out():
    """capture §2.2: status says state 6, flags bit0, error 2 (storage) and write_pos at the dropped segment's start; segments and read
    give nothing of it; the stopped event has reason 3, error 2."""
    logic = next(i for i in REG["interface"] if i["name"] == "oep.fixture.logic")
    e = logic["enum"]
    by = {c["name"]: bytes.fromhex(c["answer_hex"])[5:] for c in load("ops.json")["cases"]}
    p = by["logic status: data dropped inside a segment, state 6 and error 2"]
    state, serial_done, write_pos, flags, generation = struct.unpack_from("<BIQBI", p)
    assert (state, flags & e["status_flag"]["dropped"]) == (e["state"]["error"], e["status_flag"]["dropped"])
    assert tlvs(p[18:]) == [(logic["tlv"]["status_answer"]["error"], bytes([e["error"]["storage"]]))]
    p = by["logic segments: the dropped segment is not handed out"]
    assert p[0] == 0 and len(p) == 2 + 37 * p[1]
    kept = [struct.unpack_from("<IQI", p, 2 + 37 * k) for k in range(p[1])]
    assert serial_done not in [s for s, _, _ in kept]                                          # the dropped serial is not listed
    assert max(pos + n // 8 for _, pos, n in kept) == write_pos                                 # w 1: write_pos is the dropped one's start
    assert by["logic read: nothing of the dropped segment"] == struct.pack("<QBH", write_pos, 0, 0)
    (ev,) = [x for x in load("ops.json")["events"] if x["name"].startswith("logic stopped: data dropped")]
    f = bytes.fromhex(ev["event_hex"])
    assert struct.unpack_from("<BBI", f, 6) == (e["stopped_reason"]["error"], e["error"]["storage"], generation)


def test_an_immediate_triggers_role_is_not_looked_at():
    """capture §3.3 contract: type 0 uses neither role nor value; a role outside the plan is not refused there."""
    logic = next(i for i in REG["interface"] if i["name"] == "oep.fixture.logic")
    by = {c["name"]: c for c in load("ops.json")["cases"]}
    c = by["logic query: an immediate trigger's role is not looked at"]
    req, ans = bytes.fromhex(c["request_hex"]), bytes.fromhex(c["answer_hex"])
    (trig,) = [v for t, v in tlvs(req[10:]) if t == logic["tlv"]["configure"]["trigger"]]
    assert struct.unpack("<BBI", trig)[:2] == (logic["enum"]["trigger"]["immediate"], 5)           # role 5: not in the plan (0, 1)
    plain = bytes.fromhex(by["logic configure: one-shot, the required answer set"]["answer_hex"])
    assert ans[3:] == plain[3:]                                                                     # the same success as without it


def test_streaming_metadata_and_error_rollback_do_not_cross_segments():
    logic=next(i for i in REG['interface'] if i['name']=='oep.fixture.logic')
    by={c['name']:bytes.fromhex(c['answer_hex'])[5:] for c in load('ops.json')['cases']}
    state,_,write_pos,flags,generation=struct.unpack_from('<BIQBI',by['logic status: streaming stopped in error, write_pos at the lost segment\'s start'])
    assert (state,write_pos,flags,generation)==(6,32,1,1)
    for row in load('ops.json')['data']:
        if 'layout' in row: continue
        frame=bytes.fromhex(row['frame_hex'])
        role,fn,seq,position,count=struct.unpack_from('<BHHQH',frame)
        assert role==4 and fn==9 and len(frame)<=64
        body,tail=frame[15:15+count],dict(tlvs(frame[15+count:]))
        assert tail[1]==struct.pack('<I',generation)
        origin,samples,time_ns,uncertainty=struct.unpack('<QIQI',tail[2])
        assert origin<=position and position+count<=origin+samples
        assert time_ns==1000000+origin*1000000 and uncertainty==50
        kept=body[:max(0,min(count,write_pos-position))]
        assert len(kept)==row['keep']
        assert kept==bytes(range(position,position+len(kept)))


def test_streaming_lost_first_frame_recovers_w3_boundary_and_padding():
    row=next(r for r in load('ops.json')['data'] if r['name'].startswith('logic data: w3 byte1'))
    raw=bytes.fromhex(row['frame_hex'])
    _,_,_,position,size=struct.unpack_from('<BHHQH',raw)
    info=dict(tlvs(raw[15+size:]));origin,samples,start_ns,_=struct.unpack('<QIQI',info[2])
    assert (position,size,origin,samples,start_ns)==(1,1,0,5,1000000)
    byte=raw[15];first=(8*(position-origin)+2)//3
    end=min(samples,(8*(position-origin+size))//3)
    values=[sum(((byte>>(3*sample+bit-8))&1)<<bit for bit in range(3)) for sample in range(first,end)]
    assert values==[4,5]  # sample2's first bits were lost; the final padding is ignored.
    assert len(raw)==50 and info[1]==struct.pack('<I',1)


def test_basic_group_has_only_immediate_start_and_future_selector_refusal():
    rows={r['name']:r for r in load('ops.json')['cases']}
    raw=bytes.fromhex(rows['capture-group status: immediate group has no unused trigger fields']['answer_hex'])
    assert len(raw)==18 and struct.unpack_from('<BQI',raw,5)==(3,7000000,5)
    future=bytes.fromhex(rows['capture-group bind: future critical selector is refused']['answer_hex'])
    assert future[3:]==bytes([0,REG['reject_reasons']['unsupported'],0x81])
    group=next(i for i in REG['interface'] if i['name']=='oep.fixture.capture-group')
    assert 'force' not in {op['name'] for op in group['op']} and group['event']=={'stopped':2}


def test_capture_request_tlvs_are_plain_and_zero_counts_are_malformed():
    """capture §3.3: base setting TLVs are plain; future behavioral extension TLVs are critical;
    samples 0 is a value the definition excludes (malformed)."""
    iface = {i["name"]: i for i in REG["interface"]}
    cases = load("ops.json")["cases"]
    plain = {("oep.fixture.logic", 0x10): set(iface["oep.fixture.logic"]["tlv"]["configure"].values()) - {0x60},
             ("oep.fixture.logic", 0x18): set(iface["oep.fixture.logic"]["tlv"]["configure"].values()) - {0x60},
             ("oep.fixture.capture-group", 0x10): set(iface["oep.fixture.capture-group"]["tlv"]["bind"].values())}
    seen = 0
    for c in cases:
        req = bytes.fromhex(c["request_hex"])
        fn, opc = struct.unpack_from("<HB", req, 3)
        name = c["fns"].get(str(fn))
        if (name, opc) not in plain:
            continue
        fixed = 0 if name == "oep.fixture.logic" else 1 + 2 * req[10]
        for tg, _ in tlvs(req[10 + fixed:]):
            seen += 1
            assert tg in plain[(name, opc)] or tg & 0x80, (c["name"], hex(tg))               # a refused future extension may be critical
    assert seen
    c = next(c for c in cases if c["name"].startswith("logic query: samples 0"))
    assert bytes.fromhex(c["answer_hex"])[3:5] == bytes([REG["resolutions"]["rejected"], REG["reject_reasons"]["malformed"]])
