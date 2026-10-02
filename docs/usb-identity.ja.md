# USB の識別（OEP の probe をどう見分けるか）

状態: **ガイド**（規範ではない。規範は core §3.3、§7.5。2026-09-30。2026-10-02 に改めた: 名前や vendor class の値はほかの製品と偶然重なりうるので、
**規範はプロジェクトの USB の VID:PID だけで OEP の probe を自動で見分ける**。iProduct と interface の subclass / protocol は見分けに使わない）。
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
- host が知らない device を自動で OEP の probe と見分けるのは、**プロジェクトの USB の VID:PID を持つ device** だけ（core §3.3）。
  その VID:PID は取得したときに registry に載る。載るまでは、規範で自動で見分けられる device は無い。
- それまでの暫定の手がかり（iProduct が `OEP` で始まる、class 0xFF / subclass 0x4F / protocol 0x45 の interface、usage page 0xFF4F の HID）は
  [host 開発ガイド](host-development-guide.ja.md) §1.7。仕様の一部ではなく、候補は必ず confirm だけで確かめる（core §3.3 の探りの規則）。
  参照の firmware の iProduct は `OEP probe (ESP32-P4)`、`OEP probe (RP2040)` など。iProduct は表示のための自由な文字列。
- 利用者が unit_id で名指した probe（`oep://<unit_id>`）は、serial number が同じ device を開き、confirm と describe の unit_id で確かめる（core §3.3）。
- device の中の口は、OEP と分かった device の中で interface の記述子で選ぶ（CDC はすべてシリアルの口、class 0xFF / subclass 0x4F /
  protocol 0x45 の bulk の組、usage page 0xFF4F / usage 0x45 の HID。registry の `usb`）。interface の文字列は表示のためだけ。
- host が probe を覚えるとき（IDE、sketch.yaml、bench の設定）は、VID:PID ではなく unit_id（= USB の serial number）で覚える。
  firmware の VID:PID が変わっても、覚えた値はそのまま使える。
- fn 0 の describe の `discoverable = 1`（0x4A。旧名 `oep_pid`）は、「プロジェクトの USB の VID:PID でも列挙している」という意味
  （USB-Serial/JTAG のように別の口から開かれたときにも分かる）。プロジェクトの VID:PID が registry に載るまでは、どの probe も 0。
- serial を選べない口（USB-Serial/JTAG、USB-UART の変換チップ）は、利用者が口を選ぶ。

## 3. VID:PID の扱い

- **host の自動の判定はプロジェクトの VID:PID だけ**（core §3.3）。参照の firmware の今の VID:PID はボードの既定で、host が見分けに使う
  ことはない。独立した別の実装は、自分の VID:PID なら利用者が名指すか口を選ぶ（host が個別に対応してもよい）。
- firmware の VID:PID を替えても、unit_id で覚えた設定は変わらない。VID:PID を決め打ちにしている所（bench の usbipd の bind、
  書き込みの道具の既定）は、serial（unit_id）で探す形にしておく。
