# Open Embedded Probe — core wire model v0 draft

状態: **作業版 draft**（2026-09-22）。これは実装して実測するための最初の具体案であり、正式な wire format ではない。
既存の検討（[共通message model候補](message-model-candidates.ja.md) 候補 C、[Message header構成比較](message-header-layout-comparison.ja.md) 候補 B、
[Request correlation](request-correlation-lifecycle.ja.md) 16 bit、[Requestの受理と完了](request-completion-semantics.ja.md)）を前提にし、
数値は [E153](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/experiments/e153_p4_x035_rvswd_dedic_ceiling/README.ja.md)・
[E155](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/experiments/e155_p4_usb_jtag_roundtrip/README.ja.md) から取る。
方針は [開発ガイドライン](development-guidelines.ja.md)。

v0 で決めること: frame、message role、header、resolution、window、service の識別、plan/lease の共通操作、未知の扱い。
v0 で決めないこと: event/notification の必須化、activity の再接続、複数 host、認証。

## 1. 層

```text
service payload   (service definition が意味を決める。registry から codegen)
message           (role 別 header + payload。transport を知らない)
frame             (transport binding。USB: length prefix / UART: COBS + CRC16)
transport         (USB-Serial/JTAG, USB vendor bulk, UART, TCP ...)
```

## 2. Frame（transport binding）

### 2.1 信頼性のある byte stream（USB CDC、USB-Serial/JTAG、TCP）

```text
+--------+--------+---------------------+
| len lo | len hi | message (len byte)  |
+--------+--------+---------------------+
```

- `len` は message 長（header + payload）。0 は予約（keepalive / 同期用に将来使う）。
- CRC なし。USB / TCP は byte の完全性を保証する。**ただし probe の buffer を超えた分は保証されない**（E155）ので、§4 の window を守る。
- 同期を失った場合（長さが `max_frame` を超える、応答が来ない）は client が connection を作り直す。v0 では resync 手順を frame に持たせない。

### 2.2 信頼性のない byte stream（UART）

[UART frame layout比較](uart-frame-layout-comparison.ja.md) の暫定判断どおり COBS + CRC-16 を使い、`0x00` delimiter で区切る。message 部は 2.1 と同じ。
再送・ACK は [UART bindingの信頼性model](uart-reliability-model.ja.md) の候補に従い、v0 実装では stop-and-wait のみ対応する。

### 2.3 packet transport（USB vendor bulk、HID）

1 transfer = 1 message。length prefix は不要だが、client 側 API を揃えるため 2.1 と同じ `len` を先頭に置いてよい。Phase B で決める。

## 3. Message

### 3.1 共通 1 byte: role

| role | 値 | 方向 | 説明 |
|---|---:|---|---|
| request | 0x01 | host → probe | 評価または操作を求める |
| result | 0x02 | probe → host | request への唯一の応答。resolution を持つ |
| activity update | 0x03 | probe → host | accepted 後の進捗（v0 では任意） |
| activity outcome | 0x04 | probe → host | accepted 後の最終結果 |
| notification | 0x05 | probe → host | request に対応しない変化（v0 では送らなくてよい） |
| data | 0x06 | 双方向 | activity / flow に属する data 単位（Phase B で使う） |

未知 role は payload を解釈せず破棄し、診断 counter を増やす（result を返さない）。

### 3.2 request

```text
role=0x01 | corr lo | corr hi | fn lo | fn hi | op | payload...
```

- `corr`: 16 bit、host が割り当てる。同じ connection の未解決 request 間で重複させない。0x0000 は使わない。
- `fn`: **offered function reference**（instance id、16 bit）。0x0000 は core（endpoint 自身）。
- `op`: `fn` が参照する definition の中で解釈する operation。
- payload: definition が定める。長さは `len - 6`。

### 3.3 result

```text
role=0x02 | corr lo | corr hi | resolution | detail | payload...
```

| resolution | 値 | detail | payload |
|---|---:|---|---|
| rejected | 0x00 | reject reason（§3.4） | 任意の補助情報（受理可能な条件など。definition が定める） |
| completed | 0x01 | outcome（0 = success、1 = failed、2 = partial） | definition が定める result data / failure detail |
| accepted | 0x02 | 0 | activity reference（16 bit）+ definition が定める初期情報 |

result は request と同じ connection へ、`corr` を返す。target（`fn`, `op`）は echo しない。requester は pending 記録から復元する（correlation lifecycle の方向どおり）。

### 3.4 reject reason（共通）

| 値 | 意味 |
|---:|---|
| 0x01 | unknown function reference |
| 0x02 | unknown operation |
| 0x03 | malformed payload（長さ・値域） |
| 0x04 | unavailable（resource / lease / 現在状態） |
| 0x05 | busy（同時処理上限。client は後で再送してよい） |
| 0x06 | window exceeded（§4 違反。connection を作り直す） |
| 0x10〜 | definition 固有（definition が定める） |

reject は機能操作を開始していないことを意味する。開始後の失敗は completed + failed。

### 3.5 activity（accepted の後）

```text
update  : role=0x03 | act lo | act hi | kind | payload...
outcome : role=0x04 | act lo | act hi | outcome | payload...
```

activity reference は probe が割り当て、同じ connection 内で terminal + retire 前に再利用しない。v0 の probe は accepted を返さなくてよい（すべて rejected / completed）。
返す probe は、`stop`（core op、§6）に対応する。

### 3.6 data

```text
role=0x06 | act lo | act hi | kind | seq lo | seq hi | payload...
```

capture streaming 用。v0 の flash / memory は data role を使わず、§4 の pipelining で足りる（E155: 512 B × in-flight 4 で帯域飽和）。

## 4. Pipelining と window

endpoint confirmation（§6 op 0x01）で probe は次を返す。

| field | 意味 | P4 USB-Serial/JTAG の実測からの初期値 |
|---|---|---|
| `max_frame` | 受理する最大 message 長（byte） | 1024 |
| `window_bytes` | 未解決 request の合計 message 長の上限 | 4096（ring 8 KiB の半分） |
| `max_inflight` | 未解決 request 数の上限 | 8 |

- client は `Σ(未解決 request の len) ≤ window_bytes` かつ `未解決数 ≤ max_inflight` を守る。超えた request は probe が 0x06 で reject してよいが、
  buffer 超過で frame が失われた場合は reject すら返らない。**守るのは client の責任**。
- probe は request を受信順に処理し、result を受信順に返す（v0: in-order）。out-of-order は将来の拡張で、correlation があるので frame 形式は変わらない。
- 低スペック probe は `max_frame=64, window_bytes=64, max_inflight=1` を返せばよい。client 側の code は同じ。

## 5. Service の識別

### 5.1 definition と instance

- **function definition**: `owner`(16 bit) + `id`(16 bit) + `revision`(8 bit)。`owner=0x0000` は OEP 標準。それ以外は vendor / probe 固有（独自 tool）。
- **offered function**: probe が今提供している instance。`fn` reference（16 bit）と、参照する definition を list で返す。同じ definition の複数 instance（UART peer 2 本など）は別 `fn`。

client は list を読み、理解できる definition の instance だけを使う。未知 definition の instance は無視する（他の instance は使える）。

### 5.2 revision

- 同じ `owner:id` の revision 違いは**後方互換の追加**だけ。request の payload に optional TLV を足す、result に末尾 field を足す。
- 互換を壊す変更は新しい `id`。client は revision が自分より新しい definition を、知っている範囲で使ってよい。

### 5.3 v0 の標準 definition（候補）

| owner:id | 名前 | 内容 | 由来 |
|---|---|---|---|
| 0:0x0000 | core | confirmation、list、describe、stop、lease | §6 |
| 0:0x0001 | probe.identity | probe 個体・firmware・profile | 現 ProbeInfo |
| 0:0x0002 | probe.capabilities | channel / group / role / voltage の paged TLV | 現 revision 2 を TLV 化 |
| 0:0x0010 | target.control | attach / halt / reset / status | 現 TargetControl |
| 0:0x0011 | target.memory | read / write N byte（`max_frame` 内） | 現 TargetMemory を可変長に |
| 0:0x0012 | target.flash | geometry 取得、physical page program、erase、verify hash | 現 TargetFlash の 64/256 混在を廃止 |
| 0:0x0020 | fixture.gpio | configure / read bank / drive | 現 FixtureGpio |
| 0:0x0021 | fixture.uart | configure / write / read | 現 FixtureUart |
| 0:0x0022 | fixture.capture | RMT / PARLIO の raw capture 低速 tier | 現 FixtureCapture |
| 0:0x0023 | fixture.i2c-target | 固定長 write を受ける丸めた target（上限は数値） | 共通化できる最小部分 |
| vendor:… | p4.i2c-target-v1 | fixed-rx / framed-rx / preloaded-tx（129 B slot）、1 MHz | E147〜E150。独自 tool |

数値は registry（§8）で確定するまで仮。

## 6. core（fn=0x0000）の operation

| op | 名前 | request payload | result payload |
|---:|---|---|---|
| 0x01 | confirm | `"OEP?"`, min_rev, max_rev | `"OEP!"`, rev, max_frame(16), window_bytes(16), max_inflight(8), flags(8) |
| 0x02 | list | first index(8) | count(8), [fn(16), owner(16), id(16), revision(8), flags(8)] × n（`max_frame` に収まる分。続きは index 指定） |
| 0x03 | describe | fn(16), first tag index(8) | TLV 列（instance 固有の constraint。channel 候補、上限、排他 group） |
| 0x04 | plan apply | plan TLV（role → channel 割当、開始条件） | lease id(16)、effective TLV |
| 0x05 | plan release | lease id(16) | — |
| 0x06 | stop | activity ref(16) | — |
| 0x07 | ping | 任意 | echo |

- **plan は原子的**: 全 role を受理できるときだけ適用し、一部だけ有効にしない。既存 lease と競合する role は 0x04 unavailable で reject。
- lease は connection に属する。connection 喪失・watchdog で probe が全 lease を解放し、pin を input へ戻す。
- 「同時開始」が要る組は plan に `start-together` TLV を含める。probe は describe でその可否を宣言し、不可なら reject。

## 7. TLV

describe / plan / capabilities の可変情報は TLV で運ぶ。

```text
tag(8) | len(8) | value(len)
```

- tag の bit7 = critical。critical な未知 tag を含む対象は使わない。非 critical な未知 tag は飛ばす。
- 同じ tag の繰返しは list を表す。
- tag 空間は definition ごと（owner:id の中で解釈）。core の tag は registry で定義。

## 8. Registry と codegen（S2 への入力）

`registry/` に YAML を置き、次を生成する。

- C++: definition / op / reject reason / TLV tag の定数、request/result の pack・unpack、dispatcher の table。
- Python: 同じ定数と codec、CLI の引数。
- test vector: 各 message の byte 列と期待 decode（両実装で同じ結果になること）。

手書きの if-chain を二重に持たない。wire に現れる数値は必ず registry から出る。

## 9. 未知と失敗の扱い（まとめ）

| 受信 | 処理 |
|---|---|
| 未知 role | 破棄、counter |
| 未知 fn | rejected 0x01 |
| 既知 fn の未知 op | rejected 0x02 |
| 長さ・値域違反 | rejected 0x03 |
| 未知 corr の result（client 側） | 破棄、診断。別 request へ適用しない |
| timeout | resolution とみなさない。再送は operation の idempotency を見て client が判断 |
| window 超過 | rejected 0x06 か frame 喪失。client は connection を作り直す |

## 10. 低スペック profile との対応

| | 最小 | P4 |
|---|---|---|
| frame | COBS + CRC16、64 byte | length prefix、1024 byte |
| window | 64 / 1 in-flight | 4096 / 8 in-flight |
| role | request / result のみ | + activity / data（必要な service だけ） |
| core op | confirm, list, describe, ping | 全部 |
| service | target.flash + fixture.uart 程度 | 全部 + 独自 tool |

同じ client library が両方を扱う。差は confirmation の数値と list の内容だけ。

## 11. 実装で確かめること（次の実験）

1. registry から生成した codec の test vector が C++ / Python で一致する（常設 v0、実機なし）。
2. P4 上で v0 core + target.memory を実装し、62 KiB read を `max_frame=1024, window=4096` で測る。E153（DMI 10 µs）と E155（320 kB/s）から 0.5 s 前後を見込む。
3. window を故意に超えたときの挙動（reject が返るか、frame が失われるか）。
4. 低スペック側の 2 実装目（S3 または Pico）で confirm / list / describe が通る。
