# OEP v1 security and safety considerations

[日本語](security.ja.md)

Status: out of date. Until the v1 freeze the Japanese text (.ja.md) is the working text; this English version will be regenerated from it at the freeze and becomes authoritative then.

Status: **guide** (not normative). It adds no rule. It gathers in one place the security and safety considerations that the normative text
already holds, each with the section that holds it. Where this page and the normative text differ, the normative text is right. This English
text is authoritative; the Japanese version is its translation.

## 1. Trust model

- OEP has **no authentication and no encryption**. Any program that can open a probe's transport can use it, and any program that takes the lock
  can change state. The lock's force is not authentication; it only prevents mix-ups (core §6.4).
- USB and serial transports are trusted as the PC's other local devices are. **TCP is used only on a trusted local connection or inside an
  authenticated tunnel** (core §3.1).
- An endpoint that answers OEP requests itself is a probe and follows every probe rule, whatever is behind it; a broker that only relays is a host
  towards the probe (core §3.1).
- Updating the probe's own firmware is outside OEP (core §0); OEP neither carries nor signs firmware.
- Reading a target's memory, and its read-out protection, are the host's matter: the probe executes the host's requests and holds no target
  knowledge (core §13 rule 8; host guide §20).

## 2. Malformed input

The probe:

- checks every request's length and encoding before it acts, and refuses with malformed (core §4.3 order 5): counts that do not match, TLV encoding
  errors, a TLV whose len runs past the end (core §2.2), tags 0x7F / 0xFF (core §2.3), booleans other than 0 / 1, text that is not valid UTF-8 or
  holds control characters (core §2.1);
- refuses before executing: a request is checked in the order of core §4.3, and nothing runs until every check has passed (for plan_apply and
  probe settings set, nothing changes unless all of it is accepted: core §8, probe settings §2);
- discards a frame whose length exceeds max_frame, and the input up to the next pause; on TCP it closes the connection (core §3.1);
- restarts its reader after a pause of `probe_frame_gap_ms` inside a frame on every transport except TCP (core §3.2);
- discards a HID report whose count is larger than the report can carry, and the stream's input up to the next pause, and ignores the padding of reports (core §3.1);
- discards, without answering, a message whose role is not the request role and a request shorter than its 10-byte header (core §2.4).

The host:

- decodes candidates and discards those that do not decode, whose CRC does not match, whose role is unknown or whose corr it is not waiting for
  (core §3.1, §11.1);
- discards a message whose role is the request role, and treats an answer shorter than 5 bytes, an event or data frame shorter than its header
  (core §2.4) and an answer shorter than its fixed part as broken; it skips unknown tags, treats a TLV value whose length is not its definition's as broken, and treats unknown status and reason values as failures
  (core §2.3, §2.4);
- after a resend that also got no answer, treats the transport as failed and recovers with a confirm (or reopens it) before it sends anything
  else there (core §5.2);
- can receive messages up to 65535 bytes; no valid COBS frame is longer than `cobs_frame_max_bytes` between its two 0x00 (core §3.1, §3.3);
- replaces control characters and invalid UTF-8 in answer text before showing it (core §2.1).

## 3. Resource exhaustion

- **Requests in flight**: max_frame, window and max_inflight per transport bound what a host may send; the probe may refuse with
  window_exceeded, and a host that ignores them loses requests (core §4.4).
- **The resend table** keeps at least max_inflight entries; the probe may limit the size of remembered answers and answer a resend of a larger
  one with result_lost (core §5.2).
- **The ignored list** has at most `ignored_max_entries` entries, and the probe always keeps room for it (core §2.3).
- **Notifications**: at most max_frame × `notify_pending_max_frames` bytes wait in a transport's send buffer; the rest are dropped inside the probe
  and show as a gap in seq. The probe sends answers first and never blocks on notification writes (core §11.4). The heartbeat period may be
  rounded up to `heartbeat_min_ms` (core §11.3).
- **The host's receive capacity on serial ports**: hosts keep answers outstanding at `host_serial_inflight_max_bytes` or less and subscribe's
  min_bytes at `host_serial_min_bytes_max` or less, because OS drivers may silently drop bursts (core §3.4).
- **Time**: no request takes longer than the declared max_op_ms, and ops whose arguments could exceed it are refused unsupported (core §7.5).
  Attach and scan have their budgets `attach_budget_ms` and `scan_budget_ms`, and one request retries the wire for at most `wire_retry_ms`
  ([wire and debug](oep-if-debug.md) §1, §2). The lease lies between `lease_min_ms` and `lease_max_ms` (core §6.4).
- **Numbers**: resource numbers are u16, one space per probe; a closed number is not reused among the last `resource_reuse_distance` closed
  ones (core §9).
- **Stored data**: positioned streams and capture segments are rings that push out the oldest data and report the loss (common §1.1,
  [capture](oep-if-capture.md) §2); probe settings are bounded by max_bytes and refused unavailable cause 3 beyond it (probe settings §2).

## 4. Lock fairness

- There is **one lock** per probe; only the session that holds it changes state (core §6.1, §6.3). Lock-free requests are read-only (core §6.3,
  §13 rule 5).
- The lease frees a lock its holder stopped renewing; on expiry, as on end, the session's resources are released (core §6.1, §9). The lease is not counted
  while a request runs, which max_op_ms bounds (core §6.1, §7.5).
- A host refused with locked learns the remaining time, and the owner text if any (core §4.3, §6.4). lock_state gives the same without a session.
- The session_id is an unpredictable random value chosen by the host, and the probe never returns it, so another host cannot act as someone else's
  session without force (core §6.1, §6.4).
- force takes the lock and releases the previous session's resources as at its end (core §6.4, §9). Nothing a session created is handed to
  the next session, so a crashed host's plans and connections do not become another host's (core §9). How a host decides to use it: host guide §6
  (only when the user asks, except for a probe whose only transport is one exclusively opened serial port).

## 5. Lock-free answers that a target's output could fake

On a serial port, the target's raw bytes reach the host on the same port as OEP answers (core §3.4). The host's role and corr matching discards
frames that appear by chance, but not a frame made on purpose: on a port where raw transfer is not stopped, the target's output can contain a frame
with a valid CRC and the corr of an outstanding lock-free request (corr advances by one, so it can be predicted). A host that must trust the
contents of an answer sends the request on a port where raw transfer is stopped (after a request of its session has arrived there) or on a
length-prefixed port (core §3.4, informative note).

## 6. Electrical safety

A probe drives real lines. The rules that keep it from harming a target, a fixture or itself:

- **Drive strength**: the host chooses the strength only for gpio outputs and output idles (mode 3 / 4); the strength of wires and of the uart,
  i2c-target and spi-target lines is the probe's choice ([fixture](oep-if-fixture.md) §1.1). Practice: drive debug wires at the weakest strength
  their timing allows, and do not weaken a line that powers a target (probe guide §12, host guide §18.5).
- **Idle outputs**: a released pin goes to its idle state, the settings' idle or Hi-Z (core §8). Taking a plan does not change a pin, and an
  interface that only reads never drives (core §8; capture §1.2). An output idle drives its level whenever the pin is free, from boot, without a
  host; keeping it from meeting a target's output is the wiring's responsibility ([probe settings](oep-if-probe-config.md) §1). Channels with an
  idle item are left out of scan with count = 0 and of attach without pins, and naming one whose idle is an output is refused unavailable cause 5,
  holder_kind 7 ([wire and debug](oep-if-debug.md) §1).
- **Saved settings and boot**: at boot, before its first answer, the probe puts every channel that is not reserved in its idle state (core §8);
  saved settings drive lines at every boot without a host; before the firmware runs and the settings are applied the pins are in the MCU's reset
  state, so a line whose wrong level is harmful needs an external pull of its own; disable is a declaration, not a protection; settings have no
  authentication (probe settings §5).
- **Back-powering**: from a failed exchange until one succeeds or the connection is lost, the probe rests a wire's lines undriven and drives them
  only during an exchange, so that a target that lost power is not powered through its pins' protection diodes ([wire and debug](oep-if-debug.md)
  §2). When a connection closes, its pins go to the idle state (debug §2).
- **Writes to the target before the speed is verified** are limited to the wake / configuration sequence and dmactive; the write check uses only
  scratch registers and restores them. A probe that attaches through another debugger declares `attach_writes_unbounded` instead (debug §1).
- **scan with count = 0** drives every free candidate pin in turn; a host does not send it to a fixture whose wiring it does not know without the
  user's consent (debug §1, informative).
- **Fixture lines**: spi-target drives MISO only while CS is active, apart from cs_setup_ns, and declares cs_setup_ns when it starts MISO in
  software (fixture §4); i2c-target drives SDA / SCL open-drain only, declares any internal pull-ups and refuses the reserved addresses, so that it does not answer
  the bus's general calls or 10-bit headers (fixture §3); a uart plan holds TX at the
  UART idle level (fixture §2).
- **The reset line** is pulled open-drain (gpio modes 5 / 6, the reset TLV of attach); the reset op of riscv-dm never drives a reset line, so a
  line moves only where the host named it (debug §4.3); closing a connection never resets the target (debug §2).
- **Powering a target from probe pins** only within what a pin can source; larger loads need an external switch (host guide §18.2).
- **Finding pins** on an unknown target: host guide §19.2.

## 7. Other software on the same port

- The host opens serial ports and HID exclusively where the OS allows it (core §3.3); advisory locks do not stop other tools (host guide §6).
- On a device or port it has not identified, a host sends only confirm, and closes it if no valid answer comes (the probing rule, core §3.3), so
  that it does not disturb a device that is not a probe. A class / subclass / protocol or usage page alone never identifies a probe (core §3.3).
- The probe uses neither DTR, RTS nor the line coding to decide anything, and the 1200 bps touch and CDC line coding do nothing to it (core §3.4,
  probe settings §1.2). A host keeps DTR and RTS asserted so that an auto-reset circuit is not triggered (core §3.4, host guide §1).
- Raw bytes on a shared serial port go to the flow bound to it, and raw transfer stops on a port while a session uses it (core §3.4).

## 8. Information the probe exposes

- **owner** (open's TLV 0x01) is returned to any host by lock_state and in locked refusals: it holds nothing secret (core §6.4, informative).
- **unit_id** is readable by any host and is the USB serial number; when it is the chip's unique number, it exposes that number (core §7.5;
  probe guide §10 lists the alternatives).
- describe, list, the settings' get and state, connections, streams and positioned-stream reads are lock-free: any program that can open the port
  reads them (core §6.3).
