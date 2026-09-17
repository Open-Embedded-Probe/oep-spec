# Open Embedded Probe — 概念モデル

状態: **合意済みの概念モデル**。この文書は、[プロジェクトの目的と範囲](project-concept.ja.md)、[相互運用ユースケース](use-cases.ja.md)および[Project要求](project-requirements.ja.md)で使う中心概念と、それらの関係を整理する。具体的なprotocol設計によって矛盾が見つかった場合は、理由を記録して改訂する。

この文書で概念を区別することは、それぞれに独立したfield、数値ID、messageまたは通信段階を設けることを意味しない。具体的なprotocol表現は後で決める。

## モデルの全体像

```text
host implementation
   │                 │
   │ OEP protocol    │ declared external path
   ▼                 ▼
OEP endpoint    external interface / protocol
   │                 │
   └────────┬────────┘
            ▼
    probe implementation ── target側の通信・信号 ── target
            │
            ├─ 提供する機能 A ── 機能定義 A
            ├─ 提供する機能 B ── 機能定義 B
            └─ 独自機能 X   ── 独自機能定義 X
```

hostとprobeの間でOEP機能を利用する通信経路には、OEP protocolで運ぶOEP native pathと、OEP上で機能との関係を明示したexternal bindingがある。connection interfaceはOEP自体を運ぶが、機能の意味を定義しない。probeとtargetの間の通信や電気信号は、host–probe間の通信経路には含めない。

## 中心となる主体

### Host

probeが提供する機能を利用するsoftware側のrole。

hostは一つ以上の機能定義を理解し、probeが提供する機能との間に利用可能な共通部分がある場合に、その機能を利用する。

hostは汎用であっても、特定の独自機能だけに対応する専用hostであってもよい。専用hostであっても、probeとの機能通信はOEP内で行う。

### Probe

組み込みtargetに対する開発支援機能を提供する側のrole。hardware、firmwareおよびsoftwareを組み合わせた実装であってもよい。

probeはすべてのOEP機能を提供する必要はない。実際に提供する機能だけを持つ。

### Target

probeが操作、通信、観測または計測の対象とする組み込みsystem。

targetはhost–probe間のOEP通信へ直接参加することを要求されない。probeとtargetの間で使うprotocolや電気信号は、OEPがhost–probe間で機能を表現する方法とは区別する。

### 利用者

host、probeおよびtargetを組み合わせ、目的の開発作業を行う者。

利用者はprotocol上の通信相手とは限らないが、相互運用の結果、非対応の理由、失敗および適合性を理解できる必要がある。

### External consumer

**external consumer**は、external bindingが示す外部interfaceまたは外部protocolを直接利用するsoftwareまたはOS componentである。

たとえば、OEP hostがtarget UARTのroutingを設定し、別のterminal applicationが対応するUSB CDCを利用できる。OEP hostがI2Sの解釈を設定し、OSのaudio driverとaudio applicationがUSB Audioを利用することもできる。

OEP hostとexternal consumerは同じprogramであっても、別のprocess、driverまたはapplicationであってもよい。両者をどのように関連付け、設定変更やlifecycleを調整するかはexternal bindingの責任に含める。

## 実装とrole

**実装**は、hostまたはprobeのroleを実現する具体的なsoftware、firmwareまたはhardwareである。

一つの製品またはprogramが複数のroleを持つ可能性は排除しない。ただし、概念上のroleが同じprocess、deviceまたは通信経路に存在することと、role間の責任が同じであることは区別する。

source codeのfork、別hardwareへのportまたは別言語での再実装は、実装の由来を表す。OEP実装であるかどうかは由来ではなく、OEPの必須要求を満たすかによって決まる。

## OEP endpoint

**OEP endpoint**は、connection interfaceを介してhostがOEP protocolによる通信を行う論理的な相手である。

物理device、USB device、serial port、network address等とOEP endpointが常に一対一になるとは限らない。どの単位を一つのendpointとして扱うか、その発見方法および一つの接続上に複数endpointを置けるかは未決である。

hostは、通信相手がOEP endpointであるか、非互換な別protocolであるかを区別できる必要がある。

## Connection interface

**connection interface**は、hostとprobeの間でOEP protocolを運ぶ物理的または論理的な接続環境である。

USB、UART、network等は候補例であり、この文書では必須の接続方法を決めない。

connection interfaceには、接続の確立、dataを運ぶ単位、転送量、順序性、信頼性その他の固有性質があり得る。これらの違いは、OEP機能そのものの意味と区別する。

connection interfaceは、個別機能のdataを外部interfaceへ結び付けるexternal bindingとは異なる概念である。

## 機能の通信経路

### OEP native path

**OEP native path**は、機能の操作、data、状態、結果または失敗をOEP protocolで運ぶ通信経路である。

OEP native pathを利用する機能は、個別の外部interfaceへ依存せず、対応するOEP hostから利用できる。実際に利用できる性能や条件はconnection interfaceと実装の制限を受け得る。

### External binding

**external binding**は、OEP機能と、OEP protocol以外の外部interfaceまたは外部protocolとの関係をOEP上で明示する概念である。

external bindingでは、機能の通信の一部をUSB CDC、USB Audio等の標準interface、または独自protocolや非公開protocolで直接運べる。OEPは少なくとも、どの提供機能とどの外部経路が関係するかをhostが区別できるようにする。

OEPと外部経路のどちらが設定、開始、停止、状態、失敗およびresource管理の各責任を持つかは、external bindingごとに定義する必要がある。具体的な共通modelは未決である。

一つの提供機能がOEP native pathとexternal bindingの両方を提供することや、複数のexternal bindingを代替経路として提供することを排除しない。選択、併用および排他の表現方法は未決である。

### 未宣言の外部通信

**未宣言の外部通信**は、OEP機能の成立に必要であるにもかかわらず、OEP native pathでもexternal bindingでもなく、OEPからその依存関係を認識できないhost–probe間通信である。

OEP機能は未宣言の外部通信に依存してはならない。外部通信を使用すること自体ではなく、その必要性と関係がOEPから認識できないことを禁止する。

## 機能

### 機能定義

**機能定義**は、hostから観測できる機能の意味と振る舞いを定める概念である。

機能定義には、少なくとも次の意味が含まれ得る。

- 何を実現する機能か
- どのような操作があるか
- 操作へ与える情報と得られる結果
- 外部から観測できる状態または振る舞い
- 非対応、拒否および失敗の意味
- 実装ごとに異なってよい条件または制限

これらを一つの文書または一つのprotocol objectで表すことは、この段階では要求しない。

### 提供される機能

**提供される機能**は、probe実装が実際に利用可能にする、ある機能定義に基づく機能である。

同じ機能定義に基づく複数の提供機能が一つのprobeに存在する可能性がある。複数存在する場合にそれぞれをどのように区別するかは未決である。

提供される機能は、その実装に固有の制限、現在の状態、他機能との関係等を持つ可能性がある。機能定義が同じであることは、すべての条件や性能が同じであることを意味しない。

### 標準機能

**標準機能**は、OEP projectが共通の意味を定義し、独立したhost実装とprobe実装の相互運用対象とする機能である。

標準機能へ適合を主張する実装は、その定義に従う必要がある。どの機能を最初に標準化するかは未決である。

### 独自機能

**独自機能**は、OEP projectの標準機能として定義されていない機能である。製品固有、組織固有、実験的または非公開の機能を含む。

独自機能の意味やdata形式を、OEPの共通部分または一般的なhostが理解する必要はない。専用hostとprobeだけが理解する不透明なdataや、別protocolに由来するpacketまたはbyte列は、OEP native pathでもexternal bindingでも運べる。

独自機能の仕様公開や第三者による再実装は必須ではない。ただし、独自機能に必要なhost–probe間通信経路は、OEP native pathまたはexternal bindingとして明示しなければならない。

独自機能を理解しないhostが、別の標準機能または独自機能として誤解しないよう区別できる必要がある。具体的な識別方法とnamespaceは未決である。

## 操作と結果

**操作**は、hostがprobeの提供する機能を利用するための意味上の単位である。

操作には入力、結果、状態変化または失敗が存在し得る。すべての機能が同じ操作modelを必要とするとは限らない。短い操作、継続的なdata交換、通知等をどのようにmodel化するかは後で決める。

操作をmessage、request、command等のどの形式で表現するかは未決である。

## 制限、状態および利用可能性

### 制限

**制限**は、提供される機能が受け入れられる条件または実行可能な範囲を狭める性質である。性能上限、data量、選択できる条件、他機能との同時利用等が候補になる。

制限を静的に公開するか、利用時に判断するか、あるいは両方を使うかは未決である。

### 状態

**状態**は、提供される機能またはOEP endpointについて、時間とともに変化し得る外部から観測可能な性質である。

状態の種類、保持主体および伝達方法は未決である。

### 利用可能性

**利用可能性**は、定義上は対応している機能を、現在の構成や状態で利用できるかを表す概念である。

機能を実装していないこと、意味に互換性がないこと、条件が制限を超えること、一時的に利用できないこと、および実行中に失敗したことは区別する。

external bindingの利用可能性は、一つの主体が事前に完全には判断できない場合がある。probeはprobe側のresourceや有効化状態を判断できるが、host OS上のdriver、権限、device node、他processによる占有等は判断できない。したがって、bindingが宣言されていること、外部interfaceを特定できること、各側で既知の状態、および実際のopenや通信によって利用を確認したことを区別する。

判断できない状態は「利用可能」と推定せず、未知として扱える必要がある。具体的な状態表現は未決である。

## Identityの区別

OEPでは、少なくとも次のidentity上の問いを概念的に区別する。

| 問い | identityが表すもの |
|---|---|
| 通信相手はOEPか | OEP protocolと非互換protocolの区別 |
| どの論理的な通信相手か | OEP endpointの区別 |
| どの実装か | 実装主体、実装方式またはsoftwareの区別 |
| どの個体か | 必要な場合のdeviceまたはprobe個体の区別 |
| どの意味の機能か | 標準機能または独自機能の定義の区別 |
| どの提供機能か | 同じ定義に基づく複数の提供機能の区別 |
| どの通信経路か | OEP native path、external bindingおよびその外部interfaceの区別 |
| どの接続構成か | USB profile等、接続環境から見える構成の区別 |

それぞれに永続的なidentityが必要か、これらを同一の識別子で表すか、独立した識別子を設けるかは、この文書では決めない。ただし、一つのidentityを別の問いへの回答として誤用してはならない。

USB VID:PIDは接続候補の識別に利用できる可能性があるが、それだけで機能、適合性、真正性または個体を完全に表すものとはしない。

## OEPと非OEPの境界

OEPの必須要求を満たす実装は、使用するhardware、言語、codebaseまたはconnection interfaceにかかわらずOEP実装になり得る。

OEPの必須要求を満たさない派生protocolまたは実装は、OEP実装ではない。OEPと誤認されるprotocol identityや、将来のOEP project PIDその他の共通identityを使用しない。明示的なexternal bindingを使用することだけでは非互換にならない。

同じ物理deviceにOEP endpoint、external bindingおよびOEPから独立した別protocolを併設できる。適合するexternal bindingは、許容されたdevice profileの一部としてOEP endpointと同じUSB VID:PIDを共有し得る。独立した別protocolは、OEP endpointまたはexternal bindingと誤認されないよう区別できなければならない。

## 適合性の区別

少なくとも次の主張は、概念上別のものとして扱う。

- OEP protocolへの適合
- 特定の標準機能への適合
- 特定のconnection interfaceまたはprofileへの適合
- OEP projectの名称または共通identityを利用する資格
- 個別実装の品質、性能または安全性

一つの適合主張が、別の主張を自動的に証明するものとはしない。具体的な適合level、test、表示および管理方法は未決である。

## 概念上の不変条件

この段階までの合意から、次を不変条件とする。

1. OEP機能に必要なhost–probe間通信経路は、OEP native pathまたはexternal bindingとして明示する
2. OEP機能を未宣言の外部通信へ依存させない
3. connection interfaceが変わっても、機能の意味を別protocolとして再定義しない
4. 標準機能と独自機能は共存できる
5. 独自機能の仕様公開は必須ではない
6. 未知の機能を既知の機能として扱わない
7. OEPの必須要求を満たさない派生をOEPとして識別しない
8. OEPの共通identityへ非互換な実装を混在させない
9. 適合するexternal bindingは、外部通信を使うことだけを理由に非OEPとしない
10. 実装の由来とOEPへの適合性を混同しない

## 次に決めること

この概念モデルを確認した後、次の順に設計を具体化する。

1. OEP protocolが共通に提供すべき責任と、個別機能が持つ責任の境界
2. OEP endpointとconnection interfaceの関係
3. OEP native pathとexternal bindingに共通して必要な関係とlifecycle
4. 機能定義、提供される機能および独自機能を区別するために必要な情報
5. 操作、結果、状態および失敗に共通して必要な性質
6. 対応範囲、制限および利用可能性を判断するために必要な性質
7. protocol、機能、実装、通信経路および接続構成のidentityと互換性

これらの責任と情報を決めた後に、message model、encoding、transport bindingおよび数値registryを検討する。
