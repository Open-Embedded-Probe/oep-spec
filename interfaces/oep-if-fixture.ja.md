# OEP インターフェース: fixture v1

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](../docs/versioning.ja.md) §6）。本体は [OEP core](../docs/oep-core.ja.md)、共通部品は [共通部品](oep-if-common.ja.md)（§1 位置つきの
ストリーム）。番号の唯一の定義は `registry/oep-v1.toml`。キャプチャは [キャプチャ](oep-if-capture.ja.md)。

| 名前 | revision | 役割 | plan の role | 対象の系統 |
|---|---:|---|---|---|
| `oep.fixture.gpio` | 1 | ピンを駆動し、読む | 1 = 線 | どの系統にも使う |
| `oep.fixture.uart` | 1 | UART の送受信 | 1 = RX、2 = TX | どの系統にも使う |
| `oep.fixture.i2c-target` | 1 | I2C の target（被制御側）。DUT の I2C controller を試す | 1 = SDA、2 = SCL | どの系統にも使う |
| `oep.fixture.spi-target` | 1 | SPI の target。DUT の SPI controller を試す | 1 = SCK、2 = MOSI、3 = MISO、4 = CS | どの系統にも使う |

どれも plan（[plan](oep-if-plan.ja.md)）で割り当てたチャンネルだけを扱う。下の表の op は、その節が任意と書かない限り、すべて必須（core §1.2）。

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

- 並びは要求の順に 1 つずつ行う（NRST を引いてから離す、などを 1 要求で送れる）。確かめは全部先に行い、確かめで断る以外に
  set は失敗しない（success）。
- 割り当てていないチャンネル（set、read）は、何もせず rejected unavailable（payload は core §4.3 の TLV: channel 0x02 と、並びの位置
  tag 0x40 index（u8））。扱えない mode（宣言に無い）は rejected unsupported（payload `0x00`、後ろに同じ channel / index の TLV）。
- 扱える mode は describe の modes（tag 0x40、u32 のビット集合、bit n = mode n）で宣言する。0（入力）は必須。
- **plan で取ったチャンネルは、最初の set までそれまでの状態を保つ**（空きの状態のまま。出力の idle なら、その level の駆動を続ける）。
  取ったことで level は変わらない。

### 1.1 出力の強さ（任意）

- **段の宣言**: 出力の強さを切り替えられる probe は、describe の drive_levels（tag 0x41: default(u8)、n(u8)、n × ma(u16)）で、
  選べる強さ（段）を目安の mA の昇順に並べ、既定の段を宣言する。段の番号は並びの位置（0 から）。n は 2 以上、ma は狭義の昇順、
  default は n 未満。強さを切り替えられない probe は drive_levels を載せない。段は probe のすべての channel に共通で、
  `oep.fixture.gpio` の fn が 2 つ以上あれば、どれも同じ値を宣言する。
- **強さが効くのは mode 3 / 4 だけ**。ほかの mode と、線（`oep.wire.*`）、`oep.fixture.uart`、`oep.fixture.i2c-target`、
  `oep.fixture.spi-target` が駆動するピンの強さは probe が決め、host は指定できない。
- **強さの指定**: 段の番号（u8）。0xFF は drive_levels の既定の段。`oep.probe.config` の idle の項目も同じ値を使う。
- **set の TLV 0x01 drive**: index(u8: 要求の並びの位置)、level(u8: 強さの指定)。1 つの TLV が並びの要素 1 つに効き、繰り返して複数の要素に付ける
  （要素ごとに強さが違ってよいため。電源の線と信号の線を 1 要求で動かせる）。index が n 以上、同じ index が 2 回、指す要素の mode が 3 / 4 でない
  のどれかなら、要求全体を rejected malformed。段の数以上の level（0xFF を除く）と、drive_levels を宣言しない probe への drive は
  rejected unsupported（受け取ったままの tag）。
- **効く強さ**: set で mode 3 / 4 にした要素の強さは、その要素の drive があればその段、無ければその channel の
  idle の項目（[probe の設定](oep-if-probe-config.ja.md) §1）があればその drive、どちらも無ければ既定の段。強さは、その channel を
  次に set するまで保つ。plan で取ってから最初の set までと、plan を解いた後は、空きの状態の強さ（idle の drive、無ければ既定の段）。

## 2. `oep.fixture.uart`

ストリームは fn に 1 本。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | configure | baud(u32)、[TLV] | baud(u32、実際の値)、[TLV] | 必要 |
| 0x02 | read | from(u8)、arg(u64)、max(u16)、[TLV] | start(u64)、flags(u8)、len(u16)、data、[TLV] | 不要 |
| 0x03 | marks | from_serial(u32) | more(u8)、count(u8)、count × mark、[TLV] | 不要 |
| 0x04 | clear | — | — | 必要 |
| 0x05 | mark | value(u8) | — | 必要 |
| 0x06 | write | count(u16)、data | accepted(u16)、[TLV] | 必要 |
| 0x07 | status | — | baud(u32、実際の値)、format(u8)、[TLV] | 不要 |

- op 0x02〜0x06 は [共通部品](oep-if-common.ja.md) §1 の形（stream の byte なし）で、`oep.target.console` と同じ番号。
- configure の TLV 0x01 format（u8）: bit0-1 データ長（0 = 8、1 = 7）、bit2-3 パリティ（0 なし、1 偶数、2 奇数）、bit4 ストップ
  ビット（0 = 1、1 = 2）。無ければ 8N1。宣言（formats）に無い値は rejected unsupported（受け取ったままの tag）。baud は実現できる値を返し、要求から
  ±5%（registry の `uart_baud_tolerance_pct`）を超えて外れれば rejected unsupported（payload `0x00`）。ピンの無い fn（plan に RX も TX も無い）の configure は rejected
  unavailable（cause 6）。
- **status**（ロック不要）: 実際の baud / format。uart 項目の baud は set の時に範囲で確かめるが、実際の分周は plan で UART が動くときに決まる。
  そのとき ±5% を超えれば既定（115200 8N1、registry の `uart_default_baud`）にする。
- **ストリームは plan が作り、plan を解くと消える**。セッションの configure も plan を解くと消える。受信は plan から（configure の前は
  `oep.probe.config` の uart 項目があればその値、無ければ 115200 8N1）、セッションに関係なく貯める。configure をやり直しても貯めた分と位置はそのまま
  （境目が要るなら host が mark を付ける）。**位置とマークの serial は、plan を解いて再び作っても起動の中で戻らない**
  （[共通部品](oep-if-common.ja.md) §1.1）。受信の誤りは mark lost（detail 2 framing、3 parity）。
- **TX の線は、plan で割り当てている間（configure の前も）UART の休止（high）に保つ**: plan を取ることが TX を使い始めることである（core §8）（相手の受信が雑音を拾わないため）。plan を
  解いたら UART の駆動をやめ、core §8 の空きの状態にする。解いた後も相手の入力を浮かせたくない治具は、`oep.probe.config` の idle で
  そのピンをプルアップの入力に決めて保存する。
- plan に TX の無い fn への write は rejected unavailable（cause 6）。
- 扱える format は describe の formats（tag 0x40、n(u8)、n × u8。configure の TLV 0x01 の値）で宣言する。8N1（0）は必須。

## 3. `oep.fixture.i2c-target`

probe が I2C の target になり、DUT の controller の書き込みを受け、読み出しに答える。受けたフレームは probe の中の列に積み、host が
read_rx で取り出す。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | configure | address(u8、7 ビット)、[TLV] | — | 必要 |
| 0x03 | read_rx | — | pending(u8)、count(u16)、data、[TLV ns(u64): そのフレームを終えた STOP か次の START の時刻、任意] | 必要 |
| 0x04 | preload_tx | count(u16)、data | — | 必要 |
| 0x05 | status | — | state(u8)、queued(u8)、rx_frames(u32)、tx_slots(u8)、errors(u32)、[TLV] | 不要 |
| 0x07 | stretch | stretch_us(u32) | — | 必要 |

- この fn の plan は role 1 と 2 をちょうど 1 つずつ、別々の channel で持つ（どちらかが無い、同じ role が 2 つある、両方の role が同じ
  channel の plan_apply は rejected malformed）。plan を解く・置き換えると target は止まり、describe の直後と同じ状態に戻る（state 0、
  列・置き場・累計を消し、stretch の値は 0）。
- SDA と SCL は**オープンドレインだけ**で駆動する: probe は low に引くか離すかで、high に駆動しない。
- **内部のプルアップ**: configure されている間 SDA / SCL に自分のプルアップを入れる probe は、features の bit2（内部プルアップ）でそれを宣言する。
  宣言しない probe はプルアップを入れない。
- state 0 では probe はどのアドレスにも ACK せず、両方の線を離しておく（low に引かず、プルアップも入れない。configure までは channel は core §8 の空きの状態のまま）。
- configure は target を作り直す（積んだフレーム、置き場、rx_frames と errors は消える。stretch の値は保つ）。この fn の plan が
  無いときは rejected unavailable（cause 6）。address が 0x7F を超えるなら rejected malformed。0x00〜0x07 と 0x78〜0x7F のアドレス（I2C の仕様が予約するもの: general call、start byte、10 bit の前置きなど）は rejected unsupported（payload `0x00`）。
- **書き込み**: controller の書き込みは 1 回のトランザクション（START から STOP または次の START まで）を単位に扱い、各 byte に ACK を返す。データの
  ある書き込み 1 回が 1 フレームで、列に積む。max_length を超えた分は捨て（フレームは max_length までの data で積む）、errors を 1 増やす。
  データの無い書き込み（アドレスの byte だけのもの）は何も積まず、何も数えない。
- read_rx は、いちばん古いフレームを取り出して返す（無ければ count 0）。state 0 では rejected unavailable（cause 6）。pending は、
  取り出した後に残っている数（255 で止める）。列に queue_depth 個あるときに次のフレームが来たら、その新しいフレームを捨て、errors を
  1 増やす（rx_frames には数えない）。列の深さは describe の queue_depth。errors は書き込み 1 回につき多くても 1 増える（max_length を超え、
  列もあふれた書き込みも 1）。
- **読み出し**: controller の読み出しには、preload_tx で置いた順に、置き場から答える。count は 1〜max_length（0 は malformed）。未読の置き場は
  queue_depth 個まで。すべて埋まっているときの preload_tx は何も置かずに rejected unavailable（cause 2）。state 0 では rejected unavailable（cause 6）。controller が
  読んだバイト数が置いた長さと違っても、次の読み出しは次の置き場から答える。**置き場が空のときは 0xFF を出す**。
- preload_tx の success は、置いたデータがその後に始まる controller の読み出しで使える状態になってから返す。
- status: state 0 未設定、1 動いている。queued は積んだフレームの数（255 で止める）。rx_frames は列に積んだフレームの累計（あふれて捨てたものは
  数えない）、tx_slots は preload_tx で置いて未読の置き場の数、errors はあふれか max_length 超過のあった書き込みの数の累計（u32）。
- stretch は、受けたデータの byte ごとに、8 bit 目の後、ACK を出した状態で ACK の clock の前に SCL を low に保つ時間（µs、0 = しない）。
  read では、アドレスが一致した後に同じだけ保つ。write のアドレスの byte では保たない。stretch は任意で、describe の ops で宣言する
  （core §1.2）。持たない probe は unknown_operation で答える。stretch_us が describe の max_stretch_us を超えれば rejected unsupported。state によらず受け
  （state 0 でも）、値は次に受ける byte から効く。configure は値を変えない。
- describe: ops、role_channels、max_length（1 フレームの最大 byte）、max_clock_hz（確かめた SCL の上限）、features（bit2 内部プルアップ）、
  queue_depth（tag 0x40、u8: 積めるフレームの数と、未読の置き場の数の上限）、
  max_stretch_us（tag 0x41、u32: stretch が受ける最大の µs。1 以上。stretch を持つ probe は必ず載せる）。

## 4. `oep.fixture.spi-target`

probe が SPI の target になり、CS で区切った 1 回の転送に、先に置いた MISO のバイトで答え、MOSI のバイトを積む。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | configure | mode(u8: SPI の mode 0〜3)、bit_order(u8: 0 MSB が先、1 LSB が先)、[TLV] | — | 必要 |
| 0x02 | arm | length(u16)、count(u16)、tx(count byte)、[TLV] | — | 必要 |
| 0x03 | read_rx | — | pending(u8)、bits(u32)、count(u16)、data、[TLV ns(u64): その転送で CS が無効になった時刻、任意] | 必要 |
| 0x04 | status | — | state(u8)、mode(u8)、bit_order(u8)、armed(u8)、queued(u8)、transactions(u32)、errors(u32)、[TLV] | 不要 |

- **SPI の mode** = CPOL × 2 + CPHA。CPOL は CS が無効な間の SCK の level（0 low、1 high）。CPHA 0 では、各ビットはそのクロック周期の最初の SCK の
  エッジで取り込まれ、2 番目のエッジで変わるので、MISO の最初のビットは最初の SCK のエッジより前に線に出ている（cs_setup_ns、下）。CPHA 1 では、
  各ビットはそのクロック周期の最初のエッジで変わり、2 番目のエッジで取り込まれる。最初のエッジは、CPOL の level から離れるエッジである。バイトは、
  両方向とも、bit_order のとおり MSB を先か LSB を先に送る。
- この fn の plan は role 1〜4 をちょうど 1 つずつ、別々の channel で持つ（role が欠ける、同じ role が 2 つある、2 つの role が同じ
  channel の plan_apply は rejected malformed）。plan を解く・置き換えると target は止まり、describe の直後と同じ状態に戻る（state 0、
  mode と bit_order は 0、列・待ち・累計を消す）。
- configure は target を作り直す（積んだ転送、待ち、transactions と errors は消える）。この fn の plan が無いときは rejected unavailable
  （cause 6）。mode が 3 を超える、bit_order が 1 を超える は rejected malformed。features の bit0 が無いのに bit_order 1 は rejected
  unsupported。**CS は low で有効**（high で有効は後から TLV で）。
- arm は次の 1 回の転送を待つ: length は受ける最大 byte（1〜max_length。0 は malformed、超過は unsupported）、tx はその転送で MISO に
  出すバイト（count ≤ length。count > length は rejected malformed。足りない分は 0）。待っている間の arm は rejected unavailable（1 回に 1 つ）。**arm していない間の転送は
  MOSI を捨て、transactions と errors を数える**。**MISO は tx の外（未 arm、tx を使い切った後）では 0**。CS が有効になってから SCK が
  1 回も来ずに無効に戻ったもの（0 ビット）は転送とみなさない: 何も積まず、transactions も errors も数えず、arm は待ち続ける。
- arm の success は、次の転送に tx を出せる状態になってから返す。その後に始まる転送（cs_setup_ns を守るもの）は、この arm で答えられる。
  その状態にできなければ何も arm せずに completed failed で答える。
- **configure から plan を解くまで、probe は CS が有効な間だけ MISO を駆動する。** CS が無効な間は MISO を駆動しない（プルの無い入力）。
  ただし CS が無効になってから cs_setup_ns の間は除く（下）。
  「MISO は tx の外では 0」は、CS が有効な間の転送のビットのことである。SCK、MOSI、CS は常に入力。configure の前は channel は空きの状態のまま（core §8）。
- 転送が CS で終わると、MOSI のバイトと、実際に来たビット数（bits、0xFFFFFFFF で止める）を列に積み、transactions を 1 増やす。data の byte 数は bits を 8 で
  割って切り上げた数で、length で止める。線の k 番目（0 から）のビットは、data の byte floor(k / 8) の、MSB が先ならビット 7 − (k mod 8)、
  LSB が先ならビット k mod 8 に置く（バイトの途中で終わった転送も同じ）。最後の byte の、来なかったビットは 0。length を超えた分は捨て、errors を 1 増やす（その転送は、bits を実際に来た数のまま、data を
  length までにして積む）。列に queue_depth 個あるときに終わった転送は積まずに捨て、errors を 1 増やす（transactions には数える）。
  errors は転送 1 回につき多くても 1 増える。read_rx はいちばん古いものを返す（無ければ count 0）。state 0 では rejected
  unavailable（cause 6）。pending は取り出した後の残り（255 で止める）。
- status: state 0 未設定、1 動いている。armed は転送を待っているか。queued（255 で止める）、transactions（終わった転送の累計）、
  errors（あふれ、未 arm、length 超過のどれかがあった転送の数の累計、u32）。
- describe: role_channels、max_length（1 回の転送の最大 byte）、max_clock_hz（確かめた SCK の上限）、features（bit0 LSB が先）、
  queue_depth（tag 0x40、u8）、cs_setup_ns（tag 0x43、u32、下）。
- **cs_setup_ns**（describe の tag 0x43、u32、ns）: CS が有効になってから最初の SCK のエッジまでの時間で、MISO が最初のビットで駆動されていることを
  probe が保証する最短のもの。probe の普段の負荷での最悪の値である: ほかのインターフェースが動いており、debug の線が attach されてコンソールが動いている場合を含む。
  CS が有効になってからその時間の間、MISO は駆動されていないか、最初のビットを駆動しているかのどちらかで、ほかの値になることはない。CS が無効になった後は、
  同じ時間のうちに MISO は駆動されなくなる。CS が有効になったらすぐ最初のビットで MISO を駆動する probe は、この tag を付けないか 0 を宣言する。CS が有効に
  なったのを見てからソフトウェアで MISO を駆動し始める probe は、これを宣言する。host はこの値を利用者に見せる。CS が有効になってから cs_setup_ns より
  早く SCK を始める master は、最初のビットに頼れない。

## 5. 参照する仕様

この文書の OEP のメッセージは、本文だけで定まる。バスを動かすのに使うもの:

| インターフェース | 仕様 | 使う部分 |
|---|---|---|
| `oep.fixture.i2c-target` | I2C-bus specification and user manual (NXP UM10204) | アドレスの指定（7 bit のアドレス）、ACK、clock stretching、予約されたアドレス 0x00〜0x07 と 0x78〜0x7F |
| `oep.fixture.spi-target` | 無し: SPI には正式な標準が無い | mode、CS、ビットの順は §4 が定める |
| `oep.fixture.uart` | 無し | configure の format のとおりの線（スタートビット、LSB を先にしたデータビット、パリティ、ストップビット）（§2） |
