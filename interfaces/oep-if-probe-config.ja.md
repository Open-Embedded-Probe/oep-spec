# OEP インターフェース: probe の設定 v1

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](../docs/versioning.ja.md) §6）。本体は [OEP core](../docs/oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.probe.config` | 1 | probe の設定（plan、ラベル、空きのピン、スロット、Wi-Fi のネットワーク）と、その保存 | どの系統にも使う |

- **既定の値は持たない。** 項目はすべて host が設定し、probe は設定されたとおりに動く。設定されていない項目については何もしない。
- 設定を扱わない probe は、このインターフェースを list に出さない。
- 永続設定の plan、slot、uart は preset である。実行時の資源は、host が明示的に作り、セッションの終わりに解放する（core §9）。
- **起動の型（モード）は持たない。** 設定はどの経路からでも同じ操作で行い、set した設定はすぐ get で読める。preset の実行は host が明示する。設定のための再起動は要らない。

## 1. 項目

**設定 = 項目（TLV）の並び**。tag はこの文脈の空間。項目ごとに**キー**があり、同じ tag の項目はキーで見分ける。

- **項目の channel**: label、idle、disable の項目の channel は、`channels`（fn 0 の describe の 0x43）未満で、probe が自分で使う channel でない。そうでなければ set は rejected unsupported（受け取ったままの項目の tag）。

| tag | 項目 | 値 | キー |
|---:|---|---|---|
| 0x01 | plan | fn(u16)、role(u8)、channel(u16)（1 項目 1 割り当て） | (fn, role, channel)（同じ fn の項目で、その fn の plan になる） |
| 0x02 | label | channel(u16)、text | channel |
| 0x03 | idle | channel(u16)、mode(u8: 0 Hi-Z、1 プルアップの入力、2 プルダウンの入力、3 出力 low、4 出力 high)、drive(u8)（4 byte） | channel |
| 0x04 | slot | §1.1 | slot |
| 0x06 | uart | fn(u16)、baud(u32)、format(u8)（`oep.fixture.uart` の configure と同じ値） | fn |
| 0x07 | disable | channel(u16) | channel |
| 0x08 | wifi | §1.4 | index |

- plan、slot、uart は host が読む preset であり、設定しただけでは target の線を駆動しない。label、disable、idle、wifi はそれぞれの規則で効く。扱う項目は describe の items で宣言し、宣言していない項目の set は rejected unsupported（payload の tag は受け取ったままの項目の tag、core §4.3）。
  項目についての rejected unsupported は、payload にその項目の受け取ったままの tag を載せる。
- **項目の値の長さ**: 項目の値は後ろに伸ばさない（core §2.3: 新しいフィールドは新しい項目の tag に置く）。probe が扱う項目で、値の長さが
  定義の長さ（可変の部分を持つ項目は、その数と長さが決める長さ）と違うものは、critical の bit によらず rejected malformed（core §2.3）。label の text は値の終わりまで続く。
- **plan**: host が plan_apply に使う割り当ての preset。保存だけではピンを予約しない。
- **label**: 設定で付けた channel の名前。get で読む（core の describe の label（0x46）は firmware が持つ固定の名前で、設定では
  変わらない。host は両方を合わせて使う。core §7.3: describe は宣言だけ）。text は 1〜32 byte（registry の `limits.label_max_bytes`。外れれば rejected malformed）。
- **uart**: host が configure に使う baud / format の preset。設定だけでは configure しない。
  baud と format の有効性は set で確かめる。実行時の configure は通常のセッション所有である。
- **disable**: その channel を probe が**一切使わない**ようにする（ボードに出ていないピン、ほかの部品につながっているピン）。利用者が
  自分のボードに合わせて明示する。firmware が使えると宣言した channel（describe の role_channels など）を減らすだけで、firmware が
  使えないとしたピンを使えるようにはできない（それは自前のビルドで行う）。
  - 無効にした channel を指す要求（plan_apply、線の attach の pins と reset、scan の組、gpio など）は rejected unavailable
    （cause 5 設定が持つ、channel 付き）。preset は使用中の資源として数えない。
  - firmware が宣言していない channel の disable は rejected unsupported（上の、項目の channel）。
  - probe はその channel の pin を駆動も設定もしない（起動時と解放時の空きの状態にもしない。リセットの後のまま）。
  - いま使われている channel（実行中の plan、接続）を無効にする set は rejected unavailable
    （cause 1）。同じ channel の idle と disable を両方持つ設定は malformed。
  - unset で disable を外した channel は、すぐ空きの状態（idle か Hi-Z）になる。
  - describe は宣言だけなので変わらない（core §7.3）。host は get の disable を合わせて、使える channel を知る。
  - 保存すれば起動時に、空きの状態を掛けるより先に適用する。
- **idle**: plan にも接続にも使われていないピンの状態。起動時と、そのピンが解放されるたび（core §8）に、この状態にする。
  その channel を名指す要求は、idle が出力（mode 3 / 4）なら rejected unavailable（cause 5）（[線とデバッグ](oep-if-debug.ja.md) §1）。
  mode 3 / 4 では、そのピンが空きの間ずっと、probe がその level で駆動する。idle が無いピンは Hi-Z。治具の配線で相手の入力が浮くピン（相手の RX につながる TX など）は、host が idle で明示し、保存する。
  出力の mode は、plan が持っていない間もある level を保たなければならない channel（target の電源のスイッチなど）のためにある。
  idle の項目の変更（set / unset）は、空いている channel にはすぐ効き、plan や接続が持つ channel には、次に空きになったときに効く。
  その channel を出力として駆動できない probe では、mode 3 / 4 の idle は rejected unsupported。そのプルを持たない channel では、mode 1 か 2 の idle は rejected unsupported（受け取ったままの項目の tag）。（参考）`oep.fixture.gpio` の無い probe では、どの channel がプルや出力を持つかを host が前もって知る方法は無い。
  （参考）出力の idle が target の出力とぶつからないようにするのは、配線の責任である。
  - **強さ**: drive（[fixture](oep-if-fixture.ja.md) §1.1 の強さの指定と同じ: 段の番号、0xFF は既定の段）。効くのは mode 3 / 4 だけで、mode 0〜2 では
    probe は drive を見ない。mode 3 / 4 で、段の数以上の drive（0xFF を除く）は rejected unsupported（受け取ったままの項目の tag）。drive_levels を宣言しない
    probe（`oep.fixture.gpio` の無い probe を含む）では、0xFF 以外の drive は rejected unsupported。
  - mode 3 / 4 の idle は、その level と強さを一緒に掛ける（起動時も解放のときも）。

### 1.1 slot（配線の preset）

スロットは target を接続する場所の記述である。probe は自動 attach、再試行、コンソールの自動 open をしない。

```text
slot(u8)、wire_fn(u16)、swdio(u16)、swclk(u16)、max_speed_hz(u32)、idle_clock(u8)、mechanism(u8)、name_len(u8)、name
```

- slot は 0 から slots_max 未満。wire_fn は `oep.wire.*` の fn。ピンの組はその wire の宣言に一致する。
- max_speed_hz は 1 以上で attach の max_speed に使う。idle_clock はその wire の attach が扱う値。
- mechanism は console が宣言する方式、または 0xFF（console なし）。console を扱えない wire では 0xFF。
- name は 1〜32 byte の `a-z 0-9 - _` で、probe の設定内で重ならない。値や長さの誤りは malformed、非対応の機能は unsupported。
- host は get で読み、pins、max_speed、必要な設定を明示して attach する。接続の有無は wire の connections で確認する。
- set / unset で slot を変えても、実行中の connection と stream は変わらない。slots_max は preset の保存数で、接続数の上限とは別である。

### 1.2 生データの経路

raw endpoint の設定は OEP core の外で行う。OEP のシリアル経路へ bind する項目は持たない。

### 1.3 線の名前（label の決まり）

label（設定の label の項目、§1 と、firmware の label、core の describe の label（0x46））の text のうち、次の名前は線の役目を表す。

| 名前 | 線 | 使うもの |
|---|---|---|
| `nrst` | target のリセットの線 | host |
| `power_hi` | high のとき target の電源が入る線 | host |
| `power_lo` | low のとき target の電源が入る線 | host |

- **スロットの線の探し方**（名前 N、スロットの name S）。次の順に探し、channel がちょうど 1 つ見つかった段で止める:
  - (a) `S.N` に等しい設定の label;
  - (b) 設定が持つスロットの項目が 1 つ以下のときだけ、`N` に等しい設定の label;
  - (c) 設定が持つスロットの項目が 1 つ以下のときだけ、`N` に等しい firmware の label（fn 0 の describe、0x46）。
- 2 つ以上の channel が見つかった段で、線なしとして探すのを終える。どの段でも見つからなければ、そのスロットにその線は無い。text と名前は、ASCII の大文字と小文字を区別せずに比べる。
- スロットの項目の無い設定では、段 (b) と (c) で、probe につながる target のその線が見つかる。
- 表に無い label の text は、役目を表さない（名前でしかない）。標準の名前は registry（`oep.probe.config` の `[line_names]`）に並べる。足しても revision は変わらない（core §2.7）。標準でない役目の名前は `x-` で始める（例 `x-acme-boot0`）。標準の名前は `x-` で始まらず、どの名前も `.` を含まない（`S.N` が使う）。
- probe はこれらの名前で線を自分から動かさない。host はこの探し方で線を見つける。

### 1.4 wifi（Wi-Fi のネットワーク）

probe が Wi-Fi でつなぐネットワークの並び。probe は動く場所によって違うネットワークに会うので、entry を複数持ち、順に試す。

```text
index(u8)、ssid_len(u8)、ssid、pass_len(u8)、passphrase
```

| フィールド | 意味 |
|---|---|
| index | entry の番号（キー）で、試す順。0 から、describe の wifi_max 未満（ほかは rejected unsupported、受け取ったままの項目の tag） |
| ssid | ネットワークの名前。1〜32 byte（registry の `limits.wifi_ssid_max_bytes`。ほかは rejected malformed）。probe が扱えない ssid は rejected unsupported（受け取ったままの項目の tag） |
| pass_len、passphrase | pass_len 0 は passphrase なし（開いたネットワーク）。8〜63 は 0x20〜0x7E の byte の passphrase。64 は 16 進の数字（`0-9 a-f A-F`）64 文字の鍵。0xFF は下の「書くだけ」で、後ろに何も付けない。ほかの長さと byte は rejected malformed |

- 値の長さは 3 + ssid_len + passphrase の長さ（pass_len 0xFF では 0）。保存の max_bytes（§2、§4）は passphrase を含む形で数える。
- **max_frame**: items に wifi を宣言する probe は、どの経路でも confirm の max_frame を 112 以上にする（registry の `limits.wifi_min_max_frame`）。
  いちばん長い wifi の項目（32 byte の ssid と 64 文字の鍵）1 つの set が、要求の見出し 10 + 項目の TLV の見出し 3 + 値 99 = 112 byte で、
  これでどの有効な項目も 1 つの set で送れる。
- **passphrase は書くだけ**:
  - get は wifi の項目を passphrase なしで返す: pass_len は、passphrase があれば 0xFF、無ければ 0 で、後ろに何も付けない。
  - set の pass_len 0xFF は、その index の今の passphrase（無しを含む）を保つ。その index の項目が無ければ rejected malformed。だから get の
    答えの項目をそのまま set で送り返しても、何も変わらない。
  - probe は passphrase を、どの応答、出来事、データにも載せず、ログにも出さない。hash（§2）を
    passphrase の byte から作らない（ロック不要の get から passphrase を確かめられないため）。passphrase が変われば、ほかの変更と同じく hash は変わる。
  - host は passphrase を表示せず、ログに書かない。
- **つなぎ方**: probe は entry を index の順に試し、最初につながった（IPv4 のアドレスを得た）entry を使う。つながらないとき、
  つながりを失ったときは、また試す（間隔は probe が決める）。
- wifi の項目が 1 つも無ければ、probe は Wi-Fi を使わない（state 0）。
- set / unset が、使っている entry の項目を変えるか消したら、probe はその応答を送ってから、つながりを切り、新しい並びで初めからやり直す。
  ほかの変更ではつながりを保つ（新しい並びは次にやり直すときに使う）。
- つながりの今の様子は state の wifi の TLV（§3）で分かる。
- （参考）TCP の経路で使っている entry を変えると、その経路も切れる。応答は先に送るので set の結果は届く。host は新しいつながりで probe を
  見つけ直す（transports §3）。

## 2. 操作

| op | 名前 | 要求 | 応答 | ロック |
|---|---|---|---|---|
| 0x10 | get | first(u16) | more(u8)、hash(u32)、payload の終わりまでの項目（今の設定） | 不要 |
| 0x11 | set | 項目の並び | hash(u32)、[TLV] | 必要 |
| 0x12 | save | — | hash(u32)、[TLV] | 必要 |
| 0x13 | erase | — | — | 必要 |
| 0x14 | unset | n(u8)、n × (len(u8)、tag(u8)、key) | hash(u32)、[TLV] | 必要 |
| 0x15 | state | — | §3（今の状態）、ロック不要 | 不要 |

- **get**: 応答の項目は payload の終わりまで続く。
- **set は、要求に含まれる項目のキーごとに置き換える**（含まれないキーはそのまま。何回かの set に分けて積み上げられる）。
  plan の項目は fn ごとにまとめて、その fn の plan を置き換える。項目の順は意味を持たない。
- **unset はキーの項目を消す**（key は tag ごと: plan は fn(u16)（その fn の plan 全部）、label と idle は channel(u16)、slot は slot(u8)、
  uart は fn(u16)、disable は channel(u16)、wifi は index(u8)。要素の len は key の byte 数で、tag は数えない。len を置くのはキーの長さが tag ごとに違うため）。検証と原子性は set と同じ。無いキーは
  何もせず成功。宣言していない項目の tag は rejected unsupported（payload の tag は受け取ったままの tag、core §4.3）。preset の削除は実行中の資源を解放しない。
- 1 つの set の中で同じキー（plan は (fn, role, channel)）が 2 回出たら、要求全体を rejected malformed。
- set / unset の結果の設定全体が §1 の規則を満たさなければ（名前の重複など）、何も変えずに rejected malformed。
- **set / unset は原子的**: 変更後の設定全体を検証してから置き換える。disable / idle と実行中の資源の競合も、副作用の前に確かめる。
  失敗すれば今の設定と実行中の資源を保つ。preset を保存しても attach、plan_apply、configure は行わない。
- **どの項目も tag ごとに形が一つ**（§1）なので、get は各項目をその形で、host が送ったとおりに、critical の bit を外して返す（wifi の passphrase は返さない、§1.4）。
- **hash** は今の設定を表す u32 で、作り方は probe が決める。今の設定が変われば hash も変わる（host は hash を計算しない）。get は項目を
  tag の昇順に、同じ tag の中はキー（plan は (fn, role, channel)）の昇順に並べ、first 番目の項目から返す。キーは数として比べ、複数のフィールドのキーは
  最初のフィールドから順に比べる。どのページも同じ hash を返す（変わっていたら host は最初から読み直す）。
- **save は host の明示的な操作だけ**で、今の設定をそのまま保存する（同じ内容なら書かない）。書いている間はほかの要求に答えない
  （core の max_op_ms の対象。host の待ちは、save の引数の時間として max_op_ms を数える、core §4.4）。**保存は丸ごと置き換え**で、途中で電源が落ちても前の保存か新しい保存のどちらかが読める。describe の
  `max_bytes` は項目の TLV の byte 数の合計で、それ以下の設定は必ず保存できる（識別子の表の分は probe が差し引いて宣言する）。超えれば
  rejected unavailable（cause 3）。erase は保存を消す（今の設定は変えない。消した後は storage_state 0、storage_hash 0）。save と erase は
  任意で組で持ち、describe の ops で宣言する（core §1.2）。保存の無い probe はそれらに unknown_operation で答える。describe の storage の tag は
  save を持つときに限り載る。get、set、unset、state は必須。
- **保存は、項目が指す interface を (name、instance、revision) で持つ**（fn の番号は起動ごとに変わりうるため）。指す fn は、plan の
  fn、slot の wire_fn、uart の fn。起動時に、その組を今の list で探して fn を読み替えてから適用する（set と get の形は
  fn のまま）。指す interface が無いか、revision が違えば、**保存全体を適用しない**（一部だけ入れると治具が半端に動く。storage の
  状態は「あり・読めない」、理由 2）。指していない interface の追加・削除・並べ替えは、保存に影響しない。
- 保存の形（probe の中の持ち方）は probe が決める。読み替えの規則だけが規範。
- 起動時は、保存を今の設定にする（上の確かめを通ったとき）。そのとき probe は、ほかのどの項目より先に disable と idle を掛ける（mode 3 / 4 の出力の駆動を、その強さと一緒に含む）。
  保存を読めないときは適用せず、state で知らせる。

## 3. state（保存と probe 自身の状態、ロック不要）

```text
要求: —
応答: storage_state(u8)、storage_hash(u32)、unreadable_reason(u8)、[TLV]
```

state は接続や slot の実行状態を持たない。実行中の資源は wire の connections、console の streams、各 fixture の status で読む。

- **wifi**（応答の TLV 0x01）: wifi の項目を扱う probe は、応答にこれを載せる。値は state(u8)、entry(u8)、reason(u8)、rssi(i8)、ipv4(4 byte)
  の 8 byte。

  | フィールド | 意味 |
  |---|---|
  | state | 0 切（wifi の項目が無い）、1 つなごうとしている、2 つながっている、3 どれもつながらず、やり直しを待っている |
  | entry | state 1 では試している、state 2 では使っている entry の index。ほかは 0xFF |
  | reason | 最後の失敗の理由: 0 なし、1 ネットワークが見つからない、2 認証の失敗、3 アドレスが来ない、4 そのほか。つながったら 0 |
  | rssi | state 2 で、受けている電波の強さ（dBm） |
  | ipv4 | state 2 で、probe の IPv4 のアドレス（`a.b.c.d` を a から順に） |

  state 2 でないとき、rssi と ipv4 は 0。
- storage_state: 0 保存なし、1 あり・適用済み、2 あり・読めない。storage_hash は、保存した設定を今の設定にした時（起動時の適用か save）の hash で、その後に今の設定が変わっていなければ get の hash と同じ
  （読めなければ 0）。unreadable_reason: 0 なし、1 形が読めない（壊れた、別の版の形）、2 指す interface が無い・revision が違う、
  3 適用が断られた（資源がぶつかる）。
## 4. describe

describe は宣言だけ（core §7.3）。状態は state（§3）。

| tag | 名前 | 値 |
|---:|---|---|
| 0x40 | storage | max_bytes(u32、項目の TLV の byte 数の合計、1 以上)。save と erase を持つときに限り載る（ops、§2） |
| 0x41 | items | 扱う項目の tag の並び（u8） |
| 0x42 | slots_max | u8。登録できるスロットの数（0 はスロットを扱わない） |
| 0x46 | wifi_max | u8、1 以上。wifi の entry の数（index は 0〜wifi_max − 1）。items が wifi（0x08）を持つときに限り載る |

## 5. 安全（参考）

設定が probe の駆動する線にとって何を意味するかは [安全とセキュリティ](../docs/security.ja.md) §6 に、wifi の passphrase と経路の信頼は §1 と §8 にまとめる。
