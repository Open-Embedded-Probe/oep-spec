# Open Embedded Probe — the protocol core (OEP core) v1

[日本語](oep-core.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **normative** (v1). For the freeze state and the language and compatibility policy, see [versions and stability](versioning.md). This document defines only the protocol core of OEP. Interfaces are
defined by their own documents (the list of those whose names begin with `oep.` is in [interfaces](../interfaces/README.md)). This document is complete in itself: where a reader needs the reason for a rule,
the reason is written together with the rule. The guides (§14) add practice, not rules. Where this document and a non-normative document disagree, this document is right.

The only definition of the numbers (op, tag, reject reason, status, enum) is `registry/oep-v1.toml`; the tables in this document are copies of it.
Where they disagree, the registry is right and the document is corrected. The registry also holds the names and numbers of the interfaces whose names begin with `oep.`.
What probes and hosts do to conform, and how to check it, is listed in [conformance](conformance.md) (a guide).

## 0. Scope and layers

OEP consists of 2 layers.

| Layer | Content | Name | Version |
|---|---|---|---|
| **Core (this document)** | What every probe and host implements regardless of functions: transports and frames ([OEP transports](oep-transports.md)), messages, sessions and exclusion, discovery (confirm / list / describe), the probe's time (clock), the general rules for channels and for resource lifetime and contention, the notification mechanism, the extension rules, the optional settings mechanism (§13) | None (spoken through fn 0; not in list) | The protocol revision (confirm) |
| **Interfaces** | Named functions defined only with the core's mechanisms. Every function the core does not make mandatory is in an interface | A reverse-DNS name. The project's own have short `oep.` names (§12) | A revision per interface |

Relations between interfaces (one interface using another interface's resources, and so on) are defined by the documents of the interfaces
concerned.

Outside the core: the procedure for updating the probe's own firmware (DFU, Mass Storage and so on), the details of USB descriptors.
Specific functions for self-update and authentication can be defined as optional interfaces following §12. No update operation and no mandatory authentication function is added to the core.

**External specifications**: The OEP protocol is determined by these documents alone. To operate targets, buses and transports, the external specifications that each document lists in its "referenced specifications" section
are also needed (for transports, [transports](oep-transports.md) §8).

## 1. Terms

| Term | Meaning |
|---|---|
| probe | A device that speaks OEP (debugger, fixture, logic analyzer and so on) |
| host | Software that uses a probe |
| target | What is operated or observed (a microcontroller under development and so on). The probe itself may be the target; even then its role as an OEP endpoint is probe |
| transport | What carries OEP frames (UART bridge, USB CDC, built-in USB serial, USB vendor bulk, HID, TCP) |
| serial port | A transport that the OS sees as a serial device (UART bridge, USB CDC, built-in USB serial). It carries only OEP frames ([transports](oep-transports.md) §4) |
| interface | A function a probe offers by name. Found with list, called through fn |
| fn | A number (u16, §7.2) that points at an interface while the boot_id stays the same. fn 0 is the core (it has no name and is not in list) |
| op | The number of an operation within an interface (u8) |
| session | The right to change state while holding the lock. Identified by a session_id (u32) the host chooses |
| lease | The deadline of the lock. Extended by requests such as keepalive |
| channel | A pin of the probe. Identified by a name (the pin name of the chip's datasheet, §7.5); on the wire it is pointed at by a number (u16) valid while the boot_id stays the same |
| settings | Values the probe keeps across boots. The core coordinates them, and the owner of an item (the core or an interface) defines it (§13) |

### 1.1 Normative words

The capitalized MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are used as in RFC 2119 and RFC 8174. A sentence in the present tense that states what a probe or host does ("the probe returns …") is a requirement (MUST). "Where it can" is SHOULD. Sentences marked (informative), examples and notes are not normative. In the Japanese text, 「〜する／〜しない」 corresponds to MUST / MUST NOT, 「〜してよい」 to MAY, and 「できれば〜する」 to SHOULD.

### 1.2 Conformance

What a probe MUST implement:
- at least one of the transports of §3, and its frames;
- §4 to §6;
- confirm, list, describe, clock, open, end, keepalive and lock_state of fn 0;
- unit_id, transport and max_op_ms in the describe of fn 0 (§7.5);
- the common tag ops (§7.4) in the describe of fn 0 and of every fn put in list;
- if it has channels, channels in the describe of fn 0 (§7.5) and the channel idle state of §8;
- if it has an interface that sends notifications, §10.3 and §10.4;
- if it has settings, §13 (save is optional).

Optional: every interface. Which other interfaces a probe that offers an interface must offer is defined by that interface's document (§0).

**The minimal implementation**: a probe MAY have only one transport, with `max_frame = 64`, `window = 64`, `max_inflight = 1`.
It MAY process requests one at a time and need not have named interfaces, notifications, pins or interface resources.
Several transports, several outstanding requests and sending notifications are obligations only when they are provided, and are not required of the minimal implementation.
The amount retained for resending requests and answers can be limited as in §5.1, and a probe MAY keep no byte record for resending and refuse old requests only by the last number.
Dynamic memory allocation, threads and a 64 bit hardware timer are not required as means of implementation.

**Mandatory ops and optional ops.** The ops in an interface's op table (§11 for fn 0, the op table of the interface's document for the others) are always present in a probe that puts that interface in list, except the ops the document says are optional. **Every fn declares the ops it has in one place: the common describe tag ops (0x07, §7.4).** Every mandatory op is set there. An optional op is set only when the probe has it.

A probe answers a request for an op that the fn's ops does not set (an op the interface does not define, or an optional op it does not have) with rejected unknown_operation (§4.3). It answers a request that asks an op it has for an undeclared optional function (mode, format, value, critical TLV, pin combination) with rejected unsupported (§4.3).

## 2. Common rules

### 2.1 Byte order and text

All numbers are little endian. Text is a byte string of UTF-8 whose length is carried separately (no terminating 0).
A **bitmap** is a sequence of bytes, and bit i is bit (i mod 8) of byte ⌊i/8⌋ (bit 0 is the least significant bit). A bitmap continues to the end of the value that contains it.

- For a u8 boolean, the sender puts 0 (false) or 1 (true), and the reader reads every value that is not 0 as true.
- Before showing text from an answer, a host replaces C0 control characters (0x00 to 0x1F), 0x7F and invalid UTF-8.

### 2.2 TLV

```text
tag(u8) | len(u16) | value(len byte)
```

- **Every TLV has one shape**, regardless of the length of its value (0 to 65535 bytes). A TLV whose len goes past the end of the message that contains it is
  malformed in a request. If it is in an answer, event or data, that answer, event or data is broken.
- **The tag number is the low 7 bits (0x01 to 0x7F).** Bit 7 is the critical mark. It is used only in requests and is not part of the number: 0x10 and 0x90 are the same TLV sent without and with the mark. In answers, events and data bit 7 is 0, and a reader that meets a TLV with bit 7 set there skips it as an unknown tag.
- TLV number 0 (with or without the critical bit) is malformed in a request and a broken TLV in an answer or notification. The fixed-part mark 0 of unsupported is not a TLV.
- The payload of rejected unsupported holds the tag byte as received (including bit 7).
- The tag space is per context of the payload definition. For requests and answers (fn, op) and the answer's resolution/reason, for describe the declared fn,
  for data the fn, and for events (fn, kind) decide the context. The same number in a different context is a different thing.
- A repeated tag is a tag the definition says repeats, and expresses a sequence (§2.3).
- **The named extension TLV (tag 0x7F)**: in every context, tag 0x7F is reserved for named extensions. The value is
  `name_len(u8), name, data`. name is a reverse-DNS name of the same form as an interface name in §12 rule 1, and the shape and meaning of data are decided by
  whoever owns that name (§12 rule 7). No definition gives tag 0x7F another meaning.
  - A name has no revision. data under the same name has the same shape and meaning in every context and on every probe. To change the shape or meaning, use a new name.
  - It MAY repeat. Whether the same name can appear twice is decided by that name's definition.
  - In a request, an extension with an unknown name is refused with rejected unsupported if it is critical (0xFF) (the tag in the payload is 0xFF), and is ignored otherwise.
    An extension whose name_len does not fit in the value is malformed.
  - In answers, events, data and describe, the reader skips extensions with unknown names.

### 2.3 Fixed shapes and TLVs

- **A container knows its own length**: for frames, TLVs, sequences and byte strings (data), the reader can find the end without the request or outside knowledge.
  Variable parts (sequences, byte strings, text) are preceded by a count or length.
- **Every fixed shape is decided by (name, revision)** (for fn 0, by the protocol revision, §2.8): the fixed parts of request, answer, event and data payloads, TLV values, sequence
  elements, items of settings data. A fixed shape is not extended at the end. The variable parts within it (names, lists within an element) are preceded by a count or length,
  so a fixed shape also knows its own length.
- **Sequence**: `count, count × element`. The same in requests and answers. An element does not carry its own length. The shape of the element is decided by the revision, and the reader
  reads the fields one by one.
- **Answer**: after the fixed part of each op's answer (and sequences preceded by a count or length) comes a sequence of TLVs. Everything added later is added here as TLVs.
  The host skips unknown tags. An answer shorter than its fixed part is treated as a broken answer. A TLV in an answer, event or data whose value does not have the length the definition
  decides (for a value with variable parts, the length its counts and lengths decide) is broken: the host does not use it.
  **The shape of an answer's fixed part is decided per (op, resolution, outcome)
  by the op's definition** (success and failure may have different shapes; interface common parts §3).
- **Events and data** (§10.2) are like answers: after the fixed part comes a sequence of TLVs.
- **Request**: only a sequence of TLVs can be added after a request. The host **sets the critical bit** on a TLV without whose effect the request is meaningless or harmful (reset of attach, max_speed of scan and so on).
- **An unknown TLV** (a tag this probe does not implement): if critical, the probe refuses the request with rejected unsupported (the tag as received in the payload).
  If not critical, it ignores it.
- **An implemented TLV** is handled the same regardless of bit 7: if the length of the value differs from the definition (for a value with variable parts, from the length its counts and lengths decide), or it has
  a value the definition excludes, rejected malformed. A value the definition left unused, and a value this probe does not handle, rejected unsupported (the tag as received).
- **The value of a request TLV is not extended at the end.** New fields go in new tags.
- In a **request**, if there are 2 or more of a tag the probe implements and that the definition does not say repeats (counted as the same tag regardless of bit 7), rejected malformed.
  The probe need not validate the second and later values. Unknown tags are not counted, since the probe does not know whether they repeat.
- In an **answer, event or data**, if there are 2 or more of a tag the definition does not say repeats, the reader uses the first.
- A request shorter than its fixed part is rejected malformed.
- **A variable sequence is preceded by its count** (so that TLVs can follow it).
- No omittable field is put in a fixed part (a value one wants to omit becomes a TLV).

### 2.4 Unknown values

- A frame with an unknown role is discarded.
- A probe discards without answering a message whose role is not the request role (0x01) and a request shorter than the header (10 bytes). A host discards messages whose role is the request role.
- A host treats an answer shorter than 5 bytes, and an event or data frame shorter than its header, as a broken frame (§5.1, [transports](oep-transports.md) §5).
- An unknown resolution and an unknown outcome of completed are treated as failure.
- Unknown values of an interface's status or reason are treated as failure.
- An unknown event kind is discarded (seq is counted).
- A host ignores the reserved bits of an answer's flags. Unknown values of an answer enum that do not signal failure (cause, the kind of a scan entry) are shown as unknown values. Unknown values of status and reason stay failure.

### 2.5 Number spaces

| Space | Ranges |
|---|---|
| role | 0x01 request, 0x02 answer, 0x03 event, 0x04 data. 0x00 invalid, the rest unassigned |
| op of the core (fn 0) | 0x01 to 0x0F discovery, 0x10 to 0x1F session, 0x20 to 0x2F settings (§13, transport network), 0x30 to 0xFF unassigned |
| op of an interface | 0x01 to 0x0F only for common operations (0x01 subscribe, 0x02 unsubscribe). 0x10 to 0xFF each interface's operations |
| reject reason | 0x01 to 0x3F core (common to all interfaces), 0x40 to 0x7F interface, 0x80 to 0xFF unassigned |
| cause of unavailable | 0x01 to 0x3F core, 0x40 to 0x7F the interface of the requested fn, 0x80 to 0xFF unassigned. fn 0 uses no specific range |
| outcome | 0 success, 1 failed, 2 partial. The rest reserved |
| event kind | A space per fn. 0x01 to 0x7F decided by the interface, 0x80 to 0xFF unassigned (fn 0 sends no notifications, §10.2) |
| TLV tag | Per payload context (§2.2). The number is the low 7 bits; bit 7 is the critical mark (§2.2). 0x00 invalid in every context, 0x7F named extension in every context, 0x7E padding in the data context (§10.2) |
| describe tag | 0x01 to 0x3F common tags of the core (§7.4), 0x40 to 0x7E interface, 0x7F named extension (§2.2) |
| resource number | u32 (1 to 0xFFFFFFFF, 0 not assigned), one space per probe (§9) |

Unassigned means a number whose meaning is not defined yet. The range only for common operations can be assigned only by its owner.
Invalid numbers (role / op / TLV 0) are structurally never used. Numbers retired after the freeze are recorded as retired and not reused.
Numbers removed before the freeze MAY be rearranged and reused. Individual numbers are not reserved by guessing future uses.

**How numbers are assigned** (the core and every interface):

1. Only the owner of a space (the project for the core, the owner of the name for an interface) assigns numbers. Others take no numbers and
   identify things by name (named extension TLVs, §2.2; name lists, §7.7; their own interfaces, §12). So there is no number range for others.
2. Ranges carry meaning only (a) when several owners assign in one space (the core / common parts and interfaces; the ranges in the table above), and
   (b) when the reader decides from the number how to handle unknown values (bit 7 of a tag).
3. Otherwise numbers are assigned consecutively in order of definition from the start of the owner's range. Before the freeze no gaps are made (exception: reject reason 0x05 stays empty;
   the core's numbers do not move under the provisional fixing ([versions and stability](versioning.md) §2.1), so later numbers are not shifted down).
4. Values that several interfaces use with the same meaning (TLVs of the same family, roles, enums) are defined in one place as the family's shared space,
   and each interface uses part of it with the same numbers. The part may have gaps.
5. Values decided by an outside specification (the values of a protocol's answers, bit positions) are used as they are. Sets of bits are expressed by bit position.

Unless a definition says otherwise, unused enum values and reserved bits of requests can all be defined later (§2.8). A probe refuses them with rejected unsupported.

### 2.6 Wrapping values

The cycling of corr (u16) and the resend comparison follow the half-cycle rule of §4.1 and §5.1. The retained-range rule below does not apply to corr.

seq (u16), and the serial numbers and times an interface defines as wrapping, are compared as differences signed with the same width w
(serial number arithmetic). Among the values of one such space that the probe holds at the same time (for example, records that can still be read, data not yet released),
the difference newest minus oldest is less than 2^(w−2) (a quarter of the width). Stream positions and times that do not wrap are u64
(stream positions defined by an interface, times and so on). Resource numbers (§9) are only compared for equality and are not reused while the boot_id stays the same.

### 2.7 Clock

A probe has one clock: **ns since boot (u64)**. While the boot_id stays the same the clock does not decrease and does not wrap. Every value returned as the probe's own time (uptime_ns of clock and so on) is this value,
and "not yet" is all bits 1.
A host reads the current value of the clock with clock (§7.6). An interface that carries values of another clock states that clock's subject, origin and unit in its own definition, and does not mix it implicitly with the probe's clock.

**ns is the unit of expression, not a resolution requirement.** A probe MAY convert its clock ticks into ns. Values read within the same tick MAY be equal.
A short hardware counter MAY be extended in software. When extended, time is not lost at the counter's wrap, and monotonicity is kept while the boot_id stays the same.
When an interface needs a particular accuracy or resolution, that interface defines the capability and conditions.

### 2.8 Names and revisions

- The shape and meaning of every **fixed shape** of an interface (§2.3: fixed part, TLV value, sequence element, item) are **decided by (name, revision)** (the revision of list, u8).
- **The revision is raised when an existing contract breaks**. This includes changes to the meaning or length of a fixed shape, mandatory operations, state transitions, resource lifetimes and so on, by which existing hosts or probes can no longer work under the previous contract. It also includes making an optional operation or function mandatory. A host does not use an interface with an unknown revision.
- Adding optional request TLVs, response TLVs, optional ops or optional events while keeping the existing shapes and behaviour contracts does not change the revision. Hosts that do not
  know them do not use them. Whether an optional op exists is declared in ops (§1.2, §7.4), and whether an optional function that is not an op (modes, formats and so on) exists is declared in describe (features and so on).
- When the shape of the core, or behaviour that breaks an existing contract, changes, the protocol revision (confirm) is raised. The shapes of this document are revision 1.

## 3. Transports

Messages are carried in transport frames. Transports are defined by [OEP transports](oep-transports.md). That document is part of the core.

## 4. Messages

### 4.1 Request

```text
role=0x01 | corr(u16) | fn(u16) | op(u8) | session_id(u32) | payload    header 10 bytes
```

- `corr`: a u16 that never uses 0. A host advances the number of new requests cyclically **per session_id** (normally by 1, after 65535 comes 1).
  The forward distance `d = (new − previous) mod 65536` is 1 to 32767 (less than `corr_half_range`). The host chooses the first non-zero number.
  A host does not send a new request whose forward distance from the oldest outstanding request of that session is 32768 or more. It resolves it or recovers following §5.1.
  The numbers of session_id 0 requests do not affect the session's ordering. A large number of session_id 0 queries does not make the session's numbers skip half a cycle or more.
  On the same transport, the corr of an outstanding request and a corr for which an old answer may still remain are not reused, even with a different session_id. If needed, that number is skipped.
  Receiving the answer to a request with another number sent after the last resend copy confirms, on a transport that keeps order, that the answers before it have been read.
  If draining cannot be confirmed, the transport is recovered. Starting a new session and cycling the numbers of session_id 0 also keep this reuse rule.
  A resend makes the whole request, including the number, the same byte for byte. A resolved request is not resent later.
- `session_id`: the session the request belongs to, or **0 = no session**. Every request has it.
  - A request for an op that needs the lock (§6.3) carries the id of the session holding the lock. If 0, rejected session_required.
  - A request for an op without the lock MAY carry 0: then it is processed without the session checks (§5.1, §6.2) and does not touch the lease. With a non-zero id,
    it goes through them like a request that needs the lock, and restarts the lease count (§6.1).
  - open carries the id of the session it opens (§6.4). If 0, rejected malformed.

### 4.2 Answer

```text
role=0x02 | corr(u16) | resolution(u8) | detail(u8) | payload           header 5 bytes
```

| resolution | Value | detail | payload |
|---|---:|---|---|
| rejected | 0x00 | reject reason (§4.3) | Auxiliary information decided by the reason |
| completed | 0x01 | outcome (0 success, 1 failed, 2 partial) | Decided by the op |

- There is exactly one answer per request. The answer goes back on the transport the request came on, with the same corr. fn and op are not returned.
  When a resend copy of an unfinished request is discarded following §4.4, the one answer of the original request is the common result for that copy too.
- **rejected only when "the request was not accepted"** (format, number, session, or the current state does not allow accepting it). Something that was accepted and executed
  but did not work out is completed failed or partial, and the payload returns how far it progressed and why.
- The measurement point of completed's progress is decided by the op. For writes to an external target, failed or progress 0 does not guarantee that there was no effect.
  An interface defines measurement points such as sent or confirmed complete, and the handling when the result is unknown. A host does not automatically re-execute a state change on the basis of a failure alone.

### 4.3 Reject reasons (core)

| Value | Name | Meaning | payload |
|---:|---|---|---|
| 0x01 | unknown_function | That fn does not exist (the fn of the header, or a fn the payload points at) | — |
| 0x02 | unknown_operation | That fn has no such op | — |
| 0x03 | malformed | Wrong length or value range | — |
| 0x04 | unavailable | Cannot be accepted in the current state, resources or policy | A sequence of TLVs (optional, below) |
| 0x06 | window_exceeded | window / max_inflight exceeded | — |
| 0x07 | no_session | The request carries a session_id, but no session holds the lock (the session ended, or never existed). The host opens a session again | — |
| 0x08 | locked | Another session holds the lock | Remaining time ms (u32), [TLV owner (§6.4)] |
| 0x09 | session_required | A request for an op that needs the lock carries session_id 0 | — |
| 0x0A | no_resource | The probe does not know the resource of the request (connection, stream and so on, things pointed at by number). The host makes it again. Every interface uses this for unknown numbers | — |
| 0x0B | unsupported | It is in the definition, but this probe cannot handle it (a critical TLV, a value of the fixed part, an optional function of an op this probe has) | `tag(u8)`, [TLV]. tag is the value as received for a critical TLV, 0x00 for a value of the fixed part. To show which element, TLVs follow (the same tag space as unavailable: channel, index) |
| 0x0C | result_lost | The result of a resent request is not remembered (§5.1) | — |

The detail of rejected is the reason; other information goes in the payload. `—` in the table means there is no fixed-part field. The rule of §2.3 that adds TLVs after an answer's fixed part also applies to success answers with an empty fixed part and to rejected. Unknown answer TLVs are skipped.

**Order of refusal**: the probe checks in this order and answers with the first that applies.

1. Header: corr 0 is malformed. Otherwise unknown_function → unknown_operation (an op the fn's ops does not set, §1.2) → session_required. After that, the optional policy decision below.
2. Resend: an unfinished copy MAY be discarded following §4.4. If already processed, result_lost / the remembered answer from the table of §5.1.
3. Session (§6.2): no_session / locked.
4. Others: the probe checks format (malformed: length, counts that do not match the content, TLV encoding, contradictions between fields, values the definition excludes), support (unknown_function: the fn the payload points at does not exist;
   unsupported: values the definition left unused, values this probe does not declare, unknown critical TLVs, pin combinations the declaration does not allow) and state (window_exceeded; unavailable: cannot be accepted with the current state or resources;
   no_resource: the resource pointed at by number is unknown), all before changing anything, and refuses with any one of the reasons that apply.

**Optional policy decision**: a probe MAY refuse requests by a policy based on the transport, the party authenticated on the transport, a physical presence check, a product mode and so on.
In that case it sends rejected unavailable with the TLV cause 7. confirm / list / describe / clock / lock_state of fn 0 are not refused by this policy.
A probe without a policy can omit this decision. Authentication methods, operations and declarations for authentication, and keeping permission state are not mandatory functions of the core.
The decision is made after the header check, before handling resend copies, returning saved answers and the session decision.
A request refused by policy is not executed, and does not change the resend history, lease, owner or resources. It does not replace a saved original answer either.
This is a decision when processing a request; it does not guarantee cancelling accepted operations or stopping answers and notifications being sent.
The revocation of permissions and the handling of accepted operations and output are defined by the transport or extension that provides the policy.
A policy does not exempt from the conditions of the lock. A session_id or an owner string alone is not made a proof of identity or permission (§6).

The tag in the payload of unsupported is 0x00 for a value of the fixed part, and the tag as received of the TLV for a refusal about a TLV.

**The payload of unavailable** (an optional sequence of TLVs. The host skips unknown tags and can handle it even when absent. The probe adds what it knows):

| tag | Name | Value |
|---:|---|---|
| 0x01 | cause | u8: 1 pin in use, 2 limit of count or processing capacity, 3 not enough storage, 4 bound to another fn, 5 a setting restricts the use, 6 wrong state, 7 not allowed by policy |
| 0x02 | channel | u16. The channel that collided (MAY repeat) |
| 0x03 | item | u8. The position in the request's sequence that the refusal is about (from 0; the set and unset values of settings, §13.5) |
| 0x05 | fn | u16. The fn that the refusal is about |

An interface can add its own tags from 0x40. The TLVs after the payload of rejected unsupported are in the same space (channel 0x02, fn 0x05,
an interface's index and so on). There, however, 0x01 is supported, used for refusing confirm (§7.1). item (0x03) is also in the same space.
cause 0x40 to 0x7F can be used by the interface of the requested fn in its own definition. They are not reinterpreted as values of another fn pointed at by a diagnostic fn TLV.

### 4.4 Pipeline

- In confirm (§7.1) the probe returns `max_frame` (the largest message length it receives), `window` (the limit on the total message length of outstanding requests) and
  `max_inflight` (the limit on the number of outstanding requests). The message length includes the header (from role) and does not include the frame wrapping (COBS, CRC, length).
- The host keeps these limits. A probe MAY refuse a request that exceeds them with rejected window_exceeded, but a request lost by overflowing the buffer gets
  no answer either. Keeping them is the host's responsibility.
- A probe accepts new requests that keep each transport's window / max_inflight without losing them, even while earlier requests are being processed.
  A scheme that stops receiving is used only when this condition can be kept by buffering reception, transport flow control and so on.
  With 1 transport and max_inflight=1, the host does not send the next new request until the answer. An unfinished resend copy MAY be discarded following the rule below.
- window / max_inflight count distinct outstanding requests of that transport. A resend copy with the same transport, session_id and corr is not counted as a new outstanding request.
  While the original request is waiting to be processed, executing, or before or during sending its answer, the probe MAY discard that copy without keeping it separately and without comparing its content.
  It does not re-execute the original request, and does not update the lease or processing deadline because of that copy alone. A resend after the answer has been sent follows §5.1.
  This handling of unfinished copies also applies to session_id 0. A host makes the whole request the same byte string even when resending (§4.1).
- If the request fits but the fixed result that the request's arguments require does not fit in that transport's max_frame, the probe refuses before executing with rejected unsupported (fixed-part mark 0).
  When the interface defines shortening, a prefix or paging of the result, it fits by that rule. Results needed for success are not discarded to make it success.
- A probe processes requests in the order received and returns answers in the order of the requests.
- The max_frame, window and max_inflight of confirm are the limits **of the transport the confirm came on**. They are counted per transport, and requests outstanding on one transport do not use the receiving room of another transport. The table of §5.1 stays one per probe (a session's requests are sent on one transport, [transports](oep-transports.md) §3).
- **The host's waiting time**: an absent answer is decided only by timeout. For each request the host waits **at least**: the limit on the processing time of the whole request
  + 1000 ms (`host_wait_add_ms`) + the transfer time ([transports](oep-transports.md) §6). The processing-time limit is max_op_ms (§7.5). Only when an operation's definition
  sets a shorter limit for the whole request, including validation, internal retries, execution and cleanup, MAY that limit be used.
  The processing limit of the whole request for confirm / list / describe / clock / keepalive / lock_state of fn 0 is the smaller of max_op_ms and `core_quick_op_max_ms` (1000 ms).
  This limit includes validation and building the answer, and does not include the transfer time of the transport or the time waiting for earlier requests on the same or another transport to finish (the same as §7.5).
  It starts when the validation of that request itself begins, and includes internal waits and cleanup after validation. Processing that interrupts requests of another transport, or parallel processing, is not required.
  When there is a wait for an earlier request on another transport, it is not guaranteed that the time from sending to the answer fits within this processing limit.
  This short limit is not imposed on the cleanup of open / end.
  The waiting time of an argument alone is not used as the limit of the whole request. Before a request that changes state, the host gets max_op_ms with the fn 0 describe.
  While max_op_ms has not been obtained yet, core_quick_op_max_ms is used for these processing limits (the wait floor is 2000 ms plus the transfer time).
  The wait starts when the request has been written. While an earlier request on the same transport is outstanding, it starts when the answer to the request just before it arrives (the probe answers in order).
  Waiting longer than this floor is always allowed. When the wait has passed, proceed to the resend of §5.1.
- **This floor applies to every request**. A wait that an interface's document puts between requests is not a time to wait for an answer, and does not shorten this floor.
  The repetition of confirm that [transports](oep-transports.md) §4 allows a host handling the optional port_speed is, each time, a new request with a new corr, not a resend of §5.1: the host MAY send the next before the floor of the previous confirm has passed, and an answer to the previous corr that arrives later is accepted or skipped. Ordinary probing follows §3 of the same document. Other requests are not repeated this way.

## 5. Recovery and resending

### 5.1 Resending and keeping results

- When an answer does not come or is broken, the host MAY resend the identical request. A request that may or may not have been executed is not automatically re-executed with a new corr.
- For the last successful new session, the probe holds the corr of the last new request it received. This ordering state is mandatory.
  The record of requests and answers for resending is optional; its count and bytes MAY be limited, and it MAY be 0 entries. max_inflight is the number of outstanding requests accepted and does not set the number of resend records.
  When a record is kept, its key is (session_id, corr), and the identity of a request is all bytes of the header and payload. open is handled by the same rule.
  Records half a cycle or more in the past are discarded and not used for matching.
- After passing the header and policy decisions of §4.3, at step 2, when the same corr as a recorded request comes, rejected result_lost if not all bytes of the request are kept.
  If they are kept, the content is compared; if different, rejected malformed. If the same, the recorded answer is returned. If the answer is not kept, rejected result_lost.
  In every case it is not re-executed, and the lease and the destination of notifications do not change. This record is not returned for a request refused by the optional policy (§4.3).
- A number of the same session not in the record is judged by the difference from the last number `d = (corr − last) mod 65536`.
  If `0 < d < 32768` it is a new request; otherwise (including the same number and exactly half a cycle) rejected result_lost.
  The retention of requests and answers MAY have a size limit. Even old requests not kept are prevented from re-execution by the last number and this comparison.
  This decision assumes the host and transport ordering rules of §4.1. Reinjecting a request older than half a cycle is not guaranteed to be told apart by generation.
- A new request of the last successful new session that has passed step 2 of §4.3 updates the last corr, including one that is later rejected.
  When a byte record is kept, it is recorded within its retention limit. To correct a request, a new corr is used.
- The ordering state remains after end and expiry too. Byte records being kept also remain, following their retention limit and the half-cycle rule. An open with the same ID does not initialize the resend state.
  **Only when the open of a new session with a different ID succeeds** is the previous resend state discarded, and a new state starts from that open.
  A host does not resume a session with an ended id, and does not deliberately cycle or reuse ids. It chooses a new random number for a new session. For chance collisions, see §6.1.
- Processed requests of session_id 0 are not deduplicated. Unfinished copies MAY be discarded following §4.4. A request with corr 0 is rejected malformed.
- This resend state is one per probe and is shared by all transports. A broker that answers OEP requests itself also follows this rule.
- When resending is given up, the outstanding requests on that transport have unknown results. The host closes and reopens the connection on TCP, and on other transports
  recovers following [transports](oep-transports.md) §5. It checks the boot_id and reads the state before deciding the next state change.
- Resending the identical request after reconnecting also keeps within the half cycle. If the progress of numbers or the draining of old queues cannot be determined, recover with a new session_id.
  Hosts and brokers do not automatically reinject requests and answers left on the old transport into the new transport. Resource release by a new session is as in §9.


## 6. Sessions and exclusion

### 6.1 Lock

- A probe has **one lock**. Only the session holding the lock can execute requests that change state.
- A host chooses the session_id of each session as an unpredictable 32 bit random number. It does not use fixed values or 0. An open with session_id 0 is rejected malformed. The probe remembers the session_id that last held the lock.
  Chance coincidences of random numbers can happen. A host is not required to keep the history of all past ids.
  Requests with matching ids are treated as the same session, and it is not guaranteed that a collision can be identified by communication alone. A session_id is not used as a proof of a host's identity or permission.
- The lease is decided by open. A new request of the lock holder that has passed step 3 of §4.3 stops the lease only during validation, execution, cleanup and building the answer.
  The lease_ms count restarts when the answer is built (including rejected answers). This starting point does not depend on waiting for or completing the sending of the answer, and is the same when the transport closes and the answer is discarded.
  The lease of an old session ended with end is not updated. A new open starts the lease from building the answer for the new owner.
  Resends of processed requests, unfinished resend copies, requests of session_id 0 or of other sessions, and waiting for communication do not stop the owner's lease and do not update it.
  A long op of the owner does not end the session even if it is longer than the lease. The processing-time limit is max_op_ms (§7.5).
  The resources of a session past its deadline are released following §9. A probe that processes sequentially MAY do the expiry cleanup after processing a request of another session / session_id 0,
  but does it before processing the next request (including the resend decision) and before new notifications or resource operations. Returning pins exactly at the deadline by interrupt or another thread is not required.

### 6.2 Deciding on a received request

The probe remembers whether the lock is held, the session_id that holds or last held the lock (S below; the resend state of §5.1 is tied to it), and the
owner while the lock is held (when it implements the display). The decision of §5.1 (resend) comes before this table. Requests of session_id 0 for ops without the lock do not come here (§4.1).

| Lock | Request | Result |
|---|---|---|
| Free | open (session_id ≠ 0, different from the last ended ID; with or without force) | Set the lock: S becomes this id, the lease starts from lease_ms, owner as the open indicates |
| Free | A new open with the last ended ID, or another request with session_id ≠ 0 | rejected no_session |
| Held by S | open with session_id S (with or without force) | An open with a new corr: lease_ms is renewed. Resources and resend history remain. The destination of subscriptions does not change (a resend of the identical request is §5.1) |
| Held by S | open with another id, without force | rejected locked with the remaining time (and owner) |
| Held by S | open with another id, with force | Take it (§6.4): release the resources of S (§9), then set the lock for the new id |
| Held by S | Another request with session_id S | Process it |
| Held by S | Another request with another id | rejected locked with the remaining time (and owner) |

### 6.3 Requests that need the lock

Every operation whose request, as its effect, changes the target's state, pin driving, settings, runtime resources, subscriptions or the consumption of retained data needs the lock (it carries the session's id, §4.1).
Only read-only requests that change none of these can be used without the lock
(confirm, list, describe, clock, lock_state, read-only ops an interface defines). An op an interface
makes lock-free MUST NOT change those states. The per-transport revision choice of confirm, transport timers / recovery driven by frame reception or the passing of time,
and the progress of asynchronous acquisition and reception are distinguished from the effect of such operations. A request with session_id 0 does not stop or update the owner's lease (§6.1).

### 6.4 open, end, keepalive, force

- **open** (lease_ms, force; the session_id is the header's, §4.1): takes the lock. The answer is lease_ms (the value the probe decided) and boot_id. **There is no
  resume**: an ended session does not continue with any request. The host opens a new session. Only when the open of a new session with a different ID succeeds is the resend state of §5.1 replaced. The ordering state remains after end and expiry.
- **lease_ms**: 0 is "the probe's default". The probe accepts a request of 1000 to 60000 ms as it is, and rounds values outside the range into the range (the default is
  decided by the probe). The lease_ms of the answer is within lease_min_ms to lease_max_ms (1000 to 60000). The host takes the answer's lease_ms as authoritative.
- **end**: releases the lock and everything the session made (§9). Lease expiry and force do the same.
- **keepalive**: only extends the lease.
- **lock_state**: whether the lock is held, and the remaining time (0 if the lock is free). locked means "the lock is held by some session" (lock_state can be sent without a
  session, so the probe does not know who asked; whether the host itself holds it, the host knows from its own state).
- **owner (an optional display function)**: with the open TLV 0x01 owner (text, 1 to 32 bytes, non-critical), the host MAY attach the holder's name (for example "flash-tool pid 1234").
  A probe need not implement keeping and displaying owner. A probe that does not implement it handles owner as an unknown TLV following §2.3, and ignores a non-critical owner.
  owner is not used for whether the lock is taken or for identifying the session, and the host does not treat its absence as failure. A probe that implements it takes owner from the open that sets the lock, remembers it while the lock is held (an open with the holder's id does not change it), and forgets it when the lock
  ends. While the lock is held, it attaches it after the answer of lock_state and the payload of rejected locked as
  TLV 0x01 owner (not attached if there is no owner). owner is only for display, and
  the probe does not interpret it. (Informative) owner can be read by any host with lock_state, so a host does not put secrets in it.
- **force**: takes the lock even if another session holds it. The probe releases the previous session's resources the same as at its end (§9) before
  handing over the lock. force is not authentication; it only prevents mix-ups.

### 6.5 boot_id

boot_id is a u32 the probe chooses so that it changes at every boot, and the same value is put in the answers of confirm (§7.1), clock (§7.6) and open.
The probe decides how it is generated, and a hardware RNG or non-volatile memory is not mandatory. It uses input that differs at each boot, and does not use a deterministic generation that repeats the same value, such as only a timer at a fixed point of the boot.
Collisions can happen, so the host accepts that possibility. 0 is an ordinary value too. When the boot_id changes, the host
considers that the session's resources (interface resources), the remembered fn mapping, resource numbers and stream positions have all become invalid.
A host that does not hold the lock (monitoring, discovery) learns of a restart with confirm or clock.
The invariance, monotonicity and non-reuse of numbers that this document describes as "while the boot_id stays the same" are contracts within one boot.
Even if the boot_id coincides by chance across boots, continuity of the same boot or of resources is not guaranteed.

The answer of open also has the boot_id: a host that compares it with the boot_id it knew learns of a restart at open, and redoes list before using the remembered fn mapping (§7.2).

## 7. Discovery

### 7.1 confirm

```text
Request: "OEP?", min_rev(u8), max_rev(u8), [TLV]
Answer:  "OEP!", revision(u8), max_frame(u16), window(u32), max_inflight(u8), boot_id(u32), [TLV]
```

- TLV 0x01 transport (u8): the index (§7.5) of the transport this confirm came on. The probe always attaches it. It points at the entry of the fn 0 describe returned on the same connection.

The host sends the range of protocol revisions it handles, and the probe returns the largest revision it handles within it. If nothing in the range can be handled,
rejected unsupported (below). max_frame is 64 or more ([transports](oep-transports.md) §3), window is max_frame or more, max_inflight is 1 or more. boot_id is §6.5 (the place to learn of a restart without the lock). Both request and answer fit in 64 bytes
([transports](oep-transports.md) §3).

- The headers (§4.1, §4.2) and fixed parts of the confirm request and answer, the magics `OEP?` / `OEP!`, and the rules before confirm (64 bytes, the frames of [transports](oep-transports.md) §1, [transports](oep-transports.md) §3) are the same in every protocol revision.
- The revision the probe chose applies to every message in both directions on **the transport that confirm came on**, until the next confirm on that transport. Each transport MAY work with a different revision. On TCP, a transport is each accepted connection ([transports](oep-transports.md) §1).
- After the first confirm on a transport, the host sends `min_rev = max_rev =` the revision in use in every later confirm there (recovery, probing again).
- When no revision in the range can be handled: rejected unsupported, with the payload tag 0x00 followed by TLV 0x01 supported (min(u8), max(u8): the range the probe handles). `min_rev > max_rev` is rejected malformed.

### 7.2 list

```text
Request: first(u16)
Answer:  total(u16), count(u8), count × entry
entry:   fn(u16), instance(u16), revision(u8), name_len(u8), name
```

- Returns the probe's interfaces from the first-th, as many as fit in one frame. total is the number of interfaces. The core (fn 0) has no name and so
  is not in list: the fn of an entry is not 0.
- A name is 1 to 48 bytes, of the characters `a-z 0-9 - .` (§12). An answer with one entry is 62 bytes even with a 48 byte name (header 5, total and count 3, the fixed part of the entry 6, name 48), and fits in every max_frame (64 or more).
- instance is a **u16 identifier** that tells apart interfaces with the same (name, revision). It is not duplicated within that pair. 0 MAY be used, and gaps are allowed. It is not computed from the fn order or the position in list.
  Across firmware updates of the same product, the instance of the same logical interface is kept. The number of a removed one is not reassigned to another logical interface (because saved settings point at categories by (name, instance), §13.1).
  The host resolves a saved pair from list, and treats it as not offered if not found. fn is the call destination while the boot_id stays the same, and is not used for saved identification after a firmware update.
  instance does not identify the connected target or the wiring. When several revisions are offered, the pair of each revision is chosen explicitly. Settings belong to the (name, instance) category regardless of revision (§13.1).
- The answer of list (which interfaces exist, their fn, instance, revision, name) does not change while the boot_id stays the same. A probe whose interfaces increase or decrease restarts (a new boot_id). The host MAY remember the mapping from names to fn while the boot_id stays the same.
- If first is total or more, the answer is total and count 0.

### 7.3 describe

```text
Request: fn(u16), first(u16)
Answer:  more(u8), a sequence of TLVs
```

Returns the declaration of fn, from the first-th TLV, as many as fit in one frame. If more = 1 there is a continuation, and the host adds the number of TLVs received to first
and asks again. The probe makes each TLV small enough that, with the answer header of 5 bytes and more of 1 byte added, it fits in the max_frame of every one of its transports (the TLV value is at most the smallest max_frame − 9 bytes; describe does not depend on the transport). fn 0 is the declaration of the whole probe.

**describe returns only declarations**: while the boot_id stays the same, the sequence and values of the TLVs do not change (the host MAY cache it while the boot_id stays the same, and paging does not break
even if settings change midway). Things that change (connections, whether there is a save, free capacity) are given by ops of the interface that return state
(no lock needed).
- **The end of paging** (common to lists whose pages are pointed at with first): if first is the count or more, it returns 0 elements and more 0
  (in an answer with a field for the number of elements, that field is 0). The host stops at more = 0. list has no more; its end is known from total (§7.2).
  The rules for lists pointed at by a serial number instead of first (records, segments and so on) are decided by the document of the interface that uses them.

### 7.4 Common describe tags (0x01 to 0x3F)

| tag | Name | Value |
|---:|---|---|
| 0x01 | role_channels | role(u8), base(u16), bitmap. If bit i is set, channel base+i can be used for that role. The same role MAY be written several times (union) |
| 0x02 | max_clock_hz | u32 |
| 0x03 | max_length | u16. The limit on the length a function handles at once (describe does not depend on the transport; the interface's document decides the unit). A request that exceeds it is rejected unsupported. Requests and answers additionally fit within that transport's max_frame (§4.4). An operation that cannot split a result received from outside declares, following that operation's definition, a value whose result can be carried on every transport |
| 0x04 | min_clock_hz | u32 |
| 0x05 | features | u32. Bits of optional functions that are not ops: modes, formats and so on (the interface decides the meaning). Optional ops are declared in ops, never in features |
| 0x06 | channel_group | group(u8), n(u8), n × (role(u8), channel(u16)). For a function with one or more groups, for the roles listed in any one group, the chosen set of channels MUST match it exactly. Roles not in a group follow the role_channels rule below |
| 0x07 | ops | base(u8), bitmap. If bit i is set, op base + i is present (§1.2). Attached by the describe of every fn, including fn 0 |
| 0x08 | setting | form(u8), key_kind(u8), keys(u16), max_len(u8), flags(u8), name (text). One per settings item owned by that fn (§13.2) |
| 0x09 | setting_choice | number(u8), value(u8), name (text). One per choice of an item of form enum (§13.2) |
| 0x0A | op_name | op(u8), flags(u8), name (text). One per op that gets a name (optional; "names and forms of ops" below) |
| 0x0B | op_field | op(u8), part(u8), type(u8), name (text). One per field of an op whose op_name flags set form (optional; below) |

The role numbers are defined by the interface. These values are fixed shapes; added information goes in new tags (§2.3).

- **The value of ops**: base(u8) and a bitmap of 1 byte or more. `base + 8 × the bytes of the bitmap ≤ 256` (the bitmap does not go beyond op 0xFF).
- **ops** examples: a riscv-dm fn that has all of ops 0x10 to 0x17 sends `07 02 00 10 FF`. One with only dmi, halt and resume (0x10 to 0x12) sends `07 02 00 10 07`.
  `F9 01` (going beyond op 0xFF) is not correct. To know whether an op exists, the host reads the bitmap, not features.

- A function that can be assigned to any pin lists candidates in role_channels, and a function with fixed pin sets writes channel_group as many times as there are sets.
  When both are written, the chosen set of pins MUST match one of the channel_groups and also be within the role_channels candidates.
  role_channels constrains only the roles it lists (a role not in role_channels is decided only by channel_group, and a role not in channel_group
  is decided only by role_channels).
  For example, when a group fixes roles 1/2 and role_channels lists only role 3, the match for roles 1/2 and the candidates for role 3 are checked separately.
- role_channels and channel_group declare the selectable pins for every way an interface chooses pins (assignment by another interface, request arguments).
  The role numbers, and in which way pins are chosen, are defined by the interface's document.

**Names and forms of ops** (op_name, op_field; optional): an interface MAY show in describe the names of its ops and the fields of the fixed parts of requests and answers.
A host can then choose ops by name, build requests from the fields and read answers without knowing the interface. The authority for the form is still the interface's name and
revision (§2.8). Changing a form raises the revision.

- op_name: op is an op set in ops. flags: bit 0 `form` (all fields of the fixed parts of that op's request and of its completed success and completed failed answers are
  shown with op_field; 0 fields is allowed), bit 1 `lock_free` (that op is accepted without the lock; §6). The other bits are 0.
  name is 1 to 24 bytes, of the characters `a-z 0-9 - _`. Unique within the same fn.
- op_field: op is the op of an op_name that set form. part is 0 request, 1 completed success answer, 2 completed failed answer. type is in the table below.
  name has the same characters and length as op names and is unique within the same op and part. The order in which op_fields of the same op and part appear in describe is the order of the fields of the fixed part.
- After the fields, as before, comes a sequence of TLVs (§2.3). An op with a form that fields cannot describe (a sequence of structures preceded by a count, a form that changes with content) does not set form.
  It shows only the name, and the host sends the request as bytes.
- The names and forms of the ops of standard interfaces are held by the registry. They MAY be shown, and then they are the same as the registry (if different, the registry is right).
- Value sizes: op_name up to 2 + 24 bytes, op_field up to 4 + 24 bytes. Both fit in a describe TLV of the smallest max_frame (§7.3).

| type | Name | Form (numbers little endian, §2) |
|---:|---|---|
| 1 | u8 | 1 byte |
| 2 | u16 | 2 bytes |
| 3 | u32 | 4 bytes |
| 4 | u64 | 8 bytes |
| 5 | i8 | 1 byte, two's complement |
| 6 | i16 | 2 bytes, two's complement |
| 7 | i32 | 4 bytes, two's complement |
| 8 | i64 | 8 bytes, two's complement |
| 9 | bool | 1 byte, 0 or 1 (a request with another value is malformed) |
| 10 | bytes | len(u16), len bytes |
| 11 | text | len(u16), len bytes of UTF-8 |

- Bit 7 of type is a sequence: `count(u16)` followed by count elements of that type (1 to 9). There is no sequence of bytes or text.
- Units such as time are recommended to be shown at the end of the field name (`_ns`, `_us`, `_ms`, `_hz`, `_samples`). Not normative.

### 7.5 Declarations of the whole probe (describe of fn 0, 0x40 and up)

| tag | Name | Value |
|---:|---|---|
| 0x40 | firmware | text. Optional version and diagnostic information |
| 0x41 | model | text. The name of the kind of probe (optional; does not change for a unit) |
| 0x42 | unit_id | The ID of the unit. **Mandatory**. text of 1 to 32 bytes, only the characters `a-z 0-9 -` (the chip's unique number in lowercase hexadecimal, for example). The host uses it to group the transports of the same probe, so every transport's describe returns the same value. The same as the USB serial number ([transports](oep-transports.md) §3). The value by which a host names a probe |
| 0x43 | channels | u16. The number of channels. Channel numbers are 0 to channels − 1. A probe with channels always attaches it; without it there are 0 channels |
| 0x44 | channel_name | channel(u16), text. The name of a channel. One per channel. A probe that attaches channels always attaches it (below) |
| 0x45 | netif | text. The name of a network port (the name list of §7.7). One per port. The meaning is defined by [transports](oep-transports.md) |
| 0x49 | transport | index(u8), kind(u8), interface(u8): for USB CDC (kind 2) the bInterfaceNumber of the CDC communication interface (the first interface of that function). For built-in USB serial (kind 3) that same number as the hardware shows it, or 0xFF if the probe cannot know it. For vendor bulk and HID the number of that interface. For UART bridge (kind 1) and TCP 0xFF. One per transport of the probe. **Mandatory** |
| 0x4C | chip | text. The part number and revision of the probe's MCU (optional) |
| 0x4D | max_op_ms | u32. The longest processing time from the probe starting the validation of one request itself, through internal retries, execution and cleanup, to building the answer. The time waiting for earlier requests on the same or another transport and the transfer time of the transport are not included. **Mandatory**. 1 to 600000 (`max_op_ms_max`, 10 minutes). A request whose explicit wait argument exceeds it is rejected unsupported (which ops is defined by the interface's document). The lease is not counted only while a new request of the owner is being processed (§6.1). The probe decides the value. The host waits as in §4.4 |

- Transport kinds: 1 UART bridge, 2 USB CDC, 3 built-in USB serial (a USB serial port the MCU's hardware has, for which the probe cannot choose the USB descriptors including the serial number), 4 vendor bulk, 5 HID, 6 TCP (registry `transport_kind`).
  1 to 3 are serial ports ([transports](oep-transports.md) §4). index is the number pointing at a transport within the probe (from 0); when a setting points at a serial port, the wire also uses this number.
  The number does not change only while the boot_id stays the same. Exports point at it by the transport's name (§13.3) (saving is §13.7).
- **Channel names**: the name the chip's datasheet uses for the pin (`GPIO14` of ESP32, `PA5` of CH32 and so on). 1 to 16 bytes of `A-Z a-z 0-9 _ -`,
  unique within the probe. The number is only for while the boot_id stays the same; exports point by name (§13.3; saving is §13.7). The name a pin is called by (`NRST` and so on) is not the name but
  the setting `channel.{}.label` (§13.8).
- **Uniqueness of unit_id**: unit_id is a different value for each unit (the chip's unique number and so on). `any` is not used (it expresses "any one" in a host address, [host guide](host-development-guide.md) §5.3). A probe that has storage but no unique number SHOULD make a unit_id from a random number at its first boot and save it.
  A probe with neither a unique number nor a saved random number uses a unit_id beginning with `x-` (not unique). A host does not group transports by a unit_id beginning with `x-`, does not name a probe by it, and does not use it as the key of anything kept across sessions (for example, the record of a port's link speed). This is so that another unit on the same port inherits nothing.
- **Invariance of unit_id**: unit_id is made only from values of the unit (the chip's unique number, a saved random number; only an `x-` unit_id is an exception), and does not change with the firmware version, profile, build or kind of transport.
  No suffix is added. Hosts and the OS remember the probe by unit_id (= the USB serial number, [transports](oep-transports.md) §3).

### 7.6 clock

```text
Request: —
Answer:  boot_id(u32), uptime_ns(u64), [TLV]
```

- clock returns the probe's current time. boot_id is the value of §6.5 (the same as in the answers of confirm and open), uptime_ns is the value of the clock of §2.7.
- clock is a read-only op that needs no lock (§6.3). It can be sent without a session: a clock with session_id 0 is processed without the session checks and
  touches no session, lock or lease (§4.1).
- uptime_ns is the value of its own clock that the probe read between receiving this clock request and sending the answer (no earlier read value or estimated value is put in).

### 7.7 Name lists

Choices the probe has, which the host chooses in a request, and to which others besides the standard can add (console mechanisms, network ports and so on),
are not numbered in the registry but declared by name (the same form as the relation between fn and list).

- The interface lists them in describe, one TLV with a name each, repeated. In requests and answers, the position in that list (from 1) is used as the number. 0 is not used as a number (it expresses "none", and does not overlap the mark 0x00 of the unsupported payload).
- Standard names are held by the registry (`a-z 0-9 -`, without `.`). Others' names are reverse-DNS names of §12 rule 1 (with `.`).
  The same name expresses the same meaning and the same value shape on every probe. The same name is not put twice in one list.
- The numbers do not change while the boot_id stays the same. The host looks up the number from the name, and looks it up again when the boot_id changes. The number is not remembered in place of the name.
- A number not in the list is refused following the definition of that request (usually unsupported).

## 8. Channel idle state

A channel (a probe pin, §1) is in the **idle state** when no interface has taken it. Pins are taken by operations defined by an interface's document
(pin assignment, wire connection, settings and so on).

- **Idle state**: if the setting `channel.{}.idle` (§13.8) decides the idle state of that pin, that state (for output low / high it drives that level
  following the setting's definition and does not make it Hi-Z); if not, **Hi-Z (input, no pull)**.
- A released pin, whichever way it was released (the release operation an interface defines, the cleanup at lease expiry and force of §9), is put in the idle state.
  An interface MUST NOT leave a pin under its own driving after release (if the idle state is an output, the driving is that of the setting's idle).
  The only exception is when an interface's definition defines **holding** after release (the debug wire, [wire and debug](../interfaces/oep-if-debug.md) §2).
  Holding is a kind of idle state: a pin without a setting idle is left driven in that interface's rest state. Taking it is handled the same as an idle pin
  (not refused because of holding), and whoever takes it inherits it. A definition that defines holding makes it readable that holding is in progress, and on a probe with settings makes it possible to turn it OFF by a setting.
- **At boot**, before answering the first request, the probe puts every channel in the idle state except the channels it uses itself and the channels whose setting `channel.{}.disable` (§13.8) is true. Until then the pins are in the MCU's reset
  state (informative: a line where a wrong level does harm needs an external pull).
- **Taking a pin does not change the pin's electrical state.** A pin keeps its idle state until the interface that took it starts using it. Which operation starts using it is defined by
  each interface's document. An interface that only reads pins never changes them: it does not stop outputs, and does not change the pull or
  direction of pins driven by other functions or by an output idle.
- A request that takes a channel whose idle is an output is refused with unavailable (cause 5), unless that interface explicitly states taking it.
  An interface that allows taking also keeps the idle state when taking. A read-only taking does not change the driving.

### 8.1 Resource contention

- Everything that takes probe resources (pins, peripherals, DMA, timers and so on) checks, before taking, that it does not collide with the current pin assignments, runtime resources, use restrictions of settings, or output idles that the rule above does not allow taking. If it collides it refuses with rejected unavailable and **changes nothing in the state of the current functions**.
  Things that take: operations an interface defines that take pins or resources (pin assignment, wire connection, settings, operations that make resources).
- When configure / attach / start and so on increase resource use, it also checks that the declarations and accepted time conditions of existing functions and the new function can be kept at the same time.
  If the concurrent resources or processing capacity are not enough, it refuses with unavailable (cause 2) before any side effect. The capability to run every fn at the same time is not required.
  Pin contention stays cause 1, prohibition by a setting cause 5, and a state that cannot be operated cause 6.

## 9. Resource lifetime (general rules)

**Every runtime resource is owned by the session that made it.** When the lock is lost by end, lease expiry or force,
all of that session's resources and subscriptions are released. Dependent resources are released first, and the pins are returned to the idle state last.
Resources are not handed over to a new session. Persistent settings do not own runtime resources.
Whether there are settings that take effect independently of sessions, and their effect, is defined by the owner of the item (§13).

| Event | Runtime resources | Subscriptions | Resend state |
|---|---|---|---|
| end / lease expiry | All released | Ended | The ordering state of the last session and the byte records being kept remain (§5.1) |
| force open with another ID | All previous resources released | Ended | Replaced when the new open succeeds |
| A new open with the same ID (while held) | Remain | Remain | Remain |
| A resend of the identical open | Unchanged | Unchanged | Return the kept answer. result_lost if not kept |
| Restart | Invalid (the boot_id changes) | Invalid | Invalid |

- Resource numbers are u32, one space for the whole probe. 0 is not assigned; they increase from 1.
  **While the boot_id stays the same, even closed numbers are not reused.** When 0xFFFFFFFF has been used up, making new resources is refused with rejected unavailable (cause 2).
  Existing resources can still be used. To return the numbers to 1, restart and change the boot_id.
  That an old number does not point at another resource is guaranteed even for reads without a session. No history table of closed numbers is needed; keeping only the next number and the resources in use is enough.
- A closed resource number or a number that does not exist is rejected no_resource. A resource of a kind or creator that the operation is not defined to use is rejected unavailable (cause 6).
  When a definition states that it uses resources made by another fn, that mapping is followed (a connection whose creator and user are different fns and so on). Being another fn alone is not a reason to refuse, and resources without such a mapping are not shared implicitly.
- A request whose creation failed returns no usable number or resource. A number that failed after only being reserved MAY become a gap.
- The connected party is always specified by the request's fn and resource number. A "current target" or the last attached target is not used implicitly.
  One session MAY use several connections and fixtures. The set of dependent connections and pins is stated explicitly in each interface's requests.

## 10. Notifications

The mechanism for notifications sent from the probe. Whether notifications are sent is decided by the interface: an interface that sends them sets subscribe and
unsubscribe (§10.3) in that fn's ops. What arrives (event kinds, the meaning of data) is decided by that interface's document. A host receives nothing unless it
subscribes. §10.1 applies to every host; §10.3 and §10.4 apply to probes that have an interface that sends notifications.

### 10.1 Obligations of the host (every host)

- Sort received frames by role. Only role 0x02 is matched by corr (bytes 1 to 2 of 0x03 / 0x04 are fn).
- Discard frames with an unknown role and answers with a corr not being waited for.
- Even while notifications keep arriving, make sure the processing that waits for answers and the processing that reads reception finish by their deadlines.

### 10.2 Shape

```text
data   role=0x04 | fn(u16) | seq(u16) | position(u64) | len(u16) | data | [TLV]      header 5 bytes
event  role=0x03 | fn(u16) | seq(u16) | kind(u8) | fixed part | [TLV]               header 6 bytes
```

- The shape of the data payload is common to all interfaces: `position` is the stream position of the start of this frame (the interface decides it),
  `len` is the length of data, and TLVs follow (§2.3). The fixed part of an event is decided per kind by the interface, and TLVs follow.

- **Padding (data tag 0x7E)**: in the data of every interface, TLV tag 0x7E is reserved for padding. The value is any bytes of any
  length and has no meaning. A probe MAY put it to align frame lengths or positions, and MAY repeat it. A host skips it.
  An interface gives data tag 0x7E no other meaning.

- `seq` is the serial number of frames per fn (u16, wrapping; common to data and events). It counts from 0 at each subscribe. A gap means
  frames were lost. The probe numbers every event that arose, and ones discarded within the probe also consume numbers.
- fn 0 sends no notifications.

### 10.3 Subscription

subscribe and unsubscribe are ops of the interface that sends the notifications. **The op numbers are the same in every interface and are reserved in the op space of every
interface**: 0x01 subscribe, 0x02 unsubscribe. An interface does not use these 2 numbers for other ops.
The request does not carry the fn to subscribe to (it is a request to that fn itself, and the header's fn is the target).

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x01 | subscribe | min_bytes(u16), max_delay_ms(u32), [TLV] | — | Needed |
| 0x02 | unsubscribe | [TLV] | — | Needed |

- When notifications are provided, both subscribe and unsubscribe are present and set in ops. Whether the notification function itself is mandatory or optional is decided by that interface's document.
  (Informative) A relaying broker can recognize subscriptions by these numbers in requests to any fn and refuse them.
- **Only the lock holder can subscribe, and a subscription ends together with the lock** (end, expiry, taken by force). Read-only monitoring uses a read that needs no lock.
- unsubscribe on a fn without a subscription does nothing and succeeds.
- Subscribing to the same fn again atomically replaces the previous subscription (sending conditions, destination transport, seq from 0). There is only one subscription
  per fn.
  On replacement or cancellation, unsent notifications of the old subscription are discarded. A frame already being sent completes before the answer of the operation returned on the same transport (§10.4).
  An answer on another transport does not wait for the frame on the old transport to complete. What remains to be sent on a closed transport is discarded and not carried over to a new transport ([transports](oep-transports.md) §3).
- A probe MAY limit the amount retained for subscriptions. If the retained amount is not enough to meet the sending conditions of the requested data, it refuses with rejected unavailable (cause 2) without changing anything.
  The conditions of a successful subscription are not silently rounded. When a request that replaces an existing subscription is refused, the previous conditions, destination and seq are also kept.
- **The batching conditions apply only to data (role 0x04)**: send when min_bytes bytes have accumulated or max_delay_ms has passed since the first byte. 0
  means that condition is not used. If both are 0, send whatever there is at once: as soon as sending becomes possible, send whatever there is. What accumulated
  while the transport was blocked by a previous send MAY be put together in one frame (this does not make it arrive late; the combined result does not exceed max_frame either).
  Unsent data at the moment the condition is met MAY be split into several frames to fit max_frame, and min_bytes is not reapplied to the rest.
  min_bytes is not the minimum data length of one frame. The start of sending follows the answer priority of §10.4, and max_delay_ms does not override that priority.
- **Events (role 0x03) are not batched**: an event that arose is sent as soon as the answers to send before it (1 of §10.4) have been sent. min_bytes and max_delay_ms
  do not apply to events, and the bytes of events are not counted toward min_bytes.

### 10.4 Obligations of the probe (a probe that sends)

1. **Send answers first.** Process all requests that have arrived before starting to send a new notification frame.
   No other answer or notification is inserted into a frame already being sent on the same transport; that frame is completed before sending the next answer ([transports](oep-transports.md) §2).
2. **Keep partly sent notifications small.** Do not accumulate partly sent notifications in the transport's send buffer beyond max_frame × 2 bytes,
   and do not wait on writing. This value is a limit, not an obligation to allocate a queue of that size. Notifications that do not fit are discarded within the probe before they start to be sent (visible as a gap in seq, §10.2).
3. Notifications are sent to the transport on which that fn's subscribe came.

## 11. Operations of the core (fn 0)

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x01 | confirm | §7.1 | §7.1 | Not needed | Mandatory |
| 0x02 | list | §7.2 | §7.2 | Not needed | Mandatory |
| 0x03 | describe | §7.3 | §7.3 | Not needed | Mandatory |
| 0x04 | clock | — | boot_id(u32), uptime_ns(u64), [TLV] (§7.6) | Not needed | Mandatory |
| 0x10 | open | lease_ms(u32), force(u8), [TLV owner] (the session_id is the header's) | lease_ms(u32), boot_id(u32), [TLV] | open takes the lock | Mandatory |
| 0x11 | end | — | — | Needed | Mandatory |
| 0x12 | keepalive | — | — | Needed | Mandatory |
| 0x13 | lock_state | — | locked(u8), remaining_ms(u32), [TLV owner] | Not needed | Mandatory |
| 0x20 | get | §13.5 | §13.5 | Not needed | Mandatory if it has settings |
| 0x21 | set | §13.5 | §13.5 | Needed | Mandatory if it lets values change (paired with unset) |
| 0x22 | unset | §13.5 | §13.5 | Needed | Mandatory if it lets values change (paired with set) |
| 0x23 | save | §13.7 | §13.7 | Needed | Optional (paired with state) |
| 0x24 | state | §13.7 | §13.7 | Not needed | Mandatory if there is save |
| 0x25 | network | [transports](oep-transports.md) §7.3 | Same | Not needed | Mandatory if describe has netif |


## 12. Extension rules (how to write an interface)

Every interface is defined by the following rules.

This is the common contract that applies to all of standard OEP and to third-party extensions.
The OEP [common parts](../interfaces/oep-if-common.md) apply additionally only when adopted. There is no obligation to implement streams, connections, notifications, pins or plans that are not adopted.
The smallest extension needs only a name / revision and one specific operation or one settings item (§13). It can be discovered by list and the describe/ops of fn 0, and follows the rules below for fixed shapes, failure, lock and version.
An extension that uses pins chooses in its own definition between per-fn assignment (plan and so on) and arguments of the request that makes a resource, and states the taking and releasing.
The OEP plan scheme is not uniformly required of third-party extensions.

1. **Name**: an interface's name is the reverse-DNS name of whoever defines it (`io.github.<owner>.<name>` and so on). Anyone who extends OEP uses this.
   The only exception is the project's own interfaces, which use the reserved short prefix `oep.` instead of a reverse-DNS name: `oep.<layer>.<name>`, where the layer is `probe` (the probe itself),
   `wire` (wires and connections), `target` (target operations over a connection) or `fixture` (fixture functions). Apart from this short name, there is nothing special about them.
   Names beginning with `oep.` are given only by the project. Names are cut by what the host uses them for (not named after the probe's peripherals). Whether something is generic or for one family is
   not put in the name (rule 8). **1 to 48 bytes, of the characters `a-z 0-9 - .`** (registry `limits`; the length at which a list entry fits in one frame, §7.2).
   Each label of a name is one or more characters of `a-z 0-9 -`, and does not begin or end with `-`. A name has 2 or more labels.
2. **What the definition decides**: every interface document fills in the following checklist.
   - Name and revision.
   - The op table: numbers, requests, answers, whether the lock is needed, which ops are mandatory and which optional (optional ops are declared in ops, §1.2).
   - The request and answer TLVs of each op (the tag space of that op's context).
   - The completed success, completed failed and completed partial payloads of each op (§4.2).
   - The interface's own status, reject reasons and unavailable causes (each 0x40 to 0x7F).
   - The interface-specific describe tags (0x40 to 0x7E) and the pin role numbers.
     The conditions under which mandatory declarations fit on every transport, and under which requests / fixed results fit in the frame of the requesting transport (§4.4/§7.3).
     describe paging does not split a TLV value. Unsplittable results of external reception follow the individual definition.
   - Which target family it is for (rule 8; one used for any family says so).
   - The resources the interface makes and their lifetimes (on top of §9).
   - Whether it sends notifications. If it does, declare and implement subscribe / unsubscribe (§10.3), and the event kinds (0x01 to 0x7F) and their payloads,
     and the shape of the data payload of notifications.
     For a function whose data generation ends, also define how the remainder below the sending conditions is handled, and how the end is decided including losses.
   - How the reader handles unknown values of answer enums and unknown flags (§2.4, §12.1).
   - If it has settings items, their names, form, key, flags, initial values, semantic validation and when they take effect (§13).
   - The external specifications it relies on, their versions and the parts used (a "referenced specifications" section).
3. **Shape rules**: as in §2.3 (fixed shapes, additions only as TLVs, a count before variable sequences and no length on elements, no omittable fields, safety arguments critical).
4. **Failure**: what was not accepted is rejected; what was accepted and failed is completed failed / partial (§4.2).
5. **Ops without the lock do not change state** (§6.3).
6. **Version**: §2.8.
7. **No numbers (op, tag, enum value) are added to an interface under someone else's name.** Only whoever owns the name assigns numbers (the project for `oep.` names, §2.5).
   Others can add only where things are identified by name:
   - Named extension TLVs (§2.2, tag 0x7F): add information under your own name to requests, answers, events, data and describe (example: adding a probe-specific strength to a standard output).
   - Name lists (§7.7): add choices under your own name to choices an interface declares by name (example: a third-party console mechanism).
   Settings items are identified by name, but are not added to a category under someone else's name (§13.1). Your own settings go in an interface under your own name.
   - An interface under your own name: a new function (offered as a separate fn).
   Each of these is only skipped (non-critical) or refused (critical) by a host that does not know the name, and does not change standard behaviour.
   Anything that needs to change standard behaviour is not done here; the owner of that name extends the definition.
8. **Procedures for specific chips are not put into generic interfaces.** Procedures specialized for a chip or family (how to write flash, reset timing and so on;
   things whose timing cannot be met unless the probe does them) are put in a separate interface for that purpose.
   Which family it is for is not put in the name, but written at the head of the interface's document and, for names beginning with `oep.`, in the registry (the interface's `target`)
   (because the name is a permanent identifier, and how widely it is used changes over time). **An interface used for any family does not contain processing for
   specific chips.** Specialized things lower portability (hosts that use them are tied to probes with that function, and supporting a new chip needs an update of the probe's
   firmware). What can be done with generic procedures (raw transfers and the host's knowledge) is built that way.
   **Decisions belong to the host as a rule.** However, for things where checking and correcting the connected party from the host would be too late (things involving timing and so on),
   the definition for that family can put an automatic decision in the probe. A definition that puts an automatic decision (a) returns to the host, in an answer or a list, what was chosen (so that it can be seen that an automatic decision
   was made), (b) gives priority to the host's explicit specification, (c) on a probe with settings makes it possible to turn that decision OFF by a setting, and (d) puts the target table used for the decision in
   the registry (example: the rvswd wire rest of debug §3.1).

### 12.1 How OEP grows

After the freeze, OEP grows only by these:

1. **New TLVs**: in requests, answers, events, data and describe. New standard names in name lists (§7.7).
2. **New optional ops** (declared in ops, §1.2) or **new event kinds**.
3. **New values in reserved spaces**: values in requests that old probes refuse with unsupported (§2.5), or values in
   answers under the conditions below.
4. A **new interface name** for a new meaning, a **new revision** for a changed fixed shape (§2.8).

The core can define new optional common operations in the range only for common operations (§2.5), and can also define new transport kinds and their frames (§3).
A change to existing contracts or to the shape of the core raises the protocol revision (§2.8). When the old revision is also offered, its contract is kept (§7.1).

To add information to the elements of a sequence, a repeatable answer TLV carries the element's index.

**Value widths**: choose a width that holds the range, unit and reserved values of the defined value. Even for values that come from hardware, u8 / u16 MAY be used if a limit can be defined.
Values are not truncated to a narrow width, and values beyond the limit are not wrapped. The unit and range are stated in the interface's document.
Example: the number of elements of a page is expressed as u8, and a UART baud as u32. How an unsupported range is refused follows the definition of that op.
Changing the width or unit of an already defined fixed part is a new revision. If a wide range is needed, choose a wide width from the start, or add a new TLV / operation later.
A set of bits uses the width the existing definition chose or `base + bitmap`, and a new definition decides the number of bits needed and how to extend.

**Values added to answers.** An enum value carried by an answer, event or data, or a bit of a set of bits, MAY be added without changing the revision only when all 3 of the following hold:

1. The presence, length and position of every field do not depend on that value.
2. The handling of §2.4 is safe (an unknown outcome, status or reason is failure, others are "unknown values", reserved bits are ignored).
3. Every field whose meaning depends on that value is defined to be ignored or shown raw by a reader that does not know that value.

Otherwise, what is added becomes a new TLV, a new revision or a new interface. Every answer enum and set of bits of revision 1 meets the 3 conditions.

## 13. Settings (optional)

Settings are values the probe keeps across boots (pin names and idle states, network destinations, how interfaces rest and so on).
The core coordinates and saves them all together. Deciding items and checking and using the meaning of values is done by the owner of the item.
Both the settings mechanism and saving are optional. A probe without the settings mechanism treats every channel as in the Hi-Z idle state (§8).

Runtime state (plan, connections, UART configure and so on) is not settings. It is stated explicitly with interface ops and not put in settings.

### 13.1 Categories and items

- **Categories**: settings are divided into categories per owner. There are only 2 kinds of category: the core (fn 0, no name) or an interface (name and instance, §7.2).
  Settings of the probe's maker (host name and so on) are put in an interface under that maker's name (a settings-only interface is fine, §12).
  On a probe that offers the same (name, instance) in several revisions, only one of those fns declares the items (the category does not depend on revision).
- **Items**: an owner defines and names items only in its own category. Others do not add items to someone else's category.
  The owner of an item is decided by its category, so item names make no distinction between "standard or someone else's".
- **Item names**: labels of `a-z 0-9 -` joined by `.` (the labels have the same form as §12 rule 1). An item with a key puts exactly one `{}` in place of a label where the key goes
  (`channel.{}.label`). 1 to 48 bytes.
- **Values**: there are 0 or 1 values per (category, item, key). One value has one form (§13.3). A compound value (an address and prefix and so on) is split into a separate item per field.
- **The meaning of a name does not change**: an item with the same name in the same category expresses the same meaning, the same form and the same use of keys across firmware versions and interface revisions.
  To change the meaning, use an item with a new name. Exports hold items by name, and saves SHOULD also hold them by name (§13.7, [settings file](oep-settings-file.md)).
- **What the owner decides**: the item's name, form, kind and range of key, flags, initial value (§13.4), semantic validation of the value (a value the definition excludes is malformed, a value the probe cannot handle is unsupported, §4.3), when the value takes effect, and whether it may be changed (§13.6).
  **What the core decides**: form validation (§13.3), the read and write operations (§13.5), the generation, saving (§13.7).
- The owner holds the values in memory and uses them. The owner does not change values other than through the operations of §13.5. Using a value is not a settings read or write and does not go through the permission check of §13.6.

### 13.2 Declaration

Items are listed in the describe of the owner's fn (the core's items in the describe of fn 0). describe shows only what exists; values are read with get of §13.5.

| tag | Name | Value |
|---:|---|---|
| 0x08 | setting (common) | form(u8), key_kind(u8), keys(u16), max_len(u8), flags(u8), name (text). One per item. The k-th setting is item number k (from 1) |
| 0x09 | setting_choice (common) | number(u8), value(u8), name (text). One per choice of an item of form enum |

- The same name of setting is not put twice in one fn. Item numbers do not change while the boot_id stays the same. The host looks up the number from the name, and looks it up again when the boot_id changes.
- form, key_kind are in §13.3. keys is the number of keys for key_kind index (1 or more), and 0 for other key_kinds. max_len is the maximum length for form bytes and text, and
  0 for other forms. flags: bit 0 **secret** (§13.5), bit 1 **restart** (the new value takes effect after a restart; get returns the new value). The other bits are 0.
  When the value of an item without restart takes effect is decided by the item's definition.
- max_len is a value such that a get answer and a set request with one value of that item fit in the max_frame of every transport of the probe (at most the smallest max_frame − 18; §13.5).
- The value of setting is 6 + the length of the name, 54 bytes even with a 48 byte name, and fits in a describe of a 64 byte max_frame (§7.3).
- setting_choice: number is the item number in that fn, value is the wire value of that choice, name is 1 to 16 bytes of `a-z 0-9 -`. Neither value nor name repeats within the same item.
  A value without a setting_choice cannot be used for that item (unsupported).

### 13.3 Forms and keys

| form | Name | Wire data | Export (JSON) |
|---:|---|---|---|
| 1 | bytes | 0 to max_len bytes | A lowercase hexadecimal string |
| 2 | text | text of §2.1, 1 to max_len bytes | A string |
| 3 | u32 | u32 | A number |
| 4 | ipv4 | 4 bytes, `a.b.c.d` from a | `"a.b.c.d"` |
| 5 | bool | u8 (0 or 1) | A boolean |
| 6 | enum | u8. One of the setting_choice values | The choice's name |
| 7 | channel | u16. A channel number | The channel's name (§7.5) |
| 8 | transport | u8. A transport index | The transport's name (below) |
| 9 | fn | u16. A fn in list | `"name/instance"` |

| key_kind | Name | Wire key (u16) | Export name |
|---:|---|---|---|
| 0 | none | 0 | — (no `{}` in the name) |
| 1 | channel | A channel number | The channel's name |
| 2 | index | 0 to keys − 1 | A decimal number (`0`, `1`) |
| 3 | transport | A transport index | The transport's name |
| 4 | netif | The position in the netif list of the fn 0 describe (from 1, §7.7) | The netif's name |

- **The wire carries numbers valid only during a boot, exports carry names**: channels, transports, fns, netifs and choices are carried as numbers on the wire and held as names in exports. Saves (§13.7) SHOULD
  also hold names. The core converts between the two. A value whose name cannot be looked up to a current number at boot is not used.
- **Transport names**: the short name of the kind (1 `bridge`, 2 `cdc`, 3 `usj`, 4 `bulk`, 5 `hid`, 6 `tcp`) joined with the position among transports of the same kind in increasing order of index
  (from 0) (`cdc0`, `bridge1`).
- **Form validation**: if the length of data does not match the form, malformed. A bool of 2 or more is also malformed. For text only the length is checked (not the content; the host replaces as in §2.1 when it shows it).
  A value not in the setting_choice of an enum, a channel of channels or more, a transport that does not exist, and a fn not in list are unsupported. A key outside the range of the key_kind is unsupported.
  Even within the range, if the owner puts no item at that key (it cannot be used on that channel, and so on), unsupported.

### 13.4 Initial values

Values do not carry where they came from. get, set, unset, saving and export handle every value the same.

- An owner MAY have an initial value (a value the firmware provides) per key of an item.
- At a boot without a save (every boot on a probe without saving; on a probe with saving, a boot with storage_state 0 or 2, §13.7), the core
  puts the initial values through the same validation as set (§13.5, §13.8). An initial value that does not pass is a firmware error and is not put.
- At a boot that used a save, initial values are not put (not even if the save is empty, nor for items not in the save). It cannot be told whether a value not in the save is "one the user unset" or
  "one the firmware newly added", and the value the user removed would come back. To use initial values added by a firmware update,
  the host sets the values.
- There is no op that returns to the initial values. The host unsets the values and sets them again (the same as importing a [settings file](oep-settings-file.md)).
- A probe with values the user should not change (a fixture and so on) is configured without saving. Changes return to the initial values at restart.
  A probe that lets no value change at all (initial values only, a complete preset) does not have set and unset (§13.5). To refuse per item, §13.6.

### 13.5 Operations

The settings operations are optional ops of fn 0 (§11).

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x20 | get | first(u16), [TLV] | more(u8), generation(u32), count(u8), count × value, [TLV] | Not needed | Mandatory if it has settings |
| 0x21 | set | count(u8), count × value, [TLV] | generation(u32), [TLV] | Needed | Mandatory if it lets values change (paired with unset) |
| 0x22 | unset | count(u8), count × (fn(u16), number(u8), key(u16)), [TLV] | generation(u32), [TLV] | Needed | Mandatory if it lets values change (paired with set) |
| 0x23 | save | [TLV] | generation(u32), [TLV] | Needed | Optional (paired with state) |
| 0x24 | state | [TLV] | storage_state(u8), saved_generation(u32), reason(u8), [TLV] | Not needed | Mandatory if there is save |

```text
value:  fn(u16), number(u8), key(u16), len(u16), data (len bytes)
```

- The values of a probe without set and unset are decided only by the initial values (§13.4) and cannot be changed. The host learns this from the ops of fn 0 (§7.4) and does not send changes.
- fn is the fn of the item's owner (0 for the core), number is the item number in that fn (§13.2). A fn not in list is unknown_function. number 0 is malformed.
  A number not among that fn's settings is unsupported.
- **get** orders every (fn, number, key) that has a value by increasing fn, number, key, and returns from the first-th as many as fit in one frame.
  A value is not split. If first is the count or more, more 0, count 0. If more 1, the host adds the received count to first and continues.
  Pages with the same generation express the same content. If the generation changes midway, the host reads from the start.
- **set** replaces the value per (fn, number, key) and keeps values not sent. **unset** removes the specified values. unset where there is no value does nothing.
  Overlapping identical (fn, number, key) within one request is malformed. count 0 does nothing.
- **Accept all together, or do nothing**: for all values of a set or unset request, the probe checks, before changing anything, the form (§13.3), permission (§13.6), the owner's semantic validation,
  contradictions in the whole settings after the change, the amount it can hold, and collisions with running resources. If even one does not pass, it refuses without changing the settings, generation, pins or
  running resources. If all pass, it hands everything to the owners and advances the generation by 1. The TLV item (u8, the position of the value in the request, from 0) in the refusal's payload
  MAY show which value. A change that cannot be held is refused with unavailable (cause 2 or 3).
- **generation** is not a digest of the content but the number of changes within the same boot. It is 1 at boot (1 even after reading a save). It advances by 1 for each set and unset that actually changes the content.
  0 is not used. A change at 0xFFFFFFFF is refused with unavailable (cause 2), and it does not go back until restart. A set or unset that does not change the content succeeds. Then the probe
  SHOULD not change the generation and not reconfigure pins. The host compares only for equality, so a generation that advanced needlessly only causes a reread.
- **secret**: the value of an item with the secret flag is write-only. get does not return its data (len 0). Whether there is a value is known from the value appearing in get.
  len 0 in set keeps that value as it is (malformed if there is no value). So sending the values of get back to set as they are changes nothing. The value of a secret item
  cannot be 0 bytes (to remove it, unset). A probe does not put a secret value in any answer, event or log, and does not let it be read with any permission. A host also does not display secret values and
  does not write them to logs. OEP does not encrypt values, so secret values are sent over a trusted transport (USB and so on, [transports](oep-transports.md) §1).
- **Frame size**: a get answer with one value is 18 + len bytes (header 5, more 1, generation 4, count 1, the value's fixed part 7), and a set request is also 18 + len bytes
  (header 10, count 1, the value's fixed part 7). With the max_len rule of §13.2, every value can be carried in one request and one answer.
- The [TLV] at the end of a request is as in §2.3 and does not apply to the data of values.

### 13.6 Permission to change

- For each value of set and unset, the core asks its owner whether the change is permitted. The owner MAY refuse by looking at the situation of the request (transport and so on), and
  MAY always refuse items or keys the user is not to change (the label of a port that has only an initial value, and so on).
  To refuse, it sends rejected unavailable with cause 7 (§4.3). Permission for the core's items is decided by the probe.
- The core defines no authentication (§0). Permission for settings, like the optional policy decision of §4.3, follows a policy defined by the transport or an extension. A probe without a policy accepts every change from the session
  holding the lock.
- get and state are not refused except by the policy decision of §4.3. secret (§13.5) cannot be read under any policy.

### 13.7 Saving and booting

A probe with saving sets save and state in its ops. The probe chooses the internal format, CRC and location of the save. It has, however, the following properties.

- **No applying to another value**: a saved value is not applied to an item, key or channel other than the one it was saved for.
- **Held by name** (SHOULD): a save holds values by category (the core, or an interface's name and instance), item name, key name (§13.3) and value (references by name),
  in a form readable across firmware versions. Other saves become a save that cannot be read when the firmware changes (storage_state 2), or unusable values (reason 2).
- **save** is an explicit operation and writes all current values. If the same content is already saved, it SHOULD not rewrite it (to reduce the number of rewrites of the medium). Whether it is already saved is
  not decided by the generation alone. Whether save succeeds or fails, it does not change the current settings, generation or pins. All processing of saving finishes within max_op_ms (§7.5).
  A save that does not fit in the amount of storage is refused with unavailable (cause 3) before changing anything.
- **Power loss**: something written only partway is not treated as a complete save. A save broken by power loss is not used at all (the pins come up in the idle state of §8).
  If it cannot be confirmed that what remains is complete, storage_state 2, reason 1. If nothing remains and it cannot be told apart from having no save, storage_state 0 is fine
  (either way nothing is used, and the host imports again from the exported file). It SHOULD be ensured that wherever in the writing the power drops, either the complete save before the update or the new complete save
  remains (if there was no save, either still none or the new complete save).
- **Boot**: after the owners have declared their items, the core reads the save and uses only the values that fit declared items, looking up names to current numbers and passing the owners' validation.
  Undeclared items, names that cannot be looked up and values that do not pass validation are not used (other values are used value by value). Unused values disappear at the next save
  (since save writes only the current values). It is fine to remove them because the host can export the settings and import them again ([settings file](oep-settings-file.md)).
- **Boot order**: the core's channel items (§13.8) take effect before any interface's values, in the order disable, idle, and then the idle state of §8 is made.
  When the amount that can be held is smaller than the save, disable values are used before any other value. The rest SHOULD be used, as far as possible, in the order idle, other core items, interface items,
  and within the same item in key order.
  Invalid values are not reinterpreted as another channel or another value.
  When the labels of a save violate the uniqueness rule (§13.8) (saved by firmware from before the rule and so on), only one of the overlapping labels is used,
  and the others are not (storage_state 3, reason 2). Which one is used SHOULD be the one with the smallest channel number.
- **Erasing**: there is no op that erases the save. The host unsets all values and saves (save writes only the current values, so old unused values also disappear here).
  A save of empty settings is also a save, and the next boot does not put initial values (§13.4).
  Initialization by physical means (a button, rewriting firmware) is outside OEP.
- A probe without saving MAY also have get, set and unset in memory. The values disappear at restart and return to the initial values. The host imports again from the exported file.

The answer of **state**:

| Field | Meaning |
|---|---|
| storage_state | 0 no save, 1 the whole save could be used, or save was done, 2 the save cannot be read (its form or completeness cannot be confirmed; nothing is used), 3 only part of the save could be used |
| saved_generation | If storage_state 1, the generation whose content was the same as the save (1 at boot, the current generation on a successful save). Otherwise 0 |
| reason | 0 none, 1 the form or completeness of the save, 2 unusable values (undeclared items, names that cannot be looked up, values that do not pass validation), 3 not enough amount that can be held |

- When save succeeds (including when the content was the same and it did not rewrite), storage_state 1, saved_generation is the current generation, reason 0. Even if later set and unset change the content,
  saved_generation does not change.
- If an accepted save cannot finish writing or verifying, completed failed (partial is not returned). The fixed part of the answer is the same for success and failure. state shows the condition of the save
  confirmed after the failure: the values before the operation if the save before the update remains as it was, 0 if it is confirmed there is no save, storage_state 2, reason 1 if completeness cannot be confirmed.
  A medium failure is not confused with the power loss rule, and an unreadable save is not used silently.

### 13.8 Items of the core

Items of the core's category (fn 0). A probe that has channels and settings declares the channel items.

| Name | form | key_kind | Meaning |
|---|---|---|---|
| `channel.{}.label` | text (1 to 32) | channel | The name a pin is called by (`NRST`, `V003.swdio` and so on). The probe does not drive lines by this name |
| `channel.{}.idle` | enum | channel | The idle state (§8). Choices: 0 `hi-z`, 1 `pull-up`, 2 `pull-down`, 3 `low` (output low), 4 `high` (output high) |
| `channel.{}.disable` | bool | channel | If true, the probe neither drives nor configures that pin |

- **label is unique within the probe**: if, in the settings after the change, the labels of 2 channels are equal ignoring ASCII case, set is refused with unavailable (cause 5).
  A label keeps the case as written, and get returns it as it is. Only when comparing are A to Z folded to a to z (characters outside ASCII are not folded).
  The rule that a label of the form `S.N` names a port is used by the host ([host development guide](host-development-guide.md) §5.3). The probe does not check that form.
- A channel the probe uses itself has no channel items (a set of that key is refused with unsupported).
- **disable** takes effect before the idle state at boot and on release. It does not widen the declarations. A request that uses a disabled channel is unavailable (cause 5).
  A set that disables a channel in use is unavailable (cause 1). If the settings after the change have both idle and disable (true) for the same channel, it is refused with unavailable (cause 5)
  (unset the conflicting value first). A channel whose disable was unset or made false is returned to the idle state at once.
- A change of **idle** takes effect at once on an idle channel, and on a channel in use the next time it becomes free. A channel without a value is Hi-Z. The probe decides the output strength.
  Choices for states the probe cannot make are not listed in setting_choice. Whether a channel with an output idle can be taken follows the definition of the taking interface (§8).
- The items of network transports (the Wi-Fi destination, how IPv4 is decided) and the op network (0x25) that reads their condition are defined by [transports](oep-transports.md) §7.
- Interface items are defined by their own documents.

## 14. Non-normative documents (guides)

These add no rules.

- [Getting started](getting-started.md): the smallest probe and host, with bytes.
- [Host development guide](host-development-guide.md), [probe development guide](probe-development-guide.md): implementation practice.
- [Conformance](conformance.md): checklists for probes and hosts.
- [Safety and security](security.md), [glossary](glossary.md), [versions and stability](versioning.md).
