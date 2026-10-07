# Changelog

Changes to the OEP specification: the normative text (`docs/oep-core`, `docs/oep-transports`, `interfaces/oep-if-*`, `interfaces/target-console-dmseq`) and
`registry/oep-v1.toml`, with the guides, tools and test vectors that go with them. How releases are tagged, and what a revision bump means:
[versioning](docs/versioning.md). Before the v1 freeze, breaking changes go in without raising any revision.

## Unreleased

v1 candidate. Changes since the last pushed state (ad9f8be). Most rule changes come from the
[v1 rule-change proposal](docs/v1-rule-change-proposal-2026-10-02.md) (topics 1 to 12) and the
[2026-10-06 rule-change proposal](docs/v1-rule-change-proposal-2026-10-06.md), reviewed by the implementers (ch32rv, WireSkein, bench),
and from the [third zero-base review](docs/v1-zero-base-review-3-2026-10-02.ja.md).

### Wi-Fi settings and TCP discovery (2026-10-07)

A probe that speaks OEP over TCP on Wi-Fi needs its network credentials set by any host, and found on the network. Japanese only while
Japanese is the working text.

- probe.config: item 0x08 `wifi` = index(u8) ssid_len(u8) ssid pass_len(u8) passphrase, key index; ssid 1 to 32 bytes; the passphrase is
  none (pass_len 0), 8 to 63 bytes of 0x20-0x7E, or 64 hex digits. The probe tries the entries in index order (it may skip those a scan
  did not see), uses the first that connects, waits and starts over when all fail, starts over after a loss; no entries = Wi-Fi off. A
  set or unset that changes or removes the entry in use is answered before the link is dropped.
- probe.config: the passphrase is write-only. get answers pass_len 0xFF (set) or 0 (none) with nothing after it; a set with pass_len
  0xFF keeps that index's passphrase (malformed without an entry at that index), so get's item sent back changes nothing. The probe puts
  it in no answer and no log, and does not compute the hash from it; a host neither shows nor logs it.
- probe.config: describe 0x46 `wifi_max` (u8, 1 or more; with the item); the state answer carries TLV 0x01 `wifi` on every page:
  state (0 off, 1 connecting, 2 connected, 3 all failed, waiting), entry (0xFF none), reason (0 none, 1 not found, 2 auth, 3 no address,
  4 other), rssi (i8 dBm), ipv4 (4 bytes); rssi and ipv4 are 0 unless connected.
- Registry: the item, the describe and state-answer tags, enums `wifi_pass_len`, `wifi_state`, `wifi_entry`, `wifi_reason`, limits
  `wifi_ssid_max_bytes`, `wifi_passphrase_min_bytes`, `wifi_passphrase_max_bytes`, `wifi_psk_hex_digits`; generated code follows.
- Vectors: probe.config wifi set, get (pass_len 0xFF), get's item sent back, refusals (0xFF with no entry, a 7-byte passphrase, index at
  wifi_max), state with the wifi TLV, unset. Security guide: the passphrase crosses OEP unencrypted, so send it over a trusted transport;
  it is write-only. Conformance and glossary follow.
- Transports §3: a probe listening on TCP advertises a DNS-SD (RFC 6763) instance of `_oep._tcp` over mDNS (RFC 6762) with the TXT
  record `unit_id=<unit_id>`; the port comes from SRV (no fixed port); other TXT keys may be added and are ignored by hosts. A host opens
  only TCP endpoints found this way or given by the user, under the probing rule, and uses a named probe only when describe's unit_id
  matches. Port and discovery are no longer outside the specification.
- Host guide §4.1: browsing `_oep._tcp.local.`, choosing among probes (named, else let the user pick; one probe on USB and TCP is one
  probe), browsing again after a restart, an explicit address where mDNS does not reach; the reference probe's port 7450 as an example.
  §15.1: setting Wi-Fi (prompt for the passphrase, never print or log it, compare entries without it, 0xFF keeps it only at the same
  index, changing the entry in use drops a TCP link). Conformance and glossary follow.

### External review re-check (2026-10-07)

From the re-check of 3bca24c in `docs/external-spec-review-2026-10-06.ja.md`; verdicts in
`docs/external-spec-review-2026-10-07-response.ja.md`. Japanese only while Japanese is the working text.

- Transports: a frame may be split over any number of writes, USB transfers, HID reports or TCP segments, or written together with other
  frames; a receiver never relies on those boundaries. The "one frame per write" host rule goes; instead no sender (host or probe) pauses
  `probe_frame_gap_ms` inside a frame, except on TCP. HID rule 2 (frames across reports) is covered by this and goes (rules renumbered).
- Transports: a transport closing (a TCP connection, a USB device leaving the bus) does not end the session: session, lock, subscriptions
  and the resend table stay until a core §9 event; answers and notifications for the closed transport are dropped.
- restart: `restart_max_ms` does not apply to a client of a relaying broker; the probe's restart ends the broker (transports §1) and the
  client starts again as after a closed transport.
- Core: describe is the same on every transport, so each describe TLV and the common `max_length` fit every transport's `max_frame` (the
  smallest); debug's read_block / write_block follow.
- Core: `channels` is required when the probe has channels and absent means none; channel numbers are 0 .. channels - 1; §1.2 requires
  `channels` and §8 only from a probe with channels.
- Core: fn 0's fixed forms are set by the protocol revision (the (name, revision) rule is for named interfaces); `features` no longer lists
  notifications among its examples (notifications are declared by subscribe / unsubscribe in ops).

### Found while implementing (2026-10-07)

Japanese only while Japanese is the working text.

- Core: a host may resend with the same corr; the probe answers from its table, so a resend never runs a request twice. How many times
  and when is the host's choice (host guide §8: once after the wait when nothing came, at once up to a few times after a broken frame on a
  held serial port). The transport has failed when the wait of the last thing sent passes with no answer and the host resends no more.
  Registry `resend_max` goes; the probing rule of transports §3 says "a confirm and its resends".
- link sink: the largest count that fits is max_frame − 12 (request header 10 and count 2); the host guide's speed checks used
  max_frame − 7, 5 bytes over max_frame (source stays max_frame − 7: answer header 5 and len 2).
- fixture i2c-target: errors grows by at most 1 per write (a write over max_length into a full queue counts 1), as spi-target already
  says per transfer.
- capture rate, debug max_speed and idle_clock: refused with rejected unsupported carrying the tag as received (core §2.3); the text
  no longer names the bare tag (0x42, 0x01, 0x04), which read as if bit 7 were dropped.
- Core: interface names are 1 to 48 bytes (registry `interface_name_max_bytes` 64 → 48), so a list answer with one entry (5 + 3 + 7 +
  name) fits the smallest max_frame (64); with 64 it was 79 bytes. The longest standard name is 25 bytes.
- Host guide §5 (advice): a host that may stop and run again (a CLI, a broker) keeps its session_id per probe and, on the next run,
  opens and ends that session first to release what it held, since a closed transport does not end a session (transports §3).

### Rule review (2026-10-07)

From the v1 rule review of 2026-10-07 (`docs/v1-rule-review-2026-10-07.ja.md`): a rule stays normative only if, without it, independent
hosts and probes would fail to interoperate or would silently harm the target or the data; the rest moves to the guides, to the reference
implementation's limits document (oep-probe-arduino `docs/implementation-limits`), or goes. §3 (wording only) went in first; §2 (rule changes,
with the implementers' conditions: ch32rv, WireSkein, bench) follows. Japanese only while Japanese is the working text. Removed numbers stay
reserved in the registry and are never reused.

- **Breaking**, core: the ignored TLV (0x7F) goes. A probe ignores an unknown non-critical TLV and refuses an unknown critical one
  (unsupported); a TLV it implements is checked the same with or without bit 7 (wrong length or excluded value malformed, unused or unhandled
  value unsupported). Tags 0x00 and 0x7F are never tags. No room for ignored in answers (confirm fits 64 bytes; link source is max_frame - 7).
  The capture "always critical" exception, plan's role_assignment sent critical and uart's format note go with it.
- **Breaking**, core: refusal order keeps header, resend table and session; every other check is made before anything changes and any one
  reason that applies may answer. The contradiction paragraph and the interface refusal tables go.
- **Breaking**, core: corr_reused (0x0D, reserved) and CRC-32 go; the resend table keeps (corr, answer). probe.config's hash is a u32 the
  probe chooses that changes with the settings (get keeps tag and key order, max_bytes counts item TLV bytes, storage_hash equals get's hash
  while the saved settings are the current ones); `probe_config_hash.json` and the CRC-32 check value go.
- **Breaking**, core: list is `first(u16)` only (no prefix, no exact). `name#instance` and the `oep://` address move to the host guide (§5.3).
- **Breaking**, core: describe loses implementation (common 0x07), reserved (0x44), profile (0x45), resets_on_open (0x47), discoverable
  (0x4A) and model's character rules (`model_max_bytes`); model, chip and firmware are optional free text. unavailable loses holder_fn /
  holder_kind (cause 5 now covers the settings' plan, disable, output idle and slot).
- Core: §10 (long operations), the experimental value ranges and the reserved lock-free subscribe leave the text (registry reserves only);
  booleans read non-zero as true; request text, repeated tags and a describe TLV are no longer refused (a reader uses the first tag);
  resource numbers advance by one and skip numbers in use (no reuse distance); the ops value is base and a bitmap not past op 0xFF (no
  canonical form); no host rule for out-of-range max_op_ms or confirm values; no lease exception for table resends.
- Transports: a host writes one frame per write without a `probe_frame_gap_ms` pause (`host_frame_pause_max_ms` goes); a length-prefixed
  resync waits longer than `probe_frame_gap_ms` since the last write (`resync_quiet_ms`, `host_resync_wait_ms` go); a host opening a UART
  bridge repeats confirm for `port_speed_idle_ms` + `host_wait_add_ms` (`port_speed_confirm_extra_ms` goes), and the probing rule points
  there; the host receive-volume paragraph moves to the host guide §8 (`host_serial_*`, `cobs_frame_max_bytes` go).
- **Breaking**, debug: the probe's internal times and counts leave the text (`wire_retry_ms`, `wire_lost_ms`, `attach_budget_ms`,
  `scan_budget_ms`, `scan_tried_max`, `reset_settle_ms`, `dm_wait_ms`, `dmi_busy_retries`, `reset_wait_ms`, `reset_retries`,
  `swd_wait_retries`, `block_frame_overhead_bytes`, `tar_rewrite_bytes`): attach, scan and riscv-dm reset answer within max_op_ms, which a
  host counts as their argument time. New rules: wire retries never repeat a write that may have reached the target (busy / WAIT excepted;
  failed / partial with done before it; reads may repeat), and while a connection exists the probe's own retries and resyncs do not change
  the target (a wake that may reset it only inside attach and reset). A scan without max_speed tries the wire's slowest speed.
- **Breaking**, debug: the pinless wire, `attach_writes_unbounded` and the non-two-pin forms go; riscv-dm reset loses method, flags bit2 /
  bit3 and attempts (answer: status, flags, pc); run whose preparation fails answers stopped 3 (`not_run`); DATA0 / DATA1 restore is stated
  in riscv-dm (the probe for its ops, the host for its own dmi sequences); search_retries is diagnostic; the target_id scheme `wch_dmi_7f`
  is renamed `dmi_7f`; reserved op 0x04, address_hi, RV64 and running reads leave the text; the reference probe's RVSWD / SWIO / SWD notes
  move to the implementation limits.
- Common: a mark's position is the write position when the probe adds it (every later byte came after the event); read from 3 with
  arg > 0xFF and write count 0 are not refused.
- **Breaking**, console: the 20 ms DMSTATUS poll becomes an order (no console DATA0 / DATA1 access while a riscv-dm request of the connection
  runs or the hart is halted; DMSTATUS read after such a request before the next console read); send_queue and its minimum go. dmseq: host
  rule 1's answer after three invalid words, the empty-frame-only-when-idle rule and the host DM-reset / restore notes go.
- **Breaking**, capture: the configure answer loses timing (jitter_kind, jitter_ns) and rate_accuracy; describe loses mode's background,
  rate_list, rate_limit, channels' layout candidates, max_read, segment_ring, frontend_shared; capture-group loses max_tracks, budget and
  start_skew. skew, start_ns / start_uncertainty_ns, zero / scale_nv, frontend_used, reference and calibration stay.
- **Breaking**, fixture: gpio's drive is a level number (u8, 0xFF default; out of range or undeclared is unsupported), read loses drive, mode 7
  goes; uart's status loses configured; i2c-target has one form (configure takes the address, a write with data is one frame, reads answer from
  preload_tx; arm_rx, reset, the modes and pullup_ohms go; clock stretch stays an optional op); spi-target loses reset and counts errors once
  per transfer.
- **Breaking**, probe-config: the slot lock, boot_reset and the probe's retry with reset go (slot_state 0 / 1, no tid); bind is one stream
  (`port kind id`), without modes, mixed lines or counted resets, and resumes where it stopped after a session; the idle item is 4 bytes; the
  refusal table goes and only disable and idle must come first at start-up; at-boot slots are attached when the probe can try.
- **Breaking**, link: port_speed is the handshake only (`baud step verify_ms`; the port is the one the request came on; returns on its own
  after verify_ms, after `port_speed_idle_ms` without a good frame, or at the session's end; the host waits `port_speed_switch_wait_ms`
  and returns to the boot speed after revert, end or a restart). The 500000 default ceiling and the one-second check become the host guide's
  recommendation (§17). `port_speed_idle_max_ms` is renamed `port_speed_idle_ms`; `port_speed_broken_max` goes; `port_speed_tolerance_pct` (2) is added.
- Restart: the probe answers nothing until it restarts and answers confirm within restart_max_ms on the same transport, and does not reset
  the target; `restart_after_answer_ms` and the host procedure (now host guide §5.2, with the relaying broker) leave the interface.
- Guides: host guide §5.2 (restart), §5.3 (address and `name#instance`), §8 (broken frames on a serial port, receive volume), §10, §14 (SDI /
  DMDATA limits), §15 (settings without a computed hash), §17 (port_speed: the ceiling as a recommendation, resend at the raised speed first);
  probe guide §10 to §13 (reference values move to oep-probe-arduino's implementation limits); conformance, glossary, security, versioning,
  getting-started (list and describe bytes), review guide, USB identity and CONTRIBUTING follow.
- Registry, generated code, vectors (`checks`, `headers`, `refusals`, `discovery`, `ops_encoding`, `ops`) and tests follow.

### Structure: the core and the standard interfaces (2026-10-06)

From the v1 structure proposal (2026-10-06), decided by the user with the implementers' conditions (ch32rv, WireSkein, bench), and the
external re-review of the same day (its §3.2 and §3.3). Japanese only while Japanese is the working text.

- Documents: `docs/` keeps the core (oep-core, oep-transports), the guides and the records; the standard interface documents
  (`oep-if-*`, `target-console-dmseq`, both languages) move to `interfaces/`, with an index `interfaces/README.ja.md`. Core §14 (the list
  of standard interface documents) goes and the guides' section becomes §14; every relative link follows. A move of text: no rule changes.
- **Breaking**: the core has no name. `oep.core` is gone: fn 0 is the core, list never returns it (an example probe without
  interfaces lists nothing), and the core's version is confirm's protocol revision only; core §0 rule 3 has no exception and every
  optional feature is a named interface (core §0, §1, §1.2, §7.2). The core keeps only what every probe implements: plan_apply /
  plan_release and describe plan_roles move to the new interface `oep.probe.plan` (ops 0x01 / 0x02, describe 0x40; listed when an
  interface has plan roles; oep-if-plan); restart and restart_max_ms move to the new optional interface `oep.probe.restart` (op 0x01,
  describe 0x40; answer first, the restart after the answer, the host's wait; a relaying host forwards restart as any locking op, then
  closes its transport to the probe; oep-if-restart); `oep.link` is renamed `oep.probe.link`. Core §8 becomes the channels' free state
  (start-up, release, taking a pin changes nothing); transports §1 loses the broker's restart rules (a broker whose transport to the probe
  is gone, closed by itself included, ends) and result_lost loses its broker meaning; link §3 host obligation 6 returns to the boot speed
  after the answer of any op after which the probe restarts. Core normative text names no interface: saved settings are "settings an
  interface defines", §4.4's argument times and §7.5's max_op_ms are defined per op by the interface documents (debug: dmi, run; settings:
  save), §4.4's link wording is general. Core §13: `oep.<layer>.<name>` with the layers probe, wire, target and fixture; rule 8 keeps
  chip-specific procedures out of interfaces for any family and puts the family in the document header and the registry (`target`),
  not in the name; every interface document's header table has the family column. Registry: `[core]` replaces the `oep.core` interface
  (generated: namespace `core`, no name; Python `CORE`, not in `INTERFACES`), `target` on the wire and target interfaces. Vectors:
  discovery.json's list is empty; ops.json's restart cases are on fn 11 (`oep.probe.restart`) and new plan cases on fn 10.
- **Breaking**: notifications. subscribe and unsubscribe are ops of the interface that sends notifications, at 0x30 / 0x32 reserved in
  every interface's op space (registry `op_subscribe` / `op_unsubscribe`); the request carries no target fn (subscribe: min_bytes(u16)
  max_delay_ms(u32) [TLV]; unsubscribe: [TLV]); an interface that sends none does not have them (unknown_operation). fn 0 has no
  subscribe / unsubscribe and sends no notifications: the heartbeat (fn 0 event 0x01, `heartbeat_default_ms`, `heartbeat_min_ms`) is gone.
  min_bytes and max_delay_ms apply to data only; an event goes as soon as the answers ahead of it are sent (re-review §3.1, §3.3; core
  §1.2, §2.5, §11, §12). Logic, analog and capture-group get subscribe / unsubscribe (optional, in ops; streaming needs them) and lose
  features bit2 (notify); console and the fixtures say they have neither.
- **Breaking**: the probe's time is read with the new mandatory fn 0 op `clock` (0x04): no request fields, answer boot_id(u32)
  uptime_ns(u64) [TLV]; uptime_ns is the probe's own clock (core §2.6a), read after the request arrives and before the answer is
  sent (never an earlier or estimated value). Lock-free; with session_id 0 it needs no session and touches no session, lock or lease
  (core §1.2, §6.3, §7.7, §12). A relaying broker answers only the session ops (confirm, open, end, keepalive, lock_state) itself and
  relays clock like any other request with the ordinary wait (transports §1). How a host maps the value to its own time (midpoint of
  send and receive, half the round trip, the shortest of several reads, drift) is in the host guide §12, not in the core.
  confirm's answer is unchanged (TLV 0x01 transport only; 45 bytes with the room for ignored, core §7.1). Registry, generated code,
  vectors (discovery's fn 0 ops include 0x04; sessions.json has clock with session_id 0, with and without a session open, and with the
  session's own id) and tests follow.
- The ops encoding (re-review §3.2): the value is 2-33 bytes (a 1-32 byte bitmap), base + 8 × bitmap bytes ≤ 256, bit 0 is set (base is the
  lowest declared op) and the last byte is non-zero, so one op set has one encoding; a host that gets an ops breaking this does not use that
  fn (fn 0: the probe) (core §7.4). New vectors ops_encoding.json (shortest, longest, wrong lengths, the 0xFF bound, non-canonical) with
  an independent decoder in the tests; every ops in the vectors is canonical.
- Wording (user decision): there is no "standard interface" category. The core has two layers, the core and interfaces, and treats every
  interface the same (core §0 rule 4). An interface name is a reverse-DNS name; the project's own interfaces are the one exception and
  use the reserved short prefix `oep.` instead, which is the only special thing about them; anyone extending OEP uses a reverse-DNS name;
  only the name's owner extends an interface (core §13 rules 1, 7, 9). The project's upkeep of the `oep.` interfaces (registry entries,
  vectors, the fake probe) is stated once, where the registry is described (core, top), as project process. The Japanese text says
  インターフェース, or 名前が `oep.` で始まるインターフェース where it must; the glossary defines oep インターフェース as that shorthand. Document
  titles read 「OEP インターフェース: …」.

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
  [oep-if-link](interfaces/oep-if-link.md)): op 0x01 source `length(u32)` → `len(u16), data`, op 0x02 sink `count(u16), data` → empty, op 0x03 port_speed
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
- fn 0 describe restart_max_ms (tag 0x4F, u32, required when restart is in ops, at least `restart_after_answer_ms`): the longest time from
  restart's answer until the probe answers confirm again on the same transport (re-enumeration or listening again included). The host
  reopens and confirms until then (counted from the answer, or from the end of its wait when none came) and otherwise treats the probe as
  gone. A relaying broker forwards a client's restart under its own session; after the success answer it returns a raised port_speed to
  the boot speed, confirms until a new boot_id answers within restart_max_ms, then opens a new session; the clients' sessions end, and
  client requests meanwhile get no_session (session_id other than 0, not open) or result_lost (open, session_id 0, confirm included);
  a broker whose transport to the probe goes away ends and closes its clients (core §1.2, §4.3, §6.6, §7.5; transports §1). Conformance
  and the host guide §5.2 follow; the vector test checks restart_max_ms against ops.

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
- port_speed's default ceiling (ja, user decision agreed with ch32rv): by default a host does not try rates above 500000 bps; a faster
  rate is tried only when the user explicitly chose it (a command argument, a setting), and is committed only after, in the try state,
  oep.probe.link source (length ≥ max_frame − 26) and sink (count max_frame − 26) each ran for at least 1 s at the in-flight count the
  host will use, back to back; verify_ms covers that verify; once committed, the in-use rule that drops a rate that breaks still applies
  (link §3 host obligation 7; the old obligation 7 is 8; the terms no longer say the specification sets no default). No probe change.
  Reason (host guide §17.5, record uart-speed-negotiation §12): on one bridge, 921600 passed a full-frame verify (16 frames each of in,
  out and both at once, at most 5 % broken) and still broke 1-4 max_frame answers in every 9 KiB upload, once falling back to the boot
  speed mid-upload; 500000 was clean on both bridges measured. Host guide §17: the default candidate is 500000 for every use (the table
  in §17.3.1), the minimal form is for rates up to 500000 only, new §17.3.3 gives the 1 s verify (verify_ms 4000 for in and out, 6000
  with both at once, lease − 1000 or less), a record never adds a faster rate the user did not choose and never skips the 1 s verify,
  §17.5 names no chips; conformance's host checklist follows.

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
