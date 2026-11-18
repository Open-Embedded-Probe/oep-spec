# OEP v1 approach to safety and security

[日本語](security.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative). It adds no rules. It collects in one place the approach to safety and security that the normative text already has, with the relevant
sections. Where this page and the normative text disagree, the normative text is right.

## 1. Trust model

- The OEP core **defines neither authentication nor encryption**. On a probe without restrictions by policy, a program that can open a transport can use the core's open/force, take the lock and operate the offered functions.
  core §4.3 allows refusal by an optional policy (unavailable cause 7) even for existing operations. The decision comes before returning saved resend answers.
  Authentication methods and the lifetime of permissions are treated as contracts of the adopted transports or third-party functions. The 5 public discovery operations are not refused by policy. Owning the lock alone does not authenticate a person.
  force of the lock is not authentication; it only prevents mix-ups (core §6.4).
- USB and serial transports are trusted like the other devices at hand on the PC. **TCP is used only over a trusted local connection or inside an authenticated tunnel**
  (transports §1).
- Even when the target's memory or console contains secrets, OEP payloads are not encrypted. Protection over TCP is done by the tunnel above and the like.
- Secret items such as the Wi-Fi passphrase (core §13.5, transports §7.1) are write-only; the probe does not put them in any answer or log and does not let them be read with any permission.
  They are not in exported files either ([settings file](oep-settings-file.md)).
  They pass through the transport unencrypted, so the host configures them over a trusted transport such as USB.
- An endpoint that answers OEP requests itself is a probe whatever is behind it, and follows all probe rules. A broker that only relays is a
  host towards the probe (transports §1).
- The method of updating the probe's own firmware is outside the core (core §0). Standard OEP defines no image format or signature method.
  Examples that define a third-party update entry, image transfer or privileged operation are in the [extension examples](extension-use-cases.md).
- Reading the target's memory, and protecting that reading, is the host's business: the probe executes the host's requests and has no knowledge of the target (core §12
  rule 8). Target-specific protection and procedures are handled by the host implementation.

## 2. Broken input

A probe:

- checks the length and encoding of every request before acting, and refuses with malformed (core §4.3): counts that do not match, TLV encoding errors, TLVs whose len goes past the end
  (core §2.2), wrong lengths of implemented TLVs (core §2.3);
- refuses before executing: it checks the request completely as in core §4.3, and operates nothing until everything passes (plan_apply and settings set / unset change nothing unless all are
  accepted: [plan](../interfaces/oep-if-plan.md) §2.1, core §13.5);
- discards a frame with a length beyond max_frame together with the input up to the next pause. On TCP it closes the connection (transports §1);
- on serial ports and vendor bulk, reads anew when there is a pause of `probe_frame_gap_ms` in the middle of a frame (transports §2);
- discards an HID report whose count is larger than the report can carry, reads anew from the next report that has a first, and ignores the report's padding (transports §1);
- discards without answering messages whose role is not the request role and requests shorter than the 10 byte header (core §2.4).

A host:

- decodes candidates and discards those that do not decode, whose CRC does not match, whose role is unknown, or whose corr is not being waited for (transports §1, core §10.1);
- discards messages whose role is the request role, treats as broken answers shorter than 5 bytes, event or data frames shorter than their header (core §2.4) and answers shorter than their
  fixed part, skips unknown tags, treats TLV values whose length differs from the definition as broken, and treats unknown status and reason as failure (core §2.3, §2.4);
- if there is no answer even to resends, considers that transport failed, and recovers with confirm (or reopens) before sending anything there (core §5.1);
- can receive messages up to 65535 bytes. A correct COBS frame is never longer than 65796 bytes between its two 0x00
  (transports §3, host development guide §2);
- replaces control characters and invalid UTF-8 in answer text before showing it (core §2.1).

## 3. Not letting resources be exhausted

- **Outstanding requests**: the per-transport max_frame, window and max_inflight decide how much a host can send. A probe MAY refuse with window_exceeded, and
  a host that does not keep them loses requests (core §4.4).
- **Resending**: the ordering state of the last session_id/corr is kept. The byte records of requests/answers may be limited in count and size, and may be 0 entries.
  Old requests not kept are answered with result_lost and not re-executed (core §5.1). This is decided separately from the limit of the receive buffer.
- **Notifications**: at most max_frame × `notify_pending_max_frames` bytes wait in the transport's send buffer. The rest are discarded inside the probe and appear as skips in
  seq. The probe sends answers first and does not block on writing notifications (core §10.4). Notifications are sent only for fns the lock holder subscribed to
  (core §10.3).
- **What the host receives on a serial port**: the OS driver may silently drop what arrives at once, so the host keeps the amount of answers it waits for and the
  min_bytes of subscribe small (host development guide §8).
- **Time**: no request takes longer than the declared max_op_ms, and ops whose arguments could exceed it are refused with unsupported (core §7.5). attach, scan and
  the reset of riscv-dm also answer within it ([wire and debug](../interfaces/oep-if-debug.md) §1, §4.3). The lease is between `lease_min_ms` and `lease_max_ms` (core §6.4).
- **Numbers**: resource numbers are u32 in one space per probe. They are not reused within one boot, and closed numbers become no_resource.
  The host discards numbers that got no_resource, and discards all numbers when the boot_id changes (core §9).
- **Accumulated data**: positioned streams and capture segments are rings that push out the oldest and report the loss (common §1.1,
  [capture](../interfaces/oep-if-capture.md) §2). Settings are limited by the amount the probe can hold; changes and saves beyond it are unavailable cause 2 / 3 (core §13.5, §13.7).

## 4. Fairness of the lock

- There is **one** lock per probe. Only the session holding it can change state (core §6.1, §6.3). Requests that need no lock only read
  (core §6.3, §12 rule 5).
- A lock the holder stopped renewing is freed by the lease. On expiry, as with end, that session's resources are released (core §6.1, §9).
  The lease stops only while the owner's own new request is processed, and max_op_ms bounds its length. It does not stop for communication waits after the answer is built, or for monitoring queries.
- A host refused with locked learns the remaining time and, if any, the holder's string (core §4.3, §6.4). lock_state returns the same without a session.
- The session_id is an unpredictable 32 bit random number the host chooses, and the probe does not put it in answers. It is an identifier that reduces mix-ups, and is not treated as an authentication secret or a proof of permission (core §6.1, §6.4).
- force takes the lock and releases the previous session's resources the same as at its end (core §6.4, §9). What a session made does not pass
  to the next session, so the plan or connections of a crashed host never become another host's (core §9). When a host uses it: host guide §6 (only when the user
  asked; a probe whose only transport is a serial port opened exclusively is different).
- **A host holding the lock can restart the probe** (restart of the optional interface `oep.probe.restart`, [restart](../interfaces/oep-if-restart.md)). The lock holder can already drive wires and
  change settings, so restarting is also within trusting the holder. A request without the lock does not restart (session_required, no_session, locked). A restart interrupts every transport,
  including other hosts' lock-free reads, discards unsaved settings and closes connections. The probe sends the answer first and puts the
  wires in the idle state before restarting. The restart procedure does not intentionally reset/resume the target, but the pin states at the MCU's reset and external circuits have effects ([restart](../interfaces/oep-if-restart.md) §2). A probe that does not offer `oep.probe.restart` does not restart.

## 5. Target output and OEP control

An OEP serial transport is for frames only and is not shared with the target's raw data (transports §4).
Console bytes are carried in the payload of read. Even when a raw endpoint is offered alongside, it is not mixed with the OEP parser or receive queue.


## 6. Electrical safety

A probe drives real wires. Rules for not damaging the target, the fixture or the probe itself:

- **Output strength**: in v1 the probe decides it, and selection of levels by the host is not defined ([fixture](../interfaces/oep-if-fixture.md) §1). In practice: debug wires are driven at the weakest strength the timing allows, and wires that power the target
  are not weakened. The concrete levels follow the specifications of the probe and the external circuit.
- **Output idle**: a released pin returns to the idle state (the setting idle or Hi-Z) (core §8). Taking a plan does not change the pins, and read-only
  interfaces do not drive (core §8, capture §1.2). An output idle drives its level all the time the pin is free, from boot, without a host.
  Making sure it does not collide with the target's outputs is the responsibility of the wiring (core §13.8). A request that names a
  channel with an idle value, where the idle is an output, is unavailable cause 5 unless that interface allows taking it
  ([wire and debug](../interfaces/oep-if-debug.md) §1).
- **Saved settings and boot**: after booting, before the first answer, the probe puts every channel in the idle state except the channels it uses itself and the channels whose use and configuration settings prohibit, and with saved settings it applies
  disable and idle before the other items (core §8, §13.7).
  An output idle drives whether or not there is a host. Runtime settings of wiring and UART are applied explicitly by the host (core §13).
  From power-on or reset until the firmware applies the settings, while the firmware is being updated, and when the firmware is broken, the pins are in the MCU's reset state, and
  nothing the settings define is driven. A line where a wrong level does harm (a line that switches the target's power and so on) needs an external pull that by itself keeps it at a safe level.
  disable is the user's declaration, not a protection: a host holding the lock can remove it with unset and use that channel. The settings mechanism itself has no authentication method (core §13.6). Without restriction by policy, any host that took the lock, including by force, can change and save it (§1).
- **Back-powering**: from a failed exchange until it succeeds or the connection is lost, the probe rests the wire without driving it, and drives only during an exchange. This is so as not to power
  an unpowered target through the pins' protection diodes ([wire and debug](../interfaces/oep-if-debug.md) §2). When the connection closes, those pins return to the idle
  state (debug §2).
- **Writes to the target before checking the speed** are only the wake / setup procedure and dmactive. The write check of a wire that defines a scratch uses only that register and restores it.
  SWD checks by reading DPIDR and ACK/parity, and does not require writing to a scratch (debug §1, §5).
- **Wire retries**: the probe's wire retries do not repeat stores to the target's memory that may have reached the target or the host's dmi procedures (failure is visible as failed / partial), and while there is a connection they do not
  change the target's state (a wake that can reset the target only within attach and reset) (debug §2).
- **scan** drives, in order, the candidate pins the host specified explicitly. It is not sent to a fixture whose wiring is unknown without the user's consent (debug §1, informative).
- **Fixture lines**: spi-target drives MISO only while CS is active (except cs_setup_ns), and if it starts driving MISO in software it declares cs_setup_ns
  (fixture §4). i2c-target drives SDA / SCL only open-drain, declares internal pull-ups, and refuses reserved addresses so that it does not answer the bus's general call or 10 bit headers
  (fixture §3). The plan of uart
  keeps TX at the UART rest level (fixture §2).
- **The reset line** is pulled open-drain (gpio mode 5 / 6, the reset TLV of attach). The reset op of riscv-dm does not move the reset line,
  so lines move only where the host named them (debug §4.3). The procedure that closes a connection does not intentionally reset/resume the target. The effects of releasing pins and of external circuits are separate (debug §2).
- **Powering from probe pins** is done only within what the pins can supply. Larger loads go through an external switch.
- Before scanning or outputting to a target whose wiring is unknown, confirm the user's consent and electrical safety.

## 7. Other software on the same port

- Where the OS allows, a host opens serial ports and HID exclusively (transports §3). Cooperative locks do not stop other tools (host guide §6).
- On devices and ports not yet identified, a host sends only confirm, and closes them if no correct answer comes (the probing rule, transports §3). This is so as not to disturb devices
  that are not probes. A device is not decided to be a probe only by class / subclass / protocol or usage page (transports §3).
- The probe does not use DTR, RTS or line settings for any decision, and does nothing on a 1200 bps touch or CDC line settings (transports §4).
  The host keeps DTR and RTS asserted so as not to operate automatic reset circuits (transports §4, host guide §1).
- Raw bytes are not mixed into an OEP serial transport (transports §4).

## 8. Information the probe shows

- **owner** (open TLV 0x01) is returned to any host in lock_state and in locked refusals: do not put secrets in it (core §6.4, informative).
- **unit_id** can be read by any host and is also the USB serial number. If made from the chip's unique number, it shows that number (core §7.5; alternative
  ways to make it are in the probe guide §10).
- describe, list, settings get, state and network (the Wi-Fi passphrase is not returned), connections, streams and read of positioned streams need no lock: without restriction by policy, a program that can open the port can read them (core §6.3).
  No secret that needs hiding by policy is put in the capabilities, identification or owner returned by the 5 public discovery operations.
