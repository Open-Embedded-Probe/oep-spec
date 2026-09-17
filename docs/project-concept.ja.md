# Open Embedded Probe — プロジェクトの目的と範囲

[English](project-concept.md)

状態: **最上流のproject定義案**。project名、相互運用を中心とする目的、機能に必要な通信経路をOEP native pathまたは明示的なexternal bindingとして扱う原則、および非互換な派生をOEPとして識別しない原則は合意済みである。その他の文言と範囲は引き続き検討中であり、protocolの構造や技術的な解決方法は規定しない。

## 背景

組み込み開発では、hostとtargetの間で、debug、書込み、通信、信号制御、観測、計測などの機能を提供するさまざまなprobeが使われる。

これらの機能の意味や利用方法は、製品、hardware、firmware、接続方法、host applicationごとに個別設計されることが多い。その結果、機能が似ていても、probeとhost applicationの組合せごとに専用の対応が必要になる。

この分断には、次のような問題がある。

- probeの新しい実装や機能を追加するたびに、host側にも個別対応が必要になる
- host applicationが、特定の製品、board、firmwareまたは接続方法に依存しやすい
- 同じ意味の機能が、互換性のない方法で繰り返し実装される
- 一つのprobeが複数の機能を提供する場合、それらを一貫して公開し利用するための共通の約束がない
- 実装固有の機能を追加しながら、共通機能との相互運用を維持することが難しい
- USBを利用する場合、機能やapplicationを増やすたびに個別のdevice identityを用意する設計になりやすい
- USB以外の接続方法で同じ機能を利用する場合、別の仕組みとして設計し直すことになりやすい

USB device identityに関する課題は、この問題が表面化する具体例の一つである。USBまたは共通PIDの利用自体をprojectの目的とはしない。

## 目的

Open Embedded Probeは、組み込み開発用probeが提供する機能を共通の意味で公開し、異なるprobe実装とhost softwareの間で相互利用できるようにするための仕様を提供する。

個々の製品や接続方法に閉じた専用連携を減らし、probeの提供者とhost softwareの提供者が、互いの特定の実装を事前に知っていなくても、共通に理解する機能を利用できる状態を目指す。

## OEPにおける相互運用

OEPにおける相互運用は、特定のprobeと特定のhost applicationを個別に接続できることだけを意味しない。

probe側とhost側が共通仕様をそれぞれ実装することにより、特定の組合せ専用の取り決めを追加しなくても、双方が理解する機能を利用できる状態を指す。

その状態では、概念上、次のことが可能である。

- probeが、自身の提供する機能をhostへ公開できる
- hostが、利用可能な機能とその意味を理解できる
- hostが機能を利用し、probeが結果や状態を共通の意味で伝えられる
- 機能、実装、構成による差異や制限を扱える
- 一方が理解しない機能が存在しても、双方が理解する機能は利用できる
- 新しい機能や実装固有の機能を追加しても、既存機能の相互運用を維持できる
- 一つのprobeが複数の機能を一貫した形で提供できる
- 異なるhardware、firmwareまたは接続方法から、同じ意味の機能を提供できる
- 独自機能とその専用hostを作る場合も、必要なやり取りをOEPの範囲内で表現できる

これらは必要な性質を示すものであり、機能の公開、識別、選択、操作をどの技術で実現するかは定めない。

### OEPが管理する通信経路

OEPは、標準化された機能だけに利用を限定しない。独自機能、実験的な機能、その機能に特化したhostまたはprobeも実装できるようにする。

OEP機能は、必要なhost–probe間通信を次のいずれかの経路として扱う。

- **OEP native path** — 操作、data、状態、結果および失敗をOEP protocolで運ぶ
- **external binding** — OEP機能と外部interfaceまたは外部protocolの関係をOEP上で明示し、通信の一部をその外部経路で運ぶ

external bindingでは、OEPでrouting、変換、利用条件等を設定し、実dataをUSB CDC、USB Audioその他の標準interfaceで直接運べる。独自protocolまたは非公開protocolもexternal bindingに使用できる。

機能に必要な通信経路は、OEP native pathまたはexternal bindingとして明示されなければならない。OEPから認識できない未宣言の外部通信へ暗黙に依存してはならない。

USB、UART、network等のconnection interfaceが異なる場合も、その上でOEP protocolによる通信を行う。connection interfaceはOEP自体を運ぶ経路であり、external bindingは個別機能の通信を外部interfaceまたはprotocolへ結び付ける関係である。この二つを区別する。

独自機能の意味やdata形式は、OEPの共通部分や一般的なhostが理解できないものであってもよい。その機能に対応する専用hostとprobeは、独自に合意した意味やdataをOEP native pathまたは明示的なexternal bindingで交換できる。独自機能の仕様公開は必須としない。

独自機能であること、仕様が非公開であること、data内部に別protocolの表現を使うこと、または独自protocolをexternal bindingとして使うことは許容する。ただし、一般的なhostが利用できる標準的な経路と誤認されないよう区別する。この原則は、独自機能やexternal bindingの識別方法、拡張形式またはdata表現をこの段階で決めるものではない。

次の通信は、それ自体が未宣言の外部通信を意味しない。

- OEPを運ぶUSB、UART、network等の下位通信
- USB列挙等、OEPによる通信を開始できる状態にするための接続固有の手続き
- probeとtargetの間で使われるSWD、JTAG、UART等の通信
- OEP機能へ明示的に結び付けられたexternal binding
- OEP機能から独立した別機能または別protocolの併設

外部interfaceまたは別protocolをOEP機能に必要な経路として使用する場合は、独立した併設ではなくexternal bindingとして明示する。

### 非互換な派生との区別

OEPのsource codeまたは仕様を変更、forkまたは移植すること自体は、その実装をOEPでなくするものではない。異なるhardware、softwareまたは接続interfaceへの移植であっても、OEPの要求を満たすならOEP実装として相互運用できる。

一方、OEP機能を未宣言の外部通信へ依存させる、標準機能へ異なる意味を与える等、OEPの必須要求を満たさない変更は、OEPから派生した別protocolとして扱う。その実装はOEPへの適合または互換性を主張してはならず、OEP protocolと誤認されるprotocol名またはprotocol identityを使用してはならない。明示的なexternal bindingを使用することだけでは、非互換な派生にならない。

将来OEP projectへUSB VID:PIDその他の共通identityが割り当てられた場合、非互換な派生はそれを使用できない。独自のidentityを使用し、OEP実装と機械的に区別できなければならない。

同じ物理deviceへOEP endpoint、external bindingおよびOEPから独立した別機能を併設できる。external bindingは、登録済みまたは許容されたprofileの一部として、OEP endpointと一つのUSB VID:PIDを共有し得る。OEPから独立した別protocolは、hostがOEP endpoint、OEP機能またはそのexternal bindingと誤認しないよう区別できなければならない。具体的なprotocol identity、USB PID、interface、profileおよびcomposite deviceの規則は後で定義する。

softwareや仕様文書のlicenseに基づいてforkする権利と、OEPへの適合を主張する権利、OEPの名称を互換性表示に用いる条件、およびproject identityを利用する権利は別の問題として扱う。

## 対象となる関係

OEPが対象とする中心的な関係は、次の二者間の相互運用である。

- **probe側** — 組み込みtargetに対する開発支援機能を提供するhardwareまたはsoftware
- **host側** — probeが提供する機能を利用するsoftware

複数のprobe実装と複数のhost実装が、一対一の専用統合なしに接続できることを目指す。

「probe」および「組み込み開発用機能」に含める正確な範囲は、今後の要求定義で明確にする。UART、GPIO、SWD、JTAG、logic captureなどは出発点となった候補であり、この文書では採用、分類または必須化を決定しない。

## Projectの範囲

OEPは、probeが提供する機能について、probe側とhost側が相互運用するために必要な共通仕様を対象とする。

この範囲には、将来的に次の事項が含まれ得るが、この文書では内容や実現方法を決定しない。

- 機能と操作の共通の意味
- 提供される機能とその制約の表現
- probeとhostの間のやり取り
- 異なる実装間の互換性と拡張性
- 相互運用を確認するための要件
- 各種の接続環境でOEPを利用するための規則

## 非目標

OEPは、少なくとも次のこと自体を目的としない。

- 一種類の万能probeまたは単一の製品を作ること
- すべてのprobeに同じ機能集合を要求すること
- 特定のMCU、board、firmware framework、OSまたはprogramming languageを標準とすること
- 特定の接続方法だけを前提とすること
- 既存のdebug、programming、measurementの仕組みをすべて置き換えること
- OEP機能を、OEPから認識できない未宣言の外部通信へ依存させること
- device identityだけで機能、品質、適合性、真正性または安全性を保証すること
- 一つのreference implementationを仕様そのものとすること

## 成功した状態

Projectの中心的な成功条件は、次の状態を実証できることである。

> 独立して作られた複数のprobe実装と複数のhost実装が、個々の組合せ専用の取り決めを追加することなく、共通に定義された機能を相互利用できる。

加えて、新しい機能や実装上の差異を導入しても、共有する機能の相互運用を維持できることを目指す。

性能、対応機能数、特定の接続方法、特定のhardwareへの対応は、それだけではproject全体の成功条件としない。

## この文書で決めないこと

次の事項は、この目的と範囲に合意した後で要求を整理し、段階的に検討する。

- 機能の分類と、最初に標準化する機能
- protocolの構造、message modelおよびwire encoding
- 機能、実装、device等の識別方法
- 接続、発見および通信の方法
- versioning、拡張、互換性およびlifecycleの規則
- 適合性の定義と検証方法
- USB profile、VID/PIDおよびproject identityの運用
- repository、実装およびgovernanceの構成

これらの候補に関する既存の記述や調査結果は、決定事項ではなく、今後の設計で評価する入力として扱う。
