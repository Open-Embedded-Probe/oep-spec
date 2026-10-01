# v1 凍結前の決定（2026-09-30）

状態: **決定**（2026-09-30。★ の 3 つはユーザーが選んだ。ほかは案のとおりで進め、規範の文書に移す）。発端は bench（arduinocore）がエコシステム全体を洗い出した
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
