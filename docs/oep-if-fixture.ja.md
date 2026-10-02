# OEP 標準インターフェース: fixture v1

[English](oep-if-fixture.md)

状態: **規範**（2026-09-26。2026-10-01 に[ゼロベースの再検討](v1-zero-base-proposal.ja.md)を反映）。本体は [OEP core](oep-core.ja.md)、共通部品は [共通部品](oep-if-common.ja.md)（§1 位置つきの
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
| 0x01 | set | n(u8)、n × (channel(u16)、mode(u8))、[TLV] | — | 必要 |
| 0x02 | read | n(u8)、n × channel(u16) | n(u8)、n × level(u8: 0 / 1)、[TLV] | 不要 |

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

- 並びは要求の順に 1 つずつ行う（NRST を引いてから離す、などを 1 要求で送れる）。確かめは全部先に行い、確かめで断る以外に
  set は失敗しない（success）。
- 割り当てていないチャンネル（set、read）は、何もせず rejected unavailable（payload は core §4.3 の TLV: channel 0x02 と、並びの位置
  tag 0x40 index（u8））。扱えない mode（宣言に無い）は rejected unsupported（payload `0x00`、後ろに同じ channel / index の TLV）。
  未定義の mode（8 以上）は rejected malformed。
- 扱える mode は describe の modes（tag 0x40、u32 のビット集合、bit n = mode n）で宣言する。0（入力）は必須。
- **plan で取ったチャンネルは、最初の set までそれまでの状態を保つ**（空きの状態のまま。出力の idle なら、その level の駆動を続ける）。
  取ったことで level は変わらない。
- plan を解いたら、そのチャンネルは core §8 の空きの状態に戻る。

### 1.1 出力の強さ（任意）

- **段の宣言**: 出力の強さを切り替えられる probe は、describe の drive_levels（tag 0x41: default(u8)、n(u8)、n × ma(u16)）で、
  選べる強さ（段）を目安の mA の昇順に並べ、既定の段を宣言する。段の番号は並びの位置（0 から）。n は 2 以上、ma は狭義の昇順、
  default は n 未満。強さを切り替えられない probe は drive_levels を載せない。段は probe のすべての channel に共通で、
  `oep.fixture.gpio` の fn が 2 つ以上あれば、どれも同じ値を宣言する。
- **強さが効くのは mode 3 / 4 だけ**。ほかの mode と、線（`oep.wire.*`）、`oep.fixture.uart`、`oep.fixture.i2c-target`、
  `oep.fixture.spi-target` が駆動するピンの強さは probe が決め、host は指定できない。
- **強さの指定**: kind(u8)、value(u16)。kind 0 = 段の番号（value が段の番号）。kind 1 = mA の上限（目安の mA が value 以下の段の
  うち、いちばん強い段。value がどの段の mA より小さければ段 0）。kind 2 以上は未定義。`oep.probe.config` の idle の項目も同じ形を使う。
- **set の TLV 0x01 drive**（非 critical。host は critical の bit を付けずに送る）: index(u8: 要求の並びの位置)、kind(u8)、value(u16)。
  1 つの TLV が並びの要素 1 つに効き、繰り返して複数の要素に付ける（要素ごとに強さが違ってよいため。電源の線と信号の線を 1 要求で
  動かせる）。index が n 以上、同じ index が 2 回、kind が未定義、指す要素の mode が 3 / 4 でない のどれかなら、要求全体を
  rejected malformed。kind 0 の value が段の数以上なら、その TLV を無視する。drive_levels を宣言しない probe は、drive の TLV を
  形を確かめずにすべて無視する（drive の TLV で rejected malformed にしない）。無視した drive は応答の ignored（core §2.3）に載せる。
  ignored は tag だけを並べるので、どの要素の drive を無視したかは示さない。host は効いた段を read の応答の TLV drive で知る。
  critical の bit を付けた drive の TLV は core §2.3 に従う: 無視するはずの場合は、無視せずに要求を rejected unsupported で断る。
- **効く強さ**: set で mode 3 / 4 にした要素の強さは、その要素の drive（無視しなかったもの）があればその段、無ければその channel の
  idle の項目（[probe の設定](oep-if-probe-config.ja.md) §1）が drive を持てばその段、どちらも無ければ既定の段。強さは、その channel を
  次に set するまで保つ。plan で取ってから最初の set までと、plan を解いた後は、空きの状態の強さ（idle の drive、無ければ既定の段）。
- **read の応答の TLV 0x01 drive**: n × u8。要求の channel の順に、その channel をいま mode 3 / 4 で駆動している段の番号（空きの
  状態の出力を含む）。mode 3 / 4 で駆動していない channel は 0xFF。drive_levels を宣言する probe は必ず付け、宣言しない probe は
  付けない。段の mA は describe の drive_levels で読む。

## 2. `oep.fixture.uart`

ストリームは fn に 1 本。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | configure | baud(u32)、[TLV] | baud(u32、実際の値)、[TLV] | 必要 |
| 0x02 | read | from(u8)、arg(u64)、max(u16)、[TLV] | start(u64)、flags(u8)、len(u16)、data、[TLV] | 不要 |
| 0x03 | marks | from_serial(u32) | more(u8)、count(u8)、count × (len(u8)、mark)、[TLV] | 不要 |
| 0x04 | clear | — | — | 必要 |
| 0x05 | mark | value(u8) | — | 必要 |
| 0x06 | write | count(u16)、data | accepted(u16)、[TLV] | 必要 |
| 0x07 | status | — | configured(u8: 0 既定のまま、1 セッションの configure、2 設定の uart 項目、3 uart 項目の baud が実現できず既定にした)、baud(u32、実際の値)、format(u8)、[TLV] | 不要 |

- op 0x02〜0x06 は [共通部品](oep-if-common.ja.md) §1 の形（stream の byte なし）で、`oep.target.console` と同じ番号。
- configure の TLV 0x01 format（u8）: bit0-1 データ長（0 = 8、1 = 7）、bit2-3 パリティ（0 なし、1 偶数、2 奇数）、bit4 ストップ
  ビット（0 = 1、1 = 2）。無ければ 8N1。未定義の値（bit0-1 の 2 / 3、bit2-3 の 3、bit5-7）は rejected malformed。宣言（formats）に
  無い値は rejected unsupported（tag 0x01）。host は critical で送る（黙って 8N1 にならないため）。baud は実現できる値を返し、要求から
  ±5% を超えて外れれば rejected unsupported（payload `0x00`）。ピンの無い fn（plan に RX も TX も無い）の configure は rejected
  unavailable（cause 6）。
- **status**（ロック不要）: 何が掛かっているか（`uart_configured`）と実際の baud / format。読むだけの host が知るため。uart 項目の
  baud は set の時に範囲で確かめるが、実際の分周は plan で UART が動くときに決まる。そのとき ±5% を超えれば既定（115200 8N1）に
  して configured = 3 で知らせる。
- **ストリームは plan が作り、plan を解くと消える**。セッションの configure も plan を解くと消える。受信は plan から（configure の前は
  `oep.probe.config` の uart 項目があればその値、無ければ 115200 8N1）、セッションに関係なく貯める。configure をやり直しても貯めた分と位置はそのまま
  （境目が要るなら host が mark を付ける）。**位置とマークの serial は、plan を解いて再び作っても起動の中で戻らない**
  （[共通部品](oep-if-common.ja.md) §1.1）。受信の誤りは mark lost（detail 2 framing、3 parity）。
- **TX の線は、plan で割り当てている間（configure の前も）UART の休止（high）に保つ**（相手の受信が雑音を拾わないため）。plan を
  解いたら UART の駆動をやめ、core §8 の空きの状態にする。解いた後も相手の入力を浮かせたくない治具は、`oep.probe.config` の idle で
  そのピンをプルアップの入力に決めて保存する。
- 扱える format は describe の formats（tag 0x40、n(u8)、n × u8。configure の TLV 0x01 の値）で宣言する。8N1（0）は必須。
- 片方向だけの UART（RX だけ、TX だけ）は、plan で片方の role だけを割り当てる。ピンの組が決まっている probe は、RX だけの組と
  TX だけの組も channel_group に別々に書く（channel_group は完全一致なので）。
- revision 1 は通知を送らない（subscribe は rejected unsupported）。後から足すときは、データの payload を core §11.2 の形にする。

## 3. `oep.fixture.i2c-target`

probe が I2C の target になり、DUT の controller の書き込みを受け、読み出しに答える。受けたフレームは probe の中の列に積み、host が
read_rx で取り出す。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | configure | address(u8、7 ビット)、mode(u8)、[TLV] | — | 必要 |
| 0x02 | arm_rx | length(u16) | — | 必要 |
| 0x03 | read_rx | — | pending(u8)、count(u16)、data、[TLV ns(u64): 受けた時刻、任意] | 必要 |
| 0x04 | preload_tx | count(u16)、data | slots(u8)、[TLV] | 必要 |
| 0x05 | status | — | state(u8)、mode(u8)、armed(u8)、queued(u8)、rx_frames(u32)、tx_slots(u8)、errors(u32)、[TLV] | 不要 |
| 0x06 | reset | — | — | 必要 |
| 0x07 | stretch | stretch_us(u32) | — | 必要 |

- mode: 1 決まった長さの受信（arm_rx の length ちょうどの書き込みを 1 フレームとする）、2 長さつきの受信（1 byte の長さの書き込みと、
  **同じトランザクションの中で**続く書き込みがその長さの本文（repeated start は無し）。本文を 1 フレームとする。configure で受けられる
  状態になる）、3 送信の先置き（controller の読み出しに、preload_tx で置いた順に答える）。describe の features で扱える mode を宣言する。
- この fn の plan は role 1 と 2 をちょうど 1 つずつ、別々の channel で持つ（どちらかが無い、同じ role が 2 つある、両方の role が同じ
  channel の plan_apply は rejected malformed）。plan を解く・置き換えると target は止まり、describe の直後と同じ状態に戻る（state 0、
  mode 0、列・待ち・置き場・累計を消し、stretch の値は 0）。
- configure は target を作り直す（積んだフレーム、待ち、置き場、rx_frames と errors は消える。stretch の値は保つ）。この fn の plan が
  無いときは rejected unavailable（cause 6）。address が 0x7F を超える、mode が未定義（0、4 以上）なら rejected malformed。定義にあるが
  宣言に無い mode は rejected unsupported。
- arm_rx は mode 1 だけ（ほかは rejected unavailable cause 6）。length は 1〜describe の max_length（0 は malformed、max_length 超は
  unsupported）。すでに待っていれば、今の待ちを捨てて新しい length で待つ。待ちはフレームを受けても終わらず、次の arm_rx、reset、
  configure、plan を解くまで同じ length で受け続ける（armed は 1 のまま）。**arm していないときの controller の書き込みは ACK して捨て、
  errors を 1 増やす**（線を止めない）。
- controller の書き込みは 1 回のトランザクション（START から STOP または次の START まで）を単位に扱い、どの場合も各 byte に ACK を
  返す。データの無い書き込み（アドレスの byte だけのもの）は、どの mode でも何も数えない。mode 1 で待っているとき、データの byte 数が
  length と違う書き込みは捨て、errors を 1 増やす（待ちは続く）。mode 2 で、最初の byte（長さ L）が 0 か max_length を超える、または
  続く byte の数が L と違う書き込みは捨て、errors を 1 増やす。mode 3 の書き込みは捨て、errors を 1 増やす。
- read_rx は、いちばん古いフレームを取り出して返す（無ければ count 0）。state 0 では rejected unavailable（cause 6）。pending は、
  取り出した後に残っている数（255 で止める）。列に queue_depth 個あるときに次のフレームが来たら、その新しいフレームを捨て、errors を
  1 増やす（rx_frames には数えない）。列の深さは describe の queue_depth。
- preload_tx は mode 3 だけ。count は 1〜max_length（0 は malformed）。slots は置いた数の通し番号（u8、一周する）。未読の置き場は
  queue_depth 個まで。すべて埋まっているときの preload_tx は何も置かずに rejected unavailable（cause 2）。controller が
  読んだバイト数が置いた長さと違っても、次の読み出しは次の置き場から答える。**置き場が空のとき（と mode 1 / 2 で読み出されたとき）は
  0xFF を出す**。チップの FIFO の癖（読み出しの最後に余分なバイトを出す、など）は probe が吸収する。
- status: state 0 未設定、1 動いている。mode は configure の値。armed は mode 1 で受信を待っているか（0 / 1）。queued は積んだ
  フレームの数（255 で止める）。rx_frames は列に積んだフレームの累計（あふれて捨てたものは数えない）、tx_slots は preload_tx で置いて
  未読の置き場の数（mode 3。ほかは 0）、errors はあふれと、上の書き込みの誤り（長さの誤り、未 arm と mode 3 の書き込み）の累計（u32）。
- reset は configure 直後と同じ状態に戻す（列、待ち、累計を消す。mode と address は保つ）。state 0 では rejected unavailable（cause 6）。
- stretch は、受けたデータの byte ごとに、8 bit 目の後、ACK を出した状態で ACK の clock の前に SCL を low に保つ時間（µs、0 = しない）。
  read では、アドレスが一致した後に同じだけ保つ。write のアドレスの byte では保たない。features の bit1 を宣言する probe
  だけ（ほかは unknown_operation）。stretch_us が describe の max_stretch_us を超えれば rejected unsupported。state によらず受け
  （state 0 でも）、値は次に受ける byte から効く。configure と reset は値を変えない。
- describe: role_channels、max_length（1 フレームの最大 byte）、max_clock_hz（確かめた SCL の上限）、features（bit0 mode 3、
  bit1 stretch。mode 1 と 2 は必須）、queue_depth（tag 0x40、u8: 積めるフレームの数。mode 3 では未読の置き場の数の上限）、
  max_stretch_us（tag 0x41、u32: stretch が受ける最大の µs。1 以上。features の bit1 を宣言する probe は必ず載せる）。
- 通知は送らない（subscribe は rejected unsupported）。

## 4. `oep.fixture.spi-target`

probe が SPI の target になり、CS で区切った 1 回の転送に、先に置いた MISO のバイトで答え、MOSI のバイトを積む。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | configure | mode(u8: SPI の mode 0〜3)、bit_order(u8: 0 MSB が先、1 LSB が先)、[TLV] | — | 必要 |
| 0x02 | arm | length(u16)、count(u16)、tx(count byte)、[TLV] | — | 必要 |
| 0x03 | read_rx | — | pending(u8)、bits(u32)、count(u16)、data、[TLV ns(u64): 受けた時刻、任意] | 必要 |
| 0x04 | status | — | state(u8)、mode(u8)、bit_order(u8)、armed(u8)、queued(u8)、transactions(u32)、errors(u32)、[TLV] | 不要 |
| 0x05 | reset | — | — | 必要 |

- この fn の plan は role 1〜4 をちょうど 1 つずつ、別々の channel で持つ（role が欠ける、同じ role が 2 つある、2 つの role が同じ
  channel の plan_apply は rejected malformed）。plan を解く・置き換えると target は止まり、describe の直後と同じ状態に戻る（state 0、
  mode と bit_order は 0、列・待ち・累計を消す）。
- configure は target を作り直す（積んだ転送、待ち、transactions と errors は消える）。この fn の plan が無いときは rejected unavailable
  （cause 6）。mode が 3 を超える、bit_order が 1 を超える は rejected malformed。features の bit0 が無いのに bit_order 1 は rejected
  unsupported。**CS は low で有効**（high で有効は後から TLV で）。
- arm は次の 1 回の転送を待つ: length は受ける最大 byte（1〜max_length。0 は malformed、超過は unsupported）、tx はその転送で MISO に
  出すバイト（count ≤ length。足りない分は 0）。待っている間の arm は rejected unavailable（1 回に 1 つ）。**arm していない間の転送は
  MOSI を捨て、transactions と errors を数える**。**MISO は tx の外（未 arm、tx を使い切った後）では 0**。CS が有効になってから SCK が
  1 回も来ずに無効に戻ったもの（0 ビット）は転送とみなさない: 何も積まず、transactions も errors も数えず、arm は待ち続ける。
- 転送が CS で終わると、MOSI のバイトと、実際に来たビット数（bits）を列に積み、transactions を 1 増やす。data の byte 数は bits を 8 で
  割って切り上げた数で、length で止める。length を超えた分は捨て、errors を 1 増やす（その転送は、bits を実際に来た数のまま、data を
  length までにして積む）。列に queue_depth 個あるときに終わった転送は積まずに捨て、errors を 1 増やす（transactions には数える）。
  length を超え、かつ列があふれた転送は errors を 2 増やす。read_rx はいちばん古いものを返す（無ければ count 0）。state 0 では rejected
  unavailable（cause 6）。pending は取り出した後の残り（255 で止める）。
- status: state 0 未設定、1 動いている。armed は転送を待っているか。queued（255 で止める）、transactions（終わった転送の累計）、
  errors（あふれ、未 arm、length 超過をそれぞれ 1 と数えた累計、u32）。
- reset は configure 直後と同じ状態に戻す（列、待ち、累計を消す。mode と bit_order は保つ）。state 0 では rejected unavailable（cause 6）。
- describe: role_channels、max_length（1 回の転送の最大 byte）、max_clock_hz（確かめた SCK の上限）、features（bit0 LSB が先）、
  queue_depth（tag 0x40、u8）。
- 通知は送らない（subscribe は rejected unsupported）。
