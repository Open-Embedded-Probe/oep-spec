# OEP 標準インターフェース: 共通部品 v1

状態: **規範**（2026-09-26）。本体は [OEP core](oep-core.ja.md)。ここは、複数の標準インターフェースが同じ形で使う部品を
定める。部品は本体ではない。ある標準インターフェースがこの部品を使うと書いたときだけ、そのインターフェースに効く
（独自のインターフェースが同じ部品を使うのは自由）。番号の唯一の定義は `registry/oep-v1.toml`。

## 1. 位置つきのストリーム

使うもの: `oep.target.console`、`oep.fixture.uart`、`oep.fixture.capture` / `oep.fixture.analog`（区画つき。それぞれの文書）。

### 1.1 位置

- probe はストリームの各バイトに通し番号（**位置**、u64、一周しない）を振る。位置は、ストリームを作ったとき（または
  probe の起動）に 0 から始まる。
- **読み出しはバッファを消費しない。** バイトが消えるのは次のときだけ:
  1. あふれ（古いものから押し出す。target や相手を待たせない）。
  2. host の明示の消去（clear）。
  3. probe の再起動（位置も 0 から。boot_id が変わる）。
- target のリセットでは捨てない（リセット直前の出力が最も見たいことが多い）。代わりにマークを付ける（§1.3）。
- 応答が失われても、同じ位置でもう一度読めば同じデータが返る。

### 1.2 read

```text
要求: [stream(u8)]、from(u8)、arg(u64)、max(u16)
応答: start(u64)、flags(u8: bit0 more、bit1 gap)、data
```

| from | 意味 |
|---:|---|
| 0 | 位置 arg から |
| 1 | 残っている一番古いバイトから |
| 2 | 今から（まだ何もない位置） |
| 3 | kind が arg の最後のマークの位置から（arg 0 はどの kind でも） |

- `start` は data の先頭の位置。要求した位置がもう押し出されていれば start が先に進み、gap が立つ（差が失われた量）。
- `more` は、この応答の後ろにまだ読めるバイトがあること。host はすぐ次を読んでよい。
- data は長さの分からない並びなので、read の応答の後ろには何も足せない（core §2.3）。
- **read はロックなしで使える**（読んでも状態は変わらず、probe は読み手ごとの状態を持たない）。

### 1.3 マーク

```text
mark : serial(u32)、position(u64)、kind(u8)、time_ms(u32)、detail(u8)          18 byte
```

| kind | 名前 | 付ける契機 | detail |
|---:|---|---|---|
| 0x01 | reset | probe の指示で target をリセットした | 方法 |
| 0x02 | restart | target の再起動を検出した | 検出元 |
| 0x03 | attach | attach した | — |
| 0x04 | detach | detach した | — |
| 0x05 | lost | あふれで押し出した、または受信の誤り | 理由 |
| 0x06 | clear | host が消去した | — |
| 0x07 | host | host が付けた印 | host の値 |
| 0x08 | link-lost | 線が落ちた | — |

- kind の空間: 0x01〜0x3F 標準、0x40〜0x7F インターフェース固有。
- `serial` はストリームごとのマークの通し番号（u32、一周する。core §2.6）。同じ位置に複数のマークが付いても、serial で
  落ちも重複もなく読める。
- `time_ms` は probe の起動からの ms（u32、一周する）。バイトごとの時刻は持たない。
- マークは本文とは別の小さなリングにためる。あふれたら古いものから捨てる。

```text
marks  要求: [stream(u8)]、from_serial(u32)
       応答: more(u8)、count(u8)、count × mark
```

marks はロックなしで使える。

### 1.4 状態を変える操作

| 操作 | 要求 | 応答 | 意味 |
|---|---|---|---|
| clear | [stream(u8)] | — | 貯めたバイトを捨て、マーク clear を付ける |
| mark | [stream(u8)]、value(u8) | — | マーク host（detail = value）を付ける |
| write | [stream(u8)]、count(u16)、data | accepted(u16) | 相手への入力。受け付けた分だけ返す（バッファしない）。全部受け付けなければ completed partial |

どれもロックが要る。

### 1.5 通知のデータ

ストリームを送り出すインターフェースは、core の通知（core §11）のデータの payload を次の形にする。

```text
position(u64) | data
```

`position` はこのフレームの先頭の位置。前のフレームの終わりと合わなければ、その間は probe の中で押し出された。送ったデータを
read で読み直せるかはインターフェースが決める。

## 2. debug の connection

使うもの: `oep.wire.rvswd`、`oep.wire.swio`、`oep.wire.swd`（作る）、`oep.target.riscv-dm`、`oep.target.arm-adi`、
`oep.target.console`（使う）、`oep.probe.config` の bind（使う）。

- **connection** は、線の attach が作る、ある target への接続。番号（u8）で指し、target の操作の要求は最初の byte に
  connection を置く。
- 番号は core §9 の規則で振る（新しい connection のたびに 1〜255 を進める。閉じた番号は rejected no_connection）。
- connection は、**使っているもの**が 1 つでもある間は開いている。使っているもの:
  - attach した host のセッション（セッションごとに 1 つ）
  - connection を使う設定（`oep.probe.config` の bind）
- セッションの分は core §9 の寿命に従う: 明示の end では残り（次のセッションの attach がそのまま加わる）、lease の期限切れと
  force で奪われたときに外れる。
- 閉じるのは、使っているものが無くなったとき、force の detach、線が本当に切れたとき（インターフェースの文書が決める）だけ。
- connection に載っている資源（コンソールのストリームなど）は、connection が閉じたら閉じる（何を残すかはそのインター
  フェースが決める）。

## 3. 線と target の操作の status

使うもの: `oep.wire.*`、`oep.target.*`。

| 値 | 名前 | 意味 | host の判断の目安 |
|---:|---|---|---|
| 0 | ok | 最後まで進んだ | — |
| 1 | wait | target が「待て」を返し続けた（DMI の busy、SWD の WAIT）。probe の中の再試行を使い切った | 間を置いて続きから |
| 2 | line | 線の応答が無い、パリティの誤り | 速さを下げて attach し直す |
| 3 | fault | target が拒否した（DMI の op の失敗、SWD の FAULT、抽象コマンドの cmderr） | 原因を読んで消す |
| 4 | timeout | 待つ手順や run の上限に達した | 上限を見直す |
| 5 | state | 前提の状態でない（止まっていない hart に止まっている前提の操作など） | 状態を整えてから |

- 0x06〜0x3F は共通の値として予約、0x40〜0x7F はインターフェースが決める。知らない値は失敗として扱う。
- **失敗は completed で返す**（core §4.2）。何も進まなければ failed、途中まで進めば partial。payload の形は成功のときと同じで、
  `done`（進んだ手順・語の数）と `status` で分かる。書式の誤りは rejected malformed。
- 成功の形に done / status が無い op（scan、attach、attach_under_reset、detach）の失敗は、completed failed と payload
  `status(u8)` だけ。
