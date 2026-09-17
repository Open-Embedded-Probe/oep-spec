# Open Embedded Probe — Connection binding設計入力

状態: **検討中の下位protocol設計入力**。この文書は、OEP共通protocolをHID、UART、USB CDC、USB vendor interfaceおよびIP network上で成立させるために、connection bindingが扱う性質と初期検証対象を整理する。

ここでは個別bindingのframing、USB descriptor、HID report、baud rate、network transportまたはwire encodingをまだ決定しない。各接続方法をすべてのprobeへ実装することも要求しない。

## 目的

OEPの論理message modelを先に固定すると、実際の接続環境で運べない、または小さなprobeへ過大なbufferと状態管理を要求する可能性がある。

そのため、性質の異なる接続方法で具体的な転送を検証し、次を分離して設計する。

- OEP共通protocolが持つ論理message
- connection bindingが運ぶframeまたはfragment
- 下位interfaceが一度に転送する単位
- 個別機能が交換するdata unitまたはchunk

## 初期検証に使用する接続系統

### 制約の大きいHID

CH32V003のsoftware USB実装で使用できるHIDを、最小connection bindingの基準候補とする。

初期調査では少なくとも次を実装事実として確認する。

- control transfer、interrupt reportまたは両方のどれを使用できるか
- IN、OUTおよびhost pollingの実際の方向と順序
- reportおよびUSB転送単位の上限
- firmwareが使用できるRAM、buffer数および同時転送数
- reportを越える論理messageの分割可否
- timeout、STALL、切断および再列挙をhostからどう観測できるか

HIDを低速または補助的な経路として後付けせず、この制約内でendpoint確認と最小control interactionが成立することを初期設計の検証条件にする。

### Byte stream

UART、OEP用USB CDCおよびTCP等は、OEPから連続したbyte列として扱える可能性がある。

共通のstream framingを利用できるか検討するが、各interfaceの保証は同じではない。

- UARTは破損、欠落、byte挿入、overrunおよび接続設定の不一致が起こり得る
- USB CDCはUSB転送の境界をOEP message境界として利用できるとは限らない
- TCPは順序付きbyte streamを提供するが、OEP message境界、接続相手のidentityおよびrequestの完了までは保証しない

OEP用CDCと、target UARTを公開するexternal binding用CDCは、同じUSB classであっても役割を識別できなければならない。

### USB vendor interface

USB vendor interfaceを、高throughputおよび大きな転送を検証する基準候補とする。

USB packet、transferおよびhost APIのread/write境界を、そのままOEP message境界と仮定しない。複数転送の並行投入、大きなbuffer、方向ごとのthroughputおよびOS driver要件はbindingまたはUSB profileで扱う。

vendor interfaceが利用できない権限またはdriver環境でも、HID、CDC、UARTまたはnetwork等の別bindingを実装できることをOEP共通protocolは妨げない。

### IP network

IP networkを、物理deviceへ直接接続しない環境と複数の接続候補を検証する対象に含める。

TCP等のbyte stream transportを使用する場合、stream framingの一部をUARTやCDCと共有できる可能性がある。ただし、次はnetwork binding固有の事項として扱う。

- addressとportその他の接続先情報
- 利用者指定、設定、service discovery等による接続先情報の取得
- 接続、切断、keepaliveおよび再接続
- 複数clientとresource競合
- 認証、認可、機密性および完全性
- routing、MTUおよび中間networkによる制約

TCP、UDP、WebSocketその他のどれを標準network binding候補にするかは未決である。

## Connection bindingが明示する性質

各connection bindingは、必要に応じて次を定義または明示する。

| 性質 | 確認する内容 |
|---|---|
| 転送model | byte stream、report、datagram、transactionその他のどれか |
| 方向 | hostからprobe、probeからhost、双方向、host pollingの要否 |
| 境界 | 下位転送単位、binding frameおよび論理message境界の関係 |
| 順序 | 同一方向および双方向interactionで保証される順序 |
| 完全性 | 破損、欠落、重複および挿入をどこまで検出できるか |
| 回復 | 再送、再同期、切断、再接続および回復不能条件 |
| flow control | buffer超過を防ぐ方法とbackpressureの有無 |
| 長さ制限 | 各転送単位、frame、fragment、messageおよびdata chunkの上限 |
| lifecycle | open、close、reset、再列挙および接続喪失の意味 |
| 発見と指定 | 接続先情報の表現と、存在する場合の列挙または発見方法 |
| 性能 | 設定速度、実効throughput、latency、poll間隔および方向差 |
| 実装制約 | 必要buffer、同時転送数、driver、権限およびOS依存性 |

すべてをruntimeにprotocol上で報告することは要求しない。binding仕様として固定される性質、probeが開示する実装制限、host環境でのみ判明する状態を区別する。

## 長さの区別

「packet長」または「最大長」を一つの値として扱わない。少なくとも次を区別する。

### 下位転送単位

USB packet、HID report、UART driverへのread/write、network segment等、下位interfaceまたはAPIが扱う単位。

下位転送単位の境界がhostとprobeの双方へ同じ形で見えるとは限らない。

### Binding frameまたはfragment

connection bindingが、OEPのdataを運び、破損検出または再同期を行うために区切る単位。

一つのframeが複数の下位転送へ分割される場合や、一つの下位転送へ複数frameが入る場合を許容し得る。

### OEP logical message

OEP共通protocolが一つのrequest、response、notification、data transfer等として扱う論理単位。

一つのlogical messageを複数fragmentで運べるか、全体長を事前に示すか、受信側がmessage全体をbufferする必要があるかは今後決める。

### Function data chunk

個別機能が一まとまりとして生成または消費するdata単位。logical message一つと同じとは限らない。

各上限は、固定値、binding profile、probeの実装制限または現在のconfigurationによって決まり得る。hostは、一つの上限を別の層へ無条件に適用しない。

## UARTで必要になる性質

UART bindingは、byte値の破損だけでなく、欠落または挿入によって以後のframe境界を失う可能性を扱う。

### 破損検出

UART hardwareのparity、framing errorおよびoverrunだけで、OEP frame全体の完全性が保証されるとは限らない。binding内でchecksum、CRCその他の検出を追加するかは今後決めるが、破損した内容を正常なOEP requestとして実行する可能性を許容しない。

### 再同期

破損した長さ情報やbyte欠落後も、無期限に誤った境界として解釈し続けない方法が必要になる。delimiter、escape、magic、length、検査値その他の具体的方式は未決である。

再同期方法は、payload内に任意のbyte列を運べること、誤検出時の最大廃棄量、および小さなprobeでのparser実装を考慮する。

### 再送と重複

UART bindingがframe-levelの到達確認と再送を行う場合、その再送を上位から一回のlogical messageとして観測できなければならない。同じrequestを重複して機能操作へ渡す可能性を残す場合は、その保証を明示し、OEP共通protocol側の重複処理と組み合わせる必要がある。

再送を必須にするか、破損を検出してconnection failureとして上位へ返すだけにするかは未決である。

### 速度とflow control

UARTについて、単一の「対応速度」だけを能力として扱わない。必要に応じて次を区別する。

- 接続開始時のbaud rateおよびその他のline setting
- probeとhost adapterが対応する設定値
- 安定して通信できる設定範囲
- framingとacknowledgementを含む実効throughput
- hostからprobeとprobeからhostの方向差
- buffer容量、処理停止時間およびoverrun条件
- hardware flow controlまたはsoftware flow controlの有無

接続後にbaud rateを変更できるようにするか、切替の合意と失敗時の復帰をどうするかはUART binding設計で決める。

## 制約の情報源

接続に関する制約は、少なくとも次の情報源に分かれる。

- **binding定義** — 方式として固定される保証と上限
- **probe実装** — buffer、対応速度、最大frame、同時転送数等
- **host実装またはOS** — driver、権限、API、開けるinterface等
- **現在の接続** — 実際の設定、観測したerror、測定throughput、接続状態等

probeが開示できないhost側状態を、probeのcapabilityとして表さない。測定した性能値を、条件を示さず永続的な保証として扱わない。

## 最初の検証sequence

wire encodingを固定する前に、各候補bindingで次の同じ論理sequenceを運べるか確認する。

1. 接続先をopenまたは選択する
2. OEP endpoint確認requestを送る
3. protocol identityと互換性情報を受け取る
4. 提供機能の最小一覧を取得する
5. 未対応または不正なrequestへの拒否を受け取る
6. 小さい同期操作を実行し、result dataを受け取る
7. 応答の一部、frameまたは接続が失われた場合の観測結果を確認する

HIDではreportまたはcontrol transfer、UARTでは実際のframe byte列、CDCとTCPでは任意位置で分割されたbyte stream、vendor interfaceでは異なるtransfer sizeを使用して同じ論理sequenceを検証する。

この検証によって、論理message modelのうち実際に必要なscope、correlation、length、fragmentationおよびfailure情報を逆算する。

## この文書で決めないこと

- 最初に標準化するconnection binding
- HID report descriptor、report IDおよびcontrol request
- UART framing、checksum、CRC、acknowledgementおよび既定baud rate
- CDCのUSB profileとinterface識別
- vendor interfaceのendpoint構成とdriver方式
- TCP、UDP、WebSocketその他のnetwork transport選択
- logical messageのencodingと最大長
- fragmentation、再構成およびstreaming parserの具体的方式
- 性能classまたは必須throughput

次段階では、CH32V003のsoftware USB HID実装が実際に提供する転送方式、上限およびbuffer条件を確認し、それとUART framingに共通化できる最小転送modelを比較する。
