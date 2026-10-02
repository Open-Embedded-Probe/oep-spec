# v1 凍結前の決定（2026-09-30）と凍結の範囲（2026-10-02）

[English](v1-freeze-decisions.md)

状態: **決定**（2026-09-30。§0 は 2026-10-02 に足した凍結の範囲。★ の 3 つはユーザーが選んだ。ほかは案のとおりで進め、規範の文書に移す）。発端は bench（arduinocore）がエコシステム全体を洗い出した
「凍結前に壊さないと後で直せない所」のうち OEP の分（13 項目）。凍結前なので、どれも revision を上げずに形を変え、全ツールが
一度に追う（[開発の方針](development-guidelines.ja.md)）。

各項目: **案**、変わる所、追随するもの。★ はユーザーに選んでもらう項目。

**規範への反映（2026-09-30、1b7c93c）**: 1（core §2.3、§2.7、list / scan / connections / marks / segments の要素の長さ）、2（probe-config
§2、storage の理由）、3（core §3.3、§7.5 unit_id、probe-config の address、usb-identity）、4（core §4.3、registry
`unavailable_payload`、console の no_connection）、5（名前、status の flags、rate、scale、logic-capture §8）、6（core §11.3）、
7（oep-if-fixture §3 / §4、registry）、8（console）、10（core §7.5）。残りは実装だけ: 9（firmware.yml）、12（probe が label を受ける）、
13（client の API）、11（予約は今の文書のまま）。
1 の bind の並びは漏れていて、2026-10-01 に probe-config §1.2 に入れた（応答の並びと同じく各要素の前に len）。
12 は 2026-10-01 のゼロベースの再検討で変わった: 設定の label は core の describe には出さず probe.config の get で読む（describe は宣言だけ）。
3(b)（iProduct `OEP`）は恒久の規範になり、3(c)（HID の report）は記述子に任せる形で反映した。11 の参照「probe-cdc §6 / §7」は
open-proposals §6 / §7 の誤り。その後の決定は [ゼロベースの再検討と仕様案](v1-zero-base-proposal.ja.md)。

## 0. v1 の凍結の範囲（2026-10-02）

v1 の凍結は、host と probe が別々に作られても噛み合うための約束を止めること。何を止め、何を止めないかを 1 か所に書く。

### 0.1 凍結するもの

| 凍結するもの | 置き場 |
|---|---|
| フレームの形（COBS + CRC-16、`length(u16)`、HID の report、見出しの並びと長さ、confirm の前の 64 byte） | [core](oep-core.ja.md) §3 |
| メッセージの形（要求 / 応答 / 出来事 / データの固定部、TLV の形と critical の規則、reject reason、outcome、断り方の順） | core §2、§4 |
| 標準インターフェースの payload（op の表、固定部、TLV の tag、出来事、status、資源の寿命） | `oep-if-*.ja.md` |
| **registry/oep-v1.toml のすべての数**（op、tag、reason、status、enum、`timing`、`limits`、`usb`、インターフェースの名前と revision）。ただし名前に `reference` を含む値（`reference_vid`、`reference_pid`、`max_op_ms_reference`）は参照 firmware の値で、規範ではなく凍結しない | [registry](../registry/oep-v1.toml)、生成物 |
| core と `oep-if-*` の規範の文（「〜する」「〜しない」の文。[dmseq](target-console-dmseq.ja.md) を含む） | 各文書 |

凍結の後にこれらを変えるときは **revision を上げる**（固定部か意味を変えるインターフェースはその revision、本体の形はプロトコルの
revision。core §2.7）。後ろに足す（任意の TLV、任意の op、出来事、並びの要素の後ろ）は revision を変えずにできる（§0.4）。

### 0.2 凍結の後も自由なもの

| 自由なもの | 置き場 |
|---|---|
| host 開発ガイド、probe 開発ガイドと、その中の参考の数字（速さの候補、閾値、フレーム数、窓、再試行の回数の例） | [host](host-development-guide.ja.md)、[probe](probe-development-guide.ja.md) |
| 計測の記録（追記は自由。規範はそこから数字を引かない） | [リンクの計測](link-measurements.ja.md)、[UART の速さ](uart-speed-negotiation.ja.md)、[キャプチャ](logic-capture.ja.md) |
| リリース前の試験の中身と手順 | [release-testing](release-testing.ja.md)、oep-client-python `tests/hw/` |
| fake（偽の probe）の振る舞いのうち、規範が probe に任せている所 | oep-client-python `fake.py` |
| client の方針（候補の並び、待ち方、再試行の回数、API の形）と、参照 firmware の宣言する値（max_frame、window、max_op_ms、max_length） | 各実装 |
| 理由と経緯の文書（この文書を含む） | core §15 の一覧 |

### 0.3 意図して固定し、伸ばさないもの（理由）

[ゼロベース再検討](v1-zero-base-proposal.ja.md) §4 と [再点検](v1-zero-base-review-2026-10-02.ja.md) の ☆ から。凍結のレビューで
「理由が成り立つか」を見てほしい所。

| 固定するもの | 理由 | もし要るなら |
|---|---|---|
| フレームの見出し（要求 6 / 10 byte、応答 5 byte、通知 5 / 6 byte） | 替えるのは本体の revision。confirm で交渉できるので将来の道は閉じない | プロトコルの revision |
| COBS + CRC-16 / `length(u16)` / HID report の詰め方 | 経路の種類ごとに決まる | 新しい transport kind が自分の方式を定める |
| op（u8）、TLV の tag（u8、bit 7 critical）、reject reason（u8）、出来事の kind（u8） | 足りなくなったらインターフェースを分ける。空間を広げるより名前で分ける方が host に優しい | 別の名前のインターフェース（別の fn） |
| 要求の並びの要素に len を置かない | host は revision と describe で probe を知ってから送る（原則 3）。足すものは TLV | 要求の TLV |
| 応答の固定部そのもの | 固定部を変えるのは revision + 新しい fn。足すものは TLV（「伸ばし方は 1 つ」） | TLV、revision |
| link_source / link_sink の意味 | 線の試験用。意味を足す理由が無い | — |
| confirm の前の 64 byte | 交渉の前の約束。小さいほど安全 | — |
| probe.config の項目のキー（slot u8、port u8、fn u16、channel u16） | 1 台の probe の中の数。u8 / u16 で足りる | — |
| ☆1 confirm に host の受けの上限を足さない | 応答の量は host が同時数で、通知の量は host が min_bytes で決める。probe が host の上限を知っても使い道が無い（通知に ack が無い） | confirm の要求 TLV（非 critical）を後から |
| ☆2 max_frame は両方向の上限のまま | シリアルの口の受けの問題は 1 フレームではなく burst の量（core §3.4 の host の規則） | — |
| ☆3 DFU / firmware の更新は OEP の外（core §0） | USB の記述子にすべてある。OEP が写しを持つと版ごとに食い違う。unit_id = serial が不変なので焼く側は個体を見失わない | `oep.probe.firmware` のような名前つきのインターフェース |
| ☆4 read_block に `max_count` の宣言や専用の理由を足さない | max_length（byte）で表せる。断り方は unsupported に揃えた | address_hi は予約済み（RV64） |
| ☆5 port_speed で probe は速さの候補を宣言しない | 通る速さは host 側の変換チップで決まり、probe からは見えない。候補は host の表 | 要求 TLV に「試した結果」を後から |
| ☆6 ブリッジ側の実際の baud（整数分周のずれ）は出さない | host 側の性質で probe は知れない。応答の baud は probe の UART の実際の値で足りる | — |
| ☆7 block op の往復の減らし方（sysbus のまとめ読みなど）は op に足さない | read_block の意味は「target のバスを通して読む」で、手段は probe が選べる | riscv-dm の features ビットと op 0x09〜 |
| 長い操作、role 0x03 / 0x04、dmi の u32 step、reset の method 2、swd の attach_under_reset、capture の 0x40 以降（§11） | 使う実例が無いまま形を決めない | 予約の番号に後から定める |

### 0.4 伸ばす道（revision を変えずにできること）

| 道 | 範囲 | 規則 |
|---|---|---|
| TLV | 要求 / 応答 / 出来事の後ろ。tag は (fn, op) の文脈ごとの u8（bit 7 critical。0x00、0x7F、0xFF は予約） | core §2.2、§2.3。host は知らない非 critical を飛ばし、probe は知らない critical を unsupported で断る |
| 後ろに足す | TLV の値、出来事の payload、応答の並びの要素（`count × (len, 要素)`）の後ろ | core §2.3。読む側は知らない後ろを飛ばす、短ければ壊れた値 |
| op | インターフェースの op は 0x01〜0xEF をその定義が決める（0xF0〜0xFF は実験用）。core は 0x50〜0xEF が予約 | core §2.5。任意の op の有無は describe で宣言 |
| reject reason / status | 0x40〜0x7F をインターフェースが決める | core §2.5、common §3 |
| describe の宣言 tag | 0x01〜0x3E は本体の共通タグ、0x40〜0x7F はインターフェース。fn 0 は 0x40〜 | core §7.4、§7.5 |
| unavailable / unsupported の payload の tag | 0x40 以降をインターフェースが足す | core §4.3 |
| 出来事の kind | fn ごとに 0x01〜0x7F | core §2.5 |
| probe.config の項目 | 新しい tag、既存の項目の後ろ | probe-config §1 |
| 新しいインターフェース | `oep.` は標準、独自は逆 DNS。名前が違えば別の fn | core §13 |
| 新しい経路 | transport kind を足し、そのフレームの方式を定める | core §3.1、§3.3 |

## A. 横断（決めると他が動ける）

### 1. 固定の形の伸ばし方（core §2）

今の規則は「TLV の並びの後ろに足す」だけで、**TLV の値の中の固定の形**（config の項目、describe の値）と**数を置いた並びの
要素**（list、scan、connections、区画の情報）は、今の長さで凍結される。slot 項目は末尾の錠が残りの長さを使うので、何も足せない。

案:
- core §2.3 に規則を足す: **固定の形を持つ値（TLV の値、出来事の payload、並びの要素）は、読む側が知っている長さより長ければ、
  知らない後ろを読み飛ばす。書く側は後ろにだけ足す**（前のフィールドの意味と位置は変えない）。短ければ壊れた値。
- **数を置いた固定長の要素の並びは、数の後ろに要素の長さ（u8）を置く**: `count(u8)、size(u8)、count × size byte`。読む側は
  各要素の知らない後ろを飛ばす。対象: core の list の entry、debug の scan / connections の entry、capture の segments の区画情報。
- **可変の部分は長さを前に置き、固定の形の真ん中に置かない**: slot 項目は `…、name_len、name、lock_len(u8)、lock_scheme、
  lock_mask、lock_value` とし（lock_len = 0 は錠なし）、その後ろを将来の足し場所にする。bind の並びも同じ（n の後ろの要素に
  size を置く）。
- §2.7 に「後ろに足すのは revision を変えない」を明記する。0.0.6 / 0.0.8 / 0.0.10 の形の変更は凍結前の方針どおりで、凍結後は
  この規則だけで伸ばす。

追随: client（decode）、fake、probe（書く側）、ch32rv、wireskein（区画情報）、bench。

### 2. 保存した設定と interface の一覧（probe-config §2）

今は保存に一覧全体の CRC を付け、違えば全部を適用しない。interface を 1 つ足しても設定が消え（0.0.11〜0.0.16 の根）、DFU で
更新する治具では黙って効かなくなる。§2.7（revision を上げる）とも噛み合わない。

案:
- **保存は、項目が指す fn ごとに (name、instance、revision) を一緒に持つ**。起動時に、その組を今の list で探して fn を読み替えて
  から適用する（set の形（fn で指す）は変えない）。
- 指す interface が無い、または revision が違えば、**保存全体を適用しない**（状態 2 読めない。一部だけ入れると治具が半端に動く）。
  指していない interface の追加・削除・並べ替えでは消えない。
- storage の状態に「読めない理由」を足す: 1 形が読めない、2 指す interface が無い / revision が違う。

追随: probe（OepConfig の保存の形）、fake、client の show。

### 3. USB の識別と `oep://` のアドレス ★

- **(a) アドレスの probe 部** ★ **決定: unit_id**。案は **unit_id**（describe の unit id。どの経路でも同じ）。USB の probe は **serial number を
  unit_id と同じにする**（開かずに解決できる）。P4 の `-hs` は付けない（USJ は VID:PID が違うので serial が重なっても区別できる）。
  アドレスは `oep://<unit_id>/<slot の名前>`。host は serial で探し、見つからなければ describe の unit id で探す。
  **unit_id は 1〜32 byte の `a-z 0-9 -`**（slot の名前は今も `a-z 0-9 - _`）。どちらも URL の中で encode が要らない。
- **(b) vendor bulk の経路**: `bInterfaceClass 0xFF` で、`iInterface` が `OEP` で始まるインターフェースの bulk IN / OUT 1 組、と
  core §3.3 に書く（今の client は「最初の bulk 対」を掴んでいて、DFU や CDC が先にあると外れる）。
- **(c) HID の経路**: usage page / usage、report ID、report の長さを core §3.3 に書く（今の実装の値で固める）。
- **(d) PID を取った後**: firmware は VID:PID を 1209:4F45 に替えるだけ。host の発見は今も iProduct の `OEP` で見るので影響なし。
  bench などの VID:PID の決め打ちは、それまでに serial（unit_id）か iProduct で探す形に替える。usb-identity の iProduct を今の値に直す。

追随: probe（USB の serial）、client（発見、vendor の選び方）、ch32rv、bench（toml、dfu.py）、ArduinoCore-CH32 の IDE の保存値。

### 4. rejected unavailable の理由（core §4.3）

案:
- **unavailable の payload を、core が定める TLV の並びにする**（任意、host は知らない tag を飛ばす）: 0x01 cause(u8: 1 ピンが
  使われている、2 数の上限、3 保存先が足りない、4 組に束ねられている、5 設定が持つ、6 状態が違う)、0x02 channel(u16)、
  0x03 holder_fn(u16)、0x04 holder_kind(u8: 1 plan、2 接続、3 スロット、4 bind、5 設定の plan)。インターフェースは 0x40 以降を足せる。
- 知らない資源（connection、stream の番号）は **どのインターフェースでも no_connection（0x0A）**。console §1 の「知らない stream は
  unavailable」を直す。

追随: probe（主な断りに cause と holder を付ける）、fake、client（例外に載せる）。

## B. OEP の中

### 5. capture の族 ★

- **名前** ★ **決定**: `oep.fixture.logic` / `oep.fixture.analog` / `oep.fixture.capture-group`（今は logic だけ
  `oep.fixture.capture` で非対称）。
- `oep-if-capture` 冒頭の「アナログは番号仮」を消し、logic-capture.ja.md §8 の未決（名前、mode の統合、trigger の段、role の分け方）を
  「v1 はこの形」で閉じる: mode は 3 つ、trigger は 1 チャネル 1 段（段と組み合わせは 0x40 以降の type で後から）、role は 1 本 1 役。
- **status の flags** を定める: bit0 probe の中でデータを落とした（キュー・リング）、bit1 時間の基準が曲がった（slipped）。ほかは予約。
- **rate** は整数 Hz のまま（1 Hz 未満は範囲外と明記）。
- **アナログの zero と scale を符号付き**（i32）にする（反転する frontend）。
- calibration の scheme の文字列は probe の名前空間のまま凍結する（wireskein がファイルに持つ）。

追随: probe、fake、client、wireskein（名前が変われば）。

### 6. ロックを持たない購読

案: **v1 は今のまま**（購読はロックの持ち主だけ）。読むだけの監視は bind（生のバイト）で行う。ロックなしの購読は予約として書く
（後から TLV で足しても、今の意味は変わらない）。

### 7. I2C / SPI のデバイスの名前 ★

**決定: 標準にする**: `oep.fixture.i2c-target` / `oep.fixture.spi-target`。ちゃんと支える機能なので、凍結前に規範の文書
（oep-if-fixture に節を足す）を書き、registry に入れる。今の独自のインターフェースの op と形を土台にし、"esp32" に依る所を外す。

追随: probe、client、bench。

### 8. dmseq の版

案: 「mechanism の番号が方式を正確に決める。方式を変えるときは新しい番号（3 以降）を足す」を console の文書に書く。

### 9. Release の firmware-<ver>.json

案: `"schema": 1` を足し、各項目に `model`（describe の model）と `chip` を足す。`kind` は `merged` / `app` / `uf2` に固定。
追随: firmware.yml、bench。

### 10. model / chip の文字列

案: **小文字、ハイフン無し**に揃える。model はチップ（`esp32p4`、`esp32`、`rp2040`、`rp2350`）、chip の TLV は
`<model> v<rev>`（例 `esp32p4 v1.3`）。Arduino の profile 名と同じになる。

### 11. 予約と保留

| 項目 | 案 |
|---|---|
| 長い操作（resolution 0x02、busy 0x05、core 0x20〜0x2F） | 予約のまま凍結 |
| role 0x03 / 0x04 | 予約のまま凍結 |
| dmi の u32 step | 予約のまま |
| reset の method 2 | 予約のまま |
| swd の attach_under_reset | 予約のまま（SWD の実装が要るようになったら TLV で） |
| capture の 0x40 以降 | 別の定義のために予約のまま |
| IP の設定、recovery の案（probe-cdc §6 / §7） | v1 に入れない（規範にしない） |

### 12. label の項目

案: **probe が受ける**（describe の items に 0x02 を出す）。firmware は label を保存して core の describe（0x46）に出す。

### 13. client の公開 API

案: 公開するモジュールを決めて README に書く（`target.py` の再輸出はやめる）。設定の項目の dataclass は keyword-only
（`Slot(slot=…, wire_fn=…)`）。firmware と client の組は「同じ minor 版」と README に書く。
