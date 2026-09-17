# Open Embedded Probe — 責任境界

状態: **検討中の設計入力**。この文書は、[合意済みの概念モデル](conceptual-model.ja.md)に基づき、OEP共通protocol、個別機能、connection binding、host・probe実装、およびproject governanceがそれぞれ何を担当するかを整理する。

この文書は責任の所在を定めるものであり、message形式、encoding、識別子の形式、通信手順またはsoftware構造は規定しない。

## 責任を分ける目的

OEPでは、異なる機能、実装およびconnection interfaceを同じ相互運用modelで扱う。一方ですべての意味を共通protocolへ集めると、機能の追加が共通protocolの変更を必要とし、独自機能を扱えなくなる。

逆に、共通protocolの責任を持たず、すべてを個別機能やconnection interfaceへ委ねると、hostとprobeの組合せごとに専用protocolが必要になり、OEPの目的を満たせない。

そのため、次の五つの責任領域を区別する。

1. OEP共通protocol
2. 個別の機能定義
3. connection binding
4. hostおよびprobeの実装
5. OEP project governance

この区別は、wire上のlayer数、software module数またはrepository数を決めるものではない。

## 責任の概要

| 関心事 | 主に責任を持つ領域 |
|---|---|
| 通信相手がOEPか非OEPかの区別 | OEP共通protocol、connection binding |
| 提供される機能の区別 | OEP共通protocol |
| 機能が何を行うか | 個別の機能定義 |
| 独自payloadの意味 | 独自機能の定義と対応実装 |
| OEP通信をUSB、UART、network等で運ぶこと | connection binding |
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

### Protocol外通信の禁止

OEP共通protocolは、OEP機能に必要なhost–probe間通信をOEP内で完結できる範囲を提供しなければならない。

個別機能やconnection bindingは、OEP上の操作を入口としてhost–probe通信をOEP外へ切り替えてはならない。別protocol由来のpacketやbyte列を独自payloadとしてOEP内で運ぶことは、この禁止に該当しない。

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
- OEP機能として必要なhost–probe間通信をOEP外へ迂回させない
- 独自payload内部に別protocolの表現を使う場合も、通信経路はOEP内に保つ

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
- OEP機能をinterface固有の専用protocolへ切り替える
- VID:PID等のinterface固有identityだけで、提供機能や適合性を完全に表す

接続環境によって機能を提供できる範囲が変わることはあり得る。その場合も、変わるのは提供の有無、利用可能性または制限であり、機能定義そのものの意味ではない。

## Probe実装の責任

probe実装は次の責任を持つ。

- 実際に提供する機能だけを提供機能として扱う
- 提供する標準機能の定義に従う
- 実装上の制限と現在の利用可能性について、OEPが要求する情報を正しく提供する
- 受理できない条件を、別の操作または成功として扱わない
- 操作、data、状態、結果および失敗を、対応する機能の意味に従って処理する
- OEP機能に必要なhost–probe間通信をOEP外へ迂回させない
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
- OEP機能に必要なhost–probe間通信をOEP外へ迂回させない

専用hostは、独自機能の非公開な意味を知ることができる。それでも、OEP endpointの確認と独自機能の識別にはOEPの共通規則を使用する。

## OEP project governanceの責任

OEP project governanceは、実装ではなく、共通仕様とecosystem上のidentityを管理する責任領域である。

将来的に次を担当する可能性がある。

- OEP共通protocolの仕様と互換性規則
- 標準機能の採用、改訂および廃止
- 標準識別子、namespaceまたはregistry
- connection bindingとprofile
- test vector、適合testおよび適合表示
- OEPの名称を互換性表示に使う条件
- project VID:PIDその他の共通identityの利用条件

softwareや文書のlicenseに基づく利用許可と、OEPへの適合表示またはproject identityの利用許可を混同しない。

非互換な派生protocolは、OEPのprotocol identityまたはproject identityを使用できない。具体的な管理主体、意思決定手順、異議申立て、名称方針およびPID利用規則は未決である。

## 境界を確認する例

### 標準機能を異なる接続interfaceで利用する

- 個別機能は操作と結果の意味を定義する
- connection bindingは各interface上でOEPを運ぶ
- probe実装は各interfaceで提供できる制限を正しく反映する
- host実装は共通の機能定義に従って利用する

接続interfaceの違いを理由に、機能の意味を別protocolとして定義し直さない。

### 非公開の独自機能を利用する

- OEP共通protocolは独自機能を他機能と区別してdataを運ぶ
- 専用hostとprobeだけが独自payloadの意味を理解する
- 独自仕様の公開は要求しない
- host–probe間通信はOEP内で完結する

### OEPと非OEPを同じdeviceへ併設する

- OEP endpointと非OEP側をhostが区別できるようにする
- 非OEP機能をOEPの提供機能として公開しない
- 非OEP側はOEPのprotocol identityやproject identityを使用しない
- 非OEP通信をOEP機能の実行経路として使用しない

具体的なUSB interface、PIDまたはprofileの分離規則は後で決める。

## 未決事項

この責任境界は、次をまだ決定しない。

- OEP共通protocolを構成する具体的な機能と通信手順
- OEP endpointを確認する方法
- 提供される機能を識別、提示または選択する方法
- 共通の操作、data、状態、結果および失敗model
- 共通protocolと個別機能のversion関係
- connection bindingの共通部分とinterface固有部分
- 制限、利用可能性および機能間関係の表現方法
- 適合性、名称、registryおよびproject identityのgovernance

次段階では、OEP共通protocolが外部へ提供する必要のある責任を、具体的なwire表現ではなくprotocol上の抽象的な振る舞いとして整理する。
