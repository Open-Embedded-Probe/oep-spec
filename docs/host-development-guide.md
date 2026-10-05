# Open Embedded Probe — host development guide

[日本語](host-development-guide.ja.md)

Status: **guide** (not normative; updated 2026-10-06 to the normative text of that date). How to write a host: practical
ways to meet what [OEP core](oep-core.md) and the `oep-if-*.md` documents require, and the traps found in practice. Where this
guide and the normative text differ, the normative text is right. This English text is authoritative; the Japanese
version is its translation. The first steps (the smallest host, with bytes) are in [getting started](getting-started.md);
the checklist of what a host must do is in [conformance](conformance.md) §2. For the probe side, the reference library has its own
guides: [getting started](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/docs/guide/getting-started.md) and
[writing a probe](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/docs/guide/writing-a-probe.md) (oep-probe-arduino).

The sections run from the first things a host does (opening a port, frames, discovery, sessions, refusals) to the optional
procedures (port speed, power and reset, finding pins, writing flash).

## 1. Opening a probe without resetting it

- **Open with DTR and RTS both asserted** (the default of most serial libraries). core §3.4 asks the host to keep them asserted
  while the port is open; the probe uses neither to decide anything.
- **If you must deassert them, deassert RTS before DTR.** Many boards wire DTR / RTS to an auto-reset circuit, and the state
  RTS = 1, DTR = 0 resets the MCU. Deasserting DTR first passes through that state.
- Nothing needs to be done on close.
- Do not keep DTR deasserted while using the port: some USB serial stacks stop sending while DTR is low (core §3.4 leaves what a
  probe does then undefined).
- Do not open a probe's port at 1200 bps: several USB stacks treat opening and closing at 1200 bps as a request to enter the
  bootloader.
- These held on every board measured on Linux: USB-UART converters with an auto-reset circuit (CH340, CH343), a built-in USB serial
  (ESP32 USB-Serial/JTAG) and a native USB stack (RP2350). Windows and macOS were not measured.

## 2. Serial ports are always COBS; bytes outside frames are noise

- Every port the OS sees as a serial device (UART bridge, USB CDC, built-in USB serial) speaks COBS + CRC-16 (core §3.1). The
  frame is chosen by the kind of transport, never by VID:PID.
- Raw bytes (the target's console, etc.) arrive on the same port together with OEP answers (core §3.4). Bytes that do not
  form a frame, candidates whose CRC does not match, and answers with a corr you are not waiting for are noise: discard them.
  **Do not resend because you saw noise.** The absence of an answer is decided only by the wait (core §3.1, §4.4); the resend is
  the single one of core §5.2.
- Always enclose a frame in 0x00 on both sides. Without the leading 0x00 the probe passes the head of the frame on as raw bytes.
- While your session holds the port, raw transfer on it stops (core §3.4). Read a console through OEP's read instead.

## 3. UART speed

A UART bridge probe always starts at the boot speed, `uart_bridge_boot_baud` (115200 bps) 8N1 without flow control (core §3.4; names in
backquotes are keys of `registry/oep-v1.toml`, which holds every number). port_speed (core §3.5,
optional) raises it for the duration of a session; whether to raise it, the candidates and how to check them are the host's
choice (§17). If that is still not enough, use a faster transport of the probe (its native USB).

On a UART bridge, and on any serial port you cannot tell from one, every answer wait adds the transfer time of core §4.4. Before the
first confirm answer on the port you do not know max_frame yet: use `min_max_frame` (64) in the formula, and after it the max_frame of
the latest confirm answer on that port (core §4.4).

## 4. Finding a USB probe, and the interim clues

- By the normative rule (core §3.3) a host identifies an OEP probe automatically only by the project's USB VID:PID, which is
  listed in the registry when it is obtained. None is listed now, so the normative rule alone identifies no device. A probe
  named by its unit_id (the device whose USB serial number equals the unit_id) and a port the user chose can always be opened
  (core §3.3).
- Until then, as **interim clues**, a host may take as candidates the USB devices that match any of:
  - iProduct starts with `OEP`;
  - an interface with class 0xFF / subclass 0x4F / protocol 0x45;
  - a HID interface with usage page 0xFF4F.
- Open the candidates one by one and check each with the probing rule of core §3.3: the first thing sent is a confirm only,
  and if no valid confirm answer arrives within the wait, close the device and send nothing else. Only a candidate that gave a
  valid answer is an OEP probe.
- Names and vendor-class values can collide with other products by chance. These clues are therefore not part of the
  specification, and they go away once the project's VID:PID exists. Even now, never decide that a device is a probe from a
  clue alone: always confirm.
- The reference firmware currently runs with a temporary USB ID (the board's default VID:PID), which may not be used for
  distribution. Its iProduct starts with `OEP`, so the clues above find it today ([USB identification](usb-identity.md)).

## 5. session_id and discovery

- Choose a new unpredictable 32-bit random session_id for every open; never 0, a counter or a fixed value (core §6.1).
- **A one-shot CLI keeps its session_id per probe, keyed by unit_id** (core §7.6). On USB ports the probe exposes itself, the
  serial number is the unit_id, so it is known without opening the port. On ports where the serial number cannot be chosen
  (built-in USB serial, USB-UART converters), read it from describe.
  The next command uses the same ID; if it passes, nobody touched the probe since the previous command. If rejected
  `expired` comes back, the lease ran out and the resources were removed: start over from open and set up the plan, attach and
  subscriptions again (do not continue silently). If `no_session` comes back, look at confirm's boot_id to tell a reboot from
  another host, and check the attach state and the target's identity again. In the same way, an open with your last session_id
  answered resumed = 0 means the probe no longer knows that session: list again before you use a remembered fn mapping (core §6.5).
- **Discovery procedure**: list the USB devices; open those with the project's VID:PID (none until it is in the registry), those
  whose serial number equals a named unit_id, and those that match an interim clue of §4 (core §3.3). The serial number is the
  unit_id. Choose the ports inside the device by the interface descriptors (vendor bulk: class 0xFF / subclass 0x4F / protocol 0x45;
  HID: usage page 0xFF4F, usage 0x45; every CDC: a serial port). After opening, send a confirm first and nothing else (close if
  there is no answer), take boot_id and the limits, and check that describe's unit_id equals the serial number. A monitor without
  the lock learns of a reboot from confirm's boot_id.
- **Check the limits before you use them.** In the confirm answer, max_frame is 64 or more, window is max_frame or more and
  max_inflight is 1 or more; outside these bounds, send nothing more on that transport and report the values (do not clamp them,
  core §7.1). In the describe of fn 0, max_op_ms is 1 to `max_op_ms_max` (600000 ms); 0 or more than that means the probe does not
  conform: do not use it (core §4.4, §7.5). Your answer waits are then bounded.
- Tools that stay open for a long time (an interactive CLI, a monitor) keep the lock with keepalive or ordinary requests. Keep
  sending keepalive while waiting at a confirmation prompt, and before each destructive step check that the session is still
  alive (no `no_session` / `locked`).
- **A monitor takes the lock only while it sends input** (open → write → end). Reading needs no lock, and a monitor that holds the
  lock makes a write from another terminal fail with `locked` (the most common combination during development).
- Send end when you finish (the lock is released by expiry anyway).

### 5.1 Several transports of one probe

- One probe can show several transports (vendor bulk, HID, serial ports, TCP). They share one session and one lock (core §3.3).
  Group them by the unit_id of fn 0's describe, compared ignoring ASCII case, and never group by a unit_id that starts with `x-`
  (core §7.5).
- When you have a choice, use vendor bulk, then HID, then a serial port (core §3.3): serial ports also carry raw bytes, and their
  receive capacity is limited (core §3.4).
- Send all role 0x81 requests of one session on one transport (core §3.3). Lock-free requests may go on another (for example a
  HID port that reads describe and state while a debugger holds the vendor bulk port).
- Each transport has its own max_frame, window, max_inflight and protocol revision (core §4.4, §7.1): confirm on each transport you
  use.

## 6. Exclusive open and taking over the lock

- **Always open a serial port exclusively** (Linux / macOS: `ioctl(TIOCEXCL)`; Windows opens exclusively already; core §3.3).
  Otherwise answer bytes can go to another process and the link does not work. Advisory locks (`flock`, which some libraries
  call "exclusive") do not stop tools that ignore them, so set TIOCEXCL after opening. root bypasses TIOCEXCL.
- A libusb / WinUSB claim is exclusive by the OS.
- **The real exclusion is the session_id** (core §6). How to take over the lock depends on the number of the probe's
  transports (the transport tags of fn 0's describe):
  - **A probe whose only transport is one serial port**: once you have opened it exclusively, no previous owner process can
    hold the port, so you may take the lock at once with open's force.
  - **A probe with several transports**: read the remaining time with lock_state and wait only that long (with an upper bound of
    a few seconds). If the owner keeps renewing its lease, do not wait: report "in use". Use force only when the user asks for it
    explicitly (force is not authentication, and TCP is used only on trusted connections, core §3.1, §6.4).
- Lease: short for interactive tools (2 to 3 s), longer for tools that hold the probe a long time, such as a test session
  (10 s, renewed by keepalive).

## 7. Brokers

When several tools on the same PC use one probe at the same time, a broker on the host side holds one session with the probe
and multiplexes the tools' requests (renumbering corr, not forwarding the tools' open / end to the probe, removing a tool's
resources when it disconnects). The probe still sees one transport and one session. Between the tools and the broker, the TCP
form of the specification (`length(u16) message`, core §3.1) can be used. A broker that answers the session ops itself and
relays everything else follows the relaying-broker rules of core §3.1 and §5.2 (transport index 0xFF in its confirm, a corr map
per client connection).

## 8. Matching answers and resending (what core §5.1 and §5.2 require)

- **Do not accept an answer whose corr does not match; discard input and resynchronise** (core §5.1). On some USB paths the
  leftover of a cancelled transfer can arrive as the next answer (seen through a USB-over-IP layer).
  Vendor bulk, HID and TCP frames have no CRC, so the corr check is the defence there.
- **Advance corr by 1 per request** (role 0x01 requests count too; after 65535 comes 1; 0 is not used; core §4.1). The same corr
  is used again only for a resend.
- When an answer was broken or did not arrive, **resend once with the same corr** (`resend_max` = 1; state-changing requests too, core §5.2). The
  probe returns the remembered answer, so nothing runs twice.
  - result_lost: the probe does not remember the answer (it was too large, or fell out of the table). You cannot tell whether it
    ran: read the state again to find out.
  - corr_reused: a numbering mistake in the host.
  - If you sent unsubscribe and end during recovery, do not resend the original request.
- **When the resend also gets no answer, the transport has failed** (core §5.2): the outcome of that request is unknown, and the
  requests outstanding on that transport fail with it. Do not send the next request as if nothing happened. On every kind of frame,
  COBS included, recover first: wait for quiet input and confirm until the answer with your own corr arrives (core §5.1), or close
  and reopen the port. A changed boot_id in that confirm means a reboot (start over, §5). Then read the state before you repeat a
  state-changing request.

## 9. What to do for each refusal

rejected means the request was not accepted; completed failed / partial means it ran and did not fully succeed (core §4.2). The probe
gives the first reason that applies in the order of core §4.3, so the reason says what to fix first. Unknown reasons are failures (core
§2.4).

| reason | Meaning (core §4.3) | What the host does |
|---|---|---|
| unknown_function (0x01) | No such fn (also an fn named inside the payload) | Your fn map is stale or wrong: list again (fn numbers hold only while the boot_id is the same, core §7.2). Do not use the interface |
| unknown_operation (0x02) | The fn has no such op | An optional op the probe does not implement (core §1.2). Look at describe (features) before using optional ops |
| malformed (0x03) | The request's form is wrong | A bug in your encoder or a value excluded for every revision. Do not resend it unchanged; fix the request. Log the request bytes |
| unavailable (0x04) | Cannot be done in the current state or with the current resources | Read the TLVs: cause (1 pin in use, 2 count limit, 3 not enough storage, 4 bound into a group, 5 held by the settings, 6 wrong state), channel, holder_fn, holder_kind (1 plan, 2 wire connection, 3 slot, 4 bind, 5 settings plan, 6 settings disable, 7 settings idle). Show them to the user; release your own resources or change the order. Cause 5 means the probe's settings hold it: change the settings, not the request. Unknown cause / holder_kind values are shown as unknown (core §2.4) |
| busy (0x05) | Reserved (core §10) | Treat as a failure |
| window_exceeded (0x06) | window / max_inflight exceeded | Your pipelining exceeded the probe's limits of this transport. Wait for answers and send it again with a new corr (core §5.2: a corrected request uses a new corr) |
| no_session (0x07) | The lock is free but this session_id is not the last one | Another session came between, or the probe rebooted. Start over from open; confirm's boot_id tells a reboot |
| locked (0x08) | Another session holds the lock | The payload gives the remaining ms and maybe the owner text. Wait, report "in use" with the owner, or take it with force only when the user asks (§6) |
| session_required (0x09) | A state-changing request without session_id | A bug: send it with role 0x81 and your session_id |
| no_connection (0x0A) | The resource number is unknown | The connection / stream was closed or the probe rebooted. Discard the number and create the resource again (attach, open). Check long-held numbers with the listing ops (core §9) |
| unsupported (0x0B) | In the definition, but this probe cannot handle it | The payload's tag says what: 0x00 = a value in the fixed part, otherwise the critical TLV's tag as received; channel / index TLVs may say which element. Look at describe and choose something the probe declares; do not resend unchanged. For confirm, TLV 0x01 gives the revisions the probe supports (core §7.1) |
| result_lost (0x0C) | The answer to a resend is not remembered | You cannot tell whether it ran: read the state again (core §5.2) |
| corr_reused (0x0D) | Same corr, different request | A numbering bug in the host (core §4.1) |
| expired (0x0E) | Your lock ended by lease expiry; the resources were removed | Open again (resumed = 2), then set up the plan, attach and subscriptions again. Do not continue silently (§5) |

- **completed failed / partial**: the payload is the op's (for wires and targets, `status` and `done`, [common parts](oep-if-common.md) §3).
  status line usually means: lower the speed and attach again; wait: continue later from `done`; fault: read and clear the cause; timeout:
  review the limit; state: put the target in the needed state first. Unknown status values are failures.
- Interface-specific reasons (0x40 to 0x7F) are defined by each interface; none are defined in v1.

## 10. Revisions, TLVs and unknown values

- **Protocol revision**: send the range you handle in your first confirm on a transport; afterwards send `min_rev = max_rev =` the revision
  in use (core §7.1). On rejected unsupported, TLV 0x01 says which revisions the probe handles. Each transport (each TCP connection) has its
  own revision.
- **Interface revisions**: list gives (name, instance, revision) per fn. Do not use an interface whose revision you do not know (core §2.7).
  A probe may expose an older revision as a separate fn; choose the one you know. Instances are numbered per (name, revision) (core §7.2).
- **Reading answers**: after the fixed part comes a sequence of TLVs. Skip tags you do not know. For a tag that does not repeat, use the first
  one. A TLV value, an event payload or a sequence element longer than you know: read the part you know and skip the rest; shorter than you
  know: broken (core §2.3). describe values are closed: they are never longer than their definition (new information comes under new tags).
  A TLV with bit 7 set in an answer is an unknown tag.
- **Sending requests**: set the critical bit on a TLV when the request means nothing without it, and always on TLVs an interface says are sent
  critical (pins, speed limits, safety items; core §2.3). Do not extend a request TLV's value at the end (core §2.3). Never repeat a tag that
  does not repeat.
- **ignored** (tag 0x7F in the answer): the numbers of the non-critical TLVs the probe ignored, in request order. An entry 0x00 means "more were
  ignored": treat every TLV not listed as possibly ignored (core §2.3).
- **Unknown values in answers**: an unknown resolution, outcome, status or reason is a failure; an unknown event kind is discarded (its seq
  still counts); other unknown enum values (cause, holder_kind, scan kinds) are shown as unknown; reserved flag bits are ignored (core §2.4).
- **Booleans and text**: read any non-zero boolean as true; replace control characters and invalid UTF-8 before showing text from an answer
  (core §2.1).
- **Experimental values** (0xF0 to 0xFE in u8 enums, ops 0xF0 to 0xFF) are for trying things out; a released host does not send them (core §2.5).

## 11. Operations that take time

- **v1 has no long operations** (core §10 is reserved). Every op ends with one answer. For ops that take time (run, capture
  configure, save, attach), wait for the answer; the wait is set by the op's arguments (core §4.4).
- During run the probe answers nothing else ([wire and debug](oep-if-debug.md) §4.4). Keep the timeout well below the lease and the
  answer wait.
- In work that sends many requests (writing flash), keep the lock with ordinary requests or keepalive so the lease does not run out.

## 12. Notifications

- Subscribing needs the lock, and the subscription ends with the lock (end, expiry, force; core §11.3). A host that only monitors reads the
  raw bytes of a bound serial port instead ([probe settings](oep-if-probe-config.md) §1.2), or polls the lock-free read ops.
- Subscribing to the same fn again replaces the subscription atomically; seq starts from 0 at every subscribe. A subscribe to an fn that emits
  nothing is rejected unsupported (core §11.3).
- **Dispatch by role** (core §11.1): only answers (0x02) are matched by corr; events (0x05) and data (0x06) carry fn in bytes 1 to 2. Keep the
  code that waits for answers and the code that reads input on time even while notifications keep coming.
- **seq** counts frames per fn (u16, wraps). A gap means notifications were lost inside the probe or on the way. For data, the stream
  `position` also shows what was lost: if a frame's position is not the end of the previous one, the bytes in between are gone (core §11.2,
  [common parts](oep-if-common.md) §1.5).
- **Choosing min_bytes / max_delay_ms**: the probe sends when min_bytes have accumulated or max_delay_ms has passed since the first byte (0
  disables that condition; both 0 sends at once). Larger batches mean fewer frames; a shorter delay means lower latency. On serial ports keep
  min_bytes at `host_serial_min_bytes_max` (2 KiB) or less and the total expected volume of answers outstanding at
  `host_serial_inflight_max_bytes` (6 KiB) or less, because the OS driver may silently
  drop bursts (core §3.4).
- **Heartbeat**: subscribing to fn 0 delivers heartbeat events (kind 0x01: boot_id, uptime_ns) every max_delay_ms (`heartbeat_default_ms` if 0; the
  probe may round periods below `heartbeat_min_ms` up to it). A changed boot_id means a reboot.
- Notifications go to the transport the subscribe came from. An open with the same session_id on another transport moves them there (core
  §6.2).
- Capture's streaming has its own rules: the probe drops new data when it has no room, keeps sending what it captured before stop, and the host
  has everything when the end of the received positions equals status's write_pos after stop ([capture](oep-if-capture.md) §2.1). Keep the lock
  alive while receiving.

## 13. plan and pins

- The plan is per fn (core §8). plan_apply replaces only the assignments of the fns it names, and the plans of other fns stay. You
  can add a capture while a UART keeps receiving. Release with plan_release, listing fns (n = 0 releases all).
- Taking a pin another fn or a connection holds is rejected unavailable, and nothing changes (core §8.1).
- A released pin goes to the idle state: the idle of the probe's settings, or Hi-Z (core §8). For a pin where the peer's input would
  float because of the fixture's wiring (a TX connected to the DUT's RX), set an input-with-pull-up idle in `oep.probe.config` and save
  it (§15).
- The plan is a session resource: it stays on an explicit end and is removed on lease expiry and force (core §9). A plan from the
  settings stays.

## 14. Consoles

- A monitor after flashing reads "from the last reset mark" (common §1.2 from 3), so it does not show old unread output.
- A monitor that closes and comes back reads from the position it read last.
- If the answer's start is ahead of the requested position, the difference is what was lost; show it.
- For display times use the time of reception (the probe has no per-byte time).

## 15. Using the probe's settings (`oep.probe.config`)

The settings are a sequence of items, each with a key; set replaces items per key, unset deletes keys, save writes the whole current settings
([probe settings](oep-if-probe-config.md)). A host keeps the settings it wants in its own file and brings the probe to them:

1. **Look**: list must contain `oep.probe.config` (a probe without it handles no settings). describe gives items (the tags it handles),
   storage (max_bytes; 0 = it cannot save), slots_max and bind_modes.
2. **Compute the hash of the settings you want**: sort the items by tag, then by key compared as numbers field by field (plan: fn, role,
   channel), clear the critical bit, encode each as a TLV in the unique form of core §2.2, join them, and take the CRC-32 of core §5.2
   (probe settings §2). Check your code against `tests/vectors/probe_config_hash.json`. No items gives hash 0.
3. **Compare with get** (lock-free). Every page of get carries the same hash. **If it equals yours, do nothing.** If the hash changes
   between pages, read again from the beginning.
4. **If it differs**: open a session and send set with the items you want (set replaces per key and keeps keys not sent), and unset the keys
   present in get that you do not want. Read the items from get to find them. The answer of set / unset carries the new hash; it must now
   equal yours. A set is atomic: if any item is refused, nothing changes (probe settings §2; the refusal table is there).
5. **Save only when it changed**: read state (lock-free); if storage_state is 1 and storage_hash equals your hash, the saved settings are
   already these, so do not save. Otherwise send save. Saving writes flash, wears it, and blocks other requests while it writes (up to
   max_op_ms). Never save in a loop or on every run.
6. **Check the effect**: the automatic attach and the consoles of binds start after set completes and are not rolled back; read slot_state
   and bind_state with state (probe settings §3.3).
7. **After a firmware update**: if state shows storage_state 2 (unreadable) with reason 2 (an interface a saved item points to is missing,
   has another revision, or a bind's port is no longer a serial port), the saved settings were not applied. Set them again from your file and
   save. Reason 1 means the stored form could not be read; reason 3 that applying was refused (resources conflict).

Points to remember:

- There are no defaults: what is not set is not done (probe settings, top). A settings plan belongs to the settings, not to a session:
  plan_release does not release it, and plan_apply on that fn is refused (core §8).
- idle: give a pin whose peer input would float an input-with-pull-up idle; give a power channel an output idle at the powering level (§18.2).
  An output idle keeps driving whenever the pin is free, also at boot: check the wiring before saving one. Channels with an idle item are left
  out of scan with count = 0 and of attach without pins ([wire and debug](oep-if-debug.md) §1).
- disable: list the channels that are not brought out or are wired to other parts, so the probe never drives them.
- Lines named with labels are found by the search of probe settings §1.3 (§18.1).
- erase deletes the saved copy only; the current settings stay until the next boot.

## 16. Testing with the fake probe

oep-client-python includes a fake probe that answers as the specification says, without hardware. Use it as the first peer while
writing a host, and in your tests.

```sh
pip install oep-client-python
python -m oep_client.fake_serve --pty                      # a serial port: COBS frames and raw bytes on one pty
python -m oep_client.fake_serve --tcp 0 --framing length   # a TCP transport: length(u16) message
```

- The first line on stdout says where to open (`PTY /dev/pts/N` or `PORT n`). The program ends when its stdin closes, so a test's child
  process never stays behind; `--once` ends it after the first TCP connection closes.
- `--profile` chooses the probe it imitates (its interfaces, pins and limits); `--help` lists the profiles and options.
- Faults for testing recovery: `--drop N` does not send the N-th answer once (the request did run, so a resend gets the remembered answer),
  `--corrupt N` sends the N-th answer with a broken CRC once, `--noise TEXT` writes raw bytes in front of every answer.
- State for testing discovery and settings: `--slot`, `--bind`, `--label CH=TEXT`, `--target-id`, `--absent N`, `--no-port-speed`, and
  others (`--help`).
- The fake follows the specification where it decides; where the specification leaves a choice to the probe, the fake's choice is one example.
  A host that works only with the fake may still meet probes that choose differently: test against a real probe before release.
- `oep dump --port <port>` shows list and describe of every interface of the fake or of a real probe.

## 17. Choosing the serial port speed (informative)

core §3.5's port_speed defines **only the handshake** (the op's form, the 3 states of a port, when the probe goes back by itself,
the host obligations). Which speeds to try, how to check them, the criterion for passing and the criterion for falling back while
in use are the host's. This section is a **reference procedure**, written so that a host can be built from it alone. It has two
levels. **The minimal form (§17.2, no checking)** switches to one candidate, confirms and commits (about 50 ms) and suits even a
short CLI. **The form that adds checks per use (§17.3)** is the full procedure for hosts that need a transfer budget (streaming
capture, estimating write times). Both satisfy core §3.5. A host may simplify further (one candidate, one flow, skipping
criteria). Where this differs from the normative text, the normative text is right. The numbers (5 %, 10 %, 16 frames, 3 s, 60
frames, 32 KiB, 1 s, 2 s, 1 day, 30 days) are guides taken from measurements (§17.5), not rules.

### 17.1 Balance (raise or not)

Raising the speed costs a negotiation up front. Do not raise it without a return. The cost differs greatly between the levels.

- **Cost of the minimal form (§17.2)**: the try round trip + the switch and the `port_speed_switch_wait_ms` wait + one confirm + the commit round trip,
  **about 50 ms**. Throughput is not measured. Even on a line that does not pass, (a) / (b) of §17.2 show it within 1 s of use, and
  what is lost is the return to the boot speed (at most `port_speed_idle_max_ms` + `port_speed_confirm_extra_ms`).
- **Cost of the form with checks (§17.3)**
  - Checking a candidate: 16 frames per flow (payload max_frame − 16 bytes), about 0.25 s at 500000 and 0.15 s at 921600. Three
    flows take 0.5 to 0.7 s.
  - A candidate that fails adds the wait for the probe to go back after verify_ms (about 2 s) per candidate.
  - The confirm after switching (`port_speed_switch_wait_ms` + a round trip, small).
  - In total 0.5 to 1 s when the first candidate passes, plus k × 2 s for k failing candidates.
- **Return**: at the boot speed 115200, 1 s ≈ 10 KB. About 3 to 4 times that at 500000, 4.5 to 5 times at 921600, 7 to 8 times at
  1.5 M (when it passes).
- **Guide**:
  - The minimal form costs almost nothing, so **it pays even for a short session** that moves more than a few KB. A CLI that only
    runs describe and a few requests has no reason to raise.
  - Add checks only if the transfer the session would do at the boot speed takes **more than 3 times** the negotiation cost (0.5 to
    1 s + 2 s per failing candidate); otherwise stay with the minimal form.
  - Hosts that hold the port a long time (a broker, capture, flashing, log reading) raise by default. Only those that need a transfer
    budget (streaming capture, estimating write times) add checks. Where a broker holds the port, the broker does all this (the
    clients do not know, §7).
- **Records make later sessions cheap**: keep, per port + unit_id, the speeds that passed / failed with an expiry (§17.4). Next time,
  put a speed that passed first, so one check (0.2 to 0.7 s) is enough. Leave out speeds that failed until they expire (1 day).
- **Limit the candidates tried at once**: each candidate takes about 1 s, plus the verify_ms wait when it fails. After ordering by
  the records you may cap the number tried (for example 2 for a capture host). Fallback targets while in use (step 4 of §17.3.2) come
  only from candidates within that cap.

### 17.2 The minimal form (no checking)

The lightest form that works with the handshake alone: one candidate, no checking of flows, no throughput measurement. It suits
small two-way flows such as a console or debugging, and short CLIs (500000 passed small round trips on both converters measured,
§17.5).

1. One candidate (for example 500000). If the record (§17.4) says it failed for this port + unit_id, do not raise. At the boot speed,
   send port_speed (try, verify_ms 2000, idle_ms 3000) and check that your port can produce the answer's baud (do not raise on
   rejected unsupported; if you cannot produce it, wait verify_ms for the probe to go back).
2. Switch, wait `port_speed_switch_wait_ms`, and send confirm up to 3 times with a 100 ms wait. If one answers, send port_speed (commit). About 50 ms so
   far. No checking and no throughput measurement. If none answers, wait out verify_ms, confirm at the boot speed, and record this
   speed as failed.
3. While in use, watch only two things. (a) An answer does not arrive within the wait (core §4.4) → go back to the boot speed and
   repeat confirm (core §3.5 obligation 5; this converges whether the probe went back first or is still at the raised speed).
   (b) Resends (§8) fail several times in a row (for example 3) → send port_speed (revert) and go back to the boot speed. In both
   cases **do not raise again to that speed or a faster one in that session** (with one candidate, stay at the boot speed; with
   several, fall back to the next slower one as in step 4 of §17.3.2).
4. Record "this speed failed" per port + unit_id (§17.4) and do not try it next time.
5. Otherwise follow the obligations of core §3.5: keepalive or ordinary requests at intervals shorter than half of idle_ms
   (obligation 4), and switch to the boot speed on the answer to revert or end (obligation 6).

This satisfies the handshake of core §3.5 (obligations 1 to 8). The negotiation costs almost nothing (about 50 ms), so it pays even
for a short session with a 4-times return. What it gives up is only the number "how fast this speed really
is": on a line where confirm (a small frame) passes but large frames break, (a) or (b) appears within 1 s at the first large
frame and the host goes back to the boot speed. Nothing is lost and no state diverges (the probe goes back after `port_speed_broken_max` broken
candidates with no good frame between, and obligation 5 brings both sides together). Add the checks of §17.3 only where a transfer
budget is needed.

### 17.3 The form that adds checks per use

The full procedure for hosts that need a transfer budget (streaming capture, estimating write times, reading large logs). It adds to
the minimal form: checking the flows used, a baseline at the boot speed, thresholds, a 3-second window while in use, and records.
All numbers are guides (§17.5).

#### 17.3.1 Flows and candidates per use

A flow = a direction (probe → host / host → probe / both) and a concurrency n (the term of core §3.5). probe → host is driven with
link_source, host → probe with link_sink (core §12). Check **only the flows you use**.

| Use | Flows used | Example candidates (combinations that were measured; not rules) |
|---|---|---|
| Writing | host → probe, n = max (the smaller of the probe's max_inflight and the host's receive limit, core §3.4) | the fastest that passes (1500000 → 921600 → 500000) |
| Capture / reading logs | probe → host, n = max | 921600 → 500000 |
| Console / debugging | both, n = 1 to 2 | the single candidate 500000 |

- Order the candidates fastest first. If the record has a speed that passed, put it first.
- A converter that can only produce integer divisors of its clock may not produce some speeds (for example 921600): confirm does
  not come back. Look at the try answer's baud (the speed actually applied); if your port cannot produce it, drop that candidate, and
  if confirm does not come back, wait verify_ms and go to the next candidate (for example, a converter that emulates an FTDI chip on a
  CH552 cannot produce 921600).

#### 17.3.2 The full procedure (baseline → check → in use → record)

**Frames counted** (on the host's receiving side; core §3.5's "broken candidate" is the probe's count, a different thing): **good**
= an answer or notification that decoded with a matching CRC. **Broken** = a candidate closed by 0x00 that did not decode or whose
CRC did not match (an answer broken on the line looks like this to the host; it cannot tell which request it belonged to, so on
the request side it is also "lost": to avoid counting one accident twice, count either broken or lost consistently; the procedure
below counts lost). **Lost** = a request for which no good answer arrived within the wait. **Ratio** = lost / (good + lost). Right
after switching speed, broken frames before the first good frame at the new speed are not counted.

1. **Preconditions**: confirm and describe done at the boot speed, port_speed declared, the lock held. Send from that port (core
   §3.5 obligation 1).
2. **Baseline** (how the boot speed breaks; converters can drop frames even at the boot speed, so absolute counts are not used):
   - The ratio of what this session actually moved at the boot speed. If there is none, measure it by moving 60 frames with the same
     flow as the one used.
   - **Measure the baseline at the n you will use** (a converter that breaks at n = 2 does not show it at n = 1).
   - A flow whose baseline exceeds 10 % is measured again at n = 1; if it no longer exceeds it, cap that flow at n = 1. If it still
     does, do not raise on that port.
   - Simplification: you may take the baseline as 0 without measuring (the thresholds are then only the floors).
3. **Checking each candidate** (in order; at most about 1 s per candidate):
   1. At the boot speed send port_speed (try, baud, verify_ms, idle_ms). verify_ms is at least twice the whole check (number of flows
      × frames × one round trip + confirm) and shorter than the lease (guide 2000 ms, at most lease − 1000 ms; if it is too short
      the probe goes back in the middle of the check, which the host sees as "no answer"; if both cannot hold, reduce the frames per
      flow). idle_ms is at least twice the keepalive interval you will use (at most 3000 ms). On rejected unsupported go to the next
      candidate. If your port cannot produce the answer's baud (the speed actually applied), send nothing, wait verify_ms (the probe
      goes back) and go to step 6.
   2. Switch to the requested baud (or the answer's baud), wait `port_speed_switch_wait_ms` or more (core §3.5 obligation 2), and send confirm up to 3
      times with a 100 ms wait. If none answers, wait until verify_ms has passed and go to step 6.
   3. Move at least 16 frames per flow used, counting broken and lost. After a lost frame, resynchronise with confirm before
      continuing.
   4. Per flow, the candidate **fails when lost ≥ 3 and the ratio exceeds the threshold max(baseline × 2, 5 %)** (so that one
      accident in few frames does not jump the ratio: 1 in 16 is 6 %). If it fails and n > 1, move that flow again at n = 1; if it
      passes, it passes with n = 1 as the cap. Otherwise it fails. **The candidate fails if any flow used fails.**
   5. If it passes, send port_speed (commit, same baud) at the new speed. If the answer arrives, use that speed with the n caps. If
      not, go to step 6 (the probe has gone back).
   6. If it fails, send port_speed (revert) at the new speed (no answer needed). Go back to the boot speed and repeat confirm until it
      passes, for at most `port_speed_idle_max_ms` + `port_speed_confirm_extra_ms` (core §3.5 obligation 5). If it does not pass, it is a link failure. Do not
      use this candidate in this session (fallback targets while in use are then only slower candidates), and record it as failed
      ("unknown" within the settling time, §17.4). Go to the next candidate.
   - This 16-frame check is a **quick gate**: it misses lines that break later in long transfers. The probation of step 4 catches
     them.
4. **In use**:
   - Send keepalive or ordinary requests at intervals shorter than half of idle_ms (obligation 4).
   - **Probation**: from the commit until **32 KiB in total have moved in both directions at the new speed and 1 s has passed since the
     commit**. Judge the frames of that period by the criterion of step 3-4 (broken or lost ≥ 3, and the ratio above max(baseline ×
     2, 5 %)). If it is exceeded, or an answer does not arrive within the wait, treat it as **a failed check** (record it as failed in
     the check, not as a breakdown in use) and fall back at once (below). Good frames that complete the probation may update the record
     to "passed".
   - After the probation, look at the ratio over **the last 3 s** (a window in time, not frames; with fewer than 50 frames in 3 s, do
     not judge). If it exceeds **max(baseline × 2, 10 %)**, fall back, and record it as failed in use.
   - If an answer does not arrive within the wait (core §4.4) at the raised speed, go back to the boot speed and repeat confirm
     (obligation 5; this converges whether or not the probe went back first). When confirm passes, look at boot_id (the same: the probe
     just went back; different: it rebooted). Then step 2 of the fallback. Keep the wait well below the lease.
   - **Falling back**:
     1. Send port_speed (revert) at the raised speed (no answer needed). Go back to the boot speed and repeat confirm until it passes
        (the same limit as step 3-6).
     2. From the candidates (ordered by the records and cut by the cap), try afresh, fastest first and from step 3-1, those **slower
        than every speed that failed in this session** (try → confirm → check → commit → probation). Use the first that passes.
     3. If none remains (or none passes), continue the session at the boot speed.
     4. A speed that broke in use (probation included) and every faster speed are **never tried again in that session** (no going up
        and down). The same holds when raising again later in the same session.
   - On the answer to revert or end, switch to the boot speed (obligation 6).
5. **Records**: the baseline (per flow); per candidate and flow (speed, actual speed, frames, broken, lost, ratio, passed, n cap); the
   probation result (passed / failed, bytes moved until then); fallbacks in use (time, from speed, to speed, inside probation or not,
   the ratio used). The form is the host's. Use it for transfer budgets and for measuring limits.

### 17.4 Records and default examples

- **Key of a record**: the port (the OS device name or the USB location) + the probe's unit_id. The converter belongs to the port and
  the probe to the unit_id, so a change of either looks the record up again. Never key a record by an `x-` unit_id (core §7.5).
- **Contents**: per speed, the result (passed / failed / unknown), the step that decided it (try / confirm / check / probation / in
  use), the time.
- **When the session closes before the probation ends**: keep the record of passing the check (result passed, step check) as it is;
  the next session may put that speed first. Rewrite it to "failed" (step probation) only when it broke during the probation. Hosts that
  open many short sessions (tests, flashing, monitors) then need not check again every session, and a speed that breaks in long reads
  drops out after the time it broke. Example (JSON; the form is the host's):

```text
{ "/dev/ttyUSB0|<unit_id>": { "port": "/dev/ttyUSB0", "unit_id": "<unit_id>",
    "rates": {
      "921600": { "result": "failed",  "phase": "probation", "at": "2026-10-02T10:00:00+00:00" },
      "500000": { "result": "passed",  "phase": "probation", "at": "2026-10-02T10:00:03+00:00" },
      "230400": { "result": "unknown", "phase": "verify",    "at": "2026-10-02T10:00:02+00:00" } } } }
```

- **Settling time**: after a breakdown at another speed (failed check, broken in probation or in use) or a fallback, **do not record
  "failed" for results measured within 2 s** of returning to the boot speed (write "unknown" or nothing). Right after a breakdown the far
  side of the line may still be disturbed, and the failure may not be that speed's fault. Results that passed are written as they are.
  "Unknown" is treated as no record (neither put first nor left out).
- **Expiry**: failed (and unknown) **1 day**, passed **30 days**. A failed speed is left out until it expires. A line that broke once
  may pass the next day, and measuring a one-day-old failure again is cheap. When the OS, driver or converter changes (the port's USB
  location changes), the record is not found, which re-measures naturally.
- **When all have failed**: even when the records say every candidate failed, **try the slowest candidate once** (leave out the others).
  If it passes the record is corrected; if not, stay at the boot speed.
- **Default examples**:
  - Broker, capture, flashing, log reading: **raise by default**. Candidates: the record's passed speed → the table of §17.3.1. Add checks
    (§17.3) if a transfer budget is needed, otherwise the minimal form (§17.2).
  - Short CLI (one describe, a few requests): **do not raise by default**. When there are reads or writes of more than a few KB, or the
    user names a speed, the minimal form (§17.2) with one candidate.
  - Interactive console: the minimal form with the single candidate 500000. If it fails, stay at the boot speed.
- **Allowed simplifications**: skip all checks (= the minimal form §17.2), one candidate, one flow, a baseline of 0 (thresholds are only the
  5 % / 10 % floors), skip the in-use judgement and rely only on the return when an answer is lost (obligation 5), skip the probation,
  fall back only to the boot speed. Interoperability needs only core §3.5's obligations; this procedure stays inside the host.

### 17.5 Measurements

The numbers come from repeated runs on Linux with two kinds of USB-UART converters: a CH340, and a CH552 that emulates an FTDI chip.
They are examples, not rules; measurements with other converters (genuine FTDI, CP210x, CDC MCUs) and other operating systems are
welcome ([review guide](review-guide.md) §4 item 5).

- **How the lines broke**: only the probe → host direction broke; host → probe held up to 1500000. The CH340 lost 0 to 10 % even at
  115200, in bursts lasting seconds, so absolute counts cannot judge a speed. The CH552 converter lost nothing at 115200 with one request
  in flight, but 17 to 45 % with two (both directions at once).
- **5 % (check)**: on the CH340, 1500000 broke more than 5 % in every run, while 500000 and 921600 stayed under it.
- **10 % (in use)**: the CH340's own baseline at 115200 reached 10 %, and 921600's 3-second averages mostly stayed under it.
- **3 s window**: 100 frames take only 0.7 s at 921600, and on a line that drops frames in bursts a frame-count window jumps.
- **Measuring at the n of use**: the CH552 converter's failure with two in flight does not show with one.
- **32 KiB and 1 s of probation**: on the CH340, 921600 passed the 16-frame check and then broke in the middle of a 65 KB capture read;
  32 KiB (about 0.5 s at 921600) catches that early in the read, and 1 s keeps the probation from being too short at high speeds.
- **2 s of settling**: right after 921600 broke, 500000 lost every frame with two in flight, though it passes when not tried right
  after a breakdown.
- **500000**: passed small round trips on both converters (the single candidate of §17.2). 921600 does not come out of the CH552
  converter (it divides its clock by integers only).

## 18. Target power and reset (informative)

The target's power and reset lines are not slot items of the probe's settings. The host finds them by label and drives them itself with
`oep.fixture.gpio` and the reset TLV of attach. The only time the probe uses a reset line on its own is the retry with reset of a slot
with boot_reset 1, right after boot ([probe settings](oep-if-probe-config.md) §3.1). This section is not normative (the normative
convention for line names is [probe settings](oep-if-probe-config.md) §1.3).

### 18.1 Line names (the label convention)

The names and the search are normative in [probe settings](oep-if-probe-config.md) §1.3 (ASCII case ignored; two or more matches mean
no line). This is how to use them. Give the lines these names with label items (tag 0x02) of `oep.probe.config` and save them. The host
reads the labels with get (and the firmware's fixed labels, tag 0x46 of fn 0's describe) to find the lines.

| Name | Line |
|---|---|
| `nrst` | The target's reset line |
| `power_hi` | A line that powers the target when high |
| `power_lo` | A line that powers the target when low |

- On a probe with two or more slots, name them `<slot name>.nrst`, `<slot name>.power_hi`, `<slot name>.power_lo` (slot names:
  [probe settings](oep-if-probe-config.md) §1.1). Bare names (`nrst` etc.) are found only when the settings hold at most one slot item
  (a probe without slots can use bare names too).
- The search order is the normative one of probe settings §1.3. If nothing is found, treat the line as absent (to search for a reset line,
  §21). The probe finds `nrst` for its boot_reset retry by the same search.
- A target has either `power_hi` or `power_lo`, not both.
- A name for a role that is not standard starts with `x-` (probe settings §1.3).

### 18.2 Power cycling

1. Take the power channel with a plan of `oep.fixture.gpio` (plan_apply). Taking it does not change the level (fixture §1: it keeps its
   idle state until the first set).
2. Hold the level that powers the target off (output low for `power_hi`, output high for `power_lo`) for 200 ms or more. 200 ms is a
   default; lengthen it in the host's settings for targets that need more.
3. Set the level that powers the target on.
4. Attach. To stop before the application runs, use a halting attach (method 1).
5. Release the plan (plan_release). The channel goes to the idle state (core §8). To keep the power on, put on that channel an output idle
   at the powering level (`power_hi`: mode 4 output high; `power_lo`: mode 3 output low; [probe settings](oep-if-probe-config.md) §1) and
   save it. A saved output idle is also applied at boot, so the target is powered before the at-boot attach of a slot.

- Taking the power channel with a gpio plan does not cut the power (step 1). read gives the current level without driving.
- Power a target directly from a probe pin only when the target's consumption and inrush current fit what the pin can source (tens of mA).
  Larger targets and boards need an external switch (load switch, MOSFET); the power channel then drives its control line.

### 18.3 Attaching with reset

- Pass the `nrst` channel in attach's reset TLV ([wire and debug](oep-if-debug.md) §3). The probe must declare that channel for role 3
  (reset) in role_channels.
- Use it only when the host chooses to (flashing, recovery, stopping right after reset). Do not add it to an ordinary attach to a running
  target (the target would be reset).
- Whether the target's reset line is enabled cannot be seen from the probe (some targets can disable it). When it is disabled, the reset
  TLV does nothing and the attach acts on the running target.

### 18.4 Capturing power-up

- A capture waiting for its trigger (state 2, [capture](oep-if-capture.md) §3.2) only listens and shares its channels with other functions
  (capture §1.2, sharing pins). While it waits, the host may drive the power channel with gpio.
- The power channel itself may be one of the captured channels (power-up can be the trigger).
- Whether sharing is allowed is the probe's decision (core §8.1). On a probe that does not allow it, gpio's plan_apply is rejected
  unavailable.

### 18.5 Output drive strength

On a probe whose `oep.fixture.gpio` describe declares drive_levels, gpio set's drive and the drive of a settings idle choose the strength
of mode 3 / 4 outputs ([fixture](oep-if-fixture.md) §1.1). Without one, the default level applies. read's drive TLV gives the level in
effect.

- **The default is right in most cases**: change the strength only for a reason (a target powered from the pin, a long line, an LED).
  **Do not make a line that powers a target from a probe pin weaker than the default**: the weakest level may not be enough, and the target
  then resets repeatedly on a voltage drop.
- **Write mA ceilings, not level numbers**: if a settings file is used on other probes, use kind 1 (mA ceiling). The levels differ per probe.
- **Power lines**: when gpio set gives no drive, the idle's drive carries over. Power cycling (§18.2) keeps the strength the idle set.
- **Lines where a strong drive hurts** (use the default or a weaker level):
  - lines the DUT may drive from the other side during a test (the current in a collision grows with the strength);
  - USB PD CC lines and USB pads (D+ / D−);
  - a UART TX connected to the DUT's RX (faster edges couple more into neighbouring lines);
  - the reset line, which is pulled open-drain whatever the strength (modes 5 / 6, attach's reset TLV).
- The strength of debug wires and of the UART / SPI / I2C peripheral lines is the probe's choice (the host cannot set it); see
  [probe development guide](probe-development-guide.md) §12.

## 19. Finding pins (informative)

Not normative. A procedure to find the debug wire and the reset line of a target with unknown wiring connected to a probe whose pins the
host chooses (describe's role_channels).
oep-client-python's `oep pins` runs this procedure and keeps the knowledge per target family (wires, target_id matching, the reset vector,
how to read options, max_speed / idle_clock) in one table (`targets.FAMILIES`). The probe knows no target.

### 19.1 Procedure

1. **Classify.** Read every channel `oep.fixture.gpio` allows, with pull-up, with both pulls (mode 7) and with pull-down, in that order,
   a dozen times each at short intervals. Reading with a pull drives nothing.
   - Changes between reads: **active** (an output the target drives).
   - The same level with either pull: **driven** (push-pull, or a pull stronger than the probe's).
   - 1 with pull-up and 0 with pull-down: **floating**. 1 even with both pulls: **weak pull-up** (common on reset lines). A weak pull-down
     cannot be told from floating.
   - Read with pull-down last: a pull-down on a reset line resets the target (§19.3).
2. **Find the channels that follow power** (only when the host holds the power channel). Read with power off and with power on. Channels
   that read differently are connected to the target (an unpowered target pulls the probe's pull-up down). This only gives candidates.
3. **Find reset-line candidates by activity.** If there is an active channel, hold each floating / weak pull-up channel low, open-drain,
   one at a time, and see whether the active channel stops. Watch for longer than the longest quiet period while running (3 times it,
   0.3 to 1 s). When it stops, release, wait for the activity to come back, then go on (a boot after reset can take more than 1 s).
4. **Scan.** Scan the wire only with floating / weak pull-up channels. Try two-line wires in pairs and cap the number of pairs (when there
   are too many, narrow to the channels that follow power).
5. **Identify.** Halt-attach (method 1) a pair that answered and look at target_id for the family. If that family can disable its reset
   line by an option, read the option (read only). If it is disabled, do not look for a reset line. Resume after reading.
6. **Check the reset line.** Pass the channel that stopped activity in step 3 (or, if none, the candidates starting with weak pull-ups)
   in attach's reset TLV (method 1) and see whether dpc is the reset vector (§21). Send pins every time.
7. **Suggest a record.** Show the wire and pins as a slot ([probe settings](oep-if-probe-config.md) §1.1) and the reset line as the label
   `<slot name>.nrst` (same §1.3). Write them only when the user asks.

### 19.2 Safety rules

- Do not drive, scan or hold low a driven / active channel. scan drives the lines, which collides with push-pull outputs. Do not send scan
  with count = 0 to a fixture whose wiring you do not know without the user's consent ([wire and debug](oep-if-debug.md) §1).
- Touch the power channel only when the user named it.
- Hold low only open-drain (never drive high).
- Put an overall time limit (within a minute). At the end release every plan and close the connections you opened.
- Do not write settings (only a slot the user asked for). Read options only; never write them.
- Replacing a gpio plan returns the pins of the previous plan to the idle state for a moment (core §8). Without an output idle on the power
  channel (§18.2 step 5) the target's power drops meanwhile and may be left half-way. When you hold the power channel, power-cycle cleanly
  each time you replace the plan (off for 200 ms or more, on, wait for boot), or order the steps so that the plan is not replaced.

### 19.3 Lessons

- **An idle-high UART line looks like a debug or reset line in a power on / off comparison.** Level comparisons only give candidates; scan
  (did the wire answer) and attach (dpc) decide. It reads high with either pull, so classification calls it driven and it is left out of
  scan and holding.
- **Leave out outputs the target drives push-pull.** Scanning every channel except active and driven ones finds the debug wire quickly.
- **Find the reset line by activity and confirm it by dpc.** A short activity window reads a quiet period (an output whose duty sits at an
  end) as stopped and yields many candidates; a window 3 times the quiet period yields only the real one. The reset-TLV attach's dpc decides.
- **Send pins with the reset-TLV attach.** On a wire where the host chooses the pins, an attach without pins only joins the wire's single
  live connection and is refused unavailable when there is none; reading that refusal as "not the reset line" loses the real one.
- **Whether a reset line exists can depend on the target's option bytes.** If it is disabled, not finding it is correct; reading the option
  tells you first.
- **A pull-down also resets.** While classification pulls down, the target is held in reset, and a target whose bootloader waits takes over
  1 s to become active again. Read with pull-down last, and wait for activity before the next step (power-cycle if it does not come back).
- **A halting attach right after power-up** stops before the first instruction on targets without a reset line, another way to stop early
  (§18.2).

## 20. Writing flash (the host holds the target knowledge)

The probe knows no target; the host does (core §13 rule 8). General rules:

- **Choose the loader by write method × instruction set.** Do not reuse a loader from a similar family: a loader that uses
  registers a smaller base ISA lacks is an illegal instruction there. Look the method and the RAM size up in a per-target table.
- **Read a loader back before running it.** A garbled loader can drive the flash controller until it reaches its ebreak and damage
  every later page. A probe's ack does not prove the contents arrived. Read the written flash back as well (a loader that computes a
  CRC on the target makes this fast on slow links).
- **The erased value is not always 0xFF.** Judge "blank" pages from a per-target table, not from 0xFF.
- **Merge ELF segments per page before writing.** The initial values of `.data` often arrive as a separate segment that starts in
  the middle of a page right after `.text`.
- **Read the read-out protection first.** Writing a protected target usually needs a full erase; do not remove protection without
  an explicit instruction.
- **Do not write under a running watchdog.** An independent watchdog keeps counting while the hart is halted and resets the target
  in the middle of a write. Reset and halt before the first instruction first (`oep.target.riscv-dm` reset).
- **When the host calls a function on the target** (a ROM flash routine), mask interrupts for the call and always unmask them
  afterwards, even on errors: a debug-register mask can survive a reset and leave the next firmware running without interrupts.
- **Identify the target from target_id when the attach answer carries it** (core does not interpret it; the host knows what its
  bits mean). Otherwise read the identification registers the target family defines.
- **The probe does not reissue run or resume** ([wire and debug](oep-if-debug.md) §4.2, §4.4). If a stopped dpc is still the
  start address, the code did not run. Retry only operations that are safe to run twice (erase, writing the same page). Quirks of a
  target's resume (needing a second resumereq, not setting allresumeack) are handled by the host: read dpc and resume again if needed.

## 21. The reset line

- **Which channel is the target's reset line is found and checked by the host.** For each candidate send an attach with the reset
  TLV (method 1) and look at where the hart stopped. On the real line it stops before the first instruction (the reset vector);
  on another line the target kept running and stops somewhere in its code. Try each candidate a few times and accept it if it
  stops at the vector even once.
  - Skip a channel the probe does not allow as a reset line (rejected unsupported) and a channel held by something else
    (rejected unavailable naming that channel). Other refusals are about the pins or the wire, not the channel: stop searching.
    A failed attach (completed failed) is a miss; retry.
  - Send pins with every attach. On a wire where the host chooses the pins (role_channels), an attach without pins only joins the
    wire's single live connection, and is rejected unavailable when there is none ([wire and debug](oep-if-debug.md) §1).
  - After a hit, reset (and run) rather than resume, so that the hart is surely away from the vector; otherwise the next wrong
    candidate also reads dpc = vector and looks like a hit.
  - Pull candidates low one at a time, open-drain. Leave out lines the fixture's wiring must never pull low.
  - oep-client-python: `Wire.find_reset_line(candidates, pins=...)`; the whole procedure from candidates is §19 (`oep pins`).
- **Recovering a target whose firmware turned the debug pins into GPIO**: use the probe's attach with the reset TLV first. On a probe
  without it (unsupported), send the release of `oep.fixture.gpio` and the attach together in one write and retry: the window is
  short, and waiting for the release's answer before sending attach can miss it.
