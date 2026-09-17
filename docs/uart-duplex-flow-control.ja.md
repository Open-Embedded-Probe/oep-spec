# Open Embedded Probe — UART duplexとflow control候補

状態: **UART bindingの通信方向・queue設計候補**。この文書は、DATA、ACKおよびSYNC controlが近接または同時に発生した場合の扱いと、full-duplex UARTでdeadlockを避けるための責任を整理する。

half-duplexのturnaround形式、TX queue API、priority値および明示的なBUSY frameはまだ決定しない。

## 解決する問題

stop-and-waitで一方向の未確認DATAを一つに制限しても、反対方向の通信は同時に発生し得る。

```text
host                                  probe
 | ---- DATA(request, hseq) ----------> |
 | <--- DATA(notification, pseq) ------- |
 | ---- ACK(pseq) --------------------> |
 | <--- ACK(hseq) --------------------- |
```

さらにprobeはrequestを受信した直後、requestへのACKとOEP response DATAを同じ送信方向へ並べる場合がある。

送信callbackやUART driverが一frame分しか保持できず、新しいACKで以前のDATAを上書きすると、stop-and-waitのstate machineが正しくてもwire上ではframeを失う。

## 暫定方向

通常の独立したTX/RXを持つUARTについて、初期control channelは**full-duplex動作を第一候補**とする。

- 各方向に最大一つの未確認DATAを持てる
- 自分のDATAのACK待機中も反対方向を受信・検査する
- 反対方向の正常DATAを上位へ一度だけdeliveryし、そのACKを返す
- ACKはDATA windowを消費せず、ACK自体へACKを要求しない
- local TX上では複数のcontrol/data frameを欠落なく直列化する

これはOEP coreが常に双方向へ同時にrequestを開始できるという意味ではない。最大in-flight request、notification対応およびhost polling等の上位constraintは別に適用される。

## 二つの独立したDATA state

full-duplex stop-and-waitでは、概念上、方向ごとに独立したstateを持つ。

| state | local側が保持するもの |
|---|---|
| transmit | 現在の送信sequence、未確認DATA、retry count |
| receive | 次に期待するsequence、直前DATAの重複判定 |

自分がDATAを送信してACKを待っていることを理由に、receive処理を停止しない。双方が同時にDATAを送った場合、両方がreceiveを停止すると、互いにACKを生成できずdeadlockする。

## Local TX serialization

一つのUART TX pinでは、自端が生成するframeを順に送る必要がある。少なくとも次を同時に扱える設計が必要になる。

- 既に送信中またはqueue済みのDATA
- 受信DATAに対して新しく生成したACK
- OEP coreが生成したresponse DATA
- epoch切替時のSYNC-ACK

「ACK用にもう一つ最大frame bufferを必ず持つ」ことまでは要求しない。実装は次のいずれでもよい。

- UART driver queueへ小さいACKを直接追加する
- pending ACKのsequenceだけを保持し、送信可能時にencodeする
- control frame用の小さい固定bufferを持つ
- 上位DATAをqueueへ受理する前にACK用capacityを予約する

ただし、新しく生成したACKで未送信DATAを黙って上書きしたり、callbackが受理していないのに送信済みとしてstateを進めたりしない。

### ACKとOEP responseの送信順序

request DATAをreceiver bindingが上位queueへdeliveryした後、transport ACKを先にlocal TXへ並べれば、request側の再送状態を早く終了できる。

```text
receive request DATA
        |
deliver to OEP core
        |
queue transport ACK
        |
queue OEP response DATA
```

ただし、上位へのdelivery callbackが同期的にrequestを処理する実装では、OEP response DATAが先にqueueされ、そのcallbackから戻った後にtransport ACKが続く場合がある。この順序も相互接続上は許容する候補とする。

peerは、request ACKを待っている間も反対方向のresponse DATAをdecodeし、上位へdeliveryできなければならない。responseを受けたことだけでrequestのtransport ACKを受けたとみなさず、後続ACKも通常どおり処理する。

ACKを先にqueueすることは推奨できるが、wire順序を機能結果の意味に含めない。既に物理送信中またはqueue済みのframeへACKを割り込ませる必要はなく、ACK timeoutはそのframeの残り時間とlocal queue delayを含める。

## RXの継続性

ACK待機中もdecoderを動作させ、少なくとも次を処理する。

- 自分の送信DATAに対するACK
- 反対方向の新しいDATA
- 反対方向DATAのretry
- 新しいepochを開始する有効なSYNC

OEP coreが次のmessageを処理できない場合、receiver bindingはACKを返す前にqueue capacityを確認する。ACK後に「実は保持できなかった」としてmessageを失わない。

## Flow controlの範囲

stop-and-waitはDATA frame数を一方向一つに制限するが、UART hardware bufferのoverflowを単独では防がない。

実装は少なくとも次を考慮する。

- 最大frameをbaud rateに追従してdecodeできるか
- interruptまたはpoll間隔中にRX ring bufferが溢れないか
- local TX queueへACKを追加できるか
- OEP coreへのdelivery queueを予約できるか
- bridgeやOSが複数frameをまとめて渡す場合も全byteを処理できるか

RTS/CTSを利用できる実装は使用してよいが、最小profileの必須条件にはしない。software XON/XOFFはpayload framingと干渉し得るため、bindingで明示せずに有効と仮定しない。

receiver busy時にACKを保留する候補は、短時間のbackpressureとして機能する。しかしbusyがretry windowを超える場合はtransport failureになる。長い機能処理を理由にbinding receiveを停止せず、requestをqueueへ受理した後はtransport ACKとOEP responseを分離する。

現在の実験上限では、最大32 byte DATAのwire長は39 byte、ACKは7 byteである。同じlocal TXへ最大DATAとACKが続く基本burstは46 byteで、Arduino Uno R3 coreの既定64 byte TX bufferより小さい。ただしbufferが空であること、実際のring buffer有効容量、割込み進行および別用途との共有を含まないため、64 byteあれば常に安全という仕様根拠にはしない。

## Half-duplexとの切り分け

RS-485等のhalf-duplexでは、full-duplexと同じ「双方がいつでも送る」規則を使用すると衝突し得る。

half-duplex対応を追加する場合、少なくとも次を定義する別profileまたは追加規則が必要である。

- どちらが送信権を持つか
- DATA後にACK方向へ切り替える時点
- driver enableのguard time
- host polling中以外のprobe送信可否
- 衝突またはechoの検出
- timeout計算へturnaroundを加える方法

初期full-duplex候補がhalf-duplex上でも偶然動くことを適合条件にしない。half-duplexを非対応とする実装は、そのconnection binding constraintとして区別する。

## 1 bit sequenceと順序保存

alternating-bit方式は、同じsequenceの直近retryを重複deliveryしない。しかし、sequenceは二つの正常DATAごとに再利用される。

characterization testでは次を確認した。

1. `seq=0`、そのretry、`seq=1`の順ならdeliveryは2回で、retryは抑止される
2. `seq=0`、`seq=1`の後に古い`seq=0`を人工的に並べ替えて与えると、三つ目は新しいDATAとして受理される

したがって1 bit sequenceを採用する最小案は、各方向のbyte streamが送信順序を保存し、古い完全frameを後続frameの後へ並べ替えないことに依存する。

通常の一対一UART streamと、その上に透過的に載るUSB-UART byte streamではこの前提を置ける。次を許すbindingでは1 bit sequenceをそのまま使用しない。

- datagramの並べ替え
- 複数送信元のframe混在
- reconnect前のframeが新しいSYNC後へ移動するqueue
- application relayによる任意の蓄積・再送

その場合は、より広いsequence、DATAごとのepoch識別または下位transportに適した重複抑止が必要になる。

## 比較実装による中間結果

host-arduino-core上の比較実装で次を確認した。

- hostとprobeが同時に一つずつDATAを未確認状態にできる
- 一方のlocal TX queueで既存DATAの後へACKを追加できる
- 双方が相手のDATAを一度ずつdeliveryする
- ACK交換後に双方の送信待機が終了する
- 同期的に生成されたOEP response DATAがrequest ACKより先でも双方が完了する
- partial frame timeout後の残りbyteをdeliveryせず、retryで回復する
- 順序を人工的に崩した古いframeに対する1 bit sequenceの限界

テスト用queueは最大frame四つ分としており、これはbinding仕様の要求量ではない。同時最大DATAの試験で観測したlocal queue high-water markは46 byte以下だった。必要なqueue量と送信方法は実装方式ごとに決める。

partial frame abortを測定対象へ加えたATmega328P用ELFはFlash 2,816 byte / static RAM 156 byteだった。直前のepoch同期実装からFlash 52 byte増加し、static RAMは増加しなかった。

## 暫定合意候補

- 初期UART control channelはfull-duplexを第一候補とする
- 各方向に独立して最大一つの未確認DATAを許容する
- ACK待機中も反対方向の受信とACK生成を継続する
- local TXはDATA、ACKおよびSYNC controlを欠落なく直列化する
- transport ACKとOEP response DATAのwire順序へ機能上の意味を持たせない
- ACK待機中に先行してresponse DATAを受けても処理を継続する
- 1 bit sequenceを使用する場合は方向ごとの送信順序保存を必須前提とする
- half-duplexはturnaroundと送信権を定義する別profile候補として扱う

## 次の検証

実UARTまたはUSB-UART bridgeで次を測定する。

- 双方が同時送信した場合のRX/TX overflow
- DATA送信中に生成したACKのqueue delay
- Arduino既定64 byte TX/RX ring bufferでの最大frame処理
- main loopを遅延させた場合のfailure threshold
- port open/reset付近で古いbyteがSYNC境界を越えるか

## この文書で決めないこと

- UART driver APIとqueue実装
- ACKの厳密なpriority
- full-duplex profileの最大連続送信byte数
- hardware flow controlのnegotiation
- BUSYまたはNAK frame
- half-duplexのmedia access方式
