# OEP インターフェース: キャプチャ v1

状態: **規範**（v1）。凍結状態と言語・互換性の方針は[版と安定性](../docs/versioning.ja.md)を参照。本体は [OEP core](../docs/oep-core.ja.md)。
番号の唯一の定義は `registry/oep-v1.toml`。基本と別の定義の線引きは §3.6。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.fixture.logic` | 1 | ロジック（1 トラック） | どの系統にも使う |
| `oep.fixture.analog` | 1 | アナログ（1 トラック） | どの系統にも使う |
| `oep.fixture.capture-group` | 1 | 複数のトラックを一緒に始める（ミックスドシグナル、§4） | どの系統にも使う |

logic と analog は**操作の番号と形が同じ**で、違うのは configure の中身（§3.3）、データの layout（§1）、アナログだけの
calibration（§3.7）だけ。複数トラックの同時開始と時刻合わせは、この 2 つを広げず、トラックを束ねる別のインターフェース
（capture-group、§4）にする。チャネルごとの分解能と変化点での運び方はデータの形式（§1.3 / §1.4）、トラックをまたぐ起点は出来事の元（§4.4）。
外部クロックなどは追加の定義（§3.6）。

**時刻**: どのトラックの時刻も、probe の 1 本の時計（起動からの ns、u64 で一周しない）で表す。インターフェースが違っても同じ
時計なので、host は時刻の引き算でトラックを並べられる。時刻は**推定値と不確かさ**で返す。probe は知っている補正（ドライバが最初の
変換フレームを捨てる、など）を済ませた値を返し、それ以上の精度は約束しない。最後の合わせ込み（トラック間のオフセットと時間の
倍率）は host の分析の仕事。
時計と起動の識別はcore §2.7/§6.5/§7.6に従う。

**世代（generation）**: トラックは受け付けたstartごとに世代（u32）を1進める。起動後の最初は1。0は最初のstart前だけを表す。
0xFFFFFFFFに達した後のstartは副作用前にunavailable（cause 2）で断り、再起動まで再利用しない。
世代は等しいかどうかだけを比べる。区画のserialと位置（position）は世代の中で0から数える
ので、host は read と release に世代を付け、probe は違えば断る（古い read が新しいデータを黙って返さない）。世代は start の応答、
status、区画の情報、出来事、ストリーミングのデータの TLV で分かる。

キャプチャは位置つきのストリームの形（[共通部品](oep-if-common.ja.md) §1）を使わない（from とマークが無く、区画と世代を持つ）。
モード（ワンショット、リピート、ストリーミング）は §2.1。レートは probe が刻む。宣言は目安で、configure の応答が正（§3.5）。

**最小の構成**: 1トラック、1役割、対応modeが1つ、即時trigger、通知なしにしてよい。
ピンの割り当てには `oep.probe.plan` を採用する（§3.1）。
すべてのmode、query、force、capture-groupを実装する義務はない。
対応するmodeはdescribeのmodeで宣言し、宣言しないmodeのconfigure/queryはunsupported（受け取ったmode TLVのtag）で断る。
必須の操作と、採用したmodeのデータ/世代/終了の規則は維持する。ワンショットだけでもsegmentsは取得した区画を返す。releaseはmode 2を提供するときだけ必須。

## 1. データの形

用語: **ストリーム**は、1 世代のキャプチャで probe が返すバイトの並び。位置は世代の中で 0 から通して数え、区画ごとには戻さない（§2.2）。
§1 のサンプル配置は、各区画の先頭を 0 とした区画内のビット位置で表す。ストリーム全体でのビット位置は、区画の position × 8 を足した値である。
**区画内のビット j** は、区画内のバイト `floor(j / 8)` のビット `j mod 8`（ビット 0 = LSB）と定める。

**データの形式（format）**: 区画とストリームのバイトの並びは、形式の番号（registry `data_format`）で決まる。configure の応答の format
（§3.3）がその番号で、無ければ 0。0 は §1.1 / §1.2 の詰め方（全チャネルを全サンプルで同じビット数）。1 はロジックのブロック（§1.3）、
2 はアナログのブロック（§1.4）。番号は OEP が足す。0xFF は**名前付きの形式**: 形式を逆 DNS の名前（`a-z 0-9 - .`、1〜64 byte）で表し、
その名前の持ち主が並びの中身、可逆か要約か、最悪の帯域の計算を決める（市販の機材の FPGA の形式など）。名前は revision を持たない
（形を変えるなら新しい名前、core §2.2 の名前付き拡張と同じ考え方）。名前付きの形式でも、下の「形式によらないもの」は守る（数を知る手段が
無い機材は、その名前の形式を出さない）。

- probe は、host が configure の format で求めた番号（0xFF なら format_name の名前）だけを使い、求めが無ければ 0 を使う
  （host が知らない形式を黙って送らない）。
  使える番号は describe の formats（§3.5）で宣言する。宣言は目安で、その設定で使えるかは query と configure の応答が正（rate とチャネルの
  数によって使えないことがある）。
- host は、知っている形式だけを読む。
- **形式によらないもの**: 区画、position（その形式のバイト列での位置）、read、通知、世代の意味。区画の samples、trigger_index、pretrigger は
  元のサンプル（トラックの rate のサンプル）で数える。どのブロックも、それだけで（前のブロック無しに）復元できる。
- **確かさ**: 形式とチャネルの運び方ごとに、可逆（値と時刻が確か）か要約（何が確かかを §1.3 / §1.4 が決める）かが決まっている。
- **最悪の帯域**は configure の応答から start の前に計算できる（§1.3 / §1.4 の式）。

### 1.1 ロジック

configure の応答で probe が返す値:

| 値 | 範囲 | 意味 |
|---|---|---|
| `w` | 1〜128 の整数 | 1 サンプルのビット数。probe が選ぶ（チャネル数より大きくてよい） |
| `C` | 1 以上 | チャネル数（plan で割り当てたロジックの役割の数） |
| `pos[k]`（k = 0 … C−1） | 0 ≤ pos[k] < w、互いに異なる | チャネル k（役割の番号の小さい順）の、サンプルの中のビット位置 |
| `N` | 1 以上 | 区画のサンプル数 |

規則:

1. サンプル i（i = 0 … N−1）は、区画内のビット `i·w` から `i·w + w − 1` まで。
2. サンプル i のチャネル k の値は、区画内のビット `i·w + pos[k]`。
3. どの `pos[k]` にも当たらないビットの値は**未定義**。host は読まずに無視する（probe は 0 にしなくてよい）。
4. 区画の長さは `ceil(N·w / 8)` バイト。最後のバイトの、`N·w` を超えるビットは未定義。
5. w が 8 の倍数のとき、サンプルは `w/8` バイトの little endian の整数と同じになる（§1 のビットの定義から出る結果で、別の規則ではない）。
   w が 8 の倍数でなければ、サンプルはバイトの境目をまたぎうる。並びはビットの定義だけで決まる。

例:

| 構成 | w | pos | 中身 |
|---|---|---|---|
| 1 ビットずつ詰める probe、1 本 | 1 | [0] | サンプル 0〜7 がビット 0〜7 |
| 3 ビットずつ詰める probe、**3 本** | 3 | [0, 1, 2] | サンプル i は区画内のビット 3i〜3i+2。8 サンプルが 3 バイト。サンプル 2 はバイト 0 のビット 6〜7 とバイト 1 のビット 0 |
| 1 バイト単位でしか取れない probe、1 本 | 8 | [0] | 1 バイトが 1 サンプル。ビット 1〜7 は未定義 |
| GPIO のポートの 1 バイトをそのまま取る probe、ピンがビット 5 | 8 | [5] | ビット 5 だけが意味を持つ |
| 4 ビット単位で詰める probe、**3 本** | 4 | [0, 1, 2] | ビット 0〜2 = サンプル 2m の ch0〜2、ビット 3 未定義、ビット 4〜6 = サンプル 2m+1 の ch0〜2、ビット 7 未定義 |
| 1 バイト 1 サンプルの probe、**3 本** | 8 | [0, 1, 2] | 1 バイト 1 サンプル、ビット 3〜7 未定義 |
| 16 ビット単位で詰める probe、9 本 | 16 | [0 … 8] | 2 バイトで 1 サンプル（little endian）、ビット 9〜15 未定義 |

### 1.2 アナログ

configure の応答で probe が返す値:

| 値 | 範囲 | 意味 |
|---|---|---|
| `s` | 8, 16, 32 のどれか | 1 つの値を入れる枠のビット数 |
| `o`, `b` | 0 ≤ o、1 ≤ b ≤ 31、o + b ≤ s | 枠の中の値の位置（ビット o から b ビット、符号なし。b ≤ 31 なので値は zero(i32) と trigger の value(u32) で表せる） |
| `C` | 1 以上 | planで割り当てたアナログの役割の数 |
| `order[m]`（m = 0 … C−1） | planで割り当てた役割番号を、それぞれ1回含む並べ替え | サンプルの中の m 番目の枠が、どの役割（チャネル）か |
| `N` | 1 以上 | 区画のサンプル数 |

規則:

1. 枠は `s/8` バイトの little endian の整数。枠の値の `o` から `o+b−1` ビットが変換の結果（符号なし）。それ以外の
   ビットは未定義（host は無視する）。結果が符号付き（b bit の 2 の補数）の変換器は offset binary で送る: probe は各値の bit b−1 を反転し（2^(b−1) を足して 2^b で割った余り）、返す zero はその分を含む（0 V の値）。
2. サンプル i は、枠 `i·C` から `i·C + C − 1` まで。m 番目の枠がチャネル `order[m]`。
   アナログのチャネル番号はplanの役割番号をそのまま使い、0 … C−1へ振り直さない。例えばrole 1と3なら、
   C = 2、orderは[1,3]または[3,1]。scale、skew、frontend_usedとtriggerのroleも同じ番号を使う。
3. 区画の長さは `N·C·s/8` バイト。
4. チャネル k の電圧 = （値 − `zero[k]`）× `scale_nv[k]`。`zero` と `scale_nv`（nV / 1 値）は configure の応答でチャネルごとに返す（1 次式。曲線の較正は
   別の定義）。**この電圧はprobeの入力ピンの電圧**。前段の減衰を含めて換算した値で、hostは重ねて減衰を掛けない。
5. チャネル k の時刻は、サンプルの時刻から `skew_ns[k]` 遅れる（順番に切り替える ADC の場合）。
6. 値 0（変換器の最小コード）と 2^b − 1（最大コード）は、入力が frontend の変換する範囲のその端か、その外にあったことを表す。
   入力の実際の電圧はわからない。host はこの値を電圧としてではなく、振り切れ（クリップ）として示す: 低い端以下、または高い端以上。
   端は値 0 と 2^b − 1 に規則 4 を当てた電圧（`scale_nv` が負なら値 0 が高い端）。probe はこの値もほかの値と同じく、そのまま送る。

例:

| 構成 | s | o | b | 備考 |
|---|---|---|---|---|
| DMA の 4 バイトのレコードをそのまま送る 12 ビット ADC | 32 | 0 | 12 | ビット 13〜16 のチャネル番号などは未定義として無視される。チャネルの順番がパターンどおりであることが条件（崩れる場合は probe が並べ直すか、そのレートを宣言から外す） |
| 2 バイトのレコードをそのまま送る 12 ビット ADC | 16 | 0 | 12 | 上位 4 ビット（チャネル番号）は未定義 |
| FIFO の 16 ビットをそのまま送る 12 ビット ADC | 16 | 0 | 12 | |
| 8 ビットに縮めた ADC | 8 | 0 | 8 | |

### 1.3 ロジックのブロック（形式 1）

host は configure でチャネル（役割）ごとに**分解能 D**（元のサンプルの数、1 以上）と**運び方**（`carriage`: raw か events）を選ぶ（§3.3 の
carriage。選ばない役割は raw、D = 1）。D > 1 は events だけ（間引きは短い変化を黙って消すので持たない）。

**ブロック**: 区画のデータはブロックの並び。ブロックは元のサンプル L 個を表す（区画の最後のブロックは r = samples mod L 個、r ≥ 1 のとき）。
L は configure の応答の block で返し、**8 の倍数で、どの D の倍数でもあり、L / D ≤ 65536**。ブロックの格子は区画ごとに、区画の
サンプル 0 から始まる。1 つのブロックは、次をこの順に並べる（E は events のチャネルの数、役割の番号の小さい順に e = 0 … E−1）:

| 部分 | 長さ | 中身 |
|---|---|---|
| fallback | ceil(E / 8) byte | ビット e が 1: events のチャネル e（D = 1 のものだけ）を、このブロックでは raw の部分で運ぶ |
| start_level | ceil(E / 8) byte | ビット e: events のチャネル e の、ブロックの最初のサンプルのレベル |
| n | u16 | 出来事の数 |
| raw の部分 | ceil(r · w_b / 8) byte | サンプルごとに w_b ビット（R + そのブロックの fallback の数）。ビット j（j < R）は raw のチャネル j（役割の順）、ビット R + f は fallback の f 番目のチャネル（e の順）。サンプル i はビット `i · w_b` から（§1 のビットの定義） |
| 出来事 | n × 4 byte | tick(u16)、ch(u8: e)、state(u8: bit 7 = 刻みの後のレベル、bit 0〜6 = 刻みの中の変化の数、127 で飽和) |

- R は raw のチャネルの数。L は 8 の倍数なので、raw の部分は w_b によらずバイトの境目で終わる。区画の最後のブロック（r 個）では、
  raw の部分の後ろを次のバイトの境目まで 0 で埋める。形式 1 の応答の layout は w = R、C = R、pos = 0 … R−1（raw のチャネルの並び）。
- **出来事**: チャネル e の刻み t はブロックの元のサンプル `[t · D_e, (t+1) · D_e)`。**その刻みの中でレベルが 1 回以上変わったときだけ**、
  刻みの順に（同じ刻みはチャネルの順に）1 つ出す。変化は前のサンプルとの比較で、刻みの最初のサンプルは前の刻み（ブロックの最初の刻みでは
  start_level）と比べる。fallback のチャネルの出来事は出さない。
- fallback にするかは probe が決める（出来事の方が raw より大きいブロックで使う）。host は見出しのとおりに読む。
- **確かさ**: D = 1 のチャネルは可逆。D > 1 のチャネルは、変化の時刻が刻みの中まで、刻みの後のレベルと変化の数が確か（数が 127 なら
  「少なくとも 127」）。刻みの中の位置と、変化の数の偶奇以外の途中のレベルは分からない。
- **最悪の帯域**（byte / ブロック）: `2·ceil(E/8) + 2 + L·R/8 + Σ_{D_e = 1} L/8 + Σ_{D_e > 1} (L / D_e)·4`。D = 1 の events の
  チャネルは、出来事が L/8 byte（raw で運ぶ大きさ）を超えるブロックで probe が fallback にするので、その分で頭打ちになる。
  例: 16 チャネル、125 MHz、速い 4 本を raw、遅い 12 本を D = 64 の events、L = 4096: 見出し 6 byte、raw 2048 byte、出来事は最悪
  12 · 64 · 4 = 3072 byte。最悪 5126 byte / 32.8 µs = 156 MB/s、遅い線が UART 115200 程度なら約 63.6 MB/s（形式 0 では 250 MB/s）。
  ESP32-P4 のように出来事をソフトで作る probe は、32 bit の語で比べて変化の無い語を飛ばせば、アイドルの多い線で間に合う。間に合わない
  rate やチャネルの数は configure / query で断る。

### 1.4 アナログのブロック（形式 2）

host は configure でチャネル（役割）ごとに**運び方**（`carriage`: packed、minmax、mean）と区間 D を選ぶ（選ばない役割は packed）。

**ブロック**: 区画のデータはブロックの並び。ブロックは元のサンプル L 個を表す（区画の最後は r 個）。L は configure の応答の block で返し、
8 の倍数で、どの D の倍数でもある。1 つのブロックは、layout の order の順に各チャネルの部分を並べ、各部分の後ろを次のバイトの境目まで 0 で埋める:

| 運び方 | チャネルの部分の中身（ビットで詰める、§1 のビットの定義） | 確かさ |
|---|---|---|
| packed | r 個の値（layout の b ビットずつ、枠なし） | 可逆 |
| minmax | 区間ごと（`[k·D, (k+1)·D)`、区画の中の D 点のそろう区間だけ）に min、max の順（b ビットずつ） | 要約: 区間の最小と最大は確か。時刻は区間の中まで |
| mean | 区間ごとに平均（b ビット、元の値の和を D で割って切り捨て） | 要約: 区間の平均（切り捨て）。任意の運び方 |

- 値は §1.2 の規則 1 の値（offset binary を含む）、規則 4〜6 は同じ。
- **最悪の帯域**は固定の大きさ: 各チャネルの部分の byte 数の和。

**ピンの共有**（core §8.1）: ロジックのキャプチャは聞くだけなので、ほかの機能のピンと共有してよい。アナログの入力は
チップによっては pad をアナログの機能に切り替え、そのピンのデジタルの入出力を切る。
- ロジックのplanは出力idleのchannelも受け付け、駆動を変えずに観測する。
- アナログのチャネルを、ほかの fn の plan（ロジックのキャプチャを含む）、線の接続、設定が使うピンと共有できるかは probe が
  決める。**共有できない組み合わせは、plan_apply（と線の attach、設定の set）を rejected unavailable で断る**。どちらが後から
  来ても断る。黙ってほかの機能の読み書きを壊してはならない。
- **plan を取ってもピンの電気的な状態は変わらない**（core §8）。ロジックのキャプチャは決してそれを変えない: 聞くだけである。出力を止めず、
  ほかの機能や idle の出力が駆動しているピンのプルや向きも変えない。アナログのチャネルは start で空きの状態を離れる（pad がデジタルの機能を離れる）。
- アナログの取得が止まるとpadを空きの状態へ戻す（stop、完了、state 5の空き区画待ち、エラー）。planの予約は保つ。
  state 5から再開するときは再びアナログへ切り替える。切替えの時間は区画のstart_nsとgapに反映する。
- idle が出力（mode 3 / 4）の channel へのアナログの plan は rejected unavailable（cause 5）。

## 2. モードと区画

### 2.1 モード

| モード | ふるまい |
|---|---|
| 1 ワンショット | start（とトリガ）の後、samples 個のサンプルを取って止まる（state 4）。host は自分の速さで読む。次の start でデータは消える |
| 2 リピート | ワンショットを次々に、区画の境目に隙間なく、空いている区画にだけ取る。空きが無くなれば止まり（state 5）、release で再開する |
| 3 ストリーミング | リピートと同じく隙間なく取り、ロックを持つ者が購読している間、データを通知で送る |

- triggerは最初の区画の取得を確定する条件である。非即時なら、start後からpretriggerを残すための取得を始めてよい。
  条件成立後の区画には再適用しない。
- probeはstart後にだけ取得し、start前の先回り取得を行わない。

**ストリーミングの規則**:

1. 送る余地が無いとき、probe は**新しい**区画を丸ごと捨てる（すでに積んだデータは送る。§2.2）。捨てた量は、次のデータのフレームの position の飛びと、
   status の flags bit0 に現れる。
2. stopの後も、probeは停止前に取った未送信データを送信対象にする。残りがmin_bytes未満でもmax_delay_msを待たず、
   core §10.4の応答優先・有限の送信保持量の規則で送り出す。エラー終了時も、下のwrite_posより前の残りは同じに扱う。
   受信したpositionの末尾と停止後のstatusのwrite_posの一致は、末尾へ到達したことだけを示す。
   hostが全量受信と判断できるのは、同じgenerationの必要な位置範囲を欠落なく受信またはreadで回収した場合だけである。
   通知や区画の欠落は許され、末尾の通知が届く保証もない。停止したこと自体はstatusで確認する。
   エラーで止まったとき（state 6）は、受け取ったデータのうち write_pos から先を捨てる（§2.2）。
3. ストリーミングでは区画の出来事を送らない（stopped は送る）。
4. 通知で送ったデータはreadで読めないことがある。要求位置の後にも読めるデータが無い場合は、position=write_pos、gap=1、len=0（§3.2）。

### 2.2 区画

1 回のキャプチャは、トラック 1 本の**位置の付いたバイトの並び**（ストリーム、§1）で、区画に分かれる。

| モード | 区画 |
|---|---|
| ワンショット | 1 個（serial 0）。次の start で消える（世代が進む） |
| リピート | 隙間なく続く。host が解放するまで読める。空き区画がなくなったら取得を止め（state 5）、release で空きができたら自動で再開する。再開した最初の区画に flags bit0 が立つ |
| ストリーミング | probe の都合の区切り（DMA の 1 回ぶんなど）。データは probe が送ってくる（§3.4） |

```text
segment : serial(u32), position(u64), samples(u32), start_ns(u64), start_uncertainty_ns(u32), trigger_index(u32), flags(u8), generation(u32)   37 byte
```

| フィールド | 意味 |
|---|---|
| serial | start からの区画の通し番号（0 から。u32 で一周し、core §2.6 で比べる） |
| position | 区画の先頭のバイト位置（start から通し、u64 で一周しない。read と通知の position と同じ空間） |
| samples | 区画のサンプル数（stop で途中で終わった区画は短い） |
| start_ns | 区画の最初のサンプルの時刻の推定値（probe の時計: 起動からの ns、u64 で一周しない）。probe が知っている補正を済ませた値 |
| start_uncertainty_ns | start_ns の不確かさ（±ns）。probe が見積もれる範囲の目安で、保証ではない |
| trigger_index | 区画の中でトリガが立ったサンプルの番号。トリガを含まない区画は 0xFFFFFFFF |
| flags | bit0 前の区画との間が空いた（リピートで空き区画がなかった、ストリーミングで押し出された）、bit1 短い（stop で終わった）、bit2 時間の基準が曲がった（予定の時刻を 1 サンプル周期以上過ぎて取ったサンプルがある） |
| generation | この区画の世代（冒頭の非再利用の規則） |

- 区画の中は連続を約束する。リピートとストリーミングでは、flags bit0 が立っていない限り、区画は前の区画の直後から続く。
- **区画の隙間と、区画の中の落とし**を、落とした理由で分ける:
  - **隙間**（flags bit0）: 置き場（リピートの空き区画、ストリーミングの送る余地）が無くて、probe が区画を丸ごと取らない（捨てる）とき
    だけ。probe はそれを区画の始まりで決める: 区画は、その全部を置ける場所があるときだけ始める。取らなかった区画の次に取る区画に
    flags bit0 を立て、取得は続く。
  - **区画の中の落とし**（エラー）: それ以外の理由（取り込みのキューやリングのあふれ、DMA やペリフェラルの失敗）で落としたサンプルは、
    区画の境目にあっても、そのサンプルを含むはずの区画の中の落としである。その区画はデータではない: segments に載せず、出来事 segment を
    送らない。トラックはエラーで止まる（state 6、stopped reason 2）。error は、あふれなら 2（置き場）、DMA やペリフェラルの失敗なら 1。
    status の flags bit0 も立つ。status の write_pos はその区画の先頭（その区画の分を数えない）。read は write_pos から先を返さない。
- trigger待ちのpretrigger ringは公開streamではない。trigger/forceで最初の区画の保持範囲を選ぶまでは
  write_pos=0とし、read/通知へそのringを返さない。同じ公開positionのbyteを待ち中に差し替えない。
- probeは区画が終わる前に、確定した完全なbyteをread/通知で返してよい。
  wが8の倍数でないlogicでも、まだ後のsampleで変わる末尾byteは返さず、区画終了時だけpaddingを含む最後のbyteを返す。
  区画が終わるまで、そのデータが区画として出るかは決まっていない: **トラックがエラーで止まったら、host は受け取ったデータのうち
  write_pos から先（position が write_pos 以上のバイト）を捨てる**。区画として出た（segments に載った、出来事 segment が来た）区画の
  データは、その後のエラーで取り消されない。
- flags bit2 は、probe が自分で遅れを見つけられるときに立てる。
- 区画の情報は本文とは別の小さなリングにためる（いくつ覚えるかは probe が決める）。

## 3. 操作

### 3.1 役割（plan）

- 役割 k = チャネル k（ロジックは 0〜127、アナログは 0〜63）。アナログの役割は連番でなくてよい。
  ロジックのpos配列は役割の番号の小さい順。アナログの枠の順はlayout.orderが示し、各値はplanの役割番号そのもの（§1.2）。
- ADC のチャネルを持たないピンは、アナログの plan で拒否する。

### 3.2 操作

| op | 名前 | 要求 | 応答 | ロック | 要否 |
|---:|---|---|---|---|---|
| 0x10 | configure | 設定のTLV（§3.3） | 実際の値のTLV（§3.3） | 必要 | 必須 |
| 0x11 | start | — | generation(u32)、[TLV] | 必要 | 必須 |
| 0x12 | stop | — | — | 必要 | 必須 |
| 0x13 | force | — | —（トリガ待ちなら条件を強制する） | 必要 | 任意 |
| 0x14 | status | — | state(u8)、serial_done(u32)、write_pos(u64)、flags(u8)、generation(u32)、[TLV error] | 不要 | 必須 |
| 0x15 | read | generation(u32)、position(u64)、max(u16) | position(u64)、flags(u8: bit0 more、bit1 gap)、len(u16)、data、[TLV] | 不要 | 必須 |
| 0x16 | segments | from_serial(u32) | more(u8)、count(u8)、count × 区画の情報（§2）、[TLV] | 不要 | 必須 |
| 0x17 | release | generation(u32)、serial(u32) | —（serial以下の区画を使い回してよい） | 必要 | mode 2では必須、ほかでは任意 |
| 0x18 | query | 設定のTLV（configureと同じ） | 実際の値のTLV（設定はしない） | 不要 | 任意 |
| 0x19 | calibration | — | 較正の情報のTLV（§3.7） | 不要 | アナログで任意、ロジックでは提供しない |
| 0x01 | subscribe | core §10.3 | — | 必要 | 任意（mode 3では必須、unsubscribeと組） |
| 0x02 | unsubscribe | core §10.3 | — | 必要 | subscribeと組 |

- state: 0 未設定、1 設定済み、2 トリガ待ち、3 取得中、4 完了（ワンショット）、5 止まっている（リピートで空き区画なし）、
  6 エラー。
- `serial_done` は次に終わる区画の serial（start から終わった区画の数を 2^32 で割った余り）、`write_pos` は取り終えたバイト位置（position の空間。**捨てた分を含む**: 次に書くバイトの位置）。
- status の `flags`: bit0 データを落とした（ストリーミングで丸ごと捨てた区画（§2.1 の規則 1）か、区画の中の落とし（§2.2））、bit1 時間の基準が曲がった
  （区画の flags の bit2 と同じ）。ほかのビットは予約（0）。**start で 0 に戻し、その回の累積**。state 6 のときは応答の TLV 0x01 error（u8:
  1 DMA / ペリフェラル、2 置き場、3 時計。registry の enum `error`）で理由を返す。probe の詳しい理由は、名前つきの拡張 TLV（core §2.2）で足してよい。
- **generation**: readと、提供するreleaseは今の世代を要求に置く。違えばunavailable（cause 6）。start前は0。
  releaseのmode別no-opより先に世代を検証する。世代は半周の新旧比較を行わない（core §2.6）。
- readの要求位置が使い回された/押し出された場合、次の読める位置へ進めてgapを立てる。
  後にも読めるデータが無い場合は、position=write_pos、gap=1、len=0。
  要求位置がwrite_pos以上ならposition=write_pos、gap=0、len=0。max=0も空の成功で、位置とgapは同じ検証規則に従う。
- release はリピートだけ（ワンショットとストリーミングでは何もせず成功）。終わった区画のうち、serial かそれより前（inclusive、core §2.6 で
  比べる）のものを解放する。まだ終わっていない区画は解放しない（serial がそれより先でも、解放するのは終わった区画だけ）。state 5 で空きが
  できればprobeは自動で取得を再開し（state 3）、再開した最初の区画にflags bit0を立てる。空き区画なしではstoppedを送らない。
- read が実際に返す量は probe が決める（max 以下で、応答が max_frame に収まる量）。
- segments は [共通部品](oep-if-common.ja.md) §1.3 の通し番号のページングで答える（next は serial_done、残っているのは probe が情報を
  覚えている区画）。

**状態の遷移**（行 = 今の state、列 = 契機。「—」は何もせず成功。force の列は force を持つ probe に当てはまる）:

| state | configure | start | stop | force | release | 自動 |
|---:|---|---|---|---|---|---|
| 0 未設定 | → 1 | unavailable 6 | — | — | — | plan 無しの configure / query も unavailable 6 |
| 1 設定済み | → 1 | → 2（トリガあり）/ 3。世代 +1、区画は消える | — | — | — | |
| 2 トリガ待ち | unavailable 6 | unavailable 6 | → 1（stopped 1） | → 3 | — | トリガ → 3（triggered）、エラー → 6（stopped 3） |
| 3 取得中 | unavailable 6 | unavailable 6 | → 1（stopped 1、短い区画 bit1） | — | 空きを返す | 完了 → 4（stopped 0）、空き無し → 5、エラー → 6（stopped 3） |
| 4 完了 | → 1 | → 2 / 3（世代 +1） | — | — | — | |
| 5 止まっている | unavailable 6 | unavailable 6 | → 1 | — | 空きができれば → 3（flags bit0） | |
| 6 エラー | → 1 | → 2 / 3（世代 +1） | → 1 | — | — | |

**エラー**: トラックが state 6 に入るのは取得の失敗（§2.2 の区画の中の落としを含む）のときだけで、そのときは理由によらず必ず
出来事 stopped を reason 2 と、status の error と同じ error で送る（購読していれば。§3.4）。

planの割り当て（role, channel）の集合が変わるplan_applyは、state 2/3/5ではunavailable（cause 6）で断る。ほかのstateでは設定・データ・区画を無効にしstate 0へ戻す。
同じ集合の再指定はplan §2.1に従う。いずれもgenerationは戻さず、次のstartで進める。
plan_release（[plan](oep-if-plan.ja.md)）か、セッションの終わり（end、lease の期限切れ、force、core §9）で plan が解けたら state 0 に戻り、データも区画も消える（read は空）。mode 3（ストリーミング）の
start は、その fn の購読が無ければ rejected unavailable（cause 6）。取得中に購読が消えたら取り続け、送れない分は捨てる（position が飛ぶ）。

**startの時間**: 取得が始まってからも、応答を生成した後は通常の要求処理とleaseの規則に従う。
通信を処理できない有限な取得は、その処理をstart要求の中に含め、受付を再開できてから答えてよい。
その間もcore §4.4の一般の受信保証を保つ。経路が1つでmax_inflight=1なら、hostはstartの応答まで次の新規要求を送らない。
hostがほかの経路も静かにすることを前提にしてはならない。この条件を満たせない値の組も、configure/queryで副作用前にunsupportedとして断る。
例えば割込みを使わない即時ワンショットは、取得完了後に答えられる。全処理はmax_op_msのうちに終える。
その上限に収まる開始/受付再開を実現できない値の組は、configure/queryでunsupportedとして副作用前に断る。
start成功は取得を開始できたことを示す。応答時点で完了や取得エラーになっていてもよく、取得の結果はstatus/segmentsで読む。
通信停止中は通常の実行中要求と同じleaseの扱いであり、応答後の待ち時間やleaseに別の例外を設けない。
受理したstartで初期化/開始が失敗した場合はstate 6とerrorを設定し、completed failedで同じgenerationの固定形を返す。

### 3.3 configure

configure成功は旧データ/区画を消し、state 1へ戻す。generationは保ち、次のstartで進める。queryは変更しない。

**設定の TLV**（扱えない値は、core §2.3 のとおり configure 全体を rejected unsupported（受け取ったままの tag）で断る）:

| tag | 名前 | 値 | 対象 | 送るか（省略したとき） |
|---|---|---|---|---|
| 0x01 | mode | u8: 1 ワンショット、2 リピート、3 ストリーミング | 両方 | 必須 |
| 0x02 | rate | rate_hz(u32)（アナログはチャネルあたり。1 Hz 以上） | 両方 | 必須 |
| 0x03 | samples | u32（1 区画のサンプル数。1 以上） | 両方 | mode 1 / 2 で必須。mode 3 では送らない |
| 0x04 | segments | u32（リピートの区画の数。1 以上） | 両方 | mode 2 だけ（probe が決める） |
| 0x05 | trigger | type(u8)、role(u8)、value(u32) | 両方 | 任意（type 0 即時） |
| 0x06 | pretrigger | u32（トリガより前に残すサンプル数） | 両方 | trigger の type が 0 でないときだけ（0） |
| 0x07 | frontend | role(u8)、frontend(u8: describe の frontend の番号)。チャネルごとに 1 つ。繰り返す（core §2.3）。同じ role に 2 つあれば rejected malformed | アナログ | 任意（そのチャネルは probe が選ぶ） |
| 0x08 | format | u8: データの形式（§1、registry `data_format`）。describe の formats に無い番号は unsupported（受け取った tag） | 両方 | 任意（0）。0 以外は critical で送る |
| 0x10 | format_name | 名前（text、1〜64 byte、§1 の名前付きの形式）。describe の format_names に無い名前は unsupported | 両方 | format 0xFF のときだけ。critical で送る |
| 0x11 | data_path | u8: 0 OEP の通知と read、1 外部の経路（§3.9） | 両方 | 任意（0）。1 は critical で送る |
| 0x09 | carriage | role(u8)、kind(u8)、d(u32)。チャネルの運び方と分解能（§1.3 / §1.4）。ロジックの kind は enum `logic_carriage`（0 raw、1 events）、アナログは `analog_carriage`（0 packed、1 minmax、2 mean）。役割ごとに 1 つ、繰り返す | 両方 | format 1 / 2 のときだけ（無い役割は raw / packed、d 1）。critical で送る |
| 0x0A | trigger_pulse | level(u8: パルスの間のレベル)、cond(u8: 0 長い、1 短い、2 範囲)、min(u32)、max(u32)（元のサンプルの数。cond 0 は min より長い、1 は max より短い、2 は min 以上 max 以下） | ロジック | trigger の type 5（pulse）のときだけ |
| 0x0B | trigger_pattern | edge_role(u8: 0xFF なし)、edge(u8: trigger の edge の value)、n(u8)、mask(n byte)、value(n byte)（ビット k が役割 k。mask の立つ役割がすべて value のレベルのとき。edge_role がなければその間ずっと、あればその役割のエッジの瞬間） | ロジック | trigger の type 6（pattern）のときだけ。1 つだけ（並べた OR は予約。2 つ以上は unsupported） |

- **契約**（configure と query で同じ）: 必須の TLV が無ければ rejected malformed。表の「だけ」「送らない」に反する TLV（mode 3 の
  samples と segments、mode 1 の segments、type 0 または trigger 無しの pretrigger）は、値によらず rejected unsupported（受け取ったままの tag）。
  trigger の type が 0 でなく、その role がその fn の plan に無ければ rejected unavailable（cause 6）。type 0 の role と value は使わない:
  host は 0 を送り、probe は見ない（plan に無い role でも断らない）。pretrigger が max_pretrigger を超えるか、mode 1 / 2 で samples（切り下げた
  後）以上なら rejected unsupported（pretrigger の tag）。mode 3 では samples が無いので、pretrigger を縛るのは max_pretrigger と、下の
  挙げていない断りだけ。表が「1 以上」とする値（rate、samples、segments）の 0 は rejected malformed（定義が除く値、core §2.3）。
  断るときは何も変えない。
- **critical の bit**: この表の TLV は、その対象の probe がどれも実装するので、host は critical の bit を付けずに送る（付いていても probe は
  同じに扱う、core §2.3）。critical で送るのは、実装しない probe がありうる TLV（将来の任意機能など）だけ。
- **挙げていない断り**: この節が挙げる断りは全部ではない。probe は、自分が扱えないほかの値と値の組み合わせ（宣言で表せない
  probe 自身の上限。例: pretrigger と samples の差の下限）も、core §2.3 のとおり rejected unsupported で断る。tag はその値を持つ TLV の
  受け取ったままのtagで、組合せならそのTLVのどれか1つ。samples/segmentsの容量超過とrateの丸めは下の規則に従う。
  queryを提供する場合は、実現可能値を設定せずに確かめられる。
- **断りが 2 つ以上当たるとき**（例: mode 1 で samples が無く、ほかの TLV の値も扱えない）、probe は当たったどれか 1 つで答える（core §4.3 の
  順 4）。この節は順を決めない。host は理由の順に頼らない。
- **問い合わせは別の操作（0x18）**。configure の TLV のフラグにすると、probe はロックの要否を操作の番号で決めるので、
  ロックなしの問い合わせができない。問い合わせは今の設定と取ったデータを壊さない。
  planがあれば、state 0〜6のどの状態でも、束ねたトラックでも、要求の実現可能値を照会できる。
  state 2/3/5や、capture-groupに束ねられていることだけを理由に断らない。queryは状態・世代・
  取得中の設定・データ・区画・group bindを変えず、要求値も適用しない。planがなければunavailable cause 6。
  取得の時間経過による進行は続く（照会の前後で時刻が進めば、新しいsampleが取られてよい）。
- trigger の type: 0 即時（省略時）、1 レベル（value 0 / 1）、2 エッジ（value 0 立ち上がり / 1 立ち下がり / 2 両方）、
  3 しきい値を上向きに横切る、4 下向きに横切る（value は o / b で切り出した後の ADC の値）、5 パルス幅（trigger_pulse、role の線）、
  6 パターン（trigger_pattern。role と value は使わない）、7 linked（組の出来事の元に従う、§4.4。role と value は使わない）。
  1、2、5、6 はロジック、3、4 はアナログ、0 と 7 は両方。宣言に無い type は rejected unsupported。
- **トリガは元のサンプルで判定する**: 形式 1 / 2 で縮約するチャネル（D > 1、minmax、mean）でも、条件は縮約の前の値で判定し、パルスの幅も
  元のサンプルで数える。
- **carriage**（形式 1 / 2）: d = 0、ロジックの raw で d > 1、同じ role に 2 つ、format 1 / 2 の無い要求の carriage は rejected malformed。
  describe の carriage に無い kind か範囲の外の d は rejected unsupported（受け取った tag）。plan に無い role は rejected unavailable（cause 6）。
  L の条件（§1.3 / §1.4）を満たせない d の組み合わせ、その rate とチャネルの数で間に合わない設定は rejected unsupported（carriage の tag）。
- linked の trigger は、出来事の元を持つ組（§4.4）に束ねたときだけ使える。束ねずに start すれば rejected unavailable（cause 6）。pretrigger を
  付けてよい（そのトラックの元のサンプルの数）。
- **samplesは区画のsample総数**（pretriggerを含む）。トリガが早く立ってプリトリガの分が足りなければ、区画は短く、trigger_indexはそのまま
  小さい。force で始めたときは trigger_index = その瞬間のサンプルで triggered を送る。type 0（即時）では triggered を送らない。
- **rate**: 宣言したrate_rangeの中で、その役割/モード/設定で保てる最も近い値を使う（同距離はどちらでもよい）。
  役割数などで上限が下がる場合も、この集合で丸めてactual_rateを返す。
  要求値がrate_rangeの外か、この構成で範囲内の値を1つも保てなければunsupported（rateのtag）。
- probe が持てる量を超える samples は、その上限に切り下げ、応答の actual_samples（0x03）
  が正である。host は送った値を仮定せず、actual_samples と actual_segments を読む。
- mode 2のsegmentsも、実際のsamplesと役割数で持てる上限へ切り下げる。省略時はprobeが決め、actual_segmentsは常に1以上。
  samples/segmentsの切り下げだけでは断らない。切り下げ後にpretriggerなどの条件を満たせなければ、その条件のtagで断る。

**応答のTLV**: successはactual_rate/layoutを必ず返す。actual_samplesはmode 1/2、actual_segmentsはmode 2で必須。
アナログのscaleはplanの役割ごとに必須、skewは遅れが0の役割を省いてよい。frontend_used/referenceは任意の診断情報である。
必要な応答が要求経路のframeに収まらなければ、設定を変える前にunsupportedで断る（core §4.4）。

| tag | 名前 | 値 | 対象 |
|---|---|---|---|
| 0x01 | actual_rate | num(u32)、den(u32)（実際のレート = num / den Hz。どちらも 1 以上） | 両方 |
| 0x02 | layout | ロジック: w(u8)、C(u8)、pos[C](u8)。アナログ: s(u8)、o(u8)、b(u8)、C(u8)、order[C](u8)（§1） | 両方 |
| 0x03 | actual_samples | u32 | 両方 |
| 0x04 | actual_segments | u32 | 両方 |
| 0x05 | scale | role(u8)、zero(i32、値)、scale_nv(i32、1 値あたりの nV。負は反転する frontend)。チャネルごとに 1 つ。probe の入力ピンの電圧への 1 次式（§1.2） | アナログ |
| 0x06 | skew | role(u8)、skew_ns(u32)。チャネルごとに1つ（遅れが0の役割は省いてよい） | アナログ |
| 0x07 | frontend_used | role(u8)、frontend(u8: describe の frontend の番号)。チャネルごとに 1 つ。値の意味（入力範囲）はそのfrontendの宣言で決まる | アナログ |
| 0x08 | reference | source(u8、enum `reference_source`: 0 電源、1 内部、2 外部)、mv(u32)、how(u8、enum `reference_how`: 0 公称、1 測った)。ADC の基準電圧。電源が基準の ADC では、同じ生の値の意味が電源電圧で変わる。scale の 1 次式はこの電圧を前提にした換算 | アナログ |
| 0x09 | format | u8: 使うデータの形式（§1）。0 以外では必ず返す。0 では省いてよい | 両方 |
| 0x0A | block | L(u32)。形式 1 / 2 のブロックの元のサンプルの数（§1.3 / §1.4）。形式 1 / 2 で必ず返す | 両方 |
| 0x0E | format_name | 使う名前付きの形式の名前（format 0xFF のとき必ず返す） | 両方 |

### 3.4 通知（core §10）

ロックの持ち主がその fn に subscribe すると、そのインターフェースから次が届く（subscribe と unsubscribe を ops に立てる fn だけ）。
購読しなければ、status と segments のポーリングで同じことが分かる。

| 送るもの | いつ | 中身 |
|---|---|---|
| 出来事 kind 0x01 segment | 区画が終わった（ワンショットの完了も。ストリーミングでは送らない） | 区画の情報（§2）、[TLV] |
| 出来事 kind 0x02 stopped | 取得が止まった | reason(u8: 0 完了、1 stop（host の stop。組（§4）が止めたときも）、2 エラー（state 6 に入るときは必ずこれ、§3.2）)、error(u8: reason 2 の理由、status の error と同じ値)、generation(u32)、[TLV] |
| 出来事 kind 0x03 triggered | トリガが立った | serial(u32)、trigger_index(u32)、trigger_ns(u64: probe の時計でトリガが立った時刻の推定値)、generation(u32)、[TLV] |
| データ（role 0x04） | ストリーミングの間だけ | core §10.2の形。readと同じbyte位置。必須TLV 0x01 generation(u32)と0x02 segment_info（下）を毎frameへ付ける |

**streamingのsegment_info**: `position(u64)、samples(u32)、start_ns(u64)、start_uncertainty_ns(u32)`（24byte）。
positionは区画の先頭、samplesはそのframeを作った時点で取得済みのsample数（1以上）。取得中は後のframeで増え、終了後は最終値。
時刻/不確かさは§2.2の区画と同じ。そのframeのdataはこの1区画の中だけで、区画の境目をまたがない。
未確定の末尾byteを送らない上の規則に従う。終了時のpaddingはsamplesとlayoutから区別する。
hostはdataの絶対positionと区画の起点から区画内のbit/sampleを求め、失った前frameの断片でsampleを補わない。
毎frameに起点と時刻があるので、最初のframe/区画情報が失われても後のframeを解釈できる。GENが違うframeは別の取得である。
frame64では固定見出し15+GEN TLV7+segment_info TLV27を引き、dataは15byteまで。
probeはより大きい経路を使え、mode 3を提供しない最小構成にこの情報/取得bufferを要求しない。

- **出来事はどれも、それが生まれた世代を持つ**（segment は区画の情報の generation）。start の応答の後に前の世代の出来事が届きうる
  （core §10.4）。host は今の世代と違う出来事を前の世代のものとして扱う。
- ストリーミングは subscribe が前提（データは probe が送る。ストリーミングの mode を宣言する fn は subscribe と unsubscribe を ops に立てる）。

### 3.5 describe で宣言するもの

| tag | 名前 | 値 |
|---|---|---|
| 0x07 | ops | 持つ op（core §7.4）: query、force、subscribe と unsubscribe は持つときだけ立てる |
| 0x05 | features | revision 1はビットを定めない |
| 0x40 | mode | mode(u8)、max_samples(u32、1 区画)、max_segments(u32)（モードごとに 1 つ。**最大**の置き場で答える。describe は宣言だけなので、その時点の空きでは答えない） |
| 0x41 | rate_range | min_hz(u32)、max_hz(u32)。どちらも1以上、min ≤ max |
| 0x42 | channels | max(u8)。チャネル数の上限 |
| 0x43 | trigger | types(u32: type のビット集合)、max_pretrigger(u32) |
| 0x44 | frontend | frontend(u8: 番号)、range_min_mv(i32)、range_max_mv(i32)。入力ピンの範囲の候補ごとに1つ（アナログ）。番号はconfigureのfrontendで選ぶ |
| 0x45 | formats | u8 の列: 0 のほかに使えるデータの形式（§1）。無ければ 0 だけ |
| 0x46 | carriage | kinds(u8: kind のビット集合)、min_d(u32)、max_d(u32)（D > 1 で使える範囲。D = 1 はいつも使える）。形式 1 / 2 を宣言するとき |
| 0x4A | format_names | 名前（text）。使える名前付きの形式ごとに 1 つ、繰り返す |
| 0x4B | external_data | kind(u8)、値。外部の経路（§3.9）。kind 1 = USB の bulk IN: interface(u8)、endpoint(u8)。kind 2 = TCP: port(u16)。経路ごとに 1 つ |

- 必須の宣言はops、1つ以上のmode、rate_range、channels、trigger、およびplanで使うrole_channels/channel_group。
  アナログはfrontendも1つ以上宣言する。featuresは値0なら省略できる。
  triggerの番号はlogic/analog各インターフェースの空間で、両方とも即時（type 0）を含める。
- modeは少なくとも1つ宣言する。1/2/3を全部宣言する必要はなく、対応するmodeだけを載せる。
  max_segmentsはmode 2の置き場の上限。mode 1/3では0を送り、hostは使わない。
  宣言したmodeでの値の組合せや実現可能量は、下の目安とconfigure/queryの規則に従う。
- **宣言は目安、configure の応答が正。** 宣言に出ていない組み合わせは query で確かめる。

### 3.6 拡張の境界

mode、role、TLVなどの未割当値はcore §2.5/§12に従う。`oep.`の定義への追加はOEPが行い、第三者は自分の名前のインターフェースを定義する。
用途を予想した番号範囲は予約しない。triggerのtypeは現行describeのu32ビット集合に収まる0〜31であり、
32以上が必要なら宣言の形も含めた別インターフェースまたは新revisionで扱う。

外部clock、signed/32 bitのsampleや整数nVで表せない換算などは、既存hostが誤読しない定義で追加する。
別の並びのdataはデータの形式（§1）の番号で足す（hostが求めた番号だけが使われる）。時間軸やdataの意味を変える場合もcore §2.8に従う。

**OEP が revision を上げずに足すもの**（どれも任意で、持つかは describe で分かる）:

| 足すもの | 宣言 | 知らない側 |
|---|---|---|
| 前段・取り方の設定 | describe の TLV | host は知らない describe の TLV を読み飛ばす。probe は知らない configure の TLV を、印なしなら無視し、critical なら unsupported で断る（core §2.3）。動作を変える設定は critical で送る |
| データの並び | describe の formats、registry `data_format` | probe は host が求めた形式だけを使う。host は知らない形式を読まない |
| トリガの種類 | describe の trigger の types のビット | probe は宣言しない type を unsupported で断る |
| 出来事の元の種類（kind） | capture-group の bind の trigger_source | 持たない probe は unsupported で断る |
| 組の機能 | capture-group の features のビット | host は知らないビットを無視する |
| 応答や区画・出来事の情報 | 応答の TLV | host は知らない TLV を読み飛ばす |

**数の上限と、その先**: レートは u32 の Hz（約 4.29 GHz）、1 区画は u32 のサンプル、時刻は ns、チャネルは u8、トリガの type は 32 種類、
message は u16 の長さ。商用の USB ロジックアナライザや MSO のロジック（1 GS/s 前後、数十チャネル、数 G サンプルの深さ）はこの中に収まる。
これを超える計測器（GSa/s 級のアナログ、数百チャネル、message の数が上限になる速さ）は、別のインターフェースか external binding
（[構想](../docs/project-concept.ja.md)、生のデータを別の経路で運ぶ）で扱う。ストリーミングの位置は u64 で、欠落は seq ではなく位置で判定する。
複数trackの即時開始はcapture-group（§4）を使い、プロトコル解析など異なる意味の結果は別インターフェースで定義する。

### 3.7 calibration（アナログ）

ADC の値を電圧に換算するための、probe が持っている情報を**生のまま**返す。probe は補正を適用しない（read の値はいつも生の値。
換算は host が選ぶ。曲線の補正は測れる範囲の上下を削ることがあり、保存の段階で強制しない）。持たない情報は返さない。そうした情報を何も持たない probe は、TLV を返さない（空の成功）。

成功応答は、この操作が返す下表の情報を、その時点で持つ分すべて含む。個々のTLVの値と応答全体が要求経路のmax_frameに収まらなければ、
core §4.4に従いrejected unsupported（固定部分の印0）で断る。容量を理由にfactoryのrawを切り詰めたり、情報を省いて成功にしたりしない。
この操作は保持済みの情報を読み、ADCの測定や取得状態を変えない。情報が無いことと容量不足を区別し、completed failed / partialは返さない。
大きい情報の選択取得やページングを追加する場合は、core §12に従う新しい任意opで定義できる。

| tag | 名前 | 値 |
|---|---:|---|
| 0x01 | factory | frontend(u8)、scheme_len(u8)、scheme(text)、raw_len(u16)、raw。出荷時にチップに書かれた較正の値を、読んだまま。scheme は形式の名前で、逆 DNS（形式の持ち主の名前空間。`a-z 0-9 - .`、1〜64 byte）。raw の解釈は scheme の定義に従う。frontend ごとに 1 つ（frontend に依らないものは 0xFF） |
| 0x02 | vrefint | raw(u32)、ns(u64)、nominal_mv(u32)。内部の基準電圧（Vrefint など）を、最後の start（capture-group の start を含む）の直後に同じ ADC で測った生の値、その時刻、その基準電圧の公称値（mV。電源電圧の逆算に使う）。基準電圧が電源の ADC で、実際の電源電圧を逆算するのに使う。測れない probe は返さない |

- チップの型番とリビジョンは core の describe の chip（core §7.5）、firmware の版は同じく firmware。
- frontend ごとの減衰と測れる範囲は describe の frontend（§3.5）、チャネルごとに選ばれた frontend は configure の応答の
  frontend_used、基準電圧は reference（§3.3）。

### 3.8 前段と外部クロック（任意）

商用の計測器に一般的な前段の設定。どれも任意で、describe の宣言を持つ probe だけが受ける。configure の TLV は動作を変えるので critical で
送り（持たない probe は unsupported）、応答で使った値を返す。費用は configure の数 byte で、サンプルごとの費用は無い。

| 置き場 | tag | 名前 | 値 | 対象 |
|---|---:|---|---|---|
| describe | 0x47 | threshold | group(u8)、min_mv(i32)、max_mv(i32)、step_mv(u32: 0 は候補だけ)、n(u8)、n × preset_mv(i32)、m(u8)、m × channel(u16)。入力のしきい値を共有するチャネルの群ごとに 1 つ。固定の probe は min = max で、記録のために宣言してよい | ロジック |
| configure | 0x0C | threshold | group(u8)、mv(i32)、hysteresis_mv(u32: 0 は無し)。群ごとに 1 つ | ロジック |
| 応答 | 0x0B | threshold_used | group(u8)、mv(i32)、hysteresis_mv(u32) | ロジック |
| describe | 0x48 | coupling | frontend(u8)、kinds(u8: ビット 0 DC、1 AC、2 GND) | アナログ |
| describe | 0x49 | offset | frontend(u8)、min_mv(i32)、max_mv(i32)、step_mv(u32) | アナログ |
| configure | 0x0D | coupling | role(u8)、kind(u8: 0 DC、1 AC、2 GND) | アナログ |
| configure | 0x0E | offset | role(u8)、mv(i32: 入力から引く電圧) | アナログ |
| 応答 | 0x0C | coupling_used | role(u8)、kind(u8) | アナログ |
| 応答 | 0x0D | offset_used | role(u8)、mv(i32) | アナログ |
| configure | 0x0F | clock | role(u8)、edge(u8: 0 立ち上がり、1 立ち下がり、2 両方) | ロジック（予約） |

- しきい値: probe は mv に最も近い使える値（step か preset）を使い、threshold_used で返す。範囲の外は unsupported。
- 結合とオフセット: scale の 1 次式（§1.2 規則 4）は、offset を含めた入力ピンの電圧への換算。AC では直流の成分が無いので、host は平均の値を
  電圧の照合に使わない。
- 外部クロック（clock）: 番号と形だけを予約する（サンプルをその役割の線のエッジで取る）。規則は追加の定義で決め、それまでは unsupported。

### 3.9 データの外部の経路（任意）

**制御は OEP の経路のまま、データだけを別の経路に OEP の見出しなしで出す**（external binding、[構想](../docs/project-concept.ja.md)）。データが CPU を
通らない機材（GPIF などから USB へ直接出す）や、見出しの費用が間に合わない速さのための任意の定義。describe の external_data で経路を宣言する。

- configure の data_path 1（critical）で選ぶ。v1 では **1 つの経路は 1 つのトラック**（複数のトラックを 1 つの経路に混ぜる形は、後で
  名前付きの形式か kind で足す）。
- data_path 1 のトラックは、OEP のデータの通知を出さず、read は rejected unavailable（cause 6）。制御（configure、start、stop、status、segments、
  release）と出来事は OEP の経路のまま。
- **世代の始まりの印**: start の後、probe は経路に**最初に 16 byte の印**を出す: magic "OEPX"（4 byte）、generation(u32)、fn(u16)、format(u8)、
  予約（5 byte、0）。position はその印の後のバイトから 0 で数える（§1 のバイトの並び）。host は印で世代に同期する（読み残しや再接続の後も）。
- **世代の終わり**: 制御の経路と外部の経路の到着順は保証されないので、境目はバイトの数で決める。probe は stop か完了で、その世代の
  データを送り切るか（端数のパケットも送る）捨て、status の write_pos を**実際に経路へ送ったバイトの数**（印を除く）にする。host は write_pos
  まで読んでその世代を終える。その後のバイトは、次の印から読む。
- **落とし**: 経路（bulk、TCP）そのものは落とさない。probe の中のあふれは、§2.2 の区画の隙間、status の dropped、segments の gap で知らせる。
- **経路が切れたら**（USB の切断、TCP の切断）、そのトラックはエラーで止まる（state 6、stopped reason 2）。
- 費用: 1 世代に 16 byte。データごとの見出しは無い。

## 4. `oep.fixture.capture-group`（一括開始と出来事の元）

別々のlogic/analogトラックを同じ要求で開始する任意のインターフェース。即時に始めるのが基本で、出来事の元（§4.4、任意）を持てば、その出来事を
起点に全トラックが取る（ロジックの出来事でアナログを見る、電源の落ち込みでロジックを見る）。単独のトラックの高度なトリガも、1 トラックの組で表す。
時間の正確な一致を保証せず、各区画のstart_ns/不確かさでhostが並べる。

### 4.1 操作

| op | 名前 | 要求 | 応答 | ロック | 要否 |
|---:|---|---|---|---|---|
| 0x1A | bind | n(u8)、n × fn(u16)、[TLV] | — | 必要 | 必須 |
| 0x11 | start | [TLV] | start_ns(u64)、generation(u32)、n(u8)、n × (fn(u16)、generation(u32))、[TLV] | 必要 | 必須 |
| 0x12 | stop | [TLV] | — | 必要 | 必須 |
| 0x13 | force | [TLV] | —（出来事を待っていれば、今すぐ起きたものとする。§4.4） | 必要 | 任意（§4.4 を持つときだけ） |
| 0x14 | status | [TLV] | state(u8)、start_ns(u64)、generation(u32)、[TLV] | 不要 | 必須 |
| 0x01 | subscribe | core §10.3 | — | 必要 | 任意（unsubscribeと組） |
| 0x02 | unsubscribe | core §10.3 | — | 必要 | subscribeと組 |

- bindは設定済みのlogic/analogのfnを束ねる。全trackは同じmodeで、triggerは即時だけ（出来事の元を持つ組は§4.4）。
  新しい組へ入れるtrackはstate 1/4/6で、単独取得や別の組で使用中ならcause 6/4で断る。
  同じfnリストの再指定は状態を保つno-op。異なるリストへの変更は組がstate 3の間cause 6で断る。
  重複fnはmalformed、tracksに無いfnはunsupported（固定部分の印0）。状態/trigger/modeが合わない場合はunavailable cause 6、
  同時に使う資源が足りない場合はcause 2。fnの診断TLVはcore §4.3。拒否は全検証の後、副作用前に行う。
- n=0は束ねを解く。取得中の組（state 3）ではunavailable cause 6。束ねていなければno-op。
  束ねはsessionの資源（core §9）。束ねたtrackのconfigure/start/stop/forceとplanの変更/解放はcause 4で拒否。
  同じplanの割り当て（role, channel）の集合はno-op、query/read/status/segments/releaseは各trackの通常規則で使える。
- bindは、同じ経路のstart成功応答（18+6×n byte）がframeへ収まることも確かめ、収まらなければunsupported（固定部分の印0）。
- startは束ねがあり、全trackがstate 1/4/6のときだけ受け付ける。それ以外は副作用前にunavailable cause 6で断り、世代・状態・データを保つ。
  組/全trackの世代の空き、mode/資源/購読などをすべて確かめてから、新しい世代を割り当てて全trackの旧データ/区画を消し、開始する。
  組の世代も冒頭と同じ非再利用の規則。nとfnの順はbindと同じ。start_nsは最初のtrackを開始する時点の推定値。
  start前のstart_nsは全bit1。全処理/受付再開は§3.2のstartと同じ時間規則。
- 初期化/取得の失敗でtrackがstate 6になれば組も6とし、ほかのtrackをstopと同じに止める。
  完了済みのtrackはdata/区画を保持する。start自体が開始に失敗した場合はcompleted failedで同じ固定形を返す。
  このstartで未開始のtrackはstate 1、開始済みのtrackは§3.2のstop後のstateとなる。失敗したtrackは6を保つ。
  未開始を含め、割当済みの世代は戻さない。次のstartは上の開始可能状態と通常の資源検証に従う。
- stopは全trackへ適用し、短い区画とpadは各trackの規則に従う。束ねなしのstopはno-op。startは束ねなしならcause 6。
- statusのstate: 束ねなし0、どれかが6なら6、開始後に全部4なら4、出来事を待っていれば2（§4.4）、どれかが3/5なら3、それ以外1。
  groupのgenerationはbind変更では戻さず、次のstartで進める。groupを起動しない段階のtrack世代も変えない。

### 4.2 通知

採用したsubscribeへはstopped（kind 0x02）だけを送る。
`reason(u8: 0 全track完了、1 stop、2 error)、error(u8: reason 2のtrack error、ほかは0)、generation(u32)、[TLV]`。
組がerrorならtrackのどれか1つのerrorを返す。過去の通知を区別するため、groupの世代は省略しない。
即時のgroup/trackからtriggeredを送らない（出来事の元を持つ組は§4.4のtriggeredを送る）。各trackの通知はそのfnの購読へ送り、group購読で代用しない。

### 4.3 describe

必須はopsとtracks（tag 0x40: n(u8)、n × fn(u16)、n≥1）。個々の組合せが実現可能かはbindで確かめる。
features の bit 0（`trigger_source`）は §4.4 の出来事の元を持つことを表す。ほかの bit は OEP が後から割り当てる（host は知らない bit を無視する）。

### 4.4 出来事の元（任意: features bit 0）

**出来事の元（trigger_source）は、組の全トラックの起点になる 1 つの出来事を決める。**

- **bind の TLV** 0x01 trigger_source: kind(u8)、値。host は critical の bit を付けて送る（tag 0x81）。持たない probe は rejected unsupported
  （受け取ったままの tag）で断り、即時の組として黙って始めない。
  - kind 1（トラックの条件）: fn(u16)。束ねる fn のどれか（元のトラック）。そのトラックの configure の trigger（edge、level、pulse、pattern、cross
    など、そのインターフェースの type）が出来事の条件。束ねない fn は malformed。
  - kind 2（外部の入力）、多段（出来事の並び）、タイマ、トリガ出力（出来事をピンに出す）は、kind と役割の番号を追加の定義で足す
    （それまでは unsupported）。
- **元以外のトラック**の trigger は type 7（linked）で、pretrigger はそのトラック自身の元のサンプルの数で持つ（§3.3）。元のトラックの
  trigger が即時（type 0）か linked、元以外のトラックの trigger が linked 以外なら、bind は unavailable（cause 6、payload の TLV fn はそのトラック）。
  トリガが二重にならない。
- **start** で全トラックが取得（pretrigger のリングを含む）を始め、組は出来事を待つ state 2 になる。start_ns は取得を始めた時刻。出来事が
  起きると全トラックが自分の pretrigger と samples で区画を切り、組は state 3 になる。**force**（持つときだけ）は、待っている組で出来事が今
  起きたものとする（待っていなければ何もせず成功）。
- **判定は元のサンプルで**（§3.3）: 元のトラックが縮約する形式でも、条件は縮約の前の値で判定する。
- **各トラックの trigger_index**: 出来事の時刻に最も近い、そのトラックのサンプル。各区画の不確かさは start_uncertainty_ns。
- **出来事の時刻**: trigger_ns（probe の時計での推定値）と trigger_uncertainty_ns（元のトラックのサンプル周期や判定の遅れから来る、±ns。
  区画の start_uncertainty_ns とは別）を、status の応答の TLV 0x02 trigger（fn(u16: force では 0)、ns(u64)、uncertainty_ns(u32)）と出来事
  triggered で返す。起きるまでは TLV を付けない。例: 元がアナログの 1 Msps で、ロジックが 125 MHz なら、uncertainty は 1 µs 前後で、ロジックの
  trigger_index は ±125 サンプルずれうる。
- **出来事** kind 0x03 triggered: trigger_fn(u16)、trigger_ns(u64)、trigger_uncertainty_ns(u32)、generation(u32: 組の世代)、[TLV]。
- 費用: bind の数 byte、status の TLV 17 byte、出来事 1 つ。サンプルごとの費用は無い。持たない probe は何も払わない。
