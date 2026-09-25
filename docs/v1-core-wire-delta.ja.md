# Open Embedded Probe — core wire model v1（v0 からの差分）

状態: **固める途中**（2026-09-25〜。ch32rv セッションのレビューを受けながら進める）。§0 の共通の規則と §1〜§5 の core は
固める候補、§5.5 以降（線と target）は書き換え中。土台は [core wire model v0 draft](v0-core-wire-model.ja.md)。
ここに書いていない部分（要求と応答の見出し、resolution、TLV の形）は v0 のまま。

関連: [セッションと排他](session-and-exclusivity.ja.md)、[能力の宣言モデル](capability-declaration-model.ja.md)、
[能力の名前の階層](capability-name-hierarchy.ja.md)、[コンソールのストリーム](console-stream.ja.md)。

## 0. 共通の規則（2026-09-25）

**byte order**: 数値はすべて little endian。例外はない（名前などの文字列は UTF-8 のバイト列で、長さは別に持つ）。

**末尾の扱い（後から足せるようにする規則）**:

- **応答**: host は、自分の知っている形より後ろのバイトを**無視する**。probe は応答の後ろにフィールドを足してよい
  （同じ (名前, revision) の中で、足すだけ）。長さが足りない応答は、host が壊れた応答として扱う。
- **要求**: 要求の後ろに足せるのは、**critical bit 付きの TLV の並びだけ**（tag の bit 7 = critical、TLV の形は v0 と同じ
  `tag(u8) len(u8) value`）。probe は、知らない critical の TLV があれば rejected unsupported（0x0B、payload に tag）で断り、
  知らない非 critical の TLV は無視して、応答の後ろに ignored（tag 0x7F、値は無視した tag の並び）を付ける。
  要求の形が可変の並び（DMI の手順、書く語、link_sink のバイト）で終わる op は、後ろに TLV を付けられない
  （足したくなったら新しい op にする）。固定の部分より短い要求は rejected malformed。
- host が安全のために足した引数（速さの上限など）は critical にする。古い probe が黙って捨てて、効いたと思い込むのを防ぐ。

**知らない値**:

- 知らない role のフレームは捨てる。知らない resolution、completed の知らない outcome は失敗として扱う。
- インターフェースの status や reason の**知らない値は失敗として扱う**（値を足しただけで古い host が成功と誤読しないため）。
- 知らない出来事の kind は捨てる（seq は数える）。

**番号の空間**:

| 空間 | 範囲 |
|---|---|
| role | 0x01 要求、0x02 応答、0x05 出来事、0x06 データ。0x03 / 0x04 は予約（v0 の activity）、0x07〜0x7F 予約。**bit 7 は要求（host → probe）だけの意味**（session_id あり、§2）。probe → host のフレームでは bit 7 は 0 |
| core（fn 0）の op | 0x01〜0x0F 探索と plan、0x10〜0x1F セッション、0x20〜0x2F 長い操作、0x30〜0x3F 通知、0x40〜0x4F 線の試験、0x50〜0xEF 予約、0xF0〜0xFF 実験用（出荷する probe は使わない） |
| インターフェースの op | 0x01〜0xEF は定義が決める。0xF0〜0xFF は実験用 |
| reject reason | 0x01〜0x3F core が決める（全インターフェース共通）、0x40〜0x7F インターフェースが決める、0x80〜0xFF 予約 |
| 出来事の kind | fn ごとの空間。0x01〜0x7F はインターフェースが決める（fn 0 は core）、0x80〜0xFF は core が決める全 fn 共通の kind（予約） |
| TLV の tag | **(fn, op) の文脈ごとの空間**（同じ値でも文脈が違えば別物。例: core の describe の 0x46 と capture の configure の 0x46）。bit 7 は critical（要求の中で意味を持つ）。0x7F は全文脈で ignored（上記）に予約 |

**一周する値**: position（u32）、seq（u16）、時刻（µs、u32）は一周する。比べるときは差を符号付きで見る
（serial number arithmetic: `a - b` を同じ幅の符号付きとして解釈する）。probe は、同時に意味を持つ範囲（リングや
格納先の大きさ）を、position で 2 GiB、seq で 32768 フレームより十分小さく保つ。host は内部で u64 に伸ばして扱ってよい。

**名前と revision**: インターフェースの payload の形は **(名前, revision) で決まる**（list の entry の revision、u8）。
形を変えるときは revision を上げる。host は知らない revision のインターフェースを使わない。

## 1. v0 のまま使う部分

| 部分 | 形 |
|---|---|
| フレーム（USB CDC、USB-Serial/JTAG、TCP） | 長さ u16 + メッセージ。CRC なし |
| フレーム（UART） | COBS + CRC-16、0x00 で区切る。CRC は仮置きで CRC-16/CCITT-FALSE（多項式 0x1021、初期値 0xFFFF、反転なし、"123456789" → 0x29B1）、メッセージの後ろに little endian で付ける。COBS は 254 byte のブロックに分ける標準の形 |
| フレーム（USB の vendor bulk） | **長さ u16 + メッセージのバイト列**（CDC と同じ。2026-09-25 変更）。1 回の転送に複数のフレームが入ってよく、フレームが転送をまたいでもよい。下の「USB の束ね方」 |
| 要求 | `role(0x01) corr(u16) fn(u16) op(u8) payload` = 見出し 6 byte |
| 応答 | `role(0x02) corr(u16) resolution(u8) detail(u8) payload` = 見出し 5 byte |
| resolution | 0x00 rejected / 0x01 completed / 0x02 accepted |

**USB の束ね方**（vendor bulk）: 転送は長さが wMaxPacketSize の倍数なら続きがあるとみなされるので、区切りを伝える。

- host → probe: 書き込みの長さが wMaxPacketSize の倍数なら、ZLP（長さ 0 の転送）を続けて送る。
- probe → host: 送り終えて後ろに何も続かないとき、最後の転送が wMaxPacketSize の倍数なら、ZLP を送るか、最後の 1 byte を
  別の転送に分ける（ZLP を送れない USB スタックがある）。続きがすぐ来るとき（ストリーミング）は倍数のままでよい。

**区切りがずれたときの立て直し**（長さの見出しのフレーム。host）: corr が合わない応答、あり得ない長さ（0 は予約の
keepalive、max_frame を超える値）、途中で止まったフレームを見たら、入力が 50 ms 静かになるまで読み捨て、読むだけの要求
（confirm）で同期を確かめてから再開する。状態を変える要求は送り直さない。probe は、フレームの途中で 200 ms 入力が途切れたら
読み取りを最初からやり直す。したがって host は 1 つのフレームを途中で 100 ms 以上止めない。

どちらのフレームを使うかは transport で決まる。probe は自分の transport を知っている（UART の probe は COBS）。host は
USB の VID:PID で USB-UART の変換チップ（CH340 / CH343 / CP210x / FT232 など）を見分けて COBS を選び、指定で上書きも
できる。壊れた応答や応答なしのとき、host は session_id の無い要求（読むだけの要求、open）だけを 1 回送り直し、状態を
変える要求は送り直さない（シーケンスが無いので二重実行になりうる）。

## 2. 要求の見出しの session_id

```text
role=0x01          | corr | fn | op | payload                      session_id なし
role=0x81 (bit7=1) | corr | fn | op | session_id(u32) | payload     session_id あり
```

- role の bit 7 を「session_id あり」のフラグにする。見出しは増えない。bit 7 の立った role を知らない v0 の probe は、
  未知の role として捨てる（応答が来ない）。**host は、confirm の応答が revision 1 以上だった probe にだけ role 0x81 を
  送る。**
- 状態を変える要求は role 0x81 で送る。ロックなしで使える要求（confirm、list、describe、ロックの状態、status、
  コンソールの read / marks）は role 0x01 で送ってよい（0x81 で送れば期限を伸ばす）。
- open は session_id を payload で渡す（role 0x01）。

## 3. reject reason と失敗の返し方

**rejected は「要求を受け付けなかった」ときだけ**（書式、番号、セッション、今の状態で受けられない）。受け付けて実行し、
うまくいかなかったもの（target への書き込みの失敗など）は **completed の outcome（detail）を failed（1）か partial（2）**
にし、payload でどこまで進んだかと理由を返す（形はその op が決める）。

| 値 | 名前 | 意味 | detail | payload |
|---:|---|---|---|---|
| 0x01 | unknown function（v0） | その fn は無い | 0 | — |
| 0x02 | unknown operation（v0） | その fn にその op は無い | 0 | — |
| 0x03 | malformed（v0） | 長さ・値域の誤り | 0 | — |
| 0x04 | unavailable（v0） | 今の状態・資源では受けられない（plan していない、線が使用中など） | 0 | 定義が決める |
| 0x05 | busy（v0） | 長い操作が実行中。ぶつかる要求にはすぐに返す | 0 | — |
| 0x06 | window exceeded（v0） | window / max_inflight 超え | 0 | — |
| 0x07 | no session | ロックは空いているが、この session_id は最後の ID ではない。host は open からやり直す | 0 | — |
| 0x08 | locked | 他のセッションがロック中 | 0 | 残り時間 ms（u32）。今の session_id は返さない |
| 0x09 | session required | 状態を変える要求に session_id が無い（role 0x01） | 0 | — |
| 0x0A | no connection | 要求の connection を probe が知らない（attach していない、probe が再起動した、線や target の reset で失われた）。host は attach からやり直す | 0 | — |
| 0x0B | unsupported | 要求の critical の TLV（または値）を probe が扱えない | 0 | 扱えない tag（u8） |

- rejected の detail は 0（v0 から予約）。追加の情報は payload に置く。
- boot_id が変わった（open の応答、ハートビート）、または boot_id が 0（不明）の probe で「no session」を受けたら、host は
  すべての connection と plan が失われたとみなす。同じ boot_id で再開（resumed）できたときは、connection はそのまま使える。

判定の表は [セッションと排他](session-and-exclusivity.ja.md) の「要求を受けたときの判定」。

## 4. 長い操作はポーリング

- accepted の応答は activity の番号（u16）を返す（v0 と同じ）。
- host は core の `status(activity)` を投げる。応答は completed（最終結果。payload はその操作の結果）か、accepted と
  進捗 `done(u32) total(u32)`（total が分からなければ 0）。
- 実行中の長い操作は probe 全体で 1 つ。最後の結果は同じ session_id の間だけ取り出せ、新しい session_id でロックが
  立ったら消える。
- v0 の probe から送る role のうち 0x03 activity update、0x04 activity outcome は v1 では使わず、予約として残す。
  0x05 と 0x06 は §4.5 の通知に使う。

## 4.5 probe から送る通知（2026-09-25 の実験で動作を確認）

**probe から自動で送る仕組みを v1 に入れる。** 後から足すと、応答だけを想定した host が壊れるため。probe の対応は任意、
host は購読しなければ何も受け取らない。

### host の義務（全 host）

- 受け取ったフレームを **role で振り分ける**。corr で照合するのは role 0x02（応答）だけ。0x05 / 0x06 のフレームの
  バイト 1〜2 は fn なので、role を見ずに corr として照合すると、fn がたまたま corr と同じ値のときに応答と取り違える
  （oep-client-python は 2026-09-25 まで role を見ていなかった）。
- 知らない role のフレームは捨てる。
- データが途切れず届き続けても、要求の応答を待つ処理と、受信を読む処理が締め切りどおりに終わること（届くたびに待ち時間を
  延ばす作りだと抜けられない。client の試作で一度踏んだ）。

### 形

```text
データ   role=0x06 | fn(u16) | seq(u16) | position(u32) | data         見出し 9 byte
出来事   role=0x05 | fn(u16) | seq(u16) | kind(u8) | payload           見出し 6 byte
```

- `seq` は fn ごとのフレームの通し番号（一周する。データと出来事で共通）。抜けがあればフレームが失われた。
  subscribe のたびに 0 から数え直す。
  **probe は、生まれた出来事すべてに番号を振る。** probe の中で捨てたもの（割り込みの記録があふれた、送信待ちの
  キューがあふれた）も番号を消費し、host は抜けとして数えられる。
- fn 0 の出来事は probe 全体のもの。kind 0x01 = ハートビート（payload: boot_id u32、起動からの ms u32）。kind の空間は §0。
- `position` はその fn のストリームの中のバイト位置（一周する）。前のフレームの終わりと合わなければ、その間は
  probe の中で押し出された（host や線が遅れた）。
- 送ったデータを位置指定の読み出し（ポーリング）で読み直せるかは、インターフェースの定義による（2026-09-25 変更。
  コンソールは読める。ロジックのストリーミングは、コピーなしで送る probe がデータを残さないので読めなくてよい。
  読めない位置の読み出しは、gap の印を付けた空の応答）。

### 購読（core の操作）

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x30 | subscribe | fn(u16)、[min_bytes(u16)、max_delay_ms(u16)] | — | 必要 |
| 0x32 | unsubscribe | fn(u16) | — | 必要 |

- **購読はロックの持ち主だけができ、ロックと一緒に終わる**（end、期限切れ、**force で他の host に奪われたとき**）。
  host が消えても、期限が来れば probe は送るのをやめる。購読している host は keepalive などでロックを保つ。
- 送り出さないインターフェースは subscribe を rejected unavailable にする。
- **まとめて送る条件**: `min_bytes` バイトたまるか、最初のバイトから `max_delay_ms` 経ったら送る（省略または 0 なら、
  あるだけすぐ送る）。1 フレームの大きさは、probe の送りかけの上限（下の probe の義務 2）でも区切られる。
- fn 0 を購読するとハートビートが来る。周期は `max_delay_ms`（省略または 0 なら 1000 ms）。
- host が与える予算（クレジット）は持たない。流れの量は、取得を始めるとき（capture の configure など）に決まっているので、
  線に収まるかは host が事前に計算できる。host や線が遅れた分は probe の中で押し出され、position の飛びで分かる。

### probe の義務（送り出す probe）

1. **応答を先に送る。** 届いている要求をすべて処理してから、データを送る。
2. **送りかけのデータを小さく保つ。** 送信の経路（USB の送信バッファ、UART の送信バッファ）に、データが決めた量を超えて
   たまらないようにし、書き込みで待たない。要求の応答は、たまっているデータの後ろに並ぶので、その量がほかの操作の
   遅れの上限になる。量は probe が自分の線の速さから決める（目安: 線の速さ × 1 ms〜数 ms。USB-Serial/JTAG で 256 B、
   115200 の UART で 64 B 程度）。

### 実験（2026-09-25、oep.test.counter: 指定の速さでバイトを生み、8 KiB を超えて遅れたら押し出す試作のインターフェース）

**送りかけの量と、ほかの要求（lock_state）の遅れ**（P4、USB-Serial/JTAG。流していないとき中央値 0.44〜0.55 ms）:

| probe の制御 | 500 kB/s を流している間 | 800 kB/s を流している間 |
|---|---|---|
| 制御なし（送信バッファ 8 KiB いっぱいまで詰める） | 中央値 9.7 ms | 9.8 ms |
| 応答を先に + 送りかけ 1 KiB まで | 1.66 ms | 1.74 ms |
| **応答を先に + 送りかけ 256 B まで** | **0.69〜0.73 ms** | **0.84〜0.86 ms** |

- 送りかけを 256 B にしても、届く量は変わらなかった（約 710 kB/s。この試作の上限）。
- host の予算（クレジットの枠 32 KiB）で抑えたときも中央値 0.6 ms だったが、上の制御なら予算なしで同じになる。

**UART の probe**（classic ESP32、COBS、送りかけ 256 B。流していないとき 4.6 ms）: 2 / 5 / 8 kB/s で中央値 5.1 / 7.5 / 10.1 ms、
線の上限（約 11 kB/s）を超える 20 kB/s で 20.5 ms。256 B はこの線で約 23 ms 分なので、UART では 64 B 程度が適当。
制御なしで予算 4 KiB のときは 85〜240 ms だった。

**ロックとの結び付け**（P4、ロックの期限 1.5 s、200 kB/s）: ロックなしの subscribe は session required で断られた。keepalive を
続けている間は届き続け、host が何も送らなくなると、最後の要求から 1.10〜1.15 s（WSL の時計の遅れを含む）で送信が止まり、
以降は無音。ロックも解けていた。

**まとめて送る条件**（P4、50 kB/s、送りかけ 256 B）: 条件なしは 3 秒で 96,148 フレーム（平均 2 B）、`512 B か 5 ms` と
`4 KiB か 20 ms` はどちらも約 650 フレーム（平均 245 B。送りかけ 256 B が 1 フレームの上限になった）。ほかの要求は中央値
0.6〜0.7 ms で変わらない。

**出来事**（P4、試作の oep.test.edge: probe が自分のピンを反転し、同じパッドの割り込みで時刻とレベルを記録して送る）:
- 1 回の反転: 要求を送ってから出来事を読むまで中央値 0.6 ms（普通の要求の往復と同じ程度）。
- 200 回（20 µs / 2 µs 間隔）と 2000 回（2 µs 間隔）の連続: 送信待ちのキュー（32 件）と割り込みの記録（256 件）があふれ、
  届いたのは 32 件。**届いた数 + seq の抜けの数 = 反転の回数**（200 / 200 / 2000）で、失われた分をすべて数えられた。
  届いたもののレベルは交互で、時刻の間隔は 25 µs / 7 µs。
- ハートビート（周期 200 ms）: 間隔 200 ms、boot_id 入り。end で止まった。

**そのほか**: 購読していない間は何も来ない。化けは全条件で 0。通知の利点は速さではなく、応答の待ち時間と、host が
位置を管理しなくてよいこと。

### 未決

1. （2026-09-25 決定）まとめて送る条件は subscribe の min_bytes / max_delay_ms（上記）。
2. （2026-09-25 決定、§0）出来事の kind は fn ごとの空間で、インターフェースが定める。全 fn 共通の kind（0x80〜）は予約。
3. （2026-09-25 決定）ロックの持ち主以外の購読は扱わない。ロックなしで読めるもの（コンソールの read など）は、ポーリングの
   読み出しとしてはロックなしのまま残す。検討した用途はどれもロックの持ち主で足りた: シリアルモニタ（線を開けるのは
   1 プロセスだけなので、モニタが唯一の host としてロックを取ればよい。書き込みのときはモニタが閉じる）、複数ツールでの
   共有（間に多重化するデーモンを置き、デーモンがロックを持って配る）、ハートビートだけ見る診断ツール（取ればよい）。
   複数の host が同時につながる transport（TCP など）を入れるときに改めて決める。
4. （2026-09-25 決定）時刻は probe の起動からの µs（u32、約 71 分で一周）。差として使い、比べ方は §0 の一周する値。

## 5. core（fn 0）の操作

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | confirm | `"OEP?"`、min_rev(u8)、max_rev(u8) | `"OEP!"`、revision(u8)、flags(u8)、max_frame(u16)、window(u32)、max_inflight(u8) | 不要 |
| 0x02 | list | flags(u8、bit0 = exact)、first(u16)、prefix_len(u8)、prefix | total(u16)、count(u8)、entries | 不要 |
| 0x03 | describe | fn(u16)、first(u16) | more(u8)、TLV。fn 0 は probe 全体の宣言 | 不要 |
| 0x04 | plan_apply | role_assignment の TLV（0x90、critical: fn(u16) role(u8) channel(u16)）の並び | — | 必要 |
| 0x05 | plan_release | — | — | 必要 |
| 0x10 | open | session_id(u32)、lease_ms(u32)、force(u8) | lease_ms(u32)、boot_id(u32)、resumed(u8) | open がロックを取る |
| 0x11 | end | — | — | 必要（role 0x81） |
| 0x12 | keepalive | — | — | 必要（role 0x81） |
| 0x13 | lock_state | — | locked(u8)、remaining_ms(u32) | 不要 |
| 0x20 | status | activity(u16) | 上記 §4 | 不要 |
| 0x21 | cancel | activity(u16) | —（止められなければ rejected unavailable） | 必要 |
| 0x40 | link_source | length(u32) | length バイト（1 フレームに入る分まで）。k バイト目は k & 0xff | 不要 |
| 0x41 | link_sink | 任意のバイト | 受け取った長さ(u32) | 不要 |

- **confirm**（2026-09-25 決定）: host は扱える revision の範囲を送り、probe はその中で自分の扱える最大の revision を返す
  （このドキュメントの形は revision 1）。範囲に扱えるものが無ければ rejected unsupported。v0 の probe も同じ要求に
  `"OEP!"` と revision 0 で答える（v0 の形）ので、host は revision で見分けて、1 以上のときだけ v1 の要求（role 0x81 など）を
  送る。flags は予約で 0。window は u32（v0 の u16 から広げた。read-ahead に 256 KiB 要る実測がある）。
- list の entry: `fn(u16) instance(u16) revision(u8) flags(u8) name_len(u8) name`。**`oep.core`（fn 0、revision 1）も
  最初の entry として数える**。total と first は u16、1 つの応答の count は u8（1 フレームに入る分）。
- describe の first は TLV の番号（u16）。1 つのインターフェースの宣言が 255 個の TLV を超えてよい（ピンごとのラベル）。
- open の `resumed` は、同じ session_id でロックを立て直した（再開）とき 1。
- plan は v0 と同じ形（全インターフェースが自分の役割を受け入れたときだけ適用、1 つずつ）。割り当ては probe の状態で、
  セッションの終わりやロックの期限切れでは解かない（plan_release でだけ解く）。
- 最初の実装（2026-09-24）では、fixture（gpio / uart / capture）の各操作の payload は v0 のまま（書き換え中、別の文書）。
- **core の op の番号は確定**（2026-09-25。範囲は §0）。
- **link_source / link_sink は線の速さを測るためのもの**（2026-09-25）。host は応答の大きさと同時に出す本数を変えて
  両方向の要求・応答の速さを測り、キャプチャのストリーミングが続くか（logic-capture §5）や、書き込みにかかる時間の
  見積もりに使う。状態を変えないのでロックは要らない。source の応答は 1 フレームの上限（max_frame）で切ってよい。
  実測（P4 HS、direct build、usbipd）: probe → host は 16 KiB × 16 本で 31 MB/s、host → probe は 5.5 MB/s
  （logic-capture §7.10）。

## 5.5 `oep.wire.<線>` と `oep.target.riscv-dm` の操作（仮置き、最初の実装の形）

名前の置き方は [能力の名前の階層](capability-name-hierarchy.ja.md)。番号と書式は仮で、ch32rv のレビュー
（2026-09-24）を受けて足したものを含む。

`oep.wire.rvswd` / `oep.wire.swio`:

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | scan | — | count(u8)、kind(u8) swdio(u16) swclk(u16) DMSTATUS(u32) の並び（生の値） |
| 0x02 | attach | method(u8: 0 止めない / 1 止める) | connection(u8)、DMSTATUS(u32)、flags(u8: bit0 保留中の havereset を確認応答した) |
| 0x03 | detach | connection(u8) | — |
| 0x04 | attach_under_reset | channel(u16、0xffff = probe の既定値)、hold_ms(u16) | connection(u8)、dpc(u32) |

- attach は保留中の havereset を先に確認応答する（V00x の DM は確認応答まで DMSTATUS の halt / running を固定する）。
- attach_under_reset はリセットの線を保持して attach し、離しながら halt を打ち続ける（タイミングが厳しいので probe の
  1 操作）。host が指定できるのは probe が許可したチャンネルだけ。任意の op（持たない probe は unsupported）。
  持たない probe では、host は `oep.fixture.gpio` の解放と attach をまとめて送って再試行する（窓の縁の競争）。

`oep.target.riscv-dm`（最初の byte は connection）:

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | dmi | 手順の並び（下表） | done(u16)、status(u8: 0 ok / 1 書式 / 2 アクセス / 3 待ち切れ)、read の値 |
| 0x02 | halt | — | — |
| 0x03 | resume | — | — |
| 0x04 | reset | mode(u8: 0 走らせる / 1 走らせて実行を確認 / 2 最初の命令の前で止める) | flags(u8)、attempts(u8)、pc(u32)（mode 2 では dpc） |
| 0x05 | read_block | address(u32)、count(u16) | 語の並び |
| 0x06 | write_block | address(u32)、語の並び | — |
| 0x07 | run | pc(u32)、timeout_ms(u16)、n(u8)、n × (regno u16、value u32) | stopped(u8)、dpc(u32)、a0(u32)、elapsed_us(u32) |
| 0x08 | step | — | moved(u8)、dpc_before(u32)、dpc_after(u32) |

DMI の手順:

| kind | 手順 | 引数 |
|---:|---|---|
| 0x01 | 書く | address(u8)、value(u32) |
| 0x02 | 読む | address(u8)（値を応答に足す） |
| 0x03 | 読む回数を上限に待つ | address(u8)、mask(u32)、value(u32)、max_reads(u16) |
| 0x04 | 待ち | us(u32) |
| 0x05 | 時間を上限に待つ | address(u8)、mask(u32)、value(u32)、max_us(u32)（線の速さに依らず同じ意味） |

- reset の mode 2 は haltreq を保ったまま ndmreset を解く。semihosting、gdb の `monitor reset halt`、動いている
  ウォッチドッグの上からの書き込みに使う（IWDG は hart を止めても数え続ける）。
- step は dcsr.step を立てて resume を 1 回だけ出し、成否は dpc が動いたかで判定する（L103 は allresumeack を立てず、
  resume の出し直しは 2 ステップ進めてしまう）。prv は変えない（U モードのスケッチのステップ実行）。
- run は dcsr の ebreakm と prv = M を立てる（host のローダー用。割り込みは host が mstatus = 0 で止める）。
  止まった位置が開始位置のままなら、走らなかったとみなして resume を出し直す。
- 一つの要求は一つの hart の操作で、DMI の手順のリストは probe の都合（線の再試行、立て直し）を書けない。
  リセットや回復のようにタイミングと線の立て直しが要るものは、部品（reset、attach_under_reset）にする。

## 5.6 `oep.wire.swd` と `oep.target.arm-adi` の操作（仮置き、2026-09-24 の最初の実装）

`oep.wire.swd`（scan の kind は 0x02 = arm-adi）:

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | scan | — | count(u8)、kind(u8) swdio(u16) swclk(u16) DPIDR(u32) の並び |
| 0x02 | attach | [TARGETSEL(u32)]（multidrop のときだけ） | connection(u8)、DPIDR(u32)、flags(u8: bit0 dormant から起こした) |
| 0x03 | detach | connection(u8) | — |

- attach は JTAG から SWD への切り替えを試し、答えがなければ dormant から起こす（RP2350 の SWD v2 は後者でだけ答える）。
  電源投入（CTRL/STAT の CDBGPWRUPREQ / CSYSPWRUPREQ）は host が DP の書き込みで行う。
- attach_under_reset は持たない（任意の op）。

`oep.target.arm-adi`（最初の byte は connection）:

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | transfer | 転送の並び: req(u8: bit0 APnDP、bit1 RnW、bit2-3 A[3:2]) と、書き込みなら value(u32) | done(u16)、status(u8: 0 ok / 1 書式 / 2 FAULT / 3 応答なし・パリティ / 4 WAIT のまま)、ack(u8)、読んだ値の並び |
| 0x02 | read_block | address(u32)、count(u16) | 語の並び |
| 0x03 | write_block | address(u32)、語の並び | — |

- transfer は生の転送で、AP の読み出しが 1 つ遅れて返るのもそのまま（host が RDBUFF か次の AP の読み出しで受け取る）。
  WAIT は probe の中で再試行する。FAULT で止まるので、host は ABORT で sticky を消す。
- read_block / write_block は今の MEM-AP の TAR / DRW を使う。SELECT（TAR / DRW のある bank）と CSW（32 bit、単一増加、
  保護の属性）は host が先に設定する。probe は 1 KiB の境界ごとに TAR を書き直し、1 つ遅れる読み出しを並べ直す。
- **flash の書き込みまで通した**（2026-09-24、RP2040-Zero → Pro Micro RP2350）: host が core 0 を止め、DCRSR / DCRDR で
  レジスタを置き、SRAM の BKPT へ戻る形で boot ROM の flash 関数（connect_internal_flash → exit_xip → range_erase →
  range_program → flush_cache → enter_cmd_xip）を呼ぶ。98 KiB のイメージを消去 0.3 秒、書き込み 3.0 秒、読み戻しの
  検証 2.0 秒。ROM の reboot でチップごと再起動し、USB が再列挙して probe の firmware が戻った。target の知識
  （ROM の表の引き方、関数の並び、CSW のセキュア属性、DHCSR の C_MASKINTS がリセットを越えて残ること）はすべて host 側
  （oep-client-python の `arm.CortexM`、`rp2350`）。
- 実測（RP2040-Zero → Pro Micro RP2350、ADIv6、半周期 500 ns）: 読み出し約 47 KiB/s。AP は 0x2000 / 0x4000（Cortex-M33 の
  AHB-AP、IDR 0x34770008）、0xA000（APB-AP）、0x80000（RP-AP）。AHB-AP は非セキュア（CSW bit 30）で上がってきて、
  そのままでは SRAM が FAULT になる（セキュアにすると読める）。

## 6. 長さの確認（64 byte のフレーム）

- list の応答: 見出し 5 + list の見出し 2 + 1 項目（7 + 名前 48）= 62 byte。
- 状態を変える要求の見出し: 6 + 4 = 10 byte。payload に 54 byte 使える。

## 未決

1. （2026-09-25 決定、§5）confirm は範囲を送り、revision と flags を返す。
2. （2026-09-25 決定、§0）op の番号の空間と core の番号。
3. UART の binding のシーケンス（重複の判定）の置き場（[UART connection epoch](uart-connection-epoch.ja.md) の候補から）。
