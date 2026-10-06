# OEP standard interfaces: console v1

[日本語](oep-if-console.ja.md)

Status: **normative** (v1, before the freeze: until the v1 freeze a rule or a number may still change). Before the freeze, revision 1 alone does not identify a form: an implementation names the specification tag it implements ([versioning](versioning.md) §6). The core is [OEP core](oep-core.md), the common parts are [common parts](oep-if-common.md) (§1 positioned
streams, §2 debug connections). The only definition of the numbers is `registry/oep-v1.toml`.

| Name | revision | Role |
|---|---:|---|
| `oep.target.console` | 1 | The target's console (a stream over a debug connection) |

UART pass-through is `oep.fixture.uart` ([fixture](oep-if-fixture.md)), which uses the same stream form.

## 1. Operations

A stream is opened over a debug connection by specifying a mechanism. There is one fn per interface, and streams are designated by number.

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x01 | open | connection(u16), mechanism(u8), [TLV] | stream(u16), flags(u8: bit0 existing stream), [TLV] | Required |
| 0x02 | read | stream(u16), from(u8), arg(u64), max(u16), [TLV] | start(u64), flags(u8), len(u16), data, [TLV] | Not required |
| 0x03 | marks | stream(u16), from_serial(u32) | more(u8), count(u8), count × mark, [TLV] | Not required |
| 0x04 | clear | stream(u16) | — | Required |
| 0x05 | mark | stream(u16), value(u8) | — | Required |
| 0x06 | write | stream(u16), count(u16), data | accepted(u16), [TLV] | Required |
| 0x07 | close | stream(u16) | — | Required |
| 0x08 | streams | first(u8) | more(u8), count(u8), count × (stream(u16), connection(u16), mechanism(u8), users(u8), state(u8)), [TLV] | Not required |

Every op of this table is required (core §1.2). The mechanisms are declared by mechanisms of describe.

- read, marks, clear, mark, write take the form of [common parts](oep-if-common.md) §1 (with stream first).
- mechanism: 0 SDI, 1 DMDATA, 2 dmseq (the framing is [target-console-dmseq](target-console-dmseq.md)). **The mechanism number determines the mechanism
  exactly** (it has no version). When a mechanism changes, a new number is used (3 onwards, added to the registry), and the meaning of the old number does not change. An unknown mechanism, and
  a mechanism not in the mechanisms of describe, is rejected unsupported (payload `0x00`, core §4.3).
- describe: tag 0x40 mechanisms (a sequence of u8. The mechanisms that probe can open). Always emitted.
- An unknown stream is rejected no_connection (core §4.3). The number of a resource of a different kind (a connection number as a stream) is rejected unavailable
  cause 6. An open on an arm-adi (swd) connection is also rejected unavailable cause 6 ([wire and debug](oep-if-debug.md) §5).
- Stream numbers (u16) are assigned by the rules of core §9 (one space per probe, advancing from 1 and wrapping. A re-open at the same place does not consume a number, §2).
- **streams** is the list of live streams and of streams that are closed but still readable (`stream_state`: 0 open, 1 closed). It returns, in order of creation, from the first-th
  as many as fit in one frame, and more = 1 means there is more (the same form as connections). users is bit0 a host's
  session, bit1 a slot (bind). The op by which a lock-free host (monitoring) obtains numbers.
- A close on a closed stream does nothing and succeeds.
- revision 1 sends no notifications (subscribe is rejected unsupported). When added later, the payload of data takes the form of core §11.2.

## 2. Stream rules

- **If a stream with the same (connection, mechanism) exists, open returns it** (flags bit0. The position and the marks stay as they are).
  So that a one-command-one-process host can read from where it left off. When the same mechanism is opened at the place of a closed stream (the same pin combination of the same wire),
  it is **reopened with the same number** (the position and the marks continue, mark attach, flags bit0). An open with a different mechanism erases the old one.
- **Each mechanism defines**: the kinds of connection it opens on, the target resources it uses, how many live streams one connection can have together with
  other mechanisms, when the probe pauses reading, and how often it checks the target's state (mechanisms 0 to 2: §3).
- **The lifetime of a stream is counted the same way as a connection** ([common parts](oep-if-common.md) §2): its users are the session that opened it and
  the slot that opened it by bind. close, and the end of the session's lock (end, lease expiry, force), remove only one's own share, and it closes when every
  user has left (mark closed, detail 1 after a close, 2 when the session ended). When a session ends, the probe removes its shares of streams before its shares
  of connections, so a stream whose last user was that session closes with detail 2 even when its connection closes too.
  When a user left through the replacement or deletion of a slot item, detail 3; when the connection closed, 4.
- **Console streams are the probe's, per place and mechanism, not the session's** (core §9). The end of a session removes its share, but a closed stream stays
  readable until the same mechanism is next opened at the same place, and that open returns the old number with its position and marks (below). So a host
  that runs one command per process keeps the first lines: one command opens the console, resets the target and ends; the stream closes but keeps what it
  read; the next command's open at the same place and mechanism returns it, and reads from the reset mark.
- While a stream is open, the probe drains and accumulates the target's output regardless of sessions (with dmseq, unless it keeps reading, the target
  blocks on transmission).
- When the connection on which a stream was opened is lost, it is closed with a mark link-lost (when wire loss was decided inside a console read) or closed (4).
  On seeing a self-reset of the target (havereset), a mark restart (1) is attached, and dmseq returns to unsynchronised. **A closed stream remains readable until the same mechanism is next opened at the same connection place (the same pin combination of the same
  wire)** (read / marks. write / mark / clear are rejected unavailable). To recover the output right before the wire
  went down. An open at another place does not erase it.
- The connection a stream uses is counted as being used by the session that opened that stream (or the slot of `oep.probe.config`).
- write accepts only as much as the mechanism can carry in one go (the send slot; 2 bytes for dmseq, 3 bytes for DMDATA). **accepted is the amount placed into the send slot, and
  does not mean the target received it.** If the slot is not free, accepted 0 (completed failed). The host resends the rest, watching the progress of reads
  ([common parts](oep-if-common.md) §1.4).

## 3. Mechanisms

Mechanisms 0, 1 and 2 use the debug module's DATA0 (DMI 0x04) and DATA1 (0x05) as the mailbox. The hart is not halted. The probe reads DATA0 and receives by the rules
of the mechanism.

- **Among mechanisms 0 to 2, one connection has one live stream.** An open with another of them is rejected unavailable (cause 6). They do not open on an arm-adi
  connection (rejected unavailable cause 6).
- The probe stops reading the console **only while executing a riscv-dm request on that connection and while the hart is halted**
  (during a long request on another connection, reading on this connection continues. core §7.5 max_op_ms). To avoid contending with abstract commands for DATA0, the host puts a whole abstract-command sequence into one dmi request
  ([wire and debug](oep-if-debug.md) §4.1). "The hart is halted" is seen by the probe in DMSTATUS: whether the host halts or runs the hart inside a dmi request
  (even if the debugger writes the haltreq / resumereq of dmcontrol itself), the probe keeps reading (resumes) while the hart is running. The interval at which the probe
  checks DMSTATUS is 20 ms or less (registry `console_dmstatus_poll_ms`; after the host halts it raw, the probe may read DATA0 only within that interval).
  The host need not use the resume op of riscv-dm for the console's sake.

| mechanism | Name | Direction | Definition |
|---:|---|---|---|
| 0 | SDI | target → host | 3.1 below |
| 1 | DMDATA | both directions | 3.2 below |
| 2 | dmseq | both directions | [target-console-dmseq](target-console-dmseq.md) (with sequence numbers and CRC) |

### 3.1 SDI

Mechanism 0 is this mailbox layout only; it does not depend on the wire of the connection. It carries bytes from the target to the host.

- **Bytes in the mailbox**: byte 0 is bits 8 to 15 of DATA0, byte 1 bits 16 to 23, byte 2 bits 24 to 31; byte 3 is bits 0 to 7 of DATA1, byte 4
  bits 8 to 15, byte 5 bits 16 to 23, byte 6 bits 24 to 31. The low byte of DATA0 (bits 0 to 7) is the length L.
- **The target** sends n bytes (n = 1 to 7) at a time: it waits until DATA0 reads 0, then writes DATA1 (bytes 3 to 6), then DATA0 = n | bytes 0 to 2 << 8
  (DATA0 last). Byte positions at or beyond n carry any value. How long the target waits, and what it does with bytes it gave up on, is the target's
  choice.
- **The probe** reads DATA0. When L is 1 to 7, it also reads DATA1, receives bytes 0 to L − 1 in that order, and then writes 0 to DATA0 (the mark of receipt).
  When L is 0 there is nothing. When L is 8 or more the word is not a slot: the probe neither receives it nor writes DATA0 (it is not discarded).
- There is no host → target direction (write accepts nothing: accepted 0, completed failed).

### 3.2 DMDATA

Mechanism 1 is this mailbox layout only; it does not depend on the wire of the connection. It carries bytes in both directions, and the two sides take turns
on DATA0.

- **The status byte** is the low byte of DATA0 (bits 0 to 7). Bit 7 is T: 1 = a **target slot** (the target wrote it), 0 = written by the probe, or 0 at
  start. Bits 0 to 5 are L = the number of bytes + 4. Bit 6 is written 0 and ignored by the reader.
- **Bytes in the mailbox**: the same positions as SDI (§3.1): bytes 0 to 2 in bits 8 to 31 of DATA0, bytes 3 to 6 in DATA1.
- **The target** writes DATA0 only when bit 7 of DATA0 is 0, with one exception: it may replace its own empty slot (L = 4) with a target slot that carries
  bytes.
  - To send n bytes (n = 1 to 7) it waits until bit 7 of DATA0 is 0, takes the answer in that word (below), writes DATA1 (bytes 3 to 6) when n is 4 or
    more, then writes DATA0 = 0x80 | (n + 4) | bytes 0 to 2 << 8 (DATA0 last). Byte positions at or beyond n carry any value.
  - To ask for input without sending, it waits until bit 7 of DATA0 is 0, takes the answer in that word, then writes DATA0 = 0x84 (an **empty slot**,
    L = 4: "the mailbox is the probe's turn").
  - **Taking the answer**: a word with bit 7 = 0 whose L is 5 to 7 carries L − 4 bytes for the target, bytes 0 to L − 5. A word of 0, and any other word with
    bit 7 = 0, carries none.
  - How long the target waits, and what it does with bytes it gave up on, is the target's choice.
- **The probe** reads DATA0.
  - When bit 7 is 0 it does nothing: the word is its own answer that the target has not yet replaced, or 0. The probe never writes over a word with bit 7 = 0.
  - When bit 7 is 1 and L is 5 to 11, it receives n = L − 4 bytes: bytes 0 to 2 (as many as n) from that word, and, when n is 4 or more, bytes 3 to n − 1
    from DATA1, which it reads after DATA0. It then answers.
  - When bit 7 is 1 and L is 4, the slot is empty. The probe answers it only when its next read of DATA0 returns that empty slot again (the target may
    replace an empty slot with a slot that carries bytes, and answering at once would erase that slot).
  - When bit 7 is 1 and L is 0 to 3 or 12 to 63, the slot carries no bytes; the probe treats it as an empty slot.
  - **The answer**: exactly one write of DATA0 per target slot. When write has placed bytes in the send slot (n = 1 to 3), DATA0 = (n + 4) | bytes 0 to
    n − 1 << 8 (bit 7 = 0; byte positions at or beyond n are 0), and those bytes leave the send slot. Otherwise DATA0 = 0. The probe does not write DATA1.
- write places at most 3 bytes in the send slot (§2). When bytes placed earlier have not yet gone out in an answer, the slot is not free (accepted 0).

## 4. References

The OEP messages of this document are defined by the text alone. Driving the target uses:

| Specification | Subset used |
|---|---|
| RISC-V Debug Specification 0.13.2 and 1.0 (DMSTATUS.version 2 and 3) | The debug module's DATA0 (DMI 0x04), DATA1 (DMI 0x05), DMSTATUS (allhalted, allrunning, havereset) and its abstract commands, which also use DATA0 and DATA1 |
