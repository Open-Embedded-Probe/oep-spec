# Open Embedded Probe — Message routing model候補

状態: **検討中の論理protocol案**。この文書は、共通message modelの各roleを正しいscopeへ配送し、標準機能と独自機能のpayloadを取り違えないために、共通protocolが論理上識別する情報を整理する。

wire header、field順序、識別子幅、数値割当、encodingおよびすべての情報を毎messageへ明示するかは決定しない。connection contextや直前のexchangeから一意に導出できる情報を省略する可能性を残す。

## 解決する問題

共通dispatcherは、個別機能のpayloadを理解しなくても次を判断できなければならない。

- messageがrequest、result、activity update/outcome、notificationまたはdataのどれか
- protocol、endpoint、offered function、communication path、activityまたはdata flowのどのscopeに属するか
- 同じfunction definitionを持つ複数のoffered functionのどれが対象か
- resultがどのrequestへ対応するか
- update、outcomeまたはdataがどのactivityまたはflowへ属するか
- 未知の機能や対象が、既知の別機能として解釈されないこと

すべてのoperationを一つのglobal番号空間へ置くだけでは、function definitionとoffered function instanceを区別できず、独自機能のpayloadを安全に配送できない。

## 論理上必要なrouting情報

messageには、roleに応じて次の情報が明示または導出できる必要がある。

| 情報 | 目的 |
|---|---|
| connection context | referenceとcorrelationの有効範囲、およびresponse経路を限定する |
| message role | payloadをrequest、result、update、notificationまたはdataとして誤認しない |
| target scope kind | endpoint、offered function、path、activity等のreferenceを取り違えない |
| target reference | 現在のscope内で具体的な対象を選ぶ |
| request correlation | requestと最初のresultを対応付ける |
| activityまたはflow reference | 継続処理のupdate、outcomeおよびdataを対応付ける |
| definition固有のoperation / data kind | 選択済みの定義の中でpayloadの意味を決める |

これらを一つの固定headerへすべて置くことは要求しない。たとえばbootstrap requestは対象がprotocol coreと一意であり、resultの対象はrequest correlationから導出できる。一方、通常のfunction requestはoffered function referenceを省略できない場合がある。

## Definitionとinstanceを分ける

通常のfunction messageは、次の二段階で意味を決める。

1. **offered function reference**で、このendpointが提供する具体的なinstanceを選ぶ
2. そのoffered functionが参照する**function definition**に従って、operationとpayloadを解釈する

function definition referenceは標準機能と独自機能、異なるownerの独自機能、および非互換なrevisionを区別する。offered function referenceは同じdefinitionに基づく複数instanceを現在のconnection context内で区別する。

共通dispatcherが独自payloadの意味を理解する必要はない。対象instanceとdefinitionを誤認せず、対応する専用handlerへbyte列を渡せればよい。

## Roleごとの対応付け

| Role | 主な対象 | 対応付けに必要な情報 |
|---|---|---|
| request | protocol core、endpoint、offered function、pathまたはactivity | target scope/reference、request correlation、definition固有operation |
| result | 直前または未解決のrequest | request correlation。対象scopeはrequest記録から導出可能 |
| activity update | activeなactivity | activity reference、update kind |
| activity outcome | activeなactivity | activity reference、terminal outcome kind |
| notification | endpoint、offered function、pathその他の観測対象 | target scope/reference、notification kind。request correlationは持たない |
| data | activity、data flowまたはnative path | activity/flow/path reference、directionまたはdata kind |

`accepted` resultはrequest correlationへ対応し、新しく割り当てたactivity referenceをpayloadとして示す。その後のupdate、data、停止操作およびterminal outcomeはactivity referenceへ対応付け、元のrequest correlationをactivity identityとして使い続けることを前提にしない。

## 共通dispatcherの処理候補

受信側は概念上次の順序で処理する。

1. connection bindingから完全なlogical messageを受け取る
2. 共通protocolとして解釈できるroleとrouting情報を検証する
3. referenceを現在のconnection contextとtarget scope kindの中で解決する
4. offered functionの場合は、そのinstanceが示すfunction definitionと対応handlerを選ぶ
5. definition固有のoperationとpayloadをhandlerへ渡す
6. requestのresultは同じconnection contextへ返し、correlationを保持する

bindingはfunction definitionや独自payloadを解釈しない。個別機能handlerもUSB、UART等のresponse物理経路を直接選ばず、受信時のconnection contextを使用する。

## 未知または無効なrouting情報

| 状況 | 影響範囲と候補動作 |
|---|---|
| 未知message role | payloadとcorrelationの意味を安全に判断できないため、既知roleとして処理しない。診断またはrole自体のcriticality規則は未決 |
| 未知target scope kind | 別scopeのreferenceとして解釈しない。requestとして安全に識別できる場合はrejected候補 |
| 存在しないoffered function reference | そのrequestだけをrejectedとし、別functionを利用不能にしない |
| 未知function definition | 一般hostはそのoffered functionを利用しない。共有する別functionは利用を続ける |
| 既知definition内の未知operation | 対応するrequestをdefinitionまたは共通規則に従ってrejectedとする |
| 未知request correlationのresult | 別requestへ対応付けない。破棄、診断またはconnection failureのどれにするかは未決 |
| 未知activity/flow reference | 別activityへ対応付けない。対象messageのroleに応じて拒否、破棄またはflow failureとする |
| 未知の非critical追加情報 | 対象scopeの基本意味が変わらない場合だけ無視可能 |
| 未知のcritical追加情報 | 対象scopeを安全に利用せず、無関係なscopeへ影響を広げない |

「未知だから無視する」を全roleへ一律適用しない。requestは相手が待つresultを返せる可能性があるが、未知notificationへrequest resultを返すことは別のmessageとして誤認する原因になる。

## 小さな実装

最小probeはprotocol coreと少数のoffered functionに対するrequest/resultだけを実装してよい。

- activityを作らない場合、activity reference tableは不要
- notificationを送らない場合、notification送信queueは不要
- native data flowを提供しない場合、flow stateは不要
- 同時requestが一つでも、request/resultのcorrelationを検査して古いresponseを誤認しない
- 未実装roleを、実装済みrequest/resultとして解釈しない

高機能な実装は必要なroleのdispatcherとreference tableだけを追加できる。未使用roleのruntime stateをすべてのprobeへ要求しない。

## 不変条件候補

1. message roleを確定する前にrole固有payloadを解釈しない
2. referenceはtarget scope kindとconnection contextを伴って解釈する
3. function definition identityとoffered function instance referenceを混同しない
4. operation番号は選択済みdefinitionのscope内で解釈し、独自機能をglobal operation番号だけで識別しない
5. resultをcorrelationが一致しないrequestへ適用しない
6. activity、flowまたはpathのdataを別scopeへ配送しない
7. 未知機能または未知情報の影響を、無関係なoffered functionへ広げない
8. requestのresponseは、別経路を明示的に確立していない限り受信時と同じconnection contextへ返す

## Bootstrap実験との関係

候補Bのbootstrap parserでは、仮`kind`を検証した後にだけ、そのcore role固有の`operation`を解釈する。全256 role値と全256 operation値の走査により、未知roleをbody解釈前に分離し、既知request role内の未知operationへcorrelation付きrejectionを返せることを確認した。

通常messageでは、これにoffered function、activityまたはflowのtarget referenceが加わる。bootstrapの4 byte仮headerをすべての通常messageへそのまま採用できることは意味しない。

## 通常function requestの仮layout実験

[Message routing比較実装](../experiments/message-routing/README.ja.md)では、bootstrapのrole、operationおよびcorrelationへ16 bitのconnection-local offered function referenceを加えた6 byte headerを試作した。resultも同じ外形を使い、operation位置をresolutionまたはrejection、target位置を元のoffered function referenceとして返す。

二つのoffered functionへ同じoperation値を送り、一方は標準機能を模したhandler、もう一方は共通dispatcherが意味を知らない非公開機能handlerへ配送した。payloadの処理結果は異なるが、dispatcherはreferenceからhandlerを選ぶ以外にpayloadを解釈しない。

16 bitのoffered function reference全65,536値とcorrelation全65,536値をhost上で走査し、既知referenceだけが対応handlerへ入り、未知referenceは別instanceへ誤配送されずcorrelation付きrejectionになった。既知instance内の未知operationとpayload不正も別のrejectionにできた。

この結果は、function definition identityを毎requestへ載せず、提供情報から得たconnection-local offered function referenceで通常requestを配送できることを示す。6 byte header、16 bit reference、resultでtargetをechoする構成およびstatus値はまだ採用しない。

同じ処理をruntime function pointer tableとcompile-time固定の`switch`で比較した。後者はATmega328PでFlash 336 byte / static RAM 10 byte、CH32V003でtext 168 byte / static RAM 10 byteだった。runtime table版との差はATmega328PでFlash 414 byte / RAM 12 byte、CH32V003でtext + rodata 292 byteだった。このため、論理routingはhandler tableの保持方式を規定せず、固定機能の最小probeにruntime tableを要求しない。

## この文書で決めないこと

- role、scope kindおよびreferenceのwire field
- referenceとcorrelationの幅、割当、再利用および省略条件
- function definition referenceのnamespace、ownerおよびrevision表現
- offered function一覧とreferenceを取得する操作
- notificationの配送保証と再取得方法
- activity内の複数data channelまたはflow reference
- probeからhostへのrequest
- unknown roleへ共通errorを返せるenvelopeを設けるか
- criticalityのencoding
- batch messageと一つのmessage内の複数target

次段階では、このrequest/resultだけのroutingへactivity reference、notification targetおよびdata flow referenceを加える場合に、role固有headerと統一headerのどちらが小さい実装に適するか比較する。
