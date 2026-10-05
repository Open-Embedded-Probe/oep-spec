# OEP v1 conformance

[日本語](conformance.ja.md)

Status: **guide** (not normative). It adds no rule: every line points to the normative text that holds the rule, and where this
document and the normative text differ, the normative text is right. It answers one question: what a probe, and a host, must do to
conform to OEP v1, and how an implementer checks it. The conformance clause itself is [core](oep-core.md) §1.2.

## 1. Probe checklist

A probe conforms when it does everything in this list for the transports and interfaces it exposes.

**Transports and frames**

- At least one transport of core §3.1, with its frame (§1.2).
- Serial port: COBS + CRC-16 frames enclosed in 0x00 on both sides (§3.1), the receiving and raw-byte rules (§3.4), the UART bridge
  line and boot speed (§3.4), DTR / RTS not used to decide anything (§3.4), raw transfer stopped while a session holds the port (§3.4).
- Vendor bulk and TCP: `length(u16) message` (§3.1), the zero-length-transfer rule on vendor bulk (§3.1), no restart on a pause on TCP (§3.2).
- HID: reports of `count(u16)` and padding (§3.1), output reports on both interrupt OUT and SET_REPORT (§3.3).
- A length over max_frame: discard and wait, or close on TCP (§3.1). A pause of `probe_frame_gap_ms` restarts the read except on TCP (§3.2).
- Messages up to 64 bytes accepted before confirm (§3.3); nothing sent over max_frame (§3.3).
- USB: the serial number equals unit_id where the probe chooses it (§3.3); vendor bulk and HID in the shape of §3.3, at most one of each.
- An endpoint that answers OEP requests itself is a probe, whatever is behind it; a relaying broker follows §3.1 and §5.2.

**Messages, refusals and tails**

- Headers of requests and answers (§4.1, §4.2); one answer per request on the transport it came from, in order (§4.2, §4.4).
- rejected only for what was not accepted; completed failed / partial for what was accepted and failed (§4.2).
- The order of refusal, first reason that applies (§4.3), with the payloads of §4.3 (unavailable TLVs, unsupported tag).
- Unknown op: unknown_operation; an optional function of an implemented op: unsupported (§1.2).
- Request TLVs: critical bit, unknown critical TLV unsupported, unknown non-critical TLV ignored, a TLV longer than known, a short TLV,
  a repeated non-repeating TLV, tags 0x7F / 0xFF (§2.2, §2.3).
- ignored (tag 0x7F) on every completed answer that needs it, in request order, at most 16 entries with 0x00 as the 16th, room always kept (§2.3).
- Unique TLV encoding (§2.2); booleans and text in requests checked (§2.1); experimental values not used when shipping (§2.5).
- window / max_inflight per transport (§4.4).

**Sessions and the lock**

- One lock, the decision table of §6.2, lease restart and pause during execution (§6.1).
- open / end / keepalive / lock_state / force / owner (§6.4); lease rounded into 1000 to 60000 ms (§6.4); session_id 0 rejected (§6.1).
- The resend table: at least max_inflight entries, rejected answers stored, discarded at every successful open, one table per probe (§5.2).
- Lock-free ops change no state (§6.3); boot_id changes at every boot (§6.5).
- Lifetime of the session's resources on end, expiry, force, re-open and reboot (§9); resource numbers (§9).

**fn 0 (`oep.core`)**

- Required ops: the rows marked "yes" in core §12 (confirm, list, describe, open, end, keepalive, lock_state, subscribe, unsubscribe,
  link_source, link_sink). plan_apply / plan_release when any interface has plan roles, otherwise unknown_operation (§1.2). port_speed is
  optional; when present, the whole of §3.5 (states, return conditions) and the describe tag 0x4E.
- confirm: revision choice, the transport TLV, the refusal with the supported range (§7.1).
- list: label-boundary matching, instance numbering, stable fn while booted (§7.2).
- describe: paging, declarations only and unchanged while the boot_id is the same, no TLV in the request (§7.3).
- Required describe tags of fn 0: unit_id, transport (one per transport) and max_op_ms (§1.2, §7.5); plan_roles when the plan has a limit (§7.5);
  discoverable sent as §7.5 says. unit_id uniqueness and invariance, transport index invariance (§7.5).
- plan: atomic per fn, its refusals, settings plans, released pins to the idle state, taking a plan changes no pin (§8, §8.1).
- Notifications: subscribe / unsubscribe, seq, heartbeat on fn 0, answers first and the pending limit (§11.2 to §11.4).

**Timing bounds** (values in `registry/oep-v1.toml`)

- `probe_frame_gap_ms` (§3.2); no request longer than the declared max_op_ms, and ops that could exceed it refused (§7.5); lease limits
  (§6.4); heartbeat period (§11.3); port_speed verify_ms / idle_ms and the return conditions (§3.5); the attach and scan budgets of each
  wire ([wire and debug](oep-if-debug.md) §1).

## 2. Host checklist

- **Frames**: one frame in one write, no pause of 100 ms or more inside it (§3.2); the COBS receiving rule (§3.1); nothing over 64 bytes
  before the confirm answer, nothing over max_frame after it, able to receive 65535 bytes (§3.3); the zero-length transfer on vendor bulk (§3.1).
- **Discovery**: USB identification only by the project's VID:PID once listed in the registry, a named probe by its unit_id, otherwise
  the user's choice (§3.3); the probing rule: confirm only, then close if no valid answer (§3.3); port selection inside a known probe (§3.3);
  transport order (§3.3); exclusive open (§3.3); DTR / RTS asserted (§3.4).
- **confirm and revision**: send the range it handles, then `min_rev = max_rev` the revision in use (§7.1); do not use an interface whose
  revision it does not know (§2.7).
- **Waits**: the floor of §4.4 for every request, its own link requests included; the transfer time on a UART bridge (§4.4); the receive
  capacity on serial ports (§3.4).
- **Resend and recovery**: at most once with the same corr (§5.2); corr advanced by 1 per request, 0 skipped (§4.1); resync on
  length-prefixed frames and `host_resync_wait_ms` (§5.1).
- **Sessions**: a random non-zero session_id (§6.1); the answer's lease_ms is authoritative, and keepalive extends it (§6.4); react to no_session / expired /
  locked (§4.3, §6.2); a changed boot_id invalidates its state (§6.5); the 0x81 requests of one session on one transport (§3.3).
- **Reading answers**: skip unknown TLVs and tags, use the first of a repeated tag, read a non-zero boolean as true (§2.1, §2.3); unknown
  values per §2.4; read ignored and its 0x00 entry (§2.3); dispatch by role and corr (§11.1); the critical bit where the request is
  meaningless without the TLV (§2.3).
- **Strings**: replace control characters and invalid UTF-8 before showing answer text (§2.1); compare unit_id with serial numbers and
  each other ignoring ASCII case (§3.3); never group, name or key anything by an `x-` unit_id (§7.5); iProduct and interface strings
  for display only (§3.3); `name#instance` and `oep://` addresses (§7.2, §7.6).
- **port_speed**, when the host uses it: host obligations 1 to 8 of §3.5.

## 3. Standard interfaces

A probe that lists an `oep.` name follows that interface's whole document. The short list of what is required:

| Interface | Required | Optional, declared by |
|---|---|---|
| Positioned streams ([common parts](oep-if-common.md) §1) | read, marks, clear, mark, write as §1 for each interface that uses them; status values of §3 | — |
| `oep.wire.rvswd`, `oep.wire.swio`, `oep.wire.swd` ([wire and debug](oep-if-debug.md) §0 to §3, §5) | attach (max_speed mandatory), detach, connections; scan when the wire declares pins; §1 attach rules and budgets; §2 lifetime and line states | scan on a wire without pins; the reset TLV of attach |
| `oep.target.riscv-dm` (§4) | dmi, halt, resume | reset, read_block / write_block, run, step: features bits 0 to 3; max_length with read_block / write_block |
| `oep.target.arm-adi` (§6) | transfer, read_block, write_block; max_length always emitted | — |
| `oep.target.console` ([console](oep-if-console.md)) | the ops of §1; describe mechanisms always emitted; mechanism 2 framed as [dmseq](target-console-dmseq.md) | which mechanisms (describe mechanisms) |
| `oep.fixture.gpio` ([fixture](oep-if-fixture.md) §1) | set, read; describe modes with mode 0 | output drive strength (§1.1) |
| `oep.fixture.uart` (§2) | the ops of §2; describe formats with 8N1 | other formats |
| `oep.fixture.i2c-target` (§3) | the ops of §3 except stretch; modes 1 and 2 | stretch (features bit1, with max_stretch_us); mode 3 (bit0); pull-ups (bit2, with pullup_ohms) |
| `oep.fixture.spi-target` (§4) | the ops of §4; cs_setup_ns when MISO is driven in software | LSB first (features bit0) |
| `oep.fixture.logic`, `oep.fixture.analog` ([capture](oep-if-capture.md) §1 to §3) | the ops of §3.2; describe of §3.5; calibration on analog only | query (features bit0), force (bit1), notifications (bit2) |
| `oep.fixture.capture-group` (§4) | the ops of §4.1; describe of §4.3 | force (bit1), notifications (bit2) |
| `oep.probe.config` ([probe settings](oep-if-probe-config.md)) | listed only by a probe that handles settings; get, set, unset, state; hash; refusals of §2; describe of §4 | save / erase (refused unsupported when max_bytes is 0); slots; bind (bind_modes bits 0 and 1 when present) |

## 4. How to check

**Test vectors** ([`tests/vectors/`](../tests/vectors/)). Computed from the normative text by `tools/oepvectors1.py`; where a vector and
the text disagree, the text is right (core §0 rule 4). They cover:

| File | Covers |
|---|---|
| `checks.json` | CRC-16 (core §3.1), CRC-32 (§5.2), the dmseq CRC-8 |
| `cobs.json` | COBS encoding and whole serial-port frames, including the forms the decoder also accepts (§3.1) |
| `headers.json` | request and answer headers and TLV encoding (§2.2, §4.1, §4.2) |
| `confirm.json` | confirm exchanges (§7.1) |
| `probe_config_hash.json` | the canonical form and hash of probe.config ([probe settings](oep-if-probe-config.md) §2) |
| `refusals.json` | requests and the exact answer for refusals of §4.3 and the ignored list of §2.3 |

An implementation reads the JSON files and compares its own encoder, decoder and answers byte for byte. To check that the vectors agree
with the text and the registry:

```sh
python3 tools/oepvectors1.py --check      # exit 1 if a file differs from what the rules give
cd tests && uv run pytest vectors          # the vectors against independent code (binascii, zlib) and the tool's --check
```

**A fake probe for hosts.** [oep-client-python](https://github.com/Open-Embedded-Probe/oep-client-python) serves a probe that answers
as this specification says, on a pty (a serial port) or on TCP (either framing), with injected faults (a dropped answer, a broken CRC,
noise) for testing resend and recovery:

```sh
python -m oep_client.fake_serve --pty     # first line: where to open; --help lists profiles and faults
```

**Looking at a probe.** `oep dump --port <port>` from the same package shows list and describe of every interface; that client's test
suite also checks the vectors against its own code and the fake.

**Not covered yet.** There is no automated conformance suite for a probe: the vectors cover encodings and a set of refusals, not the
session table, the resend table, paging, plan or the interfaces' behaviour. Timing (the waits, the lease, max_op_ms, the frame gap,
port_speed's return conditions, the attach and scan budgets) is not checked by any shared tool. The electrical rules (idle states, the
lines while a wire does not answer, cs_setup_ns) and behaviour on real hardware need the implementer's own tests on hardware.

## 5. What conformance lets an implementation claim

There is no certification: a claim of conformance is the implementer's own statement, checked against this list and the normative text.

- A probe that passes section 1, and section 3 for every `oep.` interface it lists, may say it is **an OEP v1 probe**, and names the
  interfaces (with revisions) it implements. A host that passes section 2 may say it is **an OEP v1 host**. The claim is for protocol
  revision 1 (core §2.7) and implies no optional function.
- An implementation that changes the wire format, answers in a way the specification does not allow, or puts its own interfaces or
  tags under `oep.` names is not conforming (core §13 rules 1 and 7). Its own interfaces use reverse-DNS names.
- Conformance does not grant the use of the project's USB VID:PID. That is granted separately, under the conditions of PID-USE in
  [oep-probe-arduino](https://github.com/Open-Embedded-Probe/oep-probe-arduino) (among them: built from that library, its source
  published, speaking OEP as specified, identifying itself honestly). Another implementation uses a USB ID of its own; hosts open it
  when the user names it or chooses its port (core §3.3).
- Conformance does not make a probe identified automatically, and does not say anything about the target chips it supports, its speed,
  or its electrical behaviour beyond what the normative text requires.
