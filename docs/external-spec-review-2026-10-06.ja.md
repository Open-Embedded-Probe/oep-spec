# OEP v1 外部公開仕様レビュー（2026-10-07 最終再確認）

Status: **record**（非規範）。OEP v1 freeze 前の仕様を、第三者による相互運用実装、曖昧さ、独自拡張、単純性の観点からレビューした記録。

この版は、前回の再々確認への対応を含む `9118dc0` を対象とする。freeze 前は日本語版が作業上の規範であるため、日本語版を基準にした。

## 1. 結論

前回までに指摘した protocol 上の問題はすべて解消された。今回、新しい wire-level の矛盾、独立実装を妨げる曖昧さ、core の過剰な必須機能は見つからなかった。

- wifi itemを広告するprobeは、すべての経路で`max_frame >= 112`を返すことになった。
- 32 byte SSIDと64桁PSKを載せた112 byteの最大request vectorが追加された。
- mDNS / DNS-SD advertisementは任意になり、TCP framingだけのprobeも適合できる。
- advertisementを行う場合の唯一の形は `_oep._tcp`、SRVのport、TXTの`unit_id`に決まっている。
- RFC 6762 / 6763と使用部分がtransportsの参照一覧に追加された。
- conformance checklistに残っていた「1 frameを1回のwrite」が削除された。

coreはfn 0の8操作と、message、session、discovery、通知、共通資源規則に絞られている。`plan`、`restart`、`link`、probe configurationは名前付きの任意interfaceであり、通知とchannelの規則も、それらを使うprobeにだけ適用される。「小さく単純だが拡張可能」という目標を満たしている。

現在残る仕様公開前の指摘は、DNS-SD service name `oep` のIANA登録確認だけである。これは現在のローカル実装を妨げるwire上の欠陥ではないが、公開されたservice nameの衝突を防ぐため、freeze前に処理すべきgovernance項目である。

仕様書だけから互換host / probeを実装できる水準に達している。ただし、ESP32 Wi-Fiの参照実装と独立hostによる実機試験結果は、仕様の明確さとは別のfreeze条件として残る。

## 2. レビュー範囲

主に次を確認した。

- 公開された規範文書だけから、第三者が互換host / probeを実装できるか。
- wire encoding、状態遷移、拒否理由が十分に一意か。
- coreがすべてのprobeに必要な機能だけに絞られているか。
- serial、USB、TCPの違いをまたいでも同じinterface declarationが成立するか。
- 未知のTLV、enum、op、event、interfaceを安全に扱えるか。
- reverse-DNS interfaceによる第三者拡張が既存実装と共存できるか。
- ESP32 Wi-Fiに必要なframing、discovery、credentials、切断復帰が完結しているか。
- registry、生成物、test vectorが文書と一致しているか。

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

## 3. 現在残る指摘

### 3.1 Medium / Governance: DNS-SD service name `oep` を公開前に登録する

OEPはDNS-SDのservice typeとして`_oep._tcp`を定義している。RFC 6763 §7と§16ではservice nameをIANA管理の名前空間として扱い、RFC 6335がservice nameの登録手順を定めている。

2026-10-07時点の[IANA Service Name and Transport Protocol Port Number Registry](https://www.iana.org/assignments/service-names-port-numbers/)には、`oep`のentryがない。service nameはfirst-come, first-servedであり、未登録のまま外部公開すると、別用途による先行登録または同名利用との衝突リスクが残る。

推奨する対応は次である。

1. freeze前にservice name `oep`をIANAへ申請する。
2. 固定portは仕様で使わないため、service nameだけを申請する。
3. descriptionにOpen Embedded Probe protocolを示す。
4. DNS-SD TXT keyとして`unit_id`を使用することをassignment notesまたは公開仕様で関連づける。
5. 登録が完了する前に名前をfreezeする場合は、登録未完了であることと変更可能性をrelease blockerとして明記する。

RFC 6335は、DNS SRV等のためにport番号を伴わないservice nameだけを申請できるとしている。したがって、現在の「portはSRVで決まり、固定portは無い」という設計を変える必要はない。

これはprotocol framingやESP32実装のblockerではない。しかし、`_oep._tcp`を外部の独立実装が永続的な識別子として使い始める前に確定すべきである。

## 4. 前回指摘の反映確認

| 指摘 | 現在の状態 |
|---|---|
| frameの分割許可と1回のwriteの矛盾 | 解決。任意に分割・結合でき、receiverは境界に頼らない |
| conformance guideに残った旧write規則 | 解決。transports §2と同じ文へ更新 |
| `max_length` と経路ごとの `max_frame` | 解決。describeは経路共通で、すべての経路に収める |
| wifi最大requestが`max_frame = 64`に収まらない | 解決。wifi対応probeは全経路で112以上 |
| 最大wifi requestのvectorが無い | 解決。112 byte vectorとregistry計算試験を追加 |
| mDNSが全TCP probeに必須 | 解決。advertisementはprobeが選び、明示endpointだけでも適合 |
| mDNS / DNS-SDの外部仕様が参照一覧に無い | 解決。RFC 6762 / 6763と使用部分を追加 |
| brokerとrestartのend-to-end保証 | 解決。broker clientには`restart_max_ms`が掛からない |
| fn 0と固定形式の識別 | 解決。fn 0はprotocol revisionで決まる |
| channelの存在と番号範囲 | 解決。無ければ0個、持つprobeはtag必須、番号範囲も定義 |
| channel規則がchannel無しprobeにも見える | 解決。適合条件がchannelを持つprobeだけになった |
| 接続切断時のsession state | 解決。session、lock、subscription、resend tableは残る |
| TCP / ESP32実機検証 | release testing §3の10〜12へ記載。実行結果は別途必要 |

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

`plan`、`restart`、`link`、probe configurationは名前付きの任意interfaceである。通知を使わないprobeはsubscriptionを実装せず、channelを持たないprobeにはchannelの電気規則を要求しない。

GPIOだけのprobe、debugだけのprobe、TCP framingだけのprobeも、不要なinterfaceやmDNS responderを持たずに適合できる。

### 5.2 coreに残る共通規則

次は複数interfaceに共通であり、coreに置く合理性がある。

- message header、TLV、revision、未知値の扱い。
- confirm / list / describeによる発見。
- session、lock、lease、deduplication、resource lifetime。
- channelを持つprobeにだけ適用されるchannel / electrical safetyの共通規則。
- 通知を出すinterfaceにだけ適用されるsubscriptionとdeliveryの共通規則。
- `boot_id`と共通timebase。

`clock`は最小probeにも必要だが、任意化するとtimestampを使う各interfaceに依存条件とhost分岐が増える。clockを実装できない具体的なprobeがない限り、必須のままの方が仕様全体は小さい。

### 5.3 TCP接続と状態の所有範囲

複数TCP接続とWi-Fi再接続について、現在の規則から次を一意に実装できる。

- session、lock、resource、resend tableはprobe全体で共有する。
- revision、`max_frame`、window、`max_inflight`、notification destinationは接続ごと。
- 接続が閉じてもsession等はlease、end、force、rebootまで残る。
- 同じsession IDのopenを新しい接続から送るとleaseを再開し、notification destinationを移す。
- 閉じた接続へ送るはずだったresponse / notificationは捨てる。
- reboot後は`boot_id`が変わり、以前のsessionとresourceは失われる。

TCPのwrite、segment、`recv`境界には意味がなく、lengthとmessageを任意位置で分割できる。TCPには`probe_frame_gap_ms`を適用しない。第三者は一般的なstream parserとして実装できる。

## 6. 互換実装可能性

現在の日本語規範文書から、次を独立実装できる。

- serial / vendor bulk / HID / TCPのframing。
- request、response、event、data headerとTLV。
- confirm、list、describeによるdiscovery。
- session、lock、lease、resend、deduplication、resource lifetime。
- interfaceごとのoptional opとnotification capabilityの発見。
- 標準interfaceのrequest / responseと状態遷移。
- reverse-DNS名を使った独自interface。
- 手動endpointによる最小TCP probe。
- 任意のmDNS advertisementを持つlocal-network TCP probe。
- wifi credentialsの設定、write-only secret、接続状態の取得。

USB、mDNS / DNS-SD、SWD、ADI、RISC-V DM、I2C等は、規範文書に列挙された外部仕様も必要である。依存する仕様と使用部分が明示されており、OEP側の不足ではない。

freeze前は日本語版だけが最新の規範である。正式なv1 releaseでは英語版を同期し、同じrelease tagへ含める必要がある。

## 7. 拡張性

拡張モデルは単純で、第三者による追加にも適している。

1. 互換な追加情報はTLVに置く。
2. 任意操作は`ops`で宣言する。
3. 安全に無視できるevent、enum、bitは規定された条件で追加する。
4. 固定形式を変えるときはinterface revisionを上げる。
5. 意味が違う機能は新しいinterface nameにする。
6. 第三者はreverse-DNS nameを登録なしで使う。

Wi-Fi設定は既存state responseのTLV tailと、新しいconfig item tagで追加された。既存readerは未知tagを安全に無視できる。TCP discoveryもframingの必須機能ではなくなり、advertisementを持たない小さな実装を保てる。

設計原則は次の一文で説明できる。

> 固定形式はrevisionで守り、互換追加はTLV、操作の有無はops、意味が違うものは別interface。

## 8. TCP/IP と ESP32 Wi-Fiによる検証

[release testing](release-testing.ja.md)には、次が追加されている。

- TCP lengthとmessageの任意分割、複数frameの結合。
- 2接続によるlock競合と接続ごとのconfirm。
- 同じsession IDでの再接続とresend table。
- Wi-Fi loss後とreboot後の再接続。
- 全経路の`max_frame >= 112`と最大wifi item。
- advertisementを行うprobeのSRV port、TXT / describeの`unit_id`一致。
- Wi-Fi再接続とreboot後の再広告。

これは前回提言の主要部分を覆う。freeze前には、ESP32 Wi-Fi probeと独立したhostで実際に実行し、結果JSONをrelease noteから参照できるようにする必要がある。

追加で実装側が確認するとよい項目は次である。

- open network、8 byte、63 byte、64桁hexの各credential。
- getがsecretを返さず、`pass_len = 0xFF`のround-tripでsecretを保持すること。
- 使用中entryの変更ではset responseが届いてから接続が切れること。
- abrupt close、half-open、Wi-Fi再association。
- mDNS名の衝突、IP変更後の古いrecordの消去、複数network interface。
- 誤った資格情報でTCP到達不能になった場合のUSB / serialからの復旧。

これらは新しいwire規則を要求するものではなく、規範どおりの実装であることを確かめる試験である。

## 9. 機械検証

次を再実行した。

```text
python3 tools/oepgen1.py --check
python3 tools/oepvectors1.py --check
cd tests && uv run pytest registry_v1 vectors
```

結果は28件すべて成功した。registry、生成物、既存vectorの不一致は見つからなかった。

vectorにはwifiのset / get / write-only round-trip / refusal / state / unsetと、32 byte SSID + 64桁PSKの112 byte最大requestが含まれる。TCP streamの分割、複数connection、mDNS packetは実装と結合試験の範囲として明示されている。

## 10. Freeze 前の残作業

### 仕様・名前管理

1. DNS-SD service name `oep`をIANAへ申請するか、登録完了前は名前をfreezeしない。

### 実装によるFreeze判定

1. ESP32 Wi-FiのTCP probeを独立hostから操作する。
2. release testing §3の10〜12を実行する。
3. credential、切断、再接続、reboot、advertisementの結果を保存する。
4. 実機で見つかった規範不足があれば、破壊的変更が可能な間に仕様へ戻す。

### Release前

1. 日本語の規範文書から英語版を同期する。
2. 節番号の欠番を整理する。
3. 規範文書、registry、生成物、vectorを同じimmutable release tagへ含める。

## 11. 最終評価

coreは十分小さく、状態と拡張の規則も一貫している。通常のprotocol path、最小TCP path、mDNSを使うlocal discovery、ESP32 Wi-Fi設定を、現在の日本語仕様だけから第三者が実装できる。

独自拡張はreverse-DNS interface、TLV、`ops`、revisionによって既存実装から分離できる。未知値の扱いも定義されており、拡張性は担保されている。

現時点で仕様内容そのものにfreeze blockerは見つからない。残るのは、DNS-SD service nameの登録、ESP32と独立hostによる実装検証、英語版同期とrelease作業である。特にESP32実装は、文書レビューでは見えないstream分割、複数connection、Wi-Fi切断、credential最大長を検証するため、freeze前に完了すべきである。
