# Open Embedded Probe — Bootstrap layout候補

状態: **比較検討用の仮wire layout**。この文書は、OEP endpoint確認と最小constraint取得を、8 byte単位のHID control transferと小さいUART bufferの双方で実行できるか比較する。

ここに示すfield名、値、byte order、bit幅、message typeおよびhex値は説明用であり、protocol割当ではない。標準version、magic、command番号および最大長を決定しない。

## Bootstrapで成立させること

最初のbootstrap exchangeでは、次だけを成立させる。

1. 通信相手がOEP endpointであることを確認する
2. 継続して解釈できる共通protocol revisionがあるか判断する
3. 次のmessageを送るために必要な最小constraintを取得する
4. requestとresponseを対応付ける
5. 非対応、非互換および通信failureを誤った成功にしない

製品名、board名、build情報、完全な機能一覧、個体identityおよびUSB profileはbootstrap responseへ必ず含めない。必要ならendpoint確認後に取得する。

## Bootstrapに必要な最小意味

### Endpoint確認request

概念上、次を伝える。

- OEP bootstrapとして解釈を求めていること
- 別protocolの偶然の応答と区別するために必要なprotocol identity markerまたはchallenge
- hostが理解できるbootstrapまたはcore protocolの範囲
- responseを対応付けるためのtokenまたはrequest reference

### Endpoint確認response

概念上、次を返す。

- OEPとして応答していること
- requestに対応するprotocol identityの確認情報
- requestとの対応
- 共通に利用するprotocol revision、または互換範囲がないこと
- 続いてconstraintを取得できること

### 最小constraint response

初期候補として次を返す。

- probeが受信できるOEP logical messageの上限
- probeが一度に処理できるrequest数
- host pollingが必要か、自発送信を行い得るか
- 追加constraintまたは提供情報を取得する方法

host側の受信上限もprobeへ伝える必要があるかは未決である。probeから大きなresponseまたはdataを送る前には必要になる可能性がある。

## 共通の検証sequence

```text
host                                      probe
  | --- endpoint confirmation request ---> |
  | <-- confirmation / incompatibility --- |
  |                                         |
  | ------- minimum limits request -------> |
  | <------ minimum limits response ------- |
  |                                         |
  | ------ unknown request for test ------> |
  | <----------- rejected ----------------- |
```

endpoint確認と最小constraint取得を一往復へ統合できるかも比較対象とする。分離する場合は、最初のresponseを小さく固定できる一方、round tripが一回増える。

## 候補A: 共通self-framing envelope

すべてのconnection bindingで同じOEP envelopeを使い、core側にもmagic、lengthおよびcorrelationを持たせる。

### 仮header

| offset | size | 仮の意味 |
|---:|---:|---|
| 0 | 2 | protocol marker |
| 2 | 1 | envelope revision |
| 3 | 1 | message role / flags |
| 4 | 2 | request correlation |
| 6 | 2 | payload length |

headerは8 byteである。endpoint確認requestへ仮に4 byteのversion情報を加えると12 byte、responseへ8 byteの選択結果と最小constraintを加えると16 byteになる。

### HIDへの配置例

EP0のdata packetを8 byteとした場合、12 byte requestは少なくとも2 packet、16 byte responseも少なくとも2 packetになる。HID report IDやbinding fragment情報が別途必要ならさらに増える可能性がある。

### UARTへの配置例

UART bindingがdelimiter、frame lengthおよびCRCを外側へ追加する場合、core envelopeのmarkerとlengthが一部重複する。

```text
[UART delimiter/length] [8-byte OEP header] [payload] [UART CRC]
```

### 長所

- captureしたmessage単体からOEP envelopeを識別しやすい
- bindingを越えて同じbyte列を再利用しやすい
- correlationとlengthを常に同じ場所で扱える
- messageを別transportへ転送または保存しやすい

### 課題

- HID、UARTその他のbindingがすでに持つlengthや境界と重複する
- 最小requestでも8 byteの固定overheadを持つ
- 小さいcontrol操作でpayloadよりheaderが大きくなり得る
- UARTで二重のframing責任が生じる

## 候補B: Binding-framed compact core

message境界、length、破損検出およびtransport sequenceをconnection bindingへ委ね、OEP core messageには意味上必要なroleとcorrelationだけを置く。

### 仮core header

| offset | size | 仮の意味 |
|---:|---:|---|
| 0 | 1 | message role / flags |
| 1 | 1 | operation |
| 2 | 2 | request correlation |

headerは4 byteである。endpoint確認requestへprotocol identityの確認情報とversion情報を加えると、仮に8〜12 byte程度になる。responseへidentity確認、選択結果および最小constraintを加えると、仮に12〜16 byte程度になる。

### HIDへの配置例

HID report IDまたはHID binding headerが、reportの種類、fragment位置および有効長を表す。

```text
[HID binding information] [4-byte core header] [core payload]
```

identity確認情報を小さく表現できれば、endpoint確認requestが一つの8 byte packetへ収まる可能性はある。ただし、別protocolとの誤認防止を削って8 byteへ合わせない。requestとresponseの双方が2 packet以上になる可能性がある。

### UARTへの配置例

UART frameがmessage境界、length、sequenceおよびCRCを持つ。

```text
[delimiter] [binding header] [4-byte core header] [payload] [CRC]
```

CDCまたはTCPで同じUART framingを使うか、lengthだけの軽いstream framingを別に使うかはbinding設計で選べる。

### 長所

- core messageの固定overheadを小さくできる
- HID report、UART frameおよびnetwork recordの既存境界を利用できる
- 破損検出やfragment sequenceをcoreから分離できる
- 小さいprobeが処理するheaderを減らせる

### 課題

- bindingごとに異なる外側の表現が必要になる
- core messageのbyte列だけではlengthやOEP identityを判断できない
- message capture、保存、tunnelおよび別bindingへの転送にbinding情報が必要になり得る
- binding間で共通にすべき保証を仕様として揃える必要がある

## 候補C: 固定8 byte bootstrap record

endpoint確認に限り、常に8 byteの固定recordを使用する。通常のOEP message modelは、bootstrap完了後に使用する。

### 仮request record

| offset | size | 仮の意味 |
|---:|---:|---|
| 0 | 2 | bootstrap marker |
| 2 | 1 | bootstrap revision |
| 3 | 1 | operation |
| 4 | 1 | correlation token |
| 5 | 1 | host minimum core revision |
| 6 | 1 | host maximum core revision |
| 7 | 1 | flags |

### 仮response record

| offset | size | 仮の意味 |
|---:|---:|---|
| 0 | 2 | bootstrap marker |
| 2 | 1 | bootstrap revision |
| 3 | 1 | result / response operation |
| 4 | 1 | correlation token |
| 5 | 1 | selected core revisionまたは非互換表示 |
| 6 | 1 | limit classまたはdetail selector |
| 7 | 1 | flags |

詳細なconstraintは、続く固定8 byte recordまたは通常messageで取得する。

### HIDへの配置例

一つのrecordがEP0の8 byte data packet一つに一致する。ただしHID report IDがdataに含まれるAPIでは、report IDを別に扱うか、実payloadを7 byteへ減らす必要がある。

### UARTへの配置例

8 byte recordをUART binding frameへ入れる。UART側にはdelimiter、破損検出および再同期が別途必要である。

### 長所

- 最初のrequestとresponseに大きなbufferを必要としない
- endpoint確認前から長さ解釈を複雑にしなくてよい
- HID low-speedの8 byte単位で検証しやすい
- bootstrap parserを非常に小さくできる可能性がある

### 課題

- bootstrapと通常messageで二つの形式を実装する必要がある
- versionやconstraintの表現幅を早期に固定しやすい
- detail取得のround tripが増える
- 8 byteへ合わせることがHID以外では不自然な制約になり得る
- 将来拡張のための余白が小さい

## 三候補の概算比較

次の値は仮fieldを用いた概算であり、最終wire sizeではない。

| 観点 | A: self-framing | B: binding-framed | C: 固定bootstrap |
|---|---:|---:|---:|
| core固定header | 8 byte | 4 byte | bootstrap全体8 byte |
| confirmation request | 約12 byte | 約8〜12 byte | 8 byte |
| confirmation response | 約16 byte | 約12〜16 byte | 8 byte + detail |
| HID EP0 8 byteでのrequest | 2 packet以上 | 1〜2 packet以上 | 1 packet。ただしreport IDに注意 |
| UART外側framing | 一部重複 | 必要 | 必要 |
| 通常messageとの形式統一 | 高い | 高い | 低い |
| binding間で同じbyte列 | 容易 | 外側は異なる | bootstrapだけ共通化可能 |
| 小さい実装 | 固定overheadが大きい | 比較的適する | bootstrapは最小にしやすい |

## Version表現の論点

表中では単純なminimum/maximumまたはselected revisionを仮定したが、version model自体は未決である。

少なくとも次を混同しない。

- bootstrap recordまたはenvelope自体を解釈するrevision
- OEP共通protocolの互換性
- 個別機能定義のrevision
- connection bindingまたはUSB profileのrevision

一つの8 bit version番号だけで、これらすべてを表さない。

## Correlationの論点

最小実装は一度に一requestだけ処理するため、request correlationを暗黙にできる可能性がある。一方、HIDのSETと後続GET、UARTでの再送、複数request対応および遅延responseを考えると、bootstrapにも小さいtokenがある方が誤対応を検出しやすい。

候補Cの1 byte tokenは説明用であり、wraparound、再接続、重複responseおよびsecurityを考慮した幅ではない。候補A/Bの2 byte correlationも採用値ではない。

## Constraint表現の論点

bootstrap前に必要なのは、次のmessageを安全に送れることだけである。すべてのtransport性能を最初のresponseへ詰め込まない。

初期の最小constraintを、たとえば次のように限定できる。

- 次のrequestとして受信可能な最大logical message長
- 同時request上限。省略時または最小profileでは1
- response取得にhost pollingが必要か
- 詳細情報を取得するoperationが利用可能か

baud rate、実効throughput、HID report構成、UART CRC方式等はconnection bindingから既知であるか、binding固有情報として後から取得する。

最大message長をexact byte数、指数、classまたは固定profileのどれで表すかは未決である。小さいfieldへ収めるためだけに曖昧な上限を返さない。

## UART外側frameの候補

候補BまたはCでは、UART向けに外側frameが必要になる。比較対象として次がある。

### Delimiter + escape + CRC

```text
[delimiter] [escaped header + payload + CRC] [delimiter]
```

任意payloadを運べ、次のdelimiterで再同期できる。escapeによってwire lengthがdata内容に依存する。

### COBS等のdelimiter encoding + CRC

```text
[zero delimiter] [encoded header + payload + CRC] [zero delimiter]
```

delimiterをpayloadから排除して再同期しやすくできる。encodingと一時bufferまたは逐次decodeが必要になる。

### Marker + length + CRC

```text
[marker] [length] [header + payload] [CRC]
```

overheadと処理は小さくできるが、length byteが破損した場合の再同期、payload内markerの誤認および最大廃棄量を検討する必要がある。

いずれも、CRCを通過したframeだけをOEP共通protocolへ渡す。CRC種別、sequence、acknowledgementおよび再送はまだ決めない。

## HID reportへの配置の論点

HID feature reportでは、OS API上のbufferへreport IDを含める実装がある。USB control transferの8 byte packetと、HID report全体の長さは同じ概念ではない。

したがって「8 byte bootstrap」を採用しても、一つのUSB packetまたは一つのhost API callへ必ず収まるとは限らない。実際の候補descriptorとWindows、Linux、macOSおよびWebHID APIで次を確認する。

- report IDを含むhost bufferの長さ
- report descriptorで宣言した長さと実転送長の関係
- SET_REPORTとGET_REPORTで利用できる長さ
- short transfer、NAK、STALLおよびtimeoutの観測
- 複数report IDを使う場合のhost API差

## 現時点の比較結果

現時点では、**候補Bを通常messageの基準候補とし、候補Cをbootstrap専用に追加する価値があるかを実装sizeで比較する**のが妥当である。

理由は次のとおり。

- OEP共通protocolへ渡る時点でmessage境界が復元済みという責任分担と候補Bが一致する
- UARTのlengthとCRC、HIDのreport情報をcore headerで重複させずに済む
- 小さいrequestをHID reportへ収めやすい
- transport fragmentationとcore messageの意味を分離できる

ただし候補Bでは、bindingを越えて保存またはtunnelする際の自己記述性が低い。capture formatまたはtunnel bindingが必要なら、その用途の外側containerを別に定義できるか検討する。

候補Cはbootstrap parserを小さくできる可能性がある一方、二形式を持つflash costが増える可能性もある。CH32V003とUno R3級で実際にcode sizeを比較するまで、8 byteへ合わせる利点を確定しない。

## 次の検証

次は候補Bと候補Cについて、説明用ではない仮field定義を一つずつ作り、次を計測する。

1. confirmation request/responseの正確なbyte数
2. HID feature reportとEP0 packetへの分割数
3. UART frameへ入れた場合の最大wire length
4. incremental parserが必要とする最小RAM
5. 不正length、CRC failure、途中切断および重複frameの処理
6. unknown operationをrejectedとして返すために必要な情報

具体的な仮fieldとbyte数の比較は、[Bootstrap具体layout実験案](bootstrap-concrete-layout-experiment.ja.md)に示す。この検証結果を得るまで、候補BまたはCをprotocol仕様として採用しない。

## この文書で決めないこと

- 候補A、BまたはCの採用
- magic、operation、role、flagおよびversionの値
- byte orderと整数encoding
- 共通headerとpayload schema
- UART framingとCRC方式
- HID report descriptorとreport ID
- correlationの幅と省略条件
- 最大message長と最小保証値
- endpoint確認とconstraint取得を一往復に統合するか
