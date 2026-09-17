# Open Embedded Probe — 最小connection channel候補

状態: **実装事実に基づく検討案**。この文書は、CH32V003 software USB HIDとArduino Uno R3級UARTを最小実装の検証候補として、connection bindingがOEP共通protocolへ渡す最小channelを整理する。

この二つのplatformへの対応、最小message長、framing、CRC、識別子幅およびwire encodingはまだ決定しない。記載する実装値をOEP全体の固定上限として採用しない。

調査日は2026-09-17。参照したsource revisionは、rv003usb `5524a833c656a6007fca9f6c947fd49ddcc16eb6`、ArduinoCore-avr `11b9130371e8447920edb65a75706a6c951e51fc`である。

## 確認した実装事実

### CH32V003 software USB HID

[rv003usb](https://github.com/cnlohr/rv003usb/tree/5524a833c656a6007fca9f6c947fd49ddcc16eb6)は、CH32V003上でUSB low-speed deviceをsoftware実装する。project READMEは、基本HID構成が約2 KiBのcodeであり、HID feature request、control setupおよびinterrupt endpointを実装できるとしている。

現行の[rvswdio_programmer/usb_config.h](https://github.com/cnlohr/rv003usb/blob/5524a833c656a6007fca9f6c947fd49ddcc16eb6/rvswdio_programmer/usb_config.h)では、次を確認できる。

- EP0の最大packet sizeはUSB low-speedに従い8 byte
- vendor-defined HID feature reportを使用する
- report countが異なる複数のreport IDを定義する
- interrupt IN endpointもdescriptorに存在するが、sizeは1 byteで「使用しない」と記載されている

現行の[rvswdio_programmer.c](https://github.com/cnlohr/rv003usb/blob/5524a833c656a6007fca9f6c947fd49ddcc16eb6/rvswdio_programmer/rvswdio_programmer.c)では、次を確認できる。

- hostとの主なcommand交換にHID feature reportのcontrol transferを使用する
- control transferのdataを8 byte単位でscratch bufferへ受信する
- request用とresponse用に、それぞれ264 byteのbufferを持つ
- request処理中は新しいdataへNAKを返す
- main loopが受信済みcommand bufferを処理し、response bufferを準備する
- hostは別のfeature report取得によってresponseを読む

したがって、この実装は概念上次の流れに近い。

```text
host                         CH32V003
  | -- SET feature report ---> |  requestを8 byte packetへ分割
  |                             |  一つのbufferを処理
  | <-- GET feature report ---- |  responseを8 byte packetへ分割
```

これはrv003usbが対応できる唯一の方式ではなく、OEP HID bindingをこの既存protocolへ合わせる決定でもない。また、現行upstreamにはfeature report responseに関する[未解決issue](https://github.com/cnlohr/rv003usb/issues/140)があるため、この実装をそのままOEPの信頼性根拠とはしない。

### Arduino Uno R3級UART

Arduino公式の[UNO R3 datasheet](https://docs.arduino.cc/resources/datasheets/A000066-datasheet.pdf)では、application MCUであるATmega328Pは16 MHz、32 KiB flash、2 KiB SRAMを持ち、USB serial bridgeにはATmega16U2を使用する。

標準[ArduinoCore-avr HardwareSerial](https://github.com/arduino/ArduinoCore-avr/blob/11b9130371e8447920edb65a75706a6c951e51fc/cores/arduino/HardwareSerial.h)は、RAMが1 KiB以上の対象で既定のUART RX bufferとTX bufferを各64 byteとする。これはcore設定で変更できる実装値であり、OEPの固定上限ではない。

ATmega328P applicationから見ると、hostとの通信はATmega16U2等のbridgeへ接続されたUART byte streamである。USB CDC transferの境界は、ATmega328P側のOEP message境界として見えない。

UART側では次が起こり得る。

- 任意位置でreadが分割または結合される
- byteの破損、欠落、挿入またはoverrun
- baud rate、data bit、parityまたはstop bitの不一致
- host側port openに伴うresetや接続状態の変化
- RX/TX bufferと処理速度の差によるflow control不足

概念上の流れは次に近い。

```text
host                         ATmega328P
  | ===== UART byte stream ===> |  frame境界をbindingが復元
  | <==== UART byte stream ==== |  responseもframe化して返す
```

## 二つの候補から分かること

| 観点 | CH32V003 HID候補 | Uno R3級UART候補 |
|---|---|---|
| 下位model | host主導control transaction | 境界のないbyte stream |
| 小さい転送単位 | EP0で8 byte | UARTのbyte |
| message境界 | feature reportで表現可能 | binding framingが必要 |
| backpressure | NAKまたはhost polling | buffer、送信停止またはflow control |
| 自発送信 | hostの取得操作が必要になり得る | byte送信自体は可能 |
| 破損検出 | USB下位層がpacketを検査 | UART binding側の検査が必要 |
| 最小同時処理 | 一つで成立している | 一つに制限可能 |
| RAM上の注意 | 既存実装は264 byte bufferを2本使用 | core既定UART bufferだけで128 byte使用 |

したがって、最小OEP実装へ大きなmessage、複数同時request、自発notification、全messageの二重bufferまたは永続activityを無条件に要求しない。

## 最小抽象channel候補

各connection bindingは、下位通信の違いを吸収し、OEP共通protocolへ次の操作を提供する候補とする。

```text
receive(connection context)
    -> complete logical message
    -> transport failure
    -> connection closed

send(connection context, complete logical message)
    -> accepted by binding
    -> transport failure
```

これはsoftware APIを規定する擬似表現ではない。共通protocolとconnection bindingの責任境界を示す。

### Channelの基本保証候補

一つのconnection context内では、次をbindingの責任とする。

1. logical messageの境界を復元する
2. transport fragmentを結合してから上位へ渡す
3. 検出した破損messageを正常messageとして渡さない
4. binding内で再送する場合、同じlogical messageを重複して上位へ渡さない
5. 回復できない欠落、破損または切断をtransport failureとして示す
6. 下位通信が提供する順序保証と、bindingが上位へ提供する順序保証を明確にする
7. 受信可能量を超えたdataを黙って正常受信したことにしない

通信が失われる直前にmessageが相手へ届いたかどうかまで、常に確定できるとは限らない。channelの完全性保証と、OEP requestを相手が実行したかの保証は区別する。

### Response経路

OEP共通protocolは、受信messageと共にconnection contextを受け取る。requestに対するresponseは同じcontextを指定して返す。

bindingは、同じcontext内で適切な物理方向へ変換する。

- HID feature reportでは、hostのSETとGETを一つのlogical request/response関係として扱い得る
- UART、CDCおよびTCPでは、同じportまたはconnection上の反対方向へ返す
- USB vendor interfaceでは、同じlogical connectionを構成するOUTとINを対応付ける

別interfaceへresponseを送るには、別経路を明示的に確立する規則が必要である。

## 最小実装profile候補

最小実装は、次の制限を正当に開示できるようにする。

- 同時に処理できるrequestは一つ
- requestを受けてからresponseを返すまで、次のrequestを受け付けない
- probeからhostへの自発送信を行わず、host pollingまたは再取得を使用する
- activity、notificationおよびnative data flowを実装しない
- 一つのlogical messageに小さい上限を設ける
- 大量dataを一つのmessageで扱わず、機能定義に従う複数のbounded data unitとして扱う

これらはすべての実装へ課す制限ではない。高機能なbindingは複数request、非同期送信および高throughput data flowを追加できる。

## Bootstrap前に必要な共通上限

probe固有の最大message長は、提供情報を取得した後に開示できる。しかし、その提供情報を取得する最初のrequestとresponse自体は、事前に共有された上限内でなければならない。

したがって、少なくとも次のいずれかが必要になる。

- 全connection bindingが運べる小さいbootstrap message上限を共通に定める
- bindingごとにbootstrap上限を定め、共通protocolのendpoint確認をその範囲へ収める
- endpoint確認を複数の小さいmessageへ分割して取得できるようにする

CH32V003またはUno R3級を考慮して具体的なbyte数を決めるには、OEP header、identity、互換性情報およびfailure表現の最小候補を実際に配置して比較する必要がある。

## 大量dataの扱い

transport fragmentationだけで任意に大きなlogical messageを作ると、受信側へ同じ大きさの再構成bufferを要求しやすい。

そのため初期方向として、次を区別する。

- **transport fragment** — 一つのbounded logical messageを運ぶためにbindingが分割し、上位へ見せない
- **OEP data unit** — 共通protocolまたは機能定義が認識するboundedなdata単位
- **data flow** — 複数data unitの順序、完了およびfailureを扱う論理的な流れ

小さな実装はtransport fragmentを一つの小さいbufferへ再構成できる。大きな結果やstreamを持つ機能は、全体を一つのlogical messageへ入れず、複数data unitとして処理できる。

## UART bindingで追加検討する項目

UARTで最小抽象channelを提供するには、少なくとも次を決める必要がある。

- frame開始と終了またはlength
- 任意payloadを運ぶescapeまたは等価な方法
- headerとpayloadの破損検出範囲
- 破損またはbyte欠落後の再同期
- frame sequence、acknowledgement、再送および重複抑止の要否
- 最大frame長と受信bufferの関係
- 既定baud rateとline setting
- baud rate変更の合意、切替時点および復帰方法
- flow controlがない場合の最大連続送信量
- port open、DTRその他によるreset後のbootstrap

TCPやCDCへ同じstream framingを利用する場合も、UART向けの再送やCRCを常に重複実装する必要があるかは別途比較する。

## HID bindingで追加検討する項目

HIDで最小抽象channelを提供するには、少なくとも次を決める必要がある。

- feature report、interrupt reportまたは両方の利用範囲
- report IDとOEP messageまたはfragmentの関係
- hostがresponse、notificationまたはdataを取得するpolling方法
- report長を固定するか複数用意するか
- busy時のNAK、STALL、status responseまたは再試行
- 一つのrequestをいつprobe coreへ渡したとみなすか
- control transfer失敗時にrequest実行有無をどこまで判断できるか
- WebHID、hidapiおよび各OS APIで共通に利用できる範囲

既存rvswdio_programmerのreport ID、264 byte bufferおよびcommand形式を、そのままOEPへ採用することは前提としない。

## 次に行う比較

次は、次の最小通信を仮のbyte layoutへ落とし、HIDの小さいreportとUART frameの双方へ載せる。

1. endpoint確認request
2. protocol identityと互換性を返すresponse
3. 最大message長と同時request数を含む最小constraint取得
4. 未知または不正requestへの拒否

この比較ではencodingを採用決定せず、必要な情報量、固定overhead、fragment数、RAM使用量および破損時の挙動を測る。

## この文書で決めないこと

- CH32V003またはUno R3を適合対象またはreference implementationにすること
- 共通またはbindingごとのbootstrap message上限
- request ID、message type、lengthおよびCRCのfield形式
- HIDとUARTで同じwire byte列を使うか
- 一つまたは複数のrequestを同時処理する方法
- polling、notificationおよびactivityの標準化範囲
- UART再送を必須にするか
- HIDのfeature reportとinterrupt reportの選択

次段階では、最小bootstrap exchangeの仮layoutを複数案作り、8 byte単位のHIDと64 byte級bufferのUARTで比較する。
