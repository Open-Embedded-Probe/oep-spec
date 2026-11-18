# OEP interface: capture v1

[日本語](oep-if-capture.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **normative** (v1). For the freeze state and the language and compatibility policy, see [Versions and stability](../docs/versioning.md). The core is [OEP core](../docs/oep-core.md).
The only definition of the numbers is `registry/oep-v1.toml`. The line between the basics and other definitions is §3.6.

## 0. Interfaces, time, generations

| Name | revision | Role | Target family |
|---|---:|---|---|
| `oep.fixture.logic` | 1 | logic (1 track) | used for every family |
| `oep.fixture.analog` | 1 | analog (1 track) | used for every family |
| `oep.fixture.capture-group` | 1 | starts several tracks together (mixed signal, §4) | used for every family |

logic and analog have **the same operation numbers and forms**; the only differences are the contents of configure (§3.3), the data layout (§1), and the analog-only
calibration (§3.7). Simultaneous start of several tracks and time alignment are not done by widening these 2; they are done by a separate interface that bundles tracks
(capture-group, §4). Resolution per channel and carrying data at change points are the data formats (§1.3 / §1.4), and a trigger origin across tracks is the event source (§4.4).
External clock (state acquisition) is §3.8.

**Time**: the time of every track is expressed by one clock of the probe (ns since boot, u64, does not wrap). Even across interfaces it is the same
clock, so the host can line tracks up by subtracting times. Times are returned as **an estimate and an uncertainty**. The probe returns values with the corrections it knows applied (the driver discarding the first
conversion frame, and so on), and promises no more precision than that. The final alignment (offsets between tracks and the time
scale factor) is the job of the host's analysis.
The clock and the identification of a boot follow core §2.7/§6.5/§7.6.

**Generation**: a track advances its generation (u32) by 1 for each accepted start. The first after boot is 1. 0 means only before the first start.
A start after reaching 0xFFFFFFFF is refused with unavailable (cause 2) before side effects, and generations are not reused until restart.
Generations are compared only for equality. Segment serials and positions are counted from 0 within a generation,
so the host attaches the generation to read and release, and the probe refuses if it differs (an old read does not silently return new data). The generation can be seen in the answer of start,
status, segment information, events, and the TLV of streaming data.

Capture does not use the form of the positioned stream ([Common parts](oep-if-common.md) §1) (there is no from and no marks; it has segments and generations).
The modes (one-shot, repeat, streaming) are §2.1. The probe sets the rate. The declaration is a guide; the answer of configure is authoritative (§3.5).

**Minimal configuration**: 1 track, 1 role, one supported mode, immediate trigger, no notifications are allowed.
Pin assignment adopts `oep.probe.plan` (§3.1).
There is no duty to implement all modes, query, force and capture-group.
Supported modes are declared by mode of describe, and configure/query of an undeclared mode is refused with unsupported (the tag of the received mode TLV).
The required operations and the data/generation/end rules of the adopted modes are kept. Even with one-shot only, segments returns the acquired segments. release is required only when mode 2 is provided.

## 1. Data form

Terms: a **stream** is the sequence of bytes the probe returns for the capture of 1 generation. Positions are counted continuously from 0 within the generation and do not go back per segment (§2.2).
The sample placement of §1 is expressed in bit positions within the segment, with the start of each segment as 0. The bit position in the whole stream is that value plus position × 8 of the segment.
**Bit j within a segment** is defined as bit `j mod 8` (bit 0 = LSB) of byte `floor(j / 8)` within the segment.

**Data format**: the byte sequence of segments and the stream is determined by the format number (registry `data_format`). format in the answer of configure
(§3.3) is that number, 0 if absent. 0 is the packing of §1.1 / §1.2 (all channels with the same number of bits in every sample). 1 is logic blocks (§1.3),
2 is analog blocks (§1.4), 3 is timestamped states (§3.8, external clock), and 4 is the **test sequence** (below). OEP adds numbers.

- The probe uses only the number the host asked for with format of configure, and 0 when there is no request
  (it does not silently send a format the host does not know).
  The usable numbers are declared by formats of describe (§3.5). The declaration is a guide; whether it can be used with those settings is decided by the answers of query and configure (it may not be usable depending on the rate and the number of
  channels).
- The host reads only formats it knows.
- **What does not depend on the format**: segments, position (the position in the byte sequence of that format), read, notifications, and the meaning of generations. samples, trigger_index and pretrigger of a segment are
  counted in **original samples**. Original samples are the samples at the track's rate (before reduction), and the trigger
  decision is also made on them. Every block can be restored on its own (without the previous block).
- **Test sequence (format 4)**: a format for measuring the actual speed of the transport. It does not read pins; the byte at stream position k (continuous in the generation) is `k & 0xFF`, and it puts out the amount format 0 would put out
  for the rate and number of channels of those settings, at exactly that speed (in streaming it passes through notifications as they are). The host
  measures loss and corruption from the sequence of values, and speed from the amount that arrived. The number of samples and the segment rules are the same as format 0. The probe only streams a counter, and it is declared by formats.
- **Certainty**: per format and per way of carrying a channel, it is fixed whether it is lossless (values and times are certain) or a summary (§1.3 / §1.4 define what is certain).
- **The data rate** can be computed from the answer of configure before start (the formulas of §1.1 / §1.3 / §1.4). For formats 0, 1, 2 and 4 it is fixed regardless of the signal.
  The answer for streaming also returns it as data_rate (§3.3).

### 1.1 Logic

Values the probe returns in the answer of configure:

| Value | Range | Meaning |
|---|---|---|
| `w` | integer 1 to 128 | number of bits of one sample. The probe chooses it (it MAY be larger than the number of channels) |
| `C` | 1 or more | number of channels (the number of logic roles assigned by plan) |
| `pos[k]` (k = 0 … C−1) | 0 ≤ pos[k] < w, all different | the bit position within a sample of channel k (in ascending order of role number) |
| `N` | 1 or more | number of samples of the segment |

Rules:

1. Sample i (i = 0 … N−1) is bits `i·w` to `i·w + w − 1` within the segment.
2. The value of channel k of sample i is bit `i·w + pos[k]` within the segment.
3. The value of a bit that matches no `pos[k]` is **undefined**. The host ignores it without reading (the probe need not set it to 0).
4. The length of a segment is `ceil(N·w / 8)` bytes. Bits of the last byte beyond `N·w` are undefined.
5. When w is a multiple of 8, a sample is the same as a little endian integer of `w/8` bytes (a result of the bit definition of §1, not a separate rule).
   When w is not a multiple of 8, a sample can cross byte boundaries. The arrangement is determined by the bit definition alone.

Examples:

| Configuration | w | pos | Contents |
|---|---|---|---|
| a probe that packs 1 bit at a time, 1 line | 1 | [0] | samples 0 to 7 are bits 0 to 7 |
| a probe that packs 3 bits at a time, **3 lines** | 3 | [0, 1, 2] | sample i is bits 3i to 3i+2 within the segment. 8 samples are 3 bytes. Sample 2 is bits 6 to 7 of byte 0 and bit 0 of byte 1 |
| a probe that can take only whole bytes, 1 line | 8 | [0] | 1 byte is 1 sample. Bits 1 to 7 are undefined |
| a probe that takes 1 byte of a GPIO port as it is, the pin is bit 5 | 8 | [5] | only bit 5 has meaning |
| a probe that packs 4 bits at a time, **3 lines** | 4 | [0, 1, 2] | bits 0 to 2 = ch0 to 2 of sample 2m, bit 3 undefined, bits 4 to 6 = ch0 to 2 of sample 2m+1, bit 7 undefined |
| a probe with 1 byte per sample, **3 lines** | 8 | [0, 1, 2] | 1 byte per sample, bits 3 to 7 undefined |
| a probe that packs 16 bits at a time, 9 lines | 16 | [0 … 8] | 2 bytes per sample (little endian), bits 9 to 15 undefined |

### 1.2 Analog

Values the probe returns in the answer of configure:

| Value | Range | Meaning |
|---|---|---|
| `s` | one of 8, 16, 32 | number of bits of the slot that holds one value |
| `o`, `b` | 0 ≤ o, 1 ≤ b ≤ 31, o + b ≤ s | the position of the value in the slot (b bits from bit o, unsigned. b ≤ 31, so values can be expressed with zero(i32) and value(u32) of trigger) |
| `C` | 1 or more | number of analog roles assigned by plan |
| `order[m]` (m = 0 … C−1) | a permutation containing each role number assigned by plan once | which role (channel) the m-th slot in a sample is |
| `N` | 1 or more | number of samples of the segment |

Rules:

1. A slot is a little endian integer of `s/8` bytes. Bits `o` to `o+b−1` of the slot value are the conversion result (unsigned). Other
   bits are undefined (the host ignores them). A converter whose result is signed (b bit two's complement) is sent as offset binary: the probe inverts bit b−1 of each value (adds 2^(b−1) and takes the remainder modulo 2^b), and the zero it returns includes that (the value of 0 V).
2. Sample i is slots `i·C` to `i·C + C − 1`. The m-th slot is channel `order[m]`.
   Analog channel numbers use the role numbers of plan as they are, not renumbered to 0 … C−1. For example, with role 1 and 3,
   C = 2 and order is [1,3] or [3,1]. scale, skew, frontend_used and role of trigger use the same numbers.
3. The length of a segment is `N·C·s/8` bytes.
4. The voltage of channel k = (value − `zero[k]`) × `scale_nv[k]`. `zero` and `scale_nv` (nV / 1 value) are returned per channel in the answer of configure (linear. Curve calibration is
   a separate definition). **This voltage is the voltage at the probe's input pin**. It is converted including the attenuation of the front stage, and the host does not apply the attenuation again.
5. The time of channel k is `skew_ns[k]` later than the time of the sample (for an ADC that switches in turn).
6. Value 0 (the converter's minimum code) and 2^b − 1 (maximum code) mean that the input was at that end of the range the frontend converts, or outside it.
   The actual voltage of the input is unknown. The host shows such a value not as a voltage but as a clip: at or below the low end, or at or above the high end.
   The ends are the voltages from applying rule 4 to the values 0 and 2^b − 1 (if `scale_nv` is negative, value 0 is the high end). The probe sends these values as they are, like any other value.

Examples:

| Configuration | s | o | b | Notes |
|---|---|---|---|---|
| a 12 bit ADC that sends DMA records of 4 bytes as they are | 32 | 0 | 12 | channel numbers in bits 13 to 16 and so on are ignored as undefined. The condition is that the order of channels follows the pattern (if it breaks, the probe reorders or removes that rate from the declaration) |
| a 12 bit ADC that sends 2-byte records as they are | 16 | 0 | 12 | the upper 4 bits (channel number) are undefined |
| a 12 bit ADC that sends the 16 bits of a FIFO as they are | 16 | 0 | 12 | |
| an ADC reduced to 8 bits | 8 | 0 | 8 | |

### 1.3 Logic blocks (format 1)

With configure, the host chooses per channel (role) a **carriage** (`carriage`, the registry enum `logic_carriage`) and an **interval D** (a number of original samples)
(carriage of §3.3; a role not chosen is raw, D = 1). raw carries all samples; the other carriages group the original samples into **intervals** of D each
and carry one value of a fixed number of bits per interval (**reduction**). For every carriage, the number of bits per interval is fixed regardless of the signal.

| Value | Carriage | D | Bits b | Value of interval k (interval k is the original samples `[k·D, min((k+1)·D, r_end))` of the segment, r_end is the end of the segment) |
|---:|---|---|---:|---|
| 0 | raw | 1 | — | all samples (the raw part below) |
| 1 | sample | 2 or more | 1 | the value of original sample k·D (the 1 sample at the start of the interval; not a value that summarizes the interval) |
| 2 | any_high | 2 or more | 1 | 1 if there is even one sample of 1 in the interval, otherwise 0 (OR of the interval) |
| 3 | any_low | 2 or more | 1 | 0 if there is even one sample of 0 in the interval, otherwise 1 (AND of the interval) |
| 4 | change_latch | 2 or more | 2 | bit 0: the value of the last sample of the interval. bit 1: 1 if the interval has a sample whose value differs from the previous sample, otherwise 0 |

- 5 and above are reserved. OEP adds them (for example the number of changes in an interval). Added carriages also have a fixed number of bits per interval.
- **"The previous sample" of change_latch**: the first sample of an interval is compared with the original sample before it (the last of the previous interval). Original sample 0 of a segment
  is compared with the last original sample of the previous segment when the segment continues from the previous one without a gap (flags bit0 is 0; §2.2); otherwise (the first segment of the generation,
  a segment after a gap) it is compared with nothing (there is no change there). The level to compare with is carried at the start (start) of the reduced part of each block (below).
- **Relation of the change_latch bits**: if bit 0 of the previous interval (for the first interval of a block, the start of that block) and bit 0 of this interval differ, bit 1 is
  always 1 (an odd number of changes within the interval). If they are the same and bit 1 is 1, the number of changes within the interval is an even number of 2 or more. If they are the same and bit 1 is 0, there is no change.
  Data that does not match this is broken.
- **Block**: the data of a segment is a sequence of blocks. A block represents L original samples (the last block of a segment represents r = samples mod L, when r ≥ 1).
  L is returned in block of the answer of configure; it is **a multiple of 8 and a multiple of every D**, and at most block_max if the host sends block_max (§3.3). The block
  grid starts at original sample 0 of the segment, per segment. The interval grid is the same (interval k starts at original sample k·D). One block puts the following 2
  parts in this order:

| Part | Length | Contents |
|---|---|---|
| raw part | ceil(r · w / 8) bytes | the raw channels in the layout of the answer (w, C, pos), with the original samples of the block placed as in rules 1 to 3 of §1.1 (the first original sample of the block is sample 0 of §1.1). The rest up to the next byte boundary is filled with 0. 0 bytes if there are no raw channels |
| reduced part | ceil(R / 8) bytes | first, **start**: 1 bit per change_latch channel (in role order), the level to compare the first original sample of the block with (the value of the original sample before it; for the first block of a segment that compares with nothing, the value of original sample 0). Then the reduced channels in ascending order of role number, each channel's interval values of this block in interval order, packed as bits with no gaps between channels (by the bit definition of §1, from bit 0 of the first byte of the part; a value with b = 2 puts bit 0 first). After R bits in total, filled with 0 up to the next byte boundary. 0 bytes if there are no reduced channels |

- The number of intervals of channel c in a block is `ceil(r / D_c)` (L / D_c in a full block). A value is put out even when the last interval of a segment has fewer than D samples,
  and any_high, any_low and change_latch are decided only from the samples in that interval. `R = S + Σ_c ceil(r / D_c) · b_c` (S is the number of change_latch
  channels, and the sum is over the reduced channels). The j-th value of channel c is b_c bits from bit `S + off_c + j · b_c` of the reduced part (off_c is the sum of `ceil(r / D) · b` of the reduced channels before c
  in role order). Every block can be read without the previous block.
- The layout of the answer for format 1 is only for the raw channels: C = the number of raw channels, pos is 0 … C−1 in ascending role order, and w is chosen by the probe (C or more, §1.1).
  If all are reduced, w = C = 0 (an exception to the range of w in §1.1; the host can read without branching).
- **The bandwidth is fixed**: every full block is `B = ceil(L · w / 8) + ceil((S + Σ_c (L / D_c) · b_c) / 8)` bytes. The data rate is
  `actual_rate · B / L` byte/s, independent of the signal.
- **Certainty**: raw is lossless. sample is certain for the 1 sample at the start of the interval, and the other samples in the interval are unknown (a pulse shorter than D
  disappears from the record, and that it disappeared is also unknown). any_high and any_low are certain about whether that level existed in the interval (its position and length within the interval are unknown;
  an opposite level shorter than D disappears). change_latch is certain about the last level of the interval, whether there was a change, and the parity of the number of changes (the positions within the interval and the intermediate
  levels are unknown).
- **Delay**: the probe MAY send per block, so the delay of streaming is at most L / rate per block. The host can set the upper limit with block_max.

### 1.4 Analog blocks (format 2)

With configure, the host chooses per channel (role) a **carriage** (`carriage`) and an interval D (a role not chosen is packed). The carriage is a bit set: packed (alone),
or one or both of minmax and sum.

**Block**: the data of a segment is a sequence of blocks. A block represents L original samples (r at the end of a segment). L is returned in block of the answer of configure;
it is a multiple of 8, a multiple of every D, and at most block_max. One block puts the part of each channel in the order of order of the layout, and fills the end of each part with 0 up to the next
byte boundary. The intervals are `[k·D, min((k+1)·D, r))` (the last partial interval of a segment is also put out; the number of points is known from r):

| Carriage | Contents of the channel's part (packed as bits, the bit definition of §1) | Certainty |
|---|---|---|
| packed | r values (b bits each of the layout, no slots) | lossless |
| minmax | per interval min, max (b bits each) | summary: the minimum and maximum of the interval are certain. Time only to within the interval |
| sum | per interval the sum of the original values (b + ceil(log2 D) bits) | summary: the sum of the interval (the host divides by the number of points for an unbiased mean) |
| minmax and sum | per interval min, max, sum in that order | both |

- The values are the values of rule 1 of §1.2 (including offset binary), and rules 4 to 6 are the same.
- **The bandwidth** is fixed: the sum of the bytes of each channel's part (example: minmax and sum with 12 bit and D = 256 is 44 bits per interval, about 1/70 of the original values).

**Pin sharing** (core §8.1): logic capture only listens, so it MAY share pins with other functions. An analog input,
on some chips, switches the pad to the analog function and cuts the digital input/output of that pin.
- The plan of logic also accepts channels with an output idle, and observes them without changing the driving.
- Whether an analog channel can share pins used by plans of other fns (including logic capture), wire connections or settings is decided by the
  probe. **A combination that cannot share is refused with rejected unavailable on plan_apply (and on attach of a wire, set of settings)**. Whichever comes
  later is refused. It MUST NOT silently break the reads and writes of other functions.
- **Taking the plan does not change the electrical state of the pin** (core §8). Logic capture never changes it: it only listens. It does not stop outputs,
  and does not change the pull or direction of pins driven by other functions or by an idle output. An analog channel leaves the idle state at start (the pad leaves the digital function).
- When analog acquisition stops, the pad returns to the idle state (stop, completion, waiting for a free segment in state 5, error). The reservation of the plan is kept.
  When resuming from state 5, it switches to analog again. The switching time is reflected in start_ns and gap of the segment.
- An analog plan on a channel whose idle is an output (mode 3 / 4) is rejected unavailable (cause 5).

## 2. Modes and segments

### 2.1 Modes

| Mode | Behavior |
|---|---|
| 1 one-shot | after start (and the trigger), takes samples samples and stops (state 4). The host reads at its own speed. The next start erases the data |
| 2 repeat | one-shots one after another, with no gap at segment boundaries, taken only into free segments. When no free one is left it stops (state 5), and release resumes it |
| 3 streaming | takes with no gaps like repeat, and sends the data in notifications while the lock holder subscribes |

- trigger is the condition that fixes the acquisition of a segment. If it is not immediate, acquisition to keep pretrigger MAY start after start.
  If rearm of trigger_opts (§3.3) is 0 (default), it applies only to the first segment and is not applied again to segments after the condition holds. If 1, it is re-applied per segment
  (segmented acquisition where each segment of repeat starts with a trigger). With rearm 1 in streaming, the data is not cut; triggered is sent per occurrence and
  left in the trigger record (§3.9).
- **Repeat with rearm 1**: when a segment ends, the trigger of the next segment starts being watched from the end of that segment (re-armed; with arm 1, after pretrigger
  has accumulated). While waiting between segments, state is still 3 (it accepts release), and flags bit2 of status is set. force also works on this wait.
  A segment started by a trigger has flags bit3, and also bit0 unless it comes right after the previous segment (it is not a drop: dropped of status is not set).
  If a level condition stays true, segments start one after another.
- **when 1** applies at every arming (per segment in repeat with rearm 1). With rearm 1 in streaming, after it fires, the next one fires only after the condition once becomes false
  (level does not fire on every sample).
- The probe acquires only after start, and does no acquisition ahead of start.

**Rules of streaming**:

1. When there is no room to send, the probe discards a **new** segment whole (data already stacked is sent; §2.2). The amount discarded appears in the jump of position of the next data frame and in
   flags bit0 of status. When samples not yet made into a segment are lost by overflow of the capture ring or queue, it can also be handled as a gap of §2.2.
2. After stop too, the probe keeps unsent data taken before the stop as data to send. Even if the rest is less than min_bytes, it does not wait for max_delay_ms,
   and sends it out by the rules of core §10.4 (answers first, finite retained amount for sending). On an error end too, the rest before write_pos below is handled the same way.
   A match between the end of the received positions and write_pos of status after the stop shows only that the end was reached.
   The host can judge that it received everything only when it received, or recovered with read, the needed position range of the same generation without loss.
   Loss of notifications or segments is allowed, and there is no guarantee that the last notification arrives. The stop itself is confirmed with status.
   When it stopped with an error (state 6), the data received from write_pos on is discarded (§2.2).
3. In streaming, segment events are not sent (stopped is sent).
4. Data sent in notifications may not be readable with read. When there is no readable data after the requested position either, position=write_pos, gap=1, len=0 (§3.2).

### 2.2 Segments

One capture is a **sequence of positioned bytes** (stream, §1) of one track, divided into segments.

| Mode | Segments |
|---|---|
| one-shot | 1 (serial 0). Erased by the next start (the generation advances) |
| repeat | continue with no gaps. Readable until the host releases them. When no free segment is left, acquisition stops (state 5), and resumes automatically when release makes room. The first segment after resuming has flags bit0 set |
| streaming | divisions convenient for the probe (one DMA transfer and so on). The probe sends the data (§3.4) |

```text
segment : serial(u32), position(u64), samples(u32), start_ns(u64), start_uncertainty_ns(u32), trigger_index(u32), flags(u8), generation(u32)   37 byte
```

| Field | Meaning |
|---|---|
| serial | running number of segments since start (from 0. Wraps as u32, compared by core §2.6) |
| position | byte position of the start of the segment (continuous from start, u64, does not wrap. The same space as position of read and notifications) |
| samples | number of samples of the segment (a segment ended part way by stop is short) |
| start_ns | estimate of the time of the first sample of the segment (probe clock: ns since boot, u64, does not wrap). The value with the corrections the probe knows applied |
| start_uncertainty_ns | uncertainty of start_ns (±ns). A guide to the range the probe can estimate, not a guarantee |
| trigger_index | the number of the sample in the segment where the trigger fired. 0xFFFFFFFF for a segment without the trigger |
| flags | bit0 does not continue right after the previous segment (for any reason: no free segment in repeat, pushed out in streaming, waited for the next trigger with rearm 1), bit1 short (ended by stop), bit2 the time base bent (there is a sample taken one sample period or more after its scheduled time), bit3 started by a trigger (rearm 1, §2.1) |
| generation | the generation of this segment (the non-reuse rule at the top) |

- Continuity within a segment is promised. In repeat and streaming, unless flags bit0 is set, a segment continues right after the previous segment.
- **A gap between segments and a drop within a segment** are distinguished by whether the lost samples were already in a segment:
  - **Gap** (flags bit0): when the probe can lose samples **without putting them in any segment** (when it can end the segment before the lost range and start the next segment
    from the first sample after the lost range). When there is no place (a free segment in repeat, room to send in streaming) and a whole segment is
    not taken, it is a gap. When samples not yet made into a segment are lost by overflow of the capture ring or queue, a design that can keep them outside segments
    should make it a gap (recommended: the host can offer the choice of taking to the end despite drops). A design that cannot MAY stop as a drop within a segment (error) below.
    The host accepts both.
    position and write_pos are advanced by the lost samples too (the stream position jumps), start_ns of the next segment taken is computed from the number of that sample,
    flags bit0 is set, and flags bit0 (dropped) of status is set. Acquisition continues. The segment being made MAY be closed at the last sample before the loss
    (that segment is short, and flags bit0 is not set).
    The wait of rearm 1 (§2.1) also sets bit0, but that is a scheduled interval, known by bit3, and does not set dropped of status.
  - **Drop within a segment** (error): when samples already put in a segment are lost (when, even if the segment is ended, the lost samples remain inside the segment;
    when there is only one segment as in one-shot, or when it is unknown how far the data is certain because of a DMA or peripheral failure). That segment is not data:
    it is not put in segments and no segment event is sent. The track stops with an error (state 6, stopped reason 2). error is 2 for an overflow
    (place), 1 for a DMA or peripheral failure. flags bit0 of status is also set. write_pos of status is the start of that segment (it does not count
    that segment). read does not return data from write_pos on.
- The pretrigger ring while waiting for the trigger is not a public stream. Until trigger/force chooses the retained range of the first segment,
  write_pos=0, and the ring is not returned to read/notifications. The bytes of the same public position are not replaced during the wait.
- The probe MAY return fixed, complete bytes by read/notification before a segment ends.
  Even for logic whose w is not a multiple of 8, it does not return the last byte that later samples can still change; it returns the last byte including padding only when the segment ends.
  Until a segment ends, whether that data comes out as a segment is not decided: **when the track stops with an error, the host discards the data received
  from write_pos on (bytes whose position is write_pos or more)**. The data of a segment that came out as a segment (was put in segments, or a segment event came)
  is not cancelled by a later error.
- flags bit2 is set when the probe can find the delay itself.
- Segment information is kept in a small ring separate from the data (the probe decides how many to remember).

## 3. Operations

### 3.1 Roles (plan)

- Role k = channel k (0 to 127 for logic, 0 to 63 for analog). Analog roles need not be consecutive.
  The pos array of logic is in ascending order of role number. The order of analog slots is shown by layout.order, and each value is the role number of plan itself (§1.2).
- A pin without an ADC channel is refused in an analog plan.

### 3.2 Operations

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x10 | configure | settings TLVs (§3.3) | TLVs of the actual values (§3.3) | needed | required |
| 0x11 | start | — | generation(u32), [TLV] | needed | required |
| 0x12 | stop | — | — | needed | required |
| 0x13 | force | — | — (forces the condition if waiting for the trigger) | needed | optional |
| 0x14 | status | — | state(u8), serial_done(u32), write_pos(u64), flags(u8), generation(u32), [TLV error] | not needed | required |
| 0x15 | read | generation(u32), position(u64), max(u16) | position(u64), flags(u8: bit0 more, bit1 gap), len(u16), data, [TLV] | not needed | required |
| 0x16 | segments | from_serial(u32) | more(u8), count(u8), count × segment information (§2), [TLV] | not needed | required |
| 0x17 | release | generation(u32), serial(u32) | — (segments up to serial MAY be reused) | needed | required for mode 2, optional otherwise |
| 0x18 | query | settings TLVs (the same as configure) | TLVs of the actual values (no settings are made) | not needed | optional |
| 0x19 | calibration | — | calibration information TLVs (§3.7) | not needed | optional for analog, not provided for logic |
| 0x01 | subscribe | core §10.3 | — | needed | optional (required for mode 3, pair with unsubscribe) |
| 0x02 | unsubscribe | core §10.3 | — | needed | pair with subscribe |

- state: 0 unset, 1 configured, 2 waiting for the trigger, 3 acquiring, 4 complete (one-shot), 5 stopped (no free segment in repeat),
  6 error.
- `serial_done` is the serial of the next segment to finish (the number of segments finished since start modulo 2^32), and `write_pos` is the byte position acquired up to (the position space. **It includes what was discarded**: the position of the next byte to write).
- `flags` of status: bit0 data was dropped (a segment discarded whole in streaming (rule 1 of §2.1) or a drop within a segment (§2.2)), bit1 the time base bent
  (the same as bit2 of flags of a segment), bit2 waiting for the next trigger between segments (repeat with rearm 1, §2.1; the current situation, not cumulative). Other bits are reserved (0). **Reset to 0 at start, cumulative for that run**. In state 6, the answer TLV 0x01 error (u8:
  1 DMA / peripheral, 2 place, 3 clock; the registry enum `error`) returns the reason. The probe MAY add a detailed reason with a named extension TLV (core §2.2).
- **generation**: read and, if provided, release put the current generation in the request. If it differs, unavailable (cause 6). Before start it is 0.
  The generation is validated before the per-mode no-op of release. Generations are not compared as newer/older by half range (core §2.6).
- If the requested position of read was reused/pushed out, it advances to the next readable position and sets gap.
  If there is no readable data after it either, position=write_pos, gap=1, len=0.
  If the requested position is write_pos or more, position=write_pos, gap=0, len=0. max=0 is also an empty success, and position and gap follow the same validation rules.
- release is for repeat only (in one-shot and streaming it does nothing and succeeds). Among the finished segments, it releases those at serial or before (inclusive, compared by core §2.6).
  Segments not finished yet are not released (even if serial is ahead of them, only finished segments are released). If release makes room in state 5,
  the probe resumes acquisition automatically (state 3) and sets flags bit0 on the first segment after resuming. With no free segment, stopped is not sent.
- The amount read actually returns is decided by the probe (at most max, and an amount whose answer fits in max_frame).
- segments answers with the paging by running number of [Common parts](oep-if-common.md) §1.3 (next is serial_done, and what remains is the segments whose information the probe
  remembers).

**State transitions** (row = current state, column = trigger. "—" does nothing and succeeds. The force column applies to probes with force):

| state | configure | start | stop | force | release | automatic |
|---:|---|---|---|---|---|---|
| 0 unset | → 1 | unavailable 6 | — | — | — | configure / query without a plan are also unavailable 6 |
| 1 configured | → 1 | → 2 (with trigger) / 3. generation +1, segments are erased | — | — | — | |
| 2 waiting for the trigger | unavailable 6 | unavailable 6 | → 1 (stopped 1) | → 3 | — | trigger → 3 (triggered), error → 6 (stopped 2) |
| 3 acquiring | unavailable 6 | unavailable 6 | → 1 (stopped 1, short segment bit1) | — | returns free room | completion → 4 (stopped 0), no free room → 5, error → 6 (stopped 2) |
| 4 complete | → 1 | → 2 / 3 (generation +1) | — | — | — | |
| 5 stopped | unavailable 6 | unavailable 6 | → 1 | — | if room is made → 3 (flags bit0) | |
| 6 error | → 1 | → 2 / 3 (generation +1) | → 1 | — | — | |

**Error**: a track enters state 6 only on a failure of acquisition (including a drop within a segment of §2.2), and then, for any reason, it always
sends the event stopped with reason 2 and the same error as error of status (if subscribed; §3.4).

A plan_apply that changes the set of plan assignments (role, channel) is refused with unavailable (cause 6) in state 2/3/5. In other states it invalidates the settings, data and segments and returns to state 0.
Specifying the same set again follows plan §2.1. In both cases generation does not go back, and the next start advances it.
When the plan is released by plan_release ([plan](oep-if-plan.md)) or by the end of the session (end, lease expiry, force, core §9), it returns to state 0, and the data and segments are erased (read is empty). start of mode 3 (streaming)
is rejected unavailable (cause 6) if that fn has no subscription. If the subscription disappears during acquisition, acquisition continues, and what cannot be sent is discarded (position jumps).

**Time of start**: even after acquisition starts, once the answer is made, the usual request processing and lease rules apply.
A finite acquisition that cannot process communication MAY include that processing within the start request and answer after it can accept again.
Even then, the general reception guarantee of core §4.4 is kept. With one transport and max_inflight=1, the host sends no next new request until the answer to start.
The probe MUST NOT assume that the host also keeps other transports quiet. A combination of values that cannot meet this condition is also refused as unsupported by configure/query before side effects.
For example, an immediate one-shot that does not use interrupts can answer after acquisition completes. All processing finishes within max_op_ms.
A combination of values for which a start/resumption of acceptance within that limit cannot be achieved is refused as unsupported by configure/query before side effects.
start success shows that acquisition could start. At the time of the answer it MAY already be complete or have an acquisition error; the result of the acquisition is read with status/segments.
While communication is stopped, the lease is handled the same as for a normal request being executed, with no separate exception for the waiting time or lease after the answer.
If initialization/start fails for an accepted start, state 6 and error are set, and completed failed returns the fixed form with the same generation.

### 3.3 configure

configure success erases old data/segments and returns to state 1. generation is kept, and the next start advances it. query changes nothing.

**Settings TLVs** (values that cannot be handled refuse the whole configure with rejected unsupported (the tag as received), as in core §2.3):

| tag | Name | Value | Applies to | Sent? (when omitted) |
|---|---|---|---|---|
| 0x01 | mode | u8: 1 one-shot, 2 repeat, 3 streaming | both | required |
| 0x02 | rate | rate_hz(u32) (per channel for analog. 1 Hz or more) | both | required |
| 0x03 | samples | u32 (number of samples of one segment. 1 or more) | both | required for mode 1 / 2. Not sent for mode 3 |
| 0x04 | segments | u32 (number of segments of repeat. 1 or more) | both | mode 2 only (the probe decides) |
| 0x05 | trigger | type(u8), role(u8), value(u32) | both | optional (type 0 immediate) |
| 0x06 | pretrigger | u32 (number of samples kept before the trigger) | both | only when type of trigger is not 0 (0) |
| 0x07 | frontend | role(u8), frontend(u8: the number of a frontend of describe). One per channel. Repeated (core §2.3). Two for the same role is rejected malformed | analog | optional (the probe chooses for that channel) |
| 0x08 | format | u8: the data format (§1, registry `data_format`). A number not in formats of describe is unsupported (the tag received) | both | optional (0). Other than 0 is sent as critical |
| 0x09 | carriage | role(u8), kind(u8), d(u32). The carriage and resolution of a channel (§1.3 / §1.4). The logic kind is the enum `logic_carriage` (0 raw, 1 sample, 2 any_high, 3 any_low, 4 change_latch; §1.3). The analog kind is the bit set `analog_carriage` (bit 0 packed, bit 1 minmax, bit 2 sum. packed alone; minmax and sum MAY be combined). One per role, repeated | both | only with format 1 / 2 (a role without it is raw / packed, d 1). Sent as critical |
| 0x0A | trigger_opts | arm(u8: 0 immediately, 1 after the pretrigger has accumulated), rearm(u8: 0 first segment only, 1 per segment), when(u8: for a level condition, 0 when it goes from false to true, 1 fires even if already true at arming), hysteresis(u32: in units of the cross value. 0 is none) | both | optional (arm 1, rearm 0, when 0, hysteresis 0). Sent as critical |
| 0x0B | block_max | u32: upper limit of the block length L (original samples, §1.3 / §1.4). Bounds the delay of streaming | both | optional (the probe decides) |

- **Contract** (the same for configure and query): if a required TLV is missing, rejected malformed. A TLV against "only" or "not sent" of the table (samples and segments of mode 3,
  segments of mode 1, pretrigger with type 0 or without trigger) is rejected unsupported (the tag as received) regardless of its value.
  If type of trigger is not 0 and its role is not in the plan of that fn, rejected unavailable (cause 6). role and value of type 0 are not used:
  the host sends 0 and the probe does not look at them (it does not refuse even a role not in the plan). If pretrigger exceeds max_pretrigger, or for mode 1 / 2 is samples (after rounding
  down) or more, rejected unsupported (the tag of pretrigger). Mode 3 has no samples, so pretrigger is bound only by max_pretrigger and the
  unlisted refusals below. 0 for a value the table says is "1 or more" (rate, samples, segments) is rejected malformed (a value the definition excludes, core §2.3).
  On refusal nothing changes.
- **The critical bit**: a TLV for which the "Sent?" column does not say critical is implemented by every probe it applies to, so the host sends it without the critical bit
  (the probe treats it the same even if set, core §2.3). A TLV for which the column says critical (format other than 0, carriage,
  trigger_opts) is an optional function some probes may not implement, so it is sent as critical.
- **Unlisted refusals**: the refusals this section lists are not all. The probe also refuses other values and combinations of values it cannot handle (limits of the probe itself
  that the declaration cannot express; example: a lower limit on the difference between pretrigger and samples) with rejected unsupported, as in core §2.3. The tag is the tag, as received,
  of the TLV that has that value, and for a combination, any one of those TLVs. Exceeding the capacity of samples/segments and rounding of rate follow the rules below.
  If query is provided, achievable values can be checked without setting them.
- **When two or more refusals apply** (example: mode 1 without samples, and the value of another TLV also cannot be handled), the probe answers with any one of those that apply (order 4 of core §4.3).
  This section defines no order. The host does not rely on the order of reasons.
- **Query is a separate operation (0x18)**. If it were a flag in the TLVs of configure, the probe decides whether the lock is needed by the operation number,
  so a query without the lock would not be possible. A query does not break the current settings or acquired data.
  If there is a plan, the achievable values of a request can be queried in any state 0 to 6, also for a bundled track.
  It is not refused just because of state 2/3/5 or being bundled into a capture-group. query does not change the state, the generation,
  the settings during acquisition, the data, the segments or the group bind, and does not apply the requested values. Without a plan, unavailable cause 6.
  Progress of acquisition over time continues (if time advances across the query, new samples MAY be taken).
- type of trigger (the track trigger is kept minimal): 0 immediate (when omitted), 1 level (value 0 / 1), 2 edge (value 0 rising / 1 falling / 2 both),
  3 crossing a threshold upward, 4 crossing downward (value is the ADC value after extraction by o / b. hysteresis of trigger_opts: the next crossing is counted only after going back by hysteresis or more
  to the other side), 7 linked (follows the event source of the group, §4.4; role and value are not used). 1 and 2 are for logic, 3 and 4 for analog,
  0 and 7 for both. Pulse width, patterns, multiple stages, serial values and conditions across tracks are expressed by the trigger expression of a group of 1 track (§4.4).
  A type not in the declaration is rejected unsupported.
- **Arming**: with arm 1 of trigger_opts (the default), the probe starts watching the condition after pretrigger samples have accumulated (before the trigger of a segment there is always
  the length of pretrigger). The first sample watched is sample pretrigger (with rearm, counted from the re-armed position), and edge compares with the sample before it
  (a comparison within the accumulated interval). Thus with arm 1, trigger_index of a segment started by the trigger equals pretrigger (except with force). The host
  MAY rely on that to fix the length before the trigger. **Every probe with non-immediate triggers implements arm 1** (it only does not compare until accumulated). arm 0 is optional (opts bit 0 of trigger
  of describe): it watches right from start, and if it fires early, the segment is short (trigger_index stays small).
- **The trigger is decided on original samples**: even for channels reduced in format 1 / 2 (D > 1, minmax, sum), the condition is decided on the values before reduction, and pulse widths are also
  counted in original samples.
- **carriage** (format 1 / 2): d = 0, d not 1 for logic raw, d < 2 for logic other than raw, two for the same role, or carriage in a request without format 1 / 2 is rejected malformed.
  A kind not in carriage of describe, or d out of range, is rejected unsupported (the tag received). A role not in the plan is rejected unavailable (cause 6).
  A combination of d that cannot meet the conditions of L (§1.3 / §1.4) is rejected unsupported (the tag of carriage).
- A linked trigger can be used only when bundled into a group with an event source (§4.4). A start without bundling is rejected unavailable (cause 6). pretrigger MAY
  be added (a number of original samples of that track).
- **samples is the total number of samples of the segment** (including pretrigger). If the trigger fires early and the pretrigger part is not enough, the segment is short, and trigger_index stays
  small. When started by force, triggered is sent with trigger_index = the sample at that moment. With type 0 (immediate), triggered is not sent.
- **rate**: within the declared rate_range, the nearest value that can be captured with that role/mode/settings is used (either one at equal distance).
  When the upper limit drops because of the number of roles and so on, the value is still rounded within this set, and actual_rate is returned.
  If the requested value is outside rate_range, or no value within the range can be captured in this configuration, unsupported (the tag of rate).
- **Can be captured** means that the capture circuit of the probe and the path that moves the data to memory work at that rate and number of channels (a setting that would not keep up with any host or any use
  cannot be captured). **In streaming, whether the sending path (bandwidth of USB and so on, the host's reading) or the CPU when running together with other functions keeps up
  depends on the environment and use, so the probe does not lower the rate or refuse for that reason.** If it does not keep up, that part is recorded as a gap
  (§2.2). How much margin to allow is decided by the host and the user from data_rate of the answer and their own environment.
- samples beyond what the probe can hold are rounded down to that limit, and actual_samples (0x03) of the answer
  is authoritative. The host does not assume the value it sent, and reads actual_samples and actual_segments.
- segments of mode 2 is also rounded down to the limit that can be held with the actual samples and number of roles. When omitted, the probe decides, and actual_segments is always 1 or more.
  Rounding down samples/segments alone does not refuse. If after rounding down conditions such as pretrigger cannot be met, it refuses with the tag of that condition.

**Answer TLVs**: success always returns actual_rate/layout. actual_samples is required for mode 1/2, actual_segments for mode 2, and data_rate for mode 3 (except format 3).
scale of analog is required per role of the plan; skew MAY omit roles whose delay is 0. frontend_used/reference are optional diagnostic information.
If the needed answer does not fit in the frame of the request's transport, it is refused with unsupported before the settings change (core §4.4).

| tag | Name | Value | Applies to |
|---|---|---|---|
| 0x01 | actual_rate | num(u32), den(u32) (actual rate = num / den Hz. Both 1 or more) | both |
| 0x02 | layout | logic: w(u8), C(u8), pos[C](u8). analog: s(u8), o(u8), b(u8), C(u8), order[C](u8) (§1) | both |
| 0x03 | actual_samples | u32 | both |
| 0x04 | actual_segments | u32 | both |
| 0x05 | scale | role(u8), zero(i32, value), scale_nv(i32, nV per value; negative for an inverting frontend). One per channel. A linear formula to the voltage at the probe's input pin (§1.2) | analog |
| 0x06 | skew | role(u8), skew_ns(u32). One per channel (roles whose delay is 0 MAY be omitted) | analog |
| 0x07 | frontend_used | role(u8), frontend(u8: the number of a frontend of describe). One per channel. The meaning of the value (input range) is determined by the declaration of that frontend | analog |
| 0x08 | reference | source(u8, enum `reference_source`: 0 supply, 1 internal, 2 external), mv(u32), how(u8, enum `reference_how`: 0 nominal, 1 measured). The reference voltage of the ADC. For an ADC referenced to the supply, the meaning of the same raw value changes with the supply voltage. The linear formula of scale is a conversion that assumes this voltage | analog |
| 0x09 | format | u8: the data format used (§1). Always returned when not 0. MAY be omitted for 0 | both |
| 0x0A | block | L(u32). The number of original samples of a block of format 1 / 2 (§1.3 / §1.4). Always returned for format 1 / 2 | both |
| 0x14 | stream_buffer | u32: in streaming, the maximum number of bytes that can be accumulated before sending (with these settings; below) | both |
| 0x15 | judge_latency_ns | u32: when this track judges the condition of the event source of the group (§4.4), the maximum time from the sample where the condition holds until the probe knows it as an event (ns, with these settings; below) | both |
| 0x16 | data_rate | u32: in streaming, the data rate of these settings (byte/s, rounded up; the formulas of §1). Always returned for mode 3. Not returned for a format whose amount changes with the signal (format 3) | both |

- **stream_buffer** (optional, returned only for mode 3): the amount the probe can accumulate before sending is determined by memory at the time of configure, the rate and the number of channels, so it is
  returned in the answer (not declared in describe). It is known with query before start. The host estimates the delay it can tolerate without drops as
  stream_buffer ÷ data_rate. A probe that does not return it means
  "unknown". The host does not stop reading for longer than that (it keeps several asynchronous reads outstanding, and so on).
- **judge_latency_ns** (optional; returned by a probe with the event source of §4.4, on a track that can judge that condition): the judging delay is determined by the size of the capture chunks
  and the judging period, and changes with rate and w, so it is returned in the answer, not in describe. Other tracks that take part in the event source MUST accumulate and keep the samples for this time until the event is
  known, separately from pretrigger. Before bind, the host can compute the needed amount from judge_latency_ns of the judging track
  and rate × w / 8 of the following track, and can avoid combinations where the following track cannot accumulate it (cause 2 of bind). It is distinct from the uncertainty of the event time (trigger_uncertainty_ns, §4.4): this is the time judging takes, not the precision of time.
  A probe that does not return it means "unknown" (checked at bind).

### 3.4 Notifications (core §10)

When the lock owner subscribes to the fn, the following arrive from that interface (only for fns that set subscribe and unsubscribe in ops).
Without subscribing, the same things can be learned by polling status and segments.

| What is sent | When | Contents |
|---|---|---|
| event kind 0x01 segment | a segment finished (also the completion of one-shot. Not sent in streaming) | segment information (§2), [TLV] |
| event kind 0x02 stopped | acquisition stopped | reason(u8: 0 complete, 1 stop (the host's stop; also when the group (§4) stopped it), 2 error (always this when entering state 6, §3.2)), error(u8: the reason for reason 2, the same value as error of status), generation(u32), [TLV] |
| event kind 0x03 triggered | the trigger fired | serial(u32: that segment), trigger_index(u32: within the segment), record(u32: serial of the trigger record, §3.9; 0xFFFFFFFF if there is no record), sample(u64: original samples since the start of the generation), trigger_ns(u64: estimate of the time the trigger fired, on the probe clock), uncertainty_ns(u32), generation(u32), [TLV] |
| data (role 0x04) | only during streaming | the form of core §10.2. The same byte positions as read. The required TLVs 0x01 generation(u32) and 0x02 segment_info (below) are added to every frame |

**segment_info of streaming**: `position(u64), samples(u32), start_ns(u64), start_uncertainty_ns(u32)` (24 bytes).
position is the start of the segment, and samples is the number of samples acquired at the time the frame was made (1 or more). During acquisition it grows in later frames; after the end it is the final value.
Time/uncertainty are the same as for segments in §2.2. The data of that frame is only within this one segment and does not cross a segment boundary.
It follows the rule above of not sending the unfixed last byte. Padding at the end is distinguished from samples and layout.
The host finds the bit/sample within the segment from the absolute position of data and the origin of the segment, and does not fill in samples with fragments of a lost previous frame.
Every frame has the origin and the time, so later frames can be interpreted even if the first frame/segment information is lost. A frame with a different GEN is a different acquisition.
With frame 64, subtracting the fixed header 15 + GEN TLV 7 + segment_info TLV 27, data is up to 15 bytes.
The probe can use a larger transport, and a minimal configuration that does not provide mode 3 is not required to have this information/acquisition buffer.

- **Every event carries the generation it was born in** (for segment, generation of the segment information). Events of the previous generation can arrive after the answer to start
  (core §10.4). The host treats events that differ from the current generation as belonging to the previous generation.
- Streaming assumes subscribe (the probe sends the data. An fn that declares the streaming mode sets subscribe and unsubscribe in ops).

### 3.5 What describe declares

| tag | Name | Value |
|---|---|---|
| 0x07 | ops | the ops present (core §7.4): query, force, subscribe and unsubscribe are set only when present |
| 0x05 | features | revision 1 defines no bits |
| 0x40 | mode | mode(u8), max_samples(u32, 1 segment), max_segments(u32) (one per mode. Answered with the **maximum** place. describe is only a declaration, so it does not answer with the free space at that moment) |
| 0x41 | rate_range | min_hz(u32), max_hz(u32). Both 1 or more, min ≤ max |
| 0x42 | channels | max(u8). The upper limit of the number of channels |
| 0x43 | trigger | types(u32: bit set of types), max_pretrigger(u32), opts(u8: what trigger_opts has: bit 0 arm 0, bit 1 rearm 1, bit 2 when 1, bit 3 hysteresis (analog only; not set for logic)) |
| 0x44 | frontend | frontend(u8: number), range_min_mv(i32), range_max_mv(i32). One per candidate range of the input pin (analog). The number is chosen with frontend of configure |
| 0x45 | formats | a sequence of u8: data formats usable besides 0 (§1). Only 0 if absent |
| 0x46 | carriage | kinds(u8: bit set of kinds. For logic, bit k is value k of `logic_carriage`; for analog, the bits of `analog_carriage`), min_d(u32), max_d(u32) (the range usable with D > 1. D = 1 is always usable). When format 1 / 2 is declared |

- The required declarations are ops, one or more mode, rate_range, channels, trigger, and the role_channels/channel_group used by plan.
  Analog also declares one or more frontend. features can be omitted if its value is 0.
  The trigger numbers are in the space of each of the logic/analog interfaces, and both include immediate (type 0).
- At least one mode is declared. Not all of 1/2/3 need to be declared; only the supported modes are listed.
  max_segments is the upper limit of the place for mode 2. For mode 1/3, 0 is sent, and the host does not use it.
  Combinations of values and achievable amounts in a declared mode follow the guide below and the rules of configure/query.
- **The declaration is a guide; the answer of configure is authoritative.** Combinations not shown in the declaration are checked with query.

### 3.6 Boundary of extensions

Unassigned values of mode, role, TLVs and so on follow core §2.5/§12. Additions to `oep.` definitions are made by OEP, and third parties define interfaces with their own names.
Number ranges that anticipate uses are not reserved. type of trigger is 0 to 31, which fits in the u32 bit set of the current describe;
if 32 or more is needed, it is handled by another interface, including the form of the declaration, or by a new revision.

External clock is defined by §3.8 and format 3. Signed/32 bit samples and conversions that cannot be expressed in integer nV are expressed by data formats.
A different arrangement of data is added with a data format number (§1) (only numbers the host asked for are used). Changes of the time axis or the meaning of data also follow core §2.8.

**What OEP adds without raising the revision** (all optional; whether a probe has them is known from describe):

| Addition | Declaration | The side that does not know it |
|---|---|---|
| front-stage and acquisition settings | describe TLVs | the host skips unknown describe TLVs. The probe ignores unknown configure TLVs without the mark, and refuses them with unsupported if critical (core §2.3). Settings that change behavior are sent as critical |
| data arrangements | formats of describe, registry `data_format` | the probe uses only formats the host asked for. The host does not read unknown formats |
| trigger types | bits of types of trigger of describe | the probe refuses undeclared types with unsupported |
| condition types of the trigger expression, serial protocols | bits of trigger_caps of describe of capture-group | the probe refuses undeclared types / protocols with unsupported |
| group functions | bits of features of capture-group | the host ignores unknown bits |
| information of answers, segments and events | answer TLVs | the host skips unknown TLVs |

**Upper limits of numbers, and beyond**: the rate is u32 Hz (about 4.29 GHz), one segment is u32 samples, time is ns, channels are u8, trigger types are 32 kinds,
and a message has a u16 length. Commercial USB logic analyzers and the logic of MSOs (around 1 GS/s, tens of channels, depths of several G samples) fit within this.
Instruments beyond this (GSa/s-class analog, hundreds of channels, speeds where the number of messages becomes the limit) are handled by another interface or an external binding
([concept](../docs/project-concept.md), carrying raw data over another path). The position of streaming is u64, and loss is judged by position, not seq.
Immediate start of several tracks uses capture-group (§4), and results with a different meaning, such as protocol analysis, are defined by another interface.

### 3.7 calibration (analog)

Returns, **raw**, the information the probe has for converting ADC values to voltages. The probe does not apply corrections (values of read are always raw values.
The host chooses the conversion. A curve correction may cut off the top and bottom of the measurable range, so it is not forced at the storage stage). Information it does not have is not returned. A probe with no such information at all returns no TLV (an empty success).

A success answer contains all of the information in the table below that this operation returns, as much as it has at that time. If the value of an individual TLV or the whole answer does not fit in the max_frame of the request's transport,
it is refused with rejected unsupported (fixed-part mark 0) following core §4.4. It does not truncate the factory raw or leave out information to succeed because of capacity.
This operation reads retained information and does not change ADC measurement or the acquisition state. It distinguishes the absence of information from lack of capacity, and does not return completed failed / partial.
Selective retrieval or paging of large information, if added, can be defined by a new optional op following core §12.

| tag | Name | Value |
|---|---:|---|
| 0x01 | factory | frontend(u8), scheme_len(u8), scheme(text), raw_len(u16), raw. The calibration values written into the chip at the factory, as read. scheme is the name of the form, reverse DNS (the namespace of the owner of the form; `a-z 0-9 - .`, 1 to 64 bytes). raw is interpreted by the definition of scheme. One per frontend (0xFF for what does not depend on the frontend) |
| 0x02 | vrefint | raw(u32), ns(u64), nominal_mv(u32). The raw value of the internal reference voltage (Vrefint and so on) measured with the same ADC right after the last start (including start of capture-group), its time, and the nominal value of that reference voltage (mV; used to back-calculate the supply voltage). Used to back-calculate the actual supply voltage for an ADC whose reference is the supply. A probe that cannot measure it does not return it |

- The part number and revision of the chip are chip of describe of the core (core §7.5), and the firmware version likewise firmware.
- The measurable range per frontend (voltage at the input pin) is frontend of describe (§3.5), the frontend chosen per channel is frontend_used of the configure answer,
  and the reference voltage is reference (§3.3).

### 3.8 Glitch filter, input hysteresis and external clock (optional)

All are optional, and only a probe with the describe declaration accepts them. The configure TLVs change behavior, so they are sent as
critical (a probe without them answers unsupported), and the answer returns the values used. The cost is a few bytes of configure, with no cost per sample.

| Where | tag | Name | Value | Applies to |
|---|---:|---|---|---|
| describe | 0x4D | glitch_filter | group(u8), min_ns(u32), max_ns(u32), step_ns(u32) | logic |
| configure | 0x13 | glitch_filter | group(u8), ns(u32: pulses shorter than this are ignored. 0 is none) | logic |
| answer | 0x10 | glitch_used | group(u8), ns(u32) | logic |
| describe | 0x4E | input_hysteresis | states(u8: bit 0 off, bit 1 on. The set of states that can be chosen) | logic |
| configure | 0x0C | input_hysteresis | on(u8: 0 off, 1 on) | logic |
| answer | 0x11 | hysteresis_used | on(u8) | logic |
| configure | 0x0F | clock | role(u8), edge(u8: 0 rising, 1 falling, 2 both), qualifier_role(u8: 0xFF none), qualifier_level(u8) | logic |
| describe | 0x4C | external_clock | max_hz(u32), edges(u8: bit set), qualifier(u8: 0 / 1) | logic |
| answer | 0x0F | timebase | num(u32), den(u32): the rate (Hz) of the delta ticks of format 3 (timestamped states) | logic |

- The glitch filter applies to both the acquired data and the trigger decision (the decision uses the values after the filter). group is 0 only, and the same width is used for all channels of the track
  (one group 0 in both describe and configure). A group other than 0 is rejected unsupported (the tag of glitch_filter). The probe uses the step value nearest to ns
  and returns it in glitch_used. Out of range is unsupported. A probe declares only a filter whose output keeps following the input even with slow edges or noisy edges
  (one that freezes or oscillates within the window is not declared, because data would be lost silently). For a fixed width only, min_ns = max_ns.
- Input hysteresis (input_hysteresis): whether to put threshold hysteresis (Schmitt) in the input stage of all channels of the track.
  When on, it reduces wobble near the threshold on slow edges or weakly pulled-up lines showing up as short pulses (the trigger is not misled by wobble). In exchange,
  real pulses that cross the threshold only for a moment (such as a clock cut short by slow edges) no longer show up, and edge positions shift by the threshold (more for slower
  edges). When not sent in configure, a probe with bit 0 of states turns it off (so as not to reduce what shows up). A state not in states is unsupported.
  A probe with the describe always adds hysteresis_used to the configure answer. Like the glitch filter, it applies to both the data and the trigger decision.
- External clock (clock, state acquisition): samples are taken at edge of the line of the clock role (if there is a qualifier, only when that line is at qualifier_level).
  The clock role is assigned in the plan and is not included in the sample channels. rate is "the fastest clock that can come" (for computing segments and buffers, and checking against max_hz).
  actual_rate of the answer is 0 / 1 (time is unknown). samples and trigger_index of a segment are counted in samples (edges), and start_ns is the estimate of the first edge.
  The host does not convert samples to time. If time is needed, it asks for format 3 (below). Both edges (DDR) is edge 2.
- **Format 3 (timestamped states, logic, lossless)**: per sample, delta(u32: timebase ticks from the previous sample; for the first sample of a segment,
  ticks from start) and the state (the w bits of §1.1 filled with 0 up to the next byte boundary) are put in sequence. delta 0xFFFFFFFF is the mark "advance time only by 0xFFFFFFFF ticks,
  no sample", and its state is ignored (when the clock stops for a long time; one every 34.4 s with a 125 MHz timebase). samples and
  trigger_index of a segment do not count marks. timebase is returned in the answer. The cost per sample is
  4 bytes plus the state, only when chosen. The worst-case bandwidth is max_hz × (4 + ceil(w / 8)).

### 3.9 Trigger record (with rearm 1)

With rearm 1 (§2.1, trigger_opts), the probe makes one record per occurrence and keeps it in a ring. The notification triggered can be lost (§3.4), so the host
learns of losses from jumps in the serial of records and reads them again with the op triggers.

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x1B | triggers | generation(u32), from_serial(u32) | more(u8), count(u8), count × record, [TLV] | not needed | if opts bit 1 (rearm 1) of trigger of describe is declared, triggers and trigger_records are required. Optional otherwise |

- Record: serial(u32: from 0 within the generation), sample(u64: the number of the original sample since the start of the generation), trigger_ns(u64), uncertainty_ns(u32). 24 bytes.
- The number of records held is declared by trigger_records (0x52, u16) of describe. The oldest are overwritten, and if from_serial does not remain, the answer returns from the oldest
  remaining (the host knows from the serial jump). If the generation differs, rejected unavailable (cause 6).
- The event triggered carries serial and sample (§3.4). With rearm 1 in streaming, only records are made, without cutting segments.

## 4. `oep.fixture.capture-group` (start together and event source)

An optional interface that starts separate logic/analog tracks with the same request. Starting immediately is the basic case; with an event source (§4.4, optional), all tracks take data with that event as
the origin (looking at analog with a logic event, looking at logic with a supply dip). Advanced triggers of a single track are also expressed by a group of 1 track.
Exact coincidence of time is not guaranteed; the host lines them up with start_ns/uncertainty of each segment.

### 4.1 Operations

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x1A | bind | n(u8), n × fn(u16), [TLV] | — | needed | required |
| 0x11 | start | [TLV] | start_ns(u64), generation(u32), n(u8), n × (fn(u16), generation(u32)), [TLV] | needed | required |
| 0x12 | stop | [TLV] | — | needed | required |
| 0x13 | force | [TLV] | — (if waiting for the event, treats it as having happened now; §4.4) | needed | optional (only with §4.4) |
| 0x14 | status | [TLV] | state(u8), start_ns(u64), generation(u32), [TLV] | not needed | required |
| 0x01 | subscribe | core §10.3 | — | needed | optional (pair with unsubscribe) |
| 0x02 | unsubscribe | core §10.3 | — | needed | pair with subscribe |

- bind bundles configured logic/analog fns. All tracks have the same mode, and the trigger is immediate only (a group with an event source is §4.4).
  A track put into a new group is in state 1/4/6; if it is in use for single acquisition or in another group, it is refused with cause 6/4.
  Specifying the same fn list again is a no-op that keeps the state. A change to a different list is refused with cause 6 while the group is in state 3.
  A duplicate fn is malformed, and an fn not in tracks is unsupported (fixed-part mark 0). If the state/trigger/mode does not match, unavailable cause 6;
  if there are not enough resources for simultaneous use, cause 2. The diagnostic TLV of fn is core §4.3. Refusal is made after all validation, before side effects.
- n=0 releases the bundle. For a group acquiring (state 3), unavailable cause 6. If not bundled, a no-op.
  The bundle is a resource of the session (core §9). configure/start/stop/force and changes/release of the plan of a bundled track are refused with cause 4.
  The same set of plan assignments (role, channel) is a no-op, and query/read/status/segments/release can be used by the usual rules of each track.
- bind also checks that the start success answer on the same transport (18+6×n bytes) fits in a frame; if not, unsupported (fixed-part mark 0).
- The fn of a group has `oep.probe.plan` roles only when it uses trig_in / trig_out (§4.4) (declared by role_channels of describe and assigned by plan_apply).
- start is accepted only when there is a bundle and all tracks are in state 1/4/6. Otherwise it is refused with unavailable cause 6 before side effects, keeping the generations, states and data.
  After checking everything — free generations of the group/all tracks, mode/resources/subscriptions and so on — it assigns new generations, erases the old data/segments of all tracks, and starts.
  The generation of the group follows the same non-reuse rule as at the top. The order of n and fn is the same as bind. start_ns is the estimate of the time the first track starts.
  start_ns before start is all bits 1. All processing/resumption of acceptance follows the same time rules as start in §3.2.
- If a track enters state 6 by an initialization/acquisition failure, the group is also 6, and the other tracks are stopped the same as by stop.
  Completed tracks keep their data/segments. If start itself fails to start, completed failed returns the same fixed form.
  Tracks not yet started by this start are in state 1, and tracks already started are in the state after stop of §3.2. A failed track keeps 6.
  Assigned generations, including those of tracks not started, do not go back. The next start follows the startable states above and the usual resource validation.
- stop applies to all tracks, and short segments and padding follow the rules of each track. stop without a bundle is a no-op. start without a bundle is cause 6.
- state of status: 0 without a bundle, 6 if any is 6, 4 if all are 4 after start, 2 if waiting for the event (§4.4), 3 if any is 3/5, 1 otherwise.
  The generation of the group does not go back with a bind change and advances with the next start. Track generations at a stage where the group is not started do not change either.

### 4.2 Notifications

Only stopped (kind 0x02) is sent to an adopted subscribe.
`reason(u8: 0 all tracks complete, 1 stop, 2 error), error(u8: the track error for reason 2, 0 otherwise), generation(u32), [TLV]`.
If the group is error, the error of any one of the tracks is returned. The generation of the group is not omitted, so that past notifications can be distinguished.
An immediate group/track sends no triggered (a group with an event source sends the triggered of §4.4). Notifications of each track are sent to the subscription of that fn; the group subscription does not substitute for them.

### 4.3 describe

Required are ops and tracks (tag 0x40: n(u8), n × fn(u16), n≥1). Whether an individual combination is achievable is checked with bind.
bit 0 of features (`trigger_source`) means having the event source of §4.4. Other bits are assigned by OEP later (the host ignores unknown bits).

### 4.4 Event source (optional: features bit 0)

**The event source (trigger_source) decides, by a trigger expression, one event that becomes the origin of all tracks of the group.** Advanced triggers of a single track (pulse width,
patterns, multiple stages, serial values, conditions across tracks) are also expressed by a group of 1 track.

**Form of the expression**: a sequence of stages. A stage is an OR of terms, and a term is an AND of conditions. When the last stage holds, it is the event. Sent in TLVs of bind (the host sends all of them with the critical bit set.
A probe without them refuses with rejected unsupported (the tag as received), and does not silently start as an immediate group):

| tag | Name | Value |
|---:|---|---|
| 0x01 | trigger_source | stages(u8: 1 or more), holdoff_ns(u64: time after an event during which the next event is not accepted. 0 is none. Applies per event with rearm 1), arm(u8: 0 immediately, 1 after the pretrigger of all tracks has accumulated), rearm(u8: 0 first event only, 1 per event). arm and rearm mean the same as trigger_opts of a track (§2.1, §3.3) |
| 0x02 | stage | stage(u8), count(u32: the number of times the OR of that stage holds, 1 or more), within_ns(u64: upper limit of time since entering the stage. 0 is none), on_timeout(u8: 0 return to stage 0 when the time is exceeded. 1 a "what should come does not come" stage: if the OR of the stage becomes true within the time, return to stage 0; if the time is exceeded, the stage holds) |
| 0x03 | cond | stage(u8), part(u8: 0 condition term, 1 abort term), term(u8), src(u8: 1 track, 2 external input), fn(u16: the bundled fn for src 1, 0 for src 2), role(u8: for src 1 a plan role of that fn, for src 2 the plan role trig_in of this group), type(u8), arguments (depending on type) |
| 0x04 | trigger_out | role(u8: the plan role trig_out of this group), width_ns(u32), polarity(u8: 0 low pulse, 1 high pulse). Puts out a pulse on the event |

Condition types and arguments (times are ns, independent of the rate of any track):

| type | Name | Arguments | Source | Nature |
|---:|---|---|---|---|
| 1 | level | level(u8), when(u8: 0 when it goes from false to true, 1 fires even if already true at arming) | logic, external | state (keeps the value) |
| 2 | edge | edge(u8: 0 rising, 1 falling, 2 both) | logic, external | instant |
| 3 | cross_up | value(u32: the ADC value of that role, §1.2), hysteresis(u32) | analog | instant (after crossing, the next is counted after going back below value − hysteresis) |
| 4 | cross_down | value(u32), hysteresis(u32) | analog | instant (the next is counted after going back above value + hysteresis) |
| 5 | pulse | level(u8), cond(u8: 0 longer, 1 shorter, 2 range), min_ns(u64), max_ns(u64) | logic, external | cond 0 is the instant the width reaches min_ns (also catches a stuck line). cond 1 / 2 is the instant the pulse ends |
| 6 | pattern | n(u8), mask(n bytes), value(n bytes), when(u8) (bit k is role k of that fn. role is not used) | logic | state |
| 7 | above | value(u32), hysteresis(u32), when(u8) | analog | state (is above. True until it goes back below value − hysteresis) |
| 8 | below | value(u32), hysteresis(u32), when(u8) | analog | state (is below) |
| 9 | analog_pulse | value(u32), hysteresis(u32), side(u8: 0 while below, 1 while above), cond(u8), min_ns(u64), max_ns(u64) | analog | the same as pulse (cond 0 is the instant the width is reached. Supply glitches) |
| 10 | timer | ns(u64: since entering the stage) | — | instant |
| 11 | serial | protocol(u8: 1 uart, 2 i2c, 3 spi), event(u8: 0 match, 1 I2C START, 2 STOP, 3 NACK, 4 UART framing error, 5 parity error, 6 UART break), role2(u8), role3(u8) (0xFF for unused roles), baud(u32), bits(u8), parity(u8: 0 none, 1 odd, 2 even), flags(u8: bit 0 MSB first, bit 1 CPOL, bit 2 CPHA, bit 3 CS active low, bit 4 10 bit address, bit 5 inverted (UART idle is low)), n(u8), mask(n bytes), value(n bytes) (used only for event 0) | logic | the instant of that occurrence (the last bit of the matched byte sequence, the START / STOP condition, the NACK bit, the error bit) |

- Roles of serial: for uart, role = RX. For i2c, role = SDA, role2 = SCL (the head of mask / value is the address byte `(addr << 1) | R/W`, including R/W;
  a 10 bit address is the first 2 bytes). For spi, role = data, role2 = clock,
  role3 = CS (no CS if 0xFF).
- **Evaluation**: a state condition keeps its last value, and an instant condition is true only at that instant. **At most one instant condition in one term** (the others are state conditions.
  Instants of tracks with different rates never coincide, so edge AND edge is not expressed. An expression that goes beyond this is rejected unsupported). AND is judged at each sample of the fastest of the tracks taking part in the term (for an external input,
  the judging speed of the probe). **Judging is on original samples** (§3.3, before reduction). count of a stage is the number of times the OR of that stage went from false to
  true. The handling of within_ns depends on on_timeout: with 0, if the OR of the stage becomes true within the time (count times), the stage holds, and if the time is exceeded, it returns to stage 0. With 1, the OR of the stage
  is "what should come": if it comes within the time, it returns to stage 0 (what should come came: no event), and if the time is exceeded, the stage holds (no ACK comes,
  no CS comes after an IRQ). A stage with on_timeout 1 has within_ns not 0 (rejected malformed if 0). If an abort term holds during the stage,
  it returns to stage 0 (runt: stage 0 cross_up(low) → stage 1 cross_down(low), with abort of stage 1 cross_up(high)).
- **Entering a stage**: the handling when a state condition of the stage is already true at the time of entering it follows when of the condition (no new rule is added). when 0 does not count
  until it goes from false to true after entering the stage. when 1 counts it as the first time if it is true at entry. Instant conditions (edge, cross, end of pulse,
  timer) count only instants after entering the stage. Example: in a stage with on_timeout 1, when the ACK level is already high before entering, with when 0 it is not counted as "came".
- **How stages advance**: at the sample where a stage holds, the next stage is not judged; it is judged from the next sample (one sample does not advance 2 stages). A combination at the same
  instant (B is high at the rise of A) is written as an AND in the same term.
- **Arming**: with arm 1, judging starts when the pretrigger of all tracks has accumulated. The first comparison of edge and cross compares with the last sample before arming
  (the same as the track trigger, §3.3).
- **Declaration** (describe of capture-group): 0x41 trigger_caps: max_stages(u8), max_terms(u8: terms per stage), max_conds(u8: conditions per term), cross_track(u8: 0 / 1,
  AND across tracks), types(u32: bit set of condition types), protocols(u8: bit set of serial), trigger_out_latency_ns(u32: from the event to the
  edge of trigger_out. 0xFFFFFFFF means no trigger_out). The judging delay is judge_latency_ns (§3.3) in the configure / query answer of the track. The roles trig_in and trig_out are declared by role_channels of the describe of this group and assigned by plan.
  An expression beyond the declaration is rejected unsupported (the tag of the TLV that goes beyond).
- The trigger of every **bundled track** is type 7 (linked), and pretrigger is held as a number of original samples of that track itself (§3.3). If not linked, bind is
  unavailable (cause 6, the TLV fn of the payload is that track). Triggers do not double.
- At **start**, all tracks start acquisition (including the pretrigger ring), and the group enters state 2, waiting for the event. start_ns is the time acquisition started. When the event
  happens, all tracks cut segments with their own pretrigger and samples, and the group enters state 3. **force** (only when present) treats the event as having happened now
  in a waiting group (does nothing and succeeds if not waiting). In repeat / streaming, the event of the next segment is waited for from after holdoff_ns.
- **trigger_index of each track**: the sample of that track nearest to the time of the event. The uncertainty of each segment is start_uncertainty_ns.
- **Time of the event**: trigger_ns (the estimate on the probe clock) and trigger_uncertainty_ns (the sample period of the track seen by the term of the stage that decided the event;
  for an AND across tracks, the sample period of the slowest track taking part; when exceeding the time with on_timeout 1 decided the event, the larger of the sample period of the track that judged that stage
  and the granularity of the probe's time judging. A ±ns that comes from the judging delay, separate from start_uncertainty_ns of segments) are returned in the answer TLV 0x02 trigger of status
  (fn(u16: the track that judged; 0 for an external input, timer or force), ns(u64), uncertainty_ns(u32)) and in the event triggered. Until it happens, the TLV is
  not added. Example: for analog below at 1 Msps AND logic pattern, the uncertainty is around 1 µs.
- **Event** kind 0x03 triggered: trigger_fn(u16), record(u32: the running number of events with rearm 1; 0xFFFFFFFF with rearm 0), trigger_ns(u64),
  trigger_uncertainty_ns(u32), generation(u32: the generation of the group), [TLV]. Each track also has its own triggered and trigger records (§3.9), in the samples of that
  track.
- **Cost**: the expression is sent once at bind (example: 3 stages × 2 terms × 2 conditions, 20 to 40 bytes per condition, about 250 bytes). A status TLV of 14 bytes and one event. There is no per-sample
  communication cost. The cost of judging is inside the probe: a pattern of the same track is one mask comparison,
  an AND across tracks is one comparison with the kept state, and multiple stages and serial need a state machine and a decoder (a software probe declares them only at low rates;
  for an FPGA probe they are common parts). The declaration shows whether a probe has them, so a probe without them pays nothing.
