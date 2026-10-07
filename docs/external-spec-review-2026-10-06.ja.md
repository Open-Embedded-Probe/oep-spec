# OEP v1 外部公開仕様レビュー（2026-10-07 再々確認）

Status: **record**（非規範）。OEP v1 freeze 前の仕様を、第三者による相互運用実装、曖昧さ、独自拡張、単純性の観点からレビューした記録。

この版は、前回レビューへの対応と、その後の TCP discovery / Wi-Fi 設定の追加を含む `764b110` を対象とする。日本語版が freeze 前の作業上の規範であるため、日本語版を基準にした。

## 1. 結論

前回指摘した core と transport の規範上の問題は、すべて実質的に解消された。

- frame は write、USB transfer、HID report、TCP segment の境界と無関係な byte stream として扱うようになった。
- `max_length` と describe の各 TLV は、probe のすべての経路の `max_frame` に収まることになった。
- broker 経由の restart では `restart_max_ms` が client に掛からないと明記された。
- fn 0 の固定形式は protocol revision で決まると明記された。
- channel の有無、数、番号の範囲と、channel 規則の適用条件が明確になった。
- 接続が閉じても session、lock、subscription、resend table が lease 等まで残ることが明記された。

core は fn 0 の8操作と、message、session、discovery、通知、共通資源規則に絞られており、「小さく単純だが拡張可能」という目標にかなり近い。現在の core 自体に freeze を妨げる大きな未解決事項は見つからなかった。`clock` を必須に残す判断も、共通 timebase を使う interface の条件分岐を増やさないという理由があり、妥当である。

一方、前回レビュー後に追加されたネットワーク機能には、新しい重要課題がある。

1. Wi-Fi の最大資格情報を載せた `set` は112 byteになり、仕様が許す `max_frame = 64` の経路では送れない。
2. TCP probe すべてに mDNS / DNS-SD を必須にしたことで、TCP framing だけを実装する最小 probe の範囲が大きくなった。
3. mDNS / DNS-SD を規範にしたが、transports の「参照する仕様」に RFC 6762 / 6763 が載っていない。
4. 非規範の conformance checklist に、削除済みの「1 frameを1回のwriteで送る」が残っている。

通常の serial / USB / TCP protocol は、規範文書だけから第三者が互換実装できる。上の1は実際に適合 probe を作れなくする組合せなので、freeze 前に必ず直すべきである。2は仕様の線引きの判断だが、小さい core を優先するなら mDNS discovery は TCP framing から分離した方がよい。

## 2. レビュー範囲

主に次を確認した。

- 公開された規範文書だけから、第三者が互換 host / probe を実装できるか。
- wire encoding、状態遷移、拒否理由が十分に一意か。
- core がすべての probe に必要な機能だけに絞られているか。
- serial、USB、TCP の違いをまたいでも同じ interface declaration が成立するか。
- 未知の TLV、enum、op、event、interface を安全に扱えるか。
- reverse-DNS interface による第三者拡張が既存実装と共存できるか。
- ESP32 Wi-Fi の実装で必要になる discovery、credentials、切断復帰が完結しているか。
- registry、生成物、test vector が文書と一致しているか。

対象は主に次である。

- [OEP core](oep-core.ja.md)
- [OEP transports](oep-transports.ja.md)
- [probe settings](../interfaces/oep-if-probe-config.ja.md)
- [restart](../interfaces/oep-if-restart.ja.md)
- [standard interface common parts](../interfaces/oep-if-common.ja.md)
- [standard interfaces](../interfaces/README.ja.md)
- [conformance](conformance.ja.md)
- [release testing](release-testing.ja.md)
- [security](security.ja.md)
- [v1 registry](../registry/oep-v1.toml)

## 3. 新たに見つかった指摘

### 3.1 High: Wi-Fi の有効な最大 `set` が `max_frame = 64` に収まらない

`oep.probe.config` の wifi item は、最大で次の値を持つ。

```text
index              1 byte
ssid_len           1 byte
ssid              32 byte
pass_len           1 byte
hex PSK           64 byte
-------------------------
item value        99 byte
```

これに item TLV の3 byteと request headerの10 byteを加えると、messageは112 byteになる。

```text
10 + 3 + 99 = 112 byte
```

しかし protocol 全体では `max_frame >= 64` しか要求していない。wifi item を広告する probe が、ある経路で `max_frame = 64` を返すことも現在の文面では適合である。その経路では、仕様上有効な32 byte SSIDと64桁PSKを一つの原子的な `set` に載せられない。

item を分割する規則はなく、分割すると SSID と secret の原子性や write-only の扱いが増える。最も小さい修正は次である。

> wifi item を `items` に広告する probe は、すべての経路で `max_frame >= 112` を返す。

この条件を probe.config §1.4、conformance、registry の limit または comment に置き、32 byte SSID + 64桁PSKの最大 request vectorも追加することを推奨する。

将来、wifi item にフィールドを足す場合は固定形式を伸ばせないため、新しい item tag または interface revision が必要である。この点は現在の拡張規則で問題ない。

### 3.2 Design: mDNS / DNS-SD を全 TCP probe の必須機能にすると core transport が重くなる

現在の transports §3 は、TCP で待ち受けるすべての probe に `_oep._tcp` の DNS-SD instanceをmDNSで広告することを要求している。自動発見はESP32 Wi-Fiでは有用だが、TCP framingの成立には必要ない。

必須にすると、次の実装もmDNS responder、DNS-SD record、multicast interface、名前衝突処理を持たなければTCP適合にならない。

- addressとportを手動設定する小さな組込みprobe。
- 認証済みtunnelの内側だけで使うprobe。
- multicastを通さないVLAN、VPN、container、cloud network上のprobe。
- brokerが発見を担当し、upstreamはTCPだけを話す構成。

hostはすでに利用者が明示したaddress / portを使える。そのため、coreを小さく保つなら次の分離を推奨する。

- TCP transportの必須部分は `length(u16), message`、接続、session、切断復帰だけにする。
- mDNS / DNS-SD advertisementは任意の「local discovery profile」にする。
- local discovery対応probeは `_oep._tcp`、SRV、TXTの規則に従う。
- hostはmDNS discoveryを実装しなくても、明示endpointでTCP適合になれる。
- projectのESP32参照profileやrelease基準では、利便性のためlocal discoveryを必須にしてよい。

wire上のcapabilityを追加する必要はない。mDNS広告が存在すればhostは発見でき、無ければ明示endpointを使うだけである。

自動発見をOEP TCPの必須要件として残す判断も可能だが、その場合は「小さいTCP probe」ではなく「local networkでゼロ設定利用できるTCP probe」を最低適合単位にしたことを明示すべきである。

### 3.3 Medium: mDNS / DNS-SD の外部仕様が参照一覧に無い

transports §3 は RFC 6762 と RFC 6763 を規範的に使うようになったが、transports §7 の「参照する仕様」はUSB仕様だけを列挙している。

core §13は、interfaceが依存する外部仕様の版と利用部分を列挙することを要求している。同じ原則をtransportにも適用し、少なくとも次を§7へ追加するとよい。

- RFC 6762: mDNS query / response、multicast interface、名前衝突と再広告。
- RFC 6763: service instance、PTR / SRV / TXT、service type、TXT keyの扱い。

RFC番号だけでも文書は特定できるが、どの部分がOEP適合に必要かを一覧に置くことで、第三者実装の範囲が明確になる。

### 3.4 Medium: conformance checklist に旧「1回のwrite」規則が残っている

規範の transports §2 は正しく、frameを任意に分割・結合でき、receiverはwrite等の境界に頼らないとしている。

一方、非規範の [conformance](conformance.ja.md) のhost checklistには、まだ次の旧規則がある。

> 1フレームを1回のwriteで送り

同じ文書のprobe checklistは新しい規則になっているため、第三者がhost側だけを実装すると解釈を誤る。次へ置き換えるべきである。

> frameは何回のwriteに分けても、複数frameを一回にまとめてもよい。receiverはその境界に頼らない。TCP以外ではframe途中に `probe_frame_gap_ms` 以上の間を置かない。

これは非規範文書の不整合でwire規則自体の欠陥ではないが、外部実装者向けchecklistなのでfreeze前に直す価値が高い。

## 4. 前回指摘の反映確認

| 前回の指摘 | 現在の状態 |
|---|---|
| frameの分割許可と1回のwriteの矛盾 | 規範は解決。conformance guideに旧文言が1か所残る |
| `max_length` と経路ごとの `max_frame` | 解決。describeは経路共通で、すべての経路に収める |
| brokerとrestartのend-to-end保証 | 解決。broker clientには `restart_max_ms` が掛からない |
| fn 0と固定形式の識別 | 解決。fn 0はprotocol revisionで決まる |
| channelの存在と番号範囲 | 解決。無ければ0個、持つprobeはtag必須、番号範囲も定義 |
| channel規則がchannel無しprobeにも見える | 解決。適合条件がchannelを持つprobeだけになった |
| 接続切断時のsession state | 解決。session、lock、subscription、resend tableは残る |
| TCP / ESP32実機検証 | release testingへ試験項目を追加。実際の実装結果はfreeze前に確認が必要 |

## 5. core の入念な再評価

### 5.1 必須範囲

fn 0は名前を持たず、listに載らない。必須操作は次の8つだけである。

- `confirm`
- `list`
- `describe`
- `clock`
- `open`
- `end`
- `keepalive`
- `lock_state`

`plan`、`restart`、`link`、probe configurationは名前付きの任意interfaceである。通知も通知を出すinterfaceだけが実装する。GPIOだけのprobe、debugだけのprobe、TCPだけのprobeなどが、不要な機能interfaceを持たずに適合できる。

### 5.2 coreに残る共通規則

次は複数interfaceに共通であり、coreに置く合理性がある。

- message header、TLV、revision、未知値の扱い。
- confirm / list / describeによる発見。
- session、lock、lease、deduplication、resource lifetime。
- channelを持つprobeにだけ適用されるchannel / electrical safetyの共通規則。
- 通知を出すinterfaceにだけ適用されるsubscriptionとdeliveryの共通規則。
- `boot_id` と共通timebase。

`clock` は最小probeに数行の実装を要求するが、任意化するとtimestampを使う各interfaceに依存条件とhost分岐が増える。実際にclockを持てないprobeの例がない限り、必須のままの方が全体は単純である。

### 5.3 状態の所有範囲

TCP接続が増えても、現在の規則から次を実装できる。

- session、lock、resource、resend tableはprobe全体で共有する。
- revision、`max_frame`、window、`max_inflight`、notification destinationは接続ごと。
- 接続が閉じてもsession等はleaseやendまで残る。
- 同じsession IDのopenを新しい接続から送るとleaseを再開し、notification destinationを移す。
- 閉じた接続へ送るはずだったresponse / notificationは捨てる。

これはESP32 Wi-Fiの瞬断・再接続にも必要な規則であり、前版より実装可能性が上がった。

## 6. 拡張性

拡張モデルは引き続き良い。

1. 互換な追加情報はTLVに置く。
2. 任意操作は`ops`で宣言する。
3. 固定形式を変えるときはinterface revisionを上げる。
4. 意味が違う機能は新しいinterface nameにする。
5. 第三者はreverse-DNS nameを登録なしで使う。

Wi-Fi設定も、既存のstate responseのTLV tailと、新しいconfig item tagを使って追加されている。既存readerは未知tagを安全に無視できるため、追加方法自体は拡張規則に沿っている。

ただし、transport discoveryはwire上のinterface extensionではない。mDNSを必須にするかoptional profileにするかを明示しないと、TCP適合の最小境界が不必要に大きくなる。

設計原則は次でよい。

> 固定形式はrevisionで守り、互換追加はTLV、操作の有無はops、意味が違うものは別interface。

これに、transportについて次を加えると境界が明確になる。

> framingと接続の規則をtransport coreに置き、自動発見は独立したprofileに置く。

## 7. TCP/IP と ESP32 Wi-Fi で確認すべきこと

[release testing](release-testing.ja.md) にTCPの分割・結合、2接続、session再接続、Wi-Fi loss、rebootが追加されたのはよい。文書上の計画だけでは仕様検証が完了したことにはならないため、freeze条件として実際のESP32結果を残すべきである。

### 7.1 framingと接続

- lengthの2 byteを別々の`recv`に分ける。
- messageを1 byte単位を含む任意位置で分ける。
- 複数frameを一回のwrite / segment / `recv`にまとめる。
- TCPでは`probe_frame_gap_ms`で受信途中を破棄しない。
- `max_frame`を超えるlengthで接続を閉じる。
- 2 clientでglobal session / lockとconnectionごとのlimitを確認する。
- 正常close、abrupt close、half-open、Wi-Fi loss、再associationを試す。
- 同じsession IDで再openし、lease、subscription destination、resend tableを確認する。
- reboot後は`boot_id`が変わり、sessionが`no_session`になることを確認する。

### 7.2 Wi-Fi設定

- open network、8 byte passphrase、63 byte passphrase、64桁hex PSKを試す。
- 32 byte SSID + 64桁PSKの112 byte requestを各transportで送る。
- getがsecretを返さず、`pass_len = 0xFF`をsetへ戻すとsecretを保持することを確認する。
- 使用中entryのset / unsetではresponseを先に受け、その後接続が切れることを確認する。
- 誤った資格情報で到達不能になった場合の物理的な復旧手順を参照実装に用意する。
- save、reboot、再接続後もsecret自体をログやresponseへ出さないことを確認する。

### 7.3 mDNSを採用する場合

- `_oep._tcp.local.` のbrowseでPTR、SRV、TXT、addressを解決する。
- TXTの`unit_id`とOEP describeの`unit_id`を照合する。
- host名またはinstance名の衝突時にRFCどおりrename / reannounceする。
- Wi-Fi再接続やIP変更後に古いrecordを残さず再広告する。
- 複数IPv4 interfaceからqueryし、IPv6対応を主張するならIPv6 interfaceでも試す。
- mDNSが届かないnetworkでは明示address / portで接続できることを確認する。

実機結果は `release-testing.ja.md` が定めるJSONに残し、使用firmware、client、board、transport、失敗条件をrelease noteから参照できるようにする。

## 8. 機械検証

次を再実行した。

```text
python3 tools/oepgen1.py --check
python3 tools/oepvectors1.py --check
cd tests && uv run pytest registry_v1 vectors
```

結果は27件すべて成功した。registry、生成物、既存vectorの不一致は見つからなかった。

現在のvectorにはwifiのset / get / write-only round-trip / refusal / state / unsetが追加されている。ただし、32 byte SSID + 64桁PSKの最大request、mDNS packet、実際のTCP stream分割、複数connectionは共有vectorでは扱っていない。

## 9. Freeze 前の推奨変更

### 必須

1. wifiを広告するprobeの全経路に`max_frame >= 112`を要求するか、最大資格情報を運べる別の分割形式を定義する。単純さのため前者を推奨する。
2. conformance checklistに残る「1 frameを1回のwrite」を削除する。
3. mDNSを規範に残すなら、RFC 6762 / 6763と使用部分をtransportsの参照一覧へ追加する。

### core / transportを小さく保つための推奨

1. TCP framingとmDNS local discoveryを分離する。
2. 明示address / portだけでTCP適合になれるようにする。
3. ESP32参照profileではmDNSを要求し、使いやすさを保つ。

### Freeze判定の実装条件

1. ESP32 Wi-FiのTCP probeを独立hostから操作する。
2. 最大wifi itemを含む全credential vectorを通す。
3. TCP分割・結合、2 client、切断、再接続、rebootを通す。
4. mDNSを採用するなら、広告、衝突、再広告、複数interfaceを通す。
5. 実機結果を保存し、仕様の各規則へ対応づける。

### Release前

1. 日本語の規範文書から英語版を同期する。
2. 節番号の欠番を整理する。
3. 規範文書、registry、生成物、vectorを同じimmutable release tagに含める。

## 10. 最終評価

coreの縮小と前回指摘への対応は良好である。fn 0は小さく、optional interfaceとreverse-DNS extensionの境界も明確で、第三者が独自機能を追加できる。通常のprotocol pathは仕様書だけから互換実装できる水準にある。

今回の最大の規範上の問題は、wifiの最大有効requestと`max_frame=64`の不整合である。これはESP32実装を行えば早い段階で見つかる種類の問題であり、「実装しないと仕様上の不備を見つけにくい」という判断を裏づける。

mDNS / DNS-SDは実用上有益だが、全TCP probeの必須機能にするかはcoreの小ささに直接影響する。TCP transportとlocal discovery profileを分け、ESP32参照実装では両方を実装する構成が、単純性、拡張性、実用性のバランスが最もよい。
