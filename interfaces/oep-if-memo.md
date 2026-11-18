# OEP interface: memo area v1

[日本語](oep-if-memo.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **normative** (v1). For the freeze state and the language and compatibility policy, see [Versions and stability](../docs/versioning.md). The core is [OEP core](../docs/oep-core.md). The only definition of the numbers is `registry/oep-v1.toml`.

| Name | revision | Role | Target family |
|---|---:|---|---|
| `oep.probe.memo` | 1 | a host keeps small named data on a probe and reads it back later | used for every family |

- It lets a host keep per-probe records (the connected target, the wiring of a fixture, test preparations and so on) on the probe itself. When the probe is moved to another host,
  the records go with the probe.
- `oep.probe.memo` is an optional interface. A probe puts at most one `oep.probe.memo` in list.
- **Transport size**: a probe that puts `oep.probe.memo` in list makes the max_frame (core §4.4) of every transport 128 or more. Even a write with a 64 byte name
  can then carry 39 bytes of data at once after the header and the fixed part (89 bytes).
- **The probe does not use the memo area**: the probe does not read the stored data, gives it no meaning, and changes no behavior by the contents of the memo area. No rule of OEP
  relies on the contents of the memo area. Values that decide the behavior of the probe belong in the settings (core §13). Settings and the memo area are separate things and do not affect each other's storage, amounts or rules.
- **There is no distinction of owners**: an object is determined by its name alone. For any tool of any host, the same name refers to the same object.

## 1. Objects

The memo area is a collection of objects. An object has a name, data and a crc.

- **Name**: text (core §2.1) of 1 to 64 bytes. The probe compares names as byte strings (no reinterpretation that ignores case or normalization).
  The kinds of characters are not restricted.
- **Data**: a byte string of 0 to max_object bytes. The probe does not know the form of the data.
- **crc**: u32. When writing, the host puts the CRC-32 of the whole data; the probe checks it when the write finishes and keeps it with the data. On reading, the probe returns
  the value it holds. CRC-32 is CRC-32/ISO-HDLC (polynomial 0x04C11DB7, initial value 0xFFFFFFFF, input and output reflected, final XOR with 0xFFFFFFFF,
  "123456789" → 0xCBF43926; the same as crc32 of zlib). The crc of data of length 0 is 0.

describe (in addition to the common tags of core §7.4):

| tag | Name | Value |
|---:|---|---|
| 0x40 | max_object | u32. **Required**. 1 or more. The maximum length (bytes) of the data of an object |
| 0x41 | max_objects | u16. **Required**. 1 or more. The number of objects that can be held at once (all of them can be pointed to with first (u16) of list) |

- The probe guarantees that it can hold up to max_objects objects at once, each with a 64 byte name and max_object bytes of data. The declaration is a guarantee: a probe
  may be able to hold more than declared, but a probe is never made that can hold less than declared.
- No lower limit is defined. The host reads the declaration and does not use the memo area if it is not enough.

## 2. Operations

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x10 | list | first(u16), prefix(text, 0 to 64 bytes), [TLV] | more(u8), count(u8), count × (name(text), size(u32), crc(u32)), [TLV] | not needed | required |
| 0x11 | read | name(text), offset(u32), max(u16), [TLV] | size(u32), crc(u32), len(u16), data, [TLV] | not needed | required |
| 0x12 | write | name(text), size(u32), offset(u32), crc(u32), len(u16), data, [TLV] | —, [TLV] | needed | required |
| 0x13 | delete | name(text), [TLV] | —, [TLV] | needed | required |

Every text is placed in the form `len(u8), bytes`.

### 2.1 list

- Lists the objects whose names start with prefix (all of them if prefix is empty). The probe decides the order of the list. The order does not change until an object is added or deleted.
- first is the position (from 0) in that order from which to return. count is the number put in the answer; the probe puts as many as fit in the max_frame (core §4.4) of the transport the request came on.
  more is 1 if more matching objects follow, otherwise 0. The host adds count to first to read the rest.
- size is the length of the data, and crc is the crc the object holds (§1). An object being written (§2.3) is not listed.

### 2.2 read

- Returns up to max bytes of the data of the object name, from offset. The returned len is the smallest of max, size minus offset, and the length that fits in the max_frame
  of the transport the request came on. If offset is size or more, len is 0.
- size and crc are the values of the whole object (§1). After reading everything, the host compares the CRC-32 of the data with crc (§3).
- If the object name does not exist, rejected no_resource. An object being written (§2.3) is also treated as not existing.

### 2.3 write

One object is written with one write, or with several writes in order of offset.

- **Start**: a write with offset 0 starts writing the object name. The previous data is then discarded (if an object with the same name exists,
  its contents MAY be lost at this point). Until the write finishes, the object is being written and appears in neither list nor read.
- **Continuation**: a write with offset other than 0 continues the object being written. name, size and crc MUST be the same values as in the starting write, and offset MUST be the number of bytes
  received so far. Otherwise rejected unavailable (cause 6, wrong_state), and the object being written does not change.
- **End**: at the write where the number of received bytes reaches size, the probe compares the CRC-32 of the whole data with crc. If they match, it finishes writing the object and
  answers completed success. If they do not match, it answers completed failed. The object then does not exist (the previous one is also gone; read in §2.2 is
  no_resource). An object of size 0 is written with one write with offset 0 and len 0.
- **One object being written**: the probe holds at most one object being written. A write that starts another write (offset 0), a delete of that object,
  and the end of the session holding the lock (end, expiry, force; core §6, §9) discard the object being written.
- **Refusals** (nothing changes):
  - size is larger than max_object: rejected unsupported (a value of the fixed part, tag 0x00).
  - the data of one write goes beyond size: rejected malformed.
  - a write that starts with a new name when max_objects objects already exist: rejected unavailable (cause 2, limit).
  - the medium cannot be written: completed failed. The object MAY be gone.
- One write finishes within max_op_ms (core §7.5), like any other op. The host splits the data it sends at once to fit the max_frame of the transport.

### 2.4 delete

- Deletes the object name. If it does not exist, rejected no_resource. A delete of the object being written discards it and answers completed success.

## 3. Storage and power loss

- The memo area survives restarts (including `oep.probe.restart`) and power loss. OEP has no op that erases the memo area other than delete.
  It can be erased by means outside OEP, such as rewriting the firmware.
- **Power loss**: whenever the power fails during a write or delete, the other objects remain as they are. The object of that operation becomes one of: the previous complete one,
  the new complete one, none, or one whose crc does not match its data. The probe need not make writes atomic (it MAY make them atomic).
- **Objects whose crc does not match**: the probe does not hide or repair them, and shows them in list and read as they are. The host learns of the damage because the CRC-32 of the data does not match crc,
  and writes it again from its own copy or deletes it.
- Apart from being able to reuse the space of deleted objects, the probe does not show the host its management of space (wear leveling and so on).

## 4. How hosts use it (not normative)

The names and contents of the memo area are free (§1). So that they do not collide when other hosts or tools use the same probe, and so that any host can read them, the following use is recommended.

### 4.1 Names

- **A name is `<owner>/<rest>`**. The owner decides what follows `/`. Example: `io.github.example.bench/port/x035` (the reverse-DNS name has the same form as core §12 rule 1,
  such as `io.github.<owner>.<name>`).
- **The owner is the name of whoever decides the form**: its own reverse-DNS name, or the name of the interface that defines the form of the object (for forms the project decided,
  `oep.probe.memo`, §4.3). An interface name is used as the owner only for objects whose form the document of that interface decided.
  Do not make a new name for the owner.
- **Names have no version**. To change the form or the meaning, use a new name (the same as named extension TLVs, core §2.2). Within the same name,
  only add, so that readers can skip members they do not know.
- **When putting a port or a target in a name, make it lowercase**. Port names and target names are equal regardless of case ([host development guide](../docs/host-development-guide.md) §5.3), but
  the memo area compares bytes as they are (§1). Convert A-Z to a-z so that the same port does not split into two names.
- A name is up to 64 bytes in total (§1). Choose a short owner name (`oep.probe.memo/port/` with a 16 character port name is 36 bytes).

### 4.2 Contents and how to write

- The contents are one UTF-8 JSON (no BOM), as in [settings file](../docs/oep-settings-file.md) §2, with an object at the top level.
  Readers skip members they do not know.
- **Write an object of another owner only following that owner's definition**. Only read an object whose definition you do not know; do not delete it.
- **To rewrite, read and then write within the same session, and keep members you do not know**. write needs the lock (§2), so during that session
  no other host can write. read does not need the lock, so rewriting based on contents read outside the session erases changes by other hosts in between.
- Do not rewrite the same contents. If size and crc in list are the same as your copy, do not write (this reduces rewrites of the medium).
- Keep the correct contents on the host side too. The memo area is a copy that goes with the probe. [Settings file](../docs/oep-settings-file.md) §2.4
  exports the whole memo area together with the settings, and imports it again.
- Do not put values for safety (how pins are handled and so on). The probe does not read the memo area (top of this document). Values that decide the behavior of the probe belong in the settings (core §13).

### 4.3 Port record `oep.probe.memo/port/<port>`

An object for every host to read and write in the same form what is connected beyond a port of the probe ([host development guide](../docs/host-development-guide.md) §5.3).
The name is `oep.probe.memo/port/` followed by the port name (lowercase). The contents are the JSON of §4.2, and every member is optional:

| Member | Value |
|---|---|
| `target` | string. The name of the target last confirmed on that port (`<family>-<hex of the individual value>` of host development guide §5.3, lowercase) |
| `part` | string. The part number of the target as the maker writes it (such as `CH32X035F8U6`). Written when the family and the individual value do not determine it |
| `note` | string. A note for people to read |

- This is a record, not a check. Work on an address with a target level checks the target name on that connection regardless of the record (host development guide §5.3).
  The record is used as a hint to find a port from a target name, and for display.
- When the port name or the wiring changes, correct or delete the record of that port.
- Facts only a tool uses (external parts and their terminals, defects found in tests and so on) go in an object with the name of the owner of that tool.
