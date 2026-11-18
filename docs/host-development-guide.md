# Open Embedded Probe — host development guide

[日本語](host-development-guide.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative). For people who write hosts, it collects practical ways to meet what [OEP core](oep-core.md) and
the `oep-if-*.md` documents require, and the traps people tend to fall into. Where it disagrees with the normative text, the normative text is right.
The first step (the smallest host and the bytes) is in [getting started](getting-started.md), and the checklist of what a host must do
is [conformance](conformance.md) §2. For how to use a probe implementation, see the repository of that implementation.

The sections are ordered from what a host does first (opening the port, frames, discovery, sessions, refusals) to optional settings. Product- or target-specific procedures are kept in the documents of the client or application that implements them.

## 1. Opening a probe without resetting it

- **Open with both DTR and RTS asserted** (the default of many serial libraries). transports §4 requires the host to keep them asserted while the port is
  open. The probe uses neither for any decision.
- **If you must lower them, lower RTS before DTR.** Many boards connect DTR / RTS to an automatic reset circuit, and the MCU is reset in the state RTS = 1,
  DTR = 0. Lowering DTR first passes through that state.
- Nothing needs to be done when closing.
- Do not use it with DTR lowered: some USB serial stacks do not send while DTR is low (transports §4 does not define the probe's behaviour in that case).
- Do not open a probe's port at 1200 bps: several USB stacks take opening and closing at 1200 bps as the signal to enter the bootloader.

## 2. Serial ports always use COBS, and what is outside frames is noise

- Every port the OS sees as a serial device (UART bridge, USB CDC, built-in USB serial) speaks COBS + CRC-16 (transports §1).
  The frame shape is decided by the kind of transport, not chosen by VID:PID.
- An OEP port is for frames only and does not mix in raw console data. Candidates that do not decode and CRC mismatches are discarded.
  Even a correct frame is discarded if it is an answer with a corr not being waited for. Resending follows §8.
- A correct COBS frame holds no more than 65796 bytes between its two 0x00 (a 65535 byte message and its CRC-16,
  plus 1 COBS code byte per 254 bytes). A candidate that grows longer may be discarded as noise without waiting for the closing 0x00.
- Always enclose frames you send in 0x00 before and after. A candidate without the leading delimiter may be discarded by the probe.
- The console uses OEP read / write. A separate raw endpoint is treated as an explicitly stated path.

## 3. UART speed

A UART bridge probe always starts at the boot speed `uart_bridge_boot_baud` (115200 bps) 8N1, no flow control (transports §4; names in backquotes
are keys of `registry/oep-v1.toml`, which holds every number). port_speed ([link](../interfaces/oep-if-link.md) §3, optional) raises it
only for the session. Whether to raise it, the candidates, how to check and the criteria for reverting are decided by the host. If the needed bandwidth cannot be met, use the probe's faster
transport (native USB).

On a UART bridge, and on serial ports that cannot be told apart from one, add the transfer time of core §4.4 to every wait for an answer. Before the first confirm
answer on that port, max_frame is not yet known: use `min_max_frame` (64) in the formula, and after that the max_frame of the newest confirm answer on that port
(core §4.4).

## 4. Finding USB probes

- A host automatically recognizes OEP probes only by the project's USB VID:PID `1209:4F45` (VID 0x1209, PID 0x4F45; `project_vid` / `project_pid` of registry
  `usb`; transports §3). When making a list of probes, list the USB devices with this VID:PID.
  Each one's USB serial number is the unit_id, so they can be told apart without opening them.
- Do not recognize probes by anything else: neither iProduct, nor the interface class / subclass / protocol, nor the HID usage page. These can
  coincide with other products by chance. iProduct is a name for people, and nothing recognizes probes by it. Interface values are used only to choose ports within a device
  known to be a probe (transports §3).
- Other devices and ports are opened only when the user named a probe by unit_id (a device whose USB serial number is the same) or chose the port
  (transports §3). Once opened, check with the probing rule of transports §3: the first thing sent is only confirm, and if no correct confirm answer comes within the waiting
  time, close it and send nothing else.
- Some probes cannot have the project's VID:PID: probes behind a USB-UART bridge (the bridge enumerates with its own VID:PID and serial number)
  and probes on built-in USB serial whose descriptors the hardware decides. The host cannot find these by itself: the user chooses the
  port. After confirm, the fn 0 describe returns that probe's unit_id. The probe is remembered by this, not by the port name (§5.3).

### 4.1 Finding TCP probes

When a probe listening on TCP advertises itself, it advertises the DNS-SD service `_oep._tcp` over mDNS (transports §3; advertising is the probe's choice).

- Browse `_oep._tcp.local.`, and for each instance read SRV (host name and port), the address, and `unit_id` in TXT. Always use the SRV value for the port.
- The service name `oep` is not a name registered with IANA. Another service may be advertised under the same name, so check everything found with confirm (an `OEP!` answer) and the describe unit_id before using it, and drop from the candidates what cannot be checked (as in the probing rule of transports §3).
  The specification does not decide the port.
- Once opened, send only confirm first, as in the probing rule of transports §3. Check with the unit_id of the fn 0 describe, and close if it differs from TXT.
- **Which one to use** is decided by the host. A guideline: if the user named a unit_id, open the instance whose TXT unit_id is the same. If nothing is named and none is
  remembered, list the probes found (unit_id and instance name) and let the user choose, and remember the chosen unit_id. If the same unit_id is found on both USB and
  TCP, group them as one probe (§5.1), and usually use the USB transport (no Wi-Fi drops or delays).
- After a restart or a Wi-Fi reconnection, the address can change: browse again by unit_id (item 5 of §5.2).
- Send queries from every IPv4 network connection (choosing the outgoing interface per connection). Sending once from a socket on address 0.0.0.0
  goes out only on the one connection the OS chose (which may be a virtual one), and probes beyond the other connections are missed.
- For probes that do not advertise, and where mDNS does not reach (beyond a router, VPN, virtual machines behind NAT), the user specifies the address and port explicitly.
- Anyone on the same network can advertise, and the describe unit_id can also be faked. Use TCP only on a trusted network or inside an authenticated tunnel
  (transports §1).

### 4.2 Configuring the TCP transport

- Settings that put a probe on Wi-Fi or wired IPv4 are done, on every probe, with the core settings items `wifi.{}.*` and `ipv4.{}.*` ([transports](oep-transports.md) §7).
  Sending the same values means the same thing on every probe. A netif without `ipv4.{}.mode` uses DHCP, and without `wifi.{}.ssid` Wi-Fi is not used.
- A guideline for the procedure: connect over USB, check what can be handled with setting and netif in the fn 0 describe, and send `wifi.0.ssid` and `wifi.0.passphrase` (and the ipv4 values if needed) in
  one set. Check state 2, the address and tcp_port with network, confirm it is reachable over TCP (find the unit_id with §4.1 and confirm passes), and then save.
  Before the save, a restart returns to the saved content.
- passphrase is secret, and get does not return its data (len 0). Sending the value of get back unchanged with set does not change the passphrase. Neither display nor log the passphrase.
- Where mDNS does not reach, show the user the address and tcp_port of network, and use them as an explicit destination.
- **The list of settings**: items of the core and of interfaces are listed by name and form in the setting of each fn's describe (core §13.2). A host can display the name of an item even when it does not know its meaning,
  accept input according to the form, and get / set / save it. Items are told apart by name, and numbers are looked up per probe with describe.

## 5. session_id and discovery

- At every open, choose a new, unpredictable 32 bit random session_id. Not 0, sequential numbers or a fixed value (core §6.1).
- **A one-shot CLI opens a new session for each command.** It does not reuse the connections or streams of the previous session.
  It reads the wiring settings saved on the host, and attaches with pins and speed stated explicitly. When output or connections are to be kept across several commands, run them in the same session.
  Read needed console output before end and save it to the host's log.
  Record the boot_id per unit_id, and when it changes, rebuild the fn mapping from list.
- **Discovery procedure**: enumerate USB devices, and open those with the project's VID:PID (§4) and those whose serial number is the same as a named
  unit_id (transports §3). The serial number is the unit_id. Ports within a device are chosen by interface
  descriptors (vendor bulk: class 0xFF / subclass 0x4F / protocol 0x45, HID: usage page 0xFF4F / usage 0x45, every CDC is a serial port).
  Once opened, first send only confirm (close if there is no answer), get the boot_id and limits, and check that the describe unit_id is the same as the serial.
  Monitoring without the lock learns of restarts from the boot_id of confirm or clock.
- **Check the limits before using them.** In the confirm answer, max_frame is 64 or more, window is max_frame or more, max_inflight is 1 or more (core §7.1).
  In the fn 0 describe, max_op_ms is 1 to `max_op_ms_max` (600000 ms, core §7.5), and this bounds the wait for answers. A probe that returns a value out of range
  does not conform, so it is best not to round it, but to tell the user the value and not use that transport.
- Things kept open for a long time, such as interactive CLIs and monitors, keep the lock with keepalive or ordinary requests. Keep sending
  keepalive while stopped at a confirmation prompt too, and before each destructive procedure check that the session is alive (does not become `no_session` / `locked`).
- **Monitoring that reads an existing stream may use session_id 0**. The owner that made that stream needs to keep its session, and monitoring reads do not update the lease.
  If the monitor itself makes a plan/connection/stream, keep its owning session while in use. write is also done in that owning session, and end removes the resources it made and unread buffers.
  When several tools use the same resources, bundle them into one owning session of a broker. Do not assume each tool can send open → write → end and leave shared resources behind.
- When finishing, send end (even without it, the lock is freed at the deadline).
- **A host that may stop and run again** (CLI, broker): a session does not end when the transport closes (transports §3), so the lock and resources of a host that stopped without sending end
  remain until the lease runs out. To end the previous session on the next run, send open and end with that id
  **as new requests** (an open with the same id keeps the session, core §6.2). The corr of a new request becomes result_lost unless it is
  1 to 32767 ahead of the last corr the previous run used (core §4.1, §5.1). So the host keeps, together with the session_id, corrs the previous run has not yet used,
  per probe (keyed by unit_id), in a file or the like. For example, reserve 1024 ahead at a time, and write the next reservation before using it up. On the next run,
  send open and end from the reserved corr, release what it held before, and then open a session with a new id.
  When there is no record, or it cannot be read, wait until the previous lease runs out (the remaining time of lock_state), or take it by force only when the user says so explicitly.
  Do not keep this record for an `x-` unit_id (core §7.5).

### 5.1 Several transports of one probe

- One probe may show several transports (vendor bulk, HID, serial port, TCP). The transports share one session and one lock
  (transports §3). Group them by the unit_id of the fn 0 describe (compared ignoring ASCII case), and do not group by a unit_id beginning with `x-`
  (core §7.5).
- If you can choose, use vendor bulk, HID, serial port in that order (transports §3). Serial ports also have a limited receive amount
  (transports §4).
- Send every request carrying your session's id on one transport (transports §3). Lock-free requests may be sent on another transport (for example,
  reading describe and state over HID while a debugger holds vendor bulk).
- max_frame, window, max_inflight and the protocol revision are per transport (core §4.4, §7.1): confirm on each transport you use.

### 5.2 Restarting a probe (restart)

restart of `oep.probe.restart` ([restart](../interfaces/oep-if-restart.md)) restarts the probe without unplugging the port. It is used to recover a probe
that got into a strange state, and to test the host's own path for "the probe restarted". It is an optional interface, so find `oep.probe.restart` in list
before using it. restart_max_ms in its describe is the limit until the probe's internals recover, and does not include OS enumeration or network connection time.
Read it before restart, and the host decides the deadline for reopening by adding the external waits to it.

1. Take the lock (restart is an op that needs the lock; with session_id 0, session_required). If there are settings you want to keep, save first:
   unsaved settings are lost on restart (core §13.7).
2. Send restart. Do not follow it with requests (on any transport): after the answer the probe processes nothing and answers nothing.
3. When the completed success answer comes, close all transports of that probe. If port_speed was raised on a UART bridge, return to the boot speed
   (host 2 of [link](../interfaces/oep-if-link.md) §3).
4. Wait a little (about 100 ms as a guideline). The probe starts restarting during this time.
5. Reopen the same as opening anew (§4, the probing rule of transports §3: confirm first; the boot speed on a UART bridge). On USB the device leaves the bus and enumerates again:
   the OS port name may change, so look again by serial number (= unit_id). If it cannot be opened or confirm gets no answer, repeat reopening and confirm until the
   deadline the host decided after receiving the answer (wait for the confirm answer as in core §4.4). The passing of restart_max_ms alone cannot tell
   whether the external path has recovered or whether the probe violated it. If there is no correct
   confirm answer by the deadline, treat the probe as gone: close the transports of that probe, tell the user, and send nothing until the user reopens it.
   A reopening the user asked for beforehand (a tool option that keeps reopening for a while after closing, and so on) counts as the user reopening.
   UART bridge and TCP ports may stay open without closing, but the same procedure is fine. On TCP, the address can change, so browse again by unit_id (§4.1).
6. Compare the boot_id of confirm with the one before restart. If different, it restarted: discard the remembered fn mapping, resource numbers, stream positions and the session
   (core §6.5), do list again, and open a new session if needed. Requests with the previous session's id are refused with no_session. If the same,
   treat restart as not executed.
7. When the answer did not come, check the same as 5 to 6. The host's reopening deadline counts from when the wait for the restart answer passed.
   When a restart with the same corr is refused with no_session, also go on to 5 to 6, and decide the reopening deadline based on that answer.

**A relaying host** (the relaying broker of transports §1) relays restart like any other op that needs the lock, and after returning the answer to the tool, closes the path to the
probe as above. When the broker's path to the probe is gone (the broker closed it, USB re-enumerated, TCP closed), the broker ends,
and also closes the connections to the tools (transports §1): the tools start again the same as opening anew.

After the restart, saved settings are applied as at an ordinary boot (the host reapplies wiring settings).
The restart procedure does not intentionally reset/resume the target, but the reset state of pins and the effects of external circuits are checked separately ([restart](../interfaces/oep-if-restart.md) §2).

### 5.3 How probes, ports and targets are named

**Address**: when a host names a destination in text (CLI, IDE, settings files, logs), it writes it in the following form.

```text
oep://<probe>[/<port>[/<target>]]
```

| Level | What it points at | Value |
|---|---|---|
| probe | The probe unit | unit_id (core §7.5). Not remembered by port name or VID:PID |
| port | Which set of the probe's pins | `S` of the probe's settings label `S.N` ("port names" below). In the case as written |
| target | The actual chip at the end of the wire | A target name the host decides ("target names" below) |

- Every level uses only letters, digits, `-` and `.`, and needs no URL encoding. `:` (the URL port field) and `*` (shell glob) are not used.
- **Case**: display (discovery, lists, logs) shows names as written where they were decided (the probe's label, the host's settings). Equality is decided
  ignoring ASCII case (A to Z folded to a to z before comparing). When an IDE or the like compares addresses as strings, it also folds before comparing.
  In tools that remember an address as a string as it is (the selected port of the Arduino IDE and so on), changing the case of a label can make it look like another port.
- An address is always written in full. There is no way of writing "any one". The convenience of omitting levels when there is one candidate may be offered as a tool feature (it is not the address format).
- Not writing a level does not mean "unspecified" but that the location is fully stated: `oep://<probe>` is the probe itself, and `oep://<probe>/<port>` is that port, without checking the chip beyond it.

**Port names**: ports are named by the probe's setting `channel.{}.label` (core §13.8). A set of channels with labels of the form `S.N`, such as `S.swdio`, `S.swclk`, `S.swio`, `S.nrst`,
is the port named `S`. It is stored in the probe, so it looks the same name from every host.

A label may append, with `@P`, the target pin that channel connects to (`S.N@P`). A line without a role is written `S@P` (a line of port `S` of which only the pin is known).

```text
x035.swdio@pc18     line swdio of port x035. Connects to PC18 of the target
x035.nrst@pa21      line nrst of port x035. Connects to PA21 of the target (the pin that becomes NRST by configuration)
x035@pb6            a line of port x035. No role; connects to PB6 of the target
```

- `S` begins with a letter and consists of 1 to 16 letters, digits and `-`. `N` and `P` consist of 1 or more letters, digits, `-` and `_`. `.` is the separator between `S` and `N`, and only one is put.
  Only one `@` is put, before `P`. The whole label is up to 32 characters (core §13.8).
- `P` writes the name of the target pin (port and bit, `pa21` and so on) in a way the host decides. Pins that connect to one lead in the package are written
  joined with `-` (`pc16-pc11`). `P` is a record the host reads; the probe does not drive lines by it.
- The role is decided by what comes before `@`. `S.N@P` names the same line as `S.N`. `S@P` belongs to port `S`, but cannot be found by a role name.
- For a target where the same pin changes role by configuration (PA21 of CH32X035 is a reset only when made NRST with option bytes), write both the role name and `@P`.
  Whether the role is in effect now is checked by the host with the target's configuration.
- Labels that do not fit this form (`NRST`, `My Port.swdio` and so on) do not name ports. They can be used as they are as names pins are called by, and the host does not show them in the list of ports
  (the user may be told about labels that resemble `S.N` but do not fit).
- Ports are only the named ones. A probe without labels of `S.N` has no port that can be pointed at by address (it is used by specifying the wire's terminals directly; a tool feature).
- Discovery and port lists show only named ports, as written in the label.
- Labels are unique within the probe ignoring case (core §13.8), so port names and line names are also decided uniquely.
- A port name does not decide the kind of wire (rvswd and swd can use the same line names). Which wire to connect with is decided by the family of the target name, the host's settings and the user's specification.

How to find labels as line roles: line `N` of port `S` is found by the label whose part before `@` is `S.N` (ignoring ASCII case). The line of target pin `P` is found by
the label whose port is `S` and that has `@P`. The probe does not drive lines from these names.
Line names can conventionally be `swdio`, `swclk`, `swio` (debug wires), `rx` (fixture UART reception; connected to the target's TX), `tx` (fixture UART sending), `nrst`, `power_hi`, `power_lo`.

**Target names**: they express a chip unit. The target_id in the attach answer (debug §1) is a value of family and version, and does not tell units apart.
How to read a unit's value (the UID of CH32 and so on) is chip knowledge, so the host holds it, and the name is `<family>-<unit value in hexadecimal>` (example `ch32v003-0123456789abcdef`).
Aliases may be given in the host's settings.
A record of the target beyond a port can be put in the probe's memo area as `oep.probe.memo/port/<port>` ([memo area](../interfaces/oep-if-memo.md) §4.3). Every host reads and writes it in the same form.

**Resolution**:

1. Look up the probe level by the unit_id visible in discovery, and the port level by the port name of that probe's labels (both ignoring case).
2. If not found, stop. Do not substitute another probe or port.
3. If there is a target level, make the connection used for the work on that port, and before side effects such as writing, match the target name over that connection. If it differs, do nothing and stop.

The target level is not a key to search with, but a value matched before the work:

- Most unit values are in memory, and reading them stops the hart (read_block of riscv-dm assumes halt, debug §4.5). On rvswd the wake of attach itself can reset the target (debug §3).
  So matching is done over the same connection, alongside work that stops the target anyway (writing, debugging). Checking over another connection and then using it misses a swap in between.
- For work that does not stop the target, such as monitoring the console, matching the target level is not done by default and the request is refused. Matching is done only when the user allows stopping.
- Finding a target by attaching to candidate ports one by one is not part of address resolution. It is a tool feature the user runs explicitly, and rvswd ports are skipped by default.

| Written form | Meaning |
|---|---|
| `oep://<probe>` | The probe itself |
| `oep://<probe>/<port>` | That port. The chip beyond it is not checked |
| `oep://<probe>/<port>/<target>` | That port, matching before the work that it is that chip |

**Transport**: the same probe may be reachable over several transports, so one transport can be appended to the address to choose it. It does not change the location (probe, port, target), only the transport that reaches it.

```text
oep://<probe>[/<port>[/<target>]][?via=<transport>]
```

| via | Transport |
|---|---|
| None | The host chooses. The candidates are the transports that can be found by unit_id (USB VID:PID and serial number, the unit_id in the DNS-SD TXT) |
| `usb` | One of the USB transports. Whether bulk, hid or cdc is used is decided by the host |
| `bulk`, `hid`, `cdc` | The USB transport of that kind (the short kind names are in core §13.3) |
| `net` | TCP found with DNS-SD |
| `tcp:<host>:<port>` | TCP at that address and port. `<host>` is a name or IPv4; IPv6 is enclosed in `[...]` |
| `tty:<path>` | An OS serial port (`/dev/ttyACM0`, `/dev/serial/by-id/...`, `COM3`). Transports that cannot be found by unit_id, such as USB-UART converters, USB-Serial/JTAG and CDC with other VID:PIDs, are written with this |

- Whichever transport it opens, the host checks that the unit_id of confirm and of the fn 0 describe is the same as `<probe>`, and closes if different (transports §3). Specifying a transport is no reason to accept another probe.
- `via` is not part of the location. When comparing whether 2 addresses are the same location, compare them without `via`.
- A tool that reads addresses first removes everything from `?` on, and then splits the location levels by `/` (the value of `tty:` contains `/`).
- The value of `via`, as a URL query, can contain `/` and `:` as they are. `?`, `#`, `&`, `%` and spaces are written as `%XX`.
- The query is only one, `via`. An address with a query of an unknown name is refused (so as not to confuse it with names added later).
- Discovery (an IDE's port list and so on) outputs one line per location in the form without `via`. Users who choose the transport append `via` in the CLI or settings.
  In tools that remember and compare addresses as strings as they are (Arduino IDE), adding `via` in a setting separate from the address (a board menu and so on) keeps the remembered location unchanged.
- A tool that makes a device exclusion key from an address makes it from the probe (unit_id) without `via`. Even with different transports or ports, the same probe gives the same key.
- Short inputs, such as accepting only a tty path when the unit_id is not known, may be offered as tool features. When saving (settings files, ports an IDE remembers), write the full form.

**Interface**: when one interface is pointed at in text (CLI, settings files, logs), it is written `name#instance` (instance is the value in list;
0 is also valid, and `#0` may be omitted). Example: `oep.fixture.uart#1` is `oep.fixture.uart` with instance=1, not the 2nd in list.
The revision is stated, saved and chosen separately, and (name, instance, revision) is resolved. If it is a gap, treat it as not offered.

Descriptions of how to connect, such as wire speed and how to choose the target, are held by the host. They are not standard probe settings items.

## 6. Exclusion and taking the lock

- **Always open serial ports exclusively** (`ioctl(TIOCEXCL)` on Linux / macOS; exclusive from the start on Windows; transports §3). Without exclusion, answer
  bytes go to another process and the transport does not work. Cooperative locks (`flock`; some libraries call it "exclusive") do not stop tools that do not look at them,
  so apply TIOCEXCL after opening. root passes through TIOCEXCL.
- A libusb / WinUSB claim is made exclusive by the OS.
- **Real exclusion is done by session_id** (core §6). How to take the lock is decided by the number of the probe's transports (transport in the fn 0 describe).
  - **A probe whose only transport is one serial port**: once it is opened exclusively, the previous owner's process does not hold the port, so it may be taken on the spot with
    force of open.
  - **A probe with several transports**: read the remaining time with lock_state and wait only that long (up to a few seconds). If the holder keeps renewing the lease,
    report "in use" without waiting. Use force only when the user says so explicitly (force is not authentication, and TCP is used only over trusted connections; transports §1,
    core §6.4).
- Choose the lease including the margin to recover one lost request by resending. Let H be the interval from the last new request of the same SID to the next keepalive,
  W the keepalive resend wait of core §4.4, T the transfer time for the resent request to reach the probe,
  and Q the upper bound of the time waiting for earlier processing during which the owner's request does not stop the lease; make H + W + T + Q + the host's scheduling margin sufficiently smaller than the accepted lease.
  W is min(max_op_ms, core_quick_op_max_ms) + host_wait_add_ms + the transfer time, and its largest processing part is 1000 ms.
  An interactive tool on a fast transport can start with, for example, a lease of 5 seconds and a keepalive interval of 1 second. On slow transports or with large frames, also compute the transfer time, and lengthen the lease if needed.
  In configurations where the margin cannot be secured even with lease_max_ms, there is no guarantee of recovering from the loss of one frame while keeping the session.
  With a single transport, max_inflight=1 and no earlier processing, Q=0 is fine. When Q cannot be estimated, such as with long queries on another transport, that guarantee is not given either.
  The lease advances from the probe building the answer, so do not assume the whole of it remains from when the host received the answer.
  Even if it expires because sending stalled, a success that arrives late does not guarantee the continuation of resources.

A success received by resending is the result of the original request. Even if the lease has already run out, a kept result may come back, but the lock and resources are not restored, and the resend does not extend the lease (core §5.1/§9).
On recovery, check the boot_id and the state. For example, ownership can be confirmed with a new keepalive of the same SID; if it is no_session, that SID has ended.
Do not delay the next renewal on the strength of the success of a resent keepalive alone; renew with a keepalive with a new corr.
When a new session with another SID is opened, do not take over earlier resources; remake the needed connections and plans explicitly.

## 7. Brokers

A broker that answers OEP itself runs as an independent OEP endpoint. It implements list / describe / confirm, sessions, resend history and resource lifetimes
for its clients, and manages the mapping to the upstream probe internally. It is not made an endpoint that answers only some ops of fn 0 itself and passes the others through.
Several tools that want to hold the same resources for a long time bundle their processing within the broker's session. The core does not decide the sharing policy towards clients.

### 7.1 Sharing `oep.probe.share`

When a broker lets several tools (clients) share one lock, it lets share only the clients that attached the named extension `oep.probe.share` (core §2.2, data empty)
to open.

- The client attaches `oep.probe.share` as critical (0xFF). Endpoints that do not know the extension (probes, brokers that do not share) refuse it with unsupported
  (core §2.2), so the client notices that it is not sharing. If refused, it reopens without the extension, or stops.
- While sharing, the broker holds the probe's lock as one owner, and keeps the lease towards the probe. Sessions are per client, and when a client ends or
  its connection drops, only that client's share is removed. Resources a client made (connections, plans, subscriptions) are recorded per client, and released when that client
  leaves. When the last client leaves, the broker may release the probe's lock.
- Client requests are passed to the probe without breaking order within one client, and in the order they arrived across clients.
- Clients that do not attach the extension are answered as in the core (one lock, resend history, lease, force). While sharing, an open from a client without the extension
  becomes locked. An open with force takes the lock as in the core, and all sharers lose their sessions (sharing is treated as one owner).
  While a client without the extension holds the lock, a sharing open becomes locked.
- To change the content of sharing, add an extension with a new name (core §2.2).

### 7.2 Finding the broker

So that a broker can be found from every tool, whatever the tool's location or the broker's implementation, the broker puts a file in a per-user location.

- **Location**: `oep/brokers/` in a per-user directory. On Linux `$XDG_RUNTIME_DIR/oep/brokers/`; when there is no `XDG_RUNTIME_DIR`
  (ssh, cron, containers and so on) `$TMPDIR/oep-<uid>/brokers/` (`/tmp` if there is no `TMPDIR`). On macOS `$TMPDIR/oep/brokers/`,
  on Windows `%LOCALAPPDATA%\oep\brokers\`. Both the creating side and the reading side check that the directory's owner is themselves and its permissions are 0700, and do not use it otherwise.
- **Scope**: probes with a unit_id (core §7.5). Nothing is put for unit_ids beginning with `x-` or for transports that cannot be named by unit_id (UART converters only,
  devices without a serial and so on).
- **File**: `<unit_id>.json` (permissions 0600). It exists only while the broker is listening and clients can connect. Write it to a temporary file and then rename it,
  so readers never see it half written. The content is one UTF-8 JSON (no BOM), whose top level is an object. Readers skip unknown members.

  | Member | Value |
  |---|---|
  | `unit_id` | A string. The unit_id of the probe the broker has open |
  | `endpoints` | A sequence. Where clients connect. Elements are objects with `kind`; `{"kind": "tcp", "address": "127.0.0.1:<port>"}` is the TCP form of transports §1. Readers skip unknown `kind`s |
  | `share` | A sequence of strings. The names of sharing extensions the broker accepts (`oep.probe.share` and so on). Readers use only names they know |
  | `pid` | A number. The broker's process number |
  | `started` | A string. The time the broker started (RFC 3339) |
  | `implementation` | An object. `name` and `version` (for display and diagnosis) |
  | `via` | A string, optional. The transport the broker uses to reach the probe (for display) |

- **Competing to start**: whatever would become the broker takes `<unit_id>.lock` in the same directory exclusively (flock on Linux and macOS,
  LockFileEx on Windows). Only the one that got it becomes the broker; ones that did not get it do not start a broker. Different implementations also exclude each other with the same file.
- **Cleanup**:
  - The broker removes `<unit_id>.json` when it ends.
  - `<unit_id>.lock` is not removed. Exclusion is decided not by the file existing but by holding the lock, and the OS releases the lock even if the process crashes,
    so a leftover file can be used as it is by the next one that takes it. Removing it would let another one take the lock with a new file while a broker holding the lock exists.
  - The `<unit_id>.json` of a crashed broker is removed or rewritten by the broker that next takes `<unit_id>.lock`. Only the broker holding that lock may remove
    `<unit_id>.json`; readers do not remove it.
- **The tool's procedure**:
  1. If the environment variable `OEP_BROKER` (`<host>:<port>`) is set, connect there over TCP (an override for a broker on a remote machine or for testing).
  2. Otherwise read `<unit_id>.json` and connect to `endpoints` of a known `kind`. Once connected, always check that the unit_id of the fn 0 describe is the same as the file's
     unit_id (the listening place of a crashed broker may be reused by the broker of another probe). If it matches,
     open with the known `share` extension attached.
  3. If there is no file, it cannot connect, or the unit_id differs, open the probe directly. Do not check whether it is alive by trying to take `<unit_id>.lock`
     (that competes with a broker that is starting).
- There is no authentication. The TCP of `endpoints` is used, as in transports §1, only over trusted local connections.

unavailable cause 7 by an optional policy expresses that product conditions, such as an authenticated transport or a presence check, are not met (core §4.3).
The host does not work around it by repeating the same request or force, but goes on to that product's connection and authorization procedure. Past success answers are not taken as proof of current permission.

## 8. Matching answers and resending (what transports §5 and core §5.1 require)

- A normal answer with a corr not being waited for is discarded. Recovery when the length or frame is broken follows transports §5. TCP is closed and reopened.
  Subscriptions do not move to the reopened transport, so subscribe again to the subscriptions you want to continue (§12).
- corr is u16 and advances cyclically per session_id. Skip 0; normally 1 comes after 65535.
  Keep the distance from the previous new request and the distance from the oldest outstanding request under half a cycle, 32768. Do not advance half a cycle or more while leaving outstanding requests.
  SID0 queries do not advance the order of the owning session. Do not simply share one counter for all requests so that many SID0 queries make the session's corr skip half a cycle.
  On the same transport, avoid numbers that are outstanding or for which old answers may remain, even for different sessions.
  A resent request may leave extra answers even if it was resolved by the first answer. Do not hand that number to another session until the answer of another number sent after the last resend copy has been received.
  Discard old answers not being waited for. Stop scheduled resends of resolved requests, and do not later write old copies saved outside the transport.
  If draining or the half-cycle range cannot be determined, recover the transport and recover with a new SID (resource release is core §9).
- A resend uses the same byte string, including the header and payload. A changed request gets a new corr. Changing the content with the same corr is malformed.
- result_lost means it is unknown whether it was executed, so read the state before re-executing. The count and bytes of resend records are limited, and 0 entries are allowed.
  Do not count on always getting back the results of max_inflight requests. If the IDs of created resources and the like cannot be recovered, release the resources together with end of the same SID whose ownership can be confirmed, or release the unknown resources by switching to a new SID following the rules, and then make them again.
  Repeating a result_lost request automatically with a new corr can make a second one while the original resource remains. Reopening the connection alone does not initialize the lock, resources or resend order (transports §3).
- Treat all outstanding requests on a transport where resending was given up as of unknown result. On recovery, check the boot_id, and read the list of resources and the state before deciding the next step.
- The host decides the number of resends and the interval. When a candidate with a CRC mismatch arrives, the identical request may be resent before the waiting time.

- **Receive amount on serial ports**: the OS serial driver may silently drop data without an error when the amount that arrives at once exceeds the driver's receive amount
  (some Linux drivers drop on bursts of about 8 KiB). On serial ports, keep the expected amount of answers to outstanding requests (concurrency ×
  frame limit) and the min_bytes of subscriptions small (guideline: answers 6 KiB or less, min_bytes 2 KiB or less), and prefer vendor bulk for large transfers.
  The probe's max_inflight and window are the limits of the probe's reception, not of the host's.

## 9. What the host does for each refusal

rejected means the request was not accepted; completed failed / partial means it was executed but not all of it worked (core §4.2). Header,
resend table and session refusals come in this order. For a request to which 2 of the other reasons apply, the probe answers with any one of them (core §4.3): whatever the reason,
handle it by fixing or giving up. Unknown reasons are treated as failure (core §2.4).

| reason | Meaning (core §4.3) | What the host does |
|---|---|---|
| unknown_function (0x01) | That fn does not exist (also a fn pointed at in the payload) | The local fn mapping is stale or wrong. Do list again (fn numbers are valid only while the boot_id stays the same, core §7.2). Do not use that interface |
| unknown_operation (0x02) | That fn has no such op | An optional op the probe does not implement (core §1.2). Use optional ops after looking at ops (0x07) in describe. When you check ops and do not send, report the same failure as this answer, so that the caller sees one error either way |
| malformed (0x03) | The shape of the request is wrong | An error in your own encoding, or a value excluded in every revision. Do not resend as is; fix the request. Log the bytes of the request |
| unavailable (0x04) | Cannot be done in the current state or with the current resources | Read the TLVs: cause (1 pin in use, 2 limit of count or processing capacity, 3 not enough storage capacity, 4 bound into a group, 5 held by a setting, 6 wrong state, 7 not allowed by policy), channel, fn. Show them to the user, and release your own resources or change the order. For cause 5 the probe's settings (disable, output idle) hold it, so change the settings rather than the request (which one holds it is seen with get of the probe's settings). For cause 7, do not repeat the same request or force; go on to that product's connection and authorization procedure (§7). Show unknown causes as unknown (core §2.4) |
| window_exceeded (0x06) | window / max_inflight exceeded | It sent ahead beyond the probe's limit on this transport. Wait for answers, and resend with a new corr (core §5.1: a corrected request is sent with a new corr) |
| no_session (0x07) | No session holds the lock: your session ended (end, lease expiry, force) or the probe restarted | Everything the session made has been released (core §9). Open a new session and set up plan, attach and subscriptions again. Do not silently continue (§5). A restart is seen from the boot_id of open |
| locked (0x08) | Another session holds the lock | The payload has the remaining ms and, if any, the holder's string. Wait, report "in use" with the holder, or take it by force only when the user asked (§6) |
| session_required (0x09) | A request for an op that needs the lock had session_id 0 | An error: send with your session_id |
| no_resource (0x0A) | That resource number is unknown | The connection or stream closed, or the probe restarted. Discard the number and make the resource again (attach, open). Check long-held numbers with list ops (core §9) |
| unsupported (0x0B) | It is in the definition, but this probe cannot handle it | The tag of the payload shows what: 0x00 = a value of the fixed part, otherwise the tag of the critical TLV as received. channel / index TLVs may show which element. Look at describe and choose what the probe declares. Do not resend as is. In confirm, TLV 0x01 shows the revisions the probe handles (core §7.1) |
| result_lost (0x0C) | The answer to the resend is not remembered | Whether it was executed is unknown: read the state again (core §5.1) |
| Unassigned reasons | Undefined | Treat as failure |

- **completed failed / partial**: the payload is decided by the op (`status` and `done` for wires and targets, [common parts](../interfaces/oep-if-common.md) §3).
  For status line, usually lower the speed and attach again. For wait, continue later from `done`. For fault, read the cause and clear it. For timeout, review the limits.
  For state, first put the target in the needed state. Unknown status is failure.
- Interface-specific reasons (0x40 to 0x7F) are defined by each interface. There are none in v1.

## 10. Revisions, TLVs, unknown values

- **Protocol revision**: in the first confirm on a transport, send the range it handles, and after that send `min_rev = max_rev =` the revision in use
  (core §7.1). On rejected unsupported, TLV 0x01 shows the revisions the probe handles. The revision is per transport (per connection for TCP).
- **Optional ops**: use optional ops (marks / clear / mark / write of console, halt of riscv-dm and so on) only when they are set in ops of that fn's describe.
  Sending an op that is not set gives unknown_operation; prepare an alternative way so that it works even with a probe of minimal configuration (for example, a console with only open / read / close / streams)
  (core §1.2).
- **Interface revision**: list returns (name, instance, revision) per fn. Do not use interfaces with an unknown revision
  (core §2.8). A probe may offer an old revision under another fn, so choose the one you know. instance is an identifier per (name, revision) and allows gaps
  (core §7.2).
- **Reading answers**: after the fixed part comes a sequence of TLVs. Skip unknown tags. For non-repeating tags use the first, and also validate the structure and known lengths of the later ones (core §2.3). Sequences are `count × element`
  without element lengths, so read elements field by field as defined. Fixed shapes are not extended at the end. TLV values whose length differs from the definition are
  broken (core §2.3). New information comes in new tags. Treat a TLV with bit 7 set in an answer as an unknown tag.
- **Sending requests**: set the critical bit on TLVs without whose effect the request is meaningless, or that do harm if they have no effect (reset of attach, max_speed of scan and so on) (core §2.3).
  A probe that does not implement that tag refuses if it is critical, and otherwise silently ignores it. A probe that implements it checks the value regardless of the bit.
  pins and max_speed of attach are in the fixed part, so they are handled by fixed-part validation, not by this critical rule.
  Do not extend the value of a request TLV at the end (core §2.3). Do not repeat a non-repeating tag.
- **Unknown values in answers**: unknown resolution, outcome, status and reason are failure. Events of an unknown kind are discarded (seq is counted). Unknown values of other enums
  (cause, the kind of scan) are shown as unknown. Reserved bits of flags are ignored (core §2.4).
- **Booleans and text**: a non-zero boolean is read as true. Text in answers has control characters and invalid UTF-8 replaced before it is shown (core §2.1).

## 11. Operations that take time

- Every op ends with one answer. For ops that take time (run, capture configure, save, attach, scan, reset), wait until the answer comes.
  The wait is based on max_op_ms + host_wait_add_ms + the transfer time (core §4.4). Only when an operation sets a shorter limit for the whole request is that limit used.
- Time waiting for earlier requests on another transport is not included in the processing limit. Even for clock and the like with a short limit, when they wait for a long op on another transport, an answer within that limit from sending is not guaranteed.
  A host that knows of outstanding requests on another transport also takes that wait into account; when it does not know, it does not decide on a restart or double execution from a timeout alone, but recovers with core §5.1.
- During run, the probe answers no other requests ([OEP core](oep-core.md) §4.4). Execution, preparation and cleanup are included in max_op_ms, and the lease is not counted while the owner's own request is being processed.
  Waiting to send after the answer is built is counted. Lock-free queries or resends on another transport alone do not extend the owner's lease.
- Processing that sends many requests, such as writing, keeps the lock with ordinary requests or keepalive so that the lease does not run out.
  Operations that consume data, such as read_rx of I2C/SPI, also have unknown results if the answer is lost. If there is no resend record and it is result_lost, that frame may not be recoverable.
  Sending read_rx with a new corr consumes the next frame. Distinguish resending a request from reading new data.

If cleanup fails in a high-level debug op, the connection and the dependent console stream close, and unread output is also lost.
Move the logs you need to the host with console read before the operation and between executions. There is no guarantee of recovering even the crash log just before a wire fault.
When building a wait for halt from an abstract command or reset with raw dmi, put the whole sequence including the wait in one request (debug §4.1).

## 12. Notifications

- Subscribing needs the lock, and a subscription ends together with the session. A host that only monitors uses lock-free read.
- A subscription is sent to the fn of the interface that sends the notifications, with that fn's own ops: subscribe is op 0x01, unsubscribe is op 0x02 (the same numbers in every
  interface; the request does not carry the target fn). If these 2 are not set in ops of that fn's describe, that fn sends no notifications (sending them gives
  unknown_operation). Subscribing to the same fn again replaces the subscription entirely, and seq counts from 0 at each subscription (core §10.3).
- **Sort by role** (core §10.1): only answers (0x02) are matched by corr. For events (0x03) and data (0x04), bytes 1 to 2 are fn. Even while notifications
  keep coming, make sure the processing that waits for answers and the processing that reads input finish by their deadlines.
- **seq** is the serial number of frames per fn (u16, wrapping). A skip means notifications were lost inside the probe or on the way. For data, the stream's
  `position` also shows what was lost: if a frame's position does not match the end of the previous frame, the bytes in between were lost (core §10.2,
  [common parts](../interfaces/oep-if-common.md) §1.5).
- **Choosing min_bytes / max_delay_ms**: for data, the probe sends when min_bytes have accumulated or max_delay_ms has passed since the first byte (0 does not use that
  condition; if both are 0, it sends at once). Events are not batched and arrive right after the earlier answers (core §10.3). Larger batches mean fewer frames; shorter delays mean less waiting. On serial ports keep min_bytes
  small (the receive amount of §8).
- **Reading the probe's time**: read the probe's current time with clock of fn 0 (op 0x04) (core §7.6). It needs no lock; sent with session_id 0, it
  answers even without a session and even while another tool holds the lock, and touches no session, lock or lease. The answer is boot_id and uptime_ns.
  1. Read your own clock just before sending (t0), and again right after receiving the answer (t1).
  2. uptime_ns is a value of the probe's clock read somewhere between t0 and t1, so assign it the midpoint (t0 + t1) / 2, with uncertainty (t1 − t0) / 2.
  3. When accuracy is needed, read clock several times in a row and use the one with the shortest t1 − t0 (the round-trip delay varies, and the shorter the round trip, the surer the midpoint).
  4. Reading again some time apart, such as before and after a capture, shows the drift between the two clocks (how much faster one is). This is used to map the times of marks and segments (the probe's clock) to
     the host's time.
  5. If the boot_id of the answer differs from before, the probe restarted: it cannot be compared with earlier uptime_ns (core §6.5).
  It can be used the same way through a relaying broker: the broker does not answer clock itself but relays it to the probe, so the value is the probe's, and the relay delay is in the round trip
  (transports §1). Whether the probe is alive is seen from the waiting time for answers, and restarts from the boot_id of confirm, clock and open (core §6.5).
- Notifications are sent to the transport on which the subscription was received. Sending an open with the same session_id on another transport does not change the destination (core §6.2). Only subscribing again
  moves the destination (core §10.3). Even when a transport is closed and reopened (reopening TCP, replugging USB, §8), the subscription keeps sending to the closed
  transport, and that is discarded (transports §3). The host subscribes again on the new transport to every fn it wants to continue, with the same conditions
  (seq from 0; what was lost in between is seen from skips in seq and position).
- Continuous capture streaming has its own rules: when there is no room to send, the probe discards new segments entirely, and keeps sending what was taken before stop. After stop,
  even if the end of the received positions becomes equal to write_pos of status, that only shows the end was reached. Everything can be said to be received only when it was received without position skips
  (losses), or the missing parts were recovered with read ([capture](../interfaces/oep-if-capture.md) §2.1 rule 2).
  The probe may send a segment's data before that segment ends. When a track stops with an error (stopped reason 2, state 6), read status and
  discard the received data from write_pos on (a segment dropped within a segment is not data; capture §2.2). Keep the lock while
  receiving.

- **Capture bandwidth and formats** (capture §1, §1.3 to §1.4, §3.3, §3.9): the host learns the bandwidth from data_rate in the configure answer (streaming; otherwise computed from layout,
  block, carriage and rate), and judges for itself whether the OEP transport (notifications) and other functions have room. The probe does not know the host-side bandwidth and
  usage, so it does not lower the rate on the grounds of whether sending keeps up. If it does not keep up, gaps result (flags bit0 of the segment, dropped of status).
  Blocks of formats 1 / 2 have a decided length, but the last block of a segment can be short, so read in order from the start of the segment. With rearm 1,
  watch for skips in the record of triggered, and read the records again with op triggers (notifications can be dropped).

Capture generations are not reused within the same boot. When 0xFFFFFFFF is used up, existing data can still be read and released, but new starts are refused with cause 2 until restart.
After restart, check the boot_id, and configure again from a new session and plan (capture §0).

## 13. Plan and pins

- plan is per fn (`oep.probe.plan`, [plan](../interfaces/oep-if-plan.md) §2). plan_apply replaces only the assignments of the fns it names, and the plans of other fns remain. Capture can be added
  while receiving UART. To release, list the fns in plan_release (all if n = 0).
- Trying to take pins held by another fn or connection gives rejected unavailable, and nothing changes (core §8.1).
- Released pins go to the idle state: the probe's setting idle, or Hi-Z (core §8). For pins where the fixture wiring leaves the counterpart's input floating (TX connected to the DUT's RX
  and so on), make them pull-up inputs with the core setting `channel.{}.idle` and save (§15).
- A plan is a session resource and is released by end, lease expiry and force (core §9). The host's wiring settings can remain, but a running plan is not taken over.

## 14. Console

- On a console that provides marks, putting the reset kind 0x40 in the arg of from 3 reads from the last reset mark (common §1.2, console §2).
  In configurations that do not provide marks, read with from 0 from a position the host keeps, and record the boundaries of operations in the host-side log.
- When a monitor closes once and comes back, it reads from the position it read last time.
- If the start of the answer is ahead of the requested position, the difference is the amount lost. Keep it in the display.
- For display times use the time received (the probe has no per-byte times).
- **Sending input**: write returns as accepted what entered the probe's send queue (whose size the probe decides) ([console](../interfaces/oep-if-console.md) §2).
  If accepted is less than count, wait a little and send the rest (the queue frees up only by what the target
  received: in dmseq, 2 bytes per answer to one frame of the target; in DMDATA, 3 bytes per answer to one slot). accepted does not mean the target received it:
  whether it arrived is seen from the console output (echo and so on).
- **Whether a dmseq console is answering**: a target that outputs or looks for input emits a frame at least once per the long wait plus the short wait
  (the "timeout" of [dmseq](../interfaces/target-console-dmseq.md)). If no valid frame has been read for 3 s while unsynchronized, the user
  may be told that the dmseq console is not answering. A target that neither outputs nor reads input emits nothing, so this is not evidence that
  there is no console.
- **Limits of SDI and DMDATA**: these 2 mechanisms have no numbers on slots, so when a wire write is lost, the same slot can arrive twice (duplication), and in DMDATA
  input bytes carried in an answer can be lost. If neither duplication nor loss is allowed, use dmseq ([dmseq](../interfaces/target-console-dmseq.md)).
- **When the hart is halted**: the probe does not read the console while the hart is halted ([console](../interfaces/oep-if-console.md) §3). If you change
  DATA0 / DATA1 using abstract commands with dmi, write back the original values before running the hart ([wire and debug](../interfaces/oep-if-debug.md) §4).

## 15. Probe settings

The core coordinates the settings (core §13). Items are declared by the core (fn 0) and by interfaces (their fn), and are read and written with get/set/unset/save/state of fn 0.
When a port is made pass-through by a pass-through item ([fixture](../interfaces/oep-if-fixture.md) §2.1, [console](../interfaces/oep-if-console.md) §2.1), a host that opened that port
reads and discards bytes outside frames (the target's output) as noise. If a session's requests are sent from that port, pass-through stops for that session.
Runtime settings of wiring and UART are managed by the host.

1. Read setting and setting_choice in the describe of fn 0 and of each fn. The k-th setting of each fn is its item number k; look up the number from the name (look it up again per boot_id).
   Look up channel names with channel_name of fn 0, and transport names (core §13.3) from the list of transports.
2. Read the count values of get, and read the trailing extension TLVs separately. If more, add count to first and continue.
   If the generation changes midway, read again from the start. The generation is a change counter within the boot, not a hash the host computes.
   Values do not carry where they came from (core §13.4). The values of a probe without set/unset in the ops of fn 0 cannot be changed.
3. Compare value by value with the wanted content, and do nothing if the same. For changes, take the lock and send counted set/unset. The values of one request are accepted all together, or nothing changes.
   A value is `fn, number, key, len, data`, a container separate from the outer TLVs.
4. save only if you want to save. If state is provided and saved_generation is equal to the current generation, it is saved.
   If the content is the same, the probe skips needless writes. To erase the save, unset all user values and save.
5. Export the settings before updating the firmware, and import them after the update ([settings file](oep-settings-file.md)). If state shows partial application or an unreadable state,
   check the values in effect with get, and import again from the exported file.
   Do not assume that independent disable/idle all disappeared because of an invalid label and the like.
6. For a probe without saving, a file the user chose may be imported at every connection.

An idle output stays in effect on free pins even after the host leaves. Check the wiring and levels before saving.

## 16. Combining wire and target operations

State explicitly the connection number returned by the wire's attach in requests to the corresponding target fn. Do not use the wire's fn number as the target's fn number.
Even with several connections, choose the saved number per request, and do not implicitly use the last connection.

A minimal arm-adi probe provides only transfer. If read_block/write_block are not in ops, the host builds AP selection, configuration and the collection of posted reads with transfer.
If there are block operations, use them within their max_length. Distinguish building something from unimplemented optional operations from re-executing an operation that failed.
A failed write or done 0 does not guarantee there was no effect on the target, so after a failure do not automatically repeat the same write with another operation.
The only exception is groups defined to end in the same state as once however many times they are executed (in riscv-dm, the DM's working registers while the hart is halted, and reads and writes of
registers with no effect besides the value, [wire and debug](../interfaces/oep-if-debug.md) §4.1). On wires that fail easily, read back after a write with the same group
to check, and if it cannot be confirmed, redo that group.
Chip-specific procedures and recovery handled with raw transfer/dmi are managed by the host-side project.
