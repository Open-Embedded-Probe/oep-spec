# Open Embedded Probe — 共通protocolの情報model

状態: **合意済みの情報model**。この文書は、[共通protocolの抽象的な振る舞い](common-protocol-behavior.ja.md)を成立させるために、OEPが概念上区別する必要のある情報とその関係を整理する。下流設計によって矛盾が見つかった場合は、理由を記録して改訂する。

ここで定義する情報要素は、そのままwire上のobject、message、fieldまたは個別のqueryになるとは限らない。複数の情報をまとめること、既知の情報を省略すること、接続固有の方法から導出することは、将来のprotocol設計で決める。

## 情報modelの全体像

```text
OEP endpoint
  ├─ protocol identity / compatibility
  ├─ endpoint information
  └─ offered function
       ├─ function definition reference
       ├─ implementation constraints
       ├─ resource relationships
       └─ communication path
            ├─ OEP native path
            └─ external binding
                 └─ external endpoint reference

host request
  └─ requested configuration
          │
          ▼
probe decision
  ├─ accepted / effective configuration
  └─ rejection
          │
          ▼
activity / data flow / outcome / failure
```

この図は情報の包含または参照関係を示す。実装上のmemory layoutやwire上の入れ子構造は示さない。

## 情報のscope

情報は、何についての情報かを区別できなければならない。

| scope | 対象の例 |
|---|---|
| protocol | OEPであること、共通protocolの互換範囲 |
| endpoint | 一つの論理的なOEP通信相手 |
| offered function | probeが提供する特定の機能 |
| communication path | その機能を利用する一つの経路 |
| configuration | hostが要求した条件、probeが採用した条件 |
| activity | 一回の操作、継続処理またはdata flow |
| observation | ある主体がある時点または範囲で観測した状態 |

一つのscopeの情報を、別のscopeへ無条件に適用してはならない。たとえば、endpointがOEPに対応することは全機能への対応を意味せず、機能を提供することはすべてのcommunication pathが現在利用できることを意味しない。

## Protocol identityと互換性

### Protocol identity

hostが通信相手をOEP endpointとして確認し、非互換なprotocolと区別するための情報。

protocol identityは、USB VID:PID、serial port名、network addressまたはproduct名だけで代替しない。

具体的な値、表現、確認方法および偽装への対処は未決である。

### 共通protocolの互換性

hostとprobeが共有できるOEP共通protocolの意味の範囲を判断するための情報。

共通protocolの互換性は、個別機能、connection binding、external bindingおよびUSB profileの互換性とは区別する。

単一のversion番号、範囲、feature集合その他のどのmodelを用いるかは未決である。

## Endpoint information

**endpoint information**は、現在通信している論理的なOEP endpointについての情報である。

候補には次がある。

- endpointを現在の接続内で参照するために必要な情報
- 実装、製品またはbuildを診断目的で説明する情報
- 提供情報の更新や再取得が必要か判断するための情報
- endpoint全体へ適用される制限または状態

実装名、product名、board名またはbuild情報は、診断や表示に利用できる。ただし、標準機能の意味や対応可否をそれらだけから判断しない。

永続的なdevice identityまたは個体識別子を必須にするかは未決である。identityの安定性、privacyおよび複製可能性を検討せずに一意性を仮定しない。

## Function definition reference

**function definition reference**は、提供される機能がどの意味の機能かを区別するための情報である。

少なくとも次を誤認しないようにする。

- 異なる標準機能
- 標準機能と独自機能
- 異なる主体が定義した独自機能
- 意味に互換性がない機能の改訂

識別子の大きさ、namespace、ownerの表現、registryおよびversionとの関係は未決である。

識別子そのものへ機能の性能、実装、接続方法または現在状態の意味を詰め込まない。それらはoffered functionやcommunication pathの情報として扱う。

## Offered function

**offered function**は、probeが実際に提供する一つの機能を表す。

offered functionは、少なくとも次との関係を持つ。

- function definition reference
- 現在のendpoint内でその提供機能を区別するためのreference
- 実装上の制限
- communication path
- 必要に応じて状態、利用可能性またはresource関係

同じfunction definitionに基づくoffered functionが複数存在してよい。function definitionのidentityと、offered functionのinstance referenceを混同しない。

offered functionのreferenceが接続を越えて安定するか、再接続時に再利用できるかは未決である。安定性が定義されていないreferenceを永続identityとして保存しない。

## Communication path

**communication path**は、offered functionを利用する一つの通信経路を表す。

各pathについて、概念上次を区別する。

- OEP native pathかexternal bindingか
- どのoffered functionに属するか
- 同じ機能の他pathとの代替、併用または排他関係
- path固有の制限
- pathを利用するために必要な構成またはresource
- pathについて各主体が観測した状態

一つのoffered functionが一つ以上のpathを持つ場合、それらを個別に参照する必要があるかは将来のinteraction設計で決める。

### OEP native path information

OEP native pathについて、hostが対応可能なdata交換形態か、どの制限があるかを判断するための情報が必要になり得る。

request、response、event、stream等を固定分類として採用するかは未決である。

### External binding information

external bindingは、少なくとも次の関係を表せる必要がある。

- 対応するoffered function
- external bindingの種類または定義
- 対応するexternal endpoint
- OEP側と外部側の設定、開始、停止、状態および失敗の責任分担
- external consumerに必要な前提
- OEP native pathまたは別bindingとの関係
- resource共有または排他関係

USB CDC、USB Audio等の標準bindingでは、標準classがすでに定義する意味を参照できる。OEPで同じ意味を重複して定義する必要はない。

独自または非公開bindingでは、一般的なhostが内容を理解できなくてもよい。ただし、理解できないbindingを既知の標準bindingとして扱わないための区別は必要である。

## External endpoint reference

**external endpoint reference**は、external consumerが利用する外部interfaceまたは外部protocol上の相手を、対応するOEP endpointおよびoffered functionと関連付けるための情報である。

候補例にはUSB interface、OSが公開するdevice、network endpoint等があるが、具体的な表現はbindingとconnection environmentによって異なる。

referenceには、その有効scopeとlifetimeが必要である。USB interface番号のように一つのUSB構成内で意味を持つ値を、別device、別構成または再接続後にも同じ意味として扱わない。

external endpoint referenceを解決できることは、openまたは通信の成功を保証しない。

## Constraint

**constraint**は、offered function、communication path、configurationまたはresourceについて、受理可能な条件や実行可能な範囲を表す情報である。

constraintには次の形があり得る。

- 数値範囲または上限
- 選択肢
- 複数条件の組合せ
- 他機能またはpathとの同時利用条件
- 現在状態に依存する条件
- 具体的な要求をprobeが評価することによってのみ判明する条件

probeは、hostが利用候補を選ぶために必要なconstraintを、表現可能な範囲で開示する。すべてのconstraintを静的な一覧へ変換できるとは仮定せず、静的記述と具体的なconfiguration要求への受理・拒否を併用できるmodelが必要になる可能性がある。

constraintの意味、単位および条件間の関係は、個別機能またはbindingが定義する。OEP共通protocolは、意味を推測せず正しいscopeへ対応付ける。

## Resource relationship

**resource relationship**は、複数のoffered functionまたはcommunication pathが、probe内部または外部interface上のresourceを共有することによって生じる関係を表す。

少なくとも次の関係が必要になる可能性がある。

- 同時利用できない
- 一方が他方の代替である
- 一つの構成変更が複数機能へ影響する
- 一つのactivityがresourceを占有している間だけ他方が利用できない

内部hardware resourceをすべて公開することは要求しない。hostが成立しない組合せを成功すると誤認しないために必要な外部関係だけを表せればよい。

resourceを独立objectとして表すか、機能間関係として表すかは未決である。

## Availability observation

**availability observation**は、ある主体が、あるscopeと時点または有効範囲において観測した状態である。

availabilityを一つの絶対的なbooleanとして扱わない。少なくとも次を区別する。

- 機能またはbindingが宣言されている
- probe側で既知の範囲では利用を妨げる状態がない
- host側でexternal endpointを特定できる
- external consumerがbindingの種類へ対応している
- external endpointのopenを試みて成功または失敗した
- 実際の通信を確認した
- 現在は判断できない

observationには、概念上次の性質が必要になる。

- 誰またはどの領域による観測か
- 何についての観測か
- 何を確認し、何を確認していないか
- いつまで、またはどの状態が変わるまで有効と考えられるか

timestamp、generation、期限等の具体的な表現は未決である。probe側のobservationをhost側のopen保証として扱わない。

## Requested configurationとeffective configuration

### Requested configuration

**requested configuration**は、hostが利用したい条件を表す。

### Effective configuration

**effective configuration**は、probeが受理し、実際に採用する条件を表す。

requested configurationとeffective configurationは同じとは限らない。probeが条件を調整できる場合、hostが差異を確認して同意する必要があるか、調整を事前に許可できるかは未決である。

いずれの場合も、probeは満たせないrequested configurationを、異なるeffective configurationで暗黙に成功扱いしてはならない。

拒否されたconfiguration、受理されたconfiguration、現在有効なconfiguration、および以前有効だったconfigurationを混同しない。

## Activity

**activity**は、offered function上で進行する一回の操作、継続処理またはdata flowを区別するための概念である。

すべての機能が明示的なactivity identityを必要とするとは限らない。複数の処理が同時進行する場合や、開始後に結果、停止または失敗を対応付ける必要がある場合に、区別が必要になる。

activityについて、必要に応じて次を対応付ける。

- 対象のoffered function
- 使用するcommunication path
- effective configuration
- 開始、進行、完了、停止または失敗
- resourceの占有と解放
- 結果またはdata flow

session、transaction、job、stream等の具体的なmodelは未決である。

## Outcomeとfailure

**outcome**は、要求またはactivityの結果を表す。

**failure**は、要求またはactivityを意図した意味で完了できなかったことを表す。

少なくとも次を区別するための情報が必要になる。

- どの要求、activity、機能またはpathに関係するか
- 成功、拒否、未完了または失敗のどれか
- failure domain
- resultが存在する場合、その全部または一部を信頼できるか
- resourceやconfigurationがどの状態に残ったか
- hostが再試行、再取得または停止を判断するために必要な情報

failure domainには、connection、OEP共通protocol、機能、configuration、resource、external bindingおよびexternal consumer側があり得る。

すべてのfailureを単一のglobal error番号空間へ入れることは要求しない。共通protocolは、scopeとdomainを誤認しないための共通性を提供する。

## Information freshnessとchange

機能、constraint、resource関係、configurationおよびavailability observationは、接続中または再接続後に変化し得る。

情報について、必要に応じて次を区別する。

- 定義として安定している情報
- 一つのfirmware buildまたはdevice構成で安定している情報
- 現在の接続中だけ有効な情報
- activityまたはresource状態により変化する情報
- ある主体が過去に観測しただけの情報

変更を通知するか、再取得するか、操作時に再検証するかは未決である。古いobservationを現在の保証として扱わない。

## Unknown informationとcriticality

受信側は、未知の機能、bindingまたは追加情報に遭遇し得る。

未知情報が存在しても、理解できる別のscopeを不必要に利用不能にしない。一方、その情報を理解しなければ対象scopeを安全に解釈できない場合は、無視して利用を続けてはならない。

したがって、将来のprotocolは、少なくとも次を区別する必要がある。

- 理解しなくても対象scopeの意味が変わらない追加情報
- 理解しなければ対象scopeを利用できない情報

criticalityをfield、container、versionまたは別の方法で表すかは未決である。未知でcriticalな情報がある場合も、影響のない別機能まで無条件に利用不能にしない。

## Capabilityという語の扱い

この段階では、**capability**を単一のobjectや固定schemaの名称として確定しない。

一般的な説明では、提供機能、communication path、constraint、resource関係およびavailability observationをまとめてcapabilityと呼ぶことがある。ただし、次を一つの静的な一覧として扱わない。

- 実装しているという宣言
- 実装上の限界
- 現在状態による利用可能性
- host側の対応
- 実際のopenまたは通信成功

## Conformance informationとの関係

runtimeに観測できるoffered functionやconstraintと、OEP projectによる適合表示またはproject identityの利用資格は別の情報である。

probeが自身について行うclaimだけで、第三者によるcertification、品質、安全性または真正性を証明したものと扱わない。

conformance claimをprotocol上で運ぶか、その発行者や証拠をどう表すかは未決である。

## 情報modelの不変条件

1. protocol、endpoint、function definition、offered function、communication pathおよびactivityのscopeを混同しない
2. function definitionのidentityへ実装状態や接続方法の意味を詰め込まない
3. offered functionの宣言を、すべてのpathが現在利用可能という保証にしない
4. external endpoint referenceを、openまたは通信成功の保証にしない
5. probe側のobservationをhost側の状態として扱わない
6. requested configurationとeffective configurationを区別する
7. 未知情報の影響範囲を、無関係な機能へ不必要に広げない
8. runtime情報と適合表示またはproject identity利用資格を混同しない

## この文書で決めないこと

- 各情報要素を独立したobjectまたはfieldにするか
- 識別子の幅、encoding、namespaceおよび割当方法
- 一括取得、個別query、変更通知およびcacheの方法
- snapshot、generation、timestampおよび有効期限の表現
- configurationの比較、調整およびcommit方法
- activity、stream、jobまたはsessionの共通model
- external endpoint referenceのconnection bindingごとの表現
- error code、failure detailおよびpartial resultの形式
- criticalityと未知情報のwire表現
- conformance claimをruntime protocolへ含めるか

次段階では、この情報modelを利用する最小限のinteraction patternを定義する。
