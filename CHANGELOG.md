# Changelog

## Unreleased

- planは残る割当とGPIOの出力を保ち、動作中の配線変更を拒否する。captureの設定は役割変更で無効にし、UARTは明示configureから受信する。consoleはopen/read/close/streamsだけの実装を許し、マークと送信を任意にする。読めない終了マークと未使用open flagsを削除し、debug固有のマークをconsoleの番号空間へ移す。

- 凍結前レビューに基づき、資源番号だけをu32へ広げ、起動中の非再利用を維持する。connection/streamを参照する固定形と共有ベクタを更新し、65536以降の番号を検査する。corr/fnと要求10byte・応答5byteの見出しは維持する。
- 未使用のconfirm flagsを削除する。Hostは操作全体の上限max_op_msを基に応答を待ち、引数の待ち時間だけで内部再試行・準備・後始末を省かない。経路の実装範囲と起動時の使用禁止channelの除外を明確にする。

- Scope partial-frame completion to the same route. Other routes can reply independently; discard closed-route output rather than delaying a new subscription or carrying the old tail into its stream.

- Clarify subscription replacement/removal: discard old unsent notifications and complete an already-started frame before the operation's response.

- Permit bounded subscription storage and reject unsatisfiable data batching without changing an existing subscription. Clarify response priority at frame boundaries and that the notification staging ceiling is not a required queue allocation. Remove excessive buffer/DMA requirements from the probe guide.

- Explain recovery from a lost resource-creation result without requiring a replay cache: confirm ownership and end the session, or change sessions under the existing rules, before explicitly recreating resources.

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
- Make connections, console streams, plans and configured fixtures session-owned. Keep connection wiring/UART presets on the Host; standard Probe settings contain only pin disable/idle/label. Remove autonomous attach, bind and resource refcounts. Closing a console stream releases its buffers. Use 32-bit resource IDs and never reuse them within a boot; exhaustion rejects new resources until a reboot changes boot_id.
- Require explicit attach pins. Scan is optional, accepts a nonempty finite candidate list and returns prefix progress; remove implicit candidate search/skip. Attach never joins or evicts an existing connection. List entries omit refcounts and slot ownership; probe.config state reports storage state only.
- Assign roles 1/2/3/4 to request/result/event/data. Named-interface common ops occupy 01–0F (subscribe 01, unsubscribe 02); own ops start at 10 and may extend through FF. Compact common describe tags to 01–07. TLV IDs occupy 01–7F with bit 7 critical, and 00 is invalid. Removed pre-freeze numbers may be reused; post-freeze removals use retired ranges.
- Update normative documents, registry constants in C/C++/Python/JS and wire vectors. Cover independent counters past half a cycle, cache eviction, altered replay bytes, open history, session endings and explicit multiple-target attach.

- Keep only raw DMI mandatory on RISC-V targets and attach method 0 mandatory on wires. Advertise optional RISC-V attach-halt through features. Encode required attach pins/speed in its fixed 9-byte body; retain optional reset/idle/selection TLVs. Separate SWD read identity (DPIDR) from selected-target metadata and allow one connection per pin pair. Remove reset mode 1 and unstandardized search-retry diagnostics.
- Require temporary debug state restoration for success; attempt bounded cleanup on failure and close the connection/streams if cleanup cannot finish. Always lower haltreq after successful halt/reset-halt. SPI declares at least one supported mode and may reject concurrent workloads before effects if timing guarantees cannot be met. Bound restart by Probe-controlled readiness, with Host/OS/network recovery timed separately; MCU reset pin behavior is not an unconditional target-state guarantee.

- Capture start returns generation without a post-response blackout period; finite blocking capture can finish within the pending request under max_op_ms and normal lease rules. Capture read length fields use u16. Generations are not reused within a boot; exhausting them rejects start. Require release only with repeat mode, make analog calibration optional, and keep frontend/reference diagnostics optional while scale and nonzero skew remain required.

- Limit standard Probe settings to disable/idle/label, and remove mandatory idle drive strength. Count settings records in get/set and separate their trailing extension TLVs. Use a boot-scoped, nonreused change generation rather than a content hash. Keep save/erase/state optional for volatile-only implementations; restore independently valid pin settings with disable first and report partial loading. Wiring/UART/network profiles belong to the Host or separate definitions.

- Streaming capture adds required per-frame segment origin/count/time information, carries one segment per frame, and withholds unfinished trailing bytes. Keep immediate-only capture groups with bind/start/stop/status; remove unused trigger status fields and retain generation to identify old notifications. Defer coupled trigger/pretrigger and multirate to separate definitions.

- Keep UART port_speed optional for bridges without native USB, with a current port_state query to recover from historical replay results. Remove a universal four-second discovery wait; recovery includes request processing and frame drain time. Drain prior requests before try, finish frames before changing rate, require input heartbeat while committed, and do not cancel session-ended recovery with another session.

Python clients/virtual probes, Arduino firmware and other OEP endpoint implementations must follow this SPEC commit before claiming conformance to it. Existing hardware results remain evidence for their recorded older SPEC/firmware only. These changes do not freeze or tag v1 and do not update installed firmware.

After the first tagged release, this file records user-visible differences between releases, not commit-by-commit development history.
