# Getting started with OEP v1: the first probe and the first host

[日本語](getting-started.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative). It adds no rules. Every step points at the normative text, and where this guide and the normative text disagree, the normative text is right.

A page for people seeing OEP for the first time. It builds the smallest probe that answers **confirm**, **list** and **describe**, and the smallest host that finds a probe, confirms it and
reads describe, together with every byte on the line. This is not yet a conforming implementation: what to add next is in §6,
and the full checklist is [conformance](conformance.md).

Keep these open: [OEP core](oep-core.md) (the rules), `registry/oep-v1.toml` (every number; `generated/oep-v1/` has C, C++, Python and JS forms of it),
[`tests/vectors/`](../tests/vectors/) (the byte strings used for checking).

## 1. The parts on one page

- **Byte order**: all numbers are little endian (core §2.1).
- **Serial port frames** (UART bridge, USB CDC, built-in USB serial): `0x00 COBS(message + CRC-16) 0x00`. CRC-16/CCITT-FALSE
  (polynomial 0x1021, initial value 0xFFFF, no reflection; "123456789" → 0x29B1) is attached in little endian, and it becomes COBS with 254 byte blocks
  (transports §1). Vendor bulk and TCP frames are `length(u16) message`, with no CRC.
- **Request**: `role(0x01) corr(u16) fn(u16) op(u8) session_id(u32) payload` (header 10 bytes). session_id 0 means no session.
  A session's requests carry its id (core §4.1).
- **Answer**: `role(0x02) corr(u16) resolution(u8) detail(u8) payload` (header 5 bytes). With resolution 0x01 completed, detail is the outcome
  (0 success); with 0x00 rejected, detail is the reason for refusal (core §4.2, §4.3).
- **TLV**: `tag(u8) len(u16) value`. One shape regardless of length (core §2.2).
- **fn 0** is the core; it has no name and is not in list. Its ops are confirm 0x01, list 0x02, describe 0x03 (core §11).

## 2. The example

One probe, one transport: a UART bridge (transport kind 1, index 0) at the boot speed `uart_bridge_boot_baud`, 115200 8N1 (transports §4).
The probe's values (those of `tests/vectors/confirm.json` and `discovery.json`):

| Value | Example | Where |
|---|---|---|
| max_frame, window, max_inflight | 1024, 4096, 4 | confirm, core §4.4 |
| boot_id | 0x12345678 (a new random number at every boot) | confirm, core §6.5 |
| unit_id | `a1b2c3d4` | describe 0x42, core §7.5 |
| transport | index 0, kind 1 (UART bridge), interface 0xFF (not USB) | describe 0x49, confirm TLV 0x01 |
| max_op_ms | 1000 | describe 0x4D |

The host numbers its requests corr 1, 2, 3 in order (core §4.1).

## 3. The bytes

Every message here is a test vector, and its name is given in each section: confirm in `tests/vectors/confirm.json` (frames in `cobs.json`), list,
describe and refusals in `tests/vectors/discovery.json`. `tools/oepvectors1.py` computes them from the text, and `tests/vectors/test_vectors.py` checks them with separately written
COBS and CRC-16 (`binascii.crc_hqx`). Spaces are only for reading.

### 3.1 confirm (core §7.1)

Vector: "revision 1 asked and answered" of `confirm.json`. Request: `"OEP?" min_rev max_rev` = revision 1 to 1.

```text
message      01 0100 0000 01 00000000 | 4f 45 50 3f 01 01
               role corr fn op session_id | "OEP?" min_rev max_rev
serial frame 00 03 01 01 01 01 02 01 01 01 01 09 4f 45 50 3f 01 01 08 96 00      (CRC-16 0x9608 → 08 96)
length frame 10 00 01 01 00 00 00 01 00 00 00 00 4f 45 50 3f 01 01
```

Answer: `"OEP!" revision max_frame(u16) window(u32) max_inflight(u8) boot_id(u32)`, followed by TLV 0x01 transport (the index of the transport the confirm
came on; always attached, core §7.1).

```text
message      02 0100 01 00 | 4f 45 50 21 | 01 | 0004 | 00100000 | 04 | 78563412 | 01 01 00 00
               role corr completed success | "OEP!" | rev 1 | max_frame 1024 | window 4096 | max_inflight 4 | boot_id | TLV transport = 0
serial frame 00 03 02 01 02 01 06 4f 45 50 21 01 02 04 02 10 01 08 04 78 56 34 12 01 01 01 03 61 9e 00
```

When no revision in the range can be handled (here the host asks for 2 to 3), the probe refuses with unsupported, and the payload is tag 0x00 followed by
TLV 0x01 supported = (min 1, max 1) ("no revision in the range: unsupported with the supported range" of `confirm.json`):

```text
request      01 0200 0000 01 00000000 | 4f 45 50 3f 02 03
answer       02 0200 00 0b | 00 | 01 02 00 01 01
               rejected unsupported | tag 0x00 | TLV supported: min 1, max 1
```

### 3.2 list (core §7.2)

Vector: "list everything from the first" of `discovery.json`. Request: `first(u16)` = from the first interface.

```text
message      01 0200 0000 02 00000000 | 0000
serial frame 00 03 01 02 01 01 02 02 01 01 01 01 01 03 dc 47 00
```

Answer: `total(u16) count(u8)`, followed by the entries without lengths in front: `fn(u16) instance(u16) revision(u8)
name_len(u8) name` (core §2.3). The core of fn 0 has no name and is not in list, so the list of the smallest probe without interfaces is empty.

```text
message      02 0200 01 00 | 0000 | 00
               completed success | total 0 | count 0
serial frame 00 03 02 02 02 01 01 01 01 03 2a 74 00
```

### 3.3 describe (core §7.3, §7.5)

Vector: "describe fn 0 from the first" of `discovery.json`. Request: `fn(u16) first(u16)` = from the first TLV of fn 0. No TLVs are attached to a describe
request.

```text
message      01 0300 0000 03 00000000 | 0000 | 0000
serial frame 00 03 01 03 01 01 02 03 01 01 01 01 01 01 01 03 ea 30 00
```

Answer: `more(u8)`, followed by the declaration TLVs. The 4 every probe gives on fn 0: ops (the ops this fn has, as base 0x00 and a bitmap,
core §7.4; here the 8 that core §1.2 requires of fn 0: confirm, list, describe, clock, open, end, keepalive, lock_state), unit_id, transport (one per transport), max_op_ms (core §1.2).

```text
message      02 03 00 01 00 00 07 04 00 00 1e 00 0f 42 08 00 61 31 62 32 63 33 64 34 49 03 00 00 01 ff 4d 04 00 e8 03 00 00
               completed success | more 0 | ops 01-04 10-13 | unit_id "a1b2c3d4" | transport: index 0, kind 1, interface 0xFF | max_op_ms 1000
serial frame 00 03 02 03 02 01 01 03 07 04 01 02 1e 04 0f 42 08 0b 61 31 62 32 63 33 64 34 49 03 01 05 01 ff 4d 04 03 e8 03 01 03 28 e1 00
```

A describe whose `first` is the number of TLVs (here 4) or more is answered with more 0 and no TLVs (core §7.3; "describe fn 0 from beyond the last: more 0 and no TLVs" of
`discovery.json`):

```text
request      01 0400 0000 03 00000000 | 0000 | 0400
answer       02 0400 01 00 | 00
```

### 3.4 Refuse everything else

The smallest probe refuses other requests in the header order of core §4.3: a fn it does not have is unknown_function, an op not in fn 0 is
unknown_operation. Here the refusal answers have no payload ("refusals" of `discovery.json`).

```text
request fn 7 op 1      01 0500 0700 01 00000000     answer 02 0500 00 01    rejected unknown_function
request fn 0 op 0x50   01 0600 0000 50 00000000     answer 02 0600 00 02    rejected unknown_operation
```

The exact bytes of other refusals are in `tests/vectors/refusals.json`.

## 4. The first probe

What the probe does, in order (the references hold the rules):

1. **Receive a frame.** Accumulate the bytes from a 0x00 to the next 0x00, decode COBS and check the CRC-16. Candidates that do not decode and candidates whose CRC does not match are
   broken candidates and are discarded (transports §4). If there is a pause of `probe_frame_gap_ms` (200 ms) in the middle of a frame, read anew (transports §2).
   Even before confirm, accept messages of at least `min_max_frame` (64) bytes (transports §3).
2. **Read the header.** role 0x01 and 10 bytes or more (other messages are discarded, core §2.4). These are requests that need no lock, so session_id is 0. In the order of core §4.3, check the fn (unknown_function), the op
   (unknown_operation) and the length of the fixed part (malformed).
3. **confirm** (payload `OEP?` min_rev max_rev): `min_rev > max_rev` is malformed. If 1 is in [min_rev, max_rev], answer as in §3.1;
   otherwise refuse as in §3.1. Attach the transport TLV to every confirm answer.
4. **list**: put the interfaces from `first` into entries, as many as fit in one frame (fn 0 is not included). total is the total number of interfaces (core §7.2).
5. **describe**: for fn 0, return the TLVs from `first` (at least ops, unit_id, transport, max_op_ms; §3.3). If they do not all fit,
   more = 1. If `first` is the count or more, more 0 and no TLVs. The values do not change while the boot_id stays the same (core §7.3).
   In ops, set only the ops it answers (core §1.2). The probe at this stage has the 3 ops confirm, list, describe (`01 07`: base 0x01, bitmap 0x07),
   and sets a bit each time an op is added in §6. The bytes of §3.3 are those of a probe that has finished 1 and 2 of §6 and has all mandatory ops of fn 0.
6. **Answer**: with the same corr, on the transport the request came on, in the order they came, one answer per request (core §4.2, §4.4). On serial ports, `0x00 COBS 0x00`.
7. **boot_id**: chosen from a random number at boot (core §6.5). **unit_id**: lowercase, unchanging, unique (probe guide §10).

How to implement it with a concrete library is kept in the repository of that probe implementation. Whether it meets the rules and bytes of this section is checked with [conformance](conformance.md).

## 5. The first host

1. **Open the port**: exclusively (TIOCEXCL on Linux), 115200 8N1 for a UART bridge, with DTR and RTS asserted (transports §3, §4, host guide §1).
2. **Send confirm**: enclosed in 0x00 before and after, sent without pausing midway (transports §1, §2). This is the only thing sent to a port not yet identified (the probing rule,
   transports §3). It fits in 64 bytes.
3. **Wait**: at least `core_quick_op_max_ms` + `host_wait_add_ms` (2000 ms in total) + the transfer time (core §4.4). On a serial port that may be a UART bridge, the transfer time is
   (L + max_frame × (1 + `notify_pending_max_frames`)) × 10 / baud seconds. L is the length of the request frame on the line (here 21 bytes). Before the confirm
   answer the host does not know max_frame, so it counts with `min_max_frame` (64): (21 + 64 × 3) × 10 / 115200 ≈ 18 ms. Waiting
   longer is always fine.
4. **Receive**: decode every candidate between 0x00s. Also decode the bytes from opening the port to the first 0x00. Candidates that do not decode, whose CRC does not match, whose role is unknown,
   or whose corr is not being waited for are discarded as noise (transports §1, core §10.1).
5. **Check the answer**: completed, the same corr, a payload beginning with `OEP!` (transports §3). If none comes, resend once with the same corr
   (host guide §8); if still none comes, close the port and send nothing else (transports §3, core §5.1). Keep max_frame, window, max_inflight, boot_id and
   the transport index. From then on, do not send messages longer than max_frame (transports §3).
6. **list**: from `first` 0, read up to `total`, adding the number of entries received to `first`. The name → fn mapping may be remembered while the boot_id stays the same
   (core §7.2).
7. **describe fn 0**: from `first` 0. While more = 1, add the number of TLVs received to `first` and ask again. Skip unknown tags
   (core §2.3). Read unit_id (compared ignoring ASCII case; do not group by an `x-` unit_id), the transports and max_op_ms. Cache by
   boot_id (core §7.3, §7.5).
8. **Next**: to change anything, open a session (core §6), and use interfaces through their fn. When done, send `end`.

The host is run against a virtual bench or hardware provided by another implementation, to check that independent implementations give the same results. How to start them concretely is kept in the repository of that implementation.

## 6. What to add next

A probe that answers only confirm, list and describe is not yet an OEP probe. In the order many implementations add things:

**probe** ([conformance](conformance.md) §1):

1. clock (op 0x04): returns boot_id and the uptime_ns of the clock read just before building the answer. It needs no lock and comes with session_id 0 (core §7.6).
   The first step of "clock without a session and while a session holds the lock" of `sessions.json` (uptime_ns is 2.0 s in the example):

   ```text
   request      01 0100 0000 04 00000000
   answer       02 0100 01 00 | 78563412 | 0094357700000000
                  completed success | boot_id | uptime_ns = 2000000000
   ```

2. Sessions: open, end, keepalive, lock_state, the lease, and the decision table of core §6.2. Checking the session_id (session_required, no_session,
   locked). On any of end, lease expiry and force, release what the session made (core §9).
3. The resend ordering state of core §5.1 (corr is updated even on a refusal of a new request, and it is initialized only when the open of a new session with a different ID succeeds). Byte records may be 0 entries, and old requests not kept are refused with result_lost.
4. The refusals of core §4.3, and the TLV rules of core §2.3 (critical, unknown TLVs, TLVs with a different length).
5. If there is an interface that sends notifications, subscribe / unsubscribe of that fn and how notifications are sent (core §10).
6. The interfaces you want ([conformance](conformance.md) §3). If there is an interface with plan roles, also `oep.probe.plan` ([plan](../interfaces/oep-if-plan.md)).
7. Optional: `oep.probe.link` (link tests and port_speed of the UART bridge; [link](../interfaces/oep-if-link.md)), `oep.probe.restart` ([restart](../interfaces/oep-if-restart.md)), `oep.probe.memo` ([memo area](../interfaces/oep-if-memo.md)), probe settings (core §13, [settings file](oep-settings-file.md)), other transports.

**host** ([conformance](conformance.md) §2):

1. How corr is assigned, and resending (core §4.1, §5.1, host guide §8). Resynchronizing on length-prefixed ports (transports §5).
2. Sessions: a random session_id, the lease of the open answer, keepalive, what to do for each refusal (host guide §9).
3. Revisions and unknown values (core §2.4, §2.8, host guide §10). Notifications if it subscribes (host guide §12).
4. Discovery of USB probes and several transports (transports §3, host guide §4, §5).

Then, following [conformance](conformance.md) §4, check with the test vectors, an independent virtual bench and hardware.

## 7. What to read next

- [Host development guide](host-development-guide.md), [probe development guide](probe-development-guide.md): practice and traps.
- [Glossary](glossary.md): every term the specification defines.
- [Safety and security](security.md): what to watch for before shipping.
- [Versions and stability](versioning.md): what does not change after the freeze.
