# OEP v1 glossary

[日本語](glossary.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative). It lists the terms the specification defines and the terms it uses with a fixed meaning, with the section that defines each and the correspondence between English and Japanese.
The meaning here is a short summary; the definition is the linked section. Where they disagree, the normative text is right.

Documents: core = [OEP core](oep-core.md), common = [common parts](../interfaces/oep-if-common.md), debug = [wire and debug](../interfaces/oep-if-debug.md),
console = [console](../interfaces/oep-if-console.md), dmseq = [dmseq](../interfaces/target-console-dmseq.md), fixture = [fixture](../interfaces/oep-if-fixture.md),
capture = [capture](../interfaces/oep-if-capture.md), settings = [core](oep-core.md) §13, plan = [plan](../interfaces/oep-if-plan.md),
restart = [restart](../interfaces/oep-if-restart.md), link = [link](../interfaces/oep-if-link.md). Numbers are in `registry/oep-v1.toml`.

## Participants and layers

| Japanese | English | Meaning | Defined in |
|---|---|---|---|
| probe | probe | A device that speaks OEP. Also every endpoint that answers OEP requests itself | core §1, transports §1 |
| host | host | Software that uses a probe | core §1 |
| target | target | What the probe is connected to (the MCU under development) | core §1 |
| ブローカー | broker | Software that bundles the use of several tools. As an endpoint that answers OEP requests itself it is a probe; as the side that uses downstream probes it is a host. It distinguishes the loss of a client's transport from the loss of a downstream connection it uses | transports §1, §3 |
| 中継のブローカー | relaying broker | A broker that does not answer OEP requests itself but relays requests and answers to a downstream probe. Towards the downstream it is a host | transports §1 |
| core（本体） | core | What every probe and host implements. It has no name, is spoken through fn 0 and is not in list. Its version is the protocol revision | core §0 |
| oep インターフェース | oep interface | Short for an interface whose name begins with `oep.`. The project's own; it has a short `oep.` name instead of a reverse-DNS name. Treated like any other interface | core §12 |
| 独自のインターフェース | third-party interface | An interface with a reverse-DNS name, defined by the document of whoever defined it. Anyone who extends OEP uses this. Treated like any other interface | core §12 |
| 規範の語 | normative words | MUST / MUST NOT / SHOULD / MAY of RFC 2119 / 8174. In Japanese する / しない / できれば / してよい | core §1.1 |
| 適合 | conformance | What a probe and a host must implement | core §1.2, [conformance](conformance.md) |

## Transports and frames

| Japanese | English | Meaning | Defined in |
|---|---|---|---|
| 経路 | transport | What carries OEP frames: UART bridge, USB CDC, built-in USB serial, vendor bulk, HID, TCP (`transport_kind` 1 to 6) | core §1, transports §1, core §7.5 |
| シリアルの口 | serial port | A transport the OS sees as a serial device (kind 1 to 3). It carries only OEP frames | core §1, transports §4 |
| UART bridge | UART bridge | The probe's UART brought out through a USB-UART converter chip | transports §1 |
| 内蔵の USB シリアル | built-in USB serial | A USB serial port made by the MCU's hardware. The probe cannot choose its descriptors | core §7.5 |
| vendor bulk | vendor bulk | A bulk pair of an interface with class 0xFF / 0x4F / 0x45 | transports §1, §3 |
| 経路の index | transport index | The number of a transport within the probe. It does not change across firmware | core §7.5 |
| フレーム | frame | One message on a transport, and its wrapping | transports §1 |
| COBS のフレーム | COBS frame | `0x00 COBS(message + CRC-16) 0x00`. Used on serial ports | transports §1 |
| 長さつきのフレーム | length-prefixed frame | `length(u16) message`. Used on vendor bulk, HID reports and TCP | transports §1 |
| `_oep._tcp` | `_oep._tcp` | The DNS-SD service a probe listening on TCP advertises over mDNS when it advertises itself. The port in SRV, `unit_id` in TXT | transports §3 |
| 候補 | candidate | The bytes from one 0x00 to the next 0x00. Decoded as something that may be a frame | transports §1, §4 |
| 壊れた候補 | broken candidate | A candidate that does not decode or whose CRC does not match | transports §4 |
| 生のバイト | raw bytes | Bytes a separate raw endpoint carries. Never mixed into an OEP serial transport | transports §4 |
| フレームの途切れ | frame gap | A pause of `probe_frame_gap_ms` in the middle of a frame. On serial ports and vendor bulk the probe starts reading anew (on TCP it does not, and on HID it starts anew at the report's first) | transports §1, §2 |
| 区切りの立て直し | resync | On length-prefixed frames, the host regaining the frame boundaries | transports §5 |
| 起動時の速さ | boot speed | The speed of a UART bridge at boot, `uart_bridge_boot_baud` | transports §4, link §3 |
| port_speed | port_speed | An optional handshake that makes a UART bridge faster only for the session: try, commit, revert | link §3 |
| 握手 | handshake | The part of port_speed the specification defines (not how to choose the speed) | link §3 |
| 流し方 | flow | Direction and concurrency. Used when a host checks speeds | link §3 |
| 探りの規則 | probing rule | Send only confirm to a device or port not yet identified, and close it if no correct answer comes | transports §3 |
| 名指した probe | named probe | A probe the user named by unit_id | transports §3 |
| プロジェクトの VID:PID | project's VID:PID | `1209:4F45` (registry `usb`): the only USB ID by which a host identifies probes automatically | transports §3 |

## Messages

| Japanese | English | Meaning | Defined in |
|---|---|---|---|
| role | role (of a frame) | The first byte: request 0x01, answer 0x02, event 0x03, data 0x04 | core §2.5, §4.1 |
| 要求 | request | A message from the host | core §4.1 |
| 応答 | answer | The probe's one reply to a request | core §4.2 |
| 出来事 | event | A notification with a kind and a fixed part | core §10.2 |
| データ | data | A notification that carries stream bytes with a position | core §10.2 |
| corr | corr | The u16 number a host puts on a request. It cycles skipping 0, and the distance between outstanding requests is less than half a cycle. The answer has the same value | core §4.1 |
| fn | fn | A u16 that points at an interface while the boot_id stays the same. fn 0 is the core (not in list) | core §1, §7.2 |
| op | op | The u8 number of an operation within an interface | core §1, §2.5 |
| resolution | resolution | completed (0x01) or rejected (0x00) | core §4.2 |
| outcome | outcome | success 0, failed 1, partial 2 of completed | core §4.2 |
| 断り（rejected） | rejected / refusal | The request was not accepted | core §4.2 |
| 断りの理由 | reject reason | The detail of rejected (unknown_function … result_lost) | core §4.3 |
| 断り方の順 | order of refusal | Header, resend table, session order. Otherwise the probe refuses with any one of the reasons that apply | core §4.3 |
| cause | cause | The TLV of an unavailable refusal: the reason (pin in use, limit, held by a setting, wrong state…) | core §4.3 |
| status | status | The result of wire and target operations: ok, wait, line, fault, timeout, state | common §3 |
| TLV | TLV | `tag(u8) len(u16) value`. One shape for every length | core §2.2 |
| tag の文脈 | tag context | The tag space is per payload definition: (fn, op) for requests and answers, fn for describe and data, (fn, kind) for events | core §2.2 |
| critical | critical | Bit 7 of the tag of a request TLV: a probe that does not implement the tag refuses (without the mark, it ignores it) | core §2.2, §2.3 |
| 固定部分 | fixed part | The part of a payload whose shape (name, revision) decides | core §2.3, §2.8 |
| 末尾、後ろ | tail | The TLVs that follow the fixed part of a request, answer, event or data | core §2.3 |
| 並び、要素 | sequence, element | A counted sequence, `count × element`. An element has a fixed shape and does not carry its own length | core §2.3 |
| bitmap | bitmap | Bit i is bit (i mod 8) of byte ⌊i/8⌋ | core §2.1 |
| 真偽値、文字列 | boolean, text | u8 0 / 1 (anything not 0 is read as true). UTF-8 without a terminator | core §2.1 |
| 知らない値 | unknown value | How a reader handles a value it does not know | core §2.4 |
| 一周する値 | wrapping value | corr, seq and so on: compared with serial number arithmetic. Resource numbers are not reused within one boot | core §2.6, §4.1, §9 |
| 時計 | clock | The probe's one clock: ns since boot (u64). All bits 1 means "not yet". The current value is read with the op clock | core §2.7, §7.6 |
| revision | revision | The protocol revision (confirm) and the interface revision (list). Raised only when an existing contract breaks (when a fixed shape, mandatory ops, state transitions, resource lifetimes and so on change) | core §2.8, §7.1 |
| max_frame、window、max_inflight | max_frame, window, max_inflight | Per transport, the limits on message length, outstanding bytes and outstanding requests | core §4.4 |
| 待ち時間（の下限） | wait floor | The shortest time a host waits for an answer | core §4.4 |
| 転送の時間 | transfer time | The part of the waiting time for the line speed of a UART bridge | core §4.4 |
| 送り直し | resend | Sending again with the same corr when an answer was broken or late (the probe answers from its table) | core §5.1 |
| 送り直しの表 | resend table | The recent answers a probe remembers to prevent double execution | core §5.1 |

## Sessions and resources

| Japanese | English | Meaning | Defined in |
|---|---|---|---|
| セッション | session | The right to change state while holding the lock. Identified by session_id | core §1, §6 |
| session_id | session_id | An unpredictable non-zero u32 a host chooses for one session | core §6.1 |
| ロック | lock | One lock per probe | core §6.1 |
| lease | lease | The deadline of the lock. Extended by requests | core §1, §6.1, §6.4 |
| 期限切れ | lease expiry | The lease ran out. The session's resources are released | core §6.1, §9 |
| force | force | An open that takes the lock away from another session (not authentication) | core §6.4 |
| owner | owner | A display string attached to open. Returned in lock_state and locked | core §6.4 |
| boot_id | boot_id | A value chosen so that it changes at every boot | core §6.5 |
| 資源、資源の番号 | resource, resource number | Things a session creates (plan, connection, stream…). The number is a u32 in one space per probe, increasing from 1. 0 is not assigned, and numbers are not reused within one boot | core §9 |
| 寿命 | lifetime | What happens to a resource on end, expiry, force and restart | core §9 |

## Discovery and declarations

| Japanese | English | Meaning | Defined in |
|---|---|---|---|
| confirm | confirm | The first request: `OEP?` / `OEP!`, revision, limits, boot_id | core §7.1 |
| clock（op） | clock (op) | op 0x04 of fn 0. Mandatory, needs no lock, can be sent with session_id 0. The answer is boot_id and uptime_ns. A relaying broker also relays it to the probe | core §7.6, transports §1 |
| uptime_ns | uptime_ns | The probe's current time in the clock answer (ns since boot). A value read between the probe receiving the request and sending the answer | core §2.7, §7.6 |
| list | list | The interfaces by name, with their fn, instance and revision | core §7.2 |
| describe | describe | The declaration of an interface, or (on fn 0) of the whole probe | core §7.3 |
| 宣言 | declaration | What describe returns. It does not change while the boot_id stays the same | core §7.3 |
| ページング | paging | While more = 1, ask again with `first` advanced. A first past the end gets 0 elements and more 0. marks and segments ask again with from_serial (last serial + 1) | core §7.3, common §1.3 |
| 名前、ラベル | name, label (of a name) | `a-z 0-9 - .`. Two or more labels separated by `.` | core §7.2, §12 |
| instance、`name#instance` | instance | The number within interfaces of the same (name, revision). The written form is in the host guide §5.3 | core §7.2 |
| role_channels、channel_group | role_channels, channel_group | The channels a role can use, a fixed group | core §7.4 |
| features | features | u32 bits of an interface's optional functions that are not ops (modes, formats) | core §7.4 |
| ops | ops | Common describe tag 0x07 by which every fn declares the ops it has (base + bitmap, not beyond op 0xFF) | core §1.2, §7.4 |
| unit_id | unit_id | The identifier of the unit. 1 to 32 of `a-z 0-9 -`, equal to the USB serial number | core §7.5 |
| `x-` の unit_id | `x-` unit_id | A unit_id that is not unique. Used neither for grouping nor for naming | core §7.5 |
| model、chip、firmware | model, chip, firmware | Free strings for the kind of probe, its MCU and its firmware | core §7.5 |
| max_op_ms | max_op_ms | The longest processing time of one request itself, including its validation, internal retries, execution, cleanup and building the answer. Waiting for earlier requests on the same or another transport and the transfer time of the transport are excluded | core §4.4, §7.5 |
| アドレス | address | `oep://<probe>[/<port>[/<target>]][?via=<transport>]`. probe is the unit_id, port is the `S` of the settings label `S.N`, target is a unit name the host decides, via is the transport that reaches it. The location is always written in full; comparison is case-insensitive and leaves out via | host guide §5.3 |
| 線の試験 | link test | The source and sink ops of `oep.probe.link`. They measure a transport | link §2 |
| restart | restart | An op of `oep.probe.restart`. Sends the answer first and initializes the probe's internals within restart_max_ms. OS enumeration and the host's wait for reconnection are separate | restart §2 |

## Plan and pins

| Japanese | English | Meaning | Defined in |
|---|---|---|---|
| channel | channel | The u16 number of a probe pin. 0 to channels − 1 | core §1, §7.5 |
| plan | plan | Which channel to use for which role of which fn. Kept per fn. `oep.probe.plan` | plan §2 |
| 役（role） | role (of a plan) | The function of a pin within an interface (RX, SWDIO…) | core §7.4, §12, plan head |
| role_assignment | role_assignment | The TLV of plan_apply: fn, role, channel | plan §2.1 |
| plan_roles | plan_roles | The number of assignments a plan can hold at once | plan §1, §2.1 |
| 空きの状態 | idle state | The state of a pin no interface has taken: the saved setting idle, or Hi-Z | core §8 |
| 資源の取り合い | resource contention | Refusing whatever tries to take a pin or resource that is held | core §8.1 |

## Notifications and streams

| Japanese | English | Meaning | Defined in |
|---|---|---|---|
| 通知 | notification | Events and data the probe sends without a request | core §10 |
| 購読 | subscribe, subscription | Asking for the notifications of one fn. The sending interface's own ops (0x01 subscribe, 0x02 unsubscribe). It ends together with the lock | core §10.3 |
| seq | seq | The u16 serial number of notification frames per fn | core §10.2 |
| 位置つきのストリーム | positioned stream | Bytes numbered by a u64 position that does not go back during a boot | common §1 |
| 位置 | position | The serial number of a stream byte | common §1.1 |
| gap | gap | A read flag: the asked position had been pushed out | common §1.2 |
| マーク | mark | A record of an event attached to a stream position (lost, clear, host; console also has reset/restart) | common §1.3, console §2 |

## Wires and targets

| Japanese | English | Meaning | Defined in |
|---|---|---|---|
| 線（wire） | wire | A debug wire interface `oep.wire.*` that makes connections | debug §0 |
| 接続（connection） | connection | A connection to the target made by attach | common §2 |
| 使っているもの | user (of a connection) | The session that owns a connection | common §2 |
| ピンの役 | pin role | 1 SWDIO, 2 SWCLK, 3 reset | debug §1 |
| ピンの組 | combination | The channels of one try of a wire | debug §1 |
| scan、attach、detach | scan, attach, detach | Look for a target, connect, leave | debug §1, §2 |
| 席、max_connections | seat, max_connections | The number of connections a wire can hold at once | debug §1 |
| リセットの後の待ち | reset settle wait | The wait after releasing reset until a silent debug module answers. At most max_op_ms, not counted as a wire retry | debug §2 |
| 立ち上げ | bring-up | The wire's wake, choosing a speed and checking it | debug §1 |
| スクラッチのレジスタ | scratch register | A register used to check writes and restored afterwards | debug §1 |
| target_id、scheme | target_id, scheme | The identifier the probe read, and how it was read | debug §1 |
| やり取り | exchange | One frame, packet or wake pattern on the wire | debug §2 |
| 線切れ | wire loss | Failures without any answer from the wire continue, and the probe decides to close the connection | debug §2 |
| 放した状態、休み方 | free state, rest state | The undriven wire after a failure. The state of the wire between exchanges | debug §2, §3, §5 |
| idle_clock | idle_clock | The rest state of the clock of a 2-wire link (high or low) | debug §3 |
| mechanism（方式） | mechanism | How the console is carried: SDI, DMDATA, dmseq | console §1, §3 |
| dmseq | dmseq | A console framing over DATA0 / DATA1 with sequence bits and CRC-8 | dmseq |
| 送りの列 | send queue | The probe's per-stream queue that takes console writes. The probe decides its size | console §2 |

## Capture

| Japanese | English | Meaning | Defined in |
|---|---|---|---|
| トラック | track | One logic or analog capture interface | capture §0 |
| mode | mode | one-shot, repeat, streaming | capture §2.1 |
| 区画 | segment | A part of a capture with its own time and sample count | capture §2.2 |
| 世代 | generation | Advances with each accepted start (1 at first, 0 before start; after 0xFFFFFFFF start is refused and the value is not reused until restart). read and release point at it, and events carry it. capture-group has the group's generation | capture §0, §4.1 |
| capture-group | capture-group | Starts several tracks together | capture §4 |

## Probe settings

| Japanese | English | Meaning | Defined in |
|---|---|---|---|
| 設定、カテゴリ、項目、キー | settings, category, item, key | The values of named items within categories per owner (the core or an interface). set replaces whole values | core §13.1, §13.5 |
| 初期値 | initial value | A value the firmware provides, which the core puts at a boot without a save. Once put it is like any other value | core §13.4 |
| channel の名前 | channel name | The pin name of the datasheet (`GPIO14`, `PA5`). Points at a channel in saves and exports | core §7.5 |
| label | label (item) | `channel.{}.label`: the name a channel is called by (`NRST`) | core §13.8 |
| idle | idle (item) | `channel.{}.idle`: the idle state of a channel: Hi-Z, pull, output low / high | core §13.8 |
| disable | disable | `channel.{}.disable`: a channel the probe never uses | core §13.8 |
| 書き出し、入れ直し | export, import | Writing the user values to a JSON file, and putting them back into the probe | [settings file](oep-settings-file.md) |
| 線の名前 | line names | The convention for `N` of the label `S.N`: `swdio`, `swclk`, `swio`, `rx`, `tx`, `nrst`, `power_hi`, `power_lo` | host guide §5.3 |
| 保存 | save | Writing the current user values (there is no op that erases) | core §13.7 |
| storage_state、理由 | storage_state, reason | Whether there is a save, and whether it is in effect | core §13.7 |
| 設定の世代 | settings generation | A u32 change counter not reused within a boot. Used for get pages and for equality with the saved state | core §13.5 |
