# OEP interface: console v1

[日本語](oep-if-console.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **normative** (v1). For the freeze state and the language and compatibility policy, see [Versions and stability](../docs/versioning.md). The core is [OEP core](../docs/oep-core.md), and the common parts are in [Common parts](oep-if-common.md) (§1 positioned
stream, §2 debug connection). The only definition of the numbers is `registry/oep-v1.toml`.

| Name | revision | Role | Target family |
|---|---:|---|---|
| `oep.target.console` | 1 | the console of the target (a stream over a debug connection) | used for every family (per mechanism, targets that have that mechanism) |

UART pass-through is `oep.fixture.uart` ([fixture](oep-if-fixture.md)), and it uses the same stream form.

## 1. Operations

A stream is opened over a debug connection with a mechanism specified. There is one fn for the interface, and streams are pointed to by number.

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x10 | open | connection(u32), mechanism(u8), [TLV] | stream(u32), [TLV] | needed | required |
| 0x11 | read | stream(u32), from(u8), arg(u64), max(u16), [TLV] | start(u64), flags(u8), len(u16), data, [TLV] | not needed | required |
| 0x12 | marks | stream(u32), from_serial(u32) | more(u8), count(u8), count × mark, [TLV] | not needed | optional |
| 0x13 | clear | stream(u32) | — | needed | optional |
| 0x14 | mark | stream(u32), value(u8) | — | needed | optional; marks also provided |
| 0x15 | write | stream(u32), count(u16), data | accepted(u16), [TLV] | needed | optional |
| 0x16 | close | stream(u32) | — | needed | required |
| 0x17 | streams | first(u16) | more(u8), count(u8), count × (stream(u32), connection(u32), mechanism(u8)), [TLV] | not needed | required |

Mechanisms are declared by mechanism of describe, and operations by ops. The minimum is open/read/close/streams, without a ring of marks or a send queue.
Without marks, from 3 of read is unsupported. An fn that does not provide write supplies no input even with DMDATA/dmseq, and returns empty answers to the target.
An fn that provides write provides at least one of `dmdata` or `dmseq`. A write to an `sdi` stream is refused with unsupported (fixed-part mark 0).

- read, marks, clear, mark and write have the form of [Common parts](oep-if-common.md) §1 (stream first).
- **Mechanisms are a sequence of names** (core §7.7): describe has one tag 0x40 mechanism (text: the name of the mechanism) for each mechanism the probe can open.
  One or more, with no duplicate names. Always present. mechanism(u8) in requests and answers is the position (from 1) in that sequence.
- The names of the standard mechanisms are `sdi`, `dmdata` and `dmseq` (§3). **The name determines the mechanism exactly** (it has no version). Mechanisms of others have reverse-DNS names,
  and the owner of the name decides how they carry data and their rules. A mechanism at a position not in the sequence is rejected unsupported (payload `0x00`, core §4.3).
- An unknown stream is rejected no_resource (core §4.3). A number of another kind of resource (a connection number given as a stream) is rejected unavailable
  cause 6. An open on an arm-adi (swd) connection is also rejected unavailable cause 6 ([Wires and debug](oep-if-debug.md) §5).
- Stream numbers (u32) follow core §9 and are not reused during the same boot_id.
- streams returns only live streams, in order of creation. first is u16. A request to a closed stream is no_resource.

## 2. Stream rules

- open creates a new session-owned stream. With the standard mechanisms, one connection has one live stream, and a second open, including one with another mechanism, is unavailable (cause 6).
  The number, buffer, positions and marks of a closed stream are not used again.
- close, the release of the connection, and the end of the session release the stream with its buffer and send queue.
  The host reads the output it needs with read and saves it to a log before losing it.
- While a stream is live, the probe drains the target's output between its processing and stores it in the buffer. The implementation decides the polling frequency.
  During the stop conditions of §3 and long target operations it cannot poll, and output can be lost when the finite waiting time of a dmseq target is exceeded.
- The handling of dmseq synchronization on a self-reset of the target follows [Wires and debug](oep-if-debug.md) §4.6.
- Only an fn that provides marks records the following marks in the form of the common parts. Even without marks, synchronization and duplicate removal of dmseq are done.

  | kind | Name | detail |
  |---:|---|---|
  | 0x40 | reset | 1 ndmreset (the reset of the reset op; debug §4.3). Triggers in debug §4.3, §4.6 |
  | 0x41 | restart | 1 havereset, 2 resynchronization |
  | 0x01 | lost | in addition to the common details, 0x40 TO of the target |

  With dmseq they are put on the following triggers.
  - The first synchronization from the unsynchronized state puts no restart mark.
  - Resynchronization by a new, non-duplicate SYN frame while synchronized is restart (kind 0x41, detail 2).
  - A valid target frame with TO = 1 is lost (kind 0x01, detail 0x40). This applies even if the payload is a duplicate.
  - A CRC mismatch of a target frame is lost (kind 0x01, detail 2: framing). With N > 6 the position of the CRC is not computed.
  - Marks for repeated observation of the same frame MAY be merged. No number of marks per poll is required.
  - restart/resync or lost/TO MUST NOT be put from SYN/TO of an invalid frame.
    lost/framing for a CRC mismatch is put separately from this prohibition.
  Validity, duplicates and resynchronization of frames are judged by the [host rules of dmseq](target-console-dmseq.md#host-rules-on-reading-a-word-with-bit-7-set-to-1).


- **Send queue**: an fn that provides write has a send queue per `dmdata`/`dmseq` stream (the probe decides its finite size).
  write puts data from the start at the end of the queue, as much as fits in the free space of the queue. **accepted is the number of bytes put in the queue** (the smaller of count and the free space of the queue);
  it does not mean the target received them. accepted 0 with count > 0 (completed failed) happens only when the queue is full. count 0 is a success with accepted 0.
  0 < accepted < count is completed partial. The host sends the rest (from byte accepted of data) later (the queue empties only by what the probe has passed to the target)
  ([Common parts](oep-if-common.md) §1.4).
- The probe passes bytes from the head of the queue to the target in the way the mechanism carries them: dmseq up to 2 bytes in an answer to one frame
  ([dmseq](target-console-dmseq.md) host rule 5), DMDATA up to 3 bytes in an answer to one frame (§3.2). In both, if the queue holds
  less than that, all of it is carried. Bytes carried in an answer leave the queue. The order of bytes in the queue stays the order in which write received them.
- The queue is discarded when the stream closes (a write to a closed stream is rejected no_resource). clear discards only the read buffer and does not touch the queue.

### 2.1 Console pass-through (optional settings)

Optional settings items (core §13; the category is the fn of that `oep.target.console`) that send the output of a target that cannot free its UART (one that outputs through the debug mailbox) to the serial port even while there is no session.
As in [fixture](oep-if-fixture.md) §2.1, these settings apply independently of sessions.

| Name | form | key_kind | Meaning |
|---|---|---|---|
| `passthrough.{}.wire` | fn | transport (serial port) | the wire fn (`oep.wire.rvswd` or `oep.wire.swio`). Others are unsupported |
| `passthrough.{}.swdio` | channel | transport | SWDIO |
| `passthrough.{}.swclk` | channel | transport | SWCLK (rvswd only. No value is set for swio) |
| `passthrough.{}.max-speed` | u32 | transport | the same value and rules as max_speed of debug attach. Without a value the probe decides |
| `passthrough.{}.mechanism` | text (1 to 48) | transport | the name of the mechanism (one in the mechanism sequence of §1. Others are unsupported) |

- The key is the same as in [fixture](oep-if-fixture.md) §2.1. Only one pass-through can be set on one port (an overlapping set is unavailable cause 5).
- Pass-through on the port runs only when the values of wire, swdio and mechanism (and swclk for rvswd) are all present and the pin combination is one the declaration of that wire allows.
  A set that makes the complete combination one the declaration does not allow is unsupported. If any of the pins is disable, or has an output idle, unavailable cause 5.
- **Pass-through condition**: while all of the following hold — no session request has come from that port, and no session connection or plan holds those pins — the probe
  attaches with method 0 (no halt, no reset) on that wire, reads the console with that mechanism, and sends the target's output to the port outside frames as in [transports](../docs/oep-transports.md) §4.
  When the attach does not succeed, the probe retries at intervals it decides, only on a wire whose wake / setup procedure does not reset the target (swio).
  On a wire whose wake can reset the target (rvswd, debug §3), it tries only once each time the condition comes to hold ("does not change the state of the target" of debug §2).
- When the condition stops holding, the probe closes that connection without touching the target (debug §2) and returns the pins to the idle state. A session's attach is
  not refused because of the pass-through connection (the pass-through steps back first).
- The pass-through connection and console are not OEP resources: they do not appear in connections or streams, use no numbers and put no marks. No input is sent to the target.
- On wire loss (debug §2), the probe closes the connection and handles it by the retry rule above: swio retries, and rvswd does not try until the condition once breaks
  and holds again. A self-reset of the target keeps the connection as long as the mechanism can keep reading.
  A host that wants rvswd to try again opens and ends a session on that port, or unsets the value and sets it again (either one starts the condition).

## 3. Mechanisms

The 3 standard mechanisms use DATA0 (DMI 0x04) and DATA1 (0x05) of the debug module as a mailbox. The hart is not halted. The probe reads DATA0 and receives by the rules of the
mechanism.

- **While executing a riscv-dm request of that connection, and while the hart is halted** (anyhalted of DMSTATUS is 1), the probe does not read or write
  DATA0 / DATA1 for the console. After answering a riscv-dm request of that connection, the probe reads DMSTATUS before it next reads DATA0 for the console.
  When the hart runs again, the probe resumes reading. The handling of a sequence of abstract commands is in [Wires and debug](oep-if-debug.md) §4.1.

| Name | Direction | Definition |
|---|---|---|
| `sdi` | target → host | 3.1 below |
| `dmdata` | both directions | 3.2 below |
| `dmseq` | both directions | [target-console-dmseq](target-console-dmseq.md) (with sequence numbers and CRC) |

### 3.1 SDI

`sdi` is only this arrangement of the mailbox and does not depend on the wire of the connection. It carries bytes from the target to the host.

- **Bytes in the mailbox**: byte 0 is bits 8 to 15 of DATA0, byte 1 bits 16 to 23, byte 2 bits 24 to 31. Byte 3 is bits 0 to 7 of DATA1, byte 4
  bits 8 to 15, byte 5 bits 16 to 23, byte 6 bits 24 to 31. The low byte of DATA0 (bits 0 to 7) is the length L.
- **The target** sends n bytes (n = 1 to 7) at a time: it reads DATA0 and waits until it is 0, writes DATA1 (bytes 3 to 6), then writes DATA0 = n | bytes 0 to 2 << 8
  (DATA0 last). Bytes at positions n and above may have any value.
- **The probe** reads DATA0. If L is 1 to 7, it also reads DATA1, receives bytes 0 to L − 1 in that order, then writes 0 to DATA0 (the mark of receipt).
  If L is 0, there is nothing. If L is 8 or more, the word is not a frame: the probe receives no bytes and clears it by writing 0 to DATA0.
- There is no host → target direction (no send queue, and a request to a provided write is refused with unsupported).

### 3.2 DMDATA

`dmdata` is only this arrangement of the mailbox and does not depend on the wire of the connection. It carries bytes in both directions, and both sides use DATA0
in turn.

- **The status byte** is the low byte of DATA0 (bits 0 to 7). Bit 7 is T: 1 = **a target frame** (written by the target), 0 = written by the probe, or 0
  at the start. Bits 0 to 5 are L = the number of bytes + 4. Bit 6 is written as 0 and ignored by the reader.
- **Bytes in the mailbox**: the same positions as SDI (§3.1): bytes 0 to 2 are bits 8 to 31 of DATA0, bytes 3 to 6 are DATA1.
- **The target** writes DATA0 only when bit 7 of DATA0 is 0. It does not rewrite its own frame, including an empty frame, until the probe answers.
  - To send n bytes (n = 1 to 7), it waits until bit 7 of DATA0 is 0, receives the answer in that word (below), writes DATA1 (bytes 3 to 6) if n is 4 or more,
    then writes DATA0 = 0x80 | (n + 4) | bytes 0 to 2 << 8 (DATA0 last). Bytes at positions n and above may have any value.
  - To ask for input without sending, it waits until bit 7 of DATA0 is 0, receives the answer in that word, then writes DATA0 = 0x84 (**an empty frame**,
    L = 4: "the mailbox is the probe's turn"). After that, as with any other frame, it waits for the probe's answer (bit 7 of DATA0 becomes 0).
  - **Receiving the answer**: a word with bit 7 = 0 and L of 5 to 7 carries L − 4 bytes to the target (bytes 0 to L − 5). A 0 word and other words with
    bit 7 = 0 carry nothing.
- **The probe** reads DATA0.
  - If bit 7 is 0, it does nothing: the word is its own answer the target has not replaced yet, or 0. The probe does not write over a word with bit 7 = 0.
  - If bit 7 is 1 and L is 5 to 11, it receives n = L − 4 bytes: bytes 0 to 2 (up to n) from that word, and if n is 4 or more, bytes 3 to n − 1
    from DATA1 (DATA1 is read after DATA0). Then it answers.
  - If bit 7 is 1 and L is 4, the frame is empty (carries no bytes). The probe answers it.
  - If bit 7 is 1 and L is 0 to 3 or 12 to 63, the word is not a target frame and carries no bytes (mostly a value left by the probe or another debugger,
    for example 0xffffffff). The probe clears it by writing 0 to DATA0 and puts no input on it (it takes no bytes out of the send queue).
  - **Answer**: the probe writes DATA0 exactly once per target frame. If the send queue (§2) has bytes, with n = the smaller of the number of bytes in the queue and 3,
    DATA0 = (n + 4) | bytes 0 to n − 1 << 8 (bytes 0 to n − 1 are the first n bytes of the queue. bit 7 = 0. Bytes at positions n and above are 0), and those n bytes
    leave the queue. If the queue is empty, DATA0 = 0. The probe does not write DATA1.

## 4. Referenced specifications

The OEP messages of this document are determined by this text alone. What is used to drive the target:

| Specification | Part used |
|---|---|
| RISC-V Debug Specification 0.13.2 and 1.0 (DMSTATUS.version 2 and 3) | DATA0 (DMI 0x04), DATA1 (DMI 0x05) and DMSTATUS (anyhalted of §3 and havereset for the halt check) of the debug module, and the abstract commands that also use DATA0 and DATA1 |
