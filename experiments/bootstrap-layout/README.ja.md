# Bootstrap layout比較実装

状態: **非規定の実験実装**。候補Bの16 byte HID feature reportと、候補Cのreport ID付き9 byte固定recordについて、仮parserのcode size、buffer量および往復数を比較する。

field値とresponse形式は[Bootstrap具体layout実験案](../../docs/bootstrap-concrete-layout-experiment.ja.md)から測定用に仮置きしたものであり、protocol割当ではない。

候補Bは一つの16 byte bufferをrequestからresponseへ再利用し、一往復でendpoint確認とexact limitを返す。候補Cは一つの9 byte bufferを再利用するが、endpoint確認後にexact limit用の二往復目を使用する。

host上のlogic検証:

```sh
cd tests
uv run pytest bootstrap_layout_comparison
```

Uno R3向けcompile確認:

```sh
cd tests
uv run pytest bootstrap_layout_comparison --profile=uno --run-mode=build
```

CH32V003向けcompile確認:

```sh
cd tests
uv run pytest bootstrap_layout_comparison --profile=ch32v003 --run-mode=build
```

ATmega328P向け資源量比較:

```sh
make -C experiments/bootstrap-layout avr-size
```

avr-gcc 7.3.0、`-Os`、section garbage collectionありの測定結果:

| 仮候補 | Flash | static RAM | 共有report buffer | exact limitまでの往復 |
|---|---:|---:|---:|---:|
| B: compact core + HID wrapper | 466 byte | 17 byte | 16 byte | 1 |
| C: fixed record | 404 byte | 10 byte | 9 byte | 2 |

static RAMには共有report bufferと1 byteの測定用sinkを含む。候補Bはbinding非依存の10 byte request / 14 byte responseを扱うcore handlerと、16 byte HID report wrapperへ分離した。AVRではcore handlerが142 byte、HID wrapperが74 byteで、候補Cの専用handlerは152 byteだった。HIDだけを比較すると候補Bはwrapper分だけ大きいが、UART等は142 byteのcore handlerを共有できる。

この実験では候補Cに、二往復目で16 bitのmessage上限と8 bitのin-flight上限を返す仮recordを追加した。これは比較を同じ情報量に揃えるための測定用形式であり、仕様案の追加ではない。

CH32V003 ABI（`rv32ec` / `ilp32e`）向けのbare ELF比較は、RISC-V compilerを`PATH`へ置いて次で実行する。

```sh
make -C experiments/bootstrap-layout ch32-size
```

xPack RISC-V GCC 14.3.0、`-Os`で、候補Bはtext 554 byte / RAM section 17 byte、候補Cはtext 548 byte / RAM section 13 byteだった。候補Bのcore handlerは234 byte、HID wrapperは68 byte、候補C専用handlerは252 byteだった。startup、rv003usb、interruptおよびUSB endpoint stateは含まない。

## rv003usbとのbuild統合

`rv003usb-integration`は、HID descriptor、EP0で8 byteずつ受け取るSET_REPORT callback、共有report buffer、仮parser、pending responseを保護するlifecycleおよびGET_REPORT callbackをrv003usbへ組み込む。実機へflashせず、候補B/Cのfirmware ELFを比較する。

```sh
cd experiments/bootstrap-layout/rv003usb-integration
PATH=/path/to/riscv-toolchain/bin:$PATH \
make compare RV003USB_DIR=/path/to/rv003usb \
  CH32FUN=/path/to/ch32fun/ch32fun
```

rv003usb `5cddcd5e1d46`、ch32fun `618bba58c615`、xPack RISC-V GCC 14.3.0、`-Os -flto`による結果:

| 仮候補 | Flash | RAM | USB report buffer | exact limitまでの往復 |
|---|---:|---:|---:|---:|
| B | 2,440 byte | 112 byte | 16 byte | 1 |
| C | 2,432 byte | 108 byte | 12 byte | 2 |

rv003usb `5cddcd5e1d46`は、EP0 OUTの最後のdata packetが1から3 byteの場合、user data callbackへ渡さない。report ID込み9 byteの候補Cは8+1 byteになり、最後の1 byteをparserが受け取れなかった。このため統合候補CはUSB reportを12 byteへpaddingし、8+4 byteとして測定した。仮parserが解釈する先頭9 byteは変えていない。

成立するHID構成同士では、候補Cの削減はFlash 8 byte / RAM 4 byteだった。候補Bのcore handlerはHID wrapperから分離されており、UART等から同じ形式を直接処理できる。lifecycleは未取得responseが次のSET_REPORTで上書きされることを防ぎ、正しい長さのGET_REPORT開始後にだけbufferを次のsetupで再利用可能にする。USB pin、仮VID:PID、descriptorおよびcallbackはbuild比較用であり、列挙、SET/GET_REPORTの実動作、host API差、USB STALLによるbusy通知、resetは未検証である。

## UART bindingとの結合試験

`tests/bootstrap_over_uart`は、候補Bの10 byte core requestをUART stop-and-waitでhostからprobeへ送り、probeがbinding非依存core handlerで14 byte responseを生成して同じconnection上で返す。

probeのdelivery callback内で同期的にresponseを生成するため、wire queueではresponse DATAがrequestのtransport ACKより先に並ぶ。この順序でもhostがresponseと後続ACKを別々に処理し、双方の未確認DATAが最終的に解消することをhost-arduino-core上で確認した。Uno R3とCH32V003 profileでもcompileできる。
