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
- target 側の経路も同じ。RVSWD の DMI parity は 1 bit で、壊れた応答の半分を通す（E156 / E157）。memory read や
  flash の結果は、上位の CRC か読み戻しで確かめる（[開発ガイドライン](development-guidelines.ja.md) §6-6）。

## 3.5 UART の速度は取り決める（ビルドで決めない）

**速度はビルドで決めない。** host が probe の速度を知らなくても開けるように、次の形にする（2026-09-24 の方針）。

1. probe は起動時、常に **115200 bps** で待つ。host も 115200 bps で開く。
2. host が速度の変更を要求する。probe は対応する速度を describe で宣言しておく。
3. 取り決めに失敗したら、両側とも **115200 bps に戻る**。

細部の案（未合意、実験で決める）:

- **切り替えの手順**: probe は変更の要求に今の速度で「受け付けた」と答えてから切り替える。host は新しい速度で確認の
  要求を送る。probe は一定時間（例 500 ms）内に新しい速度で正しいフレームを受けなければ 115200 bps に戻る。host も
  応答が無ければ 115200 bps に戻って確認し直す。
- **確認は最大の長さの応答で行う。** 2026-09-24、classic ESP32 + CH340 + usbip の経路は 921600 bps で host → probe は
  通ったが、probe → host の 256 byte 以上の応答で byte が落ちた（64 byte は通った）。短い確認だけでは、この経路を
  「使える」と誤って判断する。確認では宣言した最大フレーム長の応答を往復させ、CRC で確かめる。
- **戻る条件**: 無通信が一定時間続いたら 115200 bps に戻る（次の host は 115200 bps で開くため）。UART の BREAK を
  「既定の速度に戻れ」の合図にする案もある。速度は transport の状態であり、target や attach の状態（閉じても残す）
  とは分けて扱う。
- 変更後に CRC エラーが続いたら、host が一段遅い速度に取り決め直す。

## 4. target を扱う部品

- 実行して停止を待つ（`runUntilHalt` 相当）では、dcsr の ebreakm / ebreaks / ebreaku を立て、prv を M にする。
  ebreakm が無いと最後の ebreak が mtvec に飛んでアプリケーションが再起動する（V003、2026-09-22）。prv が U のままだと
  割り込みを止められない（ArduinoCore-CH32 のスケッチは V3B/V4 で U モードで動く）。割り込みは host が mstatus = 0
  を渡して止める（[flash の実験](../experiments/flash-primitives/README.ja.md)）。
- 連続した語の読み書きは、DM の autoexec で回す（読み: E156 の reader、書き: その逆）。DATA1 に残るアドレスで
  実行回数を数え、取りこぼしや二重実行を見つける。
