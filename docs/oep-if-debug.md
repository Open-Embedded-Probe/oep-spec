# OEP standard interfaces: wire and debug v1

[日本語](oep-if-debug.ja.md)

Status: **normative** (2026-09-26. Reflects the [zero-base re-examination](v1-zero-base-proposal.ja.md) (Japanese) of 2026-10-01). The core is [OEP core](oep-core.md), the common parts are [common parts](oep-if-common.md) (§2 debug
connections, §3 status). The only definition of the numbers is `registry/oep-v1.toml`. The reasons for the placement of names are in
[hierarchy of capability names](capability-name-hierarchy.ja.md) (Japanese).

| Name | revision | Role |
|---|---:|---|
| `oep.wire.rvswd` | 1 | Connects to a RISC-V DM over the 2-wire RVSWD |
| `oep.wire.swio` | 1 | Connects to a RISC-V DM over the 1-wire SWIO |
| `oep.wire.swd` | 1 | Connects to ADI over ARM's SWD |
| `oep.target.riscv-dm` | 1 | Operations on a RISC-V Debug Module |
| `oep.target.arm-adi` | 1 | Operations on ARM ADI (DP / AP) |

(Reference) RVSWD and SWIO are the 2-wire and 1-wire debug wires of WCH's RISC-V MCUs; the registry name `wch_dmi_7f` of target_id scheme 1 also comes from WCH's debug module.

- `oep.wire.*` creates connections, and `oep.target.*` operates on the target over a connection. The interfaces that handle targets
  appear in list before attach, and a request without a connection is rejected no_connection.
- **The target's family (the chip type) is not declared.** Per-chip knowledge (how to write flash, the quirks of the DM) is held by the host.
- Every op other than connections requires the lock.

## 1. Rules for attach (all wires)

- The probe does not write to the target until it has finished verifying the wire speed (it selects the speed by reading only). A write at a mismatched speed could write
  a garbled value into a target register.
- **Pin combinations**:
  - The combinations the probe can use are declared with the common tags of describe (core §7.4). Fixed combinations with channel_group; if any pin can be assigned,
    with role_channels. The role numbers are `pin_role` (1 = SWDIO, 2 = SWCLK, 3 = reset).
  - The scan request is the sequence of combinations to try. **count = 0 means every combination the probe allows.** The combinations in the answer can be passed to the pins of attach as they are.
  - On a wire declared with role_channels, the allowed combinations are "candidates of role 1 × candidates of role 2 (a 1-wire has role 1 only), not using the same channel
    twice". The count = 0 sequence is in ascending order of swdio, then ascending order of swclk within it, and **combinations containing a channel currently held by something else (a plan, the connection of another wire,
    a settings resource) are not listed** (count = 0 tries only the combinations that may be driven). If a request listing combinations contains a held
    channel, the whole request is rejected unavailable as in §8.1.
  - **Channels with an idle item**: the count = 0 sequence and the candidates of an attach without pins leave out every channel that has an **idle item**
    in the probe's settings (any mode, [probe settings](oep-if-probe-config.md) §1), in addition to channels held by something else and disabled channels.
    A request that names such a channel explicitly (a scan listing combinations, the pins of attach) is accepted when the idle is an input (mode 0 to 2).
    It is rejected unavailable (cause 5, the channel, holder_kind 7 = settings idle) when the idle is an output (mode 3 / 4).
  - (Informative) count = 0 drives every free candidate pin in turn. Without the user's consent, a host does not send count = 0 to a fixture whose wiring it does not know.
  - A wire holds the channels of the combination a live connection is using (released when the connection is gone). While held, if a plan or the settings tries
    to take that channel, rejected unavailable (core §8.1).
  - The `tried` of the scan answer is the number of combinations tried from the start of the request's sequence (for count = 0, the count = 0 sequence above. On a channel_group wire, the order emitted in describe).
    At most 255 combinations are tried in one go (tried is u8). If the found combinations would make the answer no longer fit in one frame,
    the probe stops there. **The probe also stops where the scan budget (below) does not let it start the next combination**
    (at least one combination is tried). If tried ≥ 1, the host sends the continuation. If a request listing combinations returns tried smaller than the number listed, the host sends scan again with the remaining combinations.
  - **Continuing count = 0**: a count = 0 request can pass, in the TLV skip (0x01, u16), the number of combinations to skip from the start of the count = 0 sequence (0 if absent).
    The host continues by passing the sum of the tried values so far in skip, and **stops when tried = 0 is returned**. **If combinations remain in the sequence, the probe tries at least 1**
    (tried ≥ 1. tried = 0 only when the sequence is used up). Since the sequence is determined by what is held at the time of the request,
    if a plan or the like changes midway, combinations may be skipped or repeated (the host changes nothing else during a scan). A request with count > 0 and skip
    is rejected malformed.
  - attach specifies the combination with pins (TLV 0x03, critical). If pins is absent: if that wire has exactly one live connection, that combination
    (joining the existing connection. A connection held by a slot is fine too); if there is no live connection and exactly one allowed combination, that combination;
    otherwise (2 or more live connections, or no connection and 2 or more allowed combinations) rejected unavailable (the host chooses).
  - **A combination that is not allowed is rejected unavailable without executing anything** (scan refuses the whole request if even one is in it).
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
- **The only thing scan writes to the target is dmactive** (to read DMSTATUS). dmactive is left set (same as §4.6. Clearing it erases the console frames in
  DATA0). "Found" means DMSTATUS.version is 2 or 3 (for swd, DPIDR could be read). The pins of combinations that were not found return to the idle state of core §8.
  A scan without max_speed tries at a slow speed the probe considers safe (it may do the same search as attach. For a wire like swd that cannot select by reading,
  a slow fixed value decided by the probe).
- **Target identifier**: after the attach answer, the probe may attach the target identifier it could read, as TLV 0x10 target_id (scheme(u8), value).
  scheme is how the identifier was obtained, defined by the registry per wire. When the probe could not read it (including when the value is one the scheme defines as "none"),
  it does not attach it. The meaning of the value (which bits are the family, which the revision) is known to the host. The probe does not interpret it.
- **search_retries**: the attach answer of every wire may carry TLV 0x12 search_retries (u16, optional): the number of tries of the speed search that failed
  before the speed in speed_hz was verified (0 = the first try worked; 0xFFFF = 65535 or more). A host may log it to see a wire that is close to failing.

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
- **When the probe closes a connection, it does not change the target's state more than necessary** (it does not reset the target. A hart that was halted is left as the
  host's last operation left it).
- When a connection closes, the channels of its combination go to the idle state of core §8 (the drive of idle_clock stops).

**The state machine of connection and hart**:

| Event | connection | hart | Streams |
|---|---|---|---|
| detach | Remove the share of that host's session. Close if no other user remains | Not touched | Close if the connection closes (mark closed 4) |
| detach(force) | Close (treated the same as when the wire was lost. An at boot slot retries) | Not touched | Close (mark detach, closed 4) |
| end | Nothing changes (the resources move to the next session, core §9) | Not touched | Unchanged |
| Lease expiry / taken by force | Remove the session's share. Remains if a slot is using it | **Not touched** (if halted it stays halted. The host restores it with attach(method 0) + resume) | Remove the session's share (mark closed 2) |
| Wire lost | Close | — | Close (mark link-lost, closed 4) |
| Self-reset of the target (havereset) | Keep (acknowledge, §4.6) | The target's state | Keep (mark restart 1) |
| attach of a second session | Joins the same connection (flags bit1) | As method says | The same stream if the same (connection, mechanism) |
| Probe reboot | Gone | The DM keeps dmactive | Gone |
- The probe's own automatic attach (a slot of `oep.probe.config`) is also one of the users, and a host's attach joins that connection
  (flags bit1).

### 2.1 connections (list of connections)

```text
request: first(u8)
answer:  more(u8), count(u8), count × (len(u8), entry), [TLV]  (core §2.3)
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
| 0x01 | scan | count(u8), count × (swdio(u16), swclk(u16)), [TLV] | tried(u8), count(u8), count × (len(u8), kind(u8), swdio(u16), swclk(u16), id(u32)), [TLV] |
| 0x02 | attach | method(u8: 0 do not halt / 1 halt. Others are rejected malformed), [TLV] | connection(u16), id(u32), flags(u8), speed_hz(u32), [TLV] |
| 0x03 | detach | connection(u16), [TLV] | — |
| 0x04 | — | Reserved (formerly attach_under_reset. Became the reset TLV of attach) | |
| 0x05 | connections | first(u8) | §2.1 (no lock) |

- A swio combination has swclk = 0xFFFF (a single wire. swclk ≠ 0xFFFF in scan is rejected malformed). The kind of scan is `scan_kind`: 1 = riscv-dm,
  2 = arm-adi. `id` is the raw identifier determined by the kind of wire (DMSTATUS for riscv-dm, DPIDR for arm-adi).
- **The flags of attach** (common to the 3 wires, the registry's `attach_flags`): bit0 a pending havereset was acknowledged (riscv), bit1 existing connection,
  bit2 woken from dormant (swd), bit3 the hart is halted (the answer's TLV 0x11 dpc is valid).
- **attach while applying reset**: with the TLV 0x05 reset (critical: `channel(u16), hold_ms(u16)`), the probe holds the reset wire (channel) for
  hold_ms and then releases it. With method 1 it keeps issuing halt while releasing, to halt as early as possible (flags bit3, dpc TLV). **There is no guarantee of halting before the first
  instruction** (some execution happens between the release of the reset wire and the halt taking effect. [link measurements](link-measurements.ja.md) (Japanese) §3). When a guarantee of halting at the position right after
  reset is needed, use reset mode 2 of riscv-dm (release ndmreset while holding haltreq). With method 0 it attaches with the target running. An optional function; a probe without it is rejected unsupported (tag 0x05). An attach with the reset TLV to an existing connection
  resets that target and then returns the same connection (treated the same as the NRST of the reset op: mark reset detail 3). hold_ms is
  subject to the core's max_op_ms.
- **There is no default reset wire**: which wire is used for reset is specified explicitly by the host every time with channel (a reset on the wrong wire could damage the target or the
  fixture). The channels the probe may use for reset are declared with role 3 (reset) of the role_channels of describe. An undeclared
  channel is rejected unsupported (tag 0x05) without executing anything. A channel held by an existing plan or connection is rejected
  unavailable as the contention of §8.1. **The reset wire is pulled low open-drain, and when released it stops pulling and goes to the idle state of core §8** (no short with an external reset button or
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

The schemes of target_id (`target_id_scheme`): 1 = the u32 read from DMI address 0x7F (length 4). 0 and 0xFFFFFFFF mean "none" (not attached).
2 = the targetsel of swd (u32, used only in the entries of connections. Not used for the lock). The length of the value per scheme is held in the registry
(used to verify the length of the mask / value of a slot's lock).

- **The wire settings are properties of the target, and the host holds them**: the upper limit of the wire speed (max_speed) and the way of resting (idle_clock) are what the target (chip)
  requires (there are targets whose debug wire is reset by the way SWCLK rests, and targets whose speed limit drops because of the slow clock right after reset.
  [link measurements](link-measurements.ja.md) (Japanese) §3). The probe does not hold them as defaults. The host passes them at every attach, and a slot that attaches without a host
  holds the same values in the slot's item ([probe settings](oep-if-probe-config.md) §1.1). scan accepts the same TLVs (to find such
  targets with scan without breaking them).
- If an attach to an existing connection carries an idle_clock different from the current one, the probe changes the resting of that connection and returns it. A probe that cannot change it
  treats it as a TLV value it cannot handle (core §2.3).

## 4. `oep.target.riscv-dm`

Requests start with connection(u16).

- **The mandatory ops are dmi, halt, resume.** reset, read_block / write_block, run, step are optional and declared with the features of describe
  (bit0 read_block / write_block, bit1 run, bit2 reset, bit3 step). Undeclared ops are unknown_operation. The host can build the same thing with dmi even without the
  optional ops.
- **Scope of the ops other than dmi (the high-level ops)**: they handle hart 0 of RV32 only (addresses, register values, pc are u32). Inside a high-level op the probe
  sets the hartsel of DMCONTROL to 0 and **returns with it set to 0** (a hartsel selected by the host with dmi lasts only within that dmi request). Other harts and RV64 are
  handled by the host with dmi (DMI values being u32 is the form of DMI, and does not mean a restriction to RV32). RV64 addresses are added later with the
  critical TLV 0x01 `address_hi(u32)` of read_block / write_block (reserved. The registry's reserved).

**Invariant at op boundaries**: **the probe carries no target state across an op after returning its answer.** What was used inside the op is restored before the answer.
Whatever the host does with raw DMI (the dmi op), and even if the host dies midway (lease expiry, force), there is nothing the probe forgets to restore.

| op | What the probe touches | Before the answer |
|---|---|---|
| halt | haltreq | Checks allhalted. **haltreq may be left set while halted** (whether to keep or clear it is decided by the probe; the behaviour visible to the host is the same. The reason for keeping it is [link measurements](link-measurements.ja.md) (Japanese) §3). Cleared on resume / step / reset / detach and when the connection closes |
| resume | haltreq = 0, resumereq = 1 once | Remembers nothing, restores nothing |
| step | dcsr.step, DATA0 / DATA1 (reading and writing dcsr) | Clears dcsr.step, restores DATA1, DATA0 |
| reset | haltreq, ndmreset, acknowledging havereset | Acknowledges havereset. mode 0 / 1 clear haltreq. mode 2 stays halted and may keep haltreq like halt. The internal halt of mode 1 is restored like step |
| read_block / write_block | GPRs (s0, s1, a0, a1), DATA1 / DATA0, abstractauto, program buffer, sysbus | Restores GPRs, DATA1, DATA0, abstractauto. The program buffer and SBCS / SBADDRESS are not restored (the host sets them again if it uses them) |
| run | pc, the GPRs the host specified, dcsr (ebreakm, prv), haltreq | **Returns with them changed as the host instructed** (the host's responsibility). abstractauto and haltreq are restored |
| dmi | What the host wrote | Touches nothing, restores nothing (if the host used DATA, the host restores it) |
| Console read (§4.6) | DATA0 / DATA1 | Does not read while the hart is halted |

The restored value is the "value before touching" read inside that op. The upper limit for waiting on DM state inside a high-level op (abstractcs.busy clearing, allhalted, allresumeack)
is 100 ms per wait. The status when it is exceeded is as in each op's section (halt is timeout, resume / step are state). DMI busy is
retried up to 100 times inside the probe, and when used up, status wait (same as the WAIT of §6).

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
  inserts a console read between requests. `oep.target.console` §2).

### 4.2 halt, resume, step

- **halt** does nothing and returns ok if already halted. It waits 100 ms for allhalted, and if not seen, status timeout.
- **resume** writes haltreq = 0, resumereq = 1 once. ok means "the hart left debug mode", decided by the allresumeack of DMSTATUS (or
  allrunning and not halted). resumereq is not reissued. If not seen after waiting 100 ms, status state.
  - For some targets this is not enough (a target that does not set allresumeack may immediately halt again at a breakpoint, or may not leave with one
    resumereq). Handling that (reading dpc and resuming again if it is not moving, etc.) is done by the host that knows the target.
- **DATA0 / DATA1 belong to the target**: if the probe uses DATA0 / DATA1 with an abstract command (read_block etc.) while the hart is halted,
  the word the target had placed there (a console frame or answer of dmseq etc.) is lost, and after resume the target reads the absence of its own word as
  silence and waits until its timeout ([link measurements](link-measurements.ja.md) (Japanese) §3). Therefore an op that uses DATA0 / DATA1 restores them **before its own answer** (the table of
  §4). The probe remembers nothing across ops.
- **step** sets dcsr.step, issues resume exactly once, and clears dcsr.step when it returns. It is not a failure if dpc does not move (status ok, moved = 0. An instruction that jumps to
  itself leaves dpc the same even when it executed correctly, so the host reads the instruction and decides). If the hart does not return to debug mode within 100 ms, status state.
  prv is not changed.

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

TLV 0x01 method (u8): 0 the probe chooses, 1 ndmreset. 2 is reserved (there is no common procedure for a target's system reset, so the host builds it with
dmi).

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
  connection 2 + address 4 + count 2 + words) fit within its own max_frame (max_frame − 24 or less. It may declare smaller). The host decides count from
  max_length, not by calculating from max_frame. If count × 4 exceeds max_length, rejected unsupported (payload `0x00`). count = 0 is
  success, done 0. An address that is not a multiple of 4 is rejected malformed.
- **Meaning of a read**: read_block reads through the target's bus. The probe keeps no copy on its side (it reflects what the target wrote in the preceding write_block, dmi, run).
  Only the probe's side is guaranteed; the image of the target's own cache or prefetch is out of scope (the side of the host's chip knowledge).
- **Prerequisite**: the hart is halted (if not halted, status state). The address is the one the halted hart uses in M mode.
- **Side effects**: the probe may use GPRs, the program buffer, the DATA registers, and sysbus. However, **before returning the answer, it restores the GPRs, DATA1,
  DATA0 and abstractauto it used to their values before use** (the table of §4). Even if the host saves nothing, halt → read_block → resume leaves the target's state
  unchanged. Without restoring, depending on where it stopped, the target would keep running with corrupted registers. Restoring at resume time fails when the host's raw DMI
  comes in between ([link measurements](link-measurements.ja.md) (Japanese) §3). The program buffer and SBCS / SBADDRESS are not restored (the host sets them again if it uses them).
- run (§4.4) runs the host's loader with the registers the host specified, and the GPRs and dcsr changed during it are not restored (the host's responsibility).

### 4.6 Handling of RISC-V connections

- attach first acknowledges a pending havereset (some DMs freeze the halt / running of DMSTATUS until acknowledged.
  [link measurements](link-measurements.ja.md) (Japanese) §3).
- After a target reset (the reset op, the reset TLV of attach), the probe acknowledges havereset and keeps the same connection.
- **On seeing havereset** (whether inside a request or inside a console read), acknowledge it, return the dmseq state of the console to unsynchronised, and attach a mark restart (detail 1)
  to the streams of that connection.
- **The probe does not reset the debug module even when closing a connection** (it leaves dmactive and clears haltreq etc.). Resetting would
  erase the dmseq frame in DATA0, and the next console opened would be kept waiting until the target's timeout.

## 5. `oep.wire.swd`

| op | Name | Request | Answer |
|---:|---|---|---|
| 0x01 | scan | count(u8), count × (swdio(u16), swclk(u16)), [TLV] | tried(u8), count(u8), count × (len(u8), kind(u8), swdio(u16), swclk(u16), id(u32)), [TLV] |
| 0x02 | attach | method(u8: 0 only. 1 is rejected unsupported), [TLV] | connection(u16), id(u32), flags(u8), speed_hz(u32), [TLV] |
| 0x03 | detach | connection(u16), [TLV] | — |
| 0x04 | — | Reserved | |
| 0x05 | connections | first(u8) | §2.1 (no lock) |

- The kind of scan is 2 = arm-adi, id is DPIDR. The forms of request and answer are the same as §3 (one form for the 3 wires).
- The TLVs use the same numbers as §3: scan 0x01 max_speed, 0x02 skip, 0x06 targetsel (below). attach 0x01 max_speed (mandatory), 0x02 targetsel,
  0x03 pins, 0x05 reset (a probe without it is rejected unsupported). detach 0x01 force. attach answer 0x10 target_id, 0x12 search_retries (§1).
- **How the speed is selected**: SWD cannot select the speed by reading, so it starts at `min(max_speed, the max_clock_hz of describe)`.
- attach tries the switch from JTAG to SWD, and if there is no answer wakes it from dormant (flags bit2). Power-up (the CDBGPWRUPREQ /
  CSYSPWRUPREQ of CTRL/STAT) is done by the host with DP writes. In the retries of §2, the line reset and the wake from dormant are redone.
- **targetsel (TLV 0x02, u32) is sent critical** (only for multidrop. If ignored, it would attach to a different target). **The identity of a connection
  includes targetsel.** An attach whose targetsel (including none) differs from a live connection with the same pin combination is rejected unavailable
  (the host detaches first). If the same, that connection is returned as is. scan tries without targetsel (multidrop targets that require TARGETSEL
  do not appear in scan. One can be specified and tried with the TLV 0x06 targetsel of scan).
- **Intended asymmetry** (revision 1): arm-adi has no halt / resume / step / reset / run (the host builds them with transfer). Slots, locks and consoles do not ride on an swd connection
  (swd cannot be used as the wire_fn of a slot of `oep.probe.config`, and a console open on an swd connection is
  rejected unavailable cause 6). The tid of an entry of connections is scheme 2 (targetsel) and is not used for the lock.

## 6. `oep.target.arm-adi`

Requests start with connection(u16).

| op | Name | Request (after connection) | Answer |
|---:|---|---|---|
| 0x01 | transfer | n(u16), n transfers: req(u8: bit0 APnDP, bit1 RnW, bit2-3 A[3:2], bit4-7 are 0) and, for a write, value(u32) | done(u16), status(u8), ack(u8), nvals(u16), nvals × value(u32), [TLV] |
| 0x02 | read_block | address(u32), count(u16), [TLV] | done(u16), status(u8), done × word(u32), [TLV] |
| 0x03 | write_block | address(u32), count(u16), count words, [TLV] | done(u16), status(u8), [TLV] |

- ack is the raw ACK of the last transfer (`swd_ack`: bit0 is first in wire order. OK = 1, WAIT = 2, FAULT = 4. No response is status line). If bit4-7 of req are
  not 0, rejected malformed. nvals is the number of values read (the number of reads among the first done transfers).
- transfer is a raw transfer, and the one-transfer delay of AP reads is passed through as is (the host receives it with RDBUFF or the next AP read).
  WAIT is retried up to 100 times inside the probe, and when used up, status wait. It stops on FAULT, so the host clears the sticky bits with ABORT.
- The length per request and the meaning of a read of read_block / write_block are the same as riscv-dm (§4.5): the max_length of describe (number of bytes, a multiple of 4, a value such that both request and answer
  fit in max_frame) is always emitted, and if count × 4 exceeds it, rejected unsupported (payload `0x00`). The host decides count from
  max_length. read_block reads through the target's bus and the probe keeps no copy on its side.
- read_block / write_block use the TAR / DRW of the current MEM-AP. SELECT and CSW (32 bit, single increment) are set by the host beforehand. The probe
  rewrites TAR at every 1 KiB boundary and reorders the reads that lag by one. **The state of the hart does not matter** (the MEM-AP can be read while running).
  **done is the number of words the probe sent**, not a guarantee that the target accepted them (a FAULT of a posted write is seen in a later transfer). TAR is left advanced, and
  SELECT / CSW are not changed (the arm version of the invariant of §4: the probe does not change what the host set). 64-bit AP addresses are added later with the same
  TLV 0x01 `address_hi` as riscv-dm (reserved).
