# Getting started with OEP v1: a first probe and a first host

[日本語](getting-started.ja.md)

Status: **guide** (not normative). It adds no rule; every step points to the normative text, and where this guide and the normative text
differ, the normative text is right. This English text is authoritative; the Japanese version is its translation.

This page is for someone who has never seen OEP. It builds the smallest probe that answers **confirm**, **list** and **describe**, and the
smallest host that finds a probe, confirms it and reads its describe, with every byte on the wire. That is not yet a conforming
implementation: §6 lists what to add next, and [conformance](conformance.md) is the full checklist.

What you need open: [OEP core](oep-core.md) (the rules), `registry/oep-v1.toml` (every number; `generated/oep-v1/` has it as C++, Python and
JS), and [`tests/vectors/`](../tests/vectors/) (bytes to test against).

## 1. The pieces on one page

- **Byte order**: every number is little endian (core §2.1).
- **Frame on a serial port** (UART bridge, USB CDC, built-in USB serial): `0x00 COBS(message + CRC-16) 0x00`. CRC-16/CCITT-FALSE
  (polynomial 0x1021, initial 0xFFFF, no reflection; "123456789" → 0x29B1), appended little endian, then COBS in 254-byte blocks
  (core §3.1). On vendor bulk and TCP the frame is `length(u16) message` with no CRC.
- **Request**: `role(0x01) corr(u16) fn(u16) op(u8) payload` (6-byte header), or with role 0x81 a `session_id(u32)` after op (10-byte header)
  for requests that change state (core §4.1).
- **Answer**: `role(0x02) corr(u16) resolution(u8) detail(u8) payload` (5-byte header). resolution 0x01 completed with detail = outcome
  (0 success), or 0x00 rejected with detail = the reject reason (core §4.2, §4.3).
- **TLV**: `tag(u8) len(u8) value` (len up to 254), or `tag 0xFF len(u16) value` for 255 bytes and more (core §2.2).
- **fn 0** is `oep.core`. Its ops: confirm 0x01, list 0x02, describe 0x03 (core §12).

## 2. The example

One probe, one transport: a UART bridge (transport kind 1, index 0) at the boot speed `uart_bridge_boot_baud`, 115200 8N1 (core §3.4). The
probe's values (from `tests/vectors/confirm.json` and `discovery.json`):

| Value | Example | Where |
|---|---|---|
| max_frame, window, max_inflight | 1024, 4096, 4 | confirm, core §4.4 |
| boot_id | 0x12345678 (a new random value at every boot) | confirm, core §6.5 |
| unit_id | `a1b2c3d4` | describe 0x42, core §7.5 |
| transport | index 0, kind 1 (UART bridge), interface 0xFF (not USB) | describe 0x49, confirm TLV 0x01 |
| max_op_ms | 1000 | describe 0x4D |

The host numbers its requests with corr 1, 2, 3 and onwards (core §4.1).

## 3. The bytes

Every message here is a test vector, named in each section: confirm in `tests/vectors/confirm.json` (and `cobs.json` for the frame), list,
describe and the refusals in `tests/vectors/discovery.json`. `tools/oepvectors1.py` computes them from the text, and `tests/vectors/test_vectors.py`
checks them with an independent COBS and CRC-16 (`binascii.crc_hqx`). Spaces are added for reading only.

### 3.1 confirm (core §7.1)

Vector: `confirm.json`, "revision 1 asked and answered". Request: `"OEP?" min_rev max_rev` = revisions 1 to 1.

```text
message      01 0100 0000 01 | 4f 45 50 3f 01 01
               role corr fn  op | "OEP?" min_rev max_rev
serial frame 00 03 01 01 01 01 0a 01 4f 45 50 3f 01 01 37 c5 00      (CRC-16 0xC537 → 37 c5)
length frame 0c 00 01 01 00 00 00 01 4f 45 50 3f 01 01
```

Answer: `"OEP!" revision flags max_frame(u16) window(u32) max_inflight(u8) boot_id(u32)`, then TLV 0x01 transport (the index of the transport
the confirm came on; always present).

```text
message      02 0100 01 00 | 4f 45 50 21 | 01 | 00 | 0004 | 00100000 | 04 | 78563412 | 01 01 00
               role corr completed success | "OEP!" | rev 1 | flags | max_frame 1024 | window 4096 | max_inflight 4 | boot_id | TLV transport = 0
serial frame 00 03 02 01 02 01 06 4f 45 50 21 01 01 02 04 02 10 01 08 04 78 56 34 12 01 01 03 0d c7 00
```

When the probe handles no revision in the range (here the host asks 2 to 3), it refuses with unsupported, payload tag 0x00, then TLV 0x01
supported = (min 1, max 1) (`confirm.json`, "no revision in the range: unsupported with the supported range"):

```text
request      01 0200 0000 01 | 4f 45 50 3f 02 03
answer       02 0200 00 0b | 00 | 01 02 01 01
               rejected unsupported | tag 0x00 | TLV supported: min 1, max 1
```

### 3.2 list (core §7.2)

Vector: `discovery.json`, "list everything from the first". Request: `flags(u8) first(u16) prefix_len(u8) prefix` = all names from the
first.

```text
message      01 0200 0000 02 | 00 | 0000 | 00
serial frame 00 03 01 02 01 01 02 02 01 01 01 03 98 0c 00
```

Answer: `total(u16) count(u8)`, then each entry preceded by its length: `len(u8) fn(u16) instance(u16) revision(u8) flags(u8) name_len(u8)
name`. The smallest probe has only `oep.core` (fn 0, instance 0, revision 1), which list always counts as its first entry.

```text
message      02 0200 01 00 | 0100 | 01 | 0f | 0000 | 0000 | 01 | 00 | 08 | 6f 65 70 2e 63 6f 72 65
               completed success | total 1 | count 1 | len 15 | fn 0 | instance 0 | rev 1 | flags | name_len 8 | "oep.core"
serial frame 00 03 02 02 02 01 02 01 03 01 0f 01 01 01 02 01 0c 08 6f 65 70 2e 63 6f 72 65 16 e3 00
```

### 3.3 describe (core §7.3, §7.5)

Vector: `discovery.json`, "describe fn 0 from the first". Request: `fn(u16) first(u16)` = fn 0 from its first TLV. A describe request
carries no TLV.

```text
message      01 0300 0000 03 | 0000 | 0000
serial frame 00 03 01 03 01 01 02 03 01 01 01 03 ea 4d 00
```

Answer: `more(u8)`, then the declaration TLVs. The three that every probe sends in fn 0 (core §1.2): unit_id, transport (one per transport),
max_op_ms.

```text
message      02 0300 01 00 | 00 | 42 08 61 31 62 32 63 33 64 34 | 49 03 00 01 ff | 4d 04 e8 03 00 00
               completed success | more 0 | unit_id "a1b2c3d4" | transport: index 0, kind 1, interface 0xFF | max_op_ms 1000
serial frame 00 03 02 03 02 01 01 0d 42 08 61 31 62 32 63 33 64 34 49 03 07 01 ff 4d 04 e8 03 01 03 a8 68 00
```

A describe whose `first` is at or beyond the count of TLVs (here 3) is answered with more 0 and no TLVs (core §7.3; `discovery.json`,
"describe fn 0 from beyond the last: more 0 and no TLVs"):

```text
request      01 0400 0000 03 | 0000 | 0300
answer       02 0400 01 00 | 00
```

### 3.4 Everything else: refuse

The smallest probe refuses every other request by the first reason that applies in the order of core §4.3: a fn it does not have is
unknown_function, an op fn 0 does not have is unknown_operation. Rejected answers have no payload here (`discovery.json`, "refusals").

```text
request fn 7 op 1      01 0500 0700 01            answer 02 0500 00 01    rejected unknown_function
request fn 0 op 0x50   01 0600 0000 50            answer 02 0600 00 02    rejected unknown_operation
```

More refusals, with exact bytes, are in `tests/vectors/refusals.json`.

## 4. A first probe

What the probe does, in order (the references are the rules):

1. **Receive frames.** Keep bytes from one 0x00 to the next; decode COBS; check the CRC-16; a candidate that does not decode or whose CRC does
   not match is not a request (on a serial port it is raw bytes, core §3.4). A pause of `probe_frame_gap_ms` (200 ms) inside a frame restarts
   the reader (core §3.2). Accept messages of at least `min_max_frame` (64) bytes before any confirm (core §3.3).
2. **Read the header.** role 0x01 or 0x81 (frames with another role are discarded, core §2.4). Check fn (unknown_function), then op
   (unknown_operation), then the length of the fixed part (malformed), in the order of core §4.3.
3. **confirm** (payload `OEP?` min_rev max_rev): `min_rev > max_rev` is malformed; if 1 is in [min_rev, max_rev] answer as §3.1, else refuse as §3.1. Put
   the transport TLV on every confirm answer. flags is 0.
4. **list**: match names by label boundaries (`oep` matches `oep.core`; an empty prefix matches everything), start from `first`, put as many
   entries as fit in one frame; total is the count of all matches. A request with flags bits 1 to 7 set is unsupported (core §7.2).
5. **describe**: for fn 0 return the TLVs from `first`; more = 1 when some did not fit; when `first` is at or beyond the count, return more 0 and
   no TLVs. A TLV in the request is malformed. The values do not change while the boot_id is the same (core §7.3).
6. **Answer** with the same corr, on the transport the request came from, in the order the requests arrived, one answer per request (core §4.2,
   §4.4). Frame it as `0x00 COBS 0x00` on a serial port.
7. **boot_id**: choose it at boot from a random source (core §6.5). **unit_id**: lowercase, stable, unique (probe guide §10).

The reference library's [MinimalProbe example](https://github.com/Open-Embedded-Probe/oep-probe-arduino/tree/main/examples/01.Basics/MinimalProbe)
and its guide [writing a probe](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/docs/guide/writing-a-probe.md) show a whole
probe built on that library.

## 5. A first host

1. **Open the port** exclusively (TIOCEXCL on Linux), at 115200 8N1 on a UART bridge, with DTR and RTS asserted (core §3.3, §3.4; host guide §1).
2. **Send confirm** as one write, enclosed in 0x00 on both sides (core §3.1, §3.2). It is the only thing you send to a port you have not
   identified (the probing rule, core §3.3), and it fits in 64 bytes.
3. **Wait** at least `host_wait_add_ms` (1000 ms) + the transfer time (core §4.4). On a serial port that may be a UART bridge the transfer time is
   (L + max_frame × (1 + `notify_pending_max_frames`)) × 10 / baud, L the request frame's length on the wire (17 bytes here). Before the confirm
   answer the host does not know max_frame; the reference client counts `min_max_frame` (64): (17 + 64 × 3) × 10 / 115200 ≈ 18 ms. Waiting longer
   is always allowed.
4. **Receive**: decode every candidate between 0x00 bytes, and also the bytes from opening the port to the first 0x00. Discard candidates that
   do not decode, whose CRC does not match, whose role is unknown, or whose corr you are not waiting for: they are noise (core §3.1, §11.1).
5. **Check the answer**: completed, the same corr, a payload that starts with `OEP!` (core §3.3). If none came, resend once with the same corr
   (`resend_max`), then close the port and send nothing else (core §3.3, §5.2). Keep max_frame, window, max_inflight, boot_id and the transport
   index. Afterwards send no message longer than max_frame (core §3.3).
6. **list** from `first` 0, adding the entries received to `first` until you have `total`. Remember the name → fn map while boot_id stays the same
   (core §7.2).
7. **describe fn 0** from `first` 0; while more = 1, ask again with `first` + the number of TLVs received. Skip tags you do not know (core §2.3).
   Read unit_id (compare ignoring ASCII case; never group by an `x-` unit_id), the transports, max_op_ms. Cache by boot_id (core §7.3, §7.5).
8. **Next**: to change anything, open a session (core §6), then use an interface by its fn. Send `end` when done.

Try the host against the fake probe first (host guide §16):

```sh
python -m oep_client.fake_serve --pty      # prints the pty to open; serves a probe with several interfaces
oep dump --port /dev/pts/N                 # list and describe of every interface, to compare with your host
```

## 6. What to add next

A probe that answers only confirm, list and describe is not yet an OEP probe. In the order most implementations add them:

**Probe** ([conformance](conformance.md) §1):

1. The sessions: open, end, keepalive, lock_state, with the lease and the decision table of core §6.2; role 0x81 checks (session_required,
   no_session, locked, expired).
2. The resend table of core §5.2 (at least max_inflight entries, rejected answers included, discarded at every successful open).
3. The whole refusal order of core §4.3 and the TLV rules of core §2.3 (critical, ignored, repeated, short and long TLVs).
4. subscribe / unsubscribe with the fn 0 heartbeat (core §11), link_source / link_sink (core §12).
5. plan_apply / plan_release when an interface has plan roles (core §8), and the interfaces you want ([conformance](conformance.md) §3).
6. Optional: port_speed on a UART bridge (core §3.5), probe settings ([probe settings](oep-if-probe-config.md)), more transports.

**Host** ([conformance](conformance.md) §2):

1. corr numbering and the single resend (core §4.1, §5.2); resynchronisation on length-prefixed ports (core §5.1).
2. Sessions: a random session_id, the lease from the open answer, keepalive, and what to do on each refusal (host guide §9).
3. Revisions and unknown values (core §2.4, §2.7; host guide §10); notifications if you subscribe (host guide §12).
4. Discovery of USB probes and several transports (core §3.3; host guide §4, §5).

Then check against [conformance](conformance.md) §4: the test vectors, the fake probe, and `oep dump` on a real probe.

## 7. Where to read next

- [Host development guide](host-development-guide.md), [probe development guide](probe-development-guide.md): practice and traps.
- [Glossary](glossary.md): every term the specification defines.
- [Security and safety](security.md): what to keep in mind before shipping.
- [Versioning](versioning.md): what stays stable after the freeze.
