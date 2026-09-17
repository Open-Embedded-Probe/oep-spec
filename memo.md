# Research and Transition Memo

[日本語](memo.ja.md)

Status: **Informative working memo.** This file records the background used to start the OEP specification project. It is not normative and may be reorganized or removed after its decisions are incorporated into specifications and issue tracking.

## Origin

OEP was separated from the broader [wch-protocols](https://github.com/ch32-riscv-ug/wch-protocols) research repository. That repository remains the evidence base for MCU protocol research, USB and operating-system experiments, ESP32-P4 capture measurements, and early product-design discussions.

The new organization separates the platform-independent contract from implementations:

- `oep-spec`: protocol, registries, conformance rules, and PID policy;
- `oep-probe-arduino`: Arduino firmware implementation and platform backends;
- `oep-client-python`: Python library, CLI, bridges, and initial conformance runner.

The existing research should be distilled, not copied wholesale. Experiment logs and hardware-specific performance reports remain in `wch-protocols`; OEP specifications should cite them when a normative decision depends on evidence.

## Findings carried forward

### Probe implementations are feasible on different MCUs

Existing investigation supports UART, GPIO/reset, SWD, and JTAG on RP2040 and ESP32-S3, with MCU-specific timing backends. The reusable boundary is a batched sequence or transfer engine, not per-bit host round trips and not only `digitalWrite()`-style APIs.

This supports a protocol that standardizes service meaning while allowing PIO, GPIO, SPI, RMT, DMA, or other platform-specific implementations.

### Capability discovery is the product's central mechanism

A probe may be built with only selected services. Numeric performance and configuration limits differ by MCU, firmware build, USB path, and resource allocation. The client must select services from reported capabilities rather than maintain a board-name matrix.

ESP32-P4 logic-capture experiments further show that some configurations cannot be summarized by one maximum sample rate. Channel width, per-channel reduction, encoding cost, USB budget, trigger mode, and resource sharing affect acceptance. The protocol therefore needs both descriptive limits and an explicit configuration query/accept/reject mechanism.

### A common standard service and a specialized service can describe one engine

A logic analyzer can expose a bounded, portable capture service and a richer ESP32-P4-specific mixed-rate service. A client that understands the extension may choose it; another can use the standard service. The declarations need an alternative/shared-resource relationship so they are not incorrectly opened as independent engines.

### USB identity, USB layout, and protocol capability are different concerns

The same protocol can be carried over USB, an existing USB-to-serial bridge, or a network connection. Only a firmware-controlled native USB device needs an OEP USB descriptor profile and PID policy.

Windows 11 observations in experiment E062 corrected an earlier assumption: a successful existing device instance generally follows the current descriptors and can rebind when a device changes between single-function and composite layouts or changes an interface function. `bcdDevice` is not part of the device instance identity and is not a general profile selector. Interface paths and persistent properties still require disciplined profile and interface-number management, and MS OS descriptor registry-property changes require the appropriate vendor revision mechanism.

The design consequence is not that arbitrary layouts are free of compatibility cost. Protocol capabilities may vary freely, while externally visible USB layouts require registered profiles or composition rules.

### PID use needs allocator approval and separate governance

Openmoko and pid.codes were identified as possible MCU-independent OSS PID allocation routes. The intended use is broader than one firmware image: multiple MCU ports and potentially independent conforming implementations would share one project identity. Approval for that exact scope must be obtained before it is promised.

The MIT license does not grant permission to use a project VID:PID. A future `PID-USE.md` must separately define eligibility, identity rules, required source publication, conformance, USB profiles, and handling of non-compliant uses. Implementations must be usable with serial, vendor IDs, or independently assigned IDs without accepting the project PID rules.

### Existing ecosystems should be adapters, not core constraints

CMSIS-DAP, OpenOCD, SUMP, BeagleLogic, sigrok/PulseView, and standard USB classes provide valuable interoperability. Host-side adapters can translate OEP services without forcing every probe firmware or the core wire model to adopt one existing protocol's limitations.

USB Audio, Video, CDC, DFU, or other class functions may project an internal service through an OS standard-class interface. Their descriptor-defined formats and topology belong to USB profile governance, while OEP capability discovery reports the corresponding internal service and resource relationship.

## Corrections to avoid carrying forward

- Do not treat VID:PID as complete feature identification. Confirm OEP through a handshake.
- Do not use `bcdDevice` to distinguish descriptor profiles.
- Do not require every reference probe to implement UART, SWD, and JTAG merely because they were useful feasibility targets.
- Do not define one global command ID space for all future services.
- Do not make use of one firmware library a prerequisite for protocol compatibility or future PID eligibility.
- Do not describe a shared PID as authentication, certification, or a security boundary.
- Do not copy experimental performance values into normative capability limits.

## Open design decisions

The following decisions intentionally remain open:

1. Core message framing and representation.
2. Protocol and service version-negotiation rules.
3. Stable device identity, implementation identity, and USB serial format.
4. Standard service identifier size and private namespace encoding.
5. The minimum capability directory and per-service description model.
6. Shared-resource, exclusivity, and dynamic availability representation.
7. The first control and streaming/batched services used for validation.
8. The first USB bootstrap profile and its discovery method on each OS.
9. USB profile composition rules for optional standard-class functions.
10. Conformance levels and test ownership.
11. The exact PID allocator and approved multi-implementation usage scope.
12. PID authorization, review, and version/profile compatibility policy.

No numeric registry values should be assigned until the relevant namespace and lifecycle rules are agreed.

## Proposed work sequence

1. Agree on terminology, roles, scope, and normative language.
2. Write explicit use cases and failure cases for discovery and capability matching.
3. Define the core state model before selecting a wire encoding.
4. Define service and private-extension identity and versioning.
5. Model two deliberately different probe builds and one client-selection algorithm.
6. Model the portable and ESP32-P4-specific logic-capture services as an extension test case.
7. Select a minimal USB bootstrap profile and validate it on Windows, Linux, and macOS.
8. Publish machine-readable test vectors alongside the first framing draft.
9. Implement the same draft in `oep-probe-arduino` and `oep-client-python`.
10. Add a second implementation ecosystem only when it provides independent evidence rather than another board wrapper.
11. Define conformance claims and draft `PID-USE.md`.
12. Ask the selected allocator to confirm the intended scope before applying for or promising a shared PID.

## Candidate source material

The following files in `wch-protocols` are starting points, not specifications:

- [Probe product concept](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/probe-product-concept.ja.md)
- [Arduino probe protocol feasibility](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/arduino-probe-protocol-feasibility.ja.md)
- [Probe feasibility gates](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/probe-feasibility-gates.ja.md)
- [PID acquisition roadmap](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/pid-acquisition-roadmap.ja.md)
- [Open-source USB PID application report](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/oss-usb-pid-application-report.ja.md)
- [USB host descriptor persistence](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/usb-host-descriptor-persistence.ja.md)
- [E062: USB layout changes with the same identity](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/experiments/e062_usb_same_identity_layout_change/README.ja.md)
- [ESP32-P4 logic analyzer investigation](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/p4-logic-analyzer-investigation.ja.md)
- [ESP32-P4 probe roadmap](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/p4-probe-roadmap.ja.md)
- [PulseView integration](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/pulseview-integration.ja.md)

When a conclusion moves into OEP, its specification should state the resulting rule concisely and link to the evidence rather than reproduce the full investigation history.
