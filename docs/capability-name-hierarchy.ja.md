# Open Embedded Probe — 能力の名前の階層

状態: **仮置き**（2026-09-24 の議論の合意）。実験してから調整する。名前の規則（`oep.` は予約、独自は逆 DNS）は
[能力の識別方式の比較](capability-identification-comparison.ja.md)、宣言の語彙は
[能力の宣言モデル](capability-declaration-model.ja.md)。

## 切り方の規則

- **名前は host が何に使うかで切る。** probe の MCU のペリフェラル（I2C0 など）は名前に出さない。実装の種類は
  describe の `implementation` で示す。
- **target の知識は host が持つ。** チップごとの手順（flash の書き込み、ローダー、レジスタの意味）は名前にも probe にも
  置かない。probe が持つのは、線の電気的な都合とデバッグの仕組みの癖（再試行、立て直し、タイミング）だけ。
- **アーキテクチャに依る操作を、中立な名前で包まない。** 走行中にメモリを読めるか（CH32 はシステムバスアクセスが
  無く、止めないと読めない。ARM は MEM-AP で読める）、レジスタの番号、実行して停止を待つときの手順、リセットの種類は
  アーキテクチャで違い、どれを使うかは結局 host が target の知識で知っている必要がある。中立な層が欲しければ host の
  ライブラリで作る（probe-rs が ARM と RISC-V の違いを吸収しているのと同じ）。CMSIS-DAP が DP / AP の転送だけを出し、
  上を host に任せて多数のチップに対応しているのと同じ考え方。

## 階層

| 名前 | 中身 |
|---|---|
| `oep.core` | プロトコル自体（confirm、list、describe、セッション） |
| `oep.probe.*` | probe 全体のこと（例: `oep.probe.identity`） |
| `oep.wire.<線>` | target を見つけてつなぐ（scan、attach、detach）。attach は **connection** を返す。`rvswd`、`swio`、`swd`、`jtag` |
| `oep.target.debug.<arch>` | connection を使った実際のアクセス。`riscv`: DMI の読み書き、それを並べてまとめて送る仕組み、速くするための部品（autoexec のブロック読み書き、実行して停止を待つ、halt / resume の再試行）。`arm`: DP / AP の転送、まとめて送る仕組み、ブロック転送 |
| `oep.target.console` | コンソールのストリーム（下記） |
| `oep.fixture.*` | target の周りの I/O。役割は probe から見た名前（`gpio`、`uart`、`i2c-target`、`i2c-controller`、`spi-target`、`capture`、`adc`、`dac`、`power`、NRST などの線） |

- 基本の流れ: `oep.wire.<線>` で attach して connection を受け取り、それを付けて `oep.target.debug.<arch>` で
  アクセスする。
- 線の違いは `oep.wire.*` の中に閉じる。probe が RVSWD しか話せなければ `oep.target.debug.arm` は list に出ない。
  「置けるもの」の違いは list にそのまま現れる。
- target 用の名前は attach の前から list に出る（[target の発見と接続](target-connection-use-cases.ja.md)）。
- CH32 の flash は、host が `oep.target.debug.riscv` の部品で組む（[flash の実験](../experiments/flash-primitives/README.ja.md)）。

## コンソールのストリーム

**host からは同じインターフェース、経路は probe の設定で選ぶ。**

```text
attach(...)                          → connection
console_open(connection, 方式)       → stream   （dmseq / DMDATA / SDI は debug の connection の上に開く）
console_open(UART の割り当て, ...)   → stream   （target の UART は、ピンの割り当ての上に開く）
read(stream, from, max) / marks(stream, ...)   方式に関係なく同じ
```

| データの出どころ | 乗るもの |
|---|---|
| dmseq / DMDATA / SDI | debug の connection（DM のデータレジスタ）。別の物理的な接続は張らない |
| target の UART | ピンの割り当て（plan）。probe の UART を target の UART のピンにつなぐ |
| RTT（将来） | debug の connection（CH32 は止めないとメモリを読めないので実用的でない） |

| 出し先 | 内容 |
|---|---|
| OEP の中のストリーム | 位置付き、マーク付き（[コンソールのストリーム](console-stream.ja.md)）。`oep.fixture.uart` の受信も同じ形 |
| コンソール専用の CDC | OEP の外。Monitor が占有する。口が 1 本の probe には無い |

- ストリームの寿命は乗っているものに従う。debug の connection を detach すればストリームも終わり（detach の
  マーク）、UART の割り当てを解放すれば終わる。セッションの終わりやロックの期限切れでは終わらない。
- Monitor だけを使う場合は、止めずに attach してから dmseq のストリームを開く。書き込みのツールが終わったあとも、
  connection とストリームを残しておけば Monitor は読み続けられる。

## 未決

1. `oep.target.debug.riscv` の「まとめて送る仕組み」の形（DMI の手順のリスト、または実験の `steps` の拡張）。
2. NRST などの線を `oep.fixture` に置くか `oep.wire` に置くか。
3. `oep.probe.*` の中身（identity 以外に何を置くか）。
4. fixture の名前の一覧（どれを `oep.` の標準にするかは決めない方針のまま）。
