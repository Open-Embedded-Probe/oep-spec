# Open Embedded Probe — Requestの受理と完了

状態: **検討中の論理protocol案**。この文書は、[共通message model候補](message-model-candidates.ja.md)の候補Cを仮の比較基準として、requestに対する受理、拒否、即時完了および継続処理の意味を整理する。候補Cの採用、wire上のmessage type、encodingおよびfield構成はまだ決定しない。

## 解決したい問題

hostがrequestを送った後、次の状態を区別できなければならない。

- probeがrequestを拒否し、要求された機能操作を開始していない
- probeが処理を行い、その場で完了した
- probeがrequestを受理したが、処理はまだ継続している
- 通信喪失等により、probeがrequestを受信または実行したか判断できない

「応答を受け取った」「requestが受理された」「処理が成功した」は、それぞれ異なる事実である。

## 基本となる三つのresolution

probeは、解釈できた一つのrequestに対して、論理上次のいずれか一つを示す。

| resolution | 意味 | 後続activity |
|---|---|---|
| rejected | 要求された機能操作を開始しなかった | 作成しない |
| completed | 処理が終了し、最終outcomeが確定した | 必要としない |
| accepted | requestを受理し、処理が応答後も継続する | 対応するactivityを示す |

これらを三つのwire message typeにすることは要求しない。一つのresponse形式の異なる結果として表すこともできる。

## Resolutionと付随情報

resolutionはresponseの内容全体ではなく、requestのlifecycleがどの状態へ進んだかを示す区分である。probeはresolutionだけを返すのではなく、その意味を判断し、機能を利用するために必要な情報を共に示す。

responseには、概念上次の情報が含まれ得る。

- どのrequest、offered function、operationまたはconfigurationに対する応答か
- `rejected`、`completed`または`accepted`のresolution
- resolutionに応じた理由、outcome、result dataまたはactivity reference
- 実際に採用されたeffective configuration
- constraint、resource、状態または利用可能性に関する補助情報
- 診断、再取得または回復に利用できる追加情報

resolutionごとの主な内容は次のように整理する。

| resolution | 必要になる主な情報 |
|---|---|
| rejected | 拒否の区分または理由。必要に応じて受理可能な条件や現在状態 |
| completed | 最終outcomeと、機能が定義するresult data。必要に応じてpartial result、failure detail、effective configurationまたは新しい状態 |
| accepted | 後続interactionを対応付けるactivity reference。必要に応じて受理された条件、初期状態または確保済みresource |

すべてのresponseへ同じ補助情報を要求しない。どの情報が必須かは、共通protocol、個別機能およびbindingのそれぞれの定義によって決まる。

### Resolutionとoutcomeの違い

**resolution**はrequestを拒否したか、完了したか、activityへ移行したかを示す。**outcome**は、実行した機能操作がどのような結果で終了したかを示す。

- `rejected`では機能操作を開始していないため、その操作のoutcomeは存在しない。代わりに拒否理由を示す
- `completed`では最終outcomeを同じresponseで示す
- `accepted`では最終outcomeはまだ存在せず、後でactivityのterminal outcomeとして示す

成功、failure、partial result等のoutcome区分と、その詳細なresult dataは別の情報になり得る。具体的なoutcome分類と共通failure表現は未決である。

## Rejected

`rejected`は、probeが要求された機能操作を開始せず、requestによるactivity、configuration変更または機能固有の副作用を発生させなかったことを示す。

requestの受信、decode、parameter検証、constraintとの照合およびresourceの利用可否確認は、拒否を判断するための処理であり、ここでいう機能操作の開始には含めない。要求された機能操作を開始した後に失敗した場合は`rejected`ではない。応答時点ですでに終了していればfailureを伴う`completed`、継続activityとして受理済みならそのactivityのterminal failureとして示す。

拒否理由には、たとえば次があり得る。

- request、機能または操作を理解できない
- parameterまたはconfigurationが受理可能な範囲にない
- 必要なresourceを確保できない
- 現在の状態では操作を開始できない
- 必要な権限または前提条件を満たさない

診断情報の記録、失敗回数の更新等、requestの受理判定自体に付随する内部変化まで存在しないことは要求しない。ただし、hostから見た要求対象の機能操作を開始済みである場合は`rejected`として扱わない。

configuration requestを拒否した場合、requested configurationをeffective configurationとして採用しない。代替条件を示す場合も、それは提案であり、hostの明示的な合意前に採用しない。

## Completed

`completed`は、requestに対応する処理が応答時点で終了し、最終outcomeが確定していることを示す。

最終outcomeは成功だけとは限らない。

- 全部成功した
- 定義されたpartial resultを伴って終了した
- 処理を開始したが、機能固有または実装上のfailureで完了できなかった

`completed`でfailureを返す場合、`rejected`とは異なり、処理を試みたことによる部分的な結果または副作用が残る可能性がある。副作用の有無と有効性は、機能定義またはoutcomeで判断できなければならない。

endpoint確認、提供情報取得、単純なconfigurationおよび短時間の有限操作は、`completed`だけで完了できる。

requestが`completed`になることは、その効果が消滅したことを意味しない。configurationの採用、出力状態の変更またはresourceの保持がrequest完了後も継続する場合、その継続状態と解除方法は機能定義および情報modelに従って別に扱う。

## Accepted

`accepted`は、requestが有効として受理されたが、最終outcomeはまだ確定していないことを示す。

`accepted`を返す場合、probeは後続のupdate、data、停止および最終outcomeを対応付けるためのactivityを論理上作成する。hostは、`accepted`を処理成功または完了として扱わない。

```text
host                         probe
  | -------- request --------> |
  | <------- accepted -------- |
  |                             |  processing
  | <--- update / data -------- |  必要な場合
  | <--- terminal outcome ----- |
```

処理が非常に早く終了する場合でも、probeは次のどちらかを一貫して示す。

- activityを作らず、最終outcomeを`completed`として返す
- activityを作り、`accepted`とactivityのterminal outcomeを論理的に区別する

`accepted`を返しながら、activityを識別または追跡する方法を提供しない構成は認めない。

## Activityへ移行する時点

hostは、`accepted`を得た時点で、requestがactivityへ移行したことを確認できる。

probeは、少なくとも次が成立する前に`accepted`を示さない。

- requestを実行対象として受理した
- 後続interactionを対応付けるactivityを作成した
- 受理時に必要と定義されたresourceまたはconfigurationを確保した

受理後の実行成功までは保証しない。resource喪失、target側の状態、停止要求その他の理由により、activityはfailureで終了し得る。

resourceを受理時に確保するか、実行中に取得するかは機能によって異なり得る。後者の場合、`accepted`がresource確保済みを意味しないことを、機能またはconstraintが明確にする。

## Requestごとの一意なresolution

一つのrequestについて、probeは`rejected`、`completed`または`accepted`の複数を矛盾して成立させない。

- `rejected`の後に、そのrequestのactivityを開始しない
- `completed`の後に、そのrequestを未完了activityとして継続しない
- `accepted`の後は、request自体へ別の最終responseを返すのではなく、対応するactivityのoutcomeとして完了を示す

wire上の再送、重複messageまたはcacheされた応答をどう扱うかは別途定義する。ここで要求する一意性は、同じ論理requestへ矛盾した意味を与えないことである。

## 通信喪失とtimeout

hostがresolutionを受け取れなかった場合、requestは次のどの状態にもあり得る。

- probeへ届いていない
- probeへ届いたが、まだ評価されていない
- rejected、completedまたはacceptedになったが、その応答をhostが受け取っていない
- activityがすでに進行または完了している

したがって、timeoutまたは切断を`rejected`として扱わない。requestを同じ内容で再送して安全かどうかも、timeoutだけから判断しない。

下位通信またはconnection bindingが、一つの論理的な通信単位を届けるために内部で行う再送は、requestの再実行とは区別する。その再送が上位から一回のrequestとして観測される限り、この文書のresolutionを増やさない。hostがresolutionを得られないままrequest自体を再送する場合は、別途、重複実行の可能性を扱う必要がある。

`accepted`を受信した後に接続を失った場合も、activityが停止、継続または完了したかを無条件に仮定しない。再接続後のactivity照会、再開および重複防止を共通protocolで支援するかは未決である。

## 小さな実装

小さなprobeは、一度に一つのrequestだけを処理し、すべての対応操作を`rejected`または`completed`で返してよい。その場合、activity managementを実装する必要はない。

ただし、最終outcomeが未確定であり、応答後も処理結果、dataまたはfailureを同じ処理へ対応付ける必要がある操作を、完了済みであるように見せてはならない。そのような操作を提供する場合はactivity相当の区別が必要になる。requestの効果またはconfigurationが維持されるだけで、最終outcomeが確定している場合はactivityを必須としない。

## Interaction patternとの対応

| interaction | 主なresolution |
|---|---|
| OEP-INT-001 endpoint確認 | rejectedまたはcompleted |
| OEP-INT-002 提供情報取得 | rejectedまたはcompleted |
| OEP-INT-003 configuration評価 | rejectedまたはcompleted。評価または適用自体が非同期に継続する場合はacceptedも検討対象 |
| OEP-INT-004 有限操作 | rejected、completedまたはaccepted |
| OEP-INT-005 native data flow | 開始requestに対するrejectedまたはaccepted。短い転送はcompletedも可能 |
| OEP-INT-006 external binding | OEP側の各操作に適用。外部pathのopen結果とは別に扱う |
| OEP-INT-007 状態変化 | 再取得requestには適用。自発的notificationには適用しない |
| OEP-INT-008 停止・解放 | 停止requestの受理とactivityが実際に停止したことを区別する |
| OEP-INT-009 再確認 | 再確認の各requestに適用するが、以前のrequestのresolutionを推測しない |

## この文書で決めないこと

- requestおよびresponseのwire上の名称とtype
- request correlationの識別子と省略条件
- activity identityの割当主体、表現、scopeおよびlifetime
- activity updateとterminal outcomeの具体的形式
- activityを照会、停止または解放する共通操作
- responseとterminal outcomeのordering保証
- retry、deduplication、idempotencyおよびexactly-onceに関する規則
- batch requestと各要素のresolution
- probeからhostへ開始するrequest

次段階では、`accepted`で作成されるactivityのidentity、scopeおよびlifetimeを検討する。
