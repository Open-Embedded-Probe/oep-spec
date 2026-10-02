# Open Embedded Probe — the protocol core (OEP core) v1

[日本語](oep-core.ja.md)

Status: **normative** (candidate for fixing v1, 2026-09-26. Reflects the [zero-base re-examination](v1-zero-base-proposal.ja.md) (Japanese) of 2026-10-01). This document defines only the protocol core of OEP. The standard interfaces
(wire, debug, console, fixture, capture, probe settings) are defined by their own documents (§14). The reasons for the decisions and the records of experiments are
kept in non-normative documents (§15). Where this document and a non-normative document disagree, this document is right.

The only definition of the numbers (op, tag, reject reason, status, enum) is `registry/oep-v1.toml`; the tables in this document are copies of it.
Where they disagree, the registry is right and the document is corrected.

## 0. Scope and layers

OEP consists of 3 layers.

| Layer | Contents | Name | Version |
|---|---|---|---|
| **Core (this document)** | What every probe and host implements regardless of its functions: transports and frames, messages, sessions and exclusivity, discovery (confirm / list / describe), plan, the general rules for the lifetime of resources, the notification mechanism, the rules for extension | `oep.core` (fn 0) | the protocol revision (confirm) |
| **Standard interfaces** | Named functions defined using only the mechanisms of the core. Definitions of commonly used functions whose names and numbers the project manages; "standard" does not mean a general standard (it includes ones specialised to a particular chip or family) | names starting with `oep.` | a revision per interface |
| **Extensions** | Definitions other than the optional functions of the standard interfaces, and independent interfaces | another definition of `oep.`, or a reverse-DNS name | each its own |

**Rules for drawing the line**:

1. Only what the host needs before it knows the name of an interface, or what spans all interfaces and cannot be defined by any one
   interface, goes into the core.
2. What can be defined as a named interface using only the mechanisms of the core does not go into the core, even if every probe has it
   (the test question: could a third party have defined the same thing under its own name without changing the core?).
3. The core touches neither the name nor the meaning of any particular interface (except `oep.core`).
4. Standard interfaces receive no special treatment on top of the core. They use only the same mechanisms as independent interfaces. The only differences are that the name
   is `oep.`, the numbers are in the project's registry, and the project has conformance tests.
5. Relations between interfaces (one interface using the resources of another, and so on) are defined by the documents of the interfaces
   concerned.
6. Versions are independent per layer (§2.7).

Outside OEP: updating the probe's own firmware (DFU, Mass Storage, etc.), the details of the USB descriptors.

**Language**: the English text of this specification is normative. The Japanese documents are translations; where the two differ, the English text is right.

## 1. Terms

| Term | Meaning |
|---|---|
| probe | A device that speaks OEP (a debugger, a fixture, a logic analyser, etc.) |
| host | Software that uses a probe |
| target | What the probe is connected to (a microcontroller under development, etc.) |
| transport | What carries OEP frames (UART bridge, USB CDC, built-in USB serial, USB vendor bulk, HID, TCP) |
| serial port | A transport that the OS sees as a serial device (UART bridge, USB CDC, built-in USB serial). Shares the port between OEP and raw bytes (§3.4) |
| interface | A function the probe exposes under a name. Found with list, called with fn |
| fn | A number (u16) that designates an interface for the duration of the session. fn 0 is `oep.core` |
| op | The number of an operation within an interface (u8) |
| session | The right to hold the lock and change state. Identified by a session_id (u32) chosen by the host |
| lease | The expiry of the lock. Extended by requests such as keepalive |
| channel | The number of a pin of the probe (u16) |
| plan | The assignment of which channel is used for which role of which interface |

## 2. Common rules

### 2.1 Byte order and strings

All numbers are little endian. Strings are UTF-8 byte sequences whose length is carried separately (no terminating 0).
A **bitmap** is a byte sequence in which bit i is bit (i mod 8) of byte ⌊i/8⌋, bit 0 being the least significant bit. A bitmap runs to the end of the value that contains it.

### 2.2 TLV

```text
tag(u8) | len(u8)        | value(len byte)          len 0 to 254 (short form)
tag(u8) | 0xFF | len(u16) | value(len byte)          len 255 or more (long form)
```

- **The encoding is unique**: the short form if the value is 254 bytes or less, the long form if 255 bytes or more. Any other form (254 or less in the long form, etc.) is malformed.
  The reader decides by whether the first byte of `len` is 0xFF. The `len(u8)` of an element of a sequence (§2.3) has no such escape (an element is at most 255 bytes).
- **The tag number is the low 7 bits (0x01 to 0x7E).** Bit 7 is the critical mark. It is used only in requests and is not part of the number: 0x10 and 0x90 are the same TLV, sent without and with the mark. In answers, events and data bit 7 is 0, and a reader that meets a TLV with bit 7 set there skips it as an unknown tag. Tag 0x00 is reserved (not used in TLVs; the marker in the payload of rejected unsupported, §4.3), 0x7F is reserved for ignored in answers, and 0xFF is invalid.
- ignored lists tag numbers (bit 7 cleared). The payload of rejected unsupported carries the tag byte as received (bit 7 included).
- The tag space is **per (fn, op) context** (the same value in a different context is a different thing).
- Repeating the same tag represents a sequence, for a tag whose definition says it repeats (§2.3).

### 2.3 Fixed part and tail

- **A container knows its own length**: for a frame, a TLV, an element of a sequence, or a byte sequence (data), the reader can tell where it ends without the request or outside knowledge.
  Variable parts (sequences, byte sequences, strings) are preceded by a count or a length. A form ending in a variable part without a length is limited to link_source / link_sink
  of fn 0 (the link test).
- **Answers**: after the fixed part of each op's answer (and any sequences preceded by a count or length) comes a sequence of TLVs. Everything added later is added here as TLVs.
  The host skips tags it does not know. An answer shorter than the fixed part is treated as a broken answer. **The form of the fixed part of an answer is decided by the op's definition
  per (op, resolution, outcome)** (success and failure may have different forms. Common parts of the interfaces, §3).
- **Events and data** (§11.2) are the same as answers: after the fixed part comes a sequence of TLVs.
- **Requests**: the only thing that can be appended to a request is a sequence of TLVs. The host **sets the critical bit** when the request is meaningless unless that item
  takes effect (items that may be ignored may be sent without it). TLVs that an interface's definition says are sent critical (a speed limit,
  pins, and other items for safety) always carry it. If the probe sees an unknown critical
  TLV it refuses with rejected unsupported (the tag as received in the payload). It ignores unknown non-critical TLVs and appends ignored
  (tag 0x7F, below) to the answer. It does so on every completed answer, also when the op's status is a failure.
- ignored lists the numbers (bit 7 cleared) of the ignored TLVs **in the order they appear in the request**, one entry per ignored TLV, at most 16 entries (`ignored_max_entries`). When more than 16 TLVs were ignored, the probe lists the first 15 and puts **0x00** as the 16th entry ("more were ignored"; 0x00 is never a tag, §2.2). A host that sees 0x00 treats every TLV of its request that is not listed as possibly ignored.
- The probe never leaves ignored out of an answer that needs it. When it decides how much variable data (data, sequences) goes into an answer, it keeps room for ignored (at most 18 bytes). If even the fixed part leaves less room, it lists as many entries as fit, with 0x00 as the last. `0x7F 0x01 0x00` (3 bytes) always fits.
- A tag whose definition does not say it repeats appears at most once in a request. Two or more are rejected malformed, critical or not. In an answer, the host uses the first.
- If the value of a TLV this probe implements is shorter than its definition, or holds a value its definition excludes, the request is rejected malformed, critical or not. Only a value inside the definition that this probe cannot handle is unsupported (critical) or ignored (not critical). A TLV the probe does not implement is unknown to it, whatever its length.
- **The value of a request TLV is not extended at the end.** A new field goes under a new tag. A probe that meets a request TLV it implements whose value is longer than it knows rejects it unsupported (that tag as received) when critical, and otherwise ignores the whole TLV and lists it in ignored.
- Tag 0x7F or 0xFF in a request is rejected malformed. A request shorter than the fixed part is rejected malformed.
- **Variable sequences are preceded by a count** (so that TLVs can be appended after them).
- No field that may be omitted is placed in the fixed part (a value that should be omittable becomes a TLV).
- Arguments the host adds for safety (a speed limit, etc.) are critical.

**How fixed forms are extended** (after the freeze this is the only way):
- When **the value of a TLV in an answer, an event or data, or an element of a sequence**, has a fixed form, **the reader skips whatever lies beyond the length it knows** (shorter than the known length is a broken value).
  **The writer appends only at the end.** The position and meaning of earlier fields do not change. If the form contains a variable part (with a length), what lies beyond "the end of the last
  known field" is skipped.
- A variable part inside a fixed form (a name, the value of a lock, etc.) is **preceded by a length**. A variable part without a length can only be at the very end of the form, and nothing
  can be added after it, so it is not used.
- **Elements of a sequence in an answer are preceded by the element's length (u8)**: `count(u8), count × (len(u8), element)`. The reader skips the unknown tail of each element.
  Sequences in requests (sent by the host) carry no length (anything to add becomes a TLV). However, values the probe remembers and returns on read-back (the items of probe.config,
  the sequence of streams of a bind) take the same form as the sequences of answers.
- A field appended after a value is treated as an optional item. The revision of §2.7 does not change.
- The items the probe keeps and returns (probe.config) keep the "append at the end" rule. A field appended to such an item must be one that is safe for an older probe to skip.
- **The values of describe TLVs** (bitmaps, strings, sequences of pairs) stay closed as an exception to this rule. Information added to describe is added under a new tag.
- **Width of values**: values determined by the nature of the hardware (counts, speeds, thresholds, capacities, times) are u32 or wider. u8 / u16 are used only where the limit is set by
  the protocol itself (a count within one frame, fn, resource numbers, numbers within an interface). A set of bits is u32 or `base + bitmap`.

### 2.4 Unknown values

- Frames with an unknown role are discarded.
- An unknown resolution, and an unknown outcome of completed, are treated as failure.
- Unknown values of an interface's status or reason are treated as failure.
- Events of an unknown kind are discarded (seq is still counted).
- The host ignores reserved bits of an answer's flags. It shows unknown values of an answer's enum that do not report a failure (cause, holder_kind, the kind of a scan entry) as unknown. Unknown status and reason values remain failures.

### 2.5 Number spaces

| Space | Range |
|---|---|
| role | 0x01 request, 0x02 answer, 0x05 event, 0x06 data. 0x03 / 0x04 are reserved, 0x07 to 0x7F are reserved. Bit 7 has meaning only for requests (session_id present, §4.1). In frames from probe to host bit 7 is 0 |
| op of core (fn 0) | 0x01 to 0x0F discovery and plan, 0x10 to 0x1F session, 0x20 to 0x2F reserved (long operations, §10), 0x30 to 0x3F notification, 0x40 to 0x4F link test, 0x50 to 0xEF reserved, 0xF0 to 0xFF experimental (shipping probes do not use them) |
| op of an interface | 0x01 to 0xEF are decided by the interface's definition. 0xF0 to 0xFF are experimental |
| reject reason | 0x01 to 0x3F core (common to all interfaces), 0x40 to 0x7F interface, 0x80 to 0xFF reserved |
| outcome | 0 success, 1 failed, 2 partial. Others reserved |
| event kind | A space per fn. 0x01 to 0x7F are decided by the interface (for fn 0, the core), 0x80 to 0xFF are reserved |
| TLV tag | Per (fn, op) context. The number is the low 7 bits; bit 7 is the critical mark (§2.2). 0x00, 0x7F, 0xFF are reserved in every context |
| describe tag | 0x01 to 0x3E common tags of the core (§7.4), 0x3F reserved (answer meta information), 0x40 to 0x7F interface |
| resource number | u16, one space per probe (§9) |

Unless its definition says otherwise, every unused value of an enum and every reserved bit of a request may be defined later (§2.7). A probe refuses them by order 6 of §4.3.

**Experimental values**: in every u8 enum whose definition does not say otherwise, the values 0xF0 to 0xFE are experimental. Anyone may use them while trying something out. A shipping probe and a released host do not use them, and they are never registered. (Tag numbers have no experimental range. Independent information goes into an independent interface, §13 rule 7.)

### 2.6 Wrapping values

seq (u16), resource numbers (§9), and those serial numbers and times defined by an interface that are defined to wrap, are compared by taking the difference as a signed value of the same
width (serial number arithmetic). The probe keeps the range that is meaningful at the same time well below half of that width. Values that do not wrap are u64
(the positions of streams and the times of the standard interfaces, etc.).

### 2.6a Clock

The probe has one clock: **ns since boot (u64)**. Wherever a time is returned (marks, segments, heartbeat, the "time of the last attempt" of a state) it is this value, and
"not yet" is all bits 1. Durations (timeout_ms, hold_ms, wait_us, elapsed_us, etc.) may stay in their own units.

### 2.7 Names and revisions

- The form and meaning of the **fixed part** of an interface's payload is **determined by (name, revision)** (the revision of list, u8).
- **The revision is raised only when the meaning or length of the fixed part changes.** The host does not use an interface whose revision it does not know.
- Adding optional request TLVs, response TLVs, optional ops or optional events without changing the fixed part does not change the revision. A host that does not know them
  does not use them. The presence of optional ops or modes is declared by describe (features etc.). **The "append at the end" of §2.3 does not change the revision either**
  (the value of a TLV, the payload of an event, the tail of an element of an answer's sequence).
- A probe that introduces a revision changing the fixed part preferably also exposes the old revision at the same time as a separate fn.
- The name changes only when the meaning of the interface changes.
- When the form of the core changes, the protocol revision (confirm) is raised. The form in this document is revision 1.

## 3. Transports and frames

### 3.1 Frames

Transports fall into 2 kinds. A **serial port** is a transport that the OS sees as a serial device (UART bridge = the probe's
UART brought out through a USB-UART converter chip, USB CDC, built-in USB serial); it carries OEP and raw serial bytes on the same port (§3.4).
The other transports (USB vendor bulk, HID, TCP) carry only OEP.

| Transport | Frame |
|---|---|
| Serial port (UART bridge, USB CDC, built-in USB serial) | COBS + CRC-16, delimited by 0x00 (below) |
| USB vendor bulk, TCP | `length(u16) message`. No CRC. Length 0 is reserved (keepalive; skipped). On vendor bulk, one transfer may contain several frames, and a frame may span transfers |
| USB HID (vendor-defined report) | The bytes of length-prefixed frames are packed into reports. report = `count(u16)`, count bytes, zero padding (the report size is as in the HID descriptor). If the descriptor declares a report ID, both input and output reports start with the ID, and count is counted from after it |

- **COBS frame**: CRC-16/CCITT-FALSE (polynomial 0x1021, initial value 0xFFFF, no reflection, "123456789" → 0x29B1) is appended to the message in
  little endian, encoded with COBS (the standard form split into 254-byte blocks), and **sent enclosed in 0x00 on both sides** (`0x00 <COBS> 0x00`).
  Neither probe nor host omits the leading 0x00. When the last block carries 254 bytes of data (code 0xFF), the encoder does not append an empty block, and the decoder
  accepts both the form with it and the form without it. Empty frames (consecutive 0x00) are skipped.
- **How the host receives (COBS)**: from right after opening the port up to the first 0x00, and from one 0x00 to the next 0x00, are both decoded as candidate frames
  (bytes sent before the port was opened, or bytes dropped right after opening, may mean the leading 0x00 never arrives). Candidates that do not decode, candidates whose CRC does not match,
  and frames whose role or corr does not match (§11.1) are discarded as raw serial bytes (noise). The absence of an answer is determined only by timeout.
- **USB bundling** (vendor bulk): if the length of a write is a multiple of wMaxPacketSize, the host follows it with a zero-length transfer. When the probe has finished
  sending and nothing follows, if the last transfer is a multiple of wMaxPacketSize, it either sends a zero-length transfer or splits the last 1 byte into a separate transfer.
  If more follows immediately, it may stay a multiple.
- Which frame is used is decided only by the kind of transport (not chosen by VID:PID).
- **TCP is used only on a trusted local connection or inside an authenticated tunnel.** OEP has no authentication (including the force of §6.4).
  When one probe is used by several hosts, a broker on the host side bundles them into one session (the broker is a host implementation, outside this
  specification. The transport and the session as seen from the probe do not change).

### 3.2 Sending frames

- The host **sends one frame in one write**, and does not pause for 100 ms or more in the middle of a frame.
- If input stops for 200 ms in the middle of a frame, the probe restarts the read from the beginning.

### 3.3 Several transports

- A probe may accept OEP control over several transports. **Several transports share one session and one lock.** Requests arriving from any transport are treated as the same,
  and the answer goes back on the transport the request came from. Notifications go to the transport the subscribe came from (§11.4).
- **The role 0x81 requests of one session are sent on one transport** (so that the ordering decision of §5.2 is not misled by transport delays). Read-only 0x01 may be
  sent from another transport. A misjudgement caused by the host sending 0x81 from 2 transports is the host's responsibility; the probe does not check.
- When the same probe has several transports, the host tries vendor bulk, HID, then serial ports in that order (serial ports are also used to carry raw bytes,
  §3.4). The list of the probe's transports is known from the transport of the describe of fn 0 (§7.5).
- **How to tell a USB OEP probe apart**: among devices it does not know, a host identifies an OEP probe automatically only when the device has **the project's USB
  VID:PID**. The project's VID:PID is listed in the registry's `usb` when it is obtained. Until it is listed, the registry has no
  VID:PID, and no device is identified automatically by this rule (the temporary clues until then are in [host development guide](host-development-guide.ja.md) (Japanese)
  §1.7; they are not normative). The device string iProduct is free text for display, and the host does not use it for identification. Interface strings are also for
  display and are not used for identification.
- **A named probe**: when the user names a probe by its unit_id (the address `oep://<unit_id>[/<slot name>]`, §7.6), the host may open the USB device whose serial number
  equals that unit_id without identifying it. After opening, the host follows the probing rule below, and uses the device as that probe only when the unit_id of the describe of fn 0
  sent after confirm equals the named value. Otherwise the host closes the device and sends nothing else. These comparisons (a unit_id with a serial number, and unit_ids with each other)
  ignore the case of ASCII letters (some OSes and tools show serial numbers in upper case; since a unit_id uses only the characters of §7.5, ignoring case
  never makes two different values equal).
- **Other devices and serial ports**: of the USB devices and serial ports that fit neither of the 2 cases above, the host opens only those it has its own way of handling, or those the user
  has chosen explicitly.
- **The probing rule**: on a device or port the host opens without having identified it (a named device, a port the user chose, a device the host handles on its own, a device found by
  a temporary clue), the first thing the host sends is a confirm (§7.1) only (including the single resend of §5.2). When the wait for the confirm
  (§4.4; confirm has no time set by its arguments, so 1000 ms) has passed without a valid confirm answer (when resent, when the wait for the resent
  confirm has passed without one), the host closes the device or port and sends nothing else. On a UART bridge port (transport
  kind 1), however, the host may repeat the confirm for the time of host obligation 7 in §3.5 instead of the single resend (to wait out a rate a previous host raised;
  it sends confirms only, and closes the port when no valid answer has come by then). A valid confirm answer is a completed answer with the same corr as the sent
  confirm whose payload has the shape of §7.1 (starting with `OEP!`). A device or port that gave a valid answer is treated as an OEP
  probe.
- **Choosing the ports**: inside a device known to be an OEP probe (the project's VID:PID, a named device, a device that gave a valid confirm answer), the
  ports are selected by the interface descriptors: every CDC (ACM) is a serial port (§3.4; all of them accept OEP), **the bulk IN / OUT pair of an interface with bInterfaceClass 0xFF,
  bInterfaceSubClass 0x4F ('O'), bInterfaceProtocol 0x45 ('E')** is vendor bulk, and **a HID with usage page 0xFF4F,
  usage 0x45** is HID (the registry's `usb`). A probe exposes vendor bulk and HID in this shape, and at most one of each. The host does not decide
  that a device is an OEP probe from this class / subclass / protocol and usage page / usage alone. Other class 0xFF interfaces
  (the debug function of a built-in USB serial, WebUSB, etc.) do not have this subclass / protocol, so they are not claimed. Other functions (DFU, Mass Storage, etc.) are
  outside OEP.
- **The USB serial number is the unit_id** (§7.5): on ports where the probe can choose the serial (CDC, vendor bulk, HID that the device exposes itself), the serial number is
  the unit_id itself (the invariance of §7.5). The host can tell the unit apart without opening it (and so find a named probe), and the value equals the describe of every
  transport. On ports where the serial cannot be chosen (built-in USB serial, USB-UART converter chips), the host specifies the transport from outside and confirms the unit_id with describe.
  confirm and describe can only be used after the port is opened, so the choice of port follows this rule.
- **max_frame is the limit in both directions**: the probe sends no message exceeding max_frame, and the host sends no message exceeding max_frame.
- **Before confirm**: every probe accepts messages of up to 64 bytes (the registry's `min_max_frame`) (the max_frame of confirm is 64 or more).
  The host sends no message exceeding 64 bytes until it has received the answer to confirm. The host is able to receive messages of up to 65535 bytes from the
  probe.

### 3.4 Sharing a serial port

A serial port carries OEP frames and raw bytes (the target's console, etc.) on the same port. The probe accepts OEP on every port at all times
(it has no setting that makes a port OEP-only, and no boot mode).

- **How the probe receives**: when 0x00 arrives, it accumulates up to the next 0x00 and decodes. If it decodes and the CRC matches, it is an OEP request. If it does not decode, the CRC does not match, or
  input stops for 200 ms before the next 0x00 (§3.2), the accumulated bytes (including the leading 0x00) are treated as raw bytes. The 0x00 that closed a candidate becomes
  the start of the next candidate. **A candidate of 0x00 only with no contents** (nothing follows the closing 0x00 of a frame; consecutive 0x00) is a delimiter,
  and is not turned into raw bytes even after a 200 ms pause. Bytes arriving outside 0x00 are treated as raw bytes immediately.
- **Where raw bytes go**: to the flow the probe has bound to that port (which flow is bound is decided by the probe's settings. If nothing is bound, they are discarded).
- **How the probe sends**: answers and notifications are `0x00 <COBS> 0x00`. Transmission on one port is done by one writer, and raw bytes are not interleaved
  in the middle of a frame (a frame may go out before raw bytes, and the order among raw bytes is kept).
- **Ports where raw transfer stops**: on a port where even one request of the session that holds the lock (the open that took the lock, and the role 0x81 requests with that session_id)
  has arrived, until that session ends (end, lease expiry, taken by force), the probe sends no raw bytes and discards raw bytes arriving from the
  port. Ports where only lock-free requests arrived, and ports while a session is running on another transport, are not stopped. Where raw transfer resumes from after the session
  ends is decided by the settings that define the flow bound to the port.
- Even if something that looks like a valid frame appears by chance in the raw bytes, the host discards it through the role and corr matching (§11.1).
- **The host's receive capacity**: the OS serial driver may silently lose frames when the frames the probe sends arrive in a burst exceeding the driver's receive capacity
  ([link measurements](link-measurements.ja.md) (Japanese) §1.1). On serial ports, the host keeps the expected volume of answers to outstanding requests (concurrency × frame limit)
  at 6 KiB or less. Notifications likewise: when subscribing on a serial port, the host keeps the min_bytes of subscribe small (2 KiB or less) and matches the amount the probe
  sends at once to its own receive capacity (§11.3). Bulk transfers prefer a length-prefixed port (vendor bulk). The probe's max_inflight and window are
  the probe's receive limits, not the host's receive limits.

### 3.5 Serial port speed (optional function)

An optional function to raise the link speed of a UART bridge port above the boot speed for the duration of a session. Its uses are large writes, capture, and the console
(the time of the wire's block ops is determined by the round trips on the debug wire and does not change with the link). The speed of the probe's fixture UART is separate (that interface's
configure and settings). This section defines only the **handshake**. Which speeds to try as candidates, the criterion for considering one passed, and the criterion for falling back while in use
are decided by the host (reference procedure: [host development guide](host-development-guide.ja.md) (Japanese) §7).

**Definitions of terms**

- **Boot speed**: the port speed determined by the board profile. The fallback for everything on the probe. The host decides it together with the user's choice of port and keeps it in one place.
- **Candidate**: the sequence of speeds the host tries. The probe does not declare candidates (which speeds pass is determined by the converter chip and the OS, and the probe cannot know). This specification
  decides neither the candidates nor a default.
- **Flow**: the pair of direction (probe → host, host → probe, both directions) and concurrency n. A term for the host's verification and records (this specification does not decide the
  flow).
- **Broken candidate** (probe side): in the receiving of §3.4, a candidate closed by 0x00 that does not decode or whose CRC does not match. Delimiters of 0x00 only, and bytes arriving outside
  0x00, are not counted.

**Probe**

- Only a probe with it ON declares port_speed (§7.5) in the describe of fn 0 and accepts op port_speed (fn 0, 0x14, lock required). OFF is
  unknown_operation. Only ports of transport kind 1 (UART bridge) are eligible.

```text
port_speed  request: port(u8), baud(u32), step(u8: 0 try, 1 commit, 2 revert), verify_ms(u16), idle_ms(u32), [TLV]
            answer:  baud(u32: the speed actually applied), [TLV]
```

- Refusals: port is not the port this request came from → rejected unavailable (cause 6). baud cannot be produced by the probe's UART → rejected unsupported.
  A step of 3 or more is rejected unsupported (payload tag 0x00, §2.5).
  Refusals when the lock is missing or different follow the order of §4.3 (session_required, no_session, expired, locked).
- The state is one of 3 per port: **boot / trying / committed**.
  - **Try** (step 0, accepted in the boot state): after finishing sending the answer at the current speed, switch to the baud of the answer and become **trying**. verify_ms starts
    with the value of this request.
  - **Commit** (step 1, accepted in the trying state, with the same baud, at the new speed): become **committed**. idle_ms starts with the value of this request (at most
    port_speed_idle_max_ms = 3000 ms. 0 and longer values are treated as the maximum).
  - **Revert** (step 2, in either trying or committed): send the answer (baud is the boot speed) at the current speed, then return to the boot speed.
  - A step that does not fit the state (commit in the boot state, commit after committed, revert in the boot state, try on a port that is trying or committed, commit with a baud different from
    the one being tried) is rejected unavailable (cause 6). The probe raises only one port at a time: if a try arrives on another port while one port is raised, it sends that answer,
    then returns the raised port to the boot speed and puts the new port into trying.
- **Conditions under which the probe returns to the boot speed by itself** (it does not announce the return):
  1. verify_ms passed while still trying.
  2. In the trying state, after one valid frame was received at the new speed, one broken candidate arrived on that port (broken candidates right after switching, before the first valid
     frame at the new speed, are not counted).
  3. After committing, no valid frame arrives on that port for idle_ms. idle_ms restarts whenever a valid frame is received and whenever an answer is sent (it does not advance while a request is being
     executed. Same as the lease, §6.1).
  4. After committing, 3 broken candidates in a row with no valid frame in between.
  5. The session ended (end, lease expiry, the owner changed by force). For end and force, it returns after sending the answer.
- Between trying and committing, the session's resources and lock do not change. Raw transfer (§3.4) is stopped for the duration of the session.

**Host obligations**

1. Send from a UART bridge (transport kind 1) port, holding the lock.
2. On receiving the answer to try, switch to the requested baud (or the baud of the answer if it could not be produced), wait 20 ms or more, then verify the new speed with confirm.
3. Within verify_ms, either send commit, or do not send it and wait for the probe to return (confirm at the boot speed after verify_ms has elapsed).
4. While raised, send keepalive or other requests at intervals shorter than half of idle_ms.
5. If an answer does not arrive within the wait time (§4.4) at the raised speed, return to the boot speed and repeat confirm (up to port_speed_idle_max_ms + 1000 ms).
   Even if the probe is still at the raised speed, a confirm at the boot speed reaches the probe as broken candidates, and it returns after 3 with no valid frame in between (return condition 4), so this converges.
   If it passes (same boot_id means it merely returned; different means a reboot), continue at the boot speed for that session. If confirm does not pass within the limit, it is a
   link failure (do not go back to the raised speed and wait again).
6. On receiving the answer to revert, or on receiving the answer to end, switch to the boot speed.
7. A host opening a port repeats confirm for port_speed_idle_max_ms + 1000 ms if confirm does not pass at the boot speed (waiting for the leftover of a previous host's
   raise to return).
8. Which speeds to try as candidates, the flow for verification, the criterion for considering one passed, and the criterion for falling back while in use are decided by the host (reference: [host development guide](host-development-guide.ja.md) (Japanese) §7).

The measured values and the records of how things break are in [UART speed](uart-speed-negotiation.ja.md) (Japanese), [link measurements](link-measurements.ja.md) (Japanese).

## 4. Messages

### 4.1 Requests

```text
role=0x01 | corr(u16) | fn(u16) | op(u8) | payload                      header 6 byte (no session_id)
role=0x81 | corr(u16) | fn(u16) | op(u8) | session_id(u32) | payload    header 10 byte (with session_id)
```

- `corr`: a number assigned by the host. **The host advances it by 1 per request** (role 0x01 requests count too. After 65535 comes 1. 0 is not used).
  Using the same number again happens only for the resend of §5.2. The probe uses this ordering to tell a resend from an old request it does not remember.
- Requests that change state are sent with role 0x81 (§6.3). Requests usable without the lock may be sent with 0x01 (sending them with 0x81 extends the lease).

### 4.2 Answers

```text
role=0x02 | corr(u16) | resolution(u8) | detail(u8) | payload           header 5 byte
```

| resolution | Value | detail | payload |
|---|---:|---|---|
| rejected | 0x00 | reject reason (§4.3) | Auxiliary information defined by the reason |
| completed | 0x01 | outcome (0 success, 1 failed, 2 partial) | Defined by the op |
| — | 0x02 | — | Reserved (long operations, §10). The host treats it as failure |

- Exactly one answer per request. The answer goes back on the transport the request came from, with the same corr. fn and op are not returned.
- **rejected is used only when "the request was not accepted"** (format, numbers, session, cannot be accepted in the current state). What was accepted and executed but
  did not go well becomes completed failed or partial, and the payload returns how far it got and why.

### 4.3 Reject reasons (core)

| Value | Name | Meaning | payload |
|---:|---|---|---|
| 0x01 | unknown_function | That fn does not exist | — |
| 0x02 | unknown_operation | That fn has no such op | — |
| 0x03 | malformed | Error in length or value range | — |
| 0x04 | unavailable | Cannot be accepted in the current state or with the current resources | Sequence of TLVs (optional, below) |
| 0x05 | busy | Reserved (long operations, §10) | — |
| 0x06 | window_exceeded | window / max_inflight exceeded | — |
| 0x07 | no_session | The lock is free, but this session_id is not the last ID. The host starts over from open | — |
| 0x08 | locked | Another session holds the lock | Remaining time in ms (u32), [TLV owner (§6.4)] |
| 0x09 | session_required | A state-changing request has no session_id | — |
| 0x0A | no_connection | The probe does not know the resource of the request (connection, stream, etc.; anything designated by number). The host recreates it. Every interface uses this for an unknown number | — |
| 0x0B | unsupported | It is in the definition, but this probe cannot handle it (a critical TLV, a value in the fixed part, the function of an optional op) | `tag(u8)`, [TLV]. tag is the value as received for a critical TLV, 0x00 for a value in the fixed part. To indicate which element, TLVs follow (same tag space as unavailable: channel, index) |
| 0x0C | result_lost | The result of a resent request is not remembered (§5.2) | — |
| 0x0D | corr_reused | A request arrived with the same corr but a different fn, op or contents (§5.2) | — |
| 0x0E | expired | The lock of this session_id ended by lease expiry and the resources were removed (§9). The host starts over from open (the side taken by force gets locked while the taker holds it, and no_session afterwards: the probe remembers only the last session_id) | — |

The detail of rejected is the reason, and other information goes in the payload.

**Order of refusal** (the probe checks in the following order and refuses with the first reason that applies. No two reasons are created for the same situation):

1. Header: unknown_function → unknown_operation → session_required.
2. Resend (the table of §5.2): corr_reused / result_lost / the remembered answer.
3. Session (§6.2): no_session / expired / locked.
4. window_exceeded.
5. **Format** → malformed: the length, a count that does not match the contents, a TLV encoding error, a contradiction between fields, and a value the field's definition excludes for every revision (the 7-bit `address > 0x7F`, a boolean other than 0 / 1, a value the definition calls invalid, a value whose length is unknown so that the rest of the request cannot be read, such as an unknown dmi step kind).
6. **Not handled by this probe** → unsupported: a value the definition leaves unused (an unused value of an enum, a reserved bit of a request's flags), a value in the definition that this probe does not declare (mode, format, rate, trigger type), an unknown critical TLV, a pin combination the declaration does not allow. The payload's tag is 0x00 for a value in the fixed part, and the TLV's tag as received for a value inside a critical TLV (a non-critical TLV with such a value is ignored, §2.3).
7. **Cannot be accepted in the current state or with the current resources** (plan, connection, running, capacity, bound into a group) → unavailable (with cause).
8. The resource designated by number is unknown → no_connection.

When an fn designated inside the payload (describe, subscribe, plan, settings items) does not exist, unknown_function is reused.

**The payload of unavailable** (an optional sequence of TLVs. The host skips unknown tags and copes without any. The probe attaches what it knows):

| tag | Name | Value |
|---:|---|---|
| 0x01 | cause | u8: 1 the pin is in use, 2 a count limit (plan_roles, slots, connections, etc.), 3 not enough storage, 4 bound into a group (capture-group), 5 held by the settings (a settings plan, a slot), 6 wrong state (not configured, running, etc.) |
| 0x02 | channel | u16. The channel that collided (may repeat) |
| 0x03 | holder_fn | u16. The fn holding that resource |
| 0x04 | holder_kind | u8: 1 plan, 2 wire connection, 3 slot, 4 bind, 5 settings plan, 6 settings disable |
| 0x05 | fn | u16. The fn the refusal concerns (in the bind of a capture-group, indicates which track) |

Interfaces may add their own tags from 0x40. The TLVs after the payload of rejected unsupported use the same space (channel 0x02, fn 0x05,
the interface's index, etc.).

### 4.4 Pipelining

- In confirm (§7.1) the probe returns `max_frame` (the maximum message length it accepts), `window` (the limit on the total message length of outstanding requests),
  and `max_inflight` (the limit on the number of outstanding requests). The message length includes the header (from role) and excludes the frame wrapping (COBS, CRC, length).
- The host observes both limits. The probe may refuse a request that exceeds them with rejected window_exceeded, but a request lost beyond the buffer gets
  no answer either. Observing them is the host's responsibility.
- The probe processes requests in the order received and returns answers in the order received.
- **The host's wait time**: the absence of an answer is decided only by timeout (§3.1). For each request the host waits **at least**: the time set by the request's arguments (the timeout_ms of run,
  the hold_ms of reset, the sum of the waits of dmi, save, etc.; for attach, `attach_budget_ms` plus the hold_ms of its reset TLV; for scan, `scan_budget_ms` + `attach_budget_ms` ([wire and debug](oep-if-debug.md) §1); 0 if none; at most max_op_ms, §7.5) + 1000 ms (`host_wait_add_ms`) + the transfer time. The wait starts when the request has been written, or, while earlier requests on the same transport are outstanding, when the answer to the request before it arrives (the probe answers in order).
  The transfer time is 0 except on a UART bridge. On a UART bridge it is (L + max_frame × (1 + `notify_pending_max_frames`)) × 10 / baud seconds, where L is the length on the wire of the request's frame and baud is the port's current speed. A host may wait longer. When the wait has passed, it proceeds to the resend of §5.2.

## 5. Recovery and resend

### 5.1 Recovering the delimiting (length-prefixed frames)

On length-prefixed frames (vendor bulk, HID, TCP), when the host sees an answer whose corr does not match, an impossible length (exceeding max_frame), or a frame that
stopped midway (no continuation for 200 ms), it discards input until it has been quiet for 50 ms, sends confirm, and verifies that the answer with its own corr comes back
before resuming. If the TLVs at the end of an answer are cut off midway, that answer is broken. When notifications keep flowing and the input does not become quiet,
it may send unsubscribe and end without verifying (executing them twice does no harm). COBS frames can discard broken ones by the CRC, so
this procedure is not needed there.

### 5.2 Resend and deduplication

- When an answer was broken or did not arrive, the host **may resend once with the same corr** (state-changing requests too). While the session holds the port
  (§3.4; raw transfer is stopped), a broken frame that arrives may be treated as belonging to the awaited answer, and the host may resend without waiting out the wait time. When unsubscribe
  and end were sent during recovery, the session has ended, so the original request is not resent.
- The probe remembers, for the requests of the last session (role 0x81), at least the most recent max_inflight entries of (corr, fn, op, CRC-32 of the request payload,
  answer), and the newest corr of that session. **The identity of a request is determined by corr alone** (the ordering of §4.1). The CRC is only for
  detecting a numbering mistake by the host.
- A request carrying the session_id of the last session is checked as follows **before the decision of §6.2** (the same even if the lock is free):
  - If the table has the same corr and fn, op and CRC are the same, **the remembered answer is returned without executing**. Neither the lock state nor the lease changes (a resent
    end does not re-establish the lock).
  - If the table has the same corr and any of them differs, rejected corr_reused.
  - If it is not in the table and corr is not newer than the newest corr (the difference as a signed u16 is 0 or less), rejected result_lost without executing
    (a resend of an old request that fell out of the table. The host re-reads the state to verify).
  - Otherwise it proceeds to §6.2 as a new request.
- A limit may be placed on the size of remembered answers. If a request whose answer was not remembered because of the limit is resent, rejected
  result_lost without executing.
- **The remembered table and the newest corr are discarded at every open (including resume)** (not at end). Exactly-once is not promised when the session
  changes.
- Read-only requests (role 0x01) are not deduplicated.
- CRC-32 is IEEE (reflected, polynomial 0xEDB88320, initial value and final XOR 0xFFFFFFFF. "123456789" → 0xCBF43926).

## 6. Sessions and exclusivity

### 6.1 The lock

- The probe has **one lock**. Only the session holding the lock can execute requests that change state.
- The session_id is chosen by the host (random is fine). The probe remembers the session_id that last held the lock.
- The lease is set by open and extended every time a request of the lock-holding session (role 0x81) completes. When the expiry passes, the lock becomes free
  (the expiry of §9). **The lease is not counted while a request is being executed** (the session is not cut even if a long op outlasts the lease. The upper bound on the length is
  the describe's max_op_ms, §7.5).

### 6.2 The decision when a request is received

The probe remembers whether the lock is held, the last session_id, and **how** the lock of that ID ended (released by end / removed by expiry or force).
The decision of the table of §5.2 (resend) comes before this table.

| Lock | session_id of the request | Result |
|---|---|---|
| Free (released by end) | Same as the last session_id, other than open | Re-establish the lock and process (resume. The lease is the value of the previous open, the resources remain, §9) |
| Free (released by end) | open with the same session_id as the last | Re-establish the lock, resumed = 1 |
| Free (removed by expiry) | Same as the last session_id, other than open | **rejected expired** (the resources were removed. The host starts over from open) |
| Free (removed by expiry) | open with the same session_id as the last | Establish the lock, resumed = 2 (a resume after the resources were removed) |
| Free | A different ID, other than open | rejected no_session |
| Free | open with a different ID (with or without force) | Establish the lock, update the last session_id and owner, resumed = 0 |
| Held by self | Same, other than open | Process |
| Held by self | Same open (with or without force) | Recreate the lease, resumed = 1. Subscriptions remain, and the destination of notifications changes to the transport of this open |
| Held by another | Different, other than open(force) | rejected locked with the remaining time (and owner) |
| Held by another | open(force) | Take it over (§6.4): remove the previous session's resources (§9), resumed = 0 |

### 6.3 Requests that require the lock

Every request that changes state requires the lock (role 0x81). What can be used without the lock is limited to read-only requests that do not change state
(confirm, list, describe, lock_state, link_source / link_sink, the read-only ops defined by interfaces). An op that an interface
declares lock-free must not change state.

### 6.4 open, end, keepalive, force

- **open** (session_id, lease_ms, force): takes the lock. The answer is lease_ms (the value decided by the probe), boot_id, resumed (0 new session,
  1 re-established with the same session_id with the resources kept, 2 same session_id but after the resources were removed. The registry's `resumed`). **The table of §5.2 is discarded at
  every successful open** (not at an open that gets rejected locked. Not at end, expiry or force).
- **lease_ms**: 0 means "the probe's default". The probe accepts requests of 1000 to 60000 ms as they are, and rounds values outside the range (the default and the rounding range are
  decided by the probe). The host takes the lease_ms of the answer as authoritative.
- **end**: releases the lock. The session's resources remain (§9).
- **keepalive**: only extends the lease.
- **lock_state**: whether the lock is held and the remaining time. locked means "the lock is held by whatever session" (lock_state can be sent without holding a
  session, so the probe does not know who asked. Whether it holds it, the host knows from its own state).
- **owner**: with the TLV 0x01 owner of open (text, 1 to 32 bytes, non-critical), the host may attach an owner name (e.g. "flash-tool pid 1234").
  The probe remembers owner together with the last session_id (replaced by an open with a different session_id; on a resume with the same session_id, replaced if
  owner is present, otherwise kept), and while the lock is held, appends TLV 0x01 owner after the answer of lock_state and the payload of rejected locked
  (not appended if there is no owner). **The session_id is not returned** (returning it would let another host resume with that ID and take over without force). owner is for display only, and
  the probe does not interpret it.
- **force**: takes the lock even if another session holds it. The probe performs the same cleanup as for expiry on the previous session (§9) before
  handing over the lock. force is not authentication; it only prevents mix-ups.

### 6.5 boot_id

boot_id is a value that changes at every boot of the probe, carried in the answers of confirm (§7.1) and open (the same value). A 32-bit random number is fine (the host accepts
the probability of equal values). Even a probe with neither non-volatile storage nor a source of randomness always changes the value, from the variation in boot timing and the like. 0 is an ordinary value. When the boot_id changes,
the host considers the session's resources (plan, interface resources), the remembered fn mapping, the resource numbers and the stream positions all invalid.
A host that does not hold the lock (monitoring, discovery) learns of a reboot through confirm.

## 7. Discovery

### 7.1 confirm

```text
request: "OEP?", min_rev(u8), max_rev(u8), [TLV]
answer:  "OEP!", revision(u8), flags(u8), max_frame(u16), window(u32), max_inflight(u8), boot_id(u32), [TLV]
```

The host sends the range of protocol revisions it can handle, and the probe returns the highest revision within it that it can handle. If there is none in the range it can handle,
rejected unsupported. flags is reserved (0). boot_id is §6.5 (the place to learn of a reboot without the lock). Both request and answer fit in 64 bytes
(§3.3).

### 7.2 list

```text
request: flags(u8: bit0 exact), first(u16), prefix_len(u8), prefix
answer:  total(u16), count(u8), count × (len(u8), entry)
entry:   fn(u16), instance(u16), revision(u8), flags(u8), name_len(u8), name
```

- Returns the names matching prefix, from the first-th, as many as fit in one frame. **Matching is on label boundaries (the parts separated by `.`)**:
  a name matches if it equals prefix or starts with `prefix + "."` (`oep.fixture.uart` matches `oep.fixture.uart` and `oep.fixture.uart.stream`,
  and does not match `oep.fixture.uart2`). prefix is a sequence of labels without a trailing `.` (`oep.` matches nothing;
  write `oep`). An empty prefix matches everything. With exact, only exact matches (an empty prefix matches nothing). `oep.core` (fn 0) is also counted as the first
  entry. Bits 1 to 7 of the request's flags are reserved: a request with any of them set is rejected unsupported (payload tag 0x00, §2.5).
- Names are 1 to 64 bytes; the usable characters are `a-z 0-9 - .` (§13).
- instance distinguishes several interfaces of the same name. **Those with the same name are numbered from 0 in ascending order of fn.** The probe keeps the order of ports of the same name
  across firmware versions (because saved settings designate an interface by (name, instance, revision)). flags is reserved (0).
- When a single interface is designated in text (CLI, settings files, logs), it is written `name#instance` (instance is this value, from 0.
  `#0` may be omitted). Example: `oep.fixture.uart#1` is the second `oep.fixture.uart`.
- fn does not change while the probe stays booted. The host may remember the mapping from name to fn while the boot_id is the same.

### 7.3 describe

```text
request: fn(u16), first(u16)
answer:  more(u8), sequence of TLVs
```

Returns the declaration of fn, from the first-th TLV, as many as fit in one frame. more = 1 means there is more, and the host asks again with the number of TLVs received added
to first. The probe makes each TLV individually fit within its own max_frame. fn 0 is the declaration of the probe as a whole.

**describe returns only declarations**: while the boot_id is the same, the sequence and values of the TLVs do not change (the host may cache while the boot_id is the same, and paging
does not break even if settings change midway). Things that change (connections, whether something is saved, slot states, free capacity) are exposed by an interface's state-returning op
(no lock). Tag 0x3F is reserved for answer meta information (not used for declaration tags). Since the answer itself is a sequence of TLVs,
**no TLV is placed in a describe request** (if there is one, rejected malformed. The same for the get of probe.config): ignored (0x7F) never
appears in the answer.
- **End of paging** (common to describe, state, connections, streams, segments, get): if first is at or beyond the count, return count 0 and more 0.
  The host stops at more = 0. list has no more; its end is known from total (§7.2).

### 7.4 Common tags of describe (0x01 to 0x3E. 0x3F is answer meta information)

| tag | Name | Value |
|---:|---|---|
| 0x01 | role_channels | role(u8), base(u16), bitmap. If bit i is set, channel base+i can be used for that role. The same role may be written several times (union) |
| 0x02 | max_clock_hz | u32 |
| 0x03 | max_length | u16. The maximum length handled in one go. Declared as a value such that the op's request and answer fit within max_frame (the unit is decided by the interface's document). A request exceeding it is rejected unsupported |
| 0x05 | min_clock_hz | u32 |
| 0x06 | features | u32. Bits of optional functions (the meaning is decided by the interface) |
| 0x07 | implementation | u8. 0 unspecified, 1 software, 2 dedicated peripheral, 3 peripheral + DMA / PIO (for display and diagnostics) |
| 0x08 | channel_group | group(u8), n(u8), n × (role(u8), channel(u16)). If this group is used, each role is fixed to the channels given here. For a function with one or more groups, the plan must match one group completely |

0x04 is reserved. The role numbers are defined by the interface. These values are closed forms; information to add goes under a new tag (§2.3).

- A function that can be assigned to any pin lists its candidates in role_channels; a function whose pin combination is fixed writes channel_group once per combination.
  When both are written, the plan must match one of the channel_groups and also be within the candidates of role_channels.
  role_channels constrains only the roles it lists (a role not in role_channels is determined by channel_group alone, and a role not in channel_group
  is determined by role_channels alone).
- The same declaration is also used, by interfaces that select pins by argument instead of the plan (the pins of the wire's attach, etc.), as the declaration of selectable pins.
- The role_assignment (0x10, sent critical as 0x90) of the plan request is a tag in the context of plan_apply (§8), not a describe tag.

### 7.5 Declaration of the probe as a whole (describe of fn 0, 0x40 onwards)

| tag | Name | Value |
|---:|---|---|
| 0x40 | firmware | text |
| 0x41 | model | text. The kind of probe (the same value for hardware of the same kind carrying the same firmware. Does not vary per unit). **Lowercase `a-z 0-9 -`**, 1 to 32 bytes |
| 0x42 | unit_id | The ID of the unit. **Mandatory.** text of 1 to 32 bytes; the only usable characters are `a-z 0-9 -` (the chip's unique number in lowercase hex, etc.). Used by the host to group the transports of the same probe, so the describe of every transport returns the same value. Equals the USB serial number (§3.3). The value by which the host names a probe (the address `oep://<unit_id>/<slot name>`, [probe settings](oep-if-probe-config.md) §1.1) |
| 0x43 | channels | u16. The number of channels |
| 0x44 | reserved | base(u16), bitmap. If bit i is set, channel base+i is used by the probe itself and is not assigned to interfaces |
| 0x45 | profile | text. The name of the wiring, of a fixture or the like |
| 0x46 | label | channel(u16), text. A **fixed** channel name **held by the firmware (the wiring profile)** (NRST, etc.). Names given through the settings are read with the get of `oep.probe.config` (describe is declarations only, §7.3) |
| 0x47 | resets_on_open | u8. Whether the probe resets when the transport is opened |
| 0x48 | — | Reserved |
| 0x49 | transport | index(u8), kind(u8), interface(u8: the USB interface number, 0xFF if not USB). One per transport of the probe. **Mandatory** |
| 0x4A | discoverable | u8. 1 = the probe also enumerates with the project's USB VID:PID (§3.3) (even if the current transport is not one). Until the project's VID:PID is listed in the registry, every probe sends 0 |
| 0x4B | plan_roles | u32. The number of role_assignments the plan can hold at once (the total over all fns. Includes the settings plan). A probe with a limit always emits it (§8) |
| 0x4C | chip | text. The part number and revision of the probe's MCU: `<part number> v<revision>`, the part number in lowercase without hyphens (e.g. `abc123 v1.0`). So that captured data records which chip captured it (optional) |
| 0x4D | max_op_ms | u32. The longest time the probe spends on one request. **Mandatory.** Ops that could exceed it (run, the sum of the waits of dmi, the start of capture, save, the hold_ms of the reset of attach) are rejected unsupported if the sum of their arguments exceeds it. The lease is not counted during execution (§6.1). Reading the other transports and the consoles of connections continues. The value is decided by the probe. The host waits as §4.4 says |
| 0x4E | port_speed | u8. 1 = this probe accepts op port_speed (§3.5) (emitted only when the firmware has the function ON) |

- The kind of transport: 1 UART bridge, 2 USB CDC, 3 built-in USB serial (a USB serial port implemented by the MCU's hardware, whose USB descriptors, the serial number included, the probe cannot choose), 4 vendor bulk, 5 HID, 6 TCP (the registry's `transport_kind`).
  1 to 3 are serial ports (§3.4). index is the number designating a transport within the probe (from 0); when the probe's settings designate a serial port they also use this
  number. It does not change while the probe stays booted.
- The host may decide how to take over the lock from the number of transports (if the only transport is a single serial port, there is no previous owner once the port has been opened
  exclusively. [host development guide](host-development-guide.ja.md) (Japanese)).
- **Uniqueness of unit_id**: unit_id is a different value per unit (the chip's unique number, etc.). A probe with neither a unique number nor storage may hold it as a firmware build
  constant (accepting that units with the same firmware cannot be told apart).
- **Invariance of unit_id**: unit_id is derived only from values of the unit (the chip's unique number, a saved random number), and does not change with the firmware version, the profile, the build, or the kind of
  transport. No suffix is added. The host and the OS remember a probe by unit_id (= the USB serial number, §3.3).

### 7.6 Addresses

The string by which the host names a probe and a slot: `oep://<unit_id>[/<slot name>]`. The authority is the unit_id (§7.5, lowercase), the path is exactly one slot name
([probe settings](oep-if-probe-config.md) §1.1). `oep://<unit_id>` without a path is the probe itself. v1 defines nothing beyond this (query, port,
several paths). When an IDE or a settings file remembers a probe, it remembers it in this form (not by VID:PID or port name).

## 8. plan

The plan is held **per fn**.

- **plan_apply**: a sequence of role_assignment TLVs (0x10, sent critical as 0x90: fn(u16), role(u8), channel(u16); it repeats). One assignment is identified by
  (fn, role, channel) (some functions have several channels for the same role, such as gpio). **Only the assignments of the fns appearing in the request are
  replaced atomically**; the plans of the other fns are kept as they are. Treating the current assignments of the fns being replaced as removed, each interface verifies
  without side effects (including the contention check of §8.1), and it is applied only when all accept. If even one refuses, nothing changes and the answer is
  rejected (the current plans of the fns that were to be replaced also remain).
- **Number of assignments**: the number of role_assignments the probe's plan can hold at once (the total over all fns) is the describe's plan_roles (§7.5). A plan_apply (and a settings set)
  whose total after replacement would exceed it is rejected unavailable without changing anything (not enough resources. The same refusal as §8.1. The form of the request is
  correct, so not malformed).
- **plan_release**: `n(u8), n × fn(u16)`. Releases the plans of the listed fns (n = 0 is all fns). fns without a plan are ignored.
- **A settings plan does not belong to the session**: a plan for an fn that the probe's settings (the plan items of `oep.probe.config`) put in place is changed only by
  the settings. plan_release ignores that fn without releasing it (even with n = 0), and if plan_apply lists that fn, nothing changes and the answer is rejected
  unavailable (the same refusal as the pin contention of §8.1). Changing or removing a settings plan is done with the settings set (and its save). Otherwise
  the saved settings and the actual assignments would diverge.
- A released pin, whichever way it is released (plan_release, replacement by plan_apply, the cleanup at a lease lapse and at force in §9), goes to **the idle state**,
  that is **the idle the probe's settings define for that pin, if they define one (for output low / high it is driven at that level and with the strength the idle defines, not made Hi-Z); otherwise
  Hi-Z (input, no pull)**. An interface must not leave a pin under its own drive after it is released (when the idle state is an output, that drive belongs to
  the settings' idle. The setting of the idle state is the idle of `oep.probe.config`,
  [probe settings](oep-if-probe-config.md)).
- The lifetime of the plan is §9 (per fn).

**Refusals of plan_apply** (the order of §4.3):

| Situation | reason |
|---|---|
| Malformed form, the same (fn, role, channel) twice, fn 0 listed | malformed |
| fn does not exist | unknown_function |
| The role does not exist in that interface, the channel is not among the candidates of role_channels, it matches none of the channel_groups | unsupported (tag 0x90) |
| plan_roles exceeded, contention for pins or resources (§8.1), the fn of a settings plan | unavailable (cause 2 / 1 / 5) |

### 8.1 Resource contention

- Everything that takes a probe resource (pins, peripherals, DMA, timers, etc.) verifies, before taking it, that it does not collide with the existing plans, connections, and resources
  put in place from the settings (binds, etc.). If it collides, it refuses with rejected unavailable and **changes nothing in the state of the existing functions**.
  What takes resources: plan_apply, the wire's attach (pins), the settings set, and resource-creating operations defined by interfaces.
- Which internal resource (a DMA number, etc.) is used need not be shown to the host. Sharing that is safe (two functions reading the same pin as input,
  etc.) is allowed only when the probe explicitly allows it.

## 9. Lifetime of resources (general rules)

**Resources created by a session remain on an explicit end and are handed to the next session; they are removed on lease expiry and when taken by force.**

| Event | Resources created by the session | Subscriptions (§11) | The table of §5.2 | The next request with the same ID |
|---|---|---|---|---|
| end | Remain. At the next successful open they move atomically to that session's resources | End | Remains | Resume and process (§6.2) |
| Lease expiry | Removed | End | Remains | rejected expired; open gives resumed = 2 |
| Taken by force | Removed (same as expiry) | End | Discarded (the taking open discards it) | locked while the taker holds it, no_session afterwards (the last ID is the taker's) |
| open with the same ID (while held) | Remain | Remain (the destination becomes that transport) | Discarded | — |
| Probe reboot | Gone (the boot_id changes) | Gone | Gone | no_session |

- Resources left after end become, at the next successful open (whether with a different session_id or a resume with the same session_id), that session's,
  and are removed at that session's lease expiry or by force. A host that does not want to hand them over removes them itself before end (detach, close,
  plan_release, etc.).
- Resources of the core: **plan** (removing it releases the pins just like plan_release. If the target's wire was being held by the plan, the target's state may change), notification subscriptions
  (§11. Subscriptions also end on end), the table of §5.2.
- The lifetime of resources created by interfaces (debug connections, streams, etc.) is defined by the interface's document, on top of this rule
  (who is using them, when they close).
- Resources put in place from saved settings (defined by the interface) are not the session's resources.
- **Resource numbers are u16, one space per probe** (connections, streams, and everything else that interfaces designate by number. If a resource of a different interface is
  passed, rejected unavailable cause 6). Each time a new resource is created the number advances from 1, and after 65535 comes 1 (§2.6). A closed
  number may be reused once far enough away (the 1024 most recently closed numbers are not used). A failed creation (an attach that
  failed, a re-open of the same place) does not consume a number. A request using the number of a closed resource is rejected no_connection. After wrapping, an old number may
  designate a different resource: the host discards a number for which it received no_connection, and verifies long-held numbers with the listing ops (connections, streams).

## 10. Long operations (reserved)

v1 has no long operations. Every op completes with one answer. Resolution 0x02, reject reason 0x05 busy, and the core ops 0x20 to 0x2F are
reserved for when long operations are defined (at that time, the session that can retrieve the result, the numbering, and the handling on lease expiry and force
are decided together).

## 11. Notifications

The mechanism for notifications sent from the probe. Support by the probe is optional, and a host receives nothing unless it subscribes.

### 11.1 Host obligations (all hosts)

- Dispatch received frames by role. Only role 0x02 is matched by corr (bytes 1 to 2 of 0x05 / 0x06 are fn).
- Discard frames with an unknown role and answers with a corr not being awaited (on serial ports, raw bytes that look like a frame by chance are also discarded by
  this, §3.4).
- Even while notifications keep arriving, make sure the processing that waits for answers and the processing that reads input finish by their deadlines.

### 11.2 Form

```text
data    role=0x06 | fn(u16) | seq(u16) | position(u64) | len(u16) | data | [TLV]      header 5 byte
event   role=0x05 | fn(u16) | seq(u16) | kind(u8) | fixed part | [TLV]                 header 6 byte
```

- The form of the payload of data is common to all interfaces: `position` is the stream position of the start of this frame (decided by the interface),
  `len` is the length of data, and TLVs follow (§2.3). The fixed part of an event is decided by the interface per kind, and TLVs follow.

- `seq` is the serial number of frames per fn (u16, wraps. Shared by data and events). It counts from 0 at every subscribe. A gap means
  frames were lost. The probe numbers every event that is born, and those discarded inside the probe also consume a number.
- Events of fn 0 belong to the probe as a whole. kind 0x01 = heartbeat (fixed part: boot_id(u32), uptime_ns(u64), §2.6a).

### 11.3 Subscription

| op | Name | Request | Answer |
|---:|---|---|---|
| 0x30 | subscribe | fn(u16), min_bytes(u16), max_delay_ms(u32), [TLV] | — |
| 0x32 | unsubscribe | fn(u16) | — |

- **Only the holder of the lock can subscribe, and the subscription ends together with the lock** (end, expiry, taken by force). Read-only monitoring is done through the raw bytes of a serial
  port (bind, [probe settings](oep-if-probe-config.md)). Subscription without the lock is reserved (added later with a TLV of subscribe,
  without changing the meaning of the present subscription).
- Every probe implements the subscribe / unsubscribe of fn 0. A subscribe to an fn that emits nothing is rejected unsupported (order 6 of §4.3).
  An unsubscribe of an fn with no subscription does nothing and succeeds.
- Subscribing to the same fn again atomically replaces the previous subscription (the sending conditions, the destination transport, seq from 0). There is only
  one subscription per fn.
- **Conditions for batching**: send when min_bytes bytes have accumulated or max_delay_ms has passed since the first byte. 0 disables that condition. If both are 0,
  send whatever there is immediately.
- Subscribing to fn 0 delivers the heartbeat. The period is max_delay_ms (1000 ms if 0).
- There is no flow budget (credits). What the host or the wire fell behind on is pushed out inside the probe, and is seen from the interface's payload
  (the stream position, etc.) or from a gap in seq.

### 11.4 Probe obligations (probes that emit)

1. **Send answers first.** Process every request that has arrived, then send notifications.
2. **Keep pending notifications small.** Do not accumulate more than max_frame × 2 bytes of pending notifications in the transport's send buffer,
   and do not block on writes. Notifications that do not fit are discarded inside the probe (seen as a gap in seq, §11.3). On serial ports, the receive capacity of the host's OS (§3.4) is also a limit, and the host conveys it with min_bytes.
3. Notifications are sent on the transport the subscribe for that fn came from.

## 12. List of core (fn 0) operations

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x01 | confirm | §7.1 | §7.1 | Not required |
| 0x02 | list | §7.2 | §7.2 | Not required |
| 0x03 | describe | §7.3 | §7.3 | Not required |
| 0x04 | plan_apply | Sequence of role_assignment TLVs | — | Required |
| 0x05 | plan_release | n(u8), n × fn(u16) | — | Required |
| 0x10 | open | session_id(u32), lease_ms(u32), force(u8), [TLV owner] | lease_ms(u32), boot_id(u32), resumed(u8: 0 / 1 / 2, §6.4) | open takes the lock (role 0x01) |
| 0x11 | end | — | — | Required |
| 0x12 | keepalive | — | — | Required |
| 0x13 | lock_state | — | locked(u8), remaining_ms(u32), [TLV owner] | Not required |
| 0x14 | port_speed | §3.5 (optional. Only probes that emit port_speed in describe) | baud(u32) | Required |
| 0x30 | subscribe | §11.3 | — | Required |
| 0x32 | unsubscribe | §11.3 | — | Required |
| 0x40 | link_source | length(u32) | length bytes (up to what fits in one frame. Byte k is k & 0xFF) | Not required |
| 0x41 | link_sink | Arbitrary bytes (a sequence without a count) | Received length (u32) | Not required |

link_source / link_sink are for measuring the speed of the wire and do not change state. Only these two have a form ending in a sequence without a length
(the exception of §2.3. No TLVs follow).

## 13. Rules for extension (how to write an interface)

Standard interfaces and independent interfaces are both defined by the following rules.

1. **Name**: `oep.` is reserved by the project. Independent interfaces use reverse DNS (`io.github.<owner>.<name>`, etc.). Names are cut by what the host
   uses them for (not by the name of the probe's peripheral). **1 to 64 bytes; the usable characters are `a-z 0-9 - .`** (the registry's `limits`).
2. **What the definition decides**: the revision, the table of ops (number, request, answer, whether the lock is required), the TLV tags of each op (the space of that op's context),
   the interface-specific describe tags (0x40 to 0x7F), the role numbers of the plan, reject reasons (0x40 to 0x7F), event kinds
   (0x01 to 0x7F), the form of the payload of notification data, the resources the interface creates and their lifetime (on top of §9).
3. **Rules of form**: as in §2.3 (fixed part + TLVs, a count before a variable sequence, no omittable fields, safety arguments critical).
4. **Failure**: what was not accepted is rejected; what was accepted and failed is completed failed / partial (§4.2).
5. **Lock-free ops do not change state** (§6.3).
6. **Versions**: §2.7.
7. **Do not mix independent tags into standard interfaces.** Independent information goes in an independent interface (exposed as a separate fn).
8. **Make specialised things recognisable by name.** Procedures specialised to a chip or family (how to write flash, reset timing, etc.) go in an interface
   whose name shows what it is specialised to (e.g. `oep.wire.rvswd` is for the family that has that wire. Things like the reset procedure for programming a certain family,
   which does not meet its timing unless the probe does it). They may be placed in the standard or in independent interfaces.
   **Interfaces with generic names (`oep.target.riscv-dm`, `oep.target.arm-adi`, `oep.fixture.*`, etc.) do not contain processing for a particular
   chip.** Specialised things lower portability (a host using them is tied to probes that have that function, and supporting a new chip requires
   updating the probe's firmware). What can be done with generic procedures (raw transfers and the host's knowledge) is built that way.
9. The numbers of standard interfaces are listed in the registry. The numbers of independent interfaces are managed by their definitions.

## 14. Documents of the standard interfaces

| Document | Interfaces |
|---|---|
| [Standard interfaces: common parts](oep-if-common.md) | Positioned streams, debug connections |
| [Standard interfaces: wire and debug](oep-if-debug.md) | `oep.wire.rvswd`, `oep.wire.swio`, `oep.wire.swd`, `oep.target.riscv-dm`, `oep.target.arm-adi` |
| [Standard interfaces: console](oep-if-console.md) | `oep.target.console` (the dmseq framing is [target-console-dmseq](target-console-dmseq.md)) |
| [Standard interfaces: fixture](oep-if-fixture.md) | `oep.fixture.gpio`, `oep.fixture.uart`, `oep.fixture.i2c-target`, `oep.fixture.spi-target` |
| [Standard interfaces: capture](oep-if-capture.md) | `oep.fixture.logic`, `oep.fixture.analog`, `oep.fixture.capture-group` |
| [Standard interfaces: probe settings](oep-if-probe-config.md) | `oep.probe.config` |

## 15. Non-normative documents (reasons and history)

- [core wire model v1 (delta from v0)](v1-core-wire-delta.ja.md) (Japanese): the deltas before they were consolidated into this document, and the records of experiments.
- [Sessions and exclusivity](session-and-exclusivity.ja.md), [Comparison of capability identification methods](capability-identification-comparison.ja.md),
  [Capability declaration model](capability-declaration-model.ja.md), [Hierarchy of capability names](capability-name-hierarchy.ja.md) (all Japanese): the reasons for the decisions.
- [Serial ports and persistence](probe-cdc-and-persistence.ja.md) (Japanese): prototypes and measurements of several transports, settings, and boot modes.
- [Open proposals for v1](v1-open-proposals.ja.md) (Japanese): the proposals before the decisions, and how they were decided.
- [Answers to the review](review-answer-2026-09-26.ja.md) (Japanese): the third-party review.
- [host development guide](host-development-guide.ja.md), [probe development guide](probe-development-guide.ja.md) (Japanese): implementation practice.
