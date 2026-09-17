# Open Embedded Probe — UART timeoutと回復model候補

状態: **UART bindingのtiming設計候補**。この文書は、UART control channelのtimeoutを、baud rate、frame長、queueおよび処理遅延から扱うための基準と、timeout後の回復境界を整理する。

既定baud rate、具体的なmillisecond値、retry回数およびbackoffはまだ決定しない。

## 基本方針

UART bindingのtimeoutを、すべての環境で共通な一つの固定時間として定義しない。

同じframeでも、115200 baudと9600 baudではwire時間が12倍異なる。さらにUSB-UART bridge、OS scheduling、driver queue、receiverのmain loopおよびhalf-duplex方向切替が加わる。

一方、実装ごとに無制限なtimeoutを許すと相互接続時のfailure判定が成立しない。このため、仕様では次を分けて扱う候補とする。

- timeoutの起点と対象
- baud rateと最大frame長から求めるwire時間
- binding profileが保証または要求する処理時間の上限
- 実装・接続環境が加えるmargin
- retry上限後の状態遷移

## 区別するtimer

少なくとも次のtimerを同じものとして扱わない。

| timer | 対象 | 主な結果 |
|---|---|---|
| frame assembly timeout | delimiter前で止まったpartial frame | partial frameを破棄して再同期 |
| transport ACK timeout | 送信済みDATAに対するACK | 同じframeをretry、上限後はtransport failure |
| SYNC timeout | SYNCに対する同じtokenのSYNC-ACK | 同じSYNCをretry、上限後はepoch未成立 |
| OEP response timeout | transport ACK後のOEP response | request結果不明またはOEP recovery |
| activity deadline | 長時間操作の進行・完了 | 個別機能またはactivity semanticsで処理 |

最初の三つがUART bindingの責任である。OEP responseとactivityのtimeoutを短いtransport ACK timeoutで代用しない。

## Wire時間

一文字当たりのbit数を次で求める。

```text
bits_per_character = start bit + data bits + parity bit + stop bits
```

frameの最小wire時間は次になる。

```text
wire_time(frame) = wire_bytes(frame) * bits_per_character / baud_rate
```

一般的な8-N-1では一文字10 bitである。この値は物理的な下限であり、そのままtimeout値にはならない。

## ACK timeoutの構成

ACK timeoutは概念上、少なくとも次を覆う。

```text
local transmit queue delay
+ DATA wire time
+ receiver scheduling and frame validation
+ receiver queue reservation
+ direction turnaround, if any
+ ACK transmit queue delay
+ ACK wire time
+ local receive scheduling
+ safety margin
```

timerをDATAの最後のbyteが物理的に送信された後に開始できる実装では、local transmit queueとDATA wire時間を待機値から除ける。APIが「送信queueへ受理された」ことしか示さない場合は除けない。

したがってbinding実装またはprofileは、ACK timerをどのeventから開始するか明確にする必要がある。

### Receiver busy

receiverがOEP coreへ安全にdeliveryできない場合、実験候補ではACKを返さない。senderから見ると破損やACK喪失と同じくtimeoutになる。

一時的なbusyを正常に回復させるには、次のいずれかが必要になる。

- ACK timeoutとretry window内にreceiverが受理可能になる
- binding-levelの明示的なBUSY応答を追加する
- 受信queueを事前に確保する

最小候補では明示的なBUSYをまだ要求しない。ただし、receiverが無期限にACKを保留してよいことにはしない。

## SYNC timeout

SYNC timeoutの基本式はDATA/ACKと同じだが、SYNC成立前には相手のcapabilityを取得できない。

そのため最初のSYNCには、少なくとも次のいずれかが必要である。

- UART binding profileが定める保守的なbootstrap timeout
- 利用者または接続設定が与えるtimeout
- 既知のboard/profileに対するhost側設定

SYNC後に測定したround-trip timeを後続timeoutの参考にできるが、最初の同期をその測定へ依存させない。

port openがDTR等によってprobeをresetする場合、boot時間は一回のSYNC round tripとは別に扱う。hostは、短いSYNC retryを複数回行う起動猶予期間または、board profileで定めたready待機を使用できる。

## Frame assembly timeout

delimiterまで受信した正常frameは、宣言lengthとCRCを検査して処理する。delimiterが来ないpartial frameを永久に保持しないため、frame assembly timeoutを設ける候補とする。

timeout時は次を行う。

1. partial frameをOEP coreへ渡さない
2. decoderを次の同期点まで破棄状態にするか、明示的に初期化する
3. 受信済みDATAとしてACKしない
4. active epochを直ちに終了するかはerror thresholdに従う

一回のpartial frame timeoutだけでOEP request failureを生成しない。送信側はACKを得られず、同じtransport frameをretryできる。

inter-byte gapはUSB-UART bridgeやOSによって大きく変動し得るため、数文字分だけの極端に短い値を共通仕様にしない。

## Retryとfailure

DATAまたはSYNCのretryでは、同じframe内容、transport sequenceまたはepoch tokenを使用する。

retry中に新しいOEP requestを同じ方向へ先行送信しない。後から生成されたrequestで失われたrequestを置き換えない。

retry上限へ達した場合:

- 未確認frameを破棄する
- connection epochを`failed`として扱う
- 上位へtransport failureを通知する
- bindingがOEP requestを自動再実行しない
- 次に通信するには新しいepoch同期を行う

自動的に新しいepochを開始するか、利用者・上位層の判断を待つかはhost実装方針にできる。ただし、新しいepoch上で以前のOEP requestを暗黙に再送しない。

retry間隔を固定、線形または指数backoffのどれにするかは未決である。point-to-point UARTではnetwork congestionより、baud rate、receiver schedulingまたはreset待ちが主因になるため、一般的なnetwork用backoffをそのまま要求しない。

## OEP response timeoutとの境界

transport ACKを受け取った時点で確定するのは、receiver bindingがlogical messageを上位へ一度だけdeliveryできたことまでである。

```text
DATA送信
   |
   +-- ACK timeout ---------- binding-level retry
   |
ACK受信
   |
   +-- OEP response timeout - request semantics / recovery
```

ACK後にresponseが来ない場合、同じtransport DATAを再送しない。receiverは重複DATAとして抑止できるが、transport retry windowは既に完了しているためである。

OEP response timeout後に同じ機能requestを新しいcorrelationで再実行できるかは、その操作がidempotentか、activityを照会できるか、または明示的な再試行規則を持つかによって決まる。

## 現在の実験frameによる下限値

次は非規定の比較実装で使う8-N-1のline timeだけを計算した値である。queue、処理、turnaroundおよびmarginを含まない。

| frame | wire bytes | 115200 baud | 9600 baud |
|---|---:|---:|---:|
| ACK | 7 | 約0.61 ms | 約7.29 ms |
| SYNC / SYNC-ACK | 11 | 約0.95 ms | 約11.46 ms |
| bootstrap request DATA | 17 | 約1.48 ms | 約17.71 ms |
| bootstrap response DATA | 21 | 約1.82 ms | 約21.88 ms |
| 最大32 byte DATA | 39 | 約3.39 ms | 約40.63 ms |

line timeだけの往復下限は次になる。

- SYNC + SYNC-ACK: 115200 baudで約1.91 ms、9600 baudで約22.92 ms
- 最大DATA + ACK: 115200 baudで約3.99 ms、9600 baudで約47.92 ms
- bootstrap request/responseと各ACK: 115200 baudで約4.51 ms、9600 baudで約54.17 ms

これらを丸めただけの値をtimeout既定値にしない。特にhost OSとUSB-UART bridgeを経由する場合、software delayがline timeより大きくなり得る。

## 設定と開示

hostは少なくともbaud rate、line setting、最大frame長およびtimer起点を知ってtimeoutを計算する必要がある。

probe固有の処理猶予がbootstrap既定値を超える場合、それをSYNC後のconstraintとして開示する方法を検討する。ただし、その情報を取得するSYNCと最初のOEP confirmation自体はbootstrap既定値内で応答できなければならない。

実装が安全のため長いtimeoutを選ぶことは許容できるが、それによってprotocol上の応答成功を偽装してはならない。timeoutはfailure検出速度の違いであり、機能結果の意味を変えない。

## 暫定合意候補

- frame assembly、transport ACK、SYNC、OEP responseおよびactivityのtimerを区別する
- UART bindingのACK/SYNC timeoutはbaud rateとwire長を入力に含める
- timerの開始eventをbinding実装またはprofileで明確にする
- line timeだけをtimeout値として使用しない
- transport retryでは同じsequenceまたはtokenを維持する
- retry上限後はtransport failureとし、以前のOEP requestを自動再実行しない
- ACK受信後はtransport retryを終了し、response待機をOEP semanticsへ移す
- port openに伴うboot待ちは一回のSYNC round tripと分ける

## 次の検証

host側とprobe側の送受信eventへtimestampを記録し、実UART/USB-UART bridgeで次を測る。

- frameをqueueへ渡してから最後のbyteが送信されるまで
- DATA終端からACK先頭・終端まで
- SYNC終端からSYNC-ACK終端まで
- main loop負荷によるreceiver schedulingの最大遅延
- port openから最初の有効SYNC-ACKまで
- 9600、115200および候補baud rateでの分布

平均値だけでなく、最大値または十分なpercentileと外れ値の原因を記録する。

## この文書で決めないこと

- 既定baud rateとline setting
- timerの具体的なmillisecond値
- retry回数とbackoff algorithm
- 明示的なBUSYまたはNAK frameの追加
- baud rate自動検出またはfallback
- OEP機能ごとのresponse timeout
