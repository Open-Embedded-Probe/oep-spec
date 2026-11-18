# OEP interface: restart v1

[日本語](oep-if-restart.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **normative** (v1). For the freeze state and the language and compatibility policy, see [Versions and stability](../docs/versioning.md). The core is [OEP core](../docs/oep-core.md). The only definition of the numbers is `registry/oep-v1.toml`.

| Name | revision | Role | Target family |
|---|---:|---|---|
| `oep.probe.restart` | 1 | starts the probe itself again | used for every family |

- It lets a host recover a probe that got into a bad state without unplugging and replugging it.
- `oep.probe.restart` is an optional interface. A probe puts at most one `oep.probe.restart` in list.

## 1. Operations

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x10 | restart | [TLV] | — (no fixed part. The probe restarts after the answer) | needed | required |

describe (in addition to the common tags of core §7.4):

| tag | Name | Value |
|---:|---|---|
| 0x40 | restart_max_ms | u32. **Required**. Upper limit (ms) from the moment the answer leaves the transport until the restart and initialization inside the probe are done and the probe is in the internal state where it can receive messages on the original transport. Includes preparing USB descriptors/endpoints and preparing the network stack/listening. Does not include the time spent waiting for OS enumeration, network connection/IP acquisition, or the host's reconnection and sending of confirm |

## 2. restart

- **The lock is needed** (core §6.3). restart defines no request TLV (request TLVs are as in core §2.3).
- **Answer first**: the probe answers an accepted restart with completed success (no payload). restart does not return completed failed / partial.
- **After the answer**: after sending that answer and until it restarts, the probe answers no request on any transport (including requests that came after the restart on the same transport) and sends no notification.
- **target**: the restart procedure does not intentionally reset/resume the target. During the restart, pins can be in the reset state of the MCU.
  Changes of the target caused by external pulls or power/reset wiring are not guaranteed against.
- **After the restart**, as far as OEP is concerned, it is the same as a start at power-on: boot_id is a new value (core §6.5), and nothing of the previous boot remains (the row
  "restart of the probe" in core §9). The speed of a serial port is the boot speed ([transports](../docs/oep-transports.md) §4).
- **Transport**: during the restart the probe does not answer on its transports. On a USB transport the device MAY leave the bus and enumerate again, and a TCP connection MAY be closed.
- **Internal recovery**: the probe reaches the internal state above within restart_max_ms. The
  confirm answer after the external transport becomes usable and receives a request follows the waiting rules of core §4.4. The host decides its own deadline for opening again.

How a host waits and opens again is in the [host development guide](../docs/host-development-guide.md) §5.2.
