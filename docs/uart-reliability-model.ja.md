# Open Embedded Probe — UART bindingの信頼性model候補

状態: **初期UART connection bindingの検討方針**。この文書は、UART上で破損、欠落、重複および再同期を扱い、OEP共通protocolへ完全なlogical messageまたはtransport failureを渡すための最小信頼性modelを整理する。

framing、CRC、delimiter、timeout、baud rateおよびfield値はまだ決定しない。

## 暫定方向

初期UART bindingのcontrol channelには、次を持つ**一度に一frameのstop-and-wait方式**を第一候補とする。

- frame境界と再同期
- frame全体の破損検出
- transport sequence
- acknowledgement
- timeoutと同一frameの再送
- receiverでの重複delivery抑止
- retry上限後のtransport failure

CRCで破損を検出して破棄するだけの方式は、実装比較用の最小候補として残す。ただし、UART上の一時的な欠落をすべてOEP request timeoutへ持ち上げるため、異なるbindingから共通protocolが受ける性質を揃えにくい。

stop-and-waitを採用しても、OEP操作のexactly-once、切断を越えた再送、activity recoveryまたは永続sessionを保証しない。

## 提供する抽象的な保証

一つの有効なUART connection context内で、bindingはOEP共通protocolへ次を提供することを目指す。

1. CRCその他の検査を通過した完全なframeだけを渡す
2. 同じtransport sequenceの再送を、一つのlogical messageとして一度だけ渡す
3. 正常に受理したframeを送信側へacknowledgeする
4. 一時的な破損またはacknowledgement喪失をbinding内で再試行する
5. 上限回数または接続条件を超えて回復できない場合、transport failureを示す
6. frame順序を維持する

この保証は、送信側がmessageをbindingへ渡してから、受信側bindingがOEP coreへ一度だけdeliveryするまでを対象とする。

次は保証しない。

- OEP coreがrequestを受理したこと
- 機能操作を開始または完了したこと
- responseが返ること
- 接続喪失直前の操作状態を確定できること
- probe reset後も以前のtransport sequenceを覚えていること

## Transport ACKとOEP response

transport acknowledgementとOEP responseは異なる。

```text
host binding              probe binding             OEP core
     | ---- DATA(seq) --------> |                        |
     |                          | -- logical message --> |
     | <--- ACK(seq) ---------- |                        |
     |                          |                        | process
     | <--- DATA(response) -----| <--- OEP response ---- |
     | ---- ACK(response) ----> |                        |
```

`ACK(seq)`は、receiver bindingがframeを検証し、同じframeを重複させずOEP coreへ渡せる状態になったことだけを示す。

ACKを、requestの`accepted`、`completed`、成功またはfailureとして扱わない。OEP responseが遅い操作でもtransport ACKは先に返せる。

## Receiverの動作候補

### 新しい正常frame

1. frame境界を復元する
2. 宣言lengthと実際の長さを検査する
3. CRCその他の完全性検査を行う
4. 期待するtransport sequenceか確認する
5. OEP coreへ一度だけdeliveryできる状態を確保する
6. frameをdeliveryし、ACKを返す
7. 次のsequenceを期待する

ACKを返した後で、同じframeを「受信していなかった」状態へ戻さない。OEP coreへ渡すqueueやbufferを確保できない場合は、受理したACKを先に返さない。

### 同じsequenceの再送

ACK喪失等によって直前と同じsequenceのframeを再受信した場合、OEP coreへ再deliveryせず、同じACKを返す。

これによってbinding内の再送が機能操作の重複実行にならないようにする。

### 破損frame

length不整合、decode failureまたはCRC failureを検出したframeはOEP coreへ渡さない。

sequence自体を信頼できない場合は、そのframeへACKを返さず、次のdelimiterまたは同期点まで破棄する。明示的なNAKを設けるかは未決である。

### 処理不能な長さ

宣言lengthがbindingの受信上限を超える場合、frame全体をbufferしない。次の同期点まで安全に破棄し、送信側が上限超過またはtimeoutを判断できる方法を定義する。

OEP messageとして意味が不正である場合は、UART binding failureではない。正常frameとしてOEP coreへ渡し、coreがcorrelationを保ったrejected responseを返せる。

## Senderの動作候補

1. 一つのlogical messageをframe化する
2. 現在のtransport sequenceを付ける
3. ACKを受け取るまで、そのframeを再送可能な状態で保持する
4. frameを送信し、ACK timeoutを開始する
5. 正しいsequenceのACKを受けたらframeを破棄し、次のsequenceへ進む
6. timeout時は同じframeとsequenceを再送する
7. retry上限へ達したらconnection contextをtransport failureとする

ACK待機中に次のDATA frameを送らない。反対方向のDATAとACKを扱えるか、完全なhalf-duplex順序へ限定するかは今後決める。

## Transport sequence

一度に一frameだけを未確認にする場合、alternating-bit相当の小さいsequence空間でも重複抑止は可能である。

ただし、次を検討せずに1 bitで十分とは決めない。

- 遅延した古いframeが残る時間
- hostまたはprobeだけがresetした場合
- UART bridgeやOS bufferに残るdata
- connection contextの開始を双方が認識する方法
- 双方向に独立したsequenceを持つか

sequenceの幅は、message correlationやactivity referenceの幅とは別に決める。

## Connection epochと同期

UARTにはTCP connectやUSB enumerationに相当する明確な開始がない場合がある。hostとprobeのtransport sequence状態を合わせるため、binding-levelの同期が必要になる可能性が高い。

初期候補では、host主導の同期exchangeによって新しい**connection epoch**を開始する。

```text
host                         probe
  | ---- binding SYNC -------> |
  | <--- binding SYNC-ACK ---- |
  |                             |
  | ---- OEP confirmation ----> |
```

SYNCはOEP endpoint確認ではない。UART bindingとしてframeを交換でき、sequence状態を開始できることだけを確認する。

SYNCでは、必要に応じて次を扱う。

- 古いpartial frameの破棄
- 各方向の初期sequence
- hostが選んだepoch tokenのecho
- binding revision
- bootstrap frameを運べる最小payload上限

epoch tokenは認証情報ではない。reset前の遅延frameを新しいconnectionへ誤適用しないための値である。具体的な振る舞い候補は[UART connection epoch同期候補](uart-connection-epoch.ja.md)に示す。幅と生成方法は未決である。

### Reset後の扱い

probe reset、host port再open、baud変更失敗または連続したframe errorを検出した場合、以前のsequence状態を継続できると仮定しない。bindingを再同期し、その後OEP endpoint確認をやり直す。

DTR等によってprobeがresetされるboardでは、port open直後に古いconnection contextが存続していると扱わない。

## Bufferへの影響

stop-and-wait senderは、少なくともACKを得るまで一frameを再送可能な形で保持する必要がある。

receiverは、少なくとも次を保持する。

- incremental decoderとCRC state
- 現在受信中のframeまたはlogical message
- 直前に受理したsequence
- OEP coreへdelivery可能かを示す状態

ACK喪失時にresponse自体を再送するため、直前のOEP responseをcacheすることは必須としない。bindingはrequest DATAの重複deliveryを防ぎ、responseは反対方向の独立したDATA frameとして自身のACKを得るまでsender側に保持する。

OEP response生成前にprobeがresetまたはconnectionを失った場合は、transport再送だけでは回復できない。

## Messageとframeの関係

最小UART bindingでは、一つのbounded OEP logical messageを一つのUART DATA frameへ格納する案を優先する。

これにより、複数frameを完全に再構成するための大きなbuffer、fragment bitmapおよび途中message timeoutを最小実装へ要求せずに済む。

大きな機能dataは、OEP側で意味を持つ複数のbounded data unitとして表現する。将来、一つのlogical messageを複数UART frameへfragment化するprofileを追加する場合も、その再構成はbinding内で行い、不完全messageをOEP coreへ渡さない。

## Flow control

stop-and-waitでは、receiverがACKを返すまでsenderが次のDATAを送らないこと自体が基本的なflow controlになる。

ただし、次を別途扱う必要がある。

- ACKと反対方向DATAが同時に送信される場合
- OSまたはUSB-UART bridgeが複数frameを先行bufferする場合
- UART hardware RX bufferのoverflow
- OEP coreが長時間割込みまたは受信処理を行えない場合
- baud rateに処理速度が追いつかない場合

hardware RTS/CTS等を使用できる実装は利用してよいが、最小UART bindingの前提にはしない。

双方向DATA、local TX queue、ACK優先およびhalf-duplexとの切り分けは[UART duplexとflow control候補](uart-duplex-flow-control.ja.md)に示す。

## Timeoutと速度

ACK timeoutは、固定millisecond値だけでなく、少なくとも次に依存する。

- baud rateとline setting
- 最大frame wire length
- UART bridgeとOS scheduling
- receiverがframe検査とqueue確保を行う時間
- 送受信方向の切替時間

transport ACKはOEP操作完了を待たないため、機能操作のtimeoutとは分離できる。

retry回数、timeout計算、backoffおよびconnection failureへ移行する条件は未決である。低速UARTで正常frameを早すぎるtimeoutにより重複送信し続けないようにする。

timerの種類、wire時間を用いる計算基準およびretry後の回復境界は[UART timeoutと回復model候補](uart-timeout-recovery-model.ja.md)に示す。

## Throughputへの影響

stop-and-waitはcontrol messageを単純かつ小さい状態で確実に運びやすい一方、round-trip latencyがthroughputを制限する。

UART line上の理論byte rateだけをbinding性能として扱わず、ACK、framing、escaping、turnaroundおよびretryを含む実効値を考える。

高throughput data flowでは、将来次を追加候補にできる。

- 複数frameのwindow
- cumulative ACK
- 一方向data用のcredit
- connectionが十分信頼できる場合のdetect-only profile
- OEP data unitごとの欠落通知と機能固有回復

これらを最小control channelへ必須化しない。

## HID、CDC、TCPおよびUSB vendorとの関係

stop-and-waitはUART bindingの候補であり、すべてのconnection binding上へ同じACK frameを重ねる要求ではない。

- USB control/bulkはUSB下位層のretryと完全性を利用する
- HID feature reportはcontrol transferの完了またはfailureを利用する
- TCPは順序付きbyte streamと再送を利用するが、OEP message framingは別途必要になる
- CDCはUSB側の完全性を利用できるが、byte stream framingは必要になる

各bindingがOEP coreへ同じ抽象channel保証を提供できれば、内部方式は異なってよい。

## Failure境界

| 状況 | 主に扱う層 |
|---|---|
| UART byte破損、frame欠落、ACK喪失 | UART binding |
| retry上限超過、再同期不能 | UART bindingがtransport failureとして上位へ通知 |
| 正常frame内のunknown core operation | OEP共通protocolがrejected response |
| request parameterが機能制約外 | 個別機能または共通request modelがrejected response |
| ACK後に操作実行が失敗 | OEP outcome/failure |
| response受信前の接続喪失 | 操作状態不明。OEP recoveryの対象 |
| reset後にhostがrequestを再実行 | binding retryではなく新しいOEP request |

## 暫定適合方針

初期UART bindingについて、次を暫定方針とする。

- control messageではstop-and-waitによるbinding-level再送と重複抑止を第一候補とする
- transport ACKとOEP responseを分離する
- 一つのconnection epoch内で同じframeをOEP coreへ複数回deliveryしない
- epochを越えたexactly-onceを主張しない
- 一つのOEP logical messageを一つのUART DATA frameへ収める最小profileを設ける
- 大量data向けのwindowまたは別profileは後から検討する
- HID、TCP等へUART固有ACKを強制せず、抽象channelの保証だけを揃える

## 比較実装による中間結果

[非規定のUART binding比較実装](../experiments/uart-binding/README.ja.md)で、最大32 byte payloadのframingとstop-and-waitを試作した。

host上では、frame破損、byte欠落・挿入、ACK喪失、receiver busyおよびretry上限を試験し、破損または再送されたframeをOEP coreへ重複deliveryしないことを確認した。

ATmega328P向けの測定用ELFでは、明示lengthのdetect-onlyがFlash 1,294 byte / static RAM 94 byte、delimiter-derived length、stop-and-wait、epoch同期およびpartial frame abortを含む構成がFlash 2,696 byte / static RAM 150 byteだった。差はFlash 1,402 byte / static RAM 56 byteである。Arduino core、UART driver、timerおよびOEP coreは含まないため、最終実装量ではなく候補間の中間比較として扱う。

host-arduino-core上では、epoch成立前のDATA拒否、SYNC-ACK喪失、同一tokenの冪等性、異なるtokenによるsequence初期化、片側resetおよび古いframeの無視を確認した。この結果から、初期UART control channelの第一候補はstop-and-waitとhost主導epoch同期の組合せを維持する。ただし、実UART上のresetとbuffer挙動は未検証である。

## 次の検証

比較実装の次段階として、Arduino Uno R3級の実機または実UART経路で少なくとも次を測る。

- 正常時のbootstrap latencyとACK turnaround
- probe resetとhost再同期
- 115200 baudその他の候補速度での実効throughput
- 遅延した旧frameが新しいepochへ混入しないこと
- 双方向DATAが近接した場合の動作

実測前にCRC種別、delimiter encoding、sequence幅およびretry回数をprotocol仕様として固定しない。

## この文書で決めないこと

- COBS、SLIP、HDLC型その他のframing選択
- CRC方式とfield配置
- ACK/NAK frameの具体形式
- transport sequenceの幅
- epoch tokenの幅と生成方法
- timeout、retry回数およびbackoff
- 既定baud rateとbaud変更手順
- UART以外へのstop-and-wait適用
- windowed data transferの方式
