# OEP standard interfaces: console v1

[日本語](oep-if-console.ja.md)

Status: **normative** (v1, before the freeze: until the v1 freeze a rule or a number may still change). The core is [OEP core](oep-core.md), the common parts are [common parts](oep-if-common.md) (§1 positioned
streams, §2 debug connections). The only definition of the numbers is `registry/oep-v1.toml`. The thinking and the reasons are in
[console streams](console-stream.ja.md) (Japanese).

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
| 0x03 | marks | stream(u16), from_serial(u32) | more(u8), count(u8), count × (len(u8), mark), [TLV] | Not required |
| 0x04 | clear | stream(u16) | — | Required |
| 0x05 | mark | stream(u16), value(u8) | — | Required |
| 0x06 | write | stream(u16), count(u16), data | accepted(u16), [TLV] | Required |
| 0x07 | close | stream(u16) | — | Required |
| 0x08 | streams | first(u8) | more(u8), count(u8), count × (len(u8), stream(u16), connection(u16), mechanism(u8), users(u8), state(u8)), [TLV] | Not required |

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
  the slot that opened it by bind. close, lease expiry and force remove only one's own share, and it closes when every user has left (mark closed, detail 1 / 2).
  When a user left through the replacement or deletion of a slot item, detail 3; when the connection closed, 4.
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

(Reference) This is the layout of WCH's SDI printf.

- The target waits for DATA0 to become 0, then writes DATA1 = bytes 3 to 6, DATA0 = length (1 to 7) | bytes 0 to 2 << 8 (little endian,
  DATA0 written last).
- If the low byte of DATA0 is 1 to 7, the probe also reads DATA1, receives that many bytes, and writes 0 to DATA0 (the mark of receipt).
  A low byte of 0 means nothing. 8 or more is not a slot (not discarded).
- There is no host → target direction (write accepts nothing: accepted 0, completed failed).

### 3.2 DMDATA

(Reference) This is the framing the minichlink tool uses.

- The low byte of DATA0 is the status byte. bit 7 = 1 is the target's slot, the low 6 bits are length + 4.
- In a target's slot (bit 7 = 1), if length + 4 is 5 or more, the probe also reads DATA1 and receives length (1 to 7) bytes (the layout is the same as SDI). 4 is the target's
  empty slot ("the mailbox is the host's turn").
- The probe answers exactly once per target slot: if it has bytes to send, DATA0 = (n + 4) | bytes 0 to 2 << 8 (n is 1 to 3, bit 7 = 0);
  otherwise DATA0 = 0. It does not write to a word with bit 7 = 0 (the host's slot has not yet been taken, or it has just answered).
- An empty slot is answered only when it is still there on the next read (the target may place a real slot right after an empty one, and answering immediately
  would erase that slot).
