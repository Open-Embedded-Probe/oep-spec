# USB の識別（OEP の probe をどう見分けるか）

[English](usb-identity.md)

状態: **ガイド**（規範ではない。規範は core §3.3、§7.5）。2026-10-06 に改めた。プロジェクトの USB の VID:PID は `1209:4F45`
（VID 0x1209、PID 0x4F45。registry の `usb`）で、**host はそれだけで OEP の probe を自動で見分ける**。iProduct と interface の
class / subclass / protocol は、ほかの製品と偶然重なりうるので、見分けに使わない。参照の firmware の USB の形と、host が probe を
見つけ、覚える方法をまとめる。プロジェクトの VID:PID の使い方の規則は oep-probe-arduino の
[PID-USE.md](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/PID-USE.md)。英語版が正で、この日本語版はその訳。

## 1. 何を ID で見分けるか

USB の VID:PID で見分けるのは、「OEP の probe か」だけである（host の discovery が、すべての口を開かずに一覧を作るため）。
何ができるか（インターフェース、ピン、上限、経路）は、口を開いて confirm / list / describe で読む（core §7）。VID:PID を機能の
表にしない。

## 2. 参照の firmware と host

- プロジェクトの USB の VID:PID は `1209:4F45`（registry の `usb` の `project_vid` / `project_pid`）。
- 参照の firmware（OpenEmbeddedProbe）は、自分で USB の device を出す口（ESP32-P4 の build の HS の口、RP2040 / RP2350 の USB）を
  `1209:4F45` で列挙する。その serial number は unit_id（core §7.5: チップの固有の番号の小文字の 16 進）。
- host が知らない device を自動で OEP の probe と見分けるのは、**プロジェクトの USB の VID:PID で列挙する device** だけ（core §3.3）。
- 参照の firmware の iProduct は `OEP probe (ESP32-P4)`、`OEP probe (RP2040)` など。iProduct は人のための名前で、何もそれで
  probe を見分けない。
- 利用者が unit_id で名指した probe（`oep://<unit_id>`）は、serial number が同じ device を開き、confirm と describe の unit_id で
  確かめる（core §3.3）。
- device の中の口は、OEP と分かった device の中で interface の記述子で選ぶ（CDC はすべてシリアルの口、class 0xFF / subclass 0x4F /
  protocol 0x45 の bulk の組、usage page 0xFF4F / usage 0x45 の HID。registry の `usb`）。interface の文字列は表示のためだけ。
- host が probe を覚えるとき（IDE、sketch.yaml、bench の設定）は、VID:PID や口の名前ではなく unit_id（= USB の serial number）で
  覚える。
- fn 0 の describe の `discoverable = 1`（0x4A）は、「プロジェクトの USB の VID:PID でも列挙している」という意味（内蔵の USB
  シリアルのように別の口から開いた host にも分かる）。参照の firmware は、それで列挙する口を持つとき 1 を返す。
- probe が VID:PID と serial number を選べない口（USB-UART の bridge、ハードウェアが記述子を決める内蔵の USB シリアル）は、
  プロジェクトの VID:PID で列挙しない。利用者が口を選び、confirm の後、fn 0 の describe がその probe の unit_id を返す。

## 3. VID:PID の扱い

- **host の自動の判定はプロジェクトの VID:PID だけ**（core §3.3）。独立した別の実装は、自分の VID:PID なら利用者が名指すか口を
  選ぶ（host が個別に対応してもよい）。プロジェクトの VID:PID を使ってよい範囲は PID-USE.md。
- VID:PID で権限を与える所（Linux の udev の規則、WSL のための usbipd の bind）は、`1209:4F45` で書く。個々の probe は serial
  number（unit_id）で探す。
