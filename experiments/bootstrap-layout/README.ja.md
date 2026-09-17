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
