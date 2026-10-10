# Changelog

## Unreleased

OEP v1 is under development and has not been frozen or released. Before the first release, the current normative documents and registry define the complete state; intermediate design history is available from Git history.

Breaking changes before the v1 freeze:

- Keep the 16-bit request correlation field and the 10-byte request / 5-byte result headers. Correlation increases independently per session and never wraps within it; hosts reserve an end request before exhaustion. Replays require identical request bytes, include open, and never clear the replay history or renew a lease. Small probes may bound retained request/result bytes and return result_lost without executing twice.
- Make serial OEP transports frame-only. Raw console traffic uses a separate endpoint; mixed USB CDC devices expose a bulk or HID discovery path. A broken TCP frame requires reconnecting. Brokers that answer OEP requests implement a complete endpoint contract.
- Make connections, console streams, plans and configured fixtures session-owned. Persistent plan/slot/UART items are passive presets; remove autonomous attach, bind and resource refcounts. Closing a console stream releases its buffers. Keep resource IDs at 16 bits and never reuse them within a boot; exhaustion rejects new resources until a reboot changes boot_id.
- Require explicit attach pins. Scan is optional, accepts a nonempty finite candidate list and returns prefix progress; remove implicit candidate search/skip. Attach never joins or evicts an existing connection. List entries omit refcounts and slot ownership; probe.config state reports storage/network state only.
- Assign roles 1/2/3/4 to request/result/event/data. Named-interface common ops occupy 01–0F (subscribe 01, unsubscribe 02); own ops start at 10 and may extend through FF. Compact common describe tags to 01–07. TLV IDs occupy 01–7F with bit 7 critical, and 00 is invalid. Removed pre-freeze numbers may be reused; post-freeze removals use retired ranges.
- Update normative documents, registry constants in C/C++/Python/JS and wire vectors. Cover independent counters past half a cycle, cache eviction, altered replay bytes, open history, session endings and explicit multiple-target attach.

Python clients/virtual probes, Arduino firmware and other OEP endpoint implementations must follow this SPEC commit before claiming conformance to it. Existing hardware results remain evidence for their recorded older SPEC/firmware only. These changes do not freeze or tag v1 and do not update installed firmware.

After the first tagged release, this file records user-visible differences between releases, not commit-by-commit development history.
