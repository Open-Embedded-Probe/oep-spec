# OEP standard interfaces: probe settings v1

[日本語](oep-if-probe-config.ja.md)

Status: **normative** (v1, before the freeze: until the v1 freeze a rule or a number may still change). The core is [OEP core](oep-core.md). The only definition of the numbers is `registry/oep-v1.toml`. The history and
experiments are in [serial ports and persistence](probe-cdc-and-persistence.ja.md) (Japanese).

| Name | revision | Role |
|---|---:|---|
| `oep.probe.config` | 1 | The probe's settings (plan, labels, idle pins, slots, what is sent to the serial ports) and saving them |

- **There are no default values.** Every item is set by the host, and the probe behaves as set. For items that are not set it does nothing.
- A probe that does not handle settings does not put this interface in list.
- The plan, the slot connections and the binds put in from the settings are not session resources (core §9). They are not removed even on lease expiry.
- **There are no boot types (modes).** Settings are made with the same operations over any path, and what is set takes effect immediately. No reboot is needed for settings.

## 1. Items

**Settings = a sequence of items (TLVs)**. The tag is in the space of this context. Each item has a **key**, and items with the same tag are told apart by the key.

- **The channel of an item**: the channel of a label, idle or disable item is less than `channels` (fn 0 describe 0x43) and not in `reserved` (0x44). Otherwise the set is rejected unsupported (the item's tag as received).

| tag | Item | Value | Key |
|---:|---|---|---|
| 0x01 | plan | fn(u16), role(u8), channel(u16) (1 assignment per item) | (fn, role, channel) (the items of the same fn make up the plan of that fn) |
| 0x02 | label | channel(u16), text | channel |
| 0x03 | idle | channel(u16), mode(u8: 0 Hi-Z, 1 input with pull-up, 2 input with pull-down, 3 output low, 4 output high), [drive_kind(u8), drive_value(u16)] | channel |
| 0x04 | slot | §1.1 | slot |
| 0x05 | bind | §1.2 | port |
| 0x06 | uart | fn(u16), baud(u32), format(u8) (the same values as configure of `oep.fixture.uart`) | fn |
| 0x07 | disable | channel(u16) | channel |

- Every item takes effect immediately. The items handled are declared with items of describe, and a set of an undeclared item is rejected unsupported (the payload's tag is the item's tag as received, core §4.3). Tag 0x7E is reserved for the answer's
  meta information.
- **plan**: the same as plan_apply of that fn (core §8). A settings plan is changed only by the settings: a session's plan_release (including n = 0)
  does not release it, and if plan_apply names that fn, rejected unavailable (core §8).
- **label**: the name of a channel given by the settings. Read with get (the label (0x46) of the core's describe is the fixed name the firmware holds, and does not change
  with the settings. The host uses both together. core §7.3: describe is only a declaration). text: 1 to 32 bytes (registry `limits.label_max_bytes`) of valid UTF-8 without C0 control characters (0x00 to 0x1F) or 0x7F. Otherwise rejected malformed.
- **uart**: applies the equivalent of configure at the point the plan of that fn (`oep.fixture.uart`) gets RX or TX (whether by the settings plan or by a session's plan_apply).
  set goes through even without a plan (it is applied when a plan is attached). A session's configure wins over this item until the plan is released or
  the probe reboots. baud is checked at set for the realisable value, and if it deviates by more than ±5% (registry `uart_baud_tolerance_pct`), rejected unsupported.
  format has the same values as the TLV format of configure (an unused value or a reserved bit is rejected unsupported, core §2.5). configure on an fn without pins is, as now,
  rejected unavailable (unchanged even with the item). The line coding of a CDC port is not mirrored onto the fixture UART (only OEP's configure and this item
  take effect).
- **disable**: makes the probe **not use that channel at all** (pins not brought out on the board, pins connected to other parts). The user
  states this explicitly to match their own board. It only reduces the channels the firmware declared usable (role_channels of describe, etc.), and cannot make usable a pin the firmware
  declared unusable (that is done with one's own build).
  - A request that points to a disabled channel (plan_apply, a settings plan, pins and reset of a wire's attach, a combination of scan, gpio, etc.) is rejected unavailable
    (cause 5 held by the settings, with channel and holder_kind 6 disable). It is not included in the sequence of a scan with count = 0, nor in the candidates of an attach without pins
    (if that is the only candidate, likewise cause 5). When a disable and a plan / slot using that channel are both sent in the same set, also cause 5.
  - A disable of a channel the firmware does not declare is rejected unsupported (the channel of an item, above).
  - The probe neither drives nor configures the pin of that channel (it does not put it in the idle state at boot and at release either. It stays as after reset).
  - A set that disables a channel currently in use (plan, connection, slot. Excluding those removed in the same set) is rejected unavailable
    (cause 1). Settings that have both idle and disable for the same channel are malformed.
  - A channel whose disable is removed by unset goes to the idle state (idle or Hi-Z) immediately.
  - describe is only a declaration and does not change (core §7.3). The host combines it with the disable of get to know the usable channels.
  - If saved, it is applied at boot before the idle state is applied.
- **idle**: the state of a pin used neither by a plan nor by a connection. It is put in this state at boot and each time the pin is released (core §8).
  A channel with an idle item (any mode) is left out of a scan with count = 0 and of the candidates of an attach without pins; a request that names it is rejected unavailable (cause 5, holder_kind 7) when the idle is an output (mode 3 / 4) ([wire and debug](oep-if-debug.md) §1).
  With mode 3 / 4, the probe drives that level for as long as the pin is idle. A pin without idle is Hi-Z. A pin where the peer's input would float because of the fixture's wiring (a TX connected to the peer's RX, etc.) is stated explicitly by the host with idle and saved.
  The output modes exist for a channel that must keep a level even while no plan holds it (the switch of the target's power, etc.).
  A change of the idle item (set / unset) takes effect at once on a free channel, and on a channel a plan or a connection holds, when it next becomes free.
  On a probe that cannot drive that channel as an output, an idle with mode 3 / 4 is rejected unsupported. On a channel that does not have that pull, an idle with mode 1 or 2 is rejected unsupported (the item's tag as received). (Informative) A probe without `oep.fixture.gpio` gives the host no way to learn in advance which channels have pulls or outputs. A mode of 5 or more is rejected unsupported (the item's tag as received, core §2.5).
  (Informative) Keeping an output idle from meeting an output of the target is the responsibility of the wiring.
  - **Strength (optional)**: drive_kind(u8), drive_value(u16) may be placed after mode (the same kind and value as the strength specification of [fixture](oep-if-fixture.md) §1.1).
    If not placed, the default level. Only mode 3 / 4 can carry them, and placing them with mode 0 to 2 is rejected malformed (with a mode of 5 or more the mode is rejected unsupported, core §4.3). A value length of 4 or 5
    bytes is rejected malformed. An undefined drive_kind (2 or more) is rejected unsupported (the item's tag as received. A later revision may define it, core §2.5). On a probe whose describe of `oep.fixture.gpio` declares drive_levels,
    kind 0 with drive_value equal to the number of levels or more is rejected unsupported. A probe that does not declare drive_levels (including a probe without `oep.fixture.gpio`)
    keeps this field but does not apply it (the strength stays the default).
    After drive_value (from the 7th byte of the value) is the place for fields added later (core §2.3. The probe skips it and, as in §2, keeps it without truncation).
    (Informative) Unlike gpio set, whose drive TLV ignores a level out of range, this item refuses it so that a mistake in a setting that is
    stored and used at every boot is reported when it is written.
  - An idle with mode 3 / 4 applies its level and its strength together (both at boot and at release).

### 1.1 slot

A slot is a registration of the **place** where a target is connected (not a registration of a chip. When the chip is replaced, the registration is not changed).

```text
slot(u8), wire_fn(u16), swdio(u16), swclk(u16), attach(u8), retry_ms(u32), max_speed_hz(u32), idle_clock(u8), mechanism(u8),
name_len(u8), name,
lock_len(u8), lock_scheme(u8), lock_mask(n byte), lock_value(n byte),
[boot_reset(u8)]
```

lock_len is the length of the lock part (from lock_scheme to lock_value). 0 is no lock (nothing from lock_scheme onwards is placed). After the lock, an optional
boot_reset may be placed (0 if not placed). After it is the place for fields added later (core §2.3. The reader skips the unknown tail).

| Field | Meaning |
|---|---|
| slot | The slot number (key). From 0, less than slots_max of describe |
| wire_fn | The fn of the wire interface. Only **wires that have a target_id scheme** (`oep.wire.rvswd` / `oep.wire.swio`). Others (`oep.wire.swd`) are rejected unsupported |
| swdio, swclk | The pin combination. The same as pins of attach (for a single-line wire swclk = 0xFFFF). If it is not a combination the wire allows, rejected unsupported |
| attach | The attach policy: 0 host, 1 at boot (§3.1). 2 or more is rejected unsupported (core §2.5) |
| retry_ms | For an at boot slot, the interval (ms) at which the attach is retried when the target is not there. 0 does not retry. 0 if not at boot (otherwise rejected malformed) |
| max_speed_hz | The upper limit of the wire speed passed to the attach of that slot (Hz, the same as max_speed of attach). 0 is no limit. A limit the wire cannot keep (its fixed speed is faster than it, slower than min_clock_hz) is rejected unsupported |
| idle_clock | How the wire is rested, passed to the attach of that slot (the same as idle_clock of attach: 0 = high, 1 = low). Only `oep.wire.rvswd` can have 1 (1 on other wires is rejected unsupported. The same as attach). 2 or more is rejected unsupported (core §2.5) |
| mechanism | The console mechanism (mechanism of `oep.target.console`), or **0xFF = no console** (not put on a bind; a probe without console). A mechanism that the probe's console does not declare is rejected unsupported |
| name | The slot's name. 1 to 32 bytes; the only usable characters are `a-z 0-9 - _` (others are rejected malformed). Unique within the probe (if duplicated, rejected malformed). Used by the host to name the slot (it goes as is into the IDE address `oep://<unit_id>/<name>`. unit_id is core §7.5. Both contain only characters that need no encoding in a URL), and also used for the line marker of mixed (§1.2) |
| lock_len | The length of the lock part. 0 (no lock) or 1 + 2n (n ≥ 1). Others are rejected malformed |
| lock_scheme | Only when there is a lock. The scheme of target_id ([wire and debug](oep-if-debug.md) §1). 0 is not placed (no lock is lock_len 0). A scheme the wire does not have, whether defined or not (core §2.5), is rejected unsupported |
| lock_mask, lock_value | Only when there is a lock. The same length n = (lock_len − 1) / 2. **n is the same as the length of the value of that scheme** (4 for scheme 1. If different, rejected malformed. The length is `[common.enum.target_id_len]` of the registry). The byte order is the same as the value of target_id in the answer to attach (for scheme 1, u32 little endian) |
| boot_reset | Optional. Whether, when the automatic attach at boot got no answer from the wire, the probe attaches once more using the reset line (§3.1). A boolean: 0 no, 1 yes. 0 if not placed. 2 or more is rejected malformed (a value excluded for every revision, core §4.3, not an unused value). 1 on a slot that is not at boot is rejected malformed |

- max_speed and idle_clock are properties of the target ([wire and debug](oep-if-debug.md) §3), used when the probe attaches the slot itself
  (at boot, retry). A host's attach passes its own values in the respective TLVs (the slot's values are not used).
- Two slots with the same wire_fn and the same pin combination cannot be created (a contradiction within the settings: rejected malformed).
- **When a slot item is replaced or deleted**: the slot's share is removed from the connection the slot was using (if nothing else uses it, it is closed.
  The target is not reset, [wire and debug](oep-if-debug.md) §2), and the slot's share of the console opened by bind is removed (mark closed 3).
  If the replacing item is at boot, the attach is redone with the new combination.
- **The slot's connection**: among the live connections, the one whose wire_fn is the same and whose pin combination matches the slot (regardless of who attached it).
- **Lock**: the lock matches only when the target_id of the slot's connection (TLV 0x10 of the answer to attach) has the same scheme as lock_scheme and the bitwise
  AND of the value and lock_mask equals lock_value. A slot without a lock always matches. How to compare (which bits to ignore) is decided by the host with the
  mask (example: if bits [7:4] of the low byte of the identifier are the revision and are to be ignored, mask 0xFFFFFF0F).
- **The number of at boot slots is, per wire_fn, up to max_connections of that wire** ([wire and debug](oep-if-debug.md) §1). A set exceeding it
  is rejected unavailable. The order of the sequence of slots has no meaning.
- The number that can be registered is declared by the probe with slots_max of describe.
- A slot designates a two-pin wire. A wire whose combination is not two pins gets a new item tag when slots are defined for it.

### 1.2 bind (what is sent to a serial port)

```text
port(u8), mode(u8), selected(u8), n(u8), n × (len(u8), kind(u8), id(u16))
```

| Field | Meaning |
|---|---|
| port | The number of the serial port (the index of the transport of the core's describe). If it is not a serial port, rejected unsupported. The index does not change across firmware versions (core §7.5) |
| mode | 0 last-reset, 1 manual, 2 mixed (below). A mode not in bind_modes of describe is rejected unsupported |
| selected | The selection for manual (the number in the sequence, less than n. If out of range, rejected malformed). For last-reset and mixed 0 is sent, and the probe does not look at it |
| n, sequence | The streams to send (n ≥ 1). Each element is preceded by its length len (the same form as sequences in answers, core §2.3). len is 3 or more (less than 3 is rejected malformed), and the probe skips what follows the first 3 bytes. The host sends 3 for now. kind 1 = the console of a slot (id = slot), kind 2 = reception of a fixture UART (id = the fn of `oep.fixture.uart`). Any other kind is rejected unsupported (core §2.5). Pointing to a nonexistent slot is rejected malformed (a contradiction within the settings), a nonexistent fn is unknown_function, an fn that is not `oep.fixture.uart` is rejected unsupported. A slot with mechanism 0xFF cannot be put on it (rejected malformed) |

| mode | What is sent to the port | Raw bytes coming from the port |
|---|---|---|
| **last-reset** | The selected stream. The selection switches to a slot when the host resets the target of that slot in the sequence (below). At boot and right after set, the head of the sequence | To the selected stream |
| **manual** | The stream of selected. Only a set of the bind changes it | To the selected stream |
| **mixed** | All of the sequence. Lines are accumulated per stream, and when a line is closed it is sent with `[name] ` prepended | Discarded (receive only) |

- **What counts as a host's reset**: reset of `oep.target.riscv-dm` on the slot's connection, and the reset TLV of attach of `oep.wire.*`
  ([wire and debug](oep-if-debug.md)). The probe's own attach, a self-reset of the target, ndmreset written with dmi, and a reset line moved with `oep.fixture.gpio`
  etc. do not count. Even if the connection of the selected target is lost, the selection does not switch.
- If the sequence has one element, that is sent in every mode (the behaviour does not change between one and two or more).
- **Lines of mixed**: closed by LF. Output that is not closed is closed when 128 bytes have accumulated or after 100 ms of quiet since the last byte. name is the slot's
  name. For a fixture UART, the label if the channel of RX in the plan of that fn has a label (§1), otherwise `name#instance` (core §7.2,
  e.g. `oep.fixture.uart#1`).
  When a label is used as the marker, the probe replaces `]` and bytes below 0x20 (CR, LF, etc.) with `_`.
  The order of lines between targets is the order in which the lines were closed (not suited to machine reading).
- **Raw bytes coming from the port** (the bytes outside frames of core §3.4) are passed to the peer of the selected stream (for a console, the write of console;
  for a fixture UART, TX), as much as the peer can accept. What cannot be accepted may be discarded.
- **Position of the port**: the probe keeps, per bind, a position in the stream being sent. It advances as much as the port can accept, and even if the port is not read,
  the stream is not discarded. If the stream gets ahead of the port by a whole buffer (overflow), the port jumps to the oldest byte still remaining.
- **During a session** (a port whose raw forwarding is stopped by core §3.4): the position does not advance. When the session ends, for each stream sent, it resumes
  from **the position at the point the host last reset in that session** (one of the "what counts as a host's reset" above. For a console
  stream, the position of the mark of that reset ([common parts](oep-if-common.md) §1.3); for a fixture UART, the reception position at that point).
  If there was no reset in that session, from now. The same regardless of mode.
- The stream of a slot is opened and sent by the probe as a console on that connection while the slot is in the sequence of some bind, the slot's connection exists and the lock matches. The probe does not open the console of
  a slot that is in no bind. If there is a stream with the same connection and mechanism, it is
  used ([console](oep-if-console.md) §2). A bind rides on any connection (including a connection the host attached). This opened console counts as the slot being a user of that connection ([common parts](oep-if-common.md) §2).
- The stream of a fixture UART is sent, even without a connection, while the plan of that fn has RX (the stream is created by the plan and disappears when the plan is released.
  The position does not go back within a boot, [common parts](oep-if-common.md) §1.1. The port's position does not advance once the stream disappears). baud / format come from the uart
  item (§1) or the session's configure.
- DTR / RTS / the 1200 baud touch and the CDC line coding do nothing (neither the target nor the probe is reset, nothing is attached, and the baud is not changed).

### 1.3 Line names (the label convention)

Among the texts of labels (the settings' label items, §1, and the firmware's labels, the label (0x46) of the core's describe), the following names state the role of a line.

| Name | Line | Used by |
|---|---|---|
| `nrst` | The target's reset line | The probe (the retry with reset of §3.1) and the host |
| `power_hi` | A line that powers the target when high | The host only (the probe does not use it) |
| `power_lo` | A line that powers the target when low | The host only (the probe does not use it) |

- **Finding a slot's line** (name N, slot name S). Search in this order, and stop at the first step that finds exactly one channel:
  - (a) a settings label equal to `S.N`;
  - (b) only when the settings hold at most one slot item, a settings label equal to `N`;
  - (c) only when the settings hold at most one slot item, a firmware label (describe of fn 0, 0x46) equal to `N`.
- A step that finds two or more channels ends the search with no line. If no step finds one, that slot has no such line. Texts and names are compared ignoring ASCII case.
- In settings without slot items, steps (b) and (c) find that line of the target connected to the probe.
- A label text that is not in the table states no role (it is only a name). Standard names are listed in the registry (`[line_names]` of `oep.probe.config`). Adding one does not change the revision (core §2.7). A name for a role that is not standard starts with `x-` (example `x-acme-boot0`). Standard names never start with `x-`, and no name contains `.` (`S.N` uses it).
- The probe does not use `power_hi` and `power_lo` (it does not drive the power line). The host finds the power line with the same search.

## 2. Operations

| op | Name | Request | Answer | Lock |
|---|---|---|---|---|
| 0x01 | get | first(u16) | more(u8), hash(u32), the items (the current settings) to the end of the payload | Not required |
| 0x02 | set | sequence of items | hash(u32), [TLV] | Required |
| 0x03 | save | — | hash(u32), [TLV] | Required |
| 0x04 | erase | — | — | Required |
| 0x05 | unset | n(u8), n × (len(u8), tag(u8), key) | hash(u32), [TLV] | Required |
| 0x06 | state | first_slot(u8), first_bind(u8) | §3.3 (the current state), no lock needed | Not required |

- **get**: the answer's items run to the end of the payload. Tag 0x7E is reserved for answer meta information, and a v1 probe does not place it. get takes no TLV (one is rejected malformed, core §7.3).
- **set replaces per key of the items contained in the request** (keys not contained stay as they are. Settings can be built up over several sets).
  The plan items are grouped per fn and replace the plan of that fn. The order of the items has no meaning.
- **unset deletes the item of the key** (key depends on the tag: plan is fn(u16) (the whole plan of that fn), label and idle are channel(u16), slot is slot(u8),
  bind is port(u8), uart is fn(u16), disable is channel(u16). len is placed on each element because the length of the key differs per tag). Validation and atomicity are the same as set. A nonexistent key
  does nothing and succeeds. The tag of an undeclared item is rejected unsupported (the payload's tag is the tag as received, core §4.3). The clean-up of §1.1 / §1.2 is applied to deleted slots and binds.
- If the same key (for plan, (fn, role, channel)) appears twice in one set, the whole request is rejected malformed.
- If the whole of the settings resulting from set / unset does not satisfy the rules of §1 (a bind points to a deleted slot, etc.), rejected malformed without changing anything.
- **The atomicity of set extends to the validation of the settings and the reservation of resources (applying the plan, checking pin contention)**. If any of them is not accepted, rejected
  without changing anything. The automatic attach and opening consoles (changing outside state) are done after set has completed, and their results are seen in slot_state and bind_state of state (op 0x06,
  §3.3) (not rolled back).
- **The probe keeps the byte sequence of the items the host sent as is** (removing only the critical bit. Unknown trailing fields are also kept without truncation).
  The probe does not add fields to the tail itself.
- **hash** is the CRC-32 (the same IEEE one as core §5.2) of the canonical form of the current settings. Canonical form = the byte sequence of the items sorted in ascending order of tag, and within the same tag in ascending order of key (for plan
  (fn, role, channel)), joined as TLVs (the unique encoding of core §2.2). The host computes the same value from the settings it wants, and
  if it is the same as the hash of get, does nothing. In the canonical form a tag has its critical bit cleared. Keys are compared as numbers, and multi-field keys field by field from the first. get returns from the first-th item in the order of this canonical form, and every page returns the same hash (if it has changed,
  the host reads again from the beginning).
- **save is only an explicit operation of the host**, and saves the current settings as they are (if the content is the same, nothing is written). While writing, it does not answer other requests
  (subject to the core's max_op_ms). **A save replaces the whole**, and even if power is lost partway, either the previous save or the new save can be read. `max_bytes` of
  describe is the number of bytes of the canonical form, and settings up to that length can always be saved (the probe subtracts the part for the table of identifiers when declaring it). If exceeded,
  rejected unavailable (cause 3). erase deletes the save (it does not change the current settings. After deletion, state 0, hash 0). save and erase are
  optional, offered when the storage of describe declares max_bytes above 0; a probe without saving answers them with unknown_operation (core §1.2). get, set, unset and state are required.
- **A save holds the interfaces the items point to by (name, instance, revision)** (because fn numbers can change at every boot). The fns pointed to are fn of plan,
  wire_fn of slot, id of kind 2 of bind, and fn of uart. At boot, the probe looks up that combination in the current list, rewrites the fn, and then applies it (the forms of set and get stay
  with fn). If an interface pointed to does not exist, or the revision differs, **the whole save is not applied** (putting in only part would make the fixture behave half-way. The storage
  state is "present, unreadable", reason 2). Adding, removing or reordering interfaces that are not pointed to does not affect the save.
- The form of the save (how it is kept inside the probe) is decided by the probe. Only the rewriting rule is normative.
- At boot, a saved bind whose port is not a serial port of this firmware makes the save unreadable (reason 2). If applying any saved item is refused, the whole save is not applied (reason 3).
- At boot, the probe makes the save the current settings (when it passes the checks above), applies idle (including driving the outputs of mode 3 / 4, together with their strength), applies the plan, applies uart, starts the attach of the at boot slots,
  and connects the binds. When the save cannot be read it is not applied, and this is reported in state.

**Table of refusals** (in the order of core §4.3):

- Every rejected unsupported that is about an item, whatever the item (plan, label, idle, slot, bind, uart, disable) and whichever row below gives it, carries in its payload that item's tag as received (core §4.3).
- A field that holds an undefined value is refused unsupported, and the contradictions that involve it (the malformed row) are not checked (core §4.3).

| Situation | reason |
|---|---|
| Form errors, the same key twice, characters of name, the length and characters of a label's text, range of selected, retry_ms not 0 on a host slot, length of lock, boot_reset 2 or more (a boolean) and boot_reset 1 on a host slot, a drive of an idle with mode 0 to 2, and the length of an idle's drive, putting a slot with mechanism 0xFF on a bind, a bind pointing to a nonexistent slot, two slots with the same wire_fn and the same pins, duplicate name | malformed |
| The fn pointed to does not exist (plan, wire_fn of slot, kind 2 of bind, uart) | unknown_function |
| An undeclared item, a pin combination the wire does not allow, a wire_fn whose wire cannot have a lock, a mechanism the console does not declare, an idle with mode 3 / 4 on a channel that cannot be driven as an output, an idle's level number equal to the number of levels or more, idle_clock 1 on other than rvswd, a max_speed_hz that cannot be kept, an idle with mode 1 / 2 on a channel without that pull, the channel of a label / idle / disable at or beyond channels or in reserved, a mode not in bind_modes, a port that is not a serial port, an fn that is not uart, an unrealisable baud / format, an unused value or reserved bit of format, an idle mode of 5 or more, an undefined drive_kind of an idle, a slot attach of 2 or more, a slot idle_clock of 2 or more, a bind stream kind other than 1 / 2, a lock_scheme the wire does not have (defined or not) | unsupported |
| plan_roles exceeded, contention for pins or resources, at boot slots exceeding max_connections, not enough room to save | unavailable (cause 2 / 1 / 2 / 3) |

## 3. Slot connections and state

### 3.1 attach policy

| attach | When the connection is created |
|---:|---|
| 0 host | The probe does not attach on its own. When a host's attach creates the slot's connection, the bind rides on it |
| 1 at boot | At boot, and right after the item of that slot is set. If the target is not there, retried every retry_ms (no retry if 0) |

- The automatic attach at boot starts after all idle states (including driving the outputs of mode 3 / 4, together with their strength) have been applied (the boot order of §2).
- **The automatic attach (at boot) is only a non-halting attach (method 0)**, done with the slot's pin combination according to the rules of [wire and debug](oep-if-debug.md)
  §1. If the lock does not match, the probe removes its own share without opening the console (the state is lock mismatch).
- The automatic attach is for paying up front for cases where connecting takes time. If it missed, the host attaches by itself when it uses the target.
- When the seats are full and a host's attach closed the slot's connection ([wire and debug](oep-if-debug.md) §1), that slot is left as
  it is (no retry even for at boot). The next connection is made at the next boot, at a set of that slot, or by a host's attach.
- A slot whose connection was lost (the wire went down) retries every retry_ms if it is at boot.
- **Liveness check**: the probe may check the connection of an at boot slot by reading DMSTATUS every retry_ms (no writes). If it sees wire loss, it
  closes the connection and goes into retry (even for a slot with mechanism 0xFF, or without console reads, "not there" is detected). If retry_ms is 0,
  it does not check.
- The probe does not check slots whose policy is host (it does not drive the wire).
- **Retry with reset** (a slot with boot_reset 1): when an automatic attach of that slot ended without any answer from the wire
  (completed failed, status line, [common parts](oep-if-common.md) §3), the probe immediately does the same attach (method 0) once,
  with the reset line. It behaves like attach's reset TLV ([wire and debug](oep-if-debug.md) §3), and hold_ms is the registry's
  `slot_retry_reset_hold_ms` (20 ms).
  - It is done only after boot while no session has taken the lock yet. Once the lock has been taken, it is not done within that boot
    (even after the lock is released).
  - It is done only after a failure with status line. It is not done when the attach succeeded (including lock mismatch and target_id not readable), after a failure with a status other than line
    (including read protection), or after a rejected.
  - Per slot, at most once in one boot. If the retry fails, the ordinary retries every retry_ms (without reset) continue.
  - The reset line is the channel of `nrst` found by the search of §1.3. When none is found, or when that channel cannot be used for the reset TLV of the attach of
    that slot's wire (not in role 3 of role_channels, disabled, held by a plan or a connection, the wire does not have the reset TLV), the probe does not
    retry with reset.
  - When it is done, the probe puts the time it started pulling the reset line into reset_at_ns of the state's slot_state (§3.3). The bind selection does not change (the probe's
    own attach, §1.2).

### 3.2 State

slot_state of state (op 0x06, §3.3) can be read without the lock. This is the only way for the host to know whether a target is present without driving the wire (without driving the wire,
whether it is connected cannot be known).

| state | Meaning |
|---:|---|
| 0 | Connected (the lock matches) |
| 1 | Not there (no connection. last_try_at_ns is the time of the last automatic attach attempt) |
| 2 | Lock mismatch (there is a connection, or it was found by the automatic attach and removed. target_id is what was seen) |
| 3 | target_id cannot be read (a slot with a lock, and the connection has no target_id) |

### 3.3 state (the current state, no lock needed)

```text
request: first_slot(u8), first_bind(u8)
answer:  more(u8), storage_state(u8), storage_hash(u32), unreadable_reason(u8),
         n_slots(u8), n_slots × (len(u8), slot_state), n_binds(u8), n_binds × (len(u8), bind_state), [TLV]
slot_state: slot(u8), state(u8, §3.2), connection(u16, 0 if none), last_try_at_ns(u64: the time of the last automatic attach attempt (the probe's clock; the retry with reset of §3.1 counts as an attempt), all bits 1 is not tried), tid_scheme(u8, 0 is none), tid_len(u8), tid,
      reset_at_ns(u64: the time the probe started pulling the reset line in the retry with reset of §3.1 (the probe's clock), all bits 1 is not done)
bind_state: port(u8), mode(u8), selected(u8: the number in the sequence currently selected. 0xFF for mixed), flow(u8: 0 nothing to send / 1 sending / 2 stopped by a session)
```

- storage_state: 0 no save, 1 present and applied, 2 present and unreadable. storage_hash is the hash of the canonical form after the save is rewritten to the current fns
  (0 if unreadable). unreadable_reason: 0 none, 1 the form cannot be read (corrupted, the form of a different version), 2 an interface pointed to does not exist / the revision differs / a bind's port is not a serial port,
  3 applying was refused (resources conflict).
- Returns the registered slots in ascending order of slot from the first_slot-th, and the binds in ascending order of port from the first_bind-th, as many as fit in 1 frame.
  If more = 1 there is a continuation, and the host adds n_slots to first_slot and n_binds to first_bind and asks again.
- Each page carries storage_state, storage_hash and unreadable_reason as they are when that page is answered; they may differ between pages, and the host uses those of the last page. The slots and binds may also change between pages (a set or save by the lock holder, an automatic attach); a host that needs the set of slots and binds to stay the same across its pages pages while it holds the lock (the slots' states may still change).

## 4. describe

describe is only a declaration (core §7.3). The state is in state (§3.3).

| tag | Name | Value |
|---:|---|---|
| 0x40 | storage | max_bytes(u32, the number of bytes of the canonical form. 0 = no saving; save and erase are then not offered, §2) |
| 0x41 | items | A sequence of the tags of the items handled (u8) |
| 0x42 | slots_max | u8. The number of slots that can be registered (0 does not handle slots) |
| 0x43 | bind_modes | Bits of a u32: bit0 last-reset, bit1 manual, bit2 mixed. A probe that handles bind always sets bit0 and bit1 |
| 0x44, 0x45 | — | Reserved (formerly slot_state / bind_state. Moved to the state op) |

## 5. Safety (informative)

This section adds no rule. It gathers what the rules above mean for the lines a probe drives.

- **Saved settings drive lines without a host.** At every boot the probe applies the saved idle (mode 3 / 4 drives its output), the plan, and the at boot attach with its
  boot_reset (§2, §3.1), whether or not a host is there.
- **Before the settings are applied, the pins are in the MCU's reset state.** From power-on or reset until the firmware applies idle, while the firmware is being updated,
  and when the firmware is broken, the probe drives nothing the settings define. A line whose wrong level is harmful (for example one that switches the target's power) needs an
  external pull-up or pull-down that holds it at its safe level on its own.
- **disable is the user's declaration, not a protection.** A host that holds the lock can unset it (§2) and then use the channel.
- **Settings have no authentication.** Any host that takes the lock can change and save them, including by force (core §6.4); on TCP the core's rule for trusted connections
  applies (core §3.1).
