# OEP インターフェース: probe の設定 v1

[English](oep-if-probe-config.md)

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](../docs/versioning.ja.md) §6）。本体は [OEP core](../docs/oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.probe.config` | 1 | probe の設定（plan、ラベル、空きのピン、スロット、シリアルの口に流すもの、Wi-Fi のネットワーク）と、その保存 | どの系統にも使う |

- **既定の値は持たない。** 項目はすべて host が設定し、probe は設定されたとおりに動く。設定されていない項目については何もしない。
- 設定を扱わない probe は、このインターフェースを list に出さない。
- 設定から入れた plan、スロットの接続、bind はセッションの資源ではない（core §9）。セッションが終わっても外さない。
- **起動の型（モード）は持たない。** 設定はどの経路からでも同じ操作で行い、set したものはすぐ効く。設定のための再起動は要らない。

## 1. 項目

**設定 = 項目（TLV）の並び**。tag はこの文脈の空間。項目ごとに**キー**があり、同じ tag の項目はキーで見分ける。

- **項目の channel**: label、idle、disable の項目の channel は、`channels`（fn 0 の describe の 0x43）未満で、probe が自分で使う channel でない。そうでなければ set は rejected unsupported（受け取ったままの項目の tag）。

| tag | 項目 | 値 | キー |
|---:|---|---|---|
| 0x01 | plan | fn(u16)、role(u8)、channel(u16)（1 項目 1 割り当て） | (fn, role, channel)（同じ fn の項目で、その fn の plan になる） |
| 0x02 | label | channel(u16)、text | channel |
| 0x03 | idle | channel(u16)、mode(u8: 0 Hi-Z、1 プルアップの入力、2 プルダウンの入力、3 出力 low、4 出力 high)、drive(u8)（4 byte） | channel |
| 0x04 | slot | §1.1 | slot |
| 0x05 | bind | §1.2 | port |
| 0x06 | uart | fn(u16)、baud(u32)、format(u8)（`oep.fixture.uart` の configure と同じ値） | fn |
| 0x07 | disable | channel(u16) | channel |
| 0x08 | wifi | §1.4 | index |

- どの項目もすぐ効く。扱う項目は describe の items で宣言し、宣言していない項目の set は rejected unsupported（payload の tag は受け取ったままの項目の tag、core §4.3）。
  項目についての rejected unsupported は、payload にその項目の受け取ったままの tag を載せる。
- **項目の値の長さ**: 項目の値は後ろに伸ばさない（core §2.3: 新しいフィールドは新しい項目の tag に置く）。probe が扱う項目で、値の長さが
  定義の長さ（可変の部分を持つ項目は、その数と長さが決める長さ）と違うものは、critical の bit によらず rejected malformed（core §2.3）。label の text は値の終わりまで続く。
- **plan**: その fn の plan_apply と同じ（[plan](oep-if-plan.ja.md) §2.1）。設定の plan は設定だけが変える: セッションの plan_release（n = 0 を含む）
  はそれを解かず、plan_apply がその fn を挙げたら rejected unavailable（[plan](oep-if-plan.ja.md) §2.3）。
- **label**: 設定で付けた channel の名前。get で読む（core の describe の label（0x46）は firmware が持つ固定の名前で、設定では
  変わらない。host は両方を合わせて使う。core §7.3: describe は宣言だけ）。text は 1〜32 byte（registry の `limits.label_max_bytes`。外れれば rejected malformed）。
- **uart**: その fn（`oep.fixture.uart`）の plan に RX か TX が付いた時点（設定の plan でも、セッションの plan_apply でも）で、
  configure 相当を掛ける。plan が無くても set は通る（掛かるのは plan が付いたとき）。セッションの configure は、plan を解くか
  probe が再起動するまで、この項目より勝つ。baud は set のときに実現できる値を確かめ、±5%（registry の `uart_baud_tolerance_pct`）を超えて外れれば rejected unsupported。
  format は configure の TLV format と同じ値。ピンの無い fn の configure は今どおり
  rejected unavailable（項目があっても変わらない）。
- **disable**: その channel を probe が**一切使わない**ようにする（ボードに出ていないピン、ほかの部品につながっているピン）。利用者が
  自分のボードに合わせて明示する。firmware が使えると宣言した channel（describe の role_channels など）を減らすだけで、firmware が
  使えないとしたピンを使えるようにはできない（それは自前のビルドで行う）。
  - 無効にした channel を指す要求（plan_apply、設定の plan、線の attach の pins と reset、scan の組、gpio など）は rejected unavailable
    （cause 5 設定が持つ、channel 付き）。scan の count = 0 の並びと、pins の無い attach の候補には入れない
    （候補がそれしか無ければ同じく cause 5）。同じ set の中で disable と、その channel を使う plan / slot を両方送った場合も cause 5。
  - firmware が宣言していない channel の disable は rejected unsupported（上の、項目の channel）。
  - probe はその channel の pin を駆動も設定もしない（起動時と解放時の空きの状態にもしない。リセットの後のまま）。
  - いま使われている channel（plan、接続、スロット。同じ set で外されるものは除く）を無効にする set は rejected unavailable
    （cause 1）。同じ channel の idle と disable を両方持つ設定は malformed。
  - unset で disable を外した channel は、すぐ空きの状態（idle か Hi-Z）になる。
  - describe は宣言だけなので変わらない（core §7.3）。host は get の disable を合わせて、使える channel を知る。
  - 保存すれば起動時に、空きの状態を掛けるより先に適用する。
- **idle**: plan にも接続にも使われていないピンの状態。起動時と、そのピンが解放されるたび（core §8）に、この状態にする。
  idle の項目（mode を問わない）を持つ channel は、count = 0 の scan と pins の無い attach の候補に入れない。その channel を名指す要求は、idle が出力（mode 3 / 4）なら rejected unavailable（cause 5）（[線とデバッグ](oep-if-debug.ja.md) §1）。
  mode 3 / 4 では、そのピンが空きの間ずっと、probe がその level で駆動する。idle が無いピンは Hi-Z。治具の配線で相手の入力が浮くピン（相手の RX につながる TX など）は、host が idle で明示し、保存する。
  出力の mode は、plan が持っていない間もある level を保たなければならない channel（target の電源のスイッチなど）のためにある。
  idle の項目の変更（set / unset）は、空いている channel にはすぐ効き、plan や接続が持つ channel には、次に空きになったときに効く。
  その channel を出力として駆動できない probe では、mode 3 / 4 の idle は rejected unsupported。そのプルを持たない channel では、mode 1 か 2 の idle は rejected unsupported（受け取ったままの項目の tag）。（参考）`oep.fixture.gpio` の無い probe では、どの channel がプルや出力を持つかを host が前もって知る方法は無い。
  （参考）出力の idle が target の出力とぶつからないようにするのは、配線の責任である。
  - **強さ**: drive（[fixture](oep-if-fixture.ja.md) §1.1 の強さの指定と同じ: 段の番号、0xFF は既定の段）。効くのは mode 3 / 4 だけで、mode 0〜2 では
    probe は drive を見ない。mode 3 / 4 で、段の数以上の drive（0xFF を除く）は rejected unsupported（受け取ったままの項目の tag）。drive_levels を宣言しない
    probe（`oep.fixture.gpio` の無い probe を含む）では、0xFF 以外の drive は rejected unsupported。
  - mode 3 / 4 の idle は、その level と強さを一緒に掛ける（起動時も解放のときも）。

### 1.1 slot（スロット）

スロットは、target のつながる**場所**の登録である（チップの登録ではない。チップを付け替えても登録は直さない）。

```text
slot(u8)、wire_fn(u16)、swdio(u16)、swclk(u16)、attach(u8)、retry_ms(u32)、max_speed_hz(u32)、idle_clock(u8)、mechanism(u8)、
name_len(u8)、name
```

| フィールド | 意味 |
|---|---|
| slot | スロットの番号（キー）。0 から、describe の slots_max 未満 |
| wire_fn | 線のインターフェースの fn。スロットが乗る線（`oep.wire.rvswd` / `oep.wire.swio`。[線とデバッグ](oep-if-debug.ja.md) §5: swd の connection にはスロットが乗らない）だけ。ほかは rejected unsupported |
| swdio、swclk | ピンの組。attach の pins と同じ（1 本の線は swclk = 0xFFFF）。その線が許す組でなければ rejected unsupported |
| attach | attach の方針: 0 host、1 at boot（§3.1） |
| retry_ms | at boot のスロットで、いないときに attach をやり直す間隔（ms）。0 はやり直さない。at boot でないスロットでは probe は見ない |
| max_speed_hz | そのスロットの attach に渡す線の速さの上限（Hz、attach の max_speed と同じ）。0 は上限なし。その線が守れない上限（決まった速さがそれより速い、min_clock_hz より遅い）は rejected unsupported |
| idle_clock | そのスロットの attach に渡す線の休ませ方（attach の idle_clock と同じ: 0 = high、1 = low）。`oep.wire.rvswd` だけが 1 を持てる（ほかの線で 1 は rejected unsupported。attach と同じ） |
| mechanism | コンソールの方式（`oep.target.console` の mechanism）、または **0xFF = コンソールなし**（bind に載せない、console を持たない probe）。その probe の console が宣言しない方式は rejected unsupported |
| name | スロットの名前。1〜32 byte で、使える文字は `a-z 0-9 - _` だけ（ほかは rejected malformed）。probe の中で重ならない（重なれば rejected malformed）。host がスロットを名指すのに使う（URL の中で encode が要らない文字だけ） |

- max_speed と idle_clock（[線とデバッグ](oep-if-debug.ja.md) §3 の attach の TLV と同じ）は target の性質で、probe が自分でスロットを attach するとき
  （at boot、やり直し）に使う。host の attach はそれぞれの TLV で自分の値を渡す（スロットの項目を既定には使わない）。host の attach が
  渡さない設定は、新しい connection では TLV の無いときの値、スロットの接続など既存の connection に加わるなら、その connection の今の
  設定のまま（[線とデバッグ](oep-if-debug.ja.md) §1）。
- 同じ wire_fn と同じピンの組のスロットを 2 つ作れない（設定どうしの矛盾: rejected malformed）。
- **スロットの項目を置き換えた・消したとき**: そのスロットが使っていた接続からスロットの分を外し（ほかに使うものが無ければ閉じる。
  target は reset しない、[線とデバッグ](oep-if-debug.ja.md) §2）、bind で開いていたコンソールのスロットの分を外す（mark closed 3）。
  置き換えた項目が at boot なら、新しい組で attach をやり直す。
- **スロットの接続**: 生きている接続のうち、wire_fn が同じでピンの組がスロットと一致するもの（誰が attach したかは問わない）。
- **at boot のスロットの数は、wire_fn ごとに、その線の max_connections まで**（[線とデバッグ](oep-if-debug.ja.md) §1）。超える set
  は rejected unavailable。スロットの並びの順は意味を持たない。
- 登録できる数は probe が describe の slots_max で宣言する。
- どの target がつながっているかは、host が connections の tid（[線とデバッグ](oep-if-debug.ja.md) §2.1）で確かめる。

### 1.2 bind（シリアルの口に何を流すか）

```text
port(u8)、kind(u8)、id(u16)
```

| フィールド | 意味 |
|---|---|
| port | シリアルの口の番号（core の describe の transport の index）。シリアルの口でなければ rejected unsupported。index は firmware の版を越えて変わらない（core §7.5） |
| kind、id | 口に流すストリーム。kind 1 = スロットのコンソール（id = slot）、kind 2 = fixture UART の受信（id = `oep.fixture.uart` の fn）。無いスロットを指せば rejected malformed（設定どうしの矛盾）、fn が無ければ unknown_function、fn が `oep.fixture.uart` でなければ rejected unsupported。mechanism 0xFF のスロットは載せられない（rejected malformed） |

- probe は、bind のストリームを口に流す。替えるときは host が bind を set し直す。
- **口から来た生のバイト**（transports §4 の、フレームの外のバイト）は、そのストリームの相手（コンソールなら console の write、
  fixture UART なら TX）に、相手が受け取れる分だけ渡す。受け取れない分は捨ててよい。
- **口の位置**: probe は bind ごとに、流すストリームの中の位置を持つ。口が受け取れる分だけ進め、口が読まれていなくても
  ストリームは捨てない。ストリームが口より丸ごと先に行ったら（あふれ）、口は残っている一番古いバイトまで飛ぶ。
- **セッションの間**（transports §4 で生の転送を止めた口）: 位置は進めない。セッションが終わったら、止めた位置から続ける（その間にあふれていれば、
  残っている一番古いバイトから）。
- スロットのストリームは、そのスロットがどれかの bind にあり、スロットの接続がある間、probe がその接続で
  コンソールを開いて流す。どの bind にも無いスロットのコンソールを probe は開かない。同じ connection と mechanism のストリームが
  あればそれを使う（[コンソール](oep-if-console.ja.md) §2）。bind はどの接続にも乗る（host が attach した接続にも）。この開いたコンソールは、スロットがその接続を使っているものに数える（[共通部品](oep-if-common.ja.md) §2）。
- fixture UART のストリームは、接続が無くても、その fn の plan に RX がある間は流れる（ストリームは plan が作り、plan を解くと消える。
  位置は起動の中で戻らない、[共通部品](oep-if-common.ja.md) §1.1。口の位置はストリームが消えたら進めない）。baud / format は uart の
  項目（§1）か、セッションの configure。
- DTR / RTS / 1200 baud の touch と CDC の line coding では何もしない（target も probe も reset せず、attach もせず、baud も変えない）。

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
- **passphrase は書くだけ**:
  - get は wifi の項目を passphrase なしで返す: pass_len は、passphrase があれば 0xFF、無ければ 0 で、後ろに何も付けない。
  - set の pass_len 0xFF は、その index の今の passphrase（無しを含む）を保つ。その index の項目が無ければ rejected malformed。だから get の
    答えの項目をそのまま set で送り返しても、何も変わらない。
  - probe は passphrase を、どの応答、出来事、データにも載せず、ログ（シリアルの口の生のバイトを含む）にも出さない。hash（§2）を
    passphrase の byte から作らない（ロック不要の get から passphrase を確かめられないため）。passphrase が変われば、ほかの変更と同じく hash は変わる。
  - host は passphrase を表示せず、ログに書かない。
- **つなぎ方**: probe は entry を index の順に試し、最初につながった（IPv4 のアドレスを得た）entry を使う。scan で ssid が見えなかった
  entry は飛ばしてよい。どれもつながらなければ、probe が決める時間だけ待って、初めからやり直す。つながりを失ったら、初めからやり直す。
- wifi の項目が 1 つも無ければ、probe は Wi-Fi を使わない（state 0）。
- set / unset が、使っている entry の項目を変えるか消したら、probe はその応答を送ってから、つながりを切り、新しい並びで初めからやり直す。
  ほかの変更ではつながりを保つ（新しい並びは次にやり直すときに使う）。
- つながりの今の様子は state の wifi の TLV（§3.3）で分かる。
- （参考）TCP の経路で使っている entry を変えると、その経路も切れる。応答は先に送るので set の結果は届く。host は新しいつながりで probe を
  見つけ直す（transports §3）。

## 2. 操作

| op | 名前 | 要求 | 応答 | ロック |
|---|---|---|---|---|
| 0x01 | get | first(u16) | more(u8)、hash(u32)、payload の終わりまでの項目（今の設定） | 不要 |
| 0x02 | set | 項目の並び | hash(u32)、[TLV] | 必要 |
| 0x03 | save | — | hash(u32)、[TLV] | 必要 |
| 0x04 | erase | — | — | 必要 |
| 0x05 | unset | n(u8)、n × (len(u8)、tag(u8)、key) | hash(u32)、[TLV] | 必要 |
| 0x06 | state | first_slot(u8)、first_bind(u8) | §3.3（今の状態）、ロック不要 | 不要 |

- **get**: 応答の項目は payload の終わりまで続く。
- **set は、要求に含まれる項目のキーごとに置き換える**（含まれないキーはそのまま。何回かの set に分けて積み上げられる）。
  plan の項目は fn ごとにまとめて、その fn の plan を置き換える。項目の順は意味を持たない。
- **unset はキーの項目を消す**（key は tag ごと: plan は fn(u16)（その fn の plan 全部）、label と idle は channel(u16)、slot は slot(u8)、
  bind は port(u8)、uart は fn(u16)、disable は channel(u16)、wifi は index(u8)。要素の len は key の byte 数で、tag は数えない。len を置くのはキーの長さが tag ごとに違うため）。検証と原子性は set と同じ。無いキーは
  何もせず成功。宣言していない項目の tag は rejected unsupported（payload の tag は受け取ったままの tag、core §4.3）。消したスロット・bind には §1.1 / §1.2 の後始末を適用する。
- 1 つの set の中で同じキー（plan は (fn, role, channel)）が 2 回出たら、要求全体を rejected malformed。
- set / unset の結果の設定全体が §1 の規則を満たさなければ（bind が消したスロットを指す、など）、何も変えずに rejected malformed。
- **set の原子性は、設定の検証と資源の予約（plan の適用、ピンの取り合いの確かめ）まで**。どれかが受け入れられなければ、何も変え
  ずに rejected。自動の attach とコンソールを開くこと（外の状態を変えること）は、set が済んだ後に行い、その結果は state（op 0x06、
  §3.3）の slot_state と bind_state で分かる（巻き戻さない）。
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
  fn、slot の wire_fn、bind の kind 2 の id、uart の fn。起動時に、その組を今の list で探して fn を読み替えてから適用する（set と get の形は
  fn のまま）。指す interface が無いか、revision が違えば、**保存全体を適用しない**（一部だけ入れると治具が半端に動く。storage の
  状態は「あり・読めない」、理由 2）。指していない interface の追加・削除・並べ替えは、保存に影響しない。
- 保存の形（probe の中の持ち方）は probe が決める。読み替えの規則だけが規範。
- 起動時に、保存した bind の port がこの firmware のシリアルの口でなければ、保存は読めないものになる（理由 2）。保存した項目のどれかの適用が断られたら、保存全体を適用しない（理由 3）。
- 起動時は、保存を今の設定にする（上の確かめを通ったとき）。そのとき probe は、ほかのどの項目より先に disable と idle を掛ける（mode 3 / 4 の出力の駆動を、その強さと一緒に含む）。
  保存を読めないときは適用せず、state で知らせる。

## 3. スロットの接続と状態

### 3.1 attach の方針

| attach | 接続を作る契機 |
|---:|---|
| 0 host | probe は自分から attach しない。host の attach でスロットの接続ができたら、bind はそれに乗る |
| 1 at boot | 起動時と、そのスロットの項目を set した直後。いなければ retry_ms ごとにやり直す（0 ならやり直さない） |

- **自動の attach（at boot）は止めない attach（method 0）だけ**で、スロットのピンの組で、[線とデバッグ](oep-if-debug.ja.md)
  §1 の規則どおりに行う。probe は at boot のスロットを、試せるときに attach する（試さなかったことは slot_state 1 と last_try_at_ns で分かる）。
- 席が埋まっていて host の attach がスロットの接続を閉じた（[線とデバッグ](oep-if-debug.ja.md) §1）とき、そのスロットはそのままに
  する（at boot でもやり直さない）。次の接続は、次の起動、そのスロットの set、または host の attach でできる。
- 接続が切れた（線が落ちた）スロットは、at boot なら retry_ms ごとにやり直す。
- **生存の確認**: at boot のスロットの接続は、probe が retry_ms ごとに DMSTATUS を読んで確かめてよい（書かない）。線切れを見たら
  接続を閉じて retry に入る（mechanism 0xFF のスロットでも、コンソールの読みが無くても「いない」が分かる）。retry_ms が 0 なら
  確かめない。
- policy が host のスロットを、probe は確かめない（線を駆動しない）。

### 3.2 状態

state（op 0x06、§3.3）の slot_state はロックなしで読める。host が線を駆動せずに target の有無を知る方法はこれだけである（線を駆動しないと
つながっているかは分からない）。

| state | 意味 |
|---:|---|
| 0 | 接続あり |
| 1 | いない（接続が無い。last_try_at_ns は最後に自動の attach を試した時刻） |

### 3.3 state（今の状態、ロック不要）

```text
要求: first_slot(u8)、first_bind(u8)
応答: more(u8)、storage_state(u8)、storage_hash(u32)、unreadable_reason(u8)、
      n_slots(u8)、n_slots × slot_state、n_binds(u8)、n_binds × bind_state、[TLV]
slot_state: slot(u8)、state(u8、§3.2)、connection(u16、無ければ 0)、last_try_at_ns(u64: 最後に自動の attach を試した時刻（probe の時計）、全ビット 1 は試していない)
bind_state: port(u8)、flow(u8: 0 流すものが無い / 1 流している / 2 セッションで止めている)
```

- **wifi**（応答の TLV 0x01）: wifi の項目を扱う probe は、どのページにもこれを載せる。値は state(u8)、entry(u8)、reason(u8)、rssi(i8)、ipv4(4 byte)
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
  （読めなければ 0）。unreadable_reason: 0 なし、1 形が読めない（壊れた、別の版の形）、2 指す interface が無い・revision が違う・bind の port がシリアルの口でない、
  3 適用が断られた（資源がぶつかる）。
- 登録したスロットを slot の昇順に first_slot 番目から、bind を port の昇順に first_bind 番目から、1 フレームに入る分だけ返す。
  more = 1 なら続きがあり、host は first_slot に n_slots を、first_bind に n_binds を足してもう一度聞く。
- 各ページは、storage_state、storage_hash、unreadable_reason を、そのページに答えたときの値で運ぶ。ページの間で違いうるし、host は最後のページのものを使う。slot と bind もページの間で変わりうる（ロックを持つ側の set や save、自動の attach）。ページをまたいで slot と bind の組が変わらないことが要る host は、ロックを持つ間にそのページをすべて読む（slot の状態はそれでも変わりうる: set、unset、save、erase ができるのはロックを持つ側だけで、自動の attach は状態を変えるが組は変えない）。

## 4. describe

describe は宣言だけ（core §7.3）。状態は state（§3.3）。

| tag | 名前 | 値 |
|---:|---|---|
| 0x40 | storage | max_bytes(u32、項目の TLV の byte 数の合計、1 以上)。save と erase を持つときに限り載る（ops、§2） |
| 0x41 | items | 扱う項目の tag の並び（u8） |
| 0x42 | slots_max | u8。登録できるスロットの数（0 はスロットを扱わない） |
| 0x46 | wifi_max | u8、1 以上。wifi の entry の数（index は 0〜wifi_max − 1）。items が wifi（0x08）を持つときに限り載る |

## 5. 安全（参考）

設定が probe の駆動する線にとって何を意味するかは [安全とセキュリティ](../docs/security.ja.md) §6 に、wifi の passphrase と経路の信頼は §1 と §8 にまとめる。
