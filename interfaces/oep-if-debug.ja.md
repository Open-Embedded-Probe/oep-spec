# OEP インターフェース: 線とデバッグ v1

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](../docs/versioning.ja.md) §6）。本体は [OEP core](../docs/oep-core.ja.md)、共通部品は [共通部品](oep-if-common.ja.md)（§2 debug の
connection、§3 status）。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.wire.rvswd` | 1 | 2 線の RVSWD で RISC-V の DM につなぐ | DM に 2 線の RVSWD で届く RISC-V の target |
| `oep.wire.swio` | 1 | 1 線の SWIO で RISC-V の DM につなぐ | DM に 1 線の SWIO で届く RISC-V の target |
| `oep.wire.swd` | 1 | ARM の SWD で ADI につなぐ | SWD の DP を持つ ARM の target |
| `oep.target.riscv-dm` | 1 | RISC-V Debug Module の操作 | RISC-V Debug Module を持つ RISC-V の target |
| `oep.target.arm-adi` | 1 | ARM ADI（DP / AP）の操作 | ADI を持つ ARM の target |

- `oep.wire.*` は connection を作り、`oep.target.*` は connection の上で target を操作する。target を扱うインターフェースは
  attach の前から list に出し、connection の無い要求は rejected no_connection。
- connections のほかの op はすべてロックが要る。

## 0. すべての wire が共有するもの、新しい wire が定めるもの

すべての `oep.wire.*` のインターフェースは:

1. op 0x01 scan、0x02 attach、0x03 detach、0x05 connections を §1〜§2.1 の意味で使う（wire は 0x06 から op を足してよい）。4 つとも
   すべての wire で必須;
2. §1 と §2 に従う。swdio / swclk は「ピンの役 1 / 2 の channel」と読み替える;
3. `oep.target.*` のインターフェースが使う [共通部品](oep-if-common.ja.md) §2 の connection を作る。

新しい wire の文書は、ほかに次を定める:

- ピンの役と、速さの選び方;
- wake / 設定の手順と、それが target をリセットしうるか（§2）、scratch のレジスタ（§1）;
- やり取りと、やり取りの間の線の休み方（§2）;
- 「見つかった」の基準と、scan_kind の値;
- 使う target_id の scheme（§1 の 1 つの空間から）と、線切れの見え方;
- その connection を受ける `oep.target.*` のインターフェースと、コンソールや probe.config のスロットが乗るかどうか。

## 1. attach の規範（全 wire）

- **速さを確かめる前の書き込み.** 線の速さを確かめ終えるまで、probe が target に書くのは次だけである:
  1. その wire の節が定める wake / 設定の手順（たとえば wake のパターン、line reset、target の選択、または debug module が答える前に要る
     設定のレジスタ）。wire の最も遅い速さで送る;
  2. connection が RISC-V の DM に届く wire での dmactive。DMCONTROL がすでに dmactive = 1 と読めないときだけ（この書き込みは haltreq を下ろす）。
- **速さの確かめ方.** probe は読むだけで速さを選ぶ。それから、選んだ速さで書き込みの道を確かめる。書いて読み戻してよいのは、その wire の節が
  空きの scratch（debug のコマンドが走っていない間、target のどこも使わないレジスタ）と名指した debug module のレジスタと、その wire の節が
  それを空けるための書き込みと名指したものだけである。確かめる前に各 scratch のレジスタを読み、確かめた後にその値を書き戻す。書いたものが
  読み戻らない速さは使わない。
- 速さを確かめる前に、これ以外のものを target に書かない（速さの合わない書き込みは、化けた値を target のレジスタに書きうる）。
- **ピンの組**:
  - probe が使える組は describe の共通タグ（core §7.4）で宣言する。決まった組は channel_group、どのピンにも割り当てられる
    なら role_channels。役の番号は `pin_role`（1 = SWDIO、2 = SWCLK、3 = reset）。
  - scan の要求は試す組の並び。**count = 0 は probe が許すすべての組**。応答の組は、そのまま attach の pins に渡せる。
  - role_channels で宣言した線では、許す組は「role 1 の候補 × role 2 の候補（1 本の線は role 1 だけ）で、同じ channel を 2 度
    使わないもの」。count = 0 の並びは swdio の昇順、その中で swclk の昇順とし、**今ほかのもの（plan、ほかの線の接続、設定の
    資源）が持っている channel を含む組は並べない**（count = 0 は動かしてよい組だけを試す）。組を並べた要求に、持たれている
    channel があれば、core §8.1 のとおり全体を rejected unavailable。
  - **idle の項目がある channel**: count = 0 の並びと、pins の無い attach の候補からは、ほかのものが持つ channel と無効にした channel に加えて、
    probe の設定に **idle の項目**がある channel（mode を問わない、[probe の設定](oep-if-probe-config.ja.md) §1）をすべて外す。
    そういう channel を明示した要求（組を並べた scan、attach の pins）は、idle が入力（mode 0〜2）なら受ける。
    idle が出力（mode 3 / 4）なら rejected unavailable（cause 5、その channel）。
    idle が出力（mode 3 / 4）の channel を名指した attach の reset TLV（TLV 0x05、§3）も、同じく何も実行せずに rejected unavailable
    （cause 5、その channel）。
    pins の無い attach で、許される組がただ 1 つで、それが idle の項目を持つ channel を含むもの（どの mode でも。入力も含む）は、候補が残らない: rejected
    unavailable（cause 5、その channel）。
  - （参考）count = 0 は空いている候補のピンを順に全部動かす。利用者の同意なしに、host は配線を知らない治具へ count = 0 を送らない。
  - 線は、生きている接続が使っている組の channel を持つ（接続が無くなれば放す）。持っている間、その channel を plan や設定が
    取ろうとすれば rejected unavailable（core §8.1）。
  - scan の応答の `tried` は、要求の並び（count = 0 なら上の count = 0 の並び。channel_group の線では describe に出した順）の
    先頭から試し終えた組の数（tried は u8 で、1 回に多くても 255 組）。見つかった組で応答が 1 フレームに入らなくなりそう
    なら、probe はそこで止める。**次の組を試すと応答が max_op_ms（core §7.5）を越えそうなときも、probe はそこで止める**
    （少なくとも 1 組は試す）。tried ≥ 1 なら、host は続きを送る。組を並べた要求で tried が並びの数より少なければ、host は残りの組でもう一度 scan を送る。
  - **count = 0 の続き**: count = 0 の要求は TLV skip（0x01、u16）で、count = 0 の並びの先頭から飛ばす数を渡せる（無ければ 0）。
    host は skip に今までの tried の和を渡して続け、**tried = 0 が返ったら終わり**。**並びに組が残っていれば、probe は少なくとも 1 組は
    試す**（tried ≥ 1。tried = 0 は並びを使い切ったときだけ）。**count = 0 の並びに skip から先の組が無ければ**（並びが空か、skip が
    並びの長さ以上）、応答は completed success で tried = 0、count = 0。少なくとも 1 組は試すという規則は、組が残っているときだけ
    効く。並びは要求のときの持たれ方で決まるので、
    途中で plan などが変われば、組が抜けたり重なったりしうる（host は scan の間ほかを変えない）。count > 0 の要求では
    probe は skip を見ない。
  - attach は pins（TLV 0x03、critical）で組を指定する。pins が無ければ、その線の生きている接続が 1 つ
    だけならその組（既存の接続に乗る。スロットが持っている接続でもよい）、生きている接続が無く許す組が 1 つだけならその組、
    それ以外（生きている接続が 2 つ以上、または接続が無く許す組が 2 つ以上）は rejected unavailable（host が選ぶ）。
  - **宣言（channel_group / role_channels）が許さない組は、何も実行せずに rejected unsupported**（scan は要求の中に 1 つでもあれば全体を
    断る）。attach は受け取ったままの pins の tag を payload に入れる。scan は tag 0x00 に続けて TLV 0x40 index（u8、要求の並びの中の位置）を入れる。
    持たれている channel（plan、接続、設定、disable）を含む組は rejected unavailable（cause 1 / 5、その channel 付き）。
- **時間**: attach と scan の応答は、max_op_ms（core §7.5）のうちに返す。速さの探索と再試行をいつ諦めるかは probe が決める。attach で
  どの速さも使えなければ、応答は status line の completed failed。host の待ちは、attach と scan の引数の時間を max_op_ms として数える（core §4.4）。
- **同時に持てる接続の数**: wire のインターフェースは describe の max_connections（tag 0x40、u8）で宣言する。宣言が無ければ 1。
  ロックは probe に 1 つのまま（接続ごとのロックは無い）。
- **scan と生きている接続**: 生きている接続の組は、scan で線を初めからやり直さず、その接続で読んだ値（DMSTATUS など）で見つかった
  組として返す（動いている接続を scan で壊さない）。scan の max_speed と idle_clock は、生きている接続の設定（下の、既存の
  connection に加わる attach の項）を変えない。
- **席が埋まっているときの scan**: max_connections の接続が生きている間、scan で試せるのは生きている接続の組だけである（ほかの組を
  試すには、線をその接続から離すことになる）。ほかの組を並べた要求は、何も実行せずに rejected unavailable。count = 0 の並びは
  生きている接続の組だけになる。
- **席の規則**: 生きている接続と違う組への attach は、席が空いていれば新しい connection を作る。席が埋まっていれば、使っているものが
  スロットだけ（host のセッションが使っていない、[共通部品](oep-if-common.ja.md) §2）の接続のうち最も古く作られたものを閉じて席を
  空ける。そういう接続が無ければ rejected unavailable。閉じた接続に載っていたストリームは、接続を失ったときと同じく閉じる。
  違う wire のインターフェースどうしのピンの取り合いは core §8.1 のとおり断る。
- **すでに attach している線への attach は、その connection をそのまま返す**（flags bit1）。method = 1 なら、動いていれば
  止め、止まっていれば何もしない。method = 0 は動いている hart に触れない。既存の connection が max_speed より速ければ、
  probe はその connection の速さを max_speed 以下に下げて返す。下げられない probe は、扱えない TLV の値として扱う
  （core §2.3）。
- **既存の connection に加わる attach は、運ばない設定の TLV について、その connection の今の設定を受け継ぐ**。connection の設定とは、
  wire が connection ごとに定める線の設定である: 線の速さ（max_speed で抑える）と、その wire が定めるときはクロックの休ませ方（idle_clock、§3）。
  加わる attach が設定を変えるのは運んだ TLV だけで、それぞれの規則に従う（速さは上の項、休ませ方は §3）。max_speed は attach では
  必須なので、いつも運ばれる。TLV が無いときの値（idle_clock の 0 = high など）は、新しい connection を作る attach だけが使う。
  pins（組を選ぶ）、reset（1 回の動作）、swd の targetsel（connection の同一性、§5）は、ここでいう設定ではない。
- **失敗した attach は、使っているものを増やさない**: completed failed で答えた attach は、そのセッションを connection の使っているもの
  （[共通部品](oep-if-common.ja.md) §2）に加えない。生きている組に reset TLV を付けた attach が失敗して、その connection が保たれるとき（§3）も
  同じである。そのセッションがすでにその connection の使っているものなら、その分はそのまま残る。
- `speed_hz` は probe が選んだ線の速さ（1 ビットの周期の逆数の目安）。
- max_speed（TLV 0x01、u32 Hz）: probe はこれを超える速さを選ばない。**attach では必須**（無ければ rejected malformed）、critical で
  送る。probe の min_clock_hz より小さければ rejected unsupported（受け取ったままの tag、core §2.3）。scan にも付けられる（下）。pins と idle_clock は任意で、送るときは critical。
- **scan が書くもの**: 「速さを確かめる前の書き込み」の 1 と 2 だけで、「見つかった」の識別子を読むためである。scan は書き込みの道を
  確かめず、scratch のレジスタに書かない。max_speed の無い scan は、その wire の最も遅い速さで試す。max_speed のある scan は、attach と同じく
  max_speed 以下で読むことで速さを選んでよい。dmactive は立てたまま残す。「見つかった」は DMSTATUS.version が 2 以上で 15 でないこと（0 = DM が無い、1 = このインターフェースが
  扱わない版、15 = 適合しない DM）。swd は DPIDR が読めたこと。外れた組のピンは core §8 の
  空きの状態に戻す。
- **target の識別子**: attach の応答の後ろに、probe が読めた target の識別子を TLV 0x10 target_id（scheme(u8)、値）で付けてよい。
  scheme は識別子の取り方。target_id の scheme の番号は probe 全体で 1 つの空間である（registry `[common.enum.target_id_scheme]`:
  1 その debug module の DMI 0x7F の u32、2 swd の targetsel）。各 wire は、どの scheme を使うかを書く。probe は読めなかったとき（scheme が「無い」と定める値だったときを含む）
  は付けない。値の意味（どのビットが系統で、どれがリビジョンか）は host が知っている。probe は解釈しない。
- **search_retries**: どの wire の attach の応答にも TLV 0x12 search_retries（u16、任意）を付けてよい: 立ち上げ（wake / 設定の手順、速さを選ぶこと、
  それを確かめること）で、最初の試しを超えて要った試しの数（0xFFFF で止まる）。数え方は実装が決める。診断のための値で、host は記録して切れかけの線を
  見るのに使ってよい。

## 2. connection の寿命（全 wire）

[共通部品](oep-if-common.ja.md) §2 に加えて:

- **detach は、その host のセッションの分を外すだけ**。ほかに使っているものがあれば connection は閉じない。detach の TLV 0x01
  force（長さ 0、critical で送る）で、使っているものがあっても閉じる。
- **target の reset では connection を閉じない**。probe は、reset の後も同じ connection で使えるように保つ（wire ごとの手順は
  §4.6 など、target を扱うインターフェースの節）。
- **1 つの要求の中の再試行**: probe は 1 つの要求の中で線を再試行してよい（どれだけ続けるかは probe が決め、遅い速さでの再試行を含む）。
  諦めたら、その要求を status line で終える。それだけでは線切れと決めない。再試行の間の遅い速さは一時的で、connection の speed_hz は変えない。
- **書き込みを繰り返さない**: target のメモリへの store（store を起こす書き込みを含む）と host の dmi の要求の手順は、target に届いたかもしれない後には、
  probe の線の再試行で繰り返さない（target が受けなかったと答えたもの、DMI の busy と SWD の WAIT は繰り返してよい）。probe 自身が debug module と
  レジスタに値を置く書き込み（同じ値をもう一度書いても何も起こらないもの: program buffer、abstractauto、GPR、dcsr、戻す DATA0 / DATA1）は繰り返してよく、
  ほかの書き込み（hart を走らせる resumereq など）は store と同じく繰り返さない。繰り返さない書き込みで失敗した要求は completed failed / partial で答え、
  done はそれより前に済んだ手順か語の数にする。probe 自身の読み出しは繰り返すことがある。
- **target の状態を変えない**: connection がある間、probe が自分の判断で行う線の再試行と同期の取り直しは、target の状態を変えない。wake / 設定の手順が
  target をリセットしうる wire では、connection の上でそれを送るのは attach と、reset（attach の reset TLV、riscv-dm の reset の op）の中だけである。
- **線切れ**: ある connection の操作が線からの応答無しで失敗し続け（status line。要求の中でもコンソールの読みの中でも）、その間にその connection で
  成功した操作が無いとき、probe はその connection の線が切れたと決めてよい（いつ決めるかは probe が決める。reset の線を保っている間とそれを解いた直後は、
  target が答えないことがある）。probe が要求の中で線切れと決めたら、その要求に status line で答えてから connection を閉じる。
- **線切れの判定は、要求の中かコンソールの読みの中でだけ行う**（at boot のスロットの生存確認は
  [probe の設定](oep-if-probe-config.ja.md) §3.1）。status line だけでは connection が閉じたことにならない: host は connections で確かめる。
  コンソールの読みの中で判定したら、mark link-lost を付けて閉じる。
- **線が応えない間の線**（電気的な安全）: やり取りとは、wire の節が定める 1 つの frame か packet、または 1 回の wake pattern で、節がその直前に求める
  線の level を含む。線からの応答無しで失敗したやり取り（上の線切れに数える失敗）から、その線でやり取りが成功するまで、または connection を失うまで、
  probe はやり取りの間、その線を放した状態で休ませ、やり取りの最中だけ駆動する（再試行の 1 回 1 回もやり取り）。放した状態とは駆動しない状態で、
  pull 無しか、その connection でのその線の休みの level に向けた pull とする。idle_clock 1（low）を使う connection のクロックの線では、
  pull 無しか pull-down で、pull-up にはしない。やり取りがまた成功したら、probe は次のやり取りの前に connection の休み方（クロックの線は
  idle_clock の level、データの線はその休み方: rvswd は §3.1、swio は §3.2、swd は §5）に戻す。やり取りが成功している間の、やり取りの間の休み方は wire の節が定めるとおりで、この規則では変わらない。
- **probe は connection を閉じるとき、target の状態を必要以上に変えない**（target を reset しない。止めていた hart は、閉じる前の
  host の操作のままにする）。
- connection が閉じたら、その組の channel は core §8 の空きの状態になる（idle_clock の駆動もやめる）。

**connection と hart の状態機械**:

| 出来事 | connection | hart | ストリーム |
|---|---|---|---|
| detach | その host のセッションの分を外す。ほかに使うものが無ければ閉じる | 触らない | connection が閉じれば閉じる（mark closed 4） |
| detach(force) | 閉じる（線が落ちたときと同じ扱い。at boot のスロットは retry） | 触らない | 閉じる（mark detach、closed 4） |
| end / lease 切れ / force で奪われる | セッションの分を外す（core §9）。ほかに使うものが無ければ閉じる。スロットが使っていれば残る | **触らない**（止まっていれば止まったまま。host は attach(method 0) + resume で戻す） | セッションの分を外す（mark closed 2。閉じたストリームは読めるまま残る、[コンソール](oep-if-console.ja.md) §2） |
| 線が切れた | 閉じる | — | 閉じる（mark link-lost、closed 4） |
| target の自己リセット（havereset） | 保つ（確認応答、§4.6） | target の状態 | 保つ（mark restart 1） |
| スロットが connection を保っている間の、後のセッションの attach | 同じ connection に加わる（flags bit1） | method のとおり | 同じ (connection, mechanism) なら同じストリーム |
| probe の再起動 | 無くなる | DM は dmactive を残す | 無くなる |
- （参考、安全）セッションの終わり（end、lease の期限切れ、force）は hart に触らない: hart を止めたまま host が死ぬと、target は止まったままになる（デバッガの
  detach と違い、走り出さない）。target が何を制御していてもそうである。host が去った後に target を走らせたい host は、end の前に resume する。

### 2.1 connections（接続の一覧）

```text
要求: first(u8)
応答: more(u8)、count(u8)、count × entry、[TLV]（core §2.3）
entry: connection(u16)、swdio(u16)、swclk(u16)、speed_hz(u32)、users(u8)、slot(u8)、tid_scheme(u8)、tid_len(u8)、tid
```

- そのインターフェースの生きている接続を、作られた順に first 番目から 1 フレームに入る分だけ返す。more = 1 なら続きがあり、host は
  first に受け取った数を足してもう一度聞く。ロックなしで使える。
- users: bit0 host のセッションが使っている、bit1 スロットが使っている（自動の attach か bind のコンソール）。
- slot は、その接続がスロットの接続（`oep.probe.config` §1.1）ならスロットの番号、そうでなければ 0xFF。
- tid は attach のときに読めた target_id（無ければ tid_scheme 0、tid_len 0）。swd は tid_scheme 2 = targetsel(u32)（multidrop で無ければ
  0）で、同じピンの組で targetsel の違う connection を見分ける。DPIDR は attach の応答で返る。

## 3. `oep.wire.rvswd` / `oep.wire.swio`

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | scan | count(u8)、count × (swdio(u16)、swclk(u16))、[TLV] | tried(u8)、count(u8)、count × (kind(u8)、swdio(u16)、swclk(u16)、id(u32))、[TLV] |
| 0x02 | attach | method(u8: 0 止めない / 1 止める。ほかは rejected unsupported、payload `0x00`)、[TLV] | connection(u16)、id(u32)、flags(u8)、speed_hz(u32)、[TLV] |
| 0x03 | detach | connection(u16)、[TLV] | — |
| 0x05 | connections | first(u8) | §2.1（ロック不要） |

- swio の組は swclk = 0xFFFF（1 本の線。swclk ≠ 0xFFFF は宣言が許さない組で、scan でも attach でも §1 のとおり rejected unsupported）。rvswd と swio の scan の entry の kind は 1（riscv-dm）、
  id は DMSTATUS。その connection を使うのは `oep.target.riscv-dm` と `oep.target.console`。
- **attach の flags**（3 線共通、registry の `attach_flags`）: bit0 保留中の havereset を確認応答した（riscv）、bit1 既存の connection、
  bit2 dormant から起こした（swd）、bit3 hart が止まっている（応答の TLV 0x11 dpc が有効）。
- **wake / 設定の手順**（§1 の 1）: rvswd: wake のパターン（§3.1）、続けて DMI 0x7E と DMI 0x7D にそれぞれ 0x5AA50400 を書く。その組を 2 回。
  swio: DMI 0x7E と DMI 0x7D にそれぞれ 0x5AA50400 を書く。その組を 2 回。両方の線のフレームは §3.1 と §3.2。
- **scratch**（§1）: PROGBUF0（DMI 0x20）。それを空ける書き込み: ABSTRACTAUTO（DMI 0x18）= 0。これは戻さない（前のセッションが残した autoexec は、
  アクセスのたびに走る）。
- **reset をかけながらの attach**: TLV 0x05 reset（critical: `channel(u16)、hold_ms(u16)`）を付けると、probe はリセットの線（channel）を
  hold_ms 保ってから離す。method 1 なら離しながら halt を打ち続け、できるだけ早く止める（flags bit3、dpc TLV）。**最初の命令の前で
  止まる保証は無い**（reset の線の解放から halt が効くまでに走った分がある）。reset の直後の位置で
  止める保証が要るときは、riscv-dm の reset mode 2（ndmreset を haltreq を保ったまま解く）を使う。method 0 なら走ったまま attach する。任意の機能で、role_channels の role 3（reset）で宣言する。持たない probe は reset の TLV を rejected unsupported で断る（受け取ったままの tag、0x85、core §2.3）。既存の connection に reset TLV を付けた
  attach は、その target を reset してから同じ connection を返す（mark reset detail 3）。hold_ms は
  core の max_op_ms の対象。
- **線を離した後の待ち**: リセットの線を離した後、target は自分でもう一度再起動することがあり（ブートローダを通る、など）、その間 debug module は
  線に答えない。probe は、DMSTATUS の読みを wire の最も遅い速さで繰り返し、読みが線の応答を得る（status line にならない）まで待つ。読みの間に、
  その wire の wake / 設定の手順（§1 の 1）を送り直してよい。DM が答えたら速さを探す（§1）。max_op_ms のうちに答えなければ、probe は status line の
  completed failed で答える。既存の connection に付けた attach では、その connection を保つ（target は reset した。mark reset detail 3）。
- **reset の線に既定は無い**: どの線を reset に使うかは host が毎回 channel で明示する（線を取り違えた reset は target や治具を
  壊しうる）。probe が reset に使ってよい channel は describe の role_channels の role 3（reset）で宣言する。宣言していない
  channel は、何も実行せずに rejected unsupported（受け取ったままの tag、0x85）。今ある plan や接続が持つ channel は、core §8.1 の取り合いとして rejected
  unavailable。idle が出力の channel は、§1 のとおり rejected unavailable。**reset の線はオープンドレインで low に引き、離すときは引くのをやめて core §8 の空きの状態にする**（外部の reset ボタンや
  ほかの driver と短絡しない）。channel は op の間だけ持つ。持たない probe では、host は `oep.fixture.gpio` の解放と attach をまとめて
  送って再試行する。

TLV:

| op | tag | 名前 | 値 |
|---|---:|---|---|
| scan | 0x01 | max_speed | u32 Hz（無ければその wire の最も遅い速さ） |
| scan（count = 0 だけ） | 0x02 | skip | u16。count = 0 の並びの先頭から飛ばす組の数 |
| scan（rvswd だけ） | 0x04 | idle_clock | u8。scan の間の休ませ方（下） |
| attach | 0x01 | max_speed | u32 Hz。**必須**、critical |
| attach | 0x03 | pins | swdio(u16)、swclk(u16)。critical |
| attach（rvswd だけ） | 0x04 | idle_clock | u8。線を休ませる間の SWCLK: 0 = high（新しい connection で無いときと同じ。既存の connection に加わる attach で無ければ、その connection の今の休ませ方、§1）、1 = low。critical。rvswd 以外に 1 を送れば rejected unsupported（受け取ったままの tag、core §2.3） |
| attach | 0x05 | reset | channel(u16)、hold_ms(u16)。critical。上 |
| detach | 0x01 | force | 長さ 0。critical |
| attach の応答 | 0x10 | target_id | scheme(u8)、値 |
| attach の応答 | 0x11 | dpc | u32。hart が止まっている（flags bit3）ときの dpc |
| attach の応答 | 0x12 | search_retries | u16、任意。§1 |

これらの wire が使う target_id の scheme（`target_id_scheme`、probe で 1 つの空間、§1）: 1 = DMI のアドレス 0x7F を読んだ u32（長さ 4）。0 と 0xFFFFFFFF は「無い」（付けない）。
2 = swd の targetsel（u32、connections の entry だけに使う）。

- 既存の connection への attach が idle_clock を運び、それが今と違えば、probe はその connection の休ませ方を替えて返す。替えられない
  probe は、扱えない TLV の値として扱う（core §2.3）。

### 3.1 RVSWD のフレーム

線は 2 本、SWDIO（ピンの役割 1）と SWCLK（ピンの役割 2）。probe は SWCLK をいつも駆動する。SWDIO は読み出しのデータの間を除いて駆動し、
線を使っている間は SWDIO にプルアップを保つ（どちらも駆動しないとき、線が high に読めるように）。

**ビットの区切り。** T は半周期。1 つのビットの区切りは、SWCLK low を T、続けて SWCLK high を T である。
- probe が送るビット: probe は、その区切りを始める SWCLK の立ち下がりで SWDIO をそのビットにし（2 本が同時に変わる）、次の立ち下がりまで保つ。
  target は立ち上がりでそれを読む。
- target が送るビット: target は立ち下がりの後に SWDIO を変える。probe は low の半分の終わり、立ち上がりの直前に SWDIO を読む。

**条件**（SWCLK が high の間に SWDIO が変わるのはここだけ）:
- START: 2 本とも high を T 以上、続けて SWCLK を high のまま SWDIO が下がる。最初のビットの区切りは T 後に始まる。
- STOP: SWDIO low のビットの区切り 1 つ、続けて SWCLK を high のまま SWDIO が上がる。その後 2 本とも T 以上 high のまま。

**フレーム**: DMI のアクセス 1 回。値は最上位ビットから送る。フレームはビットの区切り 53 個。

| 欄 | 区切り | 駆動する側 | 値 |
|---|---:|---|---|
| START | — | probe | |
| address | 7 | probe | DMI のアドレス |
| direction | 1 | probe | 1 書き込み、0 読み出し |
| ヘッダのパリティ | 1 | probe | address、direction とこのビットの 1 の数を偶数にする |
| aux 1 | 5 | probe | 1、0、1、0、1 |
| data | 32 | probe（書き込み）、target（読み出し） | 32 bit の値 |
| data のパリティ | 1 | data と同じ側 | data とこのビットの 1 の数を偶数にする |
| aux 2 | 5 | probe | 1、0、1、1、1 |
| STOP | 1 | probe | STOP の SWDIO low のビットの区切り |

- **向きの切り替え**（読み出し）: probe は、aux 1 の最後の区切りの立ち上がりの後、SWCLK が high の間に SWDIO の駆動をやめ、最初の data の区切りが
  余分な区切り無しに続く。data のパリティの区切りの立ち上がりの後、probe は SWDIO を再び high に駆動し、aux 2 が余分な区切り無しに続く。target が SWDIO を
  駆動するのは、data と data のパリティの 33 個の区切りの間だけである。
- data のパリティが合わない読み出しは、失敗した読み出しである（§2 のとおり再試行する）。書き込みに確認応答は無い: 書く経路は読み戻しでしか確かめられない（§1）。
- **休ませ方**（フレームの間）: idle_clock 0 では 2 本とも high のまま。idle_clock 1 では SWCLK low、SWDIO high で、どちらも probe が駆動する。フレームは 2 本
  とも high から始まる: idle_clock 1 では、START の T 以上前に、SWDIO high のまま SWCLK が上がる。

**wake のパターン**（wake / 設定の手順の最初の部分、§3）:

1. 2 本とも high に駆動して 20 µs 以上;
2. SWDIO high のビットの区切り 100 個;
3. SWDIO low のビットの区切り 1 個;
4. SWCLK が high の間に SWDIO が上がる（STOP の条件）;
5. 最初のフレームの前に、2 本とも high を 20 µs 以上。

- **wake / 設定の手順の速さ**: T は 500 ns 以上、かつ 1 / (2 × max_speed) 以上。probe が dmactive を書くとき（§1 の 2）、その直後に同じ T で設定の組
  （DMI 0x7E、続けて DMI 0x7D）をもう 2 回書いてよい。これらの書き込みは wake / 設定の手順の一部である。
- **速さの選び方**: probe は、DMSTATUS の読み出しで、一番遅い T から短い方へ進めて T を選ぶ（§1）。
- wake のパターンは、target のデバッグの口だけでなく target そのものをリセットしうる（§2 の、target の状態を変えない再試行の規則が掛かる）。

### 3.2 SWIO のフレーム

線は 1 本、SWDIO（ピンの役割 1）。休んでいるときは high。probe は、送るとき線を high にも low にも駆動する。線を使っている間、probe は線に
プルアップを保つ。フレームの間、線は high で休む: probe が high に駆動するか、そのプルアップに放す。そこで high に駆動してよいのは、target が答えている間だけ。やり取りが失敗してからは、線をプルアップに放し、high に駆動しない（§2、線が答えない間の線）。

**probe が送るビットの区切り**: 線を low、続けて high。

| 区切り | low | その後の high |
|---|---|---|
| 1 | 240 から 310 ns | 240 から 270 ns |
| 0 | 840 から 1060 ns | 240 から 270 ns |


**target が送るビットの区切り**（読み出しの区切り）: probe は線を 240 から 270 ns low に駆動し、駆動をやめる。target は、線を low に保って 0 を、
上がるにまかせて 1 を送る。probe は、自分が作った立ち下がりから 520 から 600 ns 後に線を読む（high = 1、low = 0）。その後、線がまた high に読めるまで
待つ。100 µs 以内に high に読めなければ、その読み出しは失敗である。high になったら、probe は次の区切りの前に線を 130 ns 以上 high に駆動する。
low の駆動をやめた後と、0 を読んだ後に、probe は 1 回 30 ns 以下だけ線を high に駆動してよい（充電のパルス。プルアップを通る立ち上がりを
短くするため）。

**フレーム**: DMI のアクセス 1 回。最上位ビットから、区切り 41 個:

- 書き込み: START（1 の区切り）、7 bit の DMI のアドレス、direction 1、続けて probe が送る data の区切り 32 個;
- 読み出し: START（1 の区切り）、7 bit の DMI のアドレス、direction 0、続けて読み出しの区切り 32 個。

- パリティ、確認応答、STOP は無い。読み出しが見つけられるのは high に戻らない線だけで、違うビットは見つけられない。
- probe は、フレームのすべての区切りを上の時間の中に保つ（フレームを何にも割り込ませない）。フレームの後、次のフレームの前に、線は 8 µs 以上
  high のまま。
- **速さ**: ビットの時間は決まっているので、probe は速さを選ばない。describe の min_clock_hz で、0 の区切りの速さ（1 / (その low + その high)）を宣言する。
  それより低い max_speed は rejected unsupported（§1）。

## 4. `oep.target.riscv-dm`

要求の先頭は connection(u16)。

- **必須の op は dmi、halt、resume**。reset、read_block、write_block、run、step は任意で、describe の ops で宣言する
  （core §1.2、§7.4）。read_block と write_block は組で持つ。host は、任意の op が
  無くても dmi で同じことを組める。
- **dmi 以外の op（高水準の op）の範囲**: RV32 の hart 0 だけを扱う（番地、レジスタの値、pc は u32）。probe は高水準の op の中で
  DMCONTROL の hartsel を 0 にし、**0 にして返す**（host が dmi で選んだ hartsel は、その dmi の要求の中だけ）。ほかの hart は
  host が dmi で扱う。

**op の境界の不変条件**: **probe は、op の応答を返したあと、target の状態を持ち越さない**。op の中で使ったものは応答の前に戻す。
host が raw の DMI（dmi の op）で何をしても、host が途中で死んでも（lease 切れ、force）、probe が戻し忘れるものは無い。

| op | probe が触るもの | 応答の前に |
|---|---|---|
| halt | haltreq | allhalted を見る。**止まっている間、haltreq を立てたままにしてよい**（保つか下ろすかは probe が決め、host から見える動作は同じ。保つと、hart の状態が変わると debug の link が落ちる target を助ける。そういう target では halt 直後の読みが前の値になりうる）。resume / step / reset / detach と connection を閉じるときに下ろす。halt が時間切れになったら応答の前に下ろす（§4.2） |
| resume | haltreq = 0、resumereq = 1 を 1 回 | 何も覚えず、何も戻さない |
| step | dcsr.step、DATA0 / DATA1（dcsr の読み書き）、haltreq | dcsr.step を下ろし、DATA1、DATA0 を戻し、haltreq を下ろす。hart をもう一度止められなければ、応答が step_left を示す（§4.2） |
| reset | haltreq、ndmreset、havereset の確認応答 | havereset を確認応答。mode 0 / 1 は haltreq を下ろす。mode 2 は止めたままで、halt と同じく haltreq を保ってよい。mode 1 の内部の halt は step と同じく戻す |
| read_block / write_block | GPR（s0、s1、a0、a1）、DATA1 / DATA0、abstractauto、program buffer、sysbus | GPR、DATA1、DATA0、abstractauto を戻す。program buffer と SBCS / SBADDRESS は戻さない（host が使うなら設定し直す） |
| run | pc、host が指定した GPR、dcsr（ebreakm、prv）、haltreq | **host の指示どおりに変えたまま返す**（host の責任）。abstractauto と haltreq は戻す |
| dmi | host が書いたもの | 何も触らず、何も戻さない（host が DATA を使ったら host が戻す） |
| コンソールの読み | DATA0 / DATA1 | [コンソール](oep-if-console.ja.md) §3 のとおり |

戻す値は、その op の中で読んだ「触る前の値」。高水準の op の中で DM の状態（abstractcs.busy の解除、allhalted、allresumeack）をどれだけ待つかは
probe が決める（max_op_ms のうち）。待ち切れなかったときの status は各 op の節のとおり（halt は timeout、resume / step は state）。DMI の busy は
probe の中で再試行し、諦めたら status wait（§6 の WAIT と同じ）。

**DATA0 と DATA1**: コンソールの方式（[コンソール](oep-if-console.ja.md) §3）は DATA0 / DATA1 を target との郵便受けに使う。probe は、自分の op で
使った DATA0 / DATA1 を応答の前に戻す（上の表）。host は、dmi の要求で抽象コマンドなどを使って DATA0 / DATA1 を変えたら、hart を走らせる前に、
変える前の値を書き戻す。

| op | 名前 | 要求（connection の後ろ） | 応答 |
|---:|---|---|---|
| 0x01 | dmi | n(u16)、n 個の手順 | done(u16)、status(u8)、nvals(u16)、nvals × value(u32)、[TLV] |
| 0x02 | halt | — | status(u8)、[TLV] |
| 0x03 | resume | — | status(u8)、[TLV] |
| 0x04 | reset | mode(u8)、[TLV] | status(u8)、flags(u8)、pc(u32)（mode 2 では dpc）、[TLV] |
| 0x05 | read_block | address(u32)、count(u16)、[TLV] | done(u16)、status(u8)、done × word(u32)、[TLV] |
| 0x06 | write_block | address(u32)、count(u16)、count 個の語、[TLV] | done(u16)、status(u8)、[TLV] |
| 0x07 | run | pc(u32)、timeout_ms(u32)、n(u8)、n × (regno(u16)、value(u32))、n_out(u8)、n_out × regno(u16)、[TLV] | status(u8)、stopped(u8)、dpc(u32)、elapsed_us(u32)、nvals(u8)、nvals × value(u32)、[TLV] |
| 0x08 | step | — | status(u8)、moved(u8)、dpc_before(u32)、dpc_after(u32)、[TLV] |

空の結果と端の値: dmi の n = 0 は success、done 0。dmi の max_reads / max_us = 0 は 1 回読む。run の n_out に同じ regno が 2 回あれば
そのまま 2 回返す。

### 4.1 dmi

| kind | 手順 | 引数 | 応答に足す値 |
|---:|---|---|---|
| 0x01 | 書く | address(u8)、value(u32) | — |
| 0x02 | 読む | address(u8) | 読んだ値(u32) |
| 0x03 | 読む回数を上限に待つ | address(u8)、mask(u32)、value(u32)、max_reads(u16) | 最後に読んだ値(u32) |
| 0x04 | 待ち | wait_us(u32) | — |
| 0x05 | 時間を上限に待つ | address(u8)、mask(u32)、value(u32)、max_us(u32) | 最後に読んだ値(u32) |

- 知らない kind は長さが分からないので、要求全体を rejected malformed にする（probe は手順を全部確かめてから実行する）。
- **done は最後まで済んだ手順の数**（失敗したときは、失敗した手順の 0 起点の番号）。値を足すのは 0x02 / 0x03 / 0x05 だけ。
  `nvals` は応答に入っている値の数（最初の done 個の手順のうち値を足す手順の数に、失敗した手順が 0x03 / 0x05 で待ち切れた
  （status timeout）なら 1 を足したもの）。線の不良などで読めずに失敗した手順は値を足さない。
- 0x04 の手順の wait_us と 0x05 の手順の max_us の和は max_op_ms を超えてはならない（rejected unsupported）。0x03 の手順は時間ではなく回数で抑える。
  host の待ちは、この和を引数の時間として数える（core §4.4）。
  走っている間に要求が max_op_ms に達したら、probe はその手順で要求を終え、status timeout で答える（done = その手順の番号）。
- **host は抽象コマンドの一連（data1 / data0 の書き込み、command、data0 の読み）を 1 つの dmi 要求に入れる**（probe が
  要求の間にコンソールの読みを挟んでも壊れない。`oep.target.console` §3）。

### 4.2 halt、resume、step

- **halt** は、すでに止まっていれば何もせず ok。待っても allhalted が見えなければ、probe は haltreq を下ろして status timeout で答える。
- **resume** は haltreq = 0、resumereq = 1 を 1 回書く。ok は「hart が debug mode を出た」ことで、DMSTATUS の allresumeack（または
  allrunning で halted でない）で判断する。resumereq は出し直さない。待っても見えなければ status state。
  - （参考）target によっては、これで足りない（allresumeack を立てない target がすぐ breakpoint で止まり直す、1 回の resumereq で出ない
    ことがある）。その扱い（dpc を読んで、動いていなければもう一度 resume する、など）は target を知っている host が行う。
- **step** は dcsr.step を立てて resume を 1 回だけ出し、戻ったら dcsr.step を下ろす。dpc が動かなくても失敗にしない（status ok、moved = 0。自分自身へ
  跳ぶ命令は正しく進んでも dpc が同じなので、host が命令を読んで判断する）。prv は変えない。
  hart が debug mode に戻らなければ、probe は haltreq を立てて待つ。hart が止まれば、dcsr.step を下ろし、
  DATA1 / DATA0 を戻して status state で答える。止まらなければ、haltreq を下ろし、応答の TLV 0x01 step_left
  （長さ 0）を付けて status state で答える: dcsr.step が立ったままかもしれず、hart は走っている。host はそれを止めて dcsr.step を下ろす。
- step の moved、dpc_before、dpc_after は status ok のときだけ意味を持つ。ok でなければ、probe はどれも 0 にし、host は読まない（hart が
  止まっていれば、host は dpc を dmi で読む）。

### 4.3 reset

| mode | 意味 |
|---:|---|
| 0 | 走らせる |
| 1 | 走らせて、実行を確認する |
| 2 | 最初の命令の前で止める（haltreq を保ったまま ndmreset を解く） |

応答:

| フィールド | 意味 |
|---|---|
| flags bit0 | 要求した mode の状態に達した（mode 0 / 1 は走っている、mode 2 は止まっている） |
| flags bit1 | pc を読んで実行を確かめた（mode 1 だけ） |
| pc | mode 1 で確かめた pc、mode 2 では dpc。ほかは 0 |

- outcome success の条件は、mode 0 と 2 では flags bit0、mode 1 では bit1。満たさなければ completed failed（形は同じ。status は
  止まらない / 走らない = timeout、DM が応えない = line、cmderr = fault）。hart が止まる / 走るのをどれだけ待つか、手順をやり直すかは probe が決める。
- **DM が答えない間の待ち**: ndmreset を解いた後、target は自分でもう一度再起動することがあり（ブートローダを通る、など）、その間 debug module は
  線に答えない。probe は、DMSTATUS の読みが線の応答を得る（status line にならない）まで読み直して待つ。読みの間に、その wire の wake / 設定の
  手順（§1 の 1、§3）を送り直してよい。max_op_ms のうちに DM が答えなければ、probe は status line の completed failed で答え、connection は保つ。
  host の待ちは、reset の引数の時間を max_op_ms として数える（core §4.4）。
- flags のほかの bit は 0。reset の後は havereset を確認応答し、haltreq を下ろす（mode 2 は止めたまま）。

reset は ndmreset を使う。**reset の op はリセットの線を動かさない**: リセットの線が動くのは、attach の reset TLV（§3）か、host が自分で治具のインターフェースを使うときだけ。

### 4.4 run

- host のローダーを呼ぶためのもの。probe は dcsr の ebreakm と prv = M を立て、pc から走らせ、止まるのを待つ。**probe は run を
  出し直さない**（止まった位置が開始位置のままでも、走って戻った場合と区別できない）。走らなかったかどうかは host が dpc で
  判断し、ローダーを二度走らせてよいときだけやり直す。**デバッガの continue には使わない**（prv と ebreakm を変える）。
- timeout_ms が core の max_op_ms を超えれば rejected unsupported。host の待ちは timeout_ms を引数の時間として数える（core §4.4）。
  止まったら stopped = 1（success）。上限に達したら probe は hart を止めてから dpc と値を読み、stopped = 0、status timeout、outcome
  failed で返す（dpc と値はすべて有効）。止められなければ stopped = 2、status timeout、outcome failed、nvals = 0（dpc は無効）。
  走らせる前の準備（レジスタ、dcsr、pc の設定）が失敗したら、probe は走らせずに stopped = 3（hart は止まったまま）、status はその失敗、outcome failed、
  nvals = 0（dpc は無効）で返す。応答の形はいつも同じ（`run_stopped`: 0 時間切れで止めた、1 止まった、2 止められなかった、3 走らせなかった）。
  無効な dpc は 0。
- **elapsed_us** は、probe が hart を走らせた書き込み（resumereq）から、止まったのを見た（stopped 1）、上限で止めた（0）、止めるのを
  諦めた（2）ときまでの、probe が測った時間（µs）。stopped 3 では 0。
- regno は RISC-V の抽象レジスタ番号（a0 = 0x100A）。

### 4.5 read_block、write_block

- 語（32 bit）単位。8 / 16 bit のアクセスは dmi の手順で組む。
- **1 回の長さ**: read_block / write_block を持つ probe は、describe の共通 tag max_length（core §7.4）を必ず出す。単位は **byte 数**
  （4 の倍数）。probe は max_length を、read_block の応答（見出し 5 + done 2 + status 1 + 語）と write_block の要求（見出し 10 +
  connection 2 + address 4 + count 2 + 語）がどちらも自分のどの経路の max_frame にも収まる値で宣言する（core §7.4）。host は count を
  max_length から決め、max_frame から計算しない。count × 4 が max_length を超えれば rejected unsupported（payload `0x00`）。count = 0 は
  success、done 0。4 の倍数でない address は rejected malformed。
- **読みの意味**: read_block は target のバスを通して読む。probe の側に写しを持たない（直前の write_block、dmi、run で target が
  書いたものを反映する）。
- **前提**: hart が止まっていること（止まっていなければ status state）。番地は、止まっている hart が M モードで使う番地。

### 4.6 RISC-V の connection の扱い

- attach は保留中の havereset を先に確認応答する（確認応答するまで DMSTATUS の halt / running を固定する DM がある）。
- **havereset を見たら**（要求の中でも、コンソールの読みの中でも）確認応答し、コンソールの dmseq の状態を未同期に戻し、その connection
  のストリームに mark restart（detail 1）を付ける。

## 5. `oep.wire.swd`

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | scan | count(u8)、count × (swdio(u16)、swclk(u16))、[TLV] | tried(u8)、count(u8)、count × (kind(u8)、swdio(u16)、swclk(u16)、id(u32))、[TLV] |
| 0x02 | attach | method(u8: 0 だけ。ほかは rejected unsupported、payload `0x00`)、[TLV] | connection(u16)、id(u32)、flags(u8)、speed_hz(u32)、[TLV] |
| 0x03 | detach | connection(u16)、[TLV] | — |
| 0x05 | connections | first(u8) | §2.1（ロック不要） |

- scan の kind は 2 = arm-adi、id は DPIDR。要求と応答の形は §3 と同じ（3 線で 1 つの形）。
- TLV は §3 と同じ番号: scan 0x01 max_speed、0x02 skip、0x06 targetsel（下）。attach 0x01 max_speed（必須）、0x02 targetsel、
  0x03 pins、0x05 reset（任意、§3 のとおり）。detach 0x01 force。attach の応答 0x12 search_retries（§1）。
- **wake / 設定の手順**（§1 の 1）: JTAG から SWD への切り替え、dormant からの wake、与えられたときの TARGETSEL。swd は scratch のレジスタを名指さない。
- attach は JTAG から SWD への切り替えを試し、答えがなければ dormant から起こす（flags bit2）。電源投入（CTRL/STAT の CDBGPWRUPREQ /
  CSYSPWRUPREQ）は host が DP の書き込みで行う。
- **線と packet**: この wire の線は SWDIO（ピンの役 1）と SWCLK（ピンの役 2）の 2 本で、Arm Debug Interface（ADIv5 / ADIv6）の SWD の手順を使う。
  probe は SWCLK を常に駆動する。packet とは、その手順の 1 つの SWD packet で、要求、確認応答、手順がそれに与えるデータの相を、それらの
  turnaround のサイクルとともに含む。packet の 1 つ 1 つと、line reset、JTAG から SWD への切り替え、dormant からの wake の手順の 1 つ 1 つが、§2 の 1 つのやり取りである。
- **idle サイクル**: probe は、どの packet の後にも、また上の手順の 1 つ 1 つの後にも、少なくとも 8 回の idle サイクルを刻む: SWDIO を probe が
  low に駆動したクロックのサイクルである。これはそのやり取りの一部である（§2）。
- **休み方**（やり取りの間）: SWDIO は probe が low に駆動し、SWCLK は high に駆動する。
- **probe が線の駆動をやめる前に**（detach などで connection が閉じるとき、probe がピンを放すとき、または §2 の「線が応えない間の線」の
  放した状態にするとき）、最後の packet の後の 8 回の idle サイクルを刻み、target がその packet を終えられるようにする。
- **targetsel（TLV 0x02、u32）は critical で送る**（multidrop のときだけ。無視されると別の target に attach するため）。**connection の
  同一性には targetsel を含める**。同じピンの組の生きている connection と targetsel（無しを含む）が違う attach は rejected unavailable
  （host が先に detach する）。同じなら、その connection をそのまま返す。scan は targetsel なしで試す（TARGETSEL が要る multidrop の
  target は scan に出ない。scan の TLV 0x06 targetsel で 1 つだけ指定して試せる）。
- swd の connection にはコンソールもスロットも乗らない。

## 6. `oep.target.arm-adi`

要求の先頭は connection(u16)。3 つの op はすべて必須（ops にすべて立てる）。arm-adi は任意の op を持たず、features を宣言しない。

| op | 名前 | 要求（connection の後ろ） | 応答 |
|---:|---|---|---|
| 0x01 | transfer | n(u16)、n 個の転送: req(u8: bit0 APnDP、bit1 RnW、bit2-3 A[3:2]、bit4-7 は 0) と、書き込みなら value(u32) | done(u16)、status(u8)、ack(u8)、nvals(u16)、nvals × value(u32)、[TLV] |
| 0x02 | read_block | address(u32)、count(u16)、[TLV] | done(u16)、status(u8)、done × word(u32)、[TLV] |
| 0x03 | write_block | address(u32)、count(u16)、count 個の語、[TLV] | done(u16)、status(u8)、[TLV] |

- ack は最後の転送の生の ACK（`swd_ack`: 線の順で bit0 が最初。OK = 1、WAIT = 2、FAULT = 4。無応答は status line）。req の bit4-7 が
  0 でなければ rejected malformed（req が転送の引数の長さを決めるので、知らない req では要求の残りを読めない。知らない dmi の kind と同じ）。nvals は読んだ値の数（最初の done 個の転送のうち読み出しの数）。
  n = 0 は success で、done 0、status ok、ack 0（転送が 1 つも無ければ ack は 0）、nvals 0。
- transfer は生の転送で、AP の読み出しが 1 つ遅れて返るのもそのまま（host が RDBUFF か次の AP の読み出しで受け取る）。
  WAIT は probe の中で再試行し、諦めたら status wait。FAULT で止まるので、host は ABORT で sticky を消す。
- read_block / write_block の 1 回の長さと読みの意味は riscv-dm（§4.5）と同じ: describe の max_length（byte 数、4 の倍数、要求も応答も
  どの経路の max_frame にも収まる値）を必ず出し、count × 4 がそれを超えれば rejected unsupported（payload `0x00`）。host は max_length から count を
  決める。read_block は target のバスを通して読み、probe の側に写しを持たない。
- read_block / write_block は今の MEM-AP の TAR / DRW を使う。SELECT と CSW（32 bit、単一増加）は host が先に設定する。probe は
  TAR の自動の増加が保証される範囲（ADI）を越えるところで TAR を書き直し、1 つ遅れる読み出しを並べ直す。**hart の状態は問わない**（MEM-AP は走っていても読める）。
  **done は probe が送った語の数**で、target が受けた保証ではない（posted write の FAULT は後の転送で見える）。TAR は進めたままにし、
  SELECT / CSW は変えない（§4 の不変条件の arm 版: probe は host が設定したものを変えない）。

## 7. 参照する仕様

この文書の OEP のメッセージは、本文だけで定まる。RVSWD と SWIO のフレームは §3.1 と §3.2 が定める。target を動かすのに使うもの:

| インターフェース | 仕様 | 使う部分 |
|---|---|---|
| `oep.wire.swd`、`oep.target.arm-adi` | Arm Debug Interface Architecture Specification, ADIv5.2 と ADIv6.0 | SWD のパケット、turnaround、line reset、JTAG から SWD への切り替え、dormant からの wake、TARGETSEL。DP と AP のレジスタ。MEM-AP の TAR、DRW、CSW |
| `oep.wire.rvswd`、`oep.wire.swio`、`oep.target.riscv-dm` | RISC-V Debug Specification 0.13.2 と 1.0（DMSTATUS.version 2 と 3） | DMI のレジスタ（DMCONTROL、DMSTATUS、ABSTRACTCS、COMMAND、ABSTRACTAUTO、DATA0、DATA1、PROGBUF0、SBCS、SBADDRESS）、抽象コマンド、program buffer、dcsr、dpc、havereset |
