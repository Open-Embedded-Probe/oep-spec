# OEP v1 をはじめる: 最初の probe と最初の host

[English](getting-started.md)

状態: **ガイド**（規範ではない）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。規則は足さない。どの段も規範の文を指し、このガイドと規範が食い違えば規範が正しい。

OEP を初めて見る人のためのページ。**confirm**、**list**、**describe** に答えるいちばん小さい probe と、probe を見つけて confirm し、
describe を読むいちばん小さい host を、線の上のすべてのバイトと一緒に作る。これはまだ適合する実装ではない: 次に足すものは §6、
全体のチェックリストは [適合](conformance.ja.md)。

開いておくもの: [OEP core](oep-core.ja.md)（規則）、`registry/oep-v1.toml`（すべての数。`generated/oep-v1/` に C++、Python、JS の形が
ある）、[`tests/vectors/`](../tests/vectors/)（確かめに使うバイト列）。

## 1. 部品を 1 ページで

- **バイトの順**: 数はすべてリトルエンディアン（core §2.1）。
- **シリアルの口のフレーム**（UART bridge、USB CDC、内蔵の USB シリアル）: `0x00 COBS(message + CRC-16) 0x00`。CRC-16/CCITT-FALSE
  （多項式 0x1021、初期値 0xFFFF、反転なし。"123456789" → 0x29B1）をリトルエンディアンで付け、254 byte の区切りの COBS にする
  （transports §1）。vendor bulk と TCP のフレームは `length(u16) message` で、CRC は無い。
- **要求**: `role(0x01) corr(u16) fn(u16) op(u8) session_id(u32) payload`（見出し 10 byte）。session_id 0 はセッション無しを表す。
  セッションの要求はその id を持つ（core §4.1）。
- **応答**: `role(0x02) corr(u16) resolution(u8) detail(u8) payload`（見出し 5 byte）。resolution 0x01 completed なら detail は outcome
  （0 success）、0x00 rejected なら detail は断りの理由（core §4.2、§4.3）。
- **TLV**: `tag(u8) len(u16) value`。長さによらず形は一つ（core §2.2）。
- **fn 0** は `oep.core`。op は confirm 0x01、list 0x02、describe 0x03（core §12）。

## 2. 例

probe 1 台、経路 1 つ: UART bridge（transport の kind 1、index 0）を起動時の速さ `uart_bridge_boot_baud`、115200 8N1 で（transports §4）。
probe の値（`tests/vectors/confirm.json` と `discovery.json` のもの）:

| 値 | 例 | どこ |
|---|---|---|
| max_frame、window、max_inflight | 1024、4096、4 | confirm、core §4.4 |
| boot_id | 0x12345678（起動のたびに新しい乱数） | confirm、core §6.5 |
| unit_id | `a1b2c3d4` | describe 0x42、core §7.5 |
| transport | index 0、kind 1（UART bridge）、interface 0xFF（USB でない） | describe 0x49、confirm の TLV 0x01 |
| discoverable | 0（probe はプロジェクトの USB の VID:PID で列挙しない） | describe 0x4A、core §7.5 |
| max_op_ms | 1000 | describe 0x4D |

host は要求に corr 1、2、3 と順に番号を付ける（core §4.1）。

## 3. バイト列

ここのメッセージはすべてテストベクタで、名前を各節に書く: confirm は `tests/vectors/confirm.json`（フレームは `cobs.json`）、list、
describe と断りは `tests/vectors/discovery.json`。`tools/oepvectors1.py` が本文から計算し、`tests/vectors/test_vectors.py` が別に書いた
COBS と CRC-16（`binascii.crc_hqx`）で確かめる。空白は読むためだけ。

### 3.1 confirm（core §7.1）

ベクタ: `confirm.json` の "revision 1 asked and answered"。要求: `"OEP?" min_rev max_rev` = revision 1〜1。

```text
message      01 0100 0000 01 00000000 | 4f 45 50 3f 01 01
               role corr fn op session_id | "OEP?" min_rev max_rev
serial frame 00 03 01 01 01 01 02 01 01 01 01 09 4f 45 50 3f 01 01 08 96 00      （CRC-16 0x9608 → 08 96）
length frame 10 00 01 01 00 00 00 01 00 00 00 00 4f 45 50 3f 01 01
```

応答: `"OEP!" revision flags max_frame(u16) window(u32) max_inflight(u8) boot_id(u32)`、続いて TLV 0x01 transport（confirm が来た経路の
index。いつも付く）。

```text
message      02 0100 01 00 | 4f 45 50 21 | 01 | 00 | 0004 | 00100000 | 04 | 78563412 | 01 01 00 00
               role corr completed success | "OEP!" | rev 1 | flags | max_frame 1024 | window 4096 | max_inflight 4 | boot_id | TLV transport = 0
serial frame 00 03 02 01 02 01 06 4f 45 50 21 01 01 02 04 02 10 01 08 04 78 56 34 12 01 01 01 03 ab a4 00
```

範囲の中に扱える revision が無いとき（ここでは host が 2〜3 を求める）、probe は unsupported で断り、payload は tag 0x00 と、続く
TLV 0x01 supported =（min 1、max 1）（`confirm.json` の "no revision in the range: unsupported with the supported range"）:

```text
request      01 0200 0000 01 00000000 | 4f 45 50 3f 02 03
answer       02 0200 00 0b | 00 | 01 02 00 01 01
               rejected unsupported | tag 0x00 | TLV supported: min 1、max 1
```

### 3.2 list（core §7.2）

ベクタ: `discovery.json` の "list everything from the first"。要求: `flags(u8) first(u16) prefix_len(u8) prefix` = 最初から
すべての名前。

```text
message      01 0200 0000 02 00000000 | 00 | 0000 | 00
serial frame 00 03 01 02 01 01 02 02 01 01 01 01 01 01 01 03 aa 9e 00
```

応答: `total(u16) count(u8)`、続いて項を前に長さを置かずに並べる: `fn(u16) instance(u16) revision(u8) flags(u8)
name_len(u8) name`（core §2.3）。いちばん小さい probe には `oep.core`（fn 0、instance 0、revision 1）しか無い。list はそれをいつも最初の項として数える。

```text
message      02 0200 01 00 | 0100 | 01 | 0000 | 0000 | 01 | 00 | 08 | 6f 65 70 2e 63 6f 72 65
               completed success | total 1 | count 1 | fn 0 | instance 0 | rev 1 | flags | name_len 8 | "oep.core"
serial frame 00 03 02 02 02 01 02 01 02 01 01 01 01 02 01 0c 08 6f 65 70 2e 63 6f 72 65 cb 70 00
```

### 3.3 describe（core §7.3、§7.5）

ベクタ: `discovery.json` の "describe fn 0 from the first"。要求: `fn(u16) first(u16)` = fn 0 の最初の TLV から。describe の
要求には TLV を付けない。

```text
message      01 0300 0000 03 00000000 | 0000 | 0000
serial frame 00 03 01 03 01 01 02 03 01 01 01 01 01 01 01 03 ea 30 00
```

応答: `more(u8)`、続いて宣言の TLV。fn 0 でどの probe も出す 5 つ: ops（この fn が持つ op を base 0x01 と bitmap で示す、
core §7.4。ここでは core §1.2 が fn 0 に求める 9 つ: confirm、list、describe、open、end、keepalive、lock_state、subscribe、unsubscribe。
この probe は plan の role を持たないので plan_apply と plan_release は無い）、unit_id、transport（経路ごとに 1 つ）、max_op_ms（core §1.2）と discoverable（core §7.5。UART bridge は
プロジェクトの USB の VID:PID で列挙しないので、ここでは 0）。

```text
message      02 0300 01 00 | 00 | 09 0800 01 07 80 07 00 00 80 02 | 42 0800 61 31 62 32 63 33 64 34 | 49 0300 00 01 ff | 4a 0100 00 | 4d 0400 e8 03 00 00
               completed success | more 0 | ops 01-03 10-13 30 32 | unit_id "a1b2c3d4" | transport: index 0、kind 1、interface 0xFF | discoverable 0 | max_op_ms 1000
serial frame 00 03 02 03 02 01 01 03 09 08 05 01 07 80 07 01 05 80 02 42 08 0b 61 31 62 32 63 33 64 34 49 03 01 05 01 ff 4a 01 01 03 4d 04 03 e8 03 01 03 c3 c2 00
```

`first` が TLV の数（ここでは 5）以上の describe には、more 0 で TLV 無しで答える（core §7.3。`discovery.json` の
"describe fn 0 from beyond the last: more 0 and no TLVs"）:

```text
request      01 0400 0000 03 00000000 | 0000 | 0500
answer       02 0400 01 00 | 00
```

### 3.4 ほかはすべて断る

いちばん小さい probe は、ほかの要求を core §4.3 の順で最初に当たる理由で断る: 持たない fn は unknown_function、fn 0 に無い op は
unknown_operation。ここでは断りの応答に payload は無い（`discovery.json` の "refusals"）。

```text
request fn 7 op 1      01 0500 0700 01 00000000     answer 02 0500 00 01    rejected unknown_function
request fn 0 op 0x50   01 0600 0000 50 00000000     answer 02 0600 00 02    rejected unknown_operation
```

ほかの断りの正確なバイト列は `tests/vectors/refusals.json`。

## 4. 最初の probe

probe がすることを順に（参照の先が規則）:

1. **フレームを受ける。** 0x00 から次の 0x00 までのバイトをため、COBS を解き、CRC-16 を確かめる。解けない候補と CRC の合わない候補は
   要求ではない（シリアルの口では生のバイト、transports §4）。フレームの途中で `probe_frame_gap_ms`（200 ms）途切れたら読み直す（transports §2）。
   confirm の前でも、少なくとも `min_max_frame`（64）byte のメッセージを受ける（transports §3）。
2. **見出しを読む。** role 0x01 で 10 byte 以上（ほかのメッセージは捨てる、core §2.4）。これらはロック不要の要求なので session_id は 0。core §4.3 の順に、fn（unknown_function）、op
   （unknown_operation）、固定部分の長さ（malformed）を見る。
3. **confirm**（payload は `OEP?` min_rev max_rev）: `min_rev > max_rev` は malformed。1 が [min_rev, max_rev] にあれば §3.1 のとおり答え、
   無ければ §3.1 のとおり断る。どの confirm の応答にも transport の TLV を付ける。flags は 0。
4. **list**: 名前をラベルの境で照らし（`oep` は `oep.core` に合う。空の prefix はすべてに合う）、`first` から 1 つのフレームに入るだけ
   項を入れる。total は合うものの総数。flags の bit 1〜7 が立った要求は unsupported（core §7.2）。
5. **describe**: fn 0 なら `first` からの TLV（少なくとも ops、unit_id、transport、discoverable、max_op_ms。§3.3）を返す。入りきらなければ
   more = 1。`first` が数以上なら more 0 で TLV なし。要求に TLV があれば malformed。boot_id が同じ間、値は変わらない（core §7.3）。
   ops には、答える op だけを立てる（core §1.2）。この段の probe は confirm、list、describe の 3 つ（`01 07`: base 0x01、bitmap 0x07）
   で、§6 で op を足すごとにビットを立てる。§3.3 のバイト列は、§6 の 1 と 4 を終えて fn 0 の必須の op をすべて持つ probe のもの。
6. **答える**: 同じ corr で、要求が来た経路に、来た順に、要求 1 つに応答 1 つ（core §4.2、§4.4）。シリアルの口では `0x00 COBS 0x00`。
7. **boot_id**: 起動時に乱数から選ぶ（core §6.5）。**unit_id**: 小文字、変わらない、一意（probe ガイド §10）。

参照のライブラリの [MinimalProbe の例](https://github.com/Open-Embedded-Probe/oep-probe-arduino/tree/main/examples/01.Basics/MinimalProbe) と
案内 [writing a probe](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/docs/guide/writing-a-probe.ja.md) に、そのライブラリで
作った probe の全体がある。

## 5. 最初の host

1. **口を開く**: 排他で（Linux は TIOCEXCL）、UART bridge なら 115200 8N1、DTR と RTS を立てて（transports §3、§4、host ガイド §1）。
2. **confirm を送る**: 1 回の書き込みで、前後を 0x00 で囲む（transports §1、§2）。見分けていない口に送るのはこれだけ（探りの規則、
   transports §3）。64 byte に収まる。
3. **待つ**: 少なくとも `host_wait_add_ms`（1000 ms）+ 転送の時間（core §4.4）。UART bridge かもしれないシリアルの口では、転送の時間は
   (L + max_frame × (1 + `notify_pending_max_frames`)) × 10 / baud 秒。L は線の上の要求のフレームの長さ（ここでは 21 byte）。confirm の
   応答の前には host は max_frame を知らない。参照の client は `min_max_frame`（64）で数える: (21 + 64 × 3) × 10 / 115200 ≈ 18 ms。長く
   待つのはいつでもよい。
4. **受ける**: 0x00 の間の候補をすべて解く。口を開いてから最初の 0x00 までのバイトも解く。解けない、CRC が合わない、role を知らない、
   待っていない corr の候補は雑音として捨てる（transports §1、core §11.1）。
5. **応答を確かめる**: completed、同じ corr、payload が `OEP!` で始まる（transports §3）。来なければ同じ corr で 1 回だけ送り直し
   （`resend_max`）、それでも来なければ口を閉じ、ほかに何も送らない（transports §3、core §5.2）。max_frame、window、max_inflight、boot_id、
   transport の index を取っておく。以後 max_frame より長いメッセージは送らない（transports §3）。
6. **list**: `first` 0 から、受けた項の数を `first` に足しながら `total` まで読む。名前 → fn の対応は boot_id が同じ間覚えてよい
   （core §7.2）。
7. **fn 0 を describe**: `first` 0 から。more = 1 の間、受けた TLV の数を `first` に足して聞き直す。知らない tag は読み飛ばす
   （core §2.3）。unit_id（ASCII の大文字と小文字を区別せずに比べる。`x-` の unit_id でまとめない）、経路、max_op_ms を読む。boot_id で
   cache する（core §7.3、§7.5）。
8. **次**: 何かを変えるにはセッションを開き（core §6）、インターフェースをその fn で使う。終わったら `end` を送る。

host はまず fake の probe に当てて試す（host ガイド §16）:

```sh
python -m oep_client.fake_serve --pty      # 開く pty を出す。いくつものインターフェースを持つ probe を出す
oep dump --port /dev/pts/N                 # すべてのインターフェースの list と describe。自分の host と見比べる
```

## 6. 次に足すもの

confirm、list、describe にしか答えない probe は、まだ OEP の probe ではない。多くの実装が足す順に:

**probe**（[適合](conformance.ja.md) §1）:

1. セッション: open、end、keepalive、lock_state と、lease、core §6.2 の判断の表。session_id の確かめ（session_required、no_session、
   locked）。end、lease の期限切れ、force のどれでも、セッションが作ったものを解放する（core §9）。
2. core §5.2 の送り直しの表（少なくとも max_inflight 個、断りの応答も含め、成功した open のたびに捨てる）。
3. core §4.3 の断り方の順のすべてと、core §2.3 の TLV の規則（critical、ignored、繰り返し、短い TLV と長すぎる TLV）。
4. subscribe / unsubscribe と fn 0 のハートビート（core §11）。
5. plan の role を持つインターフェースがあれば plan_apply / plan_release（core §8）と、欲しいインターフェース（[適合](conformance.ja.md) §3）。
6. 任意: `oep.link`（線の試験と、UART bridge の port_speed。[リンク](oep-if-link.ja.md)）、probe の設定（[probe の設定](oep-if-probe-config.ja.md)）、ほかの経路。

**host**（[適合](conformance.ja.md) §2）:

1. corr の振り方と 1 回の送り直し（core §4.1、§5.2）。長さつきの口での同期のし直し（transports §5）。
2. セッション: 乱数の session_id、open の応答の lease、keepalive、断りごとにすること（host ガイド §9）。
3. revision と知らない値（core §2.4、§2.7、host ガイド §10）。購読するなら通知（host ガイド §12）。
4. USB の probe の発見と複数の経路（transports §3、host ガイド §4、§5）。

それから [適合](conformance.ja.md) §4 で確かめる: 試験ベクトル、fake の probe、本物の probe への `oep dump`。

## 7. 次に読むもの

- [host 開発ガイド](host-development-guide.ja.md)、[probe 開発ガイド](probe-development-guide.ja.md): 実務と罠。
- [用語集](glossary.ja.md): 仕様が定めるすべての用語。
- [安全とセキュリティ](security.ja.md): 出荷の前に気をつけること。
- [版と安定性](versioning.ja.md): 凍結の後に何が変わらないか。
