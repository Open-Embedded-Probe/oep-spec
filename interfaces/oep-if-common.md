# OEP interface: common parts v1

[日本語](oep-if-common.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **normative** (v1). For the freeze state and the language and compatibility policy, see [Versions and stability](../docs/versioning.md). The core is [OEP core](../docs/oep-core.md). This document defines parts that several interfaces whose names start with `oep.` use in the same form.
The parts are not the core. A part applies to an interface only when the document of that interface says it uses the part
(any interface can use the same parts by saying so in its document). The only definition of the numbers is `registry/oep-v1.toml`.

The common contract that all standard and third-party interfaces keep is core §12. On top of it, this document defines the meaning of parts that are chosen and used.
The OEP GPIO uses pin assignment by plan, and UART uses plan and the positioned stream, but these are not required uniformly of third-party extensions.

## 1. Positioned stream

Used by: `oep.target.console`, `oep.fixture.uart`. Capture (`oep.fixture.logic` / `oep.fixture.analog`) has positions, but in a different form with segments and generations,
and does not use this part ([Capture](oep-if-capture.md) §2). The minimal adoption of this part is read.
Whether marks, clear, mark and write are present, and whether they are required or optional, is defined by the op table of the adopting interface.
Declared operations use the form and meaning of this section. Adopting the common part alone creates no duty to implement all of writing, clearing and recording marks.
A probe that provides mark also provides marks. A probe that does not provide marks refuses from 3 of read with rejected unsupported (fixed-part mark 0).
The adopting interface makes required only the operations its own operation table requires.
`[stream(u32)]` below is always present in definitions that point to a stream by resource number, and absent in definitions where the fn itself points to one stream.
It is not a field that an individual request chooses to omit; the fixed part is determined by the name and revision of the interface.

### 1.1 Position

- Each byte of a stream gets a position (u64, does not wrap). A stream that has a number as a resource starts at 0 when created.
  Recreation uses a new resource number. A fixture UART pointed to directly by fn does not move positions or mark serials back during the same boot_id.
- **Reading does not consume the buffer.** Bytes disappear only when:
  1. overflow (pushed out from the oldest; the target or the peer is not made to wait).
  2. explicit clearing by the host (clear).
  3. the stream is released, or the probe restarts.
- A target reset does not discard them (the output just before the reset is often what one most wants to see). Whether there is a reset mark and what triggers it is defined by the adopting interface (§1.3).

### 1.2 read

```text
request: [stream(u32)], from(u8), arg(u64), max(u16), [TLV]
answer: start(u64), flags(u8: bit0 more, bit1 gap), len(u16), data, [TLV]
```

| from | Meaning |
|---:|---|
| 0 | from position arg |
| 1 | from the oldest byte remaining |
| 2 | from now (a position with nothing yet) |
| 3 | from the position of the last mark of kind arg (arg 0 is any kind). If no mark of that kind remains, from now (the same as from 2; there never was one, or it was pushed out of the mark ring) |

- `start` is the position of the first byte of data. If the requested position was already pushed out, start moves ahead and gap is set (the difference is the amount lost).
- If the requested position (from 0) is ahead of the write position, the answer is start = the write position, len 0, flags 0.
- len is at most max, and at most what fits in the answer within max_frame. If bytes remain, `more` is set: more bytes can be read after this answer,
  and the host MAY read the next one immediately.
- **read can be used without the lock** (it does not consume retained data, and the probe keeps no per-reader state. The progress of communication and asynchronous reception is core §6.3).

### 1.3 Marks

This section applies to interfaces that provide marks. A minimal adoption without marks is not required to manage a mark ring or serials.

```text
mark : serial(u32), position(u64), kind(u8), time_ns(u64), detail(u8)          22 byte
```

| kind | Name | Trigger | detail |
|---:|---|---|---|
| 0x01 | lost | pushed out by overflow, or a receive error | reason (`mark_detail_lost`: 1 overflow, 2 framing, 3 parity) |
| 0x02 | clear | the host cleared | 0 |
| 0x03 | host | a mark the host put | the host's value |

- The position of a mark is the write position at the time the probe put the mark. All bytes from position on were received after the occurrence of that mark.
- kind space: 0x01 to 0x3F standard, 0x40 to 0x7F interface-specific. The detail of the common lost is `common.enum.mark_detail_lost` in the registry.
  Interface-specific details are defined by their definitions and the matching `interface.enum.mark_detail_*` in the registry.
  detail values 0x40 and above of common kinds are also interface-specific. Function-specific triggers such as reset and restart, and their details, are defined by the adopting interface.
- `serial` is the running number of the marks per stream (u32, wraps; core §2.6). Even if several marks are at the same position, they can be read by serial
  with no loss and no duplicates.
- `time_ns` is the probe clock (ns since boot, u64, core §2.7). There is no time per byte.
- Marks are kept in a small ring separate from the data. On overflow the oldest are discarded. The host learns of discarded marks from a jump in serial:
  the size of the jump is the number of marks pushed out.

```text
marks  request: [stream(u32)], from_serial(u32)
       answer: more(u8), count(u8), count × mark, [TLV] (core §2.3)
```

marks can be used without the lock.

**Paging by running number** (marks; segments of capture also use the same rule). Let `next` be the serial to be put next. serial wraps
and is compared by core §2.6. "Remaining" means being between the oldest remaining serial and next − 1.

1. The elements of the answer are in serial order and **include** from_serial. If from_serial remains, the answer returns what fits in one frame from there.
2. If from_serial = next, 0 elements, more 0 (nothing yet). The same when nothing remains at all.
3. Otherwise (a number pushed out, a number not put yet, a number of a previous boot), the answer returns from the oldest remaining.
   When the host is reading on through the same stream (the same generation for capture), it can treat a forward jump in serial as a loss count within the range where the comparison of core §2.6 holds.
   The difference from an arbitrary starting number or a number of another boot is not taken as a loss count as it is.
4. If more = 1, more remains after the returned elements. The host uses the last serial received + 1 (modulo 2^32) as the next from_serial.

### 1.4 Operations that change state

| Operation | Request | Answer | Meaning |
|---|---|---|---|
| clear | [stream(u32)] | — | discards the stored bytes. If marks is provided, puts the mark clear |
| mark | [stream(u32)], value(u8) | — | puts the mark host (detail = value) |
| write | [stream(u32)], count(u16), data | accepted(u16) | input to the peer. `accepted` is the number of bytes from the start of data that the probe put in its send queue (the smaller of count and the free space of the queue); it does not mean they arrived. accepted = count is completed success, 0 < accepted < count is completed partial, accepted 0 with count > 0 is completed failed. The size of the queue and the speed at which it is passed from the queue to the peer are decided by the interface (for the console, [Console](oep-if-console.md) §2; for the fixture UART, transmission of UART) |

All of them need the lock.

### 1.5 Notification data

An interface that sends out a stream uses the data form of core §10.2 (`position, len, data, [TLV]`). `position` is the position of the first byte of this frame.
If it is ahead of the end of the previous frame of the same stream, the bytes in between were not received through notifications.
Loss of notifications (core §10) and overflow of the retaining buffer are distinguished; a jump in position alone is not taken to mean that retained data was lost as well.
Whether they can be recovered with read is checked with the retention rules of the interface and start/gap of read.

## 2. Debug connection

Used by: `oep.wire.*` (creates), the matching `oep.target.*` and `oep.target.console` (use).

- A connection is a session-owned connection that attach creates for an explicit pin combination and target selection. Target operations put connection(u32) first.
- Numbers are assigned by the rules of core §9. They are not reused during the same boot_id.
- It closes on detach, the end of the session, wire loss, or a failure of the cleanup defined by a provided target op. Streams that depend on the connection are released first.
- The wire fn that creates a connection and the target fn that uses it MAY be different. The definition of the wire defines the matching targets, and the connection number of the target request selects explicitly.
  A connection of a wire that does not match is unavailable (cause 6), and a nonexistent/closed number is no_resource. The last attached connection is not used implicitly.
- Each name of `oep.target.*` and `oep.target.console` that uses connections exists once per probe (list does not show another instance with the same name).
  That one accepts the connections of all wires that the wire definitions matched to it. The host looks up the fn by name and does not choose per wire.

## 3. Status of wire and target operations

Used by: `oep.wire.*`, `oep.target.*`.

| Value | Name | Meaning |
|---:|---|---|
| 0 | ok | went to the end |
| 1 | wait | the target kept returning "wait" (DMI busy, SWD WAIT). The probe used up its internal retries |
| 2 | line | no response from the wire, parity error |
| 3 | fault | the target refused (failure of a DMI op, SWD FAULT, cmderr of an abstract command) |
| 4 | timeout | reached the limit of a waiting procedure or of run |
| 5 | state | not in the precondition state (an operation that assumes a halted hart on a hart that is not halted, and so on) |

- 0x06 to 0x3F are reserved as common values, and 0x40 to 0x7F are decided by the interface. Unknown values are treated as failure.
- **Failures are returned as completed** (core §4.2). If nothing progressed, failed; if it progressed part way, partial. The payload has the same form as on success,
  and `done` (the number of steps or words that progressed) and `status` tell what happened. A format error is rejected malformed.
- failed or done 0 is not a guarantee that no write reached the target. Each op defines where done is measured.
  The external effect of a write whose answer was lost and the like can be unknown, so the same write is not repeated by automatic re-execution with a new corr or by unconditional retries of the wire.
  Only when the interface defines a group of steps that leaves the same state however many times it runs MAY it be redone following that definition (riscv-dm is in [Wires and debug](oep-if-debug.md) §4.1).
- A failure of an op whose success form has no done / status (scan, attach, detach) is completed failed with payload `status(u8), [TLV]` (core §2.3:
  the fixed part is defined per (op, resolution, outcome)).
