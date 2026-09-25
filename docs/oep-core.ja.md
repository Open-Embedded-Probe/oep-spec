# Open Embedded Probe — プロトコル本体（OEP core）v1

状態: **規範**（v1 を固める候補、2026-09-26）。この文書は OEP のプロトコル本体だけを定める。標準インターフェース
（線、デバッグ、コンソール、fixture、キャプチャ、probe の設定）はそれぞれの文書が定める（§14）。決めた理由と実験の記録は
規範ではない文書に置く（§15）。この文書と、規範ではない文書が食い違えば、この文書が正しい。

番号（op、tag、reject reason、status、enum）の唯一の定義は `registry/oep-v1.toml` で、この文書の表はその写しである。
食い違えば registry が正しく、文書を直す。

## 0. 範囲と層

OEP は 3 つの層からなる。

| 層 | 中身 | 名前 | 版 |
|---|---|---|---|
| **本体（この文書）** | どの probe と host も、機能に関係なく実装するもの: 経路とフレーム、メッセージ、セッションと排他、発見（confirm / list / describe）、plan、資源の寿命の一般の規則、長い操作、通知の仕組み、拡張の規則 | `oep.core`（fn 0） | プロトコルの revision（confirm） |
| **標準インターフェース** | 本体の仕組みだけで定義した、名前つきの機能 | `oep.` で始まる名前 | インターフェースごとの revision |
| **拡張** | 標準インターフェースの任意機能と別の定義、独自のインターフェース | `oep.` の別の定義、または逆 DNS の名前 | それぞれ |

**線引きの規則**:

1. 本体に入れるのは、host がインターフェースの名前を知る前に要るもの、またはすべてのインターフェースにまたがり、どれか 1 つの
   インターフェースでは定義できないものだけである。
2. 本体の仕組みだけで名前つきのインターフェースとして定義できるものは、どの probe も持つとしても本体に入れない
   （判定の問い: 第三者が、本体を変えずに、独自の名前で同じものを定義できたか）。
3. 本体は、特定のインターフェースの名前にも意味にも触れない（`oep.core` を除く）。
4. 標準インターフェースに、本体の上での特別扱いは無い。独自のインターフェースと同じ仕組みだけを使う。違いは、名前が
   `oep.` で、番号が project の registry にあり、project が適合試験を持つことだけである。
5. インターフェースどうしの関係（あるインターフェースが別のインターフェースの資源を使う、など）は、関係するインターフェースの
   文書が定める。
6. 版は層ごとに独立する（§2.7）。

OEP の外: probe 自身の firmware の更新（DFU、Mass Storage など）、OEP の制御に使わない USB の機能（コンソール専用の CDC の口
など）、USB の記述子の細部。

## 1. 用語

| 用語 | 意味 |
|---|---|
| probe | OEP を話す装置（デバッガ、治具、ロジアナなど） |
| host | probe を使うソフトウェア |
| target | probe がつながる相手（開発中のマイコンなど） |
| 経路（transport） | OEP のフレームを運ぶもの（USB の vendor bulk、HID、CDC、USB-Serial/JTAG、UART、TCP） |
| インターフェース | probe が名前で出す機能。list で見つけ、fn で呼ぶ |
| fn | そのセッションの間、インターフェースを指す番号（u16）。fn 0 は `oep.core` |
| op | インターフェースの中の操作の番号（u8） |
| セッション | ロックを持って状態を変える権利。host が選ぶ session_id（u32）で識別する |
| lease | ロックの期限。keepalive などの要求で延びる |
| channel | probe のピンの番号（u16） |
| plan | どのインターフェースのどの役（role）に、どの channel を使うかの割り当て |
| activity | 長い操作（§10）の番号（u16） |

## 2. 共通の規則

### 2.1 byte order と文字列

数値はすべて little endian。文字列は UTF-8 のバイト列で、長さは別に持つ（終端の 0 は付けない）。

### 2.2 TLV

```text
tag(u8) | len(u8) | value(len byte)
```

- **tag の bit 7 は critical**（要求の中でだけ意味を持つ）。tag 0x7F は応答の ignored 専用、0xFF は無効。
- tag の空間は **(fn, op) の文脈ごと**（同じ値でも文脈が違えば別物）。
- 同じ tag の繰り返しは並びを表す。

### 2.3 固定部分と末尾

- **応答**: 各 op の応答の固定部分（と、前に数を置いた並び）の後ろは TLV の並び。後から足すものはすべてここに TLV で足す。
  host は知らない tag を読み飛ばす。長さの分からない並び（読み出したバイト列など）で終わる応答は、後ろに何も足せない。
  固定部分より短い応答は壊れた応答として扱う。
- **要求**: 要求の後ろに足せるのは TLV の並びだけで、host は **critical の bit を付けて送る**。probe は、知らない critical の
  TLV があれば rejected unsupported（payload に受け取ったままの tag）で断る。知らない非 critical の TLV は無視し、応答の
  後ろに ignored（tag 0x7F、値は無視した tag の並び）を付ける。
- 知っている TLV でも、その値を扱えなければ、critical なら rejected unsupported、そうでなければ無視して ignored に載せる。
- 要求の中に tag 0x7F か 0xFF があれば rejected malformed。固定部分より短い要求は rejected malformed。
- **可変の並びは前に数を置く**（後ろに TLV を付けられるように）。数を持たない並びで終わる op だけは後ろに何も付けられない。
- 固定部分に省略できるフィールドを置かない（省略したい値は TLV にする）。
- host が安全のために足す引数（速さの上限など）は critical にする。

### 2.4 知らない値

- 知らない role のフレームは捨てる。
- 知らない resolution、completed の知らない outcome は失敗として扱う。
- インターフェースの status や reason の知らない値は失敗として扱う。
- 知らない出来事の kind は捨てる（seq は数える）。

### 2.5 番号の空間

| 空間 | 範囲 |
|---|---|
| role | 0x01 要求、0x02 応答、0x05 出来事、0x06 データ。0x03 / 0x04 は予約、0x07〜0x7F は予約。bit 7 は要求だけの意味（session_id あり、§4.1）。probe → host のフレームでは bit 7 は 0 |
| core（fn 0）の op | 0x01〜0x0F 発見と plan、0x10〜0x1F セッション、0x20〜0x2F 長い操作、0x30〜0x3F 通知、0x40〜0x4F 線の試験、0x50〜0xEF 予約、0xF0〜0xFF 実験用（出荷する probe は使わない） |
| インターフェースの op | 0x01〜0xEF はインターフェースの定義が決める。0xF0〜0xFF は実験用 |
| reject reason | 0x01〜0x3F 本体（全インターフェース共通）、0x40〜0x7F インターフェース、0x80〜0xFF 予約 |
| outcome | 0 success、1 failed、2 partial。ほかは予約 |
| 出来事の kind | fn ごとの空間。0x01〜0x7F はインターフェースが決める（fn 0 は本体）、0x80〜0xFF は予約 |
| TLV の tag | (fn, op) の文脈ごと。bit 7 は critical。0x7F と 0xFF は全文脈で予約 |
| describe の tag | 0x01〜0x3F 本体の共通タグ（§7.4）、0x40〜0x7F インターフェース |

### 2.6 一周する値

seq（u16）と、インターフェースが定める通し番号や時刻のうち一周すると定めたものは、差を同じ幅の符号付きとして比べる
（serial number arithmetic）。probe は同時に意味を持つ範囲を、その幅の半分より十分小さく保つ。一周させない値は u64 にする
（標準インターフェースのストリームの位置など）。

### 2.7 名前と revision

- インターフェースの payload の**固定部分**の形と意味は **(名前, revision) で決まる**（list の revision、u8）。
- **revision を上げるのは、固定部分の意味か長さを変えるときだけ**。host は知らない revision のインターフェースを使わない。
- 固定部分を変えずに、任意の request TLV、response TLV、任意の op、任意の event を足すときは、revision を変えない。知らない
  host はそれらを使わない。任意の op やモードの有無は describe（features など）で宣言する。
- 固定部分を変える revision を入れる probe は、できれば古い revision も別の fn として同時に出す。
- 名前を変えるのは、インターフェースの意味が変わるときだけ。
- 本体の形を変えるときは、プロトコルの revision（confirm）を上げる。この文書の形は revision 1。

## 3. 経路とフレーム

### 3.1 フレーム

| 経路 | フレーム |
|---|---|
| USB CDC、USB-Serial/JTAG、TCP | `length(u16) message`。CRC なし。length 0 は予約（keepalive。読み飛ばす） |
| USB の vendor bulk | CDC と同じ `length(u16) message` のバイト列。1 回の転送に複数のフレームが入ってよく、フレームが転送をまたいでもよい |
| USB の HID（vendor 定義の report） | 長さつきのフレームのバイト列を report に詰める。report = `count(u16)`、count バイト、0 埋め（report の大きさは HID の記述子のとおり）。記述子が report ID を宣言していれば、input も output も report の先頭に ID が付き、count はその後ろから数える |
| UART（USB-UART の変換チップ越しを含む） | COBS + CRC-16、0x00 で区切る。CRC は CRC-16/CCITT-FALSE（多項式 0x1021、初期値 0xFFFF、反転なし、"123456789" → 0x29B1）を message の後ろに little endian で付ける。COBS は 254 byte のブロックに分ける標準の形 |

- **USB の束ね方**（vendor bulk）: host は、書き込みの長さが wMaxPacketSize の倍数なら長さ 0 の転送を続ける。probe は、送り
  終えて後ろに続かないとき、最後の転送が wMaxPacketSize の倍数なら、長さ 0 の転送を送るか最後の 1 byte を別の転送に分ける。
  続きがすぐ来るときは倍数のままでよい。
- どのフレームを使うかは経路で決まる。host は USB の VID:PID で USB-UART の変換チップを見分けて COBS を選び、指定で上書き
  できる。
- **TCP は、信頼できるローカルの接続か、認証したトンネルの内側でだけ使う。** OEP は認証を持たない（§6.4 の force を含む）。

### 3.2 フレームの送り方

- host は **1 つのフレームを 1 回の書き込みで送り**、フレームの途中で 100 ms 以上止めない。
- probe は、フレームの途中で 200 ms 入力が途切れたら読み取りを最初からやり直す。

### 3.3 複数の経路

- probe は OEP の制御を複数の経路で受けてよい。**複数の経路はセッションとロックを 1 つ共有する**。どの経路から来た要求も同じ
  ものとして扱い、応答はその要求の来た経路に返す。通知は subscribe が来た経路に送る（§11.4）。
- host は、同じ probe に複数の経路があれば vendor bulk、HID、CDC の順に試す。CDC で OEP を運ぶのは、ほかに手がないときに限る
  （CDC の口はシリアルの転送にも使われる）。

## 4. メッセージ

### 4.1 要求

```text
role=0x01 | corr(u16) | fn(u16) | op(u8) | payload                      見出し 6 byte（session_id なし）
role=0x81 | corr(u16) | fn(u16) | op(u8) | session_id(u32) | payload    見出し 10 byte（session_id あり）
```

- `corr`: host が振る番号。同じ probe の未解決の要求の間で重複させない。0 は使わない。
- 状態を変える要求は role 0x81 で送る（§6.3）。ロックなしで使える要求は 0x01 で送ってよい（0x81 で送れば lease が延びる）。
- host は、confirm の応答が revision 1 以上だった probe にだけ role 0x81 を送る。

### 4.2 応答

```text
role=0x02 | corr(u16) | resolution(u8) | detail(u8) | payload           見出し 5 byte
```

| resolution | 値 | detail | payload |
|---|---:|---|---|
| rejected | 0x00 | reject reason（§4.3） | reason が定める補助の情報 |
| completed | 0x01 | outcome（0 success、1 failed、2 partial） | op が定める |
| accepted | 0x02 | 0 | activity（u16）と op が定める初期の情報（§10） |

- 要求ごとに応答はちょうど 1 つ。応答はその要求の来た経路に、同じ corr で返す。fn と op は返さない。
- **rejected は「要求を受け付けなかった」ときだけ**（書式、番号、セッション、今の状態で受けられない）。受け付けて実行した
  結果うまくいかなかったものは completed の failed か partial にし、payload でどこまで進んだかと理由を返す。

### 4.3 reject reason（本体）

| 値 | 名前 | 意味 | payload |
|---:|---|---|---|
| 0x01 | unknown_function | その fn は無い | — |
| 0x02 | unknown_operation | その fn にその op は無い | — |
| 0x03 | malformed | 長さ・値域の誤り | — |
| 0x04 | unavailable | 今の状態・資源では受けられない | インターフェースが定める |
| 0x05 | busy | 長い操作が実行中で、ぶつかる | open(force) のときはロックの残り時間 ms（u32） |
| 0x06 | window_exceeded | window / max_inflight を超えた | — |
| 0x07 | no_session | ロックは空いているが、この session_id は最後の ID ではない。host は open からやり直す | — |
| 0x08 | locked | 他のセッションがロックを持つ | 残り時間 ms（u32） |
| 0x09 | session_required | 状態を変える要求に session_id が無い | — |
| 0x0A | no_connection | 要求の資源（connection など）を probe が知らない。host は作り直す | — |
| 0x0B | unsupported | critical の TLV か固定部分の値を扱えない | TLV のときは受け取ったままの tag（u8）、固定部分の値のときは無し |
| 0x0C | result_lost | 送り直された要求の結果を覚えていない（§5.2） | — |
| 0x0D | corr_reused | 同じ corr で fn、op、中身のどれかが違う要求が来た（§5.2） | — |

rejected の detail は reason で、そのほかの情報は payload に置く。

### 4.4 パイプライン

- confirm（§7.1）で probe は `max_frame`（受け取る最大の message 長）、`window`（未解決の要求の message 長の合計の上限）、
  `max_inflight`（未解決の要求の数の上限）を返す。
- host は両方の上限を守る。超えた要求を probe は rejected window_exceeded で断ってよいが、バッファを超えて失われた要求には
  応答も返らない。守るのは host の責任である。
- probe は要求を受け取った順に処理し、応答を受け取った順に返す。

## 5. 立て直しと送り直し

### 5.1 区切りの立て直し（長さつきのフレーム）

host は、corr の合わない応答、あり得ない長さ（max_frame を超える）、途中で止まったフレーム（続きが 200 ms 来ない）を見たら、
入力が 50 ms 静かになるまで読み捨て、confirm（範囲は 0〜255 でよい）を送って自分の corr の応答が返ることを確かめてから
再開する。応答の末尾の TLV が途中で切れていたら、その応答は壊れている。通知が流れ続けて入力が静かにならないときは、
unsubscribe と end を確かめずに送ってよい（二度実行しても害がない）。COBS のフレームは CRC で壊れたものを捨てられるので、
この手順は要らない。

### 5.2 送り直しと重複排除

- 応答が壊れたか来なかったとき、host は**同じ corr で 1 回送り直してよい**（状態を変える要求も）。立て直しの中で unsubscribe
  と end を送ったときは、セッションが終わっているので、元の要求は送り直さない。
- probe は、ロックを持つセッションの要求（role 0x81）について、直近の max_inflight 個以上の (corr, fn, op, 要求の payload の
  CRC-32, 応答) を覚えておく。同じ corr の要求が来たら:
  - fn、op、CRC が同じなら、**実行せずに覚えた応答を返す**。
  - 違えば rejected corr_reused。
- 覚えておく応答の大きさには上限を置いてよい。上限を超えて覚えていない応答の要求を送り直されたら、実行せずに rejected
  result_lost（host は状態を読み直して確かめる）。
- **覚えた表は open（resume を含む）のたびに捨てる。** セッションが変わったときの exactly-once は約束しない。
- 読むだけの要求は重複排除しなくてよい。
- CRC-32 は IEEE（reflected、多項式 0xEDB88320、初期値と最終の XOR 0xFFFFFFFF。"123456789" → 0xCBF43926）。

## 6. セッションと排他

### 6.1 ロック

- probe は**ロックを 1 つ**持つ。ロックを持つセッションだけが状態を変える要求を実行できる。
- session_id は host が選ぶ（乱数でよい）。probe は最後にロックを持った session_id を覚えている。
- lease は open で決まり、ロックを持つセッションの要求（role 0x81）が完了するたびに延びる。期限を過ぎるとロックは空く
  （§9 の期限切れ）。

### 6.2 要求を受けたときの判定

| ロック | 要求の session_id | 結果 |
|---|---|---|
| 空き | 最後の session_id と同じ | ロックを立て直して処理する（再開） |
| 空き | 違う（open 以外） | rejected no_session |
| 空き | open（任意の ID） | ロックを立て、最後の session_id を更新する |
| 自分が持つ | 同じ | 処理する |
| 他が持つ | 違う | rejected locked と残り時間 |
| 他が持つ | open(force) | 奪う（§6.4） |

### 6.3 ロックの要る要求

状態を変える要求はすべてロックが要る（role 0x81）。ロックなしで使えるのは、状態を変えない読むだけの要求に限る
（confirm、list、describe、lock_state、status、link_source / link_sink、インターフェースが定める読むだけの op）。インターフェース
がロックなしとする op は、状態を変えてはならない。

### 6.4 open、end、keepalive、force

- **open**（session_id、lease_ms、force）: ロックを取る。応答は lease_ms（probe が決めた値）、boot_id、resumed（同じ session_id
  で立て直したとき 1）。open のたびに §5.2 の表を捨てる。
- **end**: ロックを離す。セッションの資源は残す（§9）。
- **keepalive**: lease を延ばすだけ。
- **lock_state**: ロックの有無と残り時間。
- **force**: 他のセッションがロックを持っていても奪う。probe は、前のセッションに対して期限切れと同じ後始末をし（§9）、実行中の
  長い操作を cancel できれば cancel してからロックを渡す。cancel できない長い操作が実行中なら rejected busy（payload に残り
  時間）で断る。force は認証ではなく、取り違えを防ぐだけのものである。

### 6.5 boot_id

open の応答の boot_id は probe の起動ごとに変わる値（0 は不明）。host は、boot_id が変わったとき、または boot_id が 0 の probe で
no_session を受けたとき、そのセッションの資源（plan、インターフェースの資源）がすべて失われたとみなす。

## 7. 発見

### 7.1 confirm

```text
要求: "OEP?"、min_rev(u8)、max_rev(u8)
応答: "OEP!"、revision(u8)、flags(u8)、max_frame(u16)、window(u32)、max_inflight(u8)
```

host は扱えるプロトコルの revision の範囲を送り、probe はその中で扱える最大の revision を返す。範囲に扱えるものが無ければ
rejected unsupported。flags は予約（0）。

### 7.2 list

```text
要求: flags(u8: bit0 exact)、first(u16)、prefix_len(u8)、prefix
応答: total(u16)、count(u8)、count × entry
entry: fn(u16)、instance(u16)、revision(u8)、flags(u8)、name_len(u8)、name
```

- prefix に前方一致（exact なら完全一致）する名前を、first 番目から 1 フレームに入る分だけ返す。`oep.core`（fn 0）も最初の
  entry として数える。
- 同じ instance の fn は同じ実体（plan を共有する、§8）。flags は予約（0）。
- fn は probe の起動の間は変わらない。host は boot_id が同じ間、名前から fn への対応を覚えてよい。

### 7.3 describe

```text
要求: fn(u16)、first(u16)
応答: more(u8)、TLV の並び
```

fn の宣言を、first 番目の TLV から 1 フレームに入る分だけ返す。more = 1 なら続きがあり、host は first に受け取った TLV の数を
足してもう一度聞く。probe は TLV を 1 つずつ、自分の max_frame に収まる大きさにする。fn 0 は probe 全体の宣言。

### 7.4 describe の共通タグ（0x01〜0x3F）

| tag | 名前 | 値 |
|---:|---|---|
| 0x01 | role_channels | role(u8)、base(u16)、bitmap。bit i が立っていれば channel base+i をその role に使える。同じ role を複数書いてよい（和集合） |
| 0x02 | max_clock_hz | u32 |
| 0x03 | max_length | u16。1 回に扱える最大の長さ |
| 0x05 | min_clock_hz | u32 |
| 0x06 | features | u32。任意機能のビット（意味はインターフェースが決める） |
| 0x07 | implementation | u8。0 未指定、1 ソフトウェア、2 専用ペリフェラル、3 ペリフェラル + DMA / PIO（表示と診断のため） |
| 0x08 | channel_group | group(u8)、(role(u8)、channel(u16)) × n。この group を使うなら、各 role はここの channel に固定される。group が 1 つ以上ある機能では、plan はどれか 1 つの group に完全に一致しなければならない |

0x04 は予約。role の番号はインターフェースが定める。

- どのピンにも割り当てられる機能は role_channels に候補を並べ、ピンの組が決まっている機能は channel_group を組の数だけ書く。
  両方を書いた場合、plan は channel_group のどれかに一致し、かつ role_channels の候補にも入っていなければならない。
- 同じ宣言は、plan を使わずにピンを引数で選ぶインターフェース（線の attach の pins など）でも、選べるピンの宣言として使う。
- plan の要求の role_assignment（0x90）は plan_apply の文脈の tag（§8）で、describe の tag ではない。

### 7.5 probe 全体の宣言（fn 0 の describe、0x40〜）

| tag | 名前 | 値 |
|---:|---|---|
| 0x40 | firmware | text |
| 0x41 | model | text |
| 0x42 | unit_id | 個体の ID（バイト列） |
| 0x43 | channels | u16。channel の数 |
| 0x44 | reserved | base(u16)、bitmap。probe が自分で使っていてインターフェースに割り当てない channel |
| 0x45 | profile | text。治具などの配線の名前 |
| 0x46 | label | channel(u16)、text。channel の名前（NRST など） |
| 0x47 | resets_on_open | u8。経路を開くと probe がリセットするか |
| 0x48 | uart_rates | u32 の並び |

## 8. plan

- **plan_apply**: role_assignment の TLV（0x90、critical: fn(u16)、role(u8)、channel(u16)）の並び。各インターフェースが自分の
  役割を副作用なしで確かめ、**全部が受け入れたときだけ適用する**（1 つでも断れば何も変えずに rejected）。plan は 1 つずつ
  （適用中の plan があれば rejected unavailable）。
- **plan_release**: plan を解き、ピンを解放する（入力。解放したピンの状態をインターフェースが別に定めていればそれに従う。例: `oep.fixture.uart` の TX は休止の high）。
- 同じ instance の fn は plan を共有する。
- plan の寿命は §9。

## 9. 資源の寿命（一般の規則）

**セッションが作った資源は、明示の end では残して次のセッションに渡し、lease の期限切れと force で奪われたときに外す。**

| 出来事 | セッションが作った資源 |
|---|---|
| end | 残る（次のセッションがそのまま使える） |
| lease の期限切れ | 外す |
| force で奪われる | 外す（期限切れと同じ） |
| probe の再起動 | 無くなる（boot_id が変わる） |

- 本体の資源: **plan**（外すとピンは plan_release と同じく解放。target の線を plan で保っていた場合、target の状態が変わりうる）、通知の購読
  （§11。購読は end でも終わる）、§5.2 の表。
- インターフェースが作る資源（debug の connection、ストリームなど）の寿命は、インターフェースの文書が、この規則の上で定める
  （誰が使っているか、いつ閉じるか）。
- 保存した設定（インターフェースが定める）から入れた資源は、セッションの資源ではない。
- インターフェースが資源に番号を振るときは、新しい資源を作るたびに 1〜255 を順に進める（255 の次は、使っている番号を
  飛ばして 1）。閉じた資源の番号を使った要求は rejected no_connection。番号は同じ boot_id の間だけ有効。

## 10. 長い操作

- 時間のかかる op は accepted（activity の番号、u16）で応答してよい。
- host は `status(activity)` を送る。応答は completed（最終の結果。payload はその op の結果）か、accepted と進捗
  `done(u32) total(u32)`（total が分からなければ 0）。
- `cancel(activity)` で止める。止められなければ rejected unavailable。
- 実行中の長い操作は probe 全体で 1 つ。ぶつかる要求には rejected busy をすぐ返す。
- 最後の結果は同じ session_id の間だけ取り出せ、新しい session_id でロックが立ったら消える。

## 11. 通知

probe から送る通知の仕組み。probe の対応は任意で、host は購読しなければ何も受け取らない。

### 11.1 host の義務（全 host）

- 受け取ったフレームを role で振り分ける。corr で照合するのは role 0x02 だけ（0x05 / 0x06 のバイト 1〜2 は fn）。
- 知らない role のフレームは捨てる。
- 通知が届き続けても、応答を待つ処理と受信を読む処理が締め切りどおりに終わるようにする。

### 11.2 形

```text
データ   role=0x06 | fn(u16) | seq(u16) | payload            見出し 5 byte。payload はインターフェースが決める
出来事   role=0x05 | fn(u16) | seq(u16) | kind(u8) | payload  見出し 6 byte
```

- `seq` は fn ごとのフレームの通し番号（u16、一周する。データと出来事で共通）。subscribe のたびに 0 から数える。抜けがあれば
  フレームが失われた。probe は、生まれた出来事すべてに番号を振り、probe の中で捨てたものも番号を消費する。
- fn 0 の出来事は probe 全体のもの。kind 0x01 = ハートビート（payload: boot_id u32、起動からの ms u32）。

### 11.3 購読

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x30 | subscribe | fn(u16)、min_bytes(u16)、max_delay_ms(u16)、[TLV] | — |
| 0x32 | unsubscribe | fn(u16) | — |

- **購読はロックの持ち主だけができ、ロックと一緒に終わる**（end、期限切れ、force で奪われたとき）。
- 送り出さないインターフェースは subscribe を rejected unavailable にする。
- 同じ fn をもう一度 subscribe したら、前の購読を原子的に置き換える（送る条件、送り先の経路、seq を 0 から）。1 つの fn の購読は
  1 つだけ。
- **まとめて送る条件**: min_bytes バイトたまるか、最初のバイトから max_delay_ms 経ったら送る。0 はその条件を使わない。両方 0 なら
  あるだけすぐ送る。
- fn 0 を購読するとハートビートが来る。周期は max_delay_ms（0 なら 1000 ms）。
- 流れの量の予算（クレジット）は持たない。host や線が遅れた分は probe の中で押し出され、インターフェースの payload
  （ストリームの位置など）か seq の抜けで分かる。

### 11.4 probe の義務（送り出す probe）

1. **応答を先に送る。** 届いている要求をすべて処理してから、通知を送る。
2. **送りかけの通知を小さく保つ。** 経路の送信バッファに、自分の線の速さから決めた量（目安: 線の速さ × 1〜数 ms）を超えて
   たまらないようにし、書き込みで待たない。
3. 通知は、その fn の subscribe が来た経路に送る。

## 12. core（fn 0）の操作一覧

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | confirm | §7.1 | §7.1 | 不要 |
| 0x02 | list | §7.2 | §7.2 | 不要 |
| 0x03 | describe | §7.3 | §7.3 | 不要 |
| 0x04 | plan_apply | role_assignment の TLV の並び | — | 必要 |
| 0x05 | plan_release | — | — | 必要 |
| 0x10 | open | session_id(u32)、lease_ms(u32)、force(u8) | lease_ms(u32)、boot_id(u32)、resumed(u8) | open がロックを取る（role 0x01） |
| 0x11 | end | — | — | 必要 |
| 0x12 | keepalive | — | — | 必要 |
| 0x13 | lock_state | — | locked(u8)、remaining_ms(u32) | 不要 |
| 0x20 | status | activity(u16) | §10 | 不要 |
| 0x21 | cancel | activity(u16) | — | 必要 |
| 0x30 | subscribe | §11.3 | — | 必要 |
| 0x32 | unsubscribe | §11.3 | — | 必要 |
| 0x40 | link_source | length(u32) | length バイト（1 フレームに入る分まで。k バイト目は k & 0xFF） | 不要 |
| 0x41 | link_sink | 任意のバイト（数を持たない並び） | 受け取った長さ(u32) | 不要 |

link_source / link_sink は線の速さを測るためのもので、状態を変えない。

## 13. 拡張の規則（インターフェースの書き方）

標準インターフェースも独自のインターフェースも、次の規則で定義する。

1. **名前**: `oep.` は project が予約する。独自のインターフェースは逆 DNS（`io.github.<owner>.<name>` など）。名前は host が何に
   使うかで切る（probe のペリフェラルの名前にしない）。
2. **定義が決めるもの**: revision、op の表（番号、要求、応答、ロックの要否）、各 op の TLV の tag（その op の文脈の空間）、
   describe のインターフェース固有のタグ（0x40〜0x7F）、plan の role の番号、reject reason（0x40〜0x7F）、出来事の kind
   （0x01〜0x7F）、通知のデータの payload の形、インターフェースが作る資源とその寿命（§9 の上で）。
3. **形の規則**: §2.3 のとおり（固定部分 + TLV、可変の並びの前に数、省略できるフィールドを置かない、安全の引数は critical）。
4. **失敗**: 受け付けなかったものは rejected、受け付けて失敗したものは completed failed / partial（§4.2）。
5. **ロックなしの op は状態を変えない**（§6.3）。
6. **版**: §2.7。
7. **独自のタグを標準インターフェースに混ぜない。** 独自の情報は独自のインターフェースに置く（同じ instance に別の fn として出す）。
8. **target の知識は host が持つ。** チップごとの手順（flash の書き方など）を probe のインターフェースに入れない。
9. 標準インターフェースの番号は registry に載せる。独自のインターフェースの番号は、その定義が管理する。

## 14. 標準インターフェースの文書

| 文書 | インターフェース |
|---|---|
| [標準インターフェース: 共通部品](oep-if-common.ja.md) | 位置つきのストリーム、debug の connection |
| [標準インターフェース: 線とデバッグ](oep-if-debug.ja.md) | `oep.wire.rvswd`、`oep.wire.swio`、`oep.wire.swd`、`oep.target.riscv-dm`、`oep.target.arm-adi` |
| [標準インターフェース: コンソール](oep-if-console.ja.md) | `oep.target.console`（framing の dmseq は [target-console-dmseq](target-console-dmseq.ja.md)） |
| [標準インターフェース: fixture](oep-if-fixture.ja.md) | `oep.fixture.gpio`、`oep.fixture.uart` |
| [標準インターフェース: キャプチャ](oep-if-capture.ja.md) | `oep.fixture.capture`、`oep.fixture.analog` |
| [標準インターフェース: probe の設定](oep-if-probe-config.ja.md) | `oep.probe.config` |

## 15. 規範ではない文書（理由と経緯）

- [core wire model v1（v0 からの差分）](v1-core-wire-delta.ja.md): この文書にまとめる前の差分と、実験の記録。
- [セッションと排他](session-and-exclusivity.ja.md)、[能力の識別方式の比較](capability-identification-comparison.ja.md)、
  [能力の宣言モデル](capability-declaration-model.ja.md)、[能力の名前の階層](capability-name-hierarchy.ja.md): 決めた理由。
- [シリアルの口と永続化](probe-cdc-and-persistence.ja.md): 複数の経路、設定、起動モードの試作と実測。
- [v1 の未合意の案](v1-open-proposals.ja.md): 決める前の案と、決めた経緯。
- [レビューへの回答](review-answer-2026-09-26.ja.md): 第三者のレビュー。
- [host 開発ガイド](host-development-guide.ja.md)、[probe 開発ガイド](probe-development-guide.ja.md): 実装の実務。
