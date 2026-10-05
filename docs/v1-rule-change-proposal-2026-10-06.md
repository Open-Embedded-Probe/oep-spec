# OEP v1 rule-change proposal (2026-10-06)

[日本語](v1-rule-change-proposal-2026-10-06.ja.md)

Status: **proposal to the peers (not normative)**. This English version is authoritative; the Japanese version is its translation.
Readers: ch32rv (Rust host and broker), WireSkein (capture recorder), bench (HIL jigs).
Base: oep-spec 2e70f40 (required and optional ops). Source: [the third zero-base review](v1-zero-base-review-3-2026-10-02.ja.md) (Japanese): every finding still open there that changes a rule (規則), plus the part of C-21 that the required-ops change (2e70f40) did not cover, plus N-1, found while writing the guides (4bf464d, f951bd8).

The premise is the review's: people we have never met build probes and hosts from the text alone, for OSes, USB stacks, MCUs, debug wires and targets we have never seen. Each item starts with that user's case.

**How to answer.** For each item: agree, object, or agree with conditions. After agreement the order of work is spec → fake → probe → clients, as before.

**Terms in "Today".**
- *probe*: oep-probe-arduino `src/` and its examples.
- *fake*: oep-client-python `endpoint.py` (with `fake.py`, `fake_serial.py`, `fake_serve.py`).
- *Python*: the rest of oep-client-python.
- *JS*: oep-client-js `src/`.
- *WireSkein*: wireskein (it reaches probes through Python) and its web viewer.
- The Rust host was not checked (ch32rv: please say where your behaviour differs).

**Breaking** = an implementation that follows today's text or today's reference code must change its behaviour on the wire.

## Index

| id | area | sev | one line | breaking | recommendation |
|---|---|:---:|---|---|---|
| C-19 | core §6.5 | ○ | boot_id: say where the value comes from when a probe has no random source | probe (one fallback path) | adopt |
| C-20 | core §7.1 | ○ | confirm: max_inflight ≥ 1, window ≥ max_frame, and what a host does with values outside | no (hosts add a check) | adopt |
| ○2 | debug §4.3, common §1.3 | ○ | reset method 0 is ndmreset in revision 1; the reset op never drives a reset line | no | adopt |
| C-31 | core §2.6a | ○ | The clock never goes back while the boot_id is the same | probe (one platform branch) | adopt |
| C-21 (rest) | core §4.3 | ○ | Where an fn named inside the payload is checked: at the end of order 5 | probe, fake (order only) | adopt |
| C-36 | core §2.4, §4.1, §4.2 | △ | A message shorter than its header, and a role sent in the wrong direction, are discarded | hosts (short answer = broken answer) | adopt |
| C-38 | core §5.2 | △ | When the resend also gets no answer, the host treats the transport as failed and recovers | Python, JS (COBS links) | adopt |
| C-39 (rest) | core §7.2 | △ | list does not change while the boot_id is the same; first beyond the matches gives count 0 | no | adopt |
| C-40 | core §2.6 | △ | "well below half" becomes a number: a quarter of the width; resource numbers leave §2.6 | no | adopt |
| C-41 | core §7.5 | △ | The interface of a transport: the CDC communication interface; 0xFF for a UART bridge | probe (examples that send 0xFF on CDC) | adopt |
| C-47 | core §4.4, §7.5 | △ | max_op_ms has a ceiling (600000 ms), so no host waits for days | no (hosts add a check) | adopt |
| N-1 | core §4.4 | ○ | The transfer time before the first confirm answer uses min_max_frame (64) | no | adopt |
| △5 | fixture §3 | △ | i2c-target refuses the reserved addresses (unsupported) | probe, fake | adopt |
| △6 | fixture §2, §4 | △ | spi arm count > length is malformed; uart write without TX is unavailable cause 6 | fake (uart write) | adopt (console part dropped) |
| △9 | capture §1.2 | △ | A converter with a signed result is sent as offset binary | no | adopt |
| △10 | debug §3, registry | △ | rvswd / swio scan entries are kind 1 only | no | adopt |
| △12 | core §8 | △ | From boot, every channel is in its idle state before the first answer | probe (one firmware) | adopt |
| PC-9 (rest) | probe-config §3.3 | △ | storage_* are per page; the host uses the last page; consistency needs the lock | no | adopt |

Dropped: none of the listed items. Inside △6, the console part (open with mechanism 0xFF) is dropped: console §1 already rejects an unknown mechanism unsupported, and both implementations do so.

Side findings (no rule change; reported for the implementers):
- probe: plan_apply answers unknown_function for fn 0 in a role_assignment, where core §8's table says malformed (OepEndpoint.cpp plan_apply loop).
- probe: on the classic ESP32 analog frontends, zero is sent as 0 although the range starts above 0 V (OepAnalog.cpp:301-304, min_mv ignored).
- probe: `Oep.h:92` calls the clock "never wrapping"; the non-ESP32 / non-RP2 branch wraps (C-31).
- fake: `now_ns` has ms resolution and is not reset by `reboot()`, so it is not "since boot" after a simulated reboot.
- Python and JS: no host decodes the heartbeat event, although their comments say a heartbeat's boot_id is watched.

---

### C-19 ○ boot_id when the probe has no random source

**Premise.** A user builds a probe on a small MCU with no hardware random generator. They read §6.5, "even a probe with neither non-volatile storage nor a source of randomness always changes the value, from the variation in boot timing", and read a timer at a fixed point of their start-up code. The timer reads the same at every boot, so the boot_id repeats. A host that cached the fn mapping (Python, JS do, keyed on boot_id) keeps using it after the probe was reflashed with a different interface list, and sends dmi to the wrong fn. The constraint: the text cannot promise a value that some hardware cannot produce, so it must say which sources are acceptable in which order, and give the host a second signal.

**Proposed text** (core §6.5, replaces the sentences from "A 32-bit random number is fine" to "0 is an ordinary value."):

> The probe takes the boot_id, in this order of preference, from: a hardware random source (32 bits); a value kept in non-volatile storage that it changes at every boot (a counter, or a random value it saves); or, with neither, a mix of values that vary between boots (uninitialised RAM, the conversion noise of an ADC input, the count of a free-running timer when an external event such as the first USB or UART activity arrives). A timer read at a fixed point of the start-up code is not such a value. A probe that has only the last source may repeat a boot_id, and the host accepts that probability. 0 is an ordinary value.
>
> The host also learns of a reboot from open: an open with the session_id it used last, answered resumed = 0, means the probe no longer knows that session (a reboot, or another host's session in between). The host then lists again before it uses a remembered fn mapping (§7.2).

**Changes.**
- probe: the platforms other than ESP32 / RP2 take `micros()` in setup() (`platformRandom32`, OepPlatform.h:246-254), which is the "fixed point" case. Mix uninitialised RAM and an ADC read, or keep a counter in flash. A sketch that never calls `setBootId` sends 0 at every boot (OepEndpoint.h:192): make the library pick the value itself.
- fake: a fixed 0x1234ABCD (endpoint.py:538); tests pass a value to `reboot()`. No change needed (a fake is not a probe at boot), but `fake_serve` could draw a random value.
- hosts: Python and JS clear their caches on a changed boot_id at confirm and open, and treat resumed = 2 as swept. Add: resumed = 0 for their own last session_id → list again.

**Today.** ESP32 (`esp_random()`) and RP2 (`hwrand32()`) builds use a hardware source. Other platforms are the fixed-point case above.

**Recommendation.** Adopt. The order of sources is what an implementer needs, and the resumed = 0 rule costs a host one list per reconnect.

---

### C-20 ○ confirm: the bounds of its values

**Premise.** A user's probe sends window = 256 with max_frame = 1024 (a typo), or max_inflight = 0. One host deadlocks waiting for room that never comes, another sends anyway, a third clamps. The answer is the first thing every host reads, so each host author has to guess. The constraint: confirm's fixed part is the same in every protocol revision (§7.1), so the bounds must hold for every revision too.

**Proposed text** (core §7.1, after "flags is reserved (0)."):

> max_frame is 64 or more (§3.3), window is max_frame or more, and max_inflight is 1 or more. A host that receives a confirm answer outside these bounds treats that transport as not usable: it sends nothing more on it and reports the values. The host ignores the bits of flags (reserved, §2.4).

**Changes.** probe: none (every shipped sketch is inside the bounds; the smallest is window = max_frame = 512 in SwioDebugProbe). The library could refuse a `Limits` outside them at construction. fake: none (window 1 << 18, max_inflight 4). Python, JS: add the check (today both clamp max_inflight 0 to 1 and accept window < max_frame; JS also lowers its frame limit to any max_frame, even below 64).

**Today.** No host checks anything but the magic and the revision.

**Recommendation.** Adopt.

---

### ○2 reset method 0 and the reset line

**Premise.** A user implements riscv-dm reset. method 0 says "the probe chooses", and common §1.3's mark reset detail lists "2 NRST" for "when the probe chose". So they let method 0 pull a reset line. Debug §3 says there is no default reset wire, because pulling the wrong line can harm the target or the fixture; the user's probe now does exactly that. The constraint: the host must know which line moves, so the reset op cannot pick a line by itself.

**Proposed text.**

Debug §4.3, TLV 0x01 method:

> TLV 0x01 method (u8): 0 the probe's default, which in revision 1 is ndmreset; 1 ndmreset. 2 is reserved (there is no common procedure for a target's system reset, so the host builds it with dmi). A method of 2 or more is a value this probe cannot handle (core §2.3: rejected unsupported when sent critical, otherwise ignored). **The reset op never drives a reset line**: a reset line moves only through the reset TLV of attach (§3) or through the host's own use of a fixture interface.

Common §1.3, mark reset detail:

> Method (`mark_detail_reset`: 1 ndmreset (the reset op), 3 the reset TLV of attach. 2 is reserved)

Registry: `mark_detail_reset.nrst = 2` becomes a reserved comment.

**Changes.** None. probe and fake: method 0 and 1 both run ndmreset, the reset op always marks detail 1, and detail 2 is never sent (OepTarget.cpp:773-813; endpoint.py:2087-2097).

**Today.** As above.

**Recommendation.** Adopt. It states what everybody does; the only alternative (letting method 0 choose a line) contradicts debug §3.

---

### C-31 ○ The clock never goes back

**Premise.** A user records a long capture with a probe whose clock is a 32-bit microsecond counter scaled to ns. After 71.6 minutes it wraps. WireSkein places an analog track by subtracting two start_ns values (`oep.py:402-404`), so the track lands 71.6 minutes off; its web viewer places the trigger by subtraction too. boot_id does not change, so nothing tells the host. The constraint: §2.6a calls the clock "ns since boot (u64)", which a careful reader takes as non-decreasing, but it does not say so, and §2.6 lets interface times wrap.

**Proposed text** (core §2.6a, after the first sentence):

> The clock does not decrease and does not wrap while the boot_id is the same. A probe whose hardware counter is narrower than 64 bits extends it in software (counting its wraps), and reads it often enough not to miss a wrap.

**Changes.** probe: `nowNs` (Oep.h:95-103) on platforms other than ESP32 / RP2 is `micros() * 1000` with a 32-bit `micros()`; extend it with a wrap count (the main loop reads it far more often than once per 71 minutes). fake: monotonic (`time.monotonic()`), no change. Hosts: no change.

**Today.** ESP32 and RP2 use 64-bit counters. The other branch wraps at 71.6 minutes.

**Recommendation.** Adopt.

---

### C-21 (rest) ○ Where an fn named inside the payload is checked

**Premise.** A user's host sends plan_apply with a role_assignment whose fn does not exist and whose other assignment has a malformed length. One probe answers unknown_function, another malformed. A conformance test that expects one reason fails on half the probes. §4.3 says "When an fn designated inside the payload … does not exist, unknown_function is reused", but not where in the order. The constraint: the order of §4.3 already makes a probe finish the format checks (order 5) for the whole request before order 6, so the fn check fits between them without a new pass.

**Proposed text** (core §4.3, order 5, appended):

> 5. … Then, when the format is correct: an fn designated inside the payload (describe, subscribe, unsubscribe, plan_apply, the items of probe.config) that does not exist → unknown_function.

and the sentence "When an fn designated inside the payload … is reused." becomes "… is reused, at the end of order 5."

**Changes.**
- probe: checks fns item by item, mixed with each item's other checks. plan_apply checks fn per TLV inside the length loop (and answers unknown_function for fn 0, which §8 makes malformed); probe.config set checks each item fully before the next, so an earlier item's unknown_function or unsupported wins over a later item's malformed (OepConfig.cpp:626-656). Both need the malformed pass first.
- fake: plan_apply checks an unknown critical tag (unsupported) before unknown_function and some malformed checks after it (endpoint.py:1383-1388); probe.config set mixes them in dict order (endpoint.py:2926, 2962, 3064-3120). Same change.
- describe and subscribe already follow the proposed order in both.

**Today.** As above. No host depends on which reason comes first.

**Recommendation.** Adopt. Alternative: allow "per element, in order" for long payloads. Not recommended: it would make §4.3's order 5 / 6 rule depend on the payload and break the conformance vectors.

---

### C-36 △ Short messages and roles in the wrong direction

**Premise.** A user's host has a bug and sends 4-byte requests, or a bridge echoes the probe's answers back to it. §2.4 discards an unknown role, but 0x02 is known; nothing says what a probe does with an answer it receives, or with a request too short to hold fn and op. On the host side, an answer shorter than its 5-byte header makes Python and JS raise an exception from the request instead of treating it as a broken answer. The constraint: a message too short to carry corr cannot be answered, and a request without its session_id cannot be checked against §5.2, so the simplest rule is to discard.

**Proposed text** (core §2.4, added after "Frames with an unknown role are discarded."):

> - The probe discards, without answering, a message whose role is not a request role (0x01, 0x81), and a request shorter than its header (6 bytes, or 10 with session_id). The host discards a message whose role is a request role.
> - The host treats an answer shorter than 5 bytes, and an event or data frame shorter than its header, as a broken frame (§5.1, §5.2).

**Changes.** probe: none (drops all of these, OepEndpoint.cpp:388-395). fake: none (the transports drop them). Python, JS: an answer of 3 or 4 bytes with a matching corr raises `ShortPayload`; treat it as broken (resend, §5.2).

**Today.** As above. Wrong-direction roles from the probe are dropped by both hosts.

**Recommendation.** Adopt. Alternative: answer malformed when corr is readable. Not recommended: no conforming host sends such a message, and the answer for a 0x81 request without its session_id could not enter the table of §5.2.

---

### C-38 △ When the resend also gets no answer

**Premise.** A user's probe resets while a request is outstanding on a COBS serial port. The host's wait passes, it resends once (§5.2), and the resend gets no answer either. §5.2 stops there. Python and JS raise a timeout and keep using the port as if nothing happened; the next request may go to a probe that rebooted (new boot_id, no session) or now runs at another speed. The constraint: COBS recovers the framing by itself, so §5.1 does not apply to it today, but the cause here is not framing.

**Proposed text** (core §5.2, after the first bullet):

> - When the wait for the resend also passes without an answer, the host treats the transport as failed: the outcome of that request is unknown, and the requests outstanding on that transport fail with it. Before it sends anything else there, the host recovers with the confirm of §5.1 (on every kind of frame, COBS included: quiet input, then a confirm whose answer carries its own corr) or closes and reopens the transport. A changed boot_id in that confirm means a reboot (§6.5). After recovering, the host reads the state before it repeats a state-changing request.

**Changes.** probe, fake: none. Python and JS on COBS links: today they raise and keep the port; add the confirm. On length-framed links both already resync. (JS and Python also fall back from a raised port_speed first; that stays, §3.5.)

**Today.** As above.

**Recommendation.** Adopt.

---

### C-39 (rest) △ list is fixed for a boot; the end of paging

**Premise.** A user writes a probe whose interfaces appear when a module is plugged in. A host caches name → fn while the boot_id is the same (Python, JS do, as §7.2 allows). The new interface is never seen; a removed one leaves a dangling fn. §7.2 says fn does not change while booted, but not that the list does. And §7.3's "end of paging" rule names describe, state and the others but not list, so a host that asks list with first beyond the matches cannot know what comes back.

**Proposed text** (core §7.2, replacing the last bullet):

> - The answer of list (which interfaces exist, their fn, instance, revision and name) does not change while the boot_id is the same. A probe that gains or loses an interface reboots (a new boot_id). The host may remember the mapping from name to fn while the boot_id is the same.
> - If first is at or beyond the number of matching entries, the answer has that total and count 0.

**Changes.** probe: every sketch adds its interfaces in setup(); the library would still accept a later `add()` (OepEndpoint.cpp:58-63): refuse it after the first `poll()`. fake: fixed at construction. Both already answer count 0 with the real total. Hosts: no change.

**Today.** As above.

**Recommendation.** Adopt.

---

### C-40 △ Wrapping values: a number instead of "well below half"

**Premise.** A user implements marks with a u32 serial and a ring, and asks how far apart two live serials may be. §2.6 says "well below half of that width", which is not a number to test against. It also lists resource numbers, which no rule compares by order (§9 uses a reuse distance instead). The constraint: the bound must be one every probe meets with its buffers, and resource numbers must stay governed by §9 alone.

**Proposed text** (core §2.6, replaces the paragraph):

> seq (u16) and those serial numbers and times defined by an interface that are defined to wrap are compared by taking the difference as a signed value of the same width w (serial number arithmetic). Among the values of one such space that the probe holds at the same time (marks still readable, segments not yet released, placements not yet read), the newest minus the oldest is less than 2^(w−2) (a quarter of the width). Values that do not wrap are u64 (the positions of streams and the times of the standard interfaces, etc.). Resource numbers (§9) are compared only for equality; their reuse is governed by §9.

**Changes.** None on the wire. probe: mark serials (u32) and preload slots (u8) stay far inside the bound; `OepStream.h:66, 90` compares `serial_ < mark_capacity_` without wrap arithmetic, and the capture segment serial is compared with `<` (it restarts at every start): both unreachable before 2^32, worth fixing. fake: wraps with masks; resource numbers 1 to 65535 skipping live ones.

**Today.** As above.

**Recommendation.** Adopt. Alternative: delete the sentence. Not recommended: a host comparing marks needs the bound.

---

### C-41 △ Which USB interface a transport names

**Premise.** A user's host on a computer with two probes wants to match each serial port to the transport entry of describe (to know which port is the UART bridge, §4.4's transfer time). A USB CDC function has two interfaces (communication and data); the OS names the port by the first (the communication interface) on common hosts. §7.5 says "the USB interface number" without saying which, and a UART bridge (a separate USB chip) is USB to the host but not to the probe. The constraint: the probe must be able to know the value from its own descriptors.

**Proposed text** (core §7.5, row 0x49 transport, the interface field):

> interface(u8): for USB CDC (kind 2), the bInterfaceNumber of the CDC communication interface (the first interface of the function); for built-in USB serial (kind 3), the same number as the hardware presents it, or 0xFF if the probe cannot know it; for vendor bulk and HID, the number of that interface; 0xFF for a UART bridge (kind 1) and for TCP.

**Changes.** probe: ESP32-P4 sends 2 (the communication interface of its CDC pair) and the RP2 firmware sends 0, both as proposed. Examples that do not pass a number (MinimalProbe, FixtureProbe, RvswdDebugProbe on RP2) send 0xFF for a CDC transport: pass the number. fake: CDC 2 / 0, UART bridge and TCP 0xFF, as proposed. Hosts: JS parses the value, nobody uses it yet.

**Today.** As above.

**Recommendation.** Adopt.

---

### C-47 △ A ceiling on max_op_ms

**Premise.** A user's probe declares max_op_ms = 0xFFFFFFFF (an uninitialised constant). Python's `run(timeout_ms=None)` then waits about 49.7 days. JS passes 4.29e9 ms to `setTimeout`, which overflows to about 1 ms, so the request is resent and fails at once. Either way the user sees a hang or a spurious failure, and §4.4 makes the wait a floor, so the host may not shorten it. The constraint: a ceiling must cover the longest single operation a probe may legitimately take (a long run, a flash save).

**Proposed text.**

Core §7.5, row 0x4D max_op_ms, after "**Mandatory.**":

> 1 to 600000 (`max_op_ms_max`, 10 minutes).

Core §4.4, after "Waiting longer than this floor is always allowed.":

> A host that reads a max_op_ms of 0 or above `max_op_ms_max` treats the probe as not conforming and does not use it.

Registry: `limits.max_op_ms_max = 600000`.

**Changes.** probe and fake: 10000, no change. Python, JS: add the check.

**Today.** No host caps the wait.

**Recommendation.** Adopt. Alternative: let the host cut its wait at a limit of its own. Not recommended: a cut wait leaves the outcome of a state-changing request unknown while the probe may still be executing it.

---

### N-1 ○ The transfer time before the first confirm answer

**Premise.** A user writes a host for a UART bridge. Core §4.4 makes the wait of every request, the first confirm included, add a transfer time of (L + max_frame × (1 + `notify_pending_max_frames`)) × 10 / baud, but max_frame is a value of the confirm answer, which the host does not have yet. One host guesses 65535 and waits 17 s at 115200 baud for its first confirm; another uses 0 and gives up early. The constraint: before its first confirm on a transport, the only messages a host may send are of at most 64 bytes (§3.3), and a confirm that crosses a burst of notifications left over from an earlier session is covered by the repeated confirms of §3.3 and §3.5, not by a longer wait.

**Proposed text** (core §4.4, in "The transfer time …", after "baud is the port's current speed."):

> Until the host has received a confirm answer on that transport, it uses `min_max_frame` (64) as max_frame; after that, the max_frame of the latest confirm answer there.

**Changes.** None. Python (`link.py:291`, `self.max_frame = reg.MIN_MAX_FRAME`) and JS (`link.js:203`, `probeMaxFrame` starts at `reg.MIN_MAX_FRAME`) already do this. probe and fake: not affected.

**Today.** As above.

**Recommendation.** Adopt.

---

### △5 i2c-target: the reserved addresses

**Premise.** A user configures an i2c-target with address 0x00 to test a DUT's general call, or 0x78 by mistake. Some I2C target peripherals refuse these addresses, others answer every general call or every 10-bit header on the bus and disturb the DUT's other targets. Today the text accepts them and says nothing. The constraint: the 7-bit field allows them, and a later revision may want general call, which a features bit can add without a revision change (§2.7).

**Proposed text** (fixture §3, configure bullet, after "If address exceeds 0x7F, rejected malformed."):

> An address in 0x00 to 0x07 or 0x78 to 0x7F (reserved by the I2C specification: general call, start byte, the 10-bit prefix and others) is rejected unsupported (payload `0x00`).

**Changes.** probe (OepP4I2cTarget.cpp:294) and fake (endpoint.py:2505): both accept them today; add the check.

**Today.** As above.

**Recommendation.** Adopt.

---

### △6 spi arm count > length; uart write without TX

**Premise.** A user's host arms spi-target with 8 bytes to send and a length of 4, or writes to a fixture.uart whose plan has only RX. The text says "count ≤ length" and nothing about write without TX, so one probe truncates, another accepts and drops the bytes, a third refuses. The constraint: count > length is a contradiction inside the request (malformed by §4.3 order 5); a write without TX is a state of the plan (unavailable, cause 6).

**Proposed text.**

Fixture §4, arm bullet: "(count ≤ length. The shortfall is 0)" becomes:

> (count ≤ length, count > length is rejected malformed. The shortfall is 0)

Fixture §2, after the bullet on the TX line:

> - write on an fn whose plan has no TX is rejected unavailable (cause 6).

(The console part of the finding, open with mechanism 0xFF, is dropped: console §1 already rejects an unknown mechanism unsupported, payload `0x00`, and both implementations do so.)

**Changes.** probe: both already (OepP4SpiTarget.cpp:303; OepFixture.cpp:400). fake: spi already malformed (endpoint.py:2631); uart write accepts without TX (endpoint.py:2488-2490, 2268-2273): add the check.

**Today.** As above.

**Recommendation.** Adopt.

---

### △9 Signed converter results

**Premise.** A user builds an analog probe on a differential ADC whose result is two's complement. Capture §1.2 says the bits of a slot are "the result of the conversion (unsigned)", which can be read as "this probe cannot be an OEP analog probe", or the user sends two's complement and every host converts it wrongly (Python, JS, WireSkein and its file format all read unsigned). The constraint: hosts must keep one conversion, (value − zero) × scale_nv, and the slot layout lets a probe send DMA records as they are; any per-sample processing costs CPU at high rates.

**Proposed text** (capture §1.2, rule 1, appended):

> A converter whose result is signed (two's complement in b bits) is sent as offset binary: the probe inverts bit b−1 of each value (adding 2^(b−1) modulo 2^b), and the zero it returns includes that offset (the value for 0 V).

**Changes.** None today (no probe has a signed converter). A future probe pays one XOR per value.

**Today.** probe: unsigned 12-bit values, zero 0. fake: unsigned 12-bit. Hosts: unsigned only.

**Recommendation.** Adopt. Alternative: a "signed" field in the configure answer so that DMA records can go out unchanged. Not recommended: it adds a fixed-part field every host must handle, for a case none has, and an XOR per value is small next to the transfer.

---

### △10 rvswd / swio scan kinds

**Premise.** A user reads debug §3: the kind of a scan entry is "1 = riscv-dm, 2 = arm-adi" for rvswd and swio. They ask whether a two-wire or one-wire wire can yield an arm-adi connection, and if so whether swd's asymmetries (§5: no slot, no console) apply to it. Neither implementation does it, and no target on these wires speaks ADI. The constraint: a later wire that carries ADI is a new wire with its own document (§0), so nothing is lost by closing this.

**Proposed text.**

Debug §3: "The kind of scan is `scan_kind`: 1 = riscv-dm, 2 = arm-adi. `id` is the raw identifier determined by the kind of wire (DMSTATUS for riscv-dm, DPIDR for arm-adi)." becomes:

> The kind of a scan entry on rvswd and swio is 1 (riscv-dm), and id is DMSTATUS. Their connections are used by `oep.target.riscv-dm` and `oep.target.console`.

Registry: `arm_adi = 2` is removed from the `scan_kind` enums of `oep.wire.rvswd` and `oep.wire.swio` (it stays under `oep.wire.swd`).

**Changes.** None. probe: scan writes kind 1 only (OepTarget.cpp:403); arm-adi accepts only swd's connections (OepSwd.cpp:516-518). fake: kind 1 only (endpoint.py:1815). JS passes kind through.

**Today.** As above.

**Recommendation.** Adopt.

---

### △12 Pin states from boot

**Premise.** A user builds a probe without `oep.probe.config` and wires it to a DUT. Core §8 says what a released pin does, and probe-config says what saved settings do at boot, but nothing says what a pin does from boot until a plan takes it. On an MCU whose pins come out of reset with a pull, the DUT sees a pulled line until the first plan; on another, the firmware leaves a peripheral's output on. The constraint: from power-on until the firmware runs, the pins are in the MCU's reset state, which no text can change (probe-config §5 says so), and some pins are the probe's own (`reserved`).

**Proposed text** (core §8, after the bullet on released pins):

> - **At boot**, before it answers its first request, the probe puts every channel that is not reserved (§7.5) in its idle state (above: the idle of the settings when they define one, otherwise Hi-Z: input, no pull). Until then the pins are in the MCU's reset state (informative: a line whose wrong level is harmful needs an external pull, [probe settings](oep-if-probe-config.md) §5).

**Changes.** probe: the RP2 and classic ESP32 firmwares and the FixtureProbe / ProbeConfig examples park every channel as a floating input at boot, as proposed. The ESP32-P4 firmware leaves the pins as the chip boots them (Esp32P4.h:193): add the park call. A channel disabled by the settings stays untouched, as probe-config §1 says. fake: no pins.

**Today.** As above.

**Recommendation.** Adopt.

---

### PC-9 (rest) △ state paging and storage_*

**Premise.** A user's monitoring host pages probe.config's state without the lock, while another host saves. Page 1 says storage_state 0, page 2 says 1 with a new hash. The text does not say which to believe, nor that the slot rows may shift between pages. The constraint: state is lock-free on purpose (§3.3), and a probe has no room to hold a snapshot for a reader.

**Proposed text** (probe-config §3.3, after the paging bullet):

> - Each page carries storage_state, storage_hash and unreadable_reason as they are when that page is answered; they may differ between pages, and the host uses those of the last page. The slots and binds may also change between pages (a set or save by the lock holder, an automatic attach); a host that needs the set of slots and binds to stay the same across its pages pages while it holds the lock (the slots' states may still change).

**Changes.** None. probe and fake sample per page; JS keeps the last page's values (Python not checked).

**Today.** As above.

**Recommendation.** Adopt.
