# OEP standard interfaces: link v1

[日本語](oep-if-link.ja.md)

Status: **normative** (v1, before the freeze: until the v1 freeze a rule or a number may still change). Before the freeze, revision 1 alone does not identify a form: an implementation names the specification tag it implements ([versioning](versioning.md) §6). The core is [OEP core](oep-core.md). The only definition of the numbers is `registry/oep-v1.toml`.

| Name | revision | Role |
|---|---:|---|
| `oep.link` | 1 | Tests a transport (the link test), and raises the speed of a UART bridge port for the duration of a session (port_speed) |

- `oep.link` is an optional standard interface. A probe that offers port_speed lists it; a probe may also list it for the link test alone. A probe
  lists at most one `oep.link`.
- Its ops change no state of the probe, apart from the speed of a port that port_speed changes.

## 1. Operations

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x01 | source | length(u32), [TLV] | len(u16), data, [TLV] | Not required | yes |
| 0x02 | sink | count(u16), data, [TLV] | — | Not required | yes |
| 0x03 | port_speed | port(u8), baud(u32), step(u8: 0 try, 1 commit, 2 revert), verify_ms(u16), idle_ms(u32), [TLV] | baud(u32: the speed actually applied), [TLV] | Required | optional |

port_speed is optional, declared by ops of describe (core §1.2, §7.4). A probe that does not offer it answers it with unknown_operation.

## 2. The link test (source, sink)

source and sink exist to measure the speed of a transport. They change no state.

- **source**: data holds len bytes, byte k (k from 0) being k & 0xFF. len is the smaller of length and the most data that fits, with the rest of the
  answer, in one message of the max_frame of the transport the request came on (core §4.4). length 0 gives len 0.
- **sink**: count bytes of any value follow count. A count larger than the bytes that follow is rejected malformed. The answer is completed success with
  an empty payload (apart from ignored, core §2.3).
- The host waits for their answers as for any request (core §4.4); they are not repeated the way confirm is.

## 3. port_speed

port_speed raises the link speed of a UART bridge port above the boot speed for the duration of a session. Its uses are large writes, capture, and the
console (the time of the wire's block ops is determined by the round trips on the debug wire and does not change with the link). The speed of the probe's
fixture UART is separate (that interface's configure and settings). This section defines only the **handshake**. Which speeds to try as candidates, the
criterion for considering one passed, and the criterion for falling back while in use are decided by the host (reference procedure:
[host development guide](host-development-guide.md) §17).

**Definitions of terms**

- **Boot speed**: 115200 bps (core §3.4). The fallback for everything on the probe.
- **Candidate**: the sequence of speeds the host tries. The probe does not declare candidates (which speeds pass is determined by the converter chip and the OS, and the probe cannot know). This specification
  decides neither the candidates nor a default.
- **Flow**: the pair of direction (probe → host, host → probe, both directions) and concurrency n. A term for the host's verification and records (this specification does not decide the
  flow).
- **Broken candidate** (probe side): in the receiving of core §3.4, a candidate closed by 0x00 that does not decode or whose CRC does not match. Delimiters of 0x00 only, and bytes arriving outside
  0x00, are not counted.

**Probe**

- Only ports of transport kind 1 (UART bridge) are eligible.
- port: the index (core §7.5) of the transport this request came on (the transport TLV of the confirm answer, core §7.1).
- Refusals: port is not the port this request came from → rejected unavailable (cause 6). If the nearest speed the UART can produce differs from the request by more than 2 %, rejected unsupported. The answer's baud is the speed actually applied.
  verify_ms 0 in step 0 (try) is rejected malformed. In step 1 (commit) and step 2 (revert) verify_ms has no meaning and any value is accepted.
  A step of 3 or more is rejected unsupported (payload tag 0x00, core §2.5).
  Refusals when the lock is missing or different follow the order of core §4.3 (session_required, no_session, locked).
- The state is one of 3 per port: **boot / trying / committed**.
  - **Try** (step 0, accepted in the boot state): after finishing sending the answer at the current speed, switch to the baud of the answer and become **trying**. verify_ms starts
    with the value of this request.
  - **Commit** (step 1, accepted in the trying state, with the same baud, at the new speed): become **committed**. idle_ms starts with the value of this request (at most
    port_speed_idle_max_ms = 3000 ms. 0 and longer values are treated as the maximum).
  - **Revert** (step 2, in either trying or committed): send the answer (baud is the boot speed) at the current speed, then return to the boot speed.
  - A step that does not fit the state (commit in the boot state, commit after committed, revert in the boot state, try on a port that is trying or committed, commit with a baud different from
    the one being tried) is rejected unavailable (cause 6). The probe raises only one port at a time: if a try arrives on another port while one port is raised, it sends that answer,
    then returns the raised port to the boot speed and puts the new port into trying.
- **Conditions under which the probe returns to the boot speed by itself** (it does not announce the return):
  1. verify_ms passed while still trying.
  2. In the trying state, after one valid frame was received at the new speed, one broken candidate arrived on that port (broken candidates right after switching, before the first valid
     frame at the new speed, are not counted).
  3. After committing, no valid frame arrives on that port for idle_ms. idle_ms restarts whenever a valid frame is received and whenever an answer is sent (it does not advance while a request is being
     executed. Same as the lease, core §6.1).
  4. After committing, 3 broken candidates in a row with no valid frame in between (registry `port_speed_broken_max`).
  5. The session ended (end, lease expiry, the owner changed by force). For end and force, it returns after sending the answer.
- Between trying and committing, the session's resources and lock do not change. Raw transfer (core §3.4) is stopped for the duration of the session.

**Host obligations**

1. Send from a UART bridge (transport kind 1) port, holding the lock.
2. On receiving the answer to try, switch to the requested baud (or the baud of the answer if it could not be produced), wait 20 ms or more (registry `port_speed_switch_wait_ms`), then verify the new speed with confirm.
3. Within verify_ms, either send commit, or do not send it and wait for the probe to return (confirm at the boot speed after verify_ms has elapsed).
4. While raised, send keepalive or other requests at intervals shorter than half of idle_ms.
5. If an answer does not arrive within the wait time (core §4.4) at the raised speed, return to the boot speed and repeat confirm (up to port_speed_idle_max_ms + 1000 ms, registry `port_speed_confirm_extra_ms`).
   Even if the probe is still at the raised speed, a confirm at the boot speed reaches the probe as broken candidates, and it returns after 3 with no valid frame in between (return condition 4), so this converges.
   If it passes (same boot_id means it merely returned; different means a reboot), continue at the boot speed for that session. If confirm does not pass within the limit, it is a
   link failure (do not go back to the raised speed and wait again).
6. On receiving the answer to revert, or on receiving the answer to end, switch to the boot speed.
7. Which speeds to try as candidates, the flow for verification, the criterion for considering one passed, and the criterion for falling back while in use are decided by the host (reference: [host development guide](host-development-guide.md) §17).

Every host that opens a UART bridge port, whether or not it uses port_speed, repeats confirm there as core §3.4 says ("After a raised speed"), to wait out a speed a previous host raised.

The waits above (20 ms or more before the confirm that verifies a new speed, verify_ms, idle_ms, and the repeat of confirm) are times between requests, not
waits for an answer; they do not shorten the host's wait of core §4.4 for any request sent within them. The confirms of host obligation 5 are new requests,
each with a new corr, not resends (core §4.4).
