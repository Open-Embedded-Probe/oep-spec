# OEP interface: link v1

[日本語](oep-if-link.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **normative** (v1). For the freeze state and the language and compatibility policy, see [Versions and stability](../docs/versioning.md). The core is [OEP core](../docs/oep-core.md). The only definition of the numbers is `registry/oep-v1.toml`.

| Name | revision | Role | Target family |
|---|---:|---|---|
| `oep.probe.link` | 1 | tests the transport (link test) and raises the speed of a UART bridge port only for the session (port_speed) | used for every family |

- `oep.probe.link` is an optional interface. A probe with port_speed puts it in list. A probe MAY put it in list only for the link test. A probe
  puts at most one `oep.probe.link` in list.
- Its ops do not change the state of the probe, except for the port speed that port_speed changes.

## 1. Operations

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x10 | source | length(u32), [TLV] | len(u16), data, [TLV] | not needed | required |
| 0x11 | sink | count(u16), data, [TLV] | — | not needed | required |
| 0x12 | port_speed | baud(u32), step(u8: 0 try, 1 commit, 2 revert), verify_ms(u16), [TLV] | baud(u32: the speed actually applied), [TLV] | needed | optional |
| 0x13 | port_state | [TLV] | baud(u32), state(u8: 0 boot, 1 trying, 2 committed, 3 revert pending), [TLV] | not needed | required when port_speed is present |

port_state reads the current UART speed/phase of the transport of the request. On a kind other than 1 it is unavailable cause 6.
Phase 3 is the state where the revert conditions are met and the probe waits for a frame boundary. The host queries with a new corr and does not take a past port_speed success answer as the current phase.

## 2. Link test (source, sink)

source and sink are for measuring the speed of the transport. They do not change the state.

- **source**: data is len bytes, and byte k (k from 0) is k & 0xFF. len is the smaller of length and the max_frame (core §4.4) of the transport the request came on minus 7
  (the answer header 5 and len 2). If length is 0, len is 0.
- **sink**: count is followed by count bytes of any value. If count is larger than the bytes that follow, rejected malformed. The request fits in max_frame, so count is at most max_frame − 12 (the request header 10 and count 2). The answer is completed success with
  an empty payload.
- The host waits for the answer the same way as for other requests (core §4.4). It does not repeat it like confirm.

## 3. port_speed

port_speed raises the link speed of a UART bridge port above the boot speed (115200 bps, transports §4) only for the session. The speed of the probe's
fixture UART is separate (configure and settings of that interface). This section defines the **handshake**. Which speed to try, the criterion for treating it as passed,
and the criterion for reverting while in use are decided by the host.

**probe**

- It applies only when the transport the request came on is a port of transport kind 1 (UART bridge). port_speed from another transport is rejected unavailable (cause 6).
- If the nearest speed the UART can make differs from the request by more than `port_speed_tolerance_pct` (2 %), rejected unsupported. baud in the answer is the speed actually applied.
  The actual baud of step 0/1 is only a value higher than the boot speed. A request that cannot raise the speed is unsupported (fixed-part mark 0).
  verify_ms 0 with step 0 (try) is rejected malformed. With step 1 (commit) and step 2 (revert), verify_ms has no meaning and any value is accepted.
- The phase that port_state returns is managed per port. Acceptance of a step follows the table below. "Refuse" is unavailable cause 6, and the state does not change.
  Only one port is raised at a time; while another port is in phase 1/2/3, step 0 is refused with cause 6.

| Current phase | step 0 try | step 1 commit | step 2 revert |
|---|---|---|---|
| 0 boot | after answering at the current speed, switch to the baud of the answer, phase 1. Start the verify_ms of this request | refuse | refuse |
| 1 trying | refuse | receive the request with the same baud as tried at the new speed, phase 2 | after answering at the current speed (baud is the boot value), return to boot, phase 0 |
| 2 committed | refuse | refuse | the same revert procedure as phase 1 |
| 3 revert pending | refuse | refuse | refuse |

If the baud of step 1 differs from the tried value, it is also cause 6. Phase 3 is the state where a revert condition holds and the probe waits for a frame boundary.

- **Conditions under which the probe returns to the boot speed on its own** (it does not report the return):
  1. verify_ms passed while trying.
  2. After commit, no valid frame comes on that port for `port_speed_idle_ms` (3000 ms). The count restarts when a valid frame is received and when an answer is sent (while a request is
     being executed, it does not advance, whichever transport processes it). This is a rule of the revert timer of port_speed, distinct from the lease, which only the owner's requests stop (core §6.1).
  3. The session ended (end, lease expiry, the owner changed by force). For end and force, the probe returns after sending the answer.
- The verify/idle timers do not advance while a request is processed. Even when a revert condition is met, the probe does not break a frame being sent or received, or the answer to a request, by changing the speed in the middle.
  Once the revert is pending, the probe starts no new notification frame, and returns after the current send frame and receive frame end (or after a gap/resync of the reception).
  Phase 3 is not cancelled for any reason. During phase 3, step 0/1/2 is refused with cause 6, and the refusal does not change the revert conditions or the baud.
  A frame being received when phase 3 is entered is finished at the current speed up to the answer to that request, and the speed returns at that boundary. Reception that starts after the boundary is handled at the returned speed,
  and continued reception of new requests does not delay the return.
  In all cases, the header, resend and session checks of the core are done first (for example, a new request of a finished session is no_session).
  If a commit request during a try does not arrive by the verify deadline, it is refused with unavailable cause 6, and the speed returns at the frame boundary after the answer.
- Between try and commit, the resources and lock of the session do not change. Lost notifications are handled with the usual seq/position, and there is no duty to increase the retained amount.

**host**

Before trying, the host resolves all requests sent earlier on that transport and the results of resends. Until the answer to port_speed arrives, it sends no next request on the same transport.
It reads the answer to the end at the speed before the change. A notification being sent is completed by the probe at that speed before it answers.

1. On receiving the answer to try, the host switches to the requested baud (the baud of the answer if it cannot make it), waits `port_speed_switch_wait_ms` (20 ms) or longer, and then sends
   the next request at the new speed.
2. On receiving the success answer to revert, end, a force open to a different session_id, or an op that restarts the probe, the host switches the UART bridge port to the boot speed.
   An open with the same session_id keeps the session even with force, and does not return the speed (core §6.2). The host does not judge the current speed from a resent past success answer.

A host that only waits for notifications also sends valid requests such as keepalive at intervals shorter than port_speed_idle_ms to keep the committed speed.
Sending notifications alone does not extend the idle timer. This condition is independent even if the lease of the endpoint is long.
For opening again after a crash/answer loss, the host decides the wait including the processing time of earlier requests, frame transfer and the revert timer.
A host that does not handle port_speed is not required to wait a fixed long search time (transports §4).
If the answer to try/commit/revert is lost, the host recovers at the boot/tried speed with confirm and port_state with a new corr.
A resent result after the speed returned at the deadline is history; seeing success with the same corr does not mean the speed changes again (the resend rules of the core).
A new attempt starts with a new corr after checking the current phase. If the lock was lost, the usual session recovery is done first.
