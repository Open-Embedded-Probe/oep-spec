# OEP standard interfaces: wire and debug v1

[日本語](oep-if-debug.ja.md)

Status: out of date. Until the v1 freeze the Japanese text (.ja.md) is the working text; this English version will be regenerated from it at the freeze and becomes authoritative then.

Status: **normative** (v1, before the freeze: until the v1 freeze a rule or a number may still change). Before the freeze, revision 1 alone does not identify a form: an implementation names the specification tag it implements ([versioning](../docs/versioning.md) §6). The core is [OEP core](../docs/oep-core.md), the common parts are [common parts](oep-if-common.md) (§2 debug
connections, §3 status). The only definition of the numbers is `registry/oep-v1.toml`.

| Name | revision | Role |
|---|---:|---|
| `oep.wire.rvswd` | 1 | Connects to a RISC-V DM over the 2-wire RVSWD |
| `oep.wire.swio` | 1 | Connects to a RISC-V DM over the 1-wire SWIO |
| `oep.wire.swd` | 1 | Connects to ADI over ARM's SWD |
| `oep.target.riscv-dm` | 1 | Operations on a RISC-V Debug Module |
| `oep.target.arm-adi` | 1 | Operations on ARM ADI (DP / AP) |

- `oep.wire.*` creates connections, and `oep.target.*` operates on the target over a connection. The interfaces that handle targets
  appear in list before attach, and a request without a connection is rejected no_connection.
- **The target's family (the chip type) is not declared.** Per-chip knowledge (how to write flash, the quirks of the DM) is held by the host.
- Every op other than connections requires the lock.

## 0. What every wire shares, and what a new wire defines

Every `oep.wire.*` interface:

1. uses op 0x01 scan, 0x02 attach, 0x03 detach and 0x05 connections with the meanings of §1 to §2.1 (a wire may add ops from 0x06). All four are
   required on every wire;
2. follows §1 (verify the speed by reading before writing, count = 0 and what it leaves out, seats and max_connections, the scan and attach budgets, refusals) and
   §2 (lifetime, wire loss, the lines while the wire does not answer, the state machine, closing does not change the target), reading swdio / swclk as "the channel of pin role 1 / 2";
3. creates the connections of [common parts](oep-if-common.md) §2 that `oep.target.*` interfaces use.

A wire whose combination is not two pins writes, in its own document, its pins TLV, its scan entries and its connections entry with `n(u8), n × (role(u8), channel(u16))`
in place of the two u16 fields, keeping the other fields and their order.

**A wire without pins.** A wire that declares neither channel_group nor role_channels (its pins are not channels of this probe, for example a TCP endpoint that drives
another debugger) has exactly one combination, the one the endpoint uses:

- attach is sent without pins. A pins TLV is rejected unsupported (the tag as received), like any combination the declaration does not allow (§1);
- scan with count = 0 tries that one combination, and a request listing combinations is rejected unsupported;
- connections entries and scan entries carry 0xFFFF for each channel (in the `n × (role, channel)` form, n = 0);
- the pin rules of §1 (what count = 0 leaves out, held channels) have nothing to apply to.

A new wire's document also defines:

- its pin roles and how its speed is chosen;
- its wake / configuration sequence and its scratch registers (§1);
- its exchanges and the rest state of its lines between exchanges (§2);
- its "found" criterion and its scan_kind values;
- the target_id schemes it uses (from the single space of §1) and how wire loss is seen;
- which `oep.target.*` interfaces take its connections, and whether consoles and probe.config slots ride on them.

## 1. Rules for attach (all wires)

- **Writes before the speed is verified.** Until the probe has verified the wire speed, it writes to the target only:
  1. the wake / configuration sequence that the wire's section defines (for example a wake pattern, a line reset, a target select, or the debug-module configuration
     registers the module needs before it answers), sent at the wire's slowest speed;
  2. dmactive, on a wire whose connections reach a RISC-V DM, and only when DMCONTROL does not already read dmactive = 1 (the write clears haltreq).
- **Verifying the speed.** The probe chooses the speed by reads only. It then verifies the write path at the chosen speed by writing and reading back only the
  debug-module registers that the wire's section names as free scratch (registers no part of the target uses while no debug command runs), together with any write
  the wire's section names as making them free. Before the check it reads each scratch register, and after the check it writes that value back. A speed whose writes
  do not read back is not used.
- Nothing else is written to the target before the speed is verified (a write at a mismatched speed could write a garbled value into a target register).
- **A probe that attaches through another debugger.** The bound above applies to a probe that drives the wire itself. A probe whose attach goes through another debugger
  it does not control (it cannot see or bound what that debugger writes) sets bit0 `attach_writes_unbounded` of the wire's describe features (common tag 0x06,
  core §7.4), and is then outside this bound and outside the rule of §2 for the lines while the wire does not answer. A host treats an attach on such a wire like a reset of unknown effect: it does not expect the target's registers or the
  running program to survive it.
- **Pin combinations**:
  - The combinations the probe can use are declared with the common tags of describe (core §7.4). Fixed combinations with channel_group; if any pin can be assigned,
    with role_channels. The role numbers are `pin_role` (1 = SWDIO, 2 = SWCLK, 3 = reset).
  - The scan request is the sequence of combinations to try. **count = 0 means every combination the probe allows.** The combinations in the answer can be passed to the pins of attach as they are.
  - On a wire declared with role_channels, the allowed combinations are "candidates of role 1 × candidates of role 2 (a 1-wire has role 1 only), not using the same channel
    twice". The count = 0 sequence is in ascending order of swdio, then ascending order of swclk within it, and **combinations containing a channel currently held by something else (a plan, the connection of another wire,
    a settings resource) are not listed** (count = 0 tries only the combinations that may be driven). If a request listing combinations contains a held
    channel, the whole request is rejected unavailable as in core §8.1.
  - **Channels with an idle item**: the count = 0 sequence and the candidates of an attach without pins leave out every channel that has an **idle item**
    in the probe's settings (any mode, [probe settings](oep-if-probe-config.md) §1), in addition to channels held by something else and disabled channels.
    A request that names such a channel explicitly (a scan listing combinations, the pins of attach) is accepted when the idle is an input (mode 0 to 2).
    It is rejected unavailable (cause 5, the channel, holder_kind 7 = settings idle) when the idle is an output (mode 3 / 4).
    The reset TLV of attach (TLV 0x05, §3) naming a channel whose idle is an output (mode 3 / 4) is rejected unavailable in the same way, without executing anything
    (cause 5, that channel, holder_kind 7 = settings idle).
    An attach without pins whose only allowed combination contains a channel with an idle item (any mode, inputs included) has no candidate left: it is rejected
    unavailable (cause 5, that channel, holder_kind 7 = settings idle).
  - (Informative) count = 0 drives every free candidate pin in turn. Without the user's consent, a host does not send count = 0 to a fixture whose wiring it does not know.
  - A wire holds the channels of the combination a live connection is using (released when the connection is gone). While held, if a plan or the settings tries
    to take that channel, rejected unavailable (core §8.1).
  - The `tried` of the scan answer is the number of combinations tried from the start of the request's sequence (for count = 0, the count = 0 sequence above. On a channel_group wire, the order emitted in describe).
    At most 255 combinations are tried in one go (tried is u8; registry `scan_tried_max`). If the found combinations would make the answer no longer fit in one frame,
    the probe stops there. **The probe also stops where the scan budget (below) does not let it start the next combination**
    (at least one combination is tried). If tried ≥ 1, the host sends the continuation. If a request listing combinations returns tried smaller than the number listed, the host sends scan again with the remaining combinations.
  - **Continuing count = 0**: a count = 0 request can pass, in the TLV skip (0x01, u16), the number of combinations to skip from the start of the count = 0 sequence (0 if absent).
    The host continues by passing the sum of the tried values so far in skip, and **stops when tried = 0 is returned**. **If combinations remain in the sequence, the probe tries at least 1**
    (tried ≥ 1. tried = 0 only when the sequence is used up). **When the count = 0 sequence has no combination from skip on** (it is empty, or skip is at
    or beyond its length), the answer is completed success with tried = 0 and count = 0; the rule that at least one combination is tried applies only when a
    combination remains. Since the sequence is determined by what is held at the time of the request,
    if a plan or the like changes midway, combinations may be skipped or repeated (the host changes nothing else during a scan). A request with count > 0 and skip
    is rejected malformed.
  - attach specifies the combination with pins (TLV 0x03, critical). If pins is absent: if that wire has exactly one live connection, that combination
    (joining the existing connection. A connection held by a slot is fine too); if there is no live connection and exactly one allowed combination, that combination;
    otherwise (2 or more live connections, or no connection and 2 or more allowed combinations) rejected unavailable (the host chooses).
  - **A combination the declaration (channel_group / role_channels) does not allow is rejected unsupported without executing anything** (scan refuses the whole
    request if even one is in it). attach puts the pins tag as received in the payload. scan puts tag 0x00 followed by TLV 0x40 index (u8, its position in the
    request's sequence). A combination with a held channel (plan, connection, settings, disable) is rejected unavailable (cause 1 / 5, with the channel).
- **attach budget**: one attach answer takes at most 1000 ms (registry `limits.attach_budget_ms`) of the probe's time, the speed search and its retries included and
  the hold_ms of the reset TLV excluded. When no speed works within it, the answer is completed failed with status line.
- **scan budget**: the probe starts no combination later than 500 ms (`limits.scan_budget_ms`) after the scan request arrived (at least one combination is tried).
  The try of one combination is bounded by the attach budget. One scan answer therefore takes at most `scan_budget_ms` + `attach_budget_ms`.
- Both budgets are capped at max_op_ms. The host's wait counts them as argument time (core §4.4).
- **Number of connections that can be held at once**: a wire interface declares it with the max_connections of describe (tag 0x40, u8). If not declared, 1.
  The lock stays one per probe (there is no per-connection lock).
- **scan and live connections**: for the combination of a live connection, scan does not restart the wire from scratch; it returns it as a found combination using the values read over that connection (DMSTATUS etc.)
  (a scan does not break a running connection).
- **scan when the seats are full**: while max_connections connections are live, the only combinations scan can try are those of the live connections (trying another combination
  would mean taking the wire away from that connection). A request listing other combinations is rejected unavailable without executing anything. The count = 0 sequence consists of
  the combinations of the live connections only.
- **Seat rule**: an attach to a combination different from the live connections creates a new connection if a seat is free. If the seats are full, among the connections whose only user is
  a slot (not used by a host's session, [common parts](oep-if-common.md) §2), the oldest created one is closed to free a seat.
  If there is no such connection, rejected unavailable. Streams riding on the closed connection close just as when the connection is lost.
  Pin contention between different wire interfaces is refused as in core §8.1.
- **An attach to a wire that is already attached returns that connection as it is** (flags bit1). With method = 1, if running it halts,
  if halted it does nothing. method = 0 does not touch a running hart. If the existing connection is faster than max_speed,
  the probe lowers the speed of that connection to max_speed or below and returns it. A probe that cannot lower it treats it as a TLV value it cannot handle
  (core §2.3).
- `speed_hz` is the wire speed the probe selected (a guide: the reciprocal of one bit period).
- max_speed (TLV 0x01, u32 Hz): the probe does not select a speed above it. **Mandatory in attach** (rejected malformed if absent), sent
  critical. If smaller than the probe's min_clock_hz, rejected unsupported (tag 0x01). It can also be attached to scan (if absent, the probe tries at its slowest
  speed). pins and idle_clock are optional, and critical when sent.
- **What scan writes**: only the writes of items 1 and 2 of "Writes before the speed is verified", to read the identifier of "found". scan does not verify the
  write path and writes no scratch register. It may choose the speed by reads as attach does. dmactive is left set (same as §4.6. Clearing it may erase the console
  frames in DATA0). "Found" means DMSTATUS.version is 2 or more and not 15 (0 = no DM, 1 = a version this interface does not handle, 15 = a DM that does not
  conform). For swd, DPIDR could be read. The pins of combinations that were not found return to the idle state of core §8.
  A scan without max_speed tries at a slow speed the probe considers safe (it may do the same search as attach. For a wire like swd that cannot select by reading,
  a slow fixed value decided by the probe).
- **Target identifier**: after the attach answer, the probe may attach the target identifier it could read, as TLV 0x10 target_id (scheme(u8), value).
  scheme is how the identifier was obtained. The target_id scheme numbers are one space for the whole probe (registry `[common.enum.target_id_scheme]`:
  1 the u32 at DMI 0x7F of that debug module, 2 swd targetsel). Each wire states which schemes it uses. When the probe could not read it (including when the value is one the scheme defines as "none"),
  it does not attach it. The meaning of the value (which bits are the family, which the revision) is known to the host. The probe does not interpret it.
- **search_retries**: the attach answer of every wire may carry TLV 0x12 search_retries (u16, optional). A bring-up is the wire's wake / configuration sequence,
  choosing the speed and verifying it (above). search_retries is the number of extra attempts the bring-up needed beyond the first try of each of its steps,
  each of the following counted as 1:
  - a verification read, or a write and its read-back, that was repeated;
  - a pass that was repeated (a pass is a set of reads or write round trips at one speed that the probe judges as a whole);
  - a fall back to a slower speed after the write check failed at the chosen speed;
  - a repeat of the whole bring-up;
  - on a wire whose sequence has a wake, a wake that got no answer, before the one that did.

  A read that fails at a faster speed and so ends the search for a faster speed is not counted. 0 means every step succeeded at its first try. The value saturates
  at 0xFFFF (65535 or more). The probe sends it only when a bring-up ran for this attach: a new connection, an attach with the reset TLV, or an existing connection
  whose speed it lowered because of max_speed. It does not send it when the attach joins an existing connection without a bring-up. A host may log it to see a wire that
  is close to failing.

## 2. Lifetime of connections (all wires)

In addition to [common parts](oep-if-common.md) §2:

- **detach removes only the share of that host's session.** If there are other users, the connection does not close. With the detach TLV 0x01
  force (length 0, sent critical), it closes even if there are users.
- **A reset of the target does not close the connection.** The probe keeps it usable on the same connection after the reset (the per-wire procedure is in
  §4.6 and the other sections of the interfaces that handle targets).
- **Retries inside one request**: the probe spends at most 200 ms (registry `limits.wire_retry_ms`) of one request retrying the wire, retries at a slower speed
  included. When that is used up, it ends that request with status line. That alone does not decide wire loss. The speed search of attach (and of a scan combination)
  is bounded by the attach budget of §1 instead. The slow speed during retries is temporary and does not change the connection's speed_hz.
- **Wire loss**: the wire is lost when operations on a connection have failed with no answer from the wire (status line, inside requests or inside console reads)
  for **1000 ms of real time** (`limits.wire_lost_ms`), with no successful operation on that connection in between. The time the probe asserts reset or holds
  a reset line (the plan, the reset TLV of attach), and the 1000 ms after it releases it, are not counted. When the probe decides wire loss inside a request,
  it answers that request with status line, then closes the connection.
- **Wire loss is decided only inside a request or inside a console read** (idle connections are not monitored. The liveness check of at boot slots is
  [probe settings](oep-if-probe-config.md) §3.1). A status line alone does not mean that the connection closed: the host checks with connections.
  When decided inside a console read, a mark link-lost is attached and it closes.
- **Lines while the wire does not answer** (electrical safety): an exchange is one frame or packet that the wire's section defines, or one wake pattern, together with
  the line levels the section requires right before it. From an exchange that fails with no answer from the wire (the failures counted toward wire loss above) until
  an exchange on that wire succeeds, or until the connection is lost, the probe rests the wire's lines in the free state between exchanges and drives them only
  during an exchange (each retry is an exchange). The free state is undriven, with no pull or with a pull toward the line's rest level on that connection. For a
  clock line of a connection that uses idle_clock 1 (low), that is no pull or a pull-down, never a pull-up. When an exchange succeeds again, the probe restores the
  rest state of the connection (the clock line at the idle_clock level, and the data line's rest state: rvswd §3.1, swio §3.2, swd §5) before the next exchange. While exchanges succeed, the rest
  state between exchanges is the one the wire's section defines, unchanged by this rule.
- (Informative) Otherwise, a target that has lost power is powered back through the protection diodes of its pins by the lines the probe keeps driving.
- **When the probe closes a connection, it does not change the target's state more than necessary** (it does not reset the target. A hart that was halted is left as the
  host's last operation left it).
- When a connection closes, the channels of its combination go to the idle state of core §8 (the drive of idle_clock stops).

**The state machine of connection and hart**:

| Event | connection | hart | Streams |
|---|---|---|---|
| detach | Remove the share of that host's session. Close if no other user remains | Not touched | Close if the connection closes (mark closed 4) |
| detach(force) | Close (treated the same as when the wire was lost. An at boot slot retries) | Not touched | Close (mark detach, closed 4) |
| end / lease expiry / taken by force | Remove the session's share (core §9). Close if no other user remains; remains if a slot is using it | **Not touched** (if halted it stays halted. The host restores it with attach(method 0) + resume) | Remove the session's share (mark closed 2; a closed stream stays readable, [console](oep-if-console.md) §2) |
| Wire lost | Close | — | Close (mark link-lost, closed 4) |
| Self-reset of the target (havereset) | Keep (acknowledge, §4.6) | The target's state | Keep (mark restart 1) |
| attach of a later session while a slot keeps the connection | Joins the same connection (flags bit1) | As method says | The same stream if the same (connection, mechanism) |
| Probe reboot | Gone | The DM keeps dmactive | Gone |
- The probe's own automatic attach (a slot of `oep.probe.config`) is also one of the users, and a host's attach joins that connection
  (flags bit1).
- (Informative, safety) The end of a session (end, lease expiry, force) does not touch the hart: when a host dies with the hart halted, the target stays halted (unlike a debugger's
  detach, it does not start running), whatever the target was controlling. A host that wants the target to run after it leaves resumes it before end.

### 2.1 connections (list of connections)

```text
request: first(u8)
answer:  more(u8), count(u8), count × entry, [TLV]  (core §2.3)
entry:   connection(u16), swdio(u16), swclk(u16), speed_hz(u32), users(u8), slot(u8), tid_scheme(u8), tid_len(u8), tid
```

- Returns the live connections of that interface, in order of creation, from the first-th, as many as fit in one frame. more = 1 means there is more, and the host
  asks again with the number received added to first. Can be used without the lock.
- users: bit0 a host's session is using it, bit1 a slot is using it (the automatic attach or the console of a bind).
- slot is the slot number if the connection is a slot's connection (`oep.probe.config` §1.1), otherwise 0xFF.
- tid is the target_id that could be read at attach (if none, tid_scheme 0, tid_len 0). For swd, tid_scheme 2 = targetsel(u32) (0 if not multidrop),
  which distinguishes connections with the same pin combination and different targetsel. DPIDR is returned in the attach answer.

## 3. `oep.wire.rvswd` / `oep.wire.swio`

| op | Name | Request | Answer |
|---:|---|---|---|
| 0x01 | scan | count(u8), count × (swdio(u16), swclk(u16)), [TLV] | tried(u8), count(u8), count × (kind(u8), swdio(u16), swclk(u16), id(u32)), [TLV] |
| 0x02 | attach | method(u8: 0 do not halt / 1 halt. Others are rejected unsupported, payload `0x00`), [TLV] | connection(u16), id(u32), flags(u8), speed_hz(u32), [TLV] |
| 0x03 | detach | connection(u16), [TLV] | — |
| 0x04 | — | Reserved (formerly attach_under_reset. Became the reset TLV of attach) | |
| 0x05 | connections | first(u8) | §2.1 (no lock) |

- A swio combination has swclk = 0xFFFF (a single wire. swclk ≠ 0xFFFF is a combination the declaration does not allow, rejected unsupported as §1 says, in scan and attach alike). The kind of a scan entry on rvswd and swio is 1 (riscv-dm),
  and id is DMSTATUS. Their connections are used by `oep.target.riscv-dm` and `oep.target.console`.
- **The flags of attach** (common to the 3 wires, the registry's `attach_flags`): bit0 a pending havereset was acknowledged (riscv), bit1 existing connection,
  bit2 woken from dormant (swd), bit3 the hart is halted (the answer's TLV 0x11 dpc is valid).
- **Wake / configuration sequence** (§1 item 1): rvswd: the wake pattern (§3.1), then DMI 0x7E and DMI 0x7D each written 0x5AA50400, the pair twice.
  swio: DMI 0x7E and DMI 0x7D each written 0x5AA50400, the pair twice. The frames of both wires are §3.1 and §3.2.
- **Scratch** (§1): PROGBUF0 (DMI 0x20). Making it free: ABSTRACTAUTO (DMI 0x18) = 0, which is not restored (an autoexec left armed by an earlier session would run
  on each access).
- **attach while applying reset**: with the TLV 0x05 reset (critical: `channel(u16), hold_ms(u16)`), the probe holds the reset wire (channel) for
  hold_ms and then releases it. With method 1 it keeps issuing halt while releasing, to halt as early as possible (flags bit3, dpc TLV). **There is no guarantee of halting before the first
  instruction** (some execution happens between the release of the reset wire and the halt taking effect). When a guarantee of halting at the position right after
  reset is needed, use reset mode 2 of riscv-dm (release ndmreset while holding haltreq). With method 0 it attaches with the target running. An optional function, declared by role 3 (reset) of role_channels; a probe without it rejects a reset TLV unsupported (the tag as received, 0x85, core §2.3). An attach with the reset TLV to an existing connection
  resets that target and then returns the same connection (mark reset detail 3). hold_ms is
  subject to the core's max_op_ms.
- **There is no default reset wire**: which wire is used for reset is specified explicitly by the host every time with channel (a reset on the wrong wire could damage the target or the
  fixture). The channels the probe may use for reset are declared with role 3 (reset) of the role_channels of describe. An undeclared
  channel is rejected unsupported (the tag as received, 0x85) without executing anything. A channel held by an existing plan or connection is rejected
  unavailable as the contention of core §8.1. A channel whose idle is an output is rejected unavailable as §1 says. **The reset wire is pulled low open-drain, and when released it stops pulling and goes to the idle state of core §8** (no short with an external reset button or
  another driver). The channel is held only for the duration of the op. On a probe without it, the host sends the release of `oep.fixture.gpio` and the attach together
  and retries.

TLVs:

| op | tag | Name | Value |
|---|---:|---|---|
| scan | 0x01 | max_speed | u32 Hz (if absent, the probe's slowest speed) |
| scan (count = 0 only) | 0x02 | skip | u16. The number of combinations to skip from the start of the count = 0 sequence |
| scan (rvswd only) | 0x04 | idle_clock | u8. How to rest the wire during scan (below) |
| attach | 0x01 | max_speed | u32 Hz. **Mandatory**, critical |
| attach | 0x03 | pins | swdio(u16), swclk(u16). critical |
| attach (rvswd only) | 0x04 | idle_clock | u8. SWCLK while the wire rests: 0 = high (same as when absent), 1 = low. critical. Sending 1 to anything other than rvswd is rejected unsupported (tag 0x04) |
| attach | 0x05 | reset | channel(u16), hold_ms(u16). critical. Above |
| detach | 0x01 | force | Length 0. critical |
| attach answer | 0x10 | target_id | scheme(u8), value |
| attach answer | 0x11 | dpc | u32 (8 bytes for RV64). The dpc when the hart is halted (flags bit3) |
| attach answer | 0x12 | search_retries | u16, optional. §1 |

The schemes of target_id these wires use (`target_id_scheme`, one space for the probe, §1): 1 = the u32 read from DMI address 0x7F (length 4). 0 and 0xFFFFFFFF mean "none" (not attached).
2 = the targetsel of swd (u32, used only in the entries of connections. Not used for the lock). The length of the value per scheme is held in the registry
(used to verify the length of the mask / value of a slot's lock).

- **The wire settings are properties of the target, and the host holds them**: the upper limit of the wire speed (max_speed) and the way of resting (idle_clock) are what the target (chip)
  requires (a target may reset its debug logic when the clock rests at the wrong level, and may fail above some speed while it runs on its slow
  clock right after reset). The probe does not hold them as defaults. The host passes them at every attach, and a slot that attaches without a host
  holds the same values in the slot's item ([probe settings](oep-if-probe-config.md) §1.1). scan accepts the same TLVs (to find such
  targets with scan without breaking them).
- If an attach to an existing connection carries an idle_clock different from the current one, the probe changes the resting of that connection and returns it. A probe that cannot change it
  treats it as a TLV value it cannot handle (core §2.3).

### 3.1 RVSWD frames

The wire has two lines, SWDIO (pin role 1) and SWCLK (pin role 2). The probe always drives SWCLK. It drives SWDIO except during the data of a read, and while the
wire is in use it keeps a pull-up on SWDIO, so that the line reads high when neither side drives it.

**Bit cells.** T is the half period. One bit cell is SWCLK low for T, then SWCLK high for T.
- A bit the probe sends: the probe sets SWDIO at the falling edge of SWCLK that starts the cell (both lines change together) and holds it until the next falling edge.
  The target samples it at the rising edge.
- A bit the target sends: the target sets SWDIO after the falling edge. The probe samples SWDIO at the end of the low half, just before the rising edge.

**Conditions** (SWDIO changes while SWCLK is high only here):
- START: both lines high for at least T, then SWDIO falls while SWCLK stays high. The first bit cell starts T later.
- STOP: a bit cell with SWDIO low, then SWDIO rises while SWCLK stays high. Both lines then stay high for at least T.

**Frame**: one DMI access. Values are sent most significant bit first. A frame has 53 bit cells.

| Field | Cells | Driven by | Value |
|---|---:|---|---|
| START | — | probe | |
| address | 7 | probe | The DMI address |
| direction | 1 | probe | 1 write, 0 read |
| header parity | 1 | probe | Makes the number of ones in address, direction and this bit even |
| aux 1 | 5 | probe | 1, 0, 1, 0, 1 |
| data | 32 | probe (write), target (read) | The 32-bit value |
| data parity | 1 | the same side as data | Makes the number of ones in data and this bit even |
| aux 2 | 5 | probe | 1, 0, 1, 1, 1 |
| STOP | 1 | probe | The bit cell with SWDIO low of STOP |

- **Turnaround** (read): the probe stops driving SWDIO after the rising edge of the last cell of aux 1, while SWCLK is high, and the first data cell follows with no
  extra cell. After the rising edge of the data parity cell the probe drives SWDIO high again, and aux 2 follows with no extra cell. The target drives SWDIO only
  during the 33 cells of data and data parity.
- A read whose data parity does not match is a failed read (retried as §2 says). A write has no acknowledgement: the write path is checked only by reading back (§1).
- **Resting** (between frames): with idle_clock 0 both lines stay high. With idle_clock 1 SWCLK is low and SWDIO high, both driven by the probe. A frame starts from both
  lines high: with idle_clock 1, SWCLK rises with SWDIO high at least T before START.

**Wake pattern** (the first part of the wake / configuration sequence, §3):

1. both lines driven high for at least 20 µs;
2. 100 bit cells with SWDIO high;
3. 1 bit cell with SWDIO low;
4. SWDIO rises while SWCLK is high (a STOP condition);
5. both lines high for at least 20 µs before the first frame.

- **Speed of the wake / configuration sequence**: T is at least 500 ns and at least 1 / (2 × max_speed). When the probe writes dmactive (§1 item 2), it may write the
  configuration pair (DMI 0x7E, then DMI 0x7D) twice again right after it, at the same T. These writes are part of the wake / configuration sequence.
- **Choosing the speed**: the probe chooses T by DMSTATUS reads only (§1), from that slowest T towards shorter ones, and never shorter than 1 / (2 × max_speed). It then
  checks the write path at the chosen T with the scratch register (§3).
- **Losing the wire inside a request**: the target may lose the link while the bus rests. A probe that cannot bring the wire back within a request answers status
  line, as §2 says.
- (Informative) The reference probe's way back: before the first frame after a rest of 300 µs or more, it reads DMSTATUS. If that read fails, or DMSTATUS is not
  "found" (§1) with bit 7 (authenticated) set, it sends the configuration pair twice (without the wake pattern) and reads DMSTATUS again. If that still fails, it
  retries as §2 says, and while it retries it may send the whole wake / configuration sequence.
- (Informative) The wake pattern may reset the target as well as its debug interface. The reference probe sends it only when it brings up a wire that does not answer,
  not when it re-synchronises. It accepts a T when 1000 consecutive DMSTATUS reads return the same value with a matching parity, and its writes when 256 write and
  read-back round trips on the scratch register match.
- (Informative) At connect, another debugger may also send a longer form of the status query, 85 bit cells long. A probe need not send it. Someone decoding a
  capture should not read it as an error.

### 3.2 SWIO frames

The wire has one line, SWDIO (pin role 1). It rests high. When the probe sends, it drives the line both high and low. While the wire is in use the probe keeps a
pull-up on the line. Between frames the line rests high, either driven high by the probe or released to that pull-up; the probe may drive it high there only while the target answers. From a failed exchange on, it releases the line to the pull-up and does not drive it high (§2, the lines while the wire does not answer).

**Bit cells the probe sends**: the line low, then high.

| Cell | Low | High after it |
|---|---|---|
| 1 | 240 to 310 ns | 240 to 270 ns |
| 0 | 840 to 1060 ns | 240 to 270 ns |

- The recommended lows are 262 ns for a 1 and 862 ns for a 0.
- (Informative) The low ranges were measured to work on one target family; the target's own limits are not known.

**Bit cells the target sends** (read cells): the probe drives the line low for 240 to 270 ns, then stops driving it. The target sends 0 by holding the line low,
and 1 by leaving it to rise. The probe samples the line 520 to 600 ns after the falling edge it made (high = 1, low = 0). It then waits until the line reads high
again. If the line does not read high within 100 µs, the read fails. Once the line is high the probe drives it high for at least 130 ns before the next cell.
After it stops driving the line low, and again after a sample of 0, the probe may drive the line high for at most 30 ns at a time (a recharge pulse, to shorten
the rise through the pull-up).

**Frame**: one DMI access, most significant bit first, 41 cells:

- write: START (a 1 cell), the 7-bit DMI address, the direction 1, then 32 data cells sent by the probe;
- read: START (a 1 cell), the 7-bit DMI address, the direction 0, then 32 read cells.

- There is no parity, acknowledgement or stop. A read detects only a line that does not come back high; a wrong bit is not detected.
- The probe keeps every cell of a frame within the times above (nothing may interrupt a frame). After a frame the line stays high for at least 8 µs before the next
  frame.
- **Speed**: the bit timing is fixed, so the probe does not choose a speed. It declares, with min_clock_hz of describe, the rate of a 0 cell (1 / (its low + its
  high)). A max_speed below it is rejected unsupported (§1).
- (Informative) Before the first frame of an attach, the reference probe leaves the line to its pull-up for 2 ms, and finds no target if the line then reads low.

## 4. `oep.target.riscv-dm`

Requests start with connection(u16).

- **The mandatory ops are dmi, halt, resume.** reset, read_block, write_block, run and step are optional and declared by ops of describe
  (core §1.2, §7.4); read_block and write_block are offered together. riscv-dm declares no features. A probe answers an op it does not offer with unknown_operation (core §1.2). The host can build the same thing with dmi even without the
  optional ops.
- **Scope of the ops other than dmi (the high-level ops)**: they handle hart 0 of RV32 only (addresses, register values, pc are u32). Inside a high-level op the probe
  sets the hartsel of DMCONTROL to 0 and **returns with it set to 0** (a hartsel selected by the host with dmi lasts only within that dmi request). Other harts and RV64 are
  handled by the host with dmi (DMI values being u32 is the form of DMI, and does not mean a restriction to RV32). RV64 addresses are added later with the
  critical TLV 0x01 `address_hi(u32)` of read_block / write_block (reserved. The registry's reserved).
- The riscv-dm ops treat every DMSTATUS.version that scan accepts (§1) the same way.

**Invariant at op boundaries**: **the probe carries no target state across an op after returning its answer.** What was used inside the op is restored before the answer.
Whatever the host does with raw DMI (the dmi op), and even if the host dies midway (lease expiry, force), there is nothing the probe forgets to restore.

| op | What the probe touches | Before the answer |
|---|---|---|
| halt | haltreq | Checks allhalted. **haltreq may be left set while halted** (whether to keep or clear it is decided by the probe; the behaviour visible to the host is the same. Keeping it helps a target whose debug link drops when the hart's state changes; on such a target a read right after halt can return the previous value). Cleared on resume / step / reset / detach and when the connection closes. When halt times out, it is cleared before the answer (§4.2) |
| resume | haltreq = 0, resumereq = 1 once | Remembers nothing, restores nothing |
| step | dcsr.step, DATA0 / DATA1 (reading and writing dcsr), haltreq | Clears dcsr.step, restores DATA1, DATA0, clears haltreq. If the hart cannot be halted again, the answer says step_left (§4.2) |
| reset | haltreq, ndmreset, acknowledging havereset | Acknowledges havereset. mode 0 / 1 clear haltreq. mode 2 stays halted and may keep haltreq like halt. The internal halt of mode 1 is restored like step |
| read_block / write_block | GPRs (s0, s1, a0, a1), DATA1 / DATA0, abstractauto, program buffer, sysbus | Restores GPRs, DATA1, DATA0, abstractauto. The program buffer and SBCS / SBADDRESS are not restored (the host sets them again if it uses them) |
| run | pc, the GPRs the host specified, dcsr (ebreakm, prv), haltreq | **Returns with them changed as the host instructed** (the host's responsibility). abstractauto and haltreq are restored |
| dmi | What the host wrote | Touches nothing, restores nothing (if the host used DATA, the host restores it) |
| Console read (§4.6) | DATA0 / DATA1 | Does not read while the hart is halted |

The restored value is the "value before touching" read inside that op. The upper limit for waiting on DM state inside a high-level op (abstractcs.busy clearing, allhalted, allresumeack)
is 100 ms per wait (registry `dm_wait_ms`). The status when it is exceeded is as in each op's section (halt is timeout, resume / step are state). DMI busy is
retried up to 100 times inside the probe (`dmi_busy_retries`), and when used up, status wait (same as the WAIT of §6).

| op | Name | Request (after connection) | Answer |
|---:|---|---|---|
| 0x01 | dmi | n(u16), n steps | done(u16), status(u8), nvals(u16), nvals × value(u32), [TLV] |
| 0x02 | halt | — | status(u8), [TLV] |
| 0x03 | resume | — | status(u8), [TLV] |
| 0x04 | reset | mode(u8), [TLV] | status(u8), flags(u8), attempts(u8), pc(u32) (dpc in mode 2), [TLV] |
| 0x05 | read_block | address(u32), count(u16), [TLV] | done(u16), status(u8), done × word(u32), [TLV] |
| 0x06 | write_block | address(u32), count(u16), count words, [TLV] | done(u16), status(u8), [TLV] |
| 0x07 | run | pc(u32), timeout_ms(u32), n(u8), n × (regno(u16), value(u32)), n_out(u8), n_out × regno(u16), [TLV] | status(u8), stopped(u8), dpc(u32), elapsed_us(u32), nvals(u8), nvals × value(u32), [TLV] |
| 0x08 | step | — | status(u8), moved(u8), dpc_before(u32), dpc_after(u32), [TLV] |

Empty results and edge values: n = 0 of dmi and count = 0 of read_block / write_block are success, done 0. An address that is not a multiple of 4 is rejected
malformed. max_reads / max_us = 0 of dmi reads once. timeout_ms = 0 of run is rejected malformed. If the same regno appears twice in n_out,
it is returned twice as is. write_block / read_block on a hart that is not halted is status state.

### 4.1 dmi

| kind | Step | Arguments | Value added to the answer |
|---:|---|---|---|
| 0x01 | Write | address(u8), value(u32) | — |
| 0x02 | Read | address(u8) | The value read (u32) |
| 0x03 | Wait up to a number of reads | address(u8), mask(u32), value(u32), max_reads(u16) | The last value read (u32) |
| 0x04 | Wait | wait_us(u32) | — |
| 0x05 | Wait up to a time | address(u8), mask(u32), value(u32), max_us(u32) | The last value read (u32) |

- kinds 0x10 to 0x1F are reserved for the same steps with a u32 address. Since the length of an unknown kind is unknown, the whole request is rejected
  malformed (the probe verifies all the steps before executing).
- **done is the number of steps completed** (on failure, the 0-based index of the failed step). Only 0x02 / 0x03 / 0x05 add values.
  `nvals` is the number of values in the answer (the number of value-adding steps among the first done steps, plus 1 if the failed step was 0x03 / 0x05 that ran out of waiting
  (status timeout)). A step that failed without being able to read, because of a wire fault or the like, adds no value.
- The sum of the wait_us of 0x04 steps and the max_us of 0x05 steps must not exceed max_op_ms (rejected unsupported). 0x03 steps are bounded by their count, not by time.
  If a request reaches max_op_ms while running, the probe ends it at that step with status timeout (done = the index of that step).
- One request is an operation on one hart. Things that need timing and re-establishing of the wire (reset, recovery) are made into component ops.
- **The host puts a whole abstract-command sequence (writing data1 / data0, command, reading data0) into one dmi request** (so that it is not broken even if the probe
  inserts a console read between requests. `oep.target.console` §3).

### 4.2 halt, resume, step

- **halt** does nothing and returns ok if already halted. If allhalted is not seen within 100 ms, the probe clears haltreq and answers status timeout.
- **resume** writes haltreq = 0, resumereq = 1 once. ok means "the hart left debug mode", decided by the allresumeack of DMSTATUS (or
  allrunning and not halted). resumereq is not reissued. If not seen after waiting 100 ms, status state.
  - (Informative) For some targets this is not enough (a target that does not set allresumeack may immediately halt again at a breakpoint, or may not leave with one
    resumereq). Handling that (reading dpc and resuming again if it is not moving, etc.) is done by the host that knows the target.
- **DATA0 / DATA1 belong to the target**: if the probe uses DATA0 / DATA1 with an abstract command (read_block etc.) while the hart is halted,
  the word the target had placed there (a console frame or answer of dmseq etc.) is lost, and after resume the console stalls until the target posts its frame
  again under its mechanism's rules. Therefore an op that uses DATA0 / DATA1 restores them **before its own answer** (the table of
  §4). The probe remembers nothing across ops.
- **step** sets dcsr.step, issues resume exactly once, and clears dcsr.step when it returns. It is not a failure if dpc does not move (status ok, moved = 0. An instruction that jumps to
  itself leaves dpc the same even when it executed correctly, so the host reads the instruction and decides). prv is not changed.
  If the hart does not return to debug mode within 100 ms, the probe sets haltreq and waits up to 100 ms more. If the hart halts, it clears dcsr.step, restores
  DATA1 / DATA0, and answers status state with dpc_after valid. If it does not halt, it clears haltreq and answers status state with answer TLV 0x01 step_left
  (length 0): dcsr.step may still be set and the hart is running. The host halts it and clears dcsr.step.

### 4.3 reset

| mode | Meaning |
|---:|---|
| 0 | Run |
| 1 | Run and verify execution |
| 2 | Halt before the first instruction (release ndmreset while holding haltreq) |

Answer:

| Field | Meaning |
|---|---|
| flags bit0 | The state of the requested mode was reached (mode 0 / 1 running, mode 2 halted) |
| flags bit1 | Execution was verified by reading pc (mode 1 only) |
| flags bit2 | The reset procedure was redone |
| flags bit3 | The halt / resume for verification failed |
| attempts | The number of reset procedures performed (from 1) |
| pc | The pc verified in mode 1, dpc in mode 2. Otherwise 0 |

- The condition for outcome success is flags bit0 in modes 0 and 2, bit1 in mode 1. If not met, completed failed (same form. status is
  does not halt / does not run = timeout, the DM does not answer = line, cmderr = fault). The upper limit for waiting for the hart to halt / run after releasing ndmreset is
  100 ms per procedure, and the procedure is redone (flags bit2) at most once.
- The other bits of flags are 0. After the reset, havereset is acknowledged and haltreq is cleared (mode 2 stays halted).
- A mode of 3 or more is rejected unsupported (payload `0x00`. A later revision may define it, core §2.5).

TLV 0x01 method (u8): 0 the probe's default, which in revision 1 is ndmreset; 1 ndmreset. 2 is reserved (there is no common procedure for a target's system reset, so the host builds it with
dmi). A method of 2 or more is a value this probe cannot handle (core §2.3: rejected unsupported when sent critical, otherwise ignored). **The reset op never drives a reset line**: a reset line moves only through the reset TLV of attach (§3) or through the host's own use of a fixture interface.

### 4.4 run

- For calling the host's loader. The probe sets the ebreakm and prv = M of dcsr, runs from pc, and waits for it to stop. **The probe does not reissue
  run** (even if the stopped position is still the start position, it cannot be told from having run and returned). Whether it did not run is decided by the host from dpc,
  and it retries only when the loader may be run twice. **Not used for a debugger's continue** (it changes prv and ebreakm).
- timeout_ms is 1 to the core's max_op_ms (0 is rejected malformed, exceeding it is rejected unsupported). Until it returns the answer to run, the probe does not answer other requests on this
  connection (the lease is not counted during execution, core §6.1. Console reads of other connections continue).
  When it stops, stopped = 1 (success). When the limit is reached, the probe halts the hart, then reads dpc and the values, and returns stopped = 0, status timeout, outcome
  failed (dpc and the values are all valid). If it cannot halt it, stopped = 2, status timeout, outcome failed, nvals = 0 (dpc is invalid).
  The form of the answer is always the same (`run_stopped`: 0 halted by timeout, 1 stopped, 2 could not be halted).
- regno is the RISC-V abstract register number (a0 = 0x100A).

### 4.5 read_block, write_block

- In units of words (32 bit). 8 / 16-bit accesses are built from dmi steps.
- **Length per request**: a probe that has read_block / write_block always emits the common tag max_length of describe (core §7.4). The unit is **number of bytes**
  (a multiple of 4). The probe declares max_length as a value such that both the read_block answer (header 5 + done 2 + status 1 + words) and the write_block request (header 10 +
  connection 2 + address 4 + count 2 + words) fit within its own max_frame (max_frame − 24 or less, registry `block_frame_overhead_bytes`. It may declare smaller). The host decides count from
  max_length, not by calculating from max_frame. If count × 4 exceeds max_length, rejected unsupported (payload `0x00`). count = 0 is
  success, done 0. An address that is not a multiple of 4 is rejected malformed.
- **Meaning of a read**: read_block reads through the target's bus. The probe keeps no copy on its side (it reflects what the target wrote in the preceding write_block, dmi, run).
  Only the probe's side is guaranteed; the image of the target's own cache or prefetch is out of scope (the side of the host's chip knowledge).
- **Prerequisite**: the hart is halted (if not halted, status state). The address is the one the halted hart uses in M mode.
  (Informative) Reading while the hart runs (a debug module with system bus access can) may be added later with a features bit and an optional TLV, without changing the revision (core §2.7).
- **Side effects**: the probe may use GPRs, the program buffer, the DATA registers, and sysbus. However, **before returning the answer, it restores the GPRs, DATA1,
  DATA0 and abstractauto it used to their values before use** (the table of §4). Even if the host saves nothing, halt → read_block → resume leaves the target's state
  unchanged. Without restoring, depending on where it stopped, the target would keep running with corrupted registers. Restoring at resume time fails when the host's raw DMI
  comes in between. The program buffer and SBCS / SBADDRESS are not restored (the host sets them again if it uses them).
- run (§4.4) runs the host's loader with the registers the host specified, and the GPRs and dcsr changed during it are not restored (the host's responsibility).

### 4.6 Handling of RISC-V connections

- attach first acknowledges a pending havereset (some DMs freeze the halt / running of DMSTATUS until acknowledged).
- After a target reset (the reset op, the reset TLV of attach), the probe acknowledges havereset and keeps the same connection.
- **On seeing havereset** (whether inside a request or inside a console read), acknowledge it, return the dmseq state of the console to unsynchronised, and attach a mark restart (detail 1)
  to the streams of that connection.
- **The probe does not reset the debug module even when closing a connection** (it leaves dmactive and clears haltreq etc.). Resetting may
  erase the dmseq frame in DATA0, and the console then waits until the target posts it again (within a short wait, [dmseq](target-console-dmseq.md)).

## 5. `oep.wire.swd`

| op | Name | Request | Answer |
|---:|---|---|---|
| 0x01 | scan | count(u8), count × (swdio(u16), swclk(u16)), [TLV] | tried(u8), count(u8), count × (kind(u8), swdio(u16), swclk(u16), id(u32)), [TLV] |
| 0x02 | attach | method(u8: 0 only. Others are rejected unsupported, payload `0x00`), [TLV] | connection(u16), id(u32), flags(u8), speed_hz(u32), [TLV] |
| 0x03 | detach | connection(u16), [TLV] | — |
| 0x04 | — | Reserved | |
| 0x05 | connections | first(u8) | §2.1 (no lock) |

- The kind of scan is 2 = arm-adi, id is DPIDR. The forms of request and answer are the same as §3 (one form for the 3 wires).
- The TLVs use the same numbers as §3: scan 0x01 max_speed, 0x02 skip, 0x06 targetsel (below). attach 0x01 max_speed (mandatory), 0x02 targetsel,
  0x03 pins, 0x05 reset (optional, as §3). detach 0x01 force. attach answer 0x10 target_id, 0x12 search_retries (§1).
- **How the speed is selected**: SWD cannot select the speed by reading, so it starts at `min(max_speed, the max_clock_hz of describe)`.
- **Wake / configuration sequence** (§1 item 1): the JTAG-to-SWD switch, the dormant wake, and TARGETSEL when one is given. swd names no scratch register.
- attach tries the switch from JTAG to SWD, and if there is no answer wakes it from dormant (flags bit2). Power-up (the CDBGPWRUPREQ /
  CSYSPWRUPREQ of CTRL/STAT) is done by the host with DP writes. In the retries of §2, the line reset and the wake from dormant are redone.
- **Lines and packets**: the wire has two lines, SWDIO (pin role 1) and SWCLK (pin role 2), and uses the SWD protocol of the Arm Debug Interface (ADIv5 / ADIv6).
  The probe always drives SWCLK. A packet is one SWD packet of that protocol: the request, the acknowledgement and the data phase the protocol gives it, with their
  turnaround cycles. Each packet, and each of the line reset, the JTAG-to-SWD switch and the dormant wake sequences, is one exchange of §2.
- **Who drives SWDIO**: the target drives SWDIO only in the acknowledgement and read-data phases, with the turnaround cycles as the protocol defines. The probe
  drives it at all other times, except in the free state of §2.
- **Idle cycles**: after every packet, and after each of the sequences above, the probe clocks at least 8 idle cycles: clock cycles with SWDIO driven low by the
  probe. They are part of that exchange (§2).
- **Rest state** (between exchanges): SWDIO driven low by the probe and SWCLK driven high.
- **Before the probe stops driving the lines** (when a detach or anything else closes the connection, when the probe releases the pins, or for the free state of
  §2 "Lines while the wire does not answer"), it clocks the 8 idle cycles after the last packet, so that the target completes that packet.
- **targetsel (TLV 0x02, u32) is sent critical** (only for multidrop. If ignored, it would attach to a different target). **The identity of a connection
  includes targetsel.** An attach whose targetsel (including none) differs from a live connection with the same pin combination is rejected unavailable
  (the host detaches first). If the same, that connection is returned as is. scan tries without targetsel (multidrop targets that require TARGETSEL
  do not appear in scan. One can be specified and tried with the TLV 0x06 targetsel of scan).
- **Intended asymmetry** (revision 1): arm-adi has no halt / resume / step / reset / run (the host builds them with transfer). Slots, locks and consoles do not ride on an swd connection
  (swd cannot be used as the wire_fn of a slot of `oep.probe.config`, and a console open on an swd connection is
  rejected unavailable cause 6). The tid of an entry of connections is scheme 2 (targetsel) and is not used for the lock.

## 6. `oep.target.arm-adi`

Requests start with connection(u16). All three ops are required (all set in ops). arm-adi has no optional op and declares no features.

| op | Name | Request (after connection) | Answer |
|---:|---|---|---|
| 0x01 | transfer | n(u16), n transfers: req(u8: bit0 APnDP, bit1 RnW, bit2-3 A[3:2], bit4-7 are 0) and, for a write, value(u32) | done(u16), status(u8), ack(u8), nvals(u16), nvals × value(u32), [TLV] |
| 0x02 | read_block | address(u32), count(u16), [TLV] | done(u16), status(u8), done × word(u32), [TLV] |
| 0x03 | write_block | address(u32), count(u16), count words, [TLV] | done(u16), status(u8), [TLV] |

- ack is the raw ACK of the last transfer (`swd_ack`: bit0 is first in wire order. OK = 1, WAIT = 2, FAULT = 4. No response is status line). If bit4-7 of req are
  not 0, rejected malformed (req decides the length of the transfer's arguments, so an unknown req leaves the rest of the request unreadable, as an unknown dmi kind does). nvals is the number of values read (the number of reads among the first done transfers).
- transfer is a raw transfer, and the one-transfer delay of AP reads is passed through as is (the host receives it with RDBUFF or the next AP read).
  WAIT is retried up to 100 times inside the probe (registry `swd_wait_retries`), and when used up, status wait. It stops on FAULT, so the host clears the sticky bits with ABORT.
- The length per request and the meaning of a read of read_block / write_block are the same as riscv-dm (§4.5): the max_length of describe (number of bytes, a multiple of 4, a value such that both request and answer
  fit in max_frame) is always emitted, and if count × 4 exceeds it, rejected unsupported (payload `0x00`). The host decides count from
  max_length. read_block reads through the target's bus and the probe keeps no copy on its side.
- read_block / write_block use the TAR / DRW of the current MEM-AP. SELECT and CSW (32 bit, single increment) are set by the host beforehand. The probe
  rewrites TAR at every 1 KiB boundary (registry `tar_rewrite_bytes`) and reorders the reads that lag by one. **The state of the hart does not matter** (the MEM-AP can be read while running).
  **done is the number of words the probe sent**, not a guarantee that the target accepted them (a FAULT of a posted write is seen in a later transfer). TAR is left advanced, and
  SELECT / CSW are not changed (the arm version of the invariant of §4: the probe does not change what the host set). 64-bit AP addresses are added later with the same
  TLV 0x01 `address_hi` as riscv-dm (reserved).

## 7. References

The OEP messages of this document are defined by the text alone; the frames of RVSWD and SWIO are defined in §3.1 and §3.2. Driving a target uses:

| Interface | Specification | Subset used |
|---|---|---|
| `oep.wire.swd`, `oep.target.arm-adi` | Arm Debug Interface Architecture Specification, ADIv5.2 and ADIv6.0 | SWD packets, turnaround, line reset, the JTAG-to-SWD switch, the dormant wake, TARGETSEL; the DP and AP registers; MEM-AP TAR, DRW and CSW |
| `oep.wire.rvswd`, `oep.wire.swio`, `oep.target.riscv-dm` | RISC-V Debug Specification 0.13.2 and 1.0 (DMSTATUS.version 2 and 3) | The DMI registers (DMCONTROL, DMSTATUS, ABSTRACTCS, COMMAND, ABSTRACTAUTO, DATA0, DATA1, PROGBUF0, SBCS, SBADDRESS), abstract commands, the program buffer, dcsr, dpc, havereset |
