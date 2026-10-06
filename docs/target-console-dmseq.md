# OEP console mechanism 2: dmseq

[日本語](target-console-dmseq.ja.md)

Status: out of date. Until the v1 freeze the Japanese text (.ja.md) is the working text; this English version will be regenerated from it at the freeze and becomes authoritative then.

Status: **normative** (v1, before the freeze: until the v1 freeze a rule or a number may still change). Before the freeze, revision 1 alone does not identify a form: an implementation names the specification tag it implements ([versioning](versioning.md) §6). This document defines the framing of mechanism 2 (dmseq) of `oep.target.console` ([console](oep-if-console.md) §3).
This English version is authoritative; the Japanese version is its translation.

## Purpose

dmseq gives each direction a 1-bit sequence number and a CRC-8.
With them, the host can tell a frame it reads again (a **duplicate**) from a new frame with the same contents, so that nothing is delivered twice and nothing is dropped.
The CRC is required: without it, a word another debugger or an attach leaves in DATA0 can look like a valid answer.

Name: the framing name is **dmseq** (`registry/oep-v1.toml`: `[interface.enum.mechanism]` of `oep.target.console`, `dmseq = 2`).

## Carrier and ownership

The debug module's DATA0 and DATA1 ([console](oep-if-console.md) §3). Ownership alternates strictly.

- The target writes DATA0 / DATA1 only:
  (a) at begin() ("Target frame");
  (b) to post a frame when bit 7 of DATA0 is 0;
  (c) to post its outstanding frame again: under target rule 0 (bit 7 is 1 but the word is not the one it posted), under target rule 1, at the timeout,
  while keeping a frame posted ("Timeout"), and while DATA0 reads 0 ("A word of 0 is not an answer", target rules).
- The host writes only when bit 7 is 1 (a target frame is there).
- Apart from (c) over a word with bit 7 = 1 that is not the target's own frame, neither side overwrites a word the other side wrote.

## Target frame (target → host)

    DATA0 byte0  status   bit7 T=1  bit6 TO  bit5 S  bit4 A  bit3 SYN  bits2..0 N
    DATA0 byte1..3        payload 0..2
    DATA1 byte0..3        payload 3..6
    The CRC-8 is right after the payload (byte 1+N). N = 0..6.

- A frame with N <= 2 fits in DATA0; the target does not write DATA1, and the host does not read it.
- The target writes DATA1 (when it is used) before DATA0.
- **S**: the sequence number of this frame. It is inverted when the frame is acked.
- **A**: the number (H) of the last host payload the target received.
- **SYN**: 1 in every frame from begin() until the first valid answer is received.
- **TO**: a frame on which the target gave up waiting for an answer (see "Timeout"). It applies to that frame only;
  in the next frame the target posts, it is 0 again.
- **N = 0** is an empty frame (it prompts the host to answer). An empty frame also has a number and receives an answer.
- **Byte order**: byte k of DATA0 (k = 0 to 3) is bits 8k to 8k+7 of the register (byte0 is the least significant byte). Byte k of DATA1 is bits 8k to 8k+7
  of DATA1 and carries payload byte 3+k. Example: an empty SYN frame with S = 0 and A = 1 has byte0 0x98 and CRC 0x32, so DATA0 = 0x00003298.
  A host answer with K = 0, H = 0, M = 0 is DATA0 = 0x0000F300.
- **At begin()** the target sets SYN and may write 0 to DATA0. S and A may start at any value, because the host resynchronises on SYN (host rule 3).
  (Informative) The reference targets start with S = 0, A = 1 and write DATA0 = 0.

## Host answer (host → target)

    DATA0 byte0  status   bit7 0  bit6 0  bit5 K  bit4 H  bit3 0  bits2..0 M
    DATA0 byte1..3        payload, and right after it (byte 1+M) the CRC-8. M = 0..2.

- **K**: the S of the frame being answered.
- **H**: the number of this payload. It has no meaning when M = 0.

## CRC-8

poly 0x07, init 0xFF, no reflection, no final XOR. It is computed over byte0 and the payload (1+N or 1+M bytes) and placed right after them.
Because of init 0xFF an all-zero word is always invalid, so a register that does not hold its value (it reads as 0), or a mailbox the host
has cleared to 0, is never taken for a frame or an answer. The CRC also covers the bytes in DATA1, so a DATA0/DATA1 pair read across a rewrite
by the target does not pass.

The method of computation is free (an implementation conforms if it gives the same value).
Check values: the 9 ASCII bytes "123456789" → 0xFB; the single byte 0x00 → 0xF3.

## Host state

- `synced`: the host has accepted one or more frames in this session.
- `last_s`: the S of the last accepted frame.
- `last_syn`: the last accepted frame had SYN set.
- `h`, `pending`: the number and the contents of the host payload not yet known to have arrived.

A session starts unsynchronised. **A host that resets the target starts a new session** (it discards all of the state above).
For an OEP probe, see [wire and debug](oep-if-debug.md) §4.6.

## Host rules (on reading a word with bit 7 = 1)

The order within one poll: read DATA0. If bit 7 is 1 and N >= 3, read DATA1. Check.
Write the answer only after that (once it has been answered, the target may post the next frame and overwrite DATA1).

1. If the word is **invalid**, do not answer; read it again on the next poll. Invalid means N > 6, or a CRC mismatch. Look at N before
   locating the CRC (with N = 7, byte 1+N does not exist, and an all-ones word `0xffffffff`, as an attach may leave, has exactly N = 7).
   If invalid words come 3 times in a row and the host is synced, answer with K = `last_s`, M = 0.
   (The word may be the host's own answer turned into bit 7 = 1. K = `last_s` is safe whatever the target has posted: the frame with that S
   has already been accepted, and a new frame has a different S, so it fails the K check and the target posts it again.)
   The host counts consecutive polls that read an invalid word with bit 7 = 1 (`0xffffffff` included). The count restarts at 0 when it reads a valid frame,
   after it answers under this rule, and when a session starts. A poll that reads a word with bit 7 = 0 does not change the count. The rule-1 answer is sent
   only while the host is synced. While it is not, the count stops at 3 (it does not wrap) and the host does not answer; the next valid frame syncs the host
   and restarts the count.
2. **Duplicate**: if synced and S == `last_s` and (SYN is 0, or `last_syn`), discard the payload and answer as in 5.
   (A SYN frame posted again is a duplicate, like any other frame.)
3. **Resynchronisation**: if not synced, or if SYN is 1 and the frame is not a duplicate under 2: `last_s` := not S (so that this frame counts
   as new), `h` := not A, discard `pending`, `synced` := true.
   **After 3, go straight on to 4** (it is not a separate branch). If the target restarts right after the host has accepted a SYN frame and
   happens to use the same S, that one frame is lost. One bit cannot tell them apart, so a host that resets the target starts a new session.
4. **Accept**: if S != `last_s`, deliver the payload, `last_s` := S, `last_syn` := SYN.
5. If there is a `pending` and A == `h`, it has arrived: `h` := not `h`, empty `pending`.
   If `pending` is empty, put the next bytes (up to 2) in it. Answer with K = S, H = `h`, M = len(`pending`) and the CRC.

## Target rules (on reading DATA0 while a frame is posted)

0. If **bit 7 is 1 and the word differs from the word the target posted** (for example `0xffffffff` left by an attach), the target **posts
   the same frame again at once**, without waiting for an answer. This is the same before and after the timeout. A word with bit 7 = 1 is the
   host's turn, so if it is left alone, an unsynchronised host does not answer it because it is an invalid word, the target reads it as
   "still my frame" and waits, and both sides stop.

When the target reads bit 7 = 0:

**A word of 0 is not an answer.** While DATA0 reads 0, the target keeps waiting for the answer (the wait time runs on) and posts its frame again once
every short wait. It does not treat 0 under rule 1. For any other word with bit 7 = 0:

1. If the answer is invalid (M > 2, or a CRC mismatch; look at M before locating the CRC), or K != S, post the same frame again
   (the host treats it as a duplicate).
2. Otherwise it is an ack: invert S; from then on SYN is 0. If M > 0, H differs from the last received H, and there is room, take the
   payload and set last received H := H. If there is no room, do not take it (the host sends it again).
3. If there is something to send, post the next frame. Post an empty frame **only when idle** (there is nothing to send, and the application
   has not written since the previous answer). A target that keeps writing receives input on the answers to its data frames. Putting an empty
   frame between writes costs one extra round trip. A target that never posts an empty frame receives input only when it writes (input
   rides only on answers).

## Timeout

**Wait time.** The target waits for an answer for a limited time only: the **short wait** while the host has not answered since begin() (or since
the last timeout), and the **long wait** after it has answered once. The short wait lasts **at least 20 ms** and the long wait **at least 1 s** of real time.
The target measures them in a way that still ends while interrupts are disabled. "Every short wait" (keeping a frame posted, and while DATA0 reads 0) uses
the same measure. (Informative) Counting reads of DATA0, the reference targets use F_CPU (the CPU clock in Hz) / 8000 reads per ms, assuming one read loop
takes at least 8 cycles.

**What this means for the host.** If a synced host polls at least once per second, no output is lost. A host that attaches later receives the
frame that timed out and what is written after it answers. The writes in between have been discarded.

**What happens at the timeout.** The target posts the frame it had posted again **with TO set** (S and payload unchanged, the CRC computed
again), and **keeps it posted**. Later writes are discarded without waiting, until a valid answer arrives. When a host that attaches later
answers that frame, it is delivered as usual and the target returns to normal.

**Keeps it posted** means that while waiting, the target **posts that frame again every short wait**. When DATA0 stops
being the target's own word while it waits for an answer (another word with bit 7 = 1), it posts the frame again at once without waiting for
the timeout (target rule 0). The host does not need to write anything for this.

- host (debugger): **do not reset the debug module when detaching** (do not clear DMCONTROL.dmactive). Clearing it may return DATA0 and DATA1 to 0,
  and the frame the target had posted is then lost. The target posts it again within a short wait ("A word of 0 is not an answer").
- host (debugger that halts the hart): if it used DATA0 / DATA1 with abstract commands while the hart was halted, it writes back DATA1 and
  then DATA0, as they were when the hart was halted, before letting it run. Otherwise the frame the target had posted (or the host's answer)
  is lost, and the target has to post it again under its rules. An OEP probe restores them before the answer of each op that uses them
  ([wire and debug](oep-if-debug.md) §4.2).
- host: treat a TO frame as a normal frame (rules 2 and 4 apply). It is not a reason to resynchronise.
  The host may tell the user that "output written while nobody answered was discarded".
- (Informative) A target that prints or polls its input posts a frame at least once per long wait plus a short wait. A host that has read no valid
  frame for 3 s while unsynchronised may tell the user that no dmseq console is answering. A target that neither prints nor reads posts nothing, so this
  is not proof that it has no console.
