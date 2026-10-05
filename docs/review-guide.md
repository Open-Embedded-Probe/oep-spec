# Open Embedded Probe — review guide (what is written where)

[日本語](review-guide.ja.md)

Status: **guide** (not normative). A map as of 2026-10-02 (before the v1 freeze. After the decisions before the freeze and the zero-base re-examination were put into the normative text, and the remaining numbers were filled in). For someone who does not yet know OEP
and reviews the v1 freeze, this summarises where to start reading, what is at which PATH, and what we would like looked at. PATHs are relative to the root of each repository.

## 1. What OEP is

A protocol that exposes, with common meanings, the functions provided by probes for embedded development (debuggers, logic analysers, fixtures), and its
implementations. It aims for different probe implementations and different host software to be usable with each other.

- **probe**: a device connected to a PC over USB etc. (the reference implementation is an Arduino library and sketches). It has its own pins (fixture) and debug wires to the target
  (RVSWD, SWIO, SWD).
- **host**: software on the PC side (the Python client, the flashing tool ch32rv, etc.).
- **target**: the microcontroller under development.

Principle of the division of roles: **the host holds the knowledge of the target**. The probe knows only the wires and DMI (RISC-V Debug Module Interface) / DP·AP transfers, and
how to write flash and chip-specific procedures are in the host.

## 2. Current state

- It is **a candidate for the v1 freeze**. The normative text is `docs/oep-core.md`, `docs/oep-if-*.md` (6 of them), `docs/target-console-dmseq.md`, and the numbers are `registry/oep-v1.toml`.
  No undecided numbers (the "to be decided" mark) remain in the normative text. What the freeze stops and what it does not is in [versioning](versioning.md) (the record of the decision: [the scope of the freeze](v1-freeze-decisions.md) §0); the changes are in [CHANGELOG](../CHANGELOG.md).
- Until the freeze, breaking changes go in without raising the revision (there are no users yet). After the freeze, the revision is raised.
- **Releases**: oep-spec is pushed to main on GitHub (there are no tags. It is pointed to by commit). The reference implementations are oep-probe-arduino **0.0.27** (Arduino library
  `OpenEmbeddedProbe`, firmware per profile in the GitHub release) and oep-client-python **0.0.27** (PyPI `oep-client-python`). oep-client-js is
  unpublished (not on npm. Only tests against the fake). Firmware and client are paired by the same minor version.
- What **the tests on real hardware** ([release-testing](release-testing.ja.md) (Japanese), oep-client-python `tests/hw/`) cover: flashing, confirm / list / describe, `oep.probe.config`
  set / get / save / reboot / unset (including disable), wires (scan, attach, the round trip halt → dmi → read_block → resume. Only boards with a target connected),
  gpio, fixture uart, port_speed (only UART bridge boards), lease expiry / expired / force. The results are JSON in `tests/hw/results/`.
  **Not covered**: console (dmseq), capture (logic / analog / capture-group), i2c-target / spi-target, notifications, the HID path, simultaneous use of several
  paths, TCP. For these there are only the tests against the fake (`uv run pytest`, 247 cases) and manual checks.
- The way of deciding is "experiment and prototype first, then fix the specification with the results". Experiment numbers and dates are kept in **record documents**, and are not placed in the normative text
  (the normative text has no chip names, board names or dates, and its numbers are values, not guides).
- **The English text is normative.** The Japanese documents (`.ja.md`) are translations; where the two differ, the English text is right. Every normative document and every guide except release-testing has an English version; most records are Japanese only.
- **Changes**: this repository is the source of truth. How rule changes, wording changes, new `oep.` names and registry values, and errata are made is in [CONTRIBUTING](../CONTRIBUTING.md).

## 3. The shortest reading order (review of the v1 freeze)

| Order | PATH (oep-spec) | What it tells you |
|---:|---|---|
| 1 | `docs/project-concept.md` | Purpose and scope (the upstream agreement). Short |
| 2 | `docs/versioning.md`, `docs/v1-freeze-decisions.md` §0.3 | **The scope of the freeze**: what is stopped, what is free, the paths for extension, what a revision bump means; what is fixed on purpose and the reasons (§0.3) |
| 3 | `docs/oep-core.md` | **The core (normative)**. §0 layers and the rules for drawing lines, §2 common rules (TLV, unknown values, number spaces, revision), §3 transports and frames, §4 messages and reject reasons (**the order of refusals** in §4.3), §5 recovery and resend, §6 sessions, §7 discovery (confirm / list / describe), §8 plan, §9 lifetime of resources, §10 long operations (reserved), §11 notifications, §12 core ops, §13 how to write an interface. **§3.5 (serial port speed) is the handshake only**: how to choose candidates, checking, and judging during use are the reference procedure of `host-development-guide` §7 |
| 4 | `docs/oep-if-common.md` | The common parts of the standard interfaces (positioned streams, debug connections, the status of wire and target operations) |
| 5 | `docs/oep-if-debug.md`, `docs/oep-if-console.md`, `docs/oep-if-fixture.md`, `docs/oep-if-capture.md`, `docs/oep-if-probe-config.md` | The standard interfaces (normative): wires and RISC-V DM / ARM ADI, the target console, GPIO / UART / I2C·SPI targets, logic / analog capture and groups, probe settings (slots, bind, disable) |
| 6 | `docs/target-console-dmseq.md` | The console framing (dmseq): carried in both directions through the data registers of the debug module, with sequence numbers and CRC (normative for target and host) |
| 7 | `registry/oep-v1.toml` | The only definition of numbers and values. `timing` / `limits` are the numbers of the normative text (subject to the freeze) |
| 8 | `docs/v1-zero-base-proposal.ja.md` §1, §4, `docs/v1-zero-base-review-2026-10-02.ja.md` | The **8 principles** used for judgement, the places intentionally not extended, the second check (★ fixed, ☆ kept fixed) |
| 9 | `docs/getting-started.md`, `docs/host-development-guide.md`, `docs/probe-development-guide.md`, `docs/security.md`, `docs/glossary.md` | Practice (not normative): the smallest probe and host with bytes; how to send frames, recovery, refusals, notifications, probe settings, handling of USB-UART, **host guide §17 how to choose the serial port speed** (17.1 balance, 17.2 the minimal form, 17.3 the form that adds checks per use, 17.4 records, 17.5 measurements); identifiers and declarations (probe guide §10); security and safety in one place; terms |
| 10 | `docs/link-measurements.ja.md`, `docs/uart-speed-negotiation.ja.md`, `docs/logic-capture.ja.md` | **Records** (not normative): measurements of USB and serial paths, the experiments and history of UART speed, the design and measurements of capture. Where the reference numbers come from |
| 11 | `docs/release-testing.ja.md` | Tests on real hardware before a release: who owns them, what they check |
| 12 | `docs/session-and-exclusivity.ja.md`, `docs/capability-*.ja.md` (3 of them), `docs/console-stream.ja.md`, `docs/target-connection-use-cases.ja.md`, `docs/probe-cdc-and-persistence.ja.md` | Reasons for decisions (sessions and the lock, finding by name, the vocabulary of describe, streams, target discovery, sharing serial ports and saving settings) |
| — | `docs/usb-identity.md` | USB identification (the reasons behind core §3.3) |
| 13 | `docs/v1-open-proposals.ja.md`, `docs/v1-freeze-review-2026-10-01.ja.md`, `docs/review-response-2026-09-26.ja.md`, `docs/review-answer-*.ja.md` | Proposals and the history of decisions, the full review before the freeze (59 items, addressed), the response table to the previous third-party review |
| — | `docs/hardware-source-review-2026-09-26.ja.md`, `docs/v1-operation-test-audit-2026-09-26.ja.md`, `docs/v1-open-issues-research-2026-09-26.ja.md` | The second review of the 2026-09-26 version, and preliminary research on open issues (IP, recovery). There is no per-item response table (items overlapping the review before the freeze were handled there. IP and recovery are outside v1) |
| — | `docs/v1-core-wire-delta.ja.md` | The delta from v0 before the split (history) |

## 4. Viewpoints we would like the review to take

1. **Can it be built from the normative sentences alone?** Reading only the core, `oep-if-*` and the registry, can one write a host (or a probe)? Please point out what is missing, what
   cannot be decided without reading the guides or records, and where it escapes with "guide" or "etc.". If a number disagrees between the normative text and the registry, the registry is wrong.
2. **Is the reason for a refusal determined uniquely?** When "the order of refusals" of core §4.3 (header → resend → session → window → malformed → unsupported →
   unavailable → no_connection) is applied to the ops of each interface, does any place remain where two reasons can be produced for the same situation?
3. **Do the reasons for what is fixed on purpose hold?** The table of [the scope of the freeze](v1-freeze-decisions.md) §0.3 (frame headers, u8 op / tag, no len in sequences in requests,
   not adding the host's limit to confirm, the probe not declaring speed candidates, etc.). If there is a use that breaks a reason, that is a candidate to fix before the freeze.
4. **Is there anything contrary to the 8 principles?** [Zero-base re-examination](v1-zero-base-proposal.ja.md) (Japanese) §1: a container knows its own length, there is one way to extend, requests fit the probe and
   answers fit the host, values of hardware properties are u32, declaration and state are not mixed, invariants over mechanisms, one identifier and one clock each, one order of refusals.
5. **Places where the source of the reference numbers is narrow.** The numbers of `host-development-guide` §17 (5 %, 10 %, 16 frames, 3 seconds, 60 frames) and the conclusions of `link-measurements`
   come, for UART bridges, from measurements of **2 kinds of conversion chips (CH340, and a CH552 that claims FTDI compatibility)**, and for USB, from 2 families of MCUs. Measurements with other bridges
   (genuine FTDI, CP210x, CDC MCUs) and on native OSes are welcome. The normative text does not depend on these numbers (handshake only), so they do not hold up the freeze.

## 5. oep-spec (specification, number tables, experiments)

### 5.1 State of the documents

| State | PATH (`docs/`) |
|---|---|
| **Normative** | `oep-core`, `oep-if-*` (6 of them), `target-console-dmseq` |
| **Guide** (not normative) | `review-guide`, `getting-started`, `conformance`, `project-concept`, `host-development-guide`, `probe-development-guide`, `security`, `glossary`, `versioning`, `release-testing`, `usb-identity`, `development-guidelines`; `CHANGELOG.md` at the root |
| **Record**: scope of the freeze and decisions | `v1-freeze-decisions` (§0 scope, the 13 items of §A / §B), `v1-zero-base-proposal`, `v1-zero-base-review-2026-10-02`, `v1-zero-base-review-3-2026-10-02`, `v1-freeze-review-2026-10-01` (addressed) |
| **Record**: measurements (appending is free) | `link-measurements`, `target-scan-notes` (scan and attach per target), `implementation-notes` (chip-specific stories and measurements moved out of the guides), `uart-speed-negotiation`, `logic-capture` (§7 onwards), `probe-cdc-and-persistence` §7, `target-console-dmseq-notes` |
| **Record**: reasons for v1 | `session-and-exclusivity`, `capability-*` (3 of them), `console-stream`, `target-connection-use-cases`, `probe-cdc-and-persistence` |
| **Record**: proposals and history, responses to reviews | `v1-open-proposals`, `review-response-2026-09-26`, `review-answer-*` (3 of them), `hardware-source-review-2026-09-26`, `v1-operation-test-audit-2026-09-26`, `v1-open-issues-research-2026-09-26`, `v1-core-wire-delta` |
| **Record**: upstream inputs before v1 (requirements, model) | `use-cases`, `project-requirements`, `conceptual-model`, `responsibility-boundaries` |
| **Record**: comparisons and candidates of designs before v0 | `common-protocol-behavior`, `information-model`, `interaction-patterns`, `message-model-candidates`, `message-routing-model`, `message-header-layout-comparison`, `request-correlation-lifecycle`, `implicit-correlation-comparison`, `correlation-width-comparison`, `correlation-retirement-model`, `request-completion-semantics`, `activity-reference-lifecycle`, `connection-binding-design-inputs`, `minimal-connection-channel`, `bootstrap-*` (3 of them), `uart-*` (5 of them, excluding `uart-speed-negotiation`) |
| **Record**: v0 (replaced by v1) | `v0-core-wire-model`, `v003-destructive-prototype` |
| **Record**: survey | `capture-survey` (desk survey of sigrok and commercial logic analysers) |

### 5.2 Number tables and generation

| PATH | Contents |
|---|---|
| `registry/oep-v1.toml` | **The only definition of all numeric values on the v1 wire** (op, TLV tag, reject reason, status, enum, timing, limits, USB identification, the names and revisions of interfaces) |
| `tools/oepgen1.py` | Generates a C++ header, a C header and Python and JS modules from the registry, and checks the rules for numbers (core §2). `python3 tools/oepgen1.py --check` verifies they are in sync |
| `generated/oep-v1/oep_v1_registry.{h,py,js}`, `oep_v1_registry_c.h` | Generated files (the C header has the same values as `#define` macros). The probe and the client copy and use them (`OepRegistry.h`, `oep_client/registry.py`) |
| `tests/registry_v1/` | Tests of the registry and the generated files (`cd tests && uv run pytest registry_v1`) |

### 5.3 Others

| PATH | Contents |
|---|---|
| `experiments/*/README.ja.md` | Non-normative comparison implementations and records of experiments (flash-primitives, dm-console-seq, v003-reset-flags, session-id-cost, and before v0 bootstrap-layout / message-routing / uart-binding) |
| `tests/` | The verification environment for the experimental implementations (`tests/README.ja.md`) |
| `memo.ja.md` | Notes on research and migration, a copy of the user's notes (working file) |
| `README.md` | What OEP is, its status, the map of the documents, how to start, contributing and the license |
| `CONTRIBUTING.md` | The change process |

## 6. oep-probe-arduino (probe implementation, Arduino library, 0.0.27)

`README.ja.md` has the structure and usage, and `CHANGELOG.md` the changes per version. The comment at the top of each file states the corresponding sections of the specification.

| PATH | Contents |
|---|---|
| `src/Oep.h`, `src/OepResult.h` | Parts of the core (the Interface base, TLV, describe, parsing of the tail, results) |
| `src/OepEndpoint.*` | The frame receiver, sharing the serial port (core §3.4) and port_speed (§3.5), finding interfaces by name, the session lock, notifications, plan, several transports |
| `src/OepBind.*`, `src/OepStream.h` | What is sent to serial ports (bind), positioned streams |
| `src/OepRegistry.h` | A copy of the generated files of oep-spec |
| `src/OepTarget.*`, `src/OepSwd.*`, `src/OepDebug.h` | `oep.wire.rvswd` / `oep.wire.swio` / `oep.wire.swd`, `oep.target.riscv-dm` / `oep.target.arm-adi`, common parts |
| `src/OepConsole.*`, `src/OepDmConsole.*` | `oep.target.console` and framings (dmseq and others) |
| `src/OepFixture.*`, `src/OepP4I2cTarget.*`, `src/OepP4SpiTarget.*` | `oep.fixture.gpio` / `uart` / `i2c-target` / `spi-target` |
| `src/OepCapture.*`, `src/OepAnalog.*`, `src/OepCaptureGroup.*`, `src/OepSampler.*`, `src/OepDirectBulkStream.h` | `oep.fixture.logic` / `analog` / `capture-group`, the sampler, zero-copy bulk transfer |
| `src/OepConfig.*` | `oep.probe.config` (slots, bind, disable, saving) |
| `src/OepCh32Dm.*`, `src/OepDmiPhy.h`, `src/Oep*Phy.*`, `src/Oep*Frame.h`, `src/OepRp2BitBang.h` | DM operations and the physical layer of the wires (bit-bang) |
| `src/OepFrame.*`, `src/OepPlatform.h`, `src/OepPinTable.h` | Frames, differences between Arduino cores, the pin table and the idle / disabled states |
| `examples/Firmware/OepProbe/` | One firmware per chip (per profile). All pins are chosen by the host, and fixtures are expressed by settings. This is the release image |
| `examples/01.Basics/` to `06.Settings/`, `examples/Tools/` | Examples for learning (Minimal / Fixture / CustomInterface / MultipleTransports / Rvswd·Swio·Swd / LogicCapture / ProbeConfig) and bring-up tools |

## 7. oep-client-python (host implementation, Python, 0.0.27)

| PATH | Contents |
|---|---|
| `README.ja.md` | The list of public modules and usage |
| `src/oep_client/host.py` | Session rules, requests and results, the error hierarchy, pipeline, waiting times |
| `src/oep_client/link.py`, `frames.py`, `cobs.py`, `usb_stream.py`, `hid_stream.py` | transports (serial, USB vendor bulk, vendor HID), frames, COBS + CRC, recovery |
| `src/oep_client/message.py`, `registry.py` | The form of messages, a copy of the number tables of oep-spec |
| `src/oep_client/core.py`, `catalog.py`, `names.py`, `interfaces.py`, `dump.py` | Finding by name, describe, plan, display |
| `src/oep_client/riscv.py`, `arm.py`, `console.py`, `fixture.py`, `capture.py`, `config.py` | Clients per interface |
| `src/oep_client/linktest.py`, `speed_record.py` | Wire tests (the link_source / link_sink matrix) and speed records (the form of host guide §17.4) |
| `src/oep_client/ch32_flash.py`, `rp2350.py`, `uiapduino.py` | Target knowledge (actual examples of the division of roles in which the host holds it) |
| `src/oep_client/fake.py`, `fake_capture.py`, `endpoint.py`, `fake_serial.py`, `fake_serve.py` | A false probe without hardware (a working spec. `python -m oep_client.fake_serve` exposes it on a pty / TCP) |
| `tests/test_*.py` | Tests without hardware (`uv run pytest`, 247 cases) |
| `tests/hw/` | Tests on real hardware (§2). `README.ja.md` has what each test checks and how to flash each board |

## 8. Surrounding repositories (reference)

| PATH | Contents |
|---|---|
| oep-client-js | The JS client (unpublished). Tests against the fake, and manual checks in a browser |
| ArduinoCore-CH32RV `tests/manual/oep_smoke/`, `libraries/SerialDMSeq/` | Regression on real hardware (flashing with an OEP probe, judging with the console), dmseq on the target side |
| wch-protocols (`experiments/`, `protocols/`, `captures/`) | Records of observations on the wire of existing probes. The source of facts for the design of OEP (referred to by experiment numbers E1xx) |

## 9. Terms

| Term | Meaning |
|---|---|
| interface / fn | A function a probe exposes by name (`oep.wire.rvswd`, etc.) and its number (fn. Found with list) |
| describe | What an interface uses to state its capabilities in TLVs (declaration only. State is in other ops) |
| session / lock / lease | The right to send requests. One host holds the lock, and extends the lease (expiry) with keepalive |
| connection | A debug connection to a target. Closed when nothing uses it any more. The numbers are one space per probe (core §9) |
| plan | The assignment of which of the probe's pins are used for which role of which interface |
| slot / bind / disable | Items of `oep.probe.config`: a saved plan, what is sent to a serial port, channels the probe does not touch |
| port_speed | A handshake that raises the speed of a UART bridge only during a session (core §3.5) |
| TLV | tag(u8), length(u8), value. critical applies only to TLVs in requests. Unknown values are treated as failure |
| dmseq | A framing that carries the target's console through DATA0 / DATA1 of the debug module, with sequence numbers and CRC |

## 10. Notes for reading

- The normative text consists of sentences of the form "does ..." / "does not ...", and numbers are values (not guides). Experiment numbers (X1 to X6, P1 to P7, E1xx), dates, and chip and board names are in the record documents.
- What is written as "unsettled" or "unconfirmed" has not been checked yet.
- The same thing is sometimes written in an older form in other documents (the comparison documents before v0, `v1-core-wire-delta.ja.md`, etc.). In v1,
  the English `oep-core.md` and `oep-if-*.md` are right (the Japanese `.ja.md` is their translation), and for numbers `registry/oep-v1.toml` is right.
- To check the behaviour of the implementations, the quickest is to look at `src/Oep*.cpp` for the probe and `src/oep_client/` for the client. In both,
  the comment at the top states the corresponding sections of the specification.
