# Open Embedded Probe — transports and frames (OEP transports) v1

[日本語](oep-transports.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **normative** (v1). For the freeze state and the language and compatibility policy, see [versions and stability](versioning.md).
This document defines how OEP messages are carried: transports and their frames, how a host finds and opens a probe's ports (how USB is recognized, how TCP probes are found, the probing rule, how ports are chosen),
several transports of one probe, OEP-only serial ports, resync of length-prefixed frames, the transfer time the host's wait counts, and network settings.
Messages, sessions and the rest are defined by [OEP core](oep-core.md). This document belongs to the core layer, and core conformance (core §1.2) and the protocol
revision (core §7.1) include this document. The only definition of numbers is `registry/oep-v1.toml`.

## 1. Frames

Transports fall into 2 kinds. A **serial port** is a transport the OS sees as a serial device (UART bridge = the probe's
UART brought out through a USB-UART converter chip, USB CDC, built-in USB serial), and carries only OEP frames (§4).
The other transports (USB vendor bulk, HID, TCP) carry only OEP.

| Transport | Frame |
|---|---|
| Serial port (UART bridge, USB CDC, built-in USB serial) | COBS + CRC-16, delimited by 0x00 (below) |
| USB vendor bulk, TCP | `length(u16) message`. No CRC. length 0 is reserved (keepalive; skipped; below) |
| USB HID (vendor-defined report) | Carries the length-prefixed byte stream of vendor bulk in reports: report = `count(u16)`, `first(u16)`, count bytes of that stream, padding (the report size is as in the HID descriptor). Rules below |

- **A frame of length 0** (vendor bulk, TCP): it is not a request, answer or data. The receiver skips it and counts it toward nothing (it does not extend the lease of core §6;
  only requests extend the lease). It MAY be sent in either direction (on USB it can be used to close a transfer; the bundling below).
- **HID reports**: in each direction, reports carry one byte stream. The OS HID driver may discard reports that accumulated unread,
  and the sender may also discard reports it cannot send. first shows the position from which to read the stream anew.
  1. The OEP bytes of a report are the count bytes after count and first. Joined in report order per direction, they make one length-prefixed byte stream,
     the same stream as vendor bulk (`length(u16) message`).
  2. **first** is the position (counted from 0) within those count bytes of the first byte of the length of the first frame that starts in them. A frame of length 0 also counts
     as a frame. If no frame starts in that report, it is `hid_no_frame_start` (0xFFFF). The first of a report with count 0 is also
     `hid_no_frame_start`.
  3. A report with count 0 is empty and is skipped.
  4. The sender makes the padding 0. The receiver ignores the padding regardless of its value.
  5. An OEP HID interface either declares no report ID or declares one report ID used by its input reports and output reports. When it declares one,
     every report in both directions begins with it, and count and first come after it. The receiver discards reports that begin with another ID.
  6. **Reading anew**: the receiver compares the position of the first frame that starts in the report by its own reading with first. If they differ (including when only one of them
     has a start), a report is missing before it: the receiver discards the frame being read and reads anew from that report's first. If first is
     `hid_no_frame_start`, it discards input until the next report that has a first. A receiver whose stream broke (rule 7 below, a length larger than max_frame,
     received bytes it could not store) and a receiver that has just opened the transport also read anew from the next report that has a first. The gap rule of §2 (200 ms) is not applied to the HID stream.
  7. A report whose count is larger than what fits in the report (the report length − 4, − 5 if there is a report ID), and a report whose first is neither `hid_no_frame_start` nor
     smaller than count, is discarded, and the receiver treats the stream as broken.
- **COBS frames**: after the message, CRC-16/CCITT-FALSE (polynomial 0x1021, initial value 0xFFFF, no reflection, "123456789" → 0x29B1) is attached
  in little endian, it is encoded with COBS (the standard form split into 254 byte blocks), and **sent enclosed in 0x00 before and after** (`0x00 <COBS> 0x00`).
  Neither probe nor host omits the leading 0x00. When the last block holds 254 bytes of data (code 0xFF), the encoder does not append an empty block, and the decoder
  accepts both the form with it and the form without it. Empty frames (consecutive 0x00) are skipped.
- **How the host receives (COBS)**: both the part from right after opening the port to the first 0x00, and each part from a 0x00 to the next 0x00, are decoded as frame candidates
  (the leading 0x00 may not arrive because of bytes sent before opening or bytes dropped right after opening). Candidates that do not decode, candidates whose CRC does not match,
  and frames whose role or corr does not match (core §10.1) are discarded as broken candidates.
- **USB bundling** (vendor bulk): if the length of a write is a multiple of wMaxPacketSize, the host follows it with a zero-length transfer. When the probe has finished sending
  and nothing follows, if the last transfer is a multiple of wMaxPacketSize, it sends a zero-length transfer, sends a frame of length 0 (2 bytes, above),
  or splits the last 1 byte into another transfer.
  When a continuation comes right away, staying at a multiple is fine.
- **A length larger than max_frame**: the probe discards that frame and the input until the next pause of `probe_frame_gap_ms`, and waits for the next frame. It sends no answer. On TCP it closes the connection instead. On HID, the discarded range is up to the next report that has a first (rule 6 above).
- Which frame is used is decided only by the kind of transport (not chosen by VID:PID).
- **TCP is used only over a trusted local connection or inside an authenticated tunnel.** OEP has no authentication (including the force of core §6.4).
  When one probe is used by several hosts, a broker bundles them into one session (what the probe rules require of a broker is the next item).
- **An endpoint that answers OEP requests itself is a probe**, regardless of what carries it and what is behind it (for example, a program that offers OEP over TCP and operates another debugger). All probe rules apply to it. A broker that only relays requests to an OEP probe is a host towards that probe.
- **When a broker answers OEP requests itself**, it implements, as an independent OEP endpoint, all of discovery, the declaration of transports, sessions, resending and resource lifetimes.
  Mapping to upstream sessions and resources is done inside the broker. No part of the core is treated as an exception for clients.
- **When a connection to the downstream probe / target side that the broker uses is lost**, the affected resources are invalidated. If the endpoint for clients is regenerated, the boot_id changes.
  When a client-side transport closes, §3 applies, and that alone does not end the session or resources.
- **TCP transport**: a probe that listens on TCP lists one listening socket as one transport in the fn 0 describe (kind 6, interface 0xFF). Every connection accepted on that socket returns that index in the transport TLV of confirm. The rules that §3, core §4.4, core §7.1 and core §10.4 apply per transport (a session's requests on one transport, max_frame / window / max_inflight, the revision in use, the destination of notifications) apply separately to each accepted connection.
  The probe decides the listening port. How a host finds TCP probes is in §3.
  A probe MAY limit the number of concurrent connections, and it MAY be just 1 connection. A new connection beyond the limit is not accepted or is closed.
  For that, existing sessions, resources and connections need not be ended. Merely offering TCP does not require unlimited connections or a thread per connection.

## 2. How frames are sent

- On the same transport, the order of complete messages received is kept in the order sent. Splitting and joining do not change that order.
  Hosts and brokers do not reinject resolved requests later, and do not automatically carry the queue of an old transport over to a new transport (core §4.1, §5.1).
- A frame MAY be split into any number of writes, USB transfers, HID reports or TCP segments, and MAY be combined with other frames in one. The receiver does not rely on those boundaries.
- The sender (host and probe alike), except on TCP, does not pause for `probe_frame_gap_ms` in the middle of a frame.
- On serial ports and vendor bulk, if input pauses for 200 ms (`probe_frame_gap_ms`) in the middle of a frame, the probe starts reading again from the beginning. **On TCP it does not.** TCP does not lose boundaries, and a TCP connection whose stream broke is closed. HID reads anew at the report's first (§1).

## 3. Several transports

- A probe MAY accept OEP control on several transports. **Several transports share one session and one lock**. Requests from any transport are treated
  the same, and the answer goes back to the transport the request came on. Notifications are sent to the transport the subscribe came on (core §10.4).
- **Even when a transport closes** (a TCP connection closed, a USB device was removed), the session, lock, subscriptions and the table of core §5.1 remain: they end only by the events of core §9.
  Answers and notifications that were to be sent to the closed transport are discarded.
  A request being executed is processed through its normal cleanup. Requests not yet executed MAY be discarded.
  From the host both are of unknown result, and checking the state and resending after reconnecting follow core §5.1. The resend ordering state is not rolled back.
- **Requests carrying the id of one session are sent on one transport** (so that the ordering decision of core §5.1 is not misled by transport delays). Requests with session_id 0 MAY
  be sent from another transport. A wrong decision when a host sends one session's requests from 2 transports is the host's responsibility; the probe does not check.
- When the same probe has several transports, a host SHOULD try the transports it supports in the order vendor bulk, HID, serial port (§4).
  A host has no obligation to implement every kind of transport, and MAY directly use a supported transport the user specified. The probe's list of transports is known from transport in the fn 0 describe (core §7.5).
- **How USB OEP probes are recognized**: a host automatically recognizes OEP probes among unknown devices only for **devices that enumerate with the project's USB
  VID:PID `1209:4F45`** (VID 0x1209, PID 0x4F45; `project_vid` / `project_pid` of registry `usb`). OEP probes are never recognized automatically by other values.
  Otherwise, the user names the probe or chooses the port (the next 2 items). The device's
  string iProduct is a free string for display, and the host does not use it for recognition. Interface strings are also for display and not used for recognition.
- **Named probe**: when the user names a probe by unit_id, the host MAY open, without recognition, the USB device whose serial number
  is the same as that unit_id. After opening it follows the probing rule below, and uses the device as that probe only when the
  unit_id of the fn 0 describe sent after confirm is the same as the named value. If different, the host closes the device and sends nothing else. Comparisons here (unit_id with
  serial number, unit_id with unit_id) do not distinguish upper and lower case letters (some OSes and tools show the serial number in upper case; unit_id
  has only the characters of core §7.5, so ignoring case does not make different values equal).
- **Other devices and serial ports**: USB devices and serial ports not covered by the 2 above are opened only if the host itself has a way to handle them or the user
  explicitly chose them.
- **Probing rule**: on devices and ports the host opens without recognition (named devices, ports the user chose, devices the host itself handles),
  the first things the host sends are only confirm (core §7.1) and its resends (core §5.1). If no correct confirm answer comes within the confirm waiting time
  (core §4.4; before max_op_ms is obtained, core_quick_op_max_ms + host_wait_add_ms (2000 ms in total) plus the transfer time) (when it resent, if none comes within the waiting time of the last resend), the host closes that device or port and sends nothing else.
  A host that handles the optional port_speed MAY repeat confirm on a UART bridge port following the conditions of §4. This procedure is not required of hosts that do not handle port_speed. A correct confirm answer is a completed
  with the same corr as the sent confirm, whose payload has the shape of core §7.1 (beginning with `OEP!`). Devices and ports from which a correct answer came are treated as OEP
  probes.
- **How ports are chosen**: the ports within a device known to be an OEP probe (the project's VID:PID, a named device, a device from which a correct confirm answer came)
  are chosen by interface descriptors: among CDC (ACM), the interface that the describe transport declares is the OEP serial port (§4); **the bulk IN / OUT pair of an interface with bInterfaceClass 0xFF,
  bInterfaceSubClass 0x4F ('O'), bInterfaceProtocol 0x45 ('E')** is vendor bulk; **HID with usage page 0xFF4F,
  usage 0x45** is HID (registry `usb`). A probe offers vendor bulk and HID in this form, at most one of each. A host
  does not decide that a device is an OEP probe only by this class / subclass / protocol and usage page / usage. Other class 0xFF interfaces
  (the debug function of built-in USB serial, WebUSB and so on) do not have this subclass / protocol and so are not grabbed. Other functions (DFU, Mass Storage and so on) are
  outside OEP.
- A probe that also has raw CDC offers a vendor bulk or HID OEP transport usable for the first discovery. The host does confirm / describe there, and then
  opens only the declared OEP CDC interfaces. All CDC offered by a probe without vendor bulk / HID is OEP-only.
- **The USB serial number is the unit_id** (core §7.5): on ports where the probe can choose the serial (devices that offer CDC, vendor bulk or HID themselves), the serial number is
  the unit_id itself (the invariance of core §7.5). The host can tell units apart without opening them (it can look for a named probe), and the value is the same as the describe of every
  transport. For ports whose serial cannot be chosen (built-in USB serial, USB-UART converter chips), the host specifies the transport from outside and checks the unit_id with describe.
- **How TCP probes are found**: when a probe that listens on TCP advertises itself, while it is listening it advertises an instance of the DNS-SD (RFC 6763) service `_oep._tcp` over
  mDNS (RFC 6762). The port is that of the SRV record; there is no fixed port. The TXT record has `unit_id=<unit_id>` (the unit_id of the fn 0 describe).
  The probe MAY add other keys, and the host ignores unknown keys. The probe decides the instance name and host name.
  The TCP destinations a host opens are only those found with `_oep._tcp` or those the user specified explicitly (address and port), and both follow the probing rule above.
  A named probe MAY be chosen by the TXT unit_id, but it is used only when the describe unit_id is the same as the named value (otherwise close it; comparison as for named probes above).
  A probe that does not advertise is used by the address and port the user specified explicitly.
- **max_frame is the limit in both directions**: the probe does not send messages exceeding max_frame, and the host does not send messages exceeding max_frame.
- **Before confirm**: every probe accepts messages up to 64 bytes (registry `min_max_frame`) (the max_frame of confirm is 64 or more).
  The host does not send messages exceeding 64 bytes until it receives the confirm answer. The host is able to receive messages from the probe up to a length of 65535 bytes.
- Where the OS allows it, a host SHOULD open serial ports and HID exclusively (on Linux, TIOCEXCL on the tty; this prevents mix-ups with other tools).
- A probe that offers HID accepts output reports both on the interrupt OUT endpoint and by SET_REPORT (Output).
- A probe that offers vendor bulk SHOULD attach the Microsoft OS 2.0 compatible ID `WINUSB` to that interface.

### 3.1 Set of USB transports (optional)

A probe that lets the user choose the set of OEP transports its own USB device offers uses the core item of this section (core §13.8). It does not offer a third-party item for the same purpose instead.
A probe that does not let the set be chosen does not declare this item.

| Name | form | key_kind | flags | Meaning |
|---|---|---|---|---|
| `usb.transports` | enum | none | restart | The set of OEP transports the probe's own USB device offers after restart. Without a value, the probe's default set |

- **Choices**: the probe lists in setting_choice only the sets its USB device can start. Sets not listed cannot be chosen (unsupported, core §13.3).
- **Names of choices**: the short names of transports (`bulk`, `hid`, `cdc` of core §13.3) joined by `-` in the order of the describe transports, with a number after the name
  when the same kind appears 2 or more times (`bulk-hid-cdc`, `bulk-hid-cdc2`, `bulk-cdc3`). vendor bulk and HID are at most one each (§3), so only `cdc` gets a number.
  The host uses the name for display, and learns the content of the set from the describe transports after restart.
- **Every set includes vendor bulk or HID** (for the same reason as the discovery rule of §3 for probes that also have raw CDC).
- **Not included**: built-in USB serial, UART bridge, TCP transports, and USB functions that are not OEP transports (DFU, raw CDC and so on) are not included in a set.
- **When it takes effect**: after restart (restart, core §13.2). Transport indexes and names (core §13.3) change with the set, so values that hold a transport by name (pass-through items and so on) are
  not used if the name cannot be looked up to a current transport at boot (core §13.7). The host reads describe again after the boot_id changes.
- **When it cannot start**: if the USB device of the chosen set cannot be started, the probe starts with the default set for that boot (the value does not change).

## 4. Serial ports

An OEP serial transport carries frames. Raw console data, logs and boot messages are not mixed into the same transport, except the pass-through below.
The console uses OEP read / write. A separate raw endpoint MAY be offered, but it is not treated as an OEP transport, and
the identification of that endpoint and the settings of what it connects to are stated explicitly outside the OEP core. confirm is not sent to a raw endpoint on the basis of CDC enumeration alone.

- **UART bridge line**: 8 data bits, no parity, 1 stop bit, no flow control. The speed at boot is **115200 bps** (registry `uart_bridge_boot_baud`). port_speed ([link](../interfaces/oep-if-link.md) §3) changes only the speed.
- **A host that handles the optional speed change**: on a port where [port_speed](../interfaces/oep-if-link.md) was or may have been used, the host MAY retry
  confirm until it returns to the boot speed. The host decides the deadline of the wait, including the processing time of earlier requests and the transfer time of frames.
  `port_speed_idle_ms + host_wait_add_ms` alone is not taken as the limit for recovery. A uniform 4 second wait is not required of hosts that do not support it.
- **USB serial ports** (USB CDC, built-in USB serial): the probe receives and sends OEP whatever line coding the host sets, and applies the line coding to nothing.
- **Control lines**: the probe does not decide whether to receive or send OEP by DTR, RTS or the line state. The host keeps DTR and RTS asserted while the port is open (a UART bridge may connect them to the probe's reset).
- The probe processes only candidates of `0x00 <COBS(message | CRC)> 0x00`. CRC mismatches, candidates that do not decode, and timeouts midway are discarded.
  Corrupted bytes are not forwarded to the target. The 0x00 that closed a candidate also becomes the start of the next candidate.
- Answers and notifications are sent in the same frames. A transport has one writer, and no other frame is inserted in the middle of a frame.
- **Pass-through (optional)**: on a serial port pointed at by a pass-through settings item (the UART of [fixture](../interfaces/oep-if-fixture.md) §2, the pass-through of [console](../interfaces/oep-if-console.md)),
  the probe MAY, while its condition holds, send between frames the bytes that UART received or the output of the target's console. Not in the middle of a frame. After sending raw bytes, it sends
  a delimiting 0x00 before the next frame (so that raw bytes do not mix into the next candidate). When a session's request comes from that port, it does not send raw bytes until that session
  ends. The host reads and discards bytes outside frames as noise (it may receive a candidate whose CRC does not match and resend the same request).

## 5. Resync

- When the length or shape of a TCP frame breaks, the connection is closed and reopened. Making the input quiet and sending confirm does not reset the TCP parser.
  A pause in the middle of a frame alone is not judged as broken. A normal answer with a corr not being waited for is only discarded, and is not treated as broken boundaries.
- A host that lost the boundaries of vendor bulk reads and discards input, and waits longer than probe_frame_gap_ms from its last write to that port.
  It resumes after confirming the answer to a confirm with its own corr. While subscribed notifications keep arriving it does not become quiet: notifications end together with the lock
  of the subscribing session (core §10.3), so if it waits without sending requests it becomes quiet by lease_max_ms at the latest. If it cannot be made quiet, the transport is closed and reopened.
- HID reads anew from the next report that has a first (§1). It does not wait for quiet. Requests whose results did not arrive follow the resend rules of core §5.1.
- COBS discards broken candidates and reads from the next delimiter. When the result of a request is unknown, the resend rules of core §5.1 are used.
- Even after reopening, the session and resend history remain (§3). confirm on the new transport and check the boot_id.
  This does not mean carrying over the unsent / unread queue of the old transport. Even when resending the identical request, the half-cycle and number-reuse rules of core §4.1 and §5.1 are kept.


## 6. Transfer time of the host's wait

The following transfer time is added to the time the host waits for an answer (core §4.4). The transfer time is 0 except on a UART bridge. On a UART bridge it is (L + max_frame × (1 + `notify_pending_max_frames`)) × 10 / baud seconds, where L is the length on the line of that request's frame and baud is the current speed of the port. Until it receives a confirm answer on that transport, the host uses `min_max_frame` (64) as max_frame. After that, it uses the max_frame of the newest confirm answer there. A host that does not know whether a serial port is a UART bridge (for example, before reading the transport kind in the fn 0 describe, core §7.5) counts this transfer time on that serial port, with baud as the speed it set on that port.

## 7. Network settings

A host MUST be able to configure TCP transports on every probe with the same procedure. So a probe that lets the Wi-Fi destination and how IPv4 is decided be configured through OEP
uses the core items of this section (core §13.8). It does not offer third-party items or extensions for the same purpose instead (the firmware's own screen, buttons and factory values MAY exist separately).

- **netif** is a name list (core §7.7): the probe lists one name per network port in netif of the fn 0 describe (core §7.5).
  The standard names are `wifi` (Wi-Fi station; used by the items of §7.1) and `ethernet` (wired). Other ports (cellular and so on) have reverse-DNS names, and the common defaults of §7.2 also apply to them.
- **Common defaults**: if there is no value of `wifi.{}.ssid` at all, the probe does not use Wi-Fi. A netif without a value of `ipv4.{}.mode` gets its address by DHCP.
  Wired is used by DHCP when the cable is connected, even without values. A host MAY assume that the same values mean the same thing whichever probe they are sent to.
- **What the probe decides**: the reconnection interval, the mDNS instance name, the port it listens on for TCP (readable with network), whether NTP is used and its server.
  OEP time is the probe's clock (core §2.7) and does not rely on a wall clock, so NTP is not an OEP item. IPv6 is not defined in v1.
- **When it takes effect**: when set or unset changes a value of a transport in use (a value of the Wi-Fi entry in use, an ipv4 value of that netif), the probe sends the answer and then
  disconnects that transport and reconnects with the new values. Other changes keep the transport and are used at the next reconnection. Unsaved changes return to the saved content at restart.
  So even if a value is put that makes the probe unreachable over TCP, a restart (power cycle) can bring it back.
- **(Informative) Changes from TCP**: changing a value used by that transport also disconnects that connection. The answer is sent first, so the result of set arrives. The host looks for the
  unit_id again at the new address (§3), confirms it is reachable, and then saves.
- **max_frame**: a probe that declares the items of this section makes the max_frame of confirm 82 or more on every transport (registry `wifi_min_max_frame`).
  This is because the get answer of the longest value (a 64 character key) is 18 + 64 = 82 bytes (core §13.5).

### 7.1 Wi-Fi destination

A probe meets different networks depending on where it operates, so it has several entries and tries them in key order. The number of entries is the setting's keys.

| Name | form | key_kind | Meaning |
|---|---|---|---|
| `wifi.{}.ssid` | text (1 to 32) | index (entry) | The network's name. An ssid the probe cannot handle is unsupported |
| `wifi.{}.passphrase` | text (8 to 64), secret | index (entry) | 8 to 63 bytes is a passphrase of bytes 0x20 to 0x7E. 64 bytes is a key of 64 hexadecimal digits. Other lengths and bytes are malformed. Without a value, an open network |

- passphrase is secret (core §13.5): it is not readable by anyone and not put in any answer, event or log. OEP does not encrypt values, so it is sent over a trusted transport (USB and so on, §1).
- The passphrase of an entry without an ssid is not used.
- **How it connects**: the probe tries the entries that have an ssid in increasing key order and uses the first entry that connected (got an IPv4 address). When none connects,
  and when the connection is lost, it tries again from the start (the probe decides the interval).

### 7.2 How the IPv4 address is decided

The key is netif (key_kind netif of core §13.3).

| Name | form | Meaning |
|---|---|---|
| `ipv4.{}.mode` | enum: 0 `dhcp`, 1 `static` | Without a value, dhcp |
| `ipv4.{}.address` | ipv4 | The address for static. 0.0.0.0, 255.255.255.255, 127.0.0.0/8, 224.0.0.0/4 are malformed |
| `ipv4.{}.prefix` | u32 (1 to 32) | The prefix length for static. Others are malformed |
| `ipv4.{}.gateway` | ipv4 | The gateway for static. Without a value, none |
| `ipv4.{}.dns` | ipv4 | The DNS server for static. Without a value, none |

- With dhcp, the values of address, prefix, gateway and dns are not used (the values MAY remain). The gateway and dns DHCP returns are used.
- With static, when there is no value of address or prefix, or when the gateway is not within the same prefix as the address, that netif gets no address (network state 3, reason 3).
- The handling when it turns out that the fixed address is in use on the same network is decided by the probe and shown by network reason 3.

### 7.3 network (current condition)

An optional op of fn 0 (core §11). A probe with netif in the fn 0 describe has it.

| op | Name | Request | Answer | Lock |
|---:|---|---|---|---|
| 0x25 | network | [TLV] | tcp_port(u16), count(u8), count × condition, [TLV] | Not needed |

tcp_port is the port listening on TCP (0 if not listening). Then, in the order of the netif list, the condition of each netif (19 bytes) is returned.

| Field | Meaning |
|---|---|
| netif(u8) | The position in the netif list (from 1) |
| state(u8) | 0 not used (no ssid value, the wired cable is not connected), 1 trying to connect, 2 connected, 3 not connected and waiting to retry |
| entry(u16) | For Wi-Fi, the key of the entry being tried in state 1 or used in state 2. Otherwise 0xFFFF |
| reason(u8) | The reason of the last failure: 0 none, 1 network not found (no AP, no link on the cable), 2 authentication failure, 3 no address obtained (DHCP timeout, duplicate fixed address, missing static values), 4 other. 0 once connected |
| rssi(i8) | For Wi-Fi in state 2, the received signal strength (dBm). Otherwise 0 |
| address(4), prefix(u8), gateway(4), dns(4) | The values in use in state 2 (including those obtained by DHCP). Otherwise 0 |

## 8. Referenced specifications

OEP frames and messages are determined by this text alone. A probe that offers USB transports also follows the following USB specifications, and a probe that advertises as in §3 and a host that searches with it also follow the following RFCs:

| Specification | Parts used |
|---|---|
| Universal Serial Bus Specification, Revision 2.0 | Enumeration, device and interface descriptors, the serial number string, bulk transfers and zero-length packets (§1, §3) |
| USB Class Definitions for Communications Devices 1.2 and its PSTN subclass (CDC ACM) | The CDC ACM function of USB CDC serial ports: its interfaces, line coding, control lines (§3, §4) |
| Device Class Definition for HID 1.11 | Vendor-defined input and output reports, report IDs, SET_REPORT (§1, §3) |
| Microsoft OS 2.0 Descriptors Specification | The compatible ID `WINUSB` of the vendor bulk interface (§3) |
| RFC 6762 Multicast DNS | `.local` queries and answers, name checking and renaming on conflict (probing, announcing), re-advertising when the address changes (§3) |
| RFC 6763 DNS-Based Service Discovery | Service instance names, PTR / SRV / TXT records, the TXT `key=value` form (§3) |
