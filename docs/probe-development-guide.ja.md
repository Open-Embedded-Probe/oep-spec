# Open Embedded Probe — probe 開発ガイド

状態: **仮置き**（2026-09-24 起草）。protocol が probe に求めることを、実装で守るための具体的なやり方を集める。
実測が増えるたびに更新する。host 側は [host 開発ガイド](host-development-guide.ja.md)。

## 1. 開閉でリセットしない・状態を戻さない

- transport を開閉してもリセットしない。DTR / RTS の変化でリセットする回路（ESP32 の自動リセット回路、
  USB-Serial/JTAG）を持つボードは、host がそれを避けて開く（host 開発ガイド §1）。probe 側は、開閉で自分から
  再起動しない。
- **DTR に頼らない。** arduino-pico の USB シリアルは DTR が下りていると出力しない（実測、2026-09-24）。
  `Serial.ignoreFlowControl()` などで、host の開き方が違っても通信が止まらないようにする。
- **セッションを失っても状態を戻さない。** host の切断やロックの期限切れで、attach、ピン、線の状態（RVSWD の
  アイドル時のレベルなど）を戻さない。戻すのは明示的な disable / release のときだけ
  （[セッションと排他](session-and-exclusivity.ja.md)）。以前の「host を見失ったら target をリセットする」
  「切断で pin を入力に戻す」はやめる。
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

## 3.5 UART の速度は取り決める（ビルドで決めない）

**速度はビルドで決めない。** host が probe の速度を知らなくても開けるように、次の形にする（2026-09-24 の方針）。

1. probe は起動時、常に **115200 bps** で待つ。host も 115200 bps で開く。
2. host が速度の変更を要求する。
3. 取り決めに失敗したら、両側とも **115200 bps に戻る**。

**設定できる速度は能力として開示する。** 速度を決める要素は 3 つあり、知っている者が違う。

| 要素 | 違いの例 | 知っている者 |
|---|---|---|
| probe の MCU の UART | ESP32 は分周が細かく数 Mbps までほぼ任意。刻みの粗い MCU もある | probe。describe で宣言する（`uart_rates`、[能力の宣言モデル](capability-declaration-model.ja.md) §5） |
| USB-UART の変換チップ | CH340 / CH343 / CP2102 / FT232 で、設定できる速度の一覧と上限が違う | host。USB の VID:PID から分かる。probe は自分の手前に何があるかを知らない |
| 経路の実力（変換チップのバッファ、usbip など） | CH340 + usbip は 921600 bps で長い応答を落とした（2026-09-24） | 誰も事前には知らない。試して確かめる |

host は、probe の宣言と変換チップの対応の重なりから候補を選び、確認で経路の実力を確かめる。

- **`uart_rates` は設定できる速度の一覧で宣言する。** 細かい刻みは扱わない（範囲と刻みの形は採らない）。
- **速度の変更は任意の機能で、後回しにする。** 必要になるのは、ESP32 のようにメガバイト単位のイメージを書く場合
  くらいで、それ以外は 115200 bps のまま待てばよい。速さが要る場合は、USB-UART より速い transport（probe の
  ネイティブ USB、IP 経由）を選ぶ手もある。
- **仕様化するときは、事故を防ぐために時間の規則を細かく決める。** 速度が食い違ったまま残ると、次の host が
  115200 bps で開いても通じない。決める項目:
  - 切り替えの手順: 誰がいつ切り替えるか（probe は今の速度で「受け付けた」と答えてから切り替える、など）。
  - 確認: 新しい速度で何を往復させれば「使える」とするか。**最大の長さの応答で確かめる**（2026-09-24、classic
    ESP32 + CH340 + usbip は 921600 bps で host → probe は通り、probe → host の 256 byte 以上の応答で byte が落ちた。
    64 byte は通った。短い確認では誤って「使える」と判断する）。
  - 確認が来ないときに 115200 bps へ戻るまでの時間（probe 側と host 側）。
  - 使っている最中に戻る条件: 無通信の時間、CRC エラーの回数、UART の BREAK を合図にするか。
  - 戻ったことを host がどう知るか。
  - 速度は transport の状態で、target や attach の状態（閉じても残す）とは分けて扱うこと。

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
  動いているスケッチから 28 回中 0 回。最も遅い半周期（500 ns）なら 28 回中 28 回で、WCH-LinkE と同じ）。
  - リセットは最も遅い速度で行い、hart が止まってから速度を測り直す。
  - 測り直しには wake を使わない（RVSWD の wake は target をリセットする）。遅い速度から速めていき、最初に落ちたら
    一つ遅い速度に戻して確かめ直す。
  - 読み出しが化けると、DMSTATUS が「動いている」ように見える。version（下位 4 bit = 2）が合わない値は雑音として扱う。
  - 2026-09-22 に X035 で見た「ndmreset の後、書き込みを一回おきに受け付けない」「4〜5 % でリセットベクタに留まる」も、
    同じ原因だった可能性がある（未確認）。
