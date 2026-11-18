# OEP interface: wires and debug v1

[日本語](oep-if-debug.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **normative** (v1). For the freeze state and the language and compatibility policy, see [Versions and stability](../docs/versioning.md). The core is [OEP core](../docs/oep-core.md), and the common parts are in [Common parts](oep-if-common.md) (§2 debug
connection, §3 status). The only definition of the numbers is `registry/oep-v1.toml`.

| Name | revision | Role | Target family |
|---|---:|---|---|
| `oep.wire.rvswd` | 1 | connects to a RISC-V DM over 2-wire RVSWD | RISC-V targets whose DM is reached over 2-wire RVSWD |
| `oep.wire.swio` | 1 | connects to a RISC-V DM over 1-wire SWIO | RISC-V targets whose DM is reached over 1-wire SWIO |
| `oep.wire.swd` | 1 | connects to ADI over ARM SWD | ARM targets with an SWD DP |
| `oep.target.riscv-dm` | 1 | operations of the RISC-V Debug Module | RISC-V targets with a RISC-V Debug Module |
| `oep.target.arm-adi` | 1 | operations of ARM ADI (DP / AP) | ARM targets with ADI |

- `oep.wire.*` creates connections, and `oep.target.*` operates the target over a connection. Interfaces that handle targets are put in list
  even before attach, and a request without a connection is rejected no_resource.
- All ops other than connections need the lock.
- A minimal wire MAY have only attach/detach/connections and one connection; scan, multiple connections and console are not required.
  Flash procedures, memory layouts and the interpretation of chip identifiers of targets are treated as host knowledge. High-level operations a probe implements are limited to the declared target operations.
  A connection holds the pin/target selection of the wire, and each target request selects that connection by the connection number at its start. The fn numbers of the wire and the target need not match.

## 0. Rules shared by the wires of this document, and what another wire defines

`oep.wire.rvswd`, `oep.wire.swio` and `oep.wire.swd` of this document:

1. use op 0x10 scan, 0x11 attach, 0x12 detach, 0x13 connections and 0x14 holds with the meanings of §1 to §2.2 (a wire MAY add ops from 0x15). attach, detach, connections and holds are required. scan is optional and declared in ops;
2. follow §1 and §2. swdio / swclk are read as "the channels of pin roles 1 / 2";
3. create the connections of [Common parts](oep-if-common.md) §2 that `oep.target.*` interfaces use.

When defining another wire, state the following explicitly. The fixed forms of the 2-pin attach and of the connections elements of this document are not required uniformly.
A wire with a different number of roles or a different selection of what it connects to MAY define another name and fixed form following core §12.

- the pin roles, and how the speed is chosen;
- the wake / setup procedure and whether it can reset the target (§2), the scratch registers (§1);
- the exchanges, and how the wire rests between exchanges (§2);
- the criterion of "found", and the values of scan_kind;
- when adopting the common target_id, the scheme (from the space of §1), and how wire loss appears;
- the `oep.target.*` interfaces that accept that connection, and whether the console can be used.

## 1. Norms of attach (the 3 wires of this document)

- **Writes before the speed is verified.** Until the speed of the wire is verified, the probe writes only the following to the target:
  1. the wake / setup procedure the section of that wire defines (for example a wake pattern, line reset, target selection, or setup registers needed before
     the debug module answers). Sent at the slowest speed of the wire;
  2. dmactive, on a wire whose connection reaches a RISC-V DM. Only when DMCONTROL does not already read dmactive = 1 (this write lowers haltreq).
- **How the speed is verified.** A variable-speed wire chooses the speed by reading only. A wire that defines scratch also verifies the write path at the chosen speed. What MAY be written and read back is only the debug module registers that the section of that wire
  names as free scratch (registers that nothing in the target uses while no debug command runs), and the writes that the section of that wire
  names as freeing them. Each scratch register is read before verifying, and its value is written back after verifying. A speed at which what was written does not
  read back is not used. If it cannot be restored, attach ends with completed failed and no connection is created.
  How a wire without scratch and a fixed-speed wire verify is defined in their sections.
- Before the speed is verified, nothing else is written to the target (a write at a mismatched speed can write a garbled value to a target register).
- **Pin combination**: channel_group / role_channels of describe declare the candidates.
  The fixed part of attach is `method(u8), swdio(u16), swclk(u16), max_speed(u32)`. A short fixed part is rejected malformed.
  The probe does not search unspecified wiring or choose an existing connection.
- **scan is an optional finite search**: the host states count ≥ 1 candidate combinations explicitly. count 0 is rejected malformed.
  When only role_channels is declared, the host makes the candidates of role 1 × role 2 and does not use the same channel twice.
  tried in the answer is the number tried from the start of the request. While candidates remain, it is 1 or more. The host puts the untried candidates in the next request.
  A request with the same candidate twice is malformed. There is no skip, and no implicit list of candidates inside the probe.
- A combination the declaration does not allow is unsupported. A combination including a pin in use is unavailable (cause 1); a pin that is disable or has an output idle is cause 5.
  The diagnostic TLV 0x40 index (u8) of unavailable/unsupported of scan optionally shows the 0-based number of the candidate in the request. This is a tag specific to each wire.
  scan validates all candidates before side effects. Pins of a running connection are not used for the search.
  Tried pins are returned to the idle state after each candidate. The search itself creates no connection.
- **Time**: the answers to attach and scan are returned within max_op_ms (core §7.5). The probe decides when to give up the speed search and retries. If attach
  can use no speed, the answer is completed failed with status line. The host's wait follows core §4.4.
- **Number of connections held at once**: a wire interface declares it with max_connections (tag 0x40, u8) of describe. 1 if not declared.
  The lock stays one per probe (there is no lock per connection).
- **attach creates a new connection.** It does not join an existing connection implicitly. If it includes pins of an existing connection, unavailable (cause 1).
  The host uses the number it already has, or detaches explicitly and creates it again.
- An attach beyond the limit on the number of connections is unavailable (cause 2). The probe does not close another connection to make room.
- A failed attach creates no connection and does not change existing probe resources. Newly tried pins are returned to the idle state.
  The effects of writes or resets that reached the target cannot always be undone.
- `speed_hz` is the wire speed the probe chose (a guide value of the reciprocal of one bit period).
- max_speed (u32 Hz): the probe does not choose a speed above it. 0 is malformed. If it is smaller than min_clock_hz of the probe, unsupported
  (fixed-part mark 0 for attach, the tag of max_speed for scan). In scan it is given by the optional TLV 0x01.
- **What scan writes**: only 1 and 2 of "writes before the speed is verified", to read the identifier for "found". scan does not verify the write path
  and does not write scratch registers. A scan without max_speed tries at the slowest speed of the wire. A scan with max_speed MAY choose the speed, as attach does, by reading
  at or below max_speed. dmactive is left set. "Found" is DMSTATUS.version being 2 or more and not 15 (0 = no DM, 1 = a version this interface does not
  handle, 15 = a non-conforming DM). For swd, DPIDR could be read. The pins of a combination that did not match are returned to the idle state
  of core §8.
- **Target identifier**: after the answer to attach, the probe MAY add the target identifier it could read as TLV 0x01 target_id (scheme(u8), value).
  scheme is how the identifier is obtained. The numbers of target_id schemes are one space for the whole probe (registry `[common.enum.target_id_scheme]`:
  1 the u32 at DMI 0x7F of that debug module, 2 DPIDR of swd). Each wire states which scheme it uses. The probe does not add it when it could not read it (including when the scheme was the value defined as "none").
  The host knows the meaning of the value (which bits are the family and which the revision). The probe does not interpret it.
  Additions to this scheme space are assigned by OEP in the registry. Third-party interfaces MAY return their own identification in their own fixed forms/TLVs,
  and functions that do not adopt the common target_id are not required to use this scheme space (core §12).

## 2. Lifetime of a connection (the 3 wires of this document)

In addition to [Common parts](oep-if-common.md) §2:

- **Waiting for the DM after a reset**: after releasing the reset line of attach, and after the reset of the reset op (§4.3), the probe reads DMSTATUS again and again until it gets a response from the wire.
  In attach it reads at the slowest speed of the wire. Only during the wait MAY it send the wake/setup procedure of the wire (§1) again.
  It finishes within max_op_ms of the whole request, including the wait and the cleanup. The host's wait is core §4.4.
- **detach releases the connection and the streams on it.** It has no force TLV.
- **A target reset does not close the connection**. The probe keeps the same connection usable after the reset (the procedure per wire is in
  the sections of the interfaces that handle targets, such as §4.6).
- **Retries within one request**: the probe MAY retry the wire within one request (the probe decides how long, including retries at a slower speed).
  When it gives up, it ends that request with status line. That alone does not decide wire loss. The slower speed during retries is temporary and does not change speed_hz of the connection.
- **Do not repeat writes**: stores to target memory (including writes that cause a store) and the steps of the host's dmi requests are not repeated by the probe's wire retries
  once they may have reached the target (what the target answered it did not accept, DMI busy and SWD WAIT MAY be repeated). Writes by which the probe itself puts values in the debug module and
  registers (those where writing the same value again causes nothing: program buffer, abstractauto, GPR, dcsr, DATA0 / DATA1 being restored) MAY be repeated;
  other writes (such as resumereq, which runs the hart) are not repeated, like stores. A request that failed on a write that is not repeated is answered with completed failed / partial,
  and done is the number of steps or words finished before it. The probe's own reads may be repeated.
- **Do not change the state of the target**: while a connection exists, the wire retries and resynchronization the probe does on its own judgment do not change the state of the target. On a wire whose wake / setup procedure
  can reset the target, it is sent on the connection only in attach and in reset (the reset TLV of attach, the reset op of riscv-dm).
- **Wire loss**: when operations of a connection keep failing without response from the wire (status line; either within a request or within console reading) and no operation on that connection
  succeeded in between, the probe MAY decide that the wire of that connection is lost (the probe decides when. While the reset line is held and right after it is released,
  the target may not answer). When the probe decides wire loss within a request, it answers that request with status line and then closes the connection.
- **Wire loss is judged only within a request or within console reading**. status line alone does not mean the connection closed: the host checks with connections.
  When judged within console reading, the connection and the stream are closed. On closing, no mark is made that cannot be read later.
- **The wire while it does not respond** (electrical safety): an exchange is one frame or packet the section of the wire defines, or one wake pattern, including the line
  level the section requires just before it. From an exchange that failed without response from the wire (a failure counted for wire loss above) until an exchange on that wire succeeds, or until the connection is lost,
  the probe rests the lines released between exchanges, and drives them only during an exchange (each single retry is also an exchange). Released means not driven,
  with no pull or with a pull toward the rest level of that line on that connection. On the clock line of a connection that uses idle_clock 1 (low),
  no pull or pull-down, never pull-up. When an exchange succeeds again, the probe returns to the rest state of the connection (the clock line at the
  idle_clock level, the data line at its rest state: rvswd §3.1, swio §3.2, swd §5) before the next exchange. While exchanges succeed, the rest state between exchanges is as the section of the wire defines, and this rule does not change it.
- **The procedure that closes a connection does not reset/resume the target**. Changes of the target's state caused by external circuits are not guaranteed against.
- **The wire after closing (hold)**: when a connection closes other than by wire loss (detach, end / lease expiry / force of the session, core §9), the probe SHOULD **hold** the pins of that wire,
  driving them in the rest state of that connection (rvswd the resting of §3.1, swio §3.2, swd §5). Some targets lose their debug state within a few ms once the wire stops being driven
  (CH32L103 loses halt in about 5 ms and the hart is reset). The host cannot act in time, so the probe keeps it automatically
  (core §12 rule 8). A probe that does not hold puts the closed wire in the idle state of core §8 (holds always returns empty).
  The following are the rules for a probe that holds.
  - **It can be turned OFF**: a probe with settings declares the settings item `channel.{}.hold` (below) on that wire. If its value is false, it does not hold, and the pins go to the idle state of core §8.
    Without a value it holds. If the pin has a core setting idle or disable (core §13.8), it does not hold and follows that.
  - **Hold is a kind of idle state** (core §8): any interface can take a held pin the same as an idle pin (attach, plan, scan; hold is never a reason for cause 1
    or cause 5). The interface that takes it takes over the wire, and the hold of that combination ends. attach starts with wake (both lines start high),
    and the resting is decided again for that connection (§3.1). The same even if the target on the port was replaced.
  - **When the hold ends**: a pin was taken, `channel.{}.hold` became false, an idle or disable value was put on that pin, or the probe restarted. Pins whose hold ended
    go to the idle state.
  - **No hold on wire loss**: when closed by wire loss, the pins are not driven, as in "the wire while it does not respond" above, and go to the idle state.
  - **Visible**: held ports can be read with holds (§2.2). A hold is not a connection and does not appear in connections.

- When a connection closes, the channels of that combination either go to the hold above or to the idle state of core §8 (when not held, idle_clock driving also stops).

**Settings item** (core §13; the category is the fn of that wire. If a probe that holds has settings, all 3 wires of this document declare it):

| Name | form | key_kind | Meaning |
|---|---|---|---|
| `channel.{}.hold` | bool | channel (the SWDIO of that port) | if false, that port is not held after closing. Held if there is no value or it is true |

The key is a channel the declaration of that wire allows for SWDIO. Others are unsupported.

**State machine of connection and hart**:

| Event | connection | hart | Stream |
|---|---|---|---|
| detach / end / lease expiry / force | released (the wire is held, §2) | not touched | released |
| wire loss | released (the wire is idle) | — | released |
| self-reset of the target | kept | the target's state | kept (restart mark when marks is provided) |
| restart of the probe | invalid | the procedure does not reset/resume. Changes caused by the reset state of the pins are not guaranteed against | invalid |

- (Informative, safety) The end of a session (end, lease expiry, force) does not touch the hart: if the host dies with the hart halted, the target stays halted (unlike a debugger's
  detach, it does not start running). This is so whatever the target controls. A host that wants the target to run after it leaves resumes before end.

### 2.1 connections (list of connections)

```text
request: first(u8)
answer: more(u8), count(u8), count × entry, [TLV] (core §2.3)
entry: connection(u32), swdio(u16), swclk(u16), speed_hz(u32), tid_scheme(u8), tid_len(u8), tid
```
- Returns the live connections of that interface, in the order they were made, from the first-th, as many as fit in one frame. If more = 1 there is more, and the host
  adds the number received to first and asks again. Usable without the lock.
- tid is the target_id read at attach (tid_scheme 0, tid_len 0 if none). For swd, tid_scheme 2, tid_len 4, and tid is DPIDR.
  An entry for which TARGETSEL was specified on swd gets the answer TLV 0x01 selected_target (entry_index(u8), targetsel(u32)).
  entry_index is the 0-based number in this page. This TLV can repeat per entry. Only entries that fit in 1 frame together with their needed TLVs are returned.
  The selector is the selection value the host gave, distinct from the identifier read. No specification and a specification of value 0 are also distinct.

### 2.2 holds (list of held ports)

```text
request: first(u8)
answer: more(u8), count(u8), count × entry, [TLV] (core §2.3)
entry: swdio(u16), swclk(u16), rest(u8)
```

- Returns the ports that interface drives by the hold of §2, from the first-th, as many as fit in one frame (paging as in §2.1). Usable without the lock.
- For swio, swclk = 0xFFFF. rest is, for rvswd, its resting (the value of idle_clock: 0 high, 1 low), and 0 for other wires.

## 3. `oep.wire.rvswd` / `oep.wire.swio`

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x10 | scan | count(u8), count × (swdio(u16), swclk(u16)), [TLV] | tried(u8), count(u8), count × (kind(u8), swdio(u16), swclk(u16), id(u32)), [TLV] | needed | optional |
| 0x11 | attach | method(u8: 0 no halt / 1 halt), swdio(u16), swclk(u16), max_speed(u32), [TLV] | connection(u32), id(u32), flags(u8), speed_hz(u32), [TLV] | needed | required |
| 0x12 | detach | connection(u32), [TLV] | — | needed | required |
| 0x13 | connections | first(u8) | §2.1 | not needed | required |
| 0x14 | holds | first(u8) | §2.2 | not needed | required |

- A swio combination has swclk = 0xFFFF (one line; swclk ≠ 0xFFFF is a combination the declaration does not allow, rejected unsupported as in §1 in both scan and attach). The kind of the scan entry of rvswd and swio is 1 (riscv-dm),
  and id is DMSTATUS for both scan and attach. The users of that connection are `oep.target.riscv-dm` and `oep.target.console`.
- method 0 is required. method 1 is provided only when declaring features bit0 (attach_halt) of describe.
  An unprovided method and an unknown method are unsupported (fixed-part mark 0). method 1 sets hartsel to 0, and succeeds only if hart 0 halted and haltreq could be lowered.
- **flags of attach** (common to the 3 wires, `attach_flags` of the registry): bit0 acknowledged a pending havereset (riscv), bit1 unassigned,
  bit2 woke from dormant (swd), bit3 the probe confirmed hart 0 halted (0 is unconfirmed).
  method 0 is not required to change the hart selection or confirm the halted state. The dpc TLV is an optional RV32 diagnostic value, added only when bit3 is set and it could be read.
- **wake / setup procedure** (1 of §1): rvswd: the wake pattern (§3.1), then write 0x5AA50400 to DMI 0x7E and to DMI 0x7D. That set twice.
  swio: write 0x5AA50400 to DMI 0x7E and to DMI 0x7D. That set twice. The frames of both wires are in §3.1 and §3.2.
- **scratch** (§1): PROGBUF0 (DMI 0x20). The write that frees it: ABSTRACTAUTO (DMI 0x18) = 0. This is not restored (autoexec left by a previous session runs
  on every access).
- **attach while applying reset**: with TLV 0x04 reset (critical: `channel(u16), hold_ms(u16)`), the probe holds the reset line (channel)
  for hold_ms and then releases it. With method 1 it keeps issuing halt while releasing, to halt as early as possible (flags bit3, dpc TLV). **There is no guarantee that it halts
  before the first instruction** (some code runs between the release of the reset line and the halt taking effect). When a guarantee of halting at the position right after reset
  is needed, use reset mode 1 of riscv-dm (release ndmreset while keeping haltreq). method 0 issues no halt request. This is an optional function, declared by role 3 (reset) of role_channels. A probe without it refuses the reset TLV with rejected unsupported (the tag as received, 0x84, core §2.3). Conflicts with pins in use are refused before the reset. hold_ms is
  subject to max_op_ms of the core.
- The wait after releasing the reset line is §2. The speed is verified after the DM answers (§1).
- **There is no default reset line**: the host states explicitly with channel every time which line to use for reset (a reset on the wrong line can
  break the target or the fixture). The channels a probe MAY use for reset are declared by role 3 (reset) of role_channels of describe. An undeclared
  channel is rejected unsupported with nothing executed (the tag as received, 0x85). A channel held by a current plan or connection is rejected
  unavailable as contention of core §8.1. A channel whose idle is an output is rejected unavailable as in §1. **The reset line is pulled low open-drain, and on release the probe stops pulling and puts it in the idle state of core §8** (so it does not short with an external reset button or
  other drivers). The channel is held only during the op. With a probe without it, the host sends the release of `oep.fixture.gpio` and attach together
  and retries.

TLVs (one space for the wire family. rvswd, swio and swd use those of this table they use, with the same numbers. core §2.5 item 4):

| op | tag | Name | Value |
|---|---:|---|---|
| scan | 0x01 | max_speed | u32 Hz (if absent, the slowest speed of the wire) |
| scan, attach (swd only) | 0x02 | targetsel | u32. swd in §3 |
| scan, attach (rvswd only) | 0x03 | idle_clock | u8. SWCLK while the wire rests: 0 = high, 1 = low. In attach it is critical, and if absent the probe decides from target_id (§3.1). In scan, the resting during the scan (high if omitted, below) |
| attach | 0x04 | reset | channel(u16), hold_ms(u16). critical. Above |
| answer of attach | 0x01 | target_id | scheme(u8), value |
| answer of attach | 0x02 | dpc | u32. Optional. RV32 dpc when hart 0 is halted (flags bit3) |
| answer of attach (rvswd only) | 0x03 | idle_clock | u8. The resting that connection uses (0 high, 1 low). rvswd always adds it |
| answer of connections (rvswd only) | 0x02 | idle_clock | entry_index(u8), idle_clock(u8). rvswd adds it per entry (counted the same way as selected_target of §2.1) |

The pin roles (1 swdio, 2 swclk, 3 reset), the scan kinds (1 riscv-dm, 2 arm-adi), the attach methods (0 no halt, 1 halt) and the bits of the attach flags are also
one space for the family. swio has no swclk, so it uses roles 1 and 3.

target_id schemes these wires use (`target_id_scheme`, one space per probe, §1): 1 = the u32 read at DMI address 0x7F (length 4). 0 and 0xFFFFFFFF mean "none" (not added).
2 = DPIDR of swd (u32, length 4).

### 3.1 RVSWD frames

There are 2 lines, SWDIO (pin role 1) and SWCLK (pin role 2). The probe always drives SWCLK. It drives SWDIO except during read data,
and keeps a pull-up on SWDIO while using the wire (so that the line reads high when neither side drives).

**Bit slots.** T is a half period. One bit slot is SWCLK low for T, followed by SWCLK high for T.
- A bit the probe sends: the probe sets SWDIO to that bit at the SWCLK falling edge that starts the slot (the 2 lines change at the same time), and keeps it until the next falling edge.
  The target reads it at the rising edge.
- A bit the target sends: the target changes SWDIO after the falling edge. The probe reads SWDIO at the end of the low half, just before the rising edge.

**Conditions** (the only places where SWDIO changes while SWCLK is high):
- START: both lines high for T or longer, then SWDIO falls with SWCLK kept high. The first bit slot starts T later.
- STOP: one bit slot with SWDIO low, then SWDIO rises with SWCLK kept high. After that both lines stay high for T or longer.

**Frame**: one DMI access. Values are sent most significant bit first. A frame is 53 bit slots.

| Field | Slots | Driven by | Value |
|---|---:|---|---|
| START | — | probe | |
| address | 7 | probe | DMI address |
| direction | 1 | probe | 1 write, 0 read |
| header parity | 1 | probe | makes the number of ones in address, direction and this bit even |
| aux 1 | 5 | probe | 1, 0, 1, 0, 1 |
| data | 32 | probe (write), target (read) | 32 bit value |
| data parity | 1 | the same side as data | makes the number of ones in data and this bit even |
| aux 2 | 5 | probe | 1, 0, 1, 1, 1 |
| STOP | 1 | probe | the SWDIO-low bit slot of STOP |

- **Turnaround** (read): the probe stops driving SWDIO while SWCLK is high, after the rising edge of the last slot of aux 1, and the first data slot
  follows without an extra slot. After the rising edge of the data parity slot, the probe drives SWDIO high again, and aux 2 follows without an extra slot. The target drives SWDIO
  only during the 33 slots of data and data parity.
- A read whose data parity does not match is a failed read (retried as in §2). Writes have no acknowledgment: the write path can be verified only by reading back (§1).
- **Resting** (between frames): with idle_clock 0, both lines stay high. With idle_clock 1, SWCLK low and SWDIO high, both driven by the probe. A frame starts with both lines
  high: with idle_clock 1, SWCLK rises with SWDIO kept high at least T before START.
- **How the resting is decided**: the needed resting is determined by the target family and is opposite between families (CH32L103 resets its debug module in about 1 ms when resting high,
  and CH32X035 cannot be attached when resting low). No default is safe for both. attach starts with both lines high, so on any family target_id
  (scheme 1, DMI 0x7F) can be read. Checking the connected device and correcting it from the host is too late, so the probe has an automatic decision (core §12 rule 8).
  The resting is decided in this order:
  1. if there is the idle_clock TLV of attach (the host's explicit choice), that;
  2. if not, and the value of the settings item `channel.{}.rest` (below) of `oep.wire.rvswd` for that SWCLK channel is high or low, that (a port with the automatic decision turned OFF);
  3. if there is none or it is auto, the automatic decision: the probe does wake through reading target_id with high, and if bits 31 to 20 of the target_id read (the family, registry
     `target_id_family` of `oep.wire.rvswd`) are in `idle_low_family`, low; otherwise (also when target_id cannot be read) high.
  In all cases, the resting used is returned in the TLV idle_clock of the attach answer and of connections (so the host knows the automatic decision was made).
  One connection has one resting, which does not change during the connection. To change it, detach and attach again (an attach on pins of a live connection is refused as in §1).
  The table of families is target knowledge, so it is kept in the registry, and each implementation looks it up by name (adding a family is a registry change).
  An attach with method 0 (including console pass-through, [Console](oep-if-console.md)) decides the same way.

**Settings item** (core §13; the category is the fn of `oep.wire.rvswd`. A probe that makes the automatic decision declares it):

| Name | form | key_kind | Meaning |
|---|---|---|---|
| `channel.{}.rest` | enum: 0 `auto`, 1 `high`, 2 `low` | channel (the SWCLK of that port) | high / low fix it to that value with no automatic decision. Automatic decision if there is no value or it is auto |

The key is a channel the declaration of `oep.wire.rvswd` allows for SWCLK. Others are unsupported. The idle_clock TLV of attach always takes precedence.

**Wake pattern** (the first part of the wake / setup procedure, §3):

1. drive both lines high for 20 µs or longer;
2. 100 bit slots with SWDIO high;
3. 1 bit slot with SWDIO low;
4. SWDIO rises while SWCLK is high (the STOP condition);
5. before the first frame, both lines high for 20 µs or longer.

- **Speed of the wake / setup procedure**: T is 500 ns or longer, and 1 / (2 × max_speed) or longer. When the probe writes dmactive (2 of §1), it MAY write the setup set
  (DMI 0x7E, then DMI 0x7D) twice more right after it with the same T. These writes are part of the wake / setup procedure.
- **How the speed is chosen**: the probe chooses T by reading DMSTATUS, going from the slowest T toward shorter ones (§1).
- The wake pattern can reset not only the debug port of the target but the target itself (the rule of §2 on retries that do not change the state of the target applies).

### 3.2 SWIO frames

There is 1 line, SWDIO (pin role 1). It is high while resting. When sending, the probe drives the line both high and low. While using the line, the probe keeps a
pull-up on it. Between frames, the line rests high: the probe drives it high or releases it to its pull-up. It MAY drive it high there only while the target is answering. After an exchange fails, it releases the line to the pull-up and does not drive it high (§2, the wire while it does not respond).

**Bit slot the probe sends**: the line low, then high.

| Slot | low | then high |
|---|---|---|
| 1 | 240 to 310 ns | 240 to 270 ns |
| 0 | 840 to 1060 ns | 240 to 270 ns |


**Bit slot the target sends** (read slot): the probe drives the line low for 240 to 270 ns and stops driving. The target sends 0 by keeping the line low,
and 1 by letting it rise. The probe reads the line 520 to 600 ns after the falling edge it made (high = 1, low = 0). After that, it waits until the line reads high
again. If it does not read high within 100 µs, the read fails. Once high, the probe drives the line high for 130 ns or longer before the next slot.
After it stops driving low, and after reading a 0, the probe MAY drive the line high once for 30 ns or less (a charging pulse, to shorten the rise
through the pull-up).

**Frame**: one DMI access. Most significant bit first, 41 slots:

- write: START (a 1 slot), the 7 bit DMI address, direction 1, then 32 data slots sent by the probe;
- read: START (a 1 slot), the 7 bit DMI address, direction 0, then 32 read slots.

- There is no parity, acknowledgment or STOP. A read can detect only a line that does not return high; it cannot detect a wrong bit.
- The probe keeps all slots of a frame within the times above (nothing interrupts a frame). After a frame and before the next, the line stays high for 8 µs
  or longer.
- **Speed**: the bit times are fixed, so the probe does not choose a speed. min_clock_hz of describe declares the speed of the 0 slot (1 / (its low + its high)).
  speed_hz of attach is also this value. If max_speed is lower than it, unsupported (§1). The scratch check is done at this fixed speed.

## 4. `oep.target.riscv-dm`

A request starts with connection(u32).

- **The only required op is dmi**. halt, resume, reset, read_block, write_block, run and step are optional, declared in ops of describe
  (core §1.2, §7.4). read_block and write_block come as a pair. The host can build the same things with dmi even without the optional
  ops.
- **Scope of ops other than dmi (high-level ops)**: they handle only hart 0 of RV32 (addresses, register values and pc are u32). Within a high-level op the probe sets
  hartsel of DMCONTROL to 0, and **returns with it set to 0** (a hartsel the host chose with dmi applies only within that dmi request). Other harts are
  handled by the host with dmi.

**Cleanup of an op**: success of a high-level op is returned only when all of the cleanup in the table below is done.
What is restored is the values the op used temporarily. The effects of halt/resume/reset and memory writes the host asked for remain.
No restoration or additional reads and writes by the probe itself are inserted into raw dmi.

On failure too, the cleanup is attempted within max_op_ms of the whole request. If a value that needs restoring or haltreq cannot be restored,
the probe returns completed failed / partial and then closes that connection and the dependent streams (common parts §2).
status indicates the failure of the cleanup, and done stays the number of steps/words finished. The target is not guaranteed to be in its original state.
read_block / write_block are partial if done > 0 and failed if done = 0, also when the cleanup failed.
Even when all words were transferred, done = count > 0, it is partial; completion of the transfer alone does not make success.
No reset/resume is done for recovery, and no table that carries restoration over to the next op or the end of the session is required.
If needed, the host attaches again, checks the state of the target and recovers.

| op | What the probe touches | Before the answer |
|---|---|---|
| halt | haltreq | checks allhalted and then lowers haltreq. Tries to lower it also when the wait ran out |
| resume | haltreq = 0, resumereq = 1 once | remembers nothing, restores nothing |
| step | dcsr.step, DATA0 / DATA1 (read and write of dcsr), haltreq | lowers dcsr.step, restores DATA1 and DATA0, lowers haltreq. If the hart cannot be halted again, the answer shows step_left (§4.2) |
| reset | haltreq, ndmreset, acknowledgment of havereset, the system reset of the target (§4.3) and the RAM used for it | releases ndmreset, acknowledges havereset, lowers haltreq. Restores the RAM used. With mode 1 the hart stays halted |
| read_block / write_block | GPR (s0, s1, a0, a1), DATA1 / DATA0, abstractauto, program buffer, sysbus | restores GPR, DATA1, DATA0 and abstractauto. Does not restore the program buffer and SBCS / SBADDRESS (the host sets them again if it uses them) |
| run | pc, the GPRs the host specified, dcsr (ebreakm, prv), haltreq | **returns with them changed as the host instructed** (the host's responsibility). Restores abstractauto and haltreq |
| dmi | what the host wrote | touches nothing, restores nothing (if the host used DATA, the host restores it) |
| console reading | DATA0 / DATA1 | as in [Console](oep-if-console.md) §3 |

The values restored are the "values before touching" read within that op. How long to wait for DM states (abstractcs.busy clearing, allhalted, allresumeack) within a high-level op is decided by
the probe (within max_op_ms). The status when the wait runs out is as in the section of each op (timeout for halt, state for resume / step). DMI busy is
retried within the probe, and when it gives up, status wait (the same as WAIT of §6).

**DATA0 and DATA1**: the console mechanisms ([Console](oep-if-console.md) §3) use DATA0 / DATA1 as a mailbox with the target. The probe restores the DATA0 / DATA1
used in its own ops before a success answer (on failure, the cleanup rules above). When the host changes DATA0 / DATA1 with dmi requests using abstract commands and so on, it writes back
the values from before the change before running the hart.

| op | Name | Request (after connection) | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x10 | dmi | n(u16), n steps | done(u16), status(u8), nvals(u16), nvals × value(u32), [TLV] | needed | required |
| 0x11 | halt | — | status(u8), [TLV] | needed | optional |
| 0x12 | resume | — | status(u8), [TLV] | needed | optional |
| 0x13 | reset | mode(u8), [TLV] | status(u8), flags(u8), pc(u32) (dpc with mode 1), [TLV] | needed | optional |
| 0x14 | read_block | address(u32), count(u16), [TLV] | done(u16), status(u8), done × word(u32), [TLV] | needed | optional (pair with write) |
| 0x15 | write_block | address(u32), count(u16), count words, [TLV] | done(u16), status(u8), [TLV] | needed | optional (pair with read) |
| 0x16 | run | pc(u32), timeout_ms(u32), n(u8), n × (regno(u16), value(u32)), n_out(u8), n_out × regno(u16), [TLV] | status(u8), stopped(u8), dpc(u32), elapsed_us(u32), nvals(u8), nvals × value(u32), [TLV] | needed | optional |
| 0x17 | step | — | status(u8), moved(u8), dpc_before(u32), dpc_after(u32), [TLV] | needed | optional |

Empty results and edge values: dmi with n = 0 is success, done 0. dmi with max_reads / max_us = 0 reads once. If the same regno appears twice in n_out of run,
it is returned twice as it is.

### 4.1 dmi

| kind | Step | Arguments | Value added to the answer |
|---:|---|---|---|
| 0x01 | write | address(u8), value(u32) | — |
| 0x02 | read | address(u8) | the value read (u32) |
| 0x03 | wait with a limit on the number of reads | address(u8), mask(u32), value(u32), max_reads(u16) | the last value read (u32) |
| 0x04 | wait | wait_us(u32) | — |
| 0x05 | wait with a limit on time | address(u8), mask(u32), value(u32), max_us(u32) | the last value read (u32) |

- For an unknown kind the probe does not guess the length of the arguments; it stops validation at that position and refuses the whole request with rejected unsupported (fixed-part mark 0).
  The steps before it are not executed either. Short arguments of a known kind are malformed. The probe checks all steps before executing.
- **done is the number of steps finished to the end** (on failure, the 0-based number of the failed step). Only 0x02 / 0x03 / 0x05 add values.
  `nvals` is the number of values in the answer (the number of value-adding steps among the first done steps, plus 1 if the failed step was 0x03 / 0x05 and its wait ran out
  (status timeout)). A step that failed without reading, because of a wire fault and so on, adds no value.
- Before execution, with r the number of steps that return values, the probe checks that the fixed result of the success answer, `10 + 4×r` bytes, fits in the max_frame of that transport.
  If it does not fit, it refuses with unsupported (fixed-part mark 0) and does not access the DMI (core §4.4). Optional diagnostic TLVs are added only as far as they fit.
- The sum of wait_us of 0x04 steps and max_us of 0x05 steps MUST NOT exceed max_op_ms (rejected unsupported). 0x03 steps are bounded by count, not time.
  This sum is the amount of explicit waiting, not the upper limit of the whole request including internal retries, transfers and cleanup. The host's wait follows core §4.4.
  If the request reaches max_op_ms while running, the probe ends the request at that step and answers with status timeout (done = the number of that step).
- **A host that has a console stream of the same connection open puts a sequence of an abstract command (writes of data1 / data0, command, read of data0) in one dmi request** (it is not broken
  even if the probe inserts console reading between requests; `oep.target.console` §3).
- **In the same case, a sequence of steps that handles haltreq / havereset is also put in one dmi request, using wait steps**.
  For example, to reset and wait for halt, the release of reset with haltreq kept, the acknowledgment of havereset, the check of the halt and the release of haltreq are done in the same request.
  When console reading acknowledges havereset between requests, it writes DMCONTROL and lowers haltreq, so do not rely on haltreq being kept across requests.
  If the console stream of the same connection is closed and the host inserts no other conflicting target operation, raw steps MAY be split into several dmi requests.
  This split has no atomicity; if a session end or a communication failure leaves it partly applied, the host checks the state and recovers.
- **Groups that MAY be redone** (the exception of [Common parts](oep-if-common.md) §3): a group of dmi the host sends while the hart is halted whose writes are only the following
  changes the target only to the same state as executing it once, however many times it runs. When the host could not confirm the result of the group (no answer, status line /
  wait / timeout, a check the host put in the group (a read of DMSTATUS, a read-back) does not match), it MAY redo the whole group with a new corr.
  1. clearing cmderr in ABSTRACTCS, and writes to DATA0 / DATA1;
  2. an access register with aarsize 2 (32 bit), transfer 1 and postexec 0 that reads a register with no effect other than its value (GPR, dpc, dcsr) (write 0),
     or that writes a value put in DATA0 earlier in the same group (write 1).
  A group that includes other writes (memory, other CSRs, execution of the program buffer, abstractauto, haltreq / resumereq / ndmreset) is not redone.
  While the hart is halted, the probe does not use DATA0 / DATA1 for the console ([Console](oep-if-console.md) §3), so a redo does not collide with the
  mailbox. The number and interval of redos are finite, and the DATA0 / DATA1 values put by writes of the group are restored before running the hart, as in §4.
  (Informative) Reading back in the same group after a write also finds glitches of a wire that pass the DMSTATUS reads before and after (one write missed).

### 4.2 halt, resume, step

- **halt** lowers haltreq and returns ok if already halted. If allhalted is not seen after waiting, it tries to lower haltreq and answers with status timeout.
  If it cannot be lowered, it is handled as a cleanup failure of §4.
- **resume** writes haltreq = 0, resumereq = 1 once. ok means "the hart left debug mode", judged by allresumeack of DMSTATUS (or
  allrunning and not halted). resumereq is not issued again. If it is not seen after waiting, status state.
  - (Informative) For some targets this is not enough (a target that does not set allresumeack halts again at a breakpoint right away; one resumereq may not get it
    out). Handling that (reading dpc and resuming again if it did not move, and so on) is done by the host that knows the target.
- **step** sets dcsr.step, issues resume only once, and lowers dcsr.step when it comes back. It is not a failure even if dpc does not move (status ok, moved = 0; an instruction that jumps
  to itself has the same dpc even when it progresses correctly, so the host reads the instruction and judges). prv is not changed.
  If the hart does not return to debug mode, the probe sets haltreq and waits. If the hart halts, it lowers dcsr.step,
  restores DATA1 / DATA0 and answers with status state. If it does not halt, it lowers haltreq, adds the answer TLV 0x01 step_left
  (length 0), and answers with status state. dcsr.step may still be set, and the hart is running.
  The cleanup cannot be completed, so the connection is closed. The host attaches again, halts, and lowers dcsr.step.
- moved, dpc_before and dpc_after of step have meaning only with status ok. Otherwise the probe sets them all to 0 and the host does not read them (if the hart is
  halted, the host reads dpc with dmi).

### 4.3 reset

| mode | Meaning |
|---:|---|
| 0 | run |
| 1 | halt before the first instruction |

Answer:

| Field | Meaning |
|---|---|
| flags bit0 | the state of the requested mode was confirmed (mode 0 is running, mode 1 is halted and dpc could be read) |
| pc | dpc for mode 1 with flags bit0 set. 0 otherwise |

- Only modes 0 and 1 are defined. Others are unsupported (fixed-part mark 0). success only when flags bit0 is set and the cleanup is also done.
  flags bit0 does not mean the cleanup succeeded. Otherwise completed failed (the same form; status is
  does not halt/does not run = timeout, the DM does not respond = line, cmderr = fault). The waiting and cleanup are done within max_op_ms.
- The wait after the reset is §2. If the DM does not answer, completed failed with status line. If the needed cleanup is not done, the connection is closed (§4).
- Other bits of flags are 0. After reset, havereset is acknowledged and haltreq is lowered (mode 1 stays halted).

reset is a **system reset** of the target: it returns not only the hart but also the peripherals to their default values. On a target where ndmreset also returns the peripherals, ndmreset is used.
On a target where ndmreset returns only the hart (and the debug module), the probe uses the system reset of that target.

- ndmreset of CH32 (WCH RISC-V) returns only the hart. The new image may start with peripherals the previous image started (SysTick, USART, RCC and so on) still running,
  and stop on their interrupts. The probe uses the system reset of PFIC (KEY3 and SYSRESET in PFIC_CFGR; for series without PFIC_CFGR,
  SYSRESET of PFIC_SCTLR). That write is made outside a debug module command, while the probe is not putting a frame on the wire
  (in some series, a reset that hits in the middle of a command or a frame makes later frames keep failing).
- After the system reset, the target image may run briefly before the hart is halted (series where the reset also returns the debug module). mode 1
  then halts the hart before the first instruction (ndmreset and haltreq). The peripherals start from the state after the system reset.
- When the probe uses RAM for the system reset, it restores what it used to the original values after halting the hart.

**The reset op does not move the reset line**: the reset line moves only with the reset TLV of attach (§3), or when the host uses a fixture interface itself.

### 4.4 run

- It is for calling the host's loader. The probe sets ebreakm and prv = M of dcsr, runs from pc, and waits for it to stop. **The probe does not issue run
  again** (even if the stop position is still the start position, it cannot be distinguished from having run and come back). The host does not judge from dpc alone that it was not executed either.
  dpc is treated as information about the stop position, and a new request is sent only when target-specific state or the like confirms that it MAY be executed again.
  **Do not use it for a debugger's continue** (it changes prv and ebreakm).
- If timeout_ms exceeds max_op_ms of the core, rejected unsupported. The whole request, including preparation and cleanup, finishes within max_op_ms.
  timeout_ms is the upper limit of waiting for execution; if the remaining time of the whole request is shorter, the probe tries to halt and clean up within that remaining time.
  The host's wait follows core §4.4 and is not decided from timeout_ms alone.
  When it stops, stopped = 1 (success if the cleanup is also done). When it reaches the limit, the probe halts the hart, then reads dpc and the values, and returns stopped = 0, status timeout, outcome
  failed (dpc and the values are all valid). If it cannot halt it, stopped = 2, status timeout, outcome failed, nvals = 0 (dpc is invalid).
  If the preparation before running (setting registers, dcsr, pc) fails, the probe issues no resume and returns stopped = 3, status of that failure, outcome failed,
  nvals = 0 (dpc is invalid). The answer always has the same form (`run_stopped`: 0 halted at the time limit, 1 stopped, 2 could not halt, 3 did not run).
  An invalid dpc is 0.
- **elapsed_us** is the time (µs) the probe measured from the write that ran the hart (resumereq) until it saw it stop (stopped 1), halted it at the limit (0), or gave up
  halting it (2). 0 for stopped 3.
- regno is the RISC-V abstract register number (a0 = 0x100A).

### 4.5 read_block, write_block

- In words (32 bit). 8 / 16 bit accesses are built with dmi steps.
- **Length of one call**: a probe with read_block / write_block always puts the common tag max_length (core §7.4) in describe. The unit is the **number of bytes**
  (a multiple of 4). The host makes count of read_block an integer at most `min(max_length, max_frame − 8) / 4`, and count of write_block an integer at most
  `min(max_length, max_frame − 20) / 4`. The 8 bytes of read are the answer header 5 + done 2 + status 1, and the 20 bytes of write are
  the request header 10 + connection 4 + address 4 + count 2. A large transport is not uniformly limited to the transfer amount of a small transport.
  A request whose needed result does not fit in a frame is refused with unsupported before execution (core §4.4). If count × 4 exceeds max_length, rejected unsupported (payload `0x00`). count = 0 is
  success, done 0. An address that is not a multiple of 4 is rejected malformed.
- **Meaning of a read**: read_block reads through the target's bus. The probe keeps no copy on its side (it reflects what the target
  wrote with the preceding write_block, dmi or run).
- **Precondition**: the hart is halted (if not halted, status state). Addresses are those the halted hart uses in M mode.

### 4.6 Handling of RISC-V connections

- attach first acknowledges a pending havereset (some DMs freeze halt / running of DMSTATUS until it is acknowledged).
- **Automatic acknowledgment of havereset** is done in high-level ops and console reading. The raw dmi op gets no additional reads, writes or acknowledgments inserted; only the steps the host specified are executed.
  If the same connection has a dmseq console stream, that stream is returned to unsynchronized after the automatic acknowledgment.
  If there is a console stream and marks is provided, a restart mark (kind 0x41, detail 1) is put.
  After the acknowledgment of havereset by the probe's own reset op too, only existing dmseq streams are returned to unsynchronized. A probe that does not provide the console is not required to keep a synchronization state or marks.
  When the reset op succeeds, one reset (kind 0x40, detail 1) is put, and no restart is added for the same reset.
  At attach there is no stream, so no mark is put. An fn that does not provide marks is not required to keep marks.
  When the host resets the target or acknowledges havereset with raw dmi, the needed console synchronization initialization is made explicit by close/open of the stream.

## 5. `oep.wire.swd`

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x10 | scan | count(u8), count × (swdio(u16), swclk(u16)), [TLV] | tried(u8), count(u8), count × (kind(u8), swdio(u16), swclk(u16), id(u32)), [TLV] | needed | optional |
| 0x11 | attach | method(u8: 0 only; others are unsupported, fixed-part mark 0), swdio(u16), swclk(u16), max_speed(u32), [TLV] | connection(u32), id(u32), flags(u8), speed_hz(u32), [TLV] | needed | required |
| 0x12 | detach | connection(u32), [TLV] | — | needed | required |
| 0x13 | connections | first(u8) | §2.1 | not needed | required |
| 0x14 | holds | first(u8) | §2.2 | not needed | required |

- The kind of scan is 2 = arm-adi. id is DPIDR for both scan and attach. The forms of requests and answers are the same as §3.
- The TLVs of scan are 0x01 max_speed and 0x02 targetsel. The TLVs of attach are 0x02 targetsel and 0x04 reset (optional, §3).
- **wake / setup procedure** (1 of §1): switching from JTAG to SWD, wake from dormant, and TARGETSEL when given. swd names no scratch registers.
- **Speed verification**: the probe chooses a speed at or below max_speed at which a read of DPIDR ends with ACK OK and correct parity.
  No scratch write/read-back is done. A read and an ACK alone do not guarantee that write data is correct, so
  target-specific write verification is done by the host with transfer as needed.
- attach tries the switch from JTAG to SWD, and if there is no answer, wakes from dormant (flags bit2). Power-up (CDBGPWRUPREQ /
  CSYSPWRUPREQ of CTRL/STAT) is done by the host with DP writes.
- **Lines and packets**: the lines of this wire are the 2 lines SWDIO (pin role 1) and SWCLK (pin role 2), and it uses the SWD procedures of the Arm Debug Interface (ADIv5 / ADIv6).
  The probe always drives SWCLK. A packet is one SWD packet of those procedures, including the request, the acknowledgment and the data phase the procedure gives it, together with their
  turnaround cycles. Each packet, and each procedure of line reset, switching from JTAG to SWD and wake from dormant, is one exchange of §2.
- **Idle cycles**: after every packet, and after each of the procedures above, the probe clocks at least 8 idle cycles: clock cycles with SWDIO driven
  low by the probe. These are part of that exchange (§2).
- **Resting** (between exchanges): the probe drives SWDIO low and SWCLK high.
- **Before the probe stops driving the lines** (when a connection closes by detach and so on, when the probe releases the pins, or when it enters the released state of
  "the wire while it does not respond" of §2), it clocks the 8 idle cycles after the last packet, so that the target can finish that packet.
- **targetsel (TLV 0x02, u32) is sent as critical** (only for multidrop; if it were ignored, attach would go to another target).
  The connection keeps whether it was specified and its value. In v1 one pin combination has only one connection, and whether targetsel is the same or different,
  an attach including those pins is unavailable (cause 1). To switch, attach after detach.
  scan tries without targetsel (a multidrop
  target that needs TARGETSEL does not appear in scan; one can be tried by specifying exactly one with TLV 0x02 targetsel of scan).
- The console does not run over an swd connection.

## 6. `oep.target.arm-adi`

A request starts with connection(u32). transfer is required. read_block/write_block are optional ops provided as a pair, declared in ops.
A minimal implementation MAY have only transfer; the host builds AP selection, CSW/TAR setup and collection of posted reads with raw transfers.
read_block/write_block are operations that bundle those procedures within the probe; if not provided, unknown_operation. No features are added for optional ops.

| op | Name | Request (after connection) | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x10 | transfer | n(u16), n transfers: req(u8: bit0 APnDP, bit1 RnW, bit2-3 A[3:2], bit4-7 are 0), and value(u32) for a write | done(u16), status(u8), ack(u8), nvals(u16), nvals × value(u32), [TLV] | needed | required |
| 0x11 | read_block | address(u32), count(u16), [TLV] | done(u16), status(u8), done × word(u32), [TLV] | needed | optional (pair with write) |
| 0x12 | write_block | address(u32), count(u16), count words, [TLV] | done(u16), status(u8), [TLV] | needed | optional (pair with read) |

- ack is the raw ACK of the last transfer (`swd_ack`: bit0 is first in line order. OK = 1, WAIT = 2, FAULT = 4. No response is status line). If bits 4-7 of req are not
  0, validation stops at that position and the whole request is refused with rejected unsupported (fixed-part mark 0). The transfers before it are not executed either.
  A short value of a write with a known req is malformed. nvals is the number of values read (the number of reads among the first done transfers).
  n = 0 is success, with done 0, status ok, ack 0 (ack is 0 if there is no transfer at all), nvals 0.
- transfer is a raw transfer; an AP read returning one transfer late is also left as it is (the host receives it with RDBUFF or the next AP read).
  WAIT is retried within the probe, and when it gives up, status wait. It stops on FAULT, so the host clears the sticky bits with ABORT.
- Before execution, with r the number of read transfers, the probe checks that the fixed result of the success answer, `11 + 4×r` bytes, fits in the max_frame of that transport.
  If it does not fit, it refuses with unsupported (fixed-part mark 0) and sends no transfer on the wire (core §4.4). Optional diagnostic TLVs are added only as far as they fit.
- When read_block / write_block are provided, the length of one call and the meaning of a read are the same as riscv-dm (§4.5): max_length of describe (number of bytes, a multiple of 4) is always present,
  and if count × 4 exceeds it, rejected unsupported (payload `0x00`). The host chooses a count that fits in the frame of that transport with the read and write formulas of that section.
  read_block reads through the target's bus, and the probe keeps no copy on its side.
- read_block / write_block use TAR / DRW of the current MEM-AP. SELECT and CSW (32 bit, single increment) are set by the host beforehand. The probe
  rewrites TAR where it crosses the range in which automatic increment of TAR is guaranteed (ADI), and reorders the reads that come one late. **The halted state of the CPU does not matter** (a MEM-AP can be read while the CPU runs).
  **done is the number of words the probe sent**, not a guarantee that the target received them (a FAULT of a posted write appears in a later transfer). TAR is left advanced, and
  SELECT / CSW are not changed (the arm version of the invariant of §4: the probe does not change what the host set).

## 7. Referenced specifications

The OEP messages of this document are determined by this text alone. The RVSWD and SWIO frames are defined by §3.1 and §3.2. What is used to drive the target:

| Interface | Specification | Part used |
|---|---|---|
| `oep.wire.swd`, `oep.target.arm-adi` | Arm Debug Interface Architecture Specification, ADIv5.2 and ADIv6.0 | SWD packets, turnaround, line reset, switching from JTAG to SWD, wake from dormant, TARGETSEL. DP and AP registers. TAR, DRW and CSW of MEM-AP |
| `oep.wire.rvswd`, `oep.wire.swio`, `oep.target.riscv-dm` | RISC-V Debug Specification 0.13.2 and 1.0 (DMSTATUS.version 2 and 3) | DMI registers (DMCONTROL, DMSTATUS, ABSTRACTCS, COMMAND, ABSTRACTAUTO, DATA0, DATA1, PROGBUF0, SBCS, SBADDRESS), abstract commands, program buffer, dcsr, dpc, havereset |
