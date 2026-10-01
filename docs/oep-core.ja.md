# Open Embedded Probe — プロトコル本体（OEP core）v1

状態: **規範**（v1 を固める候補、2026-09-26。2026-10-01 に[ゼロベースの再検討](v1-zero-base-proposal.ja.md)を反映）。この文書は OEP のプロトコル本体だけを定める。標準インターフェース
（線、デバッグ、コンソール、fixture、キャプチャ、probe の設定）はそれぞれの文書が定める（§14）。決めた理由と実験の記録は
規範ではない文書に置く（§15）。この文書と、規範ではない文書が食い違えば、この文書が正しい。

番号（op、tag、reject reason、status、enum）の唯一の定義は `registry/oep-v1.toml` で、この文書の表はその写しである。
食い違えば registry が正しく、文書を直す。

## 0. 範囲と層

OEP は 3 つの層からなる。

| 層 | 中身 | 名前 | 版 |
|---|---|---|---|
| **本体（この文書）** | どの probe と host も、機能に関係なく実装するもの: 経路とフレーム、メッセージ、セッションと排他、発見（confirm / list / describe）、plan、資源の寿命の一般の規則、通知の仕組み、拡張の規則 | `oep.core`（fn 0） | プロトコルの revision（confirm） |
| **標準インターフェース** | 本体の仕組みだけで定義した、名前つきの機能。project が名前と番号を管理する、よく使う機能の定義で、一般の標準という意味ではない（特定のチップや系統に特化したものも含む） | `oep.` で始まる名前 | インターフェースごとの revision |
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

OEP の外: probe 自身の firmware の更新（DFU、Mass Storage など）、USB の記述子の細部。

## 1. 用語

| 用語 | 意味 |
|---|---|
| probe | OEP を話す装置（デバッガ、治具、ロジアナなど） |
| host | probe を使うソフトウェア |
| target | probe がつながる相手（開発中のマイコンなど） |
| 経路（transport） | OEP のフレームを運ぶもの（UART bridge、USB CDC、USB-Serial/JTAG、USB の vendor bulk、HID、TCP） |
| シリアルの口（serial port） | 経路のうち OS からシリアルデバイスに見えるもの（UART bridge、USB CDC、USB-Serial/JTAG）。OEP と生のバイトを共用する（§3.4） |
| インターフェース | probe が名前で出す機能。list で見つけ、fn で呼ぶ |
| fn | そのセッションの間、インターフェースを指す番号（u16）。fn 0 は `oep.core` |
| op | インターフェースの中の操作の番号（u8） |
| セッション | ロックを持って状態を変える権利。host が選ぶ session_id（u32）で識別する |
| lease | ロックの期限。keepalive などの要求で延びる |
| channel | probe のピンの番号（u16） |
| plan | どのインターフェースのどの役（role）に、どの channel を使うかの割り当て |

## 2. 共通の規則

### 2.1 byte order と文字列

数値はすべて little endian。文字列は UTF-8 のバイト列で、長さは別に持つ（終端の 0 は付けない）。

### 2.2 TLV

```text
tag(u8) | len(u8)        | value(len byte)          len が 0〜254（短い形）
tag(u8) | 0xFF | len(u16) | value(len byte)          len が 255 以上（長い形）
```

- **符号化は一意**: 値が 254 byte 以下なら短い形、255 byte 以上なら長い形。別の形（254 以下を長い形で、など）は malformed。
  読む側は `len` の 1 byte 目が 0xFF かどうかで分ける。並びの要素の `len(u8)`（§2.3）にはこの逃げ道は無い（要素は 255 byte 以内）。
- **tag の bit 7 は critical**（要求の中でだけ意味を持つ）。tag 0x00 は予約（TLV には使わない。rejected unsupported の payload の印、§4.3）、
  0x7F は応答の ignored 専用、0xFF は無効。
- tag の空間は **(fn, op) の文脈ごと**（同じ値でも文脈が違えば別物）。
- 同じ tag の繰り返しは並びを表す。

### 2.3 固定部分と末尾

- **容器は自分の長さを知る**: フレーム、TLV、並びの要素、バイト列（data）のどれも、読む側が要求や外の知識なしに終わりが分かる。
  可変の部分（並び、バイト列、文字列）には前に数か長さを置く。長さを持たない可変の部分で終わる形は、fn 0 の link_source / link_sink
  （線の試験）だけに限る。
- **応答**: 各 op の応答の固定部分（と、前に数か長さを置いた並び）の後ろは TLV の並び。後から足すものはすべてここに TLV で足す。
  host は知らない tag を読み飛ばす。固定部分より短い応答は壊れた応答として扱う。**応答の固定部分の形は (op, resolution, outcome) ごとに
  op の定義が決める**（成功と失敗で形が違ってよい。インターフェースの共通部品 §3）。
- **出来事とデータ**（§11.2）も応答と同じ: 固定部分の後ろは TLV の並び。
- **要求**: 要求の後ろに足せるのは TLV の並びだけ。host は、その項目が効かなければ要求に意味がないときに **critical の bit を
  付ける**（効かなくても構わない項目は付けずに送ってよい）。インターフェースの定義が critical で送ると決めた TLV（速さの上限、
  pins など、安全のための項目）は必ず付ける。probe は、知らない critical の
  TLV があれば rejected unsupported（payload に受け取ったままの tag）で断る。知らない非 critical の TLV は無視し、応答の
  後ろに ignored（tag 0x7F、値は無視した tag の並び）を付ける。
- 知っている TLV でも、その値を扱えなければ、critical なら rejected unsupported、そうでなければ無視して ignored に載せる。
- 要求の中に tag 0x7F か 0xFF があれば rejected malformed。固定部分より短い要求は rejected malformed。
- **可変の並びは前に数を置く**（後ろに TLV を付けられるように）。
- 固定部分に省略できるフィールドを置かない（省略したい値は TLV にする）。
- host が安全のために足す引数（速さの上限など）は critical にする。

**固定の形の伸ばし方**（凍結後はこれだけで伸ばす）:
- **TLV の値と並びの要素**が固定の形を持つとき、**読む側は、知っている長さより後ろを読み飛ばす**（知っている長さより短ければ壊れた値）。
  **書く側は後ろにだけ足す**。前のフィールドの位置と意味は変えない。形の中に可変の部分（長さつき）があれば、「知っている最後の
  フィールドの終わり」より後ろを飛ばす。
- 固定の形の中の可変の部分（名前、錠の値など）は、**前に長さを置く**。長さを持たない可変の部分は形の最後にしか置けず、その後ろ
  には何も足せないので、使わない。
- **応答の並びの要素は、前に要素の長さ（u8）を置く**: `count(u8)、count × (len(u8)、要素)`。読む側は各要素の知らない後ろを
  飛ばす。要求の並び（host が送る）は長さを置かない（足すものは TLV にする）。ただし、probe が覚えて読み返しに返す値（probe.config の
  項目、bind のストリームの並び）は応答の並びと同じ形にする。
- 値の後ろに足したフィールドは任意の項目として扱う。§2.7 の revision は変えない。
- **describe の TLV の値**（bitmap、文字列、組の並び）は、この規則の例外として閉じたままにする。describe に足す情報は新しい tag で足す。
- **値の幅**: ハードウェアの性質で決まる値（数、速さ、しきい値、容量、時間）は u32 以上にする。u8 / u16 は、プロトコルの都合で上限が
  決まるもの（1 フレームの中の数、fn、資源の番号、インターフェースの中の番号）だけに使う。ビットの集合は u32 か `base + bitmap`。

### 2.4 知らない値

- 知らない role のフレームは捨てる。
- 知らない resolution、completed の知らない outcome は失敗として扱う。
- インターフェースの status や reason の知らない値は失敗として扱う。
- 知らない出来事の kind は捨てる（seq は数える）。

### 2.5 番号の空間

| 空間 | 範囲 |
|---|---|
| role | 0x01 要求、0x02 応答、0x05 出来事、0x06 データ。0x03 / 0x04 は予約、0x07〜0x7F は予約。bit 7 は要求だけの意味（session_id あり、§4.1）。probe → host のフレームでは bit 7 は 0 |
| core（fn 0）の op | 0x01〜0x0F 発見と plan、0x10〜0x1F セッション、0x20〜0x2F 予約（長い操作、§10）、0x30〜0x3F 通知、0x40〜0x4F 線の試験、0x50〜0xEF 予約、0xF0〜0xFF 実験用（出荷する probe は使わない） |
| インターフェースの op | 0x01〜0xEF はインターフェースの定義が決める。0xF0〜0xFF は実験用 |
| reject reason | 0x01〜0x3F 本体（全インターフェース共通）、0x40〜0x7F インターフェース、0x80〜0xFF 予約 |
| outcome | 0 success、1 failed、2 partial。ほかは予約 |
| 出来事の kind | fn ごとの空間。0x01〜0x7F はインターフェースが決める（fn 0 は本体）、0x80〜0xFF は予約 |
| TLV の tag | (fn, op) の文脈ごと。bit 7 は critical。0x00、0x7F、0xFF は全文脈で予約 |
| describe の tag | 0x01〜0x3E 本体の共通タグ（§7.4）、0x3F 予約（応答のメタ情報）、0x40〜0x7F インターフェース |
| 資源の番号 | u16、probe で 1 つの空間（§9） |

### 2.6 一周する値

seq（u16）、資源の番号（§9）と、インターフェースが定める通し番号や時刻のうち一周すると定めたものは、差を同じ幅の符号付きとして
比べる（serial number arithmetic）。probe は同時に意味を持つ範囲を、その幅の半分より十分小さく保つ。一周させない値は u64 にする
（標準インターフェースのストリームの位置、時刻など）。

### 2.6a 時計

probe の時計は 1 つ: **起動からの ns（u64）**。時刻を返す所（マーク、区画、ハートビート、状態の「最後に試した時刻」）はすべてこの値で、
「まだ無い」は全ビット 1。継続時間（timeout_ms、hold_ms、wait_us、elapsed_us など）はそれぞれの単位のままでよい。

### 2.7 名前と revision

- インターフェースの payload の**固定部分**の形と意味は **(名前, revision) で決まる**（list の revision、u8）。
- **revision を上げるのは、固定部分の意味か長さを変えるときだけ**。host は知らない revision のインターフェースを使わない。
- 固定部分を変えずに、任意の request TLV、response TLV、任意の op、任意の event を足すときは、revision を変えない。知らない
  host はそれらを使わない。任意の op やモードの有無は describe（features など）で宣言する。**§2.3 の「後ろに足す」も revision を
  変えない**（TLV の値、出来事の payload、応答の並びの要素の後ろ）。
- 固定部分を変える revision を入れる probe は、できれば古い revision も別の fn として同時に出す。
- 名前を変えるのは、インターフェースの意味が変わるときだけ。
- 本体の形を変えるときは、プロトコルの revision（confirm）を上げる。この文書の形は revision 1。

## 3. 経路とフレーム

### 3.1 フレーム

経路の種類は 2 つに分かれる。**シリアルの口（serial port）** は OS からシリアルデバイスに見える経路（UART bridge = probe の
UART を USB-UART の変換チップで出したもの、USB CDC、USB-Serial/JTAG）で、OEP とシリアルの生のバイトを同じ口で運ぶ（§3.4）。
ほかの経路（USB の vendor bulk、HID、TCP）は OEP だけを運ぶ。

| 経路 | フレーム |
|---|---|
| シリアルの口（UART bridge、USB CDC、USB-Serial/JTAG） | COBS + CRC-16、0x00 で区切る（下） |
| USB の vendor bulk、TCP | `length(u16) message`。CRC なし。length 0 は予約（keepalive。読み飛ばす）。vendor bulk では 1 回の転送に複数のフレームが入ってよく、フレームが転送をまたいでもよい |
| USB の HID（vendor 定義の report） | 長さつきのフレームのバイト列を report に詰める。report = `count(u16)`、count バイト、0 埋め（report の大きさは HID の記述子のとおり）。記述子が report ID を宣言していれば、input も output も report の先頭に ID が付き、count はその後ろから数える |

- **COBS のフレーム**: message の後ろに CRC-16/CCITT-FALSE（多項式 0x1021、初期値 0xFFFF、反転なし、"123456789" → 0x29B1）を
  little endian で付け、COBS（254 byte のブロックに分ける標準の形）で符号にし、**前後を 0x00 で囲んで送る**（`0x00 <COBS> 0x00`）。
  probe も host も前の 0x00 を省かない。最後のブロックが 254 byte の data を持つ（code 0xFF）とき、符号にする側は後ろに空のブロックを付けず、解く側は
  付いた形も付かない形も受ける。空のフレーム（0x00 の連続）は読み飛ばす。
- **host の受け方（COBS）**: 口を開いた直後から最初の 0x00 までと、0x00 から次の 0x00 までを、どちらもフレームの候補として解く
  （開く前に送られたバイトや、開いた直後に落ちたバイトで前の 0x00 が届かないことがある）。解けない候補、CRC の合わない候補、
  role か corr の合わないフレーム（§11.1）は、シリアルの生のバイト（雑音）として捨てる。応答が来ないことは時間切れだけで判断する。
- **USB の束ね方**（vendor bulk）: host は、書き込みの長さが wMaxPacketSize の倍数なら長さ 0 の転送を続ける。probe は、送り
  終えて後ろに続かないとき、最後の転送が wMaxPacketSize の倍数なら、長さ 0 の転送を送るか最後の 1 byte を別の転送に分ける。
  続きがすぐ来るときは倍数のままでよい。
- どのフレームを使うかは経路の種類だけで決まる（VID:PID で選ばない）。
- **TCP は、信頼できるローカルの接続か、認証したトンネルの内側でだけ使う。** OEP は認証を持たない（§6.4 の force を含む）。
  1 つの probe を複数の host で使うときは、host の側のブローカーが 1 つのセッションに束ねる（ブローカーは host の実装で、この
  仕様の外。probe から見える経路とセッションは変わらない）。

### 3.2 フレームの送り方

- host は **1 つのフレームを 1 回の書き込みで送り**、フレームの途中で 100 ms 以上止めない。
- probe は、フレームの途中で 200 ms 入力が途切れたら読み取りを最初からやり直す。

### 3.3 複数の経路

- probe は OEP の制御を複数の経路で受けてよい。**複数の経路はセッションとロックを 1 つ共有する**。どの経路から来た要求も同じ
  ものとして扱い、応答はその要求の来た経路に返す。通知は subscribe が来た経路に送る（§11.4）。
- **1 つのセッションの role 0x81 の要求は 1 つの経路で送る**（§5.2 の順序の判定が経路の遅れで誤らないため）。読むだけの 0x01 は
  別の経路から送ってよい。host が 2 つの経路から 0x81 を送ったときの誤判定は host の責任で、probe は確かめない。
- host は、同じ probe に複数の経路があれば vendor bulk、HID、シリアルの口の順に試す（シリアルの口は生のバイトの転送にも
  使われる、§3.4）。probe の経路の一覧は fn 0 の describe の transport（§7.5）で分かる。
- **USB の OEP の probe と口の見分け方**: **device の文字列 iProduct が `OEP` で始まる device は OEP の probe**（VID:PID は見分けに
  使わない。参照の firmware の VID:PID は実務の文書 [USB の識別](usb-identity.ja.md)）。host はこれで probe を見分け、その device の口を
  interface の記述子で選ぶ: CDC（ACM）はすべてシリアルの口（§3.4。どれも OEP を受ける）、**bInterfaceClass 0xFF、bInterfaceSubClass 0x4F
  ('O')、bInterfaceProtocol 0x45 ('E') の interface の bulk IN / OUT の組**は vendor bulk、**usage page 0xFF4F、usage 0x45 の HID** は HID
  （registry の `usb`）。OEP の probe は vendor bulk と HID をそれぞれ高々 1 つしか出さない。ほかの class 0xFF の interface（USB-Serial/JTAG
  の JTAG、WebUSB など）はこの subclass / protocol を持たないので掴まない。ほかの機能（DFU、Mass Storage など）は OEP の外。
  interface の文字列は表示のためのもので、見分けには使わない。
- **USB の serial number は unit_id**（§7.5）: probe が serial を選べる口（CDC、vendor bulk、HID を自分で出す device）では、serial number を
  unit_id そのものにする（§7.5 の不変性）。host は開かずに probe を見分けられ、どの経路の describe とも同じ値になる。serial も iProduct も選べない口
  （USB-Serial/JTAG、USB-UART の変換チップ）は、host が経路を外から指定し、describe で unit_id を確かめる。confirm と describe は口を
  開いた後にしか使えないので、口の選び方はこの規則による。
- **max_frame は両方向の上限**: probe は max_frame を超える message を送らず、host は max_frame を超える message を送らない。
- **confirm の前**: どの probe も 64 byte（registry の `min_max_frame`）までの message を受ける（confirm の max_frame は 64 以上）。
  host は confirm の応答を受けるまで、64 byte を超える message を送らない。host は probe から長さ 65535 byte までの message を
  受けられるようにする。

### 3.4 シリアルの口の共用

シリアルの口は、OEP のフレームと生のバイト（target のコンソールなど）を同じ口で運ぶ。probe はどの口でもいつでも OEP を受ける
（口を OEP 専用にする設定や、起動の型は持たない）。

- **probe の受け方**: 0x00 が来たら次の 0x00 までためて解く。解けて CRC が合えば OEP の要求。解けない、CRC が合わない、または
  次の 0x00 の前に 200 ms 途切れた（§3.2）ときは、ためた分（前の 0x00 を含む）を生のバイトとして扱う。候補を閉じた 0x00 は
  次の候補の始まりになる。**0x00 だけで中身の無い候補**（フレームの閉じの 0x00 の後に何も来ないとき、0x00 の連続）は区切りで
  あり、200 ms 途切れても生のバイトにしない。0x00 の外で来たバイトはすぐ生のバイトとして扱う。
- **生のバイトの行き先**: probe がその口に結んだ流れ（どの流れを結ぶかは probe の設定が決める。結んでいなければ捨てる）。
- **probe の送り方**: 応答と通知は `0x00 <COBS> 0x00`。1 つの口の送信は 1 つの書き手が行い、フレームの途中に生のバイトを挟ま
  ない（フレームは生のバイトより先に出してよく、生のバイトどうしの順は保つ）。
- **生の転送を止める口**: ロックを持つセッションの要求（ロックを取った open と、その session_id の role 0x81 の要求）が 1 つでも
  来た口では、そのセッションが終わる（end、lease の期限切れ、force で奪われる）まで、probe は生のバイトを送らず、口から来た
  生のバイトを捨てる。ロックの要らない要求だけが来た口と、ほかの経路でセッションが動いている口は止めない。セッションが終わった
  後、どこから生の転送を再開するかは、口に結んだ流れを定める設定が決める。
- host は、生のバイトの中に正しいフレームに見えるものが偶然現れても、role と corr の照合（§11.1）で捨てる。
- **host の受けの量**: OS のシリアルドライバは、probe の送るフレームがドライバの受けの量を超えてまとまって届くと黙って失うことがある
  （[リンクの計測](link-measurements.ja.md) §1.1）。host はシリアルの口では、未解決の要求の応答の見込み量（同時数 × フレームの上限）を
  6 KiB 以下に保つ。通知も同じ: シリアルの口で購読するとき、host は subscribe の min_bytes を小さく（2 KiB 以下）保ち、probe が一度に
  送る量を自分の受けに合わせる（§11.3）。大量の転送は長さ付きフレームの口（vendor bulk）を優先する。probe の max_inflight と window は
  probe の受けの上限であって、host の受けの上限ではない。

### 3.5 シリアルの口の速さ（任意の機能）

UART bridge の口で、セッションの間だけリンクの速さを起動時の速さより上げる任意の機能。用途は大きな書き込み、キャプチャ、コンソール
（線の block op の時間はデバッグの線の往復で決まり、リンクでは変わらない）。probe の fixture UART の速さは別（そのインターフェースの
configure と設定）。

**語の定義**

- **起動時の速さ**: ボードの profile が決める口の速さ。probe のすべての戻り先。host は利用者が口を選ぶときに一緒に決めて 1 か所に持つ。
- **候補**: host が試す速さの並び。probe は候補を宣言しない（通る速さは変換チップと OS で決まり、probe には分からない）。この仕様は
  候補も既定も決めない。
- **数えるフレーム**（host の受けの側で）: **正常** = 解けて CRC の合った応答または通知。**壊れ** = 0x00 で閉じた候補のうち解けないか
  CRC の合わないもの。**失われ** = 待ち時間に応答の来なかった要求。**割合** = (壊れ + 失われ) / (正常 + 壊れ + 失われ)。速さを切り替えた
  直後、新しい速さで最初の正常なフレームが来るまでの壊れは数えない。
- **基準**: そのセッションでそれまでに起動時の速さで数えたフレームの割合。数えたフレームが 20 未満なら 0。
- **閾値** = max(基準 × 2, 床)。床は【決める: 割合。案は 1 %。どの速さでも一定の割合で落とす変換で起動時の速さと同じ壊れ方の候補が通る値を、手順どおりの計測で決める】。
- **確かめの流し方**: link_source（probe → host）と link_sink（host → probe）（§12）を、payload を max_frame − 16 byte にして使う。

**probe**

- ON の probe だけが fn 0 の describe に port_speed（§7.5）を宣言し、op port_speed（fn 0、0x14、ロックが要る）を受ける。OFF は
  unknown_operation。対象は transport kind 1（UART bridge）の口だけ。

```text
port_speed  要求: port(u8)、baud(u32)、step(u8: 0 試す、1 決める、2 戻す)、verify_ms(u16)、idle_ms(u32)、[TLV]
            応答: baud(u32: 実際に掛かる速さ)、[TLV]
```

- 断り: port がこの要求の来た口でない → rejected unavailable（cause 6）。baud を probe の UART で作れない → rejected unsupported。
  ロックが無い・違うときの断りは §4.3 の順（session_required、no_session、expired、locked）。
- 状態は口ごとに **起動時 / 試し / 決めた** の 3 つ。
  - **試す**（step 0、起動時の状態で受ける）: 応答を今の速さで送り終えてから、応答の baud に切り替えて**試し**になる。verify_ms を
    この要求の値で始める。
  - **決める**（step 1、試しの状態で、同じ baud、新しい速さで受ける）: **決めた**になる。idle_ms をこの要求の値で始める（最長
    port_speed_idle_max_ms = 3000 ms。0 とそれより長い値は最長として扱う）。
  - **戻す**（step 2、試し・決めたのどちらでも）: 応答（baud は起動時の速さ）を今の速さで送ってから起動時の速さに戻る。
  - 状態に合わない step（起動時の状態で決める、など）は rejected unavailable（cause 6）。
- **probe が自分で起動時の速さに戻る条件**（戻ったことは知らせない）:
  1. 試しのまま verify_ms が過ぎた。
  2. 試しの状態で、新しい速さで正常なフレームを 1 つ受けた後、その口に壊れが 1 つ来た。
  3. 決めた後、その口に正常なフレームが idle_ms 来ない。
  4. 決めた後、正常なフレームを挟まず壊れが 3 つ続いた。
  5. セッションが終わった（end、lease の期限切れ、force で持ち主が替わった）。end と force は応答を送ってから戻る。
- 試しと決めるの間、セッションの資源とロックは変わらない。生の転送（§3.4）はセッションの間止まっている。

**host の手順**

1. 起動時の速さで confirm と describe を済ませ、port_speed が宣言され、ロックを持っていること。要求はその口から送る。
2. 候補を並びの順に試す。候補ごとに:
   1. 起動時の速さで port_speed（試す、baud、verify_ms、idle_ms）を送る。verify_ms は 3 以降の確かめにかかる時間の 2 倍以上（目安
      2000 ms）、idle_ms は使っている間に keepalive を送る間隔の 2 倍以上（最長 3000 ms）。rejected unsupported なら次の候補。応答の
      baud（実際に掛かる速さ）を host が作れなければ、verify_ms の間待ってから 6 へ。
   2. 応答の baud に切り替え、20 ms 待ち、confirm を 100 ms の待ちで 3 回まで送る。1 つも返らなければ verify_ms が過ぎるまで
      待ってから 6 へ。
   3. **確かめる**。使う予定の同時数 n（probe の max_inflight と host の受けの上限 §3.4 の小さい方）で、(a) link_source を 16 フレーム
      以上、(b) link_sink を 16 フレーム以上、(c) 両方を交互に 16 フレーム以上、流す。壊れと失われを数える。失われがあれば confirm で
      合わせ直してから続ける。(a)〜(c) の時間は候補 1 つあたり 1 秒以内にとどめる（通らない候補はこれに verify_ms の待ちが足されるので、host は候補の数を少なく保ち、前のセッションの記録（手順 8）で通らなかった速さは候補から外す）。
   4. (a)〜(c) を合わせた割合が閾値以下なら通る。閾値を超え、かつ n > 1 なら、同じ (a)〜(c) を n = 1 で流し直し、閾値以下なら n = 1 を
      上限として通る。それでも超えれば通らない。
   5. 通れば新しい速さで port_speed（決める、同じ baud）を送る。応答が来れば、その速さと n の上限で使う。応答が来なければ 6 へ
      （probe は戻っている）。
   6. 通らなければ、新しい速さで port_speed（戻す）を送る（応答が来なくてよい）。起動時の速さに戻し、confirm が通るまで
      port_speed_idle_max_ms + 1000 ms を上限に繰り返す。通らなければリンクの失敗。この候補はこのセッションでは使わない。次の候補へ。
3. **使っている間**: 直近 100 フレームの割合を見る。閾値を超えたら port_speed（戻す）を送って起動時の速さに戻り、**このセッションでは
   二度と上げない**。
4. 上げた速さで応答が待ち時間に来なかったら、起動時の速さに戻して confirm する（2-6 と同じ繰り返し）。通れば probe が先に戻っている。
   boot_id が変わっていれば probe は再起動している。どちらも、このセッションでは起動時の速さで続ける。待ちは lease より十分短くする。
5. 上げている間、keepalive か他の要求を idle_ms の半分より短い間隔で送る。
6. セッションの end の応答を受けたら起動時の速さに戻す。
7. **口を開く host** は、起動時の速さで confirm が通らなければ、port_speed_idle_max_ms + 1000 ms の間 confirm を繰り返す（前の host が
   上げた残りが戻るのを待つ）。
8. host は基準、候補ごとの（速さ、実際の速さ、フレーム数、壊れ、失われ、割合、通ったか、n の上限）、使っている間に戻した事実を記録に
   残す（形は host の自由。転送量の予算と限界の測定に使う）。
9. 口をブローカーが持つ構成では、以上をブローカーが行う（client は知らない）。

測った値と壊れ方の記録は [UART の速さ](uart-speed-negotiation.ja.md)、[リンクの計測](link-measurements.ja.md)。

## 4. メッセージ

### 4.1 要求

```text
role=0x01 | corr(u16) | fn(u16) | op(u8) | payload                      見出し 6 byte（session_id なし）
role=0x81 | corr(u16) | fn(u16) | op(u8) | session_id(u32) | payload    見出し 10 byte（session_id あり）
```

- `corr`: host が振る番号。**host は要求ごとに 1 ずつ進める**（role 0x01 の要求も数える。65535 の次は 1。0 は使わない）。
  同じ番号をもう一度使うのは、§5.2 の送り直しのときだけ。probe は、送り直しと、覚えていない古い要求の見分けにこの順序を使う。
- 状態を変える要求は role 0x81 で送る（§6.3）。ロックなしで使える要求は 0x01 で送ってよい（0x81 で送れば lease が延びる）。

### 4.2 応答

```text
role=0x02 | corr(u16) | resolution(u8) | detail(u8) | payload           見出し 5 byte
```

| resolution | 値 | detail | payload |
|---|---:|---|---|
| rejected | 0x00 | reject reason（§4.3） | reason が定める補助の情報 |
| completed | 0x01 | outcome（0 success、1 failed、2 partial） | op が定める |
| — | 0x02 | — | 予約（長い操作、§10）。host は失敗として扱う |

- 要求ごとに応答はちょうど 1 つ。応答はその要求の来た経路に、同じ corr で返す。fn と op は返さない。
- **rejected は「要求を受け付けなかった」ときだけ**（書式、番号、セッション、今の状態で受けられない）。受け付けて実行した
  結果うまくいかなかったものは completed の failed か partial にし、payload でどこまで進んだかと理由を返す。

### 4.3 reject reason（本体）

| 値 | 名前 | 意味 | payload |
|---:|---|---|---|
| 0x01 | unknown_function | その fn は無い | — |
| 0x02 | unknown_operation | その fn にその op は無い | — |
| 0x03 | malformed | 長さ・値域の誤り | — |
| 0x04 | unavailable | 今の状態・資源では受けられない | TLV の並び（任意、下） |
| 0x05 | busy | 予約（長い操作、§10） | — |
| 0x06 | window_exceeded | window / max_inflight を超えた | — |
| 0x07 | no_session | ロックは空いているが、この session_id は最後の ID ではない。host は open からやり直す | — |
| 0x08 | locked | 他のセッションがロックを持つ | 残り時間 ms（u32）、[TLV owner（§6.4）] |
| 0x09 | session_required | 状態を変える要求に session_id が無い | — |
| 0x0A | no_connection | 要求の資源（connection、stream など、番号で指すもの）を probe が知らない。host は作り直す。どのインターフェースでも、知らない番号にはこれを使う | — |
| 0x0B | unsupported | 定義にはあるが、この probe が扱えない（critical の TLV、固定部分の値、任意の op の機能） | `tag(u8)`、[TLV]。tag は critical の TLV なら受け取ったままの値、固定部分の値なら 0x00。どの要素かを示すときは後ろに TLV（unavailable と同じ tag の空間: channel、index） |
| 0x0C | result_lost | 送り直された要求の結果を覚えていない（§5.2） | — |
| 0x0D | corr_reused | 同じ corr で fn、op、中身のどれかが違う要求が来た（§5.2） | — |
| 0x0E | expired | この session_id のロックは lease の期限切れで終わり、資源は外した（§9）。host は open からやり直す（force で奪われた側は、奪った側が持つ間は locked、その後は no_session になる: probe は最後の session_id しか覚えない） | — |

rejected の detail は reason で、そのほかの情報は payload に置く。

**断り方の順**（probe は次の順に見て、最初に当たった理由で断る。同じ状況に 2 つの理由を作らない）:

1. 見出し: unknown_function → unknown_operation → session_required。
2. 送り直し（§5.2 の表）: corr_reused / result_lost / 覚えた応答。
3. セッション（§6.2）: no_session / expired / locked。
4. window_exceeded。
5. **書式と値域の外**（長さ、未定義の値、`address > 0x7F`、`mode > 3`、設定どうしの矛盾）→ malformed。
6. **定義にはあるが、この probe が持たない**（mode、format、rate の範囲外、trigger の type、知らない critical の TLV、ピンの組）→ unsupported。
7. **今の状態・資源で受けられない**（plan、接続、動いている、容量、組に束ねられている）→ unavailable（cause 付き）。
8. 番号で指す資源を知らない → no_connection。

payload の中で指す fn（describe、subscribe、plan、設定の項目）が無いときは unknown_function を流用する。

**unavailable の payload**（任意の TLV の並び。host は知らない tag を飛ばし、無くても扱えるようにする。probe は分かる範囲で付ける）:

| tag | 名前 | 値 |
|---:|---|---|
| 0x01 | cause | u8: 1 ピンが使われている、2 数の上限（plan_roles、スロット、接続など）、3 保存先が足りない、4 組（capture-group）に束ねられている、5 設定が持つ（設定の plan、スロット）、6 状態が違う（configure していない、動いている、など） |
| 0x02 | channel | u16。ぶつかった channel（繰り返してよい） |
| 0x03 | holder_fn | u16。その資源を持っている fn |
| 0x04 | holder_kind | u8: 1 plan、2 線の接続、3 スロット、4 bind、5 設定の plan、6 設定の disable |
| 0x05 | fn | u16。断りの対象の fn（capture-group の bind で、どのトラックかを示す） |

インターフェースは 0x40 以降に自分の tag を足せる。rejected unsupported の payload の後ろの TLV も同じ空間（channel 0x02、fn 0x05、
インターフェースの index など）。

### 4.4 パイプライン

- confirm（§7.1）で probe は `max_frame`（受け取る最大の message 長）、`window`（未解決の要求の message 長の合計の上限）、
  `max_inflight`（未解決の要求の数の上限）を返す。message 長は見出し（role から）を含み、フレームの包み（COBS、CRC、length）は含まない。
- host は両方の上限を守る。超えた要求を probe は rejected window_exceeded で断ってよいが、バッファを超えて失われた要求には
  応答も返らない。守るのは host の責任である。
- probe は要求を受け取った順に処理し、応答を受け取った順に返す。
- **host の待ち時間**: 応答が来ないことは時間切れだけで判断する（§3.1）。待ち時間は、その要求の引数で決まる時間（run の timeout_ms、
  reset の hold_ms、dmi の待ちの和、save など。無ければ 0）に【決める: 固定の加算。案は 1000 ms】を足した値で、describe の max_op_ms
  （§7.5）に同じ加算をした値を超えない。過ぎたら §5.2 の送り直しに進む。

## 5. 立て直しと送り直し

### 5.1 区切りの立て直し（長さつきのフレーム）

長さつきのフレーム（vendor bulk、HID、TCP）で、host は、corr の合わない応答、あり得ない長さ（max_frame を超える）、途中で
止まったフレーム（続きが 200 ms 来ない）を見たら、入力が 50 ms 静かになるまで読み捨て、confirm を送って自分の corr の応答が返ることを
確かめてから再開する。応答の末尾の TLV が途中で切れていたら、その応答は壊れている。通知が流れ続けて入力が静かにならないときは、
unsubscribe と end を確かめずに送ってよい（二度実行しても害がない）。COBS のフレームは CRC で壊れたものを捨てられるので、
この手順は要らない。

### 5.2 送り直しと重複排除

- 応答が壊れたか来なかったとき、host は**同じ corr で 1 回送り直してよい**（状態を変える要求も）。立て直しの中で unsubscribe
  と end を送ったときは、セッションが終わっているので、元の要求は送り直さない。
- probe は、最後のセッションの要求（role 0x81）について、直近の max_inflight 個以上の (corr, fn, op, 要求の payload の CRC-32,
  応答) と、そのセッションで最も新しい corr を覚えておく。**要求の同一性は corr だけで決まる**（§4.1 の順序）。CRC は host の
  番号付けの誤りを見つけるためだけのもの。
- 最後のセッションの session_id を持つ要求は、**§6.2 の判定より先に**次のとおり見る（ロックが空いていても同じ）:
  - 表に同じ corr があり、fn、op、CRC が同じなら、**実行せずに覚えた応答を返す**。ロックの状態も lease も変えない（送り直した
    end でロックが立ち直ることはない）。
  - 表に同じ corr があり、どれかが違えば rejected corr_reused。
  - 表に無く、corr が最も新しい corr より新しくない（差を u16 の符号付きで見て 0 以下）なら、実行せずに rejected result_lost
    （表から落ちた古い要求の送り直し。host は状態を読み直して確かめる）。
  - それ以外は新しい要求として §6.2 へ進む。
- 覚えておく応答の大きさには上限を置いてよい。上限を超えて覚えていない応答の要求を送り直されたら、実行せずに rejected
  result_lost。
- **覚えた表と最も新しい corr は open（resume を含む）のたびに捨てる**（end では捨てない）。セッションが変わったときの
  exactly-once は約束しない。
- 読むだけの要求（role 0x01）は重複排除しない。
- CRC-32 は IEEE（reflected、多項式 0xEDB88320、初期値と最終の XOR 0xFFFFFFFF。"123456789" → 0xCBF43926）。

## 6. セッションと排他

### 6.1 ロック

- probe は**ロックを 1 つ**持つ。ロックを持つセッションだけが状態を変える要求を実行できる。
- session_id は host が選ぶ（乱数でよい）。probe は最後にロックを持った session_id を覚えている。
- lease は open で決まり、ロックを持つセッションの要求（role 0x81）が完了するたびに延びる。期限を過ぎるとロックは空く
  （§9 の期限切れ）。**要求を実行している間は lease を数えない**（長い op が lease より長くてもセッションは切れない。長さの上限は
  describe の max_op_ms、§7.5）。

### 6.2 要求を受けたときの判定

probe は、ロックの有無、最後の session_id、その ID のロックが**どう終わったか**（end で離した / 期限切れか force で外した）を覚えている。
§5.2 の表の判定（送り直し）はこの表より先。

| ロック | 要求の session_id | 結果 |
|---|---|---|
| 空き（end で離した） | 最後の session_id と同じ、open 以外 | ロックを立て直して処理する（再開。lease は前の open の値、資源は残っている、§9） |
| 空き（end で離した） | 最後の session_id と同じ open | ロックを立て直し、resumed = 1 |
| 空き（期限切れで外した） | 最後の session_id と同じ、open 以外 | **rejected expired**（資源は外した。host は open からやり直す） |
| 空き（期限切れで外した） | 最後の session_id と同じ open | ロックを立て、resumed = 2（資源を外した後の再開） |
| 空き | 違う ID、open 以外 | rejected no_session |
| 空き | 違う ID の open（force の有無を問わない） | ロックを立て、最後の session_id と owner を更新、resumed = 0 |
| 自分が持つ | 同じ、open 以外 | 処理する |
| 自分が持つ | 同じ open（force の有無を問わない） | lease を作り直し、resumed = 1。購読は残し、通知の送り先はこの open の経路に替える |
| 他が持つ | 違う、open(force) 以外 | rejected locked と残り時間（と owner） |
| 他が持つ | open(force) | 奪う（§6.4）: 前のセッションの資源を外し（§9）、resumed = 0 |

### 6.3 ロックの要る要求

状態を変える要求はすべてロックが要る（role 0x81）。ロックなしで使えるのは、状態を変えない読むだけの要求に限る
（confirm、list、describe、lock_state、link_source / link_sink、インターフェースが定める読むだけの op）。インターフェース
がロックなしとする op は、状態を変えてはならない。

### 6.4 open、end、keepalive、force

- **open**（session_id、lease_ms、force）: ロックを取る。応答は lease_ms（probe が決めた値）、boot_id、resumed（0 新しいセッション、
  1 同じ session_id で資源を残したまま立て直した、2 同じ session_id だが資源は外した後。registry の `resumed`）。**成功した open のたびに
  §5.2 の表を捨てる**（rejected locked の open では捨てない。end、期限切れ、force では捨てない）。
- **lease_ms**: 0 は「probe の既定」。probe は 1000〜60000 ms の要求をそのまま受け、範囲の外は probe が丸める（既定と丸めの幅は
  probe が決める）。host は応答の lease_ms を正とする。
- **end**: ロックを離す。セッションの資源は残す（§9）。
- **keepalive**: lease を延ばすだけ。
- **lock_state**: ロックの有無と残り時間。locked は「どのセッションであれロックが持たれている」（lock_state はセッションを
  持たずに送れるので、probe には誰が聞いたかは分からない。自分が持っているかは host が自分の状態で知る）。
- **owner**: open の TLV 0x01 owner（text、1〜32 byte、非 critical）で、host は持ち主の名前（例 "ch32rv monitor pid 1234"）を
  付けてよい。probe は最後の session_id と一緒に owner を覚え（別の session_id の open で置き換わり、同じ session_id の再開では
  owner が付いていれば置き換え、無ければ前のまま）、ロックが持たれている間、lock_state の応答と rejected locked の payload の後ろに
  TLV 0x01 owner で付ける（owner が無ければ付けない）。**session_id は返さない**（返すと他の host がその ID で再開でき、force なしで奪える）。owner は表示のためだけのもので、
  probe は解釈しない。
- **force**: 他のセッションがロックを持っていても奪う。probe は、前のセッションに対して期限切れと同じ後始末をしてから（§9）
  ロックを渡す。force は認証ではなく、取り違えを防ぐだけのものである。

### 6.5 boot_id

boot_id は probe の起動ごとに変わる値で、confirm（§7.1）と open の応答に入る（同じ値）。32 bit の乱数でよい（同じ値になる確率は host が
受け入れる）。不揮発の記憶も乱数源も無い probe も、起動の時刻のばらつきなどから必ず値を変える。0 も普通の値。host は、boot_id が変わった
とき、そのセッションの資源（plan、インターフェースの資源）と、覚えた fn の対応、資源の番号、ストリームの位置がすべて無効になったとみなす。
ロックを持たない host（監視、発見）は confirm で再起動を知る。

## 7. 発見

### 7.1 confirm

```text
要求: "OEP?"、min_rev(u8)、max_rev(u8)、[TLV]
応答: "OEP!"、revision(u8)、flags(u8)、max_frame(u16)、window(u32)、max_inflight(u8)、boot_id(u32)、[TLV]
```

host は扱えるプロトコルの revision の範囲を送り、probe はその中で扱える最大の revision を返す。範囲に扱えるものが無ければ
rejected unsupported。flags は予約（0）。boot_id は §6.5（ロックなしで再起動を知るための置き場）。要求も応答も 64 byte に収まる
（§3.3）。

### 7.2 list

```text
要求: flags(u8: bit0 exact)、first(u16)、prefix_len(u8)、prefix
応答: total(u16)、count(u8)、count × (len(u8)、entry)
entry: fn(u16)、instance(u16)、revision(u8)、flags(u8)、name_len(u8)、name
```

- prefix に一致する名前を、first 番目から 1 フレームに入る分だけ返す。**一致は label（`.` で区切った部分）の境界で見る**:
  名前が prefix と同じか、`prefix + "."` で始まれば一致（`oep.fixture.uart` は `oep.fixture.uart` と `oep.fixture.uart.stream` に
  一致し、`oep.fixture.uart2` には一致しない）。prefix は label の並びで、末尾に `.` を付けない（`oep.` は何にも一致しない。
  `oep` と書く）。空の prefix はすべてに一致する。exact なら完全一致だけ（空の prefix は何にも一致しない）。`oep.core`（fn 0）も最初の
  entry として数える。
- 名前は 1〜64 byte、使える文字は `a-z 0-9 - .`（§13）。
- instance は、同じ名前のインターフェースが複数あるときの見分け。**同じ名前のものを fn の昇順に 0 から振る**。probe は同じ名前の口の
  順を firmware の版を越えて保つ（保存した設定が (name, instance, revision) でインターフェースを指すため）。flags は予約（0）。
- 文字で 1 つのインターフェースを指すとき（CLI、設定のファイル、ログ）は `name#instance` と書く（instance はこの値、0 から。
  `#0` は省いてよい）。例: `oep.fixture.uart#1` は 2 つめの `oep.fixture.uart`。
- fn は probe の起動の間は変わらない。host は boot_id が同じ間、名前から fn への対応を覚えてよい。

### 7.3 describe

```text
要求: fn(u16)、first(u16)
応答: more(u8)、TLV の並び
```

fn の宣言を、first 番目の TLV から 1 フレームに入る分だけ返す。more = 1 なら続きがあり、host は first に受け取った TLV の数を
足してもう一度聞く。probe は TLV を 1 つずつ、自分の max_frame に収まる大きさにする。fn 0 は probe 全体の宣言。

**describe は宣言だけを返す**: 同じ boot_id の間、TLV の並びと値は変わらない（host は boot_id が同じ間 cache してよく、ページングは
途中で設定が変わっても崩れない）。変わるもの（接続、保存の有無、スロットの状態、空き容量）は、インターフェースが状態を返す op
（ロック不要）で出す。tag 0x3F は応答のメタ情報のために予約する（宣言の tag には使わない）。応答そのものが TLV の並びなので、
**describe の要求には TLV を置かない**（あれば rejected malformed。probe.config の get も同じ）: 応答に ignored（0x7F）が
現れることはない。
- **ページングの終わり**（describe、state、connections、streams、segments、get に共通）: first が数以上なら count 0 と more 0 を
  返す。host は more = 0 で止める。list は more を持たず、total で終わりが分かる（§7.2）。

### 7.4 describe の共通タグ（0x01〜0x3F）

| tag | 名前 | 値 |
|---:|---|---|
| 0x01 | role_channels | role(u8)、base(u16)、bitmap。bit i が立っていれば channel base+i をその role に使える。同じ role を複数書いてよい（和集合） |
| 0x02 | max_clock_hz | u32 |
| 0x03 | max_length | u16。1 回に扱える最大の長さ。その op の要求と応答が max_frame に収まる値で宣言する（単位はインターフェースの文書が決める）。超えた要求は rejected unsupported |
| 0x05 | min_clock_hz | u32 |
| 0x06 | features | u32。任意機能のビット（意味はインターフェースが決める） |
| 0x07 | implementation | u8。0 未指定、1 ソフトウェア、2 専用ペリフェラル、3 ペリフェラル + DMA / PIO（表示と診断のため） |
| 0x08 | channel_group | group(u8)、n(u8)、n × (role(u8)、channel(u16))。この group を使うなら、各 role はここの channel に固定される。group が 1 つ以上ある機能では、plan はどれか 1 つの group に完全に一致しなければならない |

0x04 は予約。role の番号はインターフェースが定める。これらの値は閉じた形で、足す情報は新しい tag にする（§2.3）。

- どのピンにも割り当てられる機能は role_channels に候補を並べ、ピンの組が決まっている機能は channel_group を組の数だけ書く。
  両方を書いた場合、plan は channel_group のどれかに一致し、かつ role_channels の候補にも入っていなければならない。
  role_channels が縛るのは、それが挙げる role だけである（role_channels に無い role は channel_group だけで決まり、channel_group に
  無い role は role_channels だけで決まる）。
- 同じ宣言は、plan を使わずにピンを引数で選ぶインターフェース（線の attach の pins など）でも、選べるピンの宣言として使う。
- plan の要求の role_assignment（0x90）は plan_apply の文脈の tag（§8）で、describe の tag ではない。

### 7.5 probe 全体の宣言（fn 0 の describe、0x40〜）

| tag | 名前 | 値 |
|---:|---|---|
| 0x40 | firmware | text |
| 0x41 | model | text。probe の種類（同じ firmware を載せた同じ種類のハードウェアで同じ値。個体では変わらない）。**小文字の `a-z 0-9 -`**、1〜32 byte |
| 0x42 | unit_id | 個体の ID。**必須**。text で 1〜32 byte、使える文字は `a-z 0-9 -` だけ（チップの固有の番号を小文字の 16 進にしたもの、など）。同じ probe の経路を host がまとめるのに使うので、どの経路の describe でも同じ値を返す。USB の serial number と同じ（§3.3）。host が probe を名指す値（アドレス `oep://<unit_id>/<スロットの名前>`、[probe の設定](oep-if-probe-config.ja.md) §1.1） |
| 0x43 | channels | u16。channel の数 |
| 0x44 | reserved | base(u16)、bitmap。probe が自分で使っていてインターフェースに割り当てない channel |
| 0x45 | profile | text。治具などの配線の名前 |
| 0x46 | label | channel(u16)、text。**firmware（配線の profile）が持つ固定の** channel の名前（NRST など）。設定で付けた名前は `oep.probe.config` の get で読む（describe は宣言だけ、§7.3） |
| 0x47 | resets_on_open | u8。経路を開くと probe がリセットするか |
| 0x48 | — | 予約 |
| 0x49 | transport | index(u8)、kind(u8)、interface(u8: USB の interface 番号、0xFF は USB でない)。probe の経路ごとに 1 つ。**必須** |
| 0x4A | discoverable | u8。1 = probe が host の discovery の一覧に出る形でも列挙している（今の経路がそうでなくても）: iProduct が `OEP` で始まる USB の device（§3.3） |
| 0x4B | plan_roles | u32。plan が一度に持てる role_assignment の数（すべての fn の合計。設定の plan を含む）。上限のある probe は必ず出す（§8） |
| 0x4C | chip | text。probe の MCU の型番とリビジョン: `<型番> v<リビジョン>`、型番は小文字でハイフンなし（例 `esp32p4 v1.3`、`rp2350 v2`）。取ったデータに、どのチップで取ったかを残すため（任意） |
| 0x4D | max_op_ms | u32。probe が 1 つの要求にかける最長の時間。**必須**。超えうる op（run、dmi の待ちの和、キャプチャの start、save、attach の reset の hold_ms）は、引数の和がこれを超えれば rejected unsupported。実行中は lease を数えない（§6.1）。ほかの経路と connection のコンソールの読みは続ける。値は probe が決める。host はこの値に、要求と応答が線を通る時間を足した値以上を待つ（§4.4） |
| 0x4E | port_speed | u8。1 = この probe は op port_speed（§3.5）を受ける（firmware が機能を ON にしたときだけ出す） |

- transport の kind: 1 UART bridge、2 USB CDC、3 USB-Serial/JTAG、4 vendor bulk、5 HID、6 TCP（registry の `transport_kind`）。
  1〜3 がシリアルの口（§3.4）。index は probe の中で経路を指す番号（0 から）で、probe の設定がシリアルの口を指すときもこの番号を
  使う。probe の起動の間は変わらない。
- host は transport の数で、ロックの奪い方を決めてよい（経路がシリアルの口 1 つだけなら、口を排他で開けた時点で前の持ち主は
  いない。[host 開発ガイド](host-development-guide.ja.md)）。
- **unit_id の一意性**: unit_id は個体ごとに違う値にする（チップの固有の番号、など）。固有の番号も保存も無い probe は firmware のビルド
  定数で持ってよい（同じ firmware の個体を区別できないことを受け入れる）。
- **unit_id の不変性**: unit_id は個体の値（チップの固有の番号、保存した乱数）だけから作り、firmware の版、profile、ビルド、経路の種類で
  変えない。接尾辞を足さない。host と OS は unit_id（= USB の serial number、§3.3）で probe を覚える。

### 7.6 アドレス

host が probe とスロットを名指す文字列: `oep://<unit_id>[/<slot name>]`。authority は unit_id（§7.5、小文字）、path はスロットの名前
（[probe の設定](oep-if-probe-config.ja.md) §1.1）1 つだけ。path の無い `oep://<unit_id>` は probe 自身。v1 はこれ以外（query、port、
複数の path）を定めない。IDE や設定のファイルが probe を覚えるときはこの形で覚える（VID:PID や口の名前ではなく）。

## 8. plan

plan は **fn ごと**に持つ。

- **plan_apply**: role_assignment の TLV（0x90、critical: fn(u16)、role(u8)、channel(u16)）の並び。1 つの割り当ての見分けは
  (fn, role, channel)（同じ role に複数の channel を持つ機能がある。gpio など）。**要求に出てくる fn の割り当てだけを
  原子的に置き換え**、ほかの fn の plan はそのまま保つ。置き換える fn の今の割り当てを外したものとして、各インターフェースが
  副作用なしで確かめ（§8.1 の取り合いの確かめを含む）、全部が受け入れたときだけ適用する。1 つでも断れば、何も変えずに
  rejected（置き換えるはずだった fn の今の plan も残る）。
- **割り当ての数**: probe の plan が一度に持てる role_assignment の数（すべての fn の合計）は describe の plan_roles（§7.5）。置き換えた後の
  合計がそれを超える plan_apply（と設定の set）は、何も変えずに rejected unavailable（資源が足りない。§8.1 と同じ断り方。要求の形は
  正しいので malformed ではない）。
- **plan_release**: `n(u8)、n × fn(u16)`。挙げた fn の plan を解く（n = 0 はすべての fn）。plan の無い fn は無視する。
- **設定の plan はセッションのものではない**: probe の設定（`oep.probe.config` の plan の項目）が入れた fn の plan は、設定だけが
  変える。plan_release はその fn を解かずに無視し（n = 0 でも）、plan_apply がその fn を挙げたら何も変えずに rejected
  unavailable（§8.1 のピンの取り合いと同じ断り方）。設定の plan を変える・外すのは、設定の set（とその保存）で行う。こうしないと、
  保存した設定と実際の割り当てが食い違う。
- 解いたピンは、**probe の設定がそのピンの空きのときの状態を決めていればその状態、決めていなければ Hi-Z（入力、プルなし）**
  にする。インターフェースは、解いた後もピンを駆動し続けてはならない（空きの状態の設定は `oep.probe.config` の idle、
  [probe の設定](oep-if-probe-config.ja.md)）。
- plan の寿命は §9（fn ごと）。

**plan_apply の断り方**（§4.3 の順）:

| 状況 | reason |
|---|---|
| 形の誤り、同じ (fn, role, channel) が 2 回、fn 0 を挙げた | malformed |
| fn が無い | unknown_function |
| role がそのインターフェースに無い、channel が role_channels の候補に無い、channel_group のどれにも一致しない | unsupported（tag 0x90） |
| plan_roles を超える、ピンや資源の取り合い（§8.1）、設定の plan の fn | unavailable（cause 2 / 1 / 5） |

### 8.1 資源の取り合い

- probe の資源（ピン、ペリフェラル、DMA、タイマーなど）を取るものはすべて、取る前に、今ある plan、connection、設定から入れた
  資源（bind など）とぶつからないか確かめる。ぶつかれば rejected unavailable で断り、**今ある機能の状態は何も変えない**。
  取るもの: plan_apply、線の attach（pins）、設定の set、インターフェースが定める資源を作る操作。
- どの内部の資源（DMA の番号など）を使うかは host に見せなくてよい。共有して安全な使い方（同じピンを 2 つの機能が入力として
  読むなど）は、probe が明示的に許すときだけ許す。

## 9. 資源の寿命（一般の規則）

**セッションが作った資源は、明示の end では残して次のセッションに渡し、lease の期限切れと force で奪われたときに外す。**

| 出来事 | セッションが作った資源 | 購読（§11） | §5.2 の表 | 次の同じ ID の要求 |
|---|---|---|---|---|
| end | 残る。次に成功した open で、そのセッションの資源に原子的に移る | 終わる | 残る | 再開して処理（§6.2） |
| lease の期限切れ | 外す | 終わる | 残る | rejected expired、open で resumed = 2 |
| force で奪われる | 外す（期限切れと同じ） | 終わる | 捨てる（奪った open が捨てる） | 奪った側が持つ間は locked、その後は no_session（最後の ID は奪った側） |
| 同じ ID の open（保持中） | 残る | 残る（送り先はその経路） | 捨てる | — |
| probe の再起動 | 無くなる（boot_id が変わる） | 無くなる | 無くなる | no_session |

- end の後に残った資源は、次に成功した open（別の session_id でも、同じ session_id の再開でも）でそのセッションのものになり、
  そのセッションの lease の期限切れか force で外れる。引き継がせたくない host は、end の前に自分で外す（detach、close、
  plan_release など）。
- 本体の資源: **plan**（外すとピンは plan_release と同じく解放。target の線を plan で保っていた場合、target の状態が変わりうる）、通知の購読
  （§11。購読は end でも終わる）、§5.2 の表。
- インターフェースが作る資源（debug の connection、ストリームなど）の寿命は、インターフェースの文書が、この規則の上で定める
  （誰が使っているか、いつ閉じるか）。
- 保存した設定（インターフェースが定める）から入れた資源は、セッションの資源ではない。
- **資源の番号は u16 で、probe で 1 つの空間**（connection、ストリームなど、インターフェースが番号で指すものすべて。別のインター
  フェースの資源を渡されたら rejected unavailable cause 6）。新しい資源を作るたびに 1 から順に進め、65535 の次は 1（§2.6）。閉じた
  番号は十分離れてから再利用してよい（直近に閉じた【決める: 数。案は 1024】個の番号は使わない）。失敗した作成（attach が
  失敗した、同じ場所の再 open）は番号を消費しない。閉じた資源の番号を使った要求は rejected no_connection。一周の後は古い番号が
  別の資源を指しうる: host は no_connection を受けた番号を捨て、長く持つ番号は一覧の op（connections、streams）で確かめる。

## 10. 長い操作（予約）

v1 は長い操作を持たない。すべての op は 1 つの応答で完了する。resolution 0x02、reject reason 0x05 busy、core の op 0x20〜0x2F は、
長い操作を定めるときのために予約する（そのときに、結果を取り出せるセッション、番号の振り方、lease の期限切れと force での
扱いを一緒に決める）。

## 11. 通知

probe から送る通知の仕組み。probe の対応は任意で、host は購読しなければ何も受け取らない。

### 11.1 host の義務（全 host）

- 受け取ったフレームを role で振り分ける。corr で照合するのは role 0x02 だけ（0x05 / 0x06 のバイト 1〜2 は fn）。
- 知らない role のフレームと、待っていない corr の応答は捨てる（シリアルの口では、生のバイトが偶然フレームに見えたものもこれで
  捨てる、§3.4）。
- 通知が届き続けても、応答を待つ処理と受信を読む処理が締め切りどおりに終わるようにする。

### 11.2 形

```text
データ   role=0x06 | fn(u16) | seq(u16) | position(u64) | len(u16) | data | [TLV]      見出し 5 byte
出来事   role=0x05 | fn(u16) | seq(u16) | kind(u8) | 固定部分 | [TLV]                   見出し 6 byte
```

- データの payload の形は全インターフェース共通: `position` はこのフレームの先頭のストリームの位置（インターフェースが決める）、
  `len` は data の長さ、後ろは TLV（§2.3）。出来事の固定部分は kind ごとにインターフェースが決め、後ろは TLV。

- `seq` は fn ごとのフレームの通し番号（u16、一周する。データと出来事で共通）。subscribe のたびに 0 から数える。抜けがあれば
  フレームが失われた。probe は、生まれた出来事すべてに番号を振り、probe の中で捨てたものも番号を消費する。
- fn 0 の出来事は probe 全体のもの。kind 0x01 = ハートビート（固定部分: boot_id(u32)、uptime_ns(u64)、§2.6a）。

### 11.3 購読

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x30 | subscribe | fn(u16)、min_bytes(u16)、max_delay_ms(u32)、[TLV] | — |
| 0x32 | unsubscribe | fn(u16) | — |

- **購読はロックの持ち主だけができ、ロックと一緒に終わる**（end、期限切れ、force で奪われたとき）。読むだけの監視は、シリアルの
  口の生のバイト（bind、[probe の設定](oep-if-probe-config.ja.md)）で行う。ロックを持たない購読は予約（後から subscribe の TLV で
  足す。今の購読の意味は変えない）。
- fn 0 の subscribe / unsubscribe はどの probe も実装する。送り出さない fn への subscribe は rejected unsupported（§4.3 の順 6）。
  購読の無い fn の unsubscribe は何もせず成功。
- 同じ fn をもう一度 subscribe したら、前の購読を原子的に置き換える（送る条件、送り先の経路、seq を 0 から）。1 つの fn の購読は
  1 つだけ。
- **まとめて送る条件**: min_bytes バイトたまるか、最初のバイトから max_delay_ms 経ったら送る。0 はその条件を使わない。両方 0 なら
  あるだけすぐ送る。
- fn 0 を購読するとハートビートが来る。周期は max_delay_ms（0 なら 1000 ms）。
- 流れの量の予算（クレジット）は持たない。host や線が遅れた分は probe の中で押し出され、インターフェースの payload
  （ストリームの位置など）か seq の抜けで分かる。

### 11.4 probe の義務（送り出す probe）

1. **応答を先に送る。** 届いている要求をすべて処理してから、通知を送る。
2. **送りかけの通知を小さく保つ。** 経路の送信バッファに、送りかけの通知を【決める: 上限。案は max_frame の 2 倍】byte を超えて
   ためず、書き込みで待たない。入らない通知は probe の中で捨てる（seq の抜けで分かる、§11.3）。シリアルの口では host の OS の受けの量（§3.4）も上限で、host が min_bytes で伝える。
3. 通知は、その fn の subscribe が来た経路に送る。

## 12. core（fn 0）の操作一覧

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | confirm | §7.1 | §7.1 | 不要 |
| 0x02 | list | §7.2 | §7.2 | 不要 |
| 0x03 | describe | §7.3 | §7.3 | 不要 |
| 0x04 | plan_apply | role_assignment の TLV の並び | — | 必要 |
| 0x05 | plan_release | n(u8)、n × fn(u16) | — | 必要 |
| 0x10 | open | session_id(u32)、lease_ms(u32)、force(u8)、[TLV owner] | lease_ms(u32)、boot_id(u32)、resumed(u8: 0 / 1 / 2、§6.4) | open がロックを取る（role 0x01） |
| 0x11 | end | — | — | 必要 |
| 0x12 | keepalive | — | — | 必要 |
| 0x13 | lock_state | — | locked(u8)、remaining_ms(u32)、[TLV owner] | 不要 |
| 0x14 | port_speed | §3.5（任意。describe の port_speed を出す probe だけ） | baud(u32) | 必要 |
| 0x30 | subscribe | §11.3 | — | 必要 |
| 0x32 | unsubscribe | §11.3 | — | 必要 |
| 0x40 | link_source | length(u32) | length バイト（1 フレームに入る分まで。k バイト目は k & 0xFF） | 不要 |
| 0x41 | link_sink | 任意のバイト（数を持たない並び） | 受け取った長さ(u32) | 不要 |

link_source / link_sink は線の速さを測るためのもので、状態を変えない。この 2 つだけが、長さを持たない並びで終わる形を持つ
（§2.3 の例外。後ろに TLV は付かない）。

## 13. 拡張の規則（インターフェースの書き方）

標準インターフェースも独自のインターフェースも、次の規則で定義する。

1. **名前**: `oep.` は project が予約する。独自のインターフェースは逆 DNS（`io.github.<owner>.<name>` など）。名前は host が何に
   使うかで切る（probe のペリフェラルの名前にしない）。**1〜64 byte、使える文字は `a-z 0-9 - .`**（registry の `limits`）。
2. **定義が決めるもの**: revision、op の表（番号、要求、応答、ロックの要否）、各 op の TLV の tag（その op の文脈の空間）、
   describe のインターフェース固有のタグ（0x40〜0x7F）、plan の role の番号、reject reason（0x40〜0x7F）、出来事の kind
   （0x01〜0x7F）、通知のデータの payload の形、インターフェースが作る資源とその寿命（§9 の上で）。
3. **形の規則**: §2.3 のとおり（固定部分 + TLV、可変の並びの前に数、省略できるフィールドを置かない、安全の引数は critical）。
4. **失敗**: 受け付けなかったものは rejected、受け付けて失敗したものは completed failed / partial（§4.2）。
5. **ロックなしの op は状態を変えない**（§6.3）。
6. **版**: §2.7。
7. **独自のタグを標準インターフェースに混ぜない。** 独自の情報は独自のインターフェースに置く（別の fn として出す）。
8. **特化したものは名前で分かるようにする。** チップや系統に特化した手順（flash の書き方、リセットのタイミングなど）は、
   何に特化しているかが名前で分かるインターフェースに置く（例: `oep.wire.rvswd` はその線を持つ系統のためのもの。ある系統の
   書き込みのリセットの手順のように、probe がやらないとタイミングが間に合わないもの）。標準にも独自にも置いてよい。
   **汎用の名前のインターフェース（`oep.target.riscv-dm`、`oep.target.arm-adi`、`oep.fixture.*` など）には、特定のチップ向けの
   処理を入れない。** 特化したものは移植性が下がる（それを使う host はその機能を持つ probe に縛られ、新しいチップへの対応に
   probe の firmware の更新が要る）。汎用の手順（生の転送と host の知識）で済むものは、そちらで組む。
9. 標準インターフェースの番号は registry に載せる。独自のインターフェースの番号は、その定義が管理する。

## 14. 標準インターフェースの文書

| 文書 | インターフェース |
|---|---|
| [標準インターフェース: 共通部品](oep-if-common.ja.md) | 位置つきのストリーム、debug の connection |
| [標準インターフェース: 線とデバッグ](oep-if-debug.ja.md) | `oep.wire.rvswd`、`oep.wire.swio`、`oep.wire.swd`、`oep.target.riscv-dm`、`oep.target.arm-adi` |
| [標準インターフェース: コンソール](oep-if-console.ja.md) | `oep.target.console`（framing の dmseq は [target-console-dmseq](target-console-dmseq.ja.md)） |
| [標準インターフェース: fixture](oep-if-fixture.ja.md) | `oep.fixture.gpio`、`oep.fixture.uart`、`oep.fixture.i2c-target`、`oep.fixture.spi-target` |
| [標準インターフェース: キャプチャ](oep-if-capture.ja.md) | `oep.fixture.logic`、`oep.fixture.analog`、`oep.fixture.capture-group` |
| [標準インターフェース: probe の設定](oep-if-probe-config.ja.md) | `oep.probe.config` |

## 15. 規範ではない文書（理由と経緯）

- [core wire model v1（v0 からの差分）](v1-core-wire-delta.ja.md): この文書にまとめる前の差分と、実験の記録。
- [セッションと排他](session-and-exclusivity.ja.md)、[能力の識別方式の比較](capability-identification-comparison.ja.md)、
  [能力の宣言モデル](capability-declaration-model.ja.md)、[能力の名前の階層](capability-name-hierarchy.ja.md): 決めた理由。
- [シリアルの口と永続化](probe-cdc-and-persistence.ja.md): 複数の経路、設定、起動モードの試作と実測。
- [v1 の未合意の案](v1-open-proposals.ja.md): 決める前の案と、決めた経緯。
- [レビューへの回答](review-answer-2026-09-26.ja.md): 第三者のレビュー。
- [host 開発ガイド](host-development-guide.ja.md)、[probe 開発ガイド](probe-development-guide.ja.md): 実装の実務。
