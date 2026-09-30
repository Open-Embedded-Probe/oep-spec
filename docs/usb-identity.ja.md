# USB の識別（OEP の probe をどう見分けるか）

状態: **実務（規範は core §3.3、§7.5）**（2026-09-30）。pid.codes への PID の申請に合わせて、今の形、割り当て後の形、切り替える
所をまとめる。PID の使い方の規則は oep-probe-arduino の [PID-USE.md](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/PID-USE.md)、
申請の資料は [pid-codes-application](pid-codes-application/README.ja.md)。

## 1. 何を ID で見分けるか

USB の VID:PID で見分けるのは、「OEP の probe か」だけである（host の discovery が、すべての口を開かずに一覧を作るため）。
何ができるか（インターフェース、ピン、上限、経路）は、口を開いて confirm / list / describe で読む（core §7）。VID:PID を機能の
表にしない（memo「引き継がない結論」）。

## 2. 今（PID を取るまで）

- 参照の firmware（OpenEmbeddedProbe の P4 の HS の口）は `303a:0002`（arduino-esp32 の TinyUSB の既定）で列挙する。
  serial number は unit_id（core §7.5: チップの固有の番号の小文字の 16 進。2026-09-30 までは `<MAC>-hs`）。
- host は、**iProduct が `OEP` で始まる device** を OEP の probe とみなす（core §3.3）。参照の firmware は `OEP probe (ESP32-P4)`、`OEP probe (RP2040)` など。
- device の中の口は、interface の種類で選ぶ（CDC はすべてシリアルの口、class 0xFF の bulk の組、vendor 定義の usage page の HID）。
  interface の文字列は表示のためだけ。
- host が probe を覚えるとき（IDE、sketch.yaml、bench の設定）は、VID:PID ではなく unit_id（= USB の serial number）で覚える。
  PID を取ったときに VID:PID が変わっても、覚えた値はそのまま使える。
- fn 0 の describe の `oep_pid = 1` は、「host の discovery に出る形でも列挙している」という意味（USB-Serial/JTAG のように別の口から
  開かれたときにも分かる）。
- VID:PID も iProduct も選べない口（USB-Serial/JTAG、USB-UART の変換チップ）は、利用者が口を選ぶ。

## 3. PID を取った後

- OpenEmbeddedProbe の firmware は `1209:4F45` で列挙する。iProduct は `OEP` で始めたまま（表示と、変換期の host のため）。
- host は `1209:4F45` で OEP の probe とみなす。iProduct での判定は、移行が済んだら消す（core §3.3 の「取るまでの間」）。
- 独立した別の実装は、自分の VID:PID を使う。host は、その実装の ID を知らなくても、口を利用者が選べば OEP を話せる
  （confirm で確かめる）。discovery に出したい実装は、host の側に自分の ID を登録してもらうか、自分の PID の規則で
  `1209:4F45` の条件を満たす。

## 4. 割り当てられたら直す所

| どこ | 何を |
|---|---|
| oep-spec core §3.3 | 「専用の VID:PID（取るまでは iProduct が `OEP`）」の括弧の中を、移行の期限つきの書き方に。番号を書く |
| oep-spec core §7.5（oep_pid）、probe 開発ガイド §3.8 | 同じ |
| oep-spec docs/pid-codes-application | 割り当ての記録（番号、日付、pull request） |
| oep-probe-arduino `examples/Firmware/OepProbe`（`Esp32P4.h` の `kUsbVid` / `kUsbPid`、`Rp2.h` に `USB.setVIDPID` を足す。今はボードの既定の VID:PID） | 番号（PID-USE.md はもう `1209:4F45` と書いてあり、「申請中」を外す） |
| oep-client-python `link.USB_VID` / `USB_PID` | 既定の番号 |
| ch32rv の discovery（`is_oep_device`） | `1209:4F45` を足し、iProduct の判定は移行の後に外す |
| ArduinoCore-CH32 の oep-workflow §3.3 | 同じ |
| ArduinoCore-CH32 の dfu.py | serial（unit_id）で探すのが本筋。serial が無いときの既定の `303a:0002` を `1209:4F45` に |
| bench の usbipd の bind | VID:PID が変わるので、焼き直した後に bind し直す（管理者の操作） |
