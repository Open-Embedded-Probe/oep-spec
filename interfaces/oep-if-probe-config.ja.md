# OEP インターフェース: probe の設定 v1

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](../docs/versioning.ja.md) §6）。本体は [OEP core](../docs/oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.probe.config` | 1 | channelのdisable/idle/labelと任意の保存 | どの系統にも使う |

このインターフェース自体も、各項目の採用も任意である。実行時のplan、接続、UART設定は各操作で明示し、ここには保存しない。
Wi-Fiなどの経路設定は別の定義で扱う。設定はRAM上でもよく、保存のための不揮発領域を一律に要求しない。

## 1. 項目

項目の形は`tag(u8)、len(u16)、value(len byte)`。tagの下位7bitを項目番号とし、Hostはbit7を0で送り、Probeはbit7を無視する。
**項目は設定データであり、操作の末尾の拡張TLVとは別の容器である。** 知らない/宣言しない項目はbit7によらずunsupported
（payloadは受け取った項目tag）。core §2.3の未知の非critical TLVを無視する規則は、外側の[TLV]に適用し、項目には適用しない。
項目番号0（tagの下位7bitが0）はmalformed。

| tag | 項目 | value | キー |
|---:|---|---|---|
| 0x02 | label | channel(u16)、text（1〜32byte、coreのtext） | channel |
| 0x03 | idle | channel(u16)、mode(u8: 0 Hi-Z、1 pull-up入力、2 pull-down入力、3 出力low、4 出力high) | channel |
| 0x07 | disable | channel(u16) | channel |

- channelはfn 0のchannels未満で、firmware自身が使うchannelではない。違えばunsupported（項目tag）。
- 知っている項目の長さが違う場合はmalformed。項目の値を後ろへ伸ばさず、新しい情報は新しい項目番号で定義する。
- labelは設定の名前で、firmwareのdescribeのlabelを変えない。Probeは名前で線を動かさない。
  線の役目として名前を使うHostの慣行は[Hostガイド](../docs/host-development-guide.ja.md) §5.3。
- disableはそのchannelの駆動/設定を行わない指定で、起動時と解放時の空き状態の設定より先に効く。
  firmwareの宣言を広げず、無効なchannelを使う要求はunavailable cause 5。
  使用中のchannelをdisableするsetはunavailable cause 1。idleとdisableを同じchannelに持つ設定はmalformed。
  disableをunsetしたchannelは、ただちに空き状態へ戻す。
- idleは空きのchannelの状態（core §8）。空きのchannelへの変更はただちに効き、使用中なら次に空きになったときに効く。
  idleが無いchannelはHi-Z。mode 3/4の出力の強さはProbeが決める。
  対応しないpull/出力/未知のmodeはunsupported（項目tag）。出力idleを取得できる機能は各インターフェースに従う。

## 2. 操作と変更の世代

| op | 名前 | 要求 | 応答 | ロック | 要否 |
|---:|---|---|---|---|---|
| 0x10 | get | first(u16) | more(u8)、generation(u32)、count(u8)、count × 項目、[TLV] | 不要 | 必須 |
| 0x11 | set | count(u8)、count × 項目、[TLV] | generation(u32)、[TLV] | 必要 | 必須 |
| 0x12 | save | [TLV] | generation(u32)、[TLV] | 必要 | 任意（erase/stateと組） |
| 0x13 | erase | [TLV] | — | 必要 | saveと組 |
| 0x14 | unset | count(u8)、count × (tag(u8)、channel(u16))、[TLV] | generation(u32)、[TLV] | 必要 | 必須 |
| 0x15 | state | [TLV] | storage_state(u8)、saved_generation(u32)、reason(u8)、[TLV] | 不要 | saveがあれば必須、ほかでは任意 |

- 設定は最大65535項目。Probeはさらに小さい有限量にしてよく、保持できない変更はunavailable（cause 2/3）で断れる。
- setは(tag,channel)ごとに置換し、送らないキーは保つ。unsetは指定キーを消し、無いキーはno-op。
  項目のtag bit7はunsetでも同じ扱い。重複キーはmalformed。
- 変更後の設定全体、容量、実行中の資源との競合を先に検証する。拒否時は設定・世代・ピン・実行中の資源を保つ。
  設定を変えないset/unsetは、ピンも再設定しない。
- generationは内容のdigestではなく、同じboot内の変更カウンタ。起動時は1（保存を読み込む場合も初期値1）。
  実際に内容が変わるset/unsetごとに1進める。0は使わない。0xFFFFFFFFでの内容変更はunavailable cause 2で断り、
  再起動まで再利用しない。同じ内容の操作はその値のまま成功する。Hostは等値だけを比較する。
- getはtag、channelの順に並べ、firstから1frameに入る項目を返す。項目tagのbit7は0。
  firstが総数以上ならmore 0/count 0。more 1なら受け取ったcountをfirstへ加えて続ける。
  項目を分割しない。同じ世代のページは同じ内容を表す。途中で世代が変わればHostは最初から読む。
  末尾の拡張TLVを設定項目へ混ぜない。
- count 0のset/unsetはno-op。外側の未知critical TLVはcore §2.3のとおり副作用前に断る。

## 3. 保存と起動

- save/eraseを提供するときだけ不揮発領域を使う。saveは明示操作で、現在の全項目を保存する。
  同じ内容が保存済みなら書き直さない。保存の判定をgenerationの一致だけに頼らない。
- 保存は、書込みの任意の時点で電源が落ちても、前の完全な保存か新しい完全な保存のどちらかを読める。
  保存の内部形式、CRC、bank配置はProbeが選ぶ。保存/消去の全処理はcoreのmax_op_ms内に終える。
- eraseは保存だけを消し、現在の設定/世代を変えない。
- 保存が読める場合は項目ごとに現firmwareで検証する。未知の項目、非対応channel/mode、無効なlabelがあっても、
  それと独立した有効なdisable/idle/labelは適用する。disableを先に適用してからidleを掛ける。
  同じchannelにdisableとidleがあればdisableを優先しidleを適用しない。重複キーはそのキーを適用しない。
  不正な項目を黙って別channelや別modeへ読み替えない。
- 保持量が減って保存全体が入らない場合は、disable、idle、labelの順で、同じ種別内はchannel順に適用できる項目を選ぶ。
  独立したdisable/idleをlabelの保持量不足で全部落とさない。容量不足は部分適用とreason 3で示す。
- 容器が壊れて境界/完全性を確かめられない保存は全体を適用しない。
  一部を適用した場合のgetは適用した現在の設定を返し、stateで部分適用を示す。
- 起動では設定済みdisableを先に反映し、ほかのchannelをidle（無ければHi-Z）へ。
  保存の有効な項目が現在の設定と全部一致する場合にsaved_generation=1とし、そうでなければ0。
- stateのstorage_state: 0 保存なし、1 全体適用済み/保存済み、2 全体を読めない、3 部分適用。
  reason: 0 なし、1 容器の形/完全性、2 無効/非対応の項目、3 保持量不足。保存が無い/全体を読めない/部分適用ならsaved_generation=0。
  save後（内容一致で書込みを省いた場合も）はsaved_generationを現在のgenerationへ置く。
  その後set/unsetで内容が変わってもsaved_generationは保つ。次の起動で両者は新しいbootの値になる。

## 4. describe

| tag | 名前 | 値 | 要否 |
|---:|---|---|---|
| 0x40 | storage | max_bytes(u32、1以上)。項目の見出し込みの合計byte数で、いつでも保存できる上限 | save/eraseを提供するときだけ必須 |
| 0x41 | items | 対応する項目tagの並び（u8）。1つ以上、重複なし | 必須 |

storageのmax_bytesには保存管理の領域を含めない。これを超えるsaveは副作用前にunavailable cause 3。
保存を提供しないProbeはstorageを宣言しない。最大長のlabel項目も、count/見出し込みで48byteのset/getに収まり、coreの64byte frameで使える。
