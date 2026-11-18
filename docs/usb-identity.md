# USB identity (how OEP probes are recognized)

[日本語](usb-identity.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative; the normative text is transports §3 and core §7.5). The project's USB VID:PID is `1209:4F45`
(VID 0x1209, PID 0x4F45; registry `usb`), and **a host recognizes OEP probes automatically by that alone**. iProduct and the interface
class / subclass / protocol can coincide with other products by chance, so they are not used for recognition. This page collects how a host finds and remembers probes. The rules for using the project's VID:PID are in oep-probe-arduino's
[PID-USE.md](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/PID-USE.md).

## 1. What the ID recognizes

The USB VID:PID recognizes only "is it an OEP probe" (so that host discovery can make a list without opening every port).
What it can do (interfaces, pins, limits, transports) is read by opening the port, with confirm / list / describe (core §7). The VID:PID is not made into a table
of functions.

## 2. How a host handles it

- The project's USB VID:PID is `1209:4F45` (`project_vid` / `project_pid` of registry `usb`).
- A host automatically recognizes an unknown device as an OEP probe only for **devices that enumerate with the project's USB VID:PID** (transports §3).
- iProduct is a name for people; a host does not use it to decide whether something is a probe or to choose functions.
- A probe the user named by unit_id (address `oep://<unit_id>`, [host development guide](host-development-guide.md) §5.3) is checked by opening the device with the same serial number and comparing the unit_id of confirm and describe
  (transports §3).
- The ports within a device are chosen by interface descriptors within a device known to be OEP (every CDC is a serial port; the bulk pair of class 0xFF / subclass 0x4F /
  protocol 0x45; HID with usage page 0xFF4F / usage 0x45; registry `usb`). Interface strings are for display only.
- When a host remembers a probe (IDE, sketch.yaml, bench settings), it remembers it by unit_id (= USB serial number), not by VID:PID or port name.
- Ports for which the probe cannot choose the VID:PID and serial number (a USB-UART bridge, a built-in USB serial whose descriptors the hardware decides)
  do not enumerate with the project's VID:PID. The user chooses the port, and after confirm, the fn 0 describe returns the probe's unit_id.

## 3. Handling of VID:PID

- **A host's automatic recognition uses only the project's VID:PID** (transports §3). For a separate independent implementation with its own VID:PID, the user names it or chooses the
  port (a host may also support it individually). How far the project's VID:PID may be used is in PID-USE.md.
- Places that grant permissions by VID:PID (Linux udev rules, usbipd bind for WSL) are written with `1209:4F45`. Individual probes are looked up by serial
  number (unit_id).
