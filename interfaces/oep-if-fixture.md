# OEP interface: fixture v1

[日本語](oep-if-fixture.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **normative** (v1). For the freeze state and the language and compatibility policy, see [Versions and stability](../docs/versioning.md). The core is [OEP core](../docs/oep-core.md), and the common parts are in [Common parts](oep-if-common.md) (§1 positioned
stream). The only definition of the numbers is `registry/oep-v1.toml`. Capture is in [Capture](oep-if-capture.md).

## 0. Interfaces and common rules

| Name | revision | Role | plan role | Target family |
|---|---:|---|---|---|
| `oep.fixture.gpio` | 1 | drives and reads pins | 1 = line | used for every family |
| `oep.fixture.uart` | 1 | UART transmit and receive | 1 = RX, 2 = TX | used for every family |
| `oep.fixture.i2c-target` | 1 | I2C target (the controlled side). Tests the DUT's I2C controller | 1 = SDA, 2 = SCL | used for every family |
| `oep.fixture.spi-target` | 1 | SPI target. Tests the DUT's SPI controller | 1 = SCK, 2 = MOSI, 3 = MISO, 4 = CS | used for every family |
| `oep.fixture.i2c-controller` | 1 | I2C controller (the controlling side). Tests the DUT's I2C target | 1 = SDA, 2 = SCL | used for every family |
| `oep.fixture.spi-controller` | 1 | SPI controller. Tests the DUT's SPI target | 1 = SCK, 2 = MOSI, 3 = MISO, 4 = CS | used for every family |
| `oep.fixture.pwm` | 1 | puts out a square wave with the specified frequency and duty (the DUT's clock, PWM input, stimulus) | k = output k (from 0) | used for every family |
| `oep.fixture.counter` | 1 | counts edges within a set time (frequency, number of pulses) | k = input k (from 0) | used for every family |
| `oep.fixture.dac` | 1 | puts out an analog value (the DUT's ADC input, reference) | k = output k (from 0) | used for every family |

All of them handle only channels assigned by [plan](oep-if-plan.md). The invariance of the state of an unchanged assignment follows plan §2.1. The ops in the tables below are all required (core §1.2) unless their section says optional.

configure of UART / I2C / SPI validates the format, supported values and resources before any side effect. On rejected, the existing settings, queues and pins do not change
(the progress of asynchronous transmission and reception is core §6.3). If initialization after acceptance fails, the result is completed failed; partial is not returned.
On both success and failure the plan is kept, and after a failure the function recovers from the unconfigured state each section defines through a new configure by the host.
Rollback to the previous hardware settings is not required. Everything up to the cleanup is included in max_op_ms of the core.

## 1. `oep.fixture.gpio`

A minimal implementation MAY have only set/read and mode 0; output modes and pulls are declared only for the supported ones.
Pin assignment of GPIO uses plan. This does not require this dependency of other third-party extensions that have no plan.

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x10 | set | n(u8), n × (channel(u16), mode(u8)), [TLV] | — | needed |
| 0x11 | read | n(u8), n × channel(u16) | n(u8), n × level(u8: 0 / 1), [TLV] | not needed |

| mode | Meaning |
|---:|---|
| 0 | input (floating) |
| 1 | input, pull-up |
| 2 | input, pull-down |
| 3 | output low |
| 4 | output high |
| 5 | open-drain low (pulls) |
| 6 | open-drain release (high by an external or target pull-up) |

- The sequence is done one by one in the order of the request (pulling NRST and then releasing it, for example, can be sent in one request). All checks are done first, and
  set does not fail except by being refused in the checks (success).
- An unassigned channel (set, read) is rejected unavailable with nothing done (the payload is the TLVs of core §4.3: channel 0x02, and the position in the sequence,
  tag 0x40 index (u8)). A mode that cannot be handled (not in the declaration) is rejected unsupported (payload `0x00`, followed by the same channel / index TLVs).
- The modes that can be handled are declared by modes of describe (tag 0x40, a u32 bit set, bit n = mode n). 0 (input) is required.
- **A channel taken by plan keeps its previous state until the first set** (it stays in the idle state; if it is an output idle, it keeps driving that level).
  Taking it does not change the level.
- The plan of GPIO also accepts channels with an output idle.
- read only observes the current level; it does not switch to input or change the output, pull or output strength.
  On release of the plan or the end of the session, the GPIO settings made by that plan are undone, and the pins return to the idle state of core §8/§9.

The probe decides the output strength. v1 does not define switching of steps; if needed, it is defined by a TLV of a new optional function.
When a host's operation depends on the strength it specified, it sends that request TLV as critical, so that an unsupporting probe does not ignore it silently (core §2.3).

## 2. `oep.fixture.uart`

There is one stream per fn. A minimal implementation is configure/read/status and MAY be receive-only.
Compared with the buffer and position management that hold reception with RX assigned, the ring of marks and the send queue are not needed when the respective optional functions are not provided.

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x10 | configure | baud(u32), [TLV] | baud(u32, the actual value on success, 0 on failed), [TLV] | needed | required |
| 0x11 | read | from(u8), arg(u64), max(u16), [TLV] | start(u64), flags(u8), len(u16), data, [TLV] | not needed | required |
| 0x12 | marks | from_serial(u32) | more(u8), count(u8), count × mark, [TLV] | not needed | optional |
| 0x13 | clear | — | — | needed | optional |
| 0x14 | mark | value(u8) | — | needed | optional; marks also needed |
| 0x15 | write | count(u16), data | accepted(u16), [TLV] | needed | optional |
| 0x16 | status | — | baud(u32, the actual value), format(u8), [TLV] | not needed | required |

- ops 0x11 to 0x15 have the form of [Common parts](oep-if-common.md) §1 (without the stream u32), with the same numbers as `oep.target.console`.
- Optional ops are set in ops only when provided. An absent op is unknown_operation. Without marks, from 3 of read is unsupported (fixed-part mark 0).
  clear can be provided without marks; in that case the clear mark is not required. Optional ops are not declared with new bits of features.
- An fn that does not provide write does not accept the TX role of plan and does not declare role_channels/channel_group of that role.
  Even in an fn that provides write, if the current plan has no TX or it is not configured, write is unavailable (cause 6). With a TX-only plan or an unconfigured plan there is no reception.
  Received data already retained can still be read with the usual read of common parts §1.2 during that time. When there is no retained data, position and gap are also returned by the same rules.
- In the state with neither RX nor TX and no plan made, valid requests of the provided ops above are refused with unavailable (cause 6). The header, session and format rules of the core are applied first.
- TLV 0x01 format (u8) of configure: bit0-1 data length (0 = 8, 1 = 7), bit2-3 parity (0 none, 1 even, 2 odd), bit4 stop
  bits (0 = 1, 1 = 2). If absent, 8N1. A value not in the declaration (formats) is rejected unsupported (the tag as received). baud returns the achievable value, and if it is off from the request
  by more than ±5% (`uart_baud_tolerance_pct` of the registry), rejected unsupported (payload `0x00`). baud 0 is malformed.
- configure returns success after the assigned RX/TX are ready to be used with the decided actual baud and the specified format. If initialization fails, it stops transmission and reception,
  returns to unconfigured, and returns completed failed with baud 0. RX returns to the idle state of core §8, and an assigned TX keeps the resting high below.
  An accepted configure, whether it succeeds or fails, discards unsent TX and does not carry it over to the new settings. What already went out on the line cannot be cancelled, and the amount that reached the peer is not guaranteed.
- **status** (lock not needed): if configured, the actual baud/format. Before the first configure and after a failed configure, it returns baud 0 and format 0.
  0 is the mark of unconfigured; there is no communication at 0 baud. There is no need to apply an unsupported default baud implicitly.
- **plan creates the stream, and releasing the plan removes it**. The session's configure is also removed when the plan is released.
  Reception starts after the host explicitly configures. Even if a value is saved on the host, reception does not start implicitly.
  While a configured plan exists, reception is stored regardless of the reading host or the session_id of requests.
  Even when configure is done again, whether it succeeds or fails, the received data, marks, positions and serials already put in the stream are kept
  (the host puts a mark if it needs a boundary). **Positions and mark serials do not go back within a boot even when the plan is released and made again**
  ([Common parts](oep-if-common.md) §1.1). When marks is provided, receive errors are mark lost (detail 2 framing, 3 parity).
  When marks is not provided, recording marks and managing serials is not required. The position of the stream is kept within the same boot.
- A change of a configured assignment is refused with unavailable (cause 6);
  the host reads the data it needs, does plan_release and then makes it again. A change of an unconfigured assignment releases the buffer and marks and replaces it, still unconfigured.
  Positions and mark serials do not go back with that change either.
- **The TX line is kept at the UART rest (high), except while transmitting, while it is assigned by plan (also before configure)**: taking the plan is starting to use TX (core §8) (so that the peer's receiver does not pick up noise). When the plan is
  released, UART driving stops and the pin goes to the idle state of core §8. A fixture that does not want the peer's input to float even after the release sets that pin to an input with pull-up
  with the core setting `channel.{}.idle` (core §13.8) and saves it.
- The formats that can be handled are declared by formats of describe (tag 0x40, n(u8), n × u8; values of TLV 0x01 of configure). 8N1 (0) is required.

### 2.1 Serial port pass-through (optional settings)

Optional settings items (core §13; the category is the fn of that
`oep.fixture.uart`) that let an ordinary serial monitor show the target's output even on a probe whose only port is a UART bridge. These settings apply independently of sessions (core §9).

| Name | form | key_kind | Meaning |
|---|---|---|---|
| `passthrough.{}.rx` | channel | transport (serial port) | the receiving channel. With a value, this UART is passed through on that port |
| `passthrough.{}.baud` | u32 | transport | speed. Without a value, 115200 |
| `passthrough.{}.format` | enum | transport | format (the value of TLV 0x01 of configure). Without a value, 8N1 |

- The key is a serial port (kind 1 to 3, core §7.5). Other transports are unsupported.
- rx is a channel declared as role 1 (RX) of that fn (others are unsupported). If rx is disable, or has an output idle, unavailable cause 5.
- baud and format follow the same rules as configure (baud 0 is malformed, a baud that cannot be made is unsupported). The choices of format (setting_choice) are the values of formats,
  and the names join the data length, the parity (`n`, `e`, `o`) and the stop bits (`8n1`, `7e2`).
- **Pass-through condition**: while all of the following hold — no session request has come from that port, that fn has no plan, and no other plan, connection or setting holds rx —
  the probe receives with that UART on rx only (TX is not used; rx is not driven) and sends the received bytes to the port outside frames as in [transports](../docs/oep-transports.md) §4.
  When any of them stops holding, it stops receiving and returns rx to the idle state. When the condition holds again, it resumes.
- Pass-through does not contend with session resources: a session's plan, connection or use of the port stops the pass-through and goes first (it is not refused because of the pass-through).
- Bytes received by pass-through are not put in the OEP stream (read) and are not retained. What could not be sent to the port is discarded.
- Sending bytes that came from the port outside frames to the target is not defined (input uses OEP write).
- Only one pass-through can be set on one port (it does not overlap with pass-through of any UART fn, nor with console pass-through ([Console](oep-if-console.md) §2.1)).
  An overlapping set is unavailable cause 5.

## 3. `oep.fixture.i2c-target`

The probe becomes an I2C target, receives writes of the DUT's controller and answers its reads. Received frames are stacked in a queue in the probe, and the host
takes them out with read_rx.

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x10 | configure | address(u8, 7 bits), [TLV nack_from(u16)] | — | needed |
| 0x11 | read_rx | — | pending(u8), count(u16), data, [TLV ns(u64): the time of the STOP or next START that ended that frame, optional] | needed |
| 0x12 | preload_tx | count(u16), data | — | needed |
| 0x13 | status | — | state(u8), queued(u8), rx_frames(u32), tx_slots(u8), errors(u32), [TLV] | not needed |
| 0x14 | stretch | stretch_us(u32) | — | needed |

- The plan of this fn has exactly one each of role 1 and 2, on separate channels. A plan_apply with a combination that does not meet this is refused with unsupported (the tag of role_assignment).
  A change of the set of assignments (role, channel) while running (state 1) is unavailable (cause 6). Releasing the plan or replacing an unset role returns it to the initial state (state 0;
  the queue, the slots and the totals are cleared, and the value of stretch is 0).
- SDA and SCL are driven **open-drain only**: the probe pulls low or releases, and does not drive high.
- **Internal pull-up**: a probe that puts its own pull-ups on SDA / SCL while configured declares it with bit0 of features (internal pull-up).
  A probe that does not declare it puts no pull-up.
- In state 0 it ACKs no address, stops driving and internal pull-ups as an I2C function, and puts the channels in the idle state of core §8.
  A pull set as the idle state is distinct from the internal pull-up of the I2C function.
- configure makes the target again (stacked frames, slots, rx_frames and errors are cleared; the value of stretch is kept). When this fn has no
  plan, rejected unavailable (cause 6). If address exceeds 0x7F, rejected malformed. Addresses 0x00 to 0x07 and 0x78 to 0x7F (those the I2C specification reserves: general call, start byte, the 10 bit prefix and so on) are rejected unsupported (payload `0x00`).
- configure returns success after reaching state 1. If initialization fails, it returns to state 0, empties the receive queue and the send slots, and sets rx_frames and errors to 0.
  The value of stretch is kept even on failure. On both success and failed the answer has no fixed part, and the tail is [TLV].
- **Write**: a write of the controller is handled per transaction (from START to STOP or the next START), and each byte gets ACK (except by nack_from). One write with data
  is one frame and is stacked in the queue. What exceeds max_length is discarded (the frame is stacked with data up to max_length), and errors is incremented by 1.
  A write without data (only the address byte) stacks nothing and counts nothing.
- **nack_from** (TLV of configure, u16, critical; optional): per write, NACK is returned for the n-th data byte after the address (1 is the first) and all after it.
  Bytes before it and the address byte get ACK. If 0 or absent, all get ACK. Bytes that got NACK are also put in the frame as received
  bytes (the counting and the max_length rules are the same as above). It does not affect reads. The value is replaced by configure and kept until configure
  is done again. A probe that has it declares it with bit1 of features. A probe that does not declare it refuses this TLV with unsupported (critical, core §2.3).
- read_rx takes out and returns the oldest frame (count 0 if none). In state 0, rejected unavailable (cause 6). pending is the number
  remaining after taking it out (stopped at 255). If the next frame comes when the queue holds queue_depth frames, the new frame is discarded and errors is
  incremented by 1 (it is not counted in rx_frames). The depth of the queue is queue_depth of describe. errors grows by at most 1 per write (a write that exceeded max_length and
  also overflowed the queue counts 1).
- **Read**: reads of the controller are answered from the slots, in the order put by preload_tx. count is 1 to max_length (0 is malformed). Unread slots are
  up to queue_depth. preload_tx when all are filled puts nothing and is rejected unavailable (cause 2). In state 0, rejected unavailable (cause 6). Even if the number of bytes the controller
  read differs from the length put, the next read is answered from the next slot. **When the slots are empty, and after the length put is used up in the same read, 0xFF is put out**.
  The next slot is not consumed in the middle of the same read.
- Success of preload_tx is returned after the data put is ready to be used by a controller read that starts after it.
- status: state 0 unset, 1 running. queued is the number of stacked frames (stopped at 255). rx_frames is the total of frames stacked in the queue (those discarded on overflow are not
  counted), tx_slots is the number of slots put by preload_tx and unread, and errors is the total (u32) of writes that had an overflow or exceeded max_length.
  rx_frames and errors saturate at 0xFFFFFFFF and return to 0 on configure or plan release.
- stretch is the time (µs, 0 = none) for which SCL is held low for each received data byte, after the 8th bit, with ACK put out, before the ACK clock.
  On a read, it is held the same time after the address matches. It is not held on the address byte of a write. stretch is optional (core §1.2). If stretch_us exceeds max_stretch_us of describe, rejected unsupported. It is accepted regardless of state
  (also in state 0), and the value takes effect from the next byte received. configure does not change the value.
- describe: ops, role_channels, max_length (maximum bytes of one frame), max_clock_hz (the verified upper limit of SCL), features (bit0 internal pull-up, bit1 nack_from),
  queue_depth (tag 0x40, u8: the upper limit of the number of frames that can be stacked and of the number of unread slots),
  max_stretch_us (tag 0x41, u32: the largest µs stretch accepts. 1 or more. A probe with stretch always puts it).
- max_length is a value with which the preload_tx request (header 10 + count 2 + data) and the read_rx answer (header 5 + pending 1 + count 2 + data)
  fit in the max_frame of every transport. A frame an external controller wrote cannot be split with read_rx. The optional timestamp TLV is added only when it fits.

## 4. `oep.fixture.spi-target`

The probe becomes an SPI target, answers one transfer delimited by CS with MISO bytes put beforehand, and stacks the MOSI bytes.

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x10 | configure | mode(u8: SPI mode 0 to 3), bit_order(u8: 0 MSB first, 1 LSB first), [TLV sck_filter(u8)] | — | needed |
| 0x11 | arm | length(u16), count(u16), tx(count bytes), [TLV] | — | needed |
| 0x12 | read_rx | — | pending(u8), bits(u32), count(u16), data, [TLV ns(u64): the time CS became inactive in that transfer, optional] | needed |
| 0x13 | status | — | state(u8), mode(u8), bit_order(u8), armed(u8), queued(u8), transactions(u32), errors(u32), [TLV] | not needed |

- **SPI mode** = CPOL × 2 + CPHA. CPOL is the level of SCK while CS is inactive (0 low, 1 high). With CPHA 0, each bit is captured at the first SCK
  edge of its clock period and changes at the second edge, so the first bit of MISO is on the line before the first SCK edge (cs_setup_ns, below). With CPHA 1,
  each bit changes at the first edge of its clock period and is captured at the second edge. The first edge is the edge leaving the CPOL level. Bytes are sent,
  in both directions, MSB first or LSB first as bit_order says.
- The plan of this fn has exactly one each of roles 1 to 4, on separate channels. A plan_apply with a combination that does not meet this is refused with unsupported (the tag of role_assignment).
  A change of the set of assignments (role, channel) while running (state 1) is unavailable (cause 6). Releasing the plan or replacing an unset role returns it to the initial state (state 0;
  mode and bit_order are 0, and the queue, the wait and the totals are cleared).
- configure makes the target again (stacked transfers, the wait, transactions and errors are cleared). When this fn has no plan, rejected unavailable
  (cause 6). mode above 3 or bit_order above 1 is rejected malformed. bit_order 1 without bit0 of features is rejected
  unsupported. A mode not in modes of describe is also unsupported (fixed-part mark 0), and the state does not change.
  Not all of modes 0 to 3 are required; one or more are provided. **CS is active low**.
- **sck_filter** (TLV of configure, u8, critical; optional): 1 means pulses shorter than sck_filter_ns (describe) on the SCK input are not counted (no extra edges are counted from slow edges or spikes coupled
  from a neighboring line). 0 means no filter (the same as without the TLV). 2 or more is rejected malformed. A probe without bit1 of features
  answers with rejected unsupported, as for an unknown critical TLV. While it is on, the probe can receive only transfers in which SCK High and Low are both longer than sck_filter_ns
  (max_clock_hz is the limit without the filter). The host chooses it only when the peer is a controller of such speed.
- configure returns success after reaching state 1. If initialization fails, it returns to state 0 and sets mode, bit_order, armed, queued, transactions and errors to 0.
  It discards the receive queue and the send data of arm, stops driving as an SPI function, and returns the channels to the idle state of core §8.
  On both success and failed the answer has no fixed part, and the tail is [TLV]. External transfers in state 0 are neither received nor counted, and do not consume an arm.
- arm in state 0 (unset) is answered with rejected unavailable (cause 6), and the state does not change.
- arm waits for the next single transfer: length is the maximum bytes to receive (1 to max_length; 0 is malformed, exceeding is unsupported), and tx is the bytes to put on MISO
  in that transfer (count ≤ length; count > length is rejected malformed; the missing part is 0). arm while waiting is rejected unavailable (one at a time). **A transfer while not armed
  discards MOSI and counts transactions and errors**. **MISO is 0 outside tx (not armed, after tx is used up)**. A CS that becomes active and returns to inactive without any SCK
  (0 bits) is not taken as a transfer: nothing is stacked, neither transactions nor errors count, and arm keeps waiting.
- Success of arm is returned after tx can be put out in the next transfer. A transfer that starts after that (one that respects cs_setup_ns) can be answered by this arm.
  If even when configured it cannot reach that state, it arms nothing and answers completed failed (no fixed part, [TLV]).
- **During state 1, the probe drives MISO only while CS is active.** While CS is inactive, MISO is not driven (an input without pull),
  except during cs_setup_ns after CS becomes inactive (below).
  "MISO is 0 outside tx" refers to the bits of the transfer while CS is active in state 1. In state 1, SCK, MOSI and CS are always inputs.
  In state 0 (before configure, after an initialization failure) the channels are in the idle state (core §8).
- When a transfer ends by CS, the MOSI bytes and the number of bits that actually came (bits, stopped at 0xFFFFFFFF) are stacked in the queue, and transactions is incremented by 1. The number of bytes of data is bits divided by 8,
  rounded up, stopped at length. The k-th bit (from 0) on the line is placed in byte floor(k / 8) of data, at bit 7 − (k mod 8) if MSB first,
  at bit k mod 8 if LSB first (the same for a transfer that ended in the middle of a byte). Bits of the last byte that did not come are 0. What exceeds length is discarded, and errors is incremented by 1 (the transfer is stacked with bits as the number that actually came and data
  up to length). A transfer that ends when the queue holds queue_depth transfers is discarded without stacking, and errors is incremented by 1 (it is counted in transactions).
  errors grows by at most 1 per transfer. read_rx returns the oldest one (if none, pending/bits/count are all 0, data is empty, and no timestamp is added). In state 0, rejected
  unavailable (cause 6). pending is the rest after taking it out (stopped at 255).
- status: state 0 unset, 1 running. armed is whether it waits for a transfer. queued (stopped at 255), transactions (total of finished transfers),
  errors (total, u32, of transfers that had any of overflow, not armed, or exceeding length).
  transactions and errors saturate at 0xFFFFFFFF and return to 0 on configure or plan release.
- describe: ops, role_channels, max_length (maximum bytes of one transfer), max_clock_hz (the verified upper limit of SCK), features (bit0 LSB first, bit1 sck_filter),
  queue_depth (tag 0x40, u8), modes (tag 0x41, u8. Required. Bit k indicates support of mode k. Bits 4 to 7 are 0, and the value is 1 or more),
  cs_setup_ns (tag 0x42, u32, below), sck_filter_ns (tag 0x43, u32, ns. A probe that sets bit1 of features always puts it. 1 or more).
- max_length is a value with which an arm request of maximum length (header 10 + length 2 + count 2 + tx) and the read_rx answer (header 5 + pending 1 + bits 4 + count 2 + data)
  fit in the max_frame of every transport. It is not assumed that a transfer of an external controller can be split with read_rx. The optional timestamp TLV is added only when it fits.
- **cs_setup_ns** (tag 0x42 of describe, u32, ns): the shortest time from CS becoming active to the first SCK edge for which
  the probe guarantees that MISO is driven with the first bit. The guarantee is kept for the accepted combination of resources.
  A probe that cannot keep max_clock_hz or cs_setup_ns in simultaneous use with other fns refuses a later configure/attach/start and so on
  with unavailable (cause 2; the diagnostic TLV of the fn if needed) before side effects, following core §8.1.
  The same applies when the SPI configure comes later. Simultaneous execution of any combination of all fns is not required.
  During that time after CS becomes active, MISO is either not driven or driving the first bit; it never takes another value. After CS becomes inactive,
  MISO stops being driven within the same time. A probe that drives MISO with the first bit as soon as CS becomes active omits this tag or declares 0. A probe that starts driving MISO
  in software after seeing CS become active declares it. The host shows this value to the user. A master that starts SCK earlier than cs_setup_ns after CS becomes active
  cannot rely on the first bit.

## 5. `oep.fixture.i2c-controller`

The probe becomes an I2C controller and writes to and reads from the DUT's target. One transfer is a sequence of parts joined by repeated START,
and it ends either by putting out STOP or by keeping the bus without putting it out.

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x10 | configure | clock_hz(u32), stretch_timeout_us(u32), [TLV] | clock_hz(u32), [TLV] | needed |
| 0x11 | transfer | flags(u8), n(u8), n × part, [TLV] | result(u8), at(u8), index(u16), count(u16), data, [TLV] | needed |
| 0x12 | status | — | state(u8), held(u8), transfers(u32), errors(u32), [TLV] | not needed |

- The plan of this fn has exactly one each of role 1 and 2, on separate channels. A plan_apply with a combination that does not meet this is refused with unsupported (the tag of role_assignment).
  A change of the set of assignments (role, channel) while running (state 1) is unavailable (cause 6). Releasing the plan or replacing an unset role,
  if the bus is held, puts out STOP and then returns to the initial state (state 0, held 0, totals cleared). The same at the end of the session.
- SDA and SCL are driven **open-drain only** (as in §3). The internal pull-up is declared with bit0 of features, as in §3.
  In state 0, driving and internal pull-ups stop, and the channels are put in the idle state of core §8.
- configure makes the controller again: if the bus is held, it puts out STOP, and sets transfers and errors to 0. When this fn has no plan,
  rejected unavailable (cause 6). clock_hz 0 or stretch_timeout_us 0 is rejected malformed. For clock_hz, the probe chooses the nearest SCL frequency it can produce
  at or below the value and returns it in clock_hz of the answer. A value lower than min_clock_hz or above max_clock_hz, and a stretch_timeout_us above
  max_stretch_timeout_us, are rejected unsupported (payload `0x00`), and the state does not change. configure returns success after reaching state 1.
  If initialization fails, it returns to state 0 and answers completed failed (no fixed part, [TLV]).
- **Part**: dir(u8: 0 write, 1 read), address(u8: 7 bits), count(u16), followed by data(count bytes) for a write.
  Parts are done in the order of the sequence; the first part starts with START (repeated START if the bus is held), and the following parts with repeated START.
  address is sent with dir appended as the R/W bit. address accepts all of 0x00 to 0x7F (unlike §3, reserved addresses are not refused either).
  A write with count 0 is a write of only the address byte (to check whether the peer is there). A read reads count bytes, returns NACK on the last byte
  and ACK on the bytes before it.
- **flags**: if bit0 = 1, STOP is put out after all parts finish. If 0, it returns keeping the bus without putting out STOP (held 1), and the next
  transfer starts with repeated START. n 0 with bit0 = 1 puts out only STOP (does nothing if the bus is not held). bit1 to 7 are 0 (core §2.5).
- Checks of the request (all refuse with nothing done): state 0 is rejected unavailable (cause 6). n 0 with bit0 = 0, dir above 1, address above
  0x7F, a read with count 0, or part lengths that do not match the request are rejected malformed. If the total of the counts of writes and reads exceeds max_length,
  rejected unsupported.
- **result**: 0 all finished, 1 NACK on the address byte, 2 NACK on a data byte of a write, 3 lost arbitration or a bus error (a change of SDA outside
  STOP and so on), 4 the target held SCL low longer than stretch_timeout_us. at is the position of the part where it stopped (from 0; 0 for result 0),
  index is the position, within that part, of the byte NACKed in result 2 (from 0; 0 otherwise). A NACK of result 2 is result 2 even on the last byte of the part
  (I2C also allows a NACK on the last byte of a write, so the host judges). count and data are the bytes read until it stopped, joined
  in the order of the read parts. transfer answers completed success regardless of result.
- With result 1 to 4, the sequence of parts stops there. 1, 2 and 4 put out STOP, and 3 releases SDA and SCL. In both cases held 0.
- One transfer fits in max_op_ms of the core. A length that does not fit (the probe decides from clock_hz and count) is rejected unsupported with nothing done, as when it
  exceeds max_length.
- status: state 0 unset, 1 running. held is 1 if the bus is held (before STOP). transfers is the total of answered transfers (those with n 0 that did nothing
  are not counted), and errors the total of those whose result is not 0. Both saturate at 0xFFFFFFFF and return to 0 on configure or plan release.
- describe: ops, role_channels, max_length (the upper limit of the total bytes written and read in one transfer), max_clock_hz (the verified upper limit of SCL),
  features (bit0 internal pull-up), max_stretch_timeout_us (tag 0x40, u32. Required. 1 or more), min_clock_hz (the lower limit of SCL configure accepts. 1 if absent).
- max_length is a value with which the request of the largest write-only transfer (header 10 + flags 1 + n 1 + part 4 + data) and the largest answer of a read-only transfer
  (header 5 + result 1 + at 1 + index 2 + count 2 + data) fit in the max_frame of every transport.

## 6. `oep.fixture.spi-controller`

The probe becomes an SPI controller, activates CS, puts out SCK, and returns the bytes sent on MOSI and received from MISO. One transfer is
a sequence of transfers with specified CS times, done back to back at intervals that do not depend on the host's round trips.

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x10 | configure | mode(u8), bit_order(u8), clock_hz(u32), [TLV] | clock_hz(u32), [TLV] | needed |
| 0x11 | transfer | n(u8), n × transfer, [TLV] | n(u8), n × (gap_ns(u32), setup_ns(u32), hold_ns(u32), count(u16), rx(count bytes)), [TLV] | needed |
| 0x12 | status | — | state(u8), mode(u8), bit_order(u8), transfers(u32), [TLV] | not needed |

- mode, bit_order, CS being active low, and how bits are taken are as in §4 (the same lines seen from the controller side).
- The plan of this fn has exactly one each of roles 1 to 4, on separate channels. A plan_apply with a combination that does not meet this is refused with unsupported (the tag of role_assignment).
  A change of the set of assignments (role, channel) while running (state 1) is unavailable (cause 6). Releasing the plan or replacing an unset role returns it to the initial state
  (state 0; mode and bit_order are 0, totals cleared).
- During state 1, the probe drives CS high and SCK at the CPOL level. MOSI is driven, and its level outside transfers is decided by the probe. MISO is
  an input without pull. In state 0 the channels are put in the idle state of core §8.
- configure makes the controller again (sets transfers to 0). When this fn has no plan, rejected unavailable (cause 6). mode above
  3, bit_order above 1, or clock_hz 0 is rejected malformed. A mode not in modes of describe, bit_order 1 without bit0 of features,
  and a clock_hz lower than min_clock_hz or above max_clock_hz are rejected unsupported (payload `0x00`), and the state does not change. For clock_hz, the probe chooses the nearest
  SCK frequency it can produce at or below the value and returns it in clock_hz of the answer. configure returns success after reaching state 1. If initialization fails,
  it returns to state 0 and answers completed failed (no fixed part, [TLV]).
- **Transfer**: gap_ns(u32), setup_ns(u32), hold_ns(u32), count(u16), tx(count bytes).
  - gap_ns: from CS becoming inactive in the previous transfer to CS becoming active in this transfer. Not used in the first transfer of the sequence.
  - setup_ns: from CS becoming active to the first SCK edge.
  - hold_ns: from the last SCK edge to CS becoming inactive.
  - count 0 activates CS and returns it to inactive without putting out SCK (CS is kept active for setup_ns and hold_ns together).
  - The bytes of tx are put out on MOSI in bit_order, and the same number of bytes are received from MISO into rx (bit placement of §4). There can be gaps longer than an SCK
    period between bytes.
- **Times**: the probe uses the nearest time it can produce at or above the requested value, and returns the values actually used in gap_ns, setup_ns and hold_ns of the answer (ns;
  gap_ns of the first transfer of the sequence is 0). A returned value means that a time at least that long was kept on the line. A value above max_delay_ns is rejected unsupported.
  A requested time is never shortened by failing to keep it.
- Checks of the request (all refuse with nothing done): state 0 is rejected unavailable (cause 6). n 0, or transfer lengths that do not match the request, are rejected malformed.
  A total of counts above max_length, or a sequence that does not fit in max_op_ms of the core, is rejected unsupported.
- The answer lists n entries in the order of the transfers. transfer answers completed success. transfers grows by the number of finished transfers (saturates at 0xFFFFFFFF and
  returns to 0 on configure or plan release).
- status: state 0 unset, 1 running. mode and bit_order are the values of configure (0 in state 0).
- describe: ops, role_channels, max_length (the upper limit of the total count of one transfer), max_clock_hz (the verified upper limit of SCK), features (bit0 LSB first),
  time_step_ns (tag 0x40, u32. Required: the time step. Returned values are not necessarily multiples of it), modes (tag 0x41, u8. Required. The same as §4),
  max_delay_ns (tag 0x42, u32. Required: the maximum gap_ns, setup_ns and hold_ns accept), min_clock_hz (the lower limit of SCK configure accepts. 1 if absent).
- max_length is a value with which the request (header 10 + n 1 + transfer 14 + tx) and the answer (header 5 + n 1 + transfer 14 + rx) of the largest transfer with a single transfer entry fit in the
  max_frame of every transport.

A probe that cannot keep clock_hz or the times in simultaneous use with other fns refuses a later configure and so on, as with cs_setup_ns of §4, with unavailable (cause 2)
before side effects, following core §8.1.

## 7. `oep.fixture.pwm`

The probe puts out a square wave on output k. The frequency and the duty (the fraction of one period that is high) are specified, and the probe returns the values it actually puts out.

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x10 | set | n(u8), n × (role(u8), hz(u32), duty(u16)), [TLV] | n(u8), n × (role(u8), num(u32), den(u32), duty(u16)), [TLV] | needed |
| 0x11 | status | — | n(u8), n × (role(u8), num(u32), den(u32), duty(u16)), [TLV] | not needed |

- role is the number of the output (from 0, less than channels of describe). The plan holds each role at most once, on separate channels. Roles need not be assigned
  consecutively from 0.
- **set** is done in the order of the sequence. hz is the frequency (Hz). duty is the fraction of one period that is high: 0 is always low, 65535 always high, and in between
  duty / 65535. hz 0 stops the output and drives that line low (duty is not looked at). The probe puts out the nearest frequency and duty, and returns them in
  num / den (Hz, a fraction) and duty of the answer. A stopped output is num 0, den 1, duty 0.
- Checks of the request (all refuse with nothing done): n 0 or a length that does not match is rejected malformed. A role of channels or more, the same role twice,
  or a non-zero hz lower than min_clock_hz or above max_clock_hz is rejected unsupported (payload `0x00`). A role not in the plan is rejected
  unavailable (cause 6).
- A channel taken by plan keeps its previous state until the first set (the same as gpio in fixture §1). Release of the plan stops the output and returns the channel to
  the idle state of core §8. A plan is a resource of the session, so it also stops at the end of the session (end, lease expiry, force, core §9).
- status returns the current output for each role in the plan (a role not set yet is num 0, den 1, duty 0).
- describe: role_channels (per role), max_clock_hz (the upper limit of frequencies it can put out), min_clock_hz (the lower limit, 1 if absent), channels (tag 0x40, u8: the number of outputs),
  duty_bits (tag 0x41, u8: the number of bits of duty resolution at max_clock_hz. It MAY become finer at lower frequencies).

## 8. `oep.fixture.counter`

The probe counts the edges of input k within a set time (gate). The frequency is found by dividing count by the time.

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x10 | measure | gate_us(u32), edge(u8), [TLV] | window_ns(u64), n(u8), n × (role(u8), count(u32)), [TLV] | needed |

- role is the number of the input (from 0, less than channels of describe). The plan holds each role at most once. **counter only listens, so
  it MAY share pins with other functions (including outputs)** (the same as logic in capture §1.2). Taking the plan does not change the electrical state of the pin.
- **measure** starts counting on all roles in the plan at the same time, counts for gate_us, and answers. edge is 0 rising, 1 falling, 2 both.
  window_ns is the time actually counted (probe clock, ns), and count is the number of edges in that time (stopped at 0xFFFFFFFF). The answer is in role order.
- Checks of the request (all refuse with nothing done): gate_us 0 or edge above 2 is rejected malformed. gate_us above max_gate_us is rejected
  unsupported (payload `0x00`). No plan is rejected unavailable (cause 6).
- Edges faster than max_clock_hz MAY be missed (missed ones are not in count).
- describe: role_channels, max_clock_hz (the upper limit of input frequency counted without misses), channels (tag 0x40, u8), max_gate_us (tag 0x41, u32: a value that fits in
  max_op_ms of the core).

## 9. `oep.fixture.dac`

The probe puts out an analog value on output k. The relation between value and voltage is shown by the range of describe (nominal).

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x10 | set | n(u8), n × (role(u8), value(u32)), [TLV] | — | needed |
| 0x11 | status | — | n(u8), n × (role(u8), value(u32), on(u8)), [TLV] | not needed |

- role is the number of the output (from 0, less than channels of describe). The plan holds each role at most once, on separate channels. An analog output
  switches the pad to the analog function, so **it does not share pins used by plans of other fns, wire connections or settings** (plan_apply is refused with rejected unavailable).
- **set** is done in the order of the sequence and sets that output to value (0 to 2^bits − 1). The nominal voltage is min_mv + (max_mv − min_mv) × value / (2^bits − 1).
  Checks of the request: n 0 or a length that does not match is rejected malformed. A role of channels or more, or value above 2^bits − 1, is rejected unsupported
  (payload `0x00`). A role not in the plan is rejected unavailable (cause 6).
- A channel taken by plan puts out nothing until the first set (it stays in the idle state). Release of the plan stops the output and returns the channel to the idle state of core §8.
- status returns, for each role in the plan, the value last set and whether it is putting out (on 1).
- describe: role_channels, channels (tag 0x40, u8), bits (tag 0x41, u8: resolution), range (tag 0x42, min_mv(i32), max_mv(i32): the nominal voltages of value 0 and
  2^bits − 1).

## 10. Referenced specifications

The OEP messages of this document are determined by this text alone. What is used to drive the buses:

| Interface | Specification | Part used |
|---|---|---|
| `oep.fixture.i2c-target` | I2C-bus specification and user manual (NXP UM10204) | addressing (7 bit addresses), ACK, clock stretching, the reserved addresses 0x00 to 0x07 and 0x78 to 0x7F |
| `oep.fixture.spi-target` | none: SPI has no formal standard | mode, CS and bit order are defined by §4 |
| `oep.fixture.i2c-controller` | I2C-bus specification and user manual (NXP UM10204) | START, repeated START, STOP, 7 bit address and R/W, ACK / NACK, clock stretching, arbitration |
| `oep.fixture.spi-controller` | none: SPI has no formal standard | mode, CS and bit order are defined by §4, times by §6 |
| `oep.fixture.pwm`, `oep.fixture.counter`, `oep.fixture.dac` | none | defined by §7 to §9 |
| `oep.fixture.uart` | none | the line as the format of configure says (start bit, data bits LSB first, parity, stop bits) (§2) |
