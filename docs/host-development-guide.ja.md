# Open Embedded Probe — host 開発ガイド

状態: **仮置き**（2026-09-24 起草）。protocol には「probe をリセットせずに開く」までを置き、その具体的なやり方を
ここに書く。実測が増えるたびに更新する。

## 1. probe をリセットせずに開く

### 1.1 結論

- **DTR と RTS を立てたまま開く（pyserial の既定）。** 実測したすべての probe でリセットしなかった。
- **DTR を下ろすなら、RTS を先に下ろす。** DTR を先に下ろすと RTS=1・DTR=0 を一瞬通り、ESP32 の自動リセット回路が
  EN を下げる。
- 閉じるときは何もしなくてよい（Linux の hupcl で両方同時に下りても、リセットしなかった）。
- DTR を下ろしたまま使わない。RP2350（arduino-pico）は DTR が下りている間、出力を止める。

### 1.2 実測（2026-09-24、Linux、起動ごとに変わる番号を 100 ms ごとに出す sketch で開閉を 3 回ずつ）

| USB 変換 | ボード | pyserial 既定 | DTR=1 RTS=0 | DTR=0 で開く（pyserial） | esp-idf-monitor の順序 | その逆順 |
|---|---|---|---|---|---|---|
| USB-Serial/JTAG | P4 ×2 | リセットなし | リセットなし | リセット | リセットなし | リセット |
| CH340 + 自動リセット回路 | classic ESP32 | リセットなし | リセットなし | リセット（RTS=1 ならリセットのまま） | リセットなし | リセット |
| CH340 + 自動リセット回路 | P4 | リセットなし | リセットなし | リセット（起動が遅く、0.8 秒の間は出力が見えない） | リセットなし | リセット |
| CH343 + 自動リセット回路 | S3 | リセットなし | リセットなし | リセット（RTS=1 ならリセットのまま） | リセットなし | リセット |
| RP2350 のネイティブ USB（arduino-pico 6.1.1、Pico SDK の USB スタック） | Pro Micro RP2350 | リセットなし | リセットなし | リセットなし（出力が止まる） | — | — |

- 「DTR=0 で開く」がリセットするのは DTR=0 そのもののせいではない。Linux ではカーネルが開くときに DTR と RTS を
  両方立て、pyserial はそのあと **DTR を先に、RTS を後に** 書く（`serialposix.py` の open）。`dtr=False` は途中で
  RTS=1・DTR=0 を通る。
- esp-idf-monitor 1.10（`serial_reader.open_serial`）は、開く前に両方を立てた状態にし、開いてから **RTS を先に**
  下ろし、次に DTR を下ろす。最後は両方下りた状態になるが、リセットはしない（実測した 4 台とも）。
- esp-idf-monitor の RTS の設定は、RTS を変えるたびに DTR も書き直す。Windows の usbser.sys は、両方を書かないと線の
  状態を送らないためである。
- RP2350（arduino-pico）は 1200 bps で開いて閉じると BOOTSEL に入る。probe を 1200 bps で開かない。
- Windows と macOS では測っていない（Windows も同じという報告はある）。

## 1.5 UART の速度

USB-UART の変換チップ越しの probe は、常に 115200 bps で開く（ビルドで決めた速度を host が知っている前提にしない）。
速度の変更は任意の機能で後回し（[probe 開発ガイド](probe-development-guide.ja.md) §3.5）。メガバイト単位の転送
（ESP32 のイメージなど）以外は 115200 bps のまま待てばよい。速さが要るなら、より速い transport（probe のネイティブ
USB、IP 経由）を選ぶ。以下は速度の変更を仕様化したときの指針。

- 候補は、probe が宣言した `uart_rates` と、**変換チップが設定できる速度**の重なりから選ぶ。変換チップは USB の
  VID:PID で見分け、host が対応表を持つ（CH340 / CH343 / CP2102 / FT232 などで一覧と上限が違う。表の中身は未作成）。
- 重なりの中でも、経路（変換チップのバッファ、usbip）が通すとは限らない。最大の長さの応答を往復させて確かめ、
  通らなければ一段遅い速度に下げる。

## 2. 排他

- OS やライブラリの排他を使えるなら使う。2 つ目の open が早く失敗し、利用者に「使用中」と伝えられる。
  - Windows の COM ポート、libusb / WinUSB の claim は OS が排他する。
  - Linux の tty は開けてしまう。pyserial なら `exclusive=True`（flock による協力型のロック。screen や minicom の
    ようにロックを見ないツールには効かない）。
- **それでも本当の排他は session_id で行う**（[セッションと排他](session-and-exclusivity.ja.md)）。BUSY が返ったら、
  残り時間を添えて「使用中」と表示する。force は利用者の確認を挟んで使う。

## 2.5 応答の対応付け（必須）

- **corr が合わない応答は受け取らず、読み捨てて同期し直す。** usbipd 越しでは、取り消した転送の残りが次の応答として
  現れたことがある（ch32rv、dump が 64 byte ずれる・flash が 1 回おきに失敗）。USB CDC のフレームには CRC が無いので、
  corr の照合がこの防御になる。

## 3. session_id

- open のたびに新しい乱数（u32）を選ぶ。連番や固定値にしない。
- **one-shot CLI は session_id を probe の個体ごとに保存する。キーは `oep.core` の describe が返す個体の番号
  （unit_id）にし、USB のシリアル番号は使わない**（CH549 の Link の fw 2.6 は仮の `0001A0000000` を返し、CH340 は
  シリアル番号を持たない）。
  次のコマンドで同じ ID を使い、通れば前のコマンドのあと誰も触っていない。「セッションなし」が返ったら、boot_id を
  見て再起動か他の host かを区別し、attach の状態と target の ID を確かめ直す。
- 対話型の CLI や Monitor のように長く開いておくものは、keepalive か普段の要求でロックを保つ。確認のプロンプトで
  止まる間も keepalive を打ち、破壊的な手順の前ごとにセッションが生きているか（`no session` / `locked` にならないか）
  を確かめる。
- **Monitor は入力を送る間だけロックを取る**（open → write → end）。読み出しはロック不要なので、Monitor がロックを
  握り続けると、別の端末の書き込みが `locked` で失敗する（開発で最もよくある組み合わせ）。
- 終わるときは end を送る（送らなくても期限で下りる）。

## 4. 長い操作

- どの操作も PENDING を返しうるものとして書く。PENDING が返ったら status を投げ、進捗 (done, total) を表示する。
- host が落ちても操作は続く。同じ session_id で戻れば最後の結果を取り出せる。新しい session_id で open すると
  最後の結果は消える。
- 応答が来ないときに要求を再送すると、二重実行になりうる（フレームにシーケンスが無い binding の場合）。
  消去や書き込みのような操作は、再送の前に status や読み戻しで状態を確かめる。

## 4.5 flash の書き込み（target の知識は host）

- **ローダーは「書き込み方式 × 命令セット」で選ぶ。** 似た系統から流用しない。X035 用のローダー
  （experiments/flash-primitives/x035_loader.S）は t3 / t4 を使うので、RV32E（V003 / V00x）では不正命令になる。
  例: V20x / V30x は direct（ページの開始）、X035 / L103 は 256 byte の buffered（RV32IMAC）、V00x は 256 byte の buffered
  だが RV32EC、V103 は half-word の書き込み + commit、V003 は wlink の 64 byte（RV32EC）。device-data の
  `flash_program_method`（`buffer_load_bits`）、`sram_bytes` で引く。
- **ローダーは走らせる前に読み戻す。** 化けたローダーは flash コントローラを動かしながら ebreak まで届き、以後の全ページを
  壊す（2026-09-24、飛び線の CH32L103 で 38 ページ書き直しても合わなかった）。probe の ack は「その内容が入った」証明に
  ならない。書き込んだ flash も必ず読み戻す（target 側で CRC を計算するローダーを使えば、遅い経路で速くなる）。
- **消去後の値は 0xff とは限らない。** V20x / V30x / V407 / X315 / H417 は `0xe339e339` を読む。「全部 0xff のページは
  飛ばす」最適化や blank check は device-data の `erased_word` で判定する。
- **ELF の segment はページ単位に併合してから書く。** `.data` の初期値は `.text` の直後に、ページの途中から始まる別の
  segment として来る。
- **読み出し保護（RDP）を先に読む。** WCH-Link は保護された target を書くとき、黙って保護を外す（option を含む全消去）。
  host 主導の書き込みでは、明示の指示が無ければ止める。
- **動いているウォッチドッグの上から書かない。** IWDG は hart を止めても数え続け、書き込みの途中で target をリセット
  する（2026-09-24、system_selftest のあとの CH32L103）。書く前に `riscv-dm` の reset（最初の命令の前で止める）を使う。
- target の識別: OEP の probe は WCH-Link のような系統の番号を返さない。host は marchid / mimpid（CSR）→ core の世代 →
  ESIG の chip_id / flash 容量 / UID（番地は DB から）の順に読む。

## 5. コンソール

- Arduino の書き込みのあとの Monitor は「最後の reset マークから」読む。前回の未取得のログが流れない。
- Monitor が一度閉じて戻るときは、前回読んだ位置から読む。
- 応答の先頭の位置が要求より進んでいたら、その差が失われた量である。表示に残す。
- 表示用の時刻は受け取った時刻を使う（probe は byte ごとの時刻を持たない）。
