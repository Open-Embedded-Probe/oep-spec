# pid.codes への申請の資料

状態: **pull request を出した**（2026-10-02、https://github.com/pidcodes/pidcodes.github.com/pull/1296 、head は fork の `add-open-embedded-probe-4f45` 080bf79。審査待ち）。ここにあるファイルを、そのまま [pid.codes](https://pid.codes/howto/) のリポジトリ
（`pidcodes/pidcodes.github.com`）への pull request に入れる。PID の使い方の規則は oep-probe-arduino の
[PID-USE.md](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/PID-USE.md)、host から見た見分け方と、割り当て後に
変える所は [USB の識別](../usb-identity.ja.md)。

## 何を申請するか

- **1 つの PID**（VID は pid.codes の `0x1209`）。対象は「OpenEmbeddedProbe ライブラリから作った firmware を動かす device」。基板や
  example ごとには分けない（何ができるかは describe で分かるので、ID は OEP の probe であることだけを示せばよい）。
- 申請の site / source は Arduino ライブラリのリポジトリ（oep-probe-arduino。Arduino の Library Manager に `OpenEmbeddedProbe` で
  載っている）。

## pid.codes の条件と、満たしているか

| 条件（https://pid.codes/howto/） | 状況 |
|---|---|
| 公開されたソースのリポジトリ | https://github.com/Open-Embedded-Probe/oep-probe-arduino |
| USB の interface を持つ device のソース（または PCB の設計） | firmware のソース（USB の vendor bulk、HID、CDC）。基板は市販の ESP32-P4 / RP2350 / RP2040 の開発ボード |
| 認められた OSS のライセンスと、リポジトリの LICENSE | MIT、LICENSE あり |
| ハードとソフトの両方なら、両方に OSS / OSHW のライセンス | ソフトだけ（自作の基板は無い） |

## ファイル

| ファイル | 入れる場所（pid.codes のリポジトリ） |
|---|---|
| [org/Open-Embedded-Probe/index.md](org/Open-Embedded-Probe/index.md) | `org/Open-Embedded-Probe/index.md` |
| [1209/4F45/index.md](1209/4F45/index.md) | `1209/4F45/index.md` |

## 手順

1. PID の番号は **`0x4F45`**（ASCII の "OE"）。2026-09-30 と 2026-10-02（開いている 28 本）に、pid.codes の `1209/` に無く、開いている 37 本の pull request にも
   出ていないことを確かめた。出す直前にもう一度確かめる（取られていたら、空いている別の番号に。`0x0000`〜`0x000F` は予約）。
2. `pidcodes/pidcodes.github.com` を fork し、上の 2 つのファイルを置く。
3. commit message の例: `Add Open Embedded Probe and 1209:4F45 (OEP probe, OpenEmbeddedProbe firmware)`。pull request を出す。
4. 認められたら、[USB の識別](../usb-identity.ja.md) §4 の一覧の所を直す（spec、ライブラリ、client、ch32rv、ArduinoCore-CH32）。

## 申請の前に済ませておくこと

- [x] oep-probe-arduino の README に、OEP とは何かと仕様へのリンク
- [x] oep-probe-arduino に PID-USE.md（英語と日本語）
- [x] PID-USE.md を oep-probe-arduino の main に入れる（申請の本文がリンクする。2026-10-02 に serial = unit_id、discoverable に直した 95e9aa8 を push してから PR を出す）
- [x] 持ち主は個人ではなく OEP（org `Open-Embedded-Probe`、ライブラリの author も "Open Embedded Probe contributors"）
