# Open Embedded Probe — 明示correlationと暗黙対応の比較

状態: **検討中の論理protocol方針**。この文書は、request/resultを直列に一件ずつ扱うprofileでcorrelation fieldを省略できるかを、HID、UARTおよび順序付きstreamのfailure境界から比較する。

correlationのbit幅、field位置、数値割当および最終encodingは決定しない。

## 暗黙対応とは

暗黙対応では、resultにcorrelationを載せず、「このconnection contextと方向で現在待っている一件」へresultを対応付ける。

正常時に次だけが起こるなら対応は一意に見える。

```text
request A -> result A -> request B -> result B
```

しかし、一件制限は同時に保持するrequest数だけを制限する。古いresultが後から観測されないことまでは保証しない。

```text
request A -> timeout -> request B -> delayed/cached result A
```

correlationがなければ、最後のresultをBへ適用してよいかmessage自身から判定できない。

## 省略に必要な条件

暗黙対応を安全にするには、少なくとも同じrequest方向について次をすべて保証する必要がある。

1. 未解決requestは最大一件であり、pipeliningしない
2. request以外を原因とするresultを送らない
3. bindingはlogical resultを順序通り一回だけdeliveryする
4. response cacheまたは再送中の古いresultを、次のexchangeへ持ち越さない
5. request送信後に結果が不明となった場合、同じcontextで次のrequestへ進まない
6. timeout、取消しまたは途中切断後は、古いresultが到着不能な新しいconnection contextを確立するか、交換終了を双方で確認する
7. 双方向requestを許す場合、各方向の暗黙slotを混同しない
8. bindingまたはprofileがこれらの保証を実装可能性ではなくprotocol上の不変条件として定義する

これらが成立する場合、exchangeの順番自体が暗黙のcorrelationになる。単に実装が現在一件しか処理しないことや、transportが通常は順序を保つことだけでは省略条件を満たさない。

## Connection bindingごとの境界

### HID feature report

検討中のHID方式は、requestのSET_REPORTとresponse取得のGET_REPORTが別control transferである。GET_REPORTが中断または再試行される可能性があり、probeはresponseを次の有効requestまたはresetまでcacheする候補になっている。

未取得responseがある状態で次のSET_REPORTがbusyとして受理されなかった場合、その後のGET_REPORTは前のresponseを返す。明示correlationがあればhostは前のrequestのresponseとして識別できるが、暗黙対応では新しいrequestのresponseと誤認し得る。

HIDで省略するには、SETとGETを一つの失敗不能なexchangeとしてbindingが見せる、次のrequest受理と古いcache破棄を原子的に対応付ける、または同等の識別情報をHID側へ持たせる必要がある。最後の方式はcorrelationを別層へ移しただけである。

### UART stop-and-wait

UART binding候補はtransport sequenceにより同じDATA frameの再送を重複deliveryしない。正常な一つのconnection epoch内でこの保証が維持される限り、binding retryだけを理由に古いresultがOEP coreへ二度届くことはない。

ただしtransport sequenceはframe deliveryを扱い、どの機能requestへのresultかは扱わない。OEP response timeout後にhostが新しいrequestへ進む場合、epoch同期または明示的なexchange終了なしでは、遅延resultを新しいrequestから区別できない。transport sequenceをrequest correlationとして解釈しない。

### TCP等の順序付きstream

同じTCP connection上のbyteは順序と重複抑止を得られるが、application requestのtimeoutによって古いresponseが消えるわけではない。timeout後も同じconnectionで次のrequestを送れば、遅れて到着した前のresultを区別する必要がある。

暗黙対応を使用するなら、結果不明になったconnectionを破棄し、古いdataが新しいconnection contextへ入らないことを保証する必要がある。

## 明示correlationで得られること

明示correlationは次を可能にする。

- cachedまたは遅延resultが現在のpending requestと一致しないことを検出する
- 複数requestを同時に扱う実装へ同じmessage modelを拡張する
- bindingが異なっても同じlogical request/resultを維持する
- duplicate resultを別requestのresultとして扱わない
- trace上でrequestとresultを対応付ける

一方、明示correlationだけで次は保証しない。

- requestが一度だけ実行されること
- timeout後のrequest再送が安全であること
- correlation再利用後の任意に古いresultを永久に検出できること
- result payload自体が同一であること
- connectionを越えたactivity recovery

correlationはrequest/resultの誤対応を防ぐ識別情報であり、exactly-onceやidempotencyの代替ではない。

## 費用

仮に16 bit correlationをrequestとresultへ明示すると、一往復あたり合計4 byteを使用する。16 byte HID reportでは各messageのpayload領域を2 byte減らす。

ただしrequesterは暗黙対応でもtarget、operationおよびresult受取先を一件分保持する必要がある。明示方式で追加される状態はcorrelation値と照合処理であり、responder側は受信値をresultへ返すだけなら複数pending tableを必要としない。

幅を1 byte、2 byte、可変長または別の表現にするかは、再利用境界、最大同時request数およびbootstrap sizeと合わせて別途比較する。

## 現時点の方向

**初期の共通logical protocolでは、直列の最小profileを含め、識別できたrequestとそのresultに明示correlationを持たせる。**

主な理由は次のとおり。

- 重要候補であるHIDの分離したSET/GETとretryable response cacheで実際に古いresponseを観測し得る
- timeout後の安全条件を全bindingで同じように満たすより、小さいcorrelationを共通に保つ方がtransport独立性を維持しやすい
- responderだけの最小probeへ複数pending stateを要求しない
- 将来の複数request対応で別のmessage encodingへ切り替えずに済む

将来、上記の省略条件をすべて保証するbinding/profileが必要になった場合、暗黙correlationをcompact encodingとして別途定義する余地は残す。そのprofileは、通常encodingのfieldを単に送らない実装依存の最適化ではなく、exchange失敗時のconnection破棄を含む観測可能な規則を定義しなければならない。

## この文書で決めないこと

- correlationのbit幅とwire位置
- correlationの初期値、増分、乱数性および予約値
- wraparoundとretention期間
- request deduplication keyをcorrelationと同一にするか
- timeout後の照会または回復操作
- 暗黙correlation profileを将来実際に定義するか

次段階では、明示correlationの候補幅と再利用windowを、HID cache、UART epochおよび最大同時request数に対して比較する。

