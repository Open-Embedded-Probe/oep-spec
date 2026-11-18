# OEP versions and stability

[日本語](versioning.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative). It collects the promises about what does not change. The rules themselves are in [OEP core](oep-core.md) (core §2.3, §2.5, §2.8, §7.1, §12) and at the head of the core and of `registry/oep-v1.toml`;
where this page disagrees with them, they are right.


## 1. Things that have a version

| Thing | Where it is carried | When it changes |
|---|---|---|
| **Protocol revision** | The revision in confirm (u8; v1 = 1). Agreed per transport (core §7.1) | When the shape of the core changes, or behaviour that breaks an existing contract changes (core §2.8). Confirm itself, its magic and the 64 byte rule do not change |
| **Interface revision** | The per-fn revision in list (u8) and the per-interface `revision` in the registry | When an existing contract breaks: the fixed parts, mandatory functions, state transitions, resource lifetimes and so on (core §2.8) |
| **Interface name** | list | When the meaning of the interface changes (a different name is a different interface) |
| **Registry schema** | `[registry] schema` (1) | When the layout of the registry file changes (not on the wire) |
| **REGISTRY_HASH** | The generated files | When any byte of the registry changes. It only shows whether the generated code matches the registry and says nothing about compatibility on the wire |
| **Specification release** | A git tag of this repository (§6) | When normative text or the registry changes |

## 2. Before the freeze (now)

OEP v1 is before its freeze. Until the freeze, breaking changes go in **without raising any revision**. Since revision 1 alone cannot decide compatibility, an implementation states the specification commit or tag it follows. Numbers removed before the freeze may be reused. The specification keeps no migration steps between pre-freeze versions.

The freeze happens with the official `v1.0.0` release (§6). Until the freeze the Japanese documents (`.ja.md`) are maintained as authoritative. Every Japanese document has an English URL (`.md`) with the same name without `.ja`; until its English translation exists, that file holds only a link to the Japanese version (links can point at the English URL from now on; no translation that goes stale is kept). The English translation is made before `v1.0.0`; after that English is normative and Japanese is the parallel translation, and both are maintained together.

### 2.1 Provisional fixing of the core

Ahead of the official freeze, the existing contracts of the core and transports are fixed as the basis for implementations.
The scope is messages / frames, the 8 operations of fn 0, discovery and identification, TLVs and unknown values, resending, session / lease, the general rules for channels and resources, the common contract of notifications and extensions,
and the registry numbers, widths and time conditions they use. Adopting common parts and the functions of individual OEPs stay within the scope of each interface.

No new mandatory operation, mandatory declaration or state table is added to this scope; functions are defined in optional interfaces.
A proposal that changes an existing meaning, width, number, mandatoriness, resending or resource lifetime updates the provisional basis by showing a contradiction or a counterexample where independent implementations cannot work, together with a boundary check.
Clarifying the wording and optional additions that keep the existing contracts are allowed. Each implementation states the Git commit after the update.

Provisional fixing is not the official freeze that carries a §6 tag, and not a conformance certification of implementations.
Compatibility between revision 1 implementations before the official freeze is still checked by commit / tag. After the official freeze, the revision and release rules of §3 to §7 apply.

## 3. What the freeze stops

After the freeze, the following change only by raising a revision:

- The shape of frames: COBS + CRC-16, `length(u16)`, the HID report, the order and length of the header, the 64 bytes before confirm (core §3);
- The shape of messages: the fixed parts of request / answer / event / data, the shape of TLVs and the critical rule, the reject reasons, outcome, the order of refusal (core §2, §4);
- The payloads of interfaces whose names begin with `oep.`: the op tables, fixed parts, TLV tags, events, status, resource lifetimes (`interfaces/oep-if-*.md`);
- **Every number in `registry/oep-v1.toml`**: op, tag, reason, status, enum, `timing`, `limits`, `usb`, interface names and revisions,
  retirements (a value removed after the freeze stays as retired and is not used for another meaning). The reference firmware's values (max_op_ms, wire times and counts) are outside the specification;
- The normative text of the core, of the `oep-if-*` documents and of dmseq.

An interface change that breaks an existing contract raises the interface revision; a change to the shape of the core or to behaviour that breaks an existing contract raises the protocol revision (core §2.8). Changing something from optional to mandatory is also a breaking change and is not treated as a mere functional addition.

Free even after the freeze: the guides and the reference numbers in them, tests before a release, the behaviour of the virtual bench where the specification leaves the choice to the probe,
and each implementation's policy and declared values.

### 3.1 What is fixed on purpose, and why

This shows the boundaries that keep the existing contracts, and where to extend. The rules and reasons for specific operations are in each interface.

| Boundary | Reason | Where to extend |
|---|---|---|
| One lock and one resend ordering state | Keeps the owner and resource lifetimes small | Sharing among several hosts is a broker. Several independent sessions are a new protocol revision |
| list / describe fixed within a boot | Keeps caching and paging consistent | Connections and free capacity are state query ops. Changing the set of offered functions is a restart |
| The shapes of fixed parts and array elements are not extended | The length and meaning are decided from the revision | Optional TLVs, TLVs with an element index, or a new revision |
| Finite number spaces such as op / tag | Each name can be handled by a small parser | Optional additions by the owner, an interface with another name |
| The 64 bytes before confirm and the per-transport frame | Discovery works even before the capabilities are known | A function that needs it uses a larger max_frame. A new list that can be split uses a dedicated query op |
| Authentication and firmware update methods are not made mandatory in the core | Product-specific state is not imposed on the minimal implementation | Authenticated transports, optional policy refusal, dedicated interfaces |

## 4. What can be added without changing a revision

After the freeze, these are the only ways OEP grows (core §12.1). Adding them changes no revision. Hosts and probes that do not know them keep working (core §2.8):

| Way | Rule |
|---|---|
| Optional request / answer / event TLVs | A new tag in the context of the op. A host skips unknown non-critical tags, and a probe refuses unknown critical tags with unsupported (core §2.2, §2.3) |
| Optional ops and events | Interface ops 0x10 to 0xFF, event kinds 0x01 to 0x7F. Whether they exist is declared in describe (core §2.5, §2.8) |
| New enum values and reserved bits | In requests: a value the definition did not use is refused with unsupported by a probe that does not know it (core §2.5, §4.3). In answers, events and data: it can be added only when the presence, length and position of every field do not depend on that value, the handling of unknown values in core §2.4 is safe, and every field whose meaning depends on that value is ignored or shown raw by a reader that does not know the value (core §2.5). Otherwise a new TLV, revision or interface |
| An interface's reject reasons, unavailable causes and status values | 0x40 to 0x7F (core §2.5, common §3) |
| describe tags | Common 0x01 to 0x3F, interface 0x40 to 0x7E. Like every fixed shape, describe values are not extended (core §2.3, §7.4) |
| Named extension TLVs | Tag 0x7F in any context, `name_len, name, data`. Others can add them under their own reverse-DNS names. They take no number (core §2.2, §12 rule 7) |
| Name lists | Console mechanisms, network ports. Standard names are in the registry, others use reverse-DNS names. The number is the position in the probe's list (core §7.7) |
| Settings items and line names | New items of the core and of `oep.` interfaces (registry settings; the meaning and shape of a name do not change, core §13.1). Others put items in an interface under their own name. Standard line names are in the registry and in the host guide §5.3 (a host convention) |
| New interfaces | `oep.` names go through this repository. Reverse-DNS names by anyone, without registration (core §12) |
| New common operations | The core assigns them to the unassigned 0x03 to 0x0F, and each fn that supports one declares it in ops (core §12.1) |
| New transports | A new transport kind together with its frame scheme (transports §1) |

A probe that raises an interface revision should, where it can, keep offering the old revision under another fn as well (core §2.8), so that old hosts keep working.

## 5. Promises of the registry

- After the freeze, **keys are not renamed and not removed**. New keys are added (head of the registry). The generated identifiers are made from the keys,
  so code that uses them keeps compiling.
- The value of a key does not change (frozen numbers, §3). A value removed after the freeze stays as retired and is not used for another meaning. To try something, use an interface under your own reverse-DNS name (core §12).
- New table kinds, and new keys of interfaces or ops, are registry changes by pull request (CONTRIBUTING).

## 6. Specification releases

- This repository gets a **git tag `vMAJOR.MINOR.PATCH`**, pushed together with the commit it points at.
  - MAJOR is the protocol revision (protocol revision 1 is `v1.y.z`).
  - MINOR increases with the additions of §4, a new interface or a new interface revision, and additions to the registry.
  - PATCH increases with errata that do not change behaviour: wording, translation, guides, records, tools.
- **The first tag is `v1.0.0`**; it is both the official release and the freeze. No tag is made before it.
- **Before the freeze, revision 1 alone does not determine one shape**: breaking changes go in without raising the revision (§2), so two implementations made from different commits
  may both say revision 1 and still not work together. So an implementation before the freeze states the specification commit it implements.
- A tag is put only on a commit where `python3 tools/oepgen1.py --check` and `python3 tools/oepvectors1.py --check` pass and `cd tests && uv run pytest`
  passes.
- The root **CHANGELOG.md** lists the changes of each release (date, tag, commit), and changes up to the next tag are collected in the "Unreleased" section. Every change to normative text or
  the registry has an entry. Wording-only changes may be grouped.
- An implementation writes the tag it implements (in its README), together with the protocol and interface revisions it handles. A probe
  may also put the tag in the free text `firmware` (0x40) of the fn 0 describe, so that a host can show it when it investigates a mismatch.

## 7. Errata after the freeze

Errata that only fix wording are PATCH. Those that change behaviour are rule changes and follow the revision rules above and [CONTRIBUTING](../CONTRIBUTING.md).
