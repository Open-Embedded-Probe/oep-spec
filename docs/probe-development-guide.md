# Open Embedded Probe — probe development guide

[日本語](probe-development-guide.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative). For people who build probes, it collects practical ways to meet what [OEP core](oep-core.md) and
the `oep-if-*.md` documents require of a probe, and the traps people tend to fall into. Where it disagrees with the normative text, the normative text is right. The host side is in the [host development guide](host-development-guide.md).

- The first step (the smallest probe that answers confirm, list and describe, with the bytes) is in [getting started](getting-started.md), and the checklist of what a probe
  must do is [conformance](conformance.md) §1.
- How to build with a probe library or per board, and the constraints, are kept in the repository of that implementation.
- Names in backquotes such as `probe_frame_gap_ms` are keys of `registry/oep-v1.toml`, which holds every number.

## 1. Do not reset or change state on open and close

- Opening and closing a transport does not reset the probe. On a board with a circuit that resets the MCU on DTR / RTS changes, the host opens so as to avoid it
  (host guide §1). The probe does not restart itself because a port was opened or closed.
- **Do not rely on DTR.** Some USB serial stacks do not send while DTR is low. Turn that off (a setting of the stack such as "ignore flow control"),
  so that it keeps talking even when hosts open differently. transports §4: the probe does not use DTR, RTS or the line state for any decision.
- **Opening and closing a transport does not change state.** attach, pins and wire states stay as they are. Resources are removed only by the lifetime rules of core §9 (explicit
  release / detach, and that session's share on lease expiry and force). Even when removing them, the target is not reset. Released pins are put in the setting idle
  state (Hi-Z by default) and not kept driven (core §8).
- **After booting, put the pins away before answering.** Before the first answer, put them in the idle state, except the channels it uses itself and the channels whose use and configuration settings prohibit: the idle if a setting
  defines one, otherwise Hi-Z (input, no pull) (core §8). Do not leave them as the MCU's startup code or the drivers of peripheral circuits left them.
  Until the firmware runs, the pins are in the MCU's reset state, and no firmware can change that. Tell users that a line where a wrong level does harm needs an external pull
  ([safety and security](security.md) §6).
- A probe that is reset by opening no matter what says so to users in its documentation.

## 2. Send and receive buffers

- **Be able to hold requests that keep the declared window and max_inflight.** window is the total message bytes, including headers, of outstanding requests, and counts requests being executed too.
  Frame wrapping, lower-layer drivers and DMA/packet retention are estimated separately. Simply providing a ring larger than window is not required.
  Answers may be built and sent in order, and there is no need to hold at once the sum of the largest answers to all requests within window.
- **Do not use the platform's default buffer sizes without checking**: they are often smaller than one max_frame.
- In configurations that accept several outstanding requests, hold conforming requests that arrive during long processing (interrupt/DMA, polling reception, lower-layer retention or backpressure and so on).
  In a max_inflight=1 configuration the host does not send the next ordinary request before the answer, so interrupt/DMA merely to achieve concurrent reception is not uniformly required.
- **Do not do heavy processing per byte on reception.** Read what has arrived together, read the clock once, and copy the body together. Reading the clock per byte
  can cap the reception speed far below the line speed.
- **Be able to receive a request of the declared max_frame whole**: check the frame retention together with the amount the lower layer hands over and the framing processing.
  The ring size and number of copies are chosen by the implementation's method. A small configuration can take as an example a 64 byte request buffer and a 64 byte result buffer, but those are not values of total RAM including wrapping, lower-layer drivers and so on.
- When providing notifications, also choose a finite retained amount. The sending limit max_frame×2 is not a mandatory queue capacity.
  Do not drop a frame that has started being sent midway or insert an answer into it, and give answers priority over unsent notifications. Refuse a subscription whose retained amount cannot be met following core §10.3.
- **Receive vendor bulk OUT per packet**. Do not receive it as large transfers ending with a ZLP: the host follows writes that are a multiple of wMaxPacketSize with
  a zero-length transfer (transports §1), so a request that ends exactly at a packet boundary can be kept waiting until the next OUT. Skip zero-length completions.
- Measure the line speed with the source / sink ops of `oep.probe.link` ([link](../interfaces/oep-if-link.md) §2). Measure again after changing the receive or send path.

Internal C structures do not need to be laid out in wire field order. For example, putting a mark's u64 first reduces ABI padding.
Encode to the wire field by field, in the decided order and little endian. Packed attributes or sending whole structures are not uniformly required.
A configuration that does not provide marks does not allocate their records, serials or rings. Replacing a plan also need not duplicate the buffers of every function;
it can compare the existing table with the received request without side effects, and then apply only the assignments removed and the assignments added.

## 3. Put nothing else on the OEP port, and do not stall on a port nobody reads

- **Do not put logs on a port that carries OEP.** Log lines break frames, and the host considers that no answer came. Stop the platform's logs on that
  port.
- **Do not stall the main loop on writes to a port nobody is reading.** A blocking write to a USB serial port that is not open waits for its timeout on every call,
  and can delay every answer and notification. Make writes non-blocking, or do not write.

## 4. CRC and resending for unreliable transports

- USB (CDC, vendor bulk) guarantees data, but **transports through a USB-UART converter chip do not**: bytes are dropped or corrupted in the UART between the probe and the converter chip,
  inside the converter chip, and in layers that carry USB over a network.
- So serial ports carry COBS + CRC-16/CCITT-FALSE (transports §1): broken frames are discarded, and the host resends (core §5.1).
  The host does not take "an answer came" as grounds for correctness.
- The target side is the same: 1 bit of parity on a debug wire lets half of broken answers through. Check memory reads and flash results with a higher-level CRC or
  a read-back.

## 5. Boot speed of the UART bridge

- A UART bridge probe always boots at `uart_bridge_boot_baud` (115200 bps) 8N1, no flow control (transports §4). Do not make the boot speed
  a setting: forgetting the setting locks you out, and automatic detection of unconfirmed speeds is avoided.
- Making it faster only for the session is port_speed ([link](../interfaces/oep-if-link.md) §3, optional): put `oep.probe.link` in list, implement the 4 states including pending recovery and the conditions
  to revert, and set port_speed (0x12) and port_state (0x13) in the ops of its describe. port_state returns the current speed and state. It always reverts to the boot speed.
- On USB CDC and built-in USB serial, the line settings are only numbers passed along and have nothing to do with speed. Ignore them (transports §4).

## 6. Building for serial frames only

Have one reader and one writer per port. Accumulate 0x00 candidates, verify COBS and CRC, and discard broken candidates.
Even if a buffer overflows, nothing is forwarded to the target. Queue to the send queue per frame, and do not insert another frame midway.
Put logs and the raw console on another endpoint (transports §4).


## 7. Preventing probe restarts

Make sure the probe does not restart when a port is opened or closed (§1). Turn off every restart trigger of the USB stack (DTR / RTS sequences, the 1200 bps "touch", vendor
reset requests). When the trigger is outside the firmware (an automatic reset circuit behind a USB-UART converter chip), the host opens with DTR and
RTS asserted (host guide §1), and if it still resets, say so to users in that probe's documentation. Platform-specific ways to configure this are kept in the implementation repository.

## 8. Recommended USB build (VID:PID, iProduct, serial number, interfaces)

For probes with native USB:

- **VID:PID**: a host recognizes OEP probes automatically only by the project's USB VID:PID `1209:4F45` (VID 0x1209, PID 0x4F45;
  registry `usb`; transports §3). A probe uses it under the conditions of PID-USE of oep-probe-arduino. For a probe that does not enumerate with it,
  the user names it or chooses the port. Ports behind a USB-UART bridge and built-in USB serial whose descriptors the hardware decides cannot have the project's VID:PID.
- **iProduct** is a name for people, and nothing recognizes probes by it (transports §3).
- **The serial number is the unit_id** (transports §3). A host looks with it for a probe the user named by unit_id.
- Ports within the device are as in transports §3: every CDC is a serial port. vendor bulk is the bulk pair of an interface with class 0xFF / subclass 0x4F / protocol 0x45
  (attach the Microsoft OS 2.0 compatible ID `WINUSB`). HID has usage page 0xFF4F / usage 0x45, and accepts output
  reports both on interrupt OUT and by SET_REPORT. At most 1 each of vendor bulk and HID.
- A good set is **vendor bulk (OEP), HID (OEP), CDC (serial port)**:
  - vendor bulk is the host's main, fast transport;
  - HID can be read even when other tools hold the vendor or CDC interface, needs no driver, and suits lock-free discovery (describe, settings get and state);
  - CDC is the serial port visible from IDEs and terminals. It also accepts OEP (transports §4), but mainly carries the console.
- List every offered transport in the fn 0 describe (the transport tag), and return the same unit_id on every transport.
- USB identification and how hosts choose are in [USB identity](usb-identity.md).

## 9. What the probe answers for taking the lock

The host decides how to take the lock by the number of transports (host guide §6). The probe:

- shows its list of transports correctly (so that a probe with only one serial port looks like that);
- frees the lock when the lease runs out (doing the cleanup, core §9), and returns the remaining time of lock_state correctly;
  only the processing of the holder's own new request is the interval in which the lease stops, and it resumes from building the answer. It does not stop for waits to send or for queries with session_id 0 (core §6.1).
  Even if the destination stops, the lease deadline check and cleanup do not stop. How sending and timers are advanced is chosen by the implementation, and does not require a separate thread.
- accepts lease requests of `lease_min_ms` to `lease_max_ms` as they are, and rounds others into that range (core §6.4).


An implementation with the optional policy decision makes it after the header check and before returning the resend byte record (core §4.3).
A minimal implementation that needs no policy is not required to have authentication operations, state tables or additional RAM.

## 10. Choosing identifiers and declarations

**unit_id** (describe 0x42 of fn 0, core §7.5): 1 to `unit_id_max_bytes` (32) bytes of `a-z 0-9 -`. Different per unit, made only from values of the unit,
the same on every transport and in every firmware version and profile, with no suffix. Where the probe can choose the serial number, equal to the USB serial
number (transports §3).

| Source | Advantages | Disadvantages |
|---|---|---|
| The chip's unique number in lowercase hexadecimal | Needs no storage. Does not change even after a full erase or rewrite | Shows the chip's factory number to anyone who can read describe or the USB serial number ([safety and security](security.md) §8). A 128 bit number uses up all 32 characters |
| A random number made and saved at the first boot | Shows nothing about the chip | Needs storage. A full erase of that storage gives the unit a new identity, and the host's records and named addresses no longer match |
| Something beginning with `x-` | For probes with neither | Not unique: the host does not group by it, name by it, or use it as a key for anything (core §7.5) |

Write hexadecimal digits in lowercase: the host compares ignoring case, but `A-F` are not among the allowed characters.

**transport index** (core §7.5): from 0, one per transport. Across firmware versions of the same model, do not change the index of each transport.
Give a new transport an index never used before, and do not reuse removed indexes. The OEP transport index is used to match the fn 0 transport with confirm.

**boot_id** (core §6.5): with a hardware RNG, a random number; if non-volatile memory can be used, a boot counter or a saved random number are candidates.
If there is neither, mix in input that differs at each boot, such as ADC noise or the timer at the first external communication received.
A timer value only at a fixed code position in the boot may not identify restarts. The choice of generation method is not an additional normative requirement.

**model** (0x41, optional): a free string. The same value for the same kind of hardware with the same firmware, not changed per unit.

**firmware** (0x40): an optional string of version and diagnostic information. describe values are fixed while the boot_id stays the same (core §7.3/§7.5).
Diagnostic information decided at boot can be included, but state that changes during operation is returned by a state query op.
**chip** (0x4C, optional): a free string. The MCU's part number and revision (used to record in capture records which chip they were taken on).

**Identifying interfaces** (core §7.2): fn does not change while the probe is running. instance is a fixed identifier, unique within the same (name, revision), that allows gaps.
It may be assigned as a constant in the firmware; no dynamic allocation table is required. Do not renumber instances left after removals or fn changes, and do not reassign removed numbers to other logical interfaces.
Saved settings point at categories by (name, instance), and the meaning of item names does not change across revisions (core §13.1). A change that breaks an existing contract raises the revision, and where possible the old revision keeps being offered under another fn (core §2.8).

**Pins** (core §7.4): for a function that can assign pins to any of a set, declare role_channels; for a function with fixed sets, declare channel_group per set.
Both may be used. Channels the probe itself uses are not put in any declaration (not assigned to interfaces), and get no channel settings items. If plan has
a limit, declare plan_roles in the describe of `oep.probe.plan` ([plan](../interfaces/oep-if-plan.md) §1).
**Port names and initial values** (core §13.4, §13.8, [host development guide](host-development-guide.md) §5.3): the host names ports by
`channel.{}.label` of the form `S.N`. A probe with wires does well to have labels that match its wiring as initial values (`V003.swio`, `dut.swdio` and so on;
`S` is up to 16 characters of letters, digits and `-`, beginning with a letter). Without a label, the host cannot point at that port by address.
Initial values are put by the core at a boot without a save, and afterwards are not distinguished from user values. For a fixture whose wiring is fixed by the board and should not be changed, a configuration without saving
returns changes to the initial values at restart. To make it a complete preset that accepts no changes at all, give it no set and unset (get only; core §13.5).
To keep only some values from being changed, refuse set and unset of those values with unavailable (cause 7) (core §13.6). A general-purpose probe with saving (a board with silkscreen and so on) may also have no initial values and let the user configure it.

A one-direction UART is used by assigning with plan only the RX or TX role it provides. If a probe that declares a fixed RX/TX pair with channel_group
also accepts a one-direction plan, it also declares a group that matches that one direction. An RX-only probe needs no TX declaration or implementation
([fixture](../interfaces/oep-if-fixture.md) §2).

**max_frame, window, max_inflight** (confirm, core §4.4), per transport:

- max_frame: `min_max_frame` (64) or more. Choose it so that one whole request of that length fits in the receive path (§2). max_length is a functional limit,
  and for splittable operations such as blocks it is also fitted to the frame of each transport. The limit of unsplittable external RX fits every transport, following that operation's definition (core §7.4).
- window: the bytes of waiting requests it can hold while busy for max_op_ms. max_frame or more (core §7.1).
- max_inflight: the number of waiting requests it accepts, 1 or more (core §7.1). This is separate from the number of resend cache entries.
  If it keeps the ordering state of the last session_id/corr, the resend byte record may be 0 entries (core §5.1). Old requests get result_lost and are not re-executed.
  When it keeps records, choose the retained memory as cache entries × (the requests/answers kept and metadata). The buffer that receives outstanding requests is allocated separately.
- On serial ports, the host OS's receive amount limits things first (host guide §8). A larger window does not help the host.

**Keeping resource IDs** (core §9): can be implemented with a counter increasing from 1 and a table of resources in use with a decided limit.
There is no need to keep the whole history of closed IDs. Keep the u32 next number and the table of resources in use, and treat a wrap to 0 as exhaustion. Using 0 as the exhaustion mark needs no extra flag or u64 counter.
At the end of a session the resources in use are released, but the allocation counter within the boot is not returned. Even after exhaustion, operating on and releasing existing resources continues.
IDs are consumed by creations that assign numbers, not by every request. For example, plan_apply returns no number, and read/write on a kept connection do not increase the number either.
A reserved number may become a gap when creation fails. Think of the number of resources usable at once and the total number of IDs created during a boot separately.

**max_op_ms** (0x4D, mandatory): the longest processing time of one request itself, including its validation, internal retries, execution, cleanup and building the answer.
Waiting for earlier requests on the same or another transport and the transfer time of the transport are excluded. It includes save, flash loaders, attach, scan and reset. 1 to `max_op_ms_max` (600000 ms).
Ops whose arguments could exceed it are refused with unsupported. The host waits max_op_ms + `host_wait_add_ms` for an answer that does not come, so do not declare much more than needed.
confirm / list / describe / clock / keepalive / lock_state process the whole request within min(max_op_ms, core_quick_op_max_ms) even when max_op_ms is large (core §4.4).

**Clock** (core §2.7): ns since boot (u64). While the boot_id stays the same it does not decrease and does not wrap. If the hardware counter is narrower than 64 bits
(a 32 bit µs counter wraps in about 71.6 minutes), widen it in software by the number of wraps, and read it (from the main loop) often enough not to miss a wrap.
The uptime_ns of the clock answer (core §7.6) is the value of this clock read while processing that request (do not reuse a value read earlier). The host assigns that value to
the midpoint of when it sent and when it received.

**session_id** is chosen by the host. The probe only remembers the last one (core §6.1).

## 11. Probe settings and saving

When it has settings (core §13):

- The core holds the list of items, the values, the generation and the save; the owners (the core's channels and network, each interface) only declare, validate and apply.
  Owners hold the values in memory, and their ordinary processing does not go through the settings path (settings reads and writes are rare).
- Track content changes with the u32 generation, and keep equality between get pages. Do not use a digest of the content as the guarantee of change detection.
- The number of values and bytes can be made finite. Update after first checking the request against the existing values; cloning the whole state is not uniformly required.
- save/state and the non-volatile area are needed only when saving is provided. The save format is free, but categories, items and keys are held by name (numbers are not saved).
  A nested structure (category → item → key name → value; CBOR and so on) takes about half the size of flat names (informative).
- Atomic saving can use 2 copies and integrity checks / commit information and so on. Check the consistency of the internal format separately from the current generation.
  If the same content is already saved, skip writing.
- At boot, use only the values that match declared items, whose names can be looked up and that pass validation, and apply them in the order disable, idle. Unused values disappear at the next save.
  Distinguish partial application from an unreadable container. If the container cannot be read, do not apply uncertain settings.
- Before the settings are applied, the pins are in the MCU's reset state. Saving alone does not guarantee the electrical state over the whole restart ([safety](security.md) §6).

## 12. Parts that handle targets

Implementation notes common to probes that handle targets.

- **When providing run**: run of riscv-dm sets ebreakm of dcsr and prv=M and runs the host's code
  ([wire and debug](../interfaces/oep-if-debug.md) §4.4). Target-specific interrupt control and the like are handled by the host's procedure.
- **How to implement block transfers**: on a supporting debug module, autoexec and the like can process them together.
  Whatever the transfer method, the measurement point of done, the prohibition of re-executing writes and the cleanup follow wire and debug §2/§4/§6. Adopting autoexec is not itself a conformance condition.
- **A wire speed is guaranteed only at the target clock at which it was checked.** If a reset returns the target to a slow clock, writes at the speed chosen earlier
  get corrupted. Reset at the slowest speed, and choose the speed again after the hart has stopped. The same for attach while asserting reset: go to the slowest speed before releasing
  reset. On a wire where wake resets the target, do not use wake, but speed up from a slow speed and measure again. A corrupted read can make
  DMSTATUS look "running": treat a value whose version field does not match as noise.
- **How the wire rests between frames is part of the wire's definition** ([wire and debug](../interfaces/oep-if-debug.md) §3.1, §3.2, §5); where idle_clock allows it, the host chooses per
  target, and on rvswd, if the host does not choose, the probe decides from target_id (debug §3.1; OFF per port with the setting `channel.{}.rest` of `oep.wire.rvswd`). Following the wire section,
  after an exchange fails, rest the wire without driving it (debug §2). After closing the connection, unless it was a wire loss, hold that rest state (debug §2; OFF per port with the setting
  `channel.{}.hold`). Some targets lose their debug state within a few ms when driving stops (CH32L103 at about 5 ms).
- **Settings that differ per target are decided by the host as a rule. For things involving timing and the like, an automatic decision in the probe can be added** (core §12 rule 8). The order to think in:
  1. **Can the host make it in time**: things where a wrong setting breaks the target's state within a few ms (example: on CH32L103, resting the rvswd wire high resets the
     debug module in about 1 ms and halt is lost; CH32X035, conversely, cannot be attached if rested low) cannot be handled by a procedure where the host checks the connected party and then corrects
     the setting. A host doing initial setup from a web browser and the like cannot do operations without time margin. Such things are candidates for an automatic decision.
  2. **Does it avoid loading knowledge onto hosts**: a design where the host checks the connected party and then changes the settings requires per-chip knowledge (bad know-how) of every host.
  3. **Conditions when adding an automatic decision**: make what was chosen readable by the host (show it in answers or lists, so that it can be seen an automatic decision was made). Give priority to the host's
     explicit specification. Make it possible to turn it OFF in the probe's settings (per port or another unit where decisions can differ). Put the chip table used for the decision in the registry,
     not as hidden knowledge inside the implementation.
  Things where judgement differs are decided by the owner of the specification after aligning hardware measurements with the opinions of host-side users (ch32rv and so on).
- **For a fault that occurs only when debug and fixture run at the same time**, check wire interference in addition to processing load.
  On hardware whose output strength can be adjusted, one method is to weaken it, within the range that keeps wire timing, and compare.
  This does not require a function to change the strength, or particular levels, of every PHY and port.
- **After fixing a problem, look for places with the same mechanism** (other PHYs, other SoCs, fixtures that drive lines, clients and the virtual bench). Record which places are fine and which are
  unchecked.
- **Do not reissue resume and run** ([wire and debug](../interfaces/oep-if-debug.md) §4.2, §4.4). Targets that need the resume request twice, or that do not report
  that all resumed, are handled by the host: putting target-specific knowledge into an interface with a generic name violates rule 8 of core §12.
- **Changes that speed up block loops can change timing on the wire.** Measure on several targets before keeping them.
- **If you stream captures, max_frame 1024 or more is recommended** ([capture](../interfaces/oep-if-capture.md) §3.4). Each data notification frame
  has 49 bytes of a 15 byte header and the mandatory TLVs (generation 7 bytes, segment_info 27 bytes). That is 77% at max_frame 64, 19% at 256,
  and 5% at 1024. The slower the link, the more the reduction of data format 1 helps (making the intervals of slow lines large; capture §1.3).
  max_frame is per transport (core §7.1), so only the fast transport (USB vendor bulk) may be made large. Serial ports may stay small.
- **Make the streaming buffer at least the expected host delay × the largest transfer speed**. Example: 50 ms × 20 MB/s = 1 MB.
  - Tell the host the depth with stream_buffer in the configure answer (capture §3.3).
  - If it is too small, segments are dropped at every jitter of the reads even if the host keeps up on average (example: a buffer of tens of KB is only a few ms at 20 MB/s, and
    a host with a single synchronous read drops segments).
  - A rate at which the path from acquisition into memory itself cannot keep up is refused in configure / query (it cannot be acquired, capture §3.3). Whether sending (USB
    bandwidth, host reads, CPU contention with other functions) keeps up varies with the environment, so do not refuse or lower the rate for that reason.
  - On the host side, keeping several asynchronous reads outstanding is assumed (example: libusb 64 KB × 32).
- **If the acquisition ring is used as a reservoir, overruns become gaps** (capture §2.2).
  - Put the acquisition DMA ring in a large RAM (external RAM and so on); while all sending stages are in use, harvesting leaves chunks in the ring and
    comes back later. One copy into a stage. Make the ring long enough that its length divided by the rate is longer than the jitter of the host's reads.
  - A chunk overrun by the DMA is closed up to the byte before the stage being built was lost and sent, position is skipped, and the next stage starts from the first
    byte after the overrun. The same for chunks that did not get into the harvest queue. They are not yet in any segment, so this is not an error.
  - Include the ring in stream_buffer. Exposing the ring's maximum usage in diagnostics helps estimate the host's delay.
- **Send out a notification batch whose condition has been met in full** (core §10.3). What had accumulated when min_bytes or max_delay_ms was met is split into max_frame and
  sent back to back, and the condition is not reapplied to the remainder.
- **The console send queue** ([console](../interfaces/oep-if-console.md) §2): write immediately accepts and answers what fits in the queue's free space, and passes it from the queue to the target in the mechanism's
  way of carrying (it does not wait for the target to receive before answering). The size of the finite queue when write is provided is decided by the probe.
  A small queue is fine; the host sends the not yet accepted remainder from accepted. Without write, no TX queue is needed.
- **Cleanup of temporary debug state** ([wire and debug](../interfaces/oep-if-debug.md) §4): saved values may be kept only for the op being executed.
  Restore before success. If they cannot be restored because of a wire failure or timeout, return failure and close the connection/stream, and do not carry the restoration work over to later ops.
- **The wait after releasing reset** ([wire and debug](../interfaces/oep-if-debug.md) §2): while the DM does not answer after releasing ndmreset or the reset line,
  read DMSTATUS again and wait (at most max_op_ms). Failures during this are counted neither as wire retries nor as wire loss.
- **Wire retries do not repeat writes** ([wire and debug](../interfaces/oep-if-debug.md) §2): if a wire failure is found in the check after writing a store to the target's memory or a host dmi procedure,
  do not redo it but answer failed / partial, with done as the count completed before the failure (excluding DMI busy and SWD WAIT, where the target answered that it did not accept).
  Writes by which the probe itself puts values into the DM and registers (program buffer, abstractauto, GPR, dcsr, DATA0 / DATA1 to restore) may be repeated.
  Retries and resynchronization on a connection do not send a wake that can reset the target.
- **The console reading order** ([console](../interfaces/oep-if-console.md) §3): after answering a riscv-dm request on that connection, read DMSTATUS before reading DATA0 for the console
  next, and do not read it if the hart is halted.
