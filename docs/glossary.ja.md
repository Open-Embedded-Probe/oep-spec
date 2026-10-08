# OEP v1 の用語集

状態: **ガイド**（規範ではない）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。仕様が定める用語と、決まった意味で使う用語を、定めた節と、英語と日本語の対応と一緒に並べる。
ここの意味は短いまとめで、定義はリンク先の節。食い違えば規範が正しい。

文書: core = [OEP core](oep-core.ja.md)、common = [共通部品](../interfaces/oep-if-common.ja.md)、debug = [線とデバッグ](../interfaces/oep-if-debug.ja.md)、
console = [コンソール](../interfaces/oep-if-console.ja.md)、dmseq = [dmseq](../interfaces/target-console-dmseq.ja.md)、fixture = [fixture](../interfaces/oep-if-fixture.ja.md)、
capture = [キャプチャ](../interfaces/oep-if-capture.ja.md)、settings = [probe の設定](../interfaces/oep-if-probe-config.ja.md)、plan = [plan](../interfaces/oep-if-plan.ja.md)、
restart = [再起動](../interfaces/oep-if-restart.ja.md)、link = [リンク](../interfaces/oep-if-link.ja.md)。数は `registry/oep-v1.toml`。

## 登場するものと層

| 日本語 | English | 意味 | 定めた所 |
|---|---|---|---|
| probe | probe | OEP を話す装置。OEP の要求に自分で答える端点もすべて | core §1、transports §1 |
| host | host | probe を使うソフトウェア | core §1 |
| target | target | probe がつながる相手（開発中の MCU） | core §1 |
| ブローカー | broker | 複数の道具を 1 つのセッションに束ねる host の側のソフトウェア。probe に対しては host | transports §1 |
| 中継のブローカー | relaying broker | セッションの op に自分で答え、ほかを 1 つの probe に中継するブローカー | transports §1、core §5.2 |
| core（本体） | core | どの probe と host も実装するもの。名前を持たず fn 0 で話し、list に載らない。版はプロトコルの revision | core §0 |
| oep インターフェース | oep interface | 名前が `oep.` で始まるインターフェースの略。project 自身のもので、逆 DNS の名前の代わりに短い `oep.` の名前を持つ。ほかのどのインターフェースとも同じに扱う | core §13 |
| 独自のインターフェース | third-party interface | 逆 DNS の名前で、それを定めた者の文書が定めるインターフェース。OEP を伸ばす者は誰でもこれを使う。ほかのどのインターフェースとも同じに扱う | core §13 |
| 規範の語 | normative words | RFC 2119 / 8174 の MUST / MUST NOT / SHOULD / MAY。日本語は する / しない / できれば / してよい | core §1.1 |
| 適合 | conformance | probe と host が実装しなければならないもの | core §1.2、[適合](conformance.ja.md) |

## 経路とフレーム

| 日本語 | English | 意味 | 定めた所 |
|---|---|---|---|
| 経路 | transport | OEP のフレームを運ぶもの: UART bridge、USB CDC、内蔵の USB シリアル、vendor bulk、HID、TCP（`transport_kind` 1〜6） | core §1、transports §1、core §7.5 |
| シリアルの口 | serial port | OS からシリアルデバイスに見える経路（kind 1〜3）。OEP と生のバイトを運ぶ | core §1、transports §4 |
| UART bridge | UART bridge | probe の UART を USB-UART の変換チップで出したもの | transports §1 |
| 内蔵の USB シリアル | built-in USB serial | MCU のハードウェアが作る USB シリアルの口。記述子を probe が選べない | core §7.5 |
| vendor bulk | vendor bulk | class 0xFF / 0x4F / 0x45 の interface の bulk の組 | transports §1、§3 |
| 経路の index | transport index | probe の中の経路の番号。firmware をまたいで変えない | core §7.5 |
| フレーム | frame | 経路の上の 1 つのメッセージと、その包み | transports §1 |
| COBS のフレーム | COBS frame | `0x00 COBS(message + CRC-16) 0x00`。シリアルの口で使う | transports §1 |
| 長さつきのフレーム | length-prefixed frame | `length(u16) message`。vendor bulk、HID の report、TCP で使う | transports §1 |
| `_oep._tcp` | `_oep._tcp` | TCP で待ち受ける probe が自分を広告するときに mDNS で広告する DNS-SD の service。port は SRV、TXT に `unit_id` | transports §3 |
| 候補 | candidate | 0x00 から次の 0x00 までのバイト。フレームかもしれないものとして解く | transports §1、§4 |
| 壊れた候補 | broken candidate | 解けないか CRC の合わない候補 | transports §4 |
| 生のバイト | raw bytes | シリアルの口の、OEP のフレームの外のバイト（target のコンソールなど） | transports §4 |
| 生の転送 | raw transfer | シリアルの口と、それに結んだ流れの間で生のバイトを運ぶこと。セッションが口を使う間は止まる | transports §4 |
| フレームの途切れ | frame gap | フレームの途中の `probe_frame_gap_ms` の途切れ。probe は読み直す（TCP では読み直さない） | transports §2 |
| 区切りの立て直し | resync | 長さつきのフレームで、host が区切りを取り戻すこと | transports §5 |
| 起動時の速さ | boot speed | UART bridge の起動時の速さ、`uart_bridge_boot_baud` | transports §4、link §3 |
| port_speed | port_speed | セッションの間だけ UART bridge を速くする任意の握手: 試す、決める、戻す | link §3 |
| 握手 | handshake | port_speed のうち仕様が定める部分（速さの選び方は含まない） | link §3 |
| 流し方 | flow | 向きと同時数。host が速さを確かめるときに使う | link §3 |
| 探りの規則 | probing rule | 見分けていない device や口には confirm だけを送り、正しい応答が無ければ閉じる | transports §3 |
| 名指した probe | named probe | 利用者が unit_id で名指した probe | transports §3 |
| プロジェクトの VID:PID | project's VID:PID | `1209:4F45`（registry の `usb`）: host が probe を自動で見分ける唯一の USB の ID | transports §3 |

## メッセージ

| 日本語 | English | 意味 | 定めた所 |
|---|---|---|---|
| role | role (of a frame) | 先頭の 1 byte: 要求 0x01、応答 0x02、出来事 0x05、データ 0x06 | core §2.5、§4.1 |
| 要求 | request | host からのメッセージ | core §4.1 |
| 応答 | answer | 要求に対する probe の 1 つの返事 | core §4.2 |
| 出来事 | event | kind と固定部分を持つ通知 | core §11.2 |
| データ | data | 位置つきでストリームのバイトを運ぶ通知 | core §11.2 |
| corr | corr | host が要求に付ける u16 の番号。1 ずつ進め、0 は使わない。応答が同じ値を持つ | core §4.1 |
| fn | fn | 同じ boot_id の間、インターフェースを指す u16。fn 0 は本体（list に載らない） | core §1、§7.2 |
| op | op | インターフェースの中の操作の u8 の番号 | core §1、§2.5 |
| resolution | resolution | completed（0x01）か rejected（0x00）。0x02 は予約 | core §4.2 |
| outcome | outcome | completed の success 0、failed 1、partial 2 | core §4.2 |
| 断り（rejected） | rejected / refusal | 要求が受け付けられなかった | core §4.2 |
| 断りの理由 | reject reason | rejected の detail（unknown_function … result_lost） | core §4.3 |
| 断り方の順 | order of refusal | 見出し、送り直しの表、セッションの順。それ以外は当たった理由のどれか 1 つで断る | core §4.3 |
| cause | cause | unavailable の断りの TLV: 理由（ピンが使われている、上限、設定が持つ、状態が違う…） | core §4.3 |
| status | status | 線と target の操作の結果: ok、wait、line、fault、timeout、state | common §3 |
| TLV | TLV | `tag(u8) len(u16) value`。どの長さでも形は一つ | core §2.2 |
| tag の文脈 | tag context | tag の空間: (fn, op) ごと | core §2.2 |
| critical | critical | 要求の TLV の tag の bit 7: その tag を実装しない probe は断る（印が無ければ無視する） | core §2.2、§2.3 |
| 固定部分 | fixed part | (name, revision) が形を決める payload の部分 | core §2.3、§2.7 |
| 末尾、後ろ | tail | 要求、応答、出来事、データの固定部分の後ろに続く TLV | core §2.3 |
| 並び、要素 | sequence, element | 数の付いた並び、`count × element`。要素は固定の形で、自分の長さを持たない | core §2.3 |
| bitmap | bitmap | bit i は byte ⌊i/8⌋ の bit (i mod 8) | core §2.1 |
| 真偽値、文字列 | boolean, text | u8 の 0 / 1（0 でなければ真と読む）。終端なしの UTF-8 | core §2.1 |
| 知らない値 | unknown value | 読む側が知らない値の扱い | core §2.4 |
| 一周する値 | wrapping value | seq、資源の番号: 通し番号の算術で比べる | core §2.6 |
| 時計 | clock | probe の 1 つの時計: 起動からの ns（u64）。全ビット 1 は「まだ」。今の値は op の clock で読む | core §2.6a、§7.7 |
| revision | revision | プロトコルの revision（confirm）とインターフェースの revision（list）。固定部分が変わるときだけ上げる | core §2.7、§7.1 |
| max_frame、window、max_inflight | max_frame, window, max_inflight | 経路ごとの、メッセージの長さ、待っている byte、待っている要求の上限 | core §4.4 |
| 待ち時間（の下限） | wait floor | host が応答を待つ最短の時間 | core §4.4 |
| 転送の時間 | transfer time | UART bridge の線の速さのための、待ち時間の一部 | core §4.4 |
| 送り直し | resend | 応答が壊れたか遅れたときの、同じ corr での送り直し（probe は表から答える） | core §5.2 |
| 送り直しの表 | resend table | 二重の実行を防ぐために probe が覚える最近の応答 | core §5.2 |

## セッションと資源

| 日本語 | English | 意味 | 定めた所 |
|---|---|---|---|
| セッション | session | ロックを持って状態を変える権利。session_id で識別する | core §1、§6 |
| session_id | session_id | 1 つのセッションに host が選ぶ、予測できない 0 でない u32 | core §6.1 |
| ロック | lock | probe に 1 つのロック | core §6.1 |
| lease | lease | ロックの期限。要求で延びる | core §1、§6.1、§6.4 |
| 期限切れ | lease expiry | lease が尽きた。そのセッションの資源は外れる | core §6.1、§9 |
| force | force | ほかのセッションからロックを奪う open（認証ではない） | core §6.4 |
| owner | owner | open に付ける表示の文字列。lock_state と locked で返る | core §6.4 |
| boot_id | boot_id | 起動のたびに変わるように選ぶ値 | core §6.5 |
| 資源、資源の番号 | resource, resource number | セッションが作るもの（plan、接続、ストリーム…）。番号は probe に 1 つの空間の u16 で、1 から 1 ずつ進め（0 は割り当てない）、使用中の番号は飛ばす | core §9 |
| 寿命 | lifetime | end、期限切れ、force、再起動で資源がどうなるか | core §9 |

## 発見と宣言

| 日本語 | English | 意味 | 定めた所 |
|---|---|---|---|
| confirm | confirm | 最初の要求: `OEP?` / `OEP!`、revision、上限、boot_id | core §7.1 |
| clock（op） | clock (op) | fn 0 の op 0x04。必須、ロック不要、session_id 0 で送れる。応答は boot_id と uptime_ns。中継のブローカーも probe に中継する | core §7.7、transports §1 |
| uptime_ns | uptime_ns | clock の応答の probe の今の時刻（起動からの ns）。probe が要求を受けてから応答を送るまでの間に読んだ値 | core §2.6a、§7.7 |
| list | list | 名前ごとのインターフェースと、その fn、instance、revision | core §7.2 |
| describe | describe | インターフェースの、または（fn 0 で）probe 全体の宣言 | core §7.3 |
| 宣言 | declaration | describe が返すもの。boot_id が同じ間変わらない | core §7.3 |
| ページング | paging | more = 1 の間、`first` を進めて聞き直す。終わりを越えた first には要素 0 個と more 0。marks と segments は from_serial（最後の serial + 1）で聞き直す | core §7.3、common §1.3 |
| 名前、ラベル | name, label (of a name) | `a-z 0-9 - .`。`.` で区切ったラベルが 2 つ以上 | core §7.2、§13 |
| instance、`name#instance` | instance | 同じ (name, revision) のインターフェースの中の番号。文字で書く形は host ガイド §5.3 | core §7.2 |
| role_channels、channel_group | role_channels, channel_group | 役が使える channel、決まった組 | core §7.4 |
| features | features | インターフェースの、op でない任意の機能の u32 の bit（モード、format） | core §7.4 |
| ops | ops | すべての fn が持つ op を宣言する、describe の共通の tag 0x09（base + bitmap、op 0xFF を越えない） | core §1.2、§7.4 |
| unit_id | unit_id | 個体の識別子。`a-z 0-9 -` の 1〜32、USB の serial number と等しい | core §7.5 |
| `x-` の unit_id | `x-` unit_id | 一意でない unit_id。まとめにも名指しにも使わない | core §7.5 |
| model、chip、firmware | model, chip, firmware | probe の種類、その MCU、firmware の自由な文字列 | core §7.5 |
| max_op_ms | max_op_ms | probe が 1 つの要求にかける最長の時間 | core §7.5 |
| label | label (firmware) | firmware の固定の channel の名前 | core §7.5 |
| アドレス | address | `oep://<unit_id>[/<スロットの name>]` | host ガイド §5.3 |
| 線の試験 | link test | `oep.probe.link` の source と sink の op。経路を測る | link §2 |
| restart | restart | `oep.probe.restart` の op: 応答を先に送り、probe が起動し直す。restart_max_ms のうちに confirm にまた答える | restart §2 |

## plan とピン

| 日本語 | English | 意味 | 定めた所 |
|---|---|---|---|
| channel | channel | probe のピンの u16 の番号。0〜channels − 1 | core §1、§7.5 |
| plan | plan | どの fn のどの役にどの channel を使うか。fn ごとに持つ。`oep.probe.plan` | plan §2 |
| 役（role） | role (of a plan) | インターフェースの中のピンの働き（RX、SWDIO…） | core §7.4、§13、plan 冒頭 |
| role_assignment | role_assignment | plan_apply の TLV: fn、role、channel | plan §2.1 |
| plan_roles | plan_roles | plan が一度に持てる割り当ての数 | plan §1、§2.1 |
| 設定の plan | settings plan | 設定が置いた plan。設定でしか変わらない | plan §2.3、settings §1 |
| 空きの状態 | idle state | どのインターフェースも取っていないピンの状態: 保存した設定の idle か Hi-Z | core §8 |
| 資源の取り合い | resource contention | 持たれているピンや資源を取ろうとするものを断る | core §8.1 |
| 出力の強さ、段 | drive strength, drive_levels | mode 3 / 4 の出力の選べる強さ | fixture §1.1 |

## 通知とストリーム

| 日本語 | English | 意味 | 定めた所 |
|---|---|---|---|
| 通知 | notification | probe が要求なしに送る出来事とデータ | core §11 |
| 購読 | subscribe, subscription | 1 つの fn の通知を求めること。送り出すインターフェース自身の op（0x30 subscribe、0x32 unsubscribe）。ロックと一緒に終わる | core §11.3 |
| seq | seq | fn ごとの通知のフレームの u16 の通し番号 | core §11.2 |
| 位置つきのストリーム | positioned stream | 起動の間戻らない u64 の位置で番号を振ったバイト | common §1 |
| 位置 | position | ストリームのバイトの通し番号 | common §1.1 |
| gap | gap | read の flag: 求めた位置が押し出されていた | common §1.2 |
| マーク | mark | ストリームの位置に付けた出来事の記録（reset、attach、lost…） | common §1.3 |

## 線と target

| 日本語 | English | 意味 | 定めた所 |
|---|---|---|---|
| 線（wire） | wire | 接続を作る debug の線のインターフェース `oep.wire.*` | debug §0 |
| 接続（connection） | connection | attach が作る target への接続 | common §2 |
| 使っているもの | user (of a connection) | 接続を開いたままにするセッションかスロット | common §2 |
| ピンの役 | pin role | 1 SWDIO、2 SWCLK、3 reset | debug §1 |
| ピンの組 | combination | 線の 1 回の試しの channel | debug §1 |
| scan、attach、detach | scan, attach, detach | target を探す、つなぐ、離れる | debug §1、§2 |
| 席、max_connections | seat, max_connections | 線が一度に持てる接続の数 | debug §1 |
| リセットの後の待ち | reset settle wait | リセットを解いた後、黙った debug module が答えるまでの待ち。多くても max_op_ms、線の再試行に数えない | debug §3、§4.3 |
| 立ち上げ、search_retries | bring-up, search_retries | wake、速さを選んで確かめること。その追加の試しの数（数え方は実装が決める、診断用） | debug §1 |
| スクラッチのレジスタ | scratch register | 書き込みの確かめに使い、後で元に戻すレジスタ | debug §1 |
| target_id、scheme | target_id, scheme | probe が読んだ識別子と、その読み方 | debug §1 |
| やり取り | exchange | 線の上の 1 つのフレーム、packet、wake pattern | debug §2 |
| 線切れ | wire loss | 線からの応答の無い失敗が続き、probe が connection を閉じると決めること | debug §2 |
| 放した状態、休み方 | free state, rest state | 失敗の後の駆動しない線。やり取りの間の線の状態 | debug §2、§3、§5 |
| idle_clock | idle_clock | 2 線のクロックの休み方（high か low） | debug §3 |
| mechanism（方式） | mechanism | コンソールの運び方: SDI、DMDATA、dmseq | console §1、§3 |
| dmseq | dmseq | DATA0 / DATA1 の上の、順番の bit と CRC-8 を持つコンソールの framing | dmseq |
| 送りの列 | send queue | コンソールの write を受ける、ストリームごとの probe の列。大きさは probe が決める | console §2 |

## キャプチャ

| 日本語 | English | 意味 | 定めた所 |
|---|---|---|---|
| トラック | track | 1 つのロジックかアナログのキャプチャのインターフェース | capture の冒頭 |
| mode | mode | one-shot、repeat、streaming | capture §2.1 |
| 区画 | segment | 自分の時刻とサンプル数を持つキャプチャの一部 | capture §2.2 |
| 世代 | generation | start のたびに進む（最初の start で 1、0xFFFFFFFF の次は 1、0 は start の前）。read と release が指し、出来事も持つ。capture-group は組の世代を持つ | capture の冒頭、§4.1 |
| capture-group | capture-group | 複数のトラックを一緒に始める | capture §4 |
| multirate | multirate | ロジックの別の定義: 全チャネルを同じ base rate で見て、チャネルごとに違う間隔 d で値を出し、区間を要約する | capture §5 |
| base sample | base sample | multirate で全チャネルのレベルを同時に見る点。rate、samples、trigger_index はこれで数える | capture §5 |
| 縮約のチャネル | reduced channel | multirate で、sample の d = 1 でないチャネル（sample、any_active、edge_latch） | capture §5.2 |
| block | block | multirate のデータの単位: L 個の base sample の、D = 1 の部分と縮約の部分 | capture §5.5 |

## probe の設定

| 日本語 | English | 意味 | 定めた所 |
|---|---|---|---|
| 設定、項目、キー | settings, item, key | 項目の並び。set はキーごとに置き換える | settings §1、§2 |
| label | label (item) | 設定で付けた channel の名前 | settings §1 |
| idle | idle (item) | channel の空きの状態: Hi-Z、pull、出力 low / high | settings §1 |
| disable | disable | probe が決して使わない channel | settings §1 |
| スロット | slot | target がつながる場所の登録 | settings §1.1 |
| attach の方針 | attach policy | host か at boot | settings §3.1 |
| bind | bind | シリアルの口が流すストリーム 1 つ（スロットのコンソールか fixture UART の受信） | settings §1.2 |
| 口の位置 | position of the port | bind の口が、流すストリームのどこにいるか | settings §1.2 |
| 線の名前 | line names | `nrst`、`power_hi`、`power_lo`。ほかは `x-` | settings §1.3 |
| hash | hash | 今の設定を表す u32。設定が変われば変わり、作り方は probe が決める | settings §2 |
| wifi の項目、entry | wifi item, entry | probe がつなぐ Wi-Fi のネットワーク 1 つ（index、ssid、passphrase）。index の順に試す | settings §1.4 |
| 書くだけ（passphrase） | write-only (passphrase) | get も state もほかのどの応答も passphrase を返さない。get の pass_len 0xFF は「ある」で、set で送り返すと今のものを保つ | settings §1.4 |
| 保存、消去 | save, erase | 保存の写しを書く / 消す | settings §2 |
| storage_state、読めない理由 | storage_state, unreadable reason | 保存があり、掛かっているか | settings §3.3 |
| slot_state、bind_state | slot_state, bind_state | スロットと bind の今の状態 | settings §3.2、§3.3 |
