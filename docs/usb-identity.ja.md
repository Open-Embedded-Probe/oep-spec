# USB の識別（OEP の probe をどう見分けるか）

状態: **実務（規範は core §3.3、§7.5）**（2026-09-30。2026-10-01 に[ゼロベースの再検討](v1-zero-base-proposal.ja.md) 3.4d を反映:
**規範は iProduct `OEP` 接頭と interface の subclass / protocol で、VID:PID は規範に入らない**）。
参照の firmware の今の形と、host が probe を見分け、覚える方法をまとめる。
PID の使い方の規則は oep-probe-arduino の [PID-USE.md](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/PID-USE.md)。

## 1. 何を ID で見分けるか

USB の VID:PID で見分けるのは、「OEP の probe か」だけである（host の discovery が、すべての口を開かずに一覧を作るため）。
何ができるか（インターフェース、ピン、上限、経路）は、口を開いて confirm / list / describe で読む（core §7）。VID:PID を機能の
表にしない（memo「引き継がない結論」）。

## 2. 参照の firmware と host

- 参照の firmware（OpenEmbeddedProbe の P4 の HS の口）は `303a:0002`（arduino-esp32 の TinyUSB の既定）で列挙する。
  今は仮の USB の ID（ボードの既定の VID:PID）で動かしていて、配布には使えない。専用の PID を取得できたら、それに切り替える予定。
  serial number は unit_id（core §7.5: チップの固有の番号の小文字の 16 進。2026-09-30 までは `<MAC>-hs`）。
- host は、**iProduct が `OEP` で始まる device** を OEP の probe とみなす（core §3.3。恒久の規範）。参照の firmware は `OEP probe (ESP32-P4)`、`OEP probe (RP2040)` など。
- device の中の口は、interface の記述子で選ぶ（CDC はすべてシリアルの口、class 0xFF / subclass 0x4F / protocol 0x45 の bulk の組、
  usage page 0xFF4F / usage 0x45 の HID。registry の `usb`）。interface の文字列は表示のためだけ。
- host が probe を覚えるとき（IDE、sketch.yaml、bench の設定）は、VID:PID ではなく unit_id（= USB の serial number）で覚える。
  firmware の VID:PID が変わっても、覚えた値はそのまま使える。
- fn 0 の describe の `discoverable = 1`（0x4A。旧名 `oep_pid`）は、「host の discovery に出る形でも列挙している」という意味（USB-Serial/JTAG のように別の口から
  開かれたときにも分かる）。
- VID:PID も iProduct も選べない口（USB-Serial/JTAG、USB-UART の変換チップ）は、利用者が口を選ぶ。

## 3. VID:PID の扱い

- **host の判定は VID:PID に依らない**（iProduct `OEP` 接頭 + interface の記述子）。VID:PID は参照の firmware の値で、host が見分けに使う
  ことはない。独立した別の実装は自分の VID:PID を使い、iProduct を `OEP` で始めれば discovery に出る。
- firmware の VID:PID を替えても core §3.3 / §7.5 は変わらない。VID:PID を決め打ちにしている所（bench の usbipd の bind、
  書き込みの道具の既定）は、serial（unit_id）か iProduct で探す形にしておく。
