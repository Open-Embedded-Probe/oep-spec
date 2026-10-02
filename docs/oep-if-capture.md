# OEP standard interfaces: capture v1

[日本語](oep-if-capture.ja.md)

Status: **normative** (2026-09-26. On 2026-09-30 the decisions before the freeze were put in: the name `oep.fixture.logic`, and the analog numbers were fixed. Reflects the [zero-base re-examination](v1-zero-base-proposal.ja.md) (Japanese) of 2026-10-01). The core is [OEP core](oep-core.md).
The only definition of the numbers is `registry/oep-v1.toml`. The design as a logic analyser, the line between basic and extension, and the measurements behind them are in
[capture (design and measurements)](logic-capture.ja.md) (Japanese).

| Name | revision | Role |
|---|---:|---|
| `oep.fixture.logic` | 1 | Logic (1 track) |
| `oep.fixture.analog` | 1 | Analog (1 track) |
| `oep.fixture.capture-group` | 1 | Starts several tracks together (mixed signal, §4) |

logic and analog have **the same operation numbers and forms**; they differ only in the contents of configure (§3.3), the layout of the data (§1), and the
calibration that only analog has (§3.8). Simultaneous start of several tracks and time alignment do not widen these 2, but are a separate interface that bundles tracks
(capture-group, §4). External clock, multi-stage triggers, etc. are separate definitions ([design](logic-capture.ja.md) (Japanese) §0.1).

**Time**: the time of every track is expressed with the probe's single clock (ns since boot, u64, does not wrap). Even across different interfaces it is the same
clock, so the host can line tracks up by subtracting times. Times are returned as **an estimate and an uncertainty**. The probe returns values with the corrections it knows
(the driver discarding the first conversion frame, etc.) already applied, and promises no more precision than that. The final alignment (the offset between tracks and the time
scale factor) is the job of the host's analysis (capture the same signal on 2 tracks, capture a marker pulse on all tracks, etc.).
Since the clock counts from boot, times can be compared only within the same boot. The host judges whether it is the same clock by whether the boot_id
(core §6.5) of the answers to confirm / open is the same.

**Generation**: a track advances its generation (u32, from 1) at each start. The serial of segments and the position count from 0 within a generation,
so the host attaches the generation to read and release, and the probe refuses if it differs (an old read does not silently return new data). The generation is seen in the answer to start,
status, the segment information, and the TLV of streaming data.

Capture does not use the form of positioned streams ([common parts](oep-if-common.md) §1) (it has no from and no marks, and has segments and generations).
The meaning of the modes (one-shot, repeat, streaming) is in [design](logic-capture.ja.md) (Japanese) §2.4, and how the rate is decided is in §2.10 of the same.

## 1. Form of the data

Terms: a **stream** is the sequence of bytes the probe returns for one capture (one segment). It starts at byte position 0.
**Bit j of the stream** is defined as bit `j mod 8` (bit 0 = LSB) of byte `floor(j / 8)`.

### 1.1 Logic

Values the probe returns in the answer to configure:

| Value | Range | Meaning |
|---|---|---|
| `w` | One of 1, 2, 4, 8, 16, 32, 64, 128 | The number of bits of one sample. The probe chooses (it may be larger than the number of channels) |
| `C` | 1 or more | The number of channels (the number of logic roles assigned by the plan) |
| `pos[k]` (k = 0 … C−1) | 0 ≤ pos[k] < w, all different | The bit position within the sample of channel k (in ascending order of role number) |
| `N` | 1 or more | The number of samples of the segment |

Rules:

1. Sample i (i = 0 … N−1) is from bit `i·w` to `i·w + w − 1` of the stream.
2. The value of channel k of sample i is bit `i·w + pos[k]` of the stream.
3. The value of a bit that falls on no `pos[k]` is **undefined**. The host ignores it without reading it (the probe does not have to make it 0).
4. The length of the segment is `ceil(N·w / 8)` bytes. The bits of the last byte beyond `N·w` are undefined.
5. When w ≥ 8, a sample is the same as a little endian integer of `w/8` bytes (the same for w = 64 / 128: bit b of byte k is bit
   `8k + b`). When w < 8, `8/w` samples go into 1 byte, and the lower-numbered sample comes in the lower bits.

Examples:

| Configuration | w | pos | Contents of 1 byte |
|---|---|---|---|
| A probe that packs 1 bit at a time, 1 line | 1 | [0] | Samples 0 to 7 are bits 0 to 7 |
| A probe that can capture only in units of 1 byte, 1 line | 8 | [0] | 1 byte is 1 sample. Bits 1 to 7 are undefined |
| A probe that captures 1 byte of a GPIO port as is, the pin is bit 5 | 8 | [5] | Only bit 5 has meaning |
| A probe that packs in units of 4 bits, **3 lines** | 4 | [0, 1, 2] | Bits 0 to 2 = ch0 to 2 of sample 2m, bit 3 undefined, bits 4 to 6 = ch0 to 2 of sample 2m+1, bit 7 undefined |
| A probe with 1 sample per byte, **3 lines** | 8 | [0, 1, 2] | 1 sample per byte, bits 3 to 7 undefined |
| A probe that packs in units of 16 bits, 9 lines | 16 | [0 … 8] | 1 sample in 2 bytes (little endian), bits 9 to 15 undefined |

A way of capturing that does not fit these rules (a peripheral that left-aligns samples into a 32-bit word) is repacked by the probe, or uses the format of a separate definition
(which chip falls into which is in [design](logic-capture.ja.md) (Japanese) §3.0).

### 1.2 Analog

Values the probe returns in the answer to configure:

| Value | Range | Meaning |
|---|---|---|
| `s` | One of 8, 16, 32 | The number of bits of the slot that holds one value |
| `o`, `b` | 0 ≤ o, 1 ≤ b ≤ 31, o + b ≤ s | The position of the value within the slot (b bits from bit o, unsigned. Since b ≤ 31, the value can be expressed by zero(i32) and the value(u32) of trigger) |
| `C` | 1 or more | The number of channels |
| `order[m]` (m = 0 … C−1) | A permutation of the channel numbers | Which channel the m-th slot within the sample is |
| `N` | 1 or more | The number of samples of the segment |

Rules:

1. A slot is a little endian integer of `s/8` bytes. Bits `o` to `o+b−1` of the slot's value are the result of the conversion (unsigned). The other
   bits are undefined (the host ignores them).
2. Sample i is from slot `i·C` to `i·C + C − 1`. The m-th slot is channel `order[m]`.
3. The length of the segment is `N·C·s/8` bytes.
4. Voltage of channel k = (value − `zero[k]`) × `scale_nv[k]`. `zero` and `scale_nv` (nV / 1 value) are returned per channel in the answer to configure (linear. Curve calibration is
   a separate definition). **This voltage is the voltage at the probe's input pin** (a value converted including the attenuation of the front stage. The attenuation_mdb of the frontend of describe is for
   display, and the host does not apply it again).
5. The time of channel k lags the time of the sample by `skew_ns[k]` (for an ADC that switches channels in turn).

Examples:

| Configuration | s | o | b | Notes |
|---|---|---|---|---|
| A 12-bit ADC that sends the 4-byte records of DMA as is | 32 | 0 | 12 | The channel number etc. in bits 13 to 16 are ignored as undefined. The condition is that the order of the channels follows the pattern (if it breaks, the probe reorders them or removes that rate from the declaration) |
| A 12-bit ADC that sends 2-byte records as is | 16 | 0 | 12 | The upper 4 bits (channel number) are undefined |
| A 12-bit ADC that sends the 16 bits of the FIFO as is | 16 | 0 | 12 | |
| An ADC reduced to 8 bits | 8 | 0 | 8 | |

Which chip falls into which is in [design](logic-capture.ja.md) (Japanese) §3.0.

**Sharing pins** (core §8.1): a logic capture only listens, so it may share pins with other functions. An analog input,
depending on the chip, switches the pad to the analog function and cuts off the digital input and output of that pin.
- Whether an analog channel can share a pin used by another fn's plan (including a logic capture), a wire connection, or the settings is decided by the
  probe. **A combination that cannot be shared is refused at plan_apply (and at the attach of a wire, the set of the settings) with rejected unavailable**. It is refused whichever
  comes later. It must not silently break the reading and writing of other functions.
- A probe that allows sharing allows it only when the digital input of that pin (and the output of other functions) does not change while the analog is running.




## 2. Segments

One capture is a **sequence of bytes with positions** of one track (a stream, §1), divided into segments.

| Mode | Segments |
|---|---|
| One-shot | 1 (serial 0). Disappears at the next start (the generation advances) |
| Repeat | Continue without gaps. Readable until the host releases them. When no free segment remains, acquisition stops (state 5), and when release frees one, it resumes automatically. flags bit0 is set on the first segment after resuming |
| Streaming | Divisions at the probe's convenience (one DMA transfer, etc.). The probe sends the data (§3.4) |

```text
segment : serial(u32), position(u64), samples(u32), start_ns(u64), start_uncertainty_ns(u32), trigger_index(u32), flags(u8), generation(u32)   37 byte
```

| Field | Meaning |
|---|---|
| serial | The serial number of the segment from start (from 0) |
| position | The byte position of the start of the segment (continuous from start, u64, does not wrap. The same space as the position of read and notifications) |
| generation | The generation of this segment (increases by 1 at each start) |
| samples | The number of samples of the segment (a segment that ended partway by stop is short) |
| start_ns | The estimate of the time of the first sample of the segment (the probe's clock: ns since boot, u64, does not wrap). A value with the corrections the probe knows already applied |
| start_uncertainty_ns | The uncertainty of start_ns (±ns). A guide to the range the probe can estimate, not a guarantee |
| trigger_index | The number of the sample within the segment where the trigger fired. 0xFFFFFFFF for a segment that does not contain the trigger |
| flags | bit0 there was a gap from the previous segment (no free segment in repeat, pushed out in streaming), bit1 short (ended by stop), bit2 within the segment the time of samples drifted beyond the timing (jitter_ns) of configure (there are samples delayed by software pacing) |

- Within a segment, continuity is promised. In repeat and streaming, unless flags bit0 is set, a segment continues right after the previous segment.
- flags bit2 is set when the probe can detect the delay itself (with software pacing, when there was a sample taken more than 1 sample period after its scheduled
  time). The time axis of a segment with it set is not uniform. The host does not measure time with that segment, or doubts the measured value.
- The segment information is accumulated in a small ring separate from the body (the limit is declared).

## 3. Operations

### 3.1 Roles (plan)

- Role k = channel k (logic 0 to 127, analog 0 to 63). The order of channels is ascending order of role number. The values of the number of channels (C, the
  max of channels, etc.) are u8 because roles are u8 (intentional).
- A pin without an ADC channel is refused in an analog plan.
- Pins for an external clock, and for trigger input and output, are not in the basic set (separate definitions).

### 3.2 Operations

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x01 | configure | TLVs of the settings (§3.3) | TLVs of the actual values (§3.3) | Required |
| 0x02 | start | — | blocking_ms(u32) (0 = answers even while capturing), generation(u32), [TLV] | Required |
| 0x03 | stop | — | — | Required |
| 0x04 | force | — | — (if waiting for the trigger, start right now) | Required |
| 0x05 | status | — | state(u8), serial_done(u32), write_pos(u64), flags(u8), generation(u32), [TLV error] | Not required |
| 0x06 | read | generation(u32), position(u64), max(u32) | position(u64), flags(u8: bit0 more, bit1 gap), len(u32), data, [TLV] | Not required |
| 0x07 | segments | from_serial(u32) | more(u8), count(u8), count × (len(u8), segment information (§2)), [TLV] | Not required |
| 0x08 | release | generation(u32), serial(u32) | — (segments up to serial may be reused) | Required |
| 0x09 | query | TLVs of the settings (the same as configure) | TLVs of the actual values (sets nothing) | Not required |
| 0x0A | calibration | — | TLVs of the calibration information (§3.8). Analog only (logic: unknown_operation) | Not required |

- state: 0 not configured, 1 configured, 2 waiting for the trigger, 3 capturing, 4 complete (one-shot), 5 stopped (no free segment in repeat),
  6 error.
- `serial_done` is the number of finished segments, `write_pos` is the byte position captured so far (the position space. **Including what was discarded**: the position of the next byte to be written).
- `flags` of status: bit0 data was dropped inside the probe (the capture queue or ring overflowed), bit1 the time base was bent
  (the same as slipped of a segment). The other bits are reserved (0). **Reset to 0 at start, cumulative for that run**. In state 6, the reason is returned with the TLV 0x01 error (u8:
  1 DMA / peripheral, 2 storage, 3 clock, 0x40 onwards probe-specific) of the answer.
- **generation**: read and release put the current generation in the request. If it differs, rejected unavailable (cause 6). 0 before start.
- If the position requested by read has already been reused (or pushed out), the position of the answer moves forward and gap is set.
  If it is a position not yet captured, it returns up to where there is data (empty if there is nothing. max = 0 is also an empty success).
- release is for repeat only (in one-shot and streaming it does nothing and succeeds). It releases **up to and including** serial (inclusive). When this frees space in state 5,
  the probe resumes acquisition automatically (state 3) and sets flags bit0 on the first segment after resuming. stopped reason 2 is not sent (reserved).
- max of read is u32 (to read large amounts at once, [design](logic-capture.ja.md) (Japanese) §7.2). The amount actually returned is decided by the probe's frame and `max_read` (declared).
- more of segments means there are segments not yet returned. If from_serial is beyond serial_done, an empty success.

**State transitions** (row = the current state, column = the trigger. "—" does nothing and succeeds):

| state | configure | start | stop | force | release | Automatic |
|---:|---|---|---|---|---|---|
| 0 not configured | → 1 | unavailable 6 | — | — | — | configure / query without a plan are also unavailable 6 |
| 1 configured | → 1 | → 2 (with trigger) / 3. Generation +1, segments disappear | — | — | — | |
| 2 waiting for the trigger | unavailable 6 | unavailable 6 | → 1 (stopped 1) | → 3 | — | trigger → 3 (triggered) |
| 3 capturing | unavailable 6 | unavailable 6 | → 1 (stopped 1, short segment bit1) | — | returns free space | complete → 4 (stopped 0), no free space → 5, error → 6 (stopped 3) |
| 4 complete | → 1 | → 2 / 3 (generation +1) | — | — | — | |
| 5 stopped | unavailable 6 | unavailable 6 | → 1 | — | if space is freed → 3 (flags bit0) | |
| 6 error | → 1 | → 2 / 3 (generation +1) | → 1 | — | — | |

When the plan is released by plan_release, lease expiry, or force, it returns to state 0 and the data and segments disappear (read is empty). A start in mode 3 (streaming)
is rejected unavailable (cause 6) if there is no subscription for that fn. If the subscription disappears while capturing, it keeps capturing and discards what cannot be sent (position jumps).
A configuration where blocking_ms of the answer to configure exceeds the core's max_op_ms is rejected unsupported at configure. The lease is not
counted during blocking.

### 3.3 configure

**TLVs of the settings** (if the probe cannot handle a TLV (or value) with critical set, the whole configure is
refused with rejected unsupported (0x0B, the tag in the payload); if critical is not set, it is ignored and listed in `ignored` (0x7F) of the answer. core §2.3):

| tag | Name | Value | Applies to |
|---|---|---|---|
| 0x40 | mode | u8: 1 one-shot, 2 repeat, 3 streaming (0x40 onwards are separate definitions) | Both |
| 0x42 | rate | rate_hz(u32) (for analog, per channel. 1 Hz or more. Slower recording is within the range of host polling, and is not in v1) | Both |
| 0x43 | samples | u32 (the number of samples of 1 segment. May be omitted in streaming) | Both |
| 0x44 | segments | u32 (the number of segments of repeat. If omitted, left to the probe) | Both |
| 0x45 | trigger | type(u8), role(u8), value(u32) | Both |
| 0x46 | pretrigger | u32 (the number of samples to keep before the trigger) | Both |
| 0x47 | frontend | role(u8), frontend(u8: the number of the frontend of describe) | Analog |

- **Querying is a separate operation (0x09)**. If it were a flag in the TLVs of configure, querying without the lock would not be possible, since the probe decides whether the lock is required
  by the operation number ([design](logic-capture.ja.md) (Japanese) §7.8). A query does not break the current settings or the captured data.
- type of trigger: 0 immediate (when omitted), 1 level (value 0 / 1), 2 edge (value 0 rising / 1 falling / 2 both),
  3 crossing a threshold upward, 4 crossing it downward (value is the ADC value after extraction with o / b). 1 to 2 are for logic, 3 to 4 for analog.
  A type not in the declaration is rejected unsupported.
- A trigger is only a start condition. Even in repeat and streaming, it takes effect only at the beginning ([design](logic-capture.ja.md) (Japanese) §2.4).
- **samples is the total of the segment** (including pretrigger). If the trigger fires early and the pretrigger part is short, the segment is short and trigger_index is
  correspondingly small. When started by force, triggered is sent with trigger_index = the sample at that instant. With type 0 (immediate), triggered is not sent.
- **rate**: if within rate_range, the probe chooses the nearest realisable value (in either direction. Seen in actual_rate). Out of range is rejected
  unsupported (tag 0x42).

**TLVs of the answer**:

| tag | Name | Value | Applies to |
|---|---|---|---|
| 0x50 | actual_rate | num(u32), den(u32) (the actual rate = num / den Hz) | Both |
| 0x51 | layout | Logic: w(u8), C(u8), pos[C](u8). Analog: s(u8), o(u8), b(u8), C(u8), order[C](u8) (§1) | Both |
| 0x52 | actual_samples | u32 | Both |
| 0x53 | actual_segments | u32 | Both |
| 0x54 | timing | jitter_kind(u8: 0 none / 1 fractional division / 2 software), jitter_ns(u32) | Both |
| 0x57 | skew | role(u8), skew_ns(u32). One per channel (channels with a delay of 0 may be omitted) | Analog |
| 0x55 | scale | role(u8), zero(i32, value), scale_nv(i32, nV per 1 value. Negative is an inverting frontend). One per channel. A linear expression to the voltage at the probe's input pin (§1.2) | Analog |
| 0x56 | blocking_ms | u32 (the expected time the probe does not answer while capturing. If 0, it answers) | Both |
| 0x58 | frontend_used | role(u8), frontend(u8: the number of the frontend of describe). One per channel. The meaning of the value (measurable range, attenuation) is decided by the declaration of that frontend | Analog |
| 0x5A | rate_accuracy | how(u8: 0 nominal value calculated from the division, 1 measured value), ppm(u32: a guide to the uncertainty of actual_rate, 0 is unknown). A guide to whether the time scale factor between tracks should be aligned | Both |
| 0x59 | reference | source(u8: 0 supply, 1 internal, 2 external), mv(u32), how(u8: 0 nominal, 1 measured). The reference voltage of the ADC. With an ADC whose reference is the supply, the meaning of the same raw value changes with the supply voltage. The linear expression of scale is a conversion that assumes this voltage | Analog |
| 0x7F | ignored | A sequence of tag(u8) (the ignored common to all contexts of core §2.3) | Both |

### 3.4 Notifications (core §11)

When the holder of the lock subscribes, the following arrive from that interface. Without subscribing, the same can be learned by polling status and
segments.

| What is sent | When | Contents |
|---|---|---|
| Event kind 0x01 segment | A segment finished (also the completion of one-shot. Not sent in streaming) | The segment information (§2), [TLV] |
| Event kind 0x02 stopped | Acquisition stopped | reason(u8: 0 complete, 1 the host's stop, 2 reserved (no free segment is not sent), 3 error), error(u8: the reason for reason 3, the same values as the error of status), [TLV] |
| Event kind 0x03 triggered | The trigger fired | serial(u32), trigger_index(u32), trigger_ns(u64: the estimate of the time the trigger fired, on the probe's clock), [TLV] |
| Data (role 0x06) | Only during streaming | The form of core §11.2 (position, len, data, TLV). The same position space as read. **Always attach TLV 0x01 generation(u32)** (because leftovers of the previous generation can arrive after the answer to start) |

- Streaming presupposes subscribe (the probe sends the data. features bit2 is set). The conditions for batching (min_bytes, max_delay_ms) are
  specified in subscribe.
- In one-shot and repeat, the host reads the data with read. Notifications are for waiting for completion.

### 3.5 What is declared in describe

| tag | Name | Value |
|---|---|---|
| 0x06 | features | Common bits. bit0 query (op 0x09), bit1 force, bit2 notifications |
| 0x40 | mode | mode(u8), background(u8), max_samples(u32, 1 segment), max_segments(u32) (one per mode. Answered with the **largest** storage. describe is only a declaration, so it does not answer with the free space at that moment) |
| 0x41 | rate_range | min_hz(u32), max_hz(u32), exact(u8: 1 = any value within the range can be specified) |
| 0x42 | rate_list | n(u8), n × rate_hz(u32). Representative rates. Candidates for a list in a UI. If they do not fit in one TLV, it may be repeated (union) |
| 0x43 | rate_limit | mode(u8), channels(u8), max_hz(u32). The upper limit when the number of channels C ≤ channels (may be repeated per condition) |
| 0x44 | channels | max(u8), layout candidates (u32: if bit i is set, 2^i can be chosen. For logic w (1 to 128: bits 0 to 7), for analog s (8, 16, 32: bits 3 to 5)) |
| 0x45 | trigger | types(u32: a bit set of type), max_pretrigger(u32) |
| 0x46 | frontend | frontend(u8: number), range_min_mv(i32), range_max_mv(i32), attenuation_mdb(u32: the attenuation of the front stage, in milli-dB. 0 is no attenuation, 0xFFFFFFFF is a front stage that cannot be expressed as attenuation). One per candidate input range (analog). The number is chosen with frontend of configure. A probe with only one candidate writes only that one |
| 0x49 | frontend_shared | u8: 1 = all channels can use only the same frontend (a different designation is refused at configure) |
| 0x47 | max_read | u32 |
| 0x48 | segment_ring | u16 (the number of segment information entries remembered) |

- **The declaration is a guide; the answer to configure is authoritative** ([design](logic-capture.ja.md) (Japanese) §2.10). Combinations not shown in the declaration are checked with query.

### 3.6 What was moved to separate definitions

As in the table of [design](logic-capture.ja.md) (Japanese) §0.1. The following TLVs that the previous version of this document had in configure were removed from the basic set: track (several tracks.
Now capture-group, §4), external clock, the stages and conditions of multi-stage triggers, trigger output. The same for roles 0xC0 onwards (external clock, qualifiers, trigger input and output). When a separate definition
is written, the numbers are assigned there.

- For mode, trigger type and layout format, 0x40 onwards are each left to separate definitions.
- For TLVs of configure and describe, 0x60 to 0x7F are left to separate definitions.
- Something where the probe goes as far as decoding (a protocol analyser) does not widen this interface, but is a separate interface.

### 3.7 Usage examples

```text
One-shot (2 logic lines, 20 MHz, automatic judgement in a test)
  plan_apply(logic: role0 = GPIO20, role1 = GPIO21)
  configure(mode=1, rate=20 MHz, samples=200000)
    → actual_rate 20000000/1, layout w=2 pos=[0,1], blocking_ms 0
  subscribe(logic)                      (wait for the completion notification. If not subscribing, poll status)
  start → generation g → event segment (serial 0) → issue several read(g, 0, 65536) at once and read to the end

One-shot, start on an edge (from 1000 samples before the first falling edge of SWCLK)
  configure(mode=1, rate=20 MHz, samples=200000, trigger(edge, role1, fall), pretrigger=1000)
  start → event triggered → segment → read

Repeat (a long time without breaks, at the host's pace)
  configure(mode=2, rate=4 MHz, samples=65536, segments=8)
  subscribe → start → read for each event segment → release(g, serial)
  if release is late, acquisition stops (state 5); when release frees space it resumes automatically, and flags bit0 of the next segment is set

Streaming (1 analog channel, 44.1 kHz)
  plan_apply(analog: role0 = GPIO16)
  configure(mode=3, rate=44100, frontend(role 0, number 2))
    → actual_rate 44642/1 etc. (as in [design](logic-capture.ja.md) §7.4, it does not come out as requested), layout s=16 o=0 b=12
  subscribe(analog, min_bytes=1024, max_delay_ms=20) → start → data arrives
```

### 3.8 calibration (analog)

Returns **raw** the information the probe has for converting ADC values to voltage. The probe applies no correction (the values of read are always raw values.
The host chooses the conversion. Curve correction can trim the top and bottom of the measurable range, so it is not forced at the storage stage). Information it does not have is not returned.

| tag | Name | Value |
|---|---:|---|
| 0x01 | factory | frontend(u8), scheme_len(u8), scheme(text), raw_len(u16), raw. The calibration values written to the chip at the factory, as read. scheme is the name of the format, in reverse DNS (the namespace of the format's owner. `a-z 0-9 - .`, 1 to 64 byte). The interpretation of raw follows the definition of the scheme (examples in [design](logic-capture.ja.md) (Japanese) §3.0). One per frontend (0xFF for one that does not depend on the frontend) |
| 0x02 | vrefint | raw(u32), ns(u64), nominal_mv(u32). The raw value of the internal reference voltage (Vrefint etc.) measured with the same ADC right after the last start (including the start of capture-group), its time, and the nominal value of that reference voltage (mV. Used to back-calculate the supply voltage). Used, with an ADC whose reference is the supply, to back-calculate the actual supply voltage. A probe that cannot measure it does not return it |

- The chip's model number and revision are in chip of the core's describe (core §7.5), the firmware version likewise in firmware.
- The attenuation and measurable range per frontend are in frontend of describe (§3.5), the frontend chosen per channel is in frontend_used of the answer to
  configure, and the reference voltage is in reference (§3.3).

## 4. `oep.fixture.capture-group` (starting several tracks together)

**Starts tracks of separate interfaces together as one capture**, such as logic and analog, or analog and analog (2 ADCs).
Each track keeps its own configure as before, and reads its own data (read, segments, release, status). What the group holds is only which
tracks to bundle, which track's trigger starts it, and the start and stop of the group. Since the time of every track is on the probe's single clock ("Time" at the beginning),
the difference between the group's start (start_ns) and the start_ns of each track's segment is the offset of that track.

### 4.1 Operations

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x01 | bind | n(u8), n × fn(u16), [TLV] | — | Required |
| 0x02 | start | — | blocking_ms(u32), start_ns(u64), [TLV 0x01 generations: n × (fn(u16), generation(u32))] | Required |
| 0x03 | stop | — | — | Required |
| 0x04 | force | — | — (if waiting for the trigger, start right now) | Required |
| 0x05 | status | — | state(u8), start_ns(u64), trigger_ns(u64), trigger_fn(u16), [TLV] | Not required |

TLVs of bind:

| tag | Name | Value |
|---:|---|---|
| 0x01 | trigger_track | fn(u16). The track that holds the condition for starting the group (the trigger and pretrigger of that track's configure). If absent, immediate. **Sent critical** (if ignored, the meaning changes) |

- **bind** bundles configured tracks (fns of `oep.fixture.logic` / `oep.fixture.analog`). n = 0 unbinds (in state 3,
  rejected unavailable cause 6. n = 0 when nothing is bound does nothing and succeeds). Ways of refusing: a duplicate of the same fn is malformed, an fn not in the declaration (tracks)
  is unsupported; not configured, modes not matching, a track other than trigger_track having a trigger that is not immediate, or exceeding budget, is
  unavailable (cause 6 / 2). Which track the refusal is about is returned with the TLV fn (0x05, core §4.3. The same for the payload of unsupported) of the payload.
  It refuses without changing anything. While bound, configure, start, stop and force of each track are rejected unavailable
  (cause 4, holder_fn = the group's fn. Use the group's ops. To configure again, first unbind with n = 0). plan_release / plan_apply of the plan of a bound track
  are also rejected unavailable (cause 4). **bind is a session resource** (core §9: it remains on end, and is released on lease expiry and
  force).
- **start** checks the prerequisites of all tracks, then starts the bound tracks as simultaneously as possible, and returns the group's start time start_ns (the probe's clock) and
  the new generation of each track (generation +1, the same as the start of each track). If a track fails after starting, the group goes to state 6,
  stopped reason 3, and the other tracks are also stopped. **start_ns is the time acquisition (including the pretrigger ring) started**. The start_ns of the first
  segment of track k − the group's start_ns is the offset of that track (an estimate. It holds only with an immediate trigger. With a trigger, align with trigger_ns and each track's
  trigger_index). Before start, start_ns and trigger_ns of status are all bits 1.
- **Trigger**: when the condition of trigger_track fires, all tracks of the group start acquisition (the pretrigger of each track is kept in that track's own
  number of samples). The time it fired, trigger_ns, is returned in status and in the event triggered, and **the trigger_index of the segment containing that time, in every track,
  is set to the sample of that track nearest to that time** (the probe maps it onto each track's time axis). The host knows the position of the same instant in
  every track.
- **stop** stops all tracks. Segments are per track (short segments have flags bit1).
- state of status has the same values as a track (§3.2), and is the state of the group as a whole (complete when all tracks have completed). trigger_ns is
  0xFFFFFFFFFFFFFFFF if it has not fired, and trigger_fn is 0. When started by force, triggered is sent, and trigger_fn is 0.
- The mode is the same for all tracks (one-shot, repeat, streaming). The release of repeat and the push of streaming are per track
  as before.

### 4.2 Notifications

Subscribing to the group's fn delivers the group's events (each track's events arrive when that track is subscribed).

| What is sent | When | Contents |
|---|---|---|
| Event kind 0x03 triggered | The condition of trigger_track fired (also when started by force) | trigger_fn(u16: 0 with force), trigger_ns(u64), [TLV] |
| Event kind 0x02 stopped | All tracks stopped | reason(u8: the same as stopped of a track), error(u8), [TLV] |

The kind numbers match those of a track (§3.4) (triggered 3, stopped 2). triggered is also emitted as an event of the track (emitted on both).

### 4.3 What is declared in describe

| tag | Name | Value |
|---|---|---|
| 0x06 | features | bit1 force, bit2 notifications (bit0 is 0: there is no query) |
| 0x40 | tracks | n(u8), n × fn(u16). Tracks that can be bundled |
| 0x41 | max_tracks | u8. The number of tracks that can be put in one group |
| 0x42 | budget | max_sps(u32, the upper limit of the sum of number of channels × rate, sample/s), n(u8), n × fn(u16). The limit shared when the listed fns are bound together (may be repeated. Examples: using one ADC for 2 tracks, sharing DMA) |
| 0x43 | start_skew | fn(u16), typical_ns(u32). A guide to how much that track's start lags the group's start (the actual value is seen in the segment's start_ns, so this is for display) |

- Which groups of tracks can be bundled is declared with tracks and budget; to check, try bind (nothing changes even if refused).
- Several channels within one track (one ADC switched in turn) are, as before, the order and skew of that track (§1.2, §3.3).

### 4.4 Usage examples

```text
2 logic lines (20 MHz) and 1 analog line (48 kHz) together, on a falling edge of logic ch1 (from 1000 samples before)
  plan_apply(logic: role0 = GPIO20, role1 = GPIO21; analog: role0 = GPIO16)
  logic.configure(mode=1, rate=20 MHz, samples=200000, trigger(edge, role1, fall), pretrigger=1000)
  analog.configure(mode=1, rate=48000, samples=4800, pretrigger=48)
  group.bind(logic, analog, trigger_track=logic)
  group.start → start_ns
  event triggered(logic, trigger_ns) → segment of each track (trigger_index in both is the position of trigger_ns)
  read each track → the host lines them up with the difference of start_ns and trigger_index
```

