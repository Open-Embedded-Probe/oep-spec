# OEP v1 rule-change proposal (2026-10-02)

[日本語](v1-rule-change-proposal-2026-10-02.ja.md)

Status: **proposal to the peers, revised with their answers (not normative)**. This English version is authoritative; the Japanese version is its translation.
Readers: ch32rv (Rust host and broker), WireSkein (capture recorder), bench (HIL jigs).
Base: oep-spec 78137fb (dmseq: cdd26b4). Revision 2 folds in the three peers' answers to the first version (ad9f8be): ch32rv (checked against its a3bf2fa), WireSkein, and bench (with measurements). Each item now carries a status line, and the final answers are in "Decisions" below. Source: [the third zero-base review](v1-zero-base-review-3-2026-10-02.ja.md) (Japanese): every rule-change finding (規則) marked ★ or ○, plus the dmseq questions raised after it.
C-11 (USB identification) is decided (no change) and is not included. Wording-only fixes that were applied separately (78137fb: C-12, C-13, C-14, C-35 and others) are not repeated.

The premise is the review's: people we have never met build probes and hosts from the text alone, for OSes, USB stacks, MCUs, debug wires and targets we have never seen. Each item starts with that user's case.

**How to answer.** For each item: agree, object, or agree with conditions. Answer the numbered questions (Q1 to Q32). After agreement the order of work is spec → fake → probe → clients, as before.

**Terms in "Today".**
- *probe*: oep-probe-arduino `src/`.
- *fake*: oep-client-python `endpoint.py` (with `fake_serial.py` / `fake_serve.py`).
- *Python*: the rest of oep-client-python.
- *JS*: oep-client-js `src/`.
- The Rust host was not checked (ch32rv: please say where your behaviour differs).
- "not checked" means I did not look.

**Breaking** = an implementation or a saved setting that follows today's text or today's reference code must change its behaviour on the wire.

## Decisions

**Status of an item.**
- **agreed**: all three peers accepted it. bench answered "OK overall" and ch32rv "OK except" the items marked otherwise. WireSkein answered for topics 3 and 8 (C-06, P2-★4, P2-★6, P2-○9, P2-○10, P2-○11, P2-○15, Q14, Q17, Q18) and then confirmed "no objection" to every other topic (2026-10-02).
- **agreed with condition**: accepted on the condition stated in the item. The condition is folded into the proposed text unless the item says it is still to be met.
- **open**: not settled. The item says what is missing.

Open items: P2-★4's cold-attach measurement (bench, before the freeze). The RVSWD and SWIO frames of debug §3.1 / §3.2 (7392817), a rule addition written from the reference probe (no item above): reviewed by ch32rv 2026-10-02, its points applied (the re-sync after a rest made informative, the 85-cell status query noted, the SWIO low ranges widened to 240 to 310 / 840 to 1060 ns, swio swclk ≠ 0xFFFF unsupported in scan as in attach).

**Final answers.**

| Q | Item | Answer |
|---|---|---|
| Q1 | C-01 | Yes: the registry writes `role_assignment = 0x10`; the generated constant changes with it |
| Q2 | C-02 | Yes: every unused enum value and reserved request bit → unsupported; malformed only for the listed values |
| Q3 | C-03 | Yes: a request TLV is never extended; a new field gets a new tag |
| Q4 | C-04 | Yes: at most 16 entries, 0x00 as the 16th for "more" |
| Q5 | C-06 | Yes: the formula is a floor. Scan and attach budgets count as argument time (P2-★4) |
| Q6 | P2-★4 | 200 ms per request and 1000 ms of real time adopted. **The attach budget is 1000 ms, not 500 ms** (bench measurement). Optional attach answer TLV `search_retries`. No host relies on "status line ⇒ the connection is gone". Bench measures one cold attach before the freeze |
| Q7 | C-07 | Discard up to the gap |
| Q8 | C-09 | Yes: 115200 for every probe |
| Q9 | C-05 | The confirm TLV. A TCP endpoint reports its listener's index; a relaying broker that answers the session ops reports 0xFF (ch32rv confirmed) |
| Q10 | C-15 | Yes: per transport; on TCP, per connection (C-05) |
| Q11 | P2-★1 | Yes |
| Q12 | P2-★2 | A rule with no option. Measured: one probe already meets it, the other drives MISO low while CS is high and is being fixed |
| Q13 | P2-★3 | Declare the pull-ups (features bit2 + pullup_ohms); do not forbid them |
| Q14 | P2-○13 | Adopt the rule |
| Q15 | P2-★7 | Yes: the `n × (role, channel)` form. Added: a wire that declares no pin combination need not implement scan (ch32rv confirmed) |
| Q16 | P2-○4 | Clear haltreq when halt times out |
| Q17 | P2-★6 | Yes: 0 = blocks, 1 = answers |
| Q18 | P2-○8 | mode, rate, trigger, pretrigger and frontend are sent critical. samples and segments are not: the probe rounds samples to its limit and the answer's value is authoritative. rate critical means "the nearest realisable value within range; out of range is unsupported" |
| Q19 | PC-1 | Firmware labels as step (c) |
| Q20 | PC-3 | Yes |
| Q21 | PC-5 | Yes: 32 bytes |
| Q22 | PC-8 | Index invariance |
| Q23 | C-10 | Keep the present-tense convention with the new §1.1 |
| Q24 | C-10 | Yes: link_source / link_sink are mandatory |
| Q25 | C-18 | The broker uses a random non-zero session_id, reopens with the same id, and always opens as 0x01: it conforms |
| Q26 | C-22 | Probe-side validation |
| Q27 | C-23 | Yes |
| Q28 | C-25 | SHOULD |
| Q29 | C-32 | Yes: ±2 %. verify_ms 0 is malformed for step 0 (try) only |
| Q30 | DS-1 | Post again every short wait (DS-1 adopted). The host safeguard of DS-8 goes only together with it |
| Q31 | DS-3 to DS-10 | ch32rv conforms to DS-4. DS-5 takes ch32rv's details (count saturates while unsynchronised) |
| Q32 | P2-★8 | Form A; ABSTRACTAUTO = 0 may be named; a probe attaching through another debugger sets `attach_writes_unbounded` (ch32rv) |

## Index

| id | topic | sev | one line | breaking | status |
|---|---|:---:|---|:---:|---|
| C-01 | 1 errors / extensibility | ★ | The tag number is the low 7 bits; the registry writes 0x10, not 0x90 | no (registry constant changes) | agreed; applied d48ca6d |
| C-02 | 1 errors / extensibility | ★ | A value a later revision may define → unsupported, not malformed | yes | agreed; applied d48ca6d (core, probe-config), fb44490 (interfaces) |
| C-03 | 1 errors / extensibility | ★ | Repeated, short and extended request TLVs | yes | agreed; applied d48ca6d |
| O-5 | 1 errors / extensibility | ○ | 0xF0 to 0xFE of u8 enums are experimental | no | agreed; applied d48ca6d |
| C-04 | 2 ignored cap | ★ | ignored: at most 16 entries, 0x00 marks "more", never left out | yes | agreed; applied cd15f53 |
| C-06 | 3 timing | ★ | The host's wait adds the UART transfer time and starts after the previous answer | no | agreed; applied f7d6d21 |
| P2-★4 | 3 timing | ★ | Wire retries 200 ms per request, wire loss 1000 ms of real time, attach budget 1000 ms, scan budget 500 ms | yes | agreed with condition; applied 3a88ec9 (debug), f7d6d21 (core), 18d7eac (registry). The cold-attach measurement is still open |
| P2-○3 | 3 timing | ○ | dmi: only time-based waits count against max_op_ms | no | agreed; applied 3a88ec9 |
| C-07 | 4 transports | ★ | No 200 ms restart on TCP; over-long lengths; resync waits 250 ms after the host's last write | yes | agreed; applied 48b8cbe, 0bb10e8 (§5.1 on TCP) |
| C-08 | 4 transports | ★ | max_frame / window / max_inflight are per transport | no | agreed; applied 48b8cbe |
| C-09 | 4 transports | ★ | UART bridge 115200 8N1 without flow control; line coding and DTR do not gate OEP | no | agreed; applied 48b8cbe |
| C-05 | 4 transports | ★ | confirm's answer says which transport it came on; a TCP endpoint is a probe | no | agreed with condition; applied 48b8cbe |
| C-15 | 5 revision scope | ★ | What a protocol revision covers; confirm never changes; the range in the refusal | yes | agreed; applied 929bbb7 |
| P2-★1 | 6 electrical safety | ★ | scan count = 0 leaves out channels with an idle item; output-idle channels are refused | yes | agreed; applied 0517c2f (debug), 18d7eac (core, probe-config, registry) |
| P2-★2 | 6 electrical safety | ★ | spi-target drives MISO only while CS is active | yes (one probe build, measured) | agreed; applied 0517c2f |
| P2-★3 | 6 electrical safety | ★ | i2c-target is open-drain only; internal pull-ups are declared | no | agreed; applied 0517c2f, 18d7eac (registry) |
| P2-○13 | 6 electrical safety | ○ | Taking a plan does not change a pin; logic capture only listens | yes | agreed; applied 0517c2f (capture), 18d7eac (core, registry), 3d51d4a (core §8 without interface names, fixture) |
| P2-★5 | 7 debug wires | ★ | A combination the declaration does not allow → unsupported | no (the probe does it already) | agreed; applied 78403b2 |
| P2-★7 | 7 debug wires | ★ | What every wire shares, and what a new wire (JTAG...) defines; a wire without pins | no | agreed; applied 78403b2 (debug), 18d7eac (probe-config) |
| P2-★8 | 7 debug wires | ★ | What the probe may write before the speed is verified; scan writes only the wake / configuration sequence and dmactive | no | agreed with condition; applied 78403b2, 18d7eac (registry) |
| P2-○1 | 7 debug wires | ○ | "Found" is DMSTATUS.version ≥ 2 and ≠ 15, for the ops too | yes | agreed; applied 78403b2 |
| P2-○4 | 7 debug wires | ○ | What a failed halt / step leaves on the target | yes | agreed; applied 78403b2, 18d7eac (registry) |
| P2-○6 | 7 debug wires | ○ | Console rules split into "every mechanism" and "the DATA0 mechanisms" | no | agreed; applied 78403b2 |
| P2-○5 | 7 debug wires | ○ | target_id_scheme is one space for the probe | no | agreed; applied 78403b2, 18d7eac (registry) |
| P2-★6 | 8 capture | ★ | Modes, streaming rules and `background` move into the normative text | no | agreed; applied a35acb0, 18d7eac (registry) |
| P2-○8 | 8 capture | ○ | Which configure TLVs the host sends critical (samples is not) | yes (hosts) | agreed with condition; applied a35acb0 |
| P2-○9 | 8 capture | ○ | What host and probe do during blocking_ms | no | agreed; applied a35acb0 |
| P2-○10 | 8 capture | ○ | capture-group state table | yes (fake) | agreed; applied a35acb0 |
| P2-○11 | 8 capture | ○ | Positioned read: beyond the write position, how much, from 3 | no | agreed; applied a35acb0 |
| P2-○15 | 8 capture | ○ | analog trigger enum loses level / edge | no | agreed; applied a35acb0, 18d7eac (registry) |
| PC-1 | 9 probe-config | ○ | Line names are also found in the firmware's fixed labels | yes (at boot) | agreed; applied 20967d7 |
| PC-2 | 9 probe-config | ○ | Names not in the table state no role; standard names in the registry; `x-` for private ones | no | agreed; applied 20967d7 |
| PC-3 | 9 probe-config | ○ | idle with a pull the channel lacks → unsupported | yes | agreed; applied 20967d7 |
| PC-4 | 9 probe-config | ○ | The channel of label / idle / disable is < channels and not reserved | yes | agreed; applied 20967d7 |
| PC-5 | 9 probe-config | ○ | label text: 1 to 32 bytes of UTF-8 without control characters | yes | agreed; applied 20967d7 |
| PC-6 | 9 probe-config | ○ | get's answer: items run to the end of the payload (wording) | no | agreed; applied 20967d7 |
| PC-7 | 9 probe-config | △ | Canonical form details for the hash (wording) | no | agreed; applied 20967d7; test vector e21a9a2 |
| PC-8 | 9 probe-config | ○ | Transport indexes do not change across firmware versions; bind at boot | no | agreed; applied 20967d7 |
| C-10 | 10 conformance | ★ | Normative words; what every probe and host must have | no | agreed; applied 4e62116 |
| C-16 | 11 other core | ○ | Rejected answers go into the resend table too; §5.2 binds TCP endpoints | no | agreed with condition; applied fc17225 |
| C-17 | 11 other core | ○ | When the lease restarts; the answer's lease_ms range | yes (fake) | agreed; applied fc17225 |
| C-18 | 11 other core | ○ | session_id random and not 0; open only as role 0x01 | yes | agreed; applied fc17225 |
| C-22 | 11 other core | ○ | Booleans 0 / 1; text without control characters | yes | agreed; applied fc17225 |
| C-23 | 11 other core | ○ | Grammar of names, model, chip | yes | agreed; applied fc17225 |
| C-24 | 11 other core | ○ | unit_id without a unique number or storage: `x-` | yes | agreed; applied fc17225 |
| C-25 | 11 other core | ○ | Exclusive open, HID output, WinUSB | no | agreed; applied fc17225 |
| C-29 | 11 other core | ○ | Registry keys are frozen; what the hash means | no | agreed; applied fc17225 |
| C-30 | 11 other core | ○ | instance is counted per (name, revision) | no | agreed; applied fc17225 |
| C-32 | 11 other core | ○ | port_speed: ±2 % baud tolerance, verify_ms 0 in a try | yes | agreed with condition; applied fc17225 |
| C-33 | 11 other core | ○ | Heartbeat period may be rounded up to 100 ms | no | agreed; applied fc17225 |
| DS-1 | 12 console dmseq | ★ | DATA0 = 0 is no answer: keep waiting, post again every short wait | yes (target) | agreed; applied 67863b1 |
| DS-2 | 12 console dmseq | ★ | The ownership rule lists the target's repost exceptions | no | agreed; applied 67863b1 |
| DS-3 | 12 console dmseq | ★ | The waits are real-time lower bounds, counted so they end with interrupts off | no | agreed; applied 67863b1 |
| DS-4 | 12 console dmseq | ★ | Byte k is bits 8k..8k+7 of the register | no | agreed; applied 67863b1 |
| DS-5 | 12 console dmseq | ○ | What restarts the host's count of invalid words | no | agreed; applied 67863b1 |
| DS-6 | 12 console dmseq | ○ | The target's state at begin() | no | agreed; applied 67863b1 |
| DS-7 | 12 console dmseq | ○ | "Reading for a long time" becomes 3 s, informative | no | agreed; applied 67863b1 |
| DS-8 | 12 console dmseq | ★ | Remove the optional host safeguard (rule 0 is mandatory), together with DS-1 | yes (ch32rv host) | agreed with condition; applied 67863b1 |
| DS-9 | 12 console dmseq | ○ | Clearing dmactive *may* clear DATA0 | no | agreed; applied 67863b1 |
| DS-10 | 12 console dmseq | ○ | CRC-8 check values | no | agreed; applied 67863b1; test vector e21a9a2 |

Items per topic:

| Topic | Items |
|---|---:|
| 1 errors / extensibility | 4 |
| 2 ignored cap | 1 |
| 3 timing | 3 |
| 4 transports | 4 |
| 5 revision scope | 1 |
| 6 electrical safety | 4 |
| 7 debug wires | 7 |
| 8 capture | 6 |
| 9 probe-config | 8 |
| 10 conformance | 1 |
| 11 other core | 11 |
| 12 console dmseq | 10 |
| **Total** | **60** |

Dropped findings and the reasons are listed at the end, followed by implementation bugs found while checking.

---

## 1. Error classes and extensibility

### C-01 ★ The tag number is the low 7 bits

**Status: agreed.**

**Problem.** An implementer reads `role_assignment = 0x90` in the registry next to `max_speed = 0x01  # critical`. From that alone they cannot tell that 0x90 already includes the critical bit. The text never says that the tag number is the low 7 bits.

**Proposed text** (core §2.2, replaces the bullet "Bit 7 of the tag is critical"):

> - **The tag number is the low 7 bits (0x01 to 0x7E).** Bit 7 is the critical mark. It is used only in requests and is not part of the number: 0x10 and 0x90 are the same TLV, sent without and with the mark. In answers, events and data bit 7 is 0, and a reader that meets a TLV with bit 7 set there skips it as an unknown tag. Tag 0x00 is reserved (not used in TLVs; the marker in the payload of rejected unsupported, §4.3), 0x7F is reserved for ignored in answers, and 0xFF is invalid.
> - ignored lists tag numbers (bit 7 cleared). The payload of rejected unsupported carries the tag byte as received (bit 7 included).

Core §7.4 and §8 write "role_assignment (0x10, sent critical as 0x90)". In the registry `role_assignment = 0x10`, with the comment `# always sent critical (0x90)`.

**Changes.**
- probe, fake: none. Both compare `tag & 0x7F`.
- Python, JS: code that sends the registry's `role_assignment` value as is must now set bit 7 itself (not checked where).
- The generated constant changes from 0x90 to 0x10.
- Saved settings: none (probe.config keeps tags without the critical bit).

**Today.** probe: `Tail::parse` masks bit 7 (Oep.h:204-223). Python: the core helpers mask it. `_speed_port` compares 0x4E exactly, which is harmless because answers carry bit 7 = 0.

**Q1.** May the registry value of `role_assignment` change from 0x90 to 0x10? The generated constant changes with it. Recommendation: yes. Every other tag in the registry is already written without the bit.

### C-02 ★ A value a later revision may define is refused as unsupported

**Status: agreed.**

**Problem.** Suppose a host is written for a later extension: gpio mode 8, i2c mode 4, a new drive kind. An old probe answers malformed (the host's error). A new probe that lacks the value answers unsupported. So the host gets two reasons for one situation, against "no two reasons for the same situation" (core §4.3). Reserved bits in request flags (list's flags) have no rule at all.

**Proposed text** (core §4.3, replaces orders 5 and 6):

> 5. **Format** → malformed: the length, a count that does not match the contents, a TLV encoding error, a contradiction between fields, and a value the field's definition excludes for every revision (the 7-bit `address > 0x7F`, a boolean other than 0 / 1, a value the definition calls invalid, a value whose length is unknown so that the rest of the request cannot be read, such as an unknown dmi step kind).
> 6. **Not handled by this probe** → unsupported: a value the definition leaves unused (an unused value of an enum, a reserved bit of a request's flags), a value in the definition that this probe does not declare (mode, format, rate, trigger type), an unknown critical TLV, a pin combination the declaration does not allow. The payload's tag is 0x00 for a value in the fixed part, and the TLV's tag as received for a value inside a critical TLV (a non-critical TLV with such a value is ignored, §2.3).

Add to core §2.5:

> Unless its definition says otherwise, every unused value of an enum and every reserved bit of a request may be defined later (§2.7). A probe refuses them by order 6 of §4.3.

Add to core §2.4:

> The host ignores reserved bits of an answer's flags. It shows unknown values of an answer's enum that do not report a failure (cause, holder_kind, the kind of a scan entry) as unknown. Unknown status and reason values remain failures.

Interface text, malformed → unsupported (payload 0x00):
- gpio mode ≥ 8;
- uart format: bit0-1 = 2 / 3, bit2-3 = 3, bits 5-7 (configure and the probe.config uart item);
- i2c-target mode 0 and ≥ 4;
- rvswd / swio attach method ≥ 2;
- riscv-dm reset mode ≥ 3;
- port_speed step ≥ 3;
- common §1.2 from ≥ 4;
- probe.config idle mode ≥ 5 and an undefined lock_scheme;
- list flags bits 1-7 (today ignored).

The drive TLV's undefined kind (fixture §1.1) moves from "the whole request malformed" to the §2.3 rule (critical: unsupported; otherwise ignored).

These stay malformed: i2c `address > 0x7F`, spi mode > 3 and bit_order > 1 (the field has no other meaning), booleans, the boot_reset value ≥ 2 (a boolean), dmi kinds (their length is unknown), lengths and counts.

**Changes.**
- probe: the checks at OepFixture.cpp:89, :175-178 / :335, :362; OepP4I2cTarget.cpp:292 (the mode part); OepTarget.cpp:366; OepSwd.cpp:210; OepEndpoint.cpp:597 and :913 (list flags); OepConsole.cpp:157; OepConfig.cpp:255, :277-278, :328.
- fake: endpoint.py:2038-2043, 2151, 1413, 1566, 1781, 2557.
- hosts: nothing depends on malformed vs unsupported for these. Python looks at malformed only on confirm.
- Saved settings: none. Such values were refused at set and never stored.

**Today.** Each handler differs, as listed above. Console mechanism > 2 is already unsupported, and so is the probe.config bind mode.

**Q2.** Shall "may be defined later" (→ unsupported) be the default for every enum value and every reserved request bit, with malformed kept only for the values listed above? Recommendation: yes.

### C-03 ★ Repeated, short and extended request TLVs

**Status: agreed.**

**Problem.** A safety item such as the attach's max_speed sent twice is read as the first value by one probe and as the last by another, and two different speeds can be applied. A host that appends a field to a critical TLV's value expects it to take effect. An old probe that "skips the unknown tail" (§2.3) silently ignores it, which defeats the critical mark.

**Proposed text** (core §2.3, added):

> - A tag whose definition does not say it repeats appears at most once in a request. Two or more are rejected malformed, critical or not. In an answer, the host uses the first.
> - If the value of a TLV this probe implements is shorter than its definition, or holds a value its definition excludes, the request is rejected malformed, critical or not. Only a value inside the definition that this probe cannot handle is unsupported (critical) or ignored (not critical). A TLV the probe does not implement is unknown to it, whatever its length.
> - **The value of a request TLV is not extended at the end.** A new field goes under a new tag. A probe that meets a request TLV it implements whose value is longer than it knows rejects it unsupported (that tag as received) when critical, and otherwise ignores the whole TLV and lists it in ignored.

The first bullet of "How fixed forms are extended" becomes: "When **the value of a TLV in an answer, an event or data, or an element of a sequence**, has a fixed form ...". Add:

> The items the probe keeps and returns (probe.config) keep the "append at the end" rule. A field appended to such an item must be one that is safe for an older probe to skip.

The registry marks the request tags that repeat with the comment `# repeats` (role_assignment, gpio set drive).

**Changes.**
- probe: a duplicate check for non-repeating request tags in `Tail` (today `Tail::find` returns the last). Longer-than-known values become unsupported / ignored (today they are malformed through exact length checks).
- fake: the same two changes. Today `Take.tail` keeps the last value, and exact length checks answer malformed.
- hosts: none. Python answers already take the first (`Tail.get`).
- Saved settings: none.

**Today.** The probe never skips a request tail silently: every handler checks the exact length. So the danger in (c) exists only in the text, not in the reference code.

**Q3.** Is "a request TLV is never extended; a new field gets a new tag" acceptable for your future requests? Recommendation: yes. The alternative, a per-TLV version, costs more than a tag.

### O-5 ○ Experimental enum values

**Status: agreed.**

**Problem.** Someone trying out a new console framing, transport kind or cause has no number they can use without colliding with a later standard value. Only op has an experimental range (0xF0 to 0xFF).

**Proposed text** (core §2.5, added):

> **Experimental values**: in every u8 enum whose definition does not say otherwise, the values 0xF0 to 0xFE are experimental. Anyone may use them while trying something out. A shipping probe and a released host do not use them, and they are never registered. (Tag numbers have no experimental range. Independent information goes into an independent interface, §13 rule 7.)

The registry notes the range on each u8 enum. Existing values above 0xF0 (mechanism `none = 0xFF`) are outside the range and unchanged.

**Changes:** none. **Today:** no implementation uses 0xF0 to 0xFE.

---

## 2. ignored cap

### C-04 ★ ignored: at most 16 entries, never left out

**Status: agreed.**

**Problem.** A host sends a gpio set with 20 non-critical drive TLVs to a probe that cannot apply them. The probe lists the first 16 and silently drops the rest. If the answer has no room, it drops the whole ignored TLV. The host then believes every drive took effect.

**Proposed text** (core §2.3, after the ignored sentence; registry `limits.ignored_max_entries = 16`):

> - ignored lists the numbers (bit 7 cleared) of the ignored TLVs **in the order they appear in the request**, one entry per ignored TLV, at most 16 entries (`ignored_max_entries`). When more than 16 TLVs were ignored, the probe lists the first 15 and puts **0x00** as the 16th entry ("more were ignored"; 0x00 is never a tag, §2.2). A host that sees 0x00 treats every TLV of its request that is not listed as possibly ignored.
> - The probe never leaves ignored out of an answer that needs it. When it decides how much variable data (data, sequences) goes into an answer, it keeps room for ignored (at most 18 bytes). If even the fixed part leaves less room, it lists as many entries as fit, with 0x00 as the last. `0x7F 0x01 0x00` (3 bytes) always fits.

**Changes.**
- probe: Oep.h:262 (put 0x00 when full) and :189 (shrink to fit instead of dropping). `reserve = 2 + kMaxIgnored` (list, uart / console read and marks, capture, probe.config) already keeps the room.
- fake: cap at 16 with the marker. Today there is no cap, and more than 255 entries would crash `bytes()`.
- hosts: treat 0x00.
- Saved settings: none.

**Today.** probe: `kMax = 16`, drops silently. Python / JS: parse the list; 0x00 has no meaning to them.

**Q4.** Is 16 entries plus the 0x00 marker acceptable? Recommendation: yes. The alternative is one entry per distinct tag (up to 126 bytes). It would undo the decision of 3cc50c8 and does not fit a 64-byte max_frame.

---

## 3. Timing

### C-06 ★ The host's wait covers the transfer time of a slow port

**Status: agreed.**

**Problem.** A user on a 115200 bps UART bridge with max_frame 4096 sends a request whose answer is large. The answer alone takes about 0.36 s on the line. Before it may come up to two max_frame of pending notifications (§11.4). With pipelining, the earlier answers come first too. A host that waits exactly "arguments + 1000 ms" times out on a correct answer and resends. The slower the port, the worse it gets.

**Proposed text** (core §4.4, replaces "The host's wait time"):

> - **The host's wait time**: the absence of an answer is decided only by timeout (§3.1). For each request the host waits **at least**: the time set by the request's arguments (the timeout_ms of run, the hold_ms of reset, the sum of the waits of dmi, save, etc.; for attach, `attach_budget_ms` plus the hold_ms of its reset TLV; for scan, `scan_budget_ms` + `attach_budget_ms` (debug §1); 0 if none; at most max_op_ms) + 1000 ms (`host_wait_add_ms`) + the transfer time. The wait starts when the request has been written, or, while earlier requests on the same transport are outstanding, when the answer to the request before it arrives (the probe answers in order). The transfer time is 0 except on a UART bridge. On a UART bridge it is (L + max_frame × (1 + `notify_pending_max_frames`)) × 10 / baud seconds, where L is the length on the wire of the request's frame and baud is the port's current speed. A host may wait longer. When the wait has passed, it proceeds to the resend of §5.2.

Core §7.5 max_op_ms: "The host waits at least this value plus the time ... (§4.4)" becomes "The host waits as §4.4 says."

Starting the clock at the previous answer means the earlier answers' sizes need not be added.

**Changes.**
- hosts: compute the floor. Python and JS already wait longer (3 s, see below) and conform as they are.
- probe, fake: none.

**Today.**
- Python: each reply's deadline is taken when that reply is read, so the clock in effect starts at the previous answer. The wait is `max(link timeout, expected + 0.5 s)` with a link timeout of 3 s (TCP 15 s), not capped at max_op_ms + 1000 ms.
- JS: 3 s.
- Rust: a fixed 3 s, which can be below the floor for long requests. ch32rv will compute it per request.

**Answers.** WireSkein and ch32rv agree; bench OK. Scan and attach budgets were added to the argument time so that the attach budget of P2-★4 does not end at the same instant as the host's wait.

**Q5.** Shall the formula be a floor (the host may wait longer)? Recommendation: yes. The failure we are fixing is waits that are too short.

### P2-★4 ★ Wire retries, wire loss and attach have time bounds that fit the host's wait

**Status: agreed with condition** — bench measures one cold attach against the 1000 ms budget before the freeze (still to be met).

**Problem.** A host sends dmi (no argument time, so it waits 1000 ms) to a target whose wire is flaky. If the probe applies "no answer for 1000 ms" inside one request, the probe's answer and the host's timeout fall on the same instant, and pipelined requests behind it time out first. The time after a reset release and the attach's speed search have no bound at all.

**Proposed text** (debug §2, replaces the bullet "The wire is considered lost ..."):

> - **Retries inside one request**: the probe spends at most 200 ms (registry `limits.wire_retry_ms`) of one request retrying the wire, retries at a slower speed included. When that is used up, it ends that request with status line. That alone does not decide wire loss. The speed search of attach (and of a scan combination) is bounded by the attach budget of §1 instead.
> - **Wire loss**: the wire is lost when operations on a connection have failed with no answer from the wire (status line, inside requests or inside console reads) for **1000 ms of real time** (`limits.wire_lost_ms`), with no successful operation on that connection in between. The time the probe asserts reset or holds a reset line (the plan, the reset TLV of attach), and the 1000 ms after it releases it, are not counted. When the probe decides wire loss inside a request, it answers that request with status line, then closes the connection.

Debug §1, added after the scan budget:

> - **attach budget**: one attach answer takes at most 1000 ms (registry `limits.attach_budget_ms`) of the probe's time, the speed search and its retries included and the hold_ms of the reset TLV excluded. When no speed works within it, completed failed with status line.
> - **scan budget**: the probe starts no combination later than 500 ms (`limits.scan_budget_ms`) after the scan request arrived (at least one combination is tried, as today). The try of one combination is bounded by the attach budget. One scan answer therefore takes at most `scan_budget_ms` + `attach_budget_ms`.
> - Both budgets are capped at max_op_ms. The host's wait counts them as argument time (core §4.4, C-06).

Attach answer, added to every wire (registry `[interface.tlv.attach_answer] search_retries = 0x12`):

> TLV 0x12 search_retries (u16, optional): the number of tries of the speed search that failed before the speed in speed_hz was verified (0 = the first try worked; 0xFFFF = 65535 or more). A host may log it to see a wire that is close to failing.

Timing consistency: per-request retries (200 ms) < scan budget (500 ms) < attach budget (1000 ms) = the time without an answer that decides wire loss (1000 ms of real time, across requests) = host_wait_add_ms. Because the host's wait for attach and scan adds their budgets to host_wait_add_ms, no bound ends at the same instant as the host's wait.

**Measurement (bench, 2026-10-02).** An RP2350 probe (0.0.28) attaching over RVSWD to an L103 target, `max_speed` 1 MHz, 16 warm attaches 0.2 s apart, two runs: successes typically 210 ms, slow ones 240 to 550 ms; the speed always settled at about 679 kHz. In the second run 4 of 10 attaches ended completed failed after 515 to 739 ms. A 500 ms budget would cut successful attaches short; 1000 ms covers every measured attach, successful or failed. A cold attach (the target ignored its first wake and the speed search needed retries) was not measured yet: it needs a power cycle of the target, and bench is asking the user.

**Changes.**
- probe:
  - time-box the PHY retries (today they are bounded by counts: RvswdPhy 200 attempts plus up to 14 bring-ups; SwioPhy 4);
  - keep a per-connection "failing since" time. Today `failure()` (OepTarget.cpp:562-570) decides wire loss after 3 DMSTATUS reads, about 3 ms, inside one request;
  - give attach a budget (today it is bounded only by counts);
  - attach `search_retries` to the attach answer (optional);
  - the console already uses 1000 ms of real time (`kLostMs`).
- fake: none (no timing model).
- hosts: a status line no longer always means that the connection has closed. The host checks with connections, as the text already says.

**Today.** As above. scan's 500 ms is checked only between pairs, so one pair's full attach is never cut short.

**Q6.** Are 200 ms per request and 1000 ms of real time acceptable? Does any host rely on "status line ⇒ the connection is gone"? Recommendation: adopt both numbers. ch32rv and bench: please say if a target of yours needs a longer bound after reset.

**Answers.** WireSkein OK. ch32rv and bench: no host relies on "status line ⇒ the connection is gone". bench measured the attach (above): 500 ms is too small, so the attach budget became 1000 ms, and bench's suggestion of an attach answer TLV with the retry count became `search_retries`. Condition still to be met: bench measures one cold attach against 1000 ms before the freeze.

### P2-○3 ○ dmi: only time-based waits count against max_op_ms

**Status: agreed.**

**Problem.** "The sum of the waits (0x04 us, the limits of 0x03 / 0x05)" includes 0x03, whose limit is a number of reads with no time. Host and probe cannot compute the same sum.

**Proposed text** (debug §4.1, replaces the sum bullet):

> - The sum of the wait_us of 0x04 steps and the max_us of 0x05 steps must not exceed max_op_ms (rejected unsupported). 0x03 steps are bounded by their count, not by time. If a request reaches max_op_ms while running, the probe ends it at that step with status timeout (done = the index of that step).

**Changes:** probe: add the max_op_ms check to the 0x03 loop (not checked whether it exists). fake: not checked. hosts: none.
**Today:** probe sums only 0x04 / 0x05 (OepTarget.cpp:793-804), as proposed.

---

## 4. Transports

### C-07 ★ TCP, over-long lengths, and the resync wait

**Status: agreed.**

**Problem.**
1. Over a tunnel or Wi-Fi, a 200 ms pause inside a TCP frame is normal. A probe that restarts its read there takes the rest of the frame for a new length and loses the stream for good.
2. If the previous host died in the middle of a write, the probe keeps waiting 200 ms for the rest of that frame. A new host's confirm sent 50 ms after its input went quiet is read as that rest, and the resync fails.
3. Nothing says what the probe does with a length above max_frame, or with a HID count larger than the report.

**Proposed text.**

Core §3.2, replaces the second bullet:

> - On serial ports, vendor bulk and HID, if input stops for 200 ms (`probe_frame_gap_ms`) in the middle of a frame, the probe restarts the read from the beginning. **On TCP it does not.** TCP does not lose boundaries, and a TCP connection whose stream is broken is closed.

Core §3.1, added after the length-prefixed rows:

> - **A length larger than max_frame**: the probe discards that frame and the input up to the next pause of `probe_frame_gap_ms`, then waits for the next frame. It sends no answer. On TCP it closes the connection instead. A HID report whose count is larger than the report can carry (the report length − 2, or − 3 with a report ID) is discarded whole.

Core §5.1, added:

> Before the confirm of a resync, and before the first confirm after opening a length-prefixed port, the host waits until `host_resync_wait_ms` (registry, 250 ms = probe_frame_gap_ms + 50 ms) have passed since it last wrote to that port, in addition to the 50 ms of quiet input. On TCP the host may instead close the connection and open a new one.

**Changes.**
- probe: `FrameReader` should not apply the gap to TCP. No TCP transport exists in `src/` today. On a length above max_frame it should discard up to the gap; today it slides by one byte (OepFrame.cpp:164-171). The HID example (UsbStreams.h:44) truncates `count`; it should discard the report.
- fake: TCP checks no length and has no gap timer (it conforms to the TCP rule).
- Python: record the time of its last write (today it waits only for quiet input, link.py:404-432, and does not wait after open).
- JS: has no confirm-based resync at all. It drops its buffer on a stall or an over-long length (link.js:196-241), which is a separate fix.

**Q7.** On an over-long length, shall the probe discard up to the gap (recommended) or slide byte by byte (today)? Sliding can lock onto a false length inside the payload.

### C-08 ★ Limits are per transport

**Status: agreed.**

**Problem.** A monitoring host on CDC (lock-free describe, link tests) and a session host on vendor bulk do not know each other. If window and max_inflight were shared by the whole probe, the monitor could use them up and the session host's requests would be refused or lost. Neither host could avoid that.

**Proposed text** (core §4.4, added):

> - max_frame, window and max_inflight of confirm are the limits **of the transport the confirm came on**. Each transport is counted separately, and requests outstanding on one transport do not use the receive room of another. The table of §5.2 stays one per probe (the 0x81 requests of a session are sent on one transport, §3.3).

**Changes:** none in today's code. **Today:** probe: one `Limits` shared by all transports. window and max_inflight are reported but not enforced, and requests are handled one at a time inside `poll()`, each transport with its own reader. fake: the same values, not enforced.

### C-09 ★ The UART bridge line, line coding, DTR / RTS

**Status: agreed.**

**Problem.** A host written from the text alone cannot open an unknown probe's UART bridge. "The boot speed is decided by the board profile", and data bits, parity, stop bits and flow control are written nowhere normative. The 115200 decision lives only in the guides. Some USB stacks stop a CDC port's output while DTR is deasserted, and firmware cannot always change that.

**Proposed text.**

Core §3.4, added at the top:

> - **The line of a UART bridge**: 8 data bits, no parity, 1 stop bit, no flow control. The boot speed is **115200 bps** (registry `uart_bridge_boot_baud`). port_speed (§3.5) changes only the speed.
> - **USB serial ports** (USB CDC, built-in USB serial): the probe accepts and sends OEP whatever line coding the host sets, and applies the line coding to nothing.
> - **Control lines**: the probe does not use DTR, RTS or the line state to decide whether to accept or send OEP. The host keeps DTR and RTS asserted while the port is open (a UART bridge may wire them to the probe's reset). What a probe does while the host holds DTR deasserted is not defined.

Core §3.5 "Boot speed: the port speed determined by the board profile" becomes "Boot speed: 115200 bps (§3.4)".

**Changes:** none for the reference code, because the hosts assert DTR.
**Today.**
- probe: examples `Serial.begin(115200)` (8N1). Nothing reads line coding. RP2 uses `ignoreFlowControl(true)`. The ESP32-P4 example's CDC stream returns 0 from write while the port is not connected (DTR-based on that USB stack).
- Python: pyserial defaults (115200 8N1, DTR and RTS asserted, no flow control).
- JS: not checked.

**Q8.** Shall the boot speed be 115200 for every probe, with no per-board boot speed? Recommendation: yes. A host cannot guess another speed.

### C-05 ★ confirm says which transport it came on

**Status: agreed with condition** — ch32rv's correction for a broker that answers the session ops itself is folded in below (2026-10-02).

**Problem.** port_speed's `port` must be "the port this request came on", but a host cannot learn that index. On a probe with two UART bridges, the reference hosts pick the first one, so speed cannot be raised from the second.

**Proposed text** (core §7.1):

> answer: "OEP!", revision(u8), flags(u8), max_frame(u16), window(u32), max_inflight(u8), boot_id(u32), [TLV]
> TLV 0x01 transport (u8): the index (§7.5) of the transport this confirm came on. The probe always attaches it.

Core §3.5: "port: the index of the transport this request came on (TLV transport of the confirm answer)". The registry gains `[interface.tlv.confirm_answer] transport = 0x01`. The answer grows from 22 to 25 bytes, within 64.

**Added for ch32rv's question (which index a TCP broker reports).** Core §3.1, after the TCP bullet (it also replaces "the broker is a host implementation, outside this specification"):

> - **An endpoint that answers OEP requests itself is a probe**, whatever carries it and whatever is behind it (for example a program that serves OEP on TCP and drives another debugger). Every probe rule applies to it. A broker that only relays requests to an OEP probe is a host towards that probe.
> - **A relaying broker that answers the session ops itself** (confirm, open, end, keepalive, lock_state) and relays every other request to one OEP probe has no describe of its own: fn 0's describe it relays is the probe's. In the transport TLV of its confirm it reports index 0xFF ("not in describe"). Towards the probe it is a host. Every rule on those session ops applies to its answers.
> - **TCP transports**: a probe that listens on TCP lists each listening socket as one transport in the describe of fn 0 (kind 6, interface 0xFF). Every connection accepted on that socket reports that index in the transport TLV of confirm. The rules that §3.3, §4.4, §7.1 and §11.4 apply per transport (the 0x81 requests of a session on one transport, max_frame / window / max_inflight, the revision in use, where notifications go) apply to each accepted connection separately.

So the transport TLV always names an entry of the describe of fn 0 returned on the same connection. port_speed (UART bridges, §3.5) and bind (serial ports, probe-config §1.2) never take a TCP index; their refusals are unchanged.

**Changes.**
- probe, fake: add the TLV. The fake builds its transport list in TLV order and ignores the index byte (endpoint.py:454-455); fix that too.
- Python (`_speed_port`, link.py:1275) and JS (`speedPort`, speed.js:162): use the TLV.

**Today:** the probe checks `port == current transport` (OepEndpoint.cpp:597). Both clients use `bridges[0]`.

**Q9.** A confirm TLV (recommended) or `port = 0xFF` meaning "this port"? The TLV also gives the host the index that probe.config bind needs (PC-8).

**Answers.** bench and WireSkein: no objection. ch32rv confirmed the TCP-endpoint rule and asked for the relaying-broker case (a broker that answers the session ops locally and relays the rest). Of its two options, index 0xFF and no transport TLV, this proposal picks 0xFF: the TLV stays always present, and a host can tell that it talks to a broker.

---

## 5. Revision scope

### C-15 ★ What a protocol revision covers

**Status: agreed.**

**Problem.** A revision-2 host meeting a revision-1 probe cannot proceed safely. Nothing says that confirm itself never changes, what the chosen revision applies to, or what the refusal carries.

**Proposed text** (core §7.1, added):

> - The confirm request and the fixed part of its answer, the magic `OEP?` / `OEP!`, and the rules before confirm (64 bytes, the frames of §3.1, §3.3) are the same in every protocol revision.
> - The revision the probe chose applies to **the transport the confirm came on**, to every message in both directions, until the next confirm on that transport. Transports may run different revisions.
> - After its first confirm on a transport, the host sends `min_rev = max_rev =` the revision in use in every later confirm there (resync, probing again).
> - When it can handle no revision in the range: rejected unsupported, payload tag 0x00 followed by TLV 0x01 supported (min(u8), max(u8): the range the probe can handle). `min_rev > max_rev` is rejected malformed.

**Changes.**
- probe: add the supported TLV; `min > max` becomes malformed (today unsupported; OepEndpoint.cpp:498).
- fake: the same.
- Python: the link's own confirms (resync, `confirm_raw`, link.py:422, 550) send 0..0xFF. Against a later probe that would switch the revision in the middle of a session, so they must send the revision in use.
- JS: not checked.
- Rust: re-confirms send 0..0xFF today; ch32rv will send the revision in use everywhere.

On TCP, "the transport" is each accepted connection (C-05).

**Today:** both sides know only revision 1, so nothing breaks yet.

**Q10.** Is the per-transport scope ("until the next confirm on that transport") acceptable for the broker? Recommendation: yes.

---

## 6. Electrical safety

### P2-★1 ★ scan count = 0 does not drive channels the settings have taken charge of

**Status: agreed.**

**Problem.** A user saves an idle item, output high, on the pin that switches the target's power. A later host runs scan with count = 0 on an unknown fixture. That pin is not "held" by a plan or a connection, so the probe drives it as SWCLK or SWDIO. The target's power switches on and off, or two outputs fight.

**Proposed text** (debug §1, added to the pin-combination rules):

> - The count = 0 sequence and the candidates of an attach without pins leave out every channel that has an **idle item** in the probe's settings (any mode), in addition to channels held by something else and disabled channels.
> - A request that names such a channel explicitly (a scan listing combinations, the pins of attach) is accepted when the idle is an input (mode 0 to 2). It is rejected unavailable (cause 5, the channel, holder_kind 7 = settings idle) when the idle is an output (mode 3 / 4).
> - (Informative) count = 0 drives every free candidate pin in turn. Without the user's consent, a host does not send count = 0 to a fixture whose wiring it does not know.

Debug §2, added (P2-○14, the same mechanism):

> - When a connection closes, the channels of its combination go to the idle state of core §8 (the drive of idle_clock stops).

The registry gains `holder_kind.settings_idle = 7`.

**Changes.**
- probe: `pairFree` (OepTarget.cpp:169-178) must also look at idle items.
- fake: the same (endpoint.py:1553-1557).
- hosts: count = 0 finds fewer pins on fixtures with idle items.
- Saved settings: a jig that set an idle on its debug pins must name them explicitly in scan.

**Today.** probe and fake leave out only held and disabled channels. Related gaps found in the probe:
- after scan, the tried pins are left Hi-Z instead of their idle state;
- after a connection closes, RVSWD with idle_clock low keeps SWCLK driven low with no time limit (OepRvswdPhy.cpp:207-213), and channels without an idle keep the PHY's state.

**Q11.** Shall all idle channels be left out of count = 0, and output-idle channels be refused when named? Recommendation: yes. The review also proposed leaving out labelled channels. I dropped that: users label exactly the debug pins they want scanned.

**Answers.** Yes (bench: its jigs set idles only on the DUT's RX lines; ch32rv: agree, its host sends count = 0 itself and will find fewer pins on fixtures with idle items).

### P2-★2 ★ spi-target drives MISO only while CS is active

**Status: agreed.**

**Problem.** Most DUTs share one SPI bus among several targets. "MISO is 0 outside tx" reads as "drive MISO low all the time". A deselected target that drives MISO fights the selected one.

**Proposed text** (fixture §4, added after the MISO sentence):

> - **From configure until the plan is released, the probe drives MISO only while CS is active.** While CS is inactive it does not drive MISO (an input with no pull). "MISO is 0 outside tx" refers to the bits of a transfer while CS is active. SCK, MOSI and CS are always inputs. Before configure the channels keep their idle state (P2-○13).

**Changes:** probe: depends on the SPI peripheral. If a peripheral drives MISO while CS is high, the firmware must switch MISO's output enable from CS. The ESP32-P4 build (ESP-IDF spi_slave, OepP4SpiTarget.cpp:69-87) meets the rule; the classic SPI slave build does not (bench's measurement below). fake: none (no electrical model).

**Q12 (bench).** Does your spi-target hardware leave MISO undriven while CS is high? Please measure once. Recommendation: make it a rule with no option. A probe that cannot do it is not a bus-safe SPI target.

**Answers.** Adopted as a rule with no option (bench's answer; no objection from ch32rv or WireSkein). **Measurement (bench, 2026-10-02):**
- the X035 jig's probe (ESP32-P4, ESP-IDF spi_slave): MISO undriven in every state. It meets the rule;
- the V003 jig's probe (classic SPI slave build, d4f6293): MISO undriven before configure and after release, but **driven low while CS is high** from configure on (configured, armed, after a CS cycle, re-armed). It fails the rule and is being fixed: the firmware must switch MISO's output enable from CS. bench reruns its test on the next build.

So the breaking column becomes "yes (one probe build)".

### P2-★3 ★ i2c-target is open-drain only; internal pull-ups are declared

**Status: agreed.**

**Problem.**
- A probe that drives SDA / SCL push-pull shorts the controller.
- A probe that silently enables internal pull-ups hides a DUT whose bus lacks pull-ups, and on a DUT that has them it shifts the levels.

**Proposed text** (fixture §3, added):

> - SDA and SCL are driven **open-drain only**: the probe pulls them low or releases them, and never drives them high.
> - **Internal pull-ups**: a probe that enables pull-ups of its own on SDA / SCL while configured declares it with features bit2 (internal pull-ups) and describe tag 0x42 pullup_ohms (u32, approximate). A probe that does not declare it enables none. v1 has no request that switches them.
> - In state 0 the probe ACKs no address and leaves both lines released.

**Changes:** probe: declare bit2 and about 45000 Ω. fake: declare nothing. hosts: may warn when bit2 is set.
**Today:** probe: the ESP-IDF slave driver (open-drain). `start()` enables the pad's internal pull-up on both lines, about 45 kΩ (OepP4I2cTarget.cpp:212-217), because the bench fixture has no external pull-ups. In state 0 no peripheral exists, so nothing is ACKed.

**Q13.** Declare the pull-ups (recommended), or forbid internal pull-ups as the review proposed? Forbidding them breaks the bench jig, which has no external pull-ups. Declaring lets a host tell the user.

**Answers.** Declare (bench: the X035 jig relies on the internal pull-ups; the V003 jig has 2.2 kΩ external ones). Internal pull-ups are not forbidden.

### P2-○13 ○ Taking a plan does not change a pin; logic capture only listens

**Status: agreed.**

**Problem.** A user's idle output powers the target. They take a logic plan on that pin to watch it. If the probe turns the pin into an input, it cuts the target's power. Nothing in the text forbids that.

**Proposed text** (core §8, added):

> - **Taking a plan does not change a pin's electrical state.** A pin keeps its idle state until the interface that holds it starts to use it. That is: gpio at the first set, uart TX at the plan (high, fixture §2), i2c-target and spi-target at configure, analog at start (the pad leaves the digital function). Logic capture never changes it: it only listens. It does not stop an output, and it does not change the pull or direction of a pin that another function or an idle output drives.
> - An analog plan on a channel whose idle is an output (mode 3 / 4) is rejected unavailable (cause 5, holder_kind 7).

**Changes.** probe: logic capture must enable the input path without `pinMode(INPUT)` (OepCapture.cpp:466-475, OepSampler.cpp:193-202). analog's planCheck must refuse output-idle channels. fake: none.
**Today.** probe:
- gpio, i2c, spi and analog keep the idle until use, as proposed;
- logic capture sets `INPUT` at the plan, so an output idle stops. Logic plans may overlap gpio / uart / wire pins (`planShares`) and set those to input too. The idle is not restored on release.

**Q14.** Can every capture peripheral you use read a pin without changing its direction? Recommendation: adopt the rule. A capture that changes the pins it watches breaks the circuit it is watching.

**Answers.** Adopt (WireSkein: its power-up test needs it).

---

## 7. Debug wire generality

### P2-★5 ★ A combination the declaration does not allow → unsupported

**Status: agreed.**

**Problem.** debug §1 refuses an undeclared pin combination as unavailable, while core §4.3 order 6, plan_apply and probe.config refuse the same mistake as unsupported. A host can get two reasons.

**Proposed text** (debug §1, replaces "A combination that is not allowed is rejected unavailable without executing anything"):

> - A combination the declaration (channel_group / role_channels) does not allow is rejected **unsupported** without executing anything. attach puts the pins tag as received in the payload. scan puts tag 0x00 followed by TLV 0x40 index (u8, its position in the request's sequence). A combination with a held channel (plan, connection, settings, disable) is rejected unavailable (cause 1 / 5, with the channel).

**Changes.**
- probe: add the index TLV to scan, and use the tag as received in attach (today always `pins | 0x80`).
- fake: scan answers a bare unavailable (endpoint.py:1551); attach is already unsupported.
- Related: the probe's spi-target refuses a channel outside its declaration as unavailable (OepP4SpiTarget.cpp:22); it should be unsupported, like plan_apply.

**Today:** the probe already answers unsupported (OepTarget.cpp:243, 290, 410). The text follows the probe.

### P2-★7 ★ What every wire shares, and what a new wire defines

**Status: agreed** — ch32rv confirmed it (2026-10-02).

**Problem.** The first thing a third party brings is likely a RISC-V JTAG DTM, cJTAG or an ARM JTAG-DP. The "all wires" rules are written with swdio / swclk, DMSTATUS and a two-pin fixed part. Nobody can tell which rules bind a new wire, nor how a 4- or 5-pin wire writes its pins.

**Proposed text** (debug, new §0 before §1):

> ## 0. What every wire shares, and what a new wire defines
>
> Every `oep.wire.*` interface:
> 1. uses op 0x01 scan, 0x02 attach, 0x03 detach and 0x05 connections with the meanings of §1 to §2.1 (a wire may add ops from 0x06). attach, detach and connections are required on every wire. scan is required on every wire that declares a pin combination (channel_group or role_channels);
> 2. follows §1 (verify the speed by reading before writing, count = 0 and what it leaves out, seats and max_connections, the scan and attach budgets, refusals) and §2 (lifetime, wire loss, the state machine, closing does not change the target), reading swdio / swclk as "the channel of pin role 1 / 2";
> 3. creates the connections of common §2 that `oep.target.*` interfaces use.
>
> A wire whose combination is not two pins writes, in its own document, its pins TLV, its scan entries and its connections entry with `n(u8), n × (role(u8), channel(u16))` in place of the two u16 fields, keeping the other fields and their order.
>
> **A wire without pins.** A wire that declares neither channel_group nor role_channels (its pins are not channels of this probe, for example a TCP endpoint that drives another debugger) has exactly one combination, the one the endpoint uses:
> - attach is sent without pins. A pins TLV is rejected unsupported (the tag as received), like any combination the declaration does not allow (P2-★5);
> - scan is optional. Without it the probe answers unknown_operation (C-10). With it, count = 0 tries that one combination, and a request listing combinations is rejected unsupported;
> - connections entries and scan entries carry 0xFFFF for each channel (in the `n × (role, channel)` form, n = 0);
> - P2-★1 and the pin rules of §1 have nothing to apply to.
>
> A new wire's document also defines:
> - its pin roles and how its speed is chosen;
> - its "found" criterion and its scan_kind values;
> - the target_id schemes it uses (from the single space, P2-○5) and how wire loss is seen;
> - which `oep.target.*` interfaces take its connections, and whether consoles and probe.config slots ride on them.

probe.config §1.1, added:

> A slot designates a two-pin wire. A wire whose combination is not two pins gets a new item tag when slots are defined for it.

**Changes:** none (three wires today).

**Q15.** Shall the `n × (role, channel)` form be fixed now for wires that are not two pins? Recommendation: yes. Otherwise each new wire invents its own and hosts must special-case each.

**Answers.** bench and WireSkein: no objection. ch32rv was unsure: if every wire MUST have scan and connections, the WCH broker needs both. Resolution: "A wire without pins" above. connections stays required everywhere (a host checks with it after status line, P2-★4, and an endpoint always knows its own connections); scan is optional only where there are no pins to search. ch32rv confirmed it (2026-10-02).

### P2-★8 ★ What the probe may write before the speed is verified

**Status: agreed with condition** — ch32rv (form A, with the flag below for a probe that attaches through another debugger), bench and WireSkein (no objection), 2026-10-02.

**Problem.** debug §1 says "The probe does not write to the target until it has finished verifying the wire speed (it selects the speed by reading only)" and "The only thing scan writes to the target is dmactive". A third party bringing a wire whose debug module answers nothing until it is woken and configured cannot meet either sentence: written as is, the probe never finds such a target. The text also does not say how the write path is verified at the chosen speed, nor what that verification may leave on the target. Reads alone are not enough: a speed whose reads are clean can still garble writes (measured on the reference probe, OepRvswdPhy.cpp:347-351; [link measurements](link-measurements.ja.md) §3), so a write check is needed.

**Today** (probe).
- rvswd attach (OepRvswdPhy.cpp:415-478): at the slowest speed, before anything is verified, writes the wake sequence, DMSHDWCFGR / DMCFGR (DMI 0x7E / 0x7D) twice each and dmactive (skipped when the module is plainly active). It chooses the speed by DMSTATUS reads only, then verifies the write path at that speed (`writesLand`, :361-379): ABSTRACTAUTO = 0, then 256 writes and read-backs of PROGBUF0, leaving PROGBUF0 = 0, not its earlier value.
- swio attach (OepSwioPhy.cpp:148-166, 398-416): the configuration pair twice and dmactive twice at its one speed, verified by reading DMCFGR back.
- scan (OepTarget.cpp:335) calls `Ch32Dm::probe` (OepCh32Dm.cpp:41-46), which runs the full attach: wake, configuration pair, dmactive, ABSTRACTAUTO and 256 PROGBUF0 writes, and the wake resets the debug module of some targets. `RvswdPhy::probeOnce` (OepRvswdPhy.cpp:316-326: wake, dmactive, one DMSTATUS read) is close to what §1 says, but nothing calls it.
- swd scan (OepSwd.cpp:106-122): the JTAG-to-SWD / dormant wake, TARGETSEL when given, and a DPIDR read. Nothing else is written.

**Proposed text, form A** (recommended). Debug §1, replaces the first bullet ("The probe does not write to the target until ..."):

> - **Writes before the speed is verified.** Until the probe has verified the wire speed, it writes to the target only:
>   1. the wake / configuration sequence that the wire's section defines (for example a wake pattern, a line reset, a target select, or the debug-module configuration registers the module needs before it answers), sent at the wire's slowest speed;
>   2. dmactive, on a wire whose connections reach a RISC-V DM, and only when DMCONTROL does not already read dmactive = 1 (the write clears haltreq).
> - **Verifying the speed.** The probe chooses the speed by reads only. It then verifies the write path at the chosen speed by writing and reading back only the debug-module registers that the wire's section names as free scratch (registers no part of the target uses while no debug command runs), together with any write the wire's section names as making them free. Before the check it reads each scratch register, and after the check it writes that value back. A speed whose writes do not read back is not used.
> - Nothing else is written to the target before the speed is verified.

Debug §1, replaces "The only thing scan writes to the target is dmactive (to read DMSTATUS)":

> - **What scan writes**: only the writes of item 1 and 2 above, to read the identifier of "found". scan does not verify the write path and writes no scratch register. It may choose the speed by reads as attach does.

Debug §3 (rvswd / swio), added:

> - **Wake / configuration sequence** (§1 item 1): rvswd: the wake pattern, then DMI 0x7E and DMI 0x7D each written 0x5AA50400, the pair twice. swio: DMI 0x7E and DMI 0x7D each written 0x5AA50400, the pair twice.
> - **Scratch** (§1): PROGBUF0 (DMI 0x20). Making it free: ABSTRACTAUTO (DMI 0x18) = 0, which is not restored (an autoexec left armed by an earlier session would run on each access).

Debug §5 (swd), added:

> - **Wake / configuration sequence** (§1 item 1): the JTAG-to-SWD switch, the dormant wake, and TARGETSEL when one is given. swd names no scratch register.

P2-★7's list of what a new wire's document defines gains "its wake / configuration sequence and its scratch registers (§1)".

**Form B.** §1 says only "Before the speed is verified the probe writes nothing except what the wire's section lists", and each wire lists its writes (as above) with no general bound. Simpler, but a new wire's author gets no rule to follow, and a host cannot rely on anything for a wire it has not read.

**Recommendation: form A.** It keeps a bound that holds for every wire (a sequence the wire defines, dmactive, and restored scratch) and leaves only the concrete registers to each wire.

**Changes.**
- probe: scan uses a bring-up without the write check (the wake / configuration sequence, dmactive, DMSTATUS read; for example `probeOnce` at the slowest speed, or an attach with `writesLand` left out). `writesLand` saves PROGBUF0 before the check and writes it back. The comment on `Ch32Dm::probe` ("nothing else written") becomes true. swio and swd: none.
- fake, hosts: none (fake: not checked).

**Breaking:** no. scan writes less than today; attach writes what it writes today, plus PROGBUF0's restore.

**Added for ch32rv (a probe that attaches through another debugger).** debug §1, after form A:

> The bound above applies to a probe that drives the wire itself. A probe whose attach goes through another debugger it does not control (it cannot see or bound what that debugger writes) sets bit `attach_writes_unbounded` in the wire's describe flags, and is then outside this bound. A host treats an attach on such a wire like a reset of unknown effect: it does not expect the target's registers or the running program to survive it.

The registry gains the flag bit in the wire describe. A flag rather than a sentence alone, because a host that meets a third party's probe must be able to tell.

**Q32.** Form A (recommended) or form B? And may a wire name a write that is not restored, as ABSTRACTAUTO = 0 above, to make its scratch free? Recommendation: yes, named per wire; an autoexec left armed is never what the next attach wants, and without the write the check fails on every attach until power-cycle.

### P2-○1 ○ "Found" is DMSTATUS.version ≥ 2 and ≠ 15, for the ops too

**Status: agreed.**

**Problem.** A RISC-V DM of a later debug specification version (4 onwards) is reported as "not there". Worse, the reference probe finds a version-3 DM (1.0, used by most non-WCH RISC-V chips) but never sees it halted.

**Proposed text** (debug §1):

> "Found" means DMSTATUS.version is 2 or more and not 15 (0 = no DM, 1 = a version this interface does not handle, 15 = a DM that does not conform). For swd, DPIDR could be read.

Debug §4, added:

> The riscv-dm ops treat every version that scan accepts the same way.

**Changes:** probe: `Ch32Dm::probe` (OepCh32Dm.cpp:41-46) requires 2 or 3. `checkHalted` (:79), the halt shortcut (:145), `resetHalt` (:451) and the console (OepDmConsole.cpp:48) require exactly 2. fake: does no check.

### P2-○4 ○ What a failed halt or step leaves on the target

**Status: agreed.**

**Problem.** A host's step times out on a target that is running motors. Was dcsr.step left set, so that the target stops after one instruction the next time anything resumes it? Was haltreq left set, so that it halts later? The invariant table says "clears dcsr.step", which cannot be done on a running hart.

**Proposed text** (debug §4 table and §4.2):

> - **halt**: if allhalted is not seen within 100 ms, the probe clears haltreq and answers status timeout.
> - **step**: if the hart does not return to debug mode within 100 ms, the probe sets haltreq and waits up to 100 ms more. If the hart halts, it clears dcsr.step, restores DATA1 / DATA0, and answers status state with dpc_after valid. If it does not halt, it clears haltreq and answers status state with answer TLV 0x01 step_left (length 0): dcsr.step may still be set and the hart is running. The host halts it and clears dcsr.step.

The registry gains `[interface.tlv.step_answer] step_left = 0x01`.

**Changes.** probe: halt (OepCh32Dm.cpp:155-172) leaves haltreq set today; step (469-500) waits 50 ms, then calls `halt()`. If that fails, dcsr.step and haltreq stay set; if the dpc read fails, the dcsr restore is skipped. fake: not checked.

**Q16.** Clear haltreq when halt times out (recommended), or leave it set (today)? A halt left pending can stop the target later, at a moment no host expects.

### P2-○6 ○ Console rules: every mechanism, and the DATA0 mechanisms

**Status: agreed.**

**Problem.** An ARM console (a memory ring read through the MEM-AP, semihosting, SWO) cannot be added as a new mechanism. "One live stream per connection (all use DATA0)", "pause during riscv-dm requests" and "DMSTATUS every 20 ms" are written as rules of the whole interface.

**Proposed text.** console §2 keeps the rules for every mechanism: numbering, open returning the existing (connection, mechanism) stream, reopening at the same place, lifetime, close, closed streams staying readable, the meaning of write, draining regardless of sessions. Added:

> Each mechanism defines: the kinds of connection it opens on, the target resources it uses, how many live streams one connection can have together with other mechanisms, when the probe pauses reading, and how often it checks the target's state.

Console §3, intro:

> Mechanisms 0, 1 and 2 use DATA0 and DATA1 as the mailbox. Among them one connection has one live stream (an open with another of them is rejected unavailable cause 6). Reading pauses while a riscv-dm request runs on that connection and while the hart is halted (DMSTATUS checked at least every 20 ms). They do not open on an arm-adi connection (rejected unavailable cause 6).

**Changes:** none (meaning unchanged). **Today:** the probe does exactly this for 0 to 2.

### P2-○5 ○ target_id_scheme is one space for the probe

**Status: agreed.**

**Problem.** The registry keeps the schemes per wire. A slot's lock compares only the scheme number, so a new wire's "scheme 1" could collide with rvswd's.

**Proposed text** (debug §1): "The target_id scheme numbers are one space for the whole probe (registry `[common.enum.target_id_scheme]`: 1 the u32 at DMI 0x7F of that debug module, 2 swd targetsel). Each wire states which schemes it uses." The registry moves the enum; numbers and the key `wch_dmi_7f` are unchanged.

**Changes:** none on the wire. Generated identifiers move (before the freeze, C-29).

---

## 8. Capture

### P2-★6 ★ Modes, streaming rules and `background` in the normative text

**Status: agreed.**

**Problem.** describe's mode carries `background(u8)`, whose meaning and values are written nowhere normative. The streaming rules are only in a Japanese record. An English reader cannot implement capture.

**Proposed text** (capture, new §2.1 "Modes"; §2 Segments becomes §2.2):

> | Mode | Behaviour |
> |---|---|
> | 1 one-shot | After start (and the trigger), captures samples samples, then stops (state 4). The host reads at its own pace. The next start discards the data |
> | 2 repeat | One-shot after one-shot, with no gap at segment boundaries, into free segments only. Stops (state 5) when none is free; resumes on release |
> | 3 streaming | Captures without gaps as repeat does, and sends the data in notifications while the lock holder subscribes |
>
> - The trigger is only a start condition: it applies to the start of the first segment in every mode.
> - The probe captures only after start. It does not capture ahead.
>
> **Streaming rules**:
> 1. When there is no room to send, the probe discards **new** data (data already queued is still sent). The discarded amount shows as a jump of position in the next data frame and as status flags bit0.
> 2. After stop, the probe still sends what it captured before stop. The host has everything when the end of the received positions equals status's write_pos after stop.
> 3. No segment events are sent in streaming (stopped is sent).
> 4. Data sent in a notification may not be readable with read (an unreadable position returns an empty answer with gap).
> 5. The subscription ends with the lock (core §11.3). A receiving host keeps the lock alive.

Capture §3.5, the mode row:

> mode(u8), background(u8: 1 = while capturing in this mode the probe keeps answering requests, and start's blocking_ms is 0; 0 = it does not answer while capturing, and start's blocking_ms says for how long, §3.2; other values reserved), max_samples(u32), max_segments(u32)

"The declaration is a guide; the answer to configure is authoritative" stays, without the link. Links to the record take the form "(reasons: ...)".

**Changes:** probe: none. fake: never drops data (it could simulate rule 1 later).
**Today.** probe:
- background is always 1 and blocking_ms 0;
- store-and-push drops new data and sets status dropped;
- the direct path discards while nobody subscribes;
- after stop both paths send the rest;
- data from store-and-push can be read until the segment is reused, data from the direct path never.

All of this is as proposed.

**Q17.** Are the values of background acceptable (0 = blocks, 1 = answers)? Recommendation: yes.

### P2-○8 ○ Which configure TLVs the host sends critical

**Status: agreed with condition** — WireSkein: samples stays non-critical, rounded to the limit, the answer authoritative (folded in).

**Problem.** A host sends mode = 3 without the critical bit to a probe without streaming. The probe ignores it and configures one-shot. If the host overlooks ignored, it records the wrong mode.

**Proposed text** (capture §3.3, a column "sent critical" in the table):

> - mode, rate, trigger, pretrigger and frontend are always sent critical. A probe that cannot honour one refuses the configure (unsupported, the tag as received).
> - rate sent critical means: the probe applies the nearest value it can realise within its declared range (actual_rate says which); a rate outside the range is unsupported.
> - samples and segments may be sent without the critical bit. A samples above what the probe can hold is rounded down to its limit, and actual_samples (0x52) in the answer is authoritative. The host reads actual_samples and actual_segments rather than assuming the values it sent.

**Changes:** hosts that send these without the bit must set it (WireSkein will send mode critical; Python capture.py: not checked). probe: round samples to its limit and report it in actual_samples (not checked whether it does today). fake: not checked.

**Q18 (WireSkein).** Is this list right for your recorder? Recommendation: yes.

**Answers.** WireSkein: mode, trigger, pretrigger and frontend critical, yes; rate critical, yes with the meaning above. For samples it offered two forms: critical, with an over-limit samples refused unsupported carrying max_samples; or non-critical, rounded to the limit with the answer authoritative. It recommended the second, which is adopted (the first proposal had samples critical).

### P2-○9 ○ During blocking_ms

**Status: agreed.**

**Proposed text** (capture §3.2, replaces "The lease is not counted during blocking"):

> - From the start answer for blocking_ms, the probe may not process frames on any transport and may lose them. The host sends nothing to that probe on any transport during blocking_ms. Afterwards, on a length-prefixed transport, it begins with the resync of core §5.1. On a serial port it simply continues. Neither the lease nor the host's wait (core §4.4) counts blocking_ms.

**Changes:** none: no probe blocks today (background = 1 everywhere). Python passes blocking_ms as the start request's expect_ms, which is harmless.

### P2-○10 ○ capture-group state table

**Status: agreed.**

**Proposed text** (capture §4.1, added):

> - With no track bound: start is rejected unavailable cause 6; stop and force do nothing and succeed; state is 0.
> - Group state: 6 if any track is 6. Otherwise 4 if started and every track is 4. Otherwise 2 if trigger_track is set, has not fired, and a track is 2 or 3. Otherwise 3 if a track is 2, 3 or 5. Otherwise 1.
> - start checks every track before starting any. In streaming, a track without a subscription makes start rejected unavailable cause 6 with TLV fn (0x05) = that track.

**Changes.**
- probe: the states already match (OepCaptureGroup.cpp:69-81). A streaming track without a subscription is found only while starting: the bound tracks are stopped and the answer is completed failed. Move the check before the start.
- fake: no error or waiting state (fake_capture.py:482-491).

### P2-○11 ○ Positioned read: beyond the write position, amount, from 3

**Status: agreed.**

**Proposed text** (common §1.2, added):

> - If the requested position (from 0) is beyond the write position, the answer is start = the write position, len 0, flags 0.
> - len is at most max and at most what fits in the answer within max_frame. more is set when bytes remain.
> - from 3 with arg > 0xFF is rejected malformed (a mark kind is u8).

**Changes:** probe: from 3 uses `arg & 0xFF` today and must refuse. fake: not checked.
**Today:** the probe clamps start to the end and len, as proposed.

### P2-○15 ○ analog trigger enum

**Status: agreed.**

**Proposed text:** registry `oep.fixture.analog` `[interface.enum.trigger]` loses level = 1 and edge = 2. The text already says 1 to 2 are for logic. **Changes:** generated constants removed. **Today:** the probe declares 0 / 3 / 4 only (OepAnalog.cpp:98) and refuses 1 / 2.

---

## 9. probe-config

### PC-1 ○ Line names are also found in the firmware's fixed labels

**Status: agreed.**

**Problem.** The most common user has a ready-made probe whose reset pin is fixed by the board. Its firmware can name that pin only in describe's 0x46 label. Today boot_reset does nothing until the user sets a settings label, and a host cannot find the reset line by any normative means.

**Proposed text** (probe-config §1.3, replaces the search rule):

> **Finding a slot's line** (name N, slot name S). Search in this order, and stop at the first step that finds exactly one channel:
> (a) a settings label equal to `S.N`;
> (b) only when the settings hold at most one slot item, a settings label equal to `N`;
> (c) only when the settings hold at most one slot item, a firmware label (describe of fn 0, 0x46) equal to `N`.
> A step that finds two or more channels ends the search with no line. Texts and names are compared ignoring ASCII case.

The sentence "Only the settings' label items are searched" is removed.

**Changes.**
- probe: `findLine` (OepConfig.cpp:1133-1181) adds step (c).
- Python `find_line`, the fake's `line_for` and JS: the same.
- Saved settings: a slot with boot_reset 1 and no settings label on a probe whose firmware labels `nrst` starts retrying with reset at boot.

**Q19.** Firmware labels as step (c) (recommended), or a new fn 0 tag `line(channel, name)`? A new tag would duplicate label.

**Answers.** Step (c) (bench welcomes it; ch32rv agrees and adds the step to its host).

### PC-2 ○ Names not in the table; standard and private names

**Status: agreed.**

**Proposed text** (probe-config §1.3, added):

> - A label text that is not in the table states no role (it is only a name). Standard names are listed in the registry (`[line_names]` of `oep.probe.config`). Adding one does not change the revision (core §2.7). A name for a role that is not standard starts with `x-` (example `x-acme-boot0`). Standard names never start with `x-`, and no name contains `.` (`S.N` uses it).

**Changes:** none. **Today:** no implementation checks names; only `nrst` is used by the probe.

### PC-3 ○ idle with a pull the channel lacks → unsupported

**Status: agreed.**

**Proposed text** (probe-config §1 idle, and the unsupported row of the refusal table):

> On a channel that does not have that pull, an idle with mode 1 or 2 is rejected unsupported (the item's tag as received). (Informative) A probe without `oep.fixture.gpio` gives the host no way to learn in advance which channels have pulls or outputs.

The review proposed malformed for mode ≥ 5. Under C-02 it is unsupported instead.

**Changes.** probe and fake accept it silently today. Saved settings: a saved idle 1 / 2 on such a channel is refused at boot, and the whole save is not applied (reason 3).

**Q20.** Is it acceptable that such a saved setting now fails at boot? Recommendation: yes. Today it reports success and the pin floats.

**Answers.** Yes (bench).

### PC-4 ○ The channel of label / idle / disable

**Status: agreed.**

**Proposed text** (probe-config §1, before the table):

> - **The channel of an item**: the channel of a label, idle or disable item is less than `channels` (fn 0 describe 0x43) and not in `reserved` (0x44). Otherwise the set is rejected unsupported (the item's tag as received).

disable's "(the same as idle)" then points here.

**Changes.** probe: label has no channel check today (OepConfig.cpp:250-252). idle and disable check the pin table's allowed set; that check can stay. fake: not checked for label. Saved settings: a saved label on a channel outside the range fails at boot.

### PC-5 ○ label text

**Status: agreed.**

**Proposed text** (probe-config §1 label):

> text: 1 to 32 bytes (registry `limits.label_max_bytes`) of valid UTF-8 without C0 control characters (0x00 to 0x1F) or 0x7F. Otherwise rejected malformed.

The parenthesis "(the label item itself is not restricted)" in §1.2 is removed. The replacement of `]` in a mixed marker stays.

**Changes.** probe and fake check only `len ≥ 3`; Python checks nothing. Saved settings: longer or invalid labels fail at boot.

**Q21.** Is 32 bytes enough (it matches slot names and owner)? Recommendation: yes.

### PC-6 ○ get's answer (wording)

**Status: agreed.**

**Proposed text** (probe-config §2, get row):

> answer: more(u8), hash(u32), the items to the end of the payload. Tag 0x7E is reserved for answer meta information, and a v1 probe does not place it. get takes no TLV (one is rejected malformed, core §7.3).

**Changes:** none.

### PC-7 △ The canonical form (wording)

**Status: agreed.**

**Proposed text** (probe-config §2 hash, added):

> In the canonical form a tag has its critical bit cleared. Keys are compared as numbers, and multi-field keys field by field from the first.

A test vector (items, canonical bytes, hash) goes in `tests/`. **Changes:** none if probe, fake and Python agree (not checked).

### PC-8 ○ Transport indexes across firmware versions; bind at boot

**Status: agreed.**

**Problem.** A user updates the vendor's firmware and never looks at bind again. If the USB configuration changes, the saved bind silently points at another port.

**Proposed text.**

Core §7.5, added:

> **Invariance of transport indexes**: a transport keeps its index across firmware versions of the same model. A firmware that adds a transport gives it an index not used before, and a removed index is not reused.

probe-config §1.2: the parenthesis "(review the bind)" is removed.

probe-config §2, added:

> At boot, a saved bind whose port is not a serial port of this firmware makes the save unreadable (reason 2). If applying any saved item is refused, the whole save is not applied (reason 3).

**Changes:** probe and fake already skip the whole save on a refusal (OepConfig.cpp:941-948; endpoint.py:2473-2504). A non-serial port gives reason 3 today; it becomes 2.

**Q22.** Index invariance (recommended), or keeping the transport kind with the bind? Invariance also keeps bind usable across updates, which a kind check would only detect.

**Answers.** Index invariance (bench: its files store bind ports as numbers).

---

## 10. Conformance

### C-10 ★ Normative words and what every probe and host must have (with O-14, O-15)

**Status: agreed.**

**Problem.** An implementer cannot find in one place which core ops a probe must answer (link_source? plan_apply on a probe without pins?) or what a minimal host must do. The English uses present tense and lower-case may / preferably without saying which are requirements.

**Proposed text.** Core, new §1.1 "Normative words":

> In capitals, MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are used as in RFC 2119 and RFC 8174. A statement in the present tense about what a probe or host does ("the probe returns ...") is a requirement (MUST). "Preferably" is SHOULD. Text marked (Informative), examples and notes are not normative. In the Japanese translation 「〜する／〜しない」 = MUST / MUST NOT, 「〜してよい」 = MAY, 「できれば〜する」 = SHOULD.

Core, new §1.2 "Conformance":

> A probe MUST implement:
> - at least one transport of §3, with its frame;
> - §4 to §6;
> - fn 0 confirm, list, describe, open, end, keepalive, lock_state, subscribe and unsubscribe, link_source and link_sink;
> - in describe of fn 0, unit_id, transport and max_op_ms.
>
> plan_apply and plan_release are required when any of its interfaces has plan roles. A probe without one answers unknown_operation. Optional: port_speed (§3.5), notifications other than fn 0's heartbeat, and every interface.
>
> A probe answers an op it does not implement with unknown_operation, and an optional function of an op it implements with unsupported.
>
> A host MUST: skip unknown TLVs and tags (§2.3, §2.4); follow §3.2 and the probing rule of §3.3; wait as §4.4 says; resend as §5.2 says; dispatch frames as §11.1 says.

Core §12 gains a column "Required" (yes / if plan roles / optional). Core §0 rule 4 ("the project has conformance tests") becomes "the project maintains the registry and the conformance material (test vectors, the fake)" until tests exist (O-8, a document item).

**Changes.**
- probe: on a build without plan roles, plan_apply answers unavailable today (Oep.h:432-435); it would become unknown_operation.
- probe: on platforms without a unique id it omits unit_id (Oep.h:478), against "mandatory" (see C-24).
- fake: implements all of these.

**Q23.** Keep the present-tense convention with this rule (recommended), or rewrite every normative sentence with capitals before the third-party review? A rewrite of the whole spec is large and risks changing meaning.

**Q24.** Shall link_source / link_sink be mandatory? Recommendation: yes. They are cheap, and hosts' link tests depend on them.

---

## 11. Other core rules

### C-16 ○ Rejected answers go into the resend table

**Status: agreed with condition** — ch32rv confirmed it and asked for the per-connection corr map of a relaying broker (folded in, 2026-10-02).

**Proposed text** (core §5.2, added):

> The probe stores the answer of every request of the last session that passes order 2 of §4.3, rejected answers included, and advances the newest corr with it. A host that corrects a rejected request sends it with a new corr.

**Added for ch32rv's question (does §5.2 bind a TCP endpoint such as the broker?).** Core §5.2, added:

> §5.2 binds every probe (C-05: every endpoint that answers OEP requests itself) on every transport, TCP included. TCP does not lose frames, but a host still resends after its wait (§4.4) when an answer is late, so the probe keeps the table to avoid executing a request twice. The table is one per probe, shared by all its transports and TCP connections, as the session is. A broker that only relays to an OEP probe keeps no table of its own; when it renumbers corr, it relays a client's resend with the same corr it used the first time. For that it keeps, per accepted client connection, the map from the client's corr to the corr it used upstream for at least the client's last max_inflight requests, and drops the map when that connection closes.

**Changes:** none for the probe, which stores every answer (OepEndpoint.cpp:450-463). fake: not checked. A TCP endpoint such as the WCH broker keeps the table.

**Answers.** bench and WireSkein: no objection. ch32rv was unsure whether §5.2 binds a TCP endpoint; the paragraph above answers yes. Open until ch32rv confirms.

### C-17 ○ When the lease restarts; the answer's lease_ms

**Status: agreed.**

**Proposed text.**

Core §6.1:

> The lease restarts (lease_ms counted again from when the answer is sent) at every answer to a request of the lock-holding session that passed order 3 of §4.3, rejected answers included. It does not restart on an answer replayed from the table of §5.2.

Core §6.4:

> The lease_ms of the answer is within lease_min_ms to lease_max_ms (1000 to 60000).

**Changes:** the probe already does both (OepEndpoint.cpp:441, 714). fake: no lower clamp, and an upper clamp of 600000 (endpoint.py:1094-1097); fix it.

### C-18 ○ session_id; open only as role 0x01

**Status: agreed.**

**Problem.** Two hosts that both use a fixed session_id (1, or a hash of the process name) silently resume each other's sessions.

**Proposed text** (core §6.1, §4.1):

> The host chooses the session_id for each session as an unpredictable 32-bit random value. It does not use a fixed value or 0. open with session_id 0 is rejected malformed. open is sent with role 0x01; an open with role 0x81 is rejected malformed.

**Changes.** probe and fake accept 0 and 0x81 open today; add two checks. Python (`SystemRandom`, 1 to 2^32−1) and JS (crypto, non-zero) conform and send open with role 0x01.

**Q25 (ch32rv).** How does the broker choose its session_id? Does it ever send open with 0x81?

**Answers.** ch32rv: a random non-zero session_id, reopened with the same id; open is always sent as 0x01, never 0x81. It conforms.

### C-22 ○ Booleans and text

**Status: agreed.**

**Problem.** owner is shown on other users' terminals. A host can put ANSI escape sequences into it.

**Proposed text** (core §2.1, added):

> - A boolean u8 is 0 (false) or 1 (true). In a request any other value is rejected malformed. In an answer the host reads any non-zero value as true.
> - Text in a request that is not valid UTF-8, or that contains C0 control characters (0x00 to 0x1F) or 0x7F, is rejected malformed. A host replaces such characters, and invalid UTF-8, before it shows text from an answer.

**Changes.**
- probe: no text validation anywhere today, and open's force treats any non-zero as true. It needs a small UTF-8 check for owner and label (slot names are already restricted).
- fake: the same.
- hosts: sanitize on display.

**Q26.** Probe-side validation (recommended), or host-side only? The probe is the one place every viewer's text passes through.

### C-23 ○ Grammar of names, model and chip

**Status: agreed.**

**Proposed text.**

Core §13 rule 1, added:

> Each label of a name is 1 or more of `a-z 0-9 -`, and does not start or end with `-`. A name has at least two labels.

Core §7.5 model:

> A model that is not the project's own starts with its maker's reverse domain name, with `.` replaced by `-` (example `com-example-probe1`).

Core §7.5 chip:

> `<part> v<revision>`. part is 1 to 24 of `a-z 0-9`. revision is digits with optional `.digits` groups. When the revision is unknown, the part alone.

**Changes:** the interface names in use conform. The models of the reference firmware and the chip strings were not checked.

**Q27.** Is the model prefix rule acceptable? Recommendation: yes. Hosts keep per-model tables (speeds), and a collision between makers picks the wrong one.

### C-24 ○ unit_id without a unique number or storage

**Status: agreed.**

**Proposed text** (core §7.5, replaces the build-constant sentence):

> A probe with storage but no unique number creates its unit_id at first boot from a random number and saves it. A probe with neither uses a unit_id that starts with `x-` (not unique). A host does not group transports by a unit_id that starts with `x-`, does not name a probe by it, and does not key anything it keeps across sessions by it (for example a record of a port's link speed), so that another unit on the same port inherits nothing.

**Changes:** the probe omits unit_id on platforms without one (Oep.h:478), which breaks "mandatory". It must send an `x-` value. Hosts: one check.

**Answers.** WireSkein asked that the client's speed record (keyed by port + unit_id) treat an `x-` unit_id as naming no unit; folded into the text above.

### C-25 ○ Exclusive open, HID output, WinUSB

**Status: agreed.**

**Proposed text** (core §3.3, added):

> - The host opens a serial port and a HID exclusively where the OS allows it (on Linux, TIOCEXCL on a tty).
> - A probe that exposes HID accepts output reports both on its interrupt OUT endpoint and by SET_REPORT (Output).
> - A probe that exposes vendor bulk SHOULD give that interface the Microsoft OS 2.0 compatible ID `WINUSB`.

**Changes:** Python already opens exclusively (flock and TIOCEXCL). HID and WinUSB in the probe were not checked.

**Q28.** WinUSB as SHOULD (recommended) or MUST? Without it, Windows users need a driver install.

### C-29 ○ Registry keys and the hash

**Status: agreed.**

**Proposed text** (core §0, after the registry sentence):

> After the freeze the registry's keys (and so the generated identifiers) are not renamed; new keys are added. REGISTRY_HASH only tells whether generated code matches the registry and says nothing about wire compatibility. Values that are not the specification's (max_op_ms_reference) are kept in a `[reference]` table outside the freeze.

**Changes:** none on the wire.

### C-30 ○ instance per (name, revision)

**Status: agreed.**

**Proposed text** (core §7.2, replaces "Those with the same name are numbered from 0 in ascending order of fn"):

> Interfaces with the same (name, revision) are numbered from 0 in ascending order of fn.

**Changes:** none today; every probe exposes one revision of each name.

### C-32 ○ port_speed: baud tolerance and verify_ms 0

**Status: agreed with condition** — ch32rv: verify_ms 0 is malformed in step 0 (try) only (folded in).

**Proposed text** (core §3.5 refusals):

> If the nearest speed the UART can produce differs from the request by more than 2 %, rejected unsupported. The answer's baud is the speed actually applied. verify_ms 0 in step 0 (try) is rejected malformed. In step 1 (commit) and step 2 (revert) verify_ms has no meaning and any value is accepted.

**Changes:** probe: the per-platform handler decides what it can produce (its tolerance was not checked). verify_ms 0 in a try is accepted today and reverts at once. fake: not checked.

**Answers.** ch32rv sends verify_ms 0 on commit and revert; its condition, "malformed for step 0 (try) only", is folded in above.

**Q29.** Is ±2 % acceptable? Recommendation: yes. With both ends at ±2 % the total stays inside what 8N1 sampling tolerates.

### C-33 ○ Heartbeat floor

**Status: agreed.**

**Proposed text** (core §11.3): "The probe may round a heartbeat period shorter than 100 ms up to 100 ms."
**Changes:** none required (the probe has no floor; that conforms).

---

## 12. Console dmseq

Checked against: `docs/target-console-dmseq.md` (cdd26b4), `experiments/dm-console-seq/DmSeqTest/DmSeq.h` (the 2026-09-24 experiment), the shipped target library ArduinoCore-CH32RV `libraries/SerialDMSeq` (outside this repo), and the probe's `src/OepDmConsole.cpp`.

### DS-1 ★ DATA0 = 0 is no answer

**Status: agreed.**

**Problem.** Target rule 1 makes a 0 word an invalid answer (its CRC fails), so the target posts again at once. The debugger bullet says the target reads 0 as silence and waits until its timeout. The two implementations differ:
- The experiment posts again at once, on every poll.
- The shipped library treats 0 as "no answer". It posts again every 20 ms only after its timeout. Before that it waits out the wait, up to 1 s after a host has answered once.

**Proposed text** (target rules, new item before rule 1):

> **A word of 0 is not an answer.** While DATA0 reads 0, the target keeps waiting for the answer (the wait time runs on) and posts its frame again once every short wait. It does not treat 0 under rule 1.

The debugger bullet changes to match DS-9.

**Changes:** shipped library: post again on the short-wait timer also before the timeout (today only when latched). experiment: optional. probe: none (it reads bit 7 = 0 as "nothing yet").

**Q30 (ch32rv).** Post again every short wait (recommended), at once (the experiment), or never (the library before the timeout)? Posting at once costs a store on every poll of a target with no debugger (the library's reason). Never posting costs up to 1 s of console after a debugger cleared DATA0.

**Answers.** Every short wait, adopted. ch32rv prefers it: its host reads bit 7 = 0 (0 included) as "nothing yet" and polls every 2 ms, and its DM accesses can leave DATA0 = 0. bench and WireSkein: no objection. DS-8 depends on it.

### DS-2 ★ The ownership rule lists the target's exceptions

**Status: agreed.**

**Proposed text** (Carrier and ownership, replaces the three bullets):

> - The target writes DATA0 / DATA1 only:
>   (a) at begin() (DS-6);
>   (b) to post a frame when bit 7 of DATA0 is 0;
>   (c) to post its outstanding frame again: under rule 0 (bit 7 is 1 but the word is not the one it posted), under rule 1, at the timeout, while keeping a frame posted, and under DS-1.
> - The host writes only when bit 7 is 1 (a target frame is there).
> - Apart from (c) over a word with bit 7 = 1 that is not the target's own frame, neither side overwrites a word the other side wrote.

**Changes:** none (text only).

### DS-3 ★ The waits are real-time lower bounds

**Status: agreed.**

**Proposed text** (Timeout, replaces "So that the wait ends even while interrupts are disabled, it is counted in register reads, not with a clock"):

> The short wait lasts **at least 20 ms** and the long wait **at least 1 s** of real time. The target measures them in a way that still ends while interrupts are disabled. "Every short wait" (keeping a frame posted, DS-1) uses the same measure. (Informative) Counting reads of DATA0, the reference targets use F_CPU / 8000 reads per ms, assuming one read loop takes at least 8 cycles.

**Changes:** none. A host relies only on "a synced host that polls at least once per second loses nothing".

### DS-4 ★ Byte order

**Status: agreed.**

**Proposed text** (Target frame, added):

> Byte k of DATA0 (k = 0 to 3) is bits 8k to 8k+7 of the register (byte0 is the least significant byte). Byte k of DATA1 is bits 8k to 8k+7 of DATA1 and carries payload byte 3+k. Example: an empty SYN frame with S = 0 and A = 1 has byte0 0x98 and CRC 0x32, so DATA0 = 0x00003298. A host answer with K = 0, H = 0, M = 0 is DATA0 = 0x0000F300.

**Changes:** none. All three implementations (experiment, library, probe) assemble words this way.

### DS-5 ○ What restarts the count of invalid words

**Status: agreed.**

**Proposed text** (host rule 1, added):

> The host counts consecutive polls that read an invalid word with bit 7 = 1 (`0xffffffff` included). The count restarts at 0 when it reads a valid frame, after it answers under this rule, and when a session starts. A poll that reads a word with bit 7 = 0 does not change the count. The rule-1 answer is sent only while the host is synced. While it is not, the count stops at 3 (it does not wrap) and the host does not answer; the next valid frame syncs the host and restarts the count.

**Changes:** probe: as proposed (OepDmConsole.cpp:195-204), except that `start()` does not reset `seq_bad_run_`. Add that, and check that the count saturates while unsynchronised (not checked).

**Answers.** ch32rv conforms and gave these details of its host, folded in above: the count resets on a valid frame, after the rule-1 answer and at session start; the rule-1 answer fires only when synced, and the count saturates while unsynced; an unsynced `0xffffffff` goes to its leftover count, the one its DS-8 safeguard uses. When the safeguard goes (DS-8), that word is simply one more invalid word in the count above.

### DS-6 ○ The target's state at begin()

**Status: agreed.**

**Proposed text** (Target frame, added):

> At begin() the target sets SYN and may write 0 to DATA0. S and A may start at any value, because the host resynchronises on SYN (host rule 3). (Informative) The reference targets start with S = 0, A = 1 and write DATA0 = 0.

**Changes:** none (experiment and library both do S = 0, A = 1, DATA0 := 0).

### DS-7 ○ "After reading for a long time"

**Status: agreed.**

**Proposed text** (replaces the last host bullet):

> (Informative) A target that prints or polls its input posts a frame at least once per long wait plus a short wait. A host that has read no valid frame for 3 s while unsynchronised may tell the user that no dmseq console is answering. A target that neither prints nor reads posts nothing, so this is not proof that it has no console.

**Changes:** none (the probe does not report it).

### DS-8 ★ Remove the optional host safeguard

**Status: agreed with condition** — ch32rv: removed only together with DS-1 (folded in).

**Problem.** The bullet "an unsynchronised host that reads 0xffffffff 3 times may write an invalid word with bit 7 = 0" exists for targets without rule 0, and rule 0 is mandatory. It is also the only rule that lets a host write while bit 7 is 1 for a reason other than answering.

**Proposed text:** delete the bullet "host (optional): ...", **in the same change as DS-1** and not before it.

**Changes.**
- ch32rv: **its host does write the word** (corrected from the first version): an unsynchronised host that reads `0xffffffff` 3 times writes 0x7f7f7f7f, because a WCH-Link attach leaves the last ESIG word in DATA0 on some targets. ch32rv drops the write once the target library re-posts every short wait (DS-1).
- probe: none (no 0x7f7f7f7f path).
- target library: none for DS-8 itself. It implements rule 0 (SerialDMSeq.cpp:127-141), and DS-1 makes it re-post every short wait. The 2026-09-24 experiment implements neither, but it is a record, not a target anyone ships.

**Answers.** ch32rv's condition: remove the safeguard only if the target always re-posts (DS-1). Adopted: DS-1 and DS-8 go in together.

### DS-9 ○ Clearing dmactive *may* clear DATA0

**Status: agreed.**

**Proposed text** (debugger bullet):

> **Do not reset the debug module when detaching** (do not clear DMCONTROL.dmactive). Clearing it may return DATA0 and DATA1 to 0, and the frame the target had posted is then lost. The target posts it again within a short wait (DS-1).

**Changes:** none. The general statement was checked on one target family only (the record keeps that).

### DS-10 ○ CRC-8 check values

**Status: agreed.**

**Proposed text** (CRC-8, added):

> Check values: the 9 ASCII bytes "123456789" → 0xFB; the single byte 0x00 → 0xF3.

**Verified:** both values computed with a bit-wise implementation of poly 0x07, init 0xFF, no reflection, no final XOR. That is the same function as the probe's `seqCrc8` and the library's 16-entry-table form. The DS-4 examples come from the same computation.

**Q31.** None of DS-3 to DS-10 changes the wire. ch32rv: please confirm that your host side (if it reads dmseq itself) agrees with DS-4 and DS-5.

**Answers.** ch32rv: DS-4 conforms; DS-5 conforms with the details folded into DS-5. bench and WireSkein: no objection.

---

## Dropped findings

| Finding | Why dropped |
|---|---|
| P2-○7 "undefined values: console and capture should say malformed like the fixtures" | Reversed by C-02. The console's and capture's unsupported is right, and the fixtures move to it |
| P2-○12 io_voltage describe tag before the freeze | An optional describe tag can be added after the freeze without changing the revision (core §2.7). There is nothing to fix now, and the number is better chosen together with a probe that has a level shifter |
| P2-★1's exclusion of labelled channels | Users label exactly the debug pins they want scanned, so excluding them would hide the target |
| PC-3's "idle mode ≥ 5 malformed" | Replaced by C-02 (unsupported) |
| C-06's "add the earlier answers' sizes" | Replaced by starting each wait at the previous answer, which is simpler and exact |
| C-11 | Decided by the user (no change) |

## Implementation bugs found while checking (check-similar)

These are bugs against **today's** text; they need no peer decision.

| Where | What |
|---|---|
| probe Oep.h:478 | unit_id (mandatory) is omitted on platforms without a unique id (C-24) |
| probe OepCh32Dm.cpp:79, 145, 451; OepDmConsole.cpp:48 | Ops and the console require DMSTATUS.version == 2. A 1.0 DM is found but never treated as halted (P2-○1) |
| probe OepRvswdPhy.cpp:207-213, OepTarget.cpp:128-140 | After a connection closes, RVSWD with idle_clock low keeps driving SWCLK. Channels without an idle keep the PHY's state. Against core §8 ("must not leave a pin under its own drive") |
| probe scan | Tried pins are left Hi-Z, not returned to their idle state (debug §1) |
| probe OepTarget.cpp:335, OepCh32Dm.cpp:41-46 | rvswd / swio scan runs the full attach (wake, configuration, dmactive, ABSTRACTAUTO, 256 PROGBUF0 writes), not dmactive only (debug §1; P2-★8) |
| probe OepCapture.cpp:466-475, OepSampler.cpp:193-202 | Logic capture switches pins to input and does not restore them (P2-○13) |
| probe OepP4SpiTarget.cpp:22 | A channel outside the declaration is refused unavailable, not unsupported (core §8 plan_apply table) |
| probe OepConfig.cpp:261 | idle's unsupported carries 0x00 instead of the item's tag as received (probe-config §1, 9ed53e7) |
| probe OepTarget.cpp:243, 410 | attach's unsupported always carries `pins | 0x80`, not the tag as received |
| fake endpoint.py:454-455 | The transport list is built in TLV order, ignoring the index byte |
| Python link.py:422, 550 | Resync confirms send the range 0..0xFF (C-15) |
| JS link.js | No confirm-based resync on length-prefixed ports (core §5.1) |
| Rust (ch32rv, reported by ch32rv) | single_serial flattened the transport TLV's value instead of reading its kind byte. Fixed locally by ch32rv |
