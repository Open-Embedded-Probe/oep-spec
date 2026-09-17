# Open Embedded Probe — Activityの参照とlifecycle

状態: **検討中の論理protocol案**。この文書は、[Requestの受理と完了](request-completion-semantics.ja.md)で`accepted`となった処理を、後続のupdate、data、停止要求およびterminal outcomeへ対応付けるためのactivity referenceとlifecycleを整理する。

wire上の識別子形式、bit幅、割当algorithm、message typeおよび再接続protocolはまだ決定しない。

## Activityを識別する目的

requestが`accepted`になった後は、最終outcomeが同じresponse内には存在しない。そのためhostとprobeは、後続のinteractionがどの継続処理に属するかを区別する必要がある。

activity referenceは、少なくとも次を対応付けるために使用する。

- activityを作成したrequestと`accepted` response
- activityの状態または進捗に関するupdate
- activityへ属するinput、outputまたはdata flow
- activityに対する停止、照会その他の操作
- terminal outcomeまたはfailure

activity referenceは、製品、物理device、OEP endpoint、function definition、offered functionまたはcommunication pathのidentityを置き換えるものではない。

## Activity referenceの基本案

### Probeが割り当てる

hostからのrequestを`accepted`とする場合、probeがactivity referenceを割り当て、`accepted` responseでhostへ示す。

probeはactivity referenceを割り当て、後続interactionへ対応付けられる状態にしてから`accepted`を示す。hostがrequestに付けたcorrelation情報を、そのままactivity referenceとして永続利用できるとは仮定しない。

将来probeからhostへ開始するrequestを認める場合、そのactivity referenceをどちらが割り当てるかは別途検討する。

### Global identityを要求しない

activity referenceは、その有効scope内でactivityを曖昧なく区別できればよい。UUID、device全体で永続する連番、再起動後も一意な値、またはproject共通registryへの登録を要求しない。

小さなprobeは、同時activity数とreferenceの再利用条件が許す範囲で、小さな局所値を使用できる。

### Reference単独で解釈しない

activity referenceは、それを発行したOEP endpointおよび有効なconnection contextと組み合わせて解釈する。別endpoint、別device、別connection contextまたはexternal bindingで同じ値が現れても、同じactivityであるとはみなさない。

## Scope

初期案では、activity referenceのscopeを次のように扱う。

```text
OEP endpoint
  └─ connection context
       └─ activity reference
            ├─ offered function
            ├─ communication path
            └─ activity lifecycle
```

- referenceは、一つのOEP endpointとの一つのconnection context内で有効とする
- 同じscope内で同時に区別する必要があるactivityへ、同じreferenceを割り当てない
- activityが属するoffered functionとcommunication pathは、作成時に確定または明示的に関連付ける
- hostはreferenceだけを別endpointまたは再接続後のcontextへ持ち越さない

ここでいうconnection contextは、物理linkそのものと同一とは限らない。物理的な一時切断を越えるlogical sessionを将来定義する可能性はあるが、初期案ではその存在を前提としない。

## 所有と可視範囲

activityは、原則としてactivityを作成したrequestのconnection contextから参照、停止および照会する。

別のhost connectionから同じactivityを参照または制御できることは仮定しない。複数hostによる共有、管理connectionからの列挙、所有権移譲または監視専用参照が必要な機能は、その可視範囲と競合規則を明示的に定義する。

activity referenceを知っていることだけを認可の根拠にしない。認証および認可を導入する場合は別のsecurity modelで扱う。

## Lifecycle

activityの論理状態を、少なくとも次の段階に分ける。

```text
allocated ── acceptedを確定 ── active ── terminal ── retired
                              │          │
                              └──────────┘
                            即座に終了する場合
```

### Allocated

probeがreferenceと必要な管理状態を用意したが、`accepted`を確定していない段階。

hostからはまだactivityの存在を確認できない。

### Active

probeがrequestを`accepted`として確定し、activityがterminal outcomeへ到達していない段階。

hostは`accepted` responseを受信した場合にactivityの存在とreferenceを確認できる。responseが失われた場合は、probe側でactivityがactiveであってもhost側ではrequestのresolutionが不明なままになり得る。activityを継続するか停止するか、および後から回復できるかは、重複防止、connection喪失および回復modelと関係する。

機能定義に従って、update、data、照会、inputおよび停止要求を扱える。すべてのactivityへ進捗通知、照会または停止対応を要求しない。

### Terminal

activityの最終outcomeが確定した段階。

terminal outcomeは、少なくとも次を区別できる必要がある。

- 正常に完了した
- failureで終了した
- partial resultを伴って終了した
- 停止要求、probe判断または接続条件によって途中終了した

一つのactivityへ矛盾する複数のterminal outcomeを成立させない。terminal後に新しい処理結果またはdataを生成しない。下位通信のorderingやbufferingにより、terminalより前に生成されたdataの観測順序が問題になる場合の規則は別途定義する。

### Retired

activityの実行状態と、hostへ必要なterminal情報を提供するための保持を終了し、referenceを将来再利用できる段階。

terminalへ到達した瞬間にreferenceを再利用可能とすることは要求しない。遅延message、再取得、重複requestまたはhostが未受信のoutcomeを古いactivityと誤認しないため、実装またはprotocolが定める期間は保持できる。

## Activityの終了とresource解放

activityがterminalになること、activity referenceがretiredになること、および関連resourceが解放されることは同じ事実とは限らない。

- activity専用resourceはterminal時に解放される場合がある
- terminal outcomeとして採用されたconfigurationや出力状態はactivity終了後も残り得る
- result dataをhostが取得するまでbufferを保持する場合がある
- external bindingや別activityがresourceの所有を引き継ぐ場合がある

機能またはbindingは、terminal時に何を解放し、何を維持するかを明確にする。hostはactivity終了だけを理由に、configuration解除または全resource解放を仮定しない。

## 停止要求との関係

hostがactivityの停止を要求した場合、そのrequest自体にも[受理と完了の区分](request-completion-semantics.ja.md)を適用する。

停止requestが受理または完了したことと、対象activityがterminalになったことを混同しない。

- 停止要求を拒否できるactivityがある
- 停止処理が非同期に進む場合がある
- 停止要求後も、境界までdataまたはpartial resultを生成する場合がある
- 停止不能な操作も許容する

対象activityが実際に終了したことは、そのactivityのterminal outcomeで確認する。

## Connection喪失との関係

connection contextを失ったことだけでは、probe内部のactivityが停止、継続または完了したかを判断できない。

機能または実装は、必要に応じて次のいずれかのpolicyを持ち得る。

- connection喪失時にactivityを停止する
- 安全な停止点まで進めて終了する
- connectionなしでも処理を継続する
- 外部resourceまたはexternal consumerの状態に従う

ただし初期案では、以前のactivity referenceを新しいconnection contextからそのまま利用できるとはみなさない。接続を越えた照会、再関連付けまたはresumeを提供する場合は、connection-localなreferenceとは別に、安全に同じactivityを特定する仕組みが必要になる。

## Referenceの再利用

probeは、古いactivityと新しいactivityをhostが誤認し得る間、同じscope内でreferenceを再利用しない。

再利用可能になる条件には、次が関係し得る。

- terminal outcomeの送信または取得状況
- connection bindingのordering、重複および遅延に関する保証
- requestやmessageの再送可能期間
- terminal recordを照会できる期間
- connection contextの終了

generation、単調増加番号、再利用待機期間その他の具体的方式は未決である。

## Data flowとの関係

継続的なOEP native data flowは、一つのactivityとして扱うことができる。その場合、dataはactivity referenceに対応付ける。

一つのactivityが複数方向または複数種類のdata flowを持つ場合、activity referenceだけで十分か、activity内のchannel、directionまたはdata kindをさらに区別する必要があるかは機能定義とdata modelで決める。

external binding上の通信は、OEP activityと関係付けられる場合があるが、external endpointや外部protocolのsessionをactivity referenceそのものとして扱わない。両者の対応とlifecycle調整はexternal bindingが定義する。

## 小さな実装

`accepted`を使用せず、すべての対応操作を`rejected`または`completed`で返すprobeは、activity referenceを実装しなくてよい。

同時に一つのactivityだけを提供するprobeでも、`accepted`後のupdate、停止およびterminal outcomeをrequestや別activityと誤認しないためのreferenceまたは同等のconnection-localな対応関係が必要になる。

## 現時点の方向

- activity referenceは`accepted`を返すprobeが割り当てる
- referenceはglobalまたは永続identityではない
- 基本scopeはOEP endpointとのconnection contextとする
- offered functionおよびcommunication pathとの関係を維持する
- activityのterminal、referenceのretireおよびresource解放を区別する
- connection喪失をactivity終了とみなさない
- 再接続後に以前のreferenceが有効とはみなさない
- 小さなprobeへactivity対応を必須にしない

## この文書で決めないこと

- activity referenceのwire形式、幅および予約値
- connection contextを明示的な識別子としてprotocolへ含めるか
- terminal outcomeの保持期間と取得確認
- activity状態の照会方法
- reference再利用とgenerationの具体的方式
- connectionを越える永続activityのidentityとresume
- parent/child activityまたは複数activityのgrouping
- activity内の複数data channelの表現
- 複数host間のactivity共有および所有権移譲

次段階では、activityとは独立してprobeからhostへ送られるnotificationを共通message modelへ含めるか、およびnotificationを実装しないprobeが再取得で適合できる範囲を検討する。
