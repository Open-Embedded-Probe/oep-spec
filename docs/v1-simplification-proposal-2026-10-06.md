# OEP v1 simplification proposal (2026-10-06)

[日本語](v1-simplification-proposal-2026-10-06.ja.md)

Status: **proposal** (not normative). It answers the [external review of 2026-10-06](external-spec-review-2026-10-06.ja.md) item by item and proposes changes to the normative text and the registry. Nothing here takes effect until the user decides and the change is made in `docs/oep-*.md` and `registry/oep-v1.toml`. This English text is authoritative; the Japanese version is its translation.

## 0. Summary

The review is a reference, not a list of orders: we adopt what makes OEP smaller and simpler while keeping it extensible, and reject what adds machinery without a clear interop gain. Breaking changes are allowed before the freeze (no revision is raised; versioning §2).

Numbering: "review 5.1" names the reviewer's item; the sections here answer review §3 in 2.x, review §4.2 in 3.1, review §5 in 4.x, and review §7 / §8 in 6.x (review 5.1 is answered in 4.1, review 5.2 in 4.2, and so on).

The target, in one sentence (the reviewer's words): **fixed forms are kept by revision, compatible additions are TLVs, different meanings are separate interfaces.**

| Review item | Recommendation | Wire change | Breaking |
|---|---|---|---|
| 3.1 answer sequence len vs op tables | Adopt, through 5.1: no element len anywhere; one rule `count × element` | Yes | Yes |
| 3.2 SDI / DMDATA "(Reference)" | Adopt: plainly normative; drop the origin notes (also the one in debug) | No | No |
| 3.3 revision 1 before the freeze | Adopt partly: decide versioning §6, state the tag; no runtime edition field | No | No |
| 3.4 HID reassembly | Adopt: one byte stream, rules for count 0, padding, report ID, gaps | No | No |
| 3.5 external specifications | Adopt: a references section per interface; scope the "text alone" claim | No | No |
| 3.6 answer enum additions | Adopt partly: three conditions; no capability opt-in | No | No |
| 3.7 probe.config paging sentence | Adopt (wording) | No | No |
| 3.8 scan with no candidate | Adopt: completed success, tried 0, count 0 | No | No |
| 4.2 interface template | Adopt partly: a checklist in core §13 now; a template guide later | No | No |
| 5.1 four extension paths only | Adopt; the trailing optional fields are folded into the fixed part | Yes | Yes |
| 5.2 no resources after end, no resume | Adopt | Yes | Yes |
| 5.3 one request header | Adopt partly: one 10-byte header with session_id (0 = none); corr stays u16 | Yes | Yes |
| 5.4 one TLV header | Adopt: `tag(u8), len(u16), value` | Yes | Yes |
| 5.5 common optional-op declaration | Adopt: describe common tag `ops` (base + bitmap) on every fn | Yes | Yes |
| 5.6 core / transport split | Adopt: three files; move link test and port_speed to `oep.link` (user decision D3) | Yes (D3) | Yes (D3) |
| §7 test gaps | Adopt partly: per-op byte vectors and session / resend / paging scenarios; timing and electrical stay release tests | No | No |
| §8 priorities | Adopt the order; three items move before the freeze, corr u32 is dropped (6.2) | — | — |

## 1. Premises shared by every item

- **Who the users are.** We judge by what many unspecified users need: a third party writing a host or a probe from the documents alone, a user who runs one CLI command after another, an IDE that starts a tool per action, a test fixture that runs unattended. Today's benches are inputs, not the target.
- **The freeze policy.** Before the v1 freeze, breaking changes go in without raising any revision, and no compatibility or migration notes are written (versioning §2). After the freeze the forms are fixed and only the paths of 4.1 remain.
- **The implementations that follow the spec**: oep-probe-arduino (the reference probe), oep-client-python and its fake probe, oep-client-js, ch32rv (a Rust host in `crates/oep`, a CLI, a relaying broker in `cli/src/broker.rs`, and a WCH-Link endpoint in `cli/src/broker_wch.rs`, which answers OEP itself and so is a probe under core §3.1), WireSkein (uses the Python client), and the bench (uses the clients; its probes hold saved settings).
- **The order of work** stays: spec, peers' review of the diff, fake, probe, clients.
- **Bytes on a UART bridge** are counted in §5, so that every simplification is weighed against bandwidth at the boot speed of 115200 bps.

## 2. Interoperability items (review §3)

### 2.1 Review 3.1: answer sequences, len or no len

**Premise.** Core §2.3 says every element of a sequence in an answer is preceded by its length: `count(u8), count × (len(u8), element)`. The len exists so that a later version can append fields to an element and an older reader skips them (the "append at the end" path of §2.3). The op tables use the len only for structured elements (list entries, connections entries, scan entries, marks, console streams, capture segments, probe.config slot_state and bind_state, bind items) and not for scalar arrays (gpio read's levels, dmi's and arm-adi transfer's values, read_block's words, run's values). A third party who reads the core first adds a len to the scalar arrays and cannot talk to any existing implementation. The existing implementations follow the op tables, so nothing breaks for them today; the risk is to every new implementation.

**Recommendation: adopt, through review 5.1 (4.1).** Remove the element len everywhere, so that one rule covers every sequence: `count, count × element`, with the element's form fixed by the revision. Every structured element is already self-delimiting (its variable parts carry their own length), so the len carries no information once tails are not extended. This removes the contradiction and one extension path in the same step.

If review 5.1 is not adopted, the smallest fix is text only: core §2.3 says the len precedes an element only where the op table writes `(len(u8), …)`.

**Changes.** The new layouts are in 4.1. Breaking: yes (the answers of list, connections, scan, marks, streams, segments and probe.config state; the bind item). Impact: as 4.1.

### 2.2 Review 3.2: SDI and DMDATA are normative

**Premise.** Core §1.1 defines (Informative), examples and notes as non-normative. Console §3.1 and §3.2 open with "(Reference) This is the layout of WCH's SDI printf" and "(Reference) This is the framing the minichlink tool uses", a marker the core does not define. The Japanese translation writes both as （参考）, which Japanese core §1.1 defines as non-normative, so in Japanese the only definitions of mechanisms 0 and 1 read as non-normative. The same marker opens debug (line "(Reference) RVSWD and SWIO are the 2-wire and 1-wire debug wires of WCH's RISC-V MCUs…"). Our own writing rules also keep chip and tool names out of normative text.

**Recommendation: adopt.** The definitions of mechanisms 0 and 1 are normative as written. Delete the two origin sentences in console and the one in debug (the history is not needed to implement them; the records keep it). The registry key `wch_dmi_7f` stays: it is an identifier, and the text defines it as the u32 at DMI 0x7F.

By our reading, §3.1 and §3.2 already define both sides (what the target writes, what the probe reads, writes and when); the peers are asked to confirm that nothing in their implementations comes from outside the text.

**Changes.** Text only: console §3.1, §3.2 and the debug header line, in English and Japanese. Not breaking. Impact: no code.

### 2.3 Review 3.3: two "revision 1" implementations may not interoperate

**Premise.** Before the freeze, breaking changes go in without raising a revision (user decision), so two implementations built from different commits can both say revision 1 and still not interoperate. Versioning §6 proposes tags; the user decided on 2026-10-06 that spec tags stay `v0.x` through the freeze and `v1.0.0` is the formal release.

**Recommendation: adopt partly.**
- Make versioning §6 decided rather than proposed: tags `v0.MINOR.PATCH` until the formal release, the freeze is a `v0` tag named in CHANGELOG, `v1.0.0` is the formal release; a tag only on a commit whose generators and vectors pass; every normative or registry change gets a CHANGELOG entry.
- Add one sentence to the status line of every normative document: "Before the freeze, revision 1 alone does not identify a form: an implementation names the specification tag it implements."
- Each implementation states the tag in its README, and a probe may also put it in the free text of fn 0 describe `firmware` (0x40).
- **Reject** a runtime edition field (in the registry or in confirm): after the freeze the revision is the only thing that identifies a form, so the field would mean nothing for the life of the protocol; before the freeze the free text already carries the tag for diagnosis.

**Changes.** Text: versioning §6, the status lines, each implementation's README. Not breaking. Impact: README lines in every repository; optional firmware text in the probe and in broker_wch.

### 2.4 Review 3.4: HID reassembly

**Premise.** Core §3.1 says the bytes of length-prefixed frames are packed into reports of `count(u16)`, count bytes and zero padding, and that a report whose count is larger than the report can carry is discarded. It does not say whether frames may span reports, whether a report may hold more than one frame, what count 0 means, what a receiver does with non-zero padding, which report ID is used, or what happens when a frame stops in the middle. The Python client (`hid_stream.py`) and ch32rv (`crates/oep/src/hid.rs`) already treat the reports as one stream.

**Recommendation: adopt** (text only). Replace the HID row and add:

1. The OEP bytes of a report are the count bytes after count. Concatenated in report order, per direction, they form one length-prefixed byte stream, the same stream as on vendor bulk.
2. A frame may span reports, and a report may hold the end of one frame and the start of the next. A sender may start each frame in a new report; a receiver does not rely on it.
3. A report with count 0 is empty and is skipped.
4. The sender sets the padding to 0. The receiver ignores the padding whatever its value.
5. The OEP HID interface declares either no report ID or one report ID, used by its input report and its output report. When it declares one, every report in both directions starts with it, and count is counted from after it. A receiver discards a report that starts with another ID.
6. The gap rule of §3.2 applies to the stream: when a frame is incomplete and no report arrives for 200 ms (`probe_frame_gap_ms`), the probe discards the incomplete frame and reads the next byte as the start of a length. The host recovers by §5.1.
7. A report whose count is larger than the report can carry is discarded, and the receiver treats the stream as broken: it discards input until a gap of 200 ms, as for a length larger than max_frame.

**Changes.** Text only (the HID part of the transport document, 4.6). Not breaking. Impact: the probe (if it exposes HID), the Python client and ch32rv check that they behave so; no change is expected.

### 2.5 Review 3.5: external specifications

**Premise.** The OEP messages can be implemented from the repository alone. Driving a target cannot: swd and arm-adi rely on the Arm Debug Interface, riscv-dm and the wires on the RISC-V debug specification, i2c-target on the I2C-bus specification. The text names some of them without a version. Fixture spi-target says "SPI mode 0 to 3" without defining the modes (the same gap, found while checking this item).

**Recommendation: adopt** (text only).
- Core §0 says: "The OEP protocol is defined by these documents alone. Driving a target also needs the external specifications that each interface document lists."
- Each interface document gets a short "References" section naming the document, its version and the subset used. Proposed entries (the editor confirms the versions):

| Interface | External specification | Subset used |
|---|---|---|
| `oep.wire.swd`, `oep.target.arm-adi` | Arm Debug Interface Architecture Specification ADIv5.2 and ADIv6.0 | SWD packets, turnaround, line reset, JTAG-to-SWD switch, dormant wake, TARGETSEL; DP / AP registers; MEM-AP TAR / DRW / CSW |
| `oep.wire.rvswd`, `oep.wire.swio`, `oep.target.riscv-dm`, `oep.target.console` | RISC-V Debug Specification 0.13.2 and 1.0 (DMSTATUS.version 2 and 3) | DMI registers, abstract commands, program buffer, dcsr, havereset; the wire frames themselves are defined in the text |
| `oep.fixture.i2c-target` | I2C-bus specification (UM10204) | Addressing, ACK, clock stretching, the reserved addresses |
| `oep.fixture.spi-target` | None (no formal standard) | Define the modes in the text: mode = CPOL × 2 + CPHA |
| core transports | USB 2.0, USB CDC ACM, HID 1.11, Microsoft OS 2.0 descriptors | Enumeration, interface descriptors, reports |

**Changes.** Text only. Not breaking. Impact: no code.

### 2.6 Review 3.6: answer enum values added without a revision

**Premise.** Core §2.5 lets any unused enum value or reserved bit be defined later. For a request this is safe: an older probe refuses the value unsupported. For an answer, an older host receives a value it does not know; core §2.4 tells it to treat unknown status, reason and outcome as failure and to show the other enums as unknown. That is safe only when the unknown value does not change how the rest of the answer is read.

**Recommendation: adopt partly.** A value may be added to an answer enum without a revision only when all three hold:
1. no field's presence, length or position depends on the value;
2. the fallback of core §2.4 (failure for outcome, status and reason; "unknown" for the others) is safe;
3. every field whose meaning depends on the value is defined as ignored (or shown raw) by a reader that does not know the value.

Otherwise the addition is a new TLV, a new revision or a new interface. **Reject** the opt-in by capability: requests already opt in (the host chooses to send the value), and for answers condition 2 makes the fallback safe; a declaration per value would add machinery to every interface. Every answer enum in v1 already meets the three conditions (scan's kind decides only the meaning of id, a mark's kind only the meaning of detail, tid_scheme only the meaning of tid, whose length tid_len carries).

**Changes.** Text: core §2.4 / §2.5 (with 4.1), versioning §4. Not breaking. Impact: no code.

### 2.7 Review 3.7: the probe.config paging sentence

**Premise.** Probe settings §3.3 ends with "… a host that needs the set of slots and binds to stay the same across its pages pages while it holds the lock …", which has lost its verb.

**Recommendation: adopt** (wording): "A host that needs the set of slots and binds to stay the same across its pages reads all of its pages while it holds the lock (the states of the slots may still change)." Holding the lock is enough: only the holder can set, unset, save or erase, and the automatic attach changes the states, not the set. Text only; not breaking; no code.

### 2.8 Review 3.8: scan with no candidate

**Premise.** Debug §1 says "at least one combination is tried" and "tried = 0 only when the sequence is used up". It does not say what happens when the count = 0 sequence is empty from the start (every candidate is held, disabled or has an idle item, or skip is at or beyond its length).

**Recommendation: adopt.** Add: "When the count = 0 sequence has no combination from skip on (it is empty, or skip is at or beyond its length), the answer is completed success with tried = 0 and count = 0. The rule that at least one combination is tried applies only when a combination remains." This is the answer a host's continuation loop already stops on, and it needs no new refusal. A request that lists combinations is unchanged (a held channel is rejected unavailable).

**Changes.** Text only. Not breaking. Impact: the probe and the fake check that they answer so (and do not reject); hosts need nothing.

## 3. Extensibility (review §4.2)

### 3.1 Review 4.2: a template for an interface

**Premise.** Core §13 rule 2 lists what an interface definition decides, but not its own status values, the payloads of completed failed and partial, the handling of unknown enum values and flags, or a refusal table in the order of §4.3. The reviewer counts nine extension paths today; 5.1 reduces them.

**Recommendation: adopt partly.** Extend core §13 rule 2 into a checklist that every interface document fills in: name and revision; op table (request, answer, lock, required or optional; optional ops are declared by the `ops` tag, 5.5); request and answer TLVs per op; the payloads of completed success, failed and partial; interface status values (0x40 to 0x7F) and reject reasons (0x40 to 0x7F); resources and their lifetime; events and data payloads; how a reader treats unknown enum values and flags (2.6); a refusal table in the order of §4.3. A template document (a guide with empty headings) can follow after the freeze; it adds no rule.

**Changes.** Text: core §13. Not breaking. Impact: no code; the existing interface documents are checked against the list.

## 4. Simplification (review §5)

### 4.1 Review 5.1: four extension paths only

**Premise.** Today a reader implements several forward-compatibility rules: skip the unknown tail of an answer TLV's value, of an event's fixed payload, of an element of an answer sequence and of a probe.config item, and keep the unknown tail of an item without truncating it; while describe values, request TLV values and the link test's answer are closed exceptions. The tail path was chosen so that a minor version could add a field without the 2 to 3 bytes of a TLV header. Nothing has ever been added that way after a freeze, because there has been no freeze; so nothing depends on it, and every reader pays for it now.

**Recommendation: adopt.** After the freeze, OEP grows only by:
1. **a new TLV** (in a request, an answer, an event, data, describe, or a new probe.config item tag);
2. **a new optional op** (declared by `ops`, 5.5) or a new event kind;
3. **a new value in a reserved space** (a request value an older probe refuses unsupported; an answer value only under 2.6);
4. **a new interface name** for a new meaning, and **a new revision** for a changed fixed form.

Every fixed form (the fixed part of a request, answer, event or data payload, a TLV value, an element of a sequence, a probe.config item) is fixed by (name, revision). Information that would have been appended to an element of a sequence goes into an answer TLV that repeats with the element's index (the pattern gpio's drive TLV already uses).

**The trailing optional fields added before the freeze: fold them into the fixed part.** They are part of revision 1 and known now; a TLV inside a probe.config item (which is itself a TLV) would need nesting; and fixed lengths make the canonical form unique. Today a slot sent with boot_reset 0 and the same slot sent without it are the same setting, but since the probe keeps the bytes as sent, they give two different hashes. The search ("optional trailing", `[…]` fields and "place for fields added later") finds three: slot `boot_reset`, idle `drive_kind`, `drive_value`, and slot_state `reset_at_ns` (always present, but added as a tail).

**Exact new layouts.**

```text
core list answer:        total(u16), count(u8), count × entry
  entry:                 fn(u16), instance(u16), revision(u8), flags(u8), name_len(u8), name
wire connections answer: more(u8), count(u8), count × entry, [TLV]
  entry:                 connection(u16), swdio(u16), swclk(u16), speed_hz(u32), users(u8), slot(u8), tid_scheme(u8), tid_len(u8), tid
wire scan answer:        tried(u8), count(u8), count × (kind(u8), swdio(u16), swclk(u16), id(u32)), [TLV]      element 9 bytes
marks answer:            more(u8), count(u8), count × mark, [TLV]                                               mark 22 bytes, unchanged
console streams answer:  more(u8), count(u8), count × (stream(u16), connection(u16), mechanism(u8), users(u8), state(u8)), [TLV]
capture segments answer: more(u8), count(u8), count × segment, [TLV]                                            segment 37 bytes, unchanged
probe.config state answer:
                         more(u8), storage_state(u8), storage_hash(u32), unreadable_reason(u8),
                         n_slots(u8), n_slots × slot_state, n_binds(u8), n_binds × bind_state, [TLV]
  slot_state:            slot(u8), state(u8), connection(u16), last_try_at_ns(u64), reset_at_ns(u64), tid_scheme(u8), tid_len(u8), tid
  bind_state:            port(u8), mode(u8), selected(u8), flow(u8)
probe.config items:
  idle (0x03):           channel(u16), mode(u8), drive_kind(u8), drive_value(u16)                               6 bytes
  slot (0x04):           slot(u8), wire_fn(u16), swdio(u16), swclk(u16), attach(u8), boot_reset(u8), retry_ms(u32),
                         max_speed_hz(u32), idle_clock(u8), mechanism(u8), name_len(u8), name,
                         lock_len(u8), [lock_scheme(u8), lock_mask(n), lock_value(n)]    (the lock part is present when lock_len > 0)
  bind (0x05):           port(u8), mode(u8), selected(u8), n(u8), n × (kind(u8), id(u16))
unset request:           unchanged: n(u8), n × (len(u8), tag(u8), key)   (len is the length of a variable key, not a tail)
```

- idle: `drive_kind` 0 = level, 1 = mA ceiling, **2 = default** (the default level of drive_levels; drive_value 0). Mode 0 to 2 carries kind 2 and value 0 (anything else is malformed). The value 2 is added to the shared `drive_kind` enum, so gpio set's drive TLV may also name the default level explicitly. A probe without drive_levels keeps the field and applies the default, as now.
- slot: `boot_reset` moves next to `attach` (fixed fields before variable ones). 0 no, 1 yes; 2 or more malformed; 1 on a host slot malformed (as now).
- slot_state: `reset_at_ns` moves before the variable `tid`.
- The rule "the probe keeps the bytes of the items as sent, unknown trailing fields included" is removed: an item has one form per tag, and a longer value is a request TLV longer than known (core §2.3).
- The link test gets counted forms, so that the exception of §2.3 ("a form ending in a variable part without a length") and the registry key `closed_tail` disappear: `link_source` answer `len(u16), data, [TLV]` (byte k is k & 0xFF, as many as fit); `link_sink` request `count(u16), data`, answer empty (a count that does not match the payload is malformed).

**Text and registry.** Core §2.3 is rewritten around the four paths (the paragraphs "How fixed forms are extended" and the describe exception go); §2.4 / §2.5 get the conditions of 2.6; §2.7 drops "the append at the end does not change the revision"; versioning §3.1 / §4 follow. Registry: `closed_tail` removed from the schema and from fn 0; `drive_kind` gains `default = 2`; the comments of `idle`, `slot` and `slot_boot_reset` follow. Breaking: yes.

**Impact.**
- oep-probe-arduino: the encoders of list, connections, scan, marks, streams, segments and state drop the len; the idle, slot and bind parsers take the fixed forms; the saved-settings layout changes, so saved settings read as unreadable (reason 1) after the update and are entered again.
- oep-client-python and the fake: the same decoders and encoders; the probe.config hash vectors are regenerated.
- oep-client-js: the same decoders.
- ch32rv: `crates/oep` (config.rs reads slot_state without reset_at_ns today, relying on the len to skip the tail: it now reads the field before tid; target.rs and stream.rs for connections, scan and marks); broker_wch's encoders for the same answers.
- WireSkein: none directly (segments are read through the client).
- bench: reflash, then enter and save the settings again.

### 4.2 Review 5.2: no resources after end, no implicit resume

**Premise.** Today (core §6.2, §6.4, §9) `end` releases the lock but keeps the session's resources (plans, shares of connections and streams); they move to whatever session opens next, whatever its id. An ordinary request with the last session_id after end re-establishes the lock (resume); an `open` with that id answers resumed 1; after lease expiry the resources are removed, requests are rejected `expired`, and an open with that id answers resumed 2. The probe therefore keeps the last session_id, how its lock ended, its owner and the resend table, and the decision table has ten rows. The reason given in the core and in console §2: a host that runs one command per process (ch32rv's CLI) can let the next process pick up where the last one stopped.

What the implementations actually rely on:
- **Resume by id**: the Python client's `open(session=…)` exists for "a one-shot CLI resuming its saved id", but no caller passes it (not its CLI, not WireSkein, not ch32rv). ch32rv opens every command with a new random id.
- **Handover after end**: ch32rv's `flash` ends without detaching ("the connection stays for the next open"), so the next command's attach joins the live connection (flags bit1) instead of a new bring-up. Its other commands detach before end.
- **expired / resumed 2**: ch32rv's broker reopens with the same id after `expired` and opens a new id after `no_session`; both lead to the same action (open again, rebuild).
- WireSkein releases its plans before end and relies on nothing.

**The general-user case.** What must survive between two commands of a user, and how it survives without the handover:
- the target's state (halted or running): closing a connection never changes the target (debug §2), so it survives anyway;
- the console's output: stream positions and marks never go back within a boot, and an open at the same place returns the same stream number (console §2), so a later command reads from where the last one stopped; reading the target while no command runs is the job of a slot with a bind, which the probe owns;
- pins that must stay driven (a power switch): a settings plan and an output idle, which the probe owns;
- a fast attach: lost. Each command does its own bring-up, at most `attach_budget_ms` (1000 ms), unless a slot keeps the connection.

The handover also has a cost for general users: what a crashed or careless host leaves after end (a plan driving pins, a halted connection) silently becomes the next, unrelated host's, which did not create it. Releasing at end leaves only what the settings define, which any host can read with get and state.

**Can the reviewer's alternative serve the one-command-per-process host without the resume machinery? Yes.** The explicit path already exists: an attach to a live combination returns that connection (flags bit1), and a console open returns the existing stream (flags bit0). A connection a slot uses survives every end, so a user who wants the fast attach across commands registers a slot. ch32rv's `flash` loses only the saved bring-up.

**Recommendation: adopt.** The probe-owned resources are those of the settings (plans, idle, slots, binds); everything a session creates is released when its lock ends, whatever ends it.

**Changes.**
- `open` answer: `lease_ms(u32), boot_id(u32), [TLV]` (resumed removed).
- `end`, lease expiry and force release the same things: the session's plans (pins go to idle), its shares of connections and streams (a resource closes when no user remains), its subscriptions. Debug §2's state machine merges the rows end and lease expiry / force; common §2 and console §2 say "when the session ends".
- Reject reason `expired` (0x0E) becomes reserved. A request whose session_id is not the holder's, with the lock free, is rejected `no_session`; the host opens again.
- The resend table (§5.2) stays keyed by the last session's id and is discarded at the next successful open, so a resent `end` is still answered from it.
- The decision of §6.2 (after the resend table):

| Lock | Request | Result |
|---|---|---|
| Free | open (session_id ≠ 0, with or without force) | Establish the lock |
| Free | any other request with session_id ≠ 0 | rejected no_session |
| Held by S | open with session_id S | Restart the lease; nothing is removed; notifications go to this transport (a resent open) |
| Held by S | open with another id, no force | rejected locked (remaining time, owner) |
| Held by S | open with another id, force | Release S's resources (§9), establish the lock |
| Held by S | other request with S | Process |
| Held by S | other request with another id | rejected locked |

- The owner is kept while the lock is held.
- Core §6.5 drops the inference "an open with the last id answered resumed 0 means a reboot"; the host relies on boot_id in the open answer (a probe with only the weak boot_id source keeps the stated probability).
- The mark detail closed 2 becomes "the session ended (end, lease expiry, force)".
- Registry: core enum `resumed` removed; `expired` → reserved; `mark_detail_closed` 2 renamed `session_ended`.
- Text: core §6.2, §6.4, §6.5, §9; common §2; console §2; debug §2; host guide §6 and §9; conformance.

Breaking: yes.

**Impact.**
- oep-probe-arduino: simpler endpoint (the swept / expired / resume paths go; end calls the same release as a lapse).
- oep-client-python and the fake: `Opened.resumed`, `Expired` and `open(session=…)` go; the fake follows.
- oep-client-js: the same.
- ch32rv: session.rs (resumed / swept), broker.rs (keepalive's `expired` path merges into the `no_session` path, which opens a new id; the broker's own open answer drops the resumed byte), the CLI's `flash` (every command now attaches again).
- WireSkein: none (one docstring names Expired).
- bench: ask whether any script relies on a plan or connection surviving between processes.

### 4.3 Review 5.3: one request header

**Premise.** Today a request is `role 0x01, corr(u16), fn(u16), op(u8)` (6 bytes) or, with bit 7 of the role set, the same followed by session_id(u32) (10 bytes); `open` alone carries its session_id in the payload and is sent with role 0x01. The two forms save 4 bytes on lock-free requests (console polls by a monitor, discovery). corr is u16 and compared by serial-number arithmetic (§2.6) to tell a resend from an old request the table no longer holds.

**Recommendation: adopt partly.** One header for every request, with session_id always present (0 = no session); corr stays u16.

```text
request   role=0x01 | corr(u16) | fn(u16) | op(u8) | session_id(u32) | payload        header 10 bytes
answer    role=0x02 | corr(u16) | resolution(u8) | detail(u8) | payload             header 5 bytes (unchanged)
event     role=0x05 | fn(u16) | seq(u16) | kind(u8) | fixed part | [TLV]               unchanged
data      role=0x06 | fn(u16) | seq(u16) | position(u64) | len(u16) | data | [TLV]    unchanged
open      request payload: lease_ms(u32), force(u8), [TLV owner]   (its session_id is the header's; 0 is malformed)
          answer: lease_ms(u32), boot_id(u32), [TLV]               (5.2)
```

- A lock-required op with session_id 0 is rejected session_required. A lock-free op with session_id 0 is processed without the session checks; with a non-zero id it goes through §6.2 and restarts the lease, as role 0x81 does today.
- Role 0x81 no longer exists (bit 7 of the role is reserved; an unknown role is discarded, §2.4). A request shorter than 10 bytes is discarded. "The 0x81 requests of a session" in §3.3 and §3.4 become "the requests with that session's id".
- open is never looked up in the resend table (as today: a resent open is handled by the row "held by S, open with S").
- **Reject corr u32.** It would not remove the serial-number arithmetic: notification seq (u16) and the serials of marks and segments still wrap (§2.6). It costs 2 bytes on every request and every answer. Within one session the table holds only max_inflight entries, far inside the quarter-range rule of §2.6.

**Byte cost** (§5): +4 bytes on lock-free requests only; locked requests and every answer are unchanged.

**Changes.** Core §2.4, §2.5 (role), §3.3, §3.4, §4.1, §5.2, §6, §12; registry `role_session_flag` removed; vectors `headers.json`. Breaking: yes.

**Impact.** Every codec: oep-probe-arduino, oep-client-python and the fake, oep-client-js, ch32rv (`codec.rs`, the broker's relay and broker_wch's parser). WireSkein and the bench: only the client update.

### 4.4 Review 5.4: one TLV header

**Premise.** Today a TLV is `tag, len(u8), value` for values of 0 to 254 bytes and `tag, 0xFF, len(u16), value` for 255 or more, and the encoding must be the unique one. Values of 255 bytes or more are rare (a role_channels bitmap of a large probe, capture's factory calibration raw), so the long path is the one least exercised and most likely wrong in a new implementation.

**Recommendation: adopt.** `tag(u8) | len(u16) | value`, always. One parser, no boundary and no canonical-form rule; every path is exercised by every TLV. The cost is 1 byte per TLV, and the hot traffic carries almost none (§5).

**Changes.** Core §2.2 (the short / long forms, the uniqueness rule and the escape go); `ignored` is at most 19 bytes (tag, len, 16 entries) and the minimal one is `7F 01 00 00` (4 bytes), so the room the probe keeps becomes 19 bytes; tag 0xFF stays invalid; registry `tlv_len_long` removed; the probe.config canonical form and its hash change (vectors regenerated). Example, max_speed 1 MHz sent critical: `81 04 00 40 42 0F 00`. Breaking: yes.

**Impact.** Every codec (probe, Python client and fake, JS client, ch32rv `codec.rs` and broker_wch); the saved settings of every probe are entered again (with 4.1); the bench re-saves.

### 4.5 Review 5.5: one declaration of optional ops

**Premise.** Core §1.2 lets each interface name what declares each optional op. Today:

| Interface | Optional ops | Declared by today |
|---|---|---|
| `oep.core` | plan_apply 0x04, plan_release 0x05 | Any interface having plan roles |
| `oep.core` | port_speed 0x14 | fn 0 describe tag 0x4E |
| `oep.target.riscv-dm` | reset 0x04, read_block 0x05, write_block 0x06, run 0x07, step 0x08 | features bit2, bit0 (both block ops), bit1, bit3 |
| `oep.fixture.i2c-target` | stretch 0x07 | features bit1 |
| `oep.fixture.logic`, `oep.fixture.analog` | query 0x09, force 0x04 | features bit0, bit1 |
| `oep.fixture.capture-group` | force 0x04 | features bit1 |
| `oep.probe.config` | save 0x03, erase 0x04 | storage max_bytes > 0 |

A host needs per-interface code even to know whether an op exists, and a conformance tool cannot check "unknown_operation exactly when not offered" generically.

**Recommendation: adopt.** A common describe tag `ops` (0x09): `base(u8), bitmap`; bit i set means op base + i is offered. Every fn's describe carries it, fn 0 included. Every required op is set; an op that is not set is answered unknown_operation; experimental ops (0xF0 to 0xFF) are never set. `features` keeps only optional functions that are not ops (modes, formats, notifications, internal pull-ups, attach_writes_unbounded).

Examples: riscv-dm with every op, `09 02 00 01 FF`; with dmi, halt and resume only, `09 02 00 01 07`. fn 0 with plan ops and without the link ops (5.6): `09 08 00 01 1F 80 07 00 00 80 02` (ops 0x01 to 0x05, 0x10 to 0x13, 0x30, 0x32).

**Changes.** Core §1.2 (one declaration for every optional op), §7.4 (tag 0x09). Registry: `describe_common.ops = 0x09`; remove riscv-dm features block, run, reset, step; i2c-target features stretch (bit1 reserved); logic and analog features query, force (bits 0 and 1 reserved); capture-group features force; fn 0 describe `port_speed` 0x4E. probe.config: the storage tag is present exactly when save is offered, and its max_bytes is 1 or more. Breaking: yes.

**Impact.** oep-probe-arduino and the fake emit `ops` per fn; the Python and JS clients test the bitmap instead of the features bits; ch32rv `speed.rs` (port_speed by the bitmap) and broker_wch (declares riscv-dm features 0x7 today: it emits `ops` instead); WireSkein through the client (capture query / force).

### 4.6 Review 5.6: separate the core from the transports

**Premise.** `oep-core.md` holds the message core and also the USB descriptors, vendor bulk ZLP, HID packing, the serial raw-byte multiplex, UART port speed and the link test. A minimal implementer reads all of it. The core's own rule 2 says that what can be a named interface using only the core's mechanisms does not go into the core; the link test and port_speed are such things.

**Recommendation: adopt.** Three normative files:

| File | Contents |
|---|---|
| `docs/oep-core.md` | Scope and layers, terms, conformance, common rules and the extension paths (4.1), messages, resend, sessions, discovery, plan, resources, notifications, fn 0's op table, the rules and checklist for interfaces (3.1). The host's wait keeps its floor and refers to the transport document for the transfer time |
| `docs/oep-transports.md` | The frames (COBS + CRC-16 on serial ports; the length-prefixed stream on vendor bulk and TCP; HID as a packing of that stream, 2.4), sending and gaps, several transports, USB identification and port choice, serial-port sharing and raw bytes, the host's receive capacity, delimiting recovery (§5.1), the UART bridge line, its boot speed and the confirm repetition after a raised speed, the transfer time of the wait |
| `docs/oep-if-link.md` | `oep.link` (D3): the link test and port_speed |

The Japanese versions follow (`.ja.md`). The other `oep-if-*.md` are unchanged. The split is done in a separate commit after the content changes, so that the peers review the rules and the move separately.

**`oep.link` (user decision D3).** An optional standard interface, revision 1:

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x01 | source | length(u32) | len(u16), data (byte k = k & 0xFF), [TLV] | Not required | yes |
| 0x02 | sink | count(u16), data | — | Not required | yes |
| 0x03 | port_speed | port(u8), baud(u32), step(u8), verify_ms(u16), idle_ms(u32), [TLV] | baud(u32), [TLV] | Required | optional (`ops`) |

A probe that offers port_speed lists `oep.link`. The handshake, states and return conditions of today's §3.5 move unchanged; the host obligations that apply whether or not the probe has `oep.link` (repeating confirm after a raised speed, the transfer time) stay in the transport document. The minimal probe no longer has to implement the link test. Breaking: yes (fn 0 loses ops 0x14, 0x40, 0x41 and describe 0x4E).

If D3 is not adopted, only the files are split: the link test and port_speed stay in fn 0, in the transport document, with the counted link-test forms of 4.1.

**Impact.** Documents and links (glossary, conformance, guides). With D3: the probe moves the handlers to a new fn; the Python and JS clients' link test and speed procedures list `oep.link` first; ch32rv `speed.rs` and `link.rs`; the bench's link measurements through the clients.

## 5. Byte costs on a 115200 bps UART bridge

Counting: a frame on the wire is the message + 2 (CRC) + 1 (COBS code per 254 bytes) + 2 (the two 0x00) bytes. At 115200 bps 8N1 one byte takes 86.8 µs (11520 bytes/s). "Proposed" is 4.3 and 4.4 as recommended (corr u16); "reviewer" is 4.3 with corr u32.

| Traffic (one round trip) | Today | Proposed | Reviewer (corr u32) |
|---|---:|---:|---:|
| Console poll by a lock-free monitor (read, empty answer): request 19 + answer 16 bytes | 45 B, 3.91 ms | 49 B, 4.25 ms (+8.9 %) | 53 B, 4.60 ms (+17.8 %) |
| Console poll by the lock holder (same) | 49 B, 4.25 ms | 49 B (±0) | 53 B (+8.2 %) |
| dmi burst, one abstract-command read (write command, wait busy, read data0; 20 bytes of steps, 2 values) | 62 B, 5.38 ms | 62 B (±0) | 66 B (+6.5 %) |
| read_block of 1 KiB | 1064 B, 92.4 ms | 1064 B (±0) | 1068 B (+0.4 %) |
| attach with max_speed and pins, answer with target_id and search_retries | 60 B, 5.21 ms | 64 B (+4, the four TLVs) | 68 B |
| describe of fn 0, one page of about 11 TLVs (once per connection) | — | +11 B | +13 B |
| marks, a page of 10 marks | 230 B of elements | 220 B (−10, no len, 4.1) | 220 B |

At a console poll of 50 Hz by a monitor, the link carries 2250 B/s today (19.5 % of 115200 bps), 2450 B/s proposed (21.3 %) and 2650 B/s with corr u32 (23.0 %). Bulk traffic (read_block, write_block, capture data) is dominated by its data and does not change. The simplifications cost nothing on the locked hot paths; corr u32 would cost 4 bytes on every round trip for no removed rule.

## 6. Test gaps (review §7) and priorities (review §8)

### 6.1 Review §7: what the vectors do not cover

**Premise.** The shared vectors cover CRC, COBS, headers, TLVs, confirm, discovery, the probe.config hash and some refusals. The session state machine, the resend table, paging, plan and contention, most interface encodings, state transitions, timing, leases, frame gaps, port_speed and electrical rules are not covered. Conformance already lists a probe conformance tool as a stated gap.

**Recommendation: adopt partly.**
- **Per-op byte vectors** for every standard interface: minimal success, a boundary value, malformed, unsupported, unavailable, no_connection, and completed failed / partial where the op has them; each as request bytes, the probe state it assumes, and the answer bytes. Written by `tools/oepvectors1.py` from cases stated in the tool, so that the text stays the source.
- **Scenario vectors** for the session decision table (5.2), the resend table, paging (describe, connections, state, segments) and plan contention: a sequence of (request bytes, answer bytes) from a stated initial state. They run against the Python fake in this repository and against any probe.
- **Timing, leases, gaps, port_speed and electrical rules** are not byte vectors: they stay in the release tests on real probes (release-testing), and the gap is declared in conformance.
- **When**: after the wire changes of 4.1 to 4.5, so that the vectors are written once; the session scenarios first, since 5.2 changes that table.

**Impact.** This repository's tools and tests; the Python fake runs them; the Arduino probe's host tests and ch32rv's fake probe may load the JSON.

### 6.2 Review §8: the order

| Reviewer's priority | Here |
|---|---|
| Before the freeze: 1 sequences (3.1) | Resolved by 4.1 |
| 2 SDI / DMDATA (3.2) | Phase 0 |
| 3 HID (3.4) | Phase 0 |
| 4 the sentence and the empty scan (3.7, 3.8) | Phase 0 |
| 5 the release identifier (3.3) | Phase 0, user decision D4 |
| For simplicity: fixed parts closed, additions are TLVs (5.1) | Phase 1, adopted |
| no handover after end, no resume (5.2) | Phase 1, user decision D1 |
| one request header, corr u32 (5.3) | Phase 1, header adopted, corr u32 rejected (D2) |
| TLV len u16 (5.4) | Phase 1, adopted |
| common optional-op declaration (5.5) | Phase 1, adopted |
| After the freeze: the template (4.2) | Moved earlier: the checklist goes in Phase 0; the template guide after the freeze |
| byte vectors, state machine model (§7) | Moved earlier: Phase 2, before the freeze |
| external references (3.5) | Moved earlier: Phase 0 (text only) |

## 7. Plan

**Phase 0: text only, no wire change** (independent of each other; wording fixes may go straight in, the rest goes to the peers first): 3.2 (SDI / DMDATA and the debug header line), 3.4 (HID), 3.5 (references, SPI modes), 3.6 (answer enum conditions), 3.7 (the sentence), 3.8 (empty scan), 4.2 (the §13 checklist), 3.3 (versioning §6 and the status lines, after D4).

**Phase 1: the breaking set, one proposal to the peers, one change to each codec.**
1. 4.1 (closed forms, no element len, folded trailing fields, counted link test), 4.4 (TLV u16) and 4.3 (one header) together: all three change the codec, so each implementation changes it once and the vectors are regenerated once.
2. 4.5 (`ops`): independent of 1; can go in the same proposal.
3. 4.2 (sessions): independent of the codec; it changes behaviour and the decision table. Same proposal, separate commit.
4. 4.6 (the split, and `oep.link` after D3): last, as a move of text after the rules are settled.

**Phase 2: vectors** (6.1), session scenarios first, then per-op vectors.

**Phase 3: implementations**, in the usual order: the fake, oep-probe-arduino, oep-client-python, oep-client-js, ch32rv, then WireSkein and the bench take the new clients. The bench reflashes and enters its saved settings again (asking b2 before using the bench hardware).

**Questions for the peers**
- ch32rv: (a) 5.2: is it acceptable that `flash` no longer leaves its connection for the next command (each command attaches again, at most `attach_budget_ms`), and does any other command or the broker rely on resources surviving end? Can the broker's `expired` path simply join its `no_session` path? (b) 5.3: the single 10-byte header with corr u16, in codec.rs, the relay and broker_wch. (c) 4.1: slot_state with reset_at_ns before tid, and the elements without len. (d) 5.5: broker_wch's riscv-dm `ops` instead of features 0x7. (e) D3: port_speed and the link test moving to `oep.link` in speed.rs and link.rs. (f) 3.2: does anything in your SDI / DMDATA handling come from outside the text?
- WireSkein: does any flow rely on a plan, a capture track or a connection surviving `end`? Capture's query and force will be declared by `ops`; is the client update enough?
- bench: does any script rely on a plan, a connection or a driven pin surviving between processes? When can the bench probes be reflashed and their settings entered again?

## 8. Decisions for the user

**D1. Release everything a session created when its lock ends (5.2).**
Premise: today `end` keeps the session's plans and connections for whatever session opens next, and a host may resume by reusing its id; only ch32rv's `flash` uses the handover (it saves the next command's bring-up), and nobody resumes by id. Releasing at end removes the resume machinery and the `expired` reason, and stops one host inheriting what another left. What a user wants kept between commands (driven pins, a console read while no command runs, a fast attach) is kept by the settings (plan, idle, slot, bind). Cost: a CLI command that does not use a slot attaches again (at most 1000 ms). Recommendation: adopt.

**D2. One 10-byte request header with session_id always present, corr kept u16 (5.3).**
Premise: the reviewer proposes one header and corr u32. One header removes the role bit, the 6 / 10-byte split and open's exception, for +4 bytes on lock-free requests only (a monitor's console poll: +8.9 %). corr u32 would cost 2 bytes on every request and answer and would not remove the serial-number arithmetic, which notifications and serials still need. Recommendation: one header, corr u16.

**D3. Move the link test and port_speed out of fn 0 into an optional `oep.link` (5.6).**
Premise: every probe must implement link_source / link_sink today, and port_speed lives in the core, although the core's own rule says that what can be a named interface does not go into the core. Moving them makes the minimal probe smaller and leaves fn 0 with discovery, sessions, plan and notifications only. Cost: renumbering in every implementation, and a host lists `oep.link` before a speed test. Without D3 only the documents are split. Recommendation: adopt.

**D4. Decide the release identifiers (3.3).**
Premise: before the freeze two implementations can both say revision 1 and differ. The user decided on 2026-10-06 that tags stay `v0.x` through the freeze and `v1.0.0` is the formal release; versioning §6 still says "proposal". Deciding it lets every implementation name the tag it implements. Recommendation: mark versioning §6 decided as written, add the status-line sentence, and add no runtime edition field.
