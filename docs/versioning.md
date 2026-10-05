# OEP versioning and stability

[日本語](versioning.ja.md)

Status: **guide** (not normative). The promise of what stays stable, gathered from [the scope of the freeze](v1-freeze-decisions.md) §0 (record,
2026-10-02), the review guide and core §2.7. The rules themselves are in [OEP core](oep-core.md) (§2.3, §2.5, §2.7, §7.1, §13) and at the top of
core and `registry/oep-v1.toml`; where this page and they differ, they are right. The release tagging in §6 is a **proposal** that waits for the
maintainers' decision. This English text is authoritative; the Japanese version is its translation.

## 1. What carries a version

| What | Where it is carried | Changes when |
|---|---|---|
| **Protocol revision** | confirm's revision (u8; v1 = 1), negotiated per transport (core §7.1) | The form of the core changes (core §2.7). confirm itself, its magic and the 64-byte rule never change |
| **Interface revision** | list's revision per fn (u8), and the registry's `revision` per interface | The meaning or length of the interface's fixed part changes (core §2.7) |
| **Interface name** | list | The meaning of the interface changes (a different name is a different interface) |
| **Registry schema** | `[registry] schema` (1) | The layout of the registry file changes (not the wire) |
| **REGISTRY_HASH** | the generated files | Any byte of the registry changes. It only tells whether generated code matches the registry; it says nothing about wire compatibility (core, top) |
| **Specification release** | a git tag of this repository (§6, proposed) | Any change to the normative text or the registry |

## 2. Before the freeze (now)

OEP v1 is a candidate for the freeze. Until the freeze, breaking changes go in **without raising any revision**: there are no users to keep
compatible, and the reference implementations follow each change at once. No compatibility or migration notes are written for these changes.

## 3. What the freeze stops

From the freeze on, these change only by raising a revision:

- the form of frames: COBS + CRC-16, `length(u16)`, the HID report, the order and length of headers, the 64 bytes before confirm (core §3);
- the form of messages: the fixed parts of request / answer / event / data, the TLV forms and the critical rule, reject reasons, outcomes, the
  order of refusal (core §2, §4);
- the payloads of the standard interfaces: op tables, fixed parts, TLV tags, events, status, the lifetime of resources (`oep-if-*.md`);
- **every number in `registry/oep-v1.toml`**: op, tag, reason, status, enum, `timing`, `limits`, `usb`, the names and revisions of interfaces.
  The `[reference]` table (values of the reference firmware) is outside the freeze;
- the normative sentences of the core, the `oep-if-*` documents and dmseq.

An interface that changes its fixed part or a meaning raises its revision; a change to the form of the core raises the protocol revision
(core §2.7).

What stays free after the freeze: the guides and the reference numbers in them, the records (appending is free), the release tests, the fake's
behaviour where the specification leaves the choice to the probe, and every implementation's own policy and declared values.

## 4. What can be added without a revision

These additions keep every revision; a host or probe that does not know them keeps working (core §2.3, §2.7):

| Path | Rule |
|---|---|
| Optional request / answer / event TLVs | New tags in the op's context. A host skips unknown non-critical tags; a probe refuses an unknown critical one with unsupported (core §2.2, §2.3) |
| Appending at the end | The tail of answer TLV values, event payloads, elements of answer sequences, and items the probe keeps (probe.config). Readers skip the unknown tail (core §2.3). Request TLV values are not extended: a new field gets a new tag |
| Optional ops and events | Interface ops 0x01 to 0xEF, event kinds 0x01 to 0x7F; their presence is declared in describe (core §2.5, §2.7) |
| New enum values and reserved bits | A value the definition left unused is refused unsupported by a probe that does not know it (core §2.5, §4.3 order 6) |
| Interface reject reasons and status values | 0x40 to 0x7F (core §2.5, common §3) |
| describe tags | Common 0x01 to 0x3E, interface 0x40 to 0x7F; describe values themselves are closed (core §2.3, §7.4) |
| probe.config items and line names | New item tags, the tail of items; standard line names in the registry (probe settings §1, §1.3) |
| New interfaces | `oep.` names through this repository; anyone's reverse-DNS names without registration (core §13) |
| New transports | A new transport kind with its frame scheme (core §3.1) |

A probe that raises an interface's revision preferably keeps exposing the old revision as another fn (core §2.7), so that older hosts keep working.

## 5. The registry's promise

- After the freeze, **keys are never renamed and never removed**; new keys are added (core, top; registry header). Generated identifiers come from
  keys, so code built on them keeps compiling.
- A key's value never changes (it is a frozen number, §3). An experimental value (0xF0 to 0xFE in u8 enums, ops 0xF0 to 0xFF) is never registered
  (core §2.5).
- A new table kind, or a new key of an interface or an op, is a registry change made by a pull request (CONTRIBUTING).

## 6. Specification releases (proposal)

To decide: the maintainers. Proposed:

- **Git tags `vMAJOR.MINOR.PATCH`** on this repository, pushed with the commit they name.
  - MAJOR is the protocol revision (`v1.y.z` for protocol revision 1).
  - MINOR grows with any addition of §4, a new interface or a new interface revision, and any registry addition.
  - PATCH grows with errata that change no behaviour: wording, translations, guides, records, tools.
- **Pre-releases** for review: `v1.0.0-rc.N`. **The freeze is the tag `v1.0.0`.**
- A tag is made only on a commit where `python3 tools/oepgen1.py --check` and `python3 tools/oepvectors1.py --check` pass and
  `cd tests && uv run pytest registry_v1 vectors` is green.
- **CHANGELOG.md** at the root lists the changes per release (date, tag, the commits), and an "Unreleased" section collects changes until the next
  tag. Every change to the normative text or the registry gets an entry; wording-only changes may be grouped.
- Implementations state the tag they implement (for example in their README), together with the protocol and interface revisions they handle.
- Whether the registry also carries a release string (for example `[registry] edition`) is a registry change and is left to the peers' review.

## 7. Errata after the freeze

An erratum that only fixes wording is a PATCH. One that changes behaviour is a rule change: it follows the revision rules above and
[CONTRIBUTING](../CONTRIBUTING.md).
