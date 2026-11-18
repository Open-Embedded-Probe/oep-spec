# OEP console mechanism dmseq

[日本語](target-console-dmseq.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **normative** (v1). For the freeze state and the language and compatibility policy, see [Versions and stability](../docs/versioning.md). This document specifies the framing of the mechanism `dmseq` of `oep.target.console` ([Console](oep-if-console.md) §3).

dmseq gives both directions a 1 bit sequence number and a CRC-8, and distinguishes a frame read again during synchronization from a new frame.
The target-side rules of this document (including the 20 ms/1 s waits) are requirements on target firmware that adopts dmseq.
They do not require target firmware or constant polling of all OEP probes/hosts. The limits on target restart and loss of the synchronization state are as below.

## Carrier and ownership

DATA0 and DATA1 of the debug module are used ([Console](oep-if-console.md) §3).

- The target writes a new frame when bit7 is 0, and while waiting for the answer only writes the same frame again.
  If bit7 is 1 but the word differs from its own, the target writes its frame again immediately, to avoid waiting on each other over an invalid word (target rule 0).
- begin() is the initialization of synchronization, and MAY set DATA0 to 0 regardless of the alternation above. It then puts out frames with SYN.
- The host answers only valid target frames with bit7 = 1. It reads DATA1 before writing DATA0, so that the peer does not get to overwrite a new DATA1 first.

## Target frame (target → host)

    DATA0 byte0  status   bit7 T=1  bit6 TO  bit5 S  bit4 A  bit3 SYN  bits2..0 N
    DATA0 byte1..3        payload 0..2
    DATA1 byte0..3        payload 3..6
    CRC-8 right after the payload (byte 1+N). N = 0..6.

- A frame with N <= 2 fits in DATA0; the target does not write DATA1, and the host does not read it.
- The target writes DATA1 (when used) before DATA0.
- **S**: the sequence number of this frame. It flips when acked.
- **A**: the number (H) of the host payload the target last received.
- **SYN**: 1 in all frames from begin() until the first valid answer is received.
- **TO**: a frame for which the target stopped waiting for an answer (see "Timeout"). It applies to that frame only;
  in the next frame the target puts out it returns to 0.
- **N = 0** is an empty frame (it prompts the host to answer). An empty frame also has a number and receives an answer.
- **Byte order**: byte k (k = 0 to 3) of DATA0 is bits 8k to 8k+7 of the register (byte0 is the lowest byte). Byte k of DATA1 is bits 8k to 8k+7 of DATA1
  and carries payload byte 3+k. Example: an empty SYN frame with S = 0, A = 1 has byte0 0x98 and CRC 0x32, so DATA0 = 0x00003298.
  A host answer with K = 0, H = 0, M = 0 is DATA0 = 0x0000F300.
- **At begin()** the target sets SYN and MAY write 0 to DATA0. S and A MAY start from any value. The host resynchronizes on SYN (host rule 3).

## Host answer (host → target)

    DATA0 byte0  status   bit7 0  bit6 0  bit5 K  bit4 H  bit3 0  bits2..0 M
    DATA0 byte1..3        payload, followed right after (byte 1+M) by CRC-8. M = 0..2.

- **K**: S of the frame being answered.
- **H**: the number of this payload. It has no meaning when M = 0.

## CRC-8

poly 0x07, init 0xFF, no reflection, no final XOR. It covers byte0 through the end of the payload, 1+N bytes in total (target→host) or 1+M bytes (host→target), and the CRC is placed right after the payload.

Any computation method may be used (it conforms if it gives the same value).
Check values: the 9 ASCII bytes "123456789" → 0xFB. The 1 byte 0x00 → 0xF3.

## Host state

- `synced`: one or more frames were accepted in this synchronization state.
- `last_s`: S of the last accepted frame.
- `last_syn`: the last accepted frame had SYN.
- `h`, `pending`: the number and contents of the host payload not yet known to have arrived.

The synchronization state starts unsynchronized. **A host that reset the target initializes the synchronization state** (discards all of the state above).
This is a state separate from the session_id/lock of the OEP core.
For OEP probes, see [Wires and debug](oep-if-debug.md) §4.6.

## Host rules (on reading a word with bit 7 set to 1)

Order of one poll: read DATA0 and check bit7 and N. If bit7 is 1 and 3 ≤ N ≤ 6, read DATA1 and check the CRC.
The answer is written after that (once answered, the target MAY put out the next frame and overwrite DATA1).

1. If **invalid**, do not answer, and read again at the next poll. Invalid means N > 6 or a CRC mismatch. Look at N before finding the position of the CRC
   (with N = 7, byte 1+N does not exist, and the all-ones word `0xffffffff` that attach can leave behind is exactly N = 7).
   The target puts out the frame again by rule 0.
2. **Duplicate**: if synced and S == `last_s` and (SYN is 0, or `last_syn`), discard the payload and answer as in 5.
   (A SYN frame put out again is also a duplicate, like any other.)
3. **Resynchronization**: if unsynchronized, or SYN is 1 and it is not a duplicate by 2, `last_s` := not S (so that this frame counts as new),
   `h` := not A, discard `pending`, and `synced` := true.
   **After 3, go on to 4 directly** (it is not a separate branch). If the target restarts right after the host accepted a SYN frame
   and happens to use the same S, that one frame is lost. 1 bit cannot tell them apart, so a host that reset the target initializes the synchronization state.
4. **Accept**: if S != `last_s`, pass on the payload, `last_s` := S, `last_syn` := SYN.
5. If there is `pending` and A == `h`, it has arrived: `h` := not `h`, empty `pending`.
   If `pending` is empty, put in the next up to 2 bytes to send (on an OEP probe, from the head of the send queue, [Console](oep-if-console.md) §2). Answer with K = S, H = `h`, M = len(`pending`) and the CRC.

The conditions under which an OEP probe notifies these observations as marks of the stream are defined in [Console §2](oep-if-console.md#2-stream-rules).
A frame with TO is also judged as duplicate/accepted like a normal frame, and TO is not a reason for resynchronization.

## Target rules (on reading DATA0 while putting out a frame)

0. **If bit 7 is 1 and the word differs from the one it put out** (such as `0xffffffff` left by attach), **put out the same frame again immediately**
   without waiting for an answer. The same before and after the timeout. A word with bit 7 = 1 is the host's turn, so if it is left alone, an unsynchronized host
   does not answer it as an invalid word, the target reads it as "still my frame" and waits,
   and both stop.

On reading bit 7 = 0:

**A 0 word is not an answer.** While DATA0 reads as 0, the target keeps waiting for an answer (the waiting time keeps advancing), and puts out the frame again once every short wait.
0 is not handled by rule 1. For other words with bit 7 = 0:

1. If invalid (M > 2 or a CRC mismatch; look at M before finding the position of the CRC), or K != S, put out the same frame again
   (the host treats it as a duplicate).
   bit3 and bit6 are ignored on the receiving side. However, the CRC is computed over the whole received byte0, including those bits.
2. Otherwise it is an ack: flip S; SYN is 0 from then on. If M > 0, H differs from the last H received, and there is room,
   take the payload and set the last H received := H. If there is no room, do not take it (the host sends it again).
3. If there is something to send, put out the next frame. If there is nothing to send, the target MAY put out an empty frame (input rides only on answers, so a target that puts out no empty frames
   can receive input only when it writes).

## Timeout

**Waiting time.** The target waits for an answer only for a finite time. While the host has not answered even once since begin() (or since the last timeout), it is a **short wait**;
after it has answered once, a **long wait**. A short wait lasts **at least 20 ms** of real time, and a long wait **at least 1 s**.
The target measures it in a way that finishes even while interrupts are disabled. "Once every short wait" (while keeping the frame out, and while DATA0 reads as 0) also
uses the same way of measuring.

**Poll interval.** As long as the interval of answering valid frames is shorter than the target's long wait, no output is lost through timeouts.
No lossless operation is guaranteed for a poll exactly at the 1 s boundary, a CRC mismatch, or not polling during a long debug operation. A host that attached later
receives the frame that timed out and what was written after it answered. Writes in between are discarded.

**What happens on a timeout.** The target puts out the frame it had out again **with TO set** (S and payload are the same, the CRC is computed
again), and **keeps it out**. Later writes are discarded without waiting until a valid answer comes. When a host that attached later
answers that frame, it gets through as usual, and the target goes back to normal.

**Keeping it out** means **putting out that frame again once every short wait** while waiting. When DATA0 stops being its own word while waiting for an answer
(another word with bit 7 = 1), the target puts it out again immediately without waiting for the timeout
(target rule 0). The host need not write anything for this.

- The write-back after abstract commands that use DATA0 / DATA1 is in [Wires and debug](oep-if-debug.md) §4.
