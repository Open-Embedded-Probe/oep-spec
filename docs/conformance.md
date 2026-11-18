# Conformance to OEP v1

[日本語](conformance.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative). It adds no rules. Each line points at the normative document that holds the rule, and where this document and the normative document disagree, the normative document is
right. It answers one question: what probes and hosts do to conform to OEP v1, and how implementers check it.
The conformance clause itself is [core](oep-core.md) §1.2.

## 3 stages of conformance checks

Define the specification first, then build independent checks. After the core is settled, settle the common interface contracts and then the contracts specific to the standard OEP interfaces; implementations follow as a separate stage.

| Stage | Applies to | What it checks |
|---|---|---|
| Core conformance | Every endpoint and host that speaks OEP | transport/framing, headers, order of refusal, TLV extension rules, session, resending, time, ownership and lifetime of resources. §1/§2 of this document |
| Interface conformance | Every interface, standard or third-party | name/revision/instance, describe/ops, the separation of declarations and state, the common paging, resource, subscription and notification rules that apply. core §7/§9/§10/§12 and [common](../interfaces/oep-if-common.md) |
| OEP-interface-specific conformance | Endpoints that implement that standard interface | The payload, behaviour, side effects, contention, time limits, refusals and failed/partial, and abnormal cases of each op. §3 of this document and each normative text |

The first 2 stages are also used for third-party extensions. The 3rd stage builds checks of "initial state → request → answer → observable side effects → cleanup" from the normative clauses, and is maintained as a template also usable for testing third-party extensions. Specific ops and wiring are given by an adapter, and implementation-specific expected values are not mixed into the common pass/fail conditions.

Results record the stage, clause, case ID, scope executed, SPEC commit/tag, registry hash, implementation version, transport, unit, conditions, requests/answers and observations. A PASS is the success of the cases executed, and is not taken to mean full conformance. Items not checked, not applicable, lacking equipment, or not executable because a precondition failed are kept apart. Specification violations, configuration mistakes and implementations not yet following are not skipped as lack of equipment.

Before settling the core, make at least the following checkable independently. Self-consistency of vectors, the behaviour of virtual endpoints, the behaviour of hardware and electrical observation are separate evidence.

| Core contract | Normal, boundary and abnormal checks |
|---|---|
| framing/transport | Splitting and joining, corruption of CRC/COBS/count/length, frame gap, oversized frames, TCP disconnection and reconnection, unknown role / corr not waited for, independence of several transports |
| confirm/discovery | 64 bytes before confirm, boundaries of the revision range, frame/window/inflight, transport matching, the end, page progress, invariance and mandatory declarations of list/describe |
| Headers, refusals, TLV | No answer to short requests, corr 0, unknown fn/op, session_required, priority of refusals, length/value range, unknown non-critical/critical, a duplicate of a known non-repeating TLV in a request is malformed, ID 0, 0x7F, auxiliary information in answers |
| session | lease minimum/maximum/default, keepalive, owner, exclusion against other IDs, end/expiry/force, no side effects of session 0, change of boot_id |
| Resending | The result of a kept identical request including open, refusal of the same corr with content different from the kept request, 0-entry cache / eviction / retention size limit and result_lost, the ordering state advancing even on rejected, history after an open with the same ID, history after the end, no change of lease/notifications by duplicates |
| corr and lifetime | u16 cycling / skipping zero, the half-cycle boundary, the forward limit for outstanding requests, draining old answers between sessions, discarding the queue on reconnection, outstanding answers of the old transport, non-reuse / exhaustion of resource IDs, release at the end, refusal of old IDs and of IDs of another kind / unsupported creator, resource use between defined fns |

On hardware too, observe the endpoint's state changes independently. A check of double execution confirms not only that the same answer comes back, but also that side effects such as the clock, resources and notifications are not duplicated. Even if the way resources are made depends on the interface adapter, the pass/fail of their ownership, release and non-reuse is decided by the core contract.

## 1. Probe checklist

A probe conforms when it does everything in this list for the transports and interfaces it offers.

**Transports and frames**

- At least one transport of transports §1, with its frames (core §1.2).
- Serial ports: COBS + CRC-16 frames enclosed in 0x00 on both sides and how they are received (transports §1), the gap rule (transports §2), the raw byte rule (transports §4), the line of the UART bridge
  and its boot speed (transports §4), nothing decided by DTR / RTS (transports §4). No raw data, logs or boot messages are mixed into an OEP serial transport, with or without a session (transports §4).
- vendor bulk and TCP: `length(u16) message` (transports §1), the zero-length transfer rule of vendor bulk (transports §1), no reading anew on a pause on TCP (transports §2).
- Frame boundaries do not rely on the boundaries of writes, transfers, reports or TCP segments. Except on TCP, the probe does not pause for `probe_frame_gap_ms` in the middle of a frame it sends (transports §2).
- Even when a transport (including a TCP connection) closes, the session, lock, subscriptions and resend table remain, and answers and notifications to the closed transport are discarded (transports §3).
- HID: the length-prefixed stream carried by reports with `count(u16)`, `first(u16)`, frames across reports, first being the position of the first frame that starts in that report (`hid_no_frame_start` if none), skipping count 0, padding sent as 0 and ignored, one report ID or none, discarding what is being read and reading anew from first when first differs from its own reading, starting from the next report with a first right after opening and on a broken stream, too-long count and first of count or more (transports §1, vector `hid_reports.json`). Output reports are accepted both on interrupt OUT and by SET_REPORT (transports §3).
- A length beyond max_frame: discard and wait. On TCP, close. On HID, read anew from the next report with a first (transports §1). Read anew on a pause of `probe_frame_gap_ms`, except TCP and HID (transports §2).
- Even before confirm, accept messages up to 64 bytes (transports §3). Do not send beyond max_frame (transports §3).
- If it listens on TCP and advertises itself, advertise DNS-SD `_oep._tcp` over mDNS, with `unit_id=<unit_id>` in TXT (the port in SRV, transports §3).
- USB: on ports the probe can choose, serial number = unit_id (transports §3). vendor bulk and HID in the form of transports §3, at most one each.
- An endpoint that answers OEP requests itself is a probe whatever is behind it (transports §1).
  Invalidation and regeneration of resources by a broker that answers itself, when the path to the downstream probe is lost, follow transports §1.

**Messages, refusals, TLVs**

- Request and answer headers (core §4.1, §4.2). One answer per request, to the transport it came on, in the order they came (core §4.2, §4.4).
- rejected only for what was not accepted. What was accepted and failed is completed failed / partial (core §4.2).
- Order of refusal: header, resend table, session, in that order. Otherwise check everything before changing anything, and refuse with any one of the reasons that apply (core §4.3).
  The payload is as in core §4.3 (TLVs of unavailable, the tag of unsupported).
- Messages whose role is not the request role, and requests shorter than the 10 byte header, are discarded without answering (core §2.4). session_id 0 on an op that needs the lock: session_required (core §4.1).
- The describe of fn 0 and of every fn carries ops (0x07): all mandatory ops set, optional ops set only when present (core §1.2, §7.4). An op not set in ops is unknown_operation; an optional function of an op the probe has is unsupported (core §1.2). The ops in an interface's table are mandatory unless the document says optional.
- The value of ops is base and a bitmap of 1 byte or more, with `base + 8 × the bytes of the bitmap ≤ 256` (core §7.4).
- Request TLVs: an unknown critical TLV is unsupported, an unknown non-critical TLV is ignored. For an implemented TLV, regardless of bit 7, a length different from the definition is malformed,
  and a value not handled is unsupported (core §2.2, §2.3).
- The shape of a TLV is the one `tag len(u16) value` (core §2.2). Sequences are `count × element` without element lengths; every fixed shape is as defined and is not extended at the end (core §2.3).
- window / max_inflight are per transport (core §4.4).
  An unfinished resend copy with the same transport/session_id/corr uses no separate credit, and needs no separate keeping, re-execution or answer. Resend records are not used for processed requests of session_id 0 (core §4.4, §5.1).
- If the request fits but the fixed result does not fit in max_frame, refuse with unsupported before executing. Shortening / prefix / paging follow the individual definition (core §4.4).
- Wrapping values: the spread of values held at the same time in one space other than corr is less than a quarter of the width (core §2.6). corr follows the half-cycle rule of core §4.1/§5.1.

**Sessions and the lock**

- One lock, the decision table of core §6.2. The lease stops only while the holder's own new request is processed, and counts again from building the answer.
  It is neither stopped nor updated by communication waits, resends, or requests of session_id 0 / other sessions. Expiry cleanup is done before the next request, notification or resource operation (core §6.1).
- open / end / keepalive / lock_state / force / owner (core §6.4). The lease is rounded to 1000 to 60000 ms (core §6.4). session_id 0 is refused (core §6.1).
  A new unpredictable 32 bit random number is chosen for a new session, and ids are not deliberately reused. A history of all ids or the impossibility of probabilistic collisions is not required (core §5.1, §6.1).
- The resend ordering state is mandatory; byte records may be 0 entries. A new request that passed the header and policy decisions updates the last corr even if rejected, and old requests without a record are refused with result_lost.
  The ordering state is replaced only when the open of a new session with a different ID succeeds. An open with the same ID keeps the history; there is one per probe (core §5.1).
- Lock-free ops do not change, as the effect of the request, the target, pins, settings, runtime resources, subscriptions or the consumption of data.
  The revision of confirm and the progress of communication / asynchronous processing are distinguished (core §6.3). boot_id is chosen at every boot, and no priority among generation methods is required (core §6.5).
- Clock: ns since boot, not decreasing and not wrapping while the boot_id stays the same (core §2.7).
- Everything a session made is released the same way when its lock ends, whether by end, expiry or force, and is kept on a resent open (core §9). There is no resume (core §6.4). Resource numbers (u32, 1 to 0xFFFFFFFF, the first after boot is 1, 0 is not assigned, core §9). Closed console streams and buffers are released, and their numbers are not reused while the boot_id stays the same (console §2).

**fn 0 (the core; it has no name and is not in list)**

- Mandatory ops: the rows of core §11 (confirm, list, describe, clock, open, end, keepalive, lock_state).
- confirm: how the revision is chosen, the transport TLV, refusal with the range it handles. max_frame is 64 or more, window is max_frame or more,
  max_inflight is 1 or more (core §7.1).
- list: fn 0 not included, uniqueness of instance within (name, revision) and gaps, independence from fn order, the answer does not change while the boot_id stays the same, total and count 0 if first is total or more (core §7.2). Keeping instance across firmware updates of the product is checked by resolving the saved pair in the new list.
- describe: paging, only more 0 and no TLVs if first is the count or more, declarations only and unchanged while the boot_id stays the same (core §7.3). Each TLV fits in the frame of every transport even with the answer header of 5 bytes and more of 1 byte added.
  max_length is treated as a functional limit, and actual requests and results fit in that transport. For declared values of unsplittable external RX, the all-transport condition of the individual operation also applies (core §7.3, §7.4).
- clock: boot_id and uptime_ns (the clock read between receiving the request and sending the answer). No lock needed; with session_id 0 it answers even without a session and even while another session
  holds the lock, and touches no session, lock or lease. A broker's own OEP endpoint also implements the same contract (core §7.6, transports §1).
- Mandatory tags of the fn 0 describe: unit_id, transport (one per transport, the interface field as in core §7.5), channels if it has channels (numbers 0 to channels − 1), max_op_ms (1 to
  `max_op_ms_max`) (core §1.2, §7.5). Uniqueness and invariance of unit_id, invariance of transport indexes (core §7.5).
- channel: released pins go to the idle state; after boot, before the first answer, every channel goes to the idle state except the channels it uses itself and the channels whose use and configuration settings prohibit.
  Taking a pin does not change the pin. Taking an output idle is allowed only when the interface states it (otherwise cause 5). Lack of concurrent resources or processing capacity is refused with cause 2 without changing anything (pin contention is cause 1; core §8, §8.1).
- Notifications (if it has an interface that sends them): set subscribe (0x01) / unsubscribe (0x02) of that fn in ops, fns that do not send have neither, seq, only data is batched and events are sent right after the earlier answers, answers sent first and the limit on accumulated amount (core §10.2 to §10.4).
- min_bytes is a sending trigger, not the minimum length of one frame. Splitting the data when the condition is met does not reapply the threshold to the remainder, and max_delay does not override the answer priority (core §10.3/§10.4).
- Insufficient retained amount for a subscription is refused with unavailable cause 2, keeping the previous subscription's conditions, destination and seq. The limit on the retained amount for notifications is not treated as a mandatory queue capacity, and no other frame is inserted in a frame that has started being sent (core §10.3 to §10.4).
- On replacing / cancelling a subscription, unsent notifications of the old subscription are discarded, and a frame that has started being sent completes before the answer of the operation on the same transport. Answers on another transport do not wait, and the remainder of a closed transport is not carried over to a new transport (core §10.3 to §10.4, transports §3).

**Refusal by optional policy** (core §4.3)

On a probe that implements a policy, check that it refuses with cause 7 and does not change the resend history, owner, lease or resources.
Saved success answers after a permission is revoked are not returned either unless they pass this decision.
confirm / list / describe / clock / lock_state of fn 0 are excluded from the policy.
The cryptographic methods of authentication, and the behaviour on revocation for accepted processing or sending in progress, are checked under the contract of the adopted transport/extension.

**Time limits** (values in `registry/oep-v1.toml`)

- confirm / list / describe / clock / keepalive / lock_state of fn 0 process the whole request within min(max_op_ms, core_quick_op_max_ms).
  The host's resend wait is this limit + host_wait_add_ms + the transfer time. open / end use max_op_ms (core §4.4).

- `probe_frame_gap_ms` (transports §2). No request takes longer than the declared max_op_ms, and ops that could exceed it are refused (core §7.5). The lease range
  (core §6.4). verify_ms of port_speed, `port_speed_idle_ms` and the conditions to revert ([link](../interfaces/oep-if-link.md) §3). attach, scan and the reset of riscv-dm answer within max_op_ms
  ([wire and debug](../interfaces/oep-if-debug.md) §1, §3, §4.3). restart_max_ms until the probe's internal restart / initialization (excluding OS enumeration and external network connection) ([restart](../interfaces/oep-if-restart.md) §1, §2).

## 2. Host checklist

- **Frames**: a frame may be split into any number of writes or combined with other frames, and the receiver does not rely on those boundaries. Except on TCP, the host does not pause for `probe_frame_gap_ms` in the middle of a frame it sends (transports §2). How COBS is received (transports §1). Before the confirm answer it
  does not send beyond 64 bytes, after it not beyond max_frame, and it can receive up to 65535 bytes (transports §3). Zero-length transfers of vendor bulk (transports §1).
- **Finding probes**: automatic USB identification only by the project's VID:PID `1209:4F45`, a named probe by unit_id, and otherwise
  the user chooses (transports §3). TCP destinations only those found with `_oep._tcp` or specified explicitly by the user, and the TXT unit_id is checked with describe (transports §3). The probing rule: send only confirm, and close if there is no correct answer (transports §3). How ports are chosen within a device known to be an OEP probe (transports §3).
  The order in which transports are tried (transports §3). Opening exclusively (transports §3). Asserting DTR / RTS (transports §4).
- **confirm and revision**: send the range it handles, and after that send the revision in use with `min_rev = max_rev` (core §7.1). Do not use interfaces
  with an unknown revision (core §2.8).
- **Optional ops and functions**: send an optional op only when it is set in ops of that fn's describe. If it is not set, take a way that does not use that op
  (for example: without console marks, do not use from 3 of read but remember the position on the host side; without write, do not send input). For optional functions that are not ops, also
  use only what describe declares (features, mechanism, modes and so on) (core §1.2, §2.8, §7.4). Mandatory ops may be used without waiting for describe.
- **Waiting**: the floor of core §4.4 for every request, including its own link requests. The transfer time on a UART bridge, with `min_max_frame` until the first confirm
  answer on that transport (core §4.4). Get max_op_ms before changing state, and use max_op_ms unless the operation sets a shorter limit for the whole request.
  The time of internal retries, preparation and cleanup is not omitted on the basis of only the sum of explicit DMI waits or the timeout_ms of run (core §4.4).
- **Resending and recovery**: a resend uses the same corr (core §5.1). corr advances cyclically per session_id, never uses 0, and keeps its distance from outstanding requests under half a cycle (core §4.1). Broken TCP boundaries mean reconnecting; for vendor bulk resync, wait longer than `probe_frame_gap_ms` after the last write, noting that it does not become quiet until the lease ends while notifications continue; HID reads anew from the next report with a first (transports §5). If even resends get no answer, that transport failed: before sending anything there, recover or reopen with the procedure of transports §5, and read the state before repeating a request that changes state (core §5.1).
- **Session**: a non-zero random session_id (core §6.1). The answer's lease_ms is authoritative, and keepalive extends it (core §6.4). Handling no_session /
  locked (core §4.3, §6.2). After no_session, open a new session and configure again. If the boot_id changes (in confirm or in open), its own state is invalid and it
  does list again (core §6.5). The requests of one session go on one transport (transports §3). Lock-free requests that need no session use session_id 0 (core §4.1).
- **Probe time**: to map the probe's time to its own time, read it with clock, assign it to the midpoint of the send and receive times, and take half the round trip as the uncertainty ([host development guide](host-development-guide.md) §12).
- **Reading answers**: messages whose role is the request role are discarded. Answers shorter than 5 bytes and event or data frames shorter than their header are
  broken frames (core §2.4). Skip unknown TLVs and tags, use the first of a repeated tag, read a non-zero boolean as true (core §2.1, §2.3). Unknown
  values as in core §2.4. Sort by role and corr (core §10.1). Put the critical mark on TLVs without whose effect the request is meaningless or harmful
  (core §2.3).
- **Text**: replace control characters and invalid UTF-8 before showing answer text (core §2.1). Compare unit_id with serial number, and unit_id with unit_id, ignoring ASCII
  case (transports §3). Do not group by, name by, or use as a key to remember anything an `x-` unit_id (core §7.5). iProduct and
  interface strings are for display only (transports §3).
- **restart** (`oep.probe.restart`): after the answer, treat the probe as answering nothing until it answers confirm in a new boot, reopen it the same as opening anew, and check by boot_id ([restart](../interfaces/oep-if-restart.md) §2; the procedure is in [host development guide](host-development-guide.md) §5.2). On a UART bridge, return to the boot speed (host 2 of [link](../interfaces/oep-if-link.md) §3).
- **port_speed**: when a host uses it, host 1 and 2 of [link](../interfaces/oep-if-link.md) §3 (after the answer of try, wait at least `port_speed_switch_wait_ms` before sending at the new speed; return to the boot speed on the success answer of revert, end, a force open to a different session_id, or an op that restarts). A supporting host decides the recovery wait including the frame/processing time needed. A 4 second wait is not required of every host. Read the current phase with port_state with a new corr, distinguishing it from the resend history (transports §4).
- **Logic capture**: read layout w of any integer from 1 to 128. If w is not a multiple of 8, samples cross byte boundaries ([capture](../interfaces/oep-if-capture.md) §1.1).
- **Analog capture**: when a host shows voltages, it shows the values 0 and 2^b − 1 not as voltages but as out of range (at or below the low end, at or above the high end)
  ([capture](../interfaces/oep-if-capture.md) §1.2 rule 6).

## 3. Interfaces whose names begin with `oep.`

A probe that puts an `oep.` name in list follows the whole document of that interface. A short list of what is mandatory:

| Interface | Mandatory | Optional (what is declared) |
|---|---|---|
| Positioned streams ([common parts](../interfaces/oep-if-common.md) §1) | Apply the common shape, non-consuming read and lifetime only to the ops adopted. If there are marks, page by serial number and handle from 3 | marks/clear/mark/write. If there is mark, also provide marks |
| `oep.wire.rvswd`, `oep.wire.swio`, `oep.wire.swd` ([wire and debug](../interfaces/oep-if-debug.md)) | attach (fixed part method/pins/max_speed, method 0 mandatory), detach, connections. Resources owned by the session. No implicit join / eviction. The attach rules of debug §1 and max_op_ms. The retries and lifetime of debug §2 | Holding the wire after closing (debug §2; if it holds, show it in holds, and if it has settings, declare `channel.{}.hold`), scan (candidate count ≥ 1, finite search), the reset TLV of attach, method 1 of RISC-V (features bit0) |
| `oep.target.riscv-dm` (debug §4) | dmi. One per name, accepting the connections of every supported wire (common §2) | halt/resume/reset, read_block / write_block, run/step: ops. If there is reset, it is a system reset that also resets peripherals, after which it waits for the DM (debug §4.3, within max_op_ms). If there is read_block / write_block, max_length. success only when the cleanup of temporary values is done. On failure too it tries within max_op_ms; if cleanup is impossible it returns failure and closes the connection and stream (debug §4). If step is not ok, moved and dpc are 0; the elapsed_us of run counts from resumereq (debug §4.2, §4.4) |
| `oep.target.arm-adi` (debug §6) | transfer (n = 0 is success, ack 0). Uses the connection of a supported wire, specified explicitly. One per name (common §2) | read_block/write_block declared in ops as a pair. max_length mandatory only when provided |
| `oep.target.console` ([console](../interfaces/oep-if-console.md)) | open/read/close/streams. One per name, openable on the connections of every supported wire (common §2). mechanism in describe (a name list of mechanisms, core §7.7) is mandatory, 1 or more. The reading order of console §3 and the framing of the adopted mechanism | marks/clear/mark/write are ops. Even without marks it does dmseq synchronization and deduplication. Without write it returns only empty answers, and write to SDI is unsupported |
| `oep.fixture.gpio` ([fixture](../interfaces/oep-if-fixture.md) §1) | set, read. mode 0 in the modes of describe | — |
| `oep.fixture.uart` (fixture §2) | configure/read/status. 8N1 in the formats of describe. Until an explicit configure, status has baud 0 and it does not receive. On releasing the plan, buffers and settings are released, and positions do not go back within the same boot. Specifying the same plan again does not change the settings | marks/clear/mark/write, other formats. mark needs marks. Without write it does not declare the TX role |
| `oep.fixture.i2c-target` (fixture §3) | The ops of fixture §3 except stretch (one write is one frame, reads come from where preload_tx put them, ns is the time of the STOP or next START that ended the frame) | stretch (in ops, with max_stretch_us). Internal pull-ups (features bit0). nack_from (features bit1: NACK from the n-th data byte, ACK before that and for the address, and the NACKed byte is also in the frame; a probe that does not declare it refuses the TLV with unsupported) |
| `oep.fixture.spi-target` (fixture §4) | The ops of fixture §4. The bit placement of data (bits that did not come are 0, also in a transfer that ended mid-byte), bits stops at 0xFFFFFFFF, the optional ns TLV is the time CS became inactive. Declare 1 or more supported modes in modes; an unsupported configure is unsupported and leaves the state unchanged. If guarantees cannot be kept under concurrent load, later operations can be refused with unavailable before side effects. cs_setup_ns if MISO is driven by software | LSB first (features bit0). sck_filter (features bit1 and describe sck_filter_ns: SCK pulses shorter than sck_filter_ns are not counted; a probe that does not declare it refuses the TLV with unsupported) |
| `oep.fixture.i2c-controller` (fixture §5) | The ops of fixture §5. repeated START between pieces; without flags bit0 it returns still holding the bus. Reserved addresses are not refused either. NACK, bus errors and the abort of stretch are returned in the result of completed success, with a STOP right there (3 releases the lines). clock_hz chooses and returns a producible value at or below the one asked. max_stretch_timeout_us | Pull-ups (features bit0), min_clock_hz |
| `oep.fixture.spi-controller` (fixture §6) | The ops of fixture §6. The transfers of one transfer are done back to back, gap_ns / setup_ns / hold_ns keep at least the asked values and return the actual values (never shorter). count 0 is CS only. clock_hz chooses and returns a producible value at or below the one asked. 1 or more in modes, time_step_ns, max_delay_ns | LSB first (features bit0), min_clock_hz |
| `oep.fixture.pwm` (fixture §7) | set, status. hz 0 stops and drives low, returns the num / den and duty produced. channels | duty_bits, min_clock_hz |
| `oep.fixture.counter` (fixture §8) | measure. Counts all roles of the plan at the same time and returns the actual window_ns. It only listens, so it may share pins with other functions. channels, max_gate_us | — |
| `oep.fixture.dac` (fixture §9) | set, status. Does not share pins with other fns. channels, bits, range | — |
| `oep.fixture.logic`, `oep.fixture.analog` ([capture](../interfaces/oep-if-capture.md) §1 to §3) | The mandatory ops of capture §3.2. release is mandatory in mode 2, calibration is optional for analog. The configure and query contract of capture §3.3 (mode and rate are mandatory, the TLVs that can be sent per mode, the role of a type 0 trigger is not looked at, samples / segments / rate of 0 are malformed, pretrigger of mode 3 is bounded by max_pretrigger, values not listed are unsupported, the mandatory rows of the answer (frontend_used/reference of analog are optional)). Paging of segments by serial number ([common parts](../interfaces/oep-if-common.md) §1.3). The generation of events. Generations 1 to 0xFFFFFFFF are not reused, and a start when exhausted is refused before side effects. If samples already put in a segment are lost, that segment is not given out and it stops with an error (capture §2.2; when samples not yet put in a segment are lost, it may make a gap whatever the reason (skipping position, flags bit0 in the next segment, dropped in status); entering state 6 always gives stopped reason 2, and write_pos after the error is the start of that segment). After the error, the host discards the received data from write_pos on. The describe of capture §3.5. max/len of read are u16. A finite process that stops communication at the start is included in the start request, and handled by the ordinary rules of max_op_ms/lease. If it has non-immediate triggers, implement arm 1 of trigger_opts (after the pretrigger has accumulated) (capture §3.3). The probe uses only the format the host asked for in the format of configure (capture §1). If it declares formats 1 / 2, keep the order of capture §1.3 / §1.4 (the interval values per carrying method, how change_latch compares with the previous sample, the last partial interval of a segment, how the reduced part is packed). The streaming answer returns data_rate, and does not lower rate or refuse on the grounds of whether sending can keep up (capture §3.3). No record of triggered is 0xFFFFFFFF. | query, force, analog calibration (ops). Notifications: subscribe / unsubscribe (ops). data of mode 3 carries generation/segment_info in every frame and fits within a single segment. Undecided trailing bytes are not returned. Data formats 1 to 3 (formats in describe), arm 0 / rearm 1 / when 1 / hysteresis of trigger_opts (opts of trigger in describe), trigger records (capture §3.9, op triggers, trigger_records), glitch filter, input hysteresis and external clock (capture §3.8) |
| `oep.fixture.capture-group` (capture §4) | bind/start/stop/status, declarations of ops/tracks. All tracks have immediate triggers and the same mode. Before starting, check all validation of bind, the frame capacity of the start answer, and room in every generation. Distinguishing start/stop/error and group/track generations. | Notifications subscribe/unsubscribe. Event sources (capture §4.4, features bit 0): trigger expressions (stages, terms, conditions, abort, on_timeout, holdoff; at most 1 instantaneous condition per term), expressions beyond the trigger_caps declaration are unsupported, all bound tracks are linked, waiting, force (ops), trigger_ns / trigger_uncertainty_ns, triggered. Plan roles of trig_in / trig_out |
| `oep.probe.plan` ([plan](../interfaces/oep-if-plan.md)) | Put in list if there is an interface with plan roles. plan_apply validates the whole request and keeps the remaining assignments and function states. Changes to the set of running assignments (role, channel) / to bound resources are refused. plan_release also validates all targets first. plan_roles if there is a limit | — |
| `oep.probe.restart` ([restart](../interfaces/oep-if-restart.md)) | restart. restart_max_ms in describe. Refused as an op that needs the lock. The answer is completed success, sent first. After the answer it answers no request on any transport until it restarts, and does no intended reset/resume of the target. Target changes due to the MCU's reset state and external circuits are not guaranteed against. After the restart it is the same as at power-on (a new boot_id, only saved settings remain). Within restart_max_ms after the answer left the transport, the probe's internals return to a state that can accept communication. OS enumeration / network connection / the host reopening are separate | — |
| `oep.probe.link` ([link](../interfaces/oep-if-link.md)) | source, sink | port_speed and port_state (ops). Change at a frame boundary, resolving the pipeline first. A host that only receives notifications also extends idle with normal requests. Timers during request processing, and no cancelling of phase 3 (link §3) |
| `oep.probe.memo` ([memo area](../interfaces/oep-if-memo.md)) | list, read, write, delete, max_object and max_objects in describe | The order of split writes and the crc check, objects being written not shown in list and read, at most one being written (it disappears on starting again, delete, or the end of the session), able to hold up to the declared amount, not hiding objects whose crc does not match (memo §2, §3) |
| Settings (core §13) | get of fn 0 (also set/unset if it lets values change), the setting declarations of each fn (the position in the list is the item number, no duplicate names), setting_choice of enums, channel_name of fn 0. Distinguishing counted values from trailing TLVs. label unique within the probe, ignoring case. Initial values at a boot without a save. The change counter not reused within a boot, a no-op leaves generation/pins unchanged. Apply after validating all values of the request. secret not returned. | The supported range of channel items. save/state adopted together with saving. Saves hold names; at boot only the values of declared items are used, disable is applied first, and partial application is shown by state. Network items adopted together with the netif list and network, max_frame 82 or more. Interface items only in their own category. |

### Boundary checks on end and failure

The following are checks when the relevant function in the table above is adopted, and do not require adding functions.

| Contract | Boundaries to check |
|---|---|
| fixture §3/§4 | In the same I2C read, 0xFF from the end of the preload on, and the next slot not consumed. An empty SPI queue has pending/bits/count 0. Cumulative u32 saturates, and is initialized by configure / plan release |
| capture §2.1, core §10.3 | Even when stopped below min_bytes with max_delay_ms=0, the remainder is still to be sent. Answer priority and finite retention are kept. If there is a hole in the received range, it is not full reception even if the end is write_pos |
| capture §4.1 | group.start during acquisition / while waiting for a free segment is refused, keeping state, generations and data. On a start failure after acceptance, the generation advances including tracks not started; failed tracks are 6, tracks not started are 1 |
| core §13.7 | The fixed shape of a save failure and the following state. A save broken by power loss is not used as a complete save (a save whose completeness cannot be confirmed is storage_state 2, reason 1). Atomicity of the save (either the previous or the new complete save remains) is recommended, and an implementation that has it checks it with power loss |
| debug §4.1 | Raw DMI procedures that are indivisible when used together with the console. Split procedures with the console closed are not atomic; after a failure midway, check the state and recover |

## 4. How to check

**Test vectors** ([`tests/vectors/`](../tests/vectors/)). `tools/oepvectors1.py` computes them from the normative documents. If a vector and a document
disagree, the document is right and the vector is corrected. Coverage:

| File | What it covers |
|---|---|
| `interface_boundaries.json` | Batching / stopping / losses of notifications, the failure answer and state of save, the start boundary of group, the end / empty queue / saturation of fixtures. Power loss during saving and actual bus behaviour are observed separately in each implementation |
| `checks.json` | CRC-16 (transports §1), the CRC-8 of dmseq |
| `cobs.json` | COBS encoding and whole serial port frames, including the other form decoding accepts (transports §1) |
| `hid_reports.json` | HID reports (transports §1): count and first when frames are packed into reports, and the messages that can be read when reports are missing, when opened midway, or when count or first are broken |
| `headers.json` | Request and answer headers, TLV encoding (core §2.2, §4.1, §4.2) |
| `core_extensions.json` | Examples adding unknown answer TLVs after the fixed parts of open/keepalive/end/clock and refusals. The extension rule is the same even if the fixed part is empty (core §2.3, §4.3) |
| `core_lifecycle.json` | Credits of unfinished resends, the boundary between lease processing and sending, monitoring and loss of a transport (core §4.4, §5.1, §6.1) |
| `core_policy.json` | The optional policy decision, and its order relative to resending, force and public discovery (core §4.3) |
| `confirm.json` | confirm exchanges (core §7.1) |
| `discovery.json` | list (core §7.2; empty for the example probe without interfaces, since fn 0 is not included), the fn 0 describe (core §7.3, §7.5), describe beyond the end, header refusals unknown_function / unknown_operation (step 1 of core §4.3) |
| `refusals.json` | Requests and their exact answers for the refusals of core §2.3 and §4.3 (states where only one reason applies) and for unknown TLVs that are ignored. Requests to which 2 or more reasons apply at step 4 of core §4.3 may be refused with any of them (an intended simplification), so there are no vectors for them, and tests accept any one |
| `sessions.json` | Session scenarios: the decision table (core §6.2), the resend table (core §5.1; a resent end), release at end and no_session (core §9), force, session_id 0 (core §4.1), clock without a session and with one open (core §7.6). Requests and answers sent in order from a decided initial state |
| `ops_encoding.json` | The boundaries of the value of the common describe tag ops (shortest, longest, wrong length, the op 0xFF boundary, another encoding of the same set) and the set of ops a correct value expresses (core §7.4) |
| `ops.json` | Bytes per op: the request, the probe state it assumes, the answer (`oep.probe.restart`, `oep.probe.plan`, `oep.probe.link`, gpio, rvswd, riscv-dm, console (paging marks by serial number, the last page of streams), logic (the configure contract, query not looking at the role of an immediate trigger, malformed samples 0, an empty page of segments, status / segments / read and stopped when dropping within a segment, the data frame (`data`) of data that had started into a segment dropped in streaming and the status and segments after it, immediate bind of capture-group and refusal of unsupported triggers / future critical selectors), a failed step of riscv-dm, the n = 0 transfer of arm-adi, partial bytes of spi-target (MSB / LSB first), start of capture-group and refusal to bind non-immediate tracks, capture event frames (`events`, generations), settings (counted get/set/unset of fn 0, optional state, a label of maximum length, label uniqueness, partial application, exhaustion of the change counter, the secret passphrase, the ipv4 form, the network answer, interface items), other parts of logic). Sequence answers are `count × element` without element lengths (core §2.3) |
| `logic_layout.json` | The logic capture stream ([capture](../interfaces/oep-if-capture.md) §1.1): layout w and pos, channel levels, the bytes of a segment. A w that is not a power of 2 (w = 3, samples crossing bytes) |
| `capture_formats.json` | Capture data formats ([capture](../interfaces/oep-if-capture.md) §1.3 logic blocks, §1.4 analog blocks, §3.8 timestamped states) and trigger expressions (capture §4.4) |
| `interface_profiles.json` | Examples of small declarations (bytes of list and describe): a probe without named functions, a third-party extension, a receive-only UART, raw ARM / RISC-V, a console |
| `settings_file.json` | [Settings file](oep-settings-file.md): the file exported from declarations, get values and the memo area, and import into a probe with other numbers |

An implementation reads the JSON and compares its own encoder, decoder and answers byte by byte. To check that the vectors match the documents and the registry:

```sh
python3 tools/oepvectors1.py --check      # exit 1 if the file differs from what the rules give
cd tests && uv run pytest vectors          # checks the vectors with separate code (binascii), and the tool's --check
```

A host is tested against both an independent virtual bench and hardware, and a probe checks list, describe and each op with an independent host.
A bridge or broker that answers OEP requests itself (one that shows another debugger as an OEP probe, core §5.1, host guide §7) is also
a probe as seen from the host, and is subject to these checks. Missing mandatory ops and mismatches between the declaration of ops and the implementation are found by running checks against its listener (TCP and so on).
That a host does not assume optional ops is checked with a probe of the minimal configuration that offers no optional ops (an option of the virtual bench and so on). The concrete tools and how to start them are kept in the implementation repository that provides them.

The shared vectors check only the encodings and scenarios that their files list, and do not prove overall conformance. Each implementation tests state transitions, contention, resending and time conditions for all items of §1 to §3 of this document in its own repository. Electrical rules and conditions that only arise on hardware are checked on the corresponding hardware.

## 5. What conformance lets you claim

There is no certification. A conformance claim is the implementer's own statement, checked against this list and the normative documents.

- A probe that meets section 1, and section 3 for every `oep.` interface it puts in list, may call itself an **OEP v1 probe**,
  listing the interfaces (and revisions) it implements. A host that meets section 2 may call itself an **OEP v1 host**. The claim is about protocol
  revision 1 (core §2.8), and does not mean it includes optional functions.
- An implementation that changes the shapes on the wire, that answers in ways the specification does not allow, or that puts its own interfaces or tags under `oep.` names
  does not conform (core §12 rules 1 and 7). Its own interfaces use reverse-domain names.
- Conformance does not grant permission to use the project's USB VID:PID. That is granted separately under the conditions of PID-USE of [oep-probe-arduino](https://github.com/Open-Embedded-Probe/oep-probe-arduino)
  (made from that library, source published, speaks OEP as specified, names itself honestly, and so on).
  Other implementations use their own USB IDs. A host opens them when the user names them or chooses the port (transports §3).
- Conformance does not make a probe identified automatically, and says nothing about the target chips it handles, its speeds, or electrical behaviour beyond what the normative documents require.
