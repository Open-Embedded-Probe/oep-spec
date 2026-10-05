# USB identification (how an OEP probe is told apart)

[日本語](usb-identity.ja.md)

Status: **guide** (not normative; the rules are core §3.3 and §7.5). 2026-09-30, revised 2026-10-02: names and vendor-class values can collide with
other products by chance, so **the normative rule identifies an OEP probe automatically only by the project's USB VID:PID**; iProduct and the
interface subclass / protocol are not used for identification. This page describes the reference firmware's current USB shape and how a host
finds and remembers a probe. The rules for using the project's PID are in oep-probe-arduino's
[PID-USE.md](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/PID-USE.md). This English text is authoritative; the Japanese
version is its translation.

## 1. What a USB ID tells

A USB VID:PID tells only "this is an OEP probe" (so that a host's discovery can build its list without opening every port). What the probe can do
(interfaces, pins, limits, transports) is read after opening a port, with confirm / list / describe (core §7). A VID:PID is never used as a table
of functions.

## 2. The reference firmware and hosts

- The reference firmware (the high-speed port of the OpenEmbeddedProbe P4 build) enumerates as `303a:0002` (the default of arduino-esp32's
  TinyUSB). It currently runs with this temporary USB ID (the board's default VID:PID), which may not be used for distribution. Its serial number
  is the unit_id (core §7.5: the chip's unique number in lowercase hex; until 2026-09-30 it was `<MAC>-hs`).
- A host identifies an unknown device automatically as an OEP probe **only when it has the project's USB VID:PID** (core §3.3). That VID:PID is
  listed in the registry when it is obtained; until then no device is identified automatically by the normative rule.
- The interim clues until then (iProduct starting with `OEP`, an interface with class 0xFF / subclass 0x4F / protocol 0x45, a HID with usage page
  0xFF4F) are in the [host development guide](host-development-guide.md) §4. They are not part of the specification, and a candidate is always
  checked with confirm only (the probing rule of core §3.3). The reference firmware's iProduct is `OEP probe (ESP32-P4)`, `OEP probe (RP2040)`
  and so on; iProduct is free text for display.
- A probe the user names by its unit_id (`oep://<unit_id>`) is found by opening the device whose serial number equals it, and checked with the
  unit_id of confirm and describe (core §3.3).
- Inside a device known to be an OEP probe, the ports are chosen by the interface descriptors (every CDC is a serial port; the bulk pair of class
  0xFF / subclass 0x4F / protocol 0x45; the HID with usage page 0xFF4F / usage 0x45; the registry's `usb`). Interface strings are for display only.
- When a host remembers a probe (an IDE, a sketch.yaml, a bench configuration), it remembers the unit_id (= the USB serial number), not the
  VID:PID. If the firmware's VID:PID changes, what was remembered still works.
- `discoverable = 1` in fn 0's describe (0x4A; formerly `oep_pid`) means "this probe also enumerates with the project's USB VID:PID" (so that a host
  that opened it through another port, such as a built-in USB serial port, can tell). Until the project's VID:PID is in the registry, every probe
  sends 0.
- On ports whose serial number cannot be chosen (built-in USB serial, USB-UART converters), the user chooses the port.

## 3. Handling VID:PIDs

- **A host's automatic identification uses only the project's VID:PID** (core §3.3). The reference firmware's current VID:PID is the board's default,
  and hosts do not use it for identification. An independent implementation with its own VID:PID is opened when the user names it or chooses its
  port (a host may also support it individually).
- Changing the firmware's VID:PID does not change settings remembered by unit_id. Places that hard-code a VID:PID (a bench's usbipd bind, the
  default of a flashing tool) are changed to look by serial number (unit_id).
