# OEP standard interfaces: fixture v1

[日本語](oep-if-fixture.ja.md)

Status: **normative** (2026-09-26. Reflects the [zero-base re-examination](v1-zero-base-proposal.ja.md) (Japanese) of 2026-10-01). The core is [OEP core](oep-core.md), the common parts are [common parts](oep-if-common.md) (§1 positioned
streams). The only definition of the numbers is `registry/oep-v1.toml`. Capture is [capture](oep-if-capture.md).

| Name | revision | Role | plan roles |
|---|---:|---|---|
| `oep.fixture.gpio` | 1 | Drives and reads pins | 1 = line |
| `oep.fixture.uart` | 1 | UART transmit and receive | 1 = RX, 2 = TX |
| `oep.fixture.i2c-target` | 1 | I2C target (the controlled side). Tests the DUT's I2C controller | 1 = SDA, 2 = SCL |
| `oep.fixture.spi-target` | 1 | SPI target. Tests the DUT's SPI controller | 1 = SCK, 2 = MOSI, 3 = MISO, 4 = CS |

All of them handle only the channels assigned by the plan (core §8).

## 1. `oep.fixture.gpio`

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x01 | set | n(u8), n × (channel(u16), mode(u8)) | — | Required |
| 0x02 | read | n(u8), n × channel(u16) | n(u8), n × level(u8: 0 / 1), [TLV] | Not required |

| mode | Meaning |
|---:|---|
| 0 | Input (floating) |
| 1 | Input, pull-up |
| 2 | Input, pull-down |
| 3 | Output low |
| 4 | Output high |
| 5 | Open-drain low (pulled) |
| 6 | Open-drain release (high by the external or the target's pull-up) |
| 7 | Input, both pull-up and pull-down (a weak intermediate voltage. A reference for the approximate voltage of a line with nothing connected) |

- The sequence is performed one at a time in the order of the request (pulling NRST and then releasing it, etc., can be sent in one request). All verification is done first, and
  set does not fail other than by refusal at verification (success).
- An unassigned channel (set, read) does nothing and is rejected unavailable (the payload is the TLVs of core §4.3: channel 0x02 and the position in the sequence,
  tag 0x40 index (u8)). A mode that cannot be handled (not in the declaration) is rejected unsupported (payload `0x00`, followed by the same channel / index TLVs).
  An undefined mode (8 or more) is rejected malformed.
- The modes that can be handled are declared with the modes of describe (tag 0x40, a u32 bit set, bit n = mode n). 0 (input) is mandatory.
- When the plan is released, the channel returns to the idle state of core §8.

## 2. `oep.fixture.uart`

One stream per fn.

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x01 | configure | baud(u32), [TLV] | baud(u32, the actual value), [TLV] | Required |
| 0x02 | read | from(u8), arg(u64), max(u16), [TLV] | start(u64), flags(u8), len(u16), data, [TLV] | Not required |
| 0x03 | marks | from_serial(u32) | more(u8), count(u8), count × (len(u8), mark), [TLV] | Not required |
| 0x04 | clear | — | — | Required |
| 0x05 | mark | value(u8) | — | Required |
| 0x06 | write | count(u16), data | accepted(u16), [TLV] | Required |
| 0x07 | status | — | configured(u8: 0 still the default, 1 the session's configure, 2 the uart item of the settings, 3 the baud of the uart item could not be realised and the default was used), baud(u32, the actual value), format(u8), [TLV] | Not required |

- ops 0x02 to 0x06 take the form of [common parts](oep-if-common.md) §1 (without the stream bytes), with the same numbers as `oep.target.console`.
- The TLV 0x01 format (u8) of configure: bit0-1 data length (0 = 8, 1 = 7), bit2-3 parity (0 none, 1 even, 2 odd), bit4 stop
  bits (0 = 1, 1 = 2). 8N1 if absent. Undefined values (2 / 3 in bit0-1, 3 in bit2-3, bit5-7) are rejected malformed. A value not in the declaration (formats)
  is rejected unsupported (tag 0x01). The host sends it critical (so that it does not silently become 8N1). baud returns the value that can be realised, and if it deviates
  more than ±5% from the request, rejected unsupported (payload `0x00`). configure on an fn without pins (neither RX nor TX in the plan) is rejected
  unavailable (cause 6).
- **status** (no lock): what is in effect (`uart_configured`) and the actual baud / format. So that a read-only host can know. The baud of a uart item
  is range-checked at set, but the actual divider is determined when the UART starts running by the plan. If at that time it deviates more than ±5%, the default (115200 8N1)
  is used and reported with configured = 3.
- **The stream is created by the plan and disappears when the plan is released.** The session's configure also disappears when the plan is released. Reception starts from the plan (before configure,
  the value of the uart item of `oep.probe.config` if there is one, otherwise 115200 8N1), and accumulates regardless of sessions. Redoing configure leaves the accumulated bytes and the position as they are
  (if a boundary is needed, the host attaches a mark). **The position and the serial of the marks do not go back within a boot even when the plan is released and created again**
  ([common parts](oep-if-common.md) §1.1). Receive errors are mark lost (detail 2 framing, 3 parity).
- **The TX line is kept at the UART idle (high) while assigned by the plan (even before configure)** (so that the peer's receiver does not pick up noise). When the plan
  is released, the drive stops and it goes to the idle state of core §8. A fixture that does not want to leave the peer's input floating after release decides, in the idle of `oep.probe.config`,
  that the pin is a pull-up input, and saves it.
- The formats that can be handled are declared with the formats of describe (tag 0x40, n(u8), n × u8. The values of the TLV 0x01 of configure). 8N1 (0) is mandatory.
- A one-directional UART (RX only, TX only) assigns only one role in the plan. A probe with fixed pin combinations also writes the RX-only combination and
  the TX-only combination separately in channel_group (since channel_group is an exact match).
- revision 1 sends no notifications (subscribe is rejected unsupported). When added later, the payload of data takes the form of core §11.2.

## 3. `oep.fixture.i2c-target`

The probe becomes an I2C target, accepts writes from the DUT's controller, and answers reads. Received frames are queued inside the probe, and the host
retrieves them with read_rx.

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x01 | configure | address(u8, 7 bit), mode(u8), [TLV] | — | Required |
| 0x02 | arm_rx | length(u16) | — | Required |
| 0x03 | read_rx | — | pending(u8), count(u16), data, [TLV ns(u64): time received, optional] | Required |
| 0x04 | preload_tx | count(u16), data | slots(u8), [TLV] | Required |
| 0x05 | status | — | state(u8), mode(u8), armed(u8), queued(u8), rx_frames(u32), tx_slots(u8), errors(u32), [TLV] | Not required |
| 0x06 | reset | — | — | Required |
| 0x07 | stretch | stretch_us(u32) | — | Required |

- mode: 1 fixed-length reception (a write of exactly the length of arm_rx is one frame), 2 length-prefixed reception (a 1-byte length write and,
  **within the same transaction**, the following write is the body of that length (no repeated start). The body is one frame. It becomes ready to receive at configure),
  3 preloaded transmission (answers the controller's reads in the order placed by preload_tx). The modes that can be handled are declared with the features of describe.
- configure recreates the target (the queued frames and counts are lost). Before the plan it is rejected unavailable (cause 6). If address exceeds 0x7F or
  mode is undefined (0, 4 or more), rejected malformed. A mode that is in the definition but not in the declaration is rejected unsupported.
- arm_rx is for mode 1 only (otherwise rejected unavailable cause 6). length is 1 to the max_length of describe (0 is malformed, above max_length is
  unsupported). If already waiting, the current wait is dropped and it waits with the new length. **A write from the controller while not armed is ACKed and discarded, and
  errors is counted** (the bus is not stalled).
- read_rx takes the oldest frame out and returns it (count 0 if none). pending is the number remaining after taking it out (capped at 255).
  If the queue overflows, new frames are discarded and errors is incremented. The depth of the queue is the queue_depth of describe.
- preload_tx is for mode 3 only. count is 1 to max_length (0 is malformed). slots is the serial number of placements (u8, wraps). Even if the number of bytes the controller
  read differs from the placed length, the next read is answered from the next placement. **When the placements are empty (and when read in mode 1 / 2),
  0xFF is emitted.** Quirks of the chip's FIFO (emitting an extra byte at the end of a read, etc.) are absorbed by the probe.
- status: state 0 not configured, 1 running. mode is the value of configure. armed is whether it is waiting to receive in mode 1 (0 / 1). queued is the number of queued
  frames (capped at 255). rx_frames is the cumulative count of received frames, tx_slots is the number of placements placed by preload_tx and not yet read (mode 3. Otherwise 0),
  errors is the cumulative count of overflows, receive errors and writes discarded while not armed (u32).
- reset returns to the state right after configure (clears the queue, the wait and the cumulative counts. Keeps mode and address). In state 0 it is rejected unavailable (cause 6).
- stretch is the time SCL is held low after the ACK of each received byte (µs, 0 = none). Only for probes that declare bit1 of features
  (otherwise unknown_operation). A length that cannot be handled is rejected unsupported.
- describe: role_channels, max_length (the maximum bytes of one frame), max_clock_hz (the verified upper limit of SCL), features (bit0 mode 3,
  bit1 stretch. modes 1 and 2 are mandatory), queue_depth (tag 0x40, u8: the number of frames that can be queued).
- No notifications are sent (subscribe is rejected unsupported).

## 4. `oep.fixture.spi-target`

The probe becomes an SPI target, answers one transfer delimited by CS with the MISO bytes placed beforehand, and queues the MOSI bytes.

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x01 | configure | mode(u8: SPI mode 0 to 3), bit_order(u8: 0 MSB first, 1 LSB first), [TLV] | — | Required |
| 0x02 | arm | length(u16), count(u16), tx(count byte), [TLV] | — | Required |
| 0x03 | read_rx | — | pending(u8), bits(u32), count(u16), data, [TLV ns(u64): time received, optional] | Required |
| 0x04 | status | — | state(u8), mode(u8), bit_order(u8), armed(u8), queued(u8), transactions(u32), errors(u32), [TLV] | Not required |
| 0x05 | reset | — | — | Required |

- configure recreates the target. Before the plan it is rejected unavailable (cause 6). mode exceeding 3, or bit_order exceeding 1, is
  rejected malformed. bit_order 1 without bit0 of features is rejected unsupported. **CS is active low** (active high comes later as a TLV).
- arm waits for the next single transfer: length is the maximum bytes to receive (1 to max_length. 0 is malformed, excess is unsupported), tx is the bytes to put out on MISO in that
  transfer (count ≤ length. The shortfall is 0). An arm while waiting is rejected unavailable (one at a time). **A transfer while not armed
  discards MOSI and counts transactions and errors.** **MISO is 0 outside tx (not armed, after tx is used up).**
- When a transfer ends with CS, the MOSI bytes and the number of bits actually received (bits) are queued. Anything beyond length is discarded (bits is the number actually received, data is
  up to length). read_rx returns the oldest (count 0 if none). pending is the remainder after taking it out (capped at 255).
- status: state 0 not configured, 1 running. armed is whether it is waiting for a transfer. queued (capped at 255), transactions (the cumulative count of finished transfers),
  errors (the cumulative count of overflows, not armed, and length excess, u32).
- reset returns to the state right after configure (clears the queue, the wait and the cumulative counts. Keeps mode and bit_order). In state 0 it is rejected unavailable (cause 6).
- describe: role_channels, max_length (the maximum bytes of one transfer), max_clock_hz (the verified upper limit of SCK), features (bit0 LSB first),
  queue_depth (tag 0x40, u8).
- No notifications are sent (subscribe is rejected unsupported).
