# Open Embedded Probe — プロトコル本体（OEP core）v1

[English](oep-core.md)

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](versioning.ja.md) §6）。この文書は OEP のプロトコル本体だけを定める。インターフェースは
それぞれの文書が定める（名前が `oep.` で始まるものの一覧は [インターフェース](../interfaces/README.ja.md)）。この文書はそれだけで完結する: 読む人が規則の
理由を必要とする所では、理由を規則と一緒に書く。ガイド（§14）は実務を足すもので、規則は足さない。この文書と、規範ではない文書が食い違えば、この文書が正しい。

番号（op、tag、reject reason、status、enum）の唯一の定義は `registry/oep-v1.toml` で、この文書の表はその写しである。
食い違えば registry が正しく、文書を直す。registry は、名前が `oep.` で始まるインターフェースの名前と番号も持つ。
probe と host が適合するために何をするか、それをどう確かめるかは [適合](conformance.ja.md)（ガイド）に並べてある。

## 0. 範囲と層

OEP は 2 つの層からなる。

| 層 | 中身 | 名前 | 版 |
|---|---|---|---|
| **本体（この文書）** | どの probe と host も、機能に関係なく実装するもの: 経路とフレーム（[OEP の経路](oep-transports.ja.md)）、メッセージ、セッションと排他、発見（confirm / list / describe）、probe の時刻（clock）、channel と資源の寿命と取り合いの一般の規則、通知の仕組み、拡張の規則 | 持たない（fn 0 で話す。list に載らない） | プロトコルの revision（confirm） |
| **インターフェース** | 本体の仕組みだけで定義した、名前つきの機能。本体が必須としない機能は、すべてインターフェースにある | 逆 DNS の名前。project 自身のものは短い `oep.` の名前（§13） | インターフェースごとの revision |

インターフェースどうしの関係（あるインターフェースが別のインターフェースの資源を使う、など）は、関係するインターフェースの
文書が定める。

OEP の外: probe 自身の firmware の更新（DFU、Mass Storage など）、USB の記述子の細部。

**外部の仕様**: OEP のプロトコルは、これらの文書だけで定まる。target、バス、経路を動かすには、それぞれの文書が「参照する仕様」の節に並べる
外部の仕様も要る（経路のものは [経路](oep-transports.ja.md) §7）。

## 1. 用語

| 用語 | 意味 |
|---|---|
| probe | OEP を話す装置（デバッガ、治具、ロジアナなど） |
| host | probe を使うソフトウェア |
| target | probe がつながる相手（開発中のマイコンなど） |
| 経路（transport） | OEP のフレームを運ぶもの（UART bridge、USB CDC、内蔵の USB シリアル、USB の vendor bulk、HID、TCP） |
| シリアルの口（serial port） | 経路のうち OS からシリアルデバイスに見えるもの（UART bridge、USB CDC、内蔵の USB シリアル）。OEP と生のバイトを共用する（[経路](oep-transports.ja.md) §4） |
| インターフェース | probe が名前で出す機能。list で見つけ、fn で呼ぶ |
| fn | そのセッションの間、インターフェースを指す番号（u16）。fn 0 は本体（名前を持たず、list に載らない） |
| op | インターフェースの中の操作の番号（u8） |
| セッション | ロックを持って状態を変える権利。host が選ぶ session_id（u32）で識別する |
| lease | ロックの期限。keepalive などの要求で延びる |
| channel | probe のピンの番号（u16） |

### 1.1 規範の語

大文字の MUST、MUST NOT、SHOULD、SHOULD NOT、MAY は RFC 2119 と RFC 8174 のとおりに使う。probe や host がすることを現在形で述べた文（「probe は〜を返す」）は要件（MUST）である。「できれば」は SHOULD。（参考）と記した文、例、注は規範ではない。日本語の訳では、「〜する／〜しない」が MUST / MUST NOT、「〜してよい」が MAY、「できれば〜する」が SHOULD にあたる。

### 1.2 適合

probe が実装しなければならない（MUST）もの:
- §3 の経路の少なくとも 1 つと、そのフレーム;
- §4〜§6;
- fn 0 の confirm、list、describe、clock、open、end、keepalive、lock_state;
- fn 0 の describe の unit_id、transport、max_op_ms（§7.5）;
- fn 0 と、list に載せるすべての fn の describe の、共通の tag ops（§7.4）;
- channel を持つなら、fn 0 の describe の channels（§7.5）と §8 の channel の空きの状態;
- 通知を送り出すインターフェースを持つなら、§11.3 と §11.4。

任意: すべてのインターフェース。あるインターフェースを出す probe が、ほかにどのインターフェースを出さなければならないかは、そのインターフェースの文書が定める（§0）。

**必ず持つ op と任意の op。** インターフェースの op の表（fn 0 は §12、ほかはそのインターフェースの文書の op の表）の op は、そのインターフェースを list に載せる probe が必ず持つ。文書が任意と書いた op は除く。**すべての fn は、持つ op を 1 か所で宣言する: describe の共通の tag ops（0x09、§7.4）。** 必須の op はすべてそこに立てる。任意の op は、probe がそれを持つときに限り立てる。

probe は、その fn の ops が立てない op（インターフェースが定義しない op、または持たない任意の op）の要求に rejected unknown_operation で答える（§4.3）。持つ op に、宣言しない任意の機能（mode、format、値、critical の TLV、ピンの組み合わせ）を求める要求には rejected unsupported で答える（§4.3）。

## 2. 共通の規則

### 2.1 byte order と文字列

数値はすべて little endian。文字列は UTF-8 のバイト列で、長さは別に持つ（終端の 0 は付けない）。
**bitmap** は byte の並びで、bit i は byte ⌊i/8⌋ の bit (i mod 8) である（bit 0 は最下位の bit）。bitmap は、それを含む値の終わりまで続く。

- 真偽値の u8 は、送る側が 0（偽）か 1（真）を置き、読む側は 0 でない値をすべて真と読む。
- host は、応答の text を見せる前に、C0 の制御文字（0x00〜0x1F）、0x7F と正しくない UTF-8 を置き換える。

### 2.2 TLV

```text
tag(u8) | len(u16) | value(len byte)
```

- **すべての TLV が 1 つの形**で、値の長さ（0〜65535 byte）によらない。len がそれを含む message の終わりを越える TLV は、
  要求では malformed。応答、出来事、データの中にあれば、その応答、出来事、データは壊れている。
- **tag の番号は下位 7 bit（0x01〜0x7E）。** bit 7 は critical の印。要求の中でだけ使い、番号には含めない: 0x10 と 0x90 は同じ TLV を、印なしと印ありで送ったもの。応答、出来事、データでは bit 7 は 0 で、そこで bit 7 の立った TLV に会った読む側は、知らない tag として読み飛ばす。tag 0x00 と 0x7F は TLV に使わない（0x00 は rejected unsupported の payload の印、§4.3）。
- rejected unsupported の payload は、受け取ったままの tag の byte（bit 7 を含む）を持つ。
- tag の空間は **(fn, op) の文脈ごと**（同じ値でも文脈が違えば別物）。
- 同じ tag の繰り返しは、繰り返すと定義が言う tag で、並びを表す（§2.3）。

### 2.3 固定の形と TLV

- **容器は自分の長さを知る**: フレーム、TLV、並び、バイト列（data）のどれも、読む側が要求や外の知識なしに終わりが分かる。
  可変の部分（並び、バイト列、文字列）には前に数か長さを置く。
- **固定の形はどれも (名前, revision) で決まる**（fn 0 ではプロトコルの revision、§2.7）: 要求、応答、出来事、データの payload の固定部分、TLV の値、並びの
  要素、probe.config の項目。固定の形は後ろに伸ばさない。その中の可変の部分（名前、要素の中の一覧）は前に数か長さを
  置くので、固定の形も自分の長さを知る。
- **並び**: `count、count × 要素`。要求でも応答でも同じ。要素は自分の長さを持たない。要素の形は revision で決まり、読む側は
  フィールドを 1 つずつ読む。
- **応答**: 各 op の応答の固定部分（と、前に数か長さを置いた並び）の後ろは TLV の並び。後から足すものはすべてここに TLV で足す。
  host は知らない tag を読み飛ばす。固定部分より短い応答は壊れた応答として扱う。応答、出来事、データの TLV で、値が定義の
  決める長さ（可変の部分を持つ値なら、その数と長さが決める長さ）を持たないものは壊れている: host はそれを使わない。
  **応答の固定部分の形は (op, resolution, outcome) ごとに
  op の定義が決める**（成功と失敗で形が違ってよい。インターフェースの共通部品 §3）。
- **出来事とデータ**（§11.2）も応答と同じ: 固定部分の後ろは TLV の並び。
- **要求**: 要求の後ろに足せるのは TLV の並びだけ。host は、効かなければ要求に意味が無いか、害がある項目（速さの上限、pins など）に
  **critical の bit を付ける**。
- **知らない TLV**（この probe が実装しない tag）: critical なら、probe は要求を rejected unsupported（payload に受け取ったままの tag）で断る。
  critical でなければ無視する。
- **実装する TLV** は、bit 7 によらず同じに扱う: 値の長さが定義と違う（可変の部分を持つ値なら、その数と長さが決める長さと違う）か、定義が除く値を
  持てば rejected malformed。定義が使わずに残した値と、この probe が扱わない値は rejected unsupported（受け取ったままの tag）。
- **要求の TLV の値は後ろに伸ばさない。** 新しいフィールドは新しい tag に置く。
- 繰り返すと定義が言わない tag が 2 つ以上あれば、読む側は最初のものを使う。
- 固定部分より短い要求は rejected malformed。
- **可変の並びは前に数を置く**（後ろに TLV を付けられるように）。
- 固定部分に省略できるフィールドを置かない（省略したい値は TLV にする）。

### 2.4 知らない値

- 知らない role のフレームは捨てる。
- probe は、role が要求の role（0x01）でない message と、見出し（10 byte）より短い要求を、答えずに捨てる。host は、role が要求の role の message を捨てる。
- host は、5 byte より短い応答と、見出しより短い出来事やデータのフレームを、壊れたフレームとして扱う（§5.2、[経路](oep-transports.ja.md) §5）。
- 知らない resolution、completed の知らない outcome は失敗として扱う。
- インターフェースの status や reason の知らない値は失敗として扱う。
- 知らない出来事の kind は捨てる（seq は数える）。
- host は応答の flags の予約のビットを無視する。応答の enum の知らない値で失敗を知らせないもの（cause、scan の entry の kind）は、知らない値として見せる。status と reason の知らない値は失敗のまま。

### 2.5 番号の空間

| 空間 | 範囲 |
|---|---|
| role | 0x01 要求、0x02 応答、0x05 出来事、0x06 データ。0x00、0x03、0x04 と 0x07〜0xFF は予約 |
| 本体（fn 0）の op | 0x01〜0x0F 発見、0x10〜0x1F セッション、0x20〜0xFF 予約 |
| インターフェースの op | 0x01〜0xEF はインターフェースの定義が決める。ただし 0x30 は subscribe、0x32 は unsubscribe に、すべてのインターフェースで予約する（§11.3）。0xF0〜0xFF は予約 |
| reject reason | 0x01〜0x3F 本体（全インターフェース共通）、0x40〜0x7F インターフェース、0x80〜0xFF 予約 |
| outcome | 0 success、1 failed、2 partial。ほかは予約 |
| 出来事の kind | fn ごとの空間。0x01〜0x7F はインターフェースが決める、0x80〜0xFF は予約（fn 0 は通知を送らない、§11.2） |
| TLV の tag | (fn, op) の文脈ごと。番号は下位 7 bit で、bit 7 は critical の印（§2.2）。0x00 と 0x7F は全文脈で予約 |
| describe の tag | 0x01〜0x3F 本体の共通タグ（§7.4）、0x40〜0x7E インターフェース |
| 資源の番号 | u16、probe で 1 つの空間（§9） |

定義が別に言わない限り、enum の使っていない値と要求の予約のビットは、どれも後から定義されうる（§2.7）。probe はそれらを rejected unsupported で断る。

### 2.6 一周する値

seq（u16）と、インターフェースが定める通し番号や時刻のうち一周すると定めたものは、差を同じ幅 w の符号付きとして
比べる（serial number arithmetic）。そうした 1 つの空間の値のうち、probe が同時に持つもの（まだ読めるマーク、まだ解放しない区画、まだ読まれない置き場）では、
いちばん新しいものからいちばん古いものを引いた差は 2^(w−2)（幅の 4 分の 1）未満。一周させない値は u64 にする
（インターフェースが定めるストリームの位置、時刻など）。資源の番号（§9）は等しいかどうかだけを比べ、使い回しは §9 で決まる。

### 2.6a 時計

probe の時計は 1 つ: **起動からの ns（u64）**。時計は、同じ boot_id の間、減らず、一周しない。時刻を返す所（clock の uptime_ns、マーク、区画、状態の「最後に試した時刻」）はすべてこの値で、
「まだ無い」は全ビット 1。
host は時計の今の値を clock（§7.7）で読む。

### 2.7 名前と revision

- インターフェースのどの**固定の形**（§2.3: 固定部分、TLV の値、並びの要素、項目）も、形と意味は **(名前, revision) で決まる**（list の revision、u8）。
- **revision を上げるのは、固定の形の意味か長さを変えるときだけ**。host は知らない revision のインターフェースを使わない。
- 固定の形を変えずに、任意の request TLV、response TLV、任意の op、任意の event を足すときは、revision を変えない。知らない
  host はそれらを使わない。任意の op の有無は ops（§1.2、§7.4）で、op でない任意の機能（モード、format など）の有無は describe（features など）で宣言する。
- 本体の形を変えるときは、プロトコルの revision（confirm）を上げる。この文書の形は revision 1。

## 3. 経路

メッセージは経路のフレームで運ぶ。経路は [OEP の経路](oep-transports.ja.md) が定める。その文書は本体の一部である。

## 4. メッセージ

### 4.1 要求

```text
role=0x01 | corr(u16) | fn(u16) | op(u8) | session_id(u32) | payload    見出し 10 byte
```

- `corr`: host が振る番号。**host は要求ごとに 1 ずつ進める**（session_id 0 の要求も数える。65535 の次は 1。0 は使わない）。
  同じ番号をもう一度使うのは、§5.2 の送り直しのときだけ。probe は、送り直しと、覚えていない古い要求の見分けにこの順序を使う。
- `session_id`: 要求が属するセッション、または **0 = セッションなし**。どの要求もこれを持つ。
  - ロックが要る op（§6.3）の要求は、ロックを持つセッションの id を持つ。0 なら rejected session_required。
  - ロックなしの op の要求は 0 を持ってよい: そのときはセッションの確かめ（§5.2、§6.2）なしに処理し、lease に触れない。0 でない id なら、
    ロックが要る要求と同じくそれらを通り、lease を数え直す（§6.1）。
  - open は、開くセッションの id を持つ（§6.4）。0 なら rejected malformed。

### 4.2 応答

```text
role=0x02 | corr(u16) | resolution(u8) | detail(u8) | payload           見出し 5 byte
```

| resolution | 値 | detail | payload |
|---|---:|---|---|
| rejected | 0x00 | reject reason（§4.3） | reason が定める補助の情報 |
| completed | 0x01 | outcome（0 success、1 failed、2 partial） | op が定める |

- 要求ごとに応答はちょうど 1 つ。応答はその要求の来た経路に、同じ corr で返す。fn と op は返さない。
- **rejected は「要求を受け付けなかった」ときだけ**（書式、番号、セッション、今の状態で受けられない）。受け付けて実行した
  結果うまくいかなかったものは completed の failed か partial にし、payload でどこまで進んだかと理由を返す。

### 4.3 reject reason（本体）

| 値 | 名前 | 意味 | payload |
|---:|---|---|---|
| 0x01 | unknown_function | その fn は無い（見出しの fn、または payload で指す fn） | — |
| 0x02 | unknown_operation | その fn にその op は無い | — |
| 0x03 | malformed | 長さ・値域の誤り | — |
| 0x04 | unavailable | 今の状態・資源では受けられない | TLV の並び（任意、下） |
| 0x06 | window_exceeded | window / max_inflight を超えた | — |
| 0x07 | no_session | 要求は session_id を持つが、どのセッションもロックを持っていない（セッションが終わった、または初めから無い）。host はセッションを開き直す | — |
| 0x08 | locked | 他のセッションがロックを持つ | 残り時間 ms（u32）、[TLV owner（§6.4）] |
| 0x09 | session_required | ロックが要る op の要求が session_id 0 を持つ | — |
| 0x0A | no_connection | 要求の資源（connection、stream など、番号で指すもの）を probe が知らない。host は作り直す。どのインターフェースでも、知らない番号にはこれを使う | — |
| 0x0B | unsupported | 定義にはあるが、この probe が扱えない（critical の TLV、固定部分の値、この probe が持つ op の任意の機能） | `tag(u8)`、[TLV]。tag は critical の TLV なら受け取ったままの値、固定部分の値なら 0x00。どの要素かを示すときは後ろに TLV（unavailable と同じ tag の空間: channel、index） |
| 0x0C | result_lost | 送り直された要求の結果を覚えていない（§5.2） | — |

rejected の detail は reason で、そのほかの情報は payload に置く。

**断り方の順**: probe は次の順に見て、最初に当たったもので答える。

1. 見出し: unknown_function → unknown_operation（その fn の ops が立てない op、§1.2）→ session_required。
2. 送り直し（§5.2 の表）: result_lost / 覚えた応答。
3. セッション（§6.2）: no_session / locked。
4. そのほか: probe は、書式（malformed: 長さ、中身と合わない数、TLV の符号化、フィールドどうしの矛盾、定義が除く値）、対応（unknown_function: payload で指す fn が無い。
   unsupported: 定義が使わずに残した値、この probe が宣言しない値、知らない critical の TLV、宣言が許さないピンの組）、状態（window_exceeded、unavailable: 今の状態や資源で受けられない。
   no_connection: 番号で指す資源を知らない）を、何も変える前にすべて確かめ、当たった理由のどれか 1 つで断る。

unsupported の payload の tag は、固定部分の値なら 0x00、TLV についての断りならその TLV の受け取ったままの tag。

**unavailable の payload**（任意の TLV の並び。host は知らない tag を飛ばし、無くても扱えるようにする。probe は分かる範囲で付ける）:

| tag | 名前 | 値 |
|---:|---|---|
| 0x01 | cause | u8: 1 ピンが使われている、2 数の上限（ピンの割り当て、スロット、接続など）、3 保存先が足りない、4 組（capture-group）に束ねられている、5 設定が持つ（設定の plan、disable、出力の idle、スロット）、6 状態が違う（configure していない、動いている、など） |
| 0x02 | channel | u16。ぶつかった channel（繰り返してよい） |
| 0x05 | fn | u16。断りの対象の fn（capture-group の bind で、どのトラックかを示す） |

インターフェースは 0x40 以降に自分の tag を足せる。rejected unsupported の payload の後ろの TLV も同じ空間（channel 0x02、fn 0x05、
インターフェースの index など）。ただしそこでは 0x01 は supported で、confirm の断りに使う（§7.1）。

### 4.4 パイプライン

- confirm（§7.1）で probe は `max_frame`（受け取る最大の message 長）、`window`（未解決の要求の message 長の合計の上限）、
  `max_inflight`（未解決の要求の数の上限）を返す。message 長は見出し（role から）を含み、フレームの包み（COBS、CRC、length）は含まない。
- host は両方の上限を守る。超えた要求を probe は rejected window_exceeded で断ってよいが、バッファを超えて失われた要求には
  応答も返らない。守るのは host の責任である。
- probe は要求を受け取った順に処理し、応答を受け取った順に返す。
- confirm の max_frame、window、max_inflight は、**その confirm が来た経路の**上限である。経路ごとに別々に数え、ある経路で未解決の要求は、ほかの経路の受けの余地を使わない。§5.2 の表は probe に 1 つのまま（セッションの要求は 1 つの経路で送る、[経路](oep-transports.ja.md) §3）。
- **host の待ち時間**: 応答が来ないことは時間切れだけで判断する。host は要求ごとに**少なくとも**次を待つ: その要求の引数で決まる時間（インターフェースの文書が
  op ごとに定める。定めなければ 0。多くても max_op_ms、§7.5）+ 1000 ms（`host_wait_add_ms`）+ 転送の時間（[経路](oep-transports.ja.md) §6）。待ちは、要求を書き終えた時から始める。同じ経路に先の要求が未解決の間は、その 1 つ前の要求の応答が届いた時から始める（probe は順に答える）。
  この下限より長く待つことはいつでも許される。待ちが過ぎたら §5.2 の送り直しに進む。
- **この下限はすべての要求に当てはまる**。インターフェースの文書が要求と要求の間に置く待ちは、応答を待つ時間ではなく、この下限を縮めない。
  [経路](oep-transports.ja.md) §3、§4 が host に繰り返させる confirm は、それぞれ新しい corr の新しい要求で、§5.2 の送り直しではない: host は、前の confirm の下限が過ぎる前に次を送ってよく、後から届いた前の corr への応答は受けるか読み飛ばす。ほかの要求はこのように繰り返さない。

## 5. 立て直しと送り直し

### 5.2 送り直しと重複排除

- 応答が壊れたか来なかったとき、host は**同じ corr で送り直してよい**（状態を変える要求も）。probe は下の表から答えるので、送り直しで要求が二度実行されることはない。
  何回、いつ送り直すかは host が決める（[host ガイド](host-development-guide.ja.md) §8）。セッションが口を持っている間
  （[経路](oep-transports.ja.md) §4、生の転送は止まっている）に届いた壊れたフレームは、待っている答えのものとして扱ってよく、待ち時間を待たずに送り直してよい。立て直しの中で unsubscribe
  と end を送ったときは、セッションが終わっているので、元の要求は送り直さない。
- 最後に送ったもの（元の要求か送り直し）の待ち時間が答えなしに過ぎ、host がもう送り直さないなら、host はその経路が失敗したとして扱う: その要求の結果は分からず、その経路で出ている要求もいっしょに失敗する。そこで何かを送る前に、host は [経路](oep-transports.ja.md) §5 の confirm で立て直す（COBS を含むどの種類のフレームでも: 入力が静かになってから、自分の corr を持つ応答が返る confirm）か、経路を閉じて開き直す。その confirm で boot_id が変わっていれば再起動（§6.5）。立て直した後、host は状態を変える要求を繰り返す前に状態を読む。
- probe は、最後のセッションの id を持った要求について、直近の max_inflight 個以上の (corr, 応答) と、そのセッションで最も新しい corr を覚えておく。
  **要求の同一性は corr だけで決まる**（§4.1 の順序）。
- probe は、最後のセッションの要求のうち §4.3 の順 2 を通ったものすべての応答を、rejected の応答も含めて覚え、それに合わせて最も新しい corr を進める。rejected になった要求を直して送る host は、新しい corr で送る。
- §5.2 はどの probe（OEP の要求に自分で答えるどの端点も、[経路](oep-transports.ja.md) §1）にも、TCP を含むどの経路でも掛かる。TCP はフレームを失わないが、応答が遅れれば host は待ち（§4.4）の後に送り直すので、probe は要求を二度実行しないように表を持つ。表は probe に 1 つで、セッションと同じく、すべての経路と TCP の接続で共有する。OEP の probe に中継するだけのブローカーは自分の表を持たない。corr を付け直すときは、client の送り直しを、最初に使ったのと同じ corr で中継する。そのために、受けた client の接続ごとに、client の corr から上流で使った corr への対応を、少なくともその client の直近の max_inflight 個の要求について持ち、その接続が閉じたら捨てる。
- 最後のセッションの session_id を持つ要求は、**§6.2 の判定より先に**次のとおり見る（ロックが空いていても同じ）。open は表で
  引かない（送り直した open は §6.2 で決まる）:
  - 表に同じ corr があれば、**実行せずに覚えた応答を返す**。ロックの状態は変えない（送り直した end でロックが立ち直ることはない）。
  - 表に無く、corr が最も新しい corr より新しくない（差を u16 の符号付きで見て 0 以下）なら、実行せずに rejected result_lost
    （表から落ちた古い要求の送り直し。host は状態を読み直して確かめる）。
  - それ以外は新しい要求として §6.2 へ進む。
- 覚えておく応答の大きさには上限を置いてよい。上限を超えて覚えていない応答の要求を送り直されたら、実行せずに rejected
  result_lost。
- **覚えた表と最も新しい corr は成功した open のたびに捨てる**（end、lease の期限切れ、force では捨てない: 送り直された end には
  表から答える）。セッションが変わったときの exactly-once は約束しない。
- session_id 0 の要求は重複排除しない。

## 6. セッションと排他

### 6.1 ロック

- probe は**ロックを 1 つ**持つ。ロックを持つセッションだけが状態を変える要求を実行できる。
- host はセッションごとの session_id を、予測できない 32 bit の乱数で選ぶ。決まった値や 0 は使わない。session_id 0 の open は rejected malformed。probe は最後にロックを持った session_id を覚えている。
- lease は open で決まる。ロックを持つセッションの要求で §4.3 の順 3 を通ったものへの応答のたびに（rejected の応答も含む）、lease は数え直す（応答を送った時から lease_ms を数え直す）。期限を過ぎるとロックは空く
  （§9 の期限切れ）。**要求を実行している間は lease を数えない**（長い op が lease より長くてもセッションは切れない。長さの上限は
  describe の max_op_ms、§7.5）。

### 6.2 要求を受けたときの判定

probe は、ロックの有無、ロックを持つ、または最後に持った session_id（以下 S。§5.2 の表はこれに結びつく）、ロックが持たれている間の
owner を覚えている。§5.2 の表の判定（送り直し）はこの表より先。session_id 0 のロックなしの op の要求はここに来ない（§4.1）。

| ロック | 要求 | 結果 |
|---|---|---|
| 空き | open（session_id ≠ 0、force の有無を問わない） | ロックを立てる: S をこの id にし、lease を lease_ms から始め、owner は open の示すとおり |
| 空き | session_id ≠ 0 のほかの要求 | rejected no_session |
| S が持つ | session_id S の open（force の有無を問わない） | 送り直された open: この open の lease_ms で lease を始め直す。何も解放しない。購読は残し、通知の送り先はこの open の経路に替える |
| S が持つ | 別の id の open、force なし | rejected locked と残り時間（と owner） |
| S が持つ | 別の id の open、force あり | 奪う（§6.4）: S の資源を解放し（§9）、それから新しい id のロックを立てる |
| S が持つ | session_id S のほかの要求 | 処理する |
| S が持つ | 別の id のほかの要求 | rejected locked と残り時間（と owner） |

### 6.3 ロックの要る要求

状態を変える要求はすべてロックが要る（セッションの id を持つ、§4.1）。ロックなしで使えるのは、状態を変えない読むだけの要求に限る
（confirm、list、describe、clock、lock_state、インターフェースが定める読むだけの op）。インターフェース
がロックなしとする op は、状態を変えてはならない。

### 6.4 open、end、keepalive、force

- **open**（lease_ms、force。session_id は見出しのもの、§4.1）: ロックを取る。応答は lease_ms（probe が決めた値）と boot_id。**再開は
  無い**: 終わったセッションは、どの要求でも続かない。host は新しいセッションを開く。**成功した open のたびに
  §5.2 の表を捨てる**（rejected locked の open では捨てない。end、期限切れ、force では捨てない）。
- **lease_ms**: 0 は「probe の既定」。probe は 1000〜60000 ms の要求をそのまま受け、範囲の外は範囲の中に丸める（既定は
  probe が決める）。応答の lease_ms は lease_min_ms〜lease_max_ms（1000〜60000）の中にある。host は応答の lease_ms を正とする。
- **end**: ロックと、セッションが作ったものすべてを解放する（§9）。lease の期限切れと force も同じ。
- **keepalive**: lease を延ばすだけ。
- **lock_state**: ロックの有無と残り時間（ロックが空いていれば 0）。locked は「どのセッションであれロックが持たれている」（lock_state はセッションを
  持たずに送れるので、probe には誰が聞いたかは分からない。自分が持っているかは host が自分の状態で知る）。
- **owner**: open の TLV 0x01 owner（text、1〜32 byte、非 critical）で、host は持ち主の名前（例 "flash-tool pid 1234"）を
  付けてよい。probe は owner をロックを立てる open から取り、ロックが持たれている間覚え（持つ側の id の open では変えない）、ロックが
  終わると忘れる。ロックが持たれている間、lock_state の応答と rejected locked の payload の後ろに
  TLV 0x01 owner で付ける（owner が無ければ付けない）。owner は表示のためだけのもので、
  probe は解釈しない。（参考）owner は lock_state でどの host からも読めるので、host は秘密を入れない。
- **force**: 他のセッションがロックを持っていても奪う。probe は、前のセッションの資源をその終わりと同じく解放してから（§9）
  ロックを渡す。force は認証ではなく、取り違えを防ぐだけのものである。

### 6.5 boot_id

boot_id は probe の起動ごとに変わる値で、confirm（§7.1）、clock（§7.7）と open の応答に入る（同じ値）。probe は boot_id を、次の好ましい順に取る: ハードウェアの乱数源（32 bit）。不揮発の記憶に置き、起動ごとに変える値（数え上げ、または保存した乱数）。どちらも無ければ、起動ごとに変わる値を混ぜたもの（初期化していない RAM、ADC の入力の変換の雑音、最初の USB や UART の動きなど外からの出来事が来たときの、止まらないタイマーの数）。起動のコードの決まった場所で読んだタイマーは、そうした値ではない。最後の素しか持たない probe は boot_id を繰り返しうるし、host はその確率を受け入れる。0 も普通の値。host は、boot_id が変わった
とき、そのセッションの資源（インターフェースの資源）と、覚えた fn の対応、資源の番号、ストリームの位置がすべて無効になったとみなす。
ロックを持たない host（監視、発見）は confirm か clock で再起動を知る。

open の応答も boot_id を持つ: 知っていた boot_id と比べる host は、open のときに再起動を知り、覚えた fn の対応を使う前に list をやり直す（§7.2）。

## 7. 発見

### 7.1 confirm

```text
要求: "OEP?"、min_rev(u8)、max_rev(u8)、[TLV]
応答: "OEP!"、revision(u8)、flags(u8)、max_frame(u16)、window(u32)、max_inflight(u8)、boot_id(u32)、[TLV]
```

- TLV 0x01 transport（u8）: この confirm が来た経路の index（§7.5）。probe は必ず付ける。同じ接続で返す fn 0 の describe の entry を指す（中継のブローカーからは 0xFF、[経路](oep-transports.ja.md) §1）。

host は扱えるプロトコルの revision の範囲を送り、probe はその中で扱える最大の revision を返す。範囲に扱えるものが無ければ
rejected unsupported（下）。flags は予約（0）。max_frame は 64 以上（[経路](oep-transports.ja.md) §3）、window は max_frame 以上、max_inflight は 1 以上。host は flags のビットを無視する（予約、§2.4）。boot_id は §6.5（ロックなしで再起動を知るための置き場）。要求も応答も 64 byte に収まる
（[経路](oep-transports.ja.md) §3）。

- confirm の要求とその応答の固定部分、magic の `OEP?` / `OEP!`、confirm の前の規則（64 byte、[経路](oep-transports.ja.md) §1 のフレーム、[経路](oep-transports.ja.md) §3）は、どのプロトコルの revision でも同じ。
- probe が選んだ revision は、**その confirm が来た経路**の、両方向のすべての message に、その経路の次の confirm まで掛かる。経路ごとに違う revision で動いてよい。TCP では、経路は受けた接続ごとである（[経路](oep-transports.ja.md) §1）。
- ある経路で最初の confirm をした後、host はそこでの後の confirm（立て直し、探り直し）ではすべて、`min_rev = max_rev =` 使っている revision を送る。
- 範囲の中に扱える revision が無いとき: rejected unsupported で、payload は tag 0x00 の後に TLV 0x01 supported（min(u8)、max(u8): probe が扱える範囲）。`min_rev > max_rev` は rejected malformed。

### 7.2 list

```text
要求: first(u16)
応答: total(u16)、count(u8)、count × entry
entry: fn(u16)、instance(u16)、revision(u8)、flags(u8)、name_len(u8)、name
```

- probe のインターフェースを、first 番目から 1 フレームに入る分だけ返す。total はインターフェースの数。本体（fn 0）は名前を持たないので
  list に載らない: entry の fn は 0 でない。
- 名前は 1〜64 byte、使える文字は `a-z 0-9 - .`（§13）。
- instance は、同じ名前のインターフェースが複数あるときの見分け。**同じ (名前, revision) のインターフェースを fn の昇順に 0 から振る**。probe は同じ名前のインターフェースの
  順を firmware の版を越えて保つ（保存した設定が (name, instance, revision) でインターフェースを指すため）。flags は予約（0）。
- list の応答（どのインターフェースがあるか、その fn、instance、revision、名前）は、同じ boot_id の間変わらない。インターフェースが増えたり減ったりする probe は再起動する（新しい boot_id）。host は boot_id が同じ間、名前から fn への対応を覚えてよい。
- first が total 以上なら、応答は total と count 0。

### 7.3 describe

```text
要求: fn(u16)、first(u16)
応答: more(u8)、TLV の並び
```

fn の宣言を、first 番目の TLV から 1 フレームに入る分だけ返す。more = 1 なら続きがあり、host は first に受け取った TLV の数を
足してもう一度聞く。probe は TLV を 1 つずつ、自分のどの経路の max_frame にも収まる大きさにする（describe は経路によらない）。fn 0 は probe 全体の宣言。

**describe は宣言だけを返す**: 同じ boot_id の間、TLV の並びと値は変わらない（host は boot_id が同じ間 cache してよく、ページングは
途中で設定が変わっても崩れない）。変わるもの（接続、保存の有無、スロットの状態、空き容量）は、インターフェースが状態を返す op
（ロック不要）で出す。
- **ページングの終わり**（describe、state、connections、streams、segments、get に共通）: first が数以上なら count 0 と more 0 を
  返す。host は more = 0 で止める。list は more を持たず、total で終わりが分かる（§7.2）。

### 7.4 describe の共通タグ（0x01〜0x3F）

| tag | 名前 | 値 |
|---:|---|---|
| 0x01 | role_channels | role(u8)、base(u16)、bitmap。bit i が立っていれば channel base+i をその role に使える。同じ role を複数書いてよい（和集合） |
| 0x02 | max_clock_hz | u32 |
| 0x03 | max_length | u16。1 回に扱える最大の長さ。その op の要求と応答が probe のどの経路の max_frame にも収まる値で宣言する（describe は経路によらない。単位はインターフェースの文書が決める）。超えた要求は rejected unsupported |
| 0x05 | min_clock_hz | u32 |
| 0x06 | features | u32。op でない任意機能のビット: モード、format など（意味はインターフェースが決める）。任意の op は ops で宣言し、決して features では宣言しない |
| 0x08 | channel_group | group(u8)、n(u8)、n × (role(u8)、channel(u16))。この group を使うなら、各 role はここの channel に固定される。group が 1 つ以上ある機能では、選んだピンの組はどれか 1 つの group に完全に一致しなければならない |
| 0x09 | ops | base(u8)、bitmap。bit i が立っていれば op base + i を持つ（§1.2）。fn 0 を含むすべての fn の describe が付ける |

role の番号はインターフェースが定める。これらの値は固定の形で、足す情報は新しい tag にする（§2.3）。

- **ops の値**: base(u8) と、1 byte 以上の bitmap。`base + 8 × bitmap の byte 数 ≤ 256`（bitmap は op 0xFF を越えない）。
- **ops** の例: op 0x01〜0x08 をすべて持つ riscv-dm の fn は `09 02 00 01 FF` を送る。dmi、halt、resume だけ（0x01〜0x03）を持つものは `09 02 00 01 07` を送る。
  `F9 01`（op 0xFF を越える）は正しくない。host は op があるかを知るのに、features ではなく bitmap を読む。

- どのピンにも割り当てられる機能は role_channels に候補を並べ、ピンの組が決まっている機能は channel_group を組の数だけ書く。
  両方を書いた場合、選んだピンの組は channel_group のどれかに一致し、かつ role_channels の候補にも入っていなければならない。
  role_channels が縛るのは、それが挙げる role だけである（role_channels に無い role は channel_group だけで決まり、channel_group に
  無い role は role_channels だけで決まる）。
- role_channels と channel_group は、インターフェースがピンを選ぶどのやり方（ほかのインターフェースによる割り当て、要求の引数）でも、
  選べるピンの宣言である。role の番号と、どのやり方でピンを選ぶかは、インターフェースの文書が定める。

### 7.5 probe 全体の宣言（fn 0 の describe、0x40〜）

| tag | 名前 | 値 |
|---:|---|---|
| 0x40 | firmware | text |
| 0x41 | model | text。probe の種類の名前（任意。個体では変わらない） |
| 0x42 | unit_id | 個体の ID。**必須**。text で 1〜32 byte、使える文字は `a-z 0-9 -` だけ（チップの固有の番号を小文字の 16 進にしたもの、など）。同じ probe の経路を host がまとめるのに使うので、どの経路の describe でも同じ値を返す。USB の serial number と同じ（[経路](oep-transports.ja.md) §3）。host が probe を名指す値 |
| 0x43 | channels | u16。channel の数。channel の番号は 0〜channels − 1。channel を持つ probe は必ず付け、無ければ channel は 0 個 |
| 0x46 | label | channel(u16)、text。**firmware（配線の profile）が持つ固定の** channel の名前（NRST など）。設定で付けた名前は、その設定を定めるインターフェースの op で読む（describe は宣言だけ、§7.3） |
| 0x49 | transport | index(u8)、kind(u8)、interface(u8): USB CDC（kind 2）は CDC の通信の interface の bInterfaceNumber（その機能の最初の interface）。内蔵の USB シリアル（kind 3）は、ハードウェアが見せるその同じ番号、probe が知れなければ 0xFF。vendor bulk と HID はその interface の番号。UART bridge（kind 1）と TCP は 0xFF。probe の経路ごとに 1 つ。**必須** |
| 0x4C | chip | text。probe の MCU の型番とリビジョン（任意） |
| 0x4D | max_op_ms | u32。probe が 1 つの要求にかける最長の時間。**必須**。1〜600000（`max_op_ms_max`、10 分）。引数で時間が決まる op（§4.4）は、その時間がこれを超えれば rejected unsupported（どの op かはインターフェースの文書が定める）。実行中は lease を数えない（§6.1）。値は probe が決める。host は §4.4 のとおり待つ |

- transport の kind: 1 UART bridge、2 USB CDC、3 内蔵の USB シリアル（MCU のハードウェアが持つ USB のシリアルの口で、serial number を含む USB の記述子を probe が選べないもの）、4 vendor bulk、5 HID、6 TCP（registry の `transport_kind`）。
  1〜3 がシリアルの口（[経路](oep-transports.ja.md) §4）。index は probe の中で経路を指す番号（0 から）で、probe の設定がシリアルの口を指すときもこの番号を
  使う。probe の起動の間は変わらない。
- **経路の index の不変性**: 経路は、同じ model の firmware の版を越えて index を保つ。経路を足す firmware は、それまで使っていない index を付け、外した index は使い直さない。
- **unit_id の一意性**: unit_id は個体ごとに違う値にする（チップの固有の番号、など）。保存はあるが固有の番号の無い probe は、最初の起動で乱数から unit_id を作って保存する。
  どちらも無い probe は `x-` で始まる unit_id を使う（一意ではない）。host は `x-` で始まる unit_id で経路をまとめず、それで probe を名指さず、セッションを越えて持つもの（たとえば口のリンクの速さの記録）のキーにしない。同じ口のほかの個体が何も引き継がないためである。
- **unit_id の不変性**: unit_id は個体の値（チップの固有の番号、保存した乱数。`x-` の unit_id だけは例外）だけから作り、firmware の版、profile、ビルド、経路の種類で
  変えない。接尾辞を足さない。host と OS は unit_id（= USB の serial number、[経路](oep-transports.ja.md) §3）で probe を覚える。

### 7.7 clock

```text
要求: —
応答: boot_id(u32)、uptime_ns(u64)、[TLV]
```

- clock は probe の今の時刻を返す。boot_id は §6.5 の値（confirm と open の応答と同じ）、uptime_ns は §2.6a の時計の値。
- clock はロックの要らない読むだけの op（§6.3）である。セッションが無くても送れる: session_id 0 の clock は、セッションの確かめなしに処理し、
  どのセッション、ロック、lease にも触れない（§4.1）。
- uptime_ns は、probe がこの clock の要求を受けてから応答を送るまでの間に読んだ、自分の時計の値である（前に読んだ値や推定した値は入れない）。

## 8. channel の空きの状態

channel（probe のピン、§1）は、インターフェースがそれを取っていないとき、**空きの状態**にある。ピンを取るのは、インターフェースの文書が
定める操作（ピンの割り当て、線の接続、保存した設定など）である。

- **空きの状態**: 保存した設定（インターフェースが定める）がそのピンの空きの状態（idle）を決めていればその状態（出力 low / high ならその level と、
  idle が決める強さで駆動し、Hi-Z にしない）、決めていなければ **Hi-Z（入力、プルなし）**。
- 解いたピンは、どの道で解いても（インターフェースが定める解く操作、§9 の lease の期限切れと force での後始末）、空きの状態にする。
  インターフェースは、解いた後もピンを自分の駆動のまま残してはならない（空きの状態が出力なら、その駆動は保存した設定の idle のもの）。
- **起動時**、probe は最初の要求に答える前に、自分で使う channel を除くすべての channel を空きの状態にする。それまでピンは MCU のリセットの
  状態である（参考: 誤った水準が害になる線には外付けのプルが要る）。
- **ピンを取ってもピンの電気の状態は変わらない。** ピンは、それを取ったインターフェースが使い始めるまで空きの状態を保つ。どの操作で使い始めるかは、
  各インターフェースの文書が定める。ピンを読むだけのインターフェースは決して変えない: 出力を止めず、ほかの機能や出力の idle が駆動するピンのプルや
  向きも変えない。
- idle が出力（保存した設定の出力の空きの状態）の channel を取る要求をインターフェースの文書が断るとき、その断りは unavailable（cause 5）である。

### 8.1 資源の取り合い

- probe の資源（ピン、ペリフェラル、DMA、タイマーなど）を取るものはすべて、取る前に、今あるピンの割り当て、connection、保存した設定から
  入れた資源とぶつからないか確かめる。ぶつかれば rejected unavailable で断り、**今ある機能の状態は何も変えない**。
  取るもの: インターフェースが定める、ピンや資源を取る操作（ピンの割り当て、線の接続、設定、資源を作る操作）。

## 9. 資源の寿命（一般の規則）

**セッションが作ったものはすべて、そのロックが終わるときに解放する。何で終わっても同じ**（end、lease の期限切れ、force で奪われる）。次の
セッションには何も渡さない。セッションをまたいで残るのは、インターフェースが定める保存した設定から入れたもので、どの host からも読める。

| 出来事 | セッションが作った資源 | 購読（§11） | §5.2 の表 | 後の同じ ID の要求 |
|---|---|---|---|---|
| end | 解放する | 終わる | 残る（送り直された end にはここから答える） | ロックが空いている間は no_session、別のセッションが持つ間は locked |
| lease の期限切れ | 解放する | 終わる | 残る | end の後と同じ |
| force で奪われる | 解放する | 終わる | 捨てる（奪った open が捨てる） | 奪った側が持つ間は locked、その後は no_session |
| 同じ ID の open（保持中） | 残る | 残る（送り先はその経路） | 捨てる | — |
| probe の再起動（インターフェースの op による再起動を含む） | 無くなる（boot_id が変わる） | 無くなる | 無くなる | no_session |

- セッションとほかのもの（保存した設定など）が共有する資源では、セッションの持ち分だけが外れ、使う者が残らなくなったときに、
  インターフェースの文書のとおり閉じる。
- 資源が閉じた後もインターフェースが読めるまま残すもの（どれがそうかはインターフェースの文書が定める）は、セッションの資源ではない。
- インターフェースが作る資源（debug の connection、ストリームなど）の寿命は、インターフェースの文書が、この規則の上で定める
  （誰が使っているか、いつ閉じるか）。
- 保存した設定（インターフェースが定める）から入れた資源は、セッションの資源ではない。
- **資源の番号は u16 で、probe で 1 つの空間**（connection、ストリームなど、インターフェースが番号で指すものすべて。別のインター
  フェースの資源を渡されたら rejected unavailable cause 6）。新しい資源を作るたびに前の番号から 1 進め（65535 の次は 1、§2.6）、使用中の番号は
  飛ばす。閉じた資源の番号を使った要求は rejected no_connection。一周の後は古い番号が
  別の資源を指しうる: host は no_connection を受けた番号を捨て、長く持つ番号は一覧の op（connections、streams）で確かめる。

## 11. 通知

probe から送る通知の仕組み。通知を送り出すかはインターフェースが決める: 送り出すインターフェースは、その fn の ops に subscribe と
unsubscribe（§11.3）を立てる。何が届くか（出来事の kind、データの意味）はそのインターフェースの文書が決める。host は購読しなければ
何も受け取らない。§11.1 はすべての host に、§11.3 と §11.4 は通知を送り出すインターフェースを持つ probe に掛かる。

### 11.1 host の義務（全 host）

- 受け取ったフレームを role で振り分ける。corr で照合するのは role 0x02 だけ（0x05 / 0x06 のバイト 1〜2 は fn）。
- 知らない role のフレームと、待っていない corr の応答は捨てる（シリアルの口では、生のバイトが偶然フレームに見えたものもこれで
  捨てる、[経路](oep-transports.ja.md) §4）。
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
- fn 0 は通知を送らない。

### 11.3 購読

subscribe と unsubscribe は、通知を送り出すインターフェース自身の op である。**op の番号はどのインターフェースでも同じで、すべての
インターフェースの op の空間で予約する**: 0x30 subscribe、0x32 unsubscribe。インターフェースはこの 2 つの番号をほかの op に使わない。
要求は購読する相手の fn を持たない（その fn 自身への要求で、見出しの fn が相手である）。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x30 | subscribe | min_bytes(u16)、max_delay_ms(u32)、[TLV] | — | 必要 |
| 0x32 | unsubscribe | [TLV] | — | 必要 |

- 通知を送り出すインターフェースは、subscribe と unsubscribe を両方とも持ち、ops に立てる（必須か任意かはそのインターフェースの文書が
  決める）。
  （参考）中継のブローカーは、どの fn への要求でも、この番号で購読を見分けて断れる。
- **購読はロックの持ち主だけができ、ロックと一緒に終わる**（end、期限切れ、force で奪われたとき）。読むだけの監視は、シリアルの
  口の生のバイト（[経路](oep-transports.ja.md) §4）で行う。
- 購読の無い fn の unsubscribe は何もせず成功。
- 同じ fn をもう一度 subscribe したら、前の購読を原子的に置き換える（送る条件、送り先の経路、seq を 0 から）。1 つの fn の購読は
  1 つだけ。
- **まとめて送る条件はデータ（role 0x06）だけに掛かる**: min_bytes バイトたまるか、最初のバイトから max_delay_ms 経ったら送る。0 は
  その条件を使わない。両方 0 ならあるだけすぐ送る。
- **出来事（role 0x05）はまとめない**: 生まれた出来事は、その前に送る応答（§11.4 の 1）を送り終えたらすぐ送る。min_bytes と max_delay_ms は
  出来事に掛からず、出来事の byte は min_bytes に数えない。

### 11.4 probe の義務（送り出す probe）

1. **応答を先に送る。** 届いている要求をすべて処理してから、通知を送る。
2. **送りかけの通知を小さく保つ。** 経路の送信バッファに、送りかけの通知を max_frame × 2 byte を超えて
   ためず、書き込みで待たない。入らない通知は probe の中で捨てる（seq の抜けで分かる、§11.3）。
3. 通知は、その fn の subscribe が来た経路に送る。

## 12. 本体（fn 0）の操作一覧

| op | 名前 | 要求 | 応答 | ロック | 要否 |
|---:|---|---|---|---|---|
| 0x01 | confirm | §7.1 | §7.1 | 不要 | 必須 |
| 0x02 | list | §7.2 | §7.2 | 不要 | 必須 |
| 0x03 | describe | §7.3 | §7.3 | 不要 | 必須 |
| 0x04 | clock | — | boot_id(u32)、uptime_ns(u64)、[TLV]（§7.7） | 不要 | 必須 |
| 0x10 | open | lease_ms(u32)、force(u8)、[TLV owner]（session_id は見出しのもの） | lease_ms(u32)、boot_id(u32)、[TLV] | open がロックを取る | 必須 |
| 0x11 | end | — | — | 必要 | 必須 |
| 0x12 | keepalive | — | — | 必要 | 必須 |
| 0x13 | lock_state | — | locked(u8)、remaining_ms(u32)、[TLV owner] | 不要 | 必須 |


## 13. 拡張の規則（インターフェースの書き方）

どのインターフェースも、次の規則で定義する。

1. **名前**: インターフェースの名前は、定義する者の逆 DNS の名前（`io.github.<owner>.<name>` など）である。OEP を伸ばす者は誰でもこれを使う。
   例外は project 自身のインターフェースだけで、逆 DNS の名前の代わりに、予約した短い接頭辞 `oep.` を使う: `oep.<層>.<名前>`、層は `probe`（probe 自身）、
   `wire`（線と connection）、`target`（connection の上の target の操作）、`fixture`（治具の機能）。この短い名前のほかに、それらに特別なものは無い。
   `oep.` で始まる名前は project だけが付ける。名前は host が何に使うかで切る（probe のペリフェラルの名前にしない）。汎用か 1 つの系統のためのものかは
   名前に入れない（規則 8）。**1〜64 byte、使える文字は `a-z 0-9 - .`**（registry の `limits`）。
   名前の label はそれぞれ `a-z 0-9 -` の 1 文字以上で、`-` で始まらず `-` で終わらない。名前は label を 2 つ以上持つ。
2. **定義が決めるもの**: インターフェースの文書はどれも、次のチェックリストを埋める。
   - 名前と revision。
   - op の表: 番号、要求、応答、ロックの要否、どの op が必須でどれが任意か（任意の op は ops で宣言する、§1.2）。
   - 各 op の要求と応答の TLV（その op の文脈の tag の空間）。
   - 各 op の completed success、completed failed、completed partial の payload（§4.2）。
   - インターフェース自身の status の値（0x40〜0x7F）と reject reason（0x40〜0x7F）。
   - describe のインターフェース固有のタグ（0x40〜0x7E）と、ピンの role の番号。
   - どの target の系統のためのものか（規則 8。どの系統にも使うものはそう書く）。
   - インターフェースが作る資源とその寿命（§9 の上で）。
   - 通知を送り出すか。送り出すなら subscribe / unsubscribe（§11.3）が必須か任意か、出来事の kind（0x01〜0x7F）とその payload、
     通知のデータの payload の形。
   - 読む側が、応答の enum の知らない値と知らない flags をどう扱うか（§2.4、§13.1）。
   - 頼る外部の仕様と、その版と、使う部分（「参照する仕様」の節）。
3. **形の規則**: §2.3 のとおり（固定の形、足すものは TLV だけ、可変の並びの前に数を置き要素に長さを置かない、省略できるフィールドを置かない、安全の引数は critical）。
4. **失敗**: 受け付けなかったものは rejected、受け付けて失敗したものは completed failed / partial（§4.2）。
5. **ロックなしの op は状態を変えない**（§6.3）。
6. **版**: §2.7。
7. **ほかの者の名前のインターフェースに、op、tag、値を足さない。** インターフェースを伸ばすのはその名前を持つ者だけで（`oep.` の名前なら project）、
   ほかの者は、自分の情報を自分の名前のインターフェースに置く（別の fn として出す）。
8. **特定のチップ向けの手順は、汎用のインターフェースに入れない。** チップや系統に特化した手順（flash の書き方、リセットのタイミングなど。
   probe がやらないとタイミングが間に合わないもの）は、そのための別のインターフェースに置く。
   どの系統のためのものかは名前に入れず、インターフェースの文書の冒頭と、名前が `oep.` で始まるものでは registry（インターフェースの `target`）に書く
   （名前は永続する識別子で、どれだけ広く使われるかは時とともに変わるため）。**どの系統にも使うインターフェースには、特定のチップ向けの処理を
   入れない。** 特化したものは移植性が下がる（それを使う host はその機能を持つ probe に縛られ、新しいチップへの対応に probe の firmware の
   更新が要る）。汎用の手順（生の転送と host の知識）で済むものは、そちらで組む。

### 13.1 伸び方

凍結の後、OEP はこれらだけで伸ばす:

1. **新しい TLV**: 要求、応答、出来事、データ、describe の中に。または probe.config の新しい項目の tag。
2. **新しい任意の op**（ops で宣言する、§1.2）か**新しい出来事の kind**。
3. **予約の空間の新しい値**: 古い probe が unsupported で断る要求の値（§2.5）、または下の条件のもとでの
   応答の値。
4. 新しい意味には**新しいインターフェースの名前**、変わった固定の形には**新しい revision**（§2.7）。

並びの要素を伸ばすはずの情報は、繰り返す応答の TLV に入れ、要素の index を持たせる（gpio set の drive の TLV が要素の index を
持つように）。

**値の幅**: ハードウェアの性質で決まる値（数、速さ、しきい値、容量、時間）は u32 以上にする。u8 / u16 は、プロトコルの都合で上限が
決まるもの（1 フレームの中の数、fn、資源の番号、インターフェースの中の番号）だけに使う。ビットの集合は u32 か `base + bitmap`。

**応答に足す値。** 応答、出来事、データが運ぶ enum の値やビットの集合のビットは、次の 3 つがすべて成り立つときだけ、revision を変えずに足してよい:

1. どのフィールドの有無、長さ、位置も、その値によらない。
2. §2.4 の扱いが安全である（知らない outcome、status、reason は失敗、ほかは「知らない値」、予約のビットは無視）。
3. 意味がその値によるフィールドはどれも、その値を知らない読む側が無視するか、生のまま見せると定めてある。

そうでなければ、足すものは新しい TLV、新しい revision、新しいインターフェースにする。revision 1 の応答の enum とビットの集合は、どれも 3 つの条件を満たす。

## 14. 規範ではない文書（ガイド）

これらは規則を足さない。

- [はじめに](getting-started.ja.md): いちばん小さい probe と host を、byte つきで。
- [host 開発ガイド](host-development-guide.ja.md)、[probe 開発ガイド](probe-development-guide.ja.md): 実装の実務。
- [適合](conformance.ja.md): probe と host のチェックリスト。
- [安全とセキュリティ](security.ja.md)、[用語集](glossary.ja.md)、[版と安定性](versioning.ja.md)。
