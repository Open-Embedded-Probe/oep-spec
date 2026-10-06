# Open Embedded Probe — プロトコル本体（OEP core）v1

[English](oep-core.md)

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](versioning.ja.md) §6）。この文書は OEP のプロトコル本体だけを定める。標準インターフェース
（線、デバッグ、コンソール、fixture、キャプチャ、probe の設定）はそれぞれの文書が定める（§14）。この文書はそれだけで完結する: 読む人が規則の
理由を必要とする所では、理由を規則と一緒に書く。ガイド（§15）は実務を足すもので、規則は足さない。この文書と、規範ではない文書が食い違えば、この文書が正しい。

番号（op、tag、reject reason、status、enum）の唯一の定義は `registry/oep-v1.toml` で、この文書の表はその写しである。
食い違えば registry が正しく、文書を直す。
凍結の後、registry のキー（したがって生成した識別子）は改名せず、新しいキーを足す。REGISTRY_HASH は生成したコードが registry と合っているかを示すだけで、線の上の互換については何も言わない。仕様のものでない値（参考の firmware の max_op_ms）は、凍結の外の `[reference]` の表に置く。

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
   `oep.` で、番号が project の registry にあり、project が registry と適合の資料（[`tests/vectors/`](../tests/vectors/) の試験のベクタ。`tools/oepvectors1.py` がこの文書から計算する。そして host が試すための偽の probe）を保守することだけである。ベクタと文書が食い違うときは文書が正しく、ベクタを直す。probe と host が適合するために何をするか、それをどう確かめるかは [適合](conformance.ja.md)（ガイド）に並べてある。
5. インターフェースどうしの関係（あるインターフェースが別のインターフェースの資源を使う、など）は、関係するインターフェースの
   文書が定める。
6. 版は層ごとに独立する（§2.7）。

OEP の外: probe 自身の firmware の更新（DFU、Mass Storage など）、USB の記述子の細部。

**外部の仕様**: OEP のプロトコルは、これらの文書だけで定まる。target、バス、経路を動かすには、それぞれの文書が「参照する仕様」の節に並べる
外部の仕様も要る（経路は §16）。

**言語**: 凍結までは、日本語の文（`.ja.md`）が作業の文で、規則はそこで決める。英語の文書は凍結のときに日本語から作り直し、そのときから英語の文が規範として正しくなる。それまでの英語の文書は古いことがある。

## 1. 用語

| 用語 | 意味 |
|---|---|
| probe | OEP を話す装置（デバッガ、治具、ロジアナなど） |
| host | probe を使うソフトウェア |
| target | probe がつながる相手（開発中のマイコンなど） |
| 経路（transport） | OEP のフレームを運ぶもの（UART bridge、USB CDC、内蔵の USB シリアル、USB の vendor bulk、HID、TCP） |
| シリアルの口（serial port） | 経路のうち OS からシリアルデバイスに見えるもの（UART bridge、USB CDC、内蔵の USB シリアル）。OEP と生のバイトを共用する（§3.4） |
| インターフェース | probe が名前で出す機能。list で見つけ、fn で呼ぶ |
| fn | そのセッションの間、インターフェースを指す番号（u16）。fn 0 は `oep.core` |
| op | インターフェースの中の操作の番号（u8） |
| セッション | ロックを持って状態を変える権利。host が選ぶ session_id（u32）で識別する |
| lease | ロックの期限。keepalive などの要求で延びる |
| channel | probe のピンの番号（u16） |
| plan | どのインターフェースのどの役（role）に、どの channel を使うかの割り当て |

### 1.1 規範の語

大文字の MUST、MUST NOT、SHOULD、SHOULD NOT、MAY は RFC 2119 と RFC 8174 のとおりに使う。probe や host がすることを現在形で述べた文（「probe は〜を返す」）は要件（MUST）である。「できれば」は SHOULD。（参考）と記した文、例、注は規範ではない。日本語の訳では、「〜する／〜しない」が MUST / MUST NOT、「〜してよい」が MAY、「できれば〜する」が SHOULD にあたる。

### 1.2 適合

probe が実装しなければならない（MUST）もの:
- §3 の経路の少なくとも 1 つと、そのフレーム;
- §4〜§6;
- fn 0 の confirm、list、describe、open、end、keepalive、lock_state、subscribe と unsubscribe;
- fn 0 の describe の unit_id、transport、max_op_ms、discoverable（§7.5。プロジェクトの USB の VID:PID で列挙しない probe は 0）;
- list に載せるすべての fn（fn 0 を含む）の describe の、共通の tag ops（§7.4）。

plan_apply と plan_release は、どれかのインターフェースが plan の role（インターフェースの文書が plan を通して割り当てる role、§8。wire の attach が引数で選ぶピンの role は plan の role ではない）を持つときに要る。plan の role を持つインターフェースが 1 つも無い probe は、それらを持たない。任意: fn 0 のハートビート以外の通知、すべてのインターフェース（その中に、線の試験と port_speed を持つ `oep.link`、[リンク](oep-if-link.ja.md)）。

**必ず持つ op と任意の op。** インターフェースの op の表（fn 0 は §12、ほかはそのインターフェースの文書の op の表）の op は、そのインターフェースを list に載せる probe が必ず持つ。文書が任意と書いた op は除く。**すべての fn は、持つ op を 1 か所で宣言する: describe の共通の tag ops（0x09、§7.4）。** 必須の op はすべてそこに立てる。任意の op は、probe がそれを持つときに限り立てる。実験用の op（0xF0〜0xFF、§2.5）は決して立てない。

probe は、その fn の ops が立てない op（インターフェースが定義しない op、または持たない任意の op）の要求に rejected unknown_operation で答える（§4.3 順 1）。持つ op に、宣言しない任意の機能（mode、format、値、critical の TLV、ピンの組み合わせ）を求める要求には rejected unsupported で答える（§4.3 順 6）。

host がしなければならない（MUST）こと: 知らない TLV と tag を読み飛ばす（§2.3、§2.4）。§3.2 と §3.3 の探りの規則に従う。§4.4 のとおり待つ。§5.2 のとおり送り直す。§11.1 のとおりフレームを振り分ける。

## 2. 共通の規則

### 2.1 byte order と文字列

数値はすべて little endian。文字列は UTF-8 のバイト列で、長さは別に持つ（終端の 0 は付けない）。
**bitmap** は byte の並びで、bit i は byte ⌊i/8⌋ の bit (i mod 8) である（bit 0 は最下位の bit）。bitmap は、それを含む値の終わりまで続く。

- 真偽値の u8 は 0（偽）か 1（真）。要求の中でほかの値なら rejected malformed。応答では、host は 0 でない値をすべて真と読む。
- 要求の中の text が正しい UTF-8 でないか、C0 の制御文字（0x00〜0x1F）か 0x7F を含めば rejected malformed。host は、応答の text を見せる前に、そうした文字と正しくない UTF-8 を置き換える。

### 2.2 TLV

```text
tag(u8) | len(u16) | value(len byte)
```

- **すべての TLV が 1 つの形**で、値の長さ（0〜65535 byte）によらない。len がそれを含む message の終わりを越える TLV は、
  要求では malformed（§4.3 順 5）。応答、出来事、データの中にあれば、その応答、出来事、データは壊れている。
- **tag の番号は下位 7 bit（0x01〜0x7E）。** bit 7 は critical の印。要求の中でだけ使い、番号には含めない: 0x10 と 0x90 は同じ TLV を、印なしと印ありで送ったもの。応答、出来事、データでは bit 7 は 0 で、そこで bit 7 の立った TLV に会った読む側は、知らない tag として読み飛ばす。tag 0x00 は予約（TLV には使わない。rejected unsupported の payload の印、§4.3）、0x7F は応答の ignored 専用、0xFF は無効。
- ignored は tag の番号（bit 7 を落としたもの）を並べる。rejected unsupported の payload は、受け取ったままの tag の byte（bit 7 を含む）を持つ。
- tag の空間は **(fn, op) の文脈ごと**（同じ値でも文脈が違えば別物）。
- 同じ tag の繰り返しは、繰り返すと定義が言う tag で、並びを表す（§2.3）。

### 2.3 固定の形と TLV

- **容器は自分の長さを知る**: フレーム、TLV、並び、バイト列（data）のどれも、読む側が要求や外の知識なしに終わりが分かる。
  可変の部分（並び、バイト列、文字列）には前に数か長さを置く。
- **固定の形はどれも (名前, revision) で決まる**（§2.7）: 要求、応答、出来事、データの payload の固定部分、TLV の値、並びの
  要素、probe.config の項目。固定の形は後ろに伸ばさない。その中の可変の部分（名前、錠の値、要素の中の一覧）は前に数か長さを
  置くので、固定の形も自分の長さを知る。
- **並び**: `count、count × 要素`。要求でも応答でも同じ。要素は自分の長さを持たない。要素の形は revision で決まり、読む側は
  フィールドを 1 つずつ読む。
- **応答**: 各 op の応答の固定部分（と、前に数か長さを置いた並び）の後ろは TLV の並び。後から足すものはすべてここに TLV で足す。
  host は知らない tag を読み飛ばす。固定部分より短い応答は壊れた応答として扱う。応答、出来事、データの TLV で、値が定義の
  決める長さ（可変の部分を持つ値なら、その数と長さが決める長さ）を持たないものは壊れている: host はそれを使わない。
  **応答の固定部分の形は (op, resolution, outcome) ごとに
  op の定義が決める**（成功と失敗で形が違ってよい。インターフェースの共通部品 §3）。
- **出来事とデータ**（§11.2）も応答と同じ: 固定部分の後ろは TLV の並び。
- **要求**: 要求の後ろに足せるのは TLV の並びだけ。host は、その項目が効かなければ要求に意味がないときに **critical の bit を
  付ける**（効かなくても構わない項目は付けずに送ってよい）。インターフェースの定義が critical で送ると決めた TLV（速さの上限、
  pins など、安全のための項目）は必ず付ける。**インターフェースの定義は、bit 7 が立っていてもいなくても probe が critical として扱う TLV を決めることもできる**
  （[捕捉](oep-if-capture.ja.md) §3.3、§4.1）。そうした TLV を実装する probe は、critical の TLV の規則をすべてそれに当てはめる: 扱えない値も、知っている長さより
  長い値も rejected unsupported（受け取ったままの tag）で断り、その TLV を無視することはない。その tag を実装しない probe は、受け取った bit のとおり知らない TLV として扱う。probe は、知らない critical の
  TLV があれば rejected unsupported（payload に受け取ったままの tag）で断る。知らない非 critical の TLV は無視し、応答の
  後ろに ignored（tag 0x7F、下）を付ける。結果が completed なら、op の status が失敗でも付ける。
- ignored は、無視した TLV の番号（bit 7 を落としたもの）を**要求に現れた順に**、無視した TLV 1 つにつき 1 つ、多くても 16 個（`ignored_max_entries`）並べる。無視した TLV が 16 を超えたら、probe は最初の 15 個を並べ、16 個目に **0x00** を置く（「ほかにも無視した」。0x00 は tag にならない、§2.2）。0x00 を見た host は、自分の要求の TLV のうち並んでいないものをすべて、無視されたかもしれないものとして扱う。
- probe は、ignored の要る応答から ignored を省かない。応答に入れる可変のデータ（data、並び）の量を決めるときは、ignored の場所（多くても 19 byte）を残す。固定部分だけでも場所が足りなければ、入るだけの数を並べ、最後を 0x00 にする。`0x7F 0x01 0x00 0x00`（4 byte）は必ず入る。
- 繰り返すと定義が言わない tag は、1 つの要求に高々 1 回しか現れない。2 つ以上あれば、critical かどうかによらず rejected malformed。応答では、host は最初のものを使う。
- この probe が実装する TLV の値が定義より短いか、定義が除く値を持てば、critical かどうかによらず要求を rejected malformed にする。定義の中の値でこの probe が扱えないものだけが unsupported（critical）か ignored（critical でない）になる。probe が実装しない TLV は、長さによらず、その probe にとって知らない TLV である。
- **要求の TLV の値は後ろに伸ばさない。** 新しいフィールドは新しい tag に置く。実装する要求の TLV で、値が知っている長さより長いものに会った probe は、critical なら unsupported（受け取ったままのその tag）で断り、そうでなければ TLV 全体を無視して ignored に載せる。
- 要求の中に tag 0x7F か 0xFF があれば rejected malformed。固定部分より短い要求は rejected malformed。
- **可変の並びは前に数を置く**（後ろに TLV を付けられるように）。
- 固定部分に省略できるフィールドを置かない（省略したい値は TLV にする）。
- host が安全のために足す引数（速さの上限など）は critical にする。

**OEP の伸び方**（凍結後はこれらだけで伸ばす）:

1. **新しい TLV**: 要求、応答、出来事、データ、describe の中に。または probe.config の新しい項目の tag。
2. **新しい任意の op**（ops で宣言する、§1.2）か**新しい出来事の kind**。
3. **予約の空間の新しい値**: 古い probe が unsupported で断る要求の値（§4.3 順 6）、または §2.5 の条件のもとでの
   応答の値。
4. 新しい意味には**新しいインターフェースの名前**、変わった固定の形には**新しい revision**（§2.7）。

並びの要素を伸ばすはずの情報は、繰り返す応答の TLV に入れ、要素の index を持たせる（gpio set の drive の TLV が要素の index を
持つように）。

- **値の幅**: ハードウェアの性質で決まる値（数、速さ、しきい値、容量、時間）は u32 以上にする。u8 / u16 は、プロトコルの都合で上限が
  決まるもの（1 フレームの中の数、fn、資源の番号、インターフェースの中の番号）だけに使う。ビットの集合は u32 か `base + bitmap`。

### 2.4 知らない値

- 知らない role のフレームは捨てる。
- probe は、role が要求の role（0x01）でない message と、見出し（10 byte）より短い要求を、答えずに捨てる。host は、role が要求の role の message を捨てる。
- host は、5 byte より短い応答と、見出しより短い出来事やデータのフレームを、壊れたフレームとして扱う（§5.1、§5.2）。
- 知らない resolution、completed の知らない outcome は失敗として扱う。
- インターフェースの status や reason の知らない値は失敗として扱う。
- 知らない出来事の kind は捨てる（seq は数える）。
- host は応答の flags の予約のビットを無視する。応答の enum の知らない値で失敗を知らせないもの（cause、holder_kind、scan の entry の kind）は、知らない値として見せる。status と reason の知らない値は失敗のまま。
- これらの扱いが安全なのは、応答に足す値に §2.5 の条件があるからである。

### 2.5 番号の空間

| 空間 | 範囲 |
|---|---|
| role | 0x01 要求、0x02 応答、0x05 出来事、0x06 データ。0x00、0x03、0x04 と 0x07〜0xFF は予約 |
| core（fn 0）の op | 0x01〜0x0F 発見と plan、0x10〜0x1F セッション、0x20〜0x2F 予約（長い操作、§10）、0x30〜0x3F 通知、0x40〜0xEF 予約、0xF0〜0xFF 実験用（出荷する probe は使わない） |
| インターフェースの op | 0x01〜0xEF はインターフェースの定義が決める。0xF0〜0xFF は実験用 |
| reject reason | 0x01〜0x3F 本体（全インターフェース共通）、0x40〜0x7F インターフェース、0x80〜0xFF 予約 |
| outcome | 0 success、1 failed、2 partial。ほかは予約 |
| 出来事の kind | fn ごとの空間。0x01〜0x7F はインターフェースが決める（fn 0 は本体）、0x80〜0xFF は予約 |
| TLV の tag | (fn, op) の文脈ごと。番号は下位 7 bit で、bit 7 は critical の印（§2.2）。0x00、0x7F、0xFF は全文脈で予約 |
| describe の tag | 0x01〜0x3E 本体の共通タグ（§7.4）、0x3F 予約（応答のメタ情報）、0x40〜0x7F インターフェース |
| 資源の番号 | u16、probe で 1 つの空間（§9） |

定義が別に言わない限り、enum の使っていない値と要求の予約のビットは、どれも後から定義されうる（§2.7）。probe は §4.3 の順 6 でそれらを断る。

**応答に足す値。** 応答、出来事、データが運ぶ enum の値やビットの集合のビットは、次の 3 つがすべて成り立つときだけ、revision を変えずに足してよい:

1. どのフィールドの有無、長さ、位置も、その値によらない。
2. §2.4 の扱いが安全である（知らない outcome、status、reason は失敗、ほかは「知らない値」、予約のビットは無視）。
3. 意味がその値によるフィールドはどれも、その値を知らない読む側が無視するか、生のまま見せると定めてある。

そうでなければ、足すものは新しい TLV、新しい revision、新しいインターフェースにする。revision 1 の応答の enum とビットの集合は、どれも 3 つの条件を満たす。

**実験用の値**: 定義が別に言わないすべての u8 の enum で、0xF0〜0xFE は実験用である。何かを試す間は誰が使ってもよい。出荷する probe と公開した host は使わず、registry に載せることもない。（tag の番号には実験用の範囲は無い。独自の情報は独自のインターフェースに置く、§13 の規則 7。）

### 2.6 一周する値

seq（u16）と、インターフェースが定める通し番号や時刻のうち一周すると定めたものは、差を同じ幅 w の符号付きとして
比べる（serial number arithmetic）。そうした 1 つの空間の値のうち、probe が同時に持つもの（まだ読めるマーク、まだ解放しない区画、まだ読まれない置き場）では、
いちばん新しいものからいちばん古いものを引いた差は 2^(w−2)（幅の 4 分の 1）未満。一周させない値は u64 にする
（標準インターフェースのストリームの位置、時刻など）。資源の番号（§9）は等しいかどうかだけを比べ、使い回しは §9 で決まる。

### 2.6a 時計

probe の時計は 1 つ: **起動からの ns（u64）**。時計は、同じ boot_id の間、減らず、一周しない。ハードウェアの数え器が 64 bit より狭い probe は、ソフトウェアで広げ（一周の数を数える）、一周を見逃さないだけの頻度で読む。時刻を返す所（マーク、区画、ハートビート、状態の「最後に試した時刻」）はすべてこの値で、
「まだ無い」は全ビット 1。継続時間（timeout_ms、hold_ms、wait_us、elapsed_us など）はそれぞれの単位のままでよい。

### 2.7 名前と revision

- インターフェースのどの**固定の形**（§2.3: 固定部分、TLV の値、並びの要素、項目）も、形と意味は **(名前, revision) で決まる**（list の revision、u8）。
- **revision を上げるのは、固定の形の意味か長さを変えるときだけ**。host は知らない revision のインターフェースを使わない。
- 固定の形を変えずに、任意の request TLV、response TLV、任意の op、任意の event を足すときは、revision を変えない。知らない
  host はそれらを使わない。任意の op の有無は ops（§1.2、§7.4）で、op でない任意の機能（モード、format など）の有無は describe（features など）で宣言する。
- 固定部分を変える revision を入れる probe は、できれば古い revision も別の fn として同時に出す。
- 名前を変えるのは、インターフェースの意味が変わるときだけ。
- 本体の形を変えるときは、プロトコルの revision（confirm）を上げる。この文書の形は revision 1。

## 3. 経路とフレーム

### 3.1 フレーム

経路の種類は 2 つに分かれる。**シリアルの口（serial port）** は OS からシリアルデバイスに見える経路（UART bridge = probe の
UART を USB-UART の変換チップで出したもの、USB CDC、内蔵の USB シリアル）で、OEP とシリアルの生のバイトを同じ口で運ぶ（§3.4）。
ほかの経路（USB の vendor bulk、HID、TCP）は OEP だけを運ぶ。

| 経路 | フレーム |
|---|---|
| シリアルの口（UART bridge、USB CDC、内蔵の USB シリアル） | COBS + CRC-16、0x00 で区切る（下） |
| USB の vendor bulk、TCP | `length(u16) message`。CRC なし。length 0 は予約（keepalive。読み飛ばす）。vendor bulk では 1 回の転送に複数のフレームが入ってよく、フレームが転送をまたいでもよい |
| USB の HID（vendor 定義の report） | vendor bulk の長さつきのバイト列を report で運ぶ: report = `count(u16)`、その列の count バイト、埋め（report の大きさは HID の記述子のとおり）。規則は下 |

- **HID の report**: 向きごとに、report は 1 つのバイト列を運ぶ。
  1. report の OEP のバイトは、count の後ろの count バイトである。向きごとに report の順につなげると、1 つの長さつきのバイト列になる。
     vendor bulk と同じ列（`length(u16) message`）である。
  2. フレームは report をまたいでよく、1 つの report があるフレームの終わりと次のフレームの始まりを持ってよい。送る側はフレームごとに新しい report から始めてよい。
     受ける側はそれに頼らない。
  3. count が 0 の report は空で、読み飛ばす。
  4. 送る側は埋めを 0 にする。受ける側は、埋めをその値によらず無視する。
  5. OEP の HID の interface は、report ID を宣言しないか、その input の report と output の report が使う report ID を 1 つ宣言する。宣言するときは、
     両方向のすべての report がそれで始まり、count はその後ろから数える。受ける側は、別の ID で始まる report を捨てる。
  6. §3.2 の途切れの規則はこの列に掛かる: フレームが途中で、report が 200 ms（`probe_frame_gap_ms`）来ないとき、probe は
     途中のフレームを捨て、列の次のバイトを長さの始まりとして読む。host は §5.1 で立て直す。
  7. count が report に入る量（report の長さ − 2、report ID があれば − 3）より大きい report は捨て、受ける側は列が壊れたとして
     扱う: 200 ms 途切れるまで入力を捨てる。max_frame より大きい長さ（下）と同じ。
- **COBS のフレーム**: message の後ろに CRC-16/CCITT-FALSE（多項式 0x1021、初期値 0xFFFF、反転なし、"123456789" → 0x29B1）を
  little endian で付け、COBS（254 byte のブロックに分ける標準の形）で符号にし、**前後を 0x00 で囲んで送る**（`0x00 <COBS> 0x00`）。
  probe も host も前の 0x00 を省かない。最後のブロックが 254 byte の data を持つ（code 0xFF）とき、符号にする側は後ろに空のブロックを付けず、解く側は
  付いた形も付かない形も受ける。空のフレーム（0x00 の連続）は読み飛ばす。
- **host の受け方（COBS）**: 口を開いた直後から最初の 0x00 までと、0x00 から次の 0x00 までを、どちらもフレームの候補として解く
  （開く前に送られたバイトや、開いた直後に落ちたバイトで前の 0x00 が届かないことがある）。解けない候補、CRC の合わない候補、
  role か corr の合わないフレーム（§11.1）は、シリアルの生のバイト（雑音）として捨てる。応答が来ないことは時間切れだけで判断する。
  （参考）正しい COBS のフレームは、2 つの 0x00 の間に 65796 byte より多くを持たない（registry の `cobs_frame_max_bytes`: 65535 byte の message とその CRC-16、
  254 byte ごとに COBS の code の 1 byte）。だから、それより長くなった候補は、閉じの 0x00 を待たずに生のバイトとして捨ててよい。
- **USB の束ね方**（vendor bulk）: host は、書き込みの長さが wMaxPacketSize の倍数なら長さ 0 の転送を続ける。probe は、送り
  終えて後ろに続かないとき、最後の転送が wMaxPacketSize の倍数なら、長さ 0 の転送を送るか最後の 1 byte を別の転送に分ける。
  続きがすぐ来るときは倍数のままでよい。
- **max_frame より大きい長さ**: probe はそのフレームと、次に `probe_frame_gap_ms` 途切れるまでの入力を捨て、次のフレームを待つ。応答は送らない。TCP では代わりに接続を閉じる。HID では、これは列から読んだ長さに掛かる（report の count は上の規則 7）。
- どのフレームを使うかは経路の種類だけで決まる（VID:PID で選ばない）。
- **TCP は、信頼できるローカルの接続か、認証したトンネルの内側でだけ使う。** OEP は認証を持たない（§6.4 の force を含む）。
  1 つの probe を複数の host で使うときは、ブローカーが 1 つのセッションに束ねる（probe の規則がブローカーに何を求めるかは次の項目）。
- **OEP の要求に自分で答える端点は probe である**。何が運び、後ろに何があるかによらない（たとえば TCP で OEP を出し、別のデバッガを動かすプログラム）。probe の規則はすべてそれに掛かる。要求を OEP の probe に中継するだけのブローカーは、その probe に対しては host である。
- **セッションの op に自分で答える中継のブローカー**（confirm、open、end、keepalive、lock_state）で、ほかの要求をすべて 1 つの OEP の probe に中継するものは、自分の describe を持たない: それが中継する fn 0 の describe は probe のもの。confirm の transport TLV では index 0xFF（「describe に無い」）を返す。probe に対しては host である。それらのセッションの op の規則はすべて、その応答に掛かる。
- **TCP の経路**: TCP で待ち受ける probe は、待ち受けの socket 1 つを fn 0 の describe の経路 1 つとして並べる（kind 6、interface 0xFF）。その socket で受けた接続はどれも、confirm の transport TLV でその index を返す。§3.3、§4.4、§7.1、§11.4 が経路ごとに掛ける規則（セッションの要求は 1 つの経路で、max_frame / window / max_inflight、使っている revision、通知の送り先）は、受けた接続ごとに別々に掛かる。
  probe が待ち受ける TCP の port と、host が TCP の probe を見つける方法は、この仕様の外である。

### 3.2 フレームの送り方

- host は **1 つのフレームを 1 回の書き込みで送り**、フレームの途中で 100 ms（`host_frame_pause_max_ms`）以上止めない。
- シリアルの口、vendor bulk、HID では、フレームの途中で 200 ms（`probe_frame_gap_ms`）入力が途切れたら、probe は読み取りを最初からやり直す。**TCP ではやり直さない。** TCP は区切りを失わず、流れの壊れた TCP の接続は閉じる。

### 3.3 複数の経路

- probe は OEP の制御を複数の経路で受けてよい。**複数の経路はセッションとロックを 1 つ共有する**。どの経路から来た要求も同じ
  ものとして扱い、応答はその要求の来た経路に返す。通知は subscribe が来た経路に送る（§11.4）。
- **1 つのセッションの id を持つ要求は 1 つの経路で送る**（§5.2 の順序の判定が経路の遅れで誤らないため）。session_id 0 の要求は
  別の経路から送ってよい。host が 1 つのセッションの要求を 2 つの経路から送ったときの誤判定は host の責任で、probe は確かめない。
- host は、同じ probe に複数の経路があれば vendor bulk、HID、シリアルの口の順に試す（シリアルの口は生のバイトの転送にも
  使われる、§3.4）。probe の経路の一覧は fn 0 の describe の transport（§7.5）で分かる。
- **USB の OEP の probe の見分け方**: host が知らない device の中から OEP の probe を自動で見分けるのは、**プロジェクトの USB の
  VID:PID `1209:4F45` で列挙する device** だけである（VID 0x1209、PID 0x4F45。registry の `usb` の `project_vid` / `project_pid`）。ほかの値で
  OEP の probe を自動で見分けることはない。それ以外は、利用者が probe を名指すか口を選ぶ（次の 2 つの項目）。device の
  文字列 iProduct は表示のための自由な文字列で、host は見分けに使わない。interface の文字列も表示のためのもので、見分けには使わない。
- **名指した probe**: 利用者が probe を unit_id で名指したとき（アドレス `oep://<unit_id>[/<slot name>]`、§7.6）、host は、serial number
  がその unit_id と同じ USB の device を、見分けずに開いてよい。開いた後は下の探りの規則に従い、confirm の後に送る fn 0 の describe の
  unit_id が名指した値と同じときだけ、その device をその probe として使う。違えば host はその device を閉じ、ほかに何も送らない。ここでの比べ方（unit_id と
  serial number、unit_id どうし）は、英字の大文字と小文字を区別しない（serial number を大文字で見せる OS や道具があるため。unit_id
  は §7.5 の文字だけなので、区別しなくても別の値が同じにはならない）。
- **ほかの device とシリアルの口**: 上の 2 つに当たらない USB の device とシリアルの口は、host が自分で扱い方を持つものか、利用者が
  明示して選んだものだけを開く。
- **探りの規則**: host が見分けずに開く device と口（名指した device、利用者の選んだ口、host が自分で扱う device）では、
  host が最初に送るのは confirm（§7.1）だけである（§5.2 の 1 回の送り直し、registry の `resend_max` を含む）。confirm の待ち時間
  （§4.4。confirm には引数で決まる時間が無いので 1000 ms（`host_wait_add_ms`）と転送の時間）が過ぎても正しい confirm の応答が来なければ（送り直したときは、送り直した
  confirm の待ち時間が過ぎても来なければ）、host はその device か口を閉じ、ほかに何も送らない。ただし UART bridge（transport の
  kind 1）の口では、送り直しの代わりに port_speed_idle_max_ms + 1000 ms（`port_speed_confirm_extra_ms`）の間 confirm を繰り返してよい（前の host が port_speed で上げた速さを待ち切るため、[リンク](oep-if-link.ja.md) §3。
  送るのは confirm だけで、その間に正しい応答が来なければ閉じる）。正しい confirm の応答とは、送った
  confirm と同じ corr の completed で、payload が §7.1 の形（`OEP!` で始まる）のものをいう。正しい応答が来た device と口は OEP の
  probe として扱う。
- **口の選び方**: OEP の probe と分かった device（プロジェクトの VID:PID、名指した device、正しい confirm の応答が来た device）の中の
  口は、interface の記述子で選ぶ: CDC（ACM）はすべてシリアルの口（§3.4。どれも OEP を受ける）、**bInterfaceClass 0xFF、
  bInterfaceSubClass 0x4F ('O')、bInterfaceProtocol 0x45 ('E') の interface の bulk IN / OUT の組**は vendor bulk、**usage page 0xFF4F、
  usage 0x45 の HID** は HID（registry の `usb`）。probe は vendor bulk と HID をこの形で出し、それぞれ高々 1 つしか出さない。host は、
  この class / subclass / protocol と usage page / usage だけで device を OEP の probe とは決めない。ほかの class 0xFF の interface
  （内蔵の USB シリアルのデバッグの機能、WebUSB など）はこの subclass / protocol を持たないので掴まない。ほかの機能（DFU、Mass Storage など）は
  OEP の外。
- **USB の serial number は unit_id**（§7.5）: probe が serial を選べる口（CDC、vendor bulk、HID を自分で出す device）では、serial number を
  unit_id そのものにする（§7.5 の不変性）。host は開かずに個体を見分けられ（名指した probe を探せる）、どの経路の describe とも同じ値に
  なる。serial を選べない口（内蔵の USB シリアル、USB-UART の変換チップ）は、host が経路を外から指定し、describe で unit_id を確かめる。
  confirm と describe は口を開いた後にしか使えないので、口の選び方はこの規則による。
- **max_frame は両方向の上限**: probe は max_frame を超える message を送らず、host は max_frame を超える message を送らない。
- **confirm の前**: どの probe も 64 byte（registry の `min_max_frame`）までの message を受ける（confirm の max_frame は 64 以上）。
  host は confirm の応答を受けるまで、64 byte を超える message を送らない。host は probe から長さ 65535 byte までの message を
  受けられるようにする。
- host は、OS が許すところでは、シリアルの口と HID を排他で開く（Linux では tty に TIOCEXCL）。
- HID を出す probe は、output の report を、interrupt OUT の endpoint でも SET_REPORT（Output）でも受ける。
- vendor bulk を出す probe は、できれば（SHOULD）その interface に Microsoft OS 2.0 の compatible ID `WINUSB` を付ける。

### 3.4 シリアルの口の共用

シリアルの口は、OEP のフレームと生のバイト（target のコンソールなど）を同じ口で運ぶ。probe はどの口でもいつでも OEP を受ける
（口を OEP 専用にする設定や、起動の型は持たない）。

- **UART bridge の回線**: データ 8 bit、パリティなし、ストップ 1 bit、フロー制御なし。起動時の速さは **115200 bps**（registry の `uart_bridge_boot_baud`）。port_speed（[リンク](oep-if-link.ja.md) §3）が変えるのは速さだけ。
- **上げた速さの後**: UART bridge の口を開く host は、port_speed を使うかどうかにかかわらず、起動時の速さで正しい confirm の応答が来なければ、
  あきらめる前にそこで port_speed_idle_max_ms + 1000 ms（`port_speed_confirm_extra_ms`）の間 confirm を繰り返す（前の host が上げた速さは
  それまでに起動時の速さに戻る、[リンク](oep-if-link.ja.md) §3）。
- **USB のシリアルの口**（USB CDC、内蔵の USB シリアル）: probe は、host がどんな line coding を設定しても OEP を受けて送り、line coding を何にも掛けない。
- **制御線**: probe は、OEP を受けるか送るかを DTR、RTS、回線の状態で決めない。host は口を開いている間 DTR と RTS を立てておく（UART bridge はそれを probe のリセットにつないでいることがある）。host が DTR を落としている間の probe の動きは定めない。
- **probe の受け方**: 0x00 が来たら次の 0x00 までためて解く。解けて CRC が合えば OEP の要求。解けない、CRC が合わない、または
  次の 0x00 の前に 200 ms 途切れた（§3.2）ときは、ためた分（前の 0x00 を含む）を生のバイトとして扱う。候補を閉じた 0x00 は
  次の候補の始まりになる。**0x00 だけで中身の無い候補**（フレームの閉じの 0x00 の後に何も来ないとき、0x00 の連続）は区切りで
  あり、200 ms 途切れても生のバイトにしない。0x00 の外で来たバイトはすぐ生のバイトとして扱う。
- **生のバイトの行き先**: probe がその口に結んだ流れ（どの流れを結ぶかは probe の設定が決める。結んでいなければ捨てる）。
  （参考）上の受け方により、0x00 の後に来た生のバイトは、次の 0x00 が来るか入力が 200 ms 途切れたときに初めて結んだ流れに届く。だから結んだ流れは
  文字の流れに向く。0x00 を含む二進の流れは、0x00 ごとに最長 200 ms 遅れる。
- **probe の送り方**: 応答と通知は `0x00 <COBS> 0x00`。1 つの口の送信は 1 つの書き手が行い、フレームの途中に生のバイトを挟ま
  ない（フレームは生のバイトより先に出してよく、生のバイトどうしの順は保つ）。
- **生の転送を止める口**: ロックを持つセッションの要求（その session_id を持つ要求。ロックを取った open も含む）が 1 つでも
  来た口では、そのセッションが終わる（end、lease の期限切れ、force で奪われる）まで、probe は生のバイトを送らず、口から来た
  生のバイトを捨てる。ロックの要らない要求だけが来た口と、ほかの経路でセッションが動いている口は止めない。セッションが終わった
  後、どこから生の転送を再開するかは、口に結んだ流れを定める設定が決める。
- host は、生のバイトの中に正しいフレームに見えるものが偶然現れても、role と corr の照合（§11.1）で捨てる。
  （参考）この照合は、わざと作ったフレームは止めない。生の転送が止まっていない口では、target の出力が、CRC の合ったフレームで、
  未解決のロックなしの要求の corr を持つものを含みうる（corr は 1 ずつ進むので予測できる）。host はそれを応答として受ける。応答の中身を信じる必要のある host は、
  生の転送が止まった口（上のとおり、自分のセッションの要求が届いた後）か、長さつきのフレームの口で要求を送る。
- **host の受けの量**: OS のシリアルドライバは、probe の送るフレームがドライバの受けの量を超えてまとまって届くと黙って失うことがある
  （理由: ドライバの読みのバッファには限りがあり、入りきらない burst はエラーなしに捨てられる。よく使われるドライバの 1 つでは約 8 KiB の burst が失われたので、
  下の上限は余裕をとっている）。host はシリアルの口では、未解決の要求の応答の見込み量（同時数 × フレームの上限）を
  6 KiB 以下に保つ（registry の `host_serial_inflight_max_bytes`）。通知も同じ: シリアルの口で購読するとき、host は subscribe の min_bytes を小さく（2 KiB 以下、`host_serial_min_bytes_max`）保ち、probe が一度に
  送る量を自分の受けに合わせる（§11.3）。大量の転送は長さ付きフレームの口（vendor bulk）を優先する。probe の max_inflight と window は
  probe の受けの上限であって、host の受けの上限ではない。

## 4. メッセージ

### 4.1 要求

```text
role=0x01 | corr(u16) | fn(u16) | op(u8) | session_id(u32) | payload    見出し 10 byte
```

- `corr`: host が振る番号。**host は要求ごとに 1 ずつ進める**（session_id 0 の要求も数える。65535 の次は 1。0 は使わない）。
  同じ番号をもう一度使うのは、§5.2 の送り直しのときだけ。probe は、送り直しと、覚えていない古い要求の見分けにこの順序を使う。
- `session_id`: 要求が属するセッション、または **0 = セッションなし**。どの要求もこれを持つ。
  - ロックが要る op（§6.3）の要求は、ロックを持つセッションの id を持つ。0 なら rejected session_required（§4.3 順 1）。
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
| 0x07 | no_session | 要求は session_id を持つが、どのセッションもロックを持っていない（セッションが終わった、または初めから無い）。host はセッションを開き直す | — |
| 0x08 | locked | 他のセッションがロックを持つ | 残り時間 ms（u32）、[TLV owner（§6.4）] |
| 0x09 | session_required | ロックが要る op の要求が session_id 0 を持つ | — |
| 0x0A | no_connection | 要求の資源（connection、stream など、番号で指すもの）を probe が知らない。host は作り直す。どのインターフェースでも、知らない番号にはこれを使う | — |
| 0x0B | unsupported | 定義にはあるが、この probe が扱えない（critical の TLV、固定部分の値、この probe が持つ op の任意の機能） | `tag(u8)`、[TLV]。tag は critical の TLV なら受け取ったままの値、固定部分の値なら 0x00。どの要素かを示すときは後ろに TLV（unavailable と同じ tag の空間: channel、index） |
| 0x0C | result_lost | 送り直された要求の結果を覚えていない（§5.2） | — |
| 0x0D | corr_reused | 同じ corr で fn、op、中身のどれかが違う要求が来た（§5.2） | — |
| 0x0E | — | 予約 | — |

rejected の detail は reason で、そのほかの情報は payload に置く。

**断り方の順**（probe は次の順に見て、最初に当たった理由で断る。同じ状況に 2 つの理由を作らない）:

1. 見出し: unknown_function → unknown_operation（その fn の ops が立てない op: インターフェースが定義しない op、またはこの probe が持たない任意の op、§1.2）→ session_required。
2. 送り直し（§5.2 の表）: corr_reused / result_lost / 覚えた応答。
3. セッション（§6.2）: no_session / locked。
4. window_exceeded。
5. **書式** → malformed: 長さ、中身と合わない数、TLV の符号化の誤り、フィールドどうしの矛盾、そしてフィールドの定義がどの revision でも除く値（7 bit の `address > 0x7F`、0 / 1 以外の真偽値、定義が無効と言う値、長さが分からず要求の残りを読めなくなる値、たとえば知らない dmi の step の kind）。書式が正しければ続けて: payload の中で指す fn（describe、subscribe、unsubscribe、plan_apply、probe.config の項目）が無い → unknown_function。
6. **この probe が扱わない** → unsupported: 定義が使わずに残した値（enum の使っていない値、要求の flags の予約のビット）、定義にあるがこの probe が宣言しない値（mode、format、rate、trigger の type）、知らない critical の TLV、宣言が許さないピンの組。payload の tag は、固定部分の値なら 0x00、critical の TLV の中の値ならその TLV の受け取ったままの tag（そうした値を持つ critical でない TLV は無視する、§2.3）。
7. **今の状態・資源で受けられない**（plan、接続、動いている、容量、組に束ねられている）→ unavailable（cause 付き）。
8. 番号で指す資源を知らない → no_connection。

**矛盾と定義されていない値**: 順 5 の矛盾の確かめは、定義された値を持つフィールドどうしにだけ当てはめる。定義が使わずに残した値（順 6: enum の使っていない値、予約のビット）を持つフィールドは、その値について unsupported で断り、そのフィールドが関わる矛盾（そのフィールドを別のフィールドと比べる規則、またはその値によって決まる規則）は確かめない。順 5 のほかの確かめ（長さ、数、TLV の符号化、定義がどの revision でも除く値、長さが分からない値）はこれに影響されず、先に来る。例: drive を持つ mode 5 の probe.config の idle の項目は、mode について unsupported で断り、mode 3 / 4 以外の drive として malformed にはしない。

payload の中で指す fn（describe、subscribe、plan、設定の項目）が無いときは、順 5 の終わりで unknown_function を流用する。

**unavailable の payload**（任意の TLV の並び。host は知らない tag を飛ばし、無くても扱えるようにする。probe は分かる範囲で付ける）:

| tag | 名前 | 値 |
|---:|---|---|
| 0x01 | cause | u8: 1 ピンが使われている、2 数の上限（plan_roles、スロット、接続など）、3 保存先が足りない、4 組（capture-group）に束ねられている、5 設定が持つ（設定の plan、スロット）、6 状態が違う（configure していない、動いている、など） |
| 0x02 | channel | u16。ぶつかった channel（繰り返してよい） |
| 0x03 | holder_fn | u16。その資源を持っている fn |
| 0x04 | holder_kind | u8: 1 plan、2 線の接続、3 スロット、4 bind、5 設定の plan、6 設定の disable、7 設定の idle |
| 0x05 | fn | u16。断りの対象の fn（capture-group の bind で、どのトラックかを示す） |

インターフェースは 0x40 以降に自分の tag を足せる。rejected unsupported の payload の後ろの TLV も同じ空間（channel 0x02、fn 0x05、
インターフェースの index など）。ただしそこでは 0x01 は supported で、confirm の断りに使う（§7.1）。

### 4.4 パイプライン

- confirm（§7.1）で probe は `max_frame`（受け取る最大の message 長）、`window`（未解決の要求の message 長の合計の上限）、
  `max_inflight`（未解決の要求の数の上限）を返す。message 長は見出し（role から）を含み、フレームの包み（COBS、CRC、length）は含まない。
- host は両方の上限を守る。超えた要求を probe は rejected window_exceeded で断ってよいが、バッファを超えて失われた要求には
  応答も返らない。守るのは host の責任である。
- probe は要求を受け取った順に処理し、応答を受け取った順に返す。
- confirm の max_frame、window、max_inflight は、**その confirm が来た経路の**上限である。経路ごとに別々に数え、ある経路で未解決の要求は、ほかの経路の受けの余地を使わない。§5.2 の表は probe に 1 つのまま（セッションの要求は 1 つの経路で送る、§3.3）。
- **host の待ち時間**: 応答が来ないことは時間切れだけで判断する（§3.1）。host は要求ごとに**少なくとも**次を待つ: その要求の引数で決まる時間（run の timeout_ms、
  reset の hold_ms、dmi の待ちの和、save など。attach は `attach_budget_ms` にその reset TLV の hold_ms を足したもの、scan は `scan_budget_ms` + `attach_budget_ms`（[線とデバッグ](oep-if-debug.ja.md) §1）。無ければ 0。多くても max_op_ms、§7.5）+ 1000 ms（`host_wait_add_ms`）+ 転送の時間。待ちは、要求を書き終えた時から始める。同じ経路に先の要求が未解決の間は、その 1 つ前の要求の応答が届いた時から始める（probe は順に答える）。
  転送の時間は UART bridge 以外では 0。UART bridge では (L + max_frame × (1 + `notify_pending_max_frames`)) × 10 / baud 秒で、L はその要求のフレームの線の上の長さ、baud は口の今の速さ。その経路で confirm の応答を受け取るまで、host は max_frame として `min_max_frame`（64）を使う。その後は、そこでのいちばん新しい confirm の応答の max_frame を使う。シリアルの口が UART bridge かどうか分からない host（たとえば fn 0 の describe で経路の種類を読む前、§7.5）は、そのシリアルの口でこの転送の時間を数え、baud は自分がその口に設定した速さとする。この下限より長く待つことはいつでも許される。max_op_ms が 0 か `max_op_ms_max` を超えると読んだ host は、その probe を適合しないものとして扱い、使わない。待ちが過ぎたら §5.2 の送り直しに進む。
- **この下限はすべての要求に当てはまる**。host 自身のリンクの要求（confirm と `oep.link` の op）も含む。[リンク](oep-if-link.ja.md) §3 が port_speed の段階について決める待ち（新しい速さを確かめる confirm の前の 20 ms 以上、verify_ms、idle_ms、port_speed_idle_max_ms + 1000 ms の間の confirm の繰り返し）はそこで決めるとおりのまま。それらは要求と要求の間の時間で、応答を待つ時間ではなく、その間に送るどの要求についてもこの下限を縮めない。
  [リンク](oep-if-link.ja.md) §3（host の義務 5）、§3.3、§3.4 が host に繰り返させる confirm は、それぞれ新しい corr の新しい要求で、§5.2 の送り直しではない: host は、前の confirm の下限が過ぎる前に次を送ってよい。後から届いた前の corr への応答は受けるか読み飛ばし、下限が過ぎる前に前の confirm を答えが無いものとは扱わない。`oep.link` の op はこのように繰り返さない。どれも自分の下限まで待つ。

## 5. 立て直しと送り直し

### 5.1 区切りの立て直し（長さつきのフレーム）

長さつきのフレーム（vendor bulk、HID、TCP）で、host は、corr の合わない応答、あり得ない長さ（max_frame を超える）、途中で
止まったフレーム（続きが 200 ms 来ない。TCP を除く: TCP ではフレームの途中の休みは普通のことで、host はそのフレームを読み続ける、§3.2）を見たら、入力が 50 ms（`resync_quiet_ms`）静かになるまで読み捨て、confirm を送って自分の corr の応答が返ることを
確かめてから再開する。応答の末尾の TLV が途中で切れていたら、その応答は壊れている。通知が流れ続けて入力が静かにならないときは、
unsubscribe と end を確かめずに送ってよい（二度実行しても害がない）。COBS のフレームは CRC で壊れたものを捨てられるので、
この手順は要らない。

立て直しの confirm の前と、長さつきのフレームの口を開いて最初の confirm の前には、host は、50 ms 静かな入力に加えて、その口に最後に書いてから `host_resync_wait_ms`（registry、250 ms = probe_frame_gap_ms + 50 ms）が過ぎるまで待つ。TCP では、代わりに接続を閉じて新しく開いてもよい（長すぎる長さの後は、probe が閉じている、§3.1）。

### 5.2 送り直しと重複排除

- 応答が壊れたか来なかったとき、host は**同じ corr で 1 回送り直してよい**（registry の `resend_max`。状態を変える要求も）。セッションが口を持っている間
  （§3.4、生の転送は止まっている）に届いた壊れたフレームは、待っている答えのものとして扱ってよく、待ち時間を待たずに送り直してよい。立て直しの中で unsubscribe
  と end を送ったときは、セッションが終わっているので、元の要求は送り直さない。
- 送り直しの待ち時間も答えなしに過ぎたら、host はその経路が失敗したとして扱う: その要求の結果は分からず、その経路で出ている要求もいっしょに失敗する。そこで何かを送る前に、host は §5.1 の confirm で立て直す（COBS を含むどの種類のフレームでも: 入力が静かになってから、自分の corr を持つ応答が返る confirm）か、経路を閉じて開き直す。その confirm で boot_id が変わっていれば再起動（§6.5）。立て直した後、host は状態を変える要求を繰り返す前に状態を読む。
- probe は、最後のセッションの id を持った要求について、直近の max_inflight 個以上の (corr, fn, op, 要求の payload の CRC-32,
  応答) と、そのセッションで最も新しい corr を覚えておく。**要求の同一性は corr だけで決まる**（§4.1 の順序）。CRC は host の
  番号付けの誤りを見つけるためだけのもの。
- probe は、最後のセッションの要求のうち §4.3 の順 2 を通ったものすべての応答を、rejected の応答も含めて覚え、それに合わせて最も新しい corr を進める。rejected になった要求を直して送る host は、新しい corr で送る。
- §5.2 はどの probe（OEP の要求に自分で答えるどの端点も、§3.1）にも、TCP を含むどの経路でも掛かる。TCP はフレームを失わないが、応答が遅れれば host は待ち（§4.4）の後に送り直すので、probe は要求を二度実行しないように表を持つ。表は probe に 1 つで、セッションと同じく、すべての経路と TCP の接続で共有する。OEP の probe に中継するだけのブローカーは自分の表を持たない。corr を付け直すときは、client の送り直しを、最初に使ったのと同じ corr で中継する。そのために、受けた client の接続ごとに、client の corr から上流で使った corr への対応を、少なくともその client の直近の max_inflight 個の要求について持ち、その接続が閉じたら捨てる。
- 最後のセッションの session_id を持つ要求は、**§6.2 の判定より先に**次のとおり見る（ロックが空いていても同じ）。open は表で
  引かない（送り直した open は §6.2 で決まる）:
  - 表に同じ corr があり、fn、op、CRC が同じなら、**実行せずに覚えた応答を返す**。ロックの状態も lease も変えない（送り直した
    end でロックが立ち直ることはない）。
  - 表に同じ corr があり、どれかが違えば rejected corr_reused。
  - 表に無く、corr が最も新しい corr より新しくない（差を u16 の符号付きで見て 0 以下）なら、実行せずに rejected result_lost
    （表から落ちた古い要求の送り直し。host は状態を読み直して確かめる）。
  - それ以外は新しい要求として §6.2 へ進む。
- 覚えておく応答の大きさには上限を置いてよい。上限を超えて覚えていない応答の要求を送り直されたら、実行せずに rejected
  result_lost。
- **覚えた表と最も新しい corr は成功した open のたびに捨てる**（end、lease の期限切れ、force では捨てない: 送り直された end には
  表から答える）。セッションが変わったときの exactly-once は約束しない。
- session_id 0 の要求は重複排除しない。
- CRC-32 は IEEE（reflected、多項式 0xEDB88320、初期値と最終の XOR 0xFFFFFFFF。"123456789" → 0xCBF43926）。

## 6. セッションと排他

### 6.1 ロック

- probe は**ロックを 1 つ**持つ。ロックを持つセッションだけが状態を変える要求を実行できる。
- host はセッションごとの session_id を、予測できない 32 bit の乱数で選ぶ。決まった値や 0 は使わない。session_id 0 の open は rejected malformed。probe は最後にロックを持った session_id を覚えている。
- lease は open で決まる。ロックを持つセッションの要求で §4.3 の順 3 を通ったものへの応答のたびに（rejected の応答も含む）、lease は数え直す（応答を送った時から lease_ms を数え直す）。§5.2 の表から返し直した応答では数え直さない。期限を過ぎるとロックは空く
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
（confirm、list、describe、lock_state、インターフェースが定める読むだけの op）。インターフェース
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
  TLV 0x01 owner で付ける（owner が無ければ付けない）。**session_id は返さない**（返すと他の host が force なしでそのセッションとして要求を送れる）。owner は表示のためだけのもので、
  probe は解釈しない。（参考）owner は lock_state でどの host からも読めるので、host は秘密を入れない。
- **force**: 他のセッションがロックを持っていても奪う。probe は、前のセッションの資源をその終わりと同じく解放してから（§9）
  ロックを渡す。force は認証ではなく、取り違えを防ぐだけのものである。

### 6.5 boot_id

boot_id は probe の起動ごとに変わる値で、confirm（§7.1）と open の応答に入る（同じ値）。probe は boot_id を、次の好ましい順に取る: ハードウェアの乱数源（32 bit）。不揮発の記憶に置き、起動ごとに変える値（数え上げ、または保存した乱数）。どちらも無ければ、起動ごとに変わる値を混ぜたもの（初期化していない RAM、ADC の入力の変換の雑音、最初の USB や UART の動きなど外からの出来事が来たときの、止まらないタイマーの数）。起動のコードの決まった場所で読んだタイマーは、そうした値ではない。最後の素しか持たない probe は boot_id を繰り返しうるし、host はその確率を受け入れる。0 も普通の値。host は、boot_id が変わった
とき、そのセッションの資源（plan、インターフェースの資源）と、覚えた fn の対応、資源の番号、ストリームの位置がすべて無効になったとみなす。
ロックを持たない host（監視、発見）は confirm で再起動を知る。

open の応答も boot_id を持つ: 知っていた boot_id と比べる host は、open のときに再起動を知り、覚えた fn の対応を使う前に list をやり直す（§7.2）。

## 7. 発見

### 7.1 confirm

```text
要求: "OEP?"、min_rev(u8)、max_rev(u8)、[TLV]
応答: "OEP!"、revision(u8)、flags(u8)、max_frame(u16)、window(u32)、max_inflight(u8)、boot_id(u32)、[TLV]
```

- TLV 0x01 transport（u8）: この confirm が来た経路の index（§7.5）。probe は必ず付ける。同じ接続で返す fn 0 の describe の entry を指す（中継のブローカーからは 0xFF、§3.1）。port_speed（UART bridge、[リンク](oep-if-link.ja.md) §3）と bind（シリアルの口、[probe の設定](oep-if-probe-config.ja.md) §1.2）が TCP の index を取ることはない。

host は扱えるプロトコルの revision の範囲を送り、probe はその中で扱える最大の revision を返す。範囲に扱えるものが無ければ
rejected unsupported（下）。flags は予約（0）。max_frame は 64 以上（§3.3）、window は max_frame 以上、max_inflight は 1 以上。この範囲を外れた confirm の応答を受けた host は、その経路を使えないものとして扱う: そこにはもう何も送らず、値を知らせる。host は flags のビットを無視する（予約、§2.4）。boot_id は §6.5（ロックなしで再起動を知るための置き場）。要求も応答も 64 byte に収まる
（§3.3）。

- confirm の要求とその応答の固定部分、magic の `OEP?` / `OEP!`、confirm の前の規則（64 byte、§3.1 のフレーム、§3.3）は、どのプロトコルの revision でも同じ。
- probe が選んだ revision は、**その confirm が来た経路**の、両方向のすべての message に、その経路の次の confirm まで掛かる。経路ごとに違う revision で動いてよい。TCP では、経路は受けた接続ごとである（§3.1）。
- ある経路で最初の confirm をした後、host はそこでの後の confirm（立て直し、探り直し）ではすべて、`min_rev = max_rev =` 使っている revision を送る。
- 範囲の中に扱える revision が無いとき: rejected unsupported で、payload は tag 0x00 の後に TLV 0x01 supported（min(u8)、max(u8): probe が扱える範囲）。`min_rev > max_rev` は rejected malformed。

### 7.2 list

```text
要求: flags(u8: bit0 exact)、first(u16)、prefix_len(u8)、prefix
応答: total(u16)、count(u8)、count × entry
entry: fn(u16)、instance(u16)、revision(u8)、flags(u8)、name_len(u8)、name
```

- prefix に一致する名前を、first 番目から 1 フレームに入る分だけ返す。**一致は label（`.` で区切った部分）の境界で見る**:
  名前が prefix と同じか、`prefix + "."` で始まれば一致（`oep.fixture.uart` は `oep.fixture.uart` と `oep.fixture.uart.stream` に
  一致し、`oep.fixture.uart2` には一致しない）。prefix は label の並びで、末尾に `.` を付けない（`oep.` は何にも一致しない。
  `oep` と書く）。空の prefix はすべてに一致する。exact なら完全一致だけ（空の prefix は何にも一致しない）。`oep.core`（fn 0）も最初の
  entry として数える。要求の flags の bit 1〜7 は予約: どれかが立った要求は rejected unsupported（payload の tag 0x00、§2.5）。
- 名前は 1〜64 byte、使える文字は `a-z 0-9 - .`（§13）。
- instance は、同じ名前のインターフェースが複数あるときの見分け。**同じ (名前, revision) のインターフェースを fn の昇順に 0 から振る**。probe は同じ名前のインターフェースの
  順を firmware の版を越えて保つ（保存した設定が (name, instance, revision) でインターフェースを指すため）。flags は予約（0）。
- 文字で 1 つのインターフェースを指すとき（CLI、設定のファイル、ログ）は `name#instance` と書く（instance はこの値、0 から。
  `#0` は省いてよい）。例: `oep.fixture.uart#1` は 2 つめの `oep.fixture.uart`。
- list の応答（どのインターフェースがあるか、その fn、instance、revision、名前）は、同じ boot_id の間変わらない。インターフェースが増えたり減ったりする probe は再起動する（新しい boot_id）。host は boot_id が同じ間、名前から fn への対応を覚えてよい。
- first が一致する entry の数以上なら、応答はその total と count 0。

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

### 7.4 describe の共通タグ（0x01〜0x3E。0x3F は応答のメタ情報）

| tag | 名前 | 値 |
|---:|---|---|
| 0x01 | role_channels | role(u8)、base(u16)、bitmap。bit i が立っていれば channel base+i をその role に使える。同じ role を複数書いてよい（和集合） |
| 0x02 | max_clock_hz | u32 |
| 0x03 | max_length | u16。1 回に扱える最大の長さ。その op の要求と応答が max_frame に収まる値で宣言する（単位はインターフェースの文書が決める）。超えた要求は rejected unsupported |
| 0x05 | min_clock_hz | u32 |
| 0x06 | features | u32。op でない任意機能のビット: モード、format、通知など（意味はインターフェースが決める）。任意の op は ops で宣言し、決して features では宣言しない |
| 0x07 | implementation | u8。0 未指定、1 ソフトウェア、2 専用ペリフェラル、3 ペリフェラル + DMA / PIO（表示と診断のため） |
| 0x08 | channel_group | group(u8)、n(u8)、n × (role(u8)、channel(u16))。この group を使うなら、各 role はここの channel に固定される。group が 1 つ以上ある機能では、plan はどれか 1 つの group に完全に一致しなければならない |
| 0x09 | ops | base(u8)、bitmap。bit i が立っていれば op base + i を持つ（§1.2）。fn 0 を含むすべての fn の describe が付ける |

0x04 は予約。role の番号はインターフェースが定める。これらの値は固定の形で、足す情報は新しい tag にする（§2.3）。

- **ops** の例: op 0x01〜0x08 をすべて持つ riscv-dm の fn は `09 02 00 01 FF` を送る。dmi、halt、resume だけ（0x01〜0x03）を持つものは `09 02 00 01 07` を送る。
  host は op があるかを知るのに、features ではなく bitmap を読む。

- どのピンにも割り当てられる機能は role_channels に候補を並べ、ピンの組が決まっている機能は channel_group を組の数だけ書く。
  両方を書いた場合、plan は channel_group のどれかに一致し、かつ role_channels の候補にも入っていなければならない。
  role_channels が縛るのは、それが挙げる role だけである（role_channels に無い role は channel_group だけで決まり、channel_group に
  無い role は role_channels だけで決まる）。
- 同じ宣言は、plan を使わずにピンを引数で選ぶインターフェース（線の attach の pins など）でも、選べるピンの宣言として使う。
- plan の要求の role_assignment（0x10、critical の 0x90 で送る）は plan_apply の文脈の tag（§8）で、describe の tag ではない。

### 7.5 probe 全体の宣言（fn 0 の describe、0x40〜）

| tag | 名前 | 値 |
|---:|---|---|
| 0x40 | firmware | text |
| 0x41 | model | text。probe の種類（同じ firmware を載せた同じ種類のハードウェアで同じ値。個体では変わらない）。**小文字の `a-z 0-9 -`**、1〜32 byte（registry の `model_max_bytes`）。project のものでない model は、作り手の逆 DNS の名前の `.` を `-` に替えたもので始める（例 `com-example-probe1`） |
| 0x42 | unit_id | 個体の ID。**必須**。text で 1〜32 byte、使える文字は `a-z 0-9 -` だけ（チップの固有の番号を小文字の 16 進にしたもの、など）。同じ probe の経路を host がまとめるのに使うので、どの経路の describe でも同じ値を返す。USB の serial number と同じ（§3.3）。host が probe を名指す値（アドレス `oep://<unit_id>/<スロットの名前>`、[probe の設定](oep-if-probe-config.ja.md) §1.1） |
| 0x43 | channels | u16。channel の数 |
| 0x44 | reserved | base(u16)、bitmap。bit i が立っていれば、channel base+i は probe が自分で使っていてインターフェースに割り当てない channel |
| 0x45 | profile | text。治具などの配線の名前 |
| 0x46 | label | channel(u16)、text。**firmware（配線の profile）が持つ固定の** channel の名前（NRST など）。設定で付けた名前は `oep.probe.config` の get で読む（describe は宣言だけ、§7.3） |
| 0x47 | resets_on_open | u8。経路を開くと probe がリセットするか |
| 0x48 | — | 予約 |
| 0x49 | transport | index(u8)、kind(u8)、interface(u8): USB CDC（kind 2）は CDC の通信の interface の bInterfaceNumber（その機能の最初の interface）。内蔵の USB シリアル（kind 3）は、ハードウェアが見せるその同じ番号、probe が知れなければ 0xFF。vendor bulk と HID はその interface の番号。UART bridge（kind 1）と TCP は 0xFF。probe の経路ごとに 1 つ。**必須** |
| 0x4A | discoverable | u8。1 = probe はプロジェクトの USB の VID:PID（§3.3）でも列挙している（今の経路がそうでなくても）。それで列挙しない probe は 0 |
| 0x4B | plan_roles | u32。plan が一度に持てる role_assignment の数（すべての fn の合計。設定の plan を含む）。上限のある probe は必ず出す（§8） |
| 0x4C | chip | text。probe の MCU の型番とリビジョン: `<part> v<revision>`。part は `a-z 0-9` の 1〜24 文字。revision は数字で、`.数字` の組が続いてよい。リビジョンが分からなければ part だけ（例 `abc123 v1.0`、`abc123`）。取ったデータに、どのチップで取ったかを残すため（任意） |
| 0x4D | max_op_ms | u32。probe が 1 つの要求にかける最長の時間。**必須**。1〜600000（`max_op_ms_max`、10 分）。超えうる op（run、dmi の待ちの和、キャプチャの start、save、attach の reset の hold_ms）は、引数の和がこれを超えれば rejected unsupported。実行中は lease を数えない（§6.1）。ほかの経路と connection のコンソールの読みは続ける。値は probe が決める。host は §4.4 のとおり待つ |
| 0x4E | — | 予約 |

- transport の kind: 1 UART bridge、2 USB CDC、3 内蔵の USB シリアル（MCU のハードウェアが持つ USB のシリアルの口で、serial number を含む USB の記述子を probe が選べないもの）、4 vendor bulk、5 HID、6 TCP（registry の `transport_kind`）。
  1〜3 がシリアルの口（§3.4）。index は probe の中で経路を指す番号（0 から）で、probe の設定がシリアルの口を指すときもこの番号を
  使う。probe の起動の間は変わらない。
- **経路の index の不変性**: 経路は、同じ model の firmware の版を越えて index を保つ。経路を足す firmware は、それまで使っていない index を付け、外した index は使い直さない。
- host は transport の数で、ロックの奪い方を決めてよい（経路がシリアルの口 1 つだけなら、口を排他で開けた時点で前の持ち主は
  いない。[host 開発ガイド](host-development-guide.ja.md) §6）。
- **unit_id の一意性**: unit_id は個体ごとに違う値にする（チップの固有の番号、など）。保存はあるが固有の番号の無い probe は、最初の起動で乱数から unit_id を作って保存する。
  どちらも無い probe は `x-` で始まる unit_id を使う（一意ではない）。host は `x-` で始まる unit_id で経路をまとめず、それで probe を名指さず、セッションを越えて持つもの（たとえば口のリンクの速さの記録）のキーにしない。同じ口のほかの個体が何も引き継がないためである。
- **unit_id の不変性**: unit_id は個体の値（チップの固有の番号、保存した乱数。`x-` の unit_id だけは例外）だけから作り、firmware の版、profile、ビルド、経路の種類で
  変えない。接尾辞を足さない。host と OS は unit_id（= USB の serial number、§3.3）で probe を覚える。

### 7.6 アドレス

host が probe とスロットを名指す文字列: `oep://<unit_id>[/<slot name>]`。authority は unit_id（§7.5、小文字）、path はスロットの名前
（[probe の設定](oep-if-probe-config.ja.md) §1.1）1 つだけ。path の無い `oep://<unit_id>` は probe 自身。v1 はこれ以外（query、port、
複数の path）を定めない。IDE や設定のファイルが probe を覚えるときはこの形で覚える（VID:PID や口の名前ではなく）。

## 8. plan

plan は **fn ごと**に持つ。

- **plan_apply**: role_assignment の TLV（0x10、critical の 0x90 で送る: fn(u16)、role(u8)、channel(u16)。繰り返す）の並び。1 つの割り当ての見分けは
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
- 解いたピンは、どの経路で解いても（plan_release、plan_apply による置き換え、§9 の lease の期限切れと force での後始末）、**空きの状態**、
  つまり **probe の設定がそのピンの idle を決めていればその状態（出力 low / high ならその level と、idle が決める強さで駆動し、Hi-Z にしない）、決めていなければ
  Hi-Z（入力、プルなし）**にする。インターフェースは、解いた後もピンを自分の駆動のまま残してはならない（空きの状態が出力なら、その駆動は
  設定の idle のもの。空きの状態の設定は `oep.probe.config` の idle、
  [probe の設定](oep-if-probe-config.ja.md)）。
- **起動時**、probe は最初の要求に答える前に、reserved（§7.5）でないすべての channel を空きの状態にする（上: 設定が idle を定めればその idle、そうでなければ Hi-Z: 入力、プルなし）。それまでピンは MCU のリセットの状態（参考: 誤った水準が害になる線には外付けのプルが要る、[probe の設定](oep-if-probe-config.ja.md) §5）。
- **plan を取ってもピンの電気の状態は変わらない。** ピンは、それを持つインターフェースが使い始めるまで空きの状態を保つ。どの操作で使い始めるかは、各インターフェースの文書が定める（plan そのもののインターフェースもある）。ピンを読むだけのインターフェースは決して変えない: 出力を止めず、ほかの機能や出力の idle が駆動するピンのプルや向きも変えない。
- idle が出力（mode 3 / 4）の channel への plan をインターフェースの文書が断るとき、その断りは unavailable（cause 5、holder_kind 7）である。
- plan の寿命は §9（fn ごと）。

**plan_apply の断り方**（§4.3 の順）:

| 状況 | reason |
|---|---|
| 形の誤り、同じ (fn, role, channel) が 2 回、fn 0 を挙げた | malformed |
| fn が無い | unknown_function |
| role がそのインターフェースに無い、channel が role_channels の候補に無い、channel_group のどれにも一致しない | unsupported（tag 0x90） |
| plan_roles を超える、ピンや資源の取り合い（§8.1）、設定の plan の fn、インターフェースが断る出力の idle | unavailable（cause 2 / 1 / 5） |

### 8.1 資源の取り合い

- probe の資源（ピン、ペリフェラル、DMA、タイマーなど）を取るものはすべて、取る前に、今ある plan、connection、設定から入れた
  資源（bind など）とぶつからないか確かめる。ぶつかれば rejected unavailable で断り、**今ある機能の状態は何も変えない**。
  取るもの: plan_apply、線の attach（pins）、設定の set、インターフェースが定める資源を作る操作。
- どの内部の資源（DMA の番号など）を使うかは host に見せなくてよい。共有して安全な使い方（同じピンを 2 つの機能が入力として
  読むなど）は、probe が明示的に許すときだけ許す。

## 9. 資源の寿命（一般の規則）

**セッションが作ったものはすべて、そのロックが終わるときに解放する。何で終わっても同じ**（end、lease の期限切れ、force で奪われる）。次の
セッションには何も渡さない。セッションをまたいで残るのは probe の設定が定めるもの（`oep.probe.config` の plan、idle の状態、slot、bind）で、どの host からも読める。

| 出来事 | セッションが作った資源 | 購読（§11） | §5.2 の表 | 後の同じ ID の要求 |
|---|---|---|---|---|
| end | 解放する | 終わる | 残る（送り直された end にはここから答える） | ロックが空いている間は no_session、別のセッションが持つ間は locked |
| lease の期限切れ | 解放する | 終わる | 残る | end の後と同じ |
| force で奪われる | 解放する | 終わる | 捨てる（奪った open が捨てる） | 奪った側が持つ間は locked、その後は no_session |
| 同じ ID の open（保持中） | 残る | 残る（送り先はその経路） | 捨てる | — |
| probe の再起動 | 無くなる（boot_id が変わる） | 無くなる | 無くなる | no_session |

- セッションとほかのものが共有する資源（slot も使う connection、bind も送るストリーム）では、セッションの持ち分だけが外れ、
  使う者が残らなくなったときに、インターフェースの文書のとおり閉じる。
- 資源が閉じた後もインターフェースが読めるまま残すものは、セッションの資源ではない: 閉じた console のストリームは、同じ場所で同じ仕組みが
  次に開かれるまで読める（[コンソール](oep-if-console.ja.md) §2）。
- 1 つのプロセスで 1 つのコマンドを走らせる host は、probe にまだ残っているものに明示の道で届く: 生きている組への attach はその
  connection を返し（slot はセッションをまたいで connection を保つ）、同じ場所と仕組みでの console の open は、開いていても閉じていてもそのストリームを、
  位置と mark ごと返す。
- 本体の資源: **plan**（外すとピンは plan_release と同じく解放。target の線を plan で保っていた場合、target の状態が変わりうる）、通知の購読
  （§11。購読は end でも終わる）、§5.2 の表。
- インターフェースが作る資源（debug の connection、ストリームなど）の寿命は、インターフェースの文書が、この規則の上で定める
  （誰が使っているか、いつ閉じるか）。
- 保存した設定（インターフェースが定める）から入れた資源は、セッションの資源ではない。
- **資源の番号は u16 で、probe で 1 つの空間**（connection、ストリームなど、インターフェースが番号で指すものすべて。別のインター
  フェースの資源を渡されたら rejected unavailable cause 6）。新しい資源を作るたびに 1 から順に進め、65535 の次は 1（§2.6）。閉じた
  番号は十分離れてから再利用してよい（直近に閉じた 1024 個の番号は使わない。registry の `resource_reuse_distance`）。失敗した作成（attach が
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
- fn 0 を購読するとハートビートが来る。周期は max_delay_ms（0 なら 1000 ms、`heartbeat_default_ms`）。probe は 100 ms より短いハートビートの周期を 100 ms（`heartbeat_min_ms`）に切り上げてよい。
- 流れの量の予算（クレジット）は持たない。host や線が遅れた分は probe の中で押し出され、インターフェースの payload
  （ストリームの位置など）か seq の抜けで分かる。

### 11.4 probe の義務（送り出す probe）

1. **応答を先に送る。** 届いている要求をすべて処理してから、通知を送る。
2. **送りかけの通知を小さく保つ。** 経路の送信バッファに、送りかけの通知を max_frame × 2 byte を超えて
   ためず、書き込みで待たない。入らない通知は probe の中で捨てる（seq の抜けで分かる、§11.3）。シリアルの口では host の OS の受けの量（§3.4）も上限で、host が min_bytes で伝える。
3. 通知は、その fn の subscribe が来た経路に送る。

## 12. core（fn 0）の操作一覧

| op | 名前 | 要求 | 応答 | ロック | 要否 |
|---:|---|---|---|---|---|
| 0x01 | confirm | §7.1 | §7.1 | 不要 | 必須 |
| 0x02 | list | §7.2 | §7.2 | 不要 | 必須 |
| 0x03 | describe | §7.3 | §7.3 | 不要 | 必須 |
| 0x04 | plan_apply | role_assignment の TLV の並び | — | 必要 | plan の role があれば（§1.2） |
| 0x05 | plan_release | n(u8)、n × fn(u16) | — | 必要 | plan の role があれば（§1.2） |
| 0x10 | open | lease_ms(u32)、force(u8)、[TLV owner]（session_id は見出しのもの） | lease_ms(u32)、boot_id(u32)、[TLV] | open がロックを取る | 必須 |
| 0x11 | end | — | — | 必要 | 必須 |
| 0x12 | keepalive | — | — | 必要 | 必須 |
| 0x13 | lock_state | — | locked(u8)、remaining_ms(u32)、[TLV owner] | 不要 | 必須 |
| 0x30 | subscribe | §11.3 | — | 必要 | 必須 |
| 0x32 | unsubscribe | §11.3 | — | 必要 | 必須 |

線の試験と port_speed は、任意のインターフェース `oep.link`（[リンク](oep-if-link.ja.md)）である。

## 13. 拡張の規則（インターフェースの書き方）

標準インターフェースも独自のインターフェースも、次の規則で定義する。

1. **名前**: `oep.` は project が予約する。独自のインターフェースは逆 DNS（`io.github.<owner>.<name>` など）。名前は host が何に
   使うかで切る（probe のペリフェラルの名前にしない）。**1〜64 byte、使える文字は `a-z 0-9 - .`**（registry の `limits`）。
   名前の label はそれぞれ `a-z 0-9 -` の 1 文字以上で、`-` で始まらず `-` で終わらない。名前は label を 2 つ以上持つ。
2. **定義が決めるもの**: インターフェースの文書はどれも、次のチェックリストを埋める。
   - 名前と revision。
   - op の表: 番号、要求、応答、ロックの要否、どの op が必須でどれが任意か（任意の op は ops で宣言する、§1.2）。
   - 各 op の要求と応答の TLV（その op の文脈の tag の空間）。
   - 各 op の completed success、completed failed、completed partial の payload（§4.2）。
   - インターフェース自身の status の値（0x40〜0x7F）と reject reason（0x40〜0x7F）。
   - describe のインターフェース固有のタグ（0x40〜0x7F）と、plan の role の番号。
   - インターフェースが作る資源とその寿命（§9 の上で）。
   - 出来事の kind（0x01〜0x7F）とその payload、通知のデータの payload の形。
   - 読む側が、応答の enum の知らない値と知らない flags をどう扱うか（§2.4、§2.5）。
   - §4.3 の順の断り方の表。
   - 頼る外部の仕様と、その版と、使う部分（「参照する仕様」の節）。
3. **形の規則**: §2.3 のとおり（固定の形、足すものは TLV だけ、可変の並びの前に数を置き要素に長さを置かない、省略できるフィールドを置かない、安全の引数は critical）。
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
| [標準インターフェース: リンク](oep-if-link.ja.md) | `oep.link`（線の試験と port_speed） |

## 15. 規範ではない文書（ガイド）

これらは規則を足さない。

- [はじめに](getting-started.ja.md): いちばん小さい probe と host を、byte つきで。
- [host 開発ガイド](host-development-guide.ja.md)、[probe 開発ガイド](probe-development-guide.ja.md): 実装の実務。
- [適合](conformance.ja.md): probe と host のチェックリスト。
- [安全とセキュリティ](security.ja.md)、[用語集](glossary.ja.md)、[版と安定性](versioning.ja.md)。

## 16. 参照する仕様

OEP のフレームと message は、この文だけで定まる。USB の経路を出す probe は、次にも従う:

| 仕様 | 使う部分 |
|---|---|
| Universal Serial Bus Specification, Revision 2.0 | 列挙、device と interface の記述子、serial number の文字列、bulk 転送と長さ 0 のパケット（§3.1、§3.3） |
| USB Class Definitions for Communications Devices 1.2 とその PSTN subclass（CDC ACM） | USB CDC のシリアルの口の CDC ACM の機能: その interface、line coding、制御線（§3.3、§3.4） |
| Device Class Definition for HID 1.11 | vendor 定義の input と output の report、report ID、SET_REPORT（§3.1、§3.3） |
| Microsoft OS 2.0 Descriptors Specification | vendor bulk の interface の compatible ID `WINUSB`（§3.3） |
