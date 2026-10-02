# OEP 標準インターフェース: probe の設定 v1

[English](oep-if-probe-config.md)

状態: **規範**（2026-09-29 に組み直し。2026-10-01 に[ゼロベースの再検討](v1-zero-base-proposal.ja.md)を反映）。本体は [OEP core](oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。経緯と
実験は [シリアルの口と永続化](probe-cdc-and-persistence.ja.md)。

| 名前 | revision | 役割 |
|---|---:|---|
| `oep.probe.config` | 1 | probe の設定（plan、ラベル、空きのピン、スロット、シリアルの口に流すもの）と、その保存 |

- **既定の値は持たない。** 項目はすべて host が設定し、probe は設定されたとおりに動く。設定されていない項目については何もしない。
- 設定を扱わない probe は、このインターフェースを list に出さない。
- 設定から入れた plan、スロットの接続、bind はセッションの資源ではない（core §9）。lease の期限切れでも外さない。
- **起動の型（モード）は持たない。** 設定はどの経路からでも同じ操作で行い、set したものはすぐ効く。設定のための再起動は要らない。

## 1. 項目

**設定 = 項目（TLV）の並び**。tag はこの文脈の空間。項目ごとに**キー**があり、同じ tag の項目はキーで見分ける。

- **項目の channel**: label、idle、disable の項目の channel は、`channels`（fn 0 の describe の 0x43）未満で、`reserved`（0x44）に無い。そうでなければ set は rejected unsupported（受け取ったままの項目の tag）。

| tag | 項目 | 値 | キー |
|---:|---|---|---|
| 0x01 | plan | fn(u16)、role(u8)、channel(u16)（1 項目 1 割り当て） | (fn, role, channel)（同じ fn の項目で、その fn の plan になる） |
| 0x02 | label | channel(u16)、text | channel |
| 0x03 | idle | channel(u16)、mode(u8: 0 Hi-Z、1 プルアップの入力、2 プルダウンの入力、3 出力 low、4 出力 high)、[drive_kind(u8)、drive_value(u16)] | channel |
| 0x04 | slot | §1.1 | slot |
| 0x05 | bind | §1.2 | port |
| 0x06 | uart | fn(u16)、baud(u32)、format(u8)（`oep.fixture.uart` の configure と同じ値） | fn |
| 0x07 | disable | channel(u16) | channel |

- どの項目もすぐ効く。扱う項目は describe の items で宣言し、宣言していない項目の set は rejected unsupported（payload の tag は受け取ったままの項目の tag、core §4.3）。tag 0x7E は応答の
  メタ情報のために予約。
- **plan**: その fn の plan_apply と同じ（core §8）。設定の plan は設定だけが変える: セッションの plan_release（n = 0 を含む）
  はそれを解かず、plan_apply がその fn を挙げたら rejected unavailable（core §8）。
- **label**: 設定で付けた channel の名前。get で読む（core の describe の label（0x46）は firmware が持つ固定の名前で、設定では
  変わらない。host は両方を合わせて使う。core §7.3: describe は宣言だけ）。text: 1〜32 byte（registry の `limits.label_max_bytes`）の正しい UTF-8 で、C0 の制御文字（0x00〜0x1F）と 0x7F を含まない。そうでなければ rejected malformed。
- **uart**: その fn（`oep.fixture.uart`）の plan に RX か TX が付いた時点（設定の plan でも、セッションの plan_apply でも）で、
  configure 相当を掛ける。plan が無くても set は通る（掛かるのは plan が付いたとき）。セッションの configure は、plan を解くか
  probe が再起動するまで、この項目より勝つ。baud は set のときに実現できる値を確かめ、±5% を超えて外れれば rejected unsupported。
  format は configure の TLV format と同じ値（使っていない値と予約のビットは rejected unsupported、core §2.5）。ピンの無い fn の configure は今どおり
  rejected unavailable（項目があっても変わらない）。CDC の口の line coding は fixture UART に写さない（OEP の configure とこの項目
  だけが効く）。
- **disable**: その channel を probe が**一切使わない**ようにする（ボードに出ていないピン、ほかの部品につながっているピン）。利用者が
  自分のボードに合わせて明示する。firmware が使えると宣言した channel（describe の role_channels など）を減らすだけで、firmware が
  使えないとしたピンを使えるようにはできない（それは自前のビルドで行う）。
  - 無効にした channel を指す要求（plan_apply、設定の plan、線の attach の pins と reset、scan の組、gpio など）は rejected unavailable
    （cause 5 設定が持つ、channel と holder_kind 6 無効化 付き）。scan の count = 0 の並びと、pins の無い attach の候補には入れない
    （候補がそれしか無ければ同じく cause 5）。同じ set の中で disable と、その channel を使う plan / slot を両方送った場合も cause 5。
  - firmware が宣言していない channel の disable は rejected unsupported（上の、項目の channel）。
  - probe はその channel の pin を駆動も設定もしない（起動時と解放時の空きの状態にもしない。リセットの後のまま）。
  - いま使われている channel（plan、接続、スロット。同じ set で外されるものは除く）を無効にする set は rejected unavailable
    （cause 1）。同じ channel の idle と disable を両方持つ設定は malformed。
  - unset で disable を外した channel は、すぐ空きの状態（idle か Hi-Z）になる。
  - describe は宣言だけなので変わらない（core §7.3）。host は get の disable を合わせて、使える channel を知る。
  - 保存すれば起動時に、空きの状態を掛けるより先に適用する。
- **idle**: plan にも接続にも使われていないピンの状態。起動時と、そのピンが解放されるたび（core §8）に、この状態にする。
  idle の項目（mode を問わない）を持つ channel は、count = 0 の scan と pins の無い attach の候補に入れない。その channel を名指す要求は、idle が出力（mode 3 / 4）なら rejected unavailable（cause 5、holder_kind 7）（[線とデバッグ](oep-if-debug.ja.md) §1）。
  mode 3 / 4 では、そのピンが空きの間ずっと、probe がその level で駆動する。idle が無いピンは Hi-Z。治具の配線で相手の入力が浮くピン（相手の RX につながる TX など）は、host が idle で明示し、保存する。
  出力の mode は、plan が持っていない間もある level を保たなければならない channel（target の電源のスイッチなど）のためにある。
  idle の項目の変更（set / unset）は、空いている channel にはすぐ効き、plan や接続が持つ channel には、次に空きになったときに効く。
  その channel を出力として駆動できない probe では、mode 3 / 4 の idle は rejected unsupported。そのプルを持たない channel では、mode 1 か 2 の idle は rejected unsupported（受け取ったままの項目の tag）。（参考）`oep.fixture.gpio` の無い probe では、どの channel がプルや出力を持つかを host が前もって知る方法は無い。mode が 5 以上なら rejected unsupported（受け取ったままの項目の tag、core §2.5）。
  （参考）出力の idle が target の出力とぶつからないようにするのは、配線の責任である。
  - **強さ（任意）**: mode の後ろに drive_kind(u8)、drive_value(u16) を置ける（[fixture](oep-if-fixture.ja.md) §1.1 の強さの指定と同じ
    kind と value）。置かなければ既定の段。置けるのは mode 3 / 4 だけで、mode 0〜2 で置けば rejected malformed（mode が 5 以上なら mode について rejected unsupported、core §4.3）。値の長さが 4 か 5
    byte なら rejected malformed。未定義の drive_kind（2 以上）は rejected unsupported（受け取ったままの項目の tag。後の revision が定めうる、core §2.5）。`oep.fixture.gpio` の describe が drive_levels を宣言する probe では、
    kind 0 で drive_value が段の数以上なら rejected unsupported。drive_levels を宣言しない probe（`oep.fixture.gpio` の無い probe を
    含む）は、このフィールドを持つが効かせない（強さは既定のまま）。
    drive_value の後ろ（値の 7 byte 目から）は、後から足すフィールドの場所（core §2.3。probe は読み飛ばし、§2 のとおり切らずに持つ）。
    （参考）gpio の set の drive の TLV が範囲外の段を無視するのと違い、ここで断るのは、保存して起動のたびに使う設定の誤りを、書いたときに
    知らせるためである。
  - mode 3 / 4 の idle は、その level と強さを一緒に掛ける（起動時も解放のときも）。

### 1.1 slot（スロット）

スロットは、target のつながる**場所**の登録である（チップの登録ではない。チップを付け替えても登録は直さない）。

```text
slot(u8)、wire_fn(u16)、swdio(u16)、swclk(u16)、attach(u8)、retry_ms(u32)、max_speed_hz(u32)、idle_clock(u8)、mechanism(u8)、
name_len(u8)、name、
lock_len(u8)、lock_scheme(u8)、lock_mask(n byte)、lock_value(n byte)、
[boot_reset(u8)]
```

lock_len は錠の部分（lock_scheme から lock_value まで）の長さ。0 は錠なし（lock_scheme 以降を置かない）。錠の後ろに任意の
boot_reset を置ける（置かなければ 0）。その後ろは、後から足すフィールドの場所（core §2.3。読む側は知らない後ろを飛ばす）。

| フィールド | 意味 |
|---|---|
| slot | スロットの番号（キー）。0 から、describe の slots_max 未満 |
| wire_fn | 線のインターフェースの fn。**target_id の scheme を持つ線**（`oep.wire.rvswd` / `oep.wire.swio`）だけ。ほか（`oep.wire.swd`）は rejected unsupported |
| swdio、swclk | ピンの組。attach の pins と同じ（1 本の線は swclk = 0xFFFF）。その線が許す組でなければ rejected unsupported |
| attach | attach の方針: 0 host、1 at boot（§3.1）。2 以上は rejected unsupported（core §2.5） |
| retry_ms | at boot のスロットで、いないときに attach をやり直す間隔（ms）。0 はやり直さない。at boot でなければ 0（ほかは rejected malformed） |
| max_speed_hz | そのスロットの attach に渡す線の速さの上限（Hz、attach の max_speed と同じ）。0 は上限なし。その線が守れない上限（決まった速さがそれより速い、min_clock_hz より遅い）は rejected unsupported |
| idle_clock | そのスロットの attach に渡す線の休ませ方（attach の idle_clock と同じ: 0 = high、1 = low）。`oep.wire.rvswd` だけが 1 を持てる（ほかの線で 1 は rejected unsupported。attach と同じ）。2 以上は rejected unsupported（core §2.5） |
| mechanism | コンソールの方式（`oep.target.console` の mechanism）、または **0xFF = コンソールなし**（bind に載せない、console を持たない probe）。その probe の console が宣言しない方式は rejected unsupported |
| name | スロットの名前。1〜32 byte で、使える文字は `a-z 0-9 - _` だけ（ほかは rejected malformed）。probe の中で重ならない（重なれば rejected malformed）。host がスロットを名指すのに使い（IDE の address `oep://<unit_id>/<name>` にそのまま入る。unit_id は core §7.5。どちらも URL の中で encode が要らない文字だけ）、mixed の行の印（§1.2）にも使う |
| lock_len | 錠の部分の長さ。0（錠なし）か 1 + 2n（n ≥ 1）。ほかは rejected malformed |
| lock_scheme | 錠があるときだけ。target_id の scheme（[線とデバッグ](oep-if-debug.ja.md) §1）。0 は置かない（錠なしは lock_len 0）。その線が持たない scheme は、定義にあってもなくても（core §2.5）rejected unsupported |
| lock_mask、lock_value | 錠があるときだけ。同じ長さ n = (lock_len − 1) / 2。**n はその scheme の値の長さと同じ**（scheme 1 は 4。違えば rejected malformed。長さは registry の `[common.enum.target_id_len]`）。バイトの並びは attach の応答の target_id の値と同じ（scheme 1 なら u32 の little endian） |
| boot_reset | 任意。起動時の自動の attach に線の応答が無かったとき、リセットの線を使ってもう 1 回 attach するか（§3.1）: 0 しない、1 する。置かなければ 0。2 以上は rejected malformed。at boot でないスロットで 1 は rejected malformed |

- max_speed と idle_clock は target の性質で（[線とデバッグ](oep-if-debug.ja.md) §3）、probe が自分でスロットを attach するとき
  （at boot、やり直し）に使う。host の attach はそれぞれの TLV で自分の値を渡す（スロットの値は使わない）。
- 同じ wire_fn と同じピンの組のスロットを 2 つ作れない（設定どうしの矛盾: rejected malformed）。
- **スロットの項目を置き換えた・消したとき**: そのスロットが使っていた接続からスロットの分を外し（ほかに使うものが無ければ閉じる。
  target は reset しない、[線とデバッグ](oep-if-debug.ja.md) §2）、bind で開いていたコンソールのスロットの分を外す（mark closed 3）。
  置き換えた項目が at boot なら、新しい組で attach をやり直す。
- **スロットの接続**: 生きている接続のうち、wire_fn が同じでピンの組がスロットと一致するもの（誰が attach したかは問わない）。
- **錠**: スロットの接続の target_id（attach の応答の TLV 0x10）が、scheme が lock_scheme と同じで、値と lock_mask のビットごとの
  AND が lock_value と一致するときだけ、錠が合う。錠の無いスロットは常に合う。比べ方（どのビットを無視するか）は host が mask で
  決める（例: 識別子の下位 byte のビット [7:4] がリビジョンで、それを無視するなら mask 0xFFFFFF0F）。
- **at boot のスロットの数は、wire_fn ごとに、その線の max_connections まで**（[線とデバッグ](oep-if-debug.ja.md) §1）。超える set
  は rejected unavailable。スロットの並びの順は意味を持たない。
- 登録できる数は probe が describe の slots_max で宣言する。
- スロットは 2 本のピンの線を指す。組が 2 本のピンでない線は、スロットをその線に定めるときに新しい項目の tag を持つ。

### 1.2 bind（シリアルの口に何を流すか）

```text
port(u8)、mode(u8)、selected(u8)、n(u8)、n × (len(u8)、kind(u8)、id(u16))
```

| フィールド | 意味 |
|---|---|
| port | シリアルの口の番号（core の describe の transport の index）。シリアルの口でなければ rejected unsupported。index は firmware の版を越えて変わらない（core §7.5） |
| mode | 0 last-reset、1 manual、2 mixed（下）。describe の bind_modes に無い mode は rejected unsupported |
| selected | manual の選択（並びの中の番号、n 未満。外れていれば rejected malformed）。last-reset と mixed では 0 を送り、probe は見ない |
| n、並び | 流すストリーム（n ≥ 1）。各要素の前に要素の長さ len を置く（応答の並びと同じ形、core §2.3）。len は 3 以上（3 未満は rejected malformed）で、probe は 3 byte より後ろを読み飛ばす。host は今は 3 を送る。kind 1 = スロットのコンソール（id = slot）、kind 2 = fixture UART の受信（id = `oep.fixture.uart` の fn）。ほかの kind は rejected unsupported（core §2.5）。無いスロットを指せば rejected malformed（設定どうしの矛盾）、fn が無ければ unknown_function、fn が `oep.fixture.uart` でなければ rejected unsupported。mechanism 0xFF のスロットは載せられない（rejected malformed） |

| mode | 口に流すもの | 口から来た生のバイト |
|---|---|---|
| **last-reset** | 選ばれているストリーム。選択は、並びの中のスロットの target を host が reset したときにそのスロットへ替わる（下）。起動時と set の直後は並びの先頭 | 選ばれているストリームへ |
| **manual** | selected のストリーム。替えるのは bind の set だけ | 選ばれているストリームへ |
| **mixed** | 並びのすべて。ストリームごとに行をため、行が閉じたら `[name] ` を前に付けて流す | 捨てる（受信専用） |

- **host の reset として数えるもの**: スロットの接続の上の `oep.target.riscv-dm` の reset と、`oep.wire.*` の attach の reset TLV
  （[線とデバッグ](oep-if-debug.ja.md)）。probe 自身の attach、target の自己リセット、dmi で書いた ndmreset、`oep.fixture.gpio`
  などで動かしたリセットの線は数えない。選ばれた target の接続が切れても、選択は替えない。
- 並びが 1 つなら、どの mode でもそれが流れる（1 つのときと 2 つ以上のときで動きが変わらない）。
- **mixed の行**: LF で閉じる。閉じない出力は、128 byte たまるか、最後のバイトから 100 ms 静かだったら閉じる。name はスロットの
  name。fixture UART は、その fn の plan の RX の channel に label（§1）があればその label、無ければ `name#instance`（core §7.2、
  例 `oep.fixture.uart#1`）。
  label を印にするとき、probe は `]` と 0x20 未満のバイト（CR、LF など）を `_` に置き換える。
  行の前後は、target どうしでは行が閉じた順（機械で読む用途には向かない）。
- **口から来た生のバイト**（core §3.4 の、フレームの外のバイト）は、選ばれているストリームの相手（コンソールなら console の write、
  fixture UART なら TX）に、相手が受け取れる分だけ渡す。受け取れない分は捨ててよい。
- **口の位置**: probe は bind ごとに、流すストリームの中の位置を持つ。口が受け取れる分だけ進め、口が読まれていなくても
  ストリームは捨てない。ストリームが口より丸ごと先に行ったら（あふれ）、口は残っている一番古いバイトまで飛ぶ。
- **セッションの間**（core §3.4 で生の転送を止めた口）: 位置は進めない。セッションが終わったら、流すストリームごとに、
  **そのセッションで host が最後に reset した時点の位置**から再開する（上の「host の reset として数えるもの」のどれか。コンソールの
  ストリームではその reset のマーク（[共通部品](oep-if-common.ja.md) §1.3）の位置、fixture UART ではその時点の受信の位置）。
  そのセッションで reset が無ければ今から。mode に関係なく同じ。
- スロットのストリームは、そのスロットがどれかの bind の並びにあり、スロットの接続があって錠が合う間、probe がその接続で
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
| `nrst` | target のリセットの線 | probe（§3.1 のリセットでのやり直し）と host |
| `power_hi` | high のとき target の電源が入る線 | host だけ（probe は使わない） |
| `power_lo` | low のとき target の電源が入る線 | host だけ（probe は使わない） |

- **スロットの線の探し方**（名前 N、スロットの name S）。次の順に探し、channel がちょうど 1 つ見つかった段で止める:
  - (a) `S.N` に等しい設定の label;
  - (b) 設定が持つスロットの項目が 1 つ以下のときだけ、`N` に等しい設定の label;
  - (c) 設定が持つスロットの項目が 1 つ以下のときだけ、`N` に等しい firmware の label（fn 0 の describe、0x46）。
- 2 つ以上の channel が見つかった段で、線なしとして探すのを終える。どの段でも見つからなければ、そのスロットにその線は無い。text と名前は、ASCII の大文字と小文字を区別せずに比べる。
- スロットの項目の無い設定では、段 (b) と (c) で、probe につながる target のその線が見つかる。
- 表に無い label の text は、役目を表さない（名前でしかない）。標準の名前は registry（`oep.probe.config` の `[line_names]`）に並べる。足しても revision は変わらない（core §2.7）。標準でない役目の名前は `x-` で始める（例 `x-acme-boot0`）。標準の名前は `x-` で始まらず、どの名前も `.` を含まない（`S.N` が使う）。
- probe は `power_hi` と `power_lo` を使わない（電源の線を駆動しない）。host は同じ探し方で電源の線を見つける。

## 2. 操作

| op | 名前 | 要求 | 応答 | ロック |
|---|---|---|---|---|
| 0x01 | get | first(u16) | more(u8)、hash(u32)、payload の終わりまでの項目（今の設定） | 不要 |
| 0x02 | set | 項目の並び | hash(u32)、[TLV] | 必要 |
| 0x03 | save | — | hash(u32)、[TLV] | 必要 |
| 0x04 | erase | — | — | 必要 |
| 0x05 | unset | n(u8)、n × (len(u8)、tag(u8)、key) | hash(u32)、[TLV] | 必要 |
| 0x06 | state | first_slot(u8)、first_bind(u8) | §3.3（今の状態）、ロック不要 | 不要 |

- **get**: 応答の項目は payload の終わりまで続く。tag 0x7E は応答のメタ情報のために予約し、v1 の probe は置かない。get は TLV を取らない（あれば rejected malformed、core §7.3）。
- **set は、要求に含まれる項目のキーごとに置き換える**（含まれないキーはそのまま。何回かの set に分けて積み上げられる）。
  plan の項目は fn ごとにまとめて、その fn の plan を置き換える。項目の順は意味を持たない。
- **unset はキーの項目を消す**（key は tag ごと: plan は fn(u16)（その fn の plan 全部）、label と idle は channel(u16)、slot は slot(u8)、
  bind は port(u8)、uart は fn(u16)、disable は channel(u16)。要素に len を置くのはキーの長さが tag ごとに違うため）。検証と原子性は set と同じ。無いキーは
  何もせず成功。宣言していない項目の tag は rejected unsupported（payload の tag は受け取ったままの tag、core §4.3）。消したスロット・bind には §1.1 / §1.2 の後始末を適用する。
- 1 つの set の中で同じキー（plan は (fn, role, channel)）が 2 回出たら、要求全体を rejected malformed。
- set / unset の結果の設定全体が §1 の規則を満たさなければ（bind が消したスロットを指す、など）、何も変えずに rejected malformed。
- **set の原子性は、設定の検証と資源の予約（plan の適用、ピンの取り合いの確かめ）まで**。どれかが受け入れられなければ、何も変え
  ずに rejected。自動の attach とコンソールを開くこと（外の状態を変えること）は、set が済んだ後に行い、その結果は state（op 0x06、
  §3.3）の slot_state と bind_state で分かる（巻き戻さない）。
- **probe は host が送った項目のバイト列をそのまま持つ**（critical の bit だけ外す。知らない後ろのフィールドも切らずに持つ）。
  probe が自分で後ろにフィールドを足すことはしない。
- **hash** は今の設定の正規形の CRC-32（core §5.2 と同じ IEEE）。正規形 = 項目を tag の昇順に、同じ tag の中はキー（plan は
  (fn, role, channel)）の昇順に並べ、TLV（core §2.2 の一意の符号化）でつないだバイト列。host は自分の欲しい設定から同じ値を計算し、
  get の hash と同じなら何もしない。正規形では tag の critical の bit を落とす。キーは数として比べ、複数のフィールドのキーは最初のフィールドから順に比べる。get はこの正規形の順で first 番目の項目から返し、どのページも同じ hash を返す（変わっていたら
  host は最初から読み直す）。
- **save は host の明示的な操作だけ**で、今の設定をそのまま保存する（同じ内容なら書かない）。書いている間はほかの要求に答えない
  （core の max_op_ms の対象）。**保存は丸ごと置き換え**で、途中で電源が落ちても前の保存か新しい保存のどちらかが読める。describe の
  `max_bytes` は正規形の byte 数で、その長さ以下の設定は必ず保存できる（識別子の表の分は probe が差し引いて宣言する）。超えれば
  rejected unavailable（cause 3）。erase は保存を消す（今の設定は変えない。消した後は状態 0、hash 0）。保存の無い probe
  （max_bytes 0）では save / erase は rejected unsupported。
- **保存は、項目が指す interface を (name、instance、revision) で持つ**（fn の番号は起動ごとに変わりうるため）。指す fn は、plan の
  fn、slot の wire_fn、bind の kind 2 の id、uart の fn。起動時に、その組を今の list で探して fn を読み替えてから適用する（set と get の形は
  fn のまま）。指す interface が無いか、revision が違えば、**保存全体を適用しない**（一部だけ入れると治具が半端に動く。storage の
  状態は「あり・読めない」、理由 2）。指していない interface の追加・削除・並べ替えは、保存に影響しない。
- 保存の形（probe の中の持ち方）は probe が決める。読み替えの規則だけが規範。
- 起動時に、保存した bind の port がこの firmware のシリアルの口でなければ、保存は読めないものになる（理由 2）。保存した項目のどれかの適用が断られたら、保存全体を適用しない（理由 3）。
- 起動時は、保存を今の設定にして（上の確かめを通ったとき）、idle を掛け（mode 3 / 4 の出力の駆動を、その強さと一緒に含む）、plan を適用し、uart を掛け、at boot のスロットの attach を
  始め、bind を結ぶ。保存を読めないときは適用せず、state で知らせる。

**断り方の表**（core §4.3 の順）:

- 項目についての rejected unsupported は、どの項目でも（plan、label、idle、slot、bind、uart、disable）、下のどの行によるものでも、payload にその項目の受け取ったままの tag を載せる（core §4.3）。保存の無い probe の save / erase は tag 0x00 を載せる。
- 定義されていない値を持つフィールドは unsupported で断り、それが関わる矛盾（malformed の行）は確かめない（core §4.3）。

| 状況 | reason |
|---|---|
| 形の誤り、同じキーが 2 回、name の文字、label の text の長さと文字、selected の範囲、retry_ms が host のスロットで 0 でない、lock の長さ、boot_reset の値と host のスロットの boot_reset 1、mode 0〜2 の idle の drive と、idle の drive の長さ、mechanism 0xFF のスロットを bind に載せる、無いスロットを bind が指す、同じ wire_fn と同じピンのスロットが 2 つ、name の重複 | malformed |
| 指す fn が無い（plan、slot の wire_fn、bind の kind 2、uart） | unknown_function |
| 宣言していない項目、その線が許さないピンの組、wire_fn が錠を持てない線、console が宣言しない mechanism、出力として駆動できない channel への mode 3 / 4 の idle、段の数以上の idle の段の番号、idle_clock 1 を rvswd 以外、守れない max_speed_hz、そのプルの無い channel への mode 1 / 2 の idle、channels 以上か reserved にある label / idle / disable の channel、bind_modes に無い mode、シリアルの口でない port、uart でない fn、実現できない baud / format、format の使っていない値と予約のビット、5 以上の idle の mode、idle の未定義の drive_kind、2 以上の slot の attach、2 以上の slot の idle_clock、1 / 2 以外の bind のストリームの kind、その線が持たない lock_scheme（定義にあってもなくても）、保存の無い probe の save / erase | unsupported |
| plan_roles 超え、ピンや資源の取り合い、at boot のスロットが max_connections を超える、保存先が足りない | unavailable（cause 2 / 1 / 2 / 3） |

## 3. スロットの接続と状態

### 3.1 attach の方針

| attach | 接続を作る契機 |
|---:|---|
| 0 host | probe は自分から attach しない。host の attach でスロットの接続ができたら、bind はそれに乗る |
| 1 at boot | 起動時と、そのスロットの項目を set した直後。いなければ retry_ms ごとにやり直す（0 ならやり直さない） |

- 起動時の自動の attach は、すべての idle（mode 3 / 4 の出力の駆動を、その強さと一緒に含む）を掛けた後に始める（§2 の起動の順）。
- **自動の attach（at boot）は止めない attach（method 0）だけ**で、スロットのピンの組で、[線とデバッグ](oep-if-debug.ja.md)
  §1 の規則どおりに行う。錠が合わなければ、コンソールを開かずに自分の分を外す（状態は錠に不一致）。
- 自動の attach は、接続に時間のかかる場合を先に払っておくもの。外れていれば、host は使うときに自分で attach する。
- 席が埋まっていて host の attach がスロットの接続を閉じた（[線とデバッグ](oep-if-debug.ja.md) §1）とき、そのスロットはそのままに
  する（at boot でもやり直さない）。次の接続は、次の起動、そのスロットの set、または host の attach でできる。
- 接続が切れた（線が落ちた）スロットは、at boot なら retry_ms ごとにやり直す。
- **生存の確認**: at boot のスロットの接続は、probe が retry_ms ごとに DMSTATUS を読んで確かめてよい（書かない）。線切れを見たら
  接続を閉じて retry に入る（mechanism 0xFF のスロットでも、コンソールの読みが無くても「いない」が分かる）。retry_ms が 0 なら
  確かめない。
- policy が host のスロットを、probe は確かめない（線を駆動しない）。
- **リセットでのやり直し**（boot_reset 1 のスロット）: そのスロットの自動の attach が、線の応答をまったく得られずに終わった
  （completed failed、status line、[共通部品](oep-if-common.ja.md) §3）とき、probe はすぐに 1 回、同じ attach（method 0）を、
  リセットの線を付けて行う。動きは attach の reset TLV（[線とデバッグ](oep-if-debug.ja.md) §3）と同じで、hold_ms は registry の
  `slot_retry_reset_hold_ms`（20 ms）。
  - 行うのは、起動してから、どのセッションもまだロックを取っていない間だけ。ロックが一度でも取られたら、その起動の中では
    （ロックが放された後も）行わない。
  - status line の失敗の後だけに行う。attach が成功した場合（錠に不一致、target_id が読めない を含む）、status line 以外の失敗
    （読み出しの保護を含む）、rejected の後には行わない。
  - スロットごとに、1 回の起動で多くても 1 回。やり直しが失敗したら、retry_ms のふつうのやり直し（リセットなし）を続ける。
  - リセットの線は、§1.3 の探し方で見つけた `nrst` の channel。見つからないとき、またはその channel をそのスロットの線の attach の
    reset TLV に使えないとき（role_channels の role 3 に無い、disable、plan や接続が持っている、その線が reset TLV を持たない）は、
    リセットでのやり直しをしない。
  - 行ったら、state の slot_state の reset_at_ns（§3.3）に、リセットの線を引き始めた時刻を入れる。bind の選択は替えない（probe
    自身の attach、§1.2）。

### 3.2 状態

state（op 0x06、§3.3）の slot_state はロックなしで読める。host が線を駆動せずに target の有無を知る方法はこれだけである（線を駆動しないと
つながっているかは分からない）。

| state | 意味 |
|---:|---|
| 0 | 接続あり（錠が合う） |
| 1 | いない（接続が無い。last_try_at_ns は最後に自動の attach を試した時刻） |
| 2 | 錠に不一致（接続はあるか、自動の attach で見つけて外した。target_id は見えたもの） |
| 3 | target_id が読めない（錠のあるスロットで、接続の target_id が無い） |

### 3.3 state（今の状態、ロック不要）

```text
要求: first_slot(u8)、first_bind(u8)
応答: more(u8)、storage_state(u8)、storage_hash(u32)、unreadable_reason(u8)、
      n_slots(u8)、n_slots × (len(u8)、slot_state)、n_binds(u8)、n_binds × (len(u8)、bind_state)、[TLV]
slot_state: slot(u8)、state(u8、§3.2)、connection(u16、無ければ 0)、last_try_at_ns(u64: 最後に自動の attach を試した時刻（probe の時計。§3.1 のリセットでのやり直しも試したうちに入る）、全ビット 1 は試していない)、tid_scheme(u8、0 は無し)、tid_len(u8)、tid、
      reset_at_ns(u64: §3.1 のリセットでのやり直しでリセットの線を引き始めた時刻（probe の時計）、全ビット 1 はしていない)
bind_state: port(u8)、mode(u8)、selected(u8: 今選ばれている並びの番号。mixed では 0xFF)、flow(u8: 0 流すものが無い / 1 流している / 2 セッションで止めている)
```

- storage_state: 0 保存なし、1 あり・適用済み、2 あり・読めない。storage_hash は、保存を今の fn に読み替えた後の正規形の hash
  （読めなければ 0）。unreadable_reason: 0 なし、1 形が読めない（壊れた、別の版の形）、2 指す interface が無い・revision が違う・bind の port がシリアルの口でない、
  3 適用が断られた（資源がぶつかる）。
- 登録したスロットを slot の昇順に first_slot 番目から、bind を port の昇順に first_bind 番目から、1 フレームに入る分だけ返す。
  more = 1 なら続きがあり、host は first に受け取った数を足してもう一度聞く。

## 4. describe

describe は宣言だけ（core §7.3）。状態は state（§3.3）。

| tag | 名前 | 値 |
|---:|---|---|
| 0x40 | storage | max_bytes(u32、正規形の byte 数。0 = 保存なし) |
| 0x41 | items | 扱う項目の tag の並び（u8） |
| 0x42 | slots_max | u8。登録できるスロットの数（0 はスロットを扱わない） |
| 0x43 | bind_modes | u32 のビット: bit0 last-reset、bit1 manual、bit2 mixed。bind を扱う probe は bit0 と bit1 を必ず立てる |
| 0x44、0x45 | — | 予約（旧 slot_state / bind_state。state op に移った） |
