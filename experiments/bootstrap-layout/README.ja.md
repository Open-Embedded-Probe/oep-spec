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
| B: compact core | 404 byte | 17 byte | 16 byte | 1 |
| C: fixed record | 404 byte | 10 byte | 9 byte | 2 |

static RAMには共有report bufferと1 byteの測定用sinkを含む。候補Bのhandler symbolは154 byte、候補Cは152 byteだったが、二つのoperationを呼ぶ測定harnessを含むELF全体のFlashは同じだった。

この実験では候補Cに、二往復目で16 bitのmessage上限と8 bitのin-flight上限を返す仮recordを追加した。これは比較を同じ情報量に揃えるための測定用形式であり、仕様案の追加ではない。

CH32V003 ABI（`rv32ec` / `ilp32e`）向けのbare ELF比較は、RISC-V compilerを`PATH`へ置いて次で実行する。

```sh
make -C experiments/bootstrap-layout ch32-size
```

xPack RISC-V GCC 14.3.0、`-Os`で、候補Bはtext 516 byte / RAM section 17 byte、候補Cはtext 548 byte / RAM section 13 byteだった。候補Cのhandler単体は12 byte小さいが、二つのoperationを組み立てるharnessを含めると全体ではFlashが32 byte増えた。startup、rv003usb、interruptおよびUSB endpoint stateは含まない。

## rv003usbとのbuild統合

`rv003usb-integration`は、HID descriptor、EP0で8 byteずつ受け取るSET_REPORT callback、共有report buffer、仮parserおよびGET_REPORT callbackをrv003usbへ組み込む。実機へflashせず、候補B/Cのfirmware ELFを比較する。

```sh
cd experiments/bootstrap-layout/rv003usb-integration
PATH=/path/to/riscv-toolchain/bin:$PATH \
make compare RV003USB_DIR=/path/to/rv003usb \
  CH32FUN=/path/to/ch32fun/ch32fun
```

rv003usb `5cddcd5e1d46`、ch32fun `618bba58c615`、xPack RISC-V GCC 14.3.0、`-Os -flto`による結果:

| 仮候補 | Flash | RAM | report buffer | exact limitまでの往復 |
|---|---:|---:|---:|---:|
| B | 2,396 byte | 112 byte | 16 byte | 1 |
| C | 2,364 byte | 108 byte | 9 byte | 2 |

候補Cは統合firmware全体でFlash 32 byte、RAM 4 byteを削減した。RAM差がbuffer差の7 byteより小さいのはsection alignmentと周辺stateを含むためである。USB pin、仮VID:PID、descriptorおよびcallbackはbuild比較用であり、列挙、SET/GET_REPORTの実動作、host API差、busy、連続requestおよびresetは未検証である。
