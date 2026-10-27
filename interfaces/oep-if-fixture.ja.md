# OEP インターフェース: fixture v1

状態: **規範**（v1）。凍結状態と言語・互換性の方針は[版と安定性](../docs/versioning.ja.md)を参照。本体は [OEP core](../docs/oep-core.ja.md)、共通部品は [共通部品](oep-if-common.ja.md)（§1 位置つきの
ストリーム）。番号の唯一の定義は `registry/oep-v1.toml`。キャプチャは [キャプチャ](oep-if-capture.ja.md)。

| 名前 | revision | 役割 | plan の role | 対象の系統 |
|---|---:|---|---|---|
| `oep.fixture.gpio` | 1 | ピンを駆動し、読む | 1 = 線 | どの系統にも使う |
| `oep.fixture.uart` | 1 | UART の送受信 | 1 = RX、2 = TX | どの系統にも使う |
| `oep.fixture.i2c-target` | 1 | I2C の target（被制御側）。DUT の I2C controller を試す | 1 = SDA、2 = SCL | どの系統にも使う |
| `oep.fixture.spi-target` | 1 | SPI の target。DUT の SPI controller を試す | 1 = SCK、2 = MOSI、3 = MISO、4 = CS | どの系統にも使う |
| `oep.fixture.i2c-controller` | 1 | I2C の controller（制御側）。DUT の I2C target を試す | 1 = SDA、2 = SCL | どの系統にも使う |
| `oep.fixture.spi-controller` | 1 | SPI の controller。DUT の SPI target を試す | 1 = SCK、2 = MOSI、3 = MISO、4 = CS | どの系統にも使う |
| `oep.fixture.pwm` | 1 | 周波数とデューティを指定した方形波を出す（DUT のクロック、PWM の入力、刺激） | k = 出力 k（0 から） | どの系統にも使う |
| `oep.fixture.counter` | 1 | 決めた時間のうちにエッジを数える（周波数、パルスの数） | k = 入力 k（0 から） | どの系統にも使う |
| `oep.fixture.dac` | 1 | アナログの値を出す（DUT の ADC の入力、基準） | k = 出力 k（0 から） | どの系統にも使う |

どれも[plan](oep-if-plan.ja.md)で割り当てたチャンネルだけを扱う。同じ割り当ての状態不変はplan §2.1に従う。下の表の op は、その節が任意と書かない限り、すべて必須（core §1.2）。

UART / I2C / SPIのconfigureは、書式・対応値・資源を副作用前に検証する。rejectedでは既存の設定・queue・ピンを変更しない
（非同期の送受信の進行はcore §6.3）。受理後の初期化に失敗した場合はcompleted failedとし、partialは返さない。
成功・失敗ともplanは保ち、失敗後は各節が定める未設定状態から、hostの新しいconfigureで回復する。
以前のハードウェア設定へのロールバックは要求しない。後始末までcoreのmax_op_msに含める。

## 1. `oep.fixture.gpio`

最小の実装はset/readとmode 0でよく、出力modeとプルは対応するものだけを宣言する。
GPIOのpin割り当てにはplanを使う。planを持たない他の独自拡張へ、この依存を要求するものではない。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x10 | set | n(u8)、n × (channel(u16)、mode(u8))、[TLV] | — | 必要 |
| 0x11 | read | n(u8)、n × channel(u16) | n(u8)、n × level(u8: 0 / 1)、[TLV] | 不要 |

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
- GPIOのplanは出力のidleのchannelも受け付ける。
- readは現在のlevelを観測するだけで、入力へ切り替えたり、出力・プル・出力の強さを変更したりしない。
  planの解放・セッション終了では、そのplanによるGPIOの設定を解き、core §8/§9の空きの状態へ戻す。

出力の強さはprobeが決める。v1では段の切替えを定義せず、必要な場合は新しい任意機能のTLVで定義する。
hostが指定した強さに動作が依存する場合は、その要求TLVをcriticalで送り、非対応のprobeに黙って無視させない（core §2.3）。

## 2. `oep.fixture.uart`

ストリームは fn に 1 本。最小の実装はconfigure/read/statusで、受信専用にしてよい。
RXを割り当てて受信を保持するbufferと位置管理に対し、マークのringと送信のqueueは、それぞれの任意機能を提供しない場合には不要である。

| op | 名前 | 要求 | 応答 | ロック | 必須 |
|---:|---|---|---|---|---|
| 0x10 | configure | baud(u32)、[TLV] | baud(u32、成功は実際の値、failedは0)、[TLV] | 必要 | 必須 |
| 0x11 | read | from(u8)、arg(u64)、max(u16)、[TLV] | start(u64)、flags(u8)、len(u16)、data、[TLV] | 不要 | 必須 |
| 0x12 | marks | from_serial(u32) | more(u8)、count(u8)、count × mark、[TLV] | 不要 | 任意 |
| 0x13 | clear | — | — | 必要 | 任意 |
| 0x14 | mark | value(u8) | — | 必要 | 任意。marksも必要 |
| 0x15 | write | count(u16)、data | accepted(u16)、[TLV] | 必要 | 任意 |
| 0x16 | status | — | baud(u32、実際の値)、format(u8)、[TLV] | 不要 | 必須 |

- op 0x11〜0x15 は [共通部品](oep-if-common.ja.md) §1 の形（stream の u32 なし）で、`oep.target.console` と同じ番号。
- 任意opは提供するときだけopsに立てる。不在opはunknown_operation。marksを提供しない場合、readのfrom 3はunsupported（固定部分の印0）。
  clearはmarksなしでも提供でき、その場合はclearのマークを要求しない。任意opをfeaturesの新しいbitで宣言しない。
- writeを提供しないfnは、planのTX roleを受け付けず、そのroleのrole_channels/channel_groupを宣言しない。
  writeを提供するfnでも、現在のplanにTXが無いか未configureならwriteはunavailable（cause 6）。TXだけのplanと未configureのplanでは受信しない。
  その間も保持済みの受信データは、共通部品 §1.2の通常のreadで読める。保持データが無い場合の位置とgapも同じ規則で返す。
- RXもTXもない、plan未作成の状態では、提供する上記opの有効な要求をunavailable（cause 6）で断る。coreの見出し・セッション・書式の規則は先に適用する。
- configure の TLV 0x01 format（u8）: bit0-1 データ長（0 = 8、1 = 7）、bit2-3 パリティ（0 なし、1 偶数、2 奇数）、bit4 ストップ
  ビット（0 = 1、1 = 2）。無ければ 8N1。宣言（formats）に無い値は rejected unsupported（受け取ったままの tag）。baud は実現できる値を返し、要求から
  ±5%（registry の `uart_baud_tolerance_pct`）を超えて外れれば rejected unsupported（payload `0x00`）。baud 0はmalformed。
- configureは割り当てたRX/TXを、決めた実際のbaudと指定のformatで使える状態になってからsuccessを返す。初期化に失敗したら送受信を停止し、
  未configureへ戻してbaud 0のcompleted failedを返す。RXはcore §8の空きの状態へ戻し、割り当てたTXは下の休止highを保つ。
  受理したconfigureは成功・失敗とも未送信のTXを捨て、新しい設定へ持ち越さない。既に線へ出た分は取り消せず、相手へ届いた量は保証しない。
- **status**（ロック不要）: configure済みなら実際のbaud/format。最初のconfigure前とconfigure失敗後は、baud 0、format 0を返す。
  0は未configureの印であり、0 baudで通信しない。対応できない既定のbaudを暗黙に掛ける必要はない。
- **ストリームはplanが作り、planを解くと消える**。セッションのconfigureもplanを解くと消える。
  受信はhostが明示的にconfigureしてから始める。hostに保存した値があっても、受信は暗黙に始めない。
  configure済みのplanを持つ間は、読むhostや要求のsession_idによらず受信を貯める。
  configureをやり直しても、成功・失敗によらず、ストリームへ収めた受信データ・マークと位置・serialは保つ
  （境目が要るなら host が mark を付ける）。**位置とマークの serial は、plan を解いて再び作っても起動の中で戻らない**
  （[共通部品](oep-if-common.ja.md) §1.1）。marksを提供する場合、受信の誤りはmark lost（detail 2 framing、3 parity）とする。
  marksを提供しない場合は、マークの記録とserialの管理を要求しない。streamの位置は同じboot内で保持する。
- configure済みの割り当て変更はunavailable（cause 6）で断り、
  hostは必要なデータを読んでplan_releaseしてから作り直す。未configureの割り当て変更は、bufferとマークを解き、未configureのまま置き換える。
  位置とマークのserialは、その変更でも戻さない。
- **TX の線は、plan で割り当てている間（configure の前も）、送信中を除きUARTの休止（high）に保つ**: plan を取ることが TX を使い始めることである（core §8）（相手の受信が雑音を拾わないため）。plan を
  解いたら UART の駆動をやめ、core §8 の空きの状態にする。解いた後も相手の入力を浮かせたくない治具は、本体の設定 `channel.{}.idle`（core §13.8）で
  そのピンをプルアップの入力に決めて保存する。
- 扱える format は describe の formats（tag 0x40、n(u8)、n × u8。configure の TLV 0x01 の値）で宣言する。8N1（0）は必須。

### 2.1 シリアルの口の素通し（任意の設定）

UART bridge しか口の無い probe でも、普通のシリアルモニタで target の出力を見られるようにする任意の設定の項目（core §13。カテゴリはその
`oep.fixture.uart` の fn）。セッションと独立に効く設定である（core §9）。

| 名前 | form | key_kind | 意味 |
|---|---|---|---|
| `passthrough.{}.rx` | channel | transport（シリアルの口） | 受ける channel。値があれば、その口でこの UART の素通しをする |
| `passthrough.{}.baud` | u32 | transport | 速さ。値が無ければ 115200 |
| `passthrough.{}.format` | enum | transport | format（configure の TLV 0x01 の値）。値が無ければ 8N1 |

- key はシリアルの口（kind 1〜3、core §7.5）。ほかの経路は unsupported。
- rx はその fn の role 1（RX）として宣言された channel（ほかは unsupported）。rx が disable なら、または出力の idle を持てば unavailable cause 5。
- baud と format は configure と同じ規則（baud 0 は malformed、作れない baud は unsupported）。format の選択肢（setting_choice）は formats の値で、
  名前はデータ長、パリティ（`n`、`e`、`o`）、ストップビットをつないだもの（`8n1`、`7e2`）。
- **素通しの条件**: その口からセッションの要求が来ていない、その fn の plan が無い、rx をほかの plan・接続・設定が取っていない、のすべてが成り立つ間、
  probe はその UART を rx だけで受け（TX は使わない。rx を駆動しない）、受けたバイトを [経路](../docs/oep-transports.ja.md) §4 のとおり口へフレームの外で送る。
  どれかが成り立たなくなったら、受けるのをやめて rx を空きの状態に戻す。条件がまた成り立てば再開する。
- 素通しはセッションの資源と取り合わない: セッションの plan、接続、口の使用は、素通しを止めて先に通る（素通しを理由に断らない）。
- 素通しで受けたバイトは OEP のストリーム（read）に入れず、保持しない。口へ送れなかった分は捨てる。
- 口からフレームの外で来たバイトを target へ送ることは定めない（入力は OEP の write を使う）。
- 1 つの口に置ける素通しは 1 つだけである（どの UART の fn の素通しとも、コンソールの素通し（[コンソール](oep-if-console.ja.md) §2.1）とも重ねない）。
  重なる set は unavailable cause 5。

## 3. `oep.fixture.i2c-target`

probe が I2C の target になり、DUT の controller の書き込みを受け、読み出しに答える。受けたフレームは probe の中の列に積み、host が
read_rx で取り出す。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x10 | configure | address(u8、7 ビット)、[TLV] | — | 必要 |
| 0x11 | read_rx | — | pending(u8)、count(u16)、data、[TLV ns(u64): そのフレームを終えた STOP か次の START の時刻、任意] | 必要 |
| 0x12 | preload_tx | count(u16)、data | — | 必要 |
| 0x13 | status | — | state(u8)、queued(u8)、rx_frames(u32)、tx_slots(u8)、errors(u32)、[TLV] | 不要 |
| 0x14 | stretch | stretch_us(u32) | — | 必要 |

- このfnのplanはrole 1と2をちょうど1つずつ、別々のchannelで持つ。満たさない組のplan_applyはunsupported（role_assignmentのtag）で断る。
  動作中（state 1）の割り当て（role, channel）の集合の変更はunavailable（cause 6）。planを解くか未設定の役割を置き換えると初期状態へ戻る（state 0、
  列・置き場・累計を消し、stretch の値は 0）。
- SDA と SCL は**オープンドレインだけ**で駆動する: probe は low に引くか離すかで、high に駆動しない。
- **内部のプルアップ**: configure されている間 SDA / SCL に自分のプルアップを入れる probe は、features の bit0（内部プルアップ）でそれを宣言する。
  宣言しない probe はプルアップを入れない。
- state 0ではどのアドレスにもACKせず、I2C機能としての駆動・内部プルアップをやめ、channelをcore §8の空きの状態にする。
  空きの状態として設定されたpullは、I2C機能による内部プルアップとは区別する。
- configure は target を作り直す（積んだフレーム、置き場、rx_frames と errors は消える。stretch の値は保つ）。この fn の plan が
  無いときは rejected unavailable（cause 6）。address が 0x7F を超えるなら rejected malformed。0x00〜0x07 と 0x78〜0x7F のアドレス（I2C の仕様が予約するもの: general call、start byte、10 bit の前置きなど）は rejected unsupported（payload `0x00`）。
- configureの成功はstate 1となってから返す。初期化に失敗したらstate 0へ戻し、受信の列と送信の置き場を空にしてrx_frames・errorsを0にする。
  stretchの値は失敗でも保つ。成功・failedとも応答の固定部分はなく、末尾は[TLV]。
- **書き込み**: controller の書き込みは 1 回のトランザクション（START から STOP または次の START まで）を単位に扱い、各 byte に ACK を返す。データの
  ある書き込み 1 回が 1 フレームで、列に積む。max_length を超えた分は捨て（フレームは max_length までの data で積む）、errors を 1 増やす。
  データの無い書き込み（アドレスの byte だけのもの）は何も積まず、何も数えない。
- read_rx は、いちばん古いフレームを取り出して返す（無ければ count 0）。state 0 では rejected unavailable（cause 6）。pending は、
  取り出した後に残っている数（255 で止める）。列に queue_depth 個あるときに次のフレームが来たら、その新しいフレームを捨て、errors を
  1 増やす（rx_frames には数えない）。列の深さは describe の queue_depth。errors は書き込み 1 回につき多くても 1 増える（max_length を超え、
  列もあふれた書き込みも 1）。
- **読み出し**: controller の読み出しには、preload_tx で置いた順に、置き場から答える。count は 1〜max_length（0 は malformed）。未読の置き場は
  queue_depth 個まで。すべて埋まっているときの preload_tx は何も置かずに rejected unavailable（cause 2）。state 0 では rejected unavailable（cause 6）。controller が
  読んだバイト数が置いた長さと違っても、次の読み出しは次の置き場から答える。**置き場が空のときと、同じ読み出しで置いた長さを使い切った後は0xFFを出す**。
  同じ読み出しの途中で次の置き場を消費しない。
- preload_tx の success は、置いたデータがその後に始まる controller の読み出しで使える状態になってから返す。
- status: state 0 未設定、1 動いている。queued は積んだフレームの数（255 で止める）。rx_frames は列に積んだフレームの累計（あふれて捨てたものは
  数えない）、tx_slots は preload_tx で置いて未読の置き場の数、errors はあふれか max_length 超過のあった書き込みの数の累計（u32）。
  rx_framesとerrorsは0xFFFFFFFFで飽和し、configureまたはplan解放で0へ戻る。
- stretch は、受けたデータの byte ごとに、8 bit 目の後、ACK を出した状態で ACK の clock の前に SCL を low に保つ時間（µs、0 = しない）。
  read では、アドレスが一致した後に同じだけ保つ。write のアドレスの byte では保たない。stretchは任意（core §1.2）。stretch_us が describe の max_stretch_us を超えれば rejected unsupported。state によらず受け
  （state 0 でも）、値は次に受ける byte から効く。configure は値を変えない。
- describe: ops、role_channels、max_length（1 フレームの最大 byte）、max_clock_hz（確かめた SCL の上限）、features（bit0 内部プルアップ）、
  queue_depth（tag 0x40、u8: 積めるフレームの数と、未読の置き場の数の上限）、
  max_stretch_us（tag 0x41、u32: stretch が受ける最大の µs。1 以上。stretch を持つ probe は必ず載せる）。
- max_lengthは、preload_txの要求（見出し10 + count 2 + data）とread_rxの応答（見出し5 + pending 1 + count 2 + data）が
  どの経路のmax_frameにも収まる値にする。外部controllerが書いたフレームは、read_rxで分割できない。任意のtimestamp TLVは収まる場合だけ付ける。

## 4. `oep.fixture.spi-target`

probe が SPI の target になり、CS で区切った 1 回の転送に、先に置いた MISO のバイトで答え、MOSI のバイトを積む。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x10 | configure | mode(u8: SPI の mode 0〜3)、bit_order(u8: 0 MSB が先、1 LSB が先)、[TLV] | — | 必要 |
| 0x11 | arm | length(u16)、count(u16)、tx(count byte)、[TLV] | — | 必要 |
| 0x12 | read_rx | — | pending(u8)、bits(u32)、count(u16)、data、[TLV ns(u64): その転送で CS が無効になった時刻、任意] | 必要 |
| 0x13 | status | — | state(u8)、mode(u8)、bit_order(u8)、armed(u8)、queued(u8)、transactions(u32)、errors(u32)、[TLV] | 不要 |

- **SPI の mode** = CPOL × 2 + CPHA。CPOL は CS が無効な間の SCK の level（0 low、1 high）。CPHA 0 では、各ビットはそのクロック周期の最初の SCK の
  エッジで取り込まれ、2 番目のエッジで変わるので、MISO の最初のビットは最初の SCK のエッジより前に線に出ている（cs_setup_ns、下）。CPHA 1 では、
  各ビットはそのクロック周期の最初のエッジで変わり、2 番目のエッジで取り込まれる。最初のエッジは、CPOL の level から離れるエッジである。バイトは、
  両方向とも、bit_order のとおり MSB を先か LSB を先に送る。
- このfnのplanはrole 1〜4をちょうど1つずつ、別々のchannelで持つ。満たさない組のplan_applyはunsupported（role_assignmentのtag）で断る。
  動作中（state 1）の割り当て（role, channel）の集合の変更はunavailable（cause 6）。planを解くか未設定の役割を置き換えると初期状態へ戻る（state 0、
  mode と bit_order は 0、列・待ち・累計を消す）。
- configure は target を作り直す（積んだ転送、待ち、transactions と errors は消える）。この fn の plan が無いときは rejected unavailable
  （cause 6）。mode が 3 を超える、bit_order が 1 を超える は rejected malformed。features の bit0 が無いのに bit_order 1 は rejected
  unsupported。describeのmodesに無いmodeもunsupported（固定部分の印0）で、状態を変えない。
  mode 0〜3のすべての実装は要求せず、1つ以上を提供する。**CS は low で有効**。
- configureの成功はstate 1となってから返す。初期化に失敗したらstate 0へ戻し、mode・bit_order・armed・queued・transactions・errorsを0にする。
  受信の列とarmの送信データを捨て、SPI機能としての駆動をやめ、channelをcore §8の空きの状態へ戻す。
  成功・failedとも応答の固定部分はなく、末尾は[TLV]。state 0の外部転送は受信・計数せず、armも消費しない。
- state 0（未設定）への arm は rejected unavailable（cause 6）で答え、状態を変えない。
- arm は次の 1 回の転送を待つ: length は受ける最大 byte（1〜max_length。0 は malformed、超過は unsupported）、tx はその転送で MISO に
  出すバイト（count ≤ length。count > length は rejected malformed。足りない分は 0）。待っている間の arm は rejected unavailable（1 回に 1 つ）。**arm していない間の転送は
  MOSI を捨て、transactions と errors を数える**。**MISO は tx の外（未 arm、tx を使い切った後）では 0**。CS が有効になってから SCK が
  1 回も来ずに無効に戻ったもの（0 ビット）は転送とみなさない: 何も積まず、transactions も errors も数えず、arm は待ち続ける。
- arm の success は、次の転送に tx を出せる状態になってから返す。その後に始まる転送（cs_setup_ns を守るもの）は、この arm で答えられる。
  設定済みでもその状態にできなければ何もarmせずにcompleted failedで答える（固定部分なし、[TLV]）。
- **state 1の間、probe は CS が有効な間だけ MISO を駆動する。** CS が無効な間は MISO を駆動しない（プルの無い入力）。
  ただし CS が無効になってから cs_setup_ns の間は除く（下）。
  「MISO は tx の外では 0」は、state 1でCSが有効な間の転送のビットのことである。state 1のSCK、MOSI、CSは常に入力。
  state 0（configure前・初期化失敗後）ではchannelは空きの状態である（core §8）。
- 転送が CS で終わると、MOSI のバイトと、実際に来たビット数（bits、0xFFFFFFFF で止める）を列に積み、transactions を 1 増やす。data の byte 数は bits を 8 で
  割って切り上げた数で、length で止める。線の k 番目（0 から）のビットは、data の byte floor(k / 8) の、MSB が先ならビット 7 − (k mod 8)、
  LSB が先ならビット k mod 8 に置く（バイトの途中で終わった転送も同じ）。最後の byte の、来なかったビットは 0。length を超えた分は捨て、errors を 1 増やす（その転送は、bits を実際に来た数のまま、data を
  length までにして積む）。列に queue_depth 個あるときに終わった転送は積まずに捨て、errors を 1 増やす（transactions には数える）。
  errors は転送 1 回につき多くても 1 増える。read_rx はいちばん古いものを返す（無ければpending/bits/countはすべて0、dataは空でtimestampを付けない）。state 0 では rejected
  unavailable（cause 6）。pending は取り出した後の残り（255 で止める）。
- status: state 0 未設定、1 動いている。armed は転送を待っているか。queued（255 で止める）、transactions（終わった転送の累計）、
  errors（あふれ、未 arm、length 超過のどれかがあった転送の数の累計、u32）。
  transactionsとerrorsは0xFFFFFFFFで飽和し、configureまたはplan解放で0へ戻る。
- describe: ops、role_channels、max_length（1回の転送の最大byte）、max_clock_hz（確かめたSCKの上限）、features（bit0 LSBが先）、
  queue_depth（tag 0x40、u8）、modes（tag 0x41、u8。必須。bit kがmode kの対応を表す。bits 4〜7は0、値は1以上）、
  cs_setup_ns（tag 0x42、u32、下）。
- max_lengthは、最大長のarm要求（見出し10 + length 2 + count 2 + tx）とread_rx応答（見出し5 + pending 1 + bits 4 + count 2 + data）が
  どの経路のmax_frameにも収まる値にする。外部controllerの転送をread_rxで分割できるとは仮定しない。任意のtimestamp TLVは収まる場合だけ付ける。
- **cs_setup_ns**（describe の tag 0x42、u32、ns）: CS が有効になってから最初の SCK のエッジまでの時間で、MISO が最初のビットで駆動されていることを
  probeが保証する最短のもの。保証は受け付けた資源の組合せで保つ。
  ほかのfnとの同時使用でmax_clock_hzやcs_setup_nsを保てないprobeは、後から来たconfigure/attach/startなどを、
  core §8.1に従い、副作用の前にunavailable（cause 2。必要ならfnの診断TLV）で断る。
  SPIのconfigureを後から受ける場合も同じ。すべてのfnの任意の組合せの同時実行は要求しない。
  CS が有効になってからその時間の間、MISO は駆動されていないか、最初のビットを駆動しているかのどちらかで、ほかの値になることはない。CS が無効になった後は、
  同じ時間のうちに MISO は駆動されなくなる。CS が有効になったらすぐ最初のビットで MISO を駆動する probe は、この tag を付けないか 0 を宣言する。CS が有効に
  なったのを見てからソフトウェアで MISO を駆動し始める probe は、これを宣言する。host はこの値を利用者に見せる。CS が有効になってから cs_setup_ns より
  早く SCK を始める master は、最初のビットに頼れない。

## 5. `oep.fixture.i2c-controller`

probe が I2C の controller になり、DUT の target へ書き込み、読み出す。1 回の transfer は、repeated START でつないだ区切りの並びで、
最後に STOP を出すか、出さずにバスを持ったまま終わる。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x10 | configure | clock_hz(u32)、stretch_timeout_us(u32)、[TLV] | clock_hz(u32)、[TLV] | 必要 |
| 0x11 | transfer | flags(u8)、n(u8)、n × 区切り、[TLV] | result(u8)、at(u8)、index(u16)、count(u16)、data、[TLV] | 必要 |
| 0x12 | status | — | state(u8)、held(u8)、transfers(u32)、errors(u32)、[TLV] | 不要 |

- このfnのplanはrole 1と2をちょうど1つずつ、別々のchannelで持つ。満たさない組のplan_applyはunsupported（role_assignmentのtag）で断る。
  動作中（state 1）の割り当て（role, channel）の集合の変更はunavailable（cause 6）。planを解くか未設定の役割を置き換えると、
  バスを持っていれば STOP を出してから初期状態へ戻る（state 0、held 0、累計を消す）。セッションの終わりも同じ。
- SDA と SCL は**オープンドレインだけ**で駆動する（§3 と同じ）。内部のプルアップは §3 と同じく features の bit0 で宣言する。
  state 0 では駆動・内部プルアップをやめ、channel を core §8 の空きの状態にする。
- configure は controller を作り直す: バスを持っていれば STOP を出し、transfers と errors を 0 にする。この fn の plan が無いときは
  rejected unavailable（cause 6）。clock_hz 0、stretch_timeout_us 0 は rejected malformed。clock_hz は、その値以下で probe が出せる
  いちばん近い SCL の周波数を選び、応答の clock_hz で返す。min_clock_hz より低い値と max_clock_hz を超える値、max_stretch_timeout_us を
  超える stretch_timeout_us は rejected unsupported（payload `0x00`）で、状態を変えない。configureの成功はstate 1となってから返す。
  初期化に失敗したらstate 0へ戻し、completed failed（固定部分なし、[TLV]）で答える。
- **区切り**: dir(u8: 0 書き込み、1 読み出し)、address(u8: 7 ビット)、count(u16)、書き込みなら続けて data(count byte)。
  区切りは並びの順に行い、最初の区切りは START（バスを持っていれば repeated START）、続く区切りは repeated START で始める。
  address の後ろに dir を R/W のビットとして付けて送る。address は 0x00〜0x7F をすべて受ける（§3 と違い、予約されたアドレスも断らない）。
  書き込みの count 0 はアドレスの byte だけの書き込み（相手がいるかを確かめる）。読み出しは count 個を読み、最後の byte に NACK、
  それより前の byte に ACK を返す。
- **flags**: bit0 = 1 なら、すべての区切りが終わった後に STOP を出す。0 なら STOP を出さずにバスを持ったまま返し（held 1）、次の
  transfer は repeated START で始まる。n 0 で bit0 = 1 は STOP だけを出す（バスを持っていなければ何もしない）。bit1〜7 は 0（core §2.5）。
- 要求の確かめ（どれも、何もせずに断る）: state 0 は rejected unavailable（cause 6）。n 0 で bit0 = 0、dir が 1 を超える、address が
  0x7F を超える、読み出しの count 0、区切りの長さが要求に合わない は rejected malformed。書き込みと読み出しの count の合計が max_length を
  超えるなら rejected unsupported。
- **result**: 0 すべて終えた、1 アドレスの byte に NACK、2 書き込みのデータの byte に NACK、3 arbitration に負けたかバスのエラー（STOP の
  外の SDA の変化など）、4 target が SCL を stretch_timeout_us より長く low に保った。at は止まった区切りの位置（0 から。result 0 では 0）、
  index は result 2 で NACK された byte の、その区切りの中の位置（0 から。ほかでは 0）。result 2 の NACK は、その区切りの最後の byte でも
  result 2 とする（I2C は書き込みの最後の byte の NACK も許すので、host が判断する）。count と data は、止まるまでに読んだ byte を
  読み出しの区切りの順につないだもの。transfer は result によらず completed success で答える。
- result 1〜4 のときは、その場で区切りの並びをやめる。1、2、4 は STOP を出し、3 は SDA と SCL を離す。どちらも held 0。
- 1 回の transfer は core の max_op_ms に収める。収まらない長さ（clock_hz と count から probe が決める）は、max_length を超える
  ときと同じく rejected unsupported で、何もしない。
- status: state 0 未設定、1 動いている。held はバスを持っている（STOP 前）なら 1。transfers は答えた transfer の累計（n 0 で何もしなかった
  ものは数えない）、errors はそのうち result が 0 でないものの累計。どちらも 0xFFFFFFFF で飽和し、configure または plan の解放で 0 へ戻る。
- describe: ops、role_channels、max_length（1 回の transfer の書き込みと読み出しの byte の合計の上限）、max_clock_hz（確かめた SCL の上限）、
  features（bit0 内部プルアップ）、max_stretch_timeout_us（tag 0x40、u32。必須。1 以上）、min_clock_hz（configure が受ける SCL の下限。無ければ 1）。
- max_lengthは、書き込みだけの最大の transfer の要求（見出し10 + flags 1 + n 1 + 区切り 4 + data）と、読み出しだけの最大の答え
  （見出し5 + result 1 + at 1 + index 2 + count 2 + data）が、どの経路のmax_frameにも収まる値にする。

## 6. `oep.fixture.spi-controller`

probe が SPI の controller になり、CS を有効にして SCK を出し、MOSI に送ったバイトと MISO から受けたバイトを返す。1 回の transfer は、
CS の時間を指定した転送の並びで、host の往復に左右されない間隔で続けて行う。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x10 | configure | mode(u8)、bit_order(u8)、clock_hz(u32)、[TLV] | clock_hz(u32)、[TLV] | 必要 |
| 0x11 | transfer | n(u8)、n × 転送、[TLV] | n × (gap_ns(u32)、setup_ns(u32)、hold_ns(u32)、count(u16)、rx(count byte))、[TLV] | 必要 |
| 0x12 | status | — | state(u8)、mode(u8)、bit_order(u8)、transfers(u32)、[TLV] | 不要 |

- mode、bit_order、CS が low で有効なこと、ビットのとり方は §4 のとおり（controller の側から見て同じ線）。
- このfnのplanはrole 1〜4をちょうど1つずつ、別々のchannelで持つ。満たさない組のplan_applyはunsupported（role_assignmentのtag）で断る。
  動作中（state 1）の割り当て（role, channel）の集合の変更はunavailable（cause 6）。planを解くか未設定の役割を置き換えると初期状態へ戻る
  （state 0、mode と bit_order は 0、累計を消す）。
- state 1 の間、probe は CS を high に、SCK を CPOL の level に駆動する。MOSI は駆動し、転送の外の level は probe が決める。MISO は
  プルの無い入力。state 0 では channel を core §8 の空きの状態にする。
- configure は controller を作り直す（transfers を 0 にする）。この fn の plan が無いときは rejected unavailable（cause 6）。mode が 3 を
  超える、bit_order が 1 を超える、clock_hz 0 は rejected malformed。describe の modes に無い mode、features の bit0 が無いのに bit_order 1、
  min_clock_hz より低いか max_clock_hz を超える clock_hz は rejected unsupported（payload `0x00`）で、状態を変えない。clock_hz は、その値以下で
  probe が出せるいちばん近い SCK の周波数を選び、応答の clock_hz で返す。configureの成功はstate 1となってから返す。初期化に失敗したら
  state 0へ戻し、completed failed（固定部分なし、[TLV]）で答える。
- **転送**: gap_ns(u32)、setup_ns(u32)、hold_ns(u32)、count(u16)、tx(count byte)。
  - gap_ns: 前の転送で CS が無効になってから、この転送で CS が有効になるまで。並びの最初の転送では使わない。
  - setup_ns: CS が有効になってから、最初の SCK のエッジまで。
  - hold_ns: 最後の SCK のエッジから、CS が無効になるまで。
  - count 0 は、SCK を出さずに CS を有効にして無効に戻す（setup_ns と hold_ns を合わせた間、CS を有効に保つ）。
  - tx の byte を bit_order の順に MOSI に出し、同じ数の byte を MISO から受けて rx にする（§4 のビットの置き方）。バイトの間に SCK の
    周期より長い間が空くことがある。
- **時間**: probe は、頼まれた値以上で出せるいちばん近い時間を使い、実際に使った値を答えの gap_ns、setup_ns、hold_ns で返す（ns。
  並びの最初の転送の gap_ns は 0）。返す値は、その値以上の時間が線で守られたことを表す。max_delay_ns を超える値は rejected unsupported。
  頼まれた時間を守れずに短くなることは無い。
- 要求の確かめ（どれも、何もせずに断る）: state 0 は rejected unavailable（cause 6）。n 0、転送の長さが要求に合わない は rejected malformed。
  count の合計が max_length を超える、または core の max_op_ms に収まらない並びは rejected unsupported。
- 答えは転送の順に n 個を並べる。transfer は completed success で答える。transfers は終えた転送の数だけ増える（0xFFFFFFFF で飽和し、
  configure または plan の解放で 0 へ戻る）。
- status: state 0 未設定、1 動いている。mode、bit_order は configure の値（state 0 では 0）。
- describe: ops、role_channels、max_length（1 回の transfer の count の合計の上限）、max_clock_hz（確かめた SCK の上限）、features（bit0 LSBが先）、
  time_step_ns（tag 0x40、u32。必須: 時間の刻み。返す値はこの倍数とは限らない）、modes（tag 0x41、u8。必須。§4 と同じ）、
  max_delay_ns（tag 0x42、u32。必須: gap_ns、setup_ns、hold_ns が受ける最大）、min_clock_hz（configure が受ける SCK の下限。無ければ 1）。
- max_lengthは、1 つの転送で最大の transfer の要求（見出し10 + n 1 + 転送 14 + tx）と答え（見出し5 + 14 + rx）が、どの経路の
  max_frameにも収まる値にする。

ほかの fn との同時使用で clock_hz や時間を保てない probe は、§4 の cs_setup_ns と同じく、後から来た configure などを core §8.1 に従い
副作用の前に unavailable（cause 2）で断る。

## 7. `oep.fixture.pwm`

probe が出力 k に方形波を出す。周波数とデューティ（1 周期のうち high の割合）を指定し、probe が実際に出す値を返す。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x10 | set | n(u8)、n × (role(u8)、hz(u32)、duty(u16))、[TLV] | n × (role(u8)、num(u32)、den(u32)、duty(u16))、[TLV] | 必要 |
| 0x11 | status | — | n(u8)、n × (role(u8)、num(u32)、den(u32)、duty(u16))、[TLV] | 不要 |

- role は出力の番号（0 から、describe の channels 未満）。plan はそれぞれの role を多くて 1 つ、別々の channel で持つ。0 から続けて
  割り当てる必要は無い。
- **set** は並びの順に行う。hz は周波数（Hz）。duty は 1 周期のうち high の割合で、0 は常に low、65535 は常に high、その間は
  duty / 65535。hz 0 は出力を止め、その線を low に駆動する（duty は見ない）。probe はいちばん近い周波数とデューティで出し、応答の
  num / den（Hz、分数）と duty で返す。止めた出力は num 0、den 1、duty 0。
- 要求の確かめ（どれも、何もせずに断る）: n 0、長さが合わない は rejected malformed。role が channels 以上、同じ role が 2 回、
  0 でない hz が min_clock_hz より低いか max_clock_hz を超える は rejected unsupported（payload `0x00`）。plan に無い role は rejected
  unavailable（cause 6）。
- plan で取った channel は、最初の set までそれまでの状態を保つ（fixture §1 の gpio と同じ）。plan の解放で出力を止め、channel を
  core §8 の空きの状態に戻す。同じ plan のままなら、セッションが終わっても出力を続ける。
- status は、plan に有る role ごとに今の出力を返す（まだ set していない role は num 0、den 1、duty 0）。
- describe: role_channels（role ごと）、max_clock_hz（出せる周波数の上限）、min_clock_hz（下限、無ければ 1）、channels（tag 0x40、u8: 出力の数）、
  duty_bits（tag 0x41、u8: max_clock_hz でのデューティの分解能のビット数。周波数が低いほど細かくなってよい）。

## 8. `oep.fixture.counter`

probe が入力 k のエッジを、決めた時間（ゲート）のうちに数える。周波数は count を時間で割って求める。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x10 | measure | gate_us(u32)、edge(u8)、[TLV] | window_ns(u64)、n(u8)、n × (role(u8)、count(u32))、[TLV] | 必要 |

- role は入力の番号（0 から、describe の channels 未満）。plan はそれぞれの role を多くて 1 つ持つ。**counter は聞くだけなので、
  ほかの機能のピン（出力を含む）と共有してよい**（キャプチャ §1.2 のロジックと同じ）。plan を取ってもピンの電気的な状態は変わらない。
- **measure** は、plan に有るすべての role で同時に数え始め、gate_us のあいだ数えて答える。edge は 0 立ち上がり、1 立ち下がり、2 両方。
  window_ns は実際に数えた時間（probe の clock、ns）で、count はその間のエッジの数（0xFFFFFFFF で止める）。答えの並びは role の順。
- 要求の確かめ（どれも、何もせずに断る）: gate_us 0、edge が 2 を超える は rejected malformed。gate_us が max_gate_us を超える は rejected
  unsupported（payload `0x00`）。plan が無い は rejected unavailable（cause 6）。
- max_clock_hz を超える速さのエッジは数え落としてよい（数え落とした分は count に入らない）。
- describe: role_channels、max_clock_hz（数え落とさない入力の周波数の上限）、channels（tag 0x40、u8）、max_gate_us（tag 0x41、u32: core の
  max_op_ms に収まる値）。

## 9. `oep.fixture.dac`

probe が出力 k にアナログの値を出す。値と電圧の対応は describe の範囲（公称）で示す。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x10 | set | n(u8)、n × (role(u8)、value(u32))、[TLV] | — | 必要 |
| 0x11 | status | — | n(u8)、n × (role(u8)、value(u32)、on(u8))、[TLV] | 不要 |

- role は出力の番号（0 から、describe の channels 未満）。plan はそれぞれの role を多くて 1 つ、別々の channel で持つ。アナログの出力は
  pad をアナログの機能に切り替えるので、**ほかの fn の plan、線の接続、設定が使うピンとは共有しない**（plan_apply を rejected unavailable で断る）。
- **set** は並びの順に行い、その出力を value（0〜2^bits − 1）にする。電圧は公称で min_mv + (max_mv − min_mv) × value / (2^bits − 1)。
  要求の確かめ: n 0、長さが合わない は rejected malformed。role が channels 以上、value が 2^bits − 1 を超える は rejected unsupported
  （payload `0x00`）。plan に無い role は rejected unavailable（cause 6）。
- plan で取った channel は、最初の set まで出力しない（空きの状態のまま）。plan の解放で出力をやめ、channel を core §8 の空きの状態に戻す。
- status は、plan に有る role ごとに最後に set した値と、出力しているか（on 1）を返す。
- describe: role_channels、channels（tag 0x40、u8）、bits（tag 0x41、u8: 分解能）、range（tag 0x42、min_mv(i32)、max_mv(i32): value 0 と
  2^bits − 1 の公称の電圧）。

## 10. 参照する仕様

この文書の OEP のメッセージは、本文だけで定まる。バスを動かすのに使うもの:

| インターフェース | 仕様 | 使う部分 |
|---|---|---|
| `oep.fixture.i2c-target` | I2C-bus specification and user manual (NXP UM10204) | アドレスの指定（7 bit のアドレス）、ACK、clock stretching、予約されたアドレス 0x00〜0x07 と 0x78〜0x7F |
| `oep.fixture.spi-target` | 無し: SPI には正式な標準が無い | mode、CS、ビットの順は §4 が定める |
| `oep.fixture.i2c-controller` | I2C-bus specification and user manual (NXP UM10204) | START、repeated START、STOP、7 bit のアドレスと R/W、ACK / NACK、clock stretching、arbitration |
| `oep.fixture.spi-controller` | 無し: SPI には正式な標準が無い | mode、CS、ビットの順は §4、時間は §6 が定める |
| `oep.fixture.pwm`、`oep.fixture.counter`、`oep.fixture.dac` | 無し | §7〜§9 が定める |
| `oep.fixture.uart` | 無し | configure の format のとおりの線（スタートビット、LSB を先にしたデータビット、パリティ、ストップビット）（§2） |
