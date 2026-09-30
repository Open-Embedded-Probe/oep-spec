# OEP 標準インターフェース: キャプチャ v1

状態: **規範**（2026-09-26。ロジックは実機で確かめた形、アナログは実測がまだなく番号は仮）。本体は [OEP core](oep-core.ja.md)。
番号の唯一の定義は `registry/oep-v1.toml`。ロジアナとしての設計、基本と拡張の線引き、根拠の実測は
[キャプチャ（設計と実測）](logic-capture.ja.md)。

| 名前 | revision | 役割 |
|---|---:|---|
| `oep.fixture.capture` | 1 | ロジック（1 トラック） |
| `oep.fixture.analog` | 1 | アナログ（1 トラック） |
| `oep.fixture.capture-group` | 1 | 複数のトラックを一緒に始める（ミックスドシグナル、§4） |

capture と analog は**操作の番号と形が同じ**で、違うのは configure の中身（§3.3）、データの layout（§1）、アナログだけの
calibration（§3.8）だけ。複数トラックの同時開始と時刻合わせは、この 2 つを広げず、トラックを束ねる別のインターフェース
（capture-group、§4）にする。外部クロック、多段トリガなどは別の定義（[設計](logic-capture.ja.md) §0.1）。

**時刻**: どのトラックの時刻も、probe の 1 本の時計（起動からの ns、u64 で一周しない）で表す。インターフェースが違っても同じ
時計なので、host は時刻の引き算でトラックを並べられる。時刻は**推定値と不確かさ**で返す。probe は知っている補正（ドライバが最初の
変換フレームを捨てる、など）を済ませた値を返し、それ以上の精度は約束しない。最後の合わせ込み（トラック間のオフセットと時間の
倍率）は host の分析の仕事（同じ信号を 2 つのトラックで取る、目印のパルスを全部のトラックで取る、など）。
時計は起動から数えるので、比べられるのは同じ起動の中だけ。host は open の応答の boot_id（core §6.5）が同じかで、同じ時計かを
判断する。
モード（ワンショット、リピート、ストリーミング）の意味は [設計](logic-capture.ja.md) §2.4、レートの決め方は同 §2.10。

## 1. データの形

用語: **ストリーム**は、1 回のキャプチャ（1 区画）で probe が返すバイトの並び。バイト位置 0 から始まる。
**ストリームのビット j** は、バイト `floor(j / 8)` のビット `j mod 8`（ビット 0 = LSB）と定める。

### 1.1 ロジック

configure の応答で probe が返す値:

| 値 | 範囲 | 意味 |
|---|---|---|
| `w` | 1, 2, 4, 8, 16, 32 のどれか | 1 サンプルのビット数。probe が選ぶ（チャネル数より大きくてよい） |
| `C` | 1 以上 | チャネル数（plan で割り当てたロジックの役割の数） |
| `pos[k]`（k = 0 … C−1） | 0 ≤ pos[k] < w、互いに異なる | チャネル k（役割の番号の小さい順）の、サンプルの中のビット位置 |
| `N` | 1 以上 | 区画のサンプル数 |

規則:

1. サンプル i（i = 0 … N−1）は、ストリームのビット `i·w` から `i·w + w − 1` まで。
2. サンプル i のチャネル k の値は、ストリームのビット `i·w + pos[k]`。
3. どの `pos[k]` にも当たらないビットの値は**未定義**。host は読まずに無視する（probe は 0 にしなくてよい）。
4. 区画の長さは `ceil(N·w / 8)` バイト。最後のバイトの、`N·w` を超えるビットは未定義。
5. w ≥ 8 のとき、サンプルは `w/8` バイトの little endian の整数と同じになる。w < 8 のとき、1 バイトに `8/w` サンプルが
   入り、若い番号のサンプルが下位ビットに来る。

例:

| 構成 | w | pos | 1 バイトの中身 |
|---|---|---|---|
| P4 PARLIO、1 本 | 1 | [0] | サンプル 0〜7 がビット 0〜7 |
| 1 バイト単位でしか取れない probe、1 本 | 8 | [0] | 1 バイトが 1 サンプル。ビット 1〜7 は未定義 |
| GPIO のポートの 1 バイトをそのまま取る probe、ピンがビット 5 | 8 | [5] | ビット 5 だけが意味を持つ |
| P4 PARLIO、**3 本** | 4 | [0, 1, 2] | ビット 0〜2 = サンプル 2m の ch0〜2、ビット 3 未定義、ビット 4〜6 = サンプル 2m+1 の ch0〜2、ビット 7 未定義 |
| classic ESP32 の sampler、**3 本** | 8 | [0, 1, 2] | 1 バイト 1 サンプル、ビット 3〜7 未定義 |
| P4 PARLIO、9 本 | 16 | [0 … 8] | 2 バイトで 1 サンプル（little endian）、ビット 9〜15 未定義 |

この規則に入らない取り方（RP2 の PIO の自動 push は、32 ビットのワードにサンプルを左詰めする）は、probe が詰め直すか、
別の定義の形式を使う。

### 1.2 アナログ

configure の応答で probe が返す値:

| 値 | 範囲 | 意味 |
|---|---|---|
| `s` | 8, 16, 32 のどれか | 1 つの値を入れる枠のビット数 |
| `o`, `b` | 0 ≤ o、1 ≤ b、o + b ≤ s | 枠の中の値の位置（ビット o から b ビット、符号なし） |
| `C` | 1 以上 | チャネル数 |
| `order[m]`（m = 0 … C−1） | チャネルの番号の並べ替え | サンプルの中の m 番目の枠が、どのチャネルか |
| `N` | 1 以上 | 区画のサンプル数 |

規則:

1. 枠は `s/8` バイトの little endian の整数。枠の値の `o` から `o+b−1` ビットが変換の結果（符号なし）。それ以外の
   ビットは未定義（host は無視する）。
2. サンプル i は、枠 `i·C` から `i·C + C − 1` まで。m 番目の枠がチャネル `order[m]`。
3. 区画の長さは `N·C·s/8` バイト。
4. チャネル k の電圧 = （値 − `zero[k]`）× `scale_nv[k]`。`zero` と `scale_nv`（nV / 1 値）は configure の応答でチャネルごとに返す（1 次式。曲線の較正は
   別の定義）。
5. チャネル k の時刻は、サンプルの時刻から `skew_ns[k]` 遅れる（順番に切り替える ADC の場合）。

例:

| 構成 | s | o | b | 備考 |
|---|---|---|---|---|
| ESP32-S3 / P4 の ADC（DMA の 4 バイトのレコードのまま） | 32 | 0 | 12 | ビット 13〜16 のチャネル番号などは未定義として無視される。チャネルの順番がパターンどおりであることが条件（崩れる場合は probe が並べ直すか、そのレートを宣言から外す） |
| classic ESP32 の ADC（2 バイトのレコードのまま） | 16 | 0 | 12 | 上位 4 ビット（チャネル番号）は未定義 |
| RP2 の ADC（FIFO の 16 ビット） | 16 | 0 | 12 | |
| RP2 の ADC（8 ビットに縮めたもの） | 8 | 0 | 8 | |




## 2. 区画

1 回のキャプチャは、トラック 1 本の**位置の付いたバイトの並び**（ストリーム、§1）で、区画に分かれる。

| モード | 区画 |
|---|---|
| ワンショット | 1 個（serial 0）。次の start で消える |
| リピート | 隙間なく続く。host が解放するまで読める。空き区画がなくなったら取得を止め、次の区画に「止まった」印が付く |
| ストリーミング | probe の都合の区切り（DMA の 1 回ぶんなど）。データは probe が送ってくる（§3.4） |

```text
segment : serial(u32), position(u64), samples(u32), start_ns(u64), start_uncertainty_ns(u32), trigger_index(u32), flags(u8)   33 byte
```

| フィールド | 意味 |
|---|---|
| serial | start からの区画の通し番号（0 から） |
| position | 区画の先頭のバイト位置（start から通し、u64 で一周しない。read と通知の position と同じ空間） |
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

- 役割 k = チャネル k（ロジックは 0〜127、アナログは 0〜63）。チャネルの順は役割の番号の小さい順。
- ADC のチャネルを持たないピンは、アナログの plan で拒否する。
- 外部クロック、トリガの入力と出力のピンは基本に入れない（別の定義）。

### 3.2 操作

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | configure | 設定の TLV（§3.3） | 実際の値の TLV（§3.3） | 必要 |
| 0x02 | start | — | blocking_ms(u32)（0 = 取っている間も答える） | 必要 |
| 0x03 | stop | — | — | 必要 |
| 0x04 | force | — | —（トリガを待っていれば、今すぐ始める） | 必要 |
| 0x05 | status | — | state(u8)、serial_done(u32)、write_pos(u64)、flags(u8) | 不要 |
| 0x06 | read | position(u64)、max(u32) | position(u64)、flags(u8: bit0 more、bit1 gap)、data | 不要 |
| 0x07 | segments | from_serial(u32) | count(u8)、区画の情報の並び（§2） | 不要 |
| 0x08 | release | serial(u32) | —（serial 以前の区画を使い回してよい） | 必要 |
| 0x09 | query | 設定の TLV（configure と同じ） | 実際の値の TLV（設定はしない） | 不要 |
| 0x0A | calibration | — | 較正の情報の TLV（§3.8）。アナログだけ（ロジックは unknown_operation） | 不要 |

- state: 0 未設定、1 設定済み、2 トリガ待ち、3 取得中、4 完了（ワンショット）、5 止まっている（リピートで空き区画なし）、
  6 エラー。
- `serial_done` は終わった区画の数、`write_pos` は取り終えたバイト位置。
- read で要求した位置がもう使い回されていれば（または押し出されていれば）、応答の position が先に進み、gap が立つ。
  まだ取れていない位置なら、あるところまで返す（何もなければ空）。
- release はリピートだけ。ワンショットでは不要（次の start で消える）、ストリーミングでは送った分から probe が使い回す。
- read の max は u32（1 回で大きく読むため、[設計](logic-capture.ja.md) §7.2）。実際に返す量は、probe の frame と `max_read`（宣言）で決まる。

### 3.3 configure

**設定の TLV**（ロジックは確定、2026-09-25。critical を立てた TLV（または値）を probe が扱えなければ configure 全体を
rejected unsupported（0x0B、payload に tag）で断り、立てていなければ無視して応答の `ignored`（0x7F）に載せる。core §2.3）:

| tag | 名前 | 値 | 対象 |
|---|---|---|---|
| 0x40 | mode | u8: 1 ワンショット、2 リピート、3 ストリーミング（0x40〜 は別の定義） | 両方 |
| 0x42 | rate | rate_hz(u32)（アナログはチャネルあたり） | 両方 |
| 0x43 | samples | u32（1 区画のサンプル数。ストリーミングでは省略してよい） | 両方 |
| 0x44 | segments | u32（リピートの区画の数。省略すれば probe に任せる） | 両方 |
| 0x45 | trigger | type(u8)、role(u8)、value(u16) | 両方 |
| 0x46 | pretrigger | u32（トリガより前に残すサンプル数） | 両方 |
| 0x47 | frontend | role(u8)、frontend(u8: describe の frontend の番号) | アナログ |

- **問い合わせは別の操作（0x09）**。configure の TLV のフラグにすると、probe はロックの要否を操作の番号で決めるので、
  ロックなしの問い合わせができない（試作で踏んだ、[設計](logic-capture.ja.md) §7.8）。問い合わせは今の設定と取ったデータを壊さない。
- trigger の type: 0 即時（省略時）、1 レベル（value 0 / 1）、2 エッジ（value 0 立ち上がり / 1 立ち下がり / 2 両方）、
  3 しきい値を上向きに横切る、4 下向きに横切る（value は ADC の値）。1〜2 はロジック、3〜4 はアナログ。
- トリガは開始の条件だけ。リピートとストリーミングでも、効くのは最初だけ（[設計](logic-capture.ja.md) §2.4）。

**応答の TLV**:

| tag | 名前 | 値 | 対象 |
|---|---|---|---|
| 0x50 | actual_rate | num(u32)、den(u32)（実際のレート = num / den Hz） | 両方 |
| 0x51 | layout | ロジック: w(u8)、C(u8)、pos[C](u8)。アナログ: s(u8)、o(u8)、b(u8)、C(u8)、order[C](u8)（§1） | 両方 |
| 0x52 | actual_samples | u32 | 両方 |
| 0x53 | actual_segments | u32 | 両方 |
| 0x54 | timing | jitter_kind(u8: 0 なし / 1 分数分周 / 2 ソフトウェア)、jitter_ns(u32) | 両方 |
| 0x57 | skew | role(u8)、skew_ns(u32)。チャネルごとに 1 つ（遅れが 0 のチャネルは省いてよい） | アナログ |
| 0x55 | scale | role(u8)、zero(u32、値)、scale_nv(u32、1 値あたりの nV)。チャネルごとに 1 つ | アナログ |
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
| 出来事 kind 0x01 segment | 区画が終わった（ワンショットの完了も。ストリーミングでは送らない） | 区画の情報（§2） |
| 出来事 kind 0x02 stopped | 取得が止まった | reason(u8: 0 完了、1 host の stop、2 空き区画なし、3 エラー) |
| 出来事 kind 0x03 triggered | トリガが立った | serial(u32)、trigger_index(u32)、trigger_ns(u64: probe の時計でトリガが立った時刻の推定値) |
| データ（role 0x06） | ストリーミングの間だけ | position(u64) と data（[共通部品](oep-if-common.ja.md) §1.5 の形。read と同じ位置の空間） |

- ストリーミングは subscribe が前提（データは probe が送る）。まとめて送る条件（min_bytes、max_delay_ms）は subscribe で
  指定する。
- ワンショットとリピートでは、データは host が read で読む。通知は完了を待つためのもの。

### 3.5 describe で宣言するもの

| tag | 名前 | 値 |
|---|---|---|
| 0x06 | features | 共通のビット。bit0 query（op 0x09）、bit1 force、bit2 通知 |
| 0x40 | mode | mode(u8)、background(u8)、max_samples(u32、1 区画)、max_segments(u32)（モードごとに 1 つ。置き場の量は describe の時点の空きで答えてよい: PSRAM の有無と量で変わる） |
| 0x41 | rate_range | min_hz(u32)、max_hz(u32)、exact(u8: 1 = 範囲内の任意の値を指定できる) |
| 0x42 | rate_list | 代表的なレートの並び（u32）。UI の一覧の候補 |
| 0x43 | rate_limit | mode(u8)、channels(u8)、max_hz(u32)（条件ごとの上限。繰り返してよい） |
| 0x44 | channels | max(u8)、layout の候補（ロジック: w のビット集合。アナログ: s の候補） |
| 0x45 | trigger | type のビット集合、max_pretrigger(u32) |
| 0x46 | frontend | frontend(u8: 番号)、range_min_mv(i32)、range_max_mv(i32)、attenuation_mdb(u32: 前段の減衰、ミリ dB。0 は減衰なし、0xFFFFFFFF は減衰で表せない前段)。入力範囲の候補ごとに 1 つ（アナログ）。番号は configure の frontend で選ぶ。候補が 1 つだけの probe はそれだけ書く |
| 0x49 | frontend_shared | u8: 1 = すべてのチャネルが同じ frontend しか使えない（違う指定は configure で断る） |
| 0x47 | max_read | u32 |
| 0x48 | segment_ring | u16（覚えている区画の情報の数） |

- **宣言は目安、configure の応答が正**（[設計](logic-capture.ja.md) §2.10）。宣言に出ていない組み合わせは query で確かめる。

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
  plan_apply(capture: role0 = GPIO20, role1 = GPIO21)
  configure(mode=1, rate=20 MHz, samples=200000)
    → actual_rate 20000000/1, layout w=2 pos=[0,1], blocking_ms 0
  subscribe(capture)                    （完了の通知を待つ。購読しないなら status をポーリング）
  start → 出来事 segment（serial 0）→ read(0, 65536) を何本か同時に出して最後まで読む

ワンショット、エッジで開始（SWCLK の最初の立ち下がりの 1000 サンプル前から）
  configure(mode=1, rate=20 MHz, samples=200000, trigger(edge, role1, fall), pretrigger=1000)
  start → 出来事 triggered → segment → read

リピート（長い時間を切れ目なく、host のペースで）
  configure(mode=2, rate=4 MHz, samples=65536, segments=8)
  subscribe → start → 出来事 segment ごとに read → release(serial)
  release が遅れると取得が止まり（出来事 stopped reason 2）、次の区画の flags bit0 が立つ

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
| 0x01 | factory | frontend(u8)、scheme_len(u8)、scheme(text)、raw(残り)。出荷時の較正の値（ESP32 の eFuse など）を、読んだまま。scheme は形式の名前で、形式の持ち主の名前空間に置く（例 `com.espressif.esp32.two-point`、`com.espressif.esp32p4.curve-fitting.v1`）。raw の解釈は scheme の定義に従う。frontend ごとに 1 つ（frontend に依らないものは 0xFF） |
| 0x02 | vrefint | raw(u32)、ns(u64)。内部の基準電圧（Vrefint など）を、最後の start（capture-group の start を含む）の直後に同じ ADC で測った生の値と、その時刻。基準電圧が電源の ADC で、実際の電源電圧を逆算するのに使う。測れない probe は返さない |

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
| 0x02 | start | — | blocking_ms(u32)、start_ns(u64) | 必要 |
| 0x03 | stop | — | — | 必要 |
| 0x04 | force | — | —（トリガを待っていれば、今すぐ始める） | 必要 |
| 0x05 | status | — | state(u8)、start_ns(u64)、trigger_ns(u64)、trigger_fn(u16) | 不要 |

bind の TLV:

| tag | 名前 | 値 |
|---:|---|---|
| 0x01 | trigger_track | fn(u16)。組の開始の条件を持つトラック（そのトラックの configure の trigger と pretrigger）。無ければ即時 |

- **bind** は、configure 済みのトラック（`oep.fixture.capture` / `oep.fixture.analog` の fn）を束ねる。n = 0 で解く。束ねられない組
  （宣言に無い fn、同じ fn の重複、configure していない、モードが揃っていない、trigger_track 以外が即時でないトリガを持つ、
  budget を超える）は、何も変えずに rejected unavailable。束ねている間、各トラックの configure、start、stop、force は
  rejected unavailable（組の op を使う。configure し直すときは、いったん n = 0 で解く）。
- **start** は、束ねたトラックをできるだけ同時に始め、組の開始の時刻 start_ns（probe の時計）を返す。トラック k の最初の区画の
  start_ns − 組の start_ns が、そのトラックのずれ（推定値。不確かさは区画の start_uncertainty_ns）。
- **トリガ**: trigger_track の条件が立つと、組の全トラックが取得を始める（各トラックの pretrigger は、そのトラック自身の
  サンプル数で残す）。立った時刻 trigger_ns は status と出来事 triggered で返し、**全トラックの、その時刻を含む区画の
  trigger_index を、そのトラックでその時刻に最も近いサンプルにする**（probe が各トラックの時間軸に写す）。host はどのトラックでも
  同じ瞬間の位置を知る。
- **stop** は全トラックを止める。区画はトラックごとに（短い区画は flags bit1）。
- status の state は capture と同じ値（§3.2）で、組全体の状態（全トラックが完了したら完了）。trigger_ns は立っていなければ
  0xFFFFFFFFFFFFFFFF、trigger_fn は 0。
- モードは全トラックで同じ（ワンショット、リピート、ストリーミング）。リピートの release とストリーミングの push は、トラック
  ごとに今までどおり。

### 4.2 通知

組の fn を subscribe すると、組の出来事が届く（各トラックの出来事は、そのトラックを subscribe したときに届く）。

| 送るもの | いつ | 中身 |
|---|---|---|
| 出来事 kind 0x01 triggered | trigger_track の条件が立った | trigger_fn(u16)、trigger_ns(u64) |
| 出来事 kind 0x02 stopped | 全トラックが止まった | reason(u8: capture の stopped と同じ) |

### 4.3 describe で宣言するもの

| tag | 名前 | 値 |
|---|---|---|
| 0x40 | tracks | n × fn(u16)。束ねられるトラック |
| 0x41 | max_tracks | u8。1 つの組に入れられるトラックの数 |
| 0x42 | budget | max_rate(u32、チャネル数 × レートの合計の上限、sample/s)、n × fn(u16)。挙げた fn を一緒に束ねたときに分け合う上限（繰り返してよい。例: 1 つの ADC を 2 つのトラックで使う、DMA を分け合う） |
| 0x43 | start_skew | fn(u16)、typical_ns(u32)。そのトラックの開始が組の開始から遅れる目安（区画の start_ns で実際の値が分かるので、表示のため） |

- どのトラックの組が束ねられるかは tracks と budget で宣言し、確かめたいときは bind を試す（断られても何も変わらない）。
- 1 つのトラックの中の複数チャネル（1 つの ADC を順番に切り替える）は今までどおり、そのトラックの order と skew（§1.2、§3.3）。

### 4.4 使い方の例

```text
ロジック 2 本（20 MHz）とアナログ 1 本（48 kHz）を一緒に、ロジックの ch1 の立ち下がりで（1000 サンプル前から）
  plan_apply(capture: role0 = GPIO20, role1 = GPIO21; analog: role0 = GPIO16)
  capture.configure(mode=1, rate=20 MHz, samples=200000, trigger(edge, role1, fall), pretrigger=1000)
  analog.configure(mode=1, rate=48000, samples=4800, pretrigger=48)
  group.bind(capture, analog, trigger_track=capture)
  group.start → start_ns
  出来事 triggered(capture, trigger_ns) → 各トラックの segment（trigger_index はどちらも trigger_ns の位置）
  各トラックを read → host は start_ns の差と trigger_index で並べる
```

