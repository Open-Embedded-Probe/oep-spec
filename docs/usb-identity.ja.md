# USB の識別（OEP の probe をどう見分けるか）

状態: **ガイド**（規範ではない。規範は transports §3、core §7.5）。プロジェクトの USB の VID:PID は `1209:4F45`
（VID 0x1209、PID 0x4F45。registry の `usb`）で、**host はそれだけで OEP の probe を自動で見分ける**。iProduct と interface の
class / subclass / protocol は、ほかの製品と偶然重なりうるので、見分けに使わない。host が probe を見つけ、覚える方法をまとめる。プロジェクトの VID:PID の使い方の規則は oep-probe-arduino の
[PID-USE.md](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/PID-USE.md)。

## 1. 何を ID で見分けるか

USB の VID:PID で見分けるのは、「OEP の probe か」だけである（host の discovery が、すべての口を開かずに一覧を作るため）。
何ができるか（インターフェース、ピン、上限、経路）は、口を開いて confirm / list / describe で読む（core §7）。VID:PID を機能の
表にしない。

## 2. host の扱い

- プロジェクトの USB の VID:PID は `1209:4F45`（registry の `usb` の `project_vid` / `project_pid`）。
- host が知らない device を自動で OEP の probe と見分けるのは、**プロジェクトの USB の VID:PID で列挙する device** だけ（transports §3）。
- iProduct は人のための名前であり、host は probe の判定や機能の選択に使わない。
- 利用者が unit_id で名指した probe（アドレス `oep://<unit_id>`、host 開発ガイド §5.3）は、serial number が同じ device を開き、confirm と describe の unit_id で
  確かめる（transports §3）。
- device の中の口は、OEP と分かった device の中で interface の記述子で選ぶ（CDC はすべてシリアルの口、class 0xFF / subclass 0x4F /
  protocol 0x45 の bulk の組、usage page 0xFF4F / usage 0x45 の HID。registry の `usb`）。interface の文字列は表示のためだけ。
- host が probe を覚えるとき（IDE、sketch.yaml、bench の設定）は、VID:PID や口の名前ではなく unit_id（= USB の serial number）で
  覚える。
- probe が VID:PID と serial number を選べない口（USB-UART の bridge、ハードウェアが記述子を決める内蔵の USB シリアル）は、
  プロジェクトの VID:PID で列挙しない。利用者が口を選び、confirm の後、fn 0 の describe がその probe の unit_id を返す。

## 3. VID:PID の扱い

- **host の自動の判定はプロジェクトの VID:PID だけ**（transports §3）。独立した別の実装は、自分の VID:PID なら利用者が名指すか口を
  選ぶ（host が個別に対応してもよい）。プロジェクトの VID:PID を使ってよい範囲は PID-USE.md。
- VID:PID で権限を与える所（Linux の udev の規則、WSL のための usbipd の bind）は、`1209:4F45` で書く。個々の probe は serial
  number（unit_id）で探す。
