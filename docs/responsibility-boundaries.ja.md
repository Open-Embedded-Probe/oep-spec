# Open Embedded Probe — 責任境界

状態: **検討中の設計入力**。この文書は、[合意済みの概念モデル](conceptual-model.ja.md)に基づき、OEP共通protocol、個別機能、connection binding、host・probe実装、およびproject governanceがそれぞれ何を担当するかを整理する。

この文書は責任の所在を定めるものであり、message形式、encoding、識別子の形式、通信手順またはsoftware構造は規定しない。

## 責任を分ける目的

OEPでは、異なる機能、実装およびconnection interfaceを同じ相互運用modelで扱う。一方ですべての意味を共通protocolへ集めると、機能の追加が共通protocolの変更を必要とし、独自機能を扱えなくなる。

逆に、共通protocolの責任を持たず、すべてを個別機能やconnection interfaceへ委ねると、hostとprobeの組合せごとに専用protocolが必要になり、OEPの目的を満たせない。

そのため、次の六つの責任領域を区別する。

1. OEP共通protocol
2. 個別の機能定義
3. connection binding
4. external binding
5. hostおよびprobeの実装
6. OEP project governance

この区別は、wire上のlayer数、software module数またはrepository数を決めるものではない。

## 責任の概要

| 関心事 | 主に責任を持つ領域 |
|---|---|
| 通信相手がOEPか非OEPかの区別 | OEP共通protocol、connection binding |
| 提供される機能の区別 | OEP共通protocol |
| 機能が何を行うか | 個別の機能定義 |
| 独自payloadの意味 | 独自機能の定義と対応実装 |
| OEP通信をUSB、UART、network等で運ぶこと | connection binding |
| 機能dataをCDC、USB Audio、独自protocol等で運ぶこと | external binding |
| 実装ごとの性能や制限 | probe実装が事実を提供し、機能定義が意味を定め、OEP共通protocolが区別して運ぶ |
| 操作を実際に実行すること | probe実装 |
| 利用する機能と条件を選ぶこと | host実装 |
| 標準機能、共通identity、適合性規則の管理 | OEP project governance |

複数領域が関係する項目でも、同じ意味をそれぞれが独自に定義しない。共通protocolは機能固有の意味を決めず、機能定義はconnection interface固有の運搬方法を決めない。

## OEP共通protocolの責任

**OEP共通protocol**は、実装する機能や使用するconnection interfaceにかかわらず、OEP endpointが相互運用するために共有する規則である。

これは概念上の責任領域であり、単一のheader、library、messageまたはwire layerを意味しない。

### OEPであることの確認

OEP共通protocolは、hostが通信相手をOEP endpointとして確認し、非互換な別protocolと区別できるようにする責任を持つ。

USB VID:PID、port名、network address等の接続固有identityだけを、この確認の完全な代替としてはならない。具体的な確認方法は未決である。

### 提供される機能の区別

OEP共通protocolは、probeが提供する機能をhostが区別し、hostが理解する機能との共通部分を判断できるようにする責任を持つ。

次を区別できる必要がある。

- 異なる意味の機能
- 同じ機能定義に基づく複数の提供機能
- 標準機能と独自機能
- hostが理解する機能と理解しない機能

識別子の形式、列挙方法および選択手順は未決である。

### 機能への通信の分離

OEP共通protocolは、ある機能へ向けた操作、data、状態、結果および失敗が、別の機能のものとして誤解されないようにする責任を持つ。

独自機能のpayloadをOEP共通protocolが解釈する必要はない。ただし、どの独自機能に属するdataかを他の機能と区別し、hostとprobeの間でOEP内に限定して運べる必要がある。

### 共通の相互作用

OEP共通protocolは、個別機能がhostとprobeの間で操作、data、状態、結果および失敗を扱うために必要な共通の性質を提供する責任を持つ。

ここでいう責任は、すべての機能へ同じ操作modelを強制することを意味しない。短い操作、継続的なdata交換、probeからhostへの通知等に、どの共通性が必要かは後で決める。

### 非対応とprotocol上の失敗

OEP共通protocolは、少なくとも次を誤った成功として扱わないための共通規則を持つ責任がある。

- 相手がOEPではない
- 対象の機能を理解または提供していない
- OEP共通protocolとして通信を解釈できない
- 通信を継続できない

機能固有の条件不成立や失敗の意味は個別機能が定義する。共通protocolの失敗と機能固有の失敗を同じ原因として扱わない。

### 互換性と未知情報

OEP共通protocolは、未知の機能や将来追加された情報が存在しても、理解できる共通部分を不必要に利用不能にしないための規則を持つ責任がある。

共通protocol自身の改訂と、個別機能の改訂は概念上区別する。それぞれのversion表現や互換性判断の方法は未決である。

### 機能の通信経路

OEP共通protocolは、機能に必要なhost–probe間通信経路を、OEP native pathまたはexternal bindingとして区別できるようにする責任を持つ。

OEP native pathでは機能の通信をOEP protocolで運ぶ。external bindingでは、OEP機能と外部interfaceまたは外部protocolとの関係を明示し、通信の一部を外部経路で運ぶ。

OEP共通protocolはexternal bindingのpayloadを解釈する必要はない。ただし、どの提供機能とどのexternal bindingが関係するかをhostが認識できなければならない。OEP機能を未宣言の外部通信へ依存させてはならない。

## 個別機能の責任

**個別機能の定義**は、その機能を理解するhostとprobeが共有する、機能固有の意味を担当する。

### 機能の意味

個別機能は、必要に応じて次を定義する責任を持つ。

- 機能の目的と外部から観測できる振る舞い
- 操作とその意味
- 入力、data、結果および状態の意味
- 実装が持ち得る制限と、その単位や関係
- 条件不成立、拒否、部分的結果および失敗の意味
- 機能の改訂間で意味に互換性がある範囲

すべての機能が同じ種類の操作、状態またはdataを持つ必要はない。

### 標準機能

標準機能の定義は、独立したhost実装とprobe実装が、その機能について組合せ固有の知識なしに相互運用できるだけの意味を定める責任を持つ。

標準機能は、特定のproduct、board、firmwareまたはconnection interfaceだけで意味が成立するように定義してはならない。ただし、ある実装や接続環境では、その機能を提供できないことや条件が制限されることは許容する。

### 独自機能

独自機能の定義は公開しなくてもよく、OEP共通protocolや一般的なhostがpayloadの意味を理解する必要はない。

独自機能は次を守る。

- 他の標準機能または独自機能と誤認されない
- OEP共通protocolの意味を変更しない
- 必要な通信経路をOEP native pathまたはexternal bindingとして明示する
- 独自payload内部に別protocolの表現を使う場合も、どの経路で運ぶかを区別する

## Connection bindingの責任

**connection binding**は、特定のconnection interface上でOEP protocolを運ぶための規則を担当する。

connection bindingは、必要に応じて次を扱う責任を持つ。

- OEP通信をそのinterface上で開始できる状態にする方法
- OEPの情報をinterface上で運ぶ単位との対応
- interfaceが持つ転送量、順序性、信頼性等の性質への対応
- 接続候補からOEP endpointを見つけるために利用できる情報
- interface固有のidentity、profileまたは構成とOEP endpointとの関係
- 接続の切断、転送不能または破損をOEP側へ伝えるために必要な性質

具体的なframingや発見方法は、connection interfaceごとの設計で決める。

### Connection bindingが決めないこと

connection bindingは次を行わない。

- 個別機能の操作やdataの意味を再定義する
- 接続interfaceごとに同じ機能へ異なる意味を与える
- 個別機能のexternal bindingを、OEP自体を運ぶconnection bindingと混同する
- VID:PID等のinterface固有identityだけで、提供機能や適合性を完全に表す

接続環境によって機能を提供できる範囲が変わることはあり得る。その場合も、変わるのは提供の有無、利用可能性または制限であり、機能定義そのものの意味ではない。

## External bindingの責任

**external binding**は、OEP機能と、OEP protocol以外の外部interfaceまたは外部protocolとの関係を定義する。

USB CDC、USB Audio等の標準interface、既存の外部protocol、独自protocolおよび非公開protocolをexternal bindingとして利用できる。

external bindingは、必要に応じて次を扱う責任を持つ。

- どの提供機能とどの外部interfaceまたはprotocolが関係するか
- external bindingをhostが識別し、対応可否を判断するために必要な情報
- OEPと外部側のどちらが設定、開始、停止および状態管理を担当するか
- dataの方向、format、単位および外部protocol上の意味
- 外部経路の利用可能性、切断、drop、破損その他の失敗
- OEP native pathや他のexternal bindingとの代替、併用または排他関係
- 他機能と共有するresourceまたは同時利用上の制限

すべてのexternal bindingが同じ情報を必要とするとは限らない。USB標準class自身が定義する設定や状態をOEPで重複して定義する必要はないが、責任の所在とOEP機能との関係は曖昧にしない。

### External bindingの相互運用範囲

標準化されたexternal bindingは、その外部interfaceまたはprotocolへ対応するhostと相互運用できる。独自または非公開のexternal bindingは専用hostを必要としてよく、そのことだけでOEP不適合にはならない。

hostがexternal bindingへ対応しない場合でも、同じprobeが提供する他の共通機能や、同じ機能の別の通信経路を不必要に利用不能にしない。

### USB device profileとの関係

USB composite deviceでは、OEP endpoint用interfaceと、CDC、Audio等のexternal binding用interfaceが一つのVID:PIDを共有し得る。

project PIDを使用できるinterface構成、external binding、interface番号およびprofileの組合せは、将来のUSB profile規則で管理する。許容されたexternal bindingが同じVID:PIDに存在することを、非OEP protocolの混在とはみなさない。

## Probe実装の責任

probe実装は次の責任を持つ。

- 実際に提供する機能だけを提供機能として扱う
- 提供する標準機能の定義に従う
- 実装上の制限と現在の利用可能性について、OEPが要求する情報を正しく提供する
- 受理できない条件を、別の操作または成功として扱わない
- 操作、data、状態、結果および失敗を、対応する機能の意味に従って処理する
- OEP機能に必要な通信経路をOEP native pathまたはexternal bindingとして正しく公開する
- 未宣言の外部通信を機能成立の必須条件にしない
- 非OEP機能をOEPの提供機能として公開しない

target固有の信号生成、電気的保護、buffering、timing、内部resource管理等はprobe実装の責任になり得る。どこまでを各標準機能の適合要件に含めるかは機能ごとに決める。

## Host実装の責任

host実装は次の責任を持つ。

- 通信相手がOEP endpointであることを、OEPで定める方法に従って確認する
- 自身が理解する機能とprobeが提供する機能の共通部分だけを利用する
- 未知の機能やdataを、既知の別機能として解釈しない
- probeの制限と現在の利用可能性を無視して、成立しない操作を成功扱いしない
- 非対応、条件不成立、protocol上の失敗および機能固有の失敗を、必要な範囲で区別する
- product名、board名等だけを根拠とする組合せ固有の処理を、標準機能の利用に必須としない
- 使用するOEP native pathまたはexternal bindingへの対応を確認する
- 宣言されていない外部通信をOEP機能の一部として推測しない

専用hostは、独自機能の非公開な意味を知ることができる。それでも、OEP endpointの確認と独自機能の識別にはOEPの共通規則を使用する。

## OEP project governanceの責任

OEP project governanceは、実装ではなく、共通仕様とecosystem上のidentityを管理する責任領域である。

将来的に次を担当する可能性がある。

- OEP共通protocolの仕様と互換性規則
- 標準機能の採用、改訂および廃止
- 標準識別子、namespaceまたはregistry
- connection bindingとprofile
- 標準化されたexternal bindingとUSB profileへの組込み規則
- test vector、適合testおよび適合表示
- OEPの名称を互換性表示に使う条件
- project VID:PIDその他の共通identityの利用条件

softwareや文書のlicenseに基づく利用許可と、OEPへの適合表示またはproject identityの利用許可を混同しない。

非互換な派生protocolは、OEPのprotocol identityまたはproject identityを使用できない。適合するexternal bindingは、許容されたprofileの一部としてproject identityを共有し得る。具体的な管理主体、意思決定手順、異議申立て、名称方針およびPID利用規則は未決である。

## 境界を確認する例

### 標準機能を異なる接続interfaceで利用する

- 個別機能は操作と結果の意味を定義する
- connection bindingは各interface上でOEPを運ぶ
- probe実装は各interfaceで提供できる制限を正しく反映する
- host実装は共通の機能定義に従って利用する

接続interfaceの違いを理由に、機能の意味を別protocolとして定義し直さない。

### 非公開の独自機能を利用する

- OEP共通protocolは独自機能を他機能と区別する
- 専用hostとprobeだけが独自payloadの意味を理解する
- 独自仕様の公開は要求しない
- dataはOEP native pathでも非公開のexternal bindingでも運べる
- 使用する経路をhostが区別できるようにする

### Target UARTをUSB CDCへ投影する

- OEP機能はtarget側UARTのpin、routingおよび必要な変換を扱う
- external bindingはその機能とUSB CDC interfaceの関係を定義する
- UART dataはUSB CDCで直接送受信する
- hostは対応するCDC interfaceとOEP機能の関係を識別できる

### Target I2SをUSB Audioへ投影する

- OEP機能はtarget側I2Sのpin、format、channel mappingおよび変換条件を扱う
- external bindingはその機能とUSB Audio interfaceの関係を定義する
- audio sampleはUSB Audioで直接転送する
- USB Audio自身が持つ制御とOEPが持つ制御の責任を定義する

### OEPと独立した別protocolを同じdeviceへ併設する

- OEP endpoint、external bindingおよび独立した別protocolをhostが区別できるようにする
- 独立した別protocolをOEP機能またはexternal bindingとして公開しない
- 別protocolがOEP機能と関係する場合はexternal bindingとして明示する
- OEPと無関係な別protocolはOEPのprotocol identityを使用しない

具体的なUSB interface、PIDまたはprofileの合成・分離規則は後で決める。

## 未決事項

この責任境界は、次をまだ決定しない。

- OEP共通protocolを構成する具体的な機能と通信手順
- OEP endpointを確認する方法
- 提供される機能を識別、提示または選択する方法
- 共通の操作、data、状態、結果および失敗model
- 共通protocolと個別機能のversion関係
- connection bindingの共通部分とinterface固有部分
- external bindingの共通model、識別、lifecycleおよび適合性
- OEP native pathとexternal bindingを代替または併用する規則
- 制限、利用可能性および機能間関係の表現方法
- 適合性、名称、registryおよびproject identityのgovernance

次段階では、OEP共通protocolがOEP native pathとexternal bindingを扱うために必要な責任を、具体的なwire表現ではなくprotocol上の抽象的な振る舞いとして整理する。
