# OEP インターフェース: キャプチャ v1

[English](oep-if-capture.md)

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](../docs/versioning.ja.md) §6）。本体は [OEP core](../docs/oep-core.ja.md)。
番号の唯一の定義は `registry/oep-v1.toml`。基本と別の定義の線引きは §3.6。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.fixture.logic` | 1 | ロジック（1 トラック） | どの系統にも使う |
| `oep.fixture.analog` | 1 | アナログ（1 トラック） | どの系統にも使う |
| `oep.fixture.capture-group` | 1 | 複数のトラックを一緒に始める（ミックスドシグナル、§4） | どの系統にも使う |

logic と analog は**操作の番号と形が同じ**で、違うのは configure の中身（§3.3）、データの layout（§1）、アナログだけの
calibration（§3.8）だけ。複数トラックの同時開始と時刻合わせは、この 2 つを広げず、トラックを束ねる別のインターフェース
（capture-group、§4）にする。外部クロック、多段トリガなどは別の定義（§3.6）。

**時刻**: どのトラックの時刻も、probe の 1 本の時計（起動からの ns、u64 で一周しない）で表す。インターフェースが違っても同じ
時計なので、host は時刻の引き算でトラックを並べられる。時刻は**推定値と不確かさ**で返す。probe は知っている補正（ドライバが最初の
変換フレームを捨てる、など）を済ませた値を返し、それ以上の精度は約束しない。最後の合わせ込み（トラック間のオフセットと時間の
倍率）は host の分析の仕事。
時計は起動から数えるので、比べられるのは同じ起動の中だけ。host は confirm、clock、open の応答の boot_id（core §6.5）が同じかで、同じ
時計かを判断する。probe の時計と host の時計の対応は clock（core §7.7）で取る。

**世代（generation）**: トラックは start ごとに世代（u32）を 1 進める。起動後の最初の start で 1、0xFFFFFFFF の次は 1 で、0 は最初の start の
前だけを表す。世代は等しいかどうかだけを比べる。区画の serial と位置（position）は世代の中で 0 から数える
ので、host は read と release に世代を付け、probe は違えば断る（古い read が新しいデータを黙って返さない）。世代は start の応答、
status、区画の情報、出来事、ストリーミングのデータの TLV で分かる。

キャプチャは位置つきのストリームの形（[共通部品](oep-if-common.ja.md) §1）を使わない（from とマークが無く、区画と世代を持つ）。
モード（ワンショット、リピート、ストリーミング）は §2.1。レートは probe が刻む。宣言は目安で、configure の応答が正（§3.5）。

## 1. データの形

用語: **ストリーム**は、1 回のキャプチャ（1 区画）で probe が返すバイトの並び。バイト位置 0 から始まる。
**ストリームのビット j** は、バイト `floor(j / 8)` のビット `j mod 8`（ビット 0 = LSB）と定める。

### 1.1 ロジック

configure の応答で probe が返す値:

| 値 | 範囲 | 意味 |
|---|---|---|
| `w` | 1, 2, 4, 8, 16, 32, 64, 128 のどれか | 1 サンプルのビット数。probe が選ぶ（チャネル数より大きくてよい） |
| `C` | 1 以上 | チャネル数（plan で割り当てたロジックの役割の数） |
| `pos[k]`（k = 0 … C−1） | 0 ≤ pos[k] < w、互いに異なる | チャネル k（役割の番号の小さい順）の、サンプルの中のビット位置 |
| `N` | 1 以上 | 区画のサンプル数 |

規則:

1. サンプル i（i = 0 … N−1）は、ストリームのビット `i·w` から `i·w + w − 1` まで。
2. サンプル i のチャネル k の値は、ストリームのビット `i·w + pos[k]`。
3. どの `pos[k]` にも当たらないビットの値は**未定義**。host は読まずに無視する（probe は 0 にしなくてよい）。
4. 区画の長さは `ceil(N·w / 8)` バイト。最後のバイトの、`N·w` を超えるビットは未定義。
5. w ≥ 8 のとき、サンプルは `w/8` バイトの little endian の整数と同じになる（w = 64 / 128 も同じ: バイト k のビット b がビット
   `8k + b`）。w < 8 のとき、1 バイトに `8/w` サンプルが入り、若い番号のサンプルが下位ビットに来る。

例:

| 構成 | w | pos | 1 バイトの中身 |
|---|---|---|---|
| 1 ビットずつ詰める probe、1 本 | 1 | [0] | サンプル 0〜7 がビット 0〜7 |
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
| `C` | 1 以上 | チャネル数 |
| `order[m]`（m = 0 … C−1） | チャネルの番号の並べ替え | サンプルの中の m 番目の枠が、どのチャネルか |
| `N` | 1 以上 | 区画のサンプル数 |

規則:

1. 枠は `s/8` バイトの little endian の整数。枠の値の `o` から `o+b−1` ビットが変換の結果（符号なし）。それ以外の
   ビットは未定義（host は無視する）。結果が符号付き（b bit の 2 の補数）の変換器は offset binary で送る: probe は各値の bit b−1 を反転し（2^(b−1) を足して 2^b で割った余り）、返す zero はその分を含む（0 V の値）。
2. サンプル i は、枠 `i·C` から `i·C + C − 1` まで。m 番目の枠がチャネル `order[m]`。
3. 区画の長さは `N·C·s/8` バイト。
4. チャネル k の電圧 = （値 − `zero[k]`）× `scale_nv[k]`。`zero` と `scale_nv`（nV / 1 値）は configure の応答でチャネルごとに返す（1 次式。曲線の較正は
   別の定義）。**この電圧は probe の入力ピンの電圧**（前段の減衰を含めて換算した値。describe の frontend の attenuation_mdb は表示の
   ためで、host が重ねて掛けない）。
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
- idle が出力（mode 3 / 4）の channel へのアナログの plan は rejected unavailable（cause 5）。

## 2. モードと区画

### 2.1 モード

| モード | ふるまい |
|---|---|
| 1 ワンショット | start（とトリガ）の後、samples 個のサンプルを取って止まる（state 4）。host は自分の速さで読む。次の start でデータは消える |
| 2 リピート | ワンショットを次々に、区画の境目に隙間なく、空いている区画にだけ取る。空きが無くなれば止まり（state 5）、release で再開する |
| 3 ストリーミング | リピートと同じく隙間なく取り、ロックを持つ者が購読している間、データを通知で送る |

- トリガは開始の条件だけである: どのモードでも、最初の区画の始まりにだけ効く。
- probe は start の後にだけ取る。先回りして取らない。

**ストリーミングの規則**:

1. 送る余地が無いとき、probe は**新しい**データを捨てる（すでに積んだデータは送る）。捨てた量は、次のデータのフレームの position の飛びと、
   status の flags bit0 に現れる。
2. stop の後も、probe は stop の前に取った分を送る。受け取った position の末尾が、stop の後の status の write_pos に等しくなれば、host はすべて受け取っている。
3. ストリーミングでは区画の出来事を送らない（stopped は送る）。
4. 通知で送ったデータは read で読めないことがある（読めない位置は gap 付きの空の応答を返す）。

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
| generation | この区画の世代（start ごとに 1 ずつ増える） |
| samples | 区画のサンプル数（stop で途中で終わった区画は短い） |
| start_ns | 区画の最初のサンプルの時刻の推定値（probe の時計: 起動からの ns、u64 で一周しない）。probe が知っている補正を済ませた値 |
| start_uncertainty_ns | start_ns の不確かさ（±ns）。probe が見積もれる範囲の目安で、保証ではない |
| trigger_index | 区画の中でトリガが立ったサンプルの番号。トリガを含まない区画は 0xFFFFFFFF |
| flags | bit0 前の区画との間が空いた（リピートで空き区画がなかった、ストリーミングで押し出された）、bit1 短い（stop で終わった）、bit2 時間の基準が曲がった（予定の時刻を 1 サンプル周期以上過ぎて取ったサンプルがある） |

- 区画の中は連続を約束する。リピートとストリーミングでは、flags bit0 が立っていない限り、区画は前の区画の直後から続く。
- flags bit2 は、probe が自分で遅れを見つけられるときに立てる。
- 区画の情報は本文とは別の小さなリングにためる（いくつ覚えるかは probe が決める）。

## 3. 操作

### 3.1 役割（plan）

- 役割 k = チャネル k（ロジックは 0〜127、アナログは 0〜63）。チャネルの順は役割の番号の小さい順。
- ADC のチャネルを持たないピンは、アナログの plan で拒否する。

### 3.2 操作

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | configure | 設定の TLV（§3.3） | 実際の値の TLV（§3.3） | 必要 |
| 0x02 | start | — | blocking_ms(u32)（0 = 取っている間も答える）、generation(u32)、[TLV] | 必要 |
| 0x03 | stop | — | — | 必要 |
| 0x04 | force | — | —（トリガを待っていれば、今すぐ始める） | 必要 |
| 0x05 | status | — | state(u8)、serial_done(u32)、write_pos(u64)、flags(u8)、generation(u32)、[TLV error] | 不要 |
| 0x06 | read | generation(u32)、position(u64)、max(u32) | position(u64)、flags(u8: bit0 more、bit1 gap)、len(u32)、data、[TLV] | 不要 |
| 0x07 | segments | from_serial(u32) | more(u8)、count(u8)、count × 区画の情報（§2）、[TLV] | 不要 |
| 0x08 | release | generation(u32)、serial(u32) | —（serial 以下の区画を使い回してよい） | 必要 |
| 0x09 | query | 設定の TLV（configure と同じ） | 実際の値の TLV（設定はしない） | 不要 |
| 0x0A | calibration | — | 較正の情報の TLV（§3.8）。アナログだけ（ロジックは unknown_operation） | 不要 |
| 0x30 | subscribe | core §11.3 | — | 必要 |
| 0x32 | unsubscribe | core §11.3 | — | 必要 |

- query（0x09）、force（0x04）、subscribe（0x30）と unsubscribe（0x32）は任意で、describe の ops で宣言する（core §1.2、§7.4）。subscribe と unsubscribe は両方とも持つか、両方とも持たない（core §11.3）。それを持たない probe は、その op に unknown_operation で答える（core §1.2）。この表のほかの op は必ず持つ。calibration はアナログでは必ず持ち、ロジックの op ではない。
- state: 0 未設定、1 設定済み、2 トリガ待ち、3 取得中、4 完了（ワンショット）、5 止まっている（リピートで空き区画なし）、
  6 エラー。
- `serial_done` は次に終わる区画の serial（start から終わった区画の数を 2^32 で割った余り）、`write_pos` は取り終えたバイト位置（position の空間。**捨てた分を含む**: 次に書くバイトの位置）。
- status の `flags`: bit0 probe の中でデータを落とした（取り込みのキューやリングがあふれた）、bit1 時間の基準が曲がった
  （区画の flags の bit2 と同じ）。ほかのビットは予約（0）。**start で 0 に戻し、その回の累積**。state 6 のときは応答の TLV 0x01 error（u8:
  1 DMA / ペリフェラル、2 置き場、3 時計、0x40〜 probe 固有。registry の enum `error`）で理由を返す。
- **generation**: read と release は今の世代を要求に置く。違えば rejected unavailable（cause 6）。start 前は 0。
- read で要求した位置がもう使い回されていれば（または押し出されていれば）、応答の position が先に進み、gap が立つ。
  まだ取れていない位置なら、あるところまで返す（何もなければ空。max = 0 も空の成功）。
- release はリピートだけ（ワンショットとストリーミングでは何もせず成功）。終わった区画のうち、serial かそれより前（inclusive、core §2.6 で
  比べる）のものを解放する。まだ終わっていない区画は解放しない（serial がそれより先でも、解放するのは終わった区画だけ）。state 5 で空きが
  できれば probe は自動で取得を再開し（state 3）、再開した最初の区画に flags bit0 を立てる。stopped reason 2 は送らない（予約）。
- read が実際に返す量は probe が決める（max 以下で、応答が max_frame に収まる量）。
- segments は [共通部品](oep-if-common.ja.md) §1.3 の通し番号のページングで答える（next は serial_done、残っているのは probe が情報を
  覚えている区画）。

**状態の遷移**（行 = 今の state、列 = 契機。「—」は何もせず成功。force の列は force を持つ probe に当てはまる）:

| state | configure | start | stop | force | release | 自動 |
|---:|---|---|---|---|---|---|
| 0 未設定 | → 1 | unavailable 6 | — | — | — | plan 無しの configure / query も unavailable 6 |
| 1 設定済み | → 1 | → 2（トリガあり）/ 3。世代 +1、区画は消える | — | — | — | |
| 2 トリガ待ち | unavailable 6 | unavailable 6 | → 1（stopped 1） | → 3 | — | トリガ → 3（triggered） |
| 3 取得中 | unavailable 6 | unavailable 6 | → 1（stopped 1、短い区画 bit1） | — | 空きを返す | 完了 → 4（stopped 0）、空き無し → 5、エラー → 6（stopped 3） |
| 4 完了 | → 1 | → 2 / 3（世代 +1） | — | — | — | |
| 5 止まっている | unavailable 6 | unavailable 6 | → 1 | — | 空きができれば → 3（flags bit0） | |
| 6 エラー | → 1 | → 2 / 3（世代 +1） | → 1 | — | — | |

plan_release（[plan](oep-if-plan.ja.md)）か、セッションの終わり（end、lease の期限切れ、force、core §9）で plan が解けたら state 0 に戻り、データも区画も消える（read は空）。mode 3（ストリーミング）の
start は、その fn の購読が無ければ rejected unavailable（cause 6）。取得中に購読が消えたら取り続け、送れない分は捨てる（position が飛ぶ）。
configure の応答の blocking_ms が core の max_op_ms を超える構成は、configure で rejected unsupported。

- start の応答から blocking_ms の間、probe はどの transport のフレームも処理しないことがあり、失うことがある。host はその間、その probe に
  どの transport でも何も送らない。その後、長さ前置きの transport では transports §5 の resync から始める。シリアルポートではそのまま続ける。
  lease も host の待ち（core §4.4）も blocking_ms を数えない。

### 3.3 configure

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
  trigger の role がその fn の plan に無ければ rejected unavailable（cause 6）。pretrigger が max_pretrigger を超えるか、samples（切り下げた
  後）以上なら rejected unsupported（pretrigger の tag）。断るときは何も変えない。
- **問い合わせは別の操作（0x09）**。configure の TLV のフラグにすると、probe はロックの要否を操作の番号で決めるので、
  ロックなしの問い合わせができない。問い合わせは今の設定と取ったデータを壊さない。
- trigger の type: 0 即時（省略時）、1 レベル（value 0 / 1）、2 エッジ（value 0 立ち上がり / 1 立ち下がり / 2 両方）、
  3 しきい値を上向きに横切る、4 下向きに横切る（value は o / b で切り出した後の ADC の値）。1〜2 はロジック、3〜4 はアナログ。
  宣言に無い type は rejected unsupported。
- **samples は区画の総数**（pretrigger を含む）。トリガが早く立ってプリトリガの分が足りなければ、区画は短く、trigger_index はそのまま
  小さい。force で始めたときは trigger_index = その瞬間のサンプルで triggered を送る。type 0（即時）では triggered を送らない。
- **rate**: probe は宣言した rate_range の中で実現できる最も近い値を使う（向きは問わない。どれかは actual_rate
  で分かる）。範囲の外の rate は rejected unsupported（受け取ったままの tag、core §2.3）。
- probe が持てる量を超える samples は、その上限に切り下げ、応答の actual_samples（0x52）
  が正である。host は送った値を仮定せず、actual_samples と actual_segments を読む。

**応答の TLV**（configure と query の success は、その対象の行をすべて返す。例外: actual_samples は mode 1 / 2 だけ、actual_segments は
mode 2 だけ、skew は遅れが 0 のチャネルを省いてよい。チャネルごとの行は plan のチャネルごとに 1 つ）:

| tag | 名前 | 値 | 対象 |
|---|---|---|---|
| 0x50 | actual_rate | num(u32)、den(u32)（実際のレート = num / den Hz。どちらも 1 以上） | 両方 |
| 0x51 | layout | ロジック: w(u8)、C(u8)、pos[C](u8)。アナログ: s(u8)、o(u8)、b(u8)、C(u8)、order[C](u8)（§1） | 両方 |
| 0x52 | actual_samples | u32 | 両方 |
| 0x53 | actual_segments | u32 | 両方 |
| 0x57 | skew | role(u8)、skew_ns(u32)。チャネルごとに 1 つ（遅れが 0 のチャネルは省いてよい） | アナログ |
| 0x55 | scale | role(u8)、zero(i32、値)、scale_nv(i32、1 値あたりの nV。負は反転する frontend)。チャネルごとに 1 つ。probe の入力ピンの電圧への 1 次式（§1.2） | アナログ |
| 0x56 | blocking_ms | u32（取っている間 probe が答えない時間の見込み。0 なら答える） | 両方 |
| 0x58 | frontend_used | role(u8)、frontend(u8: describe の frontend の番号)。チャネルごとに 1 つ。値の意味（測れる範囲、減衰）はその frontend の宣言で決まる | アナログ |
| 0x59 | reference | source(u8、enum `reference_source`: 0 電源、1 内部、2 外部)、mv(u32)、how(u8、enum `reference_how`: 0 公称、1 測った)。ADC の基準電圧。電源が基準の ADC では、同じ生の値の意味が電源電圧で変わる。scale の 1 次式はこの電圧を前提にした換算 | アナログ |

### 3.4 通知（core §11）

ロックの持ち主がその fn に subscribe すると、そのインターフェースから次が届く（subscribe と unsubscribe を ops に立てる fn だけ）。
購読しなければ、status と segments のポーリングで同じことが分かる。

| 送るもの | いつ | 中身 |
|---|---|---|
| 出来事 kind 0x01 segment | 区画が終わった（ワンショットの完了も。ストリーミングでは送らない） | 区画の情報（§2）、[TLV] |
| 出来事 kind 0x02 stopped | 取得が止まった | reason(u8: 0 完了、1 host の stop、2 予約（空き区画なしは送らない）、3 エラー)、error(u8: reason 3 の理由、status の error と同じ値)、generation(u32)、[TLV] |
| 出来事 kind 0x03 triggered | トリガが立った | serial(u32)、trigger_index(u32)、trigger_ns(u64: probe の時計でトリガが立った時刻の推定値)、generation(u32)、[TLV] |
| データ（role 0x06） | ストリーミングの間だけ | core §11.2 の形（position、len、data、TLV）。read と同じ位置の空間。**TLV 0x01 generation(u32) を必ず付ける**（start の応答の後に前の世代の送り残しが届きうるため） |

- **出来事はどれも、それが生まれた世代を持つ**（segment は区画の情報の generation）。start の応答の後に前の世代の出来事が届きうる
  （core §11.4）。host は今の世代と違う出来事を前の世代のものとして扱う。
- ストリーミングは subscribe が前提（データは probe が送る。ストリーミングの mode を宣言する fn は subscribe と unsubscribe を ops に立てる）。

### 3.5 describe で宣言するもの

| tag | 名前 | 値 |
|---|---|---|
| 0x09 | ops | 持つ op（core §7.4）: query、force、subscribe と unsubscribe は持つときだけ立てる |
| 0x06 | features | 共通のビット。revision 1 はビットを定めない（bit0〜bit2 は予約、0） |
| 0x40 | mode | mode(u8)、max_samples(u32、1 区画)、max_segments(u32)（モードごとに 1 つ。**最大**の置き場で答える。describe は宣言だけなので、その時点の空きでは答えない） |
| 0x41 | rate_range | min_hz(u32)、max_hz(u32)、exact(u8: 1 = 範囲内の任意の値を指定できる) |
| 0x44 | channels | max(u8)。チャネル数の上限 |
| 0x45 | trigger | types(u32: type のビット集合)、max_pretrigger(u32) |
| 0x46 | frontend | frontend(u8: 番号)、range_min_mv(i32)、range_max_mv(i32)、attenuation_mdb(u32: 前段の減衰、ミリ dB。0 は減衰なし、0xFFFFFFFF は減衰で表せない前段)。入力範囲の候補ごとに 1 つ（アナログ）。番号は configure の frontend で選ぶ。候補が 1 つだけの probe はそれだけ書く |

- **宣言は目安、configure の応答が正。** 宣言に出ていない組み合わせは query で確かめる。

### 3.6 別の定義に残すもの

基本は、どの host も全部実装でき、その中で probe が選んだものに分岐なしでついていける量にする。時間軸やデータの意味を変えるもの、
1 つの実装でしか意味がないものは、別の定義（別の名前のインターフェース、または独立した features のビットと文書）に残す。知らない host は
それを無視でき、基本の動作は変わらない。基本の外: 複数トラックの同時開始（別のインターフェースの capture-group、§4）、外部クロック、
多段トリガの段と条件、トリガ出力、役割の 0xC0〜（外部クロック、修飾、トリガ入出力）。別の定義を書くときに、そちらで番号を振る。

- モード、トリガの type、layout の形式は、それぞれ 0x40 以降を別の定義に残す。
- configure と describe の TLV は 0x60〜0x7F を別の定義に残す。
- probe がデコードまでするもの（プロトコルアナライザ）は、このインターフェースを広げず、別のインターフェースにする。

### 3.7 使い方の例

使い方の例は [host 開発ガイド](../docs/host-development-guide.ja.md) §22。

### 3.8 calibration（アナログ）

ADC の値を電圧に換算するための、probe が持っている情報を**生のまま**返す。probe は補正を適用しない（read の値はいつも生の値。
換算は host が選ぶ。曲線の補正は測れる範囲の上下を削ることがあり、保存の段階で強制しない）。持たない情報は返さない。そうした情報を何も持たない probe は、TLV を返さない（空の成功）。

| tag | 名前 | 値 |
|---|---:|---|
| 0x01 | factory | frontend(u8)、scheme_len(u8)、scheme(text)、raw_len(u16)、raw。出荷時にチップに書かれた較正の値を、読んだまま。scheme は形式の名前で、逆 DNS（形式の持ち主の名前空間。`a-z 0-9 - .`、1〜64 byte）。raw の解釈は scheme の定義に従う。frontend ごとに 1 つ（frontend に依らないものは 0xFF） |
| 0x02 | vrefint | raw(u32)、ns(u64)、nominal_mv(u32)。内部の基準電圧（Vrefint など）を、最後の start（capture-group の start を含む）の直後に同じ ADC で測った生の値、その時刻、その基準電圧の公称値（mV。電源電圧の逆算に使う）。基準電圧が電源の ADC で、実際の電源電圧を逆算するのに使う。測れない probe は返さない |

- チップの型番とリビジョンは core の describe の chip（core §7.5）、firmware の版は同じく firmware。
- frontend ごとの減衰と測れる範囲は describe の frontend（§3.5）、チャネルごとに選ばれた frontend は configure の応答の
  frontend_used、基準電圧は reference（§3.3）。

## 4. `oep.fixture.capture-group`（複数のトラックを一緒に始める）

**別々のインターフェースのトラック（ロジックとアナログ、2 つの ADC など）を束ね、1 回のキャプチャとして一緒に始める**（各トラックは自分の configure を持ち、データも自分で読む）。

### 4.1 操作

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | bind | n(u8)、n × fn(u16)、[TLV] | — | 必要 |
| 0x02 | start | — | blocking_ms(u32)、start_ns(u64)、generation(u32)、n(u8)、n × (fn(u16)、generation(u32))、[TLV] | 必要 |
| 0x03 | stop | — | — | 必要 |
| 0x04 | force | — | —（トリガを待っていれば、今すぐ始める） | 必要 |
| 0x05 | status | — | state(u8)、start_ns(u64)、trigger_ns(u64)、trigger_fn(u16)、generation(u32)、[TLV] | 不要 |
| 0x30 | subscribe | core §11.3 | — | 必要 |
| 0x32 | unsubscribe | core §11.3 | — | 必要 |

- force、subscribe と unsubscribe は任意で、describe の ops で宣言する（§4.3、core §1.2）。それを持たない probe は、その op に unknown_operation で答える。subscribe と unsubscribe は両方とも持つか、両方とも持たない（core §11.3）。ほかの op は必ず持つ。

bind の TLV:

| tag | 名前 | 値 |
|---:|---|---|
| 0x01 | trigger_track | fn(u16)。組の開始の条件を持つトラック（そのトラックの configure の trigger と pretrigger）。無ければ即時 |

- **bind** は、configure 済みのトラック（`oep.fixture.logic` / `oep.fixture.analog` の fn）を束ねる。n = 0 で解く（state 3 のときは
  rejected unavailable cause 6。束ねていないときの n = 0 は何もせず成功）。断り方: 同じ fn の重複は malformed、宣言（tracks）に無い fn
  は unsupported、configure していない・モードが揃っていない・trigger_track 以外が即時でないトリガを持つ・一緒に取る資源が足りない は
  unavailable（cause 6 / 2）。どのトラックについての断りかは payload の TLV fn（0x05、core §4.3。unsupported の payload も同じ）で返す。
  何も変えずに断る。束ねている間、各トラックの configure、start、stop、force は rejected unavailable
  （cause 4。組の op を使う。configure し直すときは、いったん n = 0 で解く）。束ねたトラックの plan の
  plan_release / plan_apply も rejected unavailable（cause 4）。**bind はセッションの資源**（core §9: セッションのロックが終わるとき（end、lease の
  期限切れ、force）に解ける）。
- トラックを束ねていないとき: start は rejected unavailable cause 6。stop と、持っていれば force は、何もせず成功。state は 0。
- **start** は、どのトラックを始めるよりも前に全トラックの前提を確かめ（ストリーミングで購読の無いトラックがあれば、start は TLV fn（0x05）=
  そのトラックを付けて rejected unavailable cause 6）、それから束ねたトラックをできるだけ同時に始め、組の開始の時刻 start_ns（probe の時計）、
  組の新しい世代、各トラックの新しい世代を返す（各トラックの start と同じく generation を +1）。n は束ねたトラックの数で、各 fn を bind の
  順に 1 回ずつ置く。**組の世代**は組の start ごとに 1 進め、規則はトラックの世代と同じ（起動後の最初の start で 1、0xFFFFFFFF の次は 1、
  0 は最初の start の前。bind し直しても続きから）。始めた後にトラックが失敗したら、組は state 6、
  stopped reason 3 で、ほかのトラックも止める。**start_ns は取得（pretrigger のリングを含む）を始めた時刻**。即時トリガのとき、トラックの
  ずれは、その最初の区画の start_ns − 組の start_ns（推定値）。start 前の status の start_ns と trigger_ns は全ビット 1。
- **トリガ**: trigger_track の条件が立つと、組の全トラックが取得を始める（各トラックの pretrigger は、そのトラック自身の
  サンプル数で残す）。立った時刻 trigger_ns は status と出来事 triggered で返し、**全トラックの、その時刻を含む区画の
  trigger_index を、そのトラックでその時刻に最も近いサンプルにする**（probe が各トラックの時間軸に写す）。host はどのトラックでも
  同じ瞬間の位置を知る。
- **stop** は全トラックを止める。区画はトラックごとに（短い区画は flags bit1）。
- status の state はトラックと同じ値（§3.2）で、組全体の状態: どれかのトラックが 6 なら 6。そうでなく、始めていて全トラックが 4 なら 4。
  そうでなく、trigger_track があってまだ立っておらず、どれかのトラックが 2 か 3 なら 2。そうでなく、どれかのトラックが 2、3、5 なら 3。そうでなければ 1。trigger_ns は立っていなければ
  0xFFFFFFFFFFFFFFFF、trigger_fn は 0。force で始めたときは triggered を送り、trigger_fn は 0。
- モードは全トラックで同じ（ワンショット、リピート、ストリーミング）。リピートの release とストリーミングの push は、トラック
  ごとに今までどおり。

### 4.2 通知

組の fn に subscribe すると、組の出来事が届く（各トラックの出来事は、そのトラックの fn に subscribe したときに届く）。

| 送るもの | いつ | 中身 |
|---|---|---|
| 出来事 kind 0x03 triggered | trigger_track の条件が立った（force で始めたときも） | trigger_fn(u16: force では 0)、trigger_ns(u64)、generation(u32: 組の世代)、[TLV] |
| 出来事 kind 0x02 stopped | 全トラックが止まった | reason(u8: トラックの stopped と同じ)、error(u8)、generation(u32: 組の世代)、[TLV] |

kind の番号はトラック（§3.4）と揃える（triggered 3、stopped 2）。triggered はトラックの出来事としても出る（両方に出る）。組の出来事も
トラックと同じく世代を持ち、host は今の組の世代と違うものを前の世代のものとして扱う。

### 4.3 describe で宣言するもの

| tag | 名前 | 値 |
|---|---|---|
| 0x09 | ops | 持つ op（core §7.4）: force、subscribe と unsubscribe は持つときだけ立てる |
| 0x06 | features | revision 1 はビットを定めない（bit0〜bit2 は予約、0） |
| 0x40 | tracks | n(u8)、n × fn(u16)。束ねられるトラック |

- 束ねられるトラックは tracks で宣言する。ある組を束ねられるかは bind を試して確かめる（断られても何も変わらない）。
- 1 つのトラックの中の複数チャネル（1 つの ADC を順番に切り替える）は今までどおり、そのトラックの order と skew（§1.2、§3.3）。

### 4.4 使い方の例

使い方の例は [host 開発ガイド](../docs/host-development-guide.ja.md) §22。
