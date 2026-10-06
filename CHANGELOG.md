# Changelog

Changes to the OEP specification: the normative text (`docs/oep-core.md`, `docs/oep-if-*.md`, `docs/target-console-dmseq.md`) and
`registry/oep-v1.toml`, with the guides, tools and test vectors that go with them. How releases are tagged, and what a revision bump means:
[versioning](docs/versioning.md). Before the v1 freeze, breaking changes go in without raising any revision.

## Unreleased

v1 candidate. Changes since the last pushed state (ad9f8be). Most rule changes come from the
[v1 rule-change proposal](docs/v1-rule-change-proposal-2026-10-02.md) (topics 1 to 12) and the
[2026-10-06 rule-change proposal](docs/v1-rule-change-proposal-2026-10-06.md), reviewed by the implementers (ch32rv, WireSkein, bench),
and from the [third zero-base review](docs/v1-zero-base-review-3-2026-10-02.ja.md).

### Simplification after the external review (2026-10-06)

From the [v1 simplification proposal](docs/v1-simplification-proposal-2026-10-06.md) and the user's decisions D1 to D4, reviewed by the
implementers (ch32rv, WireSkein, bench).

Text only, no wire change:

- Console: the SDI and DMDATA mechanisms are written in full as normative text (both sides of the mailbox, the byte positions, the empty slot,
  the slots that carry no bytes); the origin notes are gone, here and in wire and debug (console §3.1, §3.2).
- HID: the reports carry one length-prefixed byte stream per direction: frames span reports, count 0 is skipped, padding is sent 0 and ignored,
  one report ID or none, the frame gap applies to the stream, an over-long count breaks the stream (core §3.1).
- References: core §0 says what the text alone defines; the core (USB, CDC ACM, HID, Microsoft OS 2.0), wire and debug (ADIv5.2 / ADIv6.0,
  RISC-V Debug 0.13.2 / 1.0), console and fixture (UM10204; SPI has no standard) list the external specifications and the subset they use;
  spi-target defines its modes (mode = CPOL × 2 + CPHA).
- Answer enums: a value is added to an answer's enum or set of bits without a revision only under three conditions (core §2.5, versioning §4).
- Wire scan: a count = 0 sequence with no combination from skip on is answered completed success with tried 0 and count 0 (debug §1).
- Probe settings §3.3: the paging sentence reads "reads all of its pages while it holds the lock".
- Core §13 rule 2 is a checklist every interface document fills in.
- Versioning §6 is decided: `v0.x` tags until the formal release `v1.0.0`; before the freeze an implementation names the specification tag it
  implements (every normative status line says so); no edition field.

**Breaking** (wire changes; no revision is raised before the freeze):

- One request header: `role 0x01, corr(u16), fn(u16), op(u8), session_id(u32)`, 10 bytes, session_id always present and 0 = no session. Role
  0x81 is gone; a lock-required op with session_id 0 is session_required; a lock-free op with 0 skips the session checks; open carries its id
  in the header and its payload is `lease_ms(u32), force(u8), [TLV owner]`; corr stays u16 (core §2.4, §2.5, §3.3, §3.4, §4.1, §5.2, §6, §12).
  Registry: `role_session_flag` removed.
- One TLV header: `tag(u8), len(u16), value` for every length; the short / long forms and the unique-encoding rule are gone; ignored needs at most
  19 bytes, `7F 01 00 00` at least (core §2.2, §2.3). Registry: `tlv_len_long` removed.
- Fixed forms are fixed by (name, revision) and never extended at their end; OEP grows only by a new TLV, a new optional op or event, a new value
  in a reserved space, or a new interface or revision (core §2.3, §2.7, §13; versioning §3.1, §4). Sequences are `count × element` with no
  element length: list, connections, scan, marks, streams, segments, probe.config state (slot_state, bind_state) and the bind item. The trailing
  optional fields are folded in: the idle item is 6 bytes (drive_kind 2 = the default level, the only drive an input idle carries), the slot
  item has boot_reset after attach, slot_state has reset_at_ns before tid; the probe no longer keeps unknown trailing bytes of items. The link
  test is counted: link_source answers `len(u16), data, [TLV]`, link_sink sends `count(u16), data, [TLV]` and gets an empty answer.
  Registry: `closed_tail` removed (schema and fn 0), `drive_kind.default = 2`.
- One declaration of optional ops: the common describe tag `ops` (0x09, `base(u8), bitmap`) in the describe of every fn, fn 0 included; every
  required op is set, an op not set is answered unknown_operation, experimental ops are never set (core §1.2, §4.3, §7.4). features keeps only
  optional functions that are not ops. riscv-dm declares reset, read_block / write_block, run and step by ops and has no features; i2c-target's
  stretch, logic / analog's query and force, capture-group's force and probe.config's save / erase are declared by ops (the storage tag is
  present exactly when save is offered, max_bytes 1 or more); port_speed by op 0x14 in fn 0's ops. Registry: `describe_common.ops = 0x09`;
  riscv-dm features removed; i2c-target features bit 0x02, logic / analog / capture-group features bits 0x01 and 0x02 reserved; fn 0 describe
  `port_speed` (0x4E) reserved. `discovery.json`: the example probe's describe of fn 0 carries ops (confirm, list, describe).
- Sessions (user decision D1): end, lease expiry and force all release everything the session created (plans, its shares of connections and
  streams, subscriptions); nothing is handed to the next session and there is no resume. open's answer is `lease_ms(u32), boot_id(u32), [TLV]`;
  a request with a session_id while the lock is free is no_session; the decision table of core §6.2 has seven rows; the resend table stays keyed
  by the last session's id until the next successful open, so a resent end is still answered; owner is kept while the lock is held; lock_state
  answers remaining 0 when free; a reboot is seen by open's boot_id (core §4.3, §5.2, §6, §9). Console streams stay the probe's per place and
  mechanism: a closed stream stays readable until the same mechanism is next opened at the same place, which returns its old number with its
  position and marks, so a one-command-per-process host keeps the first lines after a reset (console §2). Common §2, debug §2 (one row for end,
  lease expiry and force), capture (plan release and capture-group bind at the end of the session), probe settings. Registry: reject reason
  `expired` (0x0E) reserved, enum `resumed` removed, `mark_detail_closed` 2 is `session_ended`.
- The link test and port_speed move out of fn 0 into the optional standard interface `oep.link` (user decision D3; new document
  [oep-if-link](docs/oep-if-link.md)): op 0x01 source `length(u32)` → `len(u16), data`, op 0x02 sink `count(u16), data` → empty, op 0x03 port_speed
  (optional, declared by ops) with the handshake, states and return conditions unchanged. A minimal probe no longer implements the link test.
  The confirm repetition after a raised speed applies to every host on a UART bridge port and stays in the core (§3.3, §3.4); the old host
  obligation 7 is gone from the list (obligation 8 is now 7). Registry: fn 0 loses ops 0x14, 0x40 and 0x41 (fn 0 ops 0x40 to 0xEF are reserved),
  `port_speed_step` moves to `oep.link`; the timing comments point to oep-if-link.
- The core is split (proposal 4.6), Japanese only while Japanese is the working text: the transports (frames, sending, several transports, USB
  identification and the probing rule, serial-port sharing, the recovery of delimiting, the transfer time of the host's wait and the USB
  references) move to the new `docs/oep-transports.ja.md` (sections 1 to 7); core §3 and §5.1 point to it and keep their numbers. Every
  cross-reference of the Japanese documents, the registry comments, the tools and the vectors follows ("core §3.4" is now "transports §4").
  No rule changes in the move.

Vectors (proposal §6.1, Phase 2, started): `sessions.json` (the decision table, the resend of end, release at end, force, session_id 0)
and `ops.json` (per-op request / state / answer bytes for oep.link, gpio, rvswd, riscv-dm, console, probe.config and logic), computed by
`tools/oepvectors1.py` and checked by independent decoders in `tests/vectors/test_vectors.py`; conformance §4 lists them.

**Working language until the freeze** (user decision, 2026-10-06): until the v1 freeze the Japanese documents (`.ja.md`) are the working
text; the English documents are marked out of date and are regenerated from the Japanese at the freeze, when English becomes authoritative.
New documents (oep-transports) are Japanese only until then (core §0, README, CONTRIBUTING). 凍結までは日本語の文書が作業の文で、英語は凍結のときに
作り直して正とする。

### Rule changes: core and registry

- TLV tags: the tag number is the low 7 bits and bit 7 is the critical mark (role_assignment is 0x10, sent as 0x90); values a later revision may
  define are refused unsupported, not malformed; repeated, short and over-long request TLVs; experimental u8 enum values 0xF0 to 0xFE
  (d48ca6d).
- ignored: at most 16 entries in request order, 0x00 as the 16th means "more", never left out (`ignored_max_entries`) (cd15f53).
- The host's wait is a floor: the time set by the arguments (with the attach and scan budgets) + `host_wait_add_ms` + a UART bridge's transfer
  time, counted from the previous answer (f7d6d21); it applies to every request including link requests, and the confirms §3.3 / §3.5 repeat are
  new requests with new corr (d24cdd6, 3c6691a).
- Transports: no frame-gap restart on TCP; over-long lengths; `host_resync_wait_ms`; max_frame / window / max_inflight per transport; a UART
  bridge is 115200 8N1 and line coding and DTR do not gate OEP; confirm's transport TLV; an endpoint that answers is a probe; a relaying broker
  reports 0xFF; TCP listeners are transports (48b8cbe, 0bb10e8).
- Protocol revision: confirm never changes, the revision applies per transport, later confirms send the revision in use, the refusal carries the
  supported range (929bbb7).
- Normative words (RFC 2119 / 8174), a conformance clause and a Required column in the op table (4e62116); required and optional ops in one rule:
  every op of an interface's table is required unless its document marks it optional and names what declares it (2e70f40).
- Resend table stores rejected answers and binds TCP endpoints; a relaying broker's corr map; when the lease restarts and the answer's lease_ms
  range; a random non-zero session_id, open only with role 0x01; booleans and text checked; names, model and chip grammar; `x-` unit_ids;
  exclusive open, HID output reports, WinUSB; registry keys frozen and the `[reference]` table; instance per (name, revision); port_speed ±2 %
  and verify_ms 0 in try; heartbeat floor (fc17225).
- Taking a plan does not change a pin; an interface that only reads never changes it; an output-idle refusal is unavailable cause 5 /
  holder_kind 7 (18d7eac, 3d51d4a).
- Every repeating TLV is marked `repeats` in the registry; an interface may make a TLV always critical; contradictions are checked only among
  defined values (3c6691a).
- Registry names for the numbers that only the text had (`port_speed_switch_wait_ms`, `resend_max`, `host_serial_inflight_max_bytes`,
  `cobs_frame_max_bytes` and others), with informative notes (C-26 forged lock-free answers, C-46 owner, C-37, C-42, C-43) (5d02a6f, c6cc1f8).
- From the 2026-10-06 proposal (b4b08f1): the probe discards messages that are not requests and requests shorter than their header, the host
  discards request roles and treats short answers, events and data as broken (§2.4); values of one wrapping space held at once span less than a
  quarter of the width, resource numbers compared only for equality (§2.6); the clock never decreases or wraps while the boot_id is the same
  (§2.6a); an fn named inside the payload is checked at the end of order 5 (§4.3); `min_max_frame` as max_frame in the transfer time before the
  first confirm answer (§4.4); max_op_ms is 1 to `max_op_ms_max` (600000 ms) and a host does not use a probe outside it (§4.4, §7.5); a resend
  that also gets no answer fails the transport, which the host recovers with confirm on every frame kind or reopens (§5.2); boot_id sources in
  order of preference, and resumed = 0 for the host's last session_id means list again (§6.5); confirm bounds max_frame ≥ 64, window ≥
  max_frame, max_inflight ≥ 1, a host does not use a transport outside them (§7.1); list fixed while the boot_id is the same, first beyond the
  matches gives count 0 (§7.2); the transport's interface field is the CDC communication interface, 0xFF for a UART bridge and TCP (§7.5);
  every non-reserved channel in its idle state from boot before the first answer (§8). Registry: `limits.max_op_ms_max`, `mark_detail_reset`
  2 reserved, rvswd / swio `scan_kind` without arm_adi.
- USB identification: the project's USB VID:PID is `1209:4F45` (registry `usb.project_vid` / `usb.project_pid`). A host identifies an OEP
  probe automatically only by it; otherwise the user names the probe or chooses the port. Name-based discovery (iProduct) is gone.
  discoverable is 1 only for a probe that enumerates with the project's VID:PID (core §3.3, §7.5) (671ce9c, 1fca3cb).
- fn 0 restart (op 0x14, optional, declared in ops; requires the lock): the probe answers completed success with no payload, stops processing,
  closes its connections and puts every non-reserved channel in its free state, then restarts within `limits.restart_after_answer_ms`
  (100 ms) after the answer has left the transport, as from power-on (a new boot_id, saved settings applied, nothing of the old boot kept).
  The host closes, waits, reopens as a new open (confirm first; on USB the device may re-enumerate) and checks the new boot_id; a resend
  after the restart gets no_session (core §6.6, §12; link §3 host obligation 6). ops.json has the answer and the refusals; conformance,
  the host guide §5.2 and security §4 follow.

### Rule changes: standard interfaces

- Wire and debug: per-request retries 200 ms, wire loss after 1000 ms of real time, attach budget 1000 ms, scan budget 500 ms, search_retries;
  only time-based dmi waits count against max_op_ms (3a88ec9); what every wire shares and what a new wire defines, wires without pins, writes
  before the speed is verified, scratch check with restore, attach_writes_unbounded, undeclared combinations unsupported with index, "found",
  halt / step timeouts, one target_id scheme space, console rules per mechanism (78403b2); RVSWD and SWIO frames (7392817, e9cd891, 598bb26);
  SWD lines and packets (8d91db0); lines while the wire does not answer, reset TLV on an output-idle channel (975d88c).
- Electrical safety: scan count = 0 leaves out idle-item channels, output-idle channels refused, pins return to idle when a connection closes;
  spi-target drives MISO only while CS is active; i2c-target open-drain only with declared pull-ups; logic capture only listens (0517c2f);
  spi-target cs_setup_ns (73a0c37).
- Capture: modes, streaming rules and background in the normative text; critical configure TLVs; blocking_ms; capture-group states; positioned
  read beyond the write position (a35acb0).
- Console dmseq: a word of 0 is not an answer, ownership, real-time waits, byte order with examples, CRC-8 check values (67863b1).
- Undefined values refused unsupported in every interface text (gpio, uart, i2c-target, attach, riscv-dm reset, read from) (fb44490).
- probe-config: line search also finds firmware labels; standard line names in the registry and `x-` for private ones; idle pulls a channel
  lacks; the channel of label / idle / disable; label text 1 to 32 bytes; get's answer; canonical form details; transport indexes invariant and
  bind checked at boot (20967d7); boot_reset is a boolean (73a0c37); §5 Safety, informative (5d02a6f).
- From the 2026-10-06 proposal (40291a4): riscv-dm reset method 0 is ndmreset in revision 1 and the reset op never drives a reset line, mark
  reset detail 2 reserved; i2c-target refuses the reserved addresses 0x00-0x07 / 0x78-0x7F unsupported; spi-target arm count > length is
  malformed, fixture uart write without TX is unavailable cause 6; a signed converter result is sent as offset binary; rvswd / swio scan
  entries are kind 1 (riscv-dm); probe-config state pages carry storage_* as they are when answered, the host uses the last page.
- Analog capture: a value of 0 or 2^b − 1 (the converter's minimum or maximum code) means the input was at or beyond that end of the
  frontend's range; the host shows it as clipped, not as a voltage, and the probe sends it unchanged (capture §1.2 rule 6; conformance host
  checklist).
- Console write and reset settle (ja, the working text; agreed by ch32rv, backed by the bench's measurements, no objection from WireSkein):
  a console write goes into a per-stream send queue whose size the probe declares in the new describe tag 0x41 send_queue (u16 bytes, at
  least 64, `limits.console_send_queue_min_bytes`; required with mechanism 1 or 2); accepted = what fits in the free space, 0 only when the
  queue is full; the probe feeds the target from the queue at the mechanism's pace (dmseq 2 bytes per answer, DMDATA 3); the "at most the
  send slot, 0 while it is busy" rule is gone (console §1, §2, §3.2; common §1.4; dmseq host rule 5). riscv-dm reset and attach's reset TLV
  wait, after the release, for a silent debug module to answer again, at most `limits.reset_settle_ms` = 700 (capped by max_op_ms), not
  counted as wire retries or in the attach budget; still silent at the bound = status line, no redo, the connection is kept (debug §1, §2,
  §3, §4.3); core §4.4's wait floor counts reset_settle_ms as argument time for both. Conformance, glossary and both guides follow.
- probe-config (ja): an item value longer than its definition follows core §2.3's longer request TLV: critical = rejected unsupported
  with the item's tag, otherwise the item is not applied and is listed in ignored; added to the refusal table (probe-config §1, §2).
- oep.link source (ja): the most that fits is max_frame − 26 (`limits.link_source_overhead_bytes`: header 5, len 2, room for ignored 19);
  the probe keeps the room for ignored even when nothing is ignored, so len does not depend on the request's TLVs (link §2); a vector
  "link source: more than fits" in ops.json.
- Wire attach joining a connection (ja, agreed by ch32rv, from a bench failure): an attach that joins an existing connection keeps the
  connection's current setting for every setting TLV it does not carry (idle_clock; max_speed is always carried); only the TLVs it carries
  change the settings, under their existing rules. The values for an absent TLV (idle_clock 0 = high) apply to a new connection only. A scan
  does not change a live connection's settings. Informative reason: a tool that only joins a slot's connection must not change how the line
  rests (debug §1, §3; probe-config §1.1; conformance and the host guide follow).

### Tools and test vectors

- `tests/vectors/`: machine-readable vectors computed from the text by `tools/oepvectors1.py` (CRCs, COBS and frames, headers and TLVs, confirm,
  the probe.config hash, refusals and ignored) (e21a9a2).
- `discovery.json`: the example probe's describe of fn 0 also carries discoverable 0 (core §7.5: it does not enumerate with the project's USB
  VID:PID), and the describe past the end asks from 4; a test checks that the example probe's confirm answers carry the transport TLV and its
  describe of fn 0 carries unit_id, transport, max_op_ms and discoverable; getting-started's bytes follow (en + ja).
- `ops.json`: the console cases use stream 2, not 1: connection 1 already holds number 1 in core §9's one space, so no probe can have
  stream 1 on connection 1.
- `discovery.json`: the example probe sets every op core §1.2 requires of fn 0 in ops (confirm, list, describe, open, end, keepalive,
  lock_state, subscribe, unsubscribe; no plan role), and the test checks ops against that list; getting-started §3.3 bytes follow and §4
  says a probe that answers only confirm, list and describe sets only those (ja).
- oepgen1: `[interface.line_names]` in all outputs (031ad71); `--check` refuses unlisted table kinds (73a0c37); SPDX lines and a C header
  `oep_v1_registry_c.h` (5d02a6f).

### Guides and records (no rule change)

- New guides, English with Japanese translations: [conformance](docs/conformance.md) (3fb3f04), [getting started](docs/getting-started.md),
  [security and safety](docs/security.md), [glossary](docs/glossary.md) (f951bd8), [versioning](docs/versioning.md) and this changelog.
- Host and probe development guides in English, renumbered and completed; chip-specific stories moved to the record
  [implementation notes](docs/implementation-notes.ja.md) (4bf464d).
- Host and probe guides, conformance and security follow the 2026-10-06 rule changes (5cae93f). development-guidelines is now a record (the
  project's working criteria); the review guide points to the English release-testing (21ac4d1).
- Host guide §4, probe guide §8, usb-identity, conformance, glossary, README and project concept follow the project's USB VID:PID
  `1209:4F45`; a probe behind a UART bridge or on a built-in USB serial with fixed descriptors is found by the port the user chooses
  (f1627ad, 7ac55de, 42d69ea, 72aa324).
- The v1 rule-change proposals (2026-10-02, 2026-10-06) and the third zero-base review with the status of every finding (41563f1, 0dd15c2,
  09622ef, d56a8e7, 536fc99, e0a0776, 1220792, 3ad540a).
