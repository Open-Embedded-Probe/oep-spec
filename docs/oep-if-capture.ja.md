# OEP 標準インターフェース: キャプチャ v1

状態: **規範**（2026-09-26。ロジックは実機で確かめた形、アナログは実測がまだなく番号は仮）。本体は [OEP core](oep-core.ja.md)。
番号の唯一の定義は `registry/oep-v1.toml`。ロジアナとしての設計、基本と拡張の線引き、根拠の実測は
[キャプチャ（設計と実測）](logic-capture.ja.md)。

| 名前 | revision | 役割 |
|---|---:|---|
| `oep.fixture.capture` | 1 | ロジック（1 トラック） |
| `oep.fixture.analog` | 1 | アナログ（1 トラック） |

2 つは**操作の番号と形が同じ**で、違うのは configure の中身（§3.3）とデータの layout（§1）だけ。複数トラックの同時開始と時刻
合わせ（ミックスドシグナル）、外部クロック、多段トリガなどは、この 2 つを広げず別の定義にする（[設計](logic-capture.ja.md) §0.1）。
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
4. 電圧 = （値 − `zero`）× `scale`。`zero`（値）と `scale`（µV / 1 値）は configure の応答で返す（1 次式。曲線の較正は
   別の定義）。
5. チャネル m の時刻は、サンプルの時刻から `skew[m]` ns 遅れる（順番に切り替える ADC の場合）。

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
segment : serial(u32), position(u64), samples(u32), start_us(u64), trigger_index(u32), flags(u8)      29 byte
```

| フィールド | 意味 |
|---|---|
| serial | start からの区画の通し番号（0 から） |
| position | 区画の先頭のバイト位置（start から通し、u64 で一周しない。read と通知の position と同じ空間） |
| samples | 区画のサンプル数（stop で途中で終わった区画は短い） |
| start_us | 区画の最初のサンプルの時刻（probe の起動からの µs、u64 で一周しない） |
| trigger_index | 区画の中でトリガが立ったサンプルの番号。トリガを含まない区画は 0xFFFFFFFF |
| flags | bit0 前の区画との間が空いた（リピートで空き区画がなかった、ストリーミングで押し出された）、bit1 短い（stop で終わった） |

- 区画の中は連続を約束する。リピートとストリーミングでは、flags bit0 が立っていない限り、区画は前の区画の直後から続く。
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
| 0x47 | frontend | role(u8)、attenuation(u8、実装の値) | アナログ |

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
| 0x54 | timing | jitter_kind(u8: 0 なし / 1 分数分周 / 2 ソフトウェア)、jitter_ns(u32)、skew_ns[C](u32)（アナログ） | 両方 |
| 0x55 | scale | zero(u32、値)、scale_nv(u32、1 値あたりの nV) | アナログ |
| 0x56 | blocking_ms | u32（取っている間 probe が答えない時間の見込み。0 なら答える） | 両方 |
| 0x7F | ignored | tag(u8) の並び（core §2.3 の全文脈共通の ignored） | 両方 |

### 3.4 通知（core §11）

ロックの持ち主が subscribe すると、そのインターフェースから次が届く。購読しなければ、status と segments のポーリングで
同じことが分かる。

| 送るもの | いつ | 中身 |
|---|---|---|
| 出来事 kind 0x01 segment | 区画が終わった（ワンショットの完了も。ストリーミングでは送らない） | 区画の情報（§2） |
| 出来事 kind 0x02 stopped | 取得が止まった | reason(u8: 0 完了、1 host の stop、2 空き区画なし、3 エラー) |
| 出来事 kind 0x03 triggered | トリガが立った | serial(u32)、trigger_index(u32) |
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
| 0x46 | analog | range_min_mv(i32)、range_max_mv(i32)、減衰の候補の並び（アナログ） |
| 0x47 | max_read | u32 |
| 0x48 | segment_ring | u16（覚えている区画の情報の数） |

- **宣言は目安、configure の応答が正**（[設計](logic-capture.ja.md) §2.10）。宣言に出ていない組み合わせは query で確かめる。

### 3.6 別の定義に回したもの

[設計](logic-capture.ja.md) §0.1 の表のとおり。この文書の前の版で configure に入れていた次の TLV は、基本から外した: トラック（複数トラック）、
外部クロック、多段トリガの段と条件、トリガ出力。役割の 0xC0〜（外部クロック、修飾、トリガ入出力）も同じ。別の定義を
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
  configure(mode=3, rate=44100, frontend(0, 12 dB))
    → actual_rate 44642/1 など（[設計](logic-capture.ja.md) §7.4 のとおり要求どおりにはならない）、layout s=16 o=0 b=12
  subscribe(analog, min_bytes=1024, max_delay_ms=20) → start → データが届く
```

