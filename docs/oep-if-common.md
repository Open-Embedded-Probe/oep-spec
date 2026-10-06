# OEP standard interfaces: common parts v1

[日本語](oep-if-common.ja.md)

Status: **normative** (v1, before the freeze: until the v1 freeze a rule or a number may still change). Before the freeze, revision 1 alone does not identify a form: an implementation names the specification tag it implements ([versioning](versioning.md) §6). The core is [OEP core](oep-core.md). This document defines the parts that several standard interfaces use in the same form.
The parts are not the core. They take effect for a standard interface only when that interface says it uses the part
(independent interfaces are free to use the same parts). The only definition of the numbers is `registry/oep-v1.toml`.

## 1. Positioned streams

Used by: `oep.target.console`, `oep.fixture.uart`. Capture (`oep.fixture.logic` / `oep.fixture.analog`) has positions, but in a different form with segments and generations,
and does not use this part ([capture](oep-if-capture.md) §2). An interface that uses this part offers read, marks, clear, mark and write as required ops (core §1.2).

### 1.1 Position

- The probe gives each byte of a stream a serial number (the **position**, u64, does not wrap). The position starts at 0 at the probe's boot and **does not go back while the probe stays
  booted**: even if a stream closes and is created again at the same place (a re-open of a console, a redo of the plan of a fixture UART), the position and the serial of the marks
  continue from where they were (so that a read by an old host does not silently return new data).
- **Reading does not consume the buffer.** Bytes disappear only in the following cases:
  1. Overflow (the oldest are pushed out. The target or the peer is not kept waiting).
  2. An explicit erase by the host (clear).
  3. A reboot of the probe (the position also restarts from 0. The boot_id changes).
- A reset of the target does not discard (the output right before the reset is often what one most wants to see). A mark is attached instead (§1.3).
- Even if an answer is lost, reading again at the same position returns the same data.

### 1.2 read

```text
request: [stream(u16)], from(u8), arg(u64), max(u16), [TLV]
answer:  start(u64), flags(u8: bit0 more, bit1 gap), len(u16), data, [TLV]
```

| from | Meaning |
|---:|---|
| 0 | From position arg |
| 1 | From the oldest byte still remaining |
| 2 | From now (a position where nothing exists yet) |
| 3 | From the position of the last mark of kind arg (arg 0 means any kind). If no mark of that kind remains, from now (same as from 2. Never existed, or pushed out of the ring of marks) |

- `start` is the position of the first byte of data. If the requested position has already been pushed out, start moves forward and gap is set (the difference is the amount lost).
- If the requested position (from 0) is beyond the write position, the answer is start = the write position, len 0, flags 0.
- len is at most max and at most what fits in the answer within max_frame. `more` is set when bytes remain: there are still readable bytes after this answer,
  and the host may read the next immediately.
- from 3 with arg > 0xFF is rejected malformed (a mark kind is u8).
- A from of 4 or more is rejected unsupported (payload `0x00`. A later revision may define it, core §2.5).
- `max` = 0 is an empty success (len 0).
- **read can be used without the lock** (reading changes no state, and the probe keeps no per-reader state).

### 1.3 Marks

```text
mark : serial(u32), position(u64), kind(u8), time_ns(u64), detail(u8)          22 byte
```

| kind | Name | When attached | detail |
|---:|---|---|---|
| 0x01 | reset | The target was reset at the probe's instruction | Method (`mark_detail_reset`: 1 ndmreset (the reset op), 3 the reset TLV of attach. 2 is reserved) |
| 0x02 | restart | A restart of the target was detected | Source of detection (`mark_detail_restart`: 1 havereset, 2 resynchronisation of the console) |
| 0x03 | attach | Attached (including a re-open at the same place) | — |
| 0x04 | detach | Detached | — |
| 0x05 | lost | Pushed out by overflow, or a receive error | Reason (`mark_detail_lost`: 1 overflow, 2 receive error (framing), 3 parity, 4 the target's TO) |
| 0x06 | clear | The host erased | — |
| 0x07 | host | A marker placed by the host | The host's value |
| 0x08 | link-lost | The wire was lost (decided inside a console read) | — |
| 0x09 | closed | The stream closed | Reason (`mark_detail_closed`: 1 every user left, 2 the session ended (end, lease expiry, force), 3 replacement or deletion of the slot, 4 the connection closed) |

- The kind space: 0x01 to 0x3F standard, 0x40 to 0x7F interface-specific. The detail values are in the registry (`common.enum.mark_detail_*`). 0x40 onwards is
  interface-specific.
- `serial` is the serial number of marks per stream (u32, wraps. core §2.6). Even if several marks are attached at the same position, they can be read by serial
  without loss or duplication.
- `time_ns` is the probe's clock (ns since boot, u64, core §2.6a). There is no per-byte time.
- Marks are accumulated in a small ring separate from the body. On overflow the oldest are discarded. The host sees the discarded marks as a jump in serial:
  the jump is the number of marks pushed out.

```text
marks  request: [stream(u16)], from_serial(u32)
       answer:  more(u8), count(u8), count × mark, [TLV]  (core §2.3)
```

marks can be used without the lock.

### 1.4 State-changing operations

| Operation | Request | Answer | Meaning |
|---|---|---|---|
| clear | [stream(u16)] | — | Discard the accumulated bytes and attach a mark clear |
| mark | [stream(u16)], value(u8) | — | Attach a mark host (detail = value) |
| write | [stream(u16)], count(u16), data | accepted(u16) | Input to the peer. `accepted` is the amount placed into the send slot of the mechanism (UART transmit, the console's mechanism), and does not mean it arrived. If the slot is not free, accepted 0 = completed failed; 0 < accepted < count = completed partial. count = 0 is malformed |

All of them require the lock.

### 1.5 Notification data

An interface that emits a stream uses the data form of core §11.2 (`position, len, data, [TLV]`). `position` is the position of the start of this frame.
If it does not match the end of the previous frame, the bytes in between were pushed out inside the probe. Whether the sent data can be re-read with read is decided by the
interface.

## 2. Debug connections

Used by: `oep.wire.rvswd`, `oep.wire.swio`, `oep.wire.swd` (create them), `oep.target.riscv-dm`, `oep.target.arm-adi`,
`oep.target.console` (use them), the slots of `oep.probe.config` (use them).

- A **connection** is a connection to a certain target, created by the attach of a wire. It is designated by a number (u16), and the requests of target operations place
  the connection first.
- The number (u16) is assigned by the rules of core §9 (one space per probe, advancing from 1 and wrapping, a failed attach does not consume one. A closed number is
  rejected no_connection, the number of a resource of a different kind is rejected unavailable cause 6).
- A connection is open while it has at least one **user**. Its users are:
  - the session of a host that attached (one per session)
  - a slot (`oep.probe.config` §1.1. The probe's automatic attach, and a console opened by a bind)
- The session's share follows the lifetime of core §9: it leaves when the session's lock ends (end, lease expiry, taken by force). A later session's attach
  joins the connection only while another user (a slot) keeps it open.
- It closes only when no user remains, on a forced detach, or when the wire is truly lost (as decided by the interface's document).
- Resources riding on a connection (console streams, etc.) close when the connection closes (what is kept is decided by that
  interface).

## 3. Status of wire and target operations

Used by: `oep.wire.*`, `oep.target.*`.

| Value | Name | Meaning | Guide for the host's decision |
|---:|---|---|---|
| 0 | ok | Ran to the end | — |
| 1 | wait | The target kept answering "wait" (DMI busy, SWD WAIT). The retries inside the probe were used up | Continue from where it stopped after a pause |
| 2 | line | No answer on the wire, or a parity error | Lower the speed and attach again |
| 3 | fault | The target refused (a failed DMI op, SWD FAULT, the cmderr of an abstract command) | Read the cause and clear it |
| 4 | timeout | A waiting procedure or the limit of run was reached | Review the limit |
| 5 | state | Not in the prerequisite state (an operation that assumes a halted hart on a hart that is not halted, etc.) | Put the state in order first |

- 0x06 to 0x3F are reserved as common values, 0x40 to 0x7F are decided by the interface. Unknown values are treated as failure.
- **Failures are returned with completed** (core §4.2). failed if nothing progressed, partial if it progressed partway. The form of the payload is the same as on success, and
  is understood from `done` (the number of steps or words progressed) and `status`. Format errors are rejected malformed.
- Failure of an op whose success form has no done / status (scan, attach, detach) is completed failed with the payload `status(u8), [TLV]` (core §2.3:
  the fixed part is defined per (op, resolution, outcome)).
- The failure status of an op that uses the reset wire: does not halt / does not run = timeout, the DM does not answer = line, cmderr = fault.
