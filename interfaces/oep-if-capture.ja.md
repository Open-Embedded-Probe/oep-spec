# OEP インターフェース: キャプチャ v1

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](../docs/versioning.ja.md) §6）。本体は [OEP core](../docs/oep-core.ja.md)。
番号の唯一の定義は `registry/oep-v1.toml`。基本と別の定義の線引きは §3.6。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.fixture.logic` | 1 | ロジック（1 トラック） | どの系統にも使う |
| `oep.fixture.analog` | 1 | アナログ（1 トラック） | どの系統にも使う |
| `oep.fixture.capture-group` | 1 | 複数のトラックを一緒に始める（ミックスドシグナル、§4） | どの系統にも使う |

logic と analog は**操作の番号と形が同じ**で、違うのは configure の中身（§3.3）、データの layout（§1）、アナログだけの
calibration（§3.7）だけ。複数トラックの同時開始と時刻合わせは、この 2 つを広げず、トラックを束ねる別のインターフェース
（capture-group、§4）にする。外部クロック、多段トリガなどは別の定義（§3.6）。チャネルごとに縮約して取るロジックは、logic の別の定義
（将来のmultirateなど）。

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
すべてのmode、query、force、capture-groupを実装する義務はない。
対応するmodeはdescribeのmodeで宣言し、宣言しないmodeのconfigure/queryはunsupported（受け取ったmode TLVのtag）で断る。
必須の操作と、採用したmodeのデータ/世代/終了の規則は維持する。ワンショットだけでもsegmentsは取得した区画を返す。releaseはmode 2を提供するときだけ必須。

## 1. データの形

用語: **ストリーム**は、1 回のキャプチャ（1 区画）で probe が返すバイトの並び。バイト位置 0 から始まる。
**ストリームのビット j** は、バイト `floor(j / 8)` のビット `j mod 8`（ビット 0 = LSB）と定める。

### 1.1 ロジック

configure の応答で probe が返す値:

| 値 | 範囲 | 意味 |
|---|---|---|
| `w` | 1〜128 の整数 | 1 サンプルのビット数。probe が選ぶ（チャネル数より大きくてよい） |
| `C` | 1 以上 | チャネル数（plan で割り当てたロジックの役割の数） |
| `pos[k]`（k = 0 … C−1） | 0 ≤ pos[k] < w、互いに異なる | チャネル k（役割の番号の小さい順）の、サンプルの中のビット位置 |
| `N` | 1 以上 | 区画のサンプル数 |

規則:

1. サンプル i（i = 0 … N−1）は、ストリームのビット `i·w` から `i·w + w − 1` まで。
2. サンプル i のチャネル k の値は、ストリームのビット `i·w + pos[k]`。
3. どの `pos[k]` にも当たらないビットの値は**未定義**。host は読まずに無視する（probe は 0 にしなくてよい）。
4. 区画の長さは `ceil(N·w / 8)` バイト。最後のバイトの、`N·w` を超えるビットは未定義。
5. w が 8 の倍数のとき、サンプルは `w/8` バイトの little endian の整数と同じになる（§1 のビットの定義から出る結果で、別の規則ではない）。
   w が 8 の倍数でなければ、サンプルはバイトの境目をまたぎうる。並びはビットの定義だけで決まる。

例:

| 構成 | w | pos | 中身 |
|---|---|---|---|
| 1 ビットずつ詰める probe、1 本 | 1 | [0] | サンプル 0〜7 がビット 0〜7 |
| 3 ビットずつ詰める probe、**3 本** | 3 | [0, 1, 2] | サンプル i はストリームのビット 3i〜3i+2。8 サンプルが 3 バイト。サンプル 2 はバイト 0 のビット 6〜7 とバイト 1 のビット 0 |
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
   別の定義）。**この電圧はProbeの入力ピンの電圧**。前段の減衰を含めて換算した値で、Hostは重ねて減衰を掛けない。
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

**ピンの共有**（core §8.1）: ロジックのキャプチャは聞くだけなので、ほかの機能のピンと共有してよい。アナログの入力は
チップによっては pad をアナログの機能に切り替え、そのピンのデジタルの入出力を切る。
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
- Probeはstart後にだけ取得し、start前の先回り取得を行わない。

**ストリーミングの規則**:

1. 送る余地が無いとき、probe は**新しい**区画を丸ごと捨てる（すでに積んだデータは送る。§2.2）。捨てた量は、次のデータのフレームの position の飛びと、
   status の flags bit0 に現れる。
2. stop の後も、probe は stop の前に取った分を送る。受け取った position の末尾が、stop の後の status の write_pos に等しくなれば、host はすべて受け取っている。
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
    送らない。トラックはエラーで止まる（state 6、stopped reason 3）。error は、あふれなら 2（置き場）、DMA やペリフェラルの失敗なら 1。
    status の flags bit0 も立つ。status の write_pos はその区画の先頭（その区画の分を数えない）。read は write_pos から先を返さない。
- trigger待ちのpretrigger ringは公開streamではない。trigger/forceで最初の区画の保持範囲を選ぶまでは
  write_pos=0とし、read/通知へそのringを返さない。同じ公開positionのbyteを待ち中に差し替えない。
- Probeは区画が終わる前に、確定した完全なbyteをread/通知で返してよい。
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

- opの採用は上表に従い、describeのopsで宣言する。提供しないopはunknown_operation（core §1.2）。
- state: 0 未設定、1 設定済み、2 トリガ待ち、3 取得中、4 完了（ワンショット）、5 止まっている（リピートで空き区画なし）、
  6 エラー。
- `serial_done` は次に終わる区画の serial（start から終わった区画の数を 2^32 で割った余り）、`write_pos` は取り終えたバイト位置（position の空間。**捨てた分を含む**: 次に書くバイトの位置）。
- status の `flags`: bit0 データを落とした（ストリーミングで丸ごと捨てた区画（§2.1 の規則 1）か、区画の中の落とし（§2.2））、bit1 時間の基準が曲がった
  （区画の flags の bit2 と同じ）。ほかのビットは予約（0）。**start で 0 に戻し、その回の累積**。state 6 のときは応答の TLV 0x01 error（u8:
  1 DMA / ペリフェラル、2 置き場、3 時計、0x40〜 probe 固有。registry の enum `error`）で理由を返す。
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
出来事 stopped を reason 3 と、status の error と同じ error で送る（購読していれば。§3.4）。

planの役割の集合が変わるplan_applyは、state 2/3/5ではunavailable（cause 6）で断る。ほかのstateでは設定・データ・区画を無効にしstate 0へ戻す。
同じ集合の再指定は状態とデータを保つ。いずれもgenerationは戻さず、次のstartで進める。
plan_release（[plan](oep-if-plan.ja.md)）か、セッションの終わり（end、lease の期限切れ、force、core §9）で plan が解けたら state 0 に戻り、データも区画も消える（read は空）。mode 3（ストリーミング）の
start は、その fn の購読が無ければ rejected unavailable（cause 6）。取得中に購読が消えたら取り続け、送れない分は捨てる（position が飛ぶ）。

**startの時間**: 取得が始まってからも、応答を送った後は通常の要求処理とleaseの規則に従う。
通信を処理できない有限な取得は、その処理をstart要求の中に含め、受付を再開できてから答えてよい。
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
| 0x40 | mode | u8: 1 ワンショット、2 リピート、3 ストリーミング | 両方 | 必須 |
| 0x42 | rate | rate_hz(u32)（アナログはチャネルあたり。1 Hz 以上） | 両方 | 必須 |
| 0x43 | samples | u32（1 区画のサンプル数。1 以上） | 両方 | mode 1 / 2 で必須。mode 3 では送らない |
| 0x44 | segments | u32（リピートの区画の数。1 以上） | 両方 | mode 2 だけ（probe が決める） |
| 0x45 | trigger | type(u8)、role(u8)、value(u32) | 両方 | 任意（type 0 即時） |
| 0x46 | pretrigger | u32（トリガより前に残すサンプル数） | 両方 | trigger の type が 0 でないときだけ（0） |
| 0x47 | frontend | role(u8)、frontend(u8: describe の frontend の番号)。チャネルごとに 1 つ。繰り返す（core §2.3）。同じ role に 2 つあれば rejected malformed | アナログ | 任意（そのチャネルは probe が選ぶ） |

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
  3 しきい値を上向きに横切る、4 下向きに横切る（value は o / b で切り出した後の ADC の値）。1〜2 はロジック、3〜4 はアナログ。
  宣言に無い type は rejected unsupported。
- **samplesは区画のsample総数**（pretriggerを含む）。トリガが早く立ってプリトリガの分が足りなければ、区画は短く、trigger_indexはそのまま
  小さい。force で始めたときは trigger_index = その瞬間のサンプルで triggered を送る。type 0（即時）では triggered を送らない。
- **rate**: 宣言したrate_rangeの中で、その役割/モード/設定で保てる最も近い値を使う（同距離はどちらでもよい）。
  役割数などで上限が下がる場合も、この集合で丸めてactual_rateを返す。
  要求値がrate_rangeの外か、この構成で範囲内の値を1つも保てなければunsupported（rateのtag）。
- probe が持てる量を超える samples は、その上限に切り下げ、応答の actual_samples（0x52）
  が正である。host は送った値を仮定せず、actual_samples と actual_segments を読む。
- mode 2のsegmentsも、実際のsamplesと役割数で持てる上限へ切り下げる。省略時はProbeが決め、actual_segmentsは常に1以上。
  samples/segmentsの切り下げだけでは断らない。切り下げ後にpretriggerなどの条件を満たせなければ、その条件のtagで断る。

**応答のTLV**: successはactual_rate/layoutを必ず返す。actual_samplesはmode 1/2、actual_segmentsはmode 2で必須。
アナログのscaleはplanの役割ごとに必須、skewは遅れが0の役割を省いてよい。frontend_used/referenceは任意の診断情報である。
必要な応答が要求経路のframeに収まらなければ、設定を変える前にunsupportedで断る（core §4.4）。

| tag | 名前 | 値 | 対象 |
|---|---|---|---|
| 0x50 | actual_rate | num(u32)、den(u32)（実際のレート = num / den Hz。どちらも 1 以上） | 両方 |
| 0x51 | layout | ロジック: w(u8)、C(u8)、pos[C](u8)。アナログ: s(u8)、o(u8)、b(u8)、C(u8)、order[C](u8)（§1） | 両方 |
| 0x52 | actual_samples | u32 | 両方 |
| 0x53 | actual_segments | u32 | 両方 |
| 0x55 | scale | role(u8)、zero(i32、値)、scale_nv(i32、1 値あたりの nV。負は反転する frontend)。チャネルごとに 1 つ。probe の入力ピンの電圧への 1 次式（§1.2） | アナログ |
| 0x57 | skew | role(u8)、skew_ns(u32)。チャネルごとに1つ（遅れが0の役割は省いてよい） | アナログ |
| 0x58 | frontend_used | role(u8)、frontend(u8: describe の frontend の番号)。チャネルごとに 1 つ。値の意味（入力範囲）はそのfrontendの宣言で決まる | アナログ |
| 0x59 | reference | source(u8、enum `reference_source`: 0 電源、1 内部、2 外部)、mv(u32)、how(u8、enum `reference_how`: 0 公称、1 測った)。ADC の基準電圧。電源が基準の ADC では、同じ生の値の意味が電源電圧で変わる。scale の 1 次式はこの電圧を前提にした換算 | アナログ |

### 3.4 通知（core §10）

ロックの持ち主がその fn に subscribe すると、そのインターフェースから次が届く（subscribe と unsubscribe を ops に立てる fn だけ）。
購読しなければ、status と segments のポーリングで同じことが分かる。

| 送るもの | いつ | 中身 |
|---|---|---|
| 出来事 kind 0x01 segment | 区画が終わった（ワンショットの完了も。ストリーミングでは送らない） | 区画の情報（§2）、[TLV] |
| 出来事 kind 0x02 stopped | 取得が止まった | reason(u8: 0 完了、1 stop（host の stop。組（§4）が止めたときも）、3 エラー（state 6 に入るときは必ずこれ、§3.2）)、error(u8: reason 3 の理由、status の error と同じ値)、generation(u32)、[TLV] |
| 出来事 kind 0x03 triggered | トリガが立った | serial(u32)、trigger_index(u32)、trigger_ns(u64: probe の時計でトリガが立った時刻の推定値)、generation(u32)、[TLV] |
| データ（role 0x04） | ストリーミングの間だけ | core §10.2の形。readと同じbyte位置。必須TLV 0x01 generation(u32)と0x02 segment_info（下）を毎frameへ付ける |

**streamingのsegment_info**: `position(u64)、samples(u32)、start_ns(u64)、start_uncertainty_ns(u32)`（24byte）。
positionは区画の先頭、samplesはそのframeを作った時点で取得済みのsample数（1以上）。取得中は後のframeで増え、終了後は最終値。
時刻/不確かさは§2.2の区画と同じ。そのframeのdataはこの1区画の中だけで、区画の境目をまたがない。
未確定の末尾byteを送らない上の規則に従う。終了時のpaddingはsamplesとlayoutから区別する。
Hostはdataの絶対positionと区画の起点から区画内のbit/sampleを求め、失った前frameの断片でsampleを補わない。
毎frameに起点と時刻があるので、最初のframe/区画情報が失われても後のframeを解釈できる。GENが違うframeは別の取得である。
frame64では固定見出し15+GEN TLV7+segment_info TLV27を引き、dataは15byteまで。
Probeはより大きい経路を使え、mode 3を提供しない最小構成にこの情報/取得bufferを要求しない。

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
| 0x44 | channels | max(u8)。チャネル数の上限 |
| 0x45 | trigger | types(u32: type のビット集合)、max_pretrigger(u32) |
| 0x46 | frontend | frontend(u8: 番号)、range_min_mv(i32)、range_max_mv(i32)。入力ピンの範囲の候補ごとに1つ（アナログ）。番号はconfigureのfrontendで選ぶ |

- 必須の宣言はops、1つ以上のmode、rate_range、channels、trigger、およびplanで使うrole_channels/channel_group。
  アナログはfrontendも1つ以上宣言する。featuresは値0なら省略できる。
  triggerの番号はlogic/analog各インターフェースの空間で、両方とも即時（type 0）を含める。
- modeは少なくとも1つ宣言する。1/2/3を全部宣言する必要はなく、対応するmodeだけを載せる。
  max_segmentsはmode 2の置き場の上限。mode 1/3では0を送り、Hostは使わない。
  宣言したmodeでの値の組合せや実現可能量は、下の目安とconfigure/queryの規則に従う。
- **宣言は目安、configure の応答が正。** 宣言に出ていない組み合わせは query で確かめる。

### 3.6 別の定義に残すもの

基本は、どの host も全部実装でき、その中で probe が選んだものに分岐なしでついていける量にする。時間軸やデータの意味を変えるもの、
1 つの実装でしか意味がないものは、別の定義（別の名前のインターフェース、または独立した features のビットと文書）に残す。知らない host は
それを無視でき、基本の動作は変わらない。基本の外: 複数トラックの同時開始（別のインターフェースの capture-group、§4）、外部クロック、
多段トリガの段と条件、トリガ出力、役割の 0xC0〜（外部クロック、修飾、トリガ入出力）。別の定義を書くときに、そちらで番号を振る。

- モードとトリガの type は、それぞれ 0x40 以降を別の定義に残す。
- configure（要求と応答）と describe の TLV は 0x60〜0x7F を別の定義に残す。layout（§1）と違う data の形は、別の定義が自分の応答の TLV で示す
  （layout の値に形式の番号は無い）。
- チャネルごとの縮約は基本に含めない。0x60〜0x7Fは将来の別定義へ残す。
- probe がデコードまでするもの（プロトコルアナライザ）は、このインターフェースを広げず、別のインターフェースにする。

### 3.7 calibration（アナログ）

ADC の値を電圧に換算するための、probe が持っている情報を**生のまま**返す。probe は補正を適用しない（read の値はいつも生の値。
換算は host が選ぶ。曲線の補正は測れる範囲の上下を削ることがあり、保存の段階で強制しない）。持たない情報は返さない。そうした情報を何も持たない probe は、TLV を返さない（空の成功）。

| tag | 名前 | 値 |
|---|---:|---|
| 0x01 | factory | frontend(u8)、scheme_len(u8)、scheme(text)、raw_len(u16)、raw。出荷時にチップに書かれた較正の値を、読んだまま。scheme は形式の名前で、逆 DNS（形式の持ち主の名前空間。`a-z 0-9 - .`、1〜64 byte）。raw の解釈は scheme の定義に従う。frontend ごとに 1 つ（frontend に依らないものは 0xFF） |
| 0x02 | vrefint | raw(u32)、ns(u64)、nominal_mv(u32)。内部の基準電圧（Vrefint など）を、最後の start（capture-group の start を含む）の直後に同じ ADC で測った生の値、その時刻、その基準電圧の公称値（mV。電源電圧の逆算に使う）。基準電圧が電源の ADC で、実際の電源電圧を逆算するのに使う。測れない probe は返さない |

- チップの型番とリビジョンは core の describe の chip（core §7.5）、firmware の版は同じく firmware。
- frontend ごとの減衰と測れる範囲は describe の frontend（§3.5）、チャネルごとに選ばれた frontend は configure の応答の
  frontend_used、基準電圧は reference（§3.3）。

## 4. `oep.fixture.capture-group`（即時の一括開始）

別々のlogic/analogトラックを同じ要求で即時開始する任意のインターフェース。
時間の正確な一致を保証せず、各区画のstart_ns/不確かさでHostが並べる。連動trigger/pretriggerと時刻からのtrigger_index写像は定義しない。

### 4.1 操作

| op | 名前 | 要求 | 応答 | ロック | 要否 |
|---:|---|---|---|---|---|
| 0x10 | bind | n(u8)、n × fn(u16)、[TLV] | — | 必要 | 必須 |
| 0x11 | start | [TLV] | start_ns(u64)、generation(u32)、n(u8)、n × (fn(u16)、generation(u32))、[TLV] | 必要 | 必須 |
| 0x12 | stop | [TLV] | — | 必要 | 必須 |
| 0x14 | status | [TLV] | state(u8)、start_ns(u64)、generation(u32)、[TLV] | 不要 | 必須 |
| 0x01 | subscribe | core §10.3 | — | 必要 | 任意（unsubscribeと組） |
| 0x02 | unsubscribe | core §10.3 | — | 必要 | subscribeと組 |

- bindは設定済みのlogic/analogのfnを束ねる。全trackは同じmodeで、triggerは即時だけ。
  新しい組へ入れるtrackはstate 1/4/6で、単独取得や別の組で使用中ならcause 6/4で断る。
  同じfnリストの再指定は状態を保つno-op。異なるリストへの変更は組がstate 3の間cause 6で断る。
  重複fnはmalformed、tracksに無いfnはunsupported（固定部分の印0）。状態/trigger/modeが合わない場合はunavailable cause 6、
  同時に使う資源が足りない場合はcause 2。fnの診断TLVはcore §4.3。拒否は全検証の後、副作用前に行う。
- n=0は束ねを解く。取得中の組（state 3）ではunavailable cause 6。束ねていなければno-op。
  束ねはsessionの資源（core §9）。束ねたtrackのconfigure/start/stop/forceとplanの変更/解放はcause 4で拒否。
  同じplan集合はno-op、query/read/status/segments/releaseは各trackの通常規則で使える。
- bindは、同じ経路のstart成功応答（18+6×n byte）がframeへ収まることも確かめ、収まらなければunsupported（固定部分の印0）。
- startは組/全trackの世代の空き、mode/資源/購読などをすべて確かめてから、新しい世代を割り当てて全trackを開始する。
  組の世代も冒頭と同じ非再利用の規則。nとfnの順はbindと同じ。start_nsは最初のtrackを開始する時点の推定値。
  start前のstart_nsは全bit1。全処理/受付再開は§3.2のstartと同じ時間規則。
- 初期化/取得の失敗でtrackがstate 6になれば組も6とし、ほかのtrackをstopと同じに止める。
  完了済みのtrackはdata/区画を保持する。start自体が開始に失敗した場合はcompleted failedで同じ固定形を返す。
- stopは全trackへ適用し、短い区画とpadは各trackの規則に従う。束ねなしのstopはno-op。startは束ねなしならcause 6。
- statusのstate: 束ねなし0、どれかが6なら6、開始後に全部4なら4、どれかが3/5なら3、それ以外1。
  groupのgenerationはbind変更では戻さず、次のstartで進める。groupを起動しない段階のtrack世代も変えない。

### 4.2 通知

採用したsubscribeへはstopped（kind 0x02）だけを送る。
`reason(u8: 0 全track完了、1 stop、3 error)、error(u8: reason3のtrack error、ほかは0)、generation(u32)、[TLV]`。
組がerrorならtrackのどれか1つのerrorを返す。過去の通知を区別するため、groupの世代は省略しない。
即時のgroup/trackからtriggeredを送らない。各trackの通知はそのfnの購読へ送り、group購読で代用しない。

### 4.3 describe

必須はopsとtracks（tag 0x40: n(u8)、n × fn(u16)、n≥1）。個々の組合せが実現可能かはbindで確かめる。
featuresのbitはv1で定めない。force、trigger_track、連動pretriggerはv1に含めない。
