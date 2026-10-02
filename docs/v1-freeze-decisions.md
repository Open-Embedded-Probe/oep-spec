# v1 decisions before the freeze (2026-09-30) and the scope of the freeze (2026-10-02)

[日本語](v1-freeze-decisions.ja.md)

Status: **decided** (2026-09-30. §0 is the scope of the freeze added on 2026-10-02. The 3 ★ items were chosen by the user. The others proceed as proposed and are moved into the normative documents). The origin is the OEP share (13 items) of
"places that cannot be fixed later unless broken before the freeze", which bench (arduinocore) found by sweeping the whole ecosystem. Since it is before the freeze, every one changes form without raising the revision, and all tools
follow at once ([development guidelines](development-guidelines.ja.md) (Japanese)).

Each item: **proposal**, what changes, what follows. ★ marks items the user was asked to choose.

**Reflected in the normative text (2026-09-30, 1b7c93c)**: 1 (core §2.3, §2.7, the element length of list / scan / connections / marks / segments), 2 (probe-config
§2, the reason of storage), 3 (core §3.3, §7.5 unit_id, the address of probe-config, usb-identity), 4 (core §4.3, registry
`unavailable_payload`, no_connection of console), 5 (names, flags of status, rate, scale, logic-capture §8), 6 (core §11.3),
7 (oep-if-fixture §3 / §4, registry), 8 (console), 10 (core §7.5). The rest is implementation only: 9 (firmware.yml), 12 (the probe accepts label),
13 (the client's API), 11 (the reservations stay as the present documents have them).
The sequence of bind in 1 was missed, and was put into probe-config §1.2 on 2026-10-01 (len before each element, the same as sequences in answers).
12 changed with the zero-base re-examination of 2026-10-01: the label of the settings is not put in the core's describe but read with get of probe.config (describe is only a declaration).
3(b) (iProduct `OEP`) became permanent normative text, and 3(c) (the HID report) was reflected in a form that leaves it to the descriptor. The reference "probe-cdc §6 / §7" in 11 is
an error for open-proposals §6 / §7. Later decisions are in [the zero-base re-examination and the specification proposal](v1-zero-base-proposal.ja.md) (Japanese).

## 0. Scope of the v1 freeze (2026-10-02)

The v1 freeze stops the promises that let a host and a probe mesh even when they are made separately. What is stopped and what is not is written in one place.

### 0.1 What is frozen

| What is frozen | Where |
|---|---|
| The form of frames (COBS + CRC-16, `length(u16)`, the HID report, the order and length of headers, the 64 bytes before confirm) | [core](oep-core.md) §3 |
| The form of messages (the fixed parts of request / answer / event / data, the form of TLVs and the critical rule, reject reason, outcome, the order of refusals) | core §2, §4 |
| The payloads of the standard interfaces (the op tables, fixed parts, TLV tags, events, status, the lifetime of resources) | `oep-if-*.ja.md` |
| **Every number in registry/oep-v1.toml** (op, tag, reason, status, enum, `timing`, `limits`, `usb`, the names and revisions of interfaces). Values whose names start with `reference_` (`reference_vid`, `reference_pid`, `max_op_ms_reference`) are the reference firmware's values, not normative, and are not frozen | [registry](../registry/oep-v1.toml), generated files |
| The normative sentences of the core and `oep-if-*` (sentences of the form "does ..." / "does not ...". Including [dmseq](target-console-dmseq.ja.md) (Japanese)) | Each document |

To change these after the freeze, **raise the revision** (an interface that changes a fixed part or a meaning raises its revision; the form of the core raises the protocol
revision. core §2.7). Adding to the tail (optional TLVs, optional ops, events, the tail of sequence elements) can be done without changing the revision (§0.4).

### 0.2 What stays free after the freeze

| What is free | Where |
|---|---|
| The host development guide, the probe development guide, and the reference numbers in them (speed candidates, thresholds, frame counts, windows, examples of retry counts) | [host](host-development-guide.ja.md) (Japanese), [probe](probe-development-guide.ja.md) (Japanese) |
| Records of measurements (appending is free. The normative text does not take numbers from them) | [link measurements](link-measurements.ja.md) (Japanese), [UART speed](uart-speed-negotiation.ja.md) (Japanese), [capture](logic-capture.ja.md) (Japanese) |
| The contents and procedure of the tests before a release | [release-testing](release-testing.ja.md) (Japanese), oep-client-python `tests/hw/` |
| The behaviour of the fake (the false probe) where the normative text leaves it to the probe | oep-client-python `fake.py` |
| The client's policies (the order of candidates, how to wait, retry counts, the shape of the API), and the values the reference firmware declares (max_frame, window, max_op_ms, max_length) | Each implementation |
| Documents of reasons and history (including this document) | The list in core §15 |

### 0.3 What is fixed on purpose and not extended (reasons)

From §4 of the [zero-base re-examination](v1-zero-base-proposal.ja.md) (Japanese) and the ☆ of the [re-check](v1-zero-base-review-2026-10-02.ja.md) (Japanese). Places where we would like the freeze review
to look at "whether the reason holds".

| What is fixed | Reason | If it is needed |
|---|---|---|
| Frame headers (request 6 / 10 byte, answer 5 byte, notification 5 / 6 byte) | Changing them is a core revision. They can be negotiated with confirm, so the future path is not closed | Protocol revision |
| COBS + CRC-16 / `length(u16)` / the packing of the HID report | Decided per kind of path | A new transport kind defines its own scheme |
| op (u8), TLV tag (u8, bit 7 critical), reject reason (u8), event kind (u8) | If they run short, split the interface. Splitting by name is kinder to the host than widening the space | An interface with another name (another fn) |
| No len on the elements of sequences in requests | The host sends after knowing the probe from the revision and describe (principle 3). Additions are TLVs | Request TLVs |
| The fixed part of answers itself | Changing a fixed part is a revision + a new fn. Additions are TLVs ("there is one way to extend") | TLV, revision |
| The meaning of link_source / link_sink | For testing the wire. There is no reason to add meaning | — |
| The 64 bytes before confirm | A promise before negotiation. The smaller, the safer | — |
| The keys of the items of probe.config (slot u8, port u8, fn u16, channel u16) | Numbers within one probe. u8 / u16 is enough | — |
| ☆1 Do not add the host's receive limit to confirm | The amount of answers is decided by the host with the number in flight, and the amount of notifications by the host with min_bytes. Even if the probe knew the host's limit it would have no use for it (notifications have no ack) | A request TLV of confirm (non-critical) later |
| ☆2 max_frame stays the limit for both directions | The receive problem of serial ports is not one frame but the amount of a burst (the host rule of core §3.4) | — |
| ☆3 DFU / firmware update is outside OEP (core §0) | Everything is in the USB descriptors. If OEP held a copy it would diverge per version. unit_id = serial does not change, so the flashing side does not lose track of the unit | A named interface such as `oep.probe.firmware` |
| ☆4 Do not add a `max_count` declaration or a dedicated reason to read_block | It can be expressed with max_length (byte). The refusal was aligned to unsupported | address_hi is reserved (RV64) |
| ☆5 With port_speed the probe does not declare speed candidates | The speeds that work are decided by the conversion chip on the host side and are not visible from the probe. The candidates are the host's table | A "result of trying" in a request TLV later |
| ☆6 The actual baud on the bridge side (the deviation of integer division) is not exposed | A property of the host side that the probe cannot know. The baud of the answer being the actual value of the probe's UART is enough | — |
| ☆7 Ways of reducing round trips for block ops (batched reads over sysbus, etc.) are not added as ops | The meaning of read_block is "read through the target's bus", and the probe can choose the means | features bits of riscv-dm and op 0x09 onwards |
| Long operations, role 0x03 / 0x04, the u32 step of dmi, method 2 of reset, attach_under_reset of swd, 0x40 onwards of capture (§11) | Do not decide the form while there is no actual use | Defined later in the reserved numbers |

### 0.4 Paths for extension (what can be done without changing the revision)

| Path | Scope | Rule |
|---|---|---|
| TLV | The tail of requests / answers / events. The tag is a u8 per (fn, op) context (bit 7 critical. 0x00, 0x7F, 0xFF are reserved) | core §2.2, §2.3. The host skips unknown non-critical ones, the probe refuses unknown critical ones with unsupported |
| Adding to the tail | The tail of TLV values, event payloads, and elements of sequences in answers (`count × (len, element)`) | core §2.3. The reader skips the unknown tail; if short, the value is broken |
| op | The ops of an interface, 0x01 to 0xEF, are decided by its definition (0xF0 to 0xFF are for experiments). For the core, 0x50 to 0xEF are reserved | core §2.5. Whether an optional op exists is declared in describe |
| reject reason / status | 0x40 to 0x7F are decided by the interface | core §2.5, common §3 |
| Declaration tags of describe | 0x01 to 0x3E are the core's common tags, 0x40 to 0x7F the interface's. For fn 0, 0x40 onwards | core §7.4, §7.5 |
| Tags of the payload of unavailable / unsupported | Interfaces add 0x40 onwards | core §4.3 |
| Event kind | 0x01 to 0x7F per fn | core §2.5 |
| Items of probe.config | New tags, the tail of existing items | probe-config §1 |
| New interfaces | `oep.` is standard, independent ones are reverse DNS. A different name is a different fn | core §13 |
| New paths | Add a transport kind and define the scheme of its frames | core §3.1, §3.3 |

## A. Cross-cutting (deciding these lets the others move)

### 1. How fixed forms are extended (core §2)

The present rule is only "add after the sequence of TLVs", so **the fixed forms inside TLV values** (config items, describe values) and **the elements of sequences
with a count** (list, scan, connections, segment information) are frozen at their present length. A slot item has the lock at the end using the remaining length, so nothing can be added.

Proposal:
- Add a rule to core §2.3: **for a value with a fixed form (a TLV value, an event payload, a sequence element), if it is longer than the length the reader knows,
  the reader skips the unknown tail. The writer adds only to the tail** (the meaning and position of earlier fields do not change). If short, the value is broken.
- **A sequence of fixed-length elements with a count places the element length (u8) after the count**: `count(u8), size(u8), count × size byte`. The reader
  skips the unknown tail of each element. Applies to: the entries of list in the core, the entries of scan / connections in debug, the segment information of segments in capture.
- **Variable parts are preceded by a length and are not placed in the middle of a fixed form**: the slot item becomes `…, name_len, name, lock_len(u8), lock_scheme,
  lock_mask, lock_value` (lock_len = 0 is no lock), and what follows is the place for future additions. The same for the sequence of bind (place
  size on the elements after n).
- State explicitly in §2.7 that "adding to the tail does not change the revision". The form changes of 0.0.6 / 0.0.8 / 0.0.10 follow the pre-freeze policy, and after the freeze
  extension is done only by this rule.

Follows: client (decode), fake, probe (the writing side), ch32rv, wireskein (segment information), bench.

### 2. Saved settings and the list of interfaces (probe-config §2)

At present, the save carries a CRC of the whole list, and if it differs, none of it is applied. Adding even one interface erases the settings (the root of 0.0.11 to 0.0.16), and on a fixture
updated by DFU it silently stops taking effect. It also does not mesh with §2.7 (raise the revision).

Proposal:
- **The save holds (name, instance, revision) together for each fn the items point to**. At boot, look up that combination in the current list, rewrite the fn,
  and then apply it (the form of set (pointing by fn) does not change).
- If an interface pointed to does not exist, or the revision differs, **the whole save is not applied** (state 2 unreadable. Putting in only part would make the fixture behave half-way).
  Adding, removing or reordering interfaces that are not pointed to does not erase it.
- Add an "unreadable reason" to the storage state: 1 the form cannot be read, 2 an interface pointed to does not exist / the revision differs.

Follows: probe (the save form of OepConfig), fake, show of the client.

### 3. USB identification and the `oep://` address ★

- **(a) The probe part of the address** ★ **Decided: unit_id**. The proposal is **unit_id** (the unit id of describe. The same on every path). A USB probe **makes the serial number
  the same as unit_id** (it can be resolved without opening). The `-hs` of P4 is not appended (USJ has a different VID:PID, so even if serials collide they can be told apart).
  The address is `oep://<unit_id>/<slot name>`. The host looks by serial, and if not found, by the unit id of describe.
  **unit_id is 1 to 32 bytes of `a-z 0-9 -`** (the slot name is still `a-z 0-9 - _`). Neither needs encoding in a URL.
- **(b) The vendor bulk path**: write in core §3.3 that it is the 1 pair of bulk IN / OUT of the interface with `bInterfaceClass 0xFF` whose `iInterface` starts with `OEP`
  (the present client grabs "the first bulk pair", and misses when DFU or CDC comes first).
- **(c) The HID path**: write the usage page / usage, report ID and report length in core §3.3 (fixed at the values of the present implementation).
- **(d) After getting a PID**: the firmware only switches its VID:PID to 1209:4F45. Host discovery still looks at `OEP` of iProduct, so there is no effect.
  Hard-coded VID:PIDs in bench etc. are changed by then to look by serial (unit_id) or iProduct. Correct the iProduct of usb-identity to the present value.

Follows: probe (USB serial), client (discovery, how vendor is chosen), ch32rv, bench (toml, dfu.py), the values saved by the IDE of ArduinoCore-CH32.

### 4. The reason for rejected unavailable (core §4.3)

Proposal:
- **Make the payload of unavailable a sequence of TLVs defined by the core** (optional; the host skips unknown tags): 0x01 cause(u8: 1 the pin is
  in use, 2 a count limit, 3 not enough storage, 4 bound into a group, 5 held by the settings, 6 wrong state), 0x02 channel(u16),
  0x03 holder_fn(u16), 0x04 holder_kind(u8: 1 plan, 2 connection, 3 slot, 4 bind, 5 settings plan). Interfaces can add 0x40 onwards.
- An unknown resource (a connection or stream number) is **no_connection (0x0A) in every interface**. Correct "an unknown stream is
  unavailable" of console §1.

Follows: probe (attach cause and holder to the main refusals), fake, client (carry them in exceptions).

## B. Inside OEP

### 5. The capture family ★

- **Names** ★ **Decided**: `oep.fixture.logic` / `oep.fixture.analog` / `oep.fixture.capture-group` (at present only logic is
  `oep.fixture.capture`, which is asymmetric).
- Remove "the analog numbers are provisional" at the top of `oep-if-capture`, and close the open points of logic-capture.ja.md §8 (names, merging of mode, trigger stages, how roles are divided) with
  "v1 has this form": mode is 3, trigger is 1 channel 1 stage (stages and combinations later with types 0x40 onwards), role is 1 line 1 role.
- Define **the flags of status**: bit0 data was dropped inside the probe (queue / ring), bit1 the time base was bent (slipped). The others are reserved.
- **rate** stays integer Hz (state explicitly that below 1 Hz is out of range).
- Make **the analog zero and scale signed** (i32) (inverting frontends).
- The scheme string of calibration is frozen as the probe's namespace (wireskein keeps it in files).

Follows: probe, fake, client, wireskein (if the names change).

### 6. Subscription without the lock

Proposal: **v1 stays as it is** (only the holder of the lock subscribes). Read-only monitoring is done with bind (raw bytes). Subscription without the lock is written as reserved
(even if added later with a TLV, the present meaning does not change).

### 7. Names of the I2C / SPI devices ★

**Decided: make them standard**: `oep.fixture.i2c-target` / `oep.fixture.spi-target`. They are functions that are properly supported, so before the freeze a normative document
(adding sections to oep-if-fixture) is written and they are put in the registry. The ops and forms of the present independent interfaces are the basis, and the parts that depend on "esp32" are removed.

Follows: probe, client, bench.

### 8. The version of dmseq

Proposal: write in the console document: "the mechanism number determines the method exactly. To change the method, add a new number (3 onwards)".

### 9. firmware-<ver>.json of the Release

Proposal: add `"schema": 1`, and add `model` (the model of describe) and `chip` to each entry. `kind` is fixed to `merged` / `app` / `uf2`.
Follows: firmware.yml, bench.

### 10. The model / chip strings

Proposal: align them to **lowercase, no hyphens**. model is the chip (`esp32p4`, `esp32`, `rp2040`, `rp2350`), and the chip TLV is
`<model> v<rev>` (e.g. `esp32p4 v1.3`). This is the same as the Arduino profile names.

### 11. Reservations and deferrals

| Item | Proposal |
|---|---|
| Long operations (resolution 0x02, busy 0x05, core 0x20 to 0x2F) | Frozen as reserved |
| role 0x03 / 0x04 | Frozen as reserved |
| The u32 step of dmi | Stays reserved |
| method 2 of reset | Stays reserved |
| attach_under_reset of swd | Stays reserved (with a TLV when an SWD implementation needs it) |
| 0x40 onwards of capture | Stays reserved for separate definitions |
| IP settings, the recovery proposal (probe-cdc §6 / §7) | Not put in v1 (not made normative) |

### 12. The label item

Proposal: **the probe accepts it** (puts 0x02 in items of describe). The firmware saves label and puts it in the core's describe (0x46).

### 13. The client's public API

Proposal: decide the modules to make public and write them in the README (stop the re-export of `target.py`). The dataclasses of the settings items are keyword-only
(`Slot(slot=…, wire_fn=…)`). Write in the README that a firmware and client pair is "the same minor version".
