# Open Embedded Probe — 共通protocolの抽象的な振る舞い

状態: **合意済みの抽象的な振る舞い**。この文書は、[概念モデル](conceptual-model.ja.md)と[責任境界](responsibility-boundaries.ja.md)に基づき、OEP共通protocolが外部から観測可能にする必要のある振る舞いを整理する。下流設計によって矛盾が見つかった場合は、理由を記録して改訂する。

この文書は、packet、message、field、encoding、転送単位、数値識別子または具体的なstate machineを規定しない。ここで示す段階を一つずつ独立した通信として実装することも要求しない。

## 基本的な流れ

```text
接続候補を得る
      │
      ▼
OEP endpointであることと共通protocolの互換範囲を確認する
      │
      ▼
提供される機能と、その通信経路を把握する
      │
      ▼
利用する機能、経路、条件を選ぶ
      │
      ▼
probeが要求を受理または拒否する
      │
      ▼
OEP native pathまたはexternal bindingで機能を利用する
      │
      ▼
完了、停止、解放、失敗または接続喪失を扱う
```

この流れは、hostが機能を安全に選択して利用するために必要な論理的関係を示す。実際のprotocolでは、複数段階をまとめる、既知情報を再利用する、または機能によって不要な段階を省くことができる。

## 1. 接続候補を得る

hostは、connection bindingが提供する方法により、OEP endpointである可能性のある接続候補を得る。

USB VID:PID、USB interface、serial port、network service等は候補を見つける手掛かりになり得るが、それだけで相手がOEPであること、提供機能、適合性または真正性を確定しない。

接続候補の列挙方法、OS API、address形式および自動接続policyは、connection bindingまたはhost implementationの責任とする。

## 2. OEP endpointを確認する

hostは、機能を利用する前に、通信相手がOEP endpointであることをOEP共通protocol上で確認できなければならない。

確認によって、少なくとも次を誤認しないようにする。

- OEPではない別protocol
- OEPから派生した非互換protocol
- OEPと同じ物理deviceへ併設された独立した別interface
- OEP endpointに関連付けられたexternal binding

external bindingはOEP endpointそのものではない。OEP endpointの確認前に、CDC、Audio等のinterfaceがどのOEP機能へ対応するかを推測してはならない。

具体的な確認手順、protocol identityおよび応答内容は未決である。

## 3. 共通protocolの互換範囲を判断する

hostとprobeは、共通protocolの意味を共有できる範囲を判断できなければならない。

互換性がない場合は、同じ名称、PIDまたは接続形式であることだけを理由に通信を継続しない。互換な共通部分を利用できる場合に、どの範囲まで継続できるかは将来の互換性規則で定義する。

共通protocolの互換性と個別機能の互換性は別に判断する。共通protocolが互換でも、すべての個別機能が互換とは限らない。

version表現、互換範囲の表現および判断主体は未決である。

## 4. 提供される機能を把握する

hostは、probeが実際に提供する機能を把握し、自身が理解する機能との共通部分を判断できなければならない。

機能について、概念上少なくとも次を区別できる必要がある。

- どの機能定義に基づくか
- 同じ機能定義に基づく複数の提供機能のうち、どれか
- 標準機能か独自機能か
- hostが理解する意味または互換範囲か
- 現在の接続で利用候補になり得るか

hostが理解しない機能の存在によって、理解する機能を不必要に利用不能にしない。未知の機能を、名称や位置が似ている既知の機能として扱わない。

機能の提示方法、一括取得、個別照会、cacheおよび変更通知の有無は未決である。

## 5. 機能の通信経路を把握する

hostは、提供される機能が利用できる通信経路を把握できなければならない。

通信経路には次がある。

- OEP native path
- 標準化されたexternal binding
- 独自または非公開のexternal binding

一つの提供機能が複数の経路を持つ場合、hostはそれらが代替、併用可能または排他的であるかを誤解なく扱える必要がある。

### OEP native path

hostは、機能の操作、data、状態、結果または失敗をOEP protocolで扱う。

すべての機能が同じdata交換modelを持つことは要求しない。短い操作、長時間の処理、連続data、probeからhostへの通知等に必要な共通性は後で決める。

### External binding

hostは、少なくとも次を判断できる必要がある。

- どの提供機能に対応するbindingか
- どの外部interfaceまたは外部protocolを使用するか
- hostまたはexternal consumerがそのbindingへ対応できるか
- bindingが宣言されているか、および各側で既知の状態は何か
- 他の経路や機能との代替、併用または排他関係

external consumerはOEP hostと同一programである必要はない。OS driverや別applicationが外部dataを利用する場合も、OEP hostまたは利用者が対応するOEP機能との関係を判断できる必要がある。

bindingが宣言されていることや外部interfaceが見えていることは、そのinterfaceを現在openして通信できることの保証ではない。probeはhost OS上のdriver、権限、device node、他processによる占有等を判断できず、hostはprobe内部のresource状態を判断できない場合がある。

したがって、少なくとも次を概念上区別する。

- bindingがOEP機能に関連付けて宣言されている
- external consumerがbindingの種類へ対応している
- 対応する外部interfaceをhost側で特定できる
- probe側で既知の範囲では利用を妨げる状態がない
- host側で既知の範囲では利用を妨げる状態がない
- 実際のopenまたは通信によって利用できることを確認した
- いずれかの状態を現在は判断できない

これらを固定した状態列挙としてprotocolへ採用することはまだ決めない。状態の情報源と観測範囲を誤認しないことが必要である。

外部interfaceの具体的な参照方法はbindingごとに定義する。USB interface番号、OS path、network endpoint等の採用はまだ決めない。

## 6. 制限と利用可能性を判断する

hostは、機能と通信経路について、目的の条件が成立するか判断するために必要な情報を得られなければならない。

少なくとも次の違いを扱える必要がある。

- 機能自体を提供していない
- 機能の意味または改訂に互換性がない
- 機能は提供するが、要求条件が実装上の制限を超える
- 機能は提供するが、現在の状態またはresource関係により利用できない
- OEP native pathは利用できるが、目的のexternal bindingは利用できない
- external bindingは存在するが、hostまたはexternal consumerが対応していない
- external bindingは宣言されているが、実際にopenできるかまだ確認していない
- external bindingのopenまたは通信を試みたが、host側またはprobe側の理由で利用できない

制限を事前に静的情報として示すか、具体的な条件をprobeへ提示して判断するか、または両方を利用するかは未決である。

## 7. 利用条件を要求し、受理結果を得る

機能が構成やresource確保を必要とする場合、hostは目的の条件をprobeへ要求でき、probeはその要求を受理したか拒否したかを明確に示さなければならない。

probeは、満たせない要求を別の条件へ暗黙に変更して成功扱いしてはならない。条件を調整して提案できるようにするかは未決だが、要求と実際に採用された条件が異なる場合はhostが区別できる必要がある。

機能定義は条件の意味を定め、probe実装は自身の制限と現在の状態に基づいて判断する。OEP共通protocolは受理、拒否および採用条件を誤解なく対応付けるために必要な共通性を担当する。

設定を持たない機能や、利用時に個別の受理を必要としない機能へ、この段階を強制しない。

## 8. External bindingを準備または確認する

external bindingを使用する場合、OEP側と外部側の責任分担に従って必要な準備を行い、external consumerが外部経路のopenまたは利用を試みる。準備が完了しても、別processによる占有等によりopenが成功するとは限らない。

bindingごとに、少なくとも次の責任がどこにあるか明確でなければならない。

- 外部interfaceの生成または存在確認
- routingとdata変換の設定
- format、rate、channel等の選択
- 開始と停止
- external consumerによるopenとclose
- 状態変化と失敗の通知
- resourceの確保と解放

USB標準classや外部protocol自身が責任を持つ操作を、OEPで重複して実行することは要求しない。OEPと外部側の双方が変更できる設定がある場合、不一致をどう検出し、どちらを正とするかをbindingが定義する必要がある。

USB descriptorのように接続前または列挙時に固定される構成と、接続後に動的に変更できる構成を同じものとして扱わない。

## 9. 機能を利用する

hostまたはexternal consumerは、選択した通信経路に従って機能を利用する。

### OEP native pathを使う場合

OEP共通protocolは、機能固有の意味を解釈せずに、対象の提供機能と操作、data、状態、結果または失敗の関係を維持できなければならない。

複数の操作やdata flowを同時に扱う必要があるか、順序、相関、flow control、取消しおよびpartial resultをどこまで共通化するかは未決である。

### External bindingを使う場合

実dataは外部interfaceまたは外部protocolで直接交換できる。OEP共通protocolがそのpayloadを中継または解釈することは要求しない。

OEP側は、binding定義で割り当てられた範囲について、利用可能性、構成、状態、失敗およびresource関係を扱う。外部側でのみ観測できる状態や失敗を、どこまでOEPへ反映するかはbindingが定義する。

OEP側が外部経路を利用可能と報告する場合も、その主張はprobe側で観測できる範囲に限定する。host側でのopen成功まで保証する表現として扱わない。

## 10. 完了、停止および解放を扱う

機能または通信経路がresourceを保持する場合、hostは不要になったresourceを解放でき、probeは解放後の利用可能性を一貫して扱わなければならない。

正常完了、hostからの停止、probeからの停止、external consumerの切断、connection interfaceの喪失、および実装内部の失敗は同一とは限らない。

すべての機能へ明示的なopen、closeまたはsessionを要求するものではない。暗黙のlifecycleを持つ機能でも、外部から観測できるresourceと状態の変化が矛盾しない必要がある。

## 11. 失敗と回復を扱う

hostは、少なくとも次のfailure domainを誤った成功として扱わないために必要な違いを判断できなければならない。

- connection bindingまたは下位通信の失敗
- OEP共通protocolとして解釈できない通信
- OEP endpointまたは共通protocolの非互換
- 機能の非対応または非互換
- 要求条件の拒否
- resource競合または一時的な利用不能
- 機能固有の実行失敗またはpartial result
- external bindingの不在、非対応または利用不能
- 外部interfaceまたはexternal consumer側の失敗

すべてを一つの共通error code空間へ入れることは要求しない。どの領域で発生した失敗かを誤認しないことを要求する。

再試行、再接続、状態再取得、操作取消しおよび自動回復の共通規則は未決である。失敗後に以前の構成や操作が継続していると暗黙に仮定しない。

## 12. 変化を扱う

probeの提供機能、制限、利用可能性、resource関係またはexternal bindingの状態は、接続中に変化する可能性がある。

hostが変化を知る必要がある場合、再取得、通知または操作結果等によって、古い情報を無期限に正しいものとして扱わないための方法が必要になる。

何が動的に変化できるか、変更通知を必須にするか、およびcacheの有効期間は未決である。

## 抽象的な不変条件

1. hostはOEP endpointの確認前に、接続固有identityだけからOEP機能を確定しない
2. 共通protocolの互換性と個別機能の互換性を混同しない
3. 未知の機能が既知の共通機能の利用を不必要に妨げない
4. 各通信経路をOEP native pathまたはexternal bindingとして区別する
5. OEP機能を未宣言の外部通信へ依存させない
6. external bindingと対応する提供機能の関係をhostが判断できる
7. external consumerがOEP hostと別であっても、関係する機能と経路を誤認しない
8. 受理できない条件を暗黙に成功扱いしない
9. failure domainを誤った成功または別機能の失敗として扱わない
10. 接続、機能、通信経路およびresourceの状態変化を同一のものとして扱わない

## この文書で決めないこと

- protocol identityとversionのencoding
- OEP endpoint確認のmessage sequence
- 機能、提供機能および通信経路の識別子
- 機能情報と制限のschema
- request、response、event、stream等の採否と共通形式
- concurrency、ordering、correlation、flow controlおよびcancellation
- error表現とerror codeのscope
- external bindingが外部interfaceを参照する形式
- USB profile、interface番号、descriptorおよびPID規則
- 認証、認可、機密性、完全性およびtrust model
- 再接続、状態回復および永続性

次段階では、この抽象的な振る舞いから、OEP共通protocolに必要な情報modelと、最小限のinteraction patternを抽出する。
