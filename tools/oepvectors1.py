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
ROLE_SESSION = REG["constants"]["role_session_flag"]
REJECTED, COMPLETED = REG["resolutions"]["rejected"], REG["resolutions"]["completed"]
REASON = REG["reject_reasons"]
CRITICAL = REG["constants"]["tag_critical"]
IGNORED = REG["constants"]["tag_ignored"]


# ---- checks (core §3.1, §5.2; dmseq "CRC-8") ------------------------------------------------------------

def crc16_ccitt_false(data: bytes) -> int:
    """poly 0x1021, init 0xFFFF, no reflection, no final XOR (core §3.1)."""
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


# ---- COBS (core §3.1) -------------------------------------------------------------------------------------

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
    if len(value) <= 254:
        return bytes([tag, len(value)]) + value
    return bytes([tag, 0xFF]) + struct.pack("<H", len(value)) + value


def request(corr: int, fn: int, op_code: int, payload: bytes, session: int | None = None) -> bytes:
    if session is None:
        return struct.pack("<BHHB", ROLE_REQUEST, corr, fn, op_code) + payload
    return struct.pack("<BHHBI", ROLE_REQUEST | ROLE_SESSION, corr, fn, op_code, session) + payload


def answer(corr: int, resolution: int, detail: int, payload: bytes = b"") -> bytes:
    return struct.pack("<BHBB", ROLE_ANSWER, corr, resolution, detail) + payload


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
            {"name": "crc16 123456789", "spec": "core §3.1", "algorithm": "crc16-ccitt-false",
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
    frames = [{"name": "confirm request on a serial port", "spec": "core §3.1",
               "message_hex": hx(msg), "crc16": crc, "frame_hex": hx(serial_frame(msg))}]
    return {"about": "COBS (core §3.1): the encoding alone, then whole serial-port frames (0x00 COBS(message + CRC-16 LE) 0x00).",
            "encode": cases, "decode_also_accepts": accepted, "frames": frames}


def headers() -> dict:
    c = op("oep.core", "describe")
    return {
        "about": "Message headers (core §4.1, §4.2). All numbers little endian.",
        "requests": [
            {"name": "request without session_id", "role": ROLE_REQUEST, "corr": 0x1234, "fn": 0x0000, "op": c,
             "session_id": None, "payload_hex": "00000000", "message_hex": hx(request(0x1234, 0, c, bytes(4)))},
            {"name": "request with session_id", "role": ROLE_REQUEST | ROLE_SESSION, "corr": 0x0102, "fn": 0x0203,
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
            {"name": "short form", "tag": 0x10, "value_hex": "0102", "tlv_hex": hx(tlv(0x10, b"\x01\x02"))},
            {"name": "short form, critical", "tag": 0x10 | CRITICAL, "value_hex": "0102", "tlv_hex": hx(tlv(0x90, b"\x01\x02"))},
            {"name": "254 bytes: still the short form", "tag": 0x41, "value_len": 254, "value_byte": 0xAA,
             "tlv_hex": hx(tlv(0x41, b"\xaa" * 254))},
            {"name": "255 bytes: the long form", "tag": 0x41, "value_len": 255, "value_byte": 0xAA,
             "tlv_hex": hx(tlv(0x41, b"\xaa" * 255))},
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
    """probe-config §2 hash (PC-7): canonical form = items sorted by tag, then key compared as numbers field by
    field, the critical bit cleared, each as the unique TLV encoding; hash = CRC-32 of it."""
    item = IFACE["oep.probe.config"]["tlv"]["item"]
    plan, label, idle = item["plan"], item["label"], item["idle"]
    sent = [   # (tag as sent, value): the order and critical bits the host happened to use
        (label | CRITICAL, struct.pack("<H", 0x0102) + b"nrst"),
        (plan | CRITICAL, struct.pack("<HBH", 0x0100, 1, 2)),
        (idle, struct.pack("<HB", 0x0004, 4) + struct.pack("<BH", 0, 1)),
        (plan, struct.pack("<HBH", 0x0003, 2, 5)),
        (label, struct.pack("<H", 0x0020) + b"x-boot0"),
        (plan | CRITICAL, struct.pack("<HBH", 0x0003, 1, 7)),
    ]

    def key(tag: int, value: bytes) -> tuple:
        if tag == plan:
            return (tag,) + struct.unpack_from("<HBH", value)
        return (tag, struct.unpack_from("<H", value)[0])

    items = sorted(((t & 0x7F, v) for t, v in sent), key=lambda p: key(*p))
    canonical = b"".join(tlv(t, v) for t, v in items)
    return {
        "about": "The hash of probe.config (oep-if-probe-config §2): items as the host sent them, the canonical form and its CRC-32. "
                 "Keys compare as numbers (channel 0x0020 before 0x0102, although their little-endian bytes compare the other way), "
                 "multi-field keys field by field (plan: fn, role, channel), critical bits cleared.",
        "cases": [
            {"name": "plan, label and idle items", "items_sent": [{"tag": t, "value_hex": hx(v)} for t, v in sent],
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
    add("a TLV in the long form whose value fits the short form", "core §2.2", {"4": "oep.wire.rvswd"},
        request(0x0017, 4, rv_attach, bytes([0, max_speed | CRITICAL, 0xFF, 4, 0]) + struct.pack("<I", 1_000_000), s), "malformed")
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
                 "(the numbers come from list in a real session). Requests with role 0x81 come from session 0x11223344, which holds the lock. "
                 "The ignored-TLV case assumes channel 3 is in fn 2's plan; the other refusals come before any state check (core §4.3 orders 5 and 6).",
        "cases": cases,
    }


def discovery() -> dict:
    """The smallest probe of docs/getting-started.md §2, §3: list (core §7.2), describe of fn 0 (core §7.3, §7.5) and the
    header refusals of core §4.3 order 1, continuing confirm.json's first exchange (corr 1)."""
    core = IFACE["oep.core"]
    list_op, describe_op = op("oep.core", "list"), op("oep.core", "describe")
    d = core["tlv"]["describe"]
    unit_id, max_op_ms = "a1b2c3d4", 1000
    t_index, t_kind, t_interface = 0, core["enum"]["transport_kind"]["uart_bridge"], 0xFF

    name = b"oep.core"
    entry = struct.pack("<HHBBB", 0, 0, core["revision"], 0, len(name)) + name
    list_req = request(2, 0, list_op, struct.pack("<BHB", 0, 0, 0))
    list_ans = answer(2, COMPLETED, 0, struct.pack("<HB", 1, 1) + bytes([len(entry)]) + entry)

    decl = (tlv(d["unit_id"], unit_id.encode()) + tlv(d["transport"], bytes([t_index, t_kind, t_interface]))
            + tlv(d["max_op_ms"], struct.pack("<I", max_op_ms)))
    desc_req = request(3, 0, describe_op, struct.pack("<HH", 0, 0))
    desc_ans = answer(3, COMPLETED, 0, b"\x00" + decl)
    past_req = request(4, 0, describe_op, struct.pack("<HH", 0, 3))
    past_ans = answer(4, COMPLETED, 0, b"\x00")

    no_fn = request(5, 7, 0x01, b"")
    no_op = request(6, 0, 0x50, b"")
    return {
        "about": "list, describe and the header refusals of the smallest probe (docs/getting-started.md §2, §3): only fn 0 (oep.core, "
                 "instance 0, revision 1), one UART bridge (transport index 0, interface 0xFF), unit_id \"a1b2c3d4\", max_op_ms 1000. "
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
             "answer": {"corr": 3, "more": 0, "unit_id": unit_id,
                        "transports": [{"index": t_index, "kind": t_kind, "interface": t_interface}], "max_op_ms": max_op_ms},
             "answer_hex": hx(desc_ans), "answer_serial_frame_hex": hx(serial_frame(desc_ans))},
            {"name": "describe fn 0 from beyond the last: more 0 and no TLVs", "spec": "core §7.3 end of paging",
             "request": {"corr": 4, "fn": 0, "first": 3},
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


FILES = {"checks.json": checks, "cobs.json": cobs, "headers.json": headers, "confirm.json": confirm,
         "probe_config_hash.json": probe_config_hash, "refusals.json": refusals,
         "discovery.json": discovery}


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
