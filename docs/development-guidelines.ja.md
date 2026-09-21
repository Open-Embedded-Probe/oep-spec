# Open Embedded Probe — 開発ガイドライン（作業版）

状態: **作業版**（2026-09-22 起草）。仕様ではなく、probe / client / 実験を並行して進めるための判断基準を集める。
実測（wch-protocols `experiments/LEDGER.ja.md`）と実装（oep-probe-arduino、oep-client-python）が進むたびに更新する。
決定に至ったものは各仕様文書へ移し、ここには「なぜそう決めたか」と「まだ決めていないこと」を残す。

## 1. 三層構造

OEP は次の三層で考える。下の層ほど汎用で変えにくく、上の層ほど probe 固有で自由度が高い。

| 層 | 内容 | 変更頻度 | 誰が実装するか |
|---|---|---|---|
| **共通 protocol（core）** | frame、request / response / event、correlation、chunked transfer、service の列挙と revision、capability の問い合わせ、lease / session、reject / failure の意味 | 低。互換性を守る | すべての probe と client |
| **共通 tool（standard service）** | 書込み / verify / reset、target memory、GPIO drive / sample、UART peer、logic capture の**丸めた**契約。MCU 名も pin 番号も出ない | 中。revision で拡張 | 対応する probe は同じ意味で実装する |
| **probe 独自 tool（vendor service）** | 特定 probe hardware / firmware を決め打ちにした高機能な契約。ESP32-P4 の I2C target v1 slot 規則、PARLIO 16 ch capture など | 高。probe の都合で変えてよい | その probe だけ |

共通 protocol の目標は「**低スペック probe（ATmega 級、UART 115200、RAM 数百 byte）から高スペック probe（P4、HS USB、
PSRAM）まで、同じ core が動く**」ことである。そのために core は次を守る。

- **最大 frame 長と in-flight 数は probe が宣言し、client が従う。** 低スペックは 64 byte・1 in-flight、P4 は 4 KiB・16 in-flight のように、
  同じ frame 形式で値だけ違う（数値は E155 で決める）。
- **core は payload の意味を知らない。** service id と operation id で routing し、中身は service の契約に委ねる。
- **未知の service / operation / TLV は副作用なく reject または無視できる。** client は reject を「非対応」として扱い、失敗と混同しない。
- **transport は差し替え可能。** USB-Serial/JTAG の byte stream、HS vendor bulk、UART、TCP のどれでも同じ frame を運ぶ。
  信頼性のない transport（UART）だけ CRC と再送を足す。
- **window は frame 数ではなく byte 数で宣言する。** E155（2026-09-22）で、ESP32-P4 の USB-Serial/JTAG は outstanding byte が
  device の ring（8 KiB）を超えると HWCDC がデータを落とした。USB 自体が無損失でも、probe の buffer を超えた分は保証されない。
  client は「probe が宣言した window byte 数」を超えて送らない。
- **往復の jitter は大きい前提で設計する。** 同経路の request 往復は min 0.36 ms、median 1.3 ms、p95 11.7 ms（usbipd/WSL）。
  stop-and-wait は使わず、pipelining を core の既定にする。帯域は 512 B frame × in-flight 4 で約 320 kB/s に飽和し、4 KiB frame でも上がらない。

## 2. 共通 tool と独自 tool の分岐点

同じ「I2C target」でも、Raspberry Pi Pico（PIO）と ESP32-P4（IDF slave v1）では受けられる transaction の形が違う。
両方を一つの capability 表で表そうとすると、宣言が複雑になりすぎて現実的でない。そこで**分岐の基準**を置く。

| 判定 | 共通 tool にする | 独自 tool にする |
|---|---|---|
| 契約を **MCU を知らずに**書けるか | 書ける（「N byte を書き込み verify する」「pin を HIGH にする」） | 書けない（「128 byte slot ごとに filler 1 byte」） |
| 差が **数値の上限**で表せるか | 表せる（最大 clock、最大長、channel 数） | 表せない（framing 方式、再 arm の可否、slot 規則） |
| client が **上限だけ見て**正しく使えるか | 使える | 使えない（手順を知る必要がある） |
| 2 実装以上で **同じ試験**が通るか | 通る（通った時点で共通へ昇格） | まだ 1 実装 |

**丸めた共通 tool と、決め打ちの独自 tool を同時に宣言してよい。** 例: P4 は共通 `i2c-target`（固定長 write を受ける、
最大 100 kHz、最大 32 byte）と、独自 `p4.i2c-target-v1`（framed-rx、preloaded-tx 129-byte slot、1 MHz）を両方出す。
一般 client は前者、P4 を知る client は後者を選ぶ。**両者は同じ pin / peripheral を使うので排他 resource として宣言する。**

昇格の流れ: 独自 tool として実装・実測 → 2 実装目が同じ試験を通る → 共通 tool の revision として取り込む。
**最初から共通 tool に入れる範囲は、書込み / verify / reset / memory / GPIO / UART peer の「今すでに 2 実装で動くもの」だけ**にする。
I2C / SPI の target 側、logic capture の高速 tier、ADC source は当面独自 tool から始める。

## 3. 機能の公開単位

### 3.1 個別か、グループか

| 公開単位 | 向く場面 | 向かない場面 |
|---|---|---|
| **個別機能**（1 service = 1 用途、例: `gpio`、`uart-peer`、`target-flash`） | 単体で使う。client が最小の知識で使える。低スペック probe が一部だけ実装できる | 同時に動かすとき、開始タイミングが揃わない |
| **グループ**（1 service に複数 role、capability で出し分け、例: `i2c-target` に fixed-rx / framed-rx / preloaded-tx） | 同じ peripheral を共有する派生。排他を service 内で扱える | mode ごとに契約が違いすぎると capability が肥大する |

指針:

1. **service は「単体で意味が閉じる最小単位」で切る。** 一つの service を使うのに別 service の状態を知る必要があってはならない。
2. **同じ peripheral の派生 mode は一つの service のグループにし、mode を capability で列挙する。** mode ごとの上限は数値で、
   手順の違いは mode 名で表す。手順が別物になったら独自 tool に分ける。
3. **同時利用は「plan」で一括指定する。** 複数 service を同時に構成・開始するとき、client は plan（role → channel の割当と開始条件）を
   1 request で送り、probe は全部受理できるときだけ原子的に適用する。一部だけ有効にすることは禁止（[project-requirements](project-requirements.ja.md) OEP-REQ-011）。
   これが「単体は個別で楽、同時は一括でないとタイミングがずれる」の両立である。
4. **開始タイミングが揃う必要がある組（capture と刺激、UART peer と target reset）は plan に「同時開始」を書ける。**
   probe は同時開始できる組合せを capability で宣言する（できなければ plan を reject）。

### 3.2 lifecycle は全 service で同じ

`configure(plan) → enable/start → status / read → disable/stop → release`。どの service もこの順で、
`disable` / host 切断 / watchdog で pin を input へ戻し peripheral を止める。status は設定値・実効値・error・overflow・timestamp を返し、
client が log を解析して成否を判定する設計にしない。

## 4. capability の表し方

- capability は **probe 自身の channel と group と上限**だけを返す。接続先 DUT の pin 名・board 名は返さない（host の manifest の仕事）。
- 上限は数値（max clock、max length、max in-flight、resolution）。**方式の違いは mode 名**。mode 名が増えすぎたら独自 tool へ。
- **排他 resource は明示する**（同じ peripheral、同じ pin、同じ DMA）。client は排他を見て plan を組む。
- 実測していない上限は宣言しない。「動くはず」の値を capability に書かない（wch-protocols README §6）。
- **TLV か固定 struct か**: core の discovery は TLV（未知 tag を飛ばせる）。service 内の request / response は revision 付きの固定 struct でよい。
  数値の registry（service id、mode id、TLV tag）は一つの YAML に置き、C++ / Python の codec と test vector を生成する。

## 5. 低スペックから高スペックまで

| | 低スペック（例: ATmega328P、UART） | 中（ESP32-S3、USB FS CDC） | 高（ESP32-P4、HS USB） |
|---|---|---|---|
| frame 上限 | 64 byte | 512 byte | 512 byte〜1 KiB（E155: 4 KiB にしても帯域は上がらない） |
| window（outstanding byte） | 64 byte（= 1 frame） | 2 KiB | 4 KiB（ring 8 KiB の半分。E155） |
| CRC / 再送 | 必須 | transport 次第 | 不要（USB が保証） |
| service | 書込み + UART peer だけでよい | + GPIO / capture 低速 tier | + 独自 tool 群 |
| capability | 最小 TLV 数個 | | paged / chunked |

client は confirmation で上限を受け取り、それ以上を送らない。低スペック probe に高スペック向け request が来たら reject（非対応）で返す。

## 6. 実装と実験の進め方

1. **実験が先、宣言は後。** 数値は wch-protocols の実験で取り、README と台帳に残してから capability / 仕様へ写す。
2. **使う前に転送する。** pytest で build → upload → 試験を 1 セットにし、`sketch.yaml` で版を pin する。
3. **共通 tool の受入試験は 2 実装で回す。** P4 と、もう一つ（S3 または Pico）。1 実装しか無いものは独自 tool のまま。
4. **速度は後、拡張性は先。** 速度改善は task list に載せ、実験時間を圧迫するものだけ予備実験で先に潰す。
5. **wire に MCU 固有の値を漏らさない。** pin 番号、peripheral 番号、IDF の enum は probe の内側で閉じる。

## 7. まだ決めていないこと

- frame の具体形式（length16 + seq + type + payload + CRC の候補。上限は E155 から 512 B〜1 KiB、window 4 KiB byte で起草する）。
- service id / mode id / TLV tag の番号空間と private namespace の encoding。
- event（非同期通知）を core に入れるか、status polling だけにするか。低スペックでは polling のみで足りる可能性。
- plan の「同時開始」の精度をどう宣言するか（µs 単位の同時か、順序保証だけか）。
- 共通 tool の最初の一覧。書込み / verify / reset / memory / GPIO / UART peer を候補にしているが、2 実装目が無い。
