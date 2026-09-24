# Open Embedded Probe — 能力の宣言モデル（describe の語彙）

状態: **非規定の設計案**（2026-09-24）。[能力の識別方式の比較](capability-identification-comparison.ja.md) の推奨
（名前で識別し、セッション内は `fn` で使う）の上で、probe が「何を、どのピンで、どこまでできるか」をどう宣言するかを
決める。**どの能力を BASIC（標準）にするかは決めない。** 決めるのは宣言の仕組みだけである。

## 目的

v0 では次のことが、実際に試して reject されるまで host に分からない。

- ある機能がどのピンでも動く（ビットバン）のか、特定のピン・組み合わせでしか動かない（専用ペリフェラル）のか。
- 任意の操作やモード（意図的な clock stretching、リセットの種類、コンソールの framing）があるか。
- target 側のデバッグ方式（RVSWD、SWIO、ARM SWD）や、NRST の線があるか。

これを list と describe だけで、試す前に分かるようにする。

## 全体の流れ

```text
confirm           → frame / window の数値
list(prefix)      → 名前、fn、revision、instance
describe(fn)      → TLV: role ごとのピン候補、ピンの組、上限、機能ビット、実装の種類
plan_apply        → role を channel に割り当てる（原子的）。describe に合わない割り当ては reject
操作              → fn で呼ぶ
```

## 1. 同じインスタンスの仲間: list の entry に instance を持たせる

1 つのインスタンスが複数のインターフェース（標準の `oep.fixture.i2c-target` と独自の
`io.github.ch32-riscv-ug.p4.i2c-target` など）を持つとき、インターフェースごとに別の `fn` を振る。
それらが同じインスタンスであることは、list の entry の `instance`（u16）で示す。

```text
list entry : fn(u16), instance(u16), revision(u8), flags(u8), name_len(u8), name(bytes)
```

- 同じ `instance` の `fn` は、plan を共有する（どれかの `fn` で割り当てた role は、同じインスタンスの他の `fn` にも効く）。
- describe の TLV でなく list に持たせるのは、仲間を知るのに describe の往復を増やさないため。2 byte で済む。

## 1.5 describe のページ送り

```text
describe request : fn(u16), first(u8)
describe result  : more(u8), TLV bytes
```

`more` = 1 は「このページのあとにも TLV が残っている。`first` にこのページの TLV の数を足して、もう一度聞け」を
意味する。v0 は `more` を持たず、host は空の応答が返るまでもう一度聞くしかなかったので、インターフェースごとに
1 往復が無駄になっていた（oep-client-python の `dump` で、P4 相当 14 インターフェースに 26 往復）。`more` を付けると、
インターフェースごとに 1 往復になる（同 14 往復）。64 byte frame の低スペック probe 相当 12 インターフェースでは
list 8 + describe 12 = 20 往復（`more` なしでは 30 往復）。

## 2. describe の TLV のタグ空間

v0 の TLV（tag u8、len u8、bit 7 = critical）を保ったまま、tag を二つに分ける。

| tag（bit 7 を除く） | 空間 | 意味を決めるもの |
|---|---|---|
| 0x01〜0x3F | 共通 | この文書（全インターフェースで同じ意味） |
| 0x40〜0x7F | インターフェース固有 | そのインターフェースの定義 |

独自の情報は独自インターフェースの describe に置く。標準インターフェースの describe に独自タグを混ぜない
（[比較文書の規則 2](capability-identification-comparison.ja.md)）。

## 3. 共通タグ

| tag | 名前 | 値 | 目的 |
|---|---|---|---|
| 0x01 | role_channels | role(u8), base(u16), bitmap(bytes) | **role ごとのピン候補**。bit i が立っていれば channel `base+i` をその role に使える。同じ role を複数回書いてよい（和集合） |
| 0x02 | max_clock_hz | u32 | 上限（v0 と同じ） |
| 0x03 | max_length | u16 | 1 回に扱える最大長（v0 と同じ） |
| 0x04 | exclusive_group | u16、繰り返し | 同じ group の機能は同時に使えない（資源の共有）。v0 と同じ |
| 0x05 | min_clock_hz | u32 | 下限（v0 と同じ） |
| 0x06 | features | u32 | **任意機能のビット**。各 bit の意味はインターフェースの定義が決める |
| 0x07 | implementation | u8 | 参考情報。0 = 未指定、1 = ソフトウェア（ビットバン）、2 = 専用ペリフェラル、3 = ペリフェラル + DMA/PIO。host はこれで動作を変えず、表示と診断に使う |
| 0x08 | channel_group | group(u8), [role(u8), channel(u16)] × n | **ピンの組の制約**。この group を使うなら、各 role はここに書いた channel に固定される。group が一つ以上ある機能では、plan はいずれか一つの group に完全に一致しなければならない |
| 0x90 | role_assignment | function(u16), role(u8), channel(u16) | plan 用（v0 と同じ、critical） |
| 0x91 | start_together | function(u16)、繰り返し | plan 用（v0 と同じ、critical） |

### role_channels と channel_group の使い分け

- **どのピンにも割り当てられる**（ESP32 の GPIO マトリクス、ビットバン）: role_channels に候補を並べるだけ。
- **ピンは決まっているが、候補が何組かある**（STM32 型の AF 固定ピン、Pico の PIO が連続ピンを要する場合）:
  channel_group を組の数だけ書く。
- 両方を書いた場合、plan は channel_group のどれかに一致し、かつ role_channels の候補にも入っていなければならない。

v0 の `channel_candidate`（role のない平たい一覧）は廃止する。

### features の例（命名と同じく例であり、標準の中身を決めるものではない）

| インターフェース（例） | bit | 意味 |
|---|---|---|
| target.riscv-dm | 0 | デバッグ経由のシステムリセット（ndmreset） |
| target.riscv-dm | 1 | リセット直後に停止（reset-halt） |
| target.console | 0 / 1 / 2 | 方式 SDI / DMDATA / dmseq（debug の connection の上に開く） |
| fixture.i2c-target | 0 | target からの読み出し（preloaded tx） |
| fixture.i2c-target | 1 | 意図的な clock stretching |

v0 の target_control.reset の mode 1/2（UIAPduino のブートローダ用 RAM ペイロード）は probe 固有なので、標準の
features ではなく独自インターフェースに移す。

## 4. target 側の能力

> 2026-09-24 の合意（仮置き）で、アーキテクチャに中立な `oep.target.control` などは作らないことにした。target への
> アクセスは `oep.wire.<線>` の attach が返す connection を使い、`oep.target.<riscv-dm|arm-adi>` で行う。NRST の線は
> アーキテクチャに依らないので `oep.fixture` か `oep.wire` の側に置く（未決）。
> [能力の名前の階層](capability-name-hierarchy.ja.md)。

線や target を扱うインターフェース（`oep.wire.<線>`、`oep.target.<riscv-dm|arm-adi>`）の describe に、インターフェース固有
タグで次を宣言する。

| 宣言 | 値 | 例 |
|---|---|---|
| debug_transport | u8、繰り返し | 1 = RVSWD、2 = SWIO（1 線）、3 = ARM SWD、4 = JTAG |
| target_voltage | u16 mV、または範囲 | I/O 電圧 |

- **target の系統（CH32V003 など）は宣言しない。** 系統ごとの知識（flash の形、debug module の癖）は host
  （ch32rv の DB など）が持つ。probe は電気的な経路だけを宣言する。
- デバッグのレジスタを直接読む操作（v0 の read_dmi / read_register）は、アーキテクチャ別のインターフェースに
  分ける（例: `oep.target.riscv-dm`）。ARM SWD の target には別のものが付く。
- **target を扱うインターフェースは、attach の前から list に出す**（2026-09-24 の合意、仮置き）。能力として見え、
  操作には attach が返した connection を付ける。未 attach で呼べばエラー。attach のたびに list が変わる形は採らない
  （[target の発見と接続](target-connection-use-cases.ja.md)）。

## 5. probe 全体の能力

v0 の probe_identity は u64 のピンマスク（reserved / fixture）を持つ。これを probe 全体の describe の TLV に移す。

| 宣言 | 値 |
|---|---|
| channel_count | u16 |
| reserved_channels | base(u16), bitmap（probe 自身が使っていて割り当てられないピン） |
| profile | 名前（例: `io.github.ch32-riscv-ug.p4-devkit`） |
| channel_label | channel(u16), 名前（`GPIO5`、`D5`、`PA13`、fixture の端子名など。任意） |
| resets_on_open | transport を開くとリセットされる probe だけが宣言する（host は閉じずに 1 セッションで使う） |
| uart_rates | UART の transport を持つ probe が、自分の UART で設定できる速度を**一覧**で宣言する（u32 の繰り返し。細かい刻みは扱わない）。速度の変更そのものは任意の機能で後回し。変換チップの制約は host が VID:PID から知り、経路の実力は取り決めのときに確かめる（[probe 開発ガイド](probe-development-guide.ja.md) §3.5） |

64 本を超える probe や、ピン以外の資源も表せるようになる。

channel は probe が振る番号で、同じファームとプロファイルなら起動ごとに同じになる。利用者はラベルで指定し、host が
channel に直す（2026-09-24 の合意、仮置き。[target の発見と接続](target-connection-use-cases.ja.md)）。

## 6. 例: P4 の I2C target

```text
list:
  fn 5  instance 3  oep.fixture.i2c-target                  rev 0
  fn 6  instance 3  io.github.ch32-riscv-ug.p4.i2c-target   rev 0
describe(5):
  role_channels   role 1 (SDA)  base 0  bitmap = GPIO マトリクスで使える全ピン
  role_channels   role 2 (SCL)  同上
  max_length      128
  max_clock_hz    1000000
  features        bit0 (preloaded tx) | bit1 (clock stretching)
  implementation  2 (専用ペリフェラル)
describe(6):
  （P4 固有: read_hw の有無、stretch の上限など、この独自インターフェースのタグ）
```

同じ機能をビットバンで実装する低スペック probe は、同じ `oep.fixture.i2c-target` を、低い max_clock_hz と
`implementation 1` で宣言する。host は同じコードで両方を使える。

## 7. v0 から壊す点（まとめ）

| 変更 | 理由 |
|---|---|
| 識別を `owner:id` から名前へ | 登録なしで衝突しない独自拡張 |
| list の entry に name と instance | 名前での発見、1 インスタンス複数インターフェース |
| describe の result の先頭に more | ページの終わりを知るための無駄な 1 往復をなくす |
| list の request に prefix と exact | 名前空間での絞り込み |
| `channel_candidate` を role_channels に置き換え、channel_group を追加 | 専用ピンの制約を宣言できるように |
| features と implementation を追加 | 任意機能と実装の種類を試す前に分かるように |
| reset の mode 1/2 を独自インターフェースへ | 標準に probe 固有の意味を入れない |
| read_dmi / read_register をアーキテクチャ別へ | ARM SWD の target を扱えるように |
| probe_identity の u64 マスクを TLV へ | 64 本を超える probe、ピン以外の資源 |

## 未決

- role_channels の bitmap の最大長（TLV の len が u8 なので 253 byte = 2024 channel まで。十分か）。
- channel_group の数の上限と、role_channels との組み合わせ規則の検証方法（probe 側の実装コスト）。
- features の 32 bit で足りるか（足りなければ 2 本目のタグ）。
- target_voltage の表し方（固定値か範囲か、可変電源の probe をどう扱うか）。
- どの機能を BASIC（`oep.` の標準）にするか（この文書の対象外）。
