# Open Embedded Probe — Request correlationのscopeとlifecycle

状態: **検討中の論理protocol案**。この文書は、requestと最初のresultを対応付け、resultに対象情報を重複して載せなくても誤配送しないためのrequest correlationを整理する。

wire表現、bit幅、予約値および再送方式は決定しない。[明示correlationと暗黙対応の比較](implicit-correlation-comparison.ja.md)により、初期の共通logical protocolでは直列profileにも明示correlationを持たせる方向とした。

## 解決する問題

requestを送信した側は、受信したresultを次へ誤って適用してはならない。

- 別の未解決request
- 同じoffered functionに対する別operation
- timeoutまたは再接続より前の古いrequest
- 別connection contextのrequest
- result後に作成されたactivity

resultがtarget referenceやoperationをすべてechoしても、それだけでは同じ対象への複数requestを区別できない。request correlationは、一つの論理requestとその最初のresultを対応付ける。

## 割当主体

requestを開始する側がcorrelationを割り当てる。hostからprobeへのrequestではhostが割り当て、将来probeからhostへのrequestを許可する場合はprobeがその方向のcorrelationを割り当てる。

応答側は、requestを安全に識別できる場合、resultへ同じcorrelationを返す。応答側が別の値へ置き換えたり、target referenceから独自に生成した値を返したりしない。

correlationの値そのものへfunction、operation、優先度または時刻の意味を持たせることは要求しない。

## Scope

correlationは少なくとも次を組み合わせたscopeで解釈する。

```text
OEP endpoint
  └─ connection context
       └─ request direction / requester
            └─ request correlation
```

- 同じrequesterが同じconnection context内で未解決の複数requestへ同じcorrelationを割り当てない
- 反対方向のrequestが同じ数値を使用しても、同じrequestとはみなさない
- 別endpointまたは別connection contextの同じ数値を関連付けない
- connectionを越えて古いcorrelationを利用する場合は、connection-local correlationとは別の再開または重複防止modelを必要とする

一つのconnection bindingが複数のlogical endpointまたはsessionをmultiplexする場合、どのcontextがcorrelation scopeを分離するかをbindingまたは上位protocolが明確にする。

## Requesterが保持するpending記録

requesterは、未解決requestごとにcorrelationから少なくとも次を復元できる必要がある。

- requestを送ったconnection contextと方向
- target scopeとtarget reference
- 選択済みfunction definitionまたはresult payloadを解釈する情報
- operation
- resultを受け取る処理または待機主体

必要に応じてdeadline、再試行情報、requested configurationおよび診断contextも保持できる。

これらをすべてheap上の共通tableとして保持することは要求しない。同期的に一つだけrequestを行うhostはcall stackまたは一つの固定slotで保持できる。複数requestを同時に扱うhostはcorrelationから対応slotを検索できなければならない。

## Resultの照合

requesterは概念上次の順序でresultを扱う。

1. result roleとして安全に識別する
2. 受信したconnection contextとrequest方向を確定する
3. correlationに一致する未解決requestを探す
4. 見つかったrequest記録からtarget、definitionおよびoperationを復元する
5. そのrequestが期待するresultとしてresolutionとpayloadを解釈する
6. `rejected`、`completed`または`accepted`に従ってpending状態を終了または移行する

未知correlationのresultを、同じtarget、直前のrequestまたは現在一つだけ待っているrequestへ推測で適用しない。破棄、診断またはconnection failureのどれにするかは、重複・順序・criticalityの規則と合わせて後に決める。

## Resolution後の状態

| resolution | pending request | 後続状態 |
|---|---|---|
| rejected | 解決済みにする | activityを作らない |
| completed | 解決済みにする | 最終outcomeとresult dataをrequest記録へ適用する |
| accepted | 解決済みにする | result内のactivity referenceで新しいactivity記録を確立する |

`accepted`後のupdate、data、停止およびterminal outcomeをrequest correlationへ対応付け続けない。request記録からactivity記録へ必要なtarget、definitionおよびoperation contextを引き継ぎ、以後はactivity referenceを使用する。

同じcorrelationを持つ同一resultが下位retryまたはcacheにより再度観測された場合、それを別requestのresultにしない。同じ論理requestへ矛盾する複数resolutionが現れた場合は、後着を新しい事実として上書きしない。

## Timeoutと再利用

resultを受信しないtimeoutだけでは、requestがprobeで未受信、処理中、解決済み、またはactivity作成済みのどれかを確定できない。このためtimeoutを`rejected`へ変換しない。

correlationを再利用できる条件は、connection bindingが古いmessageを届け得る期間、response cache、request再送および回復方式に依存する。少なくとも、古いresultを新しいrequestへ適用し得る間は再利用しない。connection contextを完全に終了し、新しいcontextで古いmessageを受信しないことが保証される場合は、以前のconnection-local correlationを持ち越す必要はない。

具体的なgeneration、連番幅、retention期間およびexhaustion処理は未決である。

## Resultのtarget echo

resultの意味上の配送には、correlationに一致したpending request記録を使用する。このため、target scope、target reference、function definitionおよびoperationをresultへ必ずechoすることは要求しない。

target echoにはtrace、診断、破損検出またはstateless中継で利点があり得るため、追加情報として禁止しない。ただしecho値だけをpending記録の代わりに使用せず、correlationと矛盾する場合の処理を定義する必要がある。

target echoを省略してもrequesterはstatelessにならない。payloadの解釈とcallback配送に必要なcontextをpending記録へ保持する責任が明確になる。

## 直列の最小実装

同時に一つのrequestしか送らない実装は、pending tableの代わりに一つのslotを使用できる。その場合も、遅延またはcached resultを新しいrequestへ誤適用しない必要がある。

初期の共通logical protocolでは明示correlationを維持する。一件制限だけでは、遅延またはcached resultが次のrequestへ誤適用されないことを保証できない。

将来「現在の一件」を暗黙のcorrelationとするcompact profileを認める場合、connection bindingまたはprofileが一件だけの未解決request、順序、重複、response cacheの破棄、および結果不明時のconnection終了を保証しなければならない。最小実装であることだけを理由にcorrelationを省略しない。

## 現時点の方向

- requestを開始する側がcorrelationを割り当てる
- correlationはconnection contextとrequest方向の中で解釈する
- 同じscope内の未解決request間で値を重複させない
- 初期の直列profileでもcorrelationを明示する
- resultは同じcorrelationを返す
- requesterはcorrelationからtarget、definition、operationおよび受取先を復元する
- resultのtarget echoを意味上の必須情報にしない
- `accepted`後はactivity referenceへ対応付けを移す
- timeoutをrequestのresolutionとして扱わない
- correlationの再利用により古いresultを新しいrequestへ適用しない

## この文書で決めないこと

- correlationのwire幅、encodingおよび予約値
- 将来、明示fieldを省略するcompact profileを定義するか
- 最大同時request数
- resultのorderingおよびout-of-order許容
- duplicate resultの識別とacknowledgement
- request deduplication、idempotencyおよびexactly-once
- timeout後の照会、再送および回復操作
- target echoを任意の診断情報として標準化するか
- probeからhostへのrequestを初期protocolへ含めるか

## Matcher実験

[Message routing比較実装](../experiments/message-routing/README.ja.md)へ、一つまたは複数の固定pending slotを使うmatcherを追加した。16 bit correlation全65,536値でopen、resolve、retireを走査し、未知resultが別requestへ適用されないこと、同一envelopeのduplicateと矛盾するresolutionを分離できること、retire前の再利用を拒否すること、および`accepted`時にtarget contextとactivity referenceを対応付けて取得できることを確認した。

この結果から、resultにtargetをechoしなくてもpending記録から意味上の配送先を復元できる。ただしrequester側の状態を不要にはできず、重複payload全体の同一性、retire可能になる時点およびtimeout後の回復は引き続き未決である。

1 slotと4 slotのbare ELFを測定すると、slot自体はATmega328Pで9 byte、CH32V003で10 byteだった。4 slot化によるcode増加はATmega328Pで0 byte、CH32V003で2 byteであり、主な増加はslotごとのRAMだった。

これはrequester側の費用である。hostからのrequestに応答するだけの最小probeはpending matcherを持たず、受信したcorrelationをresultへ返せばよい。probeからhostへのrequestを提供する場合に、その方向のpending stateが必要になる。

次段階では、correlationの候補幅と再利用windowを比較する。
