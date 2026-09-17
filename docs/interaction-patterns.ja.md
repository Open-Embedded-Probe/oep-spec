# Open Embedded Probe — 最小interaction pattern

状態: **検討中のprotocol設計入力**。この文書は、[共通protocolの情報model](information-model.ja.md)を使ってhostとprobeが行う最小限のinteraction patternを整理する。

patternは論理的なやり取りを示す。各patternを一つのmessage、commandまたはround tripとして実装することは要求しない。複数patternの統合、既知情報の省略、batch化およびconnection binding固有の最適化は将来の設計で決める。

`OEP-INT-*`の番号は議論と追跡のための仮番号であり、protocol上のcommand番号ではない。

## Patternの共通規則

### Scopeを明確にする

interactionの入力、結果、状態および失敗は、対象となるendpoint、offered function、communication path、configurationまたはactivityへ誤解なく対応付けられなければならない。

一つの対象について得た結果を、別の対象へ暗黙に適用しない。

### 完了の意味を明確にする

hostは、少なくとも次を誤認しないようにする。

- 要求がprobeへ届いたか不明
- probeが要求を拒否した
- probeが要求を受理したが、処理はまだ完了していない
- 処理が全部完了した
- 一部だけ完了した
- 結果の全部または一部を信頼できない

すべてのpatternが非同期処理を必要とするわけではない。即時に完了する実装も許容する。

### 同時進行を必須にしない

小さな実装は、一度に一つのinteractionまたはactivityだけを処理してよい。複数を同時に処理する実装は、それぞれの入力、data、結果および失敗を対応付けられなければならない。

最大同時数、直列化、queue、優先度等は実装上の制限になり得る。すべてのprobeへ複数同時処理を要求しない。

### Timeoutを結果とみなさない

host側のtimeoutは、probeが処理していないことや処理に失敗したことを証明しない。通信喪失後は、操作が未実行、実行中、完了済みのいずれであるか不明な場合がある。

再試行によって同じ操作が重複実行され得るため、操作ごとの再試行可能性または重複時の意味が必要になる可能性がある。共通のidempotency modelを設けるかは未決である。

### Unknownとcriticalityを守る

理解できない追加情報が無視可能である場合は、理解できる範囲のinteractionを継続できる。理解しなければ対象scopeを安全に利用できない情報がある場合は、そのscopeの利用を開始しない。

未知情報を理由に無関係なoffered functionまで無条件に利用不能にしない。

## OEP-INT-001: OEP endpointを確認する

### 目的

接続候補がOEP endpointであることと、共通protocolを解釈できる範囲を確認する。

### 前提

- hostが、connection bindingに従って通信を試行するために必要な接続先情報を得ている
- 候補がOEPであることはまだ確定していない

接続先情報は、connection bindingが定める発見機構だけでなく、利用者による指定、hostの設定、別の仕組みによる発見、または他のsoftwareからの受け渡しによって得てもよい。connection bindingに自動発見機構があることや、この時点で接続可能性が確認済みであることは前提としない。

同じ物理deviceに由来する接続候補が複数あっても、それぞれの到達可能性とOEP endpointであるかどうかは個別に判断する。一つの候補へ接続できないことや、一つの候補がOEPでないことを、他の候補にも無条件に一般化しない。

### 論理的なやり取り

1. hostがOEPとしての確認を試みる
2. probeがOEP protocol identityと互換性判断に必要な情報を示す
3. hostが継続可能な互換範囲を判断する

### 結果

- OEP endpointとして確認され、共通protocolを継続できる
- OEPではない
- OEPである可能性はあるが、共通protocolに互換性がない
- 通信失敗等により判断できない

「OEPではない」と「判断できない」を同一にしない。

### 不変条件

- USB VID:PID、product名、port名等だけで確認済みとしない
- 確認前に、併設されたCDC、Audio等をOEP機能へ推測で関連付けない
- 非互換な相手へ機能操作を送らない

## OEP-INT-002: 提供情報を取得する

### 目的

endpointが提供する機能、communication path、constraintおよび関係をhostが把握する。

### 論理的なやり取り

1. hostが提供情報を取得する
2. probeがoffered functionと、それらを理解するために必要な参照情報を示す
3. hostが理解するfunction definitionとの共通部分を選ぶ
4. 必要に応じて個別機能、pathまたはconstraintの詳細を取得する

### 結果

- hostが利用候補となるoffered functionとpathを得る
- 共通に理解する機能がない
- 情報の一部に未知要素があるが、理解できるscopeは利用候補になる
- criticalな未知情報、変更または通信失敗により、対象scopeを判断できない

### 一貫性

情報取得中にprobeの構成や利用可能性が変化し得る。hostは、複数回に分けて得た情報が同じ状態を表すと無条件に仮定しない。

snapshot、generation、再検証または変更通知のどれを用いるかは未決である。少なくとも、probeが保証しない一貫性をhostが推測しない。

## OEP-INT-003: Configurationを評価する

### 目的

probeが開示した選択肢と制限に基づいてhostがconfigurationを選び、probeが実際に受理して採用する条件を明確にする。

### 前提

- hostが対象のoffered function、communication pathおよびprobeが開示したconstraintを取得している
- 機能またはpathがconfigurationを必要とする

### 論理的なやり取り

1. hostが、開示されたconstraintに基づいてrequested configurationを選び、probeへ示す
2. probeが機能、path、resourceおよび現在状態に照らして評価する
3. probeが受理または拒否を示す
4. 代替条件の提案に対応する場合、probeは採用せずに候補として示し、hostがその条件を改めて要求または明示的に受諾する

### 結果

- requested configurationがそのままeffective configurationになる
- hostが明示的に合意した代替条件がeffective configurationになる
- 条件不成立、resource競合、現在利用不能等により拒否される
- 状態変化または通信失敗により結果を確定できない

### 不変条件

- probeは異なる条件を暗黙に採用して成功扱いしない
- probeが提案した代替条件を、hostの明示的な合意前にeffective configurationとしない
- 評価結果がどのrequested configurationに対するものかを誤認しない
- 評価後に状態が変化し得る場合、受理が将来の実行成功を無期限に保証するものとしない

configurationを持たない機能へこのpatternを要求しない。評価だけ行いresourceを確保しない場合と、受理によってresourceを確保する場合を同一視しない。

probeは、hostが利用候補を選ぶために必要な選択肢と制限を、表現可能な範囲で事前に開示する。resourceの現在状態や複雑な条件の組合せなど、具体的なrequested configurationを評価しなければ確定できない事項まで、静的な一覧として完全に列挙することは要求しない。

## OEP-INT-004: 有限操作を実行する

### 目的

開始と結果を対応付けられる有限の機能操作を実行する。

### 論理的なやり取り

1. hostがoffered function、必要な入力、および必要に応じてconfigurationを指定して操作を開始する
2. probeが操作を受理または拒否する
3. 受理した場合、probeが操作を実行する
4. probeが結果、partial resultまたはfailureを示す

### 実装の幅

操作は一往復で完了しても、開始後に別の結果通知を必要としてもよい。長時間処理を有限操作として扱うかactivityとして扱うかは、共通interaction modelで後に決める。

### 不変条件

- 結果を対象の操作へ対応付ける
- 拒否と実行失敗を区別する
- partial resultが完全な成功と誤認されないようにする
- timeout後の自動再試行で副作用を重複させないため、操作固有の意味を考慮する

## OEP-INT-005: OEP native data flowを利用する

### 目的

OEP native path上で、複数単位または継続的なdataを交換する。

### 論理的なやり取り

1. hostまたはprobeが、機能定義に従ってdata flowを開始する
2. 送信側がdataをOEP native pathで送る
3. 受信側がdataを対象のoffered functionとactivityへ対応付ける
4. 完了、停止または失敗を扱う

### 必要になり得る性質

- dataの方向
- 単位と境界
- 順序
- 欠落、重複または破損の扱い
- flow controlとbuffer上限
- 正常終了と途中終了
- partial dataの有効性

すべてのdata flowへ同じ保証を要求しない。機能定義、OEP共通protocolおよびconnection bindingのどこが各保証を担当するかを後で定義する。

### 小さな実装

data flowを実装しないprobeや、同時に一つだけ扱うprobeも許容する。対応していないdata flowを有限操作として見せかけて意味を変えない。

## OEP-INT-006: External bindingを利用する

### 目的

OEP機能と明示的に関連付けられた外部interfaceまたは外部protocolをexternal consumerが利用する。

```text
OEP host ── OEP ──> probe
   │                 │
   │  機能、routing、変換、bindingの関係を扱う
   │
external consumer ── external path ──> probe
          実dataを直接交換する
```

OEP hostとexternal consumerは同一programであっても、別applicationやOS driverであってもよい。

### 論理的なやり取り

1. OEP hostがoffered functionとexternal bindingの関係を取得する
2. hostが必要なconfigurationと責任分担を確認する
3. 必要に応じてOEP側でrouting、変換またはresourceを構成する
4. external consumerが対応するexternal endpointを解決する
5. external consumerがopenまたは通信を試みる
6. 成功した場合、external pathで実dataを交換する
7. bindingの規則に従って停止、closeおよびresource解放を行う

### Open前に分かることと分からないこと

OEP hostは、bindingの宣言、external endpoint reference、probe側の既知状態等を得られる。しかし、driver、権限、他processによる占有、切断等により、external consumerがopenできるかは実際に試すまで分からない場合がある。

openの成功または失敗をOEP hostへ報告する必要があるか、external consumerとOEP hostが別processの場合にどう連携するかはbindingが定義する。

### 設定責任

次のどの構成も許容する。

- OEP側だけが設定する
- 外部protocolまたは標準class側だけが設定する
- OEP側と外部側が異なる設定項目を担当する
- 同じ意味の設定を双方が観測または変更できる

最後の構成では、正となる値、変更順序、不一致検出および状態同期をbindingが定義する。標準classが定義済みの制御を理由なくOEPで重複定義しない。

### 結果

- external pathをopenして利用できる
- bindingは理解できるが、external endpointを特定できない
- endpointは特定できるが、openできない
- open後に切断または通信失敗が発生する
- probe側のresourceまたは構成により利用できない
- external consumerがbindingへ対応していない

これらのすべてをprobeが知るとは限らない。結果を観測した主体と範囲を区別する。

## OEP-INT-007: 状態または提供情報の変化を扱う

### 目的

接続中に変化した機能、constraint、availability observation、configuration、resource関係またはbinding状態をhostが扱う。

### 可能なpattern

- hostが必要な時点で再取得する
- probeが変更を通知する
- 操作結果が新しい状態を含む
- 利用開始時に再検証する

どのpatternを必須にするかは未決である。通知を実装しない小さなprobeも許容できるようにする一方、古い情報を無期限に正しいとみなさない。

### 不変条件

- observationの情報源と有効範囲を維持する
- external consumerだけが知る変化をprobeが知っていると仮定しない
- resource関係の変化によって成立しなくなった条件を、以前の受理だけで成功扱いしない

## OEP-INT-008: Activityを停止または解放する

### 目的

進行中の処理、data flow、configurationまたはresource保持を終了する。

### 終了理由

- 正常完了
- hostによる停止要求
- external consumerによるclose
- probeによる停止
- resource競合または再構成
- connectionまたはexternal pathの喪失
- 機能固有の失敗

### 不変条件

- 停止要求を受け付けたことと、activityが実際に停止したことを混同しない
- 解放後も継続するdataや副作用がある場合、その意味を機能またはbindingが定義する
- activityの停止、configurationの解除、およびresourceの解放を常に同一操作と仮定しない
- cancellationを支援しないactivityへ、停止可能であるように見せない

明示的な停止を持たず、完了または接続終了だけで終わる機能も許容する。

## OEP-INT-009: 接続喪失後に再確認する

### 目的

OEP connectionまたはexternal pathの喪失後、以前の情報や処理を安全に扱う。

### 原則

- 再接続した相手が以前と同じendpointまたは個体であると無条件に仮定しない
- offered function reference、path referenceおよびactivity referenceが再接続後も有効と仮定しない
- timeoutまたは切断時点で、操作が未実行、実行中または完了済みのどれかを推測しない
- resource、effective configurationおよびexternal bindingの状態を必要に応じて再確認する
- external pathだけが失われた場合と、OEP connection自体が失われた場合を区別する

再接続時のidentity、再開、重複防止、state recoveryおよび永続activityを共通protocolで支援するかは未決である。

## Patternの対応表

| pattern | 主な情報model |
|---|---|
| OEP-INT-001 | protocol identity、共通protocol互換性 |
| OEP-INT-002 | endpoint information、function definition reference、offered function、communication path |
| OEP-INT-003 | constraint、requested configuration、effective configuration、resource relationship |
| OEP-INT-004 | offered function、configuration、activity、outcome、failure |
| OEP-INT-005 | OEP native path、activity、data flow、outcome、failure |
| OEP-INT-006 | external binding、external endpoint reference、availability observation、external consumer |
| OEP-INT-007 | observation、information freshness、change |
| OEP-INT-008 | activity、configuration、resource relationship、outcome |
| OEP-INT-009 | endpoint information、reference lifetime、observation、activity |

## 最小実装との関係

OEP endpointは、OEP-INT-001と、自身が提供する機能およびpathをhostが把握するために必要なOEP-INT-002へ対応する必要がある。

個別機能は、その意味に必要なpatternだけを使用する。

- configurationを持たない機能はOEP-INT-003を不要にできる
- 有限操作だけの機能はOEP-INT-005を不要にできる
- external bindingを持たない機能はOEP-INT-006を不要にできる
- 動的変更を通知しない実装は、OEP-INT-007を再取得によって満たせる可能性がある
- cancellationを支援しない機能は、OEP-INT-008の停止要求へ対応する必要はないが、完了時のresource解放は定義する

「最小実装」は、非対応patternを成功したように見せる実装ではない。自身が提供する範囲と制限を正しく示す実装である。

## この文書で決めないこと

- 各patternを構成するmessage数と方向
- request、response、event、stream等のwire上の分類
- 同期、非同期およびbatch操作の共通形式
- operation、activityおよびdata flowの識別子
- ordering、correlation、flow controlおよびbackpressure
- timeout、retry、idempotencyおよび重複検出
- cancellationとresource解放の具体的な状態遷移
- snapshot、generation、変更通知およびcache invalidation
- external consumerとOEP hostのprocess間連携
- 再接続、resumeおよびstate recovery
- 同じ物理deviceに複数のOEP接続候補がある場合の識別、同一endpointとの対応、優先順位およびfallback
- USB composite device等で、どのinterfaceをOEP接続候補としてよいかを示すprofile規則

次段階では、これらのpatternから、最初のwire protocol draftに必要な共通interactionの最小集合を選び、要求を満たすmessage modelの候補を比較する。
