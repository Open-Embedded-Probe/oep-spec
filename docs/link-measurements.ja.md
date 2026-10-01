# リンクの計測記録（運び方ごとのスループットと壊れ方）

状態: 記録（2026-10-01 から）。`oep linktest`（oep-client-python の `oep_client.linktest`）で、host が選んだ条件（速さ、向き、同時数、
フレーム長）ごとに「通った / 壊れた / 失われた」を数えたもの。UART bridge の速さの交渉は
[uart-speed-negotiation.ja.md](uart-speed-negotiation.ja.md) に別に記録してある。ここは USB の運び方と、host 側の OS の都合。

計測は全部 WSL2（Linux 6.18、USB は usbipd-win 経由の vhci_hcd）。native の Linux / Windows / macOS では数値も壊れ方も違いうる。

## 1. 2026-10-01: P4（ESP32-P4、X035 治具、firmware 0.0.25）と Pro Micro RP2350（main）

フレーム長 1008 B（max_frame 1024 の限界）、300 または 200 フレームずつ。KB/s は payload だけ。

| probe / 運び方 | in x1 | in x8 | out x1 | out x8 | duplex x1 | duplex x8 | 壊れ方 |
|---|---|---|---|---|---|---|---|
| P4 vendor bulk（HS） | 1435 | 3051 | 1301 | 2180 | 1370 | 3554 | なし |
| P4 USB CDC（HS、Linux の /dev/ttyACM） | 323 | **10.9（31 % lost）** | 444 | 630 | 431 | 666 | in x8 だけ失われる（下記） |
| P4 USB CDC を libusb で直接（cdc_acm を外す） | 619（x7） | 526 | — | 394 | — | 507 | なし |
| P4 USB-Serial/JTAG（FS） | 283 | 557 | 168 | 228 | 214 | 370 | なし |
| RP2350 USB CDC（FS、pico-sdk stack） | 308 | 461 | 121 | 156 | 177 | 201 | なし |
| ATOM UART bridge（CH552 の FTDI 互換、115200） | ≈8 | — | — | — | — | — | 0.1〜0.3 % がどの速さでも壊れる（別記） |

小さいフレーム（64 B）は往復に支配され、P4 CDC で 53〜98 KB/s、x8 で 135〜195 KB/s。vendor bulk は 64 B でも 360〜940 KB/s。

### 1.1 Linux の CDC（cdc_acm）は、応答の burst が 8 KiB を超えると黙って失う

P4 の CDC で、probe → host の方向だけ、**同時 8 で 1008 B のフレーム**（応答の burst ≈ 8 × 1030 B = 8.2 KiB）のとき 20〜30 % が失われた。

- 同時 7 × 1008 B（7.2 KiB）、同時 8 × 600 B、同時 8 × 900 B（7.3 KiB、まれに 4 %）は通る。待ち時間を 0.3 → 3 s にしても戻らない
  （遅れではなく消えている）。失われたうち 1 割ほどは途中で切れたフレーム（COBS が壊れている）、残りは何も届かない。
- 同じ probe の同じ CDC を、**cdc_acm を外して libusb でエンドポイントを直接読む**と、同時 8 × 1008 B でも 1 つも失われない
  （上の表 3 行目）。vendor bulk も USJ も RP2350 の FS CDC も失わない。
- つまり probe（TinyUSB の送信）ではなく、**Linux の cdc_acm → tty の経路**で落ちている。HS の cdc_acm は 16 本 × 512 B = 8 KiB の
  読み取り URB を持ち、その量を超える burst が tty のバッファに入りきらないときに落とすらしい（usbip 経由で completion がまとめて
  届くことも効いていそう）。native の Linux で同じかは未確認。

**host の決まり（oep-client-python に入れた）**: serial 系（COBS）の link では、未解決の応答の見込み量（同時数 × COBS のフレーム長
の上限）を **6 KiB 以下**に抑える（max_frame 1024 なら同時 5）。UART bridge は max_inflight が 1〜2 なので影響なし。RP2350 の FS CDC は
8 でも通るが、同じ上限で揃える（x5 と x8 の差は小さい）。計測（linktest）だけはこの上限を外して、壊れ方そのものを記録する。
vendor bulk / HID（長さ付きフレーム）には適用しない。

### 1.2 P4 の運び方の使い分け（計測から）

- **vendor bulk** は CDC の 5〜10 倍速く、壊れない。ロジアナ / フラッシュ書き込みの大量転送はここ。
- **CDC** は OS のドライバで開ける利点のため。上の 6 KiB の決まりを守れば 500〜650 KB/s。
- **USJ**（FS）は 200〜550 KB/s。ESP32-P4 の USJ は OEP の運び方としても使え、消去 → 焼き直しの経路でもある。

### 1.3 線の op はリンクではなく線の速さで決まる（X035 治具、RVSWD）

同じ P4 で、CH32X035 に attach して halt → read_block → resume（50 回、s0 / s1 / a0 / a1 が変わらないことを確認）:

| 運び方 | read_block 64 語（256 B） | read_block 240 語（960 B） |
|---|---|---|
| vendor bulk | 8.1 ms / 回、31.5 KB/s | 20.2 ms、47.5 KB/s |
| USB CDC | 8.5 ms / 回、30.1 KB/s | 21.7 ms、44.1 KB/s |

リンクが 10 倍速くても 5 % しか違わない: block op の時間は RVSWD の DMI の往復（abstract command、語ごとの DATA0 読み）で
決まる。線の速さを上げるなら、probe の DMI の往復を減らす（sysbus、abstractauto、まとめ読み）のが先で、リンクの速さは
キャプチャ・大量転送・コンソールのため。block op の自己完結（GPR / DATA / abstractauto を戻す）はどちらの運び方でも成立。

### 1.4 V003 治具（ESP32-D0WD + CH340、UART bridge）の速さごとの壊れ方（8 s ずつ、496 B、resend なし）

| 速さ | in x1 | in x2 | out x1 / x2 | duplex x1 | duplex x2 |
|---|---|---|---|---|---|
| 115200 | 9.9 KB/s、lost 4 / 166（2.4 %） | 10.8、3 / 180 | 10.2 / 10.9、lost 0 | 10.2、0 | 18.1、8 / 300（2.7 %） |
| 500000 | 32.7、0 | 39.1、10 / 652（1.5 %） | 32.6 / 42.5、0 | 32.8、0 | 61.7、16 / 1012（1.6 %） |
| 921600 | 46.5、8 / 760（1.1 %） | 70.3、16 / 1152（1.4 %） | 48.1 / 67.9、0 | 49.5、2 / 802 | 93.2、12 / 1516（0.8 %） |
| 1500000 | 50.2、72 / 882（8 %） | 90.7、217 / 1680（13 %） | 62.0 / 93.7、0 / 4 | 60.0、54 / 1022（5 %） | 58.9、649 / 1600（41 %） |
| 2000000 | 1.8、161 / 190 | 9.9、1347 / 1512 | 69.1 / 88.1、0 / 152 | 9.0、414 / 560 | 0、424 / 424 |

- **probe → host（CH340 の受け → USB）だけが壊れ、host → probe は 1.5 M まで壊れない**。壊れる割合は 115200 でも 921600 でも
  1〜3 % で速さに依らない（この CH340 がまとまって bytes を落とす性質。bench の記録どおり）。1.5 M から急に悪くなり、2 M は使えない。
- だから CH340 では 921600 への引き上げは「壊れ方は変わらず 4.5〜5 倍速い」。host の候補は 921600 → 500000 の順でよく、1.5 M 以上は
  verify が落とす。セッション中は held の口の壊れたフレームをすぐ再送する（oep-client-python 0.0.26）ので、1〜3 % の壊れは
  1 往復の遅れになる。lost の数には再同期（confirm）の分も入る。

## 2. 環境

- host: WSL2、usbipd-win 経由。pyserial の low latency ON。
- probe: X035 治具の P4（unit 30eda0e31108、firmware 0.0.25）、Pro Micro RP2350（unit 9489dd2ae0953650、main 2026-10-01）。
- 手順: `oep linktest <port> --patterns in,out,duplex --inflight 1,8 --sizes 64,1008 --frames 300`；libusb 直接は
  oep-client-python の試験用スクリプト（cdc_acm を detach、SET_CONTROL_LINE_STATE で DTR、COBS の link をエンドポイントに載せる）。
