# Open Embedded Probe — Bootstrap具体layout実験案

状態: **比較計算用の非割当layout**。この文書は、[Bootstrap layout候補](bootstrap-layout-candidates.ja.md)の候補Bと候補Cへ具体的な仮fieldを置き、HID feature reportとUART frameに載せた場合のbyte数と状態量を比較する。

すべての値は計算用であり、protocol registry、version、magic、byte order、CRCまたは正式なtest vectorではない。

## 検証するexchange

最初の比較では、次を一往復または最小の追加取得で成立させる。

- OEP protocol identityの確認
- requestとresponseのcorrelation
- core revisionの互換性確認
- probeが受信できるlogical message長
- 同時request上限
- host pollingの要否

製品情報、個体identity、機能一覧および詳細constraintは含めない。

## 候補Bの具体案: Compact core message

### 共通header

| offset | size | 仮field | この実験での意味 |
|---:|---:|---|---|
| 0 | 1 | kind | core requestまたはcore response |
| 1 | 1 | operation | endpoint confirmation |
| 2 | 2 | correlation | requestとresponseを対応付ける値 |

この実験では2 byte整数をlittle endianと仮定する。

`kind`と`operation`を一つのglobal command IDにはしない。これは共通protocol自身の小さいcontrol namespaceを仮定した比較であり、個別機能のoperationは各function definitionのscopeで識別する。

### Confirmation request

| offset | size | 仮field | 仮値 |
|---:|---:|---|---|
| 0 | 1 | kind | `0x01` core request |
| 1 | 1 | operation | `0x01` confirmation |
| 2 | 2 | correlation | `0x1234` |
| 4 | 4 | identity challenge | ASCII `OEP?` |
| 8 | 1 | minimum core revision | `0x01` |
| 9 | 1 | maximum core revision | `0x01` |

合計は10 byteである。

説明用byte列:

```text
01 01 34 12 4f 45 50 3f 01 01
```

### Compatible response

| offset | size | 仮field | 仮値 |
|---:|---:|---|---|
| 0 | 1 | kind | `0x81` core response |
| 1 | 1 | operation | `0x01` confirmation |
| 2 | 2 | correlation | `0x1234` |
| 4 | 4 | identity response | ASCII `OEP!` |
| 8 | 1 | status | `0x00` compatible |
| 9 | 1 | selected core revision | `0x01` |
| 10 | 2 | maximum received logical message | `0x0100`、仮に256 byte |
| 12 | 1 | maximum in-flight request | `0x01` |
| 13 | 1 | connection behavior flags | `0x01`、仮にhost polling型 |

合計は14 byteである。

説明用byte列:

```text
81 01 34 12 4f 45 50 21 00 01 00 01 01 01
```

### 非互換response

非互換時も同じ14 byte形状を保ち、`status`を非互換、`selected core revision`を未選択として返す案を比較対象にする。固定形状なら小さいparserを共有できるが、不要fieldが残る。

別案として、statusごとに短いresponseを許容できる。wire sizeは減るが、lengthごとのvalidation pathが増える。

### 仮fieldの制約

このlayoutは次を決定してしまうものではない。

- 4 byteのidentity確認で十分か
- requestとresponseで固定文字列を変えるか
- revisionを1 byteで表せるか
- logical message上限を16 bitに制限するか
- polling behaviorをbit flagで表すか
- correlationを2 byteで表せるか

特にidentity challengeは認証または真正性確認ではない。別protocolとの偶然の誤認を避けるためのprotocol identity確認にすぎない。

## 候補BをHID feature reportへ載せる

計算用HID bindingとして、一つのOEP control feature reportを次の固定16 byteで仮定する。

| size | 内容 |
|---:|---|
| 1 | HID report ID |
| 1 | core messageの有効長 |
| 14 | core messageまたはpadding |

confirmation requestは有効長10、responseは有効長14になる。

```text
request report:
[RID] [0a] [10-byte core request] [4-byte padding]

response report:
[RID] [0e] [14-byte core response]
```

USB low-speed EP0の最大data packetを8 byteとすると、それぞれの16 byte report dataは2 packetで運ばれる。SET_REPORTおよびGET_REPORTのsetup packetとstatus stageはこのdata packet数に含めない。

HID report全体はUSB stackがcontrol transferとして分割・再構成し、OEP共通protocolへは有効長で切り出した一つのcore messageを渡す。

### HID側の最小buffer候補

- 固定report全体を保持する場合、受信16 byteと送信16 byte
- request処理後に同じbufferを安全に再利用できる実装では、共有16 byteと小さい状態
- USB stack自身が別に必要とするendpoint stateとpacket buffer

実際に一つのbufferを共有できるかは、SET_REPORTのstatus stage、次のGET_REPORT、NAK処理および割込み実装に依存する。

既存rvswdio_programmerの264 byte buffer二本は、この16 byte案の必須条件ではない。一方、16 byteに縮めた場合に提供機能のrequestを運べるかは別途検証が必要である。

## 候補BをUART frameへ載せる

計算用UART bindingとして、COBS系delimiter encodingを仮定する。decode後のframeを次の形とする。

| size | 内容 |
|---:|---|
| 1 | transport sequence |
| 2 | core message length |
| N | core message |
| 2 | CRC |

CRCはsequence、lengthおよびcore messageを覆うものと仮定する。CRC方式と初期値は決めない。

decode前のwireでは、上記全体をCOBS等でencodeし、末尾へ1 byteのdelimiterを置く。

### Byte数

254 byte未満のframeで、encoding overheadを1 byte、delimiterを1 byteと仮定すると次になる。

| message | core | decode後frame | wire概算 |
|---|---:|---:|---:|
| confirmation request | 10 | 15 | 17 |
| compatible response | 14 | 19 | 21 |

一往復のwire dataは概算38 byteである。UART start/stop bit、inter-frame idleおよびacknowledgementは含めない。

### UART側の最小buffer候補

bootstrap responseをframe全体で保持する実装では最大19 byteが必要になる。incremental COBS decodeとCRC計算を行い、core messageだけを保持する場合は14 byteとdecoder stateで処理できる可能性がある。

lengthまたはCRCが不正なframeはOEP coreへ渡さない。次のdelimiterまで破棄し、再同期する。

後続の[UART frame layout比較](uart-frame-layout-comparison.ja.md)では、delimiterがframe境界を与えるため、上記2 byte lengthを省略するalternativeも実装した。その場合のwire概算はrequest 15 byte、response 19 byteで、一往復34 byte、各方向の5 byte ACKを含めて44 byteになる。上記38 byteはACKを含まないexplicit length案の比較値として残す。

## 候補Cの具体案: 固定8 byte bootstrap

### Request record

| offset | size | 仮field | 仮値 |
|---:|---:|---|---|
| 0 | 2 | bootstrap marker | ASCII `OE` |
| 2 | 1 | bootstrap revision | `0x01` |
| 3 | 1 | operation | `0x01` confirmation request |
| 4 | 1 | correlation token | `0x5a` |
| 5 | 1 | minimum core revision | `0x01` |
| 6 | 1 | maximum core revision | `0x01` |
| 7 | 1 | flags | `0x00` |

説明用byte列:

```text
4f 45 01 01 5a 01 01 00
```

### Response record

| offset | size | 仮field | 仮値 |
|---:|---:|---|---|
| 0 | 2 | bootstrap marker | ASCII `OE` |
| 2 | 1 | bootstrap revision | `0x01` |
| 3 | 1 | result | `0x81` compatible response |
| 4 | 1 | correlation token | `0x5a` |
| 5 | 1 | selected core revision | `0x01` |
| 6 | 1 | limit profile | `0x08`、意味は仮 |
| 7 | 1 | flags | `0x01`、host polling型 |

説明用byte列:

```text
4f 45 01 81 5a 01 08 01
```

この8 byteだけではexactなmaximum logical message長とmaximum in-flight requestを独立して返しにくい。`limit profile`を登録済みprofileとして使うか、追加recordで詳細を返す必要がある。

## 候補CをHIDへ載せる

report IDを使用しない8 byte feature reportであれば、一つのrecordをEP0 data packet一つで運べる可能性がある。

非zeroのreport IDを使用し、report IDがUSB上のreport data先頭へ入る構成では合計9 byteになり、8 byteと1 byteの2 packetになる。

複数のOEP用reportを識別する必要がある場合や、host APIがreport IDを要求する場合に、一packetという利点を維持できるとは限らない。

exact constraintを追加recordで取得する場合、最低でも次の二往復になる。

1. 8 byte confirmation request / response
2. 8 byte limits request / response

report IDなしならdata packetは合計4個、report IDありで各reportが9 byteになるなら合計8個になる。setup packetとstatus stageは含めない。

## 候補CをUARTへ載せる

候補Bと同じUART外側frameを用いる場合、8 byte recordに5 byteのbinding fieldを加えたdecode後frameは13 byte、COBS overheadとdelimiterを含むwire概算は15 byteになる。

confirmationとlimits取得を二往復で行う場合、4 frameで概算60 byteになる。`limit profile`だけで次の通信に十分なら一往復30 byteで済むが、profile registryと粗い上限表現が必要になる。

## 比較結果

| 観点 | 候補B compact core | 候補C fixed bootstrap |
|---|---:|---:|
| confirmation request | 10 byte | 8 byte |
| confirmation response | 14 byte | 8 byte |
| exact message上限 | responseへ直接格納 | 追加recordまたはprofile化 |
| correlation | 16 bit仮定 | 8 bit仮定 |
| HID report IDあり | request/response各16 byte固定案 | 各9 byte、詳細取得時は往復追加 |
| HID EP0 data packet | 一往復で4個 | 詳細込みで最大8個。profileだけなら4個 |
| UART wire概算 | 一往復38 byte | 詳細込み60 byte。profileだけなら30 byte |
| 最大bootstrap core buffer | 14 byte | 8 byte |
| parser形式 | 通常core messageと共有可能 | bootstrap専用parserが必要 |

候補Cが節約するcore bufferはこの例では6 byteである。一方、exact constraintを追加取得するとround trip、wire量および専用parserが増える。

8 byteへ収めること自体を目的にせず、CH32V003またはUno R3級で、候補Cの専用parserが候補Bとの共通parserより実際に小さくなるかをcode sizeで確認する必要がある。

## UARTの再送を入れる場合

CRCとdelimiterだけでは、破損frameを検出して再同期できるが、自動回復はしない。binding-level再送を加える場合は、transport sequenceを使用する。

### Detect-only

- CRC failureまたは途中timeoutでframeを破棄する
- OEP coreへrequestを渡さない
- hostはresponse timeoutまたはtransport failureを観測する
- requestがprobeへ完全に届いた後にresponseだけ失われた場合、操作実行有無は不明になる

実装は小さいが、UART errorを自動回復しない。

### Stop-and-wait再送

- 一度に一つのtransport frameだけを未確認状態にする
- receiverはsequenceを確認し、同じframeの再送を重複deliveryしない
- senderはacknowledgementを得られなければ同じsequenceを再送する
- acknowledgementはframe deliveryだけを表し、OEP操作の成功を表さない

request frameをOEP coreへ渡した後にacknowledgementが失われた場合、receiverは再送された同じsequenceをcoreへ再deliveryしてはならない。

responseを再取得できるようにするには、transport acknowledgementとOEP responseを分けるか、直前のresponseを再送可能な期間保持する必要がある。後者はresponse size分のbufferを追加で必要とする。

stop-and-waitは最小実装と相性がよいが、data flowのthroughputとlatencyには不利である。control messageとdata flowで同じ再送方式を必須にするかは未決である。

## 不正入力時の処理

### HID

- reportの有効長が宣言上限を超える場合はcoreへ渡さない
- 固定paddingに規則を設ける場合、不正paddingを無視するか拒否するかを定義する
- control transfer自体が完了しなければcomplete logical messageとして渡さない
- protocol identity、kind、operationまたはrevisionが不正な場合は、transport failureではなくOEP bootstrap rejectionになり得る

### UART

- COBS decode failure、length不整合またはCRC failureはbinding failureとしてcoreへ渡さない
- 正常frameだがprotocol identityが異なる場合はOEP endpointとして確認しない
- 正常なOEP frameだがunknown operationの場合は、correlationを保ったrejected responseを返す
- 宣言lengthが実装上限を超える場合、frame全体をbufferせず次のdelimiterまで安全に破棄できる必要がある

## この実験案からの暫定判断

この計算では、候補Cを追加する利点はまだ確認できない。

- HID feature reportはEP0 packetより大きくでき、USB stackが8 byte packetへの分割を処理する
- report IDを使うと8 byte recordも一packetへ収まらない場合がある
- exact constraint取得を追加すると候補Cのwire量が増える
- 候補Bでもbootstrap core bufferは14 byteであり、Uno R3級の64 byte UART bufferより小さい
- 通常messageと同じparserを利用できる可能性がある

したがって次の実装比較では、**候補Bを第一候補とし、候補Cはcode sizeが実際に小さくなる場合だけ残す**。

これは候補Bのfieldを採用した決定ではない。特に4 byte identity、16 bit correlation、16 bit message上限および16 byte HID reportはすべて仮値である。

## 仮parserの実測結果

[Bootstrap layout比較実装](../experiments/bootstrap-layout/README.ja.md)では、候補Bをreport IDと有効長を含む16 byte report、候補Cをreport IDを含む9 byte reportとして、同じbufferをrequestからresponseへ再利用するC parserを実装した。

候補Cにもexactな16 bit message上限と8 bit in-flight上限を返す二往復目の仮recordを置き、候補Bの一往復と情報量を揃えた。field割当は測定専用である。

ATmega328P、avr-gcc 7.3.0、`-Os`での測定用ELFは次になった。

| 仮候補 | Flash | static RAM | 共有report buffer |
|---|---:|---:|---:|
| B | 466 byte | 17 byte | 16 byte |
| C | 404 byte | 10 byte | 9 byte |

候補Bをbinding非依存core handlerとHID wrapperへ分離したため、HID測定ELFでは候補CがFlash 62 byte、共有bufferを7 byte削減した。一方、AVR上の候補B core handler単体は142 byte、候補C専用handlerは152 byteであり、UART等では候補Bの共通形式に追加wrapperを必要としない。またreport IDを含む9 byte reportをlow-speed EP0で運ぶ仮定では一reportが二data packetとなり、exact limitまで二往復を要する。

この結果は候補Cの独立形式を追加する実装上の根拠を強めない。ただし一つのAVR toolchainと仮fieldによる比較であり、候補Bの採用判断にはしない。CH32V003 toolchain、実際のUSB stackとの統合、busyおよびGET_REPORT pollingの状態量は未測定である。

同じC sourceをCH32V003 ABI（`rv32ec` / `ilp32e`）、xPack RISC-V GCC 14.3.0、`-Os`でも測定した。startupを含まないbare ELFでは、候補Bがtext 554 byte / RAM section 17 byte、候補Cがtext 548 byte / RAM section 13 byteだった。候補Bのcore handler単体は234 byte、HID wrapperは68 byte、候補C専用handlerは252 byteである。

また同じparser test sketchがCH32V003 Arduino core 1.4.0でcompileできることを確認対象に加えた。これはrv003usbとの統合動作を確認するものではない。

さらにrv003usb、HID descriptor、8 byte packet単位のSET_REPORT再構成、共有buffer、pending response lifecycleおよびGET_REPORT callbackまで含むCH32V003 firmwareをbuildした。

rv003usb `5cddcd5e1d46`では、EP0 OUTの最後のdata packetが1から3 byteの場合にuser data callbackが呼ばれない。report IDを含む9 byteの候補Cは8+1 byteとなるため、そのままでは最後の1 byteが仮parserへ届かなかった。候補CのUSB reportを12 byteへpaddingし8+4 byteとした成立版で比較した。

xPack RISC-V GCC 14.3.0、`-Os -flto`で、候補BはFlash 2,440 byte / RAM 112 byte、候補C成立版はFlash 2,432 byte / RAM 108 byteだった。候補Cの削減はFlash 8 byte / RAM 4 byteに留まり、exact limitまで二往復を要する。この差は専用bootstrap形式を追加する強い実装上の根拠にはならない。候補Bのcore parserはHID wrapperから独立しており、UART等でも共有できることをhost testで確認した。ただし実機での列挙とSET/GET_REPORT、USB STALLによるbusy通知およびresetはまだ検証していない。

UART結合試験では、候補Bの同じ10 byte core requestと14 byte responseをderived-length COBS系frameおよびstop-and-waitへ載せた。probeのrequest delivery callback内でresponseを生成し、response DATAがrequest ACKより先にqueueされる場合でも、hostはresponseを一度だけ受信し、双方のtransport ACKを完了した。これにより仮core parserがHID report形式へ依存せず、UART bindingからも利用できることを確認した。

## 次の検証

UARTの再送と重複抑止に関する第一候補は、[UART bindingの信頼性model候補](uart-reliability-model.ja.md)に整理する。UART外側frameの後続比較は[UART frame layout比較](uart-frame-layout-comparison.ja.md)に示す。候補Bについて、core messageと各bindingの責任をさらに分ける必要がある。

1. `kind`が表す最小message role
2. core operation namespaceと個別機能namespaceの分離
3. compatible、incompatible、malformedおよびunknown operationのresponse形状
4. HID feature reportでのbusyとhost polling
5. UART detect-onlyとstop-and-waitのどちらを最小適合とするか
6. 16 bit message上限を採用せずに、小さいbootstrapでexact constraintを表す方法

AVRとCH32V003 ABI向け仮parserの単体比較、およびrv003usbを含むbuild比較は実施した。次は実機上で列挙、SET/GET_REPORT、busy、連続requestおよびreset時の状態を確認する。

## この文書で決めないこと

- 候補BまたはCの採用
- 説明用byte列の割当
- little endianの採用
- identity markerまたはchallengeの長さ
- protocol revision model
- maximum message lengthの幅
- HID reportの長さとreport ID
- UART COBS、CRC、sequenceおよび再送方式
- 最小実装でのnotification、activityおよびdata flow
