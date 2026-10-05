# 実装の記録（開発ガイドから移した、チップ固有の話と日付つきの実測）

状態: **記録**（規範ではない。追記は自由）。2026-10-06 作成。[host 開発ガイド](host-development-guide.md) と
[probe 開発ガイド](probe-development-guide.md) が、一般の規則だけを残すために外へ出した文を、元の文のまま集める
（3 回目のゼロベース点検 G-3）。チップ名、ボード名、治具、日付、個体の番号を含む。ガイドの各節は、ここの対応する節を指す。
規範は [OEP core](oep-core.md) と `oep-if-*.md`。target ごとの scan と attach の記録は [target-scan-notes](target-scan-notes.ja.md)、
リンクの計測は [link-measurements](link-measurements.ja.md)、UART の速さの実験は [uart-speed-negotiation](uart-speed-negotiation.ja.md)。

節の名前は「H = host ガイド、P = probe ガイド」と、その話を指すガイドの今の節の番号。見出しの「旧 §n」と、移した文の中の「§n」は、
とくに断りが無ければ 2026-10-06 に付け直す前のガイドの節の番号である。対応は次の表のとおり。

| host ガイドの旧 § | 新 § | | probe ガイドの旧 § | 新 § |
|---|---|---|---|---|
| 1 | 1 | | 1 | 1 |
| 1.5 | 3 | | 2 | 2 |
| 1.6 | 2 | | 2.5 | 3 |
| 1.7 | 4 | | 3 | 4 |
| 2 | 6 | | 3.5 | 5 |
| 2.1 | 7 | | 3.6 | 6 |
| 2.5 | 8 | | 3.7 | 7 |
| 3 | 5 | | 3.8 | 8 |
| 4 | 11 | | 3.9 | 9 |
| 4.5 | 20 | | （新） | 10 識別子と宣言の選び方 |
| 4.6 | 21 | | （新） | 11 設定と保存 |
| 5 | 14 | | 4 | 12 |
| 6 | 13 | | 5 | 13 |
| 7（7.1〜7.5） | 17（17.1〜17.5） | | | |
| 8（8.1〜8.4） | 18（18.1〜18.4） | | | |
| 8.5（実測） | 記録の §H18.4 | | | |
| 8.6 | 18.5 | | | |
| 9（9.1〜9.3） | 19（19.1〜19.3） | | | |
| 9.4（例） | 記録の §H19.4 | | | |
| （新） | 9 断りごと、10 revision と TLV、12 通知、15 probe の設定、16 fake | | | |

## H1. probe をリセットせずに開く（host ガイドの旧 §1 から）

#### 1.1 結論

- **DTR と RTS を立てたまま開く（pyserial の既定）。** 実測したすべての probe でリセットしなかった。
- **DTR を下ろすなら、RTS を先に下ろす。** DTR を先に下ろすと RTS=1・DTR=0 を一瞬通り、ESP32 の自動リセット回路が
  EN を下げる。
- 閉じるときは何もしなくてよい（Linux の hupcl で両方同時に下りても、リセットしなかった）。
- DTR を下ろしたまま使わない。RP2350（arduino-pico）は DTR が下りている間、出力を止める。

#### 1.2 実測（2026-09-24、Linux、起動ごとに変わる番号を 100 ms ごとに出す sketch で開閉を 3 回ずつ）

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

## H8. 応答の対応付け（host ガイドの旧 §2.5 から）

- **corr が合わない応答は受け取らず、読み捨てて同期し直す**（core §5.1）。usbipd 越しでは、取り消した転送の残りが次の応答
  として現れたことがある（ch32rv、dump が 64 byte ずれる・flash が 1 回おきに失敗）。vendor bulk / HID / TCP のフレームには CRC が
  無いので、corr の照合がこの防御になる。

## H5. serial を選べない口の例（host ガイドの旧 §3 から）

- serial を選べない口（USB-Serial/JTAG、CH340 などの変換チップ。CH549 の Link の fw 2.6 は仮の `0001A0000000` を返す）では describe で unit_id を読む。

## H20. flash の書き込み（host ガイドの旧 §4.5 から）

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

## H21. リセットの線（host ガイドの旧 §4.6 から）

- **どのチャンネルがリセットの線かは、host が探して確かめる。** 候補ごとに attach（reset TLV、method 1）を送り、止まった dpc を見る。
  本物の線なら最初の命令の前（CH32 は 0x0）で止まり、違う線なら target は走り続けているのでコードの途中で止まる。
  偶然 0x0 に止まることはまず無いので、候補ごとに数回試し、一度でも 0x0 なら当たりとする（2026-09-24、CH32L103 の
  本物の NRST でも 10 回に 2 回外れた。原因は probe 側で、普通の attach で速度を詰めた後だと、リセット後の既定の
  クロックに対して速すぎた。直した後は 60 回中 59 回で、残る 1 回も 0x2 = 1 命令だけ進んだところ）。
  - probe が reset の線として許していないチャンネル（rejected unsupported）と、ほかが持っているチャンネル（その channel を名指しした
    rejected unavailable）は飛ばす。ほかの断りはチャンネルではなくピンや線のことなので、探すのをやめる。attach の失敗
    （completed / failed）は外れとして再試行する。
  - 毎回の attach に pins を付ける。ピンを host が選ぶ線（role_channels）では、pins の無い attach はその線の唯一の生きた接続に
    加わるだけで、接続が無ければ unavailable で断られる（§9.3）。
  - 当たりのあとは resume ではなく reset（走らせて確認）で、hart をベクタから確実に離す。ベクタに止まったまま残ると、次の
    外れの線でも dpc = ベクタと読めて、偽の当たりになる（2026-09-24、L103 で NRST の次の GP3 が当たった）。
  - 候補を一本ずつオープンドレインで low にする。治具の配線で low にしてはいけない線は候補から外す。
  - 実測: V003（ESP32、15 候補）で 1 回 0.7〜2.1 秒、L103（RP2350、8 候補）で約 3 秒。どちらも本物の線だけが当たった。
  - oep-client-python: `Wire.find_reset_line(candidates, pins=...)`。候補の出し方から通しては §9（`oep pins`）。
- **SWD / SWIO を GPIO にしてしまったファームからの回復は、probe の中のモードを先に使う**（attach の reset TLV）。
  持たない probe（unsupported）では、`oep.fixture.gpio` の解放と attach を 1 回にまとめて送り、再試行する
  （`attach_after_gpio_reset`）。窓の縁での競争で、V003 では 5 回中 2 回届いた。解放の応答を待ってから attach を
  送ると届かない。

## H17.3. 速さの候補の例（host ガイドの旧 §7.3.1 から）

- 変換チップが整数分周しか作れないもの（例: CH552 の FTDI 互換）では 921600 に confirm が返らない。host は試すの応答の baud
  （実際に掛かる速さ）を見て、自分の口で作れなければその候補を捨て、confirm が返らなければ verify_ms を待って次の候補へ進む。

## H17.5. シリアルの口の速さの実測の要約（host ガイドの旧 §7.5 から、2026-10-02）

数字の根拠。生データは [UART の速さ](uart-speed-negotiation.ja.md) §11。チップ名はここに書くが、**測った例であって規則ではない**。

- **CH340（V003 治具、classic ESP32）**: 115200 の基準（60 フレーム）は 0〜10 %（12 回中 4 回は 0 以外。数秒まとめて落ちる）。
  921600: 確かめ 11/12 通る（数え方は 3 つの流し方 × 16 = 48 フレームを合わせた割合で 5 %。流し方ごとの判定にすると変わりうる）。使用中は 100 フレームの窓だと 2 % 超が 26/48、10 % 超が 11/48、20 % 超が 4/48 と跳ねるが、3 秒平均では
  0〜19 %（10 % 超は 3/12）。500000: 確かめ 10/12、窓 10 % 超 2/48、3 秒平均 0〜6 %。1500000: 確かめ 3/12、3 秒平均 5〜16 %
  （全部 5 % 超）。host → probe の向きは 1.5 M まで壊れない。
- **CH552 の FTDI 互換（M5Stack ATOM）**: 115200 n = 1 の基準 0/720。n = 2 の基準は 17〜45 %（両方向同時で壊れる）。
  1500000 n = 1: 確かめ 12/12、3 秒平均 0〜1.3 %。500000 n = 1: 12/12、0〜3 %。921600 は confirm が返らない（整数分周で作れない）。
- **CH340（V003 治具、classic ESP32）の長いキャプチャの読み出し**（2026-10-02、治具での測定を WireSkein が中継）: firmware /
  client 0.0.28、読み出し 65.4 KB、probe の限度は max_frame 512 / window 512 / max_inflight 1。速さを明示すると、1.5 M は確かめで
  16/16 失われ。921600 は確かめを通る（59.4 KB/s、壊れ 0 / 失われ 0）が、使用中に CorruptFrame で 115200 に戻る。500000 は確かめも
  使用中も通る（43 KB/s）。記録ありで 3 回: 1 回目は 1.5 M が確かめ（n = 1）を通り、使用中に壊れて 115200 へ。2 回目は 921600 が
  確かめで落ち、その破綻の直後に試した 500000 が n = 2 で全部失われ、n = 1 で通って決まり、使用中に壊れて 115200 へ。3 回目は記録が
  3 つとも通らなかったとしていて 115200 のまま。役に立ったのは明示の 500000 だけ。同じ CH340 の CLI は 921600 で安定（約 73 KB/s）
  なので、長い読み出しは線に別の負荷を掛ける。ここから試用期間（16 フレームの確かめは長い読み出しの破綻を見落とす）、下げ方（起動時の
  速さでなく次に遅い候補へ）、落ち着き待ち（2 回目の 500000 の失われは 921600 の破綻の直後）、期限 1 日と全部通らなかったときの
  1 回の試し直し（3 回目）を足した。
- **数字の由来**: 確かめの床 5 % は、CH340 の 1.5 M（全部 5 % 超）を落とし 500000 / 921600 を通す値。使用中の床 10 % は、CH340 の
  基準の上限（10 %）と同じで、921600 の 3 秒平均をおおむね通す値。窓を 3 秒（時間）で取るのは、100 フレームが 921600 では 0.7 s と
  短く、まとめて落ちる線で割合が跳ねるから。基準を使う n で測るのは、CH552 の n = 2 の基準が n = 1 では見えないから。
  試用期間の 32 KiB は、長い読み出しの CH340 で 921600 が確かめの後に壊れた（65.4 KB の読み出しの途中）のを、読み出しの前半で拾う
  目安（921600 の約 0.5 s 分。1 秒の下限で速い速さでも短すぎないようにする）。落ち着き待ち 2 秒は、破綻の直後に試した 500000 が
  n = 2 で全部失われた（直後でなければ通る速さ）ことから。

## H18.4. target の電源とリセットの実測（host ガイドの旧 §8.5 から、2026-10-02）

測った例であって規則ではない。

- host の側だけで電源を入れ直した（gpio で電源を切って 200 ms → 入れる → その応答を受けたらすぐ止める attach）: **8 回中 8 回、dpc 0
  （最初の命令の前）で止まった**。電源を入れた応答から止まるまで約 15 ms。
- `nrst` の channel に reset TLV を付けた attach: **6 回中 6 回、dpc 0 で止まった**。
- 出力の idle を置いていない電源の channel で、gpio の plan を解いたら、target の電源が切れた（§8.2 の 5 の理由）。
- 電源の channel に出力の idle（mode 4）を置いて保存した後（oep-probe-arduino ec1df99）: plan が無くても target は動き続け、その
  channel を gpio の plan で取っても（set を送る前）、plan を置き換えて残しても、解いても、電源は切れなかった。probe を再起動しても、
  plan の無いまま target は起動直後から動いていた。label の `v003.nrst` / `v003.power_hi` から線を引けた。
- 電源を入れたところを取った（§8.4）: logic を電源の channel の立ち上がりで待たせ（状態 2）、その間に gpio で電源を入れた。電源の
  channel 自身も取る channel に入れた。リセットの線は通電の 4.4 ms 後に上がり、target の UART の線は通電の 2 µs 後に high に
  なった。この probe の logic は最遅 1 MHz、1 回 約 6 万サンプルまでなので、1 回の窓は約 60 ms（target のアプリが動き出す約
  138 ms 後は窓の外）。

## H18.5. 出力の強さの実験（host ガイドの旧 §8.6 から、2026-10-02）

**実験**（2026-10-02。ESP32-P4、FS、CH32V003 を GPIO5 から直接給電、出力 high の強さを build で 4 段。測った例であって規則ではない）:

| 強さ | 設定だけで起動 | 電源の入れ直しからの止める attach | 止まるまで | NRST が上がるまで |
|---|---|---|---|---|
| 最弱（約 5 mA） | 動く | 8/8 | 16.7〜17.2 ms | 4.82 ms |
| 約 10 mA | 動く | 8/8 | 16.2〜16.7 ms | 4.55 ms |
| 既定（約 20 mA） | 動く | 8/8 | 16.2〜16.7 ms | 4.42 ms |
| 最強（約 40 mA） | 動く | 8/8 | 16.2〜16.5 ms | 4.37 ms |

強さで変わったのは立ち上がりの 0.5 ms ほどだった。

同じ配線で、後に firmware の drive_levels を使って gpio の set で段を選んだとき（2026-10-02、段 0〜3 = 約 5 / 10 / 20 / 40 mA）、
段 0 では target が電圧の低下でリセットを繰り返し、段 1〜3 は問題なかった。NRST は電源の線から 4.4〜4.9 ms 後に上がった。
上の表の最弱の段との違いの原因は確かめていない。最弱の段は、給電の余裕が無い。

## H19.3. ピンの探し方でわかったこと（host ガイドの旧 §9.3 から、2026-10-02）

- **idle-high の UART の線は、電源の入り切りの比較では debug の線やリセットの線と同じに見える。** レベルの比較は候補を出す
  だけで、決めるのは scan（線が答えたか）と attach（dpc）。どちらの pull でも high に読むので、分類では driven になり、scan と
  保持から外れる。
- **target が push-pull で動かす出力は scan と保持から外す。** 読むたびに変わる channel（active）と、どちらの pull でも同じに
  読む channel（driven）を除いた残りの全 channel の scan で、debug の線はすぐに見つかった。
- **リセットの線は活動で探し、dpc で確かめる。** 活動を見る窓が短いと、静かな間（出力のデューティが端に寄る間）を止まったと
  読んで、8 本を候補にした。窓を静かな間の 3 倍にすると本物の 1 本だけになった。決めるのは reset TLV の attach の dpc。
- **reset TLV の attach には pins を付ける。** ピンを host が選ぶ線では、pins の無い attach はその線の唯一の生きた接続に加わる
  だけで、接続が無ければ unavailable で断られる。1 本目の候補を試して detach した後は全部断られ、断りを「リセットの線ではない」
  と読んで、本物を候補に入れたまま「無し」になった。
- **リセットの線が有るかは target の option で決まることがある。** 無効なら見つからないのが正しい。option を読んで先に分かる。
- **pull-down でもリセットになる。** 分類で pull-down をかけた間 target はリセットされ、ブートローダが待つ target では活動が
  戻るまで 1 秒以上かかった。pull-down は最後に読み、次の段の前に活動が戻るのを待つ（戻らなければ電源を入れ直す）。
- **電源の入れ直しからの止める attach** は、通電の応答から約 15 ms で最初の命令の前に止まった（§8.5）。リセットの線が無い
  target の、もう 1 つの止め方になる。

## H19.4. 例: ESP32-P4 と CH32V003（host ガイドの旧 §9.4 から、2026-10-02）

ESP32-P4 の probe（FS USB-Serial/JTAG、`oep.wire.swio`）に CH32V003 をつなぎ、P4 の GPIO5 から給電した。`oep pins <probe>
--power 5 --wire swio` で、何も教えずに SWIO 19 と NRST 4 を見つけた（6 回中 6 回、1 回 7〜8 秒）。

- 分類（52 channel）: 22 / 23（target の UART、idle high）と 7 / 8 / 35（P4 の板の pull-up）は driven-high、51 は driven-low、
  21（アプリの出力、約 0.75 秒の周期で密度が変わる）は active、4 は弱い pull-up、19 は浮いている。電源に従うのは
  4、6、9〜11、13、15、16、19〜23、32、33。
- low に保つ探索: 45 本を 3.4 秒で試し、21 が止まったのは 4 だけ（窓 390 ms、静かな間の最長 130 ms）。
- scan: 45 channel を 0.14 秒、答えたのは 19。target_id 0x00310510。option の USER 0xF7: RST_MODE 10（NRST 有効、12 ms の窓）。
- reset TLV（4、保持 20 ms）の attach で dpc 0。保持 1 / 2 / 5 / 10 / 20 ms のどれでも 3 回中 3 回 dpc 0 だった。
- P4 の firmware（0.0.27）は gpio の plan を置き換えると前のピンをいったん Hi-Z にするので、電源の channel が途切れ、そのあと
  scan が答えなくなった（電源を入れ直すと戻った）。`oep pins` は plan を置き換えるたびに電源を入れ直す。

target ごとの詳しい記録は [対象ごとのスキャンの記録](target-scan-notes.ja.md) §3.1。

## P1. DTR（probe ガイドの旧 §1 から）

- **DTR に頼らない。** arduino-pico の USB シリアルは DTR が下りていると出力しない（実測、2026-09-24）。
  `Serial.ignoreFlowControl()` などで、host の開き方が違っても通信が止まらないようにする。

## P2. 送受信のバッファ（probe ガイドの旧 §2 から）

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

## P3. OEP の口にほかのものを出さない（probe ガイドの旧 §2.5 から、2026-09-25）

2026-09-25 の P4 の試作で 2 回踏んだ。

- **OEP の口にログを出さない。** ESP-IDF のログ（LEDC の設定エラーなど）が、OEP と同じ USB-Serial/JTAG に出てフレームを
  壊し、host は応答が来ないとみなした。OEP をその口で話す probe は、`esp_log_level_set("*", ESP_LOG_NONE)` などでログを
  止める。
- **誰も読んでいない口への書き込みで loop を止めない。** OEP を HS の vendor bulk に移し、USB-Serial/JTAG には 2 秒ごとの
  状態の行だけを出していたところ、その口を誰も開いていないと HWCDC の書き込みがタイムアウトまでブロックし、loop が
  1.8 秒止まった。パイプラインの読み出しと通知が毎回 1.83 秒遅れ、1 回ずつの往復（0.5 ms）は loop が動いている間に
  収まるので気づきにくい。書き込みがブロックしない設定（`Serial.setTxTimeoutMs(0)`）にするか、書かない。

## P4. 信頼性のない経路（probe ガイドの旧 §3 から）

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

## P5. UART bridge の速さ（probe ガイドの旧 §3.5 から。2026-09-29 の決定は core §3.5 の port_speed で置き換え）

UART bridge（probe の UART を USB-UART の変換チップで出したもの）の probe は、**115200 bps 固定**にする（2026-09-29 の決定）。

- 設定で変えられるようにすると、忘れたときに入れなくなる。自動の速度検出は、生のバイトと OEP が混ざる口（core §3.4）では危うい。
- dmseq のコンソールと書き込みには足りる（classic ESP32 + CH340 の V003 治具で、14 KB の書き込み + 確認が 4.1 秒）。速さが要る
  なら、USB CDC / USB-Serial/JTAG / vendor bulk を持つ probe を使う。USB CDC と USB-Serial/JTAG では baud は数字が渡るだけで、
  速さに関係しない。
- 参考（2026-09-24、速度ごとにビルドし直した実験用の probe）: 460800 bps から先は SWIO の側が上限で速くならず、230400 は
  変換チップの経路で通らず、2 Mbps 以上は大きなフレームで壊れた（`experiments/uart-binding/uart_rate.py`）。

## P7. probe の再起動の抑止の例（probe ガイドの旧 §3.7 から）

口を開閉しても probe が再起動しないようにする（§1）。

| 口 | 止め方 |
|---|---|
| ESP32-P4 などの USB-Serial/JTAG | `USB_DEVICE_CHIP_RST_REG` の `USB_UART_CHIP_RST_DIS`（bit2）を立てる。arduino-esp32 3.3.12 の HWCDC に API は無いので、レジスタに直接書く |
| TinyUSB の CDC（arduino-esp32 の `USBCDC`） | `enableReboot(false)`（DTR / RTS の並びと 1200 baud の touch での再起動を止める） |
| EspUsbDevice の CDC（P4 の HS） | 元から持たない |
| classic ESP32 などの UART bridge | 変換チップの先の自動リセット回路なので、firmware では止められない。host が DTR と RTS を両方立てて開く（host 開発ガイド §1）。止められないものは describe の resets_on_open で宣言する |

## P8. 参照の probe の USB の例（probe ガイドの旧 §3.8 から）

  - 参照 probe（ESP32-P4、EspUsbDevice 2.5.1）は、VID:PID は仮に 303a:0002（arduino-esp32 の TinyUSB の既定）、iProduct を
    「OEP probe (P4 HS)」にしている（CDC の「OEP console」は表示のための名前）。

## P12. target を扱う部品（probe ガイドの旧 §4 から）

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
- **debug の線は、線のタイミングが許すいちばん弱い出力の強さで駆動する。** 線の鋭いエッジは、同じ治具の隣の fixture の線に
  乗る。classic ESP32 の既定（20 mA）の SWIO では、コンソールを読んでいる間、1 MHz の spi-target が bit を落とす・ずらす
  （36 frame 中 23 だけ正しい。最弱（約 5 mA）では 72 中 72 で、線の速さは変わらない。2026-10-02、oep-probe-arduino d4f6293）。
  配線の同じ P4 の治具では起きなかった（P4 の RVSWD はもとから最弱で、入力も違う）。参照の firmware の PHY はどれも最弱にする
  （RVSWD: P4 は CAP_0、RP2 は 2 mA。SWIO: classic と P4 は CAP_0）。新しい PHY や移植でも設定する。記録は
  [対象ごとのスキャンの記録](target-scan-notes.ja.md) §4。
- **debug の線が忙しいときだけ壊れる fixture は、CPU より線のエッジを先に疑う。** 線が休んでいるとき（コンソールを外す）と
  忙しいときで同じ手順を回し、まず出力の強さを見る。直ったかは前後を同じ手順で測る（arm した frame の直後に読む。DUT の周期
  より長く待つと、arm していない次の frame が入って失敗に見える）。
- **問題を直したら、同じ仕組みの箇所を探して確かめる**（ほかの PHY、ほかの SoC、線を駆動する fixture、client と fake）。
  どれが大丈夫でどれが未確認かを記録に残す。
- **resume と run は出し直さない**（oep-if-debug §4.2、§4.4）。CH32V006 の 1 回で出ない resumereq、CH32L103 の allresumeack
  無しは host が扱う。以前 probe が dpc を見て出し直していたのは、汎用の名前の riscv-dm に CH32 の知識を入れる形だったので
  やめた（2026-09-26）。
- **1 語ごとの DMI の記録（最終アクセス時刻の `micros()` など）を、autoexec のブロックのループから外すのは見送った**
  （2026-09-25）。ESP32-P4 → X035 の読み出しは 122.6 → 133.2 KiB/s（約 9 %）速くなり、書き込みは変わらなかった。
  ところが RP2350 → L103 では、smoke 全体の中で毎回 1〜2 本のスケッチがコンソールから 0 文字になった（12/14、13/14、
  13/14。元のループに戻すと 14/14 が 2 回）。原因は突き止めていない。フレームの間隔が詰まったことが、RP2350 の probe → L103 の
  組み合わせに効いている可能性がある（L103 の配線は他の target と同じ。配線のせいではない）。
