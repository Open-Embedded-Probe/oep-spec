# OEP インターフェース: probe の設定 v1

状態: **規範**（v1）。凍結状態と言語・互換性の方針は[版と安定性](../docs/versioning.ja.md)を参照。本体は [OEP core](../docs/oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.probe.config` | 1 | channelのdisable/idle/label、シリアルの口の素通し、任意の保存 | どの系統にも使う |

このインターフェース自体も、各項目の採用も任意である。実行時のplan、接続、UART設定は各操作で明示し、ここには保存しない。
Wi-Fiなどの経路設定は別の定義で扱う。設定はRAM上でもよく、保存のための不揮発領域を一律に要求しない。

## 1. 項目

項目の形は`tag(u8)、len(u16)、value(len byte)`。tagの下位7bitを項目番号とし、hostはbit7を0で送り、probeはbit7を無視する。
**項目は設定データであり、操作の末尾の拡張TLVとは別の容器である。** 知らない/宣言しない項目はbit7によらずunsupported
（payloadは受け取った項目tag）。core §2.3の未知の非critical TLVを無視する規則は、外側の[TLV]に適用し、項目には適用しない。
項目番号0（tagの下位7bitが0）はmalformed。

| tag | 項目 | value | キー |
|---:|---|---|---|
| 0x02 | label | channel(u16)、text（1〜32byte、coreのtext） | channel |
| 0x03 | idle | channel(u16)、mode(u8: 0 Hi-Z、1 pull-up入力、2 pull-down入力、3 出力low、4 出力high) | channel |
| 0x05 | passthrough | port(u8)、fn(u16)、rx(u16)、baud(u32)、format(u8) | port |
| 0x06 | console_passthrough | port(u8)、wire_fn(u16)、swdio(u16)、swclk(u16)、max_speed(u32)、console_fn(u16)、mechanism(u8) | port |
| 0x07 | disable | channel(u16) | channel |

- channelはfn 0のchannels未満で、firmware自身が使うchannelではない。違えばunsupported（項目tag）。
- 知っている項目の長さが違う場合はmalformed。項目の値を後ろへ伸ばさず、新しい情報は新しい項目番号で定義する。
- labelは設定の名前で、firmwareのdescribeのlabelを変えない。probeは名前で線を動かさない。
  線の役目として名前を使うhostの慣行は[hostガイド](../docs/host-development-guide.ja.md) §5.3。
- disableはそのchannelの駆動/設定を行わない指定で、起動時と解放時の空き状態の設定より先に効く。
  firmwareの宣言を広げず、無効なchannelを使う要求はunavailable cause 5。
  使用中のchannelをdisableするsetはunavailable cause 1。変更後の設定で同じchannelにidleとdisableが併存するsetは、設定の使用制限との競合としてunavailable cause 5で断る。
  設定・世代・ピンは変えない。併存を解くには、先に競合する項目をunsetする。重複キーや項目の長さの誤りはmalformedのままである。
  disableをunsetしたchannelは、ただちに空き状態へ戻す。
- idleは空きのchannelの状態（core §8）。空きのchannelへの変更はただちに効き、使用中なら次に空きになったときに効く。
  idleが無いchannelはHi-Z。mode 3/4の出力の強さはprobeが決める。
  対応しないpull/出力/未知のmodeはunsupported（項目tag）。出力idleを取得できる機能は各インターフェースに従う。

### 1.1 passthrough（シリアルの口の素通し）

UART bridge しか口の無い probe でも、普通のシリアルモニタで target の出力を見られるようにする任意の項目。
ここでの作用はセッションと独立に適用する設定である（core §9）。

- port は fn 0 の describe の経路の index で、シリアルの口（kind 1〜3）。fn はその probe の `oep.fixture.uart`、rx はその fn の role 1（RX）として
  宣言された channel。baud と format は fixture §2 の configure と同じ値と規則（baud 0 は malformed、作れない baud と宣言に無い format は
  unsupported）。違う port、fn、rx は unsupported（項目 tag）。rx が disable なら、または出力の idle を持てば unavailable cause 5。
- **素通しの条件**: その口からセッションの要求が来ていない、その fn の plan が無い、rx をほかの plan・接続・設定が取っていない、のすべてが成り立つ間、
  probe はその UART を rx だけで受け（TX は使わない。rx を駆動しない）、受けたバイトを [経路](../docs/oep-transports.ja.md) §4 のとおり口へフレームの外で送る。
  どれかが成り立たなくなったら、受けるのをやめて rx を空きの状態に戻す。条件がまた成り立てば再開する。
- 素通しはセッションの資源と取り合わない: セッションの plan、接続、口の使用は、素通しを止めて先に通る（素通しを理由に断らない）。
- 素通しで受けたバイトは OEP のストリーム（fixture UART の read）に入れず、保持しない。口へ送れなかった分は捨てる。
- 口からフレームの外で来たバイトを target へ送ることは定めない（入力は OEP の write を使う）。
- キーは port。unset ではその channel(u16) の欄に port を置く。
- 1 つの口には passthrough と console_passthrough のどちらか 1 つだけを置ける（両方は unavailable cause 5）。

### 1.2 console_passthrough（debug のコンソールの素通し）

UART を空けられない target（debug の郵便受けで出力するもの）の出力を、セッションの無い間も口へ流す任意の項目。§1.1 と同じく、
セッションと独立に適用する設定である。

- wire_fn は `oep.wire.rvswd` か `oep.wire.swio`、(swdio, swclk) はその宣言が許すピンの組、max_speed は debug §1 の attach と同じ値と規則。
  console_fn はその wire の connection を受ける `oep.target.console`、mechanism はその describe の mechanisms にある方式。違えば unsupported（項目 tag）。
  ピンのどれかが disable なら、または出力の idle を持てば unavailable cause 5。
- **素通しの条件**: その口からセッションの要求が来ていない、セッションの接続・plan がそのピンを取っていない、のすべてが成り立つ間、probe はその wire で
  method 0（止めない、reset しない）の attach をして、その方式でコンソールを読み、target の出力を §1.1 と同じに口へフレームの外で送る。
  attach が成らなかったときの試し直しは、wake / 設定の手順が target をリセットしない wire（swio）でだけ、probe が決める間隔で行う。
  wake が target をリセットしうる wire（rvswd、debug §3）では、条件が成り立つたびに 1 回だけ試す（debug §2 の「target の状態を変えない」）。
- 条件が成り立たなくなったら、probe はその接続を target に触れずに閉じ（debug §2）、ピンを空きの状態に戻す。セッションの attach は、
  素通しの接続を理由に断らない（素通しが先に退く）。
- 素通しの接続とコンソールは OEP の資源ではない: connections と streams に現れず、番号を使わず、マークを付けない。target への入力は送らない。
- 線切れ（debug §2）と target の自己リセットは、素通しを止めずに試し直しで扱う。

## 2. 操作と変更の世代

| op | 名前 | 要求 | 応答 | ロック | 要否 |
|---:|---|---|---|---|---|
| 0x10 | get | first(u16) | more(u8)、generation(u32)、count(u8)、count × 項目、[TLV] | 不要 | 必須 |
| 0x11 | set | count(u8)、count × 項目、[TLV] | generation(u32)、[TLV] | 必要 | 必須 |
| 0x12 | save | [TLV] | generation(u32)、[TLV] | 必要 | 任意（erase/stateと組） |
| 0x13 | erase | [TLV] | — | 必要 | saveと組 |
| 0x14 | unset | count(u8)、count × (tag(u8)、channel(u16))、[TLV] | generation(u32)、[TLV] | 必要 | 必須 |
| 0x15 | state | [TLV] | storage_state(u8)、saved_generation(u32)、reason(u8)、[TLV] | 不要 | saveがあれば必須、ほかでは任意 |

- 設定は最大65535項目。probeはさらに小さい有限量にしてよく、保持できない変更はunavailable（cause 2/3）で断れる。
- setは(tag,channel)ごとに置換し、送らないキーは保つ。unsetは指定キーを消し、無いキーはno-op。
  項目のtag bit7はunsetでも同じ扱い。重複キーはmalformed。
- 変更後の設定全体、容量、実行中の資源との競合を先に検証する。拒否時は設定・世代・ピン・実行中の資源を保つ。
  設定を変えないset/unsetは、ピンも再設定しない。
- generationは内容のdigestではなく、同じboot内の変更カウンタ。起動時は1（保存を読み込む場合も初期値1）。
  実際に内容が変わるset/unsetごとに1進める。0は使わない。0xFFFFFFFFでの内容変更はunavailable cause 2で断り、
  再起動まで再利用しない。同じ内容の操作はその値のまま成功する。hostは等値だけを比較する。
- getはtag、channelの順に並べ、firstから1frameに入る項目を返す。項目tagのbit7は0。
  firstが総数以上ならmore 0/count 0。more 1なら受け取ったcountをfirstへ加えて続ける。
  項目を分割しない。同じ世代のページは同じ内容を表す。途中で世代が変わればhostは最初から読む。
  末尾の拡張TLVを設定項目へ混ぜない。
- count 0のset/unsetはno-op。外側の未知critical TLVはcore §2.3のとおり副作用前に断る。

## 3. 保存と起動

- save/eraseを提供するときだけ不揮発領域を使う。saveは明示操作で、現在の全項目を保存する。
  同じ内容が保存済みなら書き直さない。保存の判定をgenerationの一致だけに頼らない。
- 保存は、書込みの任意の時点で電源が落ちても、更新前の保存か新しい完全な保存のどちらかを保持する。
  更新前に完全な保存があれば、完全な旧保存または完全な新保存を読める。保存がない初回は「保存なし」または新しい完全な保存となる。
  途中の書込みを完全な保存として扱わない。
  保存の内部形式、CRC、bank配置はprobeが選ぶ。保存/消去の全処理はcoreのmax_op_ms内に終える。
- save/eraseは成功・失敗とも現在の設定/世代とピンを変えない。eraseは保存だけを消し、保存なしでも成功する。
  erase中の電源断では、更新前の保存、保存なし、または完全性を確認できない保存が残りうる。
  最後の場合は次の起動で全体を適用せず、storage_state 2/reason 1で示す。消去の原子性は要求しない。
- 保存が読める場合は項目ごとに現firmwareで検証する。未知の項目、非対応channel/mode、無効なlabelがあっても、
  それと独立した有効なdisable/idle/labelは適用する。disableを先に適用してからidleを掛ける。
  同じchannelにdisableとidleがあればdisableを優先しidleを適用しない。重複キーはそのキーを適用しない。
  不正な項目を黙って別channelや別modeへ読み替えない。
- 保持量が減って保存全体が入らない場合は、disable、idle、labelの順で、同じ種別内はchannel順に適用できる項目を選ぶ。
  独立したdisable/idleをlabelの保持量不足で全部落とさない。容量不足は部分適用とreason 3で示す。
- 容器が壊れて境界/完全性を確かめられない保存は全体を適用しない。
  一部を適用した場合のgetは適用した現在の設定を返し、stateで部分適用を示す。
- 起動では設定済みdisableを先に反映し、ほかのchannelをidle（無ければHi-Z）へ。
  保存全体が有効で、全項目を現在の設定へ適用できた場合にsaved_generation=1とし、そうでなければ0。
- stateのstorage_state: 0 保存なし、1 全体適用済み/保存済み、2 全体を読めない、3 部分適用。
  reason: 0 なし、1 容器の形/完全性、2 無効/非対応の項目、3 保持量不足。保存が無い/全体を読めない/部分適用ならsaved_generation=0。
  save成功後（内容一致で書込みを省いた場合も）はsaved_generationを現在のgenerationへ置く。
  その後set/unsetで内容が変わってもsaved_generationは保つ。次の起動で両者は新しいbootの値になる。

### 保存操作の結果

受理前の拒否は保存状態も変えない。受理したsave/eraseで書込み・消去・検証が完了できなければcompleted failedとし、partialは返さない。
応答の固定部分は成功と失敗で同じ（saveは現在のgeneration、eraseは固定部分なし、いずれも末尾に[TLV]）。
saveの応答のgenerationだけでは保存成功を意味しない。応答喪失時はcoreの再送規則とstateで確認する。

| 結果 | storage_state | saved_generation | reason |
|---|---:|---|---:|
| save成功 | 1 | 現在のgeneration | 0 |
| erase成功 | 0 | 0 | 0 |
| 失敗し、更新前の保存がそのまま残ることを確認できた | 操作前の値 | 操作前の値 | 操作前の値 |
| 失敗し、保存がないことを確認できた | 0 | 0 | 0 |
| 失敗し、保存の完全性を確認できない | 2 | 0 | 1 |

失敗時のstateは操作後に確認できた保存状態を示し、書込みの失敗そのものはcompleted failedで示す。
保存媒体の故障を電源断の原子性保証と混同せず、読めない保存を黙って適用しない。

## 4. describe

| tag | 名前 | 値 | 要否 |
|---:|---|---|---|
| 0x40 | storage | max_bytes(u32、1以上)。項目の見出し込みの合計byte数で、いつでも保存できる上限 | save/eraseを提供するときだけ必須 |
| 0x41 | items | 対応する項目tagの並び（u8）。1つ以上、重複なし | 必須 |

storageのmax_bytesには保存管理の領域を含めない。これを超えるsaveは副作用前にunavailable cause 3。
保存を提供しないprobeはstorageを宣言しない。最大長のlabel項目も、count/見出し込みで48byteのset/getに収まり、coreの64byte frameで使える。
