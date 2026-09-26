# Open Embedded Probe — host 開発ガイド

状態: **実務（規範ではない）**（2026-09-24 起草、2026-09-26 に規範の [OEP core](oep-core.ja.md) と `oep-if-*.ja.md` に
合わせて更新）。host を書く人への具体的なやり方と、実測で分かった罠。規範と食い違えば規範が正しい。

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
- 実測（2026-09-24、classic ESP32 + CH340 の V003 probe、COBS + CRC、usbipd 越し。probe は速度ごとにビルドし直した
  実験用のもので、設計としてビルドで決める案ではない。`experiments/uart-binding/uart_rate.py`）:

  | 速度 (bps) | DMI の往復 | ブロック読み出し | 14 KB の書き込み + 確認 | 結果 |
  |---:|---:|---:|---:|---|
  | 115200 | 5.7 ms | 9.1 KiB/s | 4.1 秒 | 3 回とも通る |
  | 230400 | — | — | — | **5 回とも失敗**（応答なし・CRC 不一致） |
  | 250000 | 4.2 ms | 15.4 KiB/s | 2.8 秒 | 3 回とも通る |
  | 460800 | 3.9 ms | 16.0 KiB/s | 2.4 秒 | 2 回とも通る |
  | 921600 | 3.8 ms | 16.1 KiB/s | 2.4 秒 | 2 回とも通る |
  | 1500000 | 3.7 ms | 16.4 KiB/s | 2.4 秒 | 2 回とも通る |
  | 2000000 / 3000000 | 3.6 ms | 16 KiB/s | — | 書き込みの大きなフレームで COBS が壊れる（各 2 回とも） |

  - 460800 bps から先は速くならない。SWIO の側（1 回の DMI に約 3.6 ms）が上限になる。この probe では 460800 bps で十分。
  - 一覧に載る速度でも通らないことがある（230400 は通らず、それより速い 250000 は通った。原因は未確認）。候補は
    表から選ぶだけでなく、必ず最大の長さのフレームを往復させて確かめる。
  - 小さな要求は 2 Mbps でも通り、大きなフレームで初めて壊れる。確かめる往復は最大の長さで行う。

## 2. 排他

- OS やライブラリの排他を使えるなら使う。2 つ目の open が早く失敗し、利用者に「使用中」と伝えられる。
  - Windows の COM ポート、libusb / WinUSB の claim は OS が排他する。
  - Linux の tty は開けてしまう。pyserial なら `exclusive=True`（flock による協力型のロック。screen や minicom の
    ようにロックを見ないツールには効かない）。
- **それでも本当の排他は session_id で行う**（core §6）。locked が返ったら、残り時間を添えて「使用中」と表示する。
  force は利用者の確認を挟んで使う（force は認証ではない。TCP は信頼できる接続でだけ使う、core §3.1）。

## 2.5 応答の対応付けと送り直し（必須）

- **corr が合わない応答は受け取らず、読み捨てて同期し直す**（core §5.1）。usbipd 越しでは、取り消した転送の残りが次の応答
  として現れたことがある（ch32rv、dump が 64 byte ずれる・flash が 1 回おきに失敗）。USB CDC のフレームには CRC が無いので、
  corr の照合がこの防御になる。
- **corr は要求ごとに 1 ずつ進める**（role 0x01 の要求も数える。core §4.1）。同じ corr を使うのは送り直しのときだけ。
- 応答が壊れたか来なかったら、**同じ corr で 1 回だけ送り直す**（状態を変える要求も。core §5.2）。probe は覚えた応答を
  返すので、二重に実行されない。
  - result_lost が返ったら、応答を覚えていなかった（大きすぎた、表から落ちた）。実行されたかは分からないので、状態を
    読み直して確かめる。
  - corr_reused が返ったら、host の番号付けの誤り。
  - 立て直しの中で unsubscribe と end を送ったときは、元の要求は送り直さない。

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

## 4. 時間のかかる操作

- **v1 に長い操作（accepted と status）は無い**（core §10 は予約）。どの op も 1 つの応答で終わる。時間のかかる op（run、
  キャプチャの configure など）は、応答が来るまで待つ。待ち時間は op の引数（run の timeout_ms など）から決める。
- run の間、probe はほかの要求に答えない（oep-if-debug §4.4）。timeout は lease と応答の待ち時間より十分短くする。
- 書き込みのように何度も要求を送る処理は、lease が切れないよう、普段の要求か keepalive でロックを保つ。

## 4.5 flash の書き込み（target の知識は host）

- **ローダーは「書き込み方式 × 命令セット」で選ぶ。** 似た系統から流用しない。X035 用のローダー
  （experiments/flash-primitives/x035_loader.S）は t3 / t4 を使うので、RV32E（V003 / V00x）では不正命令になる。
  例: V20x / V30x は direct（ページの開始）、X035 / L103 は 256 byte の buffered（RV32IMAC）、V00x は 256 byte の buffered
  だが RV32EC、V103 は half-word の書き込み + commit、V003 は wlink の 64 byte（RV32EC）。device-data の
  `flash_program_method`（`buffer_load_bits`）、`sram_bytes` で引く。
- **ローダーは走らせる前に読み戻す。** 化けたローダーは flash コントローラを動かしながら ebreak まで届き、以後の全ページを
  壊す（2026-09-24、RP2350 の probe 越しの CH32L103 で 38 ページ書き直しても合わなかった）。probe の ack は「その内容が入った」証明に
  ならない。書き込んだ flash も必ず読み戻す（target 側で CRC を計算するローダーを使えば、遅い経路で速くなる）。
- **消去後の値は 0xff とは限らない。** V20x / V30x / V407 / X315 / H417 は `0xe339e339` を読む。「全部 0xff のページは
  飛ばす」最適化や blank check は device-data の `erased_word` で判定する。
- **ELF の segment はページ単位に併合してから書く。** `.data` の初期値は `.text` の直後に、ページの途中から始まる別の
  segment として来る。
- **読み出し保護（RDP）を先に読む。** WCH-Link は保護された target を書くとき、黙って保護を外す（option を含む全消去）。
  host 主導の書き込みでは、明示の指示が無ければ止める。
- **動いているウォッチドッグの上から書かない。** IWDG は hart を止めても数え続け、書き込みの途中で target をリセット
  する（2026-09-24、system_selftest のあとの CH32L103）。書く前に `riscv-dm` の reset（最初の命令の前で止める）を使う。
- **Cortex-M で target の関数（ROM の flash ルーチンなど）を host から呼ぶときは、割り込みを止め（DHCSR の C_MASKINTS）、
  呼び終わったら必ず外す。** XIP を切っている間、flash にある割り込みハンドラは読めない。C_MASKINTS は debug の領域に
  あってリセットを越えて残るので、外し忘れると再起動後の firmware が SysTick / USB の割り込みなしで走り、USB の列挙が
  終わらない（2026-09-24、RP2350: Windows で「デバイス記述子要求の失敗」）。AIRCR の SYSRESETREQ も DHCSR を消さない。
  再列挙まで含めて戻すには、ROM の reboot（チップ全体）を割り込みを有効にして呼ぶ。
- target の識別: OEP の probe は WCH-Link のような系統の番号を返さない。attach の応答に target_id（WCH の線なら DMI 0x7F の
  値、scheme 1）が付けば、それが手がかりになる（値の意味、たとえば bit [7:4] がリビジョンであることは host が知っている）。
  付かなければ、host は marchid / mimpid（CSR）→ core の世代 → ESIG の chip_id / flash 容量 / UID（番地は DB から）の順に読む。
- **run は probe が出し直さない**（oep-if-debug §4.4）。止まった dpc が開始位置のままなら走っていない。ローダーを二度走らせて
  よいとき（消去、同じページの書き込み）だけ、host がやり直す。oep-client-python の `ch32_flash` は、V003 の一括消去を
  最大 3 回やり直し、ページの書き込みは読み戻しで違ったページを書き直す。
- **resume の CH32 の扱いは host が持つ**（oep-if-debug §4.2）。CH32V006 は 1 回の resumereq で出ないことがあり、CH32L103 は
  allresumeack を立てない。probe の resume が「出なかった」と返したら、dpc を読んで、動いていれば走った、動いていなければ
  もう一度 resume する（`ch32_flash.resume`）。

## 4.6 リセットの線

- **どのチャンネルがリセットの線かは、host が探して確かめる。** 候補ごとに attach_under_reset を送り、止まった dpc を見る。
  本物の線なら最初の命令の前（CH32 は 0x0）で止まり、違う線なら target は走り続けているのでコードの途中で止まる。
  偶然 0x0 に止まることはまず無いので、候補ごとに数回試し、一度でも 0x0 なら当たりとする（2026-09-24、CH32L103 の
  本物の NRST でも 10 回に 2 回外れた。原因は probe 側で、普通の attach で速度を詰めた後だと、リセット後の既定の
  クロックに対して速すぎた。直した後は 60 回中 59 回で、残る 1 回も 0x2 = 1 命令だけ進んだところ）。
  - probe が許可していないチャンネルは rejected で返るので飛ばす。attach の失敗（completed / failed）は外れとして再試行する。
  - 当たりのあとは resume ではなく reset（走らせて確認）で、hart をベクタから確実に離す。ベクタに止まったまま残ると、次の
    外れの線でも dpc = ベクタと読めて、偽の当たりになる（2026-09-24、L103 で NRST の次の GP3 が当たった）。
  - 候補を一本ずつオープンドレインで low にする。治具の配線で low にしてはいけない線は候補から外す。
  - 実測: V003（ESP32、15 候補）で 1 回 0.7〜2.1 秒、L103（RP2350、8 候補）で約 3 秒。どちらも本物の線だけが当たった。
  - oep-client-python: `Wire.find_reset_line(candidates)`。
- **SWD / SWIO を GPIO にしてしまったファームからの回復は、probe の中のモードを先に使う**（attach_under_reset）。
  持たない probe（unsupported）では、`oep.fixture.gpio` の解放と attach を 1 回にまとめて送り、再試行する
  （`attach_after_gpio_reset`）。窓の縁での競争で、V003 では 5 回中 2 回届いた。解放の応答を待ってから attach を
  送ると届かない。

## 5. コンソール

- Arduino の書き込みのあとの Monitor は「最後の reset マークから」読む。前回の未取得のログが流れない。
- Monitor が一度閉じて戻るときは、前回読んだ位置から読む。
- 応答の先頭の位置が要求より進んでいたら、その差が失われた量である。表示に残す。
- 表示用の時刻は受け取った時刻を使う（probe は byte ごとの時刻を持たない）。

## 6. plan とピン

- plan は fn ごと（core §8）。plan_apply は名前を挙げた fn の割り当てだけを置き換え、ほかの fn の plan は残る。UART を受けた
  まま capture を足すような使い方ができる。解くときは plan_release に fn を並べる（並べなければすべて）。
- ほかの fn が持つピンや、connection が使っているピンを取ろうとすると rejected unavailable で、何も変わらない（core §8.1）。
- 解いたピンは、probe の設定の idle が決めていなければ Hi-Z に戻る。治具の配線で相手の入力が浮くピン（DUT の RX につながる
  TX など）は、`oep.probe.config` の idle でプルアップにして保存する（または、配線の決まった治具の firmware が自分で決める）。
- plan はセッションの資源で、明示の end では残り、lease の期限切れと force で外れる（core §9）。設定から入れた plan は残る。
