# /// script
# requires-python = ">=3.11"
# ///
"""Compute the OEP v1 test vectors (tests/vectors/*.json) from the rules of the specification text.

Every value here is computed from the text (oep-core, oep-if-*, target-console-dmseq) and the numbers of
registry/oep-v1.toml. Implementations read the vectors; they do not define them.

Usage:
  uv run tools/oepvectors1.py            # write tests/vectors/*.json
  uv run tools/oepvectors1.py --check    # exit 1 if a file differs from what the rules give
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry" / "oep-v1.toml"
OUT = ROOT / "tests" / "vectors"

REG = tomllib.loads(REGISTRY.read_text(encoding="utf-8"))
IFACE = {i["name"]: i for i in REG["interface"]}
CORE = REG["core"]                  # fn 0: the core has no name and is not in list (core §0)


def op(iface: str, name: str) -> int:
    """An op code: of the core (iface "core") or of the named interface."""
    return next(o["code"] for o in (CORE if iface == "core" else IFACE[iface])["op"] if o["name"] == name)


ROLE_REQUEST, ROLE_ANSWER = REG["roles"]["request"], REG["roles"]["result"]
REJECTED, COMPLETED = REG["resolutions"]["rejected"], REG["resolutions"]["completed"]
REASON = REG["reject_reasons"]
CRITICAL = REG["constants"]["tag_critical"]


# ---- checks (transports §1; dmseq "CRC-8") ------------------------------------------------------------------

def crc16_ccitt_false(data: bytes) -> int:
    """poly 0x1021, init 0xFFFF, no reflection, no final XOR (transports §1)."""
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def crc8_dmseq(data: bytes) -> int:
    """poly 0x07, init 0xFF, no reflection, no final XOR (target-console-dmseq, CRC-8)."""
    crc = 0xFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


# ---- COBS (transports §1) -------------------------------------------------------------------------------------

def cobs_encode(data: bytes) -> bytes:
    """Standard COBS in 254-byte blocks; no empty block after a final full block (code 0xFF)."""
    out = bytearray()
    i, n = 0, len(data)
    while True:
        j = i
        while j < n and data[j] != 0 and j - i < 254:
            j += 1
        code = j - i + 1
        out.append(code)
        out += data[i:j]
        if j >= n:
            return bytes(out)
        i = j if code == 0xFF else j + 1


def serial_frame(message: bytes) -> bytes:
    crc = crc16_ccitt_false(message)
    return b"\x00" + cobs_encode(message + struct.pack("<H", crc)) + b"\x00"


def length_frame(message: bytes) -> bytes:
    return struct.pack("<H", len(message)) + message


# ---- messages (core §2.2, §4.1, §4.2) ---------------------------------------------------------------------

def tlv(tag: int, value: bytes) -> bytes:
    """tag(u8) len(u16) value: the one TLV form (core §2.2)."""
    return bytes([tag]) + struct.pack("<H", len(value)) + value


def request(corr: int, fn: int, op_code: int, payload: bytes, session: int = 0) -> bytes:
    """The one request header (core §4.1): session_id always present, 0 = no session."""
    return struct.pack("<BHHBI", ROLE_REQUEST, corr, fn, op_code, session) + payload


def answer(corr: int, resolution: int, detail: int, payload: bytes = b"") -> bytes:
    return struct.pack("<BHBB", ROLE_ANSWER, corr, resolution, detail) + payload


def ops_value(codes: list[int]) -> bytes:
    """The value of the common describe tag ops (core §7.4): base(u8), bitmap; bit i = op base + i."""
    base = min(codes) & ~7
    bits = bytearray((max(codes) - base) // 8 + 1)
    for c in codes:
        bits[(c - base) // 8] |= 1 << ((c - base) % 8)
    return bytes([base]) + bytes(bits)


def ops_decode(value: bytes) -> list[int] | None:
    """The op set of an ops value, or None when the value is not valid (core §7.4): base(u8), a bitmap of 1 byte or more,
    base + 8 x bitmap bytes <= 256."""
    n = len(value) - 1
    if n < 1 or value[0] + 8 * n > 256:
        return None
    return [value[0] + i for i in range(8 * n) if value[1 + i // 8] >> (i % 8) & 1]


def hx(b: bytes) -> str:
    return b.hex()


# ---- the files --------------------------------------------------------------------------------------------

def checks() -> dict:
    digits = b"123456789"
    syn = 0x98            # T = 1, TO = 0, S = 0, A = 1, SYN = 1, N = 0 (dmseq "Byte order" example)
    host = 0x00           # K = 0, H = 0, M = 0
    return {
        "about": "Check values of the two CRCs of OEP v1.",
        "cases": [
            {"name": "crc16 123456789", "spec": "transports §1", "algorithm": "crc16-ccitt-false",
             "input_hex": hx(digits), "crc": crc16_ccitt_false(digits)},
            {"name": "crc8 123456789", "spec": "target-console-dmseq CRC-8", "algorithm": "crc8-dmseq",
             "input_hex": hx(digits), "crc": crc8_dmseq(digits)},
            {"name": "crc8 one zero byte", "spec": "target-console-dmseq CRC-8", "algorithm": "crc8-dmseq",
             "input_hex": "00", "crc": crc8_dmseq(b"\x00")},
        ],
        "dmseq_words": [
            {"name": "empty SYN frame, S = 0, A = 1", "spec": "target-console-dmseq Byte order",
             "byte0": syn, "payload_hex": "", "crc": crc8_dmseq(bytes([syn])),
             "data0": syn | crc8_dmseq(bytes([syn])) << 8},
            {"name": "host answer K = 0, H = 0, M = 0", "spec": "target-console-dmseq Byte order",
             "byte0": host, "payload_hex": "", "crc": crc8_dmseq(bytes([host])),
             "data0": host | crc8_dmseq(bytes([host])) << 8},
        ],
    }


def cobs() -> dict:
    blocks = [
        ("no zero", bytes([0x11, 0x22, 0x33])),
        ("one zero", bytes([0x11, 0x00, 0x22])),
        ("zeros only", bytes([0x00, 0x00])),
        ("ends in a zero", bytes([0x11, 0x22, 0x00])),
        ("254 non-zero bytes: one full block, no empty block after it", bytes((i % 255) + 1 for i in range(254))),
        ("255 non-zero bytes: a full block and a block of one", bytes((i % 255) + 1 for i in range(255))),
        ("254 non-zero bytes then a zero", bytes((i % 255) + 1 for i in range(254)) + b"\x00"),
    ]
    cases = [{"name": n, "data_hex": hx(d), "encoded_hex": hx(cobs_encode(d))} for n, d in blocks]
    full = bytes((i % 255) + 1 for i in range(254))
    accepted = [{"name": "the decoder also accepts the empty block after a final full block",
                 "encoded_hex": hx(cobs_encode(full) + b"\x01"), "data_hex": hx(full)}]
    msg = request(1, 0, op("core", "confirm"), b"OEP?\x01\x01")
    crc = crc16_ccitt_false(msg)
    frames = [{"name": "confirm request on a serial port", "spec": "transports §1",
               "message_hex": hx(msg), "crc16": crc, "frame_hex": hx(serial_frame(msg))}]
    return {"about": "COBS (transports §1): the encoding alone, then whole serial-port frames (0x00 COBS(message + CRC-16 LE) 0x00).",
            "encode": cases, "decode_also_accepts": accepted, "frames": frames}


def headers() -> dict:
    c = op("core", "describe")
    return {
        "about": "Message headers (core §4.1, §4.2) and the TLV form (core §2.2). All numbers little endian.",
        "requests": [
            {"name": "request without a session: session_id 0", "role": ROLE_REQUEST, "corr": 0x1234, "fn": 0x0000, "op": c,
             "session_id": 0, "payload_hex": "00000000", "message_hex": hx(request(0x1234, 0, c, bytes(4)))},
            {"name": "request of a session", "role": ROLE_REQUEST, "corr": 0x0102, "fn": 0x0203,
             "op": 0x10, "session_id": 0x11223344, "payload_hex": "",
             "message_hex": hx(request(0x0102, 0x0203, 0x10, b"", 0x11223344))},
        ],
        "answers": [
            {"name": "completed success", "role": ROLE_ANSWER, "corr": 0x1234, "resolution": COMPLETED,
             "detail": 0, "payload_hex": "", "message_hex": hx(answer(0x1234, COMPLETED, 0))},
            {"name": "rejected malformed", "role": ROLE_ANSWER, "corr": 0xFFFF, "resolution": REJECTED,
             "detail": REASON["malformed"], "payload_hex": "", "message_hex": hx(answer(0xFFFF, REJECTED, REASON["malformed"]))},
        ],
        "tlvs": [
            {"name": "two bytes", "tag": 0x10, "value_hex": "0102", "tlv_hex": hx(tlv(0x10, b"\x01\x02"))},
            {"name": "two bytes, critical", "tag": 0x10 | CRITICAL, "value_hex": "0102", "tlv_hex": hx(tlv(0x90, b"\x01\x02"))},
            {"name": "an empty value", "tag": 0x01, "value_hex": "", "tlv_hex": hx(tlv(0x01, b""))},
            {"name": "max_speed 1 MHz, critical", "tag": 0x01 | CRITICAL, "value_hex": hx(struct.pack("<I", 1_000_000)),
             "tlv_hex": hx(tlv(0x81, struct.pack("<I", 1_000_000)))},
            {"name": "255 bytes: the same form", "tag": 0x41, "value_len": 255, "value_byte": 0xAA,
             "tlv_hex": hx(tlv(0x41, b"\xaa" * 255))},
        ],
    }


def confirm() -> dict:
    confirm_op = op("core", "confirm")
    t_transport = CORE["tlv"]["confirm_answer"]["transport"]
    t_supported = CORE["tlv"]["unsupported_payload"]["supported"]
    req = request(1, 0, confirm_op, b"OEP?" + bytes([1, 1]))
    fixed = b"OEP!" + struct.pack("<BHIBI", 1, 1024, 4096, 4, 0x12345678)
    ans = answer(1, COMPLETED, 0, fixed + tlv(t_transport, b"\x00"))
    req_hi = request(2, 0, confirm_op, b"OEP?" + bytes([2, 3]))
    ans_hi = answer(2, REJECTED, REASON["unsupported"], b"\x00" + tlv(t_supported, bytes([1, 1])))
    return {
        "about": "confirm (core §7.1). The answer's values (max_frame 1024, window 4096, max_inflight 4, boot_id 0x12345678, transport index 0) are an example probe's.",
        "exchanges": [
            {"name": "revision 1 asked and answered", "request": {"corr": 1, "min_rev": 1, "max_rev": 1},
             "request_hex": hx(req), "request_serial_frame_hex": hx(serial_frame(req)),
             "request_length_frame_hex": hx(length_frame(req)),
             "answer": {"corr": 1, "revision": 1, "max_frame": 1024, "window": 4096, "max_inflight": 4,
                        "boot_id": 0x12345678, "transport": 0},
             "answer_hex": hx(ans), "answer_serial_frame_hex": hx(serial_frame(ans))},
            {"name": "no revision in the range: unsupported with the supported range",
             "request": {"corr": 2, "min_rev": 2, "max_rev": 3}, "request_hex": hx(req_hi),
             "answer": {"corr": 2, "reason": "unsupported", "payload_tag": 0, "supported": [1, 1]},
             "answer_hex": hx(ans_hi)},
        ],
    }


def core_extensions() -> dict:
    """Empty and nonempty fixed results share the same TLV extension rule."""
    s = 0x11223344
    named = REG["constants"]["tag_named_extension"]
    tail = tlv(named, bytes([15]) + b"io.example.note" + b"x")   # a named extension the reader does not know (core §2.2)
    rows = []
    cases = [
        ("open", "open", struct.pack("<IB", 3000, 0), s, struct.pack("<II", 3000, 0x12345678), COMPLETED, 0),
        ("keepalive", "keepalive", b"", s, b"", COMPLETED, 0),
        ("end", "end", b"", s, b"", COMPLETED, 0),
        ("clock", "clock", b"", 0, struct.pack("<IQ", 0x12345678, 100), COMPLETED, 0),
        ("no_session", "keepalive", b"", s, b"", REJECTED, REASON["no_session"]),
        ("result_lost", "clock", b"", s, b"", REJECTED, REASON["result_lost"]),
    ]
    for corr, (name, operation, payload, sid, fixed, resolution, detail) in enumerate(cases, 1):
        rows.append({"name": name + " with unknown response TLV", "spec": "core §2.3/4.2/4.3/6.4/7.6",
                     "operation": operation, "fixed_answer_bytes": len(fixed),
                     "request_hex": hx(request(corr, 0, op("core", operation), payload, sid)),
                     "answer_hex": hx(answer(corr, resolution, detail, fixed + tail))})
    # In a request (core §2.2): a name the probe does not know is ignored, or refused unsupported naming the tag as
    # received (0xFF) when critical; a name_len past the value is malformed, critical or not (the form before anything).
    clock = op("core", "clock")
    note = bytes([15]) + b"io.example.note" + b"x"
    broken = bytes([16]) + b"io.example.note"   # name_len 16, 15 bytes of name left
    requests = [
        ("clock with an unknown named extension in the request", tlv(named, note),
         answer(7, COMPLETED, 0, struct.pack("<IQ", 0x12345678, 100))),
        ("clock with an unknown critical named extension in the request", tlv(named | CRITICAL, note),
         answer(8, REJECTED, REASON["unsupported"], bytes([named | CRITICAL]))),
        ("clock with a named extension whose name_len passes its value", tlv(named, broken),
         answer(9, REJECTED, REASON["malformed"])),
        ("clock with a critical named extension whose name_len passes its value", tlv(named | CRITICAL, broken),
         answer(10, REJECTED, REASON["malformed"])),
    ]
    request_rows = []
    for corr, (name, tail_in, ans) in enumerate(requests, len(cases) + 1):
        request_rows.append({"name": name, "spec": "core §2.2/2.3/7.6", "operation": "clock", "fixed_answer_bytes": 12,
                     "request_hex": hx(request(corr, 0, clock, tail_in, 0)), "answer_hex": hx(ans)})
    return {"about": "Independent examples, not a sequential session. Successful calls have a valid session where needed; no_session has no active session; result_lost has discarded replay bytes. A named extension TLV (0x7F) of a name the reader does not know adds no behavior, and follows both empty and nonempty fixed result payloads (core §2.3). request_cases: in a request, an unknown name is ignored, or refused unsupported (0xFF) when critical, and a name_len past its value is malformed (core §2.2).", "cases": rows, "request_cases": request_rows}


def refusals() -> dict:
    """Requests and the answer a probe gives, for the refusals of core §2.3 and §4.3."""
    s = 0x11223344
    gpio_set = op("oep.fixture.gpio", "set")
    i2c_conf = op("oep.fixture.i2c-target", "configure")
    rv_attach = op("oep.wire.rvswd", "attach")
    uart_read = op("oep.fixture.uart", "read")
    dm_reset = op("oep.target.riscv-dm", "reset")
    unav = CORE["tlv"]["unavailable_payload"]
    fixed_attach = struct.pack("<BHHI", 0, 1, 2, 1_000_000)
    idx_tag = IFACE["oep.fixture.gpio"]["tlv"]["unavailable_payload"]["index"]
    cases = []

    def add(name, spec, fns, req, reason, payload=b"", completed=False):
        corr = struct.unpack_from("<H", req, 1)[0]
        ans = answer(corr, COMPLETED, 0, payload) if completed else answer(corr, REJECTED, REASON[reason], payload)
        cases.append({"name": name, "spec": spec, "fns": fns, "request_hex": hx(req),
                      "answer": "completed success" if completed else reason, "answer_hex": hx(ans)})

    fns_gpio = {"2": "oep.fixture.gpio"}
    add("gpio mode 8 (a value a later revision may define)", "core §2.5, §4.3; fixture §1", fns_gpio,
        request(0x0010, 2, gpio_set, bytes([1]) + struct.pack("<HB", 3, 8), s), "unsupported",
        b"\x00" + tlv(unav["channel"], struct.pack("<H", 3)) + tlv(idx_tag, b"\x00"))
    add("i2c-target address above 0x7F (excluded by the definition)", "core §4.3; fixture §3",
        {"3": "oep.fixture.i2c-target"}, request(0x0011, 3, i2c_conf, bytes([0x80]), s), "malformed")
    add("i2c-target address 0x03 (reserved by the I2C specification)", "core §4.3; fixture §3",
        {"3": "oep.fixture.i2c-target"}, request(0x0012, 3, i2c_conf, bytes([0x03]), s), "unsupported", b"\x00")
    add("attach method 2", "core §4.3; debug §3", {"4": "oep.wire.rvswd"},
        request(0x0013, 4, rv_attach, bytes([2]) + fixed_attach[1:], s), "unsupported", b"\x00")
    add("attach fixed body truncated before max_speed", "debug §1", {"4": "oep.wire.rvswd"},
        request(0x0014, 4, rv_attach, fixed_attach[:5], s), "malformed")
    add("an unknown critical TLV: its tag as received", "core §2.3", {"4": "oep.wire.rvswd"},
        request(0x0015, 4, rv_attach, fixed_attach + tlv(0x3E | CRITICAL, b""), s), "unsupported", bytes([0x3E | CRITICAL]))
    add("a TLV whose length runs past the end of the request", "core §2.2, §4.3", {"4": "oep.wire.rvswd"},
        request(0x0017, 4, rv_attach, fixed_attach + bytes([0x3E]) + struct.pack("<H", 8) + struct.pack("<I", 0), s), "malformed")
    add("read from 4", "core §2.5, §4.3; common §1.2", {"5": "oep.fixture.uart"},
        request(0x0018, 5, uart_read, bytes([4]) + struct.pack("<QH", 0, 64)), "unsupported", b"\x00")
    add("riscv-dm reset mode 3", "core §2.5, §4.3; debug §4.3", {"6": "oep.target.riscv-dm"},
        request(0x0019, 6, dm_reset, struct.pack("<IB", 1, 3), s), "unsupported", b"\x00")
    undefined_mode = max(IFACE["oep.target.riscv-dm"]["enum"]["reset_mode"].values()) + 1
    add("riscv-dm reset mode past the defined ones", "debug §4.3", {"6":"oep.target.riscv-dm"},
        request(0x001C,6,dm_reset,struct.pack("<IB",1,undefined_mode),s),"unsupported",b"\x00")
    add("attach max_speed zero", "debug §1", {"4":"oep.wire.rvswd"},
        request(0x001D,4,rv_attach,struct.pack("<BHHI",0,1,2,0),s),"malformed")
    add("attach halt method is not offered", "debug §3", {"4":"oep.wire.rvswd"},
        request(0x001E,4,rv_attach,struct.pack("<BHHI",1,1,2,1000000),s),"unsupported",b"\x00")
    add("confirm min_rev > max_rev", "core §7.1", {},
        request(0x001A, 0, op("core", "confirm"), b"OEP?" + bytes([2, 1])), "malformed")
    add("an unknown non-critical TLV is ignored", "core §2.3", fns_gpio,
        request(0x001B, 2, gpio_set, bytes([1]) + struct.pack("<HB", 3, 0) + tlv(0x3E, b"\x01"), s), "", completed=True)
    add("corr zero is malformed", "core §4.1, §4.3", {},
        request(0, 0, op("core", "clock"), b""), "malformed")
    return {
        "about": "Refusals (core §2.3, §4.3) and an ignored unknown TLV. `fns` says which interface each fn number is in the example "
                 "(the numbers come from list in a real session). Requests with session_id 0x11223344 come from the session that holds the lock; "
                 "the lock-free read and confirm carry session_id 0. "
                 "Every case assumes a state in which only the reason given applies (channel 3 is in fn 2's plan, the connections and streams exist), "
                 "so each request has one answer (core §4.3 order 4).",
        "cases": cases,
    }


def discovery() -> dict:
    """The example probe of docs/getting-started.ja.md §2, §3 (with fn 0's required ops, core §1.2): list (core §7.2), describe of fn 0 (core §7.3, §7.5) and the
    header refusals of core §4.3 order 1, continuing confirm.json's first exchange (corr 1)."""
    core = CORE
    list_op, describe_op = op("core", "list"), op("core", "describe")
    d = core["tlv"]["describe"]
    unit_id, max_op_ms = "a1b2c3d4", 1000
    t_index, t_kind, t_interface = 0, core["enum"]["transport_kind"]["uart_bridge"], 0xFF

    list_req = request(2, 0, list_op, struct.pack("<H", 0))
    list_ans = answer(2, COMPLETED, 0, struct.pack("<HB", 0, 0))                  # no interface; fn 0 is never listed (core §7.2)

    # core §1.2: fn 0's required ops, all set in ops
    offered = [op("core", n) for n in ("confirm", "list", "describe", "clock", "open", "end", "keepalive", "lock_state")]
    decl_tlvs = [tlv(REG["describe_common"]["ops"], ops_value(offered)), tlv(d["unit_id"], unit_id.encode()), tlv(d["transport"], bytes([t_index, t_kind, t_interface])),
                 tlv(d["max_op_ms"], struct.pack("<I", max_op_ms))]
    decl, n_decl = b"".join(decl_tlvs), len(decl_tlvs)
    desc_req = request(3, 0, describe_op, struct.pack("<HH", 0, 0))
    desc_ans = answer(3, COMPLETED, 0, b"\x00" + decl)
    past_req = request(4, 0, describe_op, struct.pack("<HH", 0, n_decl))
    past_ans = answer(4, COMPLETED, 0, b"\x00")

    no_fn = request(5, 7, 0x01, b"")
    no_op = request(6, 0, 0x50, b"")
    return {
        "about": "list, describe and the header refusals of the example probe (docs/getting-started.ja.md §2, §3, with its §6 steps 1 and 2 done): no interface (list is empty: "
                 "fn 0, the core, has no name and is never listed), fn 0's ops are the required ops of core §1.2 (confirm, list, describe, clock, open, end, keepalive, lock_state) in describe's common tag ops, one UART bridge (transport index 0, interface 0xFF), unit_id \"a1b2c3d4\", max_op_ms 1000. "
                 "The corrs continue confirm.json's first exchange (corr 1): list 2, describe 3, describe past the end 4, the refusals 5 and 6. "
                 "Those values are an example probe's.",
        "exchanges": [
            {"name": "list everything from the first", "spec": "core §7.2",
             "request": {"corr": 2, "first": 0},
             "request_hex": hx(list_req), "request_serial_frame_hex": hx(serial_frame(list_req)),
             "answer": {"corr": 2, "total": 0, "entries": []},
             "answer_hex": hx(list_ans), "answer_serial_frame_hex": hx(serial_frame(list_ans))},
            {"name": "describe fn 0 from the first", "spec": "core §7.3, §7.5",
             "request": {"corr": 3, "fn": 0, "first": 0},
             "request_hex": hx(desc_req), "request_serial_frame_hex": hx(serial_frame(desc_req)),
             "answer": {"corr": 3, "more": 0, "ops": offered, "unit_id": unit_id,
                        "transports": [{"index": t_index, "kind": t_kind, "interface": t_interface}],
                        "max_op_ms": max_op_ms},
             "answer_hex": hx(desc_ans), "answer_serial_frame_hex": hx(serial_frame(desc_ans))},
            {"name": "describe fn 0 from beyond the last: more 0 and no TLVs", "spec": "core §7.3 end of paging",
             "request": {"corr": 4, "fn": 0, "first": n_decl},
             "request_hex": hx(past_req), "answer": {"corr": 4, "more": 0}, "answer_hex": hx(past_ans)},
        ],
        "refusals": [
            {"name": "a fn the probe does not have", "spec": "core §4.3 order 1", "request": {"corr": 5, "fn": 7, "op": 0x01},
             "request_hex": hx(no_fn), "answer": "unknown_function",
             "answer_hex": hx(answer(5, REJECTED, REASON["unknown_function"]))},
            {"name": "an op fn 0 does not define", "spec": "core §1.2, §4.3 order 1", "request": {"corr": 6, "fn": 0, "op": 0x50},
             "request_hex": hx(no_op), "answer": "unknown_operation",
             "answer_hex": hx(answer(6, REJECTED, REASON["unknown_operation"]))},
        ],
    }



def ops_encoding() -> dict:
    """The value of the common describe tag ops (core §7.4) at its boundaries: base(u8) and a bitmap of 1 byte or more, base + 8 x bitmap
    bytes <= 256; valid values decode to their op set."""
    widest = ops_value([0x01, 0xFF])                       # the lowest and the highest op an interface may define (core §2.5)
    longest = bytes([0x00]) + bytes([0x01]) + bytes(30) + bytes([0x80])     # 33 bytes: base 0, bitmap 32 bytes (bits 0 and 255)
    cases = [
        ("the shortest: one op", bytes([0x01, 0x01]), "the smallest value, 2 bytes"),
        ("riscv-dm with ops 0x10-0x17 (the core's example)", bytes([0x10, 0xFF]), "core §7.4 example"),
        ("dmi, halt and resume only (the core's example)", bytes([0x10, 0x07]), "core §7.4 example"),
        ("ops 0x01 and 0xFF: the widest set, a 32-byte bitmap", widest, "base 0, highest 0xFF"),
        ("the longest value: 33 bytes, base 0 and a 32-byte bitmap", longest, "base + 8 x 32 = 256: the decoder limit only (op 0x00 is invalid, core §2.5)"),
        ("base + 8 x n = 256 exactly", bytes([0xF8, 0x01]), "the decoder limit only: 0xF8 is interface-owned (core §2.5)"),
        ("no bitmap: 1 byte", bytes([0x01]), "invalid length"),
        ("34 bytes", bytes([0x00, 0x01]) + bytes(31) + bytes([0x01]), "invalid length"),
        ("past op 0xFF: base 0xF9 with a 1-byte bitmap", bytes([0xF9, 0x01]), "base + 8 x n > 256"),
        ("past op 0xFF: base 0xF0 with a 3-byte bitmap", bytes([0xF0, 0x01, 0x00, 0x01]), "base + 8 x n > 256"),
        ("bit 0 clear: base below the lowest op", bytes([0x00, 0x02]), "valid: the same set as 01 01"),
        ("a trailing zero byte", bytes([0x01, 0x01, 0x00]), "valid: the same set as 01 01"),
    ]
    return {
        "about": "The value of describe's common tag ops (core §7.4): base(u8) and a bitmap of 1 byte or more, base + 8 x bitmap bytes <= 256 "
                 "(the bitmap never passes op 0xFF). `ops` is the decoded set of a valid value; one set may have several valid values.",
        "cases": [{"name": n, "note": note, "value_hex": hx(v), "valid": ops_decode(v) is not None, "ops": ops_decode(v)}
                  for n, v, note in cases],
    }


def sessions() -> dict:
    """Scenarios of the session decision table (core §6.2), the resend table (core §5.1) and the release at end (core §9), as
    request / answer byte pairs from a stated initial state, for the example probe of confirm.json (boot_id 0x12345678)."""
    open_op, end_op, keep_op, state_op, clock_op = (op("core", n) for n in ("open", "end", "keepalive", "lock_state", "clock"))
    boot_id, lease = 0x12345678, 2000

    def clocked(corr, uptime_ns):
        return answer(corr, COMPLETED, 0, struct.pack("<IQ", boot_id, uptime_ns))
    S, T = 0x11223344, 0x55667788
    owner_tag = CORE["tlv"]["lock_state_answer"]["owner"]

    def opened(corr):
        return answer(corr, COMPLETED, 0, struct.pack("<II", lease, boot_id))

    def rej(corr, reason, payload=b""):
        return answer(corr, REJECTED, REASON[reason], payload)

    def ok(corr, payload=b""):
        return answer(corr, COMPLETED, 0, payload)

    def step(note, req, ans):
        return {"note": note, "request_hex": hx(req), "answer_hex": hx(ans)}

    scenarios = [
        {"name": "end releases the session; its id is then no_session, and a resent end is answered from the table",
         "spec": "core §5.1, §6.2, §6.4, §9", "initial": "lock free, no session has held it since boot",
         "steps": [
             step("open S, lease 2000 ms, no force", request(1, 0, open_op, struct.pack("<IB", lease, 0), S), opened(1)),
             step("keepalive of S", request(2, 0, keep_op, b"", S), ok(2)),
             step("end of S: the lock and everything S created are released", request(3, 0, end_op, b"", S), ok(3)),
             step("the same end resent with the same corr: the remembered answer, nothing executed", request(3, 0, end_op, b"", S), ok(3)),
             step("a new request with S: no session holds the lock", request(4, 0, keep_op, b"", S), rej(4, "no_session")),
             step("lock_state with session_id 0: free", request(5, 0, state_op, b""), ok(5, struct.pack("<BI", 0, 0))),
         ]},
        {"name": "another session while the lock is held, then force",
         "spec": "core §6.2, §6.4", "initial": "lock free",
         "steps": [
             step("open S with owner \"cli\"", request(1, 0, open_op, struct.pack("<IB", lease, 0) + tlv(0x01, b"cli"), S), opened(1)),
             step("open T without force: locked, the remaining time (as if no time had passed) and the owner",
                  request(2, 0, open_op, struct.pack("<IB", lease, 0), T), rej(2, "locked", struct.pack("<I", lease) + tlv(owner_tag, b"cli"))),
             step("keepalive of T: locked", request(3, 0, keep_op, b"", T), rej(3, "locked", struct.pack("<I", lease) + tlv(owner_tag, b"cli"))),
             step("open T with force: S's resources are released, T holds the lock", request(4, 0, open_op, struct.pack("<IB", lease, 1), T), opened(4)),
             step("keepalive of S: locked (T holds it; T's open gave no owner)", request(5, 0, keep_op, b"", S), rej(5, "locked", struct.pack("<I", lease))),
         ]},
        {"name": "session_id 0 and a resent open", "spec": "core §4.1, §4.3 order 1, §6.1, §6.2", "initial": "lock free",
         "steps": [
             step("keepalive with session_id 0: an op that requires the lock", request(1, 0, keep_op, b""), rej(1, "session_required")),
             step("open with session_id 0", request(2, 0, open_op, struct.pack("<IB", lease, 0)), rej(2, "malformed")),
             step("open S", request(3, 0, open_op, struct.pack("<IB", lease, 0), S), opened(3)),
             step("the same open resent: replay the answer, without renewing the lease or clearing the history",
                  request(3, 0, open_op, struct.pack("<IB", lease, 0), S), opened(3)),
             step("lock_state with session_id 0: held, the remaining time as if no time had passed",
                  request(4, 0, state_op, b""), ok(4, struct.pack("<BI", 1, lease))),
         ]},
        {"name": "clock without a session and while a session holds the lock",
         "spec": "core §4.1, §6.3, §7.6", "initial": "lock free, no session has held it since boot",
         "steps": [
             step("clock with session_id 0, no session: boot_id and uptime_ns", request(1, 0, clock_op, b""), clocked(1, 2_000_000_000)),
             step("open S", request(2, 0, open_op, struct.pack("<IB", lease, 0), S), opened(2)),
             step("clock with session_id 0 while S holds the lock: answered, the session, lock and lease untouched",
                  request(3, 0, clock_op, b""), clocked(3, 2_001_000_000)),
             step("lock_state with session_id 0: still held by a session",
                  request(4, 0, state_op, b""), ok(4, struct.pack("<BI", 1, lease))),
             step("clock with S: a lock-free op of the session holding the lock", request(5, 0, clock_op, b"", S), clocked(5, 2_002_000_000)),
             step("end of S", request(6, 0, end_op, b"", S), ok(6)),
             step("clock with session_id 0 after end: answered as before", request(7, 0, clock_op, b""), clocked(7, 2_003_000_000)),
         ]},
    ]
    scenarios += [
        {"name": "session-zero traffic does not advance the session; open preserves replay history",
         "spec": "core §4.1, §5.1", "initial": "lock free; max_inflight 4",
         "steps": [
             step("open S", request(1, 0, open_op, struct.pack("<IB", lease, 0), S), opened(1)),
             step("keepalive S", request(2, 0, keep_op, b"", S), ok(2)),
             step("independent session-zero counter past half-cycle", request(40000, 0, clock_op, b""), clocked(40000, 2_000_000_000)),
             step("S still advances from 2 to 3", request(3, 0, keep_op, b"", S), ok(3)),
             step("new open S keeps the existing history", request(4, 0, open_op, struct.pack("<IB", lease, 0), S), opened(4)),
             step("keepalive 2 still replays", request(2, 0, keep_op, b"", S), ok(2)),
             step("same corr with altered bytes is malformed", request(2, 0, keep_op, bytes([0]), S), rej(2, "malformed")),
         ]},
        {"name": "16-bit counter wraps without releasing resources; an ended session cannot be reopened",
         "spec": "core §4.1, §5.1, §6.2", "initial": "lock free; max_inflight 4",
         "steps": [
             step("open S near the wrap boundary", request(65533, 0, open_op, struct.pack("<IB", lease, 0), S), opened(65533)),
             step("keepalive before wrap", request(65534, 0, keep_op, b"", S), ok(65534)),
             step("last nonzero corr", request(65535, 0, keep_op, b"", S), ok(65535)),
             step("wrap, skipping zero; S still holds the lock", request(1, 0, keep_op, b"", S), ok(1)),
             step("end S after wrap", request(2, 0, end_op, b"", S), ok(2)),
             step("new open of ended S is no_session", request(3, 0, open_op, struct.pack("<IB", lease, 0), S), rej(3, "no_session")),
             step("old end still replays without resurrecting resources", request(2, 0, end_op, b"", S), ok(2)),
             step("T starts a new counter, only after all S requests resolved", request(1, 0, open_op, struct.pack("<IB", lease, 0), T), opened(1)),
         ]},
        {"name": "evicted request returns result_lost instead of being executed",
         "spec": "core §5.1", "initial": "lock free; max_inflight 4; exactly four cache entries",
         "steps": [
             step("open S", request(1, 0, open_op, struct.pack("<IB", lease, 0), S), opened(1)),
             *[step("keepalive S", request(c, 0, keep_op, b"", S), ok(c)) for c in range(2, 6)],
             step("open 1 has fallen out; it must not reset history", request(1, 0, open_op, struct.pack("<IB", lease, 0), S), rej(1, "result_lost")),
         ]},
    ]
    return {
        "about": "Session scenarios (core §5.1, §6, §9) of the example probe of confirm.json (boot_id 0x12345678). Each scenario starts from its "
                 "initial state; the steps are sent in order on one transport, each answered before the next. Remaining times are shown as if no time "
                 "had passed between the steps: a real probe answers the time actually left. clock's uptime_ns values are an example probe's (a real probe answers its "
                 "clock read just before the answer, which does not decrease while boot_id is the same). S = 0x11223344, T = 0x55667788.",
        "scenarios": scenarios,
    }


def ops() -> dict:
    """Per-op byte vectors: a request, the probe state it assumes, and the answer, for ops of the interfaces. Each answer's
    fixed part is the one the interface document gives; sequences are count x element with no element length (core §2.3)."""
    S = 0x11223344
    cases = []

    def add(name, spec, fns, state, req, ans):
        cases.append({"name": name, "spec": spec, "fns": fns, "state": state, "request_hex": hx(req), "answer_hex": hx(ans)})

    ok = lambda corr, payload=b"": answer(corr, COMPLETED, 0, payload)
    failed = lambda corr, payload=b"": answer(corr, COMPLETED, REG["outcomes"]["failed"], payload)
    rej = lambda corr, reason, payload=b"": answer(corr, REJECTED, REASON[reason], payload)
    unav = CORE["tlv"]["unavailable_payload"]
    cause = CORE["enum"]["unavailable_cause"]

    # oep.probe.restart (oep-if-restart): restart requires the lock; the answer has no payload
    rs = {"11": "oep.probe.restart"}
    restart = op("oep.probe.restart", "restart")
    add("restart: completed success, sent before the probe restarts", "oep-if-restart §2", rs,
        "session S holds the lock; restart_max_ms in fn 11's describe; after this answer the probe restarts (a new boot_id, no session)",
        request(0x10, 11, restart, b"", S), ok(0x10))
    add("restart without a session: session_required", "core §4.1, §4.3 order 1; oep-if-restart §2", rs, "—",
        request(0x11, 11, restart, b""), rej(0x11, "session_required"))
    add("restart while no session holds the lock: no_session", "core §6.2; oep-if-restart §2, §3", rs,
        "lock free (for example: the probe has restarted since S opened)",
        request(0x12, 11, restart, b"", S), rej(0x12, "no_session"))

    # oep.probe.plan (oep-if-plan): role_assignment fn(u16) role(u8) channel(u16)
    pl = {"10": "oep.probe.plan", "2": "oep.fixture.gpio"}
    ra = IFACE["oep.probe.plan"]["tlv"]["plan_apply"]["role_assignment"]
    apply_, release = op("oep.probe.plan", "plan_apply"), op("oep.probe.plan", "plan_release")
    add("plan_apply: gpio role 1 on channel 3", "oep-if-plan §2.1", pl,
        "session S holds the lock; channel 3 free and in gpio's role_channels for role 1; plan_roles not exceeded",
        request(0x14, 10, apply_, tlv(ra, struct.pack("<HBH", 2, 1, 3)), S), ok(0x14))
    add("plan_apply naming fn 0: malformed", "oep-if-plan §2.4, core §4.3", pl, "session S",
        request(0x15, 10, apply_, tlv(ra, struct.pack("<HBH", 0, 1, 3)), S), rej(0x15, "malformed"))
    add("plan_apply naming a fn the probe does not have: unknown_function", "oep-if-plan §2.4, core §4.3", pl, "session S; no fn 12",
        request(0x16, 10, apply_, tlv(ra, struct.pack("<HBH", 12, 1, 3)), S), rej(0x16, "unknown_function"))
    add("plan_release: fn 2", "oep-if-plan §2.2", pl, "session S; fn 2 has the plan above",
        request(0x17, 10, release, bytes([1]) + struct.pack("<H", 2), S), ok(0x17))
    add("plan_release: n = 2 with one fn", "oep-if-plan §2.4, core §4.3", pl, "session S",
        request(0x18, 10, release, bytes([2]) + struct.pack("<H", 2), S), rej(0x18, "malformed"))
    add("plan_apply without a session: session_required", "core §4.1, §4.3 order 1", pl, "—",
        request(0x19, 10, apply_, tlv(ra, struct.pack("<HBH", 2, 1, 3))), rej(0x19, "session_required"))
    add('plan_apply: GPIO addition preserves an existing output', 'plan §2.1, fixture §1',pl,
        'session S; fn2 role1 channel3 is high; channel4 free; keep channel3 high and acquire only channel4',
        request(0x1A,10,apply_,tlv(ra,struct.pack('<HBH',2,1,3))+tlv(ra,struct.pack('<HBH',2,1,4)),S),ok(0x1A))
    up={'10':'oep.probe.plan','5':'oep.fixture.uart'}
    add('plan_apply: identical configured UART is unchanged','plan §2.1, fixture §2',up,
        'session S; fn5 RX on channel3 at 9600 baud, bytes retained; preserve baud and buffer',
        request(0x1B,10,apply_,tlv(ra,struct.pack('<HBH',5,1,3)),S),ok(0x1B))
    add('plan_apply: configured UART channel change is refused','plan §2.1, fixture §2',up,
        'session S; fn5 RX on channel3 at 9600 baud; channel4 allowed; all old state remains',
        request(0x1C,10,apply_,tlv(ra,struct.pack('<HBH',5,1,4)),S),rej(0x1C,'unavailable',tlv(1,b'\x06')))
    add('plan_apply: active capture channel change is refused','plan §2.1, capture §3.2',
        {'10':'oep.probe.plan','9':'oep.fixture.logic'},'session S; fn9 state3, role0 channel1; preserve capture and data',
        request(0x1D,10,apply_,tlv(ra,struct.pack('<HBH',9,0,2)),S),rej(0x1D,'unavailable',tlv(1,b'\x06')))

    add('plan_apply: active capture identical assignment is unchanged','plan §2.1, capture §3.2',
        {'10':'oep.probe.plan','9':'oep.fixture.logic'},'session S; fn9 state3, role0 channel1; preserve capture and data',
        request(0x1E,10,apply_,tlv(ra,struct.pack('<HBH',9,0,1)),S),ok(0x1E))
    for corr, name, roles in ((0xF0,'oep.fixture.uart',[1]),
                              (0xF1,'oep.fixture.i2c-target',[1,2]),
                              (0xF2,'oep.fixture.spi-target',[1,2,3,4])):
        bindings = b''.join(tlv(ra,struct.pack('<HBH',5,role,role+2)) for role in roles)
        add(f'plan_apply: {name} refuses output idle','core §8, plan §2.1',
            {'10':'oep.probe.plan','5':name},
            'session S; all roles/channels supported and otherwise free; channel3 idle high in volatile config; no pin changes',
            request(corr,10,apply_,bindings,S),rej(corr,'unavailable',tlv(1,bytes([5]))+tlv(2,struct.pack('<H',3))))
    add('plan_apply: GPIO accepts output idle without changing level','core §8, fixture §1',pl,
        'session S; channel3 idle high in volatile config; role1 channel3 supported; keep idle high until set',
        request(0xF3,10,apply_,tlv(ra,struct.pack('<HBH',2,1,3)),S),ok(0xF3))

    # oep.probe.link (oep-if-link §1, §2)
    link = {"1": "oep.probe.link"}
    add("link source: 8 bytes, byte k = k & 0xFF", "oep-if-link §2", link, "max_frame 1024",
        request(0x20, 1, op("oep.probe.link", "source"), struct.pack("<I", 8)), ok(0x20, struct.pack("<H", 8) + bytes(range(8))))
    most = 1024 - 5 - 2                                                 # the answer's header and len (oep-if-link §2)
    add("link source: more than fits, len = max_frame - 7", "oep-if-link §2", link, "max_frame 1024",
        request(0x25, 1, op("oep.probe.link", "source"), struct.pack("<I", 2000)),
        ok(0x25, struct.pack("<H", most) + bytes(k & 0xFF for k in range(most))))
    add("link source: length 0", "oep-if-link §2", link, "—",
        request(0x21, 1, op("oep.probe.link", "source"), struct.pack("<I", 0)), ok(0x21, struct.pack("<H", 0)))
    add("link sink: 3 bytes, an empty answer", "oep-if-link §2", link, "—",
        request(0x22, 1, op("oep.probe.link", "sink"), struct.pack("<H", 3) + b"\xaa\xbb\xcc"), ok(0x22))
    add("link sink: count larger than the bytes that follow", "oep-if-link §2, core §4.3", link, "—",
        request(0x23, 1, op("oep.probe.link", "sink"), struct.pack("<H", 5) + b"\xaa\xbb\xcc"), rej(0x23, "malformed"))
    add("link port_speed not offered (not set in ops)", "oep-if-link §1, core §1.2", link, "ops of fn 1: source and sink only",
        request(0x24, 1, op("oep.probe.link", "port_speed"), struct.pack("<IBH", 921600, 0, 2000), S), rej(0x24, "unknown_operation"))
    add("link port_state: cached try success no longer describes the route", "link §1/3", link,
        "UART bridge, expired try, now boot baud; old try success921600 exists in replay cache",
        request(0x25,1,op("oep.probe.link","port_state"),b""),ok(0x25,struct.pack("<IB",115200,0)))
    add("link port_state: session-ended fallback waits for old frame", "link §3", link,
        "UART bridge at921600, previous owner ended; frame in progress; phase3 is never cancelled",
        request(0x26,1,op("oep.probe.link","port_state"),b""),ok(0x26,struct.pack("<IB",921600,3)))

    for step in (0, 1, 2):
        corr = 0x110 + step
        add(f'link port_speed: verify fallback pending refuses step {step}', 'link §3', link,
            'session S live on this route; phase3 at921600 after try verify expiry; old notification frame still draining; refusal does not cancel fallback or change baud',
            request(corr,1,op('oep.probe.link','port_speed'),struct.pack('<IBH',921600,step,2000),S),
            rej(corr,'unavailable',tlv(1,bytes([6]))))
        corr = 0x113 + step
        add(f'link port_speed: idle fallback pending refuses step {step}', 'link §3', link,
            'session S remains original owner; phase3 at921600 due only to committed idle expiry; phase3 is never cancelled; refusal does not change baud',
            request(corr,1,op('oep.probe.link','port_speed'),struct.pack('<IBH',921600,step,2000),S),
            rej(corr,'unavailable',tlv(1,bytes([6]))))
    add('link port_speed: ended session checked before pending phase', 'core §4.3, link §3', link,
        'session S ended; phase3 waits for old frame; no session owner; no state or baud change',
        request(0x116,1,op('oep.probe.link','port_speed'),struct.pack('<IBH',921600,2,2000),S),
        rej(0x116,'no_session'))

    # oep.fixture.gpio (fixture §1)
    gpio = {"2": "oep.fixture.gpio"}
    gset, gread = op("oep.fixture.gpio", "set"), op("oep.fixture.gpio", "read")
    gidx = IFACE["oep.fixture.gpio"]["tlv"]["unavailable_payload"]["index"]
    add("gpio set: channel 3 output high", "fixture §1", gpio, "session S holds the lock; channel 3 in fn 2's plan; modes 0 to 4 declared",
        request(0x30, 2, gset, bytes([1]) + struct.pack("<HB", 3, 4), S), ok(0x30))
    add("gpio read: channel 3 reads 1", "fixture §1", gpio, "as above, after the set; Probe-selected output strength",
        request(0x31, 2, gread, bytes([1]) + struct.pack("<H", 3)), ok(0x31, bytes([1, 1])))
    add("gpio set: channel 9 not in the plan", "fixture §1, core §4.3", gpio, "channel 9 in no plan of fn 2",
        request(0x32, 2, gset, bytes([2]) + struct.pack("<HBHB", 3, 4, 9, 0), S),
        rej(0x32, "unavailable", tlv(unav["channel"], struct.pack("<H", 9)) + tlv(gidx, b"\x01")))
    add("gpio set without a session: session_required", "core §4.1, §4.3 order 1", gpio, "—",
        request(0x33, 2, gset, bytes([1]) + struct.pack("<HB", 3, 4)), rej(0x33, "session_required"))
    add("gpio set: n = 2 with one element", "core §4.3", gpio, "—",
        request(0x34, 2, gset, bytes([2]) + struct.pack("<HB", 3, 4), S), rej(0x34, "malformed"))

    uart={'5':'oep.fixture.uart'}
    add('UART status: unconfigured has no implicit baud','fixture §2',uart,
        'RX plan exists; configure not called; no UART reception or hidden preset application',
        request(0x35,5,op('oep.fixture.uart','status'),b''),ok(0x35,bytes(5)))
    add('UART read: unconfigured uses the normal read, nothing retained','fixture §2, common §1.2',uart,
        'RX plan exists; not configured; boot-scoped write position7, no retained bytes',
        request(0x36,5,op('oep.fixture.uart','read'),struct.pack('<BQH',1,0,48)),ok(0x36,struct.pack('<QBH',7,0,0)))
    add('UART configure: zero baud is malformed','fixture §2',uart,'session S; RX plan exists; state unchanged',
        request(0x37,5,op('oep.fixture.uart','configure'),bytes(4),S),rej(0x37,'malformed'))
    # configure failure (fixture §0, §2): completed failed with baud 0, never partial; the plan, retained data and positions stay
    add('UART configure: initialization failure answers baud 0','fixture §0, §2',uart,
        'session S; RX plan exists; configured at 9600 8N1; baud 115200 accepted but the driver fails to start; '
        'reception stops, unsent TX is dropped, the plan stays; afterwards unconfigured',
        request(0x38,5,op('oep.fixture.uart','configure'),struct.pack('<I',115200),S),failed(0x38,struct.pack('<I',0)))
    add('UART status: after a failed configure, baud 0 and format 0','fixture §2',uart,
        'the configure above failed; no new configure',
        request(0x39,5,op('oep.fixture.uart','status'),b''),ok(0x39,bytes(5)))
    add('UART read: retained bytes stay readable after a failed configure','fixture §2, common §1.2',uart,
        'the configure above failed; "abcd" received before it at positions 3 to 6 (3 pushed out before), write position 7',
        request(0x3A,5,op('oep.fixture.uart','read'),struct.pack('<BQH',1,0,48)),ok(0x3A,struct.pack('<QBH',3,0,4)+b'abcd'))
    add('UART read: unconfigured, from 0 at a pushed-out position sets gap','fixture §2, common §1.2',uart,
        'TX-only plan, not receiving; the earlier RX plan received 7 bytes and was released; write position 7, no retained bytes',
        request(0x3B,5,op('oep.fixture.uart','read'),struct.pack('<BQH',0,2,48)),ok(0x3B,struct.pack('<QBH',7,2,0)))
    add('UART configure: undeclared format is refused, configuration unchanged','fixture §0, §2',uart,
        'session S; RX plan exists; configured at 9600 8N1; formats declares 8N1 only; no setting, queue or pin changes',
        request(0x3C,5,op('oep.fixture.uart','configure'),struct.pack('<I',9600)+tlv(IFACE['oep.fixture.uart']['tlv']['configure']['format'],b'\x10'),S),
        rej(0x3C,'unsupported',bytes([IFACE['oep.fixture.uart']['tlv']['configure']['format']])))

    # oep.fixture.i2c-target configure (fixture §0, §3): no fixed part either way; a failure leaves state 0 with emptied queues and counters
    i2c = {"3": "oep.fixture.i2c-target"}
    i2c_cfg = op("oep.fixture.i2c-target", "configure")
    add("i2c-target configure: success has no fixed part", "fixture §3", i2c,
        "session S; fn 3 has its SDA/SCL plan; address 0x42; state 1 once answered",
        request(0x93, 3, i2c_cfg, bytes([0x42]), S), ok(0x93))
    add("i2c-target configure: initialization failure, no fixed part", "fixture §0, §3", i2c,
        "session S; running with 2 frames queued, rx_frames 5, 1 slot preloaded, errors 1, stretch 50 us; the driver fails to start; "
        "back to state 0, queue and slots emptied, rx_frames and errors 0, stretch kept, plan kept",
        request(0x94, 3, i2c_cfg, bytes([0x42]), S), failed(0x94))
    add("i2c-target status: after a failed configure, state 0 and everything cleared", "fixture §3", i2c,
        "the configure above failed",
        request(0x95, 3, op("oep.fixture.i2c-target", "status"), b""), ok(0x95, struct.pack("<BBIBI", 0, 0, 0, 0, 0)))
    add("i2c-target read_rx: state 0 after a failed configure is unavailable", "fixture §3", i2c,
        "session S; the configure above failed",
        request(0x96, 3, op("oep.fixture.i2c-target", "read_rx"), b"", S),
        rej(0x96, "unavailable", tlv(unav["cause"], bytes([6]))))

    # oep.wire.rvswd (debug §1 to §3)
    rv = {"4": "oep.wire.rvswd"}
    scheme = REG["common"]["enum"]["target_id_scheme"]["dmi_7f"]
    entry = struct.pack("<IHHIBB", 1, 0x0001, 0x0002, 1_000_000, scheme, 4) + struct.pack("<I", 0x00203500)
    # every rvswd answer says how the connection rests (debug §3.1): these targets' families are not in idle_low_family
    rest_tags = IFACE["oep.wire.rvswd"]["tlv"]
    high = bytes([IFACE["oep.wire.rvswd"]["enum"]["idle_clock"]["high"]])
    rest_entry0 = tlv(rest_tags["connections_answer"]["idle_clock"], bytes([0]) + high)
    rest_attach = tlv(rest_tags["attach_answer"]["idle_clock"], high)
    add("rvswd connections: one connection with a target_id", "debug §2.1", rv,
        "connection 1 on channels 1 / 2 at 1 MHz, owned by the session, target_id scheme 1 = 0x00203500, resting high",
        request(0x40, 4, op("oep.wire.rvswd", "connections"), bytes([0])), ok(0x40, bytes([0, 1]) + entry + rest_entry0))
    add("rvswd connections: first beyond the count", "core §7.3 end of paging, debug §2.1", rv, "as above",
        request(0x41, 4, op("oep.wire.rvswd", "connections"), bytes([1])), ok(0x41, bytes([0, 0])))
    kind = IFACE["oep.wire.rvswd"]["enum"]["scan_kind"]["riscv_dm"]
    add("rvswd scan: one combination listed and found", "debug §1, §3", rv, "session S; channels 1 / 2 free and allowed; a DM answers DMSTATUS 0x00400382",
        request(0x42, 4, op("oep.wire.rvswd", "scan"), bytes([1]) + struct.pack("<HH", 1, 2), S),
        ok(0x42, bytes([1, 1]) + struct.pack("<BHHI", kind, 1, 2, 0x00400382)))
    add("rvswd scan: count 0 is malformed", "debug §1", rv, "session S; no implicit candidate list",
        request(0x43, 4, op("oep.wire.rvswd", "scan"), bytes([0]), S), rej(0x43, "malformed"))
    fixed_attach = struct.pack("<BHHI", 0, 1, 2, 1_000_000)
    add("rvswd attach: a short fixed body is malformed", "debug §1", rv, "session S; channels free",
        request(0x44, 4, op("oep.wire.rvswd", "attach"), fixed_attach[:3], S), rej(0x44, "malformed"))
    add("rvswd attach: a second target on separate pins", "debug §1", rv,
        "session S owns connection 1 on pins 1 / 2; max_connections 2; pins 3 / 4 allowed and free; next resource 2",
        request(0x45, 4, op("oep.wire.rvswd", "attach"), struct.pack("<BHHI", 0, 3, 4, 1_000_000), S),
        ok(0x45, struct.pack("<IIBI", 2, 0x00400382, 0, 1_000_000) + rest_attach))
    add("rvswd attach: a resource ID above u16", "debug §1, core §9", rv,
        "session S; 65535 resources were created and closed; next resource 65536; pins 3 / 4 allowed and free",
        request(0x47, 4, op("oep.wire.rvswd", "attach"), struct.pack("<BHHI", 0, 3, 4, 1_000_000), S),
        ok(0x47, struct.pack("<IIBI", 65536, 0x00400382, 0, 1_000_000) + rest_attach))
    add("rvswd attach: busy pins never join or evict", "debug §1, core §8.1", rv,
        "session S owns connection 1 on pins 1 / 2; connection remains unchanged",
        request(0x46, 4, op("oep.wire.rvswd", "attach"), fixed_attach, S),
        rej(0x46, "unavailable", tlv(1, bytes([1])) + tlv(2, struct.pack("<H", 1))))

    swd = {"5":"oep.wire.swd"}
    selector = IFACE["oep.wire.swd"]["tlv"]["attach"]["targetsel"]
    selected = IFACE["oep.wire.swd"]["tlv"]["connections_answer"]["selected_target"]
    dpidr_scheme = REG["common"]["enum"]["target_id_scheme"]["dpidr"]
    swd_entry = struct.pack("<IHHIBBI",65536,1,2,1000000,dpidr_scheme,4,0x2BA01477)
    add("swd connections: read identity and supplied selector are distinct", "debug §2.1, §5", swd,
        "connection 65536, DPIDR 0x2BA01477 read on attach; Host supplied TARGETSEL 0x01000001",
        request(0x48,5,op("oep.wire.swd","connections"),b"\0"),
        ok(0x48,b"\0\1"+swd_entry+tlv(selected,struct.pack("<BI",0,0x01000001))))
    add("swd attach: another selector on occupied pins is refused before selection", "debug §1, §5", swd,
        "connection 65536 on pins 1/2 at TARGETSEL 0x01000001 remains selected and unchanged",
        request(0x49,5,op("oep.wire.swd","attach"),fixed_attach+tlv(selector|CRITICAL,struct.pack("<I",0x01000002)),S),
        rej(0x49,"unavailable",tlv(1,b"\1")+tlv(2,struct.pack("<H",1))))

    # oep.target.riscv-dm (debug §4)
    dm = {"6": "oep.target.riscv-dm"}
    add("riscv-dm halt not offered by raw-only fn", "debug §4", dm, "fn 6 declares only dmi in ops",
        request(0x5B,6,op("oep.target.riscv-dm","halt"),struct.pack("<I",1),S),rej(0x5B,"unknown_operation"))
    reset_halt = (struct.pack('<BBI',1,0x10,0x80000003) + struct.pack('<BBI',1,0x10,0x80000001)
                  + struct.pack('<BBI',1,0x10,0x90000001)
                  + struct.pack('<BBIIH',3,0x11,0x200,0x200,16) + struct.pack('<BBI',1,0x10,1))
    add('riscv-dm dmi: reset and halt wait in one request','debug §4.1, §4.6',dm,
        'connection1; dmseq console open; raw-only fn; host acknowledges havereset while keeping haltreq; allhalted observed on first wait read with DMSTATUS0x00000382 (version 2, authenticated, all/anyhalted: a live link never reads version 0); no console poll inside request; host reopens console to resync',
        request(0xF4,6,op('oep.target.riscv-dm','dmi'),struct.pack('<IH',1,5)+reset_halt,S),
        ok(0xF4,struct.pack('<HBHI',5,0,1,0x00000382)))
    add("riscv-dm write_block: memory written but cleanup lost the line", "debug §4", dm,
        "two words completed; restoring saved DATA failed; response is sent then connection 1 and its streams close",
        request(0x5C,6,op("oep.target.riscv-dm","write_block"),struct.pack("<IIHII",1,0x20000000,2,7,8),S),
        answer(0x5C,COMPLETED,2,struct.pack("<HB",2,REG["status"]["line"])))
    add("riscv-dm dmi: connection closed after incomplete cleanup", "debug §4, core §4.3", dm,
        "connection 1 closed after the previous high-level op failed cleanup; no target access",
        request(0x5D,6,op("oep.target.riscv-dm","dmi"),struct.pack("<IH",1,0),S),rej(0x5D,"no_resource"))
    add("riscv-dm halt: halted", "debug §4.2", dm, "session S; connection 1 open; the hart halts",
        request(0x50, 6, op("oep.target.riscv-dm", "halt"), struct.pack("<I", 1), S), ok(0x50, bytes([REG["status"]["ok"]])))
    add("riscv-dm halt on an unknown connection", "core §4.3", dm, "no connection 9",
        request(0x51, 6, op("oep.target.riscv-dm", "halt"), struct.pack("<I", 9), S), rej(0x51, "no_resource"))
    add("riscv-dm run not offered", "debug §4, core §1.2", dm, "ops of fn 6: dmi only (07 02 00 10 01)",
        request(0x52, 6, op("oep.target.riscv-dm", "run"), struct.pack("<IIIBB", 1, 0x20000000, 100, 0, 0), S), rej(0x52, "unknown_operation"))
    run_stopped = IFACE["oep.target.riscv-dm"]["enum"]["run_stopped"]
    add("riscv-dm run: the preparation fails, the hart is not run", "debug §4.4", dm,
        "session S; connection 1; run offered in ops; the hart is halted and writing a0 fails with no answer from the wire",
        request(0x56, 6, op("oep.target.riscv-dm", "run"), struct.pack("<IIIB", 1, 0x20000000, 100, 1) + struct.pack("<HI", 0x100A, 7) + bytes([0]), S),
        failed(0x56, struct.pack("<BBIIB", REG["status"]["line"], run_stopped["not_run"], 0, 0, 0)))
    rd = op("oep.target.riscv-dm", "dmi")
    add("riscv-dm dmi: one read of DMSTATUS", "debug §4.1", dm, "session S; connection 1; DMSTATUS reads 0x00400382",
        request(0x53, 6, rd, struct.pack("<IH", 1, 1) + bytes([IFACE["oep.target.riscv-dm"]["enum"]["dmi_step"]["read"], 0x11]), S),
        ok(0x53, struct.pack("<HBHI", 1, 0, 1, 0x00400382)))
    add("riscv-dm dmi: n = 0", "debug §4", dm, "session S; connection 1",
        request(0x54, 6, rd, struct.pack("<IH", 1, 0), S), ok(0x54, struct.pack("<HBH", 0, 0, 0)))
    add("riscv-dm dmi: an unknown step kind", "debug §4.1, core §4.3", dm, "—",
        request(0x55, 6, rd, struct.pack("<IH", 1, 1) + bytes([0x10, 0x11]), S), rej(0x55, "unsupported", b"\x00"))
    add("riscv-dm dmi: a known write before an unknown kind is not executed", "debug §4.1, core §4.3", dm,
        "session S; connection 1; no target register is changed",
        request(0x5A, 6, rd, struct.pack("<IH", 1, 2) + bytes([1, 0x04]) + struct.pack("<I", 7) + bytes([0x10]), S),
        rej(0x5A, "unsupported", b"\x00"))

    add("riscv-dm step on a running hart: status state, moved and both dpc 0", "debug §4.2", dm,
        "session S; connection 1; step offered in ops; the hart is running",
        request(0x57, 6, op("oep.target.riscv-dm", "step"), struct.pack("<I", 1), S),
        failed(0x57, struct.pack("<BBII", REG["status"]["state"], 0, 0, 0)))
    adi = {"15": "oep.target.arm-adi"}
    add("arm-adi transfer: n = 0", "debug §6", adi, "session S; connection 1 (swd) open",
        request(0x58, 15, op("oep.target.arm-adi", "transfer"), struct.pack("<IH", 1, 0), S),
        ok(0x58, struct.pack("<HBBH", 0, REG["status"]["ok"], 0, 0)))
    add("arm-adi transfer: a connection ID above u16", "debug §6, core §9", adi,
        "session S; connection 65536 (swd) open; zero transfers",
        request(0x59, 15, op("oep.target.arm-adi", "transfer"), struct.pack("<IH", 65536, 0), S),
        ok(0x59, struct.pack("<HBBH", 0, REG["status"]["ok"], 0, 0)))
    add("arm-adi transfer: reserved req bits do not execute an earlier write", "debug §6, core §4.3", adi,
        "session S; connection 1; no wire transfer is executed",
        request(0x5B, 15, op("oep.target.arm-adi", "transfer"),
                struct.pack("<IH", 1, 2) + bytes([0]) + struct.pack("<I", 7) + bytes([0x12]), S),
        rej(0x5B, "unsupported", b"\x00"))

    # oep.target.console (console §1, common §1)
    con = {"7": "oep.target.console"}
    console_ops = {op_name: op('oep.target.console', op_name) for op_name in ('open','read','marks','write')}
    minimal_console = 'session S; connection 65536 (rvswd); fn 7 mechanism list [sdi] (sdi = 1); ops open/read/close/streams; no marks or TX queue'
    add('console open: RX-only SDI without flags', 'console §1', con, minimal_console,
        request(0x6A,7,console_ops['open'],struct.pack('<IB',65536,1),S),ok(0x6A,struct.pack('<I',65537)))
    add('console marks: absent on RX-only console', 'console §1, core §1.2', con,minimal_console,
        request(0x6B,7,console_ops['marks'],struct.pack('<II',65537,0)),rej(0x6B,'unknown_operation'))
    add('console write: absent on RX-only console', 'console §1, core §1.2', con,minimal_console,
        request(0x6C,7,console_ops['write'],struct.pack('<IH',65537,1)+b'x',S),rej(0x6C,'unknown_operation'))
    add('console read: from3 without marks is unsupported', 'console §1, common §1.2', con,minimal_console+'; stream 65537 open',
        request(0x6D,7,console_ops['read'],struct.pack('<IBQH',65537,3,0,48)),rej(0x6D,'unsupported',b'\0'))
    add('console write: SDI is unsupported even if other mechanisms can write', 'console §1', con,
        'session S; stream 65537 is SDI; fn7 also provides dmseq and write',
        request(0x6E,7,console_ops['write'],struct.pack('<IH',65537,1)+b'x',S),rej(0x6E,'unsupported',b'\0'))
    mark_kind = REG["common"]["enum"]["mark_kind"]
    mark = struct.pack("<IQBQB", 0, 0, mark_kind["host"], 1_000_000, 0)
    # connection 1 (the wire cases) and the stream share core §9's one number space: the stream opened on it is 2
    add("console marks: one host mark", "common §1.3, console §1", con, "stream 2 with one explicit host mark (serial 0, position 0, value 0 at 1 ms); marks/mark offered",
        request(0x60, 7, op("oep.target.console", "marks"), struct.pack("<II", 2, 0)), ok(0x60, bytes([0, 1]) + mark))
    # serial paging (common §1.3): marks 5 to 8 kept (1 to 4 pushed out), next 9; max_frame 64 fits 2 marks (5 + 2 + 2 x 22 = 51)
    hm = lambda n: struct.pack("<IQBQB", n, 10 * n, mark_kind["host"], 1_000_000 * n, n)
    kept = "stream 2; marks 5 to 8 kept (1 to 4 pushed out), the next mark gets serial 9; max_frame 64 (2 marks per answer)"
    mk = op("oep.target.console", "marks")
    add("console marks: from_serial included, more 1", "common §1.3 paging 1, 4", con, kept,
        request(0x64, 7, mk, struct.pack("<II", 2, 5)), ok(0x64, bytes([1, 2]) + hm(5) + hm(6)))
    add("console marks: the next page from the last serial + 1", "common §1.3 paging 4", con, kept,
        request(0x65, 7, mk, struct.pack("<II", 2, 7)), ok(0x65, bytes([0, 2]) + hm(7) + hm(8)))
    add("console marks: a pushed-out from_serial starts at the oldest kept", "common §1.3 paging 3", con, kept,
        request(0x66, 7, mk, struct.pack("<II", 2, 3)), ok(0x66, bytes([1, 2]) + hm(5) + hm(6)))
    add("console marks: from_serial = next, no marks and more 0", "common §1.3 paging 2", con, kept,
        request(0x67, 7, mk, struct.pack("<II", 2, 9)), ok(0x67, bytes([0, 0])))
    # the console's mechanism list (core §7.7): [sdi, dmdata, dmseq], so dmseq is 3
    DMSEQ = 1 + list(IFACE["oep.target.console"]["names"]["mechanism"]).index("dmseq")
    sentry = struct.pack("<IIB", 2, 1, DMSEQ)
    add("console streams: one open stream", "console §1, core §9", con, "fn 7 mechanism list [sdi, dmdata, dmseq]; stream 2 on connection 1 (one number space: connection 1, then stream 2), dmseq, opened by the session",
        request(0x61, 7, op("oep.target.console", "streams"), struct.pack("<H", 0)), ok(0x61, bytes([0, 1]) + sentry))
    add("console streams: resource IDs above u16", "console §1, core §9", con,
        "fn 7 mechanism list [sdi, dmdata, dmseq]; stream 65537 on connection 65536; one open dmseq stream",
        request(0x69, 7, op("oep.target.console", "streams"), struct.pack("<H", 0)),
        ok(0x69, bytes([0, 1]) + struct.pack("<IIB", 65537, 65536, DMSEQ)))
    add("console streams: first(u16) beyond the count, the last page", "console §1, core §7.3 end of paging", con, "as above (one stream)",
        request(0x68, 7, op("oep.target.console", "streams"), struct.pack("<H", 1)), ok(0x68, bytes([0, 0])))
    add("console read: empty at the write position", "common §1.2", con, "stream 2, 5 bytes written (position 5)",
        request(0x62, 7, op("oep.target.console", "read"), struct.pack("<IBQH", 2, 0, 5, 64)),
        ok(0x62, struct.pack("<QBH", 5, 0, 0)))
    add("console read from 4", "common §1.2, core §4.3", con, "—",
        request(0x63, 7, op("oep.target.console", "read"), struct.pack("<IBQH", 2, 4, 0, 64)), rej(0x63, "unsupported", b"\x00"))

    # Settings (core §13): fn 0's optional ops; values named by (fn, the fn's item number, key). Every case's probe declares,
    # in fn 0's describe, the core's items in the registry's order, and fn 3 (io.example.board) one item of its own.
    SET_ORDER = list(CORE["settings"])
    NUM = {name: k + 1 for k, name in enumerate(SET_ORDER)}
    decl = ("fn 0 settings: " + ", ".join(f"{NUM[n]} {n}" for n in SET_ORDER)
            + " (wifi keys 4, label max_len 32, passphrase max_len 64); netif list [wifi] (wifi = 1); channels 8; "
            + "fn 8 io.example.board: 1 ntp-server (text, key_kind none, max_len 32)")
    ce = CORE["enum"]
    item_tag = CORE["tlv"]["unsupported_payload"]["item"]
    pc = {"0": "core", "8": "io.example.board"}
    pc_set, pc_get, pc_unset, pc_state, pc_save = (op("core", n) for n in ("set", "get", "unset", "state", "save"))
    def it(name, key, data=b"", fn=0):
        """A set value: fn(u16) number(u8) key(u16) len(u16) data."""
        number = NUM[name] if isinstance(name, str) else name
        return struct.pack("<HBHH", fn, number, key, len(data)) + data
    got = it   # a get value has the set value's form: fn(u16) number(u8) key(u16) len(u16) data (core §13.5)
    def unset(*values):
        return bytes([len(values)]) + b"".join(struct.pack("<HBH", fn, NUM[name], key) for fn, name, key in values)
    idle = it("channel.{}.idle", 4, bytes([ce["channel_idle"]["hi_z"]]))
    add("settings state: no saved settings", "core §13.7", pc, f"{decl}; save and state offered; no saved settings",
        request(0x70, 0, pc_state, b""), ok(0x70, bytes(6)))
    add("settings save not offered", "core §13.7", pc, f"{decl}; get/set/unset only; no storage",
        request(0x71, 0, pc_save, b"", S), rej(0x71, "unknown_operation"))
    add("settings state not offered", "core §13.7", pc, f"{decl}; get/set/unset only; no storage/state",
        request(0x7D, 0, pc_state, b""), rej(0x7D, "unknown_operation"))
    add("settings set: idle with an extra byte is malformed", "core §13.3", pc, f"{decl}; no values, generation1 unchanged",
        request(0x72, 0, pc_set, b"\1" + it("channel.{}.idle", 4, b"\0\xff"), S), rej(0x72, "malformed"))
    add("settings set: item number 0 is malformed", "core §13.5", pc, f"{decl}; no values, generation1",
        request(0x73, 0, pc_set, b"\1" + it(0, 4, b"\0"), S), rej(0x73, "malformed"))
    for number, corr in ((len(SET_ORDER) + 1, 0x74), (0x87, 0x75)):
        add(f"settings set: item number {number} past the settings is unsupported", "core §13.5", pc, f"{decl}; no settings/pin change",
            request(corr, 0, pc_set, b"\1" + it(number, 4, b"\0"), S), rej(corr, "unsupported", b"\0" + tlv(item_tag, b"\0")))
    add("settings set: unknown outer noncritical TLV ignored", "core §13.5, §2.3", pc, f"{decl}; no values, generation1",
        request(0x76, 0, pc_set, b"\1" + idle + tlv(0x3E, b"x"), S), ok(0x76, struct.pack("<I", 2)))
    add("settings get: count separates values from response extensions", "core §13.5", pc, f"{decl}; one idle value, generation2",
        request(0x77, 0, pc_get, struct.pack("<H", 0)),
        ok(0x77, struct.pack("<BIB", 0, 2, 1) + got("channel.{}.idle", 4, bytes([ce["channel_idle"]["hi_z"]]))
           + tlv(0x7F, bytes([15]) + b"io.example.note" + b"x")))
    add("settings get: final empty page still has count and generation", "core §13.5", pc, f"{decl}; one value generation2; first1",
        request(0x78, 0, pc_get, struct.pack("<H", 1)), ok(0x78, struct.pack("<BIB", 0, 2, 0)))
    add("settings unset: fn, number and key", "core §13.5", pc, f"{decl}; disable channel4 true, generation2; becomes empty generation3",
        request(0x79, 0, pc_unset, unset((0, "channel.{}.disable", 4)), S), ok(0x79, struct.pack("<I", 3)))
    add("settings set: longest label fits frame64", "core §13.2, §13.5", pc, f"{decl}; no values generation1; channel4 free",
        request(0x7A, 0, pc_set, b"\1" + it("channel.{}.label", 4, b"L" * 32), S), ok(0x7A, struct.pack("<I", 2)))
    add("settings set: a label equal to another channel's but for ASCII case is refused", "core §13.8", pc,
        f"{decl}; channel 0's label V003.nrst, generation1; retain configuration and generation",
        request(0x7E, 0, pc_set, b"\1" + it("channel.{}.label", 4, b"v003.NRST"), S),
        rej(0x7E, "unavailable", tlv(1, bytes([cause["held_by_settings"]])) + tlv(2, struct.pack("<H", 4))))
    add("settings set: a label moved to another channel in one set", "core §13.5, §13.8", pc,
        f"{decl}; channel 0's label V003.nrst, generation1",
        request(0x127, 0, pc_set, b"\2" + it("channel.{}.label", 0, b"LED") + it("channel.{}.label", 4, b"V003.nrst"), S),
        ok(0x127, struct.pack("<I", 2)))
    add("settings set not offered: a probe of initial values only", "core §13.4, §13.5", pc,
        f"{decl}; get only (no set / unset in fn 0's ops); initial values", request(0x128, 0, pc_set, b"\1" + idle, S),
        rej(0x128, "unknown_operation"))
    add("settings state: independent valid values restored despite an invalid label", "core §13.7", pc,
        f"{decl}; complete saved settings; valid disable/idle applied, an unusable label omitted; current generation1",
        request(0x7B, 0, pc_state, b""), ok(0x7B, struct.pack("<BIB", ce["storage_state"]["partial"], 0, ce["storage_reason"]["item"])))
    add("settings set: changed contents at exhausted generation refused", "core §13.5", pc, f"{decl}; generation0xFFFFFFFF unchanged; current contents retained",
        request(0x7C, 0, pc_set, b"\1" + idle, S), rej(0x7C, "unavailable", tlv(1, bytes([cause["limit"]]))))

    disable = it("channel.{}.disable", 4, b"\1")
    for corr, name, before, records in (
        (0x117, 'disable conflicts with existing idle', 'idle channel4 exists, generation2', [disable]),
        (0x118, 'idle conflicts with existing disable', 'disable channel4 true, generation2', [idle]),
        (0x119, 'disable and idle conflict in one set', 'no values generation1', [idle, disable]),
    ):
        add(f'settings set: {name}', 'core §13.8, §4.3', pc,
            f'{decl}; {before}; channel4 not in use; retain configuration, generation and pins',
            request(corr, 0, pc_set, bytes([len(records)]) + b''.join(records), S),
            rej(corr, 'unavailable', tlv(1, bytes([cause["held_by_settings"]])) + tlv(2, struct.pack('<H', 4))))

    # network settings (transports §7) and an item of an interface (core §13.1)
    longest = it("wifi.{}.passphrase", 0, b"a" * 64)
    add("settings set: the longest passphrase fits wifi_min_max_frame", "transports §7.1, core §13.5", pc, f"{decl}; wifi entry 0 ssid lab, generation2",
        request(0x11A, 0, pc_set, b"\1" + longest, S), ok(0x11A, struct.pack("<I", 3)))
    lab = f"{decl}; wifi entry 0 ssid lab passphrase password1, generation2"
    add("settings get: a secret value has no data", "core §13.5, transports §7.1", pc, lab,
        request(0x11B, 0, pc_get, struct.pack("<H", 0)),
        ok(0x11B, struct.pack("<BIB", 0, 2, 2) + got("wifi.{}.ssid", 0, b"lab") + got("wifi.{}.passphrase", 0)))
    add("settings set: secret len 0 without a value is malformed", "core §13.5", pc, f"{decl}; no values generation1",
        request(0x11C, 0, pc_set, b"\1" + it("wifi.{}.passphrase", 0), S), rej(0x11C, "malformed"))
    add("settings set: secret len 0 keeps the value", "core §13.5", pc, lab,
        request(0x126, 0, pc_set, b"\2" + it("wifi.{}.ssid", 0, b"lab") + it("wifi.{}.passphrase", 0), S), ok(0x126, struct.pack("<I", 2)))
    add("settings set: ipv4 address 127.0.0.1 is malformed", "transports §7.2", pc, f"{decl}; no values generation1",
        request(0x11D, 0, pc_set, b"\1" + it("ipv4.{}.address", 1, bytes([127, 0, 0, 1])), S), rej(0x11D, "malformed"))
    static = (it("ipv4.{}.mode", 1, bytes([ce["ipv4_mode"]["static"]])) + it("ipv4.{}.address", 1, bytes([192, 168, 1, 23]))
              + it("ipv4.{}.prefix", 1, struct.pack("<I", 24)) + it("ipv4.{}.gateway", 1, bytes([192, 168, 1, 1])))
    add("settings set: ipv4 static on wifi, four values at once", "transports §7.2, core §13.5", pc, f"{decl}; no values generation1",
        request(0x11E, 0, pc_set, b"\4" + static, S), ok(0x11E, struct.pack("<I", 2)))
    add("settings set: ipv4 on a netif not in the list is unsupported", "core §13.3", pc, f"{decl}; no values generation1",
        request(0x11F, 0, pc_set, b"\1" + it("ipv4.{}.mode", 2, bytes([ce["ipv4_mode"]["dhcp"]])), S),
        rej(0x11F, "unsupported", b"\0" + tlv(item_tag, b"\0")))
    add("settings set: ipv4 prefix 33 is malformed", "transports §7.2", pc, f"{decl}; no values generation1",
        request(0x120, 0, pc_set, b"\1" + it("ipv4.{}.prefix", 1, struct.pack("<I", 33)), S), rej(0x120, "malformed"))
    add("settings unset: a wifi entry's ssid", "core §13.5", pc, lab,
        request(0x121, 0, pc_unset, unset((0, "wifi.{}.ssid", 0)), S), ok(0x121, struct.pack("<I", 3)))
    ne = ce["network_state"]
    add("network: wifi connected", "transports §7.3", pc,
        f"{decl}; entry 0 connected, 192.168.1.23/24, gateway and dns 192.168.1.1, -52 dBm; TCP listening on 4242",
        request(0x122, 0, op("core", "network"), b""),
        ok(0x122, struct.pack("<HB", 4242, 1) + bytes([1, ne["up"]]) + struct.pack("<H", 0)
           + bytes([0, (-52) & 0xFF, 192, 168, 1, 23, 24, 192, 168, 1, 1, 192, 168, 1, 1])))
    add("settings set: an interface's own text item", "core §13.1", pc, f"{decl}; no values generation1",
        request(0x123, 0, pc_set, b"\1" + it(1, 0, b"pool.ntp.org", fn=8), S), ok(0x123, struct.pack("<I", 2)))
    add("settings set: an own text item with no text is malformed", "core §13.3", pc, f"{decl}; no values generation1",
        request(0x124, 0, pc_set, b"\1" + it(1, 0, fn=8), S), rej(0x124, "malformed"))
    add("settings set: a key on an item without keys is unsupported", "core §13.3", pc, f"{decl}; no values generation1",
        request(0x125, 0, pc_set, b"\1" + it(1, 1, b"x", fn=8), S), rej(0x125, "unsupported", b"\0" + tlv(item_tag, b"\0")))

    # subscribe / unsubscribe (core §10.3): ops of the interface that sends notifications, 0x01 / 0x02 in the common operation range, no target fn
    sub, unsub = REG["constants"]["op_subscribe"], REG["constants"]["op_unsubscribe"]
    lgs = {"9": "oep.fixture.logic"}
    add("logic subscribe: min_bytes 1024, max_delay_ms 20", "core §10.3; capture §3.4", lgs,
        "session S holds the lock; max_frame2048; subscribe/unsubscribe declared in fn9 ops",
        request(0x82, 9, sub, struct.pack("<HI", 1024, 20), S), ok(0x82))
    add("logic unsubscribe", "core §10.3", lgs, "session S; fn 9 subscribed",
        request(0x83, 9, unsub, b"", S), ok(0x83))
    add("logic unsubscribe without a subscription: success, nothing done", "core §10.3", lgs, "session S; fn 9 not subscribed",
        request(0x84, 9, unsub, b"", S), ok(0x84))
    add("logic subscribe without a session: session_required", "core §4.1, §4.3 order 1, §10.3", lgs, "subscribe set in fn 9's ops",
        request(0x85, 9, sub, struct.pack("<HI", 0, 0)), rej(0x85, "session_required"))
    add("gpio subscribe: gpio sends no notifications (not in its ops)", "core §1.2, §10.3; fixture §1", {"2": "oep.fixture.gpio"},
        "session S", request(0x86, 2, sub, struct.pack("<HI", 0, 0), S), rej(0x86, "unknown_operation"))

    # oep.fixture.logic (capture §2, §3.2)
    lg = {"9": "oep.fixture.logic"}
    seg = struct.pack("<IQIQIIBI", 0, 0, 1000, 5_000_000, 50, 0xFFFFFFFF, 0, 1)
    add("logic segments: one segment", "capture §2.2, §3.2", lg, "one-shot done, generation 1: 1000 samples from 5 ms, ±50 ns, no trigger",
        request(0x80, 9, op("oep.fixture.logic", "segments"), struct.pack("<I", 0)), ok(0x80, bytes([0, 1]) + seg))
    add("logic read: another generation", "capture §3.2", lg, "generation 1",
        request(0x81, 9, op("oep.fixture.logic", "read"), struct.pack("<IQH", 2, 0, 64)),
        rej(0x81, "unavailable", tlv(unav["cause"], bytes([cause["wrong_state"]]))))
    add("logic segments: from_serial = serial_done, no segments and more 0", "capture §3.2, common §1.3 paging 2", lg,
        "one-shot done, generation 1, serial_done 1",
        request(0x87, 9, op("oep.fixture.logic", "segments"), struct.pack("<I", 1)), ok(0x87, bytes([0, 0])))
    lt = IFACE["oep.fixture.logic"]["tlv"]
    cfg, qry = op("oep.fixture.logic", "configure"), op("oep.fixture.logic", "query")
    mode = IFACE["oep.fixture.logic"]["enum"]["mode"]
    one_shot = (tlv(lt["configure"]["mode"], bytes([mode["one_shot"]])) + tlv(lt["configure"]["rate"], struct.pack("<I", 20_000_000))
                + tlv(lt["configure"]["samples"], struct.pack("<I", 200_000)))
    ca = lt["configure_answer"]
    add("logic configure: one-shot, the required answer set", "capture §3.3", lg,
        "session S holds the lock; roles 0 and 1 in fn 9's plan; 20 MHz exact, 200000 samples fit; the probe packs 2 bits per sample",
        request(0x88, 9, cfg, one_shot, S),
        ok(0x88, tlv(ca["actual_rate"], struct.pack("<II", 20_000_000, 1)) + tlv(ca["layout"], bytes([2, 2, 0, 1]))
           + tlv(ca["actual_samples"], struct.pack("<I", 200_000))))
    add("logic configure without rate: malformed", "capture §3.3 contract", lg, "session S; as above",
        request(0x89, 9, cfg, tlv(lt["configure"]["mode"], bytes([mode["one_shot"]])) + tlv(lt["configure"]["samples"], struct.pack("<I", 200_000)), S),
        rej(0x89, "malformed"))
    add("logic query: streaming with samples, refused with the tag", "capture §3.3 contract, core §2.3", lg, "as above (query needs no lock)",
        request(0x8A, 9, qry, tlv(lt["configure"]["mode"], bytes([mode["streaming"]])) + tlv(lt["configure"]["rate"], struct.pack("<I", 1_000_000))
                + tlv(lt["configure"]["samples"], struct.pack("<I", 1000))),
        rej(0x8A, "unsupported", bytes([lt["configure"]["samples"]])))
    add("logic query: an immediate trigger's role is not looked at", "capture §3.3 contract", lg,
        "as above (roles 0 and 1 in fn 9's plan); type 0 carries role 5, not in the plan",
        request(0xA0, 9, qry, one_shot + tlv(lt["configure"]["trigger"],
                                            struct.pack("<BBI", IFACE["oep.fixture.logic"]["enum"]["trigger"]["immediate"], 5, 0))),
        ok(0xA0, tlv(ca["actual_rate"], struct.pack("<II", 20_000_000, 1)) + tlv(ca["layout"], bytes([2, 2, 0, 1]))
           + tlv(ca["actual_samples"], struct.pack("<I", 200_000))))

    add("logic query: samples 0, a value the definition excludes: malformed", "capture §3.3 contract, core §2.3", lg, "as above",
        request(0xA2, 9, qry, tlv(lt["configure"]["mode"], bytes([mode["one_shot"]])) + tlv(lt["configure"]["rate"], struct.pack("<I", 20_000_000))
                + tlv(lt["configure"]["samples"], struct.pack("<I", 0))),
        rej(0xA2, "malformed"))

    # capture §2.2: a segment the probe could not keep seamless is not handed out; the track stops in error
    minimal = {"19":"oep.fixture.logic", "20":"oep.probe.plan"}
    add("logic start: bounded CPU capture finishes before the reply", "capture §3.2", minimal,
        "one route, max_inflight1, role0 channel1 allocated through fn20 plan; mode1, immediate, 16ms CPU capture, max_op_ms50; generation0 before; capture completes and request service resumes before this reply; lease uses core rules",
        request(0xE0,19,op("oep.fixture.logic","start"),b"",S),ok(0xE0,struct.pack("<I",1)))
    add("logic release: not offered by a one-shot-only fn", "capture §3.2", minimal,
        "mode1 only; ops10,11,12,14,15,16; no release handler",
        request(0xE1,19,op("oep.fixture.logic","release"),struct.pack("<II",1,0),S),rej(0xE1,"unknown_operation"))
    add("logic release: old generation is refused before the one-shot no-op", "capture §3.2", minimal,
        "release offered; mode1; current generation2; current data unchanged",
        request(0xE2,19,op("oep.fixture.logic","release"),struct.pack("<II",1,0),S),rej(0xE2,"unavailable",tlv(1,b"\6")))
    add("logic start: generation exhausted without clearing current data", "capture §0, §3.2", minimal,
        "current generation0xFFFFFFFF, state4, previous data retained; no new generation until reboot",
        request(0xE3,19,op("oep.fixture.logic","start"),b"",S),rej(0xE3,"unavailable",tlv(1,b"\2")))
    add("logic read: maximum u16 request, response constrained by frame", "capture §3.2", minimal,
        "generation1; 48 retained bytes at0; max_frame64; no marks/timing TLVs",
        request(0xE4,19,op("oep.fixture.logic","read"),struct.pack("<IQH",1,0,65535)),
        ok(0xE4,struct.pack("<QBH",0,0,48)+bytes(range(48))))
    analog = {"20":"oep.fixture.analog"}
    act = IFACE["oep.fixture.analog"]["tlv"]["configure_answer"]
    for roles,skews,corr in (([0],[0],0xE5),([0,1],[1],0xE6)):
        result=tlv(act["actual_rate"],struct.pack("<II",1000,1))+tlv(act["layout"],bytes([16,0,12,len(roles),*roles]))
        result+=tlv(act["actual_samples"],struct.pack("<I",10))
        result+=b"".join(tlv(act["scale"],struct.pack("<Bii",r,0,1000000)) for r in roles)
        result+=b"".join(tlv(act["skew"],struct.pack("<BI",r,5)) for r in skews)
        at=IFACE["oep.fixture.analog"]["tlv"]["configure"]
        payload=tlv(at["mode"],b"\1")+tlv(at["rate"],struct.pack("<I",1000))+tlv(at["samples"],struct.pack("<I",10))
        add(f"analog configure: {len(roles)} roles and one nonzero skew without optional diagnostics", "capture §3.3", analog,
            "mode1; given plan roles; no calibration op; scale is pin-voltage estimate; frontend/reference diagnostics omitted",
            request(corr,20,op("oep.fixture.analog","configure"),payload,S),ok(corr,result))
    # calibration (capture §3.7): everything held or rejected unsupported (0x00) when it does not fit max_frame; never cut, failed or partial
    cal, ct = op("oep.fixture.analog", "calibration"), IFACE["oep.fixture.analog"]["tlv"]["calibration_answer"]
    scheme = b"com.example.adc"
    factory = lambda raw: tlv(ct["factory"], bytes([0xFF, len(scheme)]) + scheme + struct.pack("<H", len(raw)) + raw)
    held = factory(bytes(range(4))) + tlv(ct["vrefint"], struct.pack("<IQI", 1500, 7_000_000, 1200))
    add("analog calibration: everything held fits in one answer", "capture §3.7", analog,
        "calibration offered in ops; max_frame 64; factory raw 4 bytes (frontend 0xFF), vrefint measured at the last start",
        request(0xE7, 20, cal, b""), ok(0xE7, held))
    add("analog calibration: nothing held, empty success", "capture §3.7", analog,
        "calibration offered in ops; no factory value and no vrefint",
        request(0xE8, 20, cal, b""), ok(0xE8))
    add("analog calibration: factory raw beyond max_frame is refused, not cut", "capture §3.7, core §4.4", analog,
        "calibration offered in ops; max_frame 64; factory raw 60 bytes; no ADC or capture state changes",
        request(0xE9, 20, cal, b""), rej(0xE9, "unsupported", b"\0"))
    lst = IFACE["oep.fixture.logic"]["enum"]
    drop = ("repeat, 1 channel w 1, samples 8000 (1000 bytes a segment), generation 1: serials 0 and 1 done, then the capture ring "
            "overflowed inside serial 2")
    segs = [struct.pack("<IQIQIIBI", k, 1000 * k, 8000, 5_000_000 + 8_000_000 * k, 50, 0xFFFFFFFF, 0, 1) for k in (0, 1)]
    add("logic status: data dropped inside a segment, state 6 and error 2", "capture §2.2, §3.2", lg, drop,
        request(0x90, 9, op("oep.fixture.logic", "status"), b""),
        ok(0x90, struct.pack("<BIQBI", lst["state"]["error"], 2, 2000, lst["status_flag"]["dropped"], 1)
           + tlv(lt["status_answer"]["error"], bytes([lst["error"]["storage"]]))))
    add("logic segments: the dropped segment is not handed out", "capture §2.2, common §1.3", lg, drop,
        request(0x91, 9, op("oep.fixture.logic", "segments"), struct.pack("<I", 0)), ok(0x91, bytes([0, 2]) + b"".join(segs)))
    add("logic read: nothing of the dropped segment", "capture §2.2, §3.2", lg, drop + "; write_pos 2000",
        request(0x92, 9, op("oep.fixture.logic", "read"), struct.pack("<IQH", 1, 2000, 64)), ok(0x92, struct.pack("<QBH", 2000, 0, 0)))

    add("capture-group bind: non-immediate track is refused", "capture §4.1",
        {"12":"oep.fixture.capture-group","9":"oep.fixture.logic","13":"oep.fixture.analog"},
        "fn9 configured edge trigger; fn13 immediate; prior binding unchanged",
        request(0x8A,12,op("oep.fixture.capture-group","bind"),struct.pack("<BHH",2,9,13),S),
        rej(0x8A,"unavailable",tlv(1,b"\6")+tlv(5,struct.pack("<H",9))))
    add("capture-group bind: future critical selector is refused", "capture §4.1, core §2.3",
        {"12":"oep.fixture.capture-group"},"both tracks immediate; the probe declares no features trigger_source (capture §4.4), so bind's critical trigger_source is refused; no effects",
        request(0x8C,12,op("oep.fixture.capture-group","bind"),struct.pack("<BHH",2,9,13)+tlv(0x81,struct.pack("<H",9)),S),
        rej(0x8C,"unsupported",b"\x81"))
    # oep.fixture.capture-group (capture §4): the group's generation, then n x (fn, generation) in bind order, in the fixed part
    grp = {"12": "oep.fixture.capture-group", "9": "oep.fixture.logic", "13": "oep.fixture.analog"}
    add("capture-group status: immediate group has no unused trigger fields", "capture §4.1", grp,
        "group generation5, started at7ms, both tracks capturing",
        request(0x8D,12,op("oep.fixture.capture-group","status"),b""),ok(0x8D,struct.pack("<BQI",3,7000000,5)))
    add("capture-group start: the group's and each track's new generation", "capture §4.1", grp,
        "session S; fn 12 bound to fn 9 then fn 13, both one-shot with immediate triggers; generations before: group 4, fn 9 3, fn 13 1; "
        "acquisition starts at 7 ms",
        request(0x8B, 12, op("oep.fixture.capture-group", "start"), b"", S),
        ok(0x8B, struct.pack("<QIB", 7_000_000, 5, 2) + struct.pack("<HI", 9, 4) + struct.pack("<HI", 13, 2)))

    # oep.fixture.spi-target (fixture §4): wire bit k goes to byte k // 8, bit 7 - k % 8 (MSB first) or k % 8 (LSB first); missing bits 0
    def spi_pack(wire_bits: list[int], lsb_first: bool) -> bytes:
        out = bytearray((len(wire_bits) + 7) // 8)
        for k, b in enumerate(wire_bits):
            out[k // 8] |= b << (k % 8 if lsb_first else 7 - k % 8)
        return bytes(out)

    spi = {"14": "oep.fixture.spi-target"}
    add("spi-target configure: known but unsupported mode preserves state", "fixture §4", spi,
        "fn 14 has plan and modes=1 (mode0 only); previous mode0 state, queue, counters and arm remain unchanged",
        request(0xCE,14,op("oep.fixture.spi-target","configure"),b"\3\0",S),rej(0xCE,"unsupported",b"\0"))
    add("spi-target arm: preparation failed with no fixed result", "fixture §4", spi,
        "configured with plan; driver cannot prepare output; no arm or queue/counter changes",
        request(0xCF,14,op("oep.fixture.spi-target","arm"),struct.pack("<HH",1,1)+b"x",S),failed(0xCF))
    spi_cfg = op("oep.fixture.spi-target", "configure")
    add("spi-target configure: success has no fixed part", "fixture §4", spi,
        "session S; fn 14 has its plan; modes declares mode 0; state 1 once answered",
        request(0xD0, 14, spi_cfg, b"\0\0", S), ok(0xD0))
    add("spi-target configure: initialization failure, no fixed part", "fixture §0, §4", spi,
        "session S; running in mode 0 with 1 transaction queued, armed, transactions 4, errors 1; the driver fails to start; "
        "back to state 0, queue and arm data dropped, channels free (core §8), plan kept",
        request(0xD1, 14, spi_cfg, b"\0\0", S), failed(0xD1))
    add("spi-target status: after a failed configure, state 0 and everything 0", "fixture §4", spi,
        "the configure above failed; a CS transfer came afterwards and was neither queued nor counted",
        request(0xD2, 14, op("oep.fixture.spi-target", "status"), b""), ok(0xD2, struct.pack("<BBBBBII", 0, 0, 0, 0, 0, 0, 0)))
    add("spi-target arm: state 0 after a failed configure is unavailable", "fixture §4", spi,
        "session S; the configure above failed; nothing armed",
        request(0xD3, 14, op("oep.fixture.spi-target", "arm"), struct.pack("<HH", 1, 1) + b"x", S),
        rej(0xD3, "unavailable", tlv(unav["cause"], bytes([6]))))
    wire = [1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1]
    for corr, lsb in ((0x8C, False), (0x8D, True)):
        add(f"spi-target read_rx: 12 bits, {'LSB' if lsb else 'MSB'} first, a partial last byte", "fixture §4", spi,
            f"session S; configured with bit_order {int(lsb)}; one transaction queued: CS ended after 12 MOSI bits 1 1 0 0 0 0 0 0 1 0 1 1 "
            "(in wire order); no ns TLV",
            request(corr, 14, op("oep.fixture.spi-target", "read_rx"), b"", S),
            ok(corr, struct.pack("<BIH", 0, len(wire), 2) + spi_pack(wire, lsb)))

    # oep.fixture.i2c-controller (fixture §5): segments dir address count [data]; result at index count data
    i2c = {"15": "oep.fixture.i2c-controller"}
    i2c_tr = op("oep.fixture.i2c-controller", "transfer")
    add("i2c-controller configure: the SCL used at or below the one asked", "fixture §5", i2c,
        "session S; fn 15 has its plan; the probe makes 100 kHz or 380 kHz; asked 400 kHz, stretch timeout 10 ms",
        request(0xA0, 15, op("oep.fixture.i2c-controller", "configure"), struct.pack("<II", 400000, 10000), S),
        ok(0xA0, struct.pack("<I", 380000)))
    add("i2c-controller transfer: a register read (write, repeated START, read, STOP)", "fixture §5", i2c,
        "session S; configured; the target at 0x50 ACKs the register 0x10 and answers 0xAB 0xCD",
        request(0xA1, 15, i2c_tr, bytes([1, 2]) + struct.pack("<BBH", 0, 0x50, 1) + b"\x10" + struct.pack("<BBH", 1, 0x50, 2), S),
        ok(0xA1, struct.pack("<BBHH", 0, 0, 0, 2) + b"\xAB\xCD"))
    add("i2c-controller transfer: nobody at the address", "fixture §5", i2c,
        "session S; configured; nothing ACKs 0x51; a STOP goes out, the bus is not held",
        request(0xA2, 15, i2c_tr, bytes([1, 1]) + struct.pack("<BBH", 0, 0x51, 0), S),
        ok(0xA2, struct.pack("<BBHH", 1, 0, 0, 0)))
    add("i2c-controller transfer: the target NACKs the second data byte", "fixture §5", i2c,
        "session S; configured; 0x50 ACKs its address and 0x01, NACKs 0x02; a STOP goes out",
        request(0xA3, 15, i2c_tr, bytes([1, 1]) + struct.pack("<BBH", 0, 0x50, 3) + b"\x01\x02\x03", S),
        ok(0xA3, struct.pack("<BBHH", 2, 0, 1, 0)))
    add("i2c-controller transfer: a read count 0 is malformed", "fixture §5", i2c,
        "session S; configured; nothing on the bus",
        request(0xA4, 15, i2c_tr, bytes([1, 1]) + struct.pack("<BBH", 1, 0x50, 0), S), rej(0xA4, "malformed"))
    add("i2c-controller status: holding the bus after a transfer without STOP", "fixture §5", i2c,
        "configured; one transfer answered with flags 0 (no STOP), result 0",
        request(0xA5, 15, op("oep.fixture.i2c-controller", "status"), b""), ok(0xA5, struct.pack("<BBII", 1, 1, 1, 0)))

    # oep.fixture.spi-controller (fixture §6): n x (gap_ns setup_ns hold_ns count tx) -> n x (the times used, count, rx)
    spic = {"16": "oep.fixture.spi-controller"}
    add("spi-controller configure: the SCK used at or below the one asked", "fixture §6", spic,
        "session S; fn 16 has its plan; modes declares mode 0; the probe makes 1 MHz from 1.2 MHz asked",
        request(0xA6, 16, op("oep.fixture.spi-controller", "configure"), b"\0\0" + struct.pack("<I", 1200000), S),
        ok(0xA6, struct.pack("<I", 1000000)))
    add("spi-controller transfer: two transfers, the times used at or above the ones asked", "fixture §6", spic,
        "session S; configured mode 0 MSB first; time_step_ns 25; the target answers 0x5A then 0x00 0xFF; the first transfer's gap is 0",
        request(0xA7, 16, op("oep.fixture.spi-controller", "transfer"),
                bytes([2]) + struct.pack("<IIIH", 0, 1000, 500, 1) + b"\x9F" + struct.pack("<IIIH", 2010, 1000, 500, 2) + b"\x01\x02", S),
        ok(0xA7, struct.pack("<IIIH", 0, 1000, 500, 1) + b"\x5A" + struct.pack("<IIIH", 2025, 1000, 500, 2) + b"\x00\xFF"))
    add("spi-controller transfer: n 0 is malformed", "fixture §6", spic,
        "session S; configured",
        request(0xA8, 16, op("oep.fixture.spi-controller", "transfer"), b"\0", S), rej(0xA8, "malformed"))

    # events (core §10.2): role, fn, seq, kind, the fixed part; every capture event carries its generation (capture §3.4, §4.2)
    events, data = [], []

    def event(name, spec, fns, state, fn, seq, kind, fixed, generation):
        frame = struct.pack("<BHHB", REG["roles"]["event"], fn, seq, kind) + fixed
        events.append({"name": name, "spec": spec, "fns": fns, "state": state, "generation": generation, "event_hex": hx(frame)})

    le, ge = IFACE["oep.fixture.logic"]["event"], IFACE["oep.fixture.capture-group"]["event"]
    reason = IFACE["oep.fixture.logic"]["enum"]["stopped_reason"]
    after = "fn 9 subscribed; start answered generation 4 while generation 3's stop was still queued"
    event("logic stopped of the previous generation, after the start answer", "capture §3.4, core §10.4", lg, after, 9, 7, le["stopped"],
          struct.pack("<BBI", reason["host"], 0, 3), 3)
    event("logic triggered of the new generation", "capture §3.4", lg,
          after + "; the edge at sample 1000 of serial 0 (20 MHz, rearm 0: no record), at 7.05 ms +-50 ns (a sample period)",
          9, 8, le["triggered"], struct.pack("<IIIQQII", 0, 1000, 0xFFFFFFFF, 1000, 7_050_000, 50, 4), 4)
    event("logic stopped: data dropped inside a segment, error 2", "capture §2.2, §3.4", lg,
          "fn 9 subscribed; generation 1; the capture ring overflowed inside serial 2", 9, 9, le["stopped"],
          struct.pack("<BBI", reason["error"], IFACE["oep.fixture.logic"]["enum"]["error"]["storage"], 1), 1)
    # capture §2.1 rule 2, §2.2: data of a segment may be sent before it ends; when the track stops in error the host drops what it got at
    # or past status's write_pos (the start of the segment that was not kept)
    sdrop = ("streaming, w8, generation1, 16 samples/segment; bytes24-31 and32-39 in separate frames; "
             "serial2 later lost in error, write_pos32")
    for label,pos,origin,samples,seq,keep in (("retained bytes of previous segment",24,16,16,10,8),
                                             ("a frame of the segment that is then lost",32,32,8,11,0)):
        tail=tlv(IFACE["oep.fixture.logic"]["tlv"]["data"]["generation"],struct.pack("<I",1))
        tail+=tlv(IFACE["oep.fixture.logic"]["tlv"]["data"]["segment_info"],struct.pack("<QIQI",origin,samples,1000000+origin*1000000,50))
        data.append({"name":"logic data: "+label,"spec":"capture §2.2/§3.4","fns":lg,"state":sdrop,"generation":1,"keep":keep,
                     "frame_hex":hx(struct.pack("<BHHQH",REG["roles"]["data"],9,seq,pos,8)+bytes(range(pos,pos+8))+tail)})
    packed=bytes.fromhex('d158')  # samples 1,2,3,4,5 as 3-bit little-endian words; last padding bit0.
    for offset,seq in ((0,20),(1,21)):
        tail=tlv(1,struct.pack("<I",1))+tlv(2,struct.pack("<QIQI",0,5,1000000,50))
        data.append({"name":f"logic data: w3 byte{offset}, first frame may be lost","spec":"capture §3.4", "fns":lg,
                     "state":"independent w3 capture, five samples1/2/3/4/5; one segment at0; first frame is lost in recovery test",
                     "layout":{"w":3,"pos":[0,1,2]},"generation":1,
                     "frame_hex":hx(struct.pack("<BHHQH",4,9,seq,offset,1)+packed[offset:offset+1]+tail)})
    add("logic status: streaming stopped in error, write_pos at the lost segment's start", "capture §2.2, §3.2", lg, sdrop,
        request(0xA1, 9, op("oep.fixture.logic", "status"), b""),
        ok(0xA1, struct.pack("<BIQBI", lst["state"]["error"], 2, 32, lst["status_flag"]["dropped"], 1)
           + tlv(lt["status_answer"]["error"], bytes([lst["error"]["storage"]]))))
    event("capture-group stopped: the group's generation", "capture §4.2", grp, "fn12 subscribed, generation5; every track done", 12, 1, ge["stopped"],
          struct.pack("<BBI", reason["complete"], 0, 5), 5)
    return {
        "about": "Per-op byte vectors. `fns` says which interface each fn number is in the example; `state` is the probe state the answer assumes. "
                 "Requests with session_id 0x11223344 come from the session that holds the lock; lock-free requests carry 0. "
                 "`events` are notification frames (core §10.2) with the generation each carries; `data` are data frames, with `keep` the bytes "
                 "from the frame's start the host keeps.",
        "cases": cases,
        "events": events,
        "data": data,
    }


# ---- capture data (capture §1.1) -----------------------------------------------------------------------------

def levels(n: int, ones) -> str:
    """A channel's levels as text, character i = the level of sample i."""
    ones = set(ones)
    return "".join("1" if i in ones else "0" for i in range(n))


def pack_samples(chans: list[str], w: int, pos: list[int], first: int, count: int) -> bytes:
    """capture §1.1 rules 1-4: sample i at stream bits i*w .. i*w + w - 1, channel k at bit i*w + pos[k]; ceil(count*w / 8) bytes.
    The bits no pos names (undefined) are 0 here."""
    bits = 0
    for i in range(count):
        for k, ch in enumerate(chans):
            bits |= int(ch[first + i]) << (i * w + pos[k])
    return bits.to_bytes((count * w + 7) // 8, "little")


def logic_layout() -> dict:
    cases = []

    def add(name, spec, w, pos, chans):
        n = len(chans[0])
        cases.append({"name": name, "spec": spec, "w": w, "pos": pos, "samples": n, "channels": chans,
                      "stream_hex": hx(pack_samples(chans, w, pos, 0, n))})

    add("w 3, three channels: samples cross byte boundaries", "capture §1.1 rules 1-4, the w = 3 example", 3, [0, 1, 2],
        [levels(8, (0, 1, 2, 5)), levels(8, (1, 3)), levels(8, (7,))])
    return {
        "about": "Logic capture streams (capture §1.1): the configure answer's layout (w, pos), the channels' levels (`channels[k]`, character i = "
                 "the level of channel k in sample i, channels in role order) and the segment's stream. Bits no pos names and the bits of the last "
                 "byte past N*w are undefined (any value; 0 here); a host ignores them.",
        "cases": cases,
    }


def interface_profiles() -> dict:
    """Small declaration examples, not complete probes or operation traces."""
    rows = []
    for label, entries in (
        ('core only', []),
        ('independent extension', [(3, 'io.example.echo', [0x10], [])]),
        ('receive-only UART', [(7, 'oep.fixture.uart', [0x10, 0x11, 0x16],
                               [(0x01, b'\x01\0\0\x01'), (0x40, b'\x01\0')]),
                              (20,'oep.probe.plan',[0x10,0x11],[])]),
        ('raw ARM target', [(8, 'oep.wire.swd', [0x11, 0x12, 0x13],
                            [(0x01, b'\x01\0\0\x01'), (0x01, b'\x02\0\0\x02')]),
                           (9, 'oep.target.arm-adi', [0x10], [])]),
        ('raw RISC-V target', [(4, 'oep.wire.rvswd', [0x11,0x12,0x13], []),
                                (6, 'oep.target.riscv-dm', [0x10], [])]),
        ('mode0 SPI target', [(14,'oep.fixture.spi-target',[0x10,0x11,0x12,0x13],
                              [(0x41,b'\1'),(0x40,b'\1'),(0x03,struct.pack('<H',50)),
                               (0x02,struct.pack('<I',1000000))]+[(0x01,struct.pack('<BHB',k,20+k,1)) for k in range(1,5)]),
                              (20,'oep.probe.plan',[0x10,0x11],[])]),
        ('settings-only extension', [(22,'io.example.board',[0x10],[(REG['describe_common']['setting'],
                                     struct.pack('<BBHBB',CORE['enum']['setting_form']['text'],CORE['enum']['setting_key_kind']['none'],0,32,0)+b'ntp-server')])]),
        ('one-shot logic capture', [(19,'oep.fixture.logic',[0x10,0x11,0x12,0x14,0x15,0x16],
                                    [(0x40,struct.pack('<BII',1,16,0)),(0x41,struct.pack('<II',1,1000)),
                                     (0x44,b'\1'),(0x45,struct.pack('<II',1,0)),(0x01,struct.pack('<BHB',0,1,1))]),
                                    (20,'oep.probe.plan',[0x10,0x11],[])]),
        ('receive-only SDI console', [(4, 'oep.wire.rvswd', [0x11,0x12,0x13], []),
                                     (7, 'oep.target.console', [0x10,0x11,0x16,0x17], [(0x40,b'\x01\0')])]),
        ('receive-only dmseq console', [(4, 'oep.wire.rvswd', [0x11,0x12,0x13], []),
                                       (7, 'oep.target.console', [0x10,0x11,0x16,0x17], [(0x40,b'\x01\x02')])]),
    ):
        body = struct.pack('<HB', len(entries), len(entries))
        declarations = []
        for fn, name, offered, extra in entries:
            encoded = name.encode('ascii')
            body += struct.pack('<HHBB', fn, 0, 1, len(encoded)) + encoded
            values = [(REG['describe_common']['ops'], ops_value(offered))] + extra
            declarations.append({'fn': fn, 'instance': 0, 'revision': 1, 'name': name,
                'ops': offered, 'describe_answer_hex': hx(answer(fn, COMPLETED, 0, b'\0' + b''.join(tlv(t, v) for t, v in values)))})
        listed = answer(1, COMPLETED, 0, body)
        assert len(listed) <= 64
        rows.append({'name': label, 'list_answer_hex': hx(listed), 'entries': declarations})
    return {'about': 'Declaration byte examples for core-only, independent, minimal UART, raw ARM/RISC-V and console profiles. '
            'List entries have no flags byte. Each describe reply has more=0 and ops plus selected pin/format tags. '
            'These are not complete endpoint identity/capability dumps or runtime conformance traces.', 'profiles': rows}


def core_lifecycle() -> dict:
    """Lifecycle traces with explicit receive/processing/send boundaries."""
    rows = []
    sid = 0x12345678
    def add(name, events):
        rows.append({'name': name, 'spec': 'core §4.4/5.1/6.1/6.3', 'events': events})
    def receive(corr, session=sid, operation='keepalive', route=0, expect='queued', extra=b''):
        payload = struct.pack('<IB', 5000, 0) if operation == 'open' else struct.pack('<HH',0,0) if operation == 'describe' else b''
        fn, opcode = (3, 0x10) if operation == 'slow_read' else (0, op('core',operation))
        return {'action': 'receive', 'route': route, 'request_hex': hx(request(corr,fn,opcode,payload+extra,session)), 'expect': expect}
    opened = [receive(1, operation='open'), {'action': 'process', 'route': 0, 'duration_ms': 0},
              {'action': 'sent', 'route': 0}, {'action': 'check', 'owner': sid, 'remaining_ms': 5000}]
    add('owner processing pauses lease but transmission does not', opened + [
        {'action': 'advance', 'ms': 1000}, receive(2,operation='open'),
        {'action': 'process', 'route': 0, 'duration_ms': 7000},
        {'action': 'check', 'owner': sid, 'remaining_ms': 5000, 'executions': 2},
        {'action': 'advance', 'ms': 5001},
        {'action': 'check', 'owner': 0, 'remaining_ms': 0},
        {'action': 'sent', 'route': 0},
    ])
    add('observer processing does not pause an owner lease', opened + [
        {'action': 'advance', 'ms': 1000}, receive(2,0,'slow_read',1),
        {'action': 'process', 'route': 1, 'duration_ms': 7000},
        {'action': 'check', 'owner': 0, 'remaining_ms': 0},
    ])
    add('pending retries use one credit and one execution without cache', opened + [
        receive(2), receive(2,expect='coalesced'), receive(2,expect='coalesced'),
        {'action': 'check', 'credits': {'0': 1}, 'executions': 1},
        {'action': 'process', 'route': 0, 'duration_ms': 2},
        receive(2,expect='coalesced'), {'action': 'check', 'executions': 2},
        {'action': 'sent', 'route': 0}, receive(2),
        {'action': 'process', 'route': 0, 'duration_ms': 2, 'reason': 'result_lost'},
        {'action': 'check', 'executions': 2},
    ])
    add('SID zero pending copies can coalesce but completed requests run again', [
        receive(1,0,'clock'), receive(1,0,'clock',expect='coalesced'),
        {'action': 'process', 'route': 0, 'duration_ms': 1}, {'action': 'sent', 'route': 0},
        receive(1,0,'clock'), {'action': 'process', 'route': 0, 'duration_ms': 1},
        {'action': 'check', 'owner': 0, 'executions': 2},
    ])
    add('route closure can discard an unexecuted request without ending ownership', opened + [
        receive(2), {'action': 'close', 'route': 0}, {'action': 'check', 'owner': sid, 'executions': 1},
        receive(2,route=1), {'action': 'process', 'route': 1, 'duration_ms': 1},
        {'action': 'check', 'owner': sid, 'executions': 2},
    ])
    add('wrong owner and SID zero observations cannot renew the lease', opened + [
        {'action': 'advance', 'ms': 4000}, receive(2,0,'lock_state'),
        {'action': 'process', 'route': 0, 'duration_ms': 1}, {'action': 'sent', 'route': 0},
        receive(3,sid+1), {'action': 'process', 'route': 0, 'duration_ms': 1, 'reason': 'locked'},
        {'action': 'sent', 'route': 0}, {'action': 'advance', 'ms': 1000},
        {'action': 'check', 'owner': 0, 'executions': 2},
    ])
    add('rejected fresh owner request renews from generation', opened + [
        {'action': 'advance', 'ms': 4000}, receive(2,extra=tlv(0xBE,b'x')),
        {'action': 'process', 'route': 0, 'duration_ms': 2, 'reject': 'unsupported', 'reason': 'unsupported'},
        {'action': 'check', 'owner': sid, 'remaining_ms': 5000, 'executions': 1},
    ])
    add('a queued heartbeat cannot revive an expired owner', opened + [
        {'action': 'advance', 'ms': 4000}, receive(2),
        {'action': 'advance', 'ms': 1001}, {'action': 'process', 'route': 0, 'duration_ms': 1, 'reason': 'no_session'},
        {'action': 'check', 'owner': 0, 'executions': 1},
    ])
    return {'about': 'Time is probe processing/transport time in ms. This is a contract model: max_op_ms=10000, no replay byte cache, per-route max_inflight=1 and window=64. '
            'receive queues one unique request or coalesces a pending retry; process generates an answer; sent releases route credit. '
            'Fn3 is an optional io.example.slow-query revision1 with op0x10: a side-effect-free read with empty fixed request/result, bounded by max_op_ms. '
            'Opaque durations model scheduler work, not a measured MCU or clock implementation. Zero-cache replay produces result_lost without executing.',
            'scenarios': rows}


def core_policy() -> dict:
    """Optional policy admission, with opaque downstream responses."""
    ok = lambda corr, payload=b"": answer(corr, COMPLETED, 0, payload)
    rej = lambda corr, reason, payload=b"": answer(corr, REJECTED, REASON[reason], payload)
    sid, other = 0x12345678, 0x87654321
    rows = []
    def add(name, req, expected, **extra):
        rows.append(dict(name=name, request_hex=hx(req), expected_response_hex=hx(expected), allowed=False, **extra))
    denied = tlv(1, bytes([7]))
    query, cached = request(12,2,0x10,b'',sid), ok(12,b'secret')
    add('revoked read cannot replay a secret', query, rej(12,'unavailable',denied), cache_response_hex=hx(cached))
    add('denied force preserves resources', request(1,0,op('core','open'),struct.pack('<IB',5000,1),other), rej(1,'unavailable',denied))
    add('denied fresh heartbeat preserves lease and corr', request(13,0,op('core','keepalive'),b'',sid), rej(13,'unavailable',denied))
    add('bad corr precedes policy', request(0,2,0x10,b'',sid), rej(0,'malformed'))
    add('unknown op precedes policy', request(13,2,0x11,b'',sid), rej(13,'unknown_operation'))
    for name, payload in [('confirm',b'OEP'+bytes([1])),('list',struct.pack('<H',0)),('describe',struct.pack('<HH',0,0)),('clock',b''),('lock_state',b'')]:
        add('public '+name, request(13,0,op('core',name),payload), ok(13), downstream_response_hex=hx(ok(13)))
    rows.append(dict(name='allowed replay remains historical',request_hex=hx(query),expected_response_hex=hx(cached),allowed=True,cache_response_hex=hx(cached)))
    return dict(about='Optional admission harness, not authentication or an endpoint. Owner 0x12345678, last_corr12, lease remaining1000ms, resource42. Fn2 is optional io.example.query revision1, readonly op0x10. Downstream op results are opaque sentinels; operation execution has separate vectors.',scenarios=rows)


def interface_boundaries() -> dict:
    """Finite boundary examples; observations are supplied by the endpoint test adapter."""
    batching = []
    for name, minimum, delay, age, pending, ending, frame, chunks in (
        ("running tail waits", 32, 0, 1000, 8, False, 128, []),
        ("stop flushes tail without a timer", 32, 0, 1000, 8, True, 128, [8]),
        ("timer releases tail", 32, 20, 20, 8, False, 128, [8]),
        ("threshold spans frames including the last tail", 64, 0, 0, 64, False, 64, [15, 15, 15, 15, 4]),
        ("both zero sends immediately", 0, 0, 0, 8, False, 128, [8]),
        ("empty stop creates no data frame", 32, 0, 1000, 0, True, 128, []),
    ):
        batching.append(dict(name=name, spec="core §10.3/§10.4; capture §2.1/§3.4",
                             min_bytes=minimum, max_delay_ms=delay, age_ms=age, pending_bytes=pending,
                             stopped=ending, max_frame=frame, expected_data_lengths=chunks))

    reception = []
    for name, spans, at_end, complete in (
        ("middle notification lost", [[1, 0, 16], [1, 32, 48]], True, False),
        ("contiguous reception", [[1, 0, 16], [1, 16, 32], [1, 32, 48]], True, True),
        ("read recovers a gap", [[1, 0, 16], [1, 32, 48], [1, 8, 36]], True, True),
        ("old generation cannot fill a gap", [[1, 0, 16], [0, 16, 32], [1, 32, 48]], True, False),
        ("last notification lost", [[1, 0, 32]], False, False),
    ):
        reception.append(dict(name=name, spec="capture §2.1", generation=1, write_pos=48,
                              spans=spans, expected_tail_reached=at_end, expected_complete=complete))

    # common §1.3/§1.5: a forward serial jump counts as lost only within one stream (capture: one generation) and the core §2.6 range
    serial_loss = []
    for name, same, last, first, lost in (
        ("contiguous", True, 6, 7, 0),
        ("forward jump in one stream", True, 4, 9, 4),
        ("jump across the u32 wrap", True, 0xFFFFFFFE, 2, 3),
        ("another boot's serials", False, 4, 9, None),
        ("another generation", False, 4, 9, None),
        ("no earlier serial: an arbitrary from_serial", True, None, 300, None),
        ("backwards is not a forward jump", True, 9, 4, None),
        ("beyond a quarter of the space", True, 0, 0x40000001, None),
    ):
        serial_loss.append(dict(name=name, spec="common §1.3 paging 3, core §2.6", same_stream=same,
                                last_serial=last, first_serial=first, expected_lost=lost))

    storage = []
    for action, result, observed, before, after in (
        ("save", "success", "new", [1, 4, 0], [1, 5, 0]),
        ("save", "failed", "old", [1, 4, 0], [1, 4, 0]),
        ("save", "failed", "old", [3, 0, 2], [3, 0, 2]),
        ("save", "failed", "none", [0, 0, 0], [0, 0, 0]),
        ("save", "failed", "unreadable", [1, 4, 0], [2, 0, 1]),
    ):
        storage.append(dict(name=f"{action} {result}, observed {observed}, before {before}",
                            spec="core §13.7", action=action, result=result, observed=observed,
                            before=before, expected_state=after, generation=5,
                            request_hex=hx(request(1, 0, op("core", action), b"", 0x11223344)),
                            answer_hex=hx(answer(1, COMPLETED, REG["outcomes"][result], struct.pack("<I", 5))),
                            state_answer_hex=hx(answer(2, COMPLETED, 0, struct.pack("<BIB", *after)))))

    groups = []
    for states in ([3, 3], [3, 5], [5, 5], [4, 3]):
        groups.append(dict(name=f"group start refuses states {states}", spec="capture §4.1",
                           states=states, generations=[4, 3, 1], expected_generations=[4, 3, 1],
                           request_hex=hx(request(1, 12, op("oep.fixture.capture-group", "start"), b"", 0x11223344)),
                           answer_hex=hx(answer(1, REJECTED, REASON["unavailable"], tlv(1, b"\6")))))
    for failed_index, completed_first, states_after in ((0, False, [6, 1]), (1, False, [1, 6]), (1, True, [4, 6])):
        groups.append(dict(name=f"group start failure {failed_index}, first completed {completed_first}",
                           spec="capture §4.1", states=[4, 6], generations=[4, 3, 1],
                           failed_index=failed_index, completed_first=completed_first,
                           expected_states=states_after, expected_generations=[5, 4, 2],
                           request_hex=hx(request(1, 12, op("oep.fixture.capture-group", "start"), b"", 0x11223344)),
                           answer_hex=hx(answer(1, COMPLETED, REG["outcomes"]["failed"],
                                                struct.pack("<QIBHIHI", 7000000, 5, 2, 9, 4, 13, 2)))))

    fixtures = dict(spec="fixture §3/§4", i2c_slots_hex=["1122", "33"], i2c_read_lengths=[4, 1, 2],
                    expected_i2c_reads_hex=["1122ffff", "33", "ffff"],
                    counter_before=0xFFFFFFFE, increments=3, expected_counter=0xFFFFFFFF,
                    spi_empty_answer_hex=hx(answer(1, COMPLETED, 0, struct.pack("<BIH", 0, 0, 0))))
    return dict(about="Independent boundary scenarios, not a complete endpoint. Batching has one w8 segment, required 49-byte data overhead, available output and no pending responses; listed chunks are one legal split, not required frame sizes. Storage tuples are storage_state/saved_generation/reason; current generation and pins never change. Group vectors assume a binding, valid session/resources and generation space, no interleaving; only the listed track failure occurs. Fixture reads are consecutive controller transactions. Power-cut tolerance requires separate storage fault-injection tests.",
                batching=batching, reception=reception, serial_loss=serial_loss, storage=storage, groups=groups, fixtures=fixtures)



# ---- capture data formats (capture §1.3 / §1.4 / §3.8 / §3.9 / §4.4) --------------------------------------------------------
def _bits_to_bytes(bits: list[int]) -> bytes:
    """Bits in stream order (capture §1: bit j is byte j // 8, bit j % 8) -> bytes, the tail to a byte boundary with 0."""
    out = bytearray((len(bits) + 7) // 8)
    for j, b in enumerate(bits):
        out[j // 8] |= (b & 1) << (j % 8)
    return bytes(out)


def _uint_bits(v: int, n: int) -> list[int]:
    return [(v >> k) & 1 for k in range(n)]


def logic_block(raw_chans, ev_chans, ev_d, prev_level, first, r, L):
    """One format 1 block (capture §1.3) for samples [first, first + r) of the segment's channel strings. raw_chans: the raw
    channels' level strings (role order); ev_chans / ev_d: the events channels and their D; prev_level[e]: the level of
    the sample before the block (start_level). fallback only where it is required (events > L / 8 bytes)."""
    E = len(ev_chans)
    events, fallback = [], []
    for e, ch in enumerate(ev_chans):
        D = ev_d[e]
        mine = []
        last = prev_level[e]
        t = 0
        while t * D < r:
            lo, hi = t * D, min((t + 1) * D, r)
            n = 0
            for i in range(lo, hi):
                v = int(ch[first + i])
                if v != last:
                    n += 1
                last = v
            if n:
                mine.append((t, e, (last << 7) | min(n, 127)))
            t += 1
        fb = len(mine) * 4 > L // 8
        fallback.append(fb)
        if not fb:
            events += mine
    head = bytearray(_bits_to_bytes([1 if f else 0 for f in fallback]).ljust((E + 7) // 8, b"\0"))
    head += _bits_to_bytes(prev_level).ljust((E + 7) // 8, b"\0")
    head += struct.pack("<I", len(events))
    fb_chans = [ch for ch, f in zip(ev_chans, fallback) if f]
    cols = list(raw_chans) + fb_chans
    bits = []
    for i in range(r):
        for ch in cols:
            bits.append(int(ch[first + i]))
    raw = _bits_to_bytes(bits)
    body = b"".join(struct.pack("<HBB", t, e, st) for t, e, st in events)
    return bytes(head) + raw + body, fallback


def logic_segment(raw_chans, ev_chans, ev_d, L, start_levels):
    """A segment's blocks; start_levels: the level before the segment per events channel (contiguous with the segment
    before) or None (the segment's first sample)."""
    n = len((raw_chans + ev_chans)[0])
    prev = [int(ch[0]) for ch in ev_chans] if start_levels is None else list(start_levels)
    out, fbs = b"", []
    for first in range(0, n, L):
        r = min(L, n - first)
        blk, fb = logic_block(raw_chans, ev_chans, ev_d, prev, first, r, L)
        out += blk
        fbs.append(fb)
        prev = [int(ch[first + r - 1]) for ch in ev_chans]
    return out, fbs


def analog_block(chans, kinds, ds, b, first, r):
    """One format 2 block (capture §1.4): channels in order, each part padded to a byte."""
    out = b""
    for vals, kind, D in zip(chans, kinds, ds):
        bits = []
        if kind == ["packed"]:
            for i in range(r):
                bits += _uint_bits(vals[first + i], b)
        else:
            sw = b + max(0, (D - 1).bit_length())
            for lo in range(0, r, D):
                seg = vals[first + lo:first + min(lo + D, r)]
                if "minmax" in kind:
                    bits += _uint_bits(min(seg), b) + _uint_bits(max(seg), b)
                if "sum" in kind:
                    bits += _uint_bits(sum(seg), sw)
        out += _bits_to_bytes(bits)
    return out


def capture_formats() -> dict:
    lc = []

    def add_logic(name, spec, raw, ev, ev_d, L, segments):
        """segments: [(contiguous_with_before, {chan strings})]"""
        streams, prev_end = [], None
        for contiguous, (raws, evs) in segments:
            start = prev_end if contiguous else None
            data, fbs = logic_segment(raws, evs, ev_d, L, start)
            streams.append({"contiguous": contiguous, "raw": raws, "events": evs, "fallback": fbs, "stream_hex": hx(data)})
            prev_end = [int(ch[-1]) for ch in evs]
        lc.append({"name": name, "spec": spec, "L": L, "R": len(raw), "events_d": ev_d, "segments": streams})

    raw0 = levels(128, range(0, 128, 2))
    slow = levels(128, (3, 4, 5, 9, 70))
    add_logic("raw and events mixed: a raw channel and a D 4 events channel", "capture §1.3", [raw0], [slow], [4], 128,
              [(False, ([raw0], [slow]))])
    busy = levels(128, range(0, 128, 2))
    add_logic("D 1 events past L / 8 bytes: fallback required", "capture §1.3 fallback", [], [busy], [1], 128,
              [(False, ([], [busy]))])
    busyd = levels(128, range(0, 128, 4))
    add_logic("D 2 events past L / 8 bytes: fallback for D > 1", "capture §1.3 fallback (any D)", [], [busyd], [2], 128,
              [(False, ([], [busyd]))])
    a = levels(128, range(100, 128)); b2 = levels(128, ())
    add_logic("start_level across contiguous segments: the change at the boundary is counted in the next segment", "capture §1.3 start_level",
              [], [a], [1], 128, [(False, ([], [a])), (True, ([], [b2]))])
    add_logic("start_level after a gap is the segment's first sample: no change counted at the boundary", "capture §1.3 start_level",
              [], [a], [1], 128, [(False, ([], [a])), (False, ([], [b2]))])
    part = levels(136, (5, 130))
    add_logic("a partial last block (r 8) and a partial last tick (D 16)", "capture §1.3 刻み", [], [part], [16], 128,
              [(False, ([], [part]))])
    sat = levels(512, range(0, 512, 2))
    add_logic("a count saturates at 127 (D 256)", "capture §1.3 出来事", [], [sat], [256], 512, [(False, ([], [sat]))])

    ac = []

    def add_analog(name, spec, chans, kinds, ds, b, L):
        n = len(chans[0])
        data = b"".join(analog_block(chans, kinds, ds, b, first, min(L, n - first)) for first in range(0, n, L))
        ac.append({"name": name, "spec": spec, "b": b, "L": L, "kinds": kinds, "d": ds, "channels": chans, "stream_hex": hx(data)})

    vals10 = [1, 1023, 512, 3, 7, 600, 2, 900, 5, 44]
    add_analog("packed 10 bit, no frame", "capture §1.4 packed", [vals10[:8]], [["packed"]], [1], 10, 8)
    ramp = list(range(100, 140))
    add_analog("minmax and sum together, D 16, a partial interval", "capture §1.4 minmax + sum (sum width b + ceil(log2 D))",
               [ramp], [["minmax", "sum"]], [16], 12, 32)

    st = []
    tb = [(5, 0b01), (0xFFFFFFFF, 0), (7, 0b10), (1, 0b11)]
    raw = b"".join(struct.pack("<I", d) + bytes([v]) for d, v in tb)
    st.append({"name": "format 3 with a long stop (delta 0xFFFFFFFF advances time only)", "spec": "capture §3.8 形式 3",
               "w": 2, "entries": [{"delta": d, "state": v} for d, v in tb], "samples": 3, "stream_hex": hx(raw)})

    ext = []
    mark = b"OEPX" + struct.pack("<IHB", 7, 9, 1) + bytes(5)
    ext.append({"name": "the generation's start mark", "spec": "capture §3.9", "generation": 7, "fn": 9, "format": 1, "bytes_hex": hx(mark)})
    chunk = struct.pack("<HH", 9, 3) + b"\x01\x02\x03"
    ext.append({"name": "a mux 1 chunk", "spec": "capture §3.9 mux 1", "fn": 9, "data_hex": "010203", "bytes_hex": hx(chunk)})
    pkt = struct.pack("<QIHH", 4096, 7, 9, 0) + b"\xaa\xbb"
    ext.append({"name": "a UDP / isochronous packet header", "spec": "capture §3.9 kind 3 / 4", "position": 4096, "generation": 7, "fn": 9,
                "data_hex": "aabb", "bytes_hex": hx(pkt)})

    tx = []
    G = IFACE["oep.fixture.capture-group"]
    bt, ce = G["tlv"]["bind"], G["enum"]["trigger_cond"]
    crit = REG["constants"]["tag_critical"]

    def cond(stage, part, term, src, fn, role, ctype, args):
        return tlv(bt["cond"] | crit, struct.pack("<BBBBHBB", stage, part, term, src, fn, role, ctype) + args)

    expr = (tlv(bt["trigger_source"] | crit, struct.pack("<BQBB", 2, 1000, 1, 0))
            + tlv(bt["stage"] | crit, struct.pack("<BIQB", 0, 1, 0, 0))
            + cond(0, 0, 0, 1, 9, 2, ce["edge"], bytes([1]))
            + cond(0, 0, 0, 1, 13, 0, ce["below"], struct.pack("<IIB", 2000, 8, 0))
            + tlv(bt["stage"] | crit, struct.pack("<BIQB", 1, 1, 100_000, 1))
            + cond(1, 0, 0, 1, 9, 3, ce["edge"], bytes([1]))
            + cond(1, 1, 0, 1, 9, 4, ce["level"], bytes([1, 0])))
    tx.append({"name": "two stages: CS falls while VDD is below; the event is the ACK not coming within 100 us (stage 1, on_timeout 1), the stage aborted while the abort term holds",
               "spec": "capture §4.4", "fns": {"9": "oep.fixture.logic", "13": "oep.fixture.analog"}, "bind_tlvs_hex": hx(expr), "accepted": True})
    two = (tlv(bt["trigger_source"] | crit, struct.pack("<BQBB", 1, 0, 1, 0)) + tlv(bt["stage"] | crit, struct.pack("<BIQB", 0, 1, 0, 0))
           + cond(0, 0, 0, 1, 9, 2, ce["edge"], bytes([1])) + cond(0, 0, 0, 1, 13, 0, ce["cross_up"], struct.pack("<II", 2000, 8)))
    tx.append({"name": "two instantaneous conditions in one term are refused", "spec": "capture §4.4 評価",
               "fns": {"9": "oep.fixture.logic", "13": "oep.fixture.analog"}, "bind_tlvs_hex": hx(two), "accepted": False,
               "refusal": "unsupported"})
    return {"about": "capture data formats and the trigger expression. Vectors fix fallback to the required blocks only (a probe may fall back "
                     "earlier; a host reads the header). logic: per segment the raw / events channels' levels, the fallback chosen per block, "
                     "the stream. analog: values per channel, the stream. external: marks and headers. trigger: bind TLVs.",
            "logic_blocks": lc, "analog_blocks": ac, "state_timed": st, "external": ext, "trigger_expressions": tx}


# ---- settings file (docs/oep-settings-file.ja.md) ------------------------------------------------------------

SF_FORM, SF_KEY = CORE["enum"]["setting_form"], CORE["enum"]["setting_key_kind"]
SF_FLAG = CORE["enum"]["setting_flag"]
# The forms of the items the registry names (core §13.8, transports §7, the interfaces' documents): form, key_kind, keys, max_len, flags
SF_ITEMS = {
    "channel.{}.label": ("text", "channel", 0, 32, 0), "channel.{}.idle": ("enum", "channel", 0, 0, 0),
    "channel.{}.disable": ("bool", "channel", 0, 0, 0), "wifi.{}.ssid": ("text", "index", 4, 32, 0),
    "wifi.{}.passphrase": ("text", "index", 4, 64, SF_FLAG["secret"]), "ipv4.{}.mode": ("enum", "netif", 0, 0, 0),
    "ipv4.{}.address": ("ipv4", "netif", 0, 0, 0), "ipv4.{}.prefix": ("u32", "netif", 0, 0, 0),
    "ipv4.{}.gateway": ("ipv4", "netif", 0, 0, 0), "ipv4.{}.dns": ("ipv4", "netif", 0, 0, 0),
    "rest.{}": ("enum", "channel", 0, 0, 0), "hold.{}": ("bool", "channel", 0, 0, 0),
    "passthrough.{}.rx": ("channel", "transport", 0, 0, 0), "passthrough.{}.baud": ("u32", "transport", 0, 0, 0),
    "passthrough.{}.format": ("enum", "transport", 0, 0, 0),
}
SF_CHOICES = {"channel.{}.idle": CORE["enum"]["channel_idle"], "ipv4.{}.mode": CORE["enum"]["ipv4_mode"],
              "rest.{}": IFACE["oep.wire.rvswd"]["enum"]["rest"], "passthrough.{}.format": {"8n1": 0, "8e1": 0x04}}


def sf_probe(channels, transports, fns):
    """One probe's declarations: fn 0's describe TLVs and the listed fns' (name, instance, items) with their describe TLVs."""
    d, common = CORE["tlv"]["describe"], REG["describe_common"]
    def items_tlvs(items):
        out = b""
        for k, name in enumerate(items, 1):
            form, kind, keys, max_len, flags = SF_ITEMS[name]
            out += tlv(common["setting"], struct.pack("<BBHBB", SF_FORM[form], SF_KEY[kind], keys, max_len, flags) + name.encode())
            for choice, value in SF_CHOICES.get(name, {}).items():
                out += tlv(common["setting_choice"], bytes([k, value]) + choice.replace("_", "-").encode())
        return out
    fn0 = (tlv(d["unit_id"], b"9489dd2ae0953650") + tlv(d["model"], b"rp2350") + tlv(d["firmware"], b"0.0.36")
           + tlv(d["channels"], struct.pack("<H", len(channels)))
           + b"".join(tlv(d["channel_name"], struct.pack("<H", c) + n.encode()) for c, n in enumerate(channels))
           + b"".join(tlv(d["transport"], bytes([i, CORE["enum"]["transport_kind"][k], 0xFF])) for i, k in enumerate(transports))
           + tlv(d["netif"], b"wifi") + items_tlvs(list(CORE["settings"])))
    listed = [{"fn": fn, "name": name, "instance": inst, "describe_tlvs_hex": hx(items_tlvs(items))} for fn, name, inst, items in fns]
    return {"fn0_describe_tlvs_hex": hx(fn0), "list": listed}


def settings_file() -> dict:
    core_items = list(CORE["settings"])
    num = lambda items, name: items.index(name) + 1
    ce = CORE["enum"]
    uart_items, rvswd_items = list(IFACE["oep.fixture.uart"]["settings"]), list(IFACE["oep.wire.rvswd"]["settings"])
    # probe A: channels GPIO0 GPIO1 GPIO5 GPIO14; transports cdc0 hid0; fn 1 rvswd/0, fn 2 uart/0
    a = sf_probe(["GPIO0", "GPIO1", "GPIO5", "GPIO14"], ["usb_cdc", "hid"],
                 [(1, "oep.wire.rvswd", 0, rvswd_items), (2, "oep.fixture.uart", 0, uart_items)])
    def v(fn, number, key, data=b""):
        return struct.pack("<HBHH", fn, number, key, len(data)) + data
    values = (v(0, num(core_items, "channel.{}.label"), 3, b"NRST")
              + v(0, num(core_items, "channel.{}.idle"), 3, bytes([ce["channel_idle"]["pull_up"]]))
              + v(0, num(core_items, "channel.{}.disable"), 1, b"\1")
              + v(0, num(core_items, "wifi.{}.ssid"), 0, b"lab") + v(0, num(core_items, "wifi.{}.passphrase"), 0)
              + v(0, num(core_items, "ipv4.{}.mode"), 1, bytes([ce["ipv4_mode"]["static"]]))
              + v(0, num(core_items, "ipv4.{}.address"), 1, bytes([192, 168, 1, 23]))
              + v(0, num(core_items, "ipv4.{}.prefix"), 1, struct.pack("<I", 24))
              + v(1, num(rvswd_items, "rest.{}"), 2, bytes([IFACE["oep.wire.rvswd"]["enum"]["rest"]["low"]]))
              + v(1, num(rvswd_items, "hold.{}"), 2, b"\1")
              + v(2, num(uart_items, "passthrough.{}.rx"), 0, struct.pack("<H", 1))
              + v(2, num(uart_items, "passthrough.{}.baud"), 0, struct.pack("<I", 115200))
              + v(2, num(uart_items, "passthrough.{}.format"), 0, b"\0"))
    exported = {"oep_settings": 1,
                "probe": {"model": "rp2350", "unit_id": "9489dd2ae0953650", "firmware": "0.0.36"},
                "settings": {"core": {"channel.GPIO14.label": "NRST", "channel.GPIO14.idle": "pull-up", "channel.GPIO1.disable": True,
                                      "wifi.0.ssid": "lab", "wifi.0.passphrase": {"secret": True},
                                      "ipv4.wifi.mode": "static", "ipv4.wifi.address": "192.168.1.23", "ipv4.wifi.prefix": 24},
                             "oep.wire.rvswd/0": {"rest.GPIO5": "low", "hold.GPIO5": True},
                             "oep.fixture.uart/0": {"passthrough.cdc0.rx": "GPIO1", "passthrough.cdc0.baud": 115200,
                                                    "passthrough.cdc0.format": "8n1"}}}
    # probe B: another firmware: channels renumbered, the UART first, no rvswd, one more transport before the CDC
    b = sf_probe(["GPIO14", "GPIO5", "GPIO1", "GPIO0"], ["uart_bridge", "usb_cdc"],
                 [(1, "oep.fixture.uart", 0, uart_items)])
    file_b = json.loads(json.dumps(exported))
    file_b["settings"]["io.example.gone/0"] = {"x": 1}
    def setv(fn, items, name, key, data):
        return {"fn": fn, "number": num(items, name), "key": key, "data_hex": hx(data)}
    import_b = {"current_values_hex": hx(v(0, num(core_items, "wifi.{}.ssid"), 1, b"old")),
                "expected_set": [setv(0, core_items, "channel.{}.label", 0, b"NRST"),
                                 setv(0, core_items, "channel.{}.idle", 0, bytes([ce["channel_idle"]["pull_up"]])),
                                 setv(0, core_items, "channel.{}.disable", 2, b"\1"),
                                 setv(0, core_items, "wifi.{}.ssid", 0, b"lab"),
                                 setv(0, core_items, "ipv4.{}.mode", 1, bytes([ce["ipv4_mode"]["static"]])),
                                 setv(0, core_items, "ipv4.{}.address", 1, bytes([192, 168, 1, 23])),
                                 setv(0, core_items, "ipv4.{}.prefix", 1, struct.pack("<I", 24)),
                                 setv(1, uart_items, "passthrough.{}.rx", 1, struct.pack("<H", 2)),
                                 setv(1, uart_items, "passthrough.{}.baud", 1, struct.pack("<I", 115200)),
                                 setv(1, uart_items, "passthrough.{}.format", 1, b"\0")],
                "expected_unset": [{"fn": 0, "number": num(core_items, "wifi.{}.ssid"), "key": 1}],
                "secret_without_value": [["core", "wifi.0.passphrase"]],
                "unresolved": [["oep.wire.rvswd/0", "rest.GPIO5"], ["oep.wire.rvswd/0", "hold.GPIO5"], ["io.example.gone/0", "x"]]}
    return {"about": "The settings file (docs/oep-settings-file.ja.md): a probe's declarations (fn 0's describe TLVs; each listed fn's name, "
                     "instance and describe TLVs) and its get values (count x value, core §13.5) give the exported file (every value, "
                     "names for numbers, secrets as {\"secret\": true}). Importing that file into another probe gives the values to set "
                     "(in the file's order), the values to unset, the secrets the probe does not hold, and what does not resolve. "
                     "Item numbers follow each fn's setting order; set values are listed in the file's category and member order.",
            "export": [{"name": "export: every value, numbers to names", "spec": "settings file §2, §3",
                        "probe": a, "get_values_hex": hx(values), "file": exported}],
            "import": [{"name": "import into a probe with other numbers", "spec": "settings file §4",
                        "probe": b, "file": file_b, **import_b}]}


FILES = {"checks.json": checks, "cobs.json": cobs, "headers.json": headers, "confirm.json": confirm,
         "refusals.json": refusals, "core_extensions.json": core_extensions,
         "discovery.json": discovery, "sessions.json": sessions, "ops.json": ops, "ops_encoding.json": ops_encoding,
         "logic_layout.json": logic_layout, "interface_profiles.json": interface_profiles,
         "core_lifecycle.json": core_lifecycle, "core_policy.json": core_policy,
         "interface_boundaries.json": interface_boundaries, "capture_formats.json": capture_formats,
         "settings_file.json": settings_file}


def render(build) -> str:
    return json.dumps(build(), indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    outputs = {OUT / name: render(build) for name, build in FILES.items()}
    if args.check:
        stale = [p for p, text in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        for p in stale:
            print(f"stale: {p.relative_to(ROOT)} (run tools/oepvectors1.py)", file=sys.stderr)
        return 1 if stale else 0
    OUT.mkdir(parents=True, exist_ok=True)
    for p, text in outputs.items():
        p.write_text(text, encoding="utf-8")
        print("wrote", p.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
