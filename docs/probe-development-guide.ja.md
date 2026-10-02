# Open Embedded Probe — probe 開発ガイド

状態: **実務（規範ではない）**（2026-09-24 起草、2026-09-26 に規範の [OEP core](oep-core.ja.md) と `oep-if-*.ja.md` に
合わせて更新）。規範が probe に求めることを実装で守るための具体的なやり方と、実測で分かった罠。規範と食い違えば規範が
正しい。host 側は [host 開発ガイド](host-development-guide.ja.md)。

## 1. 開閉でリセットしない・状態を戻さない

- transport を開閉してもリセットしない。DTR / RTS の変化でリセットする回路（ESP32 の自動リセット回路、
  USB-Serial/JTAG）を持つボードは、host がそれを避けて開く（host 開発ガイド §1）。probe 側は、開閉で自分から
  再起動しない。
- **DTR に頼らない。** arduino-pico の USB シリアルは DTR が下りていると出力しない（実測、2026-09-24）。
  `Serial.ignoreFlowControl()` などで、host の開き方が違っても通信が止まらないようにする。
- **transport の開閉では状態を変えない。** 経路を閉じても、attach、ピン、線の状態はそのまま。資源を外すのは、core §9 の
  寿命の規則のときだけ（明示の release / detach、lease の期限切れと force で奪われたときの、そのセッションの分）。
  外すときも target をリセットしない。解いたピンは設定の idle の状態（既定は Hi-Z）にし、駆動し続けない（core §8）。
- 開くとどうしてもリセットされる probe は、probe 全体の describe で `resets_on_open` を宣言する。

## 2. 送受信のバッファ

- **受信バッファは、宣言した window（未処理のまま受け付ける byte 数）より大きくする。** 送信バッファは、
  window 分の要求に対する応答の合計より大きくする。足りないと、probe が長い処理（flash のローダーの実行、
  スキャン）をしている間に届いた byte がこぼれる。
- 既定値のままにしない。ESP32 の Arduino の `HardwareSerial` は受信 256 byte が既定で、512 byte のフレーム 1 つにも
  足りない。今の probe は `setRxBufferSize(8192)` / `setTxBufferSize(8192)` にしている（classic ESP32 の V003 用、
  P4 の X035 用）。
- P4 の USB-Serial/JTAG は、outstanding byte が device の ring（8 KiB）を超えるとデータを落とした（E155）。window は
  device の ring の半分（4 KiB）で宣言している。
- 長い処理の間も受信を吸える作り（割り込み・DMA で受ける、処理を分けて poll を回す）にする。
- **受信は 1 byte ごとに重い処理をしない。** frame の読み取りが 1 byte ごとに時計（ESP32 の `millis()`）を読むと、
  1 byte 約 1.2 µs かかり、HS USB でも host → probe が 0.8 MB/s で頭打ちになった（2026-09-25、P4）。届いている分を
  まとめて読み、時計は 1 回だけ読み、本文はまとめて写す（oep-probe-arduino の `FrameReader::feed`）。Arduino の
  `Stream::readBytes` の既定の実装も 1 byte ごとに時計を読むので使わない。
- **宣言した max_frame の要求を丸ごと受けられるようにする。** 受信バッファ（frame 1 つ分）と、USB などの受け口の
  ring（下の層が 1 回に置く量 × 2 以上）の両方。足りないと frame の途中がこぼれ、以後の区切りがずれる
  （P4 の direct build で、8 KiB の ring に 16 KiB の要求が来てこぼれた）。
- 線の速さは core の link_source / link_sink（[core](oep-core.ja.md) §12）で測れる。受信・送信の経路を変えたら測り直す。
- **vendor bulk の OUT を、ZLP で終わる大きな転送として受けない。** host は packet の倍数の書き込みの後に ZLP を続ける
  （core §3.1）が、ESP32-P4（TinyUSB の dwc2、EspUsbDevice の direct build）で 16 KiB の OUT の転送を張り ZLP を終わりの印に
  すると（`CFG_TUD_VENDOR_RX_NEED_ZLP=1`）、ちょうど 512 byte の倍数で終わる要求の完了が次の OUT まで遅れ、probe は答えなかった
  （2026-09-30、X035 の治具、1024 byte の write_block）。packet ごとに受ければ（`=0`）、どの packet もすぐ届き、ZLP は長さ 0 の
  完了として読み飛ばされる。

## 2.5 OEP の口にほかのものを出さない・誰も読まない口で止まらない

2026-09-25 の P4 の試作で 2 回踏んだ。

- **OEP の口にログを出さない。** ESP-IDF のログ（LEDC の設定エラーなど）が、OEP と同じ USB-Serial/JTAG に出てフレームを
  壊し、host は応答が来ないとみなした。OEP をその口で話す probe は、`esp_log_level_set("*", ESP_LOG_NONE)` などでログを
  止める。
- **誰も読んでいない口への書き込みで loop を止めない。** OEP を HS の vendor bulk に移し、USB-Serial/JTAG には 2 秒ごとの
  状態の行だけを出していたところ、その口を誰も開いていないと HWCDC の書き込みがタイムアウトまでブロックし、loop が
  1.8 秒止まった。パイプラインの読み出しと通知が毎回 1.83 秒遅れ、1 回ずつの往復（0.5 ms）は loop が動いている間に
  収まるので気づきにくい。書き込みがブロックしない設定（`Serial.setTxTimeoutMs(0)`）にするか、書かない。

## 3. 信頼性のない経路には CRC と再送

- USB（CDC、vendor bulk）はデータを保証するが、**USB-UART の変換チップを挟む経路は保証しない。** probe と変換
  チップの間の UART、変換チップ自身、usbip で byte が落ちる・化けることがある。
  - 2026-09-22: 変換チップが長い連続送信で byte を落とした（classic ESP32 の V003 治具）。
  - 2026-09-24: 同じ治具で 16 KB の読み戻しが一度化け、**エラーにならずに通った**（v0 のフレームには CRC が無い）。
    読み直すと flash は正しかった。
- このような経路では、フレームに CRC を付け、壊れたフレームは捨てて再送する（[UART binding の信頼性モデル
  候補](uart-reliability-model.ja.md)）。host は「応答が来た」ことを正しさの根拠にしない。
- 実装（2026-09-24）: oep-probe-arduino の `CobsReader` / `writeCobsFrame`（COBS + CRC-16/CCITT-FALSE、仮置き）。
  V1 の endpoint に `Framing::kCobsCrc` を渡す。classic ESP32 の V003 用 probe がこれを使う。
- target 側の経路も同じ。RVSWD の DMI parity は 1 bit で、壊れた応答の半分を通す（E156 / E157）。memory read や
  flash の結果は、上位の CRC か読み戻しで確かめる（[開発ガイドライン](development-guidelines.ja.md) §6-6）。

## 3.5 UART bridge の速さは 115200 固定

UART bridge（probe の UART を USB-UART の変換チップで出したもの）の probe は、**115200 bps 固定**にする（2026-09-29 の決定）。

- 設定で変えられるようにすると、忘れたときに入れなくなる。自動の速度検出は、生のバイトと OEP が混ざる口（core §3.4）では危うい。
- dmseq のコンソールと書き込みには足りる（classic ESP32 + CH340 の V003 治具で、14 KB の書き込み + 確認が 4.1 秒）。速さが要る
  なら、USB CDC / USB-Serial/JTAG / vendor bulk を持つ probe を使う。USB CDC と USB-Serial/JTAG では baud は数字が渡るだけで、
  速さに関係しない。
- 参考（2026-09-24、速度ごとにビルドし直した実験用の probe）: 460800 bps から先は SWIO の側が上限で速くならず、230400 は
  変換チップの経路で通らず、2 Mbps 以上は大きなフレームで壊れた（`experiments/uart-binding/uart_rate.py`）。

## 3.6 シリアルの口の共用の作り

core §3.4 の規則を守るための作り（2026-09-29）。

- **受信**: 口ごとに 1 つの読み手が、0x00 の外のバイトはすぐ生のバイトの行き先（bind、[probe の設定](oep-if-probe-config.ja.md)
  §1.2）へ渡し、0x00 から次の 0x00 までを候補としてためる。候補が解けないか CRC が合わない、または 200 ms 途切れたら、ためた分を
  生のバイトとして渡す。候補のバッファは max_frame の COBS の長さ + 2 を持つ（超えたら、その時点で生のバイトとして渡す）。
- **送信のキュー**: 口ごとに送信を 1 つにまとめる。単位はフレーム丸ごとか、生のバイトの塊（64 byte 程度）。1 つの書き手が単位を
  割らずに出す。フレームは塊より先に出してよい。塊は位置つきのストリームから読むので、口が詰まっても捨てずに待てる（位置を
  進めないだけ）。Arduino の `HardwareSerial::write` は呼び出しの単位でしか排他しないので、endpoint がフレームを `Serial` に
  直接書き、別の処理が同じ口に生のバイトを書く形にしない。
- **口に OEP 以外のものを書かない**（§2.5）。ログは OEP のフレームを壊す。生のバイトとして出してよいのは bind の流れだけ。

## 3.7 probe の再起動の抑止

口を開閉しても probe が再起動しないようにする（§1）。

| 口 | 止め方 |
|---|---|
| ESP32-P4 などの USB-Serial/JTAG | `USB_DEVICE_CHIP_RST_REG` の `USB_UART_CHIP_RST_DIS`（bit2）を立てる。arduino-esp32 3.3.12 の HWCDC に API は無いので、レジスタに直接書く |
| TinyUSB の CDC（arduino-esp32 の `USBCDC`） | `enableReboot(false)`（DTR / RTS の並びと 1200 baud の touch での再起動を止める） |
| EspUsbDevice の CDC（P4 の HS） | 元から持たない |
| classic ESP32 などの UART bridge | 変換チップの先の自動リセット回路なので、firmware では止められない。host が DTR と RTS を両方立てて開く（host 開発ガイド §1）。止められないものは describe の resets_on_open で宣言する |

## 3.8 推奨の USB の作り（VID:PID、iProduct と HID の口）

ネイティブ USB を持つ probe（ESP32-P4 の HS の口、RP2350 など）の推奨の形:

- **VID:PID は規範ではない**。今は仮の USB の ID（ボードの既定の VID:PID）で動かしていて、配布には使えない。専用の PID を取得できたら、
  それに切り替える予定。**host の discovery は USB の
  device の名前（iProduct が `OEP` で始まる）で OEP の probe を見分ける**ので、iProduct を `OEP` で始める（恒久の規範、core §3.3。PID を
  取っても名前での判定は変わらない）。device の中の口は interface の種類で決まる（core §3.3: CDC はすべてシリアルの口）。この形で列挙する probe
  は、fn 0 の describe の discoverable を 1 にする（USB-Serial/JTAG のように別の口から開かれても、host がそれで分かる）。
  - 参照 probe（ESP32-P4、EspUsbDevice 2.5.1）は、VID:PID は仮に 303a:0002（arduino-esp32 の TinyUSB の既定）、iProduct を
    「OEP probe (P4 HS)」にしている（CDC の「OEP console」は表示のための名前）。
- interface は **vendor bulk（OEP）、HID（OEP）、CDC（シリアルの口）** の組（core §3.3）。
  - vendor bulk は host の主な経路（速い）。
  - HID は、他の道具が vendor や CDC を握っていても読める口で、discovery がロックなしの describe / get でスロットと状態を読むのに
    使う。OS のドライバも要らない。
  - CDC は IDE や端末から見えるシリアルの口。OEP も受けるが（core §3.4）、主にはコンソールを流す。
- fn 0 の describe の transport に、実際に出している経路をすべて並べる。unit_id はどの経路からでも同じ値を返す。

## 3.9 ロックの奪い方に probe が答えること

host は transport の数でロックの奪い方を決める（host 開発ガイド §2）。probe は次を守る。

- transport の一覧を正しく出す（シリアルの口が 1 つだけの probe は、そう見えるように）。
- lease の期限を守って空ける（期限切れの後始末、core §9）。lock_state の残り時間を正しく返す。
- 1000〜60000 ms の lease の要求は、そのまま受ける（lease の範囲の規則は core §6.4）。

## 4. target を扱う部品

- 実行して停止を待つ（`runUntilHalt` 相当）では、dcsr の ebreakm / ebreaks / ebreaku を立て、prv を M にする。
  ebreakm が無いと最後の ebreak が mtvec に飛んでアプリケーションが再起動する（V003、2026-09-22）。prv が U のままだと
  割り込みを止められない（ArduinoCore-CH32 のスケッチは V3B/V4 で U モードで動く）。割り込みは host が mstatus = 0
  を渡して止める（[flash の実験](../experiments/flash-primitives/README.ja.md)）。
- 連続した語の読み書きは、DM の autoexec で回す（読み: E156 の reader、書き: その逆）。DATA1 に残るアドレスで
  実行回数を数え、取りこぼしや二重実行を見つける。
- **リンクの速度は、決めたときの target のクロックでしか保証されない。** attach で測って選んだ速度は、スケッチがクロックを
  上げた後の値である。リセットすると CH32 は既定の遅いクロックに戻り、その速度では書き込みが化ける。ndmreset と一緒に
  保持した haltreq が失われ、hart はリセットベクタで止まらずにイメージへ走り込んだ（2026-09-24、ESP32-P4 → CH32X035、
  動いているスケッチから 28 回中 0 回。最も遅い半周期（500 ns）なら 28 回中 28 回。WCH-LinkE + ch32rv は別の X035
  （C8T6、LinkE `FC928F068181` の先。P4 の治具の F8U6 とは UID が違い、線も共有していない）で 5 回中 5 回）。
  - リセットは最も遅い速度で行い、hart が止まってから速度を測り直す。attach under reset も同じ（リセットを放す前に
    最も遅い速度にする。保持中の attach が通らなかったときも。CH32L103 は NRST の間は haltreq を保持せず、放した直後の
    問い合わせで捕まえている。直す前は 20 回中 16 回、直した後は 60 回中 59 回がリセットベクタ）。
  - 測り直しには wake を使わない（RVSWD の wake は target をリセットする）。遅い速度から速めていき、最初に落ちたら
    一つ遅い速度に戻して確かめ直す。
  - 読み出しが化けると、DMSTATUS が「動いている」ように見える。version（下位 4 bit = 2）が合わない値は雑音として扱う。
  - WCH-Link は DMI を固定の速度（400 kHz / 4 MHz / 6 MHz）で回し、target のクロックに合わせて詰めないので、
    この罠に当たらないと読める。ch32rv の DMI 直叩きの reset-halt（0x80000003 → 0x80000001）は、LinkE / CH549 経由で
    PLL 96 / 72 MHz → HSI 8 MHz に戻る V203 / V307 / V103 で各 5/5 捕まえた（ch32rv、2026-09-24。reset で dcsr.ebreakm が
    消えることも確かめてあり、先に走った hart を見誤ってはいない）。
  - 2026-09-22 に X035 で見た「4〜5 % でリセットベクタに留まる」も同じ原因と見られる。同じ probe で、リセットの速度の
    切り替えだけを外すと 100 回中 3 回留まり、入れると 100 回中 0 回だった（2026-09-24）。「ndmreset の後、書き込みを
    一回おきに受け付けない」は確かめていない。E159（2026-09-22）の「reset-halt から resume すると約 40 % で SysTick が止まる」
    は、修正後の probe では再現しなかった（reset-halt → resume、reset とも 20 回中 20 回で millis が進んだ。
    `experiments/flash-primitives/e159_recheck.py`）。
- **RVSWD のアイドル中の線の向きは target の性質で、CH32X035 と CH32L103 で逆になる**（2026-09-24、OEP 側での観察。
  `experiments/flash-primitives/idle_matrix.py`。hart を止め、host 側で d だけ待ってから、止まったまま同じ dpc かを見た。各 5 回）。

  | target（probe） | 休ませ方 | 1 ms | 5 ms | 20 ms | 100 ms 〜 2 s |
  |---|---|---|---|---|---|
  | X035F8U6（ESP32-P4） | 両方 high（今のビルド） | 保つ | 保つ | 保つ | 保つ |
  | X035F8U6（ESP32-P4） | SWCLK low | attach 自体が通らない | | | |
  | L103C8T6（RP2350） | SWCLK low（今のビルド） | 保つ | 保つ | 保つ | 保つ |
  | L103C8T6（RP2350） | 両方 high | 保つ | 保つ | DM がリセットされ hart が走る | 同左 |

  - probe は 300 µs を超える休止の後、最初の転送の前に線を立て直している（`reviveIfIdle`）。L103 が high でも 5 ms まで
    保つのはそのためと見られる（2026-09-23 の測定では、立て直しなしで 1 ms で落ちた）。
  - **WCH-Link は、どの target でも両方 high で休ませる**（2026-09-24。target 自身に自分の SWDIO / SWCLK の INDR を
    読ませ、ch32rv の dmseq モニタの間に 20 µs 以上動かなかった区間のレベルを集計した。`pin_idle_obs.ino`、
    `linke_pin_obs.py`）。

    | target（リンク） | 休ませ方 | 休止の最長 |
    |---|---|---|
    | L103C8T6（LinkE） | 両方 high | 36 ms |
    | X035C8T6（LinkE） | 両方 high | 5 ms |
    | V203 / V307（LinkE） | 両方 high | 5〜13 ms |
    | V103（CH549 のリンク） | 両方 high | 6.5 ms |
    | V003 / V006（LinkE、SWIO） | high | 4〜14 ms |

  - LinkE は休止明けに wake を送らず、いきなりスタート条件からフレームを 1 つ送る（`burst_obs.ino`、L103。サンプリングが
    5.8 µs に 1 回と遅いので、クロックの周期は目安にならない）。
  - つまり L103 は、両方 high で 36 ms 休ませても LinkE とは通信を続けられる。OEP の probe で両方 high にすると 20 ms で
    DM がリセットされるのは、休ませ方の向きではなく、こちらの休ませ方のどこかが違うためと見られる。
    - 休止明けの wake は原因ではなかった（wake なしの再同期に替えても同じ）。
    - Pico の治具の L103 に自分のピンを読ませる観察（`rest_obs.ino`、`oep_rest2.py`）は、使えないと分かった。
      プローブが静かになってまもなく hart が止まり（休止を待つループの回数が休止の長さによらず一定）、休止中の
      ピンの値も 1 / 2 / 3 と揺れた。止めた hart が休止のあと走り出した観察と表裏で、この組み合わせ（RP2350 の probe → L103）では休止中に
      DM が雑音を DMI の書き込みとして受け取っている可能性がある（未確認）。以前に書いた「休止中に SWDIO = low、
      SWCLK = high と読んだ」も、この観察の上なので当てにならない。
    - 切り分けには、線を外から見る（P4 の capture を Pico と L103 の間につなぐ）か、配線を整える必要がある。
  - 同じ L103 で WCH-Link と OEP の probe の休ませ方をそろえられれば、target ごとの設定は要らなくなる見込みがある。
  - いまは probe のビルドの設定（治具のプロファイル）で持っている。rvswd は WCH の線（名前で特化が分かるインターフェース、
    core §13 の規則 8）なので、target ごとの休ませ方をこの線の規則として持ってもよい。1 台の probe が両方の target を相手に
    するようになったら、host が attach で指定する形を考える。
- **resume と run は出し直さない**（oep-if-debug §4.2、§4.4）。CH32V006 の 1 回で出ない resumereq、CH32L103 の allresumeack
  無しは host が扱う。以前 probe が dpc を見て出し直していたのは、汎用の名前の riscv-dm に CH32 の知識を入れる形だったので
  やめた（2026-09-26）。
- **1 語ごとの DMI の記録（最終アクセス時刻の `micros()` など）を、autoexec のブロックのループから外すのは見送った**
  （2026-09-25）。ESP32-P4 → X035 の読み出しは 122.6 → 133.2 KiB/s（約 9 %）速くなり、書き込みは変わらなかった。
  ところが RP2350 → L103 では、smoke 全体の中で毎回 1〜2 本のスケッチがコンソールから 0 文字になった（12/14、13/14、
  13/14。元のループに戻すと 14/14 が 2 回）。原因は突き止めていない。フレームの間隔が詰まったことが、RP2350 の probe → L103 の
  組み合わせに効いている可能性がある（L103 の配線は他の target と同じ。配線のせいではない）。

## 5. 参照の firmware が宣言に使っている値（規範は決めない所）

- **model**（core §7.5 の 0x41）: チップの名前をハイフンなしの小文字で（`esp32p4`、`esp32`、`rp2040`、`rp2350`）。Arduino の
  profile の名前と同じにしている。
- **max_op_ms**（0x4D）: 10000。
- **chip**（0x4C）: `esp32p4 v1.3`、`rp2350 v2` のように、型番とリビジョン。
- **UART bridge の起動時の速さ**: 115200（§3.5。core §3.5 の port_speed はこの速さが戻り先）。
