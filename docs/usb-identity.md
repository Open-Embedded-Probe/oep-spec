# USB identification (how an OEP probe is told apart)

[日本語](usb-identity.ja.md)

Status: **guide** (not normative; the rules are core §3.3 and §7.5). Revised 2026-10-06. The project's USB VID:PID is `1209:4F45`
(VID 0x1209, PID 0x4F45; the registry's `usb`), and **a host identifies an OEP probe automatically only by it**; iProduct and the interface
class / subclass / protocol are not used for identification, since they can match other products by chance. This page describes the reference
firmware's USB shape and how a host finds and remembers a probe. The rules for using the project's VID:PID are in oep-probe-arduino's
[PID-USE.md](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/PID-USE.md). This English text is authoritative; the Japanese
version is its translation.

## 1. What a USB ID tells

A USB VID:PID tells only "this is an OEP probe" (so that a host's discovery can build its list without opening every port). What the probe can do
(interfaces, pins, limits, transports) is read after opening a port, with confirm / list / describe (core §7). A VID:PID is never used as a table
of functions.

## 2. The reference firmware and hosts

- The project's USB VID:PID is `1209:4F45` (the registry's `usb`: `project_vid` / `project_pid`).
- The reference firmware (OpenEmbeddedProbe) enumerates the ports whose USB device it provides itself (the high-speed port of the ESP32-P4
  build, the USB of RP2040 / RP2350) with `1209:4F45`. Their serial number is the unit_id (core §7.5: the chip's unique number in lowercase hex).
- A host identifies an unknown device automatically as an OEP probe **only when it enumerates with the project's USB VID:PID** (core §3.3).
- The reference firmware's iProduct is `OEP probe (ESP32-P4)`, `OEP probe (RP2040)` and so on. iProduct is a name for people; nothing identifies
  a probe by it.
- A probe the user names by its unit_id (`oep://<unit_id>`) is found by opening the device whose serial number equals it, and checked with
  confirm and the unit_id of describe (core §3.3).
- Inside a device known to be an OEP probe, the ports are chosen by the interface descriptors (every CDC is a serial port; the bulk pair of class
  0xFF / subclass 0x4F / protocol 0x45; the HID with usage page 0xFF4F / usage 0x45; the registry's `usb`). Interface strings are for display only.
- When a host remembers a probe (an IDE, a sketch.yaml, a bench configuration), it remembers the unit_id (= the USB serial number), not the
  VID:PID or the port name.
- `discoverable = 1` in fn 0's describe (0x4A) means "this probe also enumerates with the project's USB VID:PID" (so that a host that opened it
  through another port, such as a built-in USB serial port, can tell). The reference firmware sends 1 when it has a port that enumerates with it.
- Ports whose VID:PID and serial number the probe cannot choose (a USB-UART bridge, a built-in USB serial whose descriptors the hardware fixes)
  do not enumerate with the project's VID:PID. The user chooses the port; after the confirm, the describe of fn 0 gives the probe's unit_id.

## 3. Handling VID:PIDs

- **A host's automatic identification uses only the project's VID:PID** (core §3.3). An independent implementation with its own VID:PID is opened
  when the user names it or chooses its port (a host may also support it individually). Who may use the project's VID:PID: PID-USE.md.
- Places that grant access by VID:PID (Linux udev rules, a usbipd bind for WSL) are written for `1209:4F45`. A particular probe is found by its
  serial number (unit_id).
