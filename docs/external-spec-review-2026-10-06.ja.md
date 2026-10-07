# OEP v1 外部公開仕様レビュー（2026-10-07 core 再確認）

Status: **record**（非規範）。OEP v1 freeze 前の仕様を、第三者による相互運用実装、曖昧さ、独自拡張、単純性の観点からレビューした記録。

この版は、DNS-SD の未登録名について host guide を更新した `0991759` を対象とする。freeze 前は日本語版が作業上の規範であるため、日本語版を基準にした。今回は特に [OEP core](oep-core.ja.md) を先頭から再読し、wire encoding、状態遷移、ページング、資源番号を独立実装者の視点で再確認した。

## 1. 結論

前回までに指摘した protocol 上の問題は解消された。core の分割、状態モデル、再送、拡張モデルに大きな設計上の問題はなく、必須範囲も十分小さい。一方、今回の core 集中再読で、freeze 前に直すべき局所的な規範上の不備を3点見つけた。

1. describe の TLV が `max_frame` に収まるという条件に、応答headerと`more`を含むことが明示されていない。
2. describe等のページング終端に、その応答形式には無い`count`を返すと書かれている。
3. probe全体で共有するresource numberが1から始まり、0を割り当てないことがcore日本語版には明記されていない。

いずれも新しい仕組みを足す変更ではなく、既存設計の意図を1〜2文で固定する修正である。しかし、1と2は実際のresponse byte列、3は`connection = 0`を「無し」とするinterfaceとの整合に関わるため、規範文を直してからfreezeするべきである。

- wifi itemを広告するprobeは、すべての経路で`max_frame >= 112`を返すことになった。
- 32 byte SSIDと64桁PSKを載せた112 byteの最大request vectorが追加された。
- mDNS / DNS-SD advertisementは任意になり、TCP framingだけのprobeも適合できる。
- advertisementを行う場合の唯一の形は `_oep._tcp`、SRVのport、TXTの`unit_id`に決まっている。
- RFC 6762 / 6763と使用部分がtransportsの参照一覧に追加された。
- conformance checklistに残っていた「1 frameを1回のwrite」が削除された。

coreはfn 0の8操作と、message、session、discovery、通知、共通資源規則に絞られている。`plan`、`restart`、`link`、probe configurationは名前付きの任意interfaceであり、通知とchannelの規則も、それらを使うprobeにだけ適用される。「小さく単純だが拡張可能」という目標を満たしている。

DNS-SD service name `oep` はIANAに登録しない方針である。これは現在のローカル実装を妨げるwire上の欠陥ではなく、登録をOEP適合やfreezeの条件にはしない。未登録名であることと、同名の別serviceをIANAが排除してくれる保証がないことだけを明記して使う。

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

### 3.1 Medium / Core: describe の1 TLVが収まる条件に応答overheadを含める

core §7.3は、probeがdescribeの「TLVを1つずつ、自分のどの経路のmax_frameにも収まる大きさにする」と定める。しかしdescribe responseには、message header 5 byteと`more` 1 byteがTLVより前にある。現状の文を「encoded TLV単体がmax_frame以下」と読めば、そのTLVを載せたresponseは最大6 byte超過する。

規範は、例えば次の条件にする。

> probeは、各TLVについて、応答header 5 byte、more 1 byte、そのTLV全体（tag 1 byte、len 2 byte、value）を合わせた長さが、自分のどの経路のmax_frameにも収まるようにする。

すなわち、describe TLVのvalue長の上限は、経路の最小`max_frame - 9` byteである。この修正はwire形式を増やさず、元の意図を正確にするだけである。conformanceの「各TLVがmax_frameに収まる」も同じ表現へ合わせる。

### 3.2 Medium / Core: ページング終端の`count 0`を「要素0個」に直す

core §7.3の共通規則は、firstが数以上なら「count 0とmore 0」を返すとしている。しかしdescribe responseは`more(u8), TLVの並び`であり、count fieldを持たない。probe.configのgetもcountを持たない。字面どおりに実装すると、describeの空pageに余分な0 byteを付ける実装と、TLV 0個なので`more`だけを返す実装に分かれうる。

次のようにfield名ではなく要素数で書けば、すべての対象に適用できる。

> firstが数以上なら、要素を0個、more = 0で返す。count fieldを持つ応答ではcount = 0とする。

### 3.3 Medium / Core: resource numberの0を明示的に予約する

core §9はresource numberをu16とし、「新しい資源を作るたびに前の番号から1進め、65535の次は1」とするが、最初の番号と0を割り当てるかを日本語規範で明記していない。一方、probe.configの`slot_state.connection`は0を「接続無し」のsentinelに使い、consoleはcore §9の番号を「1から進める」と説明する。

独立したcore実装が最初のresourceに0を割り当てると、標準interfaceの0 sentinelと衝突する。core §9で次を明記する。

> resource numberは1から65535。新しい資源には前の番号から1進めた番号を割り当て、65535の次は1とする。0は資源に割り当てない。

### 3.4 Note / Core editorial: 意味は確定している表現上の修正

次は他の節から正しい意味を一意に回復でき、相互運用上のblockerではないが、coreをfreezeするときに直すとよい。

- §1の`fn`は「そのセッションの間」とあるが、§7.2では同じboot_idの間、対応が固定される。用語表も「その起動の間」とする。
- §4.4は`max_frame`、`window`、`max_inflight`の3値を挙げた直後に「両方の上限」とする。どれを指すか列挙するか、「これらの上限」とする。
- §6.5はboot_idを「起動ごとに変わる値」と定義しつつ、最後のfallbackでは繰り返しを許す。「変わるように選ぶ値」とすれば、許容する確率的衝突と矛盾して見えない。

### 3.5 解決確認 / Governance: DNS-SD service name `oep` は未登録名として使う

OEPはDNS-SDのservice typeとして`_oep._tcp`を定義している。ここで以前述べた「IANA登録」は、固定TCP port、domain、組織名、商標の登録ではなく、先頭labelに使うservice name `oep`をIANAのService Name and Transport Protocol Port Number Registryへ載せる申請を指す。

2026-10-07時点の[IANA Service Name and Transport Protocol Port Number Registry](https://www.iana.org/assignments/service-names-port-numbers/)には、`oep`のentryがない。projectは登録しないため、`_oep._tcp`はOEP仕様がlocal discovery用に選んだ未登録名として扱う。

`0991759`で、未登録名であること、発見したすべてのendpointをconfirmとdescribeで検証すること、検証できない候補を外すことがhost guideに明記された。以前のレビューで求めた文書上の対応は完了した。

維持すべき扱いは次である。

1. `_oep._tcp`をIANA登録済みの一意な名前として扱わない。
2. advertisementで見つけたendpointも、通常どおりOEP `confirm`とfn 0の`describe`で検証する。
3. TXTの`unit_id`だけを認証またはprotocol判定として信頼しない。
4. 将来IANAで`oep`が別用途に登録された場合は、service typeの変更と移行手順を別途決める。

未登録でもmDNS / DNS-SDのpacket形式、SRVによるport解決、TXTの`unit_id`は実装できる。登録の有無はwire形式を変えない。

衝突時に無関係なserviceへ接続する可能性は残るが、hostは最初にOEP `confirm`だけを送り、正しい応答が無ければ閉じる。さらにTXTとdescribeの`unit_id`を照合するため、同名であるだけのendpointをOEP probeとして使い続けない。この残余リスクを受け入れるなら、IANA登録はfreeze blockerではない。

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

今回見つけた3点は既存vectorの対象外なので、現在の成功はそれらを否定しない。修正時には、最小`max_frame = 64`でvalue 55 byteのdescribe TLVが1個だけ収まる例、範囲外firstへのdescribe responseが`more = 0`の1 byteだけである例、最初のresource numberが1でwrap後も0を使わない例を追加すると再発を防げる。

## 10. Freeze 前の残作業

### 仕様

1. core §7.3のdescribe TLV上限に、response headerと`more`を含める。
2. core §7.3のページング終端を「要素0個、more = 0」に直す。
3. core §9でresource numberを1〜65535とし、0を割り当てないと明記する。
4. conformanceの対応する記述を同期し、可能なら3.4のeditorial項目も直す。
5. `_oep._tcp`を未登録名として扱い、`confirm`とdescribeによるin-band検証を維持する（host guideへの注記は`0991759`で完了）。

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

coreは「ほぼ問題ない」と評価できる。ただし「このまま規範をfreezeしてよい」段階ではなく、上の3点を先に直す。その後にESP32と独立hostによる実装検証を通せば、core設計を見直す可能性は低い。
