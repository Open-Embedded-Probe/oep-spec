# Changelog

Changes to the OEP specification: the normative text (`docs/oep-core.md`, `docs/oep-if-*.md`, `docs/target-console-dmseq.md`) and
`registry/oep-v1.toml`, with the guides, tools and test vectors that go with them. How releases are tagged, and what a revision bump means:
[versioning](docs/versioning.md). Before the v1 freeze, breaking changes go in without raising any revision.

## Unreleased

v1 candidate. Changes since the last pushed state (ad9f8be). Most rule changes come from the
[v1 rule-change proposal](docs/v1-rule-change-proposal-2026-10-02.md) (topics 1 to 12), reviewed by the implementers (ch32rv, WireSkein, bench),
and from the [third zero-base review](docs/v1-zero-base-review-3-2026-10-02.ja.md).

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

### Tools and test vectors

- `tests/vectors/`: machine-readable vectors computed from the text by `tools/oepvectors1.py` (CRCs, COBS and frames, headers and TLVs, confirm,
  the probe.config hash, refusals and ignored) (e21a9a2).
- oepgen1: `[interface.line_names]` in all outputs (031ad71); `--check` refuses unlisted table kinds (73a0c37); SPDX lines and a C header
  `oep_v1_registry_c.h` (5d02a6f).

### Guides and records (no rule change)

- New guides, English with Japanese translations: [conformance](docs/conformance.md) (3fb3f04), [getting started](docs/getting-started.md),
  [security and safety](docs/security.md), [glossary](docs/glossary.md) (f951bd8), [versioning](docs/versioning.md) and this changelog.
- Host and probe development guides in English, renumbered and completed; chip-specific stories moved to the record
  [implementation notes](docs/implementation-notes.ja.md) (4bf464d).
- The v1 rule-change proposal and the third zero-base review with the status of every finding (41563f1, 0dd15c2, 09622ef, d56a8e7, 536fc99,
  e0a0776, 1220792).
