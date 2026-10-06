# OEP v1 glossary

[日本語](glossary.ja.md)

Status: out of date. Until the v1 freeze the Japanese text (.ja.md) is the working text; this English version will be regenerated from it at the freeze and becomes authoritative then.

Status: **guide** (not normative). Every term the specification defines or uses with a fixed meaning, with the section that defines it and the
Japanese term the translations use. The definitions here are short summaries; the linked section is the definition. Where they differ, the
normative text is right. This English text is authoritative; the Japanese version is its translation.

Documents: core = [OEP core](oep-core.md); common = [common parts](../interfaces/oep-if-common.md); debug = [wire and debug](../interfaces/oep-if-debug.md);
console = [console](../interfaces/oep-if-console.md); dmseq = [dmseq](../interfaces/target-console-dmseq.md); fixture = [fixture](../interfaces/oep-if-fixture.md);
capture = [capture](../interfaces/oep-if-capture.md); settings = [probe settings](../interfaces/oep-if-probe-config.md). Numbers are in `registry/oep-v1.toml`.

## Parties and layers

| Term | 日本語 | Meaning | Defined in |
|---|---|---|---|
| probe | probe | A device that speaks OEP; also any endpoint that answers OEP requests itself | core §1, §3.1 |
| host | host | Software that uses a probe | core §1 |
| target | target | What the probe is connected to (an MCU under development) | core §1 |
| broker | ブローカー | Host-side software that bundles several tools into one session; a host towards the probe | core §3.1 |
| relaying broker | 中継のブローカー | A broker that answers the session ops itself and relays everything else to one probe | core §3.1, §5.2 |
| core | core（本体） | What every probe and host implements; `oep.core`, fn 0 | core §0 |
| standard interface | 標準インターフェース | An interface with an `oep.` name whose numbers are in the project's registry | core §0, §13 |
| independent interface, extension | 独立したインターフェース、拡張 | An interface with a reverse-DNS name, defined by its own document | core §0, §13 |
| normative words | 規範の語 | MUST / MUST NOT / SHOULD / MAY as in RFC 2119 / 8174; Japanese する / しない / できれば / してよい | core §1.1 |
| conformance | 適合 | What a probe and a host must implement | core §1.2, [conformance](conformance.md) |

## Transports and frames

| Term | 日本語 | Meaning | Defined in |
|---|---|---|---|
| transport | 経路 | What carries OEP frames: UART bridge, USB CDC, built-in USB serial, vendor bulk, HID, TCP (`transport_kind` 1 to 6) | core §1, §3.1, §7.5 |
| serial port | シリアルの口 | A transport the OS sees as a serial device (kinds 1 to 3); carries OEP and raw bytes | core §1, §3.4 |
| UART bridge | UART bridge | The probe's UART brought out through a USB-UART converter | core §3.1 |
| built-in USB serial | 内蔵の USB シリアル | A USB serial port made by the MCU's hardware, whose descriptors the probe cannot choose | core §7.5 |
| vendor bulk | vendor bulk | The bulk pair of a class 0xFF / 0x4F / 0x45 interface | core §3.1, §3.3 |
| transport index | 経路の index | The number of a transport within a probe, invariant across firmware | core §7.5 |
| frame | フレーム | One message on a transport, with its wrapping | core §3.1 |
| COBS frame | COBS のフレーム | `0x00 COBS(message + CRC-16) 0x00`, used on serial ports | core §3.1 |
| length-prefixed frame | 長さつきのフレーム | `length(u16) message`, used on vendor bulk, HID reports and TCP | core §3.1 |
| candidate | 候補 | Bytes from a 0x00 to the next 0x00, decoded as a possible frame | core §3.1, §3.4 |
| broken candidate | 壊れた候補 | A candidate that does not decode or whose CRC does not match | link §3 |
| raw bytes | 生のバイト | Bytes on a serial port outside OEP frames (the target's console, etc.) | core §3.4 |
| raw transfer | 生の転送 | Forwarding raw bytes between a serial port and its bound flow; stopped while a session uses the port | core §3.4 |
| frame gap | フレームの途切れ | A pause of `probe_frame_gap_ms` inside a frame that restarts the probe's reader (not on TCP) | core §3.2 |
| resync | 区切りの立て直し | The host's recovery of delimiting on length-prefixed frames | core §5.1 |
| boot speed | 起動時の速さ | A UART bridge's speed at boot, `uart_bridge_boot_baud` | core §3.4, link §3 |
| port_speed | port_speed | The optional handshake that raises a UART bridge's speed for a session: try, commit, revert | link §3 |
| handshake | 握手 | The part of port_speed the specification defines (not the choice of speeds) | link §3 |
| flow | 流し方 | A direction and a concurrency, for the host's checks of a speed | link §3 |
| probing rule | 探りの規則 | On an unidentified device or port the host sends only confirm, and closes it without a valid answer | core §3.3 |
| named probe | 名指した probe | A probe the user names by its unit_id | core §3.3 |
| project's VID:PID | プロジェクトの VID:PID | `1209:4F45` (registry `usb`): the only USB ID by which a host identifies a probe automatically | core §3.3 |
| discoverable | discoverable | fn 0 describe tag: the probe also enumerates with the project's VID:PID | core §7.5 |

## Messages

| Term | 日本語 | Meaning | Defined in |
|---|---|---|---|
| role (of a frame) | role | The first byte: request 0x01, answer 0x02, event 0x05, data 0x06 | core §2.5, §4.1 |
| request | 要求 | A message from the host | core §4.1 |
| answer | 応答 | The probe's one reply to a request | core §4.2 |
| event | 出来事 | A notification with a kind and a fixed part | core §11.2 |
| data | データ | A notification carrying stream bytes with a position | core §11.2 |
| corr | corr | The u16 number the host gives a request, advanced by 1 (0 not used); the answer carries it | core §4.1 |
| fn | fn | The u16 number of an interface for the session; fn 0 is `oep.core` | core §1, §7.2 |
| op | op | The u8 number of an operation within an interface | core §1, §2.5 |
| resolution | resolution | completed (0x01) or rejected (0x00); 0x02 reserved | core §4.2 |
| outcome | outcome | success 0, failed 1, partial 2 of a completed answer | core §4.2 |
| rejected / refusal | 断り（rejected） | The request was not accepted | core §4.2 |
| reject reason | 断りの理由 | The detail of rejected (unknown_function … corr_reused) | core §4.3 |
| order of refusal | 断り方の順 | The fixed order in which a probe checks a request and refuses with the first reason that applies | core §4.3 |
| cause, holder_fn, holder_kind | cause、holder_fn、holder_kind | TLVs of an unavailable refusal: why, and what holds the resource | core §4.3 |
| status | status | The result of a wire or target operation: ok, wait, line, fault, timeout, state | common §3 |
| TLV | TLV | `tag(u8) len(u16) value`, one form for every length | core §2.2 |
| tag context | tag の文脈 | The space of tags: per (fn, op) | core §2.2 |
| critical | critical | Bit 7 of a request TLV's tag: the request means nothing unless it takes effect | core §2.2, §2.3 |
| ignored | ignored | Answer TLV 0x7F listing the non-critical request TLVs the probe ignored | core §2.3 |
| fixed part | 固定部分 | The part of a payload whose form (name, revision) determines | core §2.3, §2.7 |
| tail | 末尾、後ろ | The TLVs that follow the fixed part of a request, an answer, an event or data | core §2.3 |
| sequence, element | 並び、要素 | A counted list, `count × element`; an element has a fixed form and no length of its own | core §2.3 |
| bitmap | bitmap | Bit i is bit (i mod 8) of byte ⌊i/8⌋ | core §2.1 |
| boolean, text | 真偽値、文字列 | u8 0 / 1; UTF-8 without terminator, checked in requests | core §2.1 |
| unknown value | 知らない値 | How a reader treats values it does not know | core §2.4 |
| experimental value | 実験用の値 | 0xF0 to 0xFE in u8 enums, ops 0xF0 to 0xFF; never shipped or registered | core §2.5 |
| wrapping value | 一周する値 | seq, resource numbers: compared by serial-number arithmetic | core §2.6 |
| clock | 時計 | The probe's one clock: ns since boot (u64); all bits 1 = "not yet" | core §2.6a |
| revision | revision | Protocol revision (confirm) and interface revision (list); raised only when a fixed part changes | core §2.7, §7.1 |
| max_frame, window, max_inflight | max_frame、window、max_inflight | Per-transport limits on message length, outstanding bytes and outstanding requests | core §4.4 |
| wait floor | 待ち時間（の下限） | The least time a host waits for an answer | core §4.4 |
| transfer time | 転送の時間 | The part of the wait floor for a UART bridge's line speed | core §4.4 |
| resend | 送り直し | One resend with the same corr when an answer was broken or late | core §5.2 |
| resend table | 送り直しの表 | The probe's memory of recent answers for deduplication | core §5.2 |

## Sessions and resources

| Term | 日本語 | Meaning | Defined in |
|---|---|---|---|
| session | セッション | The right to hold the lock and change state, identified by session_id | core §1, §6 |
| session_id | session_id | The host's unpredictable non-zero u32 for one session | core §6.1 |
| lock | ロック | The one lock of a probe | core §6.1 |
| lease | lease | The expiry of the lock, renewed by requests | core §1, §6.1, §6.4 |
| lease expiry | 期限切れ | The lease ran out; the session's resources are removed | core §6.1, §9 |
| force | force | open that takes the lock from another session (not authentication) | core §6.4 |
| owner | owner | Display text attached to open, returned by lock_state and locked | core §6.4 |
| boot_id | boot_id | A value that changes at every boot | core §6.5 |
| resource, resource number | 資源、資源の番号 | What a session creates (plan, connections, streams…); u16 numbers in one space per probe | core §9 |
| lifetime | 寿命 | What happens to resources on end, expiry, force and reboot | core §9 |
| long operation | 長い操作 | Reserved for a later revision | core §10 |

## Discovery and declarations

| Term | 日本語 | Meaning | Defined in |
|---|---|---|---|
| confirm | confirm | The first request: `OEP?` / `OEP!`, revision, limits, boot_id | core §7.1 |
| list | list | The interfaces by name, with fn, instance and revision | core §7.2 |
| describe | describe | The declaration of an interface or (fn 0) of the probe | core §7.3 |
| declaration | 宣言 | What describe returns; unchanged while the boot_id is the same | core §7.3 |
| paging | ページング | Asking again with `first` while `more` = 1 | core §7.3 |
| name, label (of a name) | 名前、ラベル | `a-z 0-9 - .`, at least two labels separated by `.` | core §7.2, §13 |
| instance, `name#instance` | instance | The number of an interface among those with the same (name, revision) | core §7.2 |
| role_channels, channel_group | role_channels、channel_group | Which channels a role may use; fixed combinations | core §7.4 |
| features | features | u32 bits of optional functions of an interface that are not ops (modes, formats, notifications) | core §7.4 |
| ops | ops | The common describe tag 0x09 (base + bitmap) by which every fn declares the ops it offers | core §1.2, §7.4 |
| unit_id | unit_id | The unit's identifier, 1 to 32 of `a-z 0-9 -`, equal to the USB serial number | core §7.5 |
| `x-` unit_id | `x-` の unit_id | A unit_id that is not unique; not used for grouping or naming | core §7.5 |
| model, chip, firmware | model、chip、firmware | The kind of probe, its MCU, its firmware text | core §7.5 |
| max_op_ms | max_op_ms | The longest time the probe spends on one request | core §7.5 |
| reserved (channels), label (firmware) | reserved、label | Channels the probe uses itself; fixed channel names of the firmware | core §7.5 |
| address | アドレス | `oep://<unit_id>[/<slot name>]` | core §7.6 |
| link test | 線の試験 | The source and sink ops of `oep.link`, for measuring a transport | link §2 |

## Plan and pins

| Term | 日本語 | Meaning | Defined in |
|---|---|---|---|
| channel | channel | The u16 number of a pin of the probe | core §1 |
| plan | plan | Which channel is used for which role of which fn; held per fn | core §1, §8 |
| role (of a plan) | 役（role） | A function of a pin within an interface (RX, SWDIO, …) | core §8, §13 |
| role_assignment | role_assignment | plan_apply's TLV: fn, role, channel | core §8 |
| plan_roles | plan_roles | How many assignments the plan can hold | core §7.5, §8 |
| settings plan | 設定の plan | A plan put in place by the settings, changed only by them | core §8, settings §1 |
| idle state | 空きの状態 | The state of a pin no plan or connection holds: the settings' idle or Hi-Z | core §8 |
| resource contention | 資源の取り合い | Refusing what would take a held pin or resource | core §8.1 |
| drive strength, drive_levels | 出力の強さ、段 | Selectable strengths of mode 3 / 4 outputs | fixture §1.1 |

## Notifications and streams

| Term | 日本語 | Meaning | Defined in |
|---|---|---|---|
| notification | 通知 | Events and data the probe sends without a request | core §11 |
| subscribe, subscription | 購読 | Asking for one fn's notifications; ends with the lock | core §11.3 |
| seq | seq | Per-fn u16 serial of notification frames | core §11.2 |
| heartbeat | ハートビート | fn 0 event kind 0x01 with boot_id and uptime | core §11.2, §11.3 |
| positioned stream | 位置つきのストリーム | Bytes numbered by a u64 position that never goes back within a boot | common §1 |
| position | 位置 | The serial number of a stream byte | common §1.1 |
| gap | gap | read's flag: the requested position was pushed out | common §1.2 |
| mark | マーク | A record of an event at a stream position (reset, attach, lost…) | common §1.3 |

## Wires and targets

| Term | 日本語 | Meaning | Defined in |
|---|---|---|---|
| wire | 線（wire） | A debug wire interface `oep.wire.*` that creates connections | debug §0 |
| connection | 接続（connection） | A connection to a target, created by attach | common §2 |
| user (of a connection) | 使っているもの | A session or a slot that keeps a connection open | common §2 |
| pin role | ピンの役 | 1 SWDIO, 2 SWCLK, 3 reset | debug §1 |
| combination | ピンの組 | The channels of one try of a wire | debug §1 |
| scan, attach, detach | scan、attach、detach | Find targets; connect; leave | debug §1, §2 |
| seat, max_connections | 席、max_connections | How many connections a wire holds at once | debug §1 |
| attach budget, scan budget | attach の予算、scan の予算 | `attach_budget_ms`, `scan_budget_ms` | debug §1 |
| bring-up, search_retries | 立ち上げ、search_retries | Wake, choosing and verifying the speed; its extra attempts | debug §1 |
| scratch register | スクラッチのレジスタ | Registers used to verify writes, restored afterwards | debug §1 |
| target_id, scheme | target_id、scheme | An identifier the probe read, and how it was read | debug §1 |
| attach_writes_unbounded | attach_writes_unbounded | Features bit of a wire attached through another debugger | debug §1 |
| exchange | やり取り | One frame, packet or wake pattern on a wire | debug §2 |
| wire loss | 線切れ | No answer from the wire for `wire_lost_ms` of real time | debug §2 |
| free state, rest state | 放した状態、休み方 | Lines undriven after a failure; the lines' state between exchanges | debug §2, §3, §5 |
| idle_clock | idle_clock | How a two-wire clock rests (high or low) | debug §3 |
| mechanism | mechanism（方式） | How a console is carried: SDI, DMDATA, dmseq | console §1, §3 |
| dmseq | dmseq | Console framing with sequence bits and CRC-8 over DATA0 / DATA1 | dmseq |

## Capture

| Term | 日本語 | Meaning | Defined in |
|---|---|---|---|
| track | トラック | One logic or analog capture interface | capture, top |
| mode | mode | one-shot, repeat, streaming | capture §2.1 |
| segment | 区画 | A part of a capture with its own time and sample count | capture §2.2 |
| generation | 世代 | Advanced at every start; read and release name it | capture, top |
| capture-group | capture-group | Starts several tracks together | capture §4 |

## Probe settings

| Term | 日本語 | Meaning | Defined in |
|---|---|---|---|
| settings, item, key | 設定、項目、キー | A sequence of items; set replaces items per key | settings §1, §2 |
| label (item) | label | A channel name given by the settings | settings §1 |
| idle (item) | idle | A channel's idle state: Hi-Z, pulls, output low / high | settings §1 |
| disable | disable | A channel the probe never uses | settings §1 |
| slot | スロット | A registration of a place where a target is connected | settings §1.1 |
| slot lock | 錠 | A target_id mask and value a slot's connection must match | settings §1.1 |
| attach policy | attach の方針 | host or at boot | settings §3.1 |
| boot_reset | boot_reset | A slot's one retry with the reset line after boot | settings §1.1, §3.1 |
| bind | bind | What a serial port sends: last-reset, manual, mixed | settings §1.2 |
| position of the port | 口の位置 | Where a bind's port is in the stream it sends | settings §1.2 |
| line names | 線の名前 | `nrst`, `power_hi`, `power_lo`; `x-` for others | settings §1.3 |
| canonical form, hash | 正規形、hash | Sorted items and their CRC-32 | settings §2 |
| save, erase | 保存、消去 | Writing / deleting the stored copy | settings §2 |
| storage_state, unreadable reason | storage_state、読めない理由 | Whether the save is present and applied | settings §3.3 |
| slot_state, bind_state | slot_state、bind_state | The current state of slots and binds | settings §3.2, §3.3 |
