# OEP 標準インターフェース: 共通部品 v1

[English](oep-if-common.md)

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](versioning.ja.md) §6）。本体は [OEP core](oep-core.ja.md)。ここは、複数の標準インターフェースが同じ形で使う部品を
定める。部品は本体ではない。ある標準インターフェースがこの部品を使うと書いたときだけ、そのインターフェースに効く
（独自のインターフェースが同じ部品を使うのは自由）。番号の唯一の定義は `registry/oep-v1.toml`。

## 1. 位置つきのストリーム

使うもの: `oep.target.console`、`oep.fixture.uart`。キャプチャ（`oep.fixture.logic` / `oep.fixture.analog`）は位置を持つが、区画と世代を
持つ別の形で、この部品は使わない（[キャプチャ](oep-if-capture.ja.md) §2）。この部品を使うインターフェースは、read、marks、clear、mark、write を必須の op として持つ。

### 1.1 位置

- probe はストリームの各バイトに通し番号（**位置**、u64、一周しない）を振る。位置は probe の起動で 0 から始まり、**起動の間は
  戻らない**: ストリームが閉じて同じ場所に再び作られても（コンソールの再 open、fixture UART の plan のやり直し）、位置とマークの
  serial は続きから進む（古い host の read が新しいデータを黙って返さないため）。
- **読み出しはバッファを消費しない。** バイトが消えるのは次のときだけ:
  1. あふれ（古いものから押し出す。target や相手を待たせない）。
  2. host の明示の消去（clear）。
  3. probe の再起動（位置も 0 から。boot_id が変わる）。
- target のリセットでは捨てない（リセット直前の出力が最も見たいことが多い）。代わりにマークを付ける（§1.3）。
- 応答が失われても、同じ位置でもう一度読めば同じデータが返る。

### 1.2 read

```text
要求: [stream(u16)]、from(u8)、arg(u64)、max(u16)、[TLV]
応答: start(u64)、flags(u8: bit0 more、bit1 gap)、len(u16)、data、[TLV]
```

| from | 意味 |
|---:|---|
| 0 | 位置 arg から |
| 1 | 残っている一番古いバイトから |
| 2 | 今から（まだ何もない位置） |
| 3 | kind が arg の最後のマークの位置から（arg 0 はどの kind でも）。その kind のマークが残っていなければ今から（from 2 と同じ。一度も無い、またはマークのリングから押し出された） |

- `start` は data の先頭の位置。要求した位置がもう押し出されていれば start が先に進み、gap が立つ（差が失われた量）。
- 要求した位置（from 0）が書き込みの位置より先なら、応答は start = 書き込みの位置、len 0、flags 0。
- len は max 以下で、かつ max_frame の中で応答に収まる分以下。バイトが残っていれば `more` を立てる: この応答の後ろにまだ読めるバイトがあり、
  host はすぐ次を読んでよい。
- from 3 で arg > 0xFF は rejected malformed（マークの kind は u8）。
- 4 以上の from は rejected unsupported（payload `0x00`。後の revision が定めうる、core §2.5）。
- `max` = 0 は空の成功（len 0）。
- **read はロックなしで使える**（読んでも状態は変わらず、probe は読み手ごとの状態を持たない）。

### 1.3 マーク

```text
mark : serial(u32)、position(u64)、kind(u8)、time_ns(u64)、detail(u8)          22 byte
```

| kind | 名前 | 付ける契機 | detail |
|---:|---|---|---|
| 0x01 | reset | probe の指示で target をリセットした | 方法（`mark_detail_reset`: 1 ndmreset（reset の op）、3 attach の reset TLV。2 は予約） |
| 0x02 | restart | target の再起動を検出した | 検出元（`mark_detail_restart`: 1 havereset、2 コンソールの再同期） |
| 0x03 | attach | attach した（同じ場所の再 open を含む） | — |
| 0x04 | detach | detach した | — |
| 0x05 | lost | あふれで押し出した、または受信の誤り | 理由（`mark_detail_lost`: 1 あふれ、2 受信の誤り（framing）、3 パリティ、4 target の TO） |
| 0x06 | clear | host が消去した | — |
| 0x07 | host | host が付けた印 | host の値 |
| 0x08 | link-lost | 線が落ちた（コンソールの読みの中で判定） | — |
| 0x09 | closed | ストリームが閉じた | 理由（`mark_detail_closed`: 1 使っているものが全員外れた、2 lease 切れ / force、3 スロットの置き換え・削除、4 connection が閉じた） |

- kind の空間: 0x01〜0x3F 標準、0x40〜0x7F インターフェース固有。detail の値は registry（`common.enum.mark_detail_*`）。0x40 以降は
  インターフェース固有。
- `serial` はストリームごとのマークの通し番号（u32、一周する。core §2.6）。同じ位置に複数のマークが付いても、serial で
  落ちも重複もなく読める。
- `time_ns` は probe の時計（起動からの ns、u64、core §2.6a）。バイトごとの時刻は持たない。
- マークは本文とは別の小さなリングにためる。あふれたら古いものから捨てる。host は捨てられたマークを serial の飛びで知る:
  飛んだ数が押し出されたマークの数である。

```text
marks  要求: [stream(u16)]、from_serial(u32)
       応答: more(u8)、count(u8)、count × mark、[TLV]（core §2.3）
```

marks はロックなしで使える。

### 1.4 状態を変える操作

| 操作 | 要求 | 応答 | 意味 |
|---|---|---|---|
| clear | [stream(u16)] | — | 貯めたバイトを捨て、マーク clear を付ける |
| mark | [stream(u16)]、value(u8) | — | マーク host（detail = value）を付ける |
| write | [stream(u16)]、count(u16)、data | accepted(u16) | 相手への入力。`accepted` は方式（UART の送信、コンソールの mechanism）の送り枠に入れた分で、届いたことは意味しない。枠が空いていなければ accepted 0 = completed failed、0 < accepted < count = completed partial。count = 0 は malformed |

どれもロックが要る。

### 1.5 通知のデータ

ストリームを送り出すインターフェースは、core §11.2 のデータの形（`position, len, data, [TLV]`）を使う。`position` はこのフレームの
先頭の位置。前のフレームの終わりと合わなければ、その間は probe の中で押し出された。送ったデータを read で読み直せるかはインター
フェースが決める。

## 2. debug の connection

使うもの: `oep.wire.rvswd`、`oep.wire.swio`、`oep.wire.swd`（作る）、`oep.target.riscv-dm`、`oep.target.arm-adi`、
`oep.target.console`（使う）、`oep.probe.config` のスロット（使う）。

- **connection** は、線の attach が作る、ある target への接続。番号（u16）で指し、target の操作の要求は先頭に
  connection を置く。
- 番号（u16）は core §9 の規則で振る（probe で 1 つの空間、1 から進めて一周する、失敗した attach は消費しない。閉じた番号は
  rejected no_connection、別の種類の資源の番号は rejected unavailable cause 6）。
- connection は、**使っているもの**が 1 つでもある間は開いている。使っているもの:
  - attach した host のセッション（セッションごとに 1 つ）
  - スロット（`oep.probe.config` §1.1。probe の自動の attach と、bind が開いたコンソール）
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
- 成功の形に done / status が無い op（scan、attach、detach）の失敗は、completed failed と payload `status(u8)、[TLV]`（core §2.3:
  固定部分は (op, resolution, outcome) ごとに定める）。
- reset の線を使う op の失敗の status: 止まらない / 走らない = timeout、DM が応えない = line、cmderr = fault。
