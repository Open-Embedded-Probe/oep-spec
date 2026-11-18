# OEP interfaces

[日本語](README.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative). A list of the documents of the interfaces whose names start with `oep.`. The normative text is in each document; the core is [OEP core](../docs/oep-core.md) and
[OEP transports](../docs/oep-transports.md). The only definition of the numbers is [`registry/oep-v1.toml`](../registry/oep-v1.toml). Until the freeze, only the Japanese text (`.ja.md`) is maintained.

An interface is a named function defined only with the mechanisms of the core. The ones listed here belong to the project itself and have
short `oep.` names instead of reverse-DNS names (core §12 rule 1). On the protocol they are treated the same as any other interface. A probe puts the ones it has in list, and
a host finds them with list and uses only the ones it needs.

Which family of targets each one is for is in the table at the top of each document and in `target` of the registry (core §12 rule 8).

| Document | Interfaces |
|---|---|
| [Common parts](oep-if-common.md) | positioned stream, debug connection (not interfaces; they apply only to the interfaces that say they use them) |
| [Wires and debug](oep-if-debug.md) | `oep.wire.rvswd`, `oep.wire.swio`, `oep.wire.swd`, `oep.target.riscv-dm`, `oep.target.arm-adi` |
| [Console](oep-if-console.md) | `oep.target.console` (the dmseq framing is in [target-console-dmseq](target-console-dmseq.md)) |
| [fixture](oep-if-fixture.md) | `oep.fixture.gpio`, `oep.fixture.uart`, `oep.fixture.i2c-target`, `oep.fixture.spi-target`, `oep.fixture.i2c-controller`, `oep.fixture.spi-controller`, `oep.fixture.pwm`, `oep.fixture.counter`, `oep.fixture.dac` |
| [Capture](oep-if-capture.md) | `oep.fixture.logic`, `oep.fixture.analog`, `oep.fixture.capture-group` |
| [plan](oep-if-plan.md) | `oep.probe.plan` (the assignment of which channel to use for which role) |
| [Restart](oep-if-restart.md) | `oep.probe.restart` (restart of the probe itself) |
| [Link](oep-if-link.md) | `oep.probe.link` (link test and port_speed) |
| [Memo area](oep-if-memo.md) | `oep.probe.memo` (named data a host keeps on a probe; the probe does not use it) |

How to write an interface (with a reverse-DNS name; anyone can add one) is in core §12.

## Scope adopted by small probes

A probe with only the core and no named function is valid. The minimal examples below are choices for when the function is put in list; the table does not require all functions uniformly.
For the detailed required operations, dependencies and refusals, see each normative document. Optional ops are declared in ops, and abilities other than ops by the definitions of each describe.

| Function | Example of a small configuration | Not required uniformly |
|---|---|---|
| plan | assign and release the pins of the chosen fn | adoption of plan by other extensions |
| GPIO | set/read, input mode 0 | output modes |
| UART | configure/read/status, RX only from an explicit configure | marks/clear/mark/write, TX queue, implicit initialization to a default baud |
| I2C target | one 7 bit address, small frame/queue | stretch, internal pull-up, nack_from, the receive timestamp TLV |
| SPI target | one supported mode, one arm, small frame/queue | all modes, LSB first, receive timestamp, simultaneous use with all fns |
| capture | 1 track / 1 role / one-shot mode 1, immediate trigger, polling | query/force/calibration/notifications/group, release when mode 2 is not adopted, the remaining modes. A probe that chooses another mode meets the contract of that mode |
| capture-group | declare only the needed tracks and handle the group with bind/start/stop/status | notifications, all combinations of tracks, the event source (the trigger expression, capture §4.4, features bit 0) and force |
| wire | attach method 0/detach/connections, 1 connection | scan, multiple connections, console, RISC-V attach method 1 |
| RISC-V target | dmi only | halt/resume/reset/block/run/step, chip-specific flash procedures |
| ARM target | transfer only | read_block/write_block |
| console | open/read/close/streams, 1 connection / 1 stream, only the supported mechanisms | marks/clear/mark/write, send queue, all mechanisms |
| settings (core §13) | only the supported items, settings in RAM | save/state, non-volatile area, network items and network, interface items |
| link / restart / memo | adopted only when provided | uniform adoption into the core, port_speed of link |

Finite buffers, resource IDs not reused within the same boot, and release at the end of a session are common contracts of the core.
Check separately the number of requests that fit in a frame and the size of the success answers needed. For example, the analog description of capture grows with the number of roles, and some configurations do not fit in the minimum of 64 bytes.
In that case, do not leave out important results; choose the needed max_frame, or refuse unsupported requests before execution.
