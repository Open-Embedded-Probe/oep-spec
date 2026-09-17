# UART binding比較実装

状態: **非規定の実験実装**。このdirectoryは、UART control channelについてdetect-only framingとstop-and-waitを比較するためのものであり、wire formatを仕様として割り当てるものではない。

## 実験の範囲

主要なstop-and-wait codecは、次の仮条件を使用する。

- 最大payload: 32 byte
- decode後: 1 byteのtype/sequence、payload、2 byte CRC
- frame境界: COBS系encodingと`0x00` delimiter
- 完全性検査: CRC-16、polynomial `0x1021`、初期値`0xffff`
- 一つのDATA frameに一つのlogical messageを格納

stop-and-wait部分は、1 bit sequence、ACK、timeout時の同一frame再送、retry上限およびreceiver側の重複delivery抑止を実装する。ACKはOEP処理結果ではなく、bindingから上位へmessageをdeliveryできたことだけを表す。

さらにhost/probe roleと、`unsynchronized`、`synchronizing`、`active`、`failed`のepoch stateを持ち、host主導のSYNC / SYNC-ACKを実装する。この実験ではtokenを4 byteと仮置きするが、仕様上の幅ではない。

実時間timer、baud変更および同時送信時の調停はまだ実装していない。`reset_epoch()`はlocal stateを未同期へ戻すだけであり、単独では相手との同期を成立させない。

## 仮frame

decode後のframeは次の形である。

| offset | size | 内容 |
|---:|---:|---|
| 0 | 1 | 上位4 bit: frame type、下位1 bit: sequence |
| 1 | N | payload |
| 1+N | 2 | CRC、little endian |

payload長はdelimiterで確定したdecode後frame長から導出する。COBS系encodingの後にdelimiterを加えるため、最大32 byte payloadのwire長は最大37 byte、payloadなしのACKは5 byteになる。

4 byte tokenを使用する仮SYNC / SYNC-ACKは各9 byteになる。通常DATAにはepoch tokenを付加しない。16 bit explicit length版は比較用codecとして残す。

## 確認した挙動

host testでは次を確認する。

- `0x00`を含むpayloadと、0から32 byteまでの全payload長のround trip
- 一byte破損をCRCで破棄し、次のframeで再同期
- 一byte欠落または挿入後に、次のframeで再同期
- encoded上限超過、malformed COBSおよび空delimiterからの回復
- 最大長frameの全byte位置に対する破損・欠落・挿入後の再同期
- token長不正SYNC、payload付きACKおよびunknown frame typeの無視
- 正常なDATA/ACK交換
- ACK喪失時に再送しても上位へ重複deliveryしない
- DATA破損後のtimeout再送
- receiverが上位へdeliveryできない間はACKせず、再送時に受理
- retry上限後のfailure
- epoch成立前のDATA拒否
- SYNC-ACK喪失時の同一token再送
- 同一tokenのSYNCを受けてもsequence stateを再初期化しないこと
- 異なるtokenによる新しいepochとsequence初期化
- probeだけがresetした場合のDATA拒否と再同期
- 同期中の古いSYNC-ACKおよびDATAの無視
- SYNC retry上限後のfailed state
- partial frame timeout後の残りbyte破棄とDATA retryによる回復
- 双方向で同時に未確認DATAを持つ場合のDATA/ACK直列化
- OEP response DATAがrequest ACKより先に並ぶ場合の相互処理
- 1 bit sequenceが送信順序保存を前提とすることのcharacterization
- COBS系およびSLIP型encoderのbuffer容量境界とguard領域の保持
- 固定seedによる256通りのnoise列後のframe再同期
- payload長0から32 byteの連続送信中にDATA/ACKの欠落・破損とreceiver busyを順番に注入しても、各messageを一度だけdeliveryすること

## ATmega328Pでの中間測定

Arduino Uno R3相当のATmega328Pを対象に、avr-gcc 7.3.0、`-Os`、section garbage collectionありで測定した。数値は小さな測定用`main`とcallbackを含むELF全体であり、Arduino core、UART driver、ring buffer、timerおよびOEP coreを含まない。

| 構成 | Flash | static RAM |
|---|---:|---:|
| detect-only codecの送受信 | 1,294 byte | 94 byte |
| delimiter-derived length codecの送受信 | 1,178 byte | 90 byte |
| SLIP型derived length codecの送受信 | 1,018 byte | 124 byte |
| delimiter-derived codec + stop-and-wait + epoch同期 + partial abort | 2,696 byte | 150 byte |
| explicit detect-onlyとの差 | +1,402 byte | +56 byte |

explicit length版では、epoch同期追加前のstop-and-waitがFlash 2,078 byte / static RAM 146 byte、epoch同期追加時がFlash 2,764 byte / static RAM 156 byte、partial frame abort追加時がFlash 2,816 byte / static RAM 156 byteだった。主要実装をdelimiter-derived lengthへ移した現在値はFlash 2,696 byte / static RAM 150 byteである。差には測定harnessの増減も含む。

16 bit explicit lengthを持つdetect-only codecに対し、delimiterからpayload長を導出するalternativeはFlash 116 byte / static RAM 4 byte小さかった。wire上でも各frameを2 byte削減できた。詳細は[UART frame layout比較](../../docs/uart-frame-layout-comparison.ja.md)に示す。

SLIP型alternativeはderived COBS系よりFlash 160 byte小さい一方、最大wire bufferが37 byteから71 byteへ増え、測定ELFのstatic RAMは34 byte増えた。主要stop-and-wait実装は、固定worst-caseを小さく保つCOBS系のままとした。

測定ELF上の`oep_uart_stopwait` stateは93 byteである。これには37 byteの再送frame、38 byteのincremental decoder領域、4 byte token、roleおよびstateが含まれる。

この差は最終実装の費用ではない。codecとの関数統合、incremental CRC、buffer共有、UART driverとの統合によって変わる。ただし、32 byte payloadのstop-and-wait候補がUno R3の2 KiB SRAMに対して直ちに成立しない大きさではないことは確認できる。

## Wire時間の概算

8-N-1では1 byteを10 bitとして計算する。115200 baudで、error、OS/bridge latency、処理時間およびframe間idleがない場合:

- 10 byte bootstrap request DATA 15 byte + ACK 5 byte: 約1.74 ms
- 14 byte bootstrap response DATA 19 byte + ACK 5 byte: 約2.08 ms
- request/response一往復の合計44 byte: 約3.82 ms
- ACKなしのrequest/response合計34 byte: 約2.95 ms

32 byte DATAとACKは合計42 byteで、payload比率は約76.2%である。line timeだけから求めた一方向上限は約8.78 kB/s（約8.57 KiB/s）だが、stop-and-waitではACK turnaroundとsoftware schedulingが加わるため実効値はこれより低い。

## 通常の検証方法

```sh
cd tests
uv run pytest uart_binding
```

`pytest-embedded`、Arduino CLI backendおよび`lang-ship:host` coreを通し、Arduino libraryとしてbuildしてhost上で実行する。詳しくは[testsの説明](../../tests/README.ja.md)を参照する。

Uno R3向けのcompile確認は次で行う。

```sh
cd tests
uv run pytest uart_binding --profile=uno --run-mode=build
```

`Makefile`は、codec候補とstop-and-waitのAVR footprintを同じ小さいharnessで比較する補助測定にだけ残す。通常のlogic検証経路にはしない。

```sh
make -C experiments/uart-binding avr-size
```

補助測定には`avr-gcc`、`avr-size`および`avr-nm`が必要である。

## 中間結論

stop-and-waitはdetect-onlyより状態とwire overheadを増やすが、破損DATAとACK喪失をbinding内で回復し、同じrequestをOEP coreへ重複deliveryしない性質を小さい実装で実現できた。epoch同期を加えてもATmega328P上のstateは93 byteであり、初期UART control channelの第一候補を維持する。

host-arduino-core上では片側resetと古いframeの排除を確認した。採用を確定する前に、実UART/USB-UART bridge上の片側reset、遅延した旧frame、timeoutとthroughputを検証する必要がある。
