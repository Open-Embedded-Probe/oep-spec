# Changelog

## Unreleased

- Clarify in the host guide that a retained success after lease expiry is a historical result and does not restore ownership or resources.

- Add a generic extension-definition and three-layer testing guide with a small stateless example. Align the conformance checklist with stable, sparse instance identity.

- Explain bounded resource-ID allocation using a counter and only live entries; retain boot-scoped nonreuse and clarify that request/plan counts are not allocation counts. Correct the host guide's name#instance example to refer to an identifier rather than list position.

- Make instance a stable, possibly sparse identifier within (name, revision), independent of fn order. Resolve saved interface identities explicitly and do not reuse removed logical identities. Clarify that breaking requiredness, state or resource-lifetime contracts also requires a revision change after freeze; wire widths remain unchanged.

- 応答の共通 TLV 拡張規則が、固定部分の空の成功応答と rejected にも掛かることを明記し、共有ベクタと独立した検査を追加。

OEP v1 is under development and has not been frozen or released. Before the first release, the current normative documents and registry define the complete state; intermediate design history is available from Git history.

Breaking changes before the v1 freeze:

- Reject fixed-result batches before execution when their required result cannot fit the route's max_frame, even if the request fits. DMI and ARM transfer count result-producing reads before target access; defined paging/prefix operations retain their own rules.
- Allow transfer-only ARM ADI targets; paired block operations are optional through ops. Permit resources to cross fn boundaries only when their interface definitions explicitly establish compatibility, including wire-created connections consumed by target interfaces. Failed external writes do not guarantee absence of effects and must not be blindly reexecuted.
- Permit a receive-only fixture UART with configure/read/status. Make marks/clear/mark/write optional through ops; mark requires marks, and omitting write also omits the TX pin role. Unplanned UART operations reject unavailable. Retain the existing operation numbers and payloads, and keep target-console requirements independent.
- Separate mandatory replay order state from optional request/result byte retention. Permit zero replay entries and return result_lost for old requests without reexecution; max_inflight limits unresolved input, not cache capacity. Allow bounded numeric widths in extension definitions rather than requiring all hardware values to be at least 32 bits. Existing standard-interface field widths remain unchanged.
- Keep 16-bit corr and 10-byte request / 5-byte result headers. Correlation advances independently per session using a half-range modulo comparison, skipping zero; wrapping does not end a session or release resources. Hosts bound unresolved request distance, prevent reuse while old replies may remain, and never reinsert resolved requests or old connection queues. Remove the unused list-entry flags byte. Replays require identical request bytes, include open, and never clear replay history or renew a lease. Small probes may bound retained request/result bytes and return result_lost without reexecution within the Host/transport contract.
- Make serial OEP transports frame-only. Raw console traffic uses a separate endpoint; mixed USB CDC devices expose a bulk or HID discovery path. A broken TCP frame requires reconnecting. Brokers that answer OEP requests implement a complete endpoint contract.
- Make connections, console streams, plans and configured fixtures session-owned. Persistent plan/slot/UART items are passive presets; remove autonomous attach, bind and resource refcounts. Closing a console stream releases its buffers. Keep resource IDs at 16 bits and never reuse them within a boot; exhaustion rejects new resources until a reboot changes boot_id.
- Require explicit attach pins. Scan is optional, accepts a nonempty finite candidate list and returns prefix progress; remove implicit candidate search/skip. Attach never joins or evicts an existing connection. List entries omit refcounts and slot ownership; probe.config state reports storage/network state only.
- Assign roles 1/2/3/4 to request/result/event/data. Named-interface common ops occupy 01–0F (subscribe 01, unsubscribe 02); own ops start at 10 and may extend through FF. Compact common describe tags to 01–07. TLV IDs occupy 01–7F with bit 7 critical, and 00 is invalid. Removed pre-freeze numbers may be reused; post-freeze removals use retired ranges.
- Update normative documents, registry constants in C/C++/Python/JS and wire vectors. Cover independent counters past half a cycle, cache eviction, altered replay bytes, open history, session endings and explicit multiple-target attach.

Python clients/virtual probes, Arduino firmware and other OEP endpoint implementations must follow this SPEC commit before claiming conformance to it. Existing hardware results remain evidence for their recorded older SPEC/firmware only. These changes do not freeze or tag v1 and do not update installed firmware.

After the first tagged release, this file records user-visible differences between releases, not commit-by-commit development history.
