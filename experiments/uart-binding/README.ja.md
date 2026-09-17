# UART binding比較実装

状態: **非規定の実験実装**。このdirectoryは、UART control channelについてdetect-only framingとstop-and-waitを比較するためのものであり、wire formatを仕様として割り当てるものではない。

## 実験の範囲

共通codecは、次の仮条件を使用する。

- 最大payload: 32 byte
- decode後: 1 byteのtype/sequence、2 byteのpayload length、payload、2 byte CRC
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
| 1 | 2 | payload length、little endian |
| 3 | N | payload |
| 3+N | 2 | CRC、little endian |

COBS系encodingの後にdelimiterを加えるため、最大32 byte payloadのwire長は最大39 byte、payloadなしのACKは7 byteになる。

4 byte tokenを使用する仮SYNC / SYNC-ACKは各11 byteになる。通常DATAにはepoch tokenを付加しない。

## 確認した挙動

host testでは次を確認する。

- `0x00`を含むpayloadと、0から32 byteまでの全payload長のround trip
- 一byte破損をCRCで破棄し、次のframeで再同期
- 一byte欠落または挿入後に、次のframeで再同期
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

## ATmega328Pでの中間測定

Arduino Uno R3相当のATmega328Pを対象に、avr-gcc 7.3.0、`-Os`、section garbage collectionありで測定した。数値は小さな測定用`main`とcallbackを含むELF全体であり、Arduino core、UART driver、ring buffer、timerおよびOEP coreを含まない。

| 構成 | Flash | static RAM |
|---|---:|---:|
| detect-only codecの送受信 | 1,294 byte | 94 byte |
| codec + stop-and-wait + epoch同期 | 2,764 byte | 156 byte |
| detect-onlyとの差 | +1,470 byte | +62 byte |

epoch同期追加前のstop-and-wait測定はFlash 2,078 byte / static RAM 146 byteだった。同じtoolchainでの差はFlash 686 byte / static RAM 10 byteである。差にはSYNCを実行する測定harnessの増加も含む。

測定ELF上の`oep_uart_stopwait` stateは97 byteである。これには39 byteの再送frame、38 byteのincremental decoder領域、4 byte token、roleおよびstateが含まれる。

この差は最終実装の費用ではない。codecとの関数統合、incremental CRC、buffer共有、UART driverとの統合によって変わる。ただし、32 byte payloadのstop-and-wait候補がUno R3の2 KiB SRAMに対して直ちに成立しない大きさではないことは確認できる。

## Wire時間の概算

8-N-1では1 byteを10 bitとして計算する。115200 baudで、error、OS/bridge latency、処理時間およびframe間idleがない場合:

- 10 byte bootstrap request DATA 17 byte + ACK 7 byte: 約2.08 ms
- 14 byte bootstrap response DATA 21 byte + ACK 7 byte: 約2.43 ms
- request/response一往復の合計52 byte: 約4.51 ms
- detect-onlyのrequest/response 38 byte: 約3.30 ms

32 byte DATAとACKは合計46 byteで、payload比率は約69.6%である。line timeだけから求めた一方向上限は約8.0 kB/s（約7.8 KiB/s）だが、stop-and-waitではACK turnaroundとsoftware schedulingが加わるため実効値はこれより低い。

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

`Makefile`は、detect-onlyとstop-and-waitのAVR footprintを同じ小さいharnessで比較する補助測定にだけ残す。通常のlogic検証経路にはしない。

```sh
make -C experiments/uart-binding avr-size
```

補助測定には`avr-gcc`、`avr-size`および`avr-nm`が必要である。

## 中間結論

stop-and-waitはdetect-onlyより状態とwire overheadを増やすが、破損DATAとACK喪失をbinding内で回復し、同じrequestをOEP coreへ重複deliveryしない性質を小さい実装で実現できた。epoch同期を加えてもATmega328P上のstateは97 byteであり、初期UART control channelの第一候補を維持する。

host-arduino-core上では片側resetと古いframeの排除を確認した。採用を確定する前に、実UART/USB-UART bridge上の片側reset、遅延した旧frame、timeoutとthroughputを検証する必要がある。
