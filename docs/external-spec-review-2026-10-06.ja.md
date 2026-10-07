# OEP v1 外部公開仕様レビュー（2026-10-07 core / interface 再確認）

Status: **record**（非規範）。OEP v1 freeze 前の仕様を、第三者による相互運用実装、曖昧さ、独自拡張、単純性の観点からレビューした記録。

この版は、DNS-SD の未登録名について host guide を更新した `0991759` を対象とする。freeze 前は日本語版が作業上の規範であるため、日本語版を基準にした。今回は [OEP core](oep-core.ja.md) に加え、`interfaces/*.ja.md` の標準インターフェースを先頭から再読し、wire encoding、状態遷移、ページング、資源番号を独立実装者の視点で再確認した。

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

coreとtransportの通常経路は、仕様書だけから互換host / probeを実装できる水準に達している。ただし、ESP32 Wi-Fiの参照実装と独立hostによる実機試験結果は、仕様の明確さとは別のfreeze条件として残る。

標準interface側は同じ評価ではない。plan、link、restart、probe.config、GPIO / UART / I2Cは概ね実装可能だが、共通streamとcaptureには独立実装のwireまたは状態が分かれる未確定箇所が残る。特にcaptureは、configure / queryの必須入力・必須応答、capture-groupのgeneration列、世代をまたぐ通知を確定するまでfreezeしない。

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

現在の日本語規範文書から、core / transportと、下記の標準interfaceの通常経路を独立実装できる。

- serial / vendor bulk / HID / TCPのframing。
- request、response、event、data headerとTLV。
- confirm、list、describeによるdiscovery。
- session、lock、lease、resend、deduplication、resource lifetime。
- interfaceごとのoptional opとnotification capabilityの発見。
- plan、link、restart、probe.config、GPIO / UART / I2C等の標準interfaceの通常のrequest / responseと状態遷移。
- reverse-DNS名を使った独自interface。
- 手動endpointによる最小TCP probe。
- 任意のmDNS advertisementを持つlocal-network TCP probe。
- wifi credentialsの設定、write-only secret、接続状態の取得。

USB、mDNS / DNS-SD、SWD、ADI、RISC-V DM、I2C等は、規範文書に列挙された外部仕様も必要である。依存する仕様と使用部分が明示されており、OEP側の不足ではない。

capture、共通streamのmarks、SPIの部分byte、consoleの大きな一覧、debugの一部の端の場合は§12の修正が必要であり、全標準interfaceを独立実装可能とはまだ判定しない。

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

今回見つけたcoreの3点と§12のinterface項目は既存vectorの対象外なので、現在の成功はそれらを否定しない。修正時には、最小`max_frame = 64`でvalue 55 byteのdescribe TLVが1個だけ収まる例、範囲外firstへのdescribe responseが`more = 0`の1 byteだけである例、最初のresource numberが1でwrap後も0を使わない例を追加すると再発を防げる。interface側は、marksの継続と欠落、capture configureの必須集合、capture-groupのgenerations、世代をまたぐevent、SPIの部分byte、console streamsの最後のpageをvectorにする。

## 10. Freeze 前の残作業

### 仕様

1. core §7.3のdescribe TLV上限に、response headerと`more`を含める。
2. core §7.3のページング終端を「要素0個、more = 0」に直す。
3. core §9でresource numberを1〜65535とし、0を割り当てないと明記する。
4. conformanceの対応する記述を同期し、可能なら3.4のeditorial項目も直す。
5. `_oep._tcp`を未登録名として扱い、`confirm`とdescribeによるin-band検証を維持する（host guideへの注記は`0991759`で完了）。
6. §12.1〜§12.7のinterface契約を確定し、registry、conformance、vectorを同期する。

### 実装によるFreeze判定

1. ESP32 Wi-FiのTCP probeを独立hostから操作する。
2. release testing §3の10〜12を実行する。
3. credential、切断、再接続、reboot、advertisementの結果を保存する。
4. 実機で見つかった規範不足があれば、破壊的変更が可能な間に仕様へ戻す。

### Release前

1. 日本語の規範文書から英語版を同期する。
2. 節番号の欠番を整理する。
3. 規範文書、registry、生成物、vectorを同じimmutable release tagへ含める。

## 11. coreの評価

coreは十分小さく、状態と拡張の規則も一貫している。通常のprotocol path、最小TCP path、mDNSを使うlocal discovery、ESP32 Wi-Fi設定を、現在の日本語仕様だけから第三者が実装できる。

独自拡張はreverse-DNS interface、TLV、`ops`、revisionによって既存実装から分離できる。未知値の扱いも定義されており、拡張性は担保されている。

coreは「ほぼ問題ない」と評価できる。ただし「このまま規範をfreezeしてよい」段階ではなく、上の3点を先に直す。その後にESP32と独立hostによる実装検証を通せば、core設計を見直す可能性は低い。

標準interface群は、単純なinterfaceはこの水準に近いが、captureと共通streamにfreeze前の仕様修正が残る。したがってOEP全体については、まだ「仕様書だけで全標準interfaceの互換実装ができる」とは結論しない。

## 12. 標準interfaceの再評価

### 12.1 High / Capture: configure / queryの契約を閉じる

`oep.fixture.logic` / `analog`のconfigureとqueryは「設定のTLV」と「実際の値のTLV」を列挙するが、次が規範として決まっていない。

- requestで必須なのはどのTLVか。少なくともmodeとrate、one-shot / repeatのsamplesは必須に見えるが、明記されていない。
- modeごとに、samples、segments、trigger、pretriggerを省略したときの値と、送ってはいけない組み合わせ。
- success responseで必ず返すTLV。hostがdataを解釈するには、少なくともactual_rate、layout、actual_samples、actual_segments、blocking_msが必要で、analogではscale、frontend_used等の要否も決める必要がある。
- `den = 0`、pretriggerがsamplesまたはmax_pretriggerを超える場合、triggerのroleがplanに無い場合などの断り方。

TLVをすべて任意と読む実装と、表の一部を必須と読む実装では、空または部分的なconfigureの結果が異なる。各TLVを「必須／省略時の値／そのmodeでは不可」のいずれかに分類し、success responseの必須集合を明記する。

### 12.2 High / Capture-group: generations TLVの形と必須性を直す

capture-groupのstart responseは、TLV 0x01 generationsを`n × (fn(u16), generation(u32))`とする。しかしcore §2.3は、可変の並びを`count, count × element`と定める。現在の形にはcountが無く、registryも同じ記述である。

さらに、個々のtrackのread / releaseにはgenerationが必須なので、このTLVを省略可能にできない。次のどちらかに固定する。

> `n(u8), n × (fn(u16), generation(u32))`。start successでは必須で、nはbind中のtrack数と一致し、各fnを1回ずつ含む。

または、固定部に同じ列を移す。前者の方が現在の拡張モデルを変えない。

### 12.3 High / Capture通知: 世代をまたいだ古いeventを識別可能にする

streaming dataには、start responseの後に前世代の送り残しが届きうるためgeneration TLVが必須である。一方、trackの`triggered`と`stopped` eventにはgenerationがない。core §11.4は届いているrequestへのresponseをnotificationより先に送るため、前世代で生まれて送信待ちだったeventが、新しいstart responseの後に届くことがある。hostはそれを新世代の停止・トリガと区別できない。

trackの`triggered` / `stopped`にgenerationを含める。capture-groupにも同じ問題があるため、group固有のrun generationを導入するか、eventにtrackのgenerationsを載せるか、start前に旧eventを必ず破棄してseqの欠落として示す、のいずれかを規範にする。

### 12.4 Medium / Common streamとCapture: serialによるページングを定義する

共通streamのmarksはrequestを`from_serial(u32)`とするだけで、次が書かれていない。

- `from_serial`と同じserialを含めるのか、その次からなのか。
- request位置がリングから押し出されていた場合、残る最古から返すのか。
- request位置が最新より先の場合の空response。
- `more`が何を意味し、次のrequestにどの値を入れるか。
- u32 wrap時の比較。

captureのsegmentsも、`from_serial`、`serial_done`、releaseの比較とwrapが十分に閉じていない。`from_serial == serial_done`のときは返すsegmentが無いが、本文は「より先」だけを空successとしている。未来のserialをreleaseした場合の扱いも未定義である。marksとsegmentsについて、inclusiveな開始、欠落時の最古、空page、継続値、wrapまたは1 generation内の上限を明記する。

captureのgenerationもstart前の0とstart後の1から始まることは決まっているが、`0xFFFFFFFF`の次を決める必要がある。0を予約して1へ戻すか、同じboot中のstart回数を制限する。

### 12.5 Medium / Console: streams paginationの到達可能な件数を決める

consoleのstreamsはprobe全体の生存streamと、まだ読めるclosed streamを一覧にするが、requestのfirstはu8で、総数の上限がない。256件を超えると次pageのfirstを表せない。debugのconnectionsは各wireの`max_connections(u8)`で上限を持つが、consoleには対応する上限がない。

破壊的変更が可能な今ならfirstをu16にするのが単純である。u8を保つなら、一覧に同時に現れるstreamを256件以下に制限し、最後のpageでmore = 0になることを明記する。

### 12.6 Medium / SPI target: byte途中で終わるtransferのdataを定義する

SPI targetは実際のbit数を返し、data長を`ceil(bits / 8)`とするため、CSがbyte途中で戻るtransferを表せる。しかし最後の部分byteについて、受けたbitを上位／下位のどちらへ置くか、未使用bitを何にするかが定義されていない。MSB-firstとLSB-firstの双方についてpackingを規定する。

I2C / SPIのread_rxが付けられる`ns` TLVも「受けた時刻」だけではSTART、最初のdata bit、STOP / CS解除のどれか不明なので、基準点を決める。SPIの`bits(u32)`が飽和・wrapするほど長いCS区間をどう扱うかも、上限、飽和、またはerrorのどれかにする。

### 12.7 Medium / Debug: 一部の固定response fieldの意味を補う

- riscv-dm runの`elapsed_us`を、どの時点からどの時点まで測るか、run前失敗や停止失敗では何を返すか定める。
- stepの失敗時に`moved`、`dpc_before`、`dpc_after`のどれが有効で、無効fieldに何を入れるか定める。
- arm-adi transferの`n = 0`をsuccessにするかmalformedにするかと、その場合の`ack`を定める。
- debug §4.3にはreset outcomeの説明が同じ文で2回続く箇所があるため削る。

これらはdebug全体のstate machineを変える問題ではないが、固定fieldを独立hostが同じ意味で表示・判定するために必要である。

### 12.8 提案 / Logic captureのチャネル別縮約を任意拡張として設計する

現在のlogic captureは、1 trackの全channelを同じrateで保存する基本形式に絞っている。この判断は基本実装を小さく保つ点では妥当だが、ESP32-P4の試作で成立している次の用途を直接は表せない。

- 全pinは同じbase rate（例: 100 MHz）で同時に観測する。
- SPI clock / MOSI / MISO等は全sampleを残す。
- CS、IRQ、button等は1/32等へ縮約して、保存・転送・codec処理の予算へ収める。
- 単純にD点ごとの1点を残すだけでなく、「区間内にLOWが一度でもあればLOW」のように短いactive pulseを残す。

これは、低速channelを別trackの3.125 MHz取得として扱うのとは意味が違う。後者では、100 MHzの共通時間格子、正確な整数比、縮約bucketの位相、bucket内で何を観測したかを表せない。

基本layoutへこの機能を混ぜず、予約済みのcapture拡張範囲を使う任意の標準multirate定義とすることを提案する。基本captureだけのprobe / hostには実装を要求しない。再設計時には、少なくとも次を規範にする。

- track全体の`base_rate`。segmentのsamples、trigger index、時刻の基準はbase sampleの番号で数える。
- channel（role）ごとの`step = D`と、点を選ぶ形式では`phase`。保存点jはbase sample `phase + j * D`に対応する。
- bucketから保存値を作る縮約policy。ESP32-P4の試作では、全点を残す`raw`、指定位置の1点を残す`decimate_hold`、active levelが一度でもあればactiveにする`any_active`、bucket末尾levelとactive edgeの有無を残す`edge_latch`を検証している。
- `any_active` / `edge_latch`のactive polarity。active-lowの`any_active`が「LOWが一度でもあればLOW」であり、active-highはその逆である。
- dataのblock layout、channel順、bit packing、block末尾のpadding、最後の不完全block。異なるstepのchannelを既存の単一rate interleaved layoutとして送ってはならない。
- 縮約値の時刻上の意味と不確かさ。`any_active`はbucket内にactiveが存在したことだけを表し、その正確な位置や長さを表さない。
- triggerを縮約前のbase samplesで評価するのか、縮約後の値で評価するのか。短いCS / IRQをtriggerに使う用途では、縮約前に評価してbase sample単位のtrigger時刻を返す形が有用である。

設定自体は、roleごとの小さなdescriptor（概念的には`role, policy, step, phase-or-polarity`）の繰り返しで表せる。試作ではpower-of-twoのDを`log2(D)`で表したが、OEPで同じ制約にするか、一般の整数Dにするかは実装能力とblock layoutを合わせて設計し直す。初版をさらに小さくするなら、1 bitを返す`raw` / 点選択 / `any_active`だけを標準化し、2 bitを返す`edge_latch`は予約または後続revisionにできる。

予算も1個の「Mbps」にまとめない。少なくとも、全pinを読むcapture前段、縮約後のpayload、byte paddingとframe overheadを含むwire、codec処理能力を区別する。縮約後の論理payloadは、1 bitを返すpolicyなら概ね`sum(base_rate / D[channel])` bit/s、`edge_latch`ならそのchannelを2 bitとして数えられる。ただし最終的な可否はpin幅、DMA、block packingと実測codec能力にも依存するため、describeの数値だけで成功を保証せず、query / configureの実際の応答を正とする。

この機能はcoreのfreeze条件ではなく、既存の基本capture wireを破壊する必要もない。一方、複数の私有codecが生まれる前に、共通の意味（base rate、step、phase、policy、不確かさ）とcodec識別方法だけは標準の任意拡張として揃える価値がある。ESP32-P4実装と、既にmultirateを扱える後処理を接続してvectorを作れば、仕様の不足を早く発見できる。

### 12.9 interface別の現在評価

| 範囲 | 評価 | 残る作業 |
|---|---|---|
| common stream | 要修正 | marksのserial paging |
| plan | ほぼ良い | 存在しないfnと「planの無いfn」の表現を明確化 |
| link | ほぼ良い | 実機UART bridgeでspeed切替と自動復帰を検証 |
| restart | ほぼ良い | USB / TCP / brokerの実装試験 |
| probe.config / Wi-Fi | ほぼ良い | ESP32でcredential、応答後切断、再接続を検証 |
| GPIO / UART / I2C target | ほぼ良い | UART statusのplan無し時とtimestamp基準を補足 |
| SPI target | 要修正 | 部分byte、timestamp、極端に長いtransfer |
| console / dmseq | 概ね良い | streams一覧の上限またはfirst幅 |
| wire / debug target | 概ね良い | 固定responseの端の場合、scan総候補数の上限 |
| logic / analog capture | 要修正 | configure契約、serial / generation、notification。logicのmultirate縮約は任意拡張として再設計を提案 |
| capture-group | 要修正 | generations列と古いeventの識別 |

拡張の構造自体は良い。interface name、revision、optional opの`ops`、request / response TLV、別interfaceによる大きな意味の分離は一貫している。問題は拡張余地ではなく、既にrevision 1へ入れる固定形式と端の場合を閉じ切れていない点である。新しい汎用機構を追加せず、上の契約を明記してvectorへ固定するのがよい。

## 13. 全体評価

- core: ほぼ問題ない。3点の局所修正後にfreeze可能な水準。
- interfaceの構造: 小さく分割され、独自拡張にも適する。
- 単純な標準interface: 概ね問題ない。
- captureと共通stream: まだfreezeしない。既存の形を増やすのではなく、必須値、ページング、generationを明記して閉じる。

したがって、OEPの基礎設計を再検討する必要はないが、OEP v1全体を「この仕様だけで全機能を互換実装できる」と宣言する前に、§12の修正とそのbyte vectorが必要である。
