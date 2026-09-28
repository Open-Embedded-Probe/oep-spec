# OEP v1 未決事項の事前調査（IP 経路、設定からの復旧）

状態: 調査と提案。規範ではない。2026-09-26 時点の [未合意の案 §6–7](v1-open-proposals.ja.md) と
[レビューへの対応](review-response-2026-09-26.ja.md) を現行仕様と照合した。
外部資料は RFC と実装元の資料を確認した。実機でのネットワーク設定・復旧試験はしていない。

## 1. どこまでが既に決まっているか

- [core §3.1、§3.3](oep-core.ja.md) に TCP 上の `length(u16) message`、認証のない OEP の信頼境界、複数経路で共有する
  セッションとロックがある。TCP の framing 自体を設計し直す必要はない。
- 現行の [probe.config](oep-if-probe-config.ja.md) は USB の設定と永続化を持つが、IP の接続先・listen ポート・実際の状態は持たない。
- USB に依存しない probe や、外部の設定手段を持つ probe も OEP を話せる。`oep.probe.config` が全 probe の必須機能ではない。
- [review-response](review-response-2026-09-26.ja.md) にあるレビュー R1〜R14 はすでに判断・反映済み。
  古いレビュー文の指摘を、そのまま現在の未決事項として数えない。

## 2. IP 経路について調べたこと

### 2.1 TCP と、probe の接続先を見つける仕組み

TCP を使うなら、host が接続する endpoint（ホスト名またはアドレス、ポート）が要る。
USB でつないだ後に describe でアドレスを読む方法は補助手段にはなるが、IP だけの probe を最初に発見することはできない。
またアドレスは DHCP 等で変わるので、保存されたアドレスの恒久的な識別子とは扱えない。

DNS-SD はサービス名から候補を列挙し、SRV でホスト名とポートを解決できる。mDNS と組み合わせればローカルリンクで使える。
一方、mDNS の通常の範囲はローカルリンクで、別サブネット・VPN 越しまで自動発見できる約束ではない。
[RFC 6763 §4–5](https://www.rfc-editor.org/rfc/rfc6763.html)、[RFC 6762 §5](https://www.rfc-editor.org/rfc/rfc6762.html)。

将来 DNS-SD を標準化するなら、サービス型、TXT の最小内容、同じ probe の USB と IP を突き合わせる安定 ID を決める必要がある。
候補名 `_oep._tcp` は形式上短いが、正式名として使う前にサービス名登録の扱いを確認したい。
DNS-SD のサービス名には長さ制限がある。[RFC 6763 §7](https://www.rfc-editor.org/rfc/rfc6763.html)、
[IANA サービス名の登録規則](https://www.rfc-editor.org/rfc/rfc6335.html)。
DNS-SD を v1 に採らないなら、host にアドレスとポートを外部指定する条件を明記するだけで TCP は使える。

### 2.2 IP 設定を `probe.config` に入れる範囲

Wi-Fi の SSID / credential と、Ethernet のアドレス設定は別物。LTE のように probe が単に外向きの client になる場合、
probe への TCP 接続を host が開始できるとは限らない。このため「IP を持つこと」と「OEP の TCP 待ち受けを提供すること」は
別の能力として考えるべきである。TCP 接続可能性は、モバイル網の経路・NAT・ファイアウォール等にも依存する。

Wi-Fi・Ethernet・LTE を一つの必須の `probe.config` 形式に押し込む必要はない。v1 では TCP framing と既存のセッション規則を
維持し、ネットワーク初期設定は probe 固有の手段または後続の任意インターフェースに置くのが最小と判断する。
この判断なら、Wi-Fi の接続先を firmware に焼き込まない方針も、特定の設定 wire 形式を今決めずに満たせる。
設定を共通化する段階では、少なくとも DHCP / 固定 IPv4 の選択、IPv6 の扱い、複数インターフェース、接続失敗時の状態、
変更後に到達できなくなる場合の復旧を一緒に設計する。

### 2.3 secret と現行の `get` / `hash` はそのまま結合できない

[probe.config §2](oep-if-probe-config.ja.md) の hash は「現在の設定の正規形の CRC-32」で、host が望む設定から同じ hash を
計算して一致を確認する仕組み。Wi-Fi の secret を `get` から伏せても、hash に生の secret を含めれば、低エントロピーの候補を
試す手掛かりを公開する。一方、hash から除くと、secret だけを変更した場合に hash が変わらず、「望む設定と一致する」の意味が崩れる。
これは現行の正規形と API からの推論である。CRC-32 は通信エラー検出用で、秘密照合用ではない。

提案: secret は書き込み専用の別項目として扱う。通常の get は「設定済みか」だけを返し、公開設定の hash は secret の一致を
保証しないことを明示する。host が新しい secret を指定したら、hash の一致を理由に書き込みを省略しない。
接続成功・失敗は別の status で確認する。使う MCU の保存領域では、平文残留を防ぐ手段も個別に評価する。
ESP-IDF の資料は、Wi-Fi credential が既定の NVS に保存されることと、NVS 暗号化の仕組みを説明している。
[Espressif: NVS Encryption](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/storage/nvs_encryption.html)。

### 2.4 ネットワーク越しの制御権

OEP の `force` と状態変更には認証がなく、現在の core は「信頼できるローカル接続か、認証したトンネル内で TCP を使う」とする。
ネットワークに入れることだけで、すべての接続者を OEP の操作者として認められるかは利用環境次第。
アクセスポイントへの接続、mDNS での発見、Wi-Fi secret の保存は OEP 操作者の認証の代わりにはならない。
これはプロトコルの能力からの推論であり、外部資料に新しい義務を読み込んでいない。

任意の LAN で使える汎用 TCP サービスとして説明するなら、認証と保護されたチャネルの binding を別に定める必要がある。
v1 のままなら、信頼境界と到達できる host を実装・運用で制限する説明にとどめる。

## 3. 復旧について調べたこと

### 3.1 「OEP 経路が一つある」だけでは復旧できない

[案 §7](v1-open-proposals.ja.md) の「経路が一つも無くなる設定を拒否する」は、USB の全 OEP 口を消す単純な事故を防げる。
ただし、ネットワーク上の待ち受け設定が残っていても、SSID 間違い・DHCP 失敗・ファイアウォール・host が到達できない
アドレスなら操作できない。特に USB を持たない probe には、構成上の「経路あり」と実際の「到達可能」は異なる。
これも現行案の条件からの推論である。

復旧方式はボード依存。ESP32 の BOOT に使う GPIO0 は download mode の選択にも使うので、アプリの設定復旧ボタンとして
使う場合には起動タイミングと衝突する。
[Espressif: Boot Mode Selection](https://docs.espressif.com/projects/esptool/en/latest/esp32/advanced-topics/boot-mode-selection.html)。
Espressif の provisioning API には credential の reset 操作があるが、これをいつ呼ぶか、どの物理操作で起動するかは
製品側が決める。[Espressif: Wi-Fi Provisioning](https://docs.espressif.com/projects/esp-idf/en/v5.1/esp32/api-reference/provisioning/wifi_provisioning.html)。

### 3.2 v1 に置くことを勧める範囲

- `probe.config` の set / save / 起動時適用で、宣言済みの OEP 経路がゼロになる構成を拒否するかは、提供する probe の条件として
  決める。これだけを「復旧保証」とは呼ばない。
- 回復モードは [案 §7](v1-open-proposals.ja.md) のユーザー方針どおり推奨にとどめる。firmware を焼き直すことを許す場合、
  すべてのボードにボタンや二度押し reset を要求しない。
- 開発ガイドには、「保存設定を無視して起動できること」「消す設定の範囲（ネットワーク credential、boot_mode、plan 等）」
  「復旧中の OEP の接続手段」「解除条件」を実装ごとに書く。電源断を含めて確認する。

### 3.3 実機で確かめる最小シナリオ

| probe | 保存して試す状態 | 合格条件 |
|---|---|---|
| P4 / classic ESP32 の USB OEP probe | OEP の USB 口がない boot_mode、起動直後の reset、保存データ破損 | set / save または起動時に取り扱いが一意。利用者が文書どおりに再設定できる |
| Wi-Fi + USB probe（実装時） | 誤った SSID / secret、DHCP 失敗、IP 変更中の電源断 | USB または製品固有の復旧手段で設定を直せる。失敗状態を読める |
| IP のみの probe（実装時） | ネットワーク未設定、ルータ不在、接続先変更 | 最初の設定方法と失敗後の再設定方法が文書にあり、実機で通る |

どのボードでボタン・二度押し reset・短時間の既定口・再書き込みを採るかは、ボードの配線、boot ROM、保存方式を見て実測する。
手元の文書に IP 対応 probe の動作実験はないので、現時点で「検証済み」とは書けない。

## 4. 判断待ちとして残すもの

| 論点 | 調査後の提案 | 判断に必要な材料 |
|---|---|---|
| IP 接続の設定を v1 の標準 `probe.config` に入れるか | v1 では保留。TCP は外部指定で使用可能と明示する | 共通の Wi-Fi / Ethernet 設定が必要な独立 probe 2 種以上の実装例 |
| IP 上の自動発見を v1 に入れるか | 保留。必要なら DNS-SD の小さな binding を先に試す | USB なし、ローカルリンク、別サブネットの host 利用形態 |
| 認証なし TCP をどの環境まで許すか | core の信頼境界を維持 | 想定する設置ネットワークと利用者境界 |
| 経路ゼロの設定を規範で一律に拒否するか | 復旧策の有無も含めて決める | IP-only / ヘッドレス probe の初期設定と再設定の実機確認 |
| 回復の物理操作 | probe 開発ガイドに実装例を載せる | P4、classic ESP32、RP2 のボタン・boot ROM・NVS 等の試験 |

## 5. IP 以外の未検証項目

[review-response の「確かめていないこと」](review-response-2026-09-26.ja.md) にある次の点は、資料調査だけでは閉じない。

- firmware 更新で interface 一覧の識別値が変わったとき、古い plan / bind が適用されず、起動モードの退避が働くこと。
  既存の保存データを持つ実機で、fn の順番を変えた firmware に更新して確かめる。
- SWD の targetsel が違う場合の拒否と、アナログのチャネル別 scale / skew。該当する実機または独立実装が必要。
- L103 の attach(halt) が約 8 回に 1 回 `status line` になる原因。現行の
  [probe 開発ガイド §4](probe-development-guide.ja.md) には RVSWD の休止中の線の状態に未確認の差があり、
  配線・ロジック波形・同条件の WCH-Link との比較を先に行うべきと記録されている。
  この現象を一般の RISC-V/MCU 規則へ昇格させない。

今回の資料調査だけで新しく確定できる規範値（ポート番号、サービス名、secret の wire 形式、物理復旧操作）はない。
IP 対応が必要になった時点で、上の実装例と試験結果から最小の binding を決めるのが妥当と考える。
