# OEP 標準インターフェース: キャプチャ v1

[English](oep-if-capture.md)

状態: **規範**（2026-09-26。2026-09-30 に凍結前の決定を入れた: 名前 `oep.fixture.logic`、アナログの番号を確定。2026-10-01 に[ゼロベースの再検討](v1-zero-base-proposal.ja.md)を反映）。本体は [OEP core](oep-core.ja.md)。
番号の唯一の定義は `registry/oep-v1.toml`。ロジアナとしての設計、基本と拡張の線引き、根拠の実測は
[キャプチャ（設計と実測）](logic-capture.ja.md)。

| 名前 | revision | 役割 |
|---|---:|---|
| `oep.fixture.logic` | 1 | ロジック（1 トラック） |
| `oep.fixture.analog` | 1 | アナログ（1 トラック） |
| `oep.fixture.capture-group` | 1 | 複数のトラックを一緒に始める（ミックスドシグナル、§4） |

logic と analog は**操作の番号と形が同じ**で、違うのは configure の中身（§3.3）、データの layout（§1）、アナログだけの
calibration（§3.8）だけ。複数トラックの同時開始と時刻合わせは、この 2 つを広げず、トラックを束ねる別のインターフェース
（capture-group、§4）にする。外部クロック、多段トリガなどは別の定義（[設計](logic-capture.ja.md) §0.1）。

**時刻**: どのトラックの時刻も、probe の 1 本の時計（起動からの ns、u64 で一周しない）で表す。インターフェースが違っても同じ
時計なので、host は時刻の引き算でトラックを並べられる。時刻は**推定値と不確かさ**で返す。probe は知っている補正（ドライバが最初の
変換フレームを捨てる、など）を済ませた値を返し、それ以上の精度は約束しない。最後の合わせ込み（トラック間のオフセットと時間の
倍率）は host の分析の仕事（同じ信号を 2 つのトラックで取る、目印のパルスを全部のトラックで取る、など）。
時計は起動から数えるので、比べられるのは同じ起動の中だけ。host は confirm / open の応答の boot_id（core §6.5）が同じかで、同じ
時計かを判断する。

**世代（generation）**: トラックは start ごとに世代（u32、1 から）を進める。区画の serial と位置（position）は世代の中で 0 から数える
ので、host は read と release に世代を付け、probe は違えば断る（古い read が新しいデータを黙って返さない）。世代は start の応答、
status、区画の情報、ストリーミングのデータの TLV で分かる。

キャプチャは位置つきのストリームの形（[共通部品](oep-if-common.ja.md) §1）を使わない（from とマークが無く、区画と世代を持つ）。
モード（ワンショット、リピート、ストリーミング）は §2.1（理由: [設計](logic-capture.ja.md) §2.4。レートの決め方: 同 §2.10）。

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

この規則に入らない取り方（32 ビットの語にサンプルを左詰めするペリフェラル）は、probe が詰め直すか、別の定義の形式を使う
（どのチップがどれに当たるかは [設計](logic-capture.ja.md) §3.0）。

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
   ビットは未定義（host は無視する）。
2. サンプル i は、枠 `i·C` から `i·C + C − 1` まで。m 番目の枠がチャネル `order[m]`。
3. 区画の長さは `N·C·s/8` バイト。
4. チャネル k の電圧 = （値 − `zero[k]`）× `scale_nv[k]`。`zero` と `scale_nv`（nV / 1 値）は configure の応答でチャネルごとに返す（1 次式。曲線の較正は
   別の定義）。**この電圧は probe の入力ピンの電圧**（前段の減衰を含めて換算した値。describe の frontend の attenuation_mdb は表示の
   ためで、host が重ねて掛けない）。
5. チャネル k の時刻は、サンプルの時刻から `skew_ns[k]` 遅れる（順番に切り替える ADC の場合）。

例:

| 構成 | s | o | b | 備考 |
|---|---|---|---|---|
| DMA の 4 バイトのレコードをそのまま送る 12 ビット ADC | 32 | 0 | 12 | ビット 13〜16 のチャネル番号などは未定義として無視される。チャネルの順番がパターンどおりであることが条件（崩れる場合は probe が並べ直すか、そのレートを宣言から外す） |
| 2 バイトのレコードをそのまま送る 12 ビット ADC | 16 | 0 | 12 | 上位 4 ビット（チャネル番号）は未定義 |
| FIFO の 16 ビットをそのまま送る 12 ビット ADC | 16 | 0 | 12 | |
| 8 ビットに縮めた ADC | 8 | 0 | 8 | |

どのチップがどれに当たるかは [設計](logic-capture.ja.md) §3.0。

**ピンの共有**（core §8.1）: ロジックのキャプチャは聞くだけなので、ほかの機能のピンと共有してよい。アナログの入力は
チップによっては pad をアナログの機能に切り替え、そのピンのデジタルの入出力を切る。
- アナログのチャネルを、ほかの fn の plan（ロジックのキャプチャを含む）、線の接続、設定が使うピンと共有できるかは probe が
  決める。**共有できない組み合わせは、plan_apply（と線の attach、設定の set）を rejected unavailable で断る**。どちらが後から
  来ても断る。黙ってほかの機能の読み書きを壊してはならない。
- 共有を許す probe は、アナログが動いている間もそのピンのデジタルの入力（と、ほかの機能の出力）が変わらないときだけ許す。
- **plan を取ってもピンの電気的な状態は変わらない**（core §8）。ロジックのキャプチャは決してそれを変えない: 聞くだけである。出力を止めず、
  ほかの機能や idle の出力が駆動しているピンのプルや向きも変えない。アナログのチャネルは start で空きの状態を離れる（pad がデジタルの機能を離れる）。
- idle が出力（mode 3 / 4）の channel へのアナログの plan は rejected unavailable（cause 5、holder_kind 7）。

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
5. 購読はロックとともに終わる（core §11.3）。受けている host はロックを保つ。

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
| serial | start からの区画の通し番号（0 から） |
| position | 区画の先頭のバイト位置（start から通し、u64 で一周しない。read と通知の position と同じ空間） |
| generation | この区画の世代（start ごとに 1 ずつ増える） |
| samples | 区画のサンプル数（stop で途中で終わった区画は短い） |
| start_ns | 区画の最初のサンプルの時刻の推定値（probe の時計: 起動からの ns、u64 で一周しない）。probe が知っている補正を済ませた値 |
| start_uncertainty_ns | start_ns の不確かさ（±ns）。probe が見積もれる範囲の目安で、保証ではない |
| trigger_index | 区画の中でトリガが立ったサンプルの番号。トリガを含まない区画は 0xFFFFFFFF |
| flags | bit0 前の区画との間が空いた（リピートで空き区画がなかった、ストリーミングで押し出された）、bit1 短い（stop で終わった）、bit2 区画の中でサンプルの時刻が configure の timing（jitter_ns）を超えてずれた（ソフトウェアの歩調で遅れたサンプルがある） |

- 区画の中は連続を約束する。リピートとストリーミングでは、flags bit0 が立っていない限り、区画は前の区画の直後から続く。
- flags bit2 は、probe が自分で遅れを見つけられるときに立てる（ソフトウェアの歩調なら、予定の時刻を 1 サンプル周期以上過ぎて取った
  サンプルがあったとき）。立った区画の時間軸は一様でない。host はその区画で時間を測らないか、測った値を疑う。
- 区画の情報は本文とは別の小さなリングにためる（上限は宣言する）。

## 3. 操作

### 3.1 役割（plan）

- 役割 k = チャネル k（ロジックは 0〜127、アナログは 0〜63）。チャネルの順は役割の番号の小さい順。チャネル数の値（C、channels の
  max など）が u8 なのは、役割が u8 だから（意図的）。
- ADC のチャネルを持たないピンは、アナログの plan で拒否する。
- 外部クロック、トリガの入力と出力のピンは基本に入れない（別の定義）。

### 3.2 操作

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | configure | 設定の TLV（§3.3） | 実際の値の TLV（§3.3） | 必要 |
| 0x02 | start | — | blocking_ms(u32)（0 = 取っている間も答える）、generation(u32)、[TLV] | 必要 |
| 0x03 | stop | — | — | 必要 |
| 0x04 | force | — | —（トリガを待っていれば、今すぐ始める） | 必要 |
| 0x05 | status | — | state(u8)、serial_done(u32)、write_pos(u64)、flags(u8)、generation(u32)、[TLV error] | 不要 |
| 0x06 | read | generation(u32)、position(u64)、max(u32) | position(u64)、flags(u8: bit0 more、bit1 gap)、len(u32)、data、[TLV] | 不要 |
| 0x07 | segments | from_serial(u32) | more(u8)、count(u8)、count × (len(u8)、区画の情報（§2）)、[TLV] | 不要 |
| 0x08 | release | generation(u32)、serial(u32) | —（serial 以下の区画を使い回してよい） | 必要 |
| 0x09 | query | 設定の TLV（configure と同じ） | 実際の値の TLV（設定はしない） | 不要 |
| 0x0A | calibration | — | 較正の情報の TLV（§3.8）。アナログだけ（ロジックは unknown_operation） | 不要 |

- state: 0 未設定、1 設定済み、2 トリガ待ち、3 取得中、4 完了（ワンショット）、5 止まっている（リピートで空き区画なし）、
  6 エラー。
- `serial_done` は終わった区画の数、`write_pos` は取り終えたバイト位置（position の空間。**捨てた分を含む**: 次に書くバイトの位置）。
- status の `flags`: bit0 probe の中でデータを落とした（取り込みのキューやリングがあふれた）、bit1 時間の基準が曲がった
  （区画の flags の bit2 と同じ）。ほかのビットは予約（0）。**start で 0 に戻し、その回の累積**。state 6 のときは応答の TLV 0x01 error（u8:
  1 DMA / ペリフェラル、2 置き場、3 時計、0x40〜 probe 固有）で理由を返す。
- **generation**: read と release は今の世代を要求に置く。違えば rejected unavailable（cause 6）。start 前は 0。
- read で要求した位置がもう使い回されていれば（または押し出されていれば）、応答の position が先に進み、gap が立つ。
  まだ取れていない位置なら、あるところまで返す（何もなければ空。max = 0 も空の成功）。
- release はリピートだけ（ワンショットとストリーミングでは何もせず成功）。serial **以下**（inclusive）を解放する。state 5 で空きが
  できれば probe は自動で取得を再開し（state 3）、再開した最初の区画に flags bit0 を立てる。stopped reason 2 は送らない（予約）。
- read の max は u32（1 回で大きく読むため、[設計](logic-capture.ja.md) §7.2）。実際に返す量は、probe の frame と `max_read`（宣言）で決まる。
- segments の more は、まだ返していない区画があること。from_serial が serial_done より先なら空の成功。

**状態の遷移**（行 = 今の state、列 = 契機。「—」は何もせず成功）:

| state | configure | start | stop | force | release | 自動 |
|---:|---|---|---|---|---|---|
| 0 未設定 | → 1 | unavailable 6 | — | — | — | plan 無しの configure / query も unavailable 6 |
| 1 設定済み | → 1 | → 2（トリガあり）/ 3。世代 +1、区画は消える | — | — | — | |
| 2 トリガ待ち | unavailable 6 | unavailable 6 | → 1（stopped 1） | → 3 | — | トリガ → 3（triggered） |
| 3 取得中 | unavailable 6 | unavailable 6 | → 1（stopped 1、短い区画 bit1） | — | 空きを返す | 完了 → 4（stopped 0）、空き無し → 5、エラー → 6（stopped 3） |
| 4 完了 | → 1 | → 2 / 3（世代 +1） | — | — | — | |
| 5 止まっている | unavailable 6 | unavailable 6 | → 1 | — | 空きができれば → 3（flags bit0） | |
| 6 エラー | → 1 | → 2 / 3（世代 +1） | → 1 | — | — | |

plan_release、lease の期限切れ、force で plan が解けたら state 0 に戻り、データも区画も消える（read は空）。mode 3（ストリーミング）の
start は、その fn の購読が無ければ rejected unavailable（cause 6）。取得中に購読が消えたら取り続け、送れない分は捨てる（position が飛ぶ）。
configure の応答の blocking_ms が core の max_op_ms を超える構成は、configure で rejected unsupported。

- start の応答から blocking_ms の間、probe はどの transport のフレームも処理しないことがあり、失うことがある。host はその間、その probe に
  どの transport でも何も送らない。その後、長さ前置きの transport では core §5.1 の resync から始める。シリアルポートではそのまま続ける。
  lease も host の待ち（core §4.4）も blocking_ms を数えない。

### 3.3 configure

**設定の TLV**（critical を立てた TLV（または値）を probe が扱えなければ configure 全体を
rejected unsupported（0x0B、payload に tag）で断り、立てていなければ無視して応答の `ignored`（0x7F）に載せる。core §2.3）:

| tag | 名前 | 値 | 対象 | critical で送るか |
|---|---|---|---|---|
| 0x40 | mode | u8: 1 ワンショット、2 リピート、3 ストリーミング（0x40〜 は別の定義） | 両方 | 常に |
| 0x42 | rate | rate_hz(u32)（アナログはチャネルあたり。1 Hz 以上。それより遅い記録は host の問い合わせの範囲で、v1 には入れない） | 両方 | 常に |
| 0x43 | samples | u32（1 区画のサンプル数。ストリーミングでは省略してよい） | 両方 | 立てずに送ってよい |
| 0x44 | segments | u32（リピートの区画の数。省略すれば probe に任せる） | 両方 | 立てずに送ってよい |
| 0x45 | trigger | type(u8)、role(u8)、value(u32) | 両方 | 常に |
| 0x46 | pretrigger | u32（トリガより前に残すサンプル数） | 両方 | 常に |
| 0x47 | frontend | role(u8)、frontend(u8: describe の frontend の番号) | アナログ | 常に |

- **問い合わせは別の操作（0x09）**。configure の TLV のフラグにすると、probe はロックの要否を操作の番号で決めるので、
  ロックなしの問い合わせができない（[設計](logic-capture.ja.md) §7.8）。問い合わせは今の設定と取ったデータを壊さない。
- trigger の type: 0 即時（省略時）、1 レベル（value 0 / 1）、2 エッジ（value 0 立ち上がり / 1 立ち下がり / 2 両方）、
  3 しきい値を上向きに横切る、4 下向きに横切る（value は o / b で切り出した後の ADC の値）。1〜2 はロジック、3〜4 はアナログ。
  宣言に無い type は rejected unsupported。
- トリガは開始の条件だけ。リピートとストリーミングでも、効くのは最初だけ（§2.1）。
- **samples は区画の総数**（pretrigger を含む）。トリガが早く立ってプリトリガの分が足りなければ、区画は短く、trigger_index はそのまま
  小さい。force で始めたときは trigger_index = その瞬間のサンプルで triggered を送る。type 0（即時）では triggered を送らない。
- **critical で送るもの**: mode、rate、trigger、pretrigger、frontend は常に critical で送る。そのどれかに従えない probe は configure を断る
  （unsupported、受け取ったままの tag）。
- **rate**: critical で送ったとき、probe は宣言した rate_range の中で実現できる最も近い値を使う（向きは問わない。どれかは actual_rate
  で分かる）。範囲の外の rate は rejected unsupported（tag 0x42）。
- **samples と segments** は critical を立てずに送ってよい。probe が持てる量を超える samples は、その上限に切り下げ、応答の actual_samples（0x52）
  が正である。host は送った値を仮定せず、actual_samples と actual_segments を読む。

**応答の TLV**:

| tag | 名前 | 値 | 対象 |
|---|---|---|---|
| 0x50 | actual_rate | num(u32)、den(u32)（実際のレート = num / den Hz） | 両方 |
| 0x51 | layout | ロジック: w(u8)、C(u8)、pos[C](u8)。アナログ: s(u8)、o(u8)、b(u8)、C(u8)、order[C](u8)（§1） | 両方 |
| 0x52 | actual_samples | u32 | 両方 |
| 0x53 | actual_segments | u32 | 両方 |
| 0x54 | timing | jitter_kind(u8: 0 なし / 1 分数分周 / 2 ソフトウェア)、jitter_ns(u32) | 両方 |
| 0x57 | skew | role(u8)、skew_ns(u32)。チャネルごとに 1 つ（遅れが 0 のチャネルは省いてよい） | アナログ |
| 0x55 | scale | role(u8)、zero(i32、値)、scale_nv(i32、1 値あたりの nV。負は反転する frontend)。チャネルごとに 1 つ。probe の入力ピンの電圧への 1 次式（§1.2） | アナログ |
| 0x56 | blocking_ms | u32（取っている間 probe が答えない時間の見込み。0 なら答える） | 両方 |
| 0x58 | frontend_used | role(u8)、frontend(u8: describe の frontend の番号)。チャネルごとに 1 つ。値の意味（測れる範囲、減衰）はその frontend の宣言で決まる | アナログ |
| 0x5A | rate_accuracy | how(u8: 0 分周から計算した公称値、1 測った値)、ppm(u32: actual_rate の不確かさの目安、0 は不明)。トラック間で時間の倍率を合わせ込むべきかの目安 | 両方 |
| 0x59 | reference | source(u8: 0 電源、1 内部、2 外部)、mv(u32)、how(u8: 0 公称、1 測った)。ADC の基準電圧。電源が基準の ADC では、同じ生の値の意味が電源電圧で変わる。scale の 1 次式はこの電圧を前提にした換算 | アナログ |
| 0x7F | ignored | tag(u8) の並び（core §2.3 の全文脈共通の ignored） | 両方 |

### 3.4 通知（core §11）

ロックの持ち主が subscribe すると、そのインターフェースから次が届く。購読しなければ、status と segments のポーリングで
同じことが分かる。

| 送るもの | いつ | 中身 |
|---|---|---|
| 出来事 kind 0x01 segment | 区画が終わった（ワンショットの完了も。ストリーミングでは送らない） | 区画の情報（§2）、[TLV] |
| 出来事 kind 0x02 stopped | 取得が止まった | reason(u8: 0 完了、1 host の stop、2 予約（空き区画なしは送らない）、3 エラー)、error(u8: reason 3 の理由、status の error と同じ値)、[TLV] |
| 出来事 kind 0x03 triggered | トリガが立った | serial(u32)、trigger_index(u32)、trigger_ns(u64: probe の時計でトリガが立った時刻の推定値)、[TLV] |
| データ（role 0x06） | ストリーミングの間だけ | core §11.2 の形（position、len、data、TLV）。read と同じ位置の空間。**TLV 0x01 generation(u32) を必ず付ける**（start の応答の後に前の世代の送り残しが届きうるため） |

- ストリーミングは subscribe が前提（データは probe が送る。features bit2 を立てる）。まとめて送る条件（min_bytes、max_delay_ms）は
  subscribe で指定する。
- ワンショットとリピートでは、データは host が read で読む。通知は完了を待つためのもの。

### 3.5 describe で宣言するもの

| tag | 名前 | 値 |
|---|---|---|
| 0x06 | features | 共通のビット。bit0 query（op 0x09）、bit1 force、bit2 通知 |
| 0x40 | mode | mode(u8)、background(u8: 1 = このモードで取っている間も probe は要求に答え続け、start の blocking_ms は 0。0 = 取っている間は答えず、start の blocking_ms がその長さを示す、§3.2。ほかの値は予約)、max_samples(u32、1 区画)、max_segments(u32)（モードごとに 1 つ。**最大**の置き場で答える。describe は宣言だけなので、その時点の空きでは答えない） |
| 0x41 | rate_range | min_hz(u32)、max_hz(u32)、exact(u8: 1 = 範囲内の任意の値を指定できる) |
| 0x42 | rate_list | n(u8)、n × rate_hz(u32)。代表的なレート。UI の一覧の候補。1 つの TLV に入らなければ繰り返してよい（和集合） |
| 0x43 | rate_limit | mode(u8)、channels(u8)、max_hz(u32)。チャネル数 C ≤ channels のときの上限（条件ごとに繰り返してよい） |
| 0x44 | channels | max(u8)、layout の候補(u32: ビット i が立っていれば 2^i を選べる。ロジックは w（1〜128: ビット 0〜7）、アナログは s（8、16、32: ビット 3〜5）） |
| 0x45 | trigger | types(u32: type のビット集合)、max_pretrigger(u32) |
| 0x46 | frontend | frontend(u8: 番号)、range_min_mv(i32)、range_max_mv(i32)、attenuation_mdb(u32: 前段の減衰、ミリ dB。0 は減衰なし、0xFFFFFFFF は減衰で表せない前段)。入力範囲の候補ごとに 1 つ（アナログ）。番号は configure の frontend で選ぶ。候補が 1 つだけの probe はそれだけ書く |
| 0x49 | frontend_shared | u8: 1 = すべてのチャネルが同じ frontend しか使えない（違う指定は configure で断る） |
| 0x47 | max_read | u32 |
| 0x48 | segment_ring | u16（覚えている区画の情報の数） |

- **宣言は目安、configure の応答が正。** 宣言に出ていない組み合わせは query で確かめる。

### 3.6 別の定義に回したもの

[設計](logic-capture.ja.md) §0.1 の表のとおり。この文書の前の版で configure に入れていた次の TLV は、基本から外した: トラック（複数トラック。
今は capture-group、§4）、外部クロック、多段トリガの段と条件、トリガ出力。役割の 0xC0〜（外部クロック、修飾、トリガ入出力）も同じ。別の定義を
書くときに、そちらで番号を振る。

- モード、トリガの type、layout の形式は、それぞれ 0x40 以降を別の定義に残す。
- configure と describe の TLV は 0x60〜0x7F を別の定義に残す。
- probe がデコードまでするもの（プロトコルアナライザ）は、このインターフェースを広げず、別のインターフェースにする。

### 3.7 使い方の例

```text
ワンショット（ロジック 2 本、20 MHz、テストの自動判定）
  plan_apply(logic: role0 = GPIO20, role1 = GPIO21)
  configure(mode=1, rate=20 MHz, samples=200000)
    → actual_rate 20000000/1, layout w=2 pos=[0,1], blocking_ms 0
  subscribe(logic)                      （完了の通知を待つ。購読しないなら status をポーリング）
  start → generation g → 出来事 segment（serial 0）→ read(g, 0, 65536) を何本か同時に出して最後まで読む

ワンショット、エッジで開始（SWCLK の最初の立ち下がりの 1000 サンプル前から）
  configure(mode=1, rate=20 MHz, samples=200000, trigger(edge, role1, fall), pretrigger=1000)
  start → 出来事 triggered → segment → read

リピート（長い時間を切れ目なく、host のペースで）
  configure(mode=2, rate=4 MHz, samples=65536, segments=8)
  subscribe → start → 出来事 segment ごとに read → release(g, serial)
  release が遅れると取得が止まり（state 5）、release で空きができれば自動で再開し、次の区画の flags bit0 が立つ

ストリーミング（アナログ 1 チャネル、44.1 kHz）
  plan_apply(analog: role0 = GPIO16)
  configure(mode=3, rate=44100, frontend(role 0, 番号 2))
    → actual_rate 44642/1 など（[設計](logic-capture.ja.md) §7.4 のとおり要求どおりにはならない）、layout s=16 o=0 b=12
  subscribe(analog, min_bytes=1024, max_delay_ms=20) → start → データが届く
```

### 3.8 calibration（アナログ）

ADC の値を電圧に換算するための、probe が持っている情報を**生のまま**返す。probe は補正を適用しない（read の値はいつも生の値。
換算は host が選ぶ。曲線の補正は測れる範囲の上下を削ることがあり、保存の段階で強制しない）。持たない情報は返さない。

| tag | 名前 | 値 |
|---|---:|---|
| 0x01 | factory | frontend(u8)、scheme_len(u8)、scheme(text)、raw_len(u16)、raw。出荷時にチップに書かれた較正の値を、読んだまま。scheme は形式の名前で、逆 DNS（形式の持ち主の名前空間。`a-z 0-9 - .`、1〜64 byte）。raw の解釈は scheme の定義に従う（例は [設計](logic-capture.ja.md) §3.0）。frontend ごとに 1 つ（frontend に依らないものは 0xFF） |
| 0x02 | vrefint | raw(u32)、ns(u64)、nominal_mv(u32)。内部の基準電圧（Vrefint など）を、最後の start（capture-group の start を含む）の直後に同じ ADC で測った生の値、その時刻、その基準電圧の公称値（mV。電源電圧の逆算に使う）。基準電圧が電源の ADC で、実際の電源電圧を逆算するのに使う。測れない probe は返さない |

- チップの型番とリビジョンは core の describe の chip（core §7.5）、firmware の版は同じく firmware。
- frontend ごとの減衰と測れる範囲は describe の frontend（§3.5）、チャネルごとに選ばれた frontend は configure の応答の
  frontend_used、基準電圧は reference（§3.3）。

## 4. `oep.fixture.capture-group`（複数のトラックを一緒に始める）

ロジックとアナログ、アナログ同士（2 つの ADC）など、**別々のインターフェースのトラックを、1 回のキャプチャとして一緒に始める**。
各トラックは今までどおり自分の configure を持ち、データも自分で読む（read、segments、release、status）。組が持つのは、どの
トラックを束ねるか、どのトラックのトリガで始めるか、組の開始と停止だけ。時刻はどのトラックも probe の 1 本の時計（冒頭の「時刻」）
なので、組の開始（start_ns）と各トラックの区画の start_ns の差が、そのトラックのずれになる。

### 4.1 操作

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | bind | n(u8)、n × fn(u16)、[TLV] | — | 必要 |
| 0x02 | start | — | blocking_ms(u32)、start_ns(u64)、[TLV 0x01 generations: n × (fn(u16)、generation(u32))] | 必要 |
| 0x03 | stop | — | — | 必要 |
| 0x04 | force | — | —（トリガを待っていれば、今すぐ始める） | 必要 |
| 0x05 | status | — | state(u8)、start_ns(u64)、trigger_ns(u64)、trigger_fn(u16)、[TLV] | 不要 |

bind の TLV:

| tag | 名前 | 値 |
|---:|---|---|
| 0x01 | trigger_track | fn(u16)。組の開始の条件を持つトラック（そのトラックの configure の trigger と pretrigger）。無ければ即時。**critical で送る**（無視されると意味が変わる） |

- **bind** は、configure 済みのトラック（`oep.fixture.logic` / `oep.fixture.analog` の fn）を束ねる。n = 0 で解く（state 3 のときは
  rejected unavailable cause 6。束ねていないときの n = 0 は何もせず成功）。断り方: 同じ fn の重複は malformed、宣言（tracks）に無い fn
  は unsupported、configure していない・モードが揃っていない・trigger_track 以外が即時でないトリガを持つ・budget を超える は
  unavailable（cause 6 / 2）。どのトラックについての断りかは payload の TLV fn（0x05、core §4.3。unsupported の payload も同じ）で返す。
  何も変えずに断る。束ねている間、各トラックの configure、start、stop、force は rejected unavailable
  （cause 4、holder_fn = 組の fn。組の op を使う。configure し直すときは、いったん n = 0 で解く）。束ねたトラックの plan の
  plan_release / plan_apply も rejected unavailable（cause 4）。**bind はセッションの資源**（core §9: end で残り、lease の期限切れと
  force で解ける）。
- トラックを束ねていないとき: start は rejected unavailable cause 6。stop と force は何もせず成功。state は 0。
- **start** は、どのトラックを始めるよりも前に全トラックの前提を確かめ（ストリーミングで購読の無いトラックがあれば、start は TLV fn（0x05）=
  そのトラックを付けて rejected unavailable cause 6）、それから束ねたトラックをできるだけ同時に始め、組の開始の時刻 start_ns（probe の時計）と、
  各トラックの新しい世代を返す（各トラックの start と同じく generation を +1）。始めた後にトラックが失敗したら、組は state 6、
  stopped reason 3 で、ほかのトラックも止める。**start_ns は取得（pretrigger のリングを含む）を始めた時刻**。トラック k の最初の
  区画の start_ns − 組の start_ns がそのトラックのずれ（推定値。即時トリガのときだけ成り立つ。トリガ付きは trigger_ns と各トラックの
  trigger_index で合わせる）。start 前の status の start_ns と trigger_ns は全ビット 1。
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

組の fn を subscribe すると、組の出来事が届く（各トラックの出来事は、そのトラックを subscribe したときに届く）。

| 送るもの | いつ | 中身 |
|---|---|---|
| 出来事 kind 0x03 triggered | trigger_track の条件が立った（力で始めたときも） | trigger_fn(u16: force では 0)、trigger_ns(u64)、[TLV] |
| 出来事 kind 0x02 stopped | 全トラックが止まった | reason(u8: トラックの stopped と同じ)、error(u8)、[TLV] |

kind の番号はトラック（§3.4）と揃える（triggered 3、stopped 2）。triggered はトラックの出来事としても出る（両方に出る）。

### 4.3 describe で宣言するもの

| tag | 名前 | 値 |
|---|---|---|
| 0x06 | features | bit1 force、bit2 通知（bit0 は 0: query は無い） |
| 0x40 | tracks | n(u8)、n × fn(u16)。束ねられるトラック |
| 0x41 | max_tracks | u8。1 つの組に入れられるトラックの数 |
| 0x42 | budget | max_sps(u32、チャネル数 × レートの合計の上限、sample/s)、n(u8)、n × fn(u16)。挙げた fn を一緒に束ねたときに分け合う上限（繰り返してよい。例: 1 つの ADC を 2 つのトラックで使う、DMA を分け合う） |
| 0x43 | start_skew | fn(u16)、typical_ns(u32)。そのトラックの開始が組の開始から遅れる目安（区画の start_ns で実際の値が分かるので、表示のため） |

- どのトラックの組が束ねられるかは tracks と budget で宣言し、確かめたいときは bind を試す（断られても何も変わらない）。
- 1 つのトラックの中の複数チャネル（1 つの ADC を順番に切り替える）は今までどおり、そのトラックの order と skew（§1.2、§3.3）。

### 4.4 使い方の例

```text
ロジック 2 本（20 MHz）とアナログ 1 本（48 kHz）を一緒に、ロジックの ch1 の立ち下がりで（1000 サンプル前から）
  plan_apply(logic: role0 = GPIO20, role1 = GPIO21; analog: role0 = GPIO16)
  logic.configure(mode=1, rate=20 MHz, samples=200000, trigger(edge, role1, fall), pretrigger=1000)
  analog.configure(mode=1, rate=48000, samples=4800, pretrigger=48)
  group.bind(logic, analog, trigger_track=logic)
  group.start → start_ns
  出来事 triggered(logic, trigger_ns) → 各トラックの segment（trigger_index はどちらも trigger_ns の位置）
  各トラックを read → host は start_ns の差と trigger_index で並べる
```

