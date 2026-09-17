# Open Embedded Probe — Message header構成比較

状態: **非規定の比較案**。この文書は、request/result、activity、notificationおよびdataを配送する情報を、すべてのmessageに共通する固定headerへ置く方式と、message roleごとに必要なheaderを持つ方式で比較する。

wire field、数値、幅、byte order、alignmentおよびroleの個数は決定しない。以下のbyte数は差を観察するための仮定であり、protocol上の上限または採用layoutではない。

## 比較する問題

各message roleが必要とする対応付けは同じではない。

- requestは対象とrequest correlationを必要とする
- resultはrequest correlationを必要とし、対象は未解決requestの記録から導出できる
- activity updateとterminal outcomeはactivity referenceを必要とする
- notificationは通知対象を必要とするがrequest correlationを持たない
- dataはactivity、flowまたはpathのreferenceを必要とする

すべてに最大集合を載せればparserの入口を揃えられるが、使わないfieldの値、検証方法および将来の意味まで定義する必要が生じる。role別にすればmessageは小さくなるが、長さとfield位置がroleによって変わる。

## 候補A: 最大集合を持つ固定header

すべてのmessageへ概念上次を置く。

```text
role | detail | target scope | correlation | target/activity/flow reference
```

### 長所

- header長とfield位置を固定できる
- 共通のtrace表示や初期decodeを単純にしやすい
- 将来同じmessageで複数の対応付けを使う場合にfieldを追加せずに済む可能性がある

### 課題

- resultではtarget reference、activity messageではcorrelation等、意味上不要なfieldを運ぶ
- 未使用fieldをzeroにするか、echoするか、無視するかの規則が必要になる
- 未使用fieldへ非zero値が来た場合にmessage全体を拒否するかという互換性問題が増える
- 小さいHID reportやUART frameで機能固有payloadの領域を減らす
- 固定headerであっても、`detail`とreferenceのnamespaceはrole確定後にしか解釈できない

## 候補B: Role別header

最初にroleを識別し、その後はroleが必要とするrouting情報だけを置く。

```text
request          | operation / target / request correlation
result           | resolution / request correlation
activity update  | update kind / activity reference
activity outcome | outcome kind / activity reference
notification     | notification kind / target scope / target reference
data             | data kind / activity, flow, or path reference
```

### 長所

- 不要なreferenceまたはcorrelationを送らない
- fieldの意味と検証規則を、そのfieldを使うroleへ限定できる
- activity、notificationまたはdataを実装しない小さなprobeは、そのparserとruntime stateを持たなくてよい
- 短い固定reportでもpayloadへ残る領域を増やせる

### 課題

- roleごとに最小長とfield位置を検証する必要がある
- roleを検証する前に後続fieldを読めない
- 共通のtrace toolはroleごとのdecode情報を必要とする
- 新しいroleを追加した場合、古い実装はそのheaderを解釈せず安全に分離する必要がある

## 仮幅による比較

差を確認するためだけに、role、detailおよびscope kindを各1 byte、correlationと各referenceを各2 byteと仮定する。

候補Aの最大集合は7 byteになる。候補Bでは、offered functionを対象とするrequestは6 byte、result、activity update/outcomeおよび単一scopeのdataは4 byte、複数scopeを対象にできるnotificationは5 byteになる。

| 論理message | 候補A | 候補B | 候補Bで省く情報 |
|---|---:|---:|---|
| offered function request | 7 | 6 | target scopeをroleから導出 |
| result | 7 | 4 | target scope/referenceをrequest記録から導出 |
| activity update/outcome | 7 | 4 | correlationとscopeをroleから除外 |
| notification | 7 | 5 | correlationを除外 |
| activityに属するdata | 7 | 4 | correlationとscopeをroleから除外 |

16 byteのHID reportへ一つのlogical messageを置く仮定では、header後に残る領域は候補Aの9 byteに対し、候補Bでは10から12 byteになる。この差はHID専用の意味を導入する根拠ではないが、小さいconnection bindingで不要fieldを常時運ぶ費用を示す。

この表は、すべてのrequestがoffered functionを対象にする、すべてのdataがactivityだけに属する、または各fieldをこの幅で採用するという決定ではない。target scopeをroleから一意に導出できないmessageは、scope kindまたはrole subtypeを追加する必要がある。

## 共通に保つもの

Role別headerを選んでも、各roleを無関係な独自形式にはしない。共通protocolは少なくとも次を揃える。

- 完全なlogical messageをconnection bindingから受け取った後に解釈する
- roleを確定してからrole固有headerとpayloadを解釈する
- roleごとの必須routing情報と最小長を定義する
- referenceをconnection contextと定義されたscope内だけで解決する
- request/result correlationとactivity/flow referenceを混同しない
- 未知roleを既知roleとしてfallback decodeしない
- requestへのresultは、別経路を明示的に確立していない限り同じconnection contextへ返す

共通性は全roleのbyte位置を同じにすることではなく、role、scope、対応付けおよび未知情報の扱いを同じ規則で判断できることに置く。

## 現時点の方向

**Roleを共通に識別し、その後のrouting headerはroleごとに必要な情報だけを持つ方式を優先候補とする。**

最大集合の固定headerは、不要fieldのwire費用だけでなく、その値と検証規則も全実装へ要求する。role別headerなら、request/resultだけの最小probeにactivity、notificationおよびdata用fieldや状態を要求せず、必要な実装だけを追加できる。これは共通message modelで選んだ段階的実装の方向と一致する。

ただし、これは可変長encodingや具体的field配置の採用ではない。

## Decoder実験

[Message routing比較実装](../experiments/message-routing/README.ja.md)へ、上記の仮幅で6 roleすべてを正規化した同じviewへdecodeする固定header版とrole別header版を追加した。role全256値と長さ0から7 byteを走査し、既知roleが各最小長へ達した場合だけ成功すること、失敗時に出力viewを変更しないこと、および入力境界外を書き換えないことを確認した。

全roleを含むbare ELFでは、role別版のcodeは固定版よりATmega328Pで90 byte、CH32V003で46 byte大きかった。一方、wire headerはmessageごとに1から3 byte短く、測定用入力bufferも1から2 byte小さい。どちらも永続的なparser stateを持たない。

したがってrole別方式はcode sizeが常に小さいから選ぶのではなく、小さいtransferで不要fieldとその検証規則を常時負担しないための候補である。request/resultだけのprobeは未使用roleのdecoderを省けるため、全role parserの差をすべての最小probeへ課す必要はない。

## 次の確認

- [Request correlationのscopeとlifecycle](request-correlation-lifecycle.ja.md)で整理したpending記録を最小slotと複数slotで実験する
- notificationとdataでtarget scopeをroleから導出できる範囲を確認する
- 未知roleおよび未知role subtypeのcriticalityをheader自身から判断可能にする必要があるか検討する
