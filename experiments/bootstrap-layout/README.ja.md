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
| B: compact core + HID wrapper | 480 byte | 17 byte | 16 byte | 1 |
| C: fixed record | 404 byte | 10 byte | 9 byte | 2 |

static RAMには共有report bufferと1 byteの測定用sinkを含む。候補Bはbinding非依存の10 byte request / 14 byte responseを扱うcore handlerと、16 byte HID report wrapperへ分離した。AVRではcore handlerが156 byte、HID wrapperが74 byteで、候補Cの専用handlerは152 byteだった。候補Bはcompatible、incompatibleおよびunknown operation rejectionを区別する。HIDだけを比較すると候補Bはwrapper分だけ大きいが、UART等は同じcore handlerを共有できる。

この実験では候補Cに、二往復目で16 bitのmessage上限と8 bitのin-flight上限を返す仮recordを追加した。これは比較を同じ情報量に揃えるための測定用形式であり、仕様案の追加ではない。

候補Bの仮8 bit minimum/maximum revisionは全65,536組をhost上で試験し、revision 1を範囲に含む場合だけcompatibleとなること、compatible/incompatibleの双方で16 bit correlationを保存することを確認した。これは8 bit幅またはrange方式を採用する根拠ではなく、比較実装の境界試験である。

候補B requestの未使用padding 4 byteは、既定実装では内容を無視する。4 byteすべてをzero必須とするstrict variantもbuildした。

| toolchain | padding無視 | zero必須 | 差 |
|---|---:|---:|---:|
| avr-gcc 7.3.0 ELF | 480 byte | 504 byte | +24 byte Flash |
| RISC-V GCC 14.3.0 text | 566 byte | 590 byte | +24 byte text |

どちらもstatic RAMは同じだった。strict paddingはcanonicalな送信形状を検査でき、padding無視は将来利用またはhost API差への許容度が高い。この測定ではpolicyを決定しない。

CH32V003 ABI（`rv32ec` / `ilp32e`）向けのbare ELF比較は、RISC-V compilerを`PATH`へ置いて次で実行する。

```sh
make -C experiments/bootstrap-layout ch32-size
```

xPack RISC-V GCC 14.3.0、`-Os`で、候補Bはtext 566 byte / RAM section 17 byte、候補Cはtext 548 byte / RAM section 13 byteだった。候補Bのcore handlerは246 byte、HID wrapperは68 byte、候補C専用handlerは252 byteだった。startup、rv003usb、interruptおよびUSB endpoint stateは含まない。

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
| B | 2,492 byte | 112 byte | 16 byte | 1 |
| C | 2,460 byte | 108 byte | 12 byte | 2 |
| C + rv003usb短packet実験パッチ | 2,440 byte | 108 byte | 9 byte | 2 |

rv003usb `5cddcd5e1d46`は、EP0 OUTの最後のdata packetが1から3 byteの場合、user data callbackへ渡さない。report ID込み9 byteの候補Cは8+1 byteになり、最後の1 byteをparserが受け取れなかった。このため統合候補CはUSB reportを12 byteへpaddingし、8+4 byteとして測定した。仮parserが解釈する先頭9 byteは変えていない。

report全長1から64 byteについて同じpacket分割条件を走査した。8で割った余りが1、2、3となる長さは最後のpacketがcallbackへ届かず、余り0または4から7の長さは全byteが届く。これはUSBまたはHID一般の制約ではなく、上記rv003usb revisionの`usb_pid_handle_data()`にあるcallback条件のcharacterizationである。

`rv003usb-short-out.patch`でそのcallback条件を`length > 0`へ変更し、候補Cをpaddingなしの9 byte reportとしてbuildした。統合Makefileへ一時コピーのpathを`RV003USB_C`、`-DOEP_RV003USB_SHORT_OUT_PATCHED`を`PATCH_DEFINE`として渡せる。外部checkout自体は変更しない。測定上はpadding版からFlashが20 byte減り、RAMは変わらなかった。このパッチはbuildのみの実験であり、短packetの実受信、zero-length packetおよびrv003usbの他機能との組合せは未検証である。

成立するHID構成同士では、候補Cの削減はFlash 32 byte / RAM 4 byteだった。候補Bはunknown operationをcorrelation付きresponseで拒否する処理も含む。core handlerはHID wrapperから分離されており、UART等から同じ形式を直接処理できる。lifecycleは未取得responseが次のSET_REPORTで上書きされることを防ぎ、正しい長さのGET_REPORT開始後にだけbufferを次のsetupで再利用可能にする。SET_REPORT受信途中またはGET_REPORT送信途中に次のSET_REPORT/GET_REPORT setupが始まった場合は、前のcontrol transferを終了して新しい要求を評価する。4状態と6操作の全24組合せをhost testで確認した。

rv003usbのsource経路では、callbackが拒否を`endpoint->max_len = 0`で表してもSTALLにはならない。SET_REPORTの後続OUT DATAはACKされ、GET_REPORTのINにはzero-length DATAが返る。このため現在の統合試作はbusyをUSB errorとして通知できず、hostがSET_REPORTと対応するGET_REPORTを一組ずつ直列化する必要がある。明示的なbusy応答をOEP dataにするか、bindingまたはUSB stackにSTALL/NAK機構を加えるかは未決定である。USB pin、仮VID:PID、descriptorおよびcallbackはbuild比較用であり、列挙、SET/GET_REPORTの実動作、host API差、resetは未検証である。

誤って二つ目のSET_REPORTを先行した場合も結合試験した。probeは未取得の一つ目のresponseを保護する。hostは次のGET_REPORTで一つ目のcorrelationを識別して消費し、二つ目を再送すると対応するcorrelationのresponseを取得できる。したがってsilent busyからの回復にはcorrelationが有効だが、USB上で二つ目のSET_REPORTが拒否された事実を直接通知するものではない。

rv003usbがHID callbackへ渡す`lValueLSBIndexMSB`も検証する。統合試作はFeature Report type 3、report ID 1、interface 0の組合せ`0x00000301`だけを受け付ける。異なるreport type、report IDまたはinterfaceのGET_REPORTは未取得responseを消費せず、SET_REPORTはOEP parserへ渡さない。

## UART bindingとの結合試験

`tests/bootstrap_over_uart`は、候補Bの10 byte core requestをUART stop-and-waitでhostからprobeへ送り、probeがbinding非依存core handlerで14 byte responseを生成して同じconnection上で返す。

probeのdelivery callback内で同期的にresponseを生成するため、wire queueではresponse DATAがrequestのtransport ACKより先に並ぶ。この順序でもhostがresponseと後続ACKを別々に処理し、双方の未確認DATAが最終的に解消することをhost-arduino-core上で確認した。Uno R3とCH32V003 profileでもcompileできる。

CRCとframeが正常だがbootstrap identityが不正なDATAも試験した。UART bindingはそのDATAを一度だけdeliveryしてtransport ACKを返し、core parserの拒否をtransport retryへ変換しない。仮parserはまだ規定のrejected responseを生成しないため、この試験ではOEP responseを返さず、層の分離だけを確認する。

bootstrap identityとrequest roleが正常でoperationだけが未知の場合は、仮status `unsupported operation`、元のoperationおよびcorrelationを含む14 byte responseを返す。identity不一致による無応答と、認識済みnamespace内のoperation rejectionを実験上区別した。status値とresponse形状は非規定である。

core parserが要求する10 byteと異なる0、9、15および32 byteのlogical messageもUARTで送った。いずれもbindingは一度だけdeliveryしてtransport ACKを返し、core側で無応答のmalformed inputとして拒否した。message長不一致をreceiver busyやtransport破損として再送しないことを確認した。

仮`kind` 256値と、そのrequest role内の仮`operation` 256値も全走査した。認識するrequest role以外はbodyを変更せず無応答とし、認識済みrole内では未知operationも元のoperationとcorrelationを持つrejected responseにできた。この結果は、roleを検証してからrole固有のoperation namespaceを解釈できることを示す。role、operationおよびstatusの値や、未知roleを常に無応答にする規則を採用するものではない。
