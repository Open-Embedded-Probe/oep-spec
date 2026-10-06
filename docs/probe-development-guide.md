# Open Embedded Probe — probe development guide

[日本語](probe-development-guide.ja.md)

Status: out of date. Until the v1 freeze the Japanese text (.ja.md) is the working text; this English version will be regenerated from it at the freeze and becomes authoritative then.

Status: **guide** (not normative; updated 2026-10-06 to the normative text of that date). How to build a probe: practical ways to meet
what [OEP core](oep-core.md) and the `oep-if-*.md` documents require of a probe, and the traps found in practice. Where this guide and
the normative text differ, the normative text is right. This English text is authoritative; the Japanese version is its translation.
The host side is the [host development guide](host-development-guide.md).

- The first steps (the smallest probe that answers confirm, list and describe, with bytes) are in [getting started](getting-started.md);
  the checklist of what a probe must do is in [conformance](conformance.md) §1.
- The reference library has its own guides for building a probe on it:
  [getting started](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/docs/guide/getting-started.md),
  [writing a probe](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/docs/guide/writing-a-probe.md) and the example
  `examples/01.Basics/MinimalProbe` (oep-probe-arduino).
- Names in backquotes such as `probe_frame_gap_ms` are keys of `registry/oep-v1.toml`, which holds every number.

## 1. Opening and closing do not reset or change state

- Opening or closing a transport does not reset the probe. Boards whose circuit resets the MCU on DTR / RTS changes are opened by the host
  in a way that avoids it (host guide §1); the probe itself never restarts because a port was opened or closed.
- **Do not depend on DTR.** Some USB serial stacks stop sending while DTR is deasserted; turn that off (the stack's "ignore flow control"
  option or equivalent) so that the probe keeps talking however the host opens the port. core §3.4: the probe does not use DTR, RTS or the
  line state to decide anything.
- **Opening and closing a transport changes no state.** Attachments, pins and line states stay. Resources are removed only by core §9's
  lifetime rules (explicit release / detach, and the session's share on lease expiry and force). Removing them does not reset the target.
  A released pin goes to the settings' idle state (Hi-Z by default) and is not left driven (core §8).
- **At boot, park the pins before you answer.** Before the first answer, put every channel that is not in `reserved` in its idle state: the
  settings' idle when they define one, otherwise Hi-Z (input, no pull) (core §8). Do not leave a pin as the MCU's start-up code or a
  peripheral's driver left it. Until your firmware runs, the pins are in the MCU's reset state, which no firmware can change; tell users
  that a line whose wrong level is harmful needs an external pull (probe settings §5).
- A probe that unavoidably resets when a transport is opened declares `resets_on_open` in fn 0's describe (core §7.5).

## 2. Receive and send buffers

- **Make the receive buffer larger than the declared window** (the bytes of requests accepted but not yet processed), and the send buffer
  larger than the answers to a window's worth of requests. Otherwise bytes that arrive while the probe runs a long operation (a flash loader,
  a scan) are lost.
- **Do not keep a platform's default buffer sizes** without checking them: they are often smaller than one max_frame.
- Receive while long operations run (interrupts or DMA, or split the work and keep polling the receiver).
- **Do no heavy work per received byte.** Read what has arrived in one go, read the clock once, and copy the body in bulk. A per-byte clock
  read can cap the receive rate far below the link's speed.
- **Accept a whole request of the declared max_frame**: the frame buffer and the receive ring under it (at least twice what the lower layer
  delivers at once). Otherwise the middle of a frame is lost and later delimiting drifts.
- **On vendor bulk, receive OUT per packet** rather than as one large transfer ended by a zero-length packet: the host follows a write that
  is a multiple of wMaxPacketSize with a zero-length transfer (core §3.1), and a request that ends exactly on a packet boundary may otherwise
  wait for the next OUT. Skip a zero-length completion.
- Measure the link with the source / sink ops of `oep.link` ([link](../interfaces/oep-if-link.md) §2), and measure again after changing the receive or send path.

## 3. Nothing else on an OEP port; never block on a port nobody reads

- **Do not write logs to a port that carries OEP.** A log line breaks frames, and the host sees no answer. Silence the platform's logging on
  that port.
- **Do not let a write to a port nobody reads stop the main loop.** A blocking write to an unopened USB serial port can wait for its timeout
  on every call and delay every answer and notification. Make such writes non-blocking or do not write.

## 4. CRC and resend on unreliable paths

- USB (CDC, vendor bulk) delivers data intact, but **a path through a USB-UART converter does not**: bytes can be dropped or changed on the
  UART between the probe and the converter, in the converter, or in a USB-over-IP layer.
- That is why serial ports carry COBS + CRC-16/CCITT-FALSE (core §3.1): a broken frame is discarded and the host resends (core §5.2). The host
  does not take "an answer arrived" as proof of correctness.
- The target side is the same: a one-bit parity on a debug wire passes half of the broken answers. Check memory reads and flash results with
  a CRC or a read-back at a higher level.

## 5. The boot speed of a UART bridge

- A UART bridge probe always boots at `uart_bridge_boot_baud` (115200 bps) 8N1 without flow control (core §3.4). Do not make the boot speed a
  setting: a forgotten setting locks users out, and automatic speed detection is unsafe on a port where raw bytes and OEP mix.
- A faster link during a session is port_speed ([link](../interfaces/oep-if-link.md) §3, optional): list `oep.link`, implement its three states and its return
  conditions, and set op 0x03 in the ops of its describe. The speed it returns to is always the boot speed.
- On USB CDC and built-in USB serial the line coding is only a number and does not change the speed; ignore it (core §3.4).

## 6. Sharing a serial port

How to meet the rules of core §3.4:

- **Receiving**: one reader per port. Bytes outside 0x00 go to the raw-byte destination (the bind, [probe settings](../interfaces/oep-if-probe-config.md)
  §1.2) at once; from a 0x00 to the next 0x00 is kept as a candidate. If a candidate does not decode, its CRC does not match, or input pauses
  for `probe_frame_gap_ms`, pass the kept bytes on as raw bytes. The candidate buffer holds the COBS length of max_frame + 2; when it would
  overflow, pass its contents on as raw bytes at that point.
- **Send queue**: one queue per port. Its units are whole frames or chunks of raw bytes (about 64 bytes). One writer sends the units without
  splitting them. A frame may go before a chunk. Chunks come from a positioned stream, so when the port is full they can wait without being
  discarded (the position simply does not advance). Do not let the endpoint write frames straight to the port while another task writes raw
  bytes to the same port: most serial drivers serialise only per call.
- **Nothing but OEP and the bound flow goes to the port** (§3).

## 7. Keeping the probe from rebooting

Opening and closing a port must not reboot the probe (§1). Turn off every reboot trigger the USB stack has: DTR / RTS sequences, the 1200 bps
"touch", vendor reset requests. Where the trigger is outside the firmware (an auto-reset circuit behind a USB-UART converter), the host opens
the port with DTR and RTS asserted (host guide §1), and the probe declares `resets_on_open` if it still resets. For example: an ESP32 USB-Serial/JTAG port resets the chip on a DTR / RTS
sequence unless its chip-reset-disable bit is set; TinyUSB's CDC in arduino-esp32 (`USBCDC`) stops rebooting with `enableReboot(false)`.

## 8. Recommended USB shape (VID:PID, iProduct, serial number and interfaces)

For probes with native USB:

- **VID:PID**: a host identifies an OEP probe automatically only by the project's USB VID:PID, `1209:4F45` (VID 0x1209, PID 0x4F45;
  the registry's `usb`; core §3.3). A probe uses it under the conditions of PID-USE in oep-probe-arduino. A probe that enumerates with it
  sets discoverable = 1 in fn 0's describe (so a host that opened it through another port can tell). A probe that does not sends 0; the
  user names it or chooses its port. A port behind a USB-UART bridge, or a built-in USB serial whose descriptors the hardware fixes, cannot
  carry the project's VID:PID.
- **iProduct** is a name for people; nothing identifies a probe by it (core §3.3).
- **The serial number is the unit_id** (core §3.3). A host finds a probe the user named by its unit_id this way.
- The ports inside the device follow core §3.3: every CDC is a serial port; vendor bulk is the bulk pair of an interface with class 0xFF /
  subclass 0x4F / protocol 0x45 (give it the Microsoft OS 2.0 compatible ID `WINUSB`); HID is usage page 0xFF4F / usage 0x45, taking output
  reports both on interrupt OUT and by SET_REPORT. At most one vendor bulk and one HID.
- A good set is **vendor bulk (OEP), HID (OEP), CDC (serial port)**:
  - vendor bulk is the host's main, fast path;
  - HID can be read even while other tools hold the vendor or CDC interface, needs no driver, and suits lock-free discovery (describe, the
    settings' get and state);
  - CDC is the serial port IDEs and terminals see. It also accepts OEP (core §3.4) but mainly carries the console.
- List every transport you expose in fn 0's describe (transport tags), and return the same unit_id on all of them.
- The reference probe's current USB shape: [USB identification](usb-identity.md).

## 9. What the probe does for lock takeover

The host decides how to take over the lock from the number of transports (host guide §6). The probe:

- lists its transports correctly (a probe with a single serial port must look like one);
- frees the lock when the lease expires (and cleans up, core §9), and returns the correct remaining time in lock_state;
- accepts lease requests of `lease_min_ms` to `lease_max_ms` as they are, and rounds others into that range (core §6.4).

## 10. Choosing identifiers and declarations

**unit_id** (fn 0 describe 0x42, core §7.5): 1 to `unit_id_max_bytes` (32) bytes of `a-z 0-9 -`, different per unit, derived only from values
of the unit, and the same on every transport, in every firmware version and profile, without a suffix. It equals the USB serial number where
the probe chooses it (core §3.3).

| Source | For | Against |
|---|---|---|
| The chip's unique number, in lowercase hex | Needs no storage; survives a full erase and reflashing | Exposes a factory number of the chip to anyone who can read describe or the USB serial number ([security](security.md) §8); a 128-bit number already takes 32 characters |
| A random number made at first boot and saved | Exposes nothing about the chip | Needs storage; a full erase of that storage gives the unit a new identity, so hosts lose their records and named addresses |
| `x-` followed by anything | For a probe with neither | Not unique: hosts do not group, name or key anything by it (core §7.5) |

Write hex digits in lower case: hosts compare unit_ids ignoring case, but `A-F` is not in the allowed characters.

**Transport indexes** (core §7.5): from 0, one per transport. Keep each transport's index across firmware versions of the same model; give a new
transport an index never used before, and never reuse a removed one. Saved binds name serial ports by index (probe settings §1.2).

**model** (0x41): lowercase `a-z 0-9 -`, 1 to `model_max_bytes` (32) bytes, the same for all hardware of the same kind with the same firmware,
not per unit. A model that is not the project's own starts with its maker's reverse domain name with `.` replaced by `-` (`com-example-probe1`).

**firmware** (0x40): free text, typically the version. **chip** (0x4C, optional): `<part> v<revision>`, part 1 to 24 of `a-z 0-9`, revision
digits with optional `.digits` groups, or the part alone when the revision is unknown.

**Interfaces and their order** (core §7.2): fns do not change while the probe stays booted. Instances of the same (name, revision) are numbered
by ascending fn, and saved settings point to interfaces by (name, instance, revision): keep the order of interfaces of the same name across
firmware versions. When you change an interface's fixed part, raise its revision and, preferably, keep exposing the old revision as another fn
(core §2.7).

**Pins** (core §7.4): a function whose pins can be any of a set declares role_channels; a function with fixed combinations declares one
channel_group per combination; both may be used together. Channels the probe uses itself go in `reserved` (0x44), and fixed names of the wiring
in `label` (0x46). Declare plan_roles when the plan has a limit (core §8).

**max_frame, window, max_inflight** (confirm, core §4.4), per transport:

- max_frame: at least `min_max_frame` (64). Choose it so that one whole request of that length fits the receive path (§2). Interface limits such
  as max_length must let a request and its answer fit in max_frame.
- window: the bytes of outstanding requests the probe can hold while it is busy for max_op_ms. It is max_frame or more (core §7.1); a host
  does not use a transport whose confirm answer breaks these bounds.
- max_inflight: the outstanding requests it accepts, 1 or more (core §7.1). The resend table keeps at least max_inflight entries with their answers (core §5.2); the
  memory is max_inflight × the largest answer you remember. You may cap the size of a remembered answer (a resend of a larger one then gets
  result_lost).
- On a serial port, keep in mind that hosts keep the answers they wait for at `host_serial_inflight_max_bytes` or less (core §3.4); a larger
  window does not help them.

**max_op_ms** (0x4D, mandatory): the longest time one request takes, save and a flash loader included, 1 to `max_op_ms_max` (600000 ms; a
host does not use a probe that declares 0 or more, core §4.4). Ops whose arguments could exceed it are
refused unsupported. Hosts wait max_op_ms + `host_wait_add_ms` for an answer that never comes, so do not declare much more than you need.

**boot_id** (core §6.5): a new value at every boot. Take it, in this order of preference, from a hardware random number generator; from a
value in non-volatile storage that you change at every boot (a counter, or a random value you save); or, with neither, from a mix of values
that vary between boots (uninitialised RAM, ADC conversion noise, a free-running timer read when the first USB or UART activity arrives). A
timer read at a fixed point of the start-up code reads the same at every boot and is not such a value. Never a constant, and do not leave a
library default that is the same at every boot.

**The clock** (core §2.6a): ns since boot (u64), never decreasing and never wrapping while the boot_id is the same. If the hardware counter is
narrower than 64 bits (a 32-bit microsecond counter wraps after about 71.6 minutes), extend it in software with a wrap count, and read it
often enough (from the main loop) not to miss a wrap.

**session_id** is chosen by the host; the probe only remembers the last one and never returns it (core §6.4).

## 11. Probe settings and saving

For a probe that lists `oep.probe.config` ([probe settings](../interfaces/oep-if-probe-config.md)):

- **Keep the items in their one form per tag** (critical bit cleared) and compute the hash over the canonical form
  (probe settings §2). Check your hash against `tests/vectors/probe_config_hash.json`.
- **A save replaces the whole, and a power loss in the middle leaves either the previous save or the new one readable** (probe settings §2).
  Two ways to get that:
  - two copies (A / B), each with a sequence number and a CRC: write the new copy over the older one, verify it, and at boot use the valid copy
    with the higher sequence number;
  - a key-value store that replaces one value atomically: store the whole saved form as one value.
  Do not write when the content is the same as the save (probe settings §2), so that a host that saves needlessly does not wear the flash.
- **A save holds (name, instance, revision) for every fn its items point to**, and is rewritten to the current fns at boot. If one is missing or
  has another revision, or a saved bind's port is no longer a serial port, the whole save is not applied (unreadable, reason 2).
- **Boot order**: make the save the current settings, apply disable, apply idle (outputs with their strength), the plan, uart, then start the
  at-boot attaches and connect the binds (probe settings §2, §3.1).
- **max_bytes** (describe 0x40) is the canonical form's length that can always be saved; subtract what you need for the identifier table.
- **Safety**: saved settings drive lines at every boot without a host, and before they are applied the pins are in the MCU's reset state
  (probe settings §5). Tell users that a line whose wrong level is harmful needs an external pull of its own.
- **boot_reset's hold time** is fixed at `slot_retry_reset_hold_ms` (20 ms). If a board needs a longer reset hold, the way to add it later is a
  new item tag keyed by the slot (core §2.3: a new item tag is one of the ways OEP grows), with no revision change.

## 12. Parts that handle the target

General rules from the reference probe.

- **Run until halt**: before running code the host gave, set the debug control bits that make ebreak enter debug mode in every privilege
  mode, and run in the most privileged mode, so that the final ebreak halts instead of jumping to the trap vector. The host masks interrupts
  through the registers it passes.
- **Consecutive words**: use the debug module's autoexec for block reads and writes, and keep the address it leaves behind to count how many
  ran (to catch lost or doubled steps).
- **A wire speed is verified only at the target's clock of that moment.** A reset can drop the target to a slower clock, at which the speed
  chosen earlier garbles writes. Reset at the slowest speed, and choose the speed again after the hart has halted. The same for attach with
  reset: switch to the slowest speed before releasing reset. Re-measure from slow to fast without the wake pattern when the wake would reset the
  target. A garbled read can make DMSTATUS look like "running": treat values whose version field does not match as noise.
- **How a wire rests between frames is part of the wire's definition** ([wire and debug](../interfaces/oep-if-debug.md) §3.1, §3.2, §5) and, where idle_clock
  allows, the host's choice per target. Follow the wire's section, and after a failed exchange rest the lines undriven (debug §2).
- **Drive debug wires at the weakest output strength the wire's timing allows.** Sharp edges on a debug wire couple into neighbouring fixture
  lines (a nearby SPI or UART target loses or shifts bits while the console runs). Set it on every PHY and every port. The strength of wire and
  fixture lines is the probe's choice (fixture §1.1).
- **A fixture that breaks only while the debug wire is busy**: suspect the wire's edges before the CPU. Run the same procedure with the wire
  resting and busy, look at the drive strength first, and measure before and after a fix with the same procedure.
- **After fixing a problem, look for the same mechanism elsewhere** (other PHYs, other SoCs, fixtures that drive lines, the client and the fake),
  and record which places are fine and which are unchecked.
- **Do not reissue resume or run** ([wire and debug](../interfaces/oep-if-debug.md) §4.2, §4.4). A target that needs a second resume request, or that does not
  report all-resumed, is handled by the host: target-specific knowledge in an interface with a generic name breaks core §13 rule 8.
- **Changes that speed up block loops can change timing on the wire.** Measure across targets before keeping them.

## 13. Values the reference firmware declares (where the normative text leaves the choice)

- **model** (core §7.5, 0x41): the chip name in lowercase without hyphens (`esp32p4`, `esp32`, `rp2040`, `rp2350`), the same as the Arduino profile
  name.
- **max_op_ms** (0x4D): 10000 (registry `[reference]`).
- **chip** (0x4C): part and revision, for example `esp32p4 v1.3`, `rp2350 v2`.
- **unit_id**: the chip's unique number in lowercase hex.
- **UART bridge boot speed**: `uart_bridge_boot_baud` (§5).
