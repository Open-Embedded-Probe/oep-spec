# OEP 標準インターフェース: fixture v1

状態: **規範**（2026-09-26）。本体は [OEP core](oep-core.ja.md)、共通部品は [共通部品](oep-if-common.ja.md)（§1 位置つきの
ストリーム）。番号の唯一の定義は `registry/oep-v1.toml`。キャプチャは [キャプチャ](oep-if-capture.ja.md)。

| 名前 | revision | 役割 | plan の role |
|---|---:|---|---|
| `oep.fixture.gpio` | 1 | ピンを駆動し、読む | 1 = 線 |
| `oep.fixture.uart` | 1 | UART の送受信 | 1 = RX、2 = TX |
| `oep.fixture.i2c-target` | 1 | I2C の target（被制御側）。DUT の I2C controller を試す | 1 = SDA、2 = SCL |
| `oep.fixture.spi-target` | 1 | SPI の target。DUT の SPI controller を試す | 1 = SCK、2 = MOSI、3 = MISO、4 = CS |

どれも plan（core §8）で割り当てたチャンネルだけを扱う。

## 1. `oep.fixture.gpio`

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | set | n(u8)、n × (channel(u16)、mode(u8)) | — | 必要 |
| 0x02 | read | n(u8)、n × channel(u16) | n × level(u8: 0 / 1) | 不要 |

| mode | 意味 |
|---:|---|
| 0 | 入力（浮き） |
| 1 | 入力、プルアップ |
| 2 | 入力、プルダウン |
| 3 | 出力 low |
| 4 | 出力 high |
| 5 | オープンドレイン low（引く） |
| 6 | オープンドレインの解放（外部または target のプルアップで high） |
| 7 | 入力、プルアップとプルダウンを両方（弱い中間の電圧。何もつながっていない線の、目安の電圧の基準） |

- 並びは要求の順に 1 つずつ行う（NRST を引いてから離す、などを 1 要求で送れる）。
- 割り当てていないチャンネルや扱えない mode があれば、何もせず rejected unavailable。payload は core §4.3 の TLV の並びで、
  channel（0x02）とその並びの位置（tag 0x40 index、u8）を付ける。
- 扱える mode は describe の modes（tag 0x40、u8 のビット集合、bit n = mode n）で宣言する。0（入力）は必須。
- plan を解いたら、そのチャンネルは core §8 の空きの状態に戻る。

## 2. `oep.fixture.uart`

ストリームは fn に 1 本。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | configure | baud(u32)、[TLV] | baud(u32、実際の値) | 必要 |
| 0x02 | read | from(u8)、arg(u64)、max(u16) | start(u64)、flags(u8)、data | 不要 |
| 0x03 | marks | from_serial(u32) | more(u8)、count(u8)、count × (len(u8)、mark) | 不要 |
| 0x04 | clear | — | — | 必要 |
| 0x05 | mark | value(u8) | — | 必要 |
| 0x06 | write | count(u16)、data | accepted(u16) | 必要 |

- op 0x02〜0x06 は [共通部品](oep-if-common.ja.md) §1 の形（stream の byte なし）で、`oep.target.console` と同じ番号。
- configure の TLV 0x01 format（u8）: bit0-1 データ長（0 = 8、1 = 7）、bit2-3 パリティ（0 なし、1 偶数、2 奇数）、bit4 ストップ
  ビット（0 = 1、1 = 2）。無ければ 8N1。
- 受信は configure から plan を解くまで、セッションに関係なく貯める。configure をやり直しても貯めた分と位置はそのまま
  （境目が要るなら host が mark を付ける）。
- **TX の線は、plan で割り当てている間（configure の前も）UART の休止（high）に保つ**（相手の受信が雑音を拾わないため）。plan を
  解いたら駆動をやめ、core §8 の空きの状態にする。解いた後も相手の入力を浮かせたくない治具は、`oep.probe.config` の idle で
  そのピンをプルアップの入力に決めて保存する。
- 扱える format は describe の formats（tag 0x40、configure の TLV 0x01 の値の並び、u8）で宣言する。8N1（0）は必須。
- 片方向だけの UART（RX だけ、TX だけ）は、plan で片方の role だけを割り当てる。ピンの組が決まっている probe は、RX だけの組と
  TX だけの組も channel_group に別々に書く（channel_group は完全一致なので）。
- revision 1 は通知を送らない（subscribe は rejected unavailable）。後から足すときは、データの payload を共通部品 §1.5 の形にする。

## 3. `oep.fixture.i2c-target`

probe が I2C の target になり、DUT の controller の書き込みを受け、読み出しに答える（2026-09-30 に標準にした。それまでは
`io.github.ch32-riscv-ug.esp32.i2c-target`）。受けたフレームは probe の中の列に積み、host が read_rx で取り出す。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | configure | address(u8、7 ビット)、mode(u8) | — | 必要 |
| 0x02 | arm_rx | length(u16) | — | 必要 |
| 0x03 | read_rx | — | pending(u8)、count(u16)、data | 必要 |
| 0x04 | preload_tx | count(u16)、data | slots(u8) | 必要 |
| 0x05 | status | — | state(u8)、mode(u8)、armed(u8)、queued(u8)、rx_frames(u32)、tx_slots(u8)、errors(u16) | 不要 |
| 0x06 | reset | — | — | 必要 |
| 0x07 | stretch | stretch_us(u32) | — | 必要 |

- mode: 1 決まった長さの受信（arm_rx の length ちょうどの書き込みを 1 フレームとする）、2 長さつきの受信（1 byte の長さの書き込み、
  続く書き込みがその長さの本文。本文を 1 フレームとする。configure で受けられる状態になる）、3 送信の先置き（controller の読み出しに、
  preload_tx で置いた順に答える）。describe の features で扱える mode を宣言する。
- configure は target を作り直す（積んだフレームと数は消える）。plan の前は rejected unavailable。address が 0x7F を超えれば
  rejected malformed。扱えない mode は rejected unsupported。
- arm_rx は mode 1 だけ（ほかは rejected unavailable）。length は 1〜describe の max_length（外れれば rejected malformed）。すでに
  待っていれば、今の待ちを捨てて新しい length で待つ。
- read_rx は、いちばん古いフレームを取り出して返す（無ければ count 0）。pending は、取り出した後に残っている数。列があふれたら
  新しいフレームを捨て、errors を増やす。
- preload_tx は mode 3 だけ。count は 1〜max_length。slots は置いた数の通し番号（u8、一周する）。controller が読んだバイト数が
  置いた長さと違っても、次の読み出しは次の置き場から答える。チップの FIFO の癖（読み出しの最後に余分なバイトを出す、など）は
  probe が吸収する。
- status: state 0 未設定、1 動いている。mode は configure の値。armed は mode 1 で受信を待っているか（0 / 1）。queued は積んだ
  フレームの数。rx_frames は受けたフレームの累計、errors はあふれと受信の誤りの累計（u16、一周する）。
- stretch は、受けたバイトごとに SCL を low に保つ時間（µs、0 = しない）。features の bit1 を宣言する probe だけ（ほかは
  unknown_operation）。扱えない長さは rejected unsupported。
- describe: role_channels、max_length（1 フレームの最大 byte）、max_clock_hz（確かめた SCL の上限）、features（bit0 mode 3、
  bit1 stretch。mode 1 と 2 は必須）。
- 通知は送らない（subscribe は rejected unavailable）。

## 4. `oep.fixture.spi-target`

probe が SPI の target になり、CS で区切った 1 回の転送に、先に置いた MISO のバイトで答え、MOSI のバイトを積む（2026-09-30 に
標準にした。それまでは `io.github.ch32-riscv-ug.esp32.spi-target`）。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | configure | mode(u8: SPI の mode 0〜3)、bit_order(u8: 0 MSB が先、1 LSB が先) | — | 必要 |
| 0x02 | arm | length(u16)、count(u16)、tx(count byte) | — | 必要 |
| 0x03 | read_rx | — | pending(u8)、bits(u32)、count(u16)、data | 必要 |
| 0x04 | status | — | state(u8)、mode(u8)、bit_order(u8)、armed(u8)、queued(u8)、transactions(u32)、errors(u16) | 不要 |
| 0x05 | reset | — | — | 必要 |

- configure は target を作り直す。plan の前は rejected unavailable。mode が 3 を超える、bit_order が 1 を超えるか features の bit0 が
  無いのに 1、は rejected unsupported。
- arm は次の 1 回の転送を待つ: length は受ける最大 byte（1〜max_length）、tx はその転送で MISO に出すバイト（count ≤ length。
  足りない分は 0）。待っている間の arm は rejected unavailable（1 回に 1 つ）。
- 転送が CS で終わると、MOSI のバイトと、実際に来たビット数（bits）を列に積む。read_rx はいちばん古いものを返す（無ければ count 0）。
  pending は取り出した後の残り。
- status: state 0 未設定、1 動いている。armed は転送を待っているか。queued、transactions（終わった転送の累計）、errors（あふれ）。
- describe: role_channels、max_length（1 回の転送の最大 byte）、max_clock_hz（確かめた SCK の上限）、features（bit0 LSB が先）。
- 通知は送らない。
