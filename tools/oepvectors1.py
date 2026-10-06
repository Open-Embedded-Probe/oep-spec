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


def op(iface: str, name: str) -> int:
    return next(o["code"] for o in IFACE[iface]["op"] if o["name"] == name)


ROLE_REQUEST, ROLE_ANSWER = REG["roles"]["request"], REG["roles"]["result"]
REJECTED, COMPLETED = REG["resolutions"]["rejected"], REG["resolutions"]["completed"]
REASON = REG["reject_reasons"]
CRITICAL = REG["constants"]["tag_critical"]
IGNORED = REG["constants"]["tag_ignored"]


# ---- checks (transports §1, core §5.2; dmseq "CRC-8") ------------------------------------------------------------

def crc16_ccitt_false(data: bytes) -> int:
    """poly 0x1021, init 0xFFFF, no reflection, no final XOR (transports §1)."""
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def crc32_ieee(data: bytes) -> int:
    """reflected, poly 0xEDB88320, init and final XOR 0xFFFFFFFF (core §5.2)."""
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xEDB88320 if crc & 1 else crc >> 1
    return crc ^ 0xFFFFFFFF


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
    base = min(codes)
    bits = bytearray((max(codes) - base) // 8 + 1)
    for c in codes:
        bits[(c - base) // 8] |= 1 << ((c - base) % 8)
    return bytes([base]) + bytes(bits)


def hx(b: bytes) -> str:
    return b.hex()


# ---- the files --------------------------------------------------------------------------------------------

def checks() -> dict:
    digits = b"123456789"
    syn = 0x98            # T = 1, TO = 0, S = 0, A = 1, SYN = 1, N = 0 (dmseq "Byte order" example)
    host = 0x00           # K = 0, H = 0, M = 0
    return {
        "about": "Check values of the three CRCs of OEP v1.",
        "cases": [
            {"name": "crc16 123456789", "spec": "transports §1", "algorithm": "crc16-ccitt-false",
             "input_hex": hx(digits), "crc": crc16_ccitt_false(digits)},
            {"name": "crc32 123456789", "spec": "core §5.2", "algorithm": "crc32-ieee",
             "input_hex": hx(digits), "crc": crc32_ieee(digits)},
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
    msg = request(1, 0, op("oep.core", "confirm"), b"OEP?\x01\x01")
    crc = crc16_ccitt_false(msg)
    frames = [{"name": "confirm request on a serial port", "spec": "transports §1",
               "message_hex": hx(msg), "crc16": crc, "frame_hex": hx(serial_frame(msg))}]
    return {"about": "COBS (transports §1): the encoding alone, then whole serial-port frames (0x00 COBS(message + CRC-16 LE) 0x00).",
            "encode": cases, "decode_also_accepts": accepted, "frames": frames}


def headers() -> dict:
    c = op("oep.core", "describe")
    return {
        "about": "Message headers (core §4.1, §4.2) and the TLV form (core §2.2). All numbers little endian.",
        "requests": [
            {"name": "request without a session: session_id 0", "role": ROLE_REQUEST, "corr": 0x1234, "fn": 0x0000, "op": c,
             "session_id": 0, "payload_hex": "00000000", "message_hex": hx(request(0x1234, 0, c, bytes(4)))},
            {"name": "request of a session", "role": ROLE_REQUEST, "corr": 0x0102, "fn": 0x0203,
             "op": 0x01, "session_id": 0x11223344, "payload_hex": "",
             "message_hex": hx(request(0x0102, 0x0203, 0x01, b"", 0x11223344))},
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
            {"name": "the smallest ignored", "tag": IGNORED, "value_hex": "00", "tlv_hex": hx(tlv(IGNORED, b"\x00"))},
        ],
    }


def confirm() -> dict:
    confirm_op = op("oep.core", "confirm")
    t_transport = IFACE["oep.core"]["tlv"]["confirm_answer"]["transport"]
    t_supported = IFACE["oep.core"]["tlv"]["unsupported_payload"]["supported"]
    req = request(1, 0, confirm_op, b"OEP?" + bytes([1, 1]))
    fixed = b"OEP!" + struct.pack("<BBHIBI", 1, 0, 1024, 4096, 4, 0x12345678)
    ans = answer(1, COMPLETED, 0, fixed + tlv(t_transport, b"\x00"))
    req_hi = request(2, 0, confirm_op, b"OEP?" + bytes([2, 3]))
    ans_hi = answer(2, REJECTED, REASON["unsupported"], b"\x00" + tlv(t_supported, bytes([1, 1])))
    return {
        "about": "confirm (core §7.1). The answer's values (max_frame 1024, window 4096, max_inflight 4, boot_id 0x12345678, transport index 0) are an example probe's.",
        "exchanges": [
            {"name": "revision 1 asked and answered", "request": {"corr": 1, "min_rev": 1, "max_rev": 1},
             "request_hex": hx(req), "request_serial_frame_hex": hx(serial_frame(req)),
             "request_length_frame_hex": hx(length_frame(req)),
             "answer": {"corr": 1, "revision": 1, "flags": 0, "max_frame": 1024, "window": 4096, "max_inflight": 4,
                        "boot_id": 0x12345678, "transport": 0},
             "answer_hex": hx(ans), "answer_serial_frame_hex": hx(serial_frame(ans))},
            {"name": "no revision in the range: unsupported with the supported range",
             "request": {"corr": 2, "min_rev": 2, "max_rev": 3}, "request_hex": hx(req_hi),
             "answer": {"corr": 2, "reason": "unsupported", "payload_tag": 0, "supported": [1, 1]},
             "answer_hex": hx(ans_hi)},
        ],
    }


def probe_config_hash() -> dict:
    """probe-config §2 hash: canonical form = items sorted by tag, then key compared as numbers field by field, the
    critical bit cleared, each as a TLV (core §2.2); hash = CRC-32 of it. Every item has its one fixed form (probe-config §1)."""
    pc = IFACE["oep.probe.config"]
    item = pc["tlv"]["item"]
    plan, label, idle, slot = item["plan"], item["label"], item["idle"], item["slot"]
    kind = IFACE["oep.fixture.gpio"]["enum"]["drive_kind"]
    mode = pc["enum"]["idle_mode"]
    at_boot = pc["enum"]["slot_attach"]["at_boot"]
    dmseq = IFACE["oep.target.console"]["enum"]["mechanism"]["dmseq"]
    name = b"dut"
    slot0 = (struct.pack("<BHHHBBIIBB", 0, 4, 0x0001, 0x0002, at_boot, 1, 500, 1_000_000, 0, dmseq)
             + bytes([len(name)]) + name + bytes([0]))   # slot 0 on wire fn 4, boot_reset 1, no lock (lock_len 0)
    sent = [   # (tag as sent, value): the order and critical bits the host happened to use
        (label | CRITICAL, struct.pack("<H", 0x0102) + b"nrst"),
        (plan | CRITICAL, struct.pack("<HBH", 0x0100, 1, 2)),
        (idle, struct.pack("<HBBH", 0x0004, mode["output_high"], kind["level"], 1)),
        (plan, struct.pack("<HBH", 0x0003, 2, 5)),
        (slot | CRITICAL, slot0),
        (label, struct.pack("<H", 0x0020) + b"x-boot0"),
        (idle, struct.pack("<HBBH", 0x0005, mode["pull_up"], kind["default"], 0)),
        (plan | CRITICAL, struct.pack("<HBH", 0x0003, 1, 7)),
    ]

    def key(tag: int, value: bytes) -> tuple:
        if tag == plan:
            return (tag,) + struct.unpack_from("<HBH", value)
        if tag == slot:
            return (tag, value[0])
        return (tag, struct.unpack_from("<H", value)[0])

    items = sorted(((t & 0x7F, v) for t, v in sent), key=lambda p: key(*p))
    canonical = b"".join(tlv(t, v) for t, v in items)
    return {
        "about": "The hash of probe.config (oep-if-probe-config §2): items as the host sent them, the canonical form and its CRC-32. "
                 "Keys compare as numbers (channel 0x0020 before 0x0102, although their little-endian bytes compare the other way), "
                 "multi-field keys field by field (plan: fn, role, channel), critical bits cleared. Each item has its one fixed form: "
                 "an idle is 6 bytes (an input idle carries drive_kind 2 = default and drive_value 0), a slot carries boot_reset after attach.",
        "cases": [
            {"name": "plan, label, idle and slot items", "items_sent": [{"tag": t, "value_hex": hx(v)} for t, v in sent],
             "canonical_order": [{"tag": t, "value_hex": hx(v)} for t, v in items],
             "canonical_hex": hx(canonical), "hash": crc32_ieee(canonical)},
            {"name": "no items", "items_sent": [], "canonical_order": [], "canonical_hex": "", "hash": crc32_ieee(b"")},
        ],
    }


def refusals() -> dict:
    """Requests and the answer a probe gives, for the refusals of core §4.3 (and the ignored list of §2.3)."""
    s = 0x11223344
    gpio_set = op("oep.fixture.gpio", "set")
    i2c_conf = op("oep.fixture.i2c-target", "configure")
    rv_attach = op("oep.wire.rvswd", "attach")
    uart_read = op("oep.fixture.uart", "read")
    dm_reset = op("oep.target.riscv-dm", "reset")
    unav = IFACE["oep.core"]["tlv"]["unavailable_payload"]
    max_speed = IFACE["oep.wire.rvswd"]["tlv"]["attach"]["max_speed"]
    ms = tlv(max_speed | CRITICAL, struct.pack("<I", 1_000_000))
    idx_tag = IFACE["oep.fixture.gpio"]["tlv"]["unavailable_payload"]["index"]
    cases = []

    def add(name, spec, fns, req, reason, payload=b"", completed=False):
        corr = struct.unpack_from("<H", req, 1)[0]
        ans = answer(corr, COMPLETED, 0, payload) if completed else answer(corr, REJECTED, REASON[reason], payload)
        cases.append({"name": name, "spec": spec, "fns": fns, "request_hex": hx(req),
                      "answer": "completed success" if completed else reason, "answer_hex": hx(ans)})

    fns_gpio = {"2": "oep.fixture.gpio"}
    add("gpio mode 8 (a value a later revision may define)", "core §2.5, §4.3 order 6; fixture §1", fns_gpio,
        request(0x0010, 2, gpio_set, bytes([1]) + struct.pack("<HB", 3, 8), s), "unsupported",
        b"\x00" + tlv(unav["channel"], struct.pack("<H", 3)) + tlv(idx_tag, b"\x00"))
    add("i2c-target address above 0x7F (excluded by the definition)", "core §4.3 order 5; fixture §3",
        {"3": "oep.fixture.i2c-target"}, request(0x0011, 3, i2c_conf, bytes([0x80, 1]), s), "malformed")
    add("i2c-target mode 4 (a value a later revision may define)", "core §4.3 order 6; fixture §3",
        {"3": "oep.fixture.i2c-target"}, request(0x0012, 3, i2c_conf, bytes([0x50, 4]), s), "unsupported", b"\x00")
    add("attach method 2", "core §4.3 order 6; debug §3", {"4": "oep.wire.rvswd"},
        request(0x0013, 4, rv_attach, bytes([2]) + ms, s), "unsupported", b"\x00")
    add("attach without max_speed (a mandatory TLV)", "debug §1", {"4": "oep.wire.rvswd"},
        request(0x0014, 4, rv_attach, bytes([0]), s), "malformed")
    add("an unknown critical TLV: its tag as received", "core §2.3", {"4": "oep.wire.rvswd"},
        request(0x0015, 4, rv_attach, bytes([0]) + ms + tlv(0x3E | CRITICAL, b""), s), "unsupported", bytes([0x3E | CRITICAL]))
    add("the same non-repeating TLV twice", "core §2.3", {"4": "oep.wire.rvswd"},
        request(0x0016, 4, rv_attach, bytes([0]) + ms + ms, s), "malformed")
    add("a TLV whose length runs past the end of the request", "core §2.2, §4.3 order 5", {"4": "oep.wire.rvswd"},
        request(0x0017, 4, rv_attach, bytes([0, max_speed | CRITICAL]) + struct.pack("<H", 8) + struct.pack("<I", 1_000_000), s), "malformed")
    add("read from 4", "core §4.3 order 6; common §1.2", {"5": "oep.fixture.uart"},
        request(0x0018, 5, uart_read, bytes([4]) + struct.pack("<QH", 0, 64)), "unsupported", b"\x00")
    add("riscv-dm reset mode 3", "core §4.3 order 6; debug §4.3", {"6": "oep.target.riscv-dm"},
        request(0x0019, 6, dm_reset, struct.pack("<HB", 0, 3), s), "unsupported", b"\x00")
    add("confirm min_rev > max_rev", "core §7.1", {},
        request(0x001A, 0, op("oep.core", "confirm"), b"OEP?" + bytes([2, 1])), "malformed")
    add("an unknown non-critical TLV is ignored and listed", "core §2.3", fns_gpio,
        request(0x001B, 2, gpio_set, bytes([1]) + struct.pack("<HB", 3, 0) + tlv(0x3E, b"\x01"), s), "",
        tlv(IGNORED, bytes([0x3E])), completed=True)
    return {
        "about": "Refusals (core §4.3) and the ignored list (core §2.3). `fns` says which interface each fn number is in the example "
                 "(the numbers come from list in a real session). Requests with session_id 0x11223344 come from the session that holds the lock; "
                 "the lock-free read and confirm carry session_id 0. "
                 "The ignored-TLV case assumes channel 3 is in fn 2's plan; the other refusals come before any state check (core §4.3 orders 5 and 6).",
        "cases": cases,
    }


def discovery() -> dict:
    """The example probe of docs/getting-started.md §2, §3 (with fn 0's required ops, core §1.2): list (core §7.2), describe of fn 0 (core §7.3, §7.5) and the
    header refusals of core §4.3 order 1, continuing confirm.json's first exchange (corr 1)."""
    core = IFACE["oep.core"]
    list_op, describe_op = op("oep.core", "list"), op("oep.core", "describe")
    d = core["tlv"]["describe"]
    unit_id, max_op_ms, discoverable = "a1b2c3d4", 1000, 0   # a UART bridge: not the project's USB VID:PID, so 0 (core §7.5)
    t_index, t_kind, t_interface = 0, core["enum"]["transport_kind"]["uart_bridge"], 0xFF

    name = b"oep.core"
    entry = struct.pack("<HHBBB", 0, 0, core["revision"], 0, len(name)) + name
    list_req = request(2, 0, list_op, struct.pack("<BHB", 0, 0, 0))
    list_ans = answer(2, COMPLETED, 0, struct.pack("<HB", 1, 1) + entry)          # count x entry, no element len (core §2.3, §7.2)

    # core §1.2: fn 0's required ops, all set in ops; this probe has no plan role, so no plan_apply / plan_release
    offered = [op("oep.core", n) for n in ("confirm", "list", "describe", "open", "end", "keepalive", "lock_state", "subscribe", "unsubscribe")]
    decl_tlvs = [tlv(REG["describe_common"]["ops"], ops_value(offered)), tlv(d["unit_id"], unit_id.encode()), tlv(d["transport"], bytes([t_index, t_kind, t_interface])),
                 tlv(d["discoverable"], bytes([discoverable])), tlv(d["max_op_ms"], struct.pack("<I", max_op_ms))]
    decl, n_decl = b"".join(decl_tlvs), len(decl_tlvs)
    desc_req = request(3, 0, describe_op, struct.pack("<HH", 0, 0))
    desc_ans = answer(3, COMPLETED, 0, b"\x00" + decl)
    past_req = request(4, 0, describe_op, struct.pack("<HH", 0, n_decl))
    past_ans = answer(4, COMPLETED, 0, b"\x00")

    no_fn = request(5, 7, 0x01, b"")
    no_op = request(6, 0, 0x50, b"")
    return {
        "about": "list, describe and the header refusals of the example probe (docs/getting-started.md §2, §3, with its §6 steps 1 and 4 done): only fn 0 (oep.core, "
                 "instance 0, revision 1) whose ops are fn 0's required ops of core §1.2 (confirm, list, describe, open, end, keepalive, lock_state, subscribe, unsubscribe; no plan role, so no plan_apply / plan_release) in describe's common tag ops, one UART bridge (transport index 0, interface 0xFF), unit_id \"a1b2c3d4\", discoverable 0 (it does not enumerate with the project's USB VID:PID), max_op_ms 1000. "
                 "The corrs continue confirm.json's first exchange (corr 1): list 2, describe 3, describe past the end 4, the refusals 5 and 6. "
                 "Those values are an example probe's.",
        "exchanges": [
            {"name": "list everything from the first", "spec": "core §7.2",
             "request": {"corr": 2, "flags": 0, "first": 0, "prefix": ""},
             "request_hex": hx(list_req), "request_serial_frame_hex": hx(serial_frame(list_req)),
             "answer": {"corr": 2, "total": 1, "entries": [{"fn": 0, "instance": 0, "revision": core["revision"], "flags": 0,
                                                            "name": name.decode()}]},
             "answer_hex": hx(list_ans), "answer_serial_frame_hex": hx(serial_frame(list_ans))},
            {"name": "describe fn 0 from the first", "spec": "core §7.3, §7.5",
             "request": {"corr": 3, "fn": 0, "first": 0},
             "request_hex": hx(desc_req), "request_serial_frame_hex": hx(serial_frame(desc_req)),
             "answer": {"corr": 3, "more": 0, "ops": offered, "unit_id": unit_id,
                        "transports": [{"index": t_index, "kind": t_kind, "interface": t_interface}],
                        "discoverable": discoverable, "max_op_ms": max_op_ms},
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



def sessions() -> dict:
    """Scenarios of the session decision table (core §6.2), the resend table (core §5.2) and the release at end (core §9), as
    request / answer byte pairs from a stated initial state, for the example probe of confirm.json (boot_id 0x12345678)."""
    open_op, end_op, keep_op, state_op = (op("oep.core", n) for n in ("open", "end", "keepalive", "lock_state"))
    boot_id, lease = 0x12345678, 2000
    S, T = 0x11223344, 0x55667788
    owner_tag = IFACE["oep.core"]["tlv"]["lock_state_answer"]["owner"]

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
         "spec": "core §5.2, §6.2, §6.4, §9", "initial": "lock free, no session has held it since boot",
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
             step("the same open resent (open is not looked up in the table): the lease restarts, nothing is released",
                  request(3, 0, open_op, struct.pack("<IB", lease, 0), S), opened(3)),
             step("lock_state with session_id 0: held, the remaining time as if no time had passed",
                  request(4, 0, state_op, b""), ok(4, struct.pack("<BI", 1, lease))),
         ]},
    ]
    return {
        "about": "Session scenarios (core §5.2, §6, §9) of the example probe of confirm.json (boot_id 0x12345678). Each scenario starts from its "
                 "initial state; the steps are sent in order on one transport, each answered before the next. Remaining times are shown as if no time "
                 "had passed between the steps: a real probe answers the time actually left. S = 0x11223344, T = 0x55667788.",
        "scenarios": scenarios,
    }


def ops() -> dict:
    """Per-op byte vectors: a request, the probe state it assumes, and the answer, for ops of the standard interfaces. Each answer's
    fixed part is the one the interface document gives; sequences are count x element with no element length (core §2.3)."""
    S = 0x11223344
    cases = []

    def add(name, spec, fns, state, req, ans):
        cases.append({"name": name, "spec": spec, "fns": fns, "state": state, "request_hex": hx(req), "answer_hex": hx(ans)})

    ok = lambda corr, payload=b"": answer(corr, COMPLETED, 0, payload)
    failed = lambda corr, payload=b"": answer(corr, COMPLETED, REG["outcomes"]["failed"], payload)
    rej = lambda corr, reason, payload=b"": answer(corr, REJECTED, REASON[reason], payload)
    unav = IFACE["oep.core"]["tlv"]["unavailable_payload"]
    cause = IFACE["oep.core"]["enum"]["unavailable_cause"]

    # oep.link (oep-if-link §1, §2)
    link = {"1": "oep.link"}
    add("link source: 8 bytes, byte k = k & 0xFF", "oep-if-link §2", link, "max_frame 1024",
        request(0x20, 1, op("oep.link", "source"), struct.pack("<I", 8)), ok(0x20, struct.pack("<H", 8) + bytes(range(8))))
    add("link source: length 0", "oep-if-link §2", link, "—",
        request(0x21, 1, op("oep.link", "source"), struct.pack("<I", 0)), ok(0x21, struct.pack("<H", 0)))
    add("link sink: 3 bytes, an empty answer", "oep-if-link §2", link, "—",
        request(0x22, 1, op("oep.link", "sink"), struct.pack("<H", 3) + b"\xaa\xbb\xcc"), ok(0x22))
    add("link sink: count larger than the bytes that follow", "oep-if-link §2, core §4.3 order 5", link, "—",
        request(0x23, 1, op("oep.link", "sink"), struct.pack("<H", 5) + b"\xaa\xbb\xcc"), rej(0x23, "malformed"))
    add("link port_speed not offered (not set in ops)", "oep-if-link §1, core §1.2", link, "ops of fn 1: source and sink only",
        request(0x24, 1, op("oep.link", "port_speed"), struct.pack("<BIBHI", 0, 921600, 0, 2000, 3000), S), rej(0x24, "unknown_operation"))

    # oep.fixture.gpio (fixture §1)
    gpio = {"2": "oep.fixture.gpio"}
    gset, gread = op("oep.fixture.gpio", "set"), op("oep.fixture.gpio", "read")
    gidx = IFACE["oep.fixture.gpio"]["tlv"]["unavailable_payload"]["index"]
    add("gpio set: channel 3 output high", "fixture §1", gpio, "session S holds the lock; channel 3 in fn 2's plan; modes 0 to 4 declared",
        request(0x30, 2, gset, bytes([1]) + struct.pack("<HB", 3, 4), S), ok(0x30))
    add("gpio read: channel 3 reads 1", "fixture §1", gpio, "as above, after the set; no drive_levels",
        request(0x31, 2, gread, bytes([1]) + struct.pack("<H", 3)), ok(0x31, bytes([1, 1])))
    add("gpio set: channel 9 not in the plan", "fixture §1, core §4.3 order 7", gpio, "channel 9 in no plan of fn 2",
        request(0x32, 2, gset, bytes([2]) + struct.pack("<HBHB", 3, 4, 9, 0), S),
        rej(0x32, "unavailable", tlv(unav["channel"], struct.pack("<H", 9)) + tlv(gidx, b"\x01")))
    add("gpio set without a session: session_required", "core §4.1, §4.3 order 1", gpio, "—",
        request(0x33, 2, gset, bytes([1]) + struct.pack("<HB", 3, 4)), rej(0x33, "session_required"))
    add("gpio set: n = 2 with one element", "core §4.3 order 5", gpio, "—",
        request(0x34, 2, gset, bytes([2]) + struct.pack("<HB", 3, 4), S), rej(0x34, "malformed"))

    # oep.wire.rvswd (debug §1 to §3)
    rv = {"4": "oep.wire.rvswd"}
    users = IFACE["oep.wire.rvswd"]["enum"]["connection_users"]
    scheme = REG["common"]["enum"]["target_id_scheme"]["wch_dmi_7f"]
    entry = struct.pack("<HHHIBBBB", 1, 0x0001, 0x0002, 1_000_000, users["host_session"], 0xFF, scheme, 4) + struct.pack("<I", 0x00203500)
    add("rvswd connections: one connection with a target_id", "debug §2.1", rv,
        "connection 1 on channels 1 / 2 at 1 MHz, attached by the session, no slot, target_id scheme 1 = 0x00203500",
        request(0x40, 4, op("oep.wire.rvswd", "connections"), bytes([0])), ok(0x40, bytes([0, 1]) + entry))
    add("rvswd connections: first beyond the count", "core §7.3 end of paging, debug §2.1", rv, "as above",
        request(0x41, 4, op("oep.wire.rvswd", "connections"), bytes([1])), ok(0x41, bytes([0, 0])))
    kind = IFACE["oep.wire.rvswd"]["enum"]["scan_kind"]["riscv_dm"]
    add("rvswd scan: one combination listed and found", "debug §1, §3", rv, "session S; channels 1 / 2 free and allowed; a DM answers DMSTATUS 0x00400382",
        request(0x42, 4, op("oep.wire.rvswd", "scan"), bytes([1]) + struct.pack("<HH", 1, 2), S),
        ok(0x42, bytes([1, 1]) + struct.pack("<BHHI", kind, 1, 2, 0x00400382)))
    add("rvswd scan: count 0 with nothing left from skip", "debug §1", rv, "session S; the count = 0 sequence has 4 combinations",
        request(0x43, 4, op("oep.wire.rvswd", "scan"), bytes([0]) + tlv(IFACE["oep.wire.rvswd"]["tlv"]["scan"]["skip"], struct.pack("<H", 4)), S),
        ok(0x43, bytes([0, 0])))
    add("rvswd scan: count > 0 with skip", "debug §1", rv, "—",
        request(0x44, 4, op("oep.wire.rvswd", "scan"), bytes([1]) + struct.pack("<HH", 1, 2)
                + tlv(IFACE["oep.wire.rvswd"]["tlv"]["scan"]["skip"], struct.pack("<H", 1)), S), rej(0x44, "malformed"))

    # oep.target.riscv-dm (debug §4)
    dm = {"6": "oep.target.riscv-dm"}
    add("riscv-dm halt: halted", "debug §4.2", dm, "session S; connection 1 open; the hart halts",
        request(0x50, 6, op("oep.target.riscv-dm", "halt"), struct.pack("<H", 1), S), ok(0x50, bytes([REG["status"]["ok"]])))
    add("riscv-dm halt on an unknown connection", "core §4.3 order 8", dm, "no connection 9",
        request(0x51, 6, op("oep.target.riscv-dm", "halt"), struct.pack("<H", 9), S), rej(0x51, "no_connection"))
    add("riscv-dm run not offered", "debug §4, core §1.2", dm, "ops of fn 6: dmi, halt, resume (09 02 00 01 07)",
        request(0x52, 6, op("oep.target.riscv-dm", "run"), struct.pack("<HIIBB", 1, 0x20000000, 100, 0, 0), S), rej(0x52, "unknown_operation"))
    rd = op("oep.target.riscv-dm", "dmi")
    add("riscv-dm dmi: one read of DMSTATUS", "debug §4.1", dm, "session S; connection 1; DMSTATUS reads 0x00400382",
        request(0x53, 6, rd, struct.pack("<HH", 1, 1) + bytes([IFACE["oep.target.riscv-dm"]["enum"]["dmi_step"]["read"], 0x11]), S),
        ok(0x53, struct.pack("<HBHI", 1, 0, 1, 0x00400382)))
    add("riscv-dm dmi: n = 0", "debug §4", dm, "session S; connection 1",
        request(0x54, 6, rd, struct.pack("<HH", 1, 0), S), ok(0x54, struct.pack("<HBH", 0, 0, 0)))
    add("riscv-dm dmi: an unknown step kind", "debug §4.1, core §4.3 order 5", dm, "—",
        request(0x55, 6, rd, struct.pack("<HH", 1, 1) + bytes([0x10, 0x11]), S), rej(0x55, "malformed"))

    # oep.target.console (console §1, common §1)
    con = {"7": "oep.target.console"}
    mark_kind = REG["common"]["enum"]["mark_kind"]
    mark = struct.pack("<IQBQB", 0, 0, mark_kind["attach"], 1_000_000, 0)
    # connection 1 (the wire cases) and the stream share core §9's one number space: the stream opened on it is 2
    add("console marks: one attach mark", "common §1.3, console §1", con, "stream 2 with one mark (serial 0, position 0, attach at 1 ms)",
        request(0x60, 7, op("oep.target.console", "marks"), struct.pack("<HI", 2, 0)), ok(0x60, bytes([0, 1]) + mark))
    st = IFACE["oep.target.console"]["enum"]
    sentry = struct.pack("<HHBBB", 2, 1, st["mechanism"]["dmseq"], st["stream_users"]["host_session"], st["stream_state"]["open"])
    add("console streams: one open stream", "console §1, core §9", con, "stream 2 on connection 1 (one number space: connection 1, then stream 2), dmseq, opened by the session",
        request(0x61, 7, op("oep.target.console", "streams"), bytes([0])), ok(0x61, bytes([0, 1]) + sentry))
    add("console read: empty at the write position", "common §1.2", con, "stream 2, 5 bytes written (position 5)",
        request(0x62, 7, op("oep.target.console", "read"), struct.pack("<HBQH", 2, 0, 5, 64)),
        ok(0x62, struct.pack("<QBH", 5, 0, 0)))
    add("console read from 4", "common §1.2, core §4.3 order 6", con, "—",
        request(0x63, 7, op("oep.target.console", "read"), struct.pack("<HBQH", 2, 4, 0, 64)), rej(0x63, "unsupported", b"\x00"))

    # oep.probe.config (probe settings §3.3)
    pc = {"8": "oep.probe.config"}
    pce = IFACE["oep.probe.config"]["enum"]
    slot_state = (struct.pack("<BBHQQ", 0, pce["slot_state"]["connected"], 1, 1_000_000, 0xFFFFFFFFFFFFFFFF)
                  + bytes([scheme, 4]) + struct.pack("<I", 0x00203500))
    bind_state = bytes([0, pce["bind_mode"]["last_reset"], 0, pce["bind_flow"]["streaming"]])
    add("probe.config state: one slot and one bind", "probe settings §3.3", pc,
        "no save; slot 0 connected on connection 1 (last try at 1 ms, no retry with reset), target_id scheme 1; bind on port 0, last-reset, streaming",
        request(0x70, 8, op("oep.probe.config", "state"), bytes([0, 0])),
        ok(0x70, struct.pack("<BBIB", 0, pce["storage_state"]["none"], 0, 0) + bytes([1]) + slot_state + bytes([1]) + bind_state))
    add("probe.config save not offered", "probe settings §2, core §1.2", pc, "ops without save and erase; no storage tag",
        request(0x71, 8, op("oep.probe.config", "save"), b"", S), rej(0x71, "unknown_operation"))
    idle_tag = IFACE["oep.probe.config"]["tlv"]["item"]["idle"]
    add("probe.config set: an input idle with a drive other than kind 2 value 0", "probe settings §1", pc, "session S",
        request(0x72, 8, op("oep.probe.config", "set"), tlv(idle_tag | CRITICAL, struct.pack("<HBBH", 4, 0, 0, 1)), S), rej(0x72, "malformed"))
    add("probe.config set: an idle value of 3 bytes", "probe settings §1, core §2.3", pc, "session S",
        request(0x73, 8, op("oep.probe.config", "set"), tlv(idle_tag | CRITICAL, struct.pack("<HB", 4, 0)), S), rej(0x73, "malformed"))

    # oep.fixture.logic (capture §2, §3.2)
    lg = {"9": "oep.fixture.logic"}
    seg = struct.pack("<IQIQIIBI", 0, 0, 1000, 5_000_000, 50, 0xFFFFFFFF, 0, 1)
    add("logic segments: one segment", "capture §2.2, §3.2", lg, "one-shot done, generation 1: 1000 samples from 5 ms, ±50 ns, no trigger",
        request(0x80, 9, op("oep.fixture.logic", "segments"), struct.pack("<I", 0)), ok(0x80, bytes([0, 1]) + seg))
    add("logic read: another generation", "capture §3.2", lg, "generation 1",
        request(0x81, 9, op("oep.fixture.logic", "read"), struct.pack("<IQI", 2, 0, 64)),
        rej(0x81, "unavailable", tlv(unav["cause"], bytes([cause["wrong_state"]]))))
    return {
        "about": "Per-op byte vectors. `fns` says which interface each fn number is in the example; `state` is the probe state the answer assumes. "
                 "Requests with session_id 0x11223344 come from the session that holds the lock; lock-free requests carry 0. "
                 "Answers carry no ignored TLV because no request TLV is ignored.",
        "cases": cases,
    }

FILES = {"checks.json": checks, "cobs.json": cobs, "headers.json": headers, "confirm.json": confirm,
         "probe_config_hash.json": probe_config_hash, "refusals.json": refusals,
         "discovery.json": discovery, "sessions.json": sessions, "ops.json": ops}


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
