# dmseq — a sequenced console over the debug module's data registers (draft 0.3, 2026-09-24)

Status: experiment draft, signed off by the ch32rv side after two review rounds (2026-09-24). Not in the OEP spec yet.

## Decision

- One new framing, sequence numbers **with** CRC-8. The sequence-only variant measured in
  the experiment ("framing 2" in the result tables) is not shipped: a corrupted word is
  accepted and the sequence state drifts. On WCH probes that is not a rare fault but a
  certainty: attach leaves `0xffffffff` in DATA0, and a CH32V30x flash leaves `0xe339e339`,
  whose bit 7 is clear - without a CRC the target takes it for a valid host answer.
- Name **dmseq**. OEP `target.console` framing 2 (0 = SerialSDI, 1 = SerialDMDATA's minichlink
  framing); ch32rv `monitor --source dmseq`; target library **`SerialDMSeq`**.
  ("dmlink" was dropped: one letter from `dmdata`, and "link" already means the probe.)
- CRC routine: one class, `SerialDMSeq`, with a 16-entry nibble table. Only sketches that use
  the console pay for it, and the table costs 24 bytes over bitwise while running as fast as a
  256-byte table (+208 bytes for 2-3 %). No separate table-less class: 24 bytes does not earn
  a second global object and a second choice for users. Any routine producing the same CRC
  conforms, so another can be added later without touching the wire format.

## Carrier and ownership

The debug module's DATA0/DATA1, as SerialDMDATA. Ownership alternates strictly: the target
writes DATA0 only while its bit 7 is clear (an answer, or nothing yet); the host writes only
while bit 7 is set (a target frame). Neither side overwrites the other's word. This is what
removes the need for framing 1's "let an empty frame stand for one poll" workaround.

## Target frame (target -> host)

    DATA0 byte0  status   bit7 T=1  bit6 TO  bit5 S  bit4 A  bit3 SYN  bits2..0 N
    DATA0 byte1..3        payload 0..2
    DATA1 byte0..3        payload 3..6
    CRC-8 in the byte right after the payload (byte 1+N). N = 0..6.

- N <= 2: the frame fits DATA0; DATA1 is neither written by the target nor read by the host.
  (On a WCH-LinkE every DMI access is a USB round trip, ~0.4 ms; this saves a third of a
  short frame's cost.)
- The target writes DATA1 (when used) before DATA0.
- **S**: this frame's sequence bit. It flips when the frame is acknowledged.
- **A**: the sequence bit (H) of the last host payload the target accepted.
- **SYN**: set on every frame from begin() until the first valid answer.
- **TO**: this frame is one the target stopped waiting for (see "Timeout"). It applies to
  this frame only; the next frame posted has TO clear.
- **N = 0** is an empty frame, an invitation to answer. Every frame, empty or not, has a
  sequence bit and is answered.

## Host answer (host -> target)

    DATA0 byte0  status   bit7 0  bit6 0  bit5 K  bit4 H  bit3 0  bits2..0 M
    DATA0 byte1..3        payload, then CRC-8 at byte 1+M. M = 0..2.

- **K**: the S of the frame being answered.
- **H**: the sequence bit of this payload; meaningless when M = 0.

## CRC-8

poly 0x07, init 0xFF, no reflection, no xor-out, over byte0 and the payload (1+N or 1+M
bytes), stored right after them. init 0xFF makes an all-zero word invalid, so a register
that does not hold a value (a V4 part with no debugger attached reads 0) or a host that
clears the mailbox is never taken for a frame or an answer. The CRC also covers DATA1's
bytes, so a DATA0/DATA1 pair read across a target rewrite does not pass.

## Host state

- `synced`: a frame has been accepted this session.
- `last_s`: the S of the last accepted frame.
- `last_syn`: the last accepted frame had SYN set.
- `h`, `pending`: the sequence bit and bytes of the host payload not yet known delivered.

A session starts unsynced. **A host that resets the target starts a new session** (drops
all of the above); ch32rv's `run`/`monitor` and the OEP probe's reset path do this.

## Host rules, on reading a word with bit 7 set

Order within one poll: read DATA0; if bit 7 is set and N >= 3, read DATA1; check; only then
write the answer. (Once answered, the target may post its next frame and overwrite DATA1.)

1. Invalid -> do not answer; read again next poll. Invalid is: N > 6, or the CRC wrong. Check
   N before locating the CRC - the byte at 1+N does not exist for N = 7, and N = 7 is exactly
   what the `0xffffffff` an attach leaves behind decodes to. After three invalid reads in a row, if
   synced, answer K = `last_s`, M = 0. (The word may be the host's own answer corrupted into
   bit 7 set. K = `last_s` is safe whatever the target has outstanding: a frame with that S
   was already accepted; a new frame has the other S, fails the K check and is posted again.)
2. Duplicate: synced, S == `last_s`, and (SYN clear, or `last_syn`) -> discard the payload,
   answer as in 5. (A reposted SYN frame is a duplicate like any other.)
3. Resync: not synced, or SYN set and not a duplicate by 2 -> `last_s` := not S (so this
   frame counts as new), `h` := not A, drop `pending`, `synced` := true. A target that
   restarts right after the host accepted its first SYN frame, and happens to reuse the
   same S, loses that one frame; 1 bit cannot tell the two apart, which is why a host that
   resets the target starts a new session. **Rule 3 continues into rule 4**: the frame that
   resynced is then accepted like any new frame (it is not a separate branch).
4. Accept: S != `last_s` -> deliver the payload; `last_s` := S; `last_syn` := SYN.
5. If `pending` is non-empty and A == `h`: it was delivered; `h` := not `h`, clear it.
   Take the next bytes (up to 2) into `pending` if empty. Answer K = S, H = `h`,
   M = len(`pending`), CRC.

## Target rules, on finding bit 7 clear while a frame is outstanding

1. Invalid (M > 2, CRC wrong - check M before locating the CRC), or K != S -> post the same
   frame again (the host treats it as a duplicate).
2. Otherwise the frame is acknowledged: flip S; SYN clear from now on. If M > 0,
   H != last accepted H, and there is room: take the payload, last accepted H := H.
   No room: leave it; the host resends it.
3. Post the next frame when there is something to send. Post an empty frame only when idle
   (nothing queued to send, and the sketch did not write since the last answer):
   **not while the sketch is writing**. A target that never posts an empty frame never
   receives input unless it prints - input can only arrive in an answer. A target that keeps printing receives input on the
   answers to its data frames; an empty frame between two prints costs a round trip (on a
   LinkE it halves output throughput).

## Timeout

**The waits.** The target waits a bounded time for an answer: **20 ms** until a host has
answered once since begin() (or since the last timeout), **1 s** after. The waits must end with
interrupts masked, so they count polls of the register, not a clock.

**What they mean for a host.** A synced host that polls at least once a second loses nothing.
A host that attaches later gets the frame that timed out and whatever is written after it
answers; writes in between are dropped.

**What happens on a timeout.** The target reposts the outstanding frame with **TO set** (same
S, same payload, CRC recomputed) and **leaves it posted**. Later writes are dropped without
waiting until a valid answer arrives; a host that attaches later answers that frame, it is
delivered normally, and the target resumes.

"Leaves it posted" means the target **posts that frame again every short wait (20 ms)** while
it is latched. A probe attach may rewrite DATA0; if what it leaves has bit 7 set (`0xffffffff`),
the target would read it as its own frame and wait, and an unsynced host would take it as an
invalid word and not answer - both stuck. Reposting keeps the frame readable; the host never
has to write anything to get out of this. (Found by the ch32rv side, 2026-09-24.)

- Host: a TO frame is an ordinary frame (rule 2/4 apply); it is not a reason to resync.
  The host may tell the user that output was dropped while nobody answered.
- Host: reading only non-frames (CRC wrong, or bit 7 clear) while unsynced for a long time
  means there is no dmseq console on the target; the host may report that rather than stay
  silent.

## Results so far (2026-09-24, OEP probes: X035 on P4, V003 on ESP32/SWIO, L103 on RP2350)

Clean (no faults), RUN = 1270 B, 3 rounds + 20 echo lines:

| | framing 1 (SerialDMDATA) | 2 | 3 (bitwise CRC) |
|---|---|---|---|
| X035 | 40 kB/s, first RUN lost | 46 kB/s, all OK | 25.6 kB/s, all OK |
| V003 | 7.5 kB/s, first RUN lost | 8.1 kB/s, all OK | 7.6 kB/s, all OK |
| L103 | 10.0 kB/s, one duplicated byte | 13.0 kB/s, all OK | 7.9 kB/s, all OK |

Faults injected in the probe (2 % each: answer dropped, answer corrupted, frame read corrupted):
framing 2 broke on all three (no RUN ever taken, echo 0/20, visible garbage "dmseq RUADY");
framing 3 was byte-exact on all three (RUN 3/3, echo 20/20; the probe rejected 87-199 bad
words and discarded 152-422 duplicates) at the same speed as clean.

Size (V003, whole test sketch): framing 1 text 2776, framing 2 2684, framing 3 2908
(+224 for bitwise CRC); RAM +8 bytes.

Clean runs, one at a time with nothing else on the bench (2026-09-24; the numbers above were
taken with three probes running at once):

| | framing 2 | framing 3, table CRC | framing 3, bitwise CRC |
|---|---|---|---|
| X035 | 51 kB/s | 41 kB/s | 26 kB/s |
| V003 | 8.3 kB/s | 7.9 kB/s | (7.6, concurrent) |
| L103 | 13.1 kB/s | 9.2 kB/s | (7.9, concurrent) |

All byte-exact, echo 20/20. On the X035 almost all of the CRC cost was the target computing
it bitwise; a 256-byte table takes it back to 80 % of framing 2. On the V003 the SWIO round
trip dominates and CRC costs ~5 %. On the L103 the rest of the gap is the extra DATA1 access
for 3..6-byte frames over a slow bit-banged link.

Flash for the table (V003 test sketch): framing 2 2724, table CRC 3212 (+488), bitwise CRC
about +224. The wire format is the same either way; which CRC routine a target uses is an
implementation choice (see the nibble table below and the Decision).

**Nibble table (16 entries, two lookups per byte)** - the same CRC-8, so no probe change:

| | framing 2 | CRC bitwise | CRC nibble | CRC 256-table |
|---|---|---|---|---|
| X035 speed | 51 kB/s | 26 kB/s | 40 kB/s | 41 kB/s |
| V003 speed | 8.3 kB/s | - | 7.95 kB/s | 7.9 kB/s |
| X035 sketch bytes | 2252 | 2500 | 2524 | 2732 |
| V003 sketch bytes | 2724 | 2980 | 3004 | 3212 |

The nibble version costs 24 bytes more than bitwise and runs as fast as the full table, so it
is the one implementation (Decision). A simpler check
(XOR/sum) would save perhaps a few tens of bytes but misses two errors in the same bit
position (and a sum misses swapped bytes), which a bit-slipping link produces; CRC-8 catches
every 1- and 2-bit error and every burst up to 8 bits in frames this short.

## Review round 1 (ch32rv side, 2026-09-24) and what changed

- SYN hole: resyncing on every SYN frame took a reposted SYN frame (answer lost) as new and
  delivered its payload twice. Host rule 2 now treats it as a duplicate (`last_syn`). The old
  harness could not see this: it compared only the RUN body, and SYN frames only occur at
  start-up. The harness now (a) checks every received line, banners included, against what
  must appear, and (b) sends RESTART so the target re-enters SYN while the host is attached
  and polling, where nothing may be lost or doubled.
- Test with the probe dropping the first two answers to SYN frames after every resync
  (`-DOEP_CONSOLE_FAULT_SYN=2`), X035, nibble-CRC target: new rule - RUN 3/3, echo 20/20,
  7 exact banners after RESTART, 144 lines with 0 unexpected, 4 duplicates discarded (two
  reposted SYN frames at boot, two after RESTART). Old rule (`-DOEP_CONSOLE_SYN_OLD_RULE=1`),
  same image: never got a single banner (each repost resynced, so its answer was dropped
  again). The test detects the hole.
- Names unified to `last_s`; TO is per frame and the latched frame stays posted; empty
  frames only when idle (the prototype no longer posts one right after a write); host may
  report TO and "no console"; CRC covering DATA1 and WCH attach/flash garbage written down.
- Name dmlink -> dmseq.
- WCH-LinkE (ch32rv's capture, V203, fw 2.22): one DMI access = one USB round trip, p50
  369 us. dmseq ~2.6 kB/s for short frames, ~5 kB/s for 6-byte frames, vs ~5.8 kB/s for
  SerialDMDATA's 7-byte frames. The CRC routine does not matter there.
