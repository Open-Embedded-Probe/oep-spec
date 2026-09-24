# Open Embedded Probe — 能力の名前の階層

状態: **仮置き**（2026-09-24 の議論の合意）。実験してから調整する。名前の規則（`oep.` は予約、独自は逆 DNS）は
[能力の識別方式の比較](capability-identification-comparison.ja.md)、宣言の語彙は
[能力の宣言モデル](capability-declaration-model.ja.md)。

## 切り方の規則

- **最初は必要最低限の機能で作り、困ったら追加する**（2026-09-24 の方針）。使う場面が実際に出ていない機能は、
  名前も操作も先に作らない。

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
| `oep.probe.*` | probe 全体への操作。今は無い（再起動などが必要になったら足す）。probe 全体の宣言と識別情報は `oep.core` の describe |
| `oep.wire.<線>` | target を見つけてつなぐ（scan、attach、detach）。attach は **connection** を返す。`rvswd`、`swio`、`swd`、`jtag` |
| `oep.target.riscv-dm` | connection を使った RISC-V Debug Module へのアクセス。DMI の手順のリスト、速くするための部品（autoexec のブロック読み書き、実行して停止を待つ、halt / resume の再試行） |
| `oep.target.arm-adi` | connection を使った ARM Debug Interface（ADIv5 / v6）へのアクセス。DP / AP の転送のリスト、ブロック転送 |
| `oep.target.console` | コンソールのストリーム（下記） |
| `oep.fixture.*` | target の周りの I/O。役割は probe から見た名前。最初は `gpio`、`uart`（USART を含む）、`capture` だけ（未決 4）。NRST などの線は `gpio` で動かす |

- 基本の流れ: `oep.wire.<線>` で attach して connection を受け取り、それを付けて `oep.target.riscv-dm` /
  `oep.target.arm-adi` でアクセスする。
- **名前は命令セットではなくデバッグ仕様で付ける**（2026-09-24 の合意）。中身は「RISC-V の DM を DMI 経由で叩く」
  「ARM の DP / AP を叩く」ことで、Cortex-M でも Cortex-A でも ADI の層は共通。どの線（RVSWD / SWIO は DMI を直接運び、
  JTAG は DTM を通す）でつないでも、attach のあとは「DMI にアクセスできる接続」になる。仕様の版（RISC-V Debug
  0.13 / 1.0、ADIv5 / v6）は名前に入れない（DMSTATUS / DPIDR を読めば分かる）。CH32 の DM は仕様どおりでない部分
  （QingKe V2 の SWIO、システムバスアクセスが無い、halt の癖）があるが、レジスタの番地と意味は同じなので
  `riscv-dm` として扱い、違いは host の知識と probe の再試行で吸収する。
- 線の違いは `oep.wire.*` の中に閉じる。probe が RVSWD しか話せなければ `oep.target.arm-adi` は list に出ない。
  「置けるもの」の違いは list にそのまま現れる。
- target 用の名前は attach の前から list に出る（[target の発見と接続](target-connection-use-cases.ja.md)）。
- CH32 の flash は、host が `oep.target.riscv-dm` の部品で組む（[flash の実験](../experiments/flash-primitives/README.ja.md)）。

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

1. （決定、2026-09-24）`oep.target.riscv-dm` は **DMI の手順のリスト**（書き、読み、条件を満たすまで読む。最初の
   失敗で止め、済んだ数と読んだ値を返す）を基本にし、速くするための部品を別の操作で足す: ブロック読み書き
   （autoexec）、実行して停止を待つ、halt / resume（CH32 の再発行・立て直し込み）。部品が使う方法（プログラム
   バッファ + autoexec など）は describe で宣言し、合わない target では host がリストで組む。メモリの手順のリスト
   （実験の `steps`）は標準にしない。CMSIS-DAP の `DAP_Transfer` + `DAP_TransferBlock` と同じ 2 本立て。
2. （決定、2026-09-24）**NRST 専用の能力も attach の引数も、v1 では作らない。** probe はどのピンが target の
   リセットかを知らない（配線の知識。治具ならプロファイルがラベルを付け、ばら配線なら host の記録）。debug が
   つながっていればリセットは debug 経由で足りる（riscv-dm の ndmreset、arm-adi は host が AIRCR の SYSRESETREQ を書く）。
   線を動かす必要がある場面（PINRSTF を見る UIAPduino のブートローダ、リセットの挙動の試験、debug の無い target の
   EN / IO0）は `oep.fixture.gpio` のオープンドレインのパルスで行う。debug がつながらなくなった target の回復は、まず
   `oep.fixture.power` の電源の入れ直しで対応し、「リセットしながら attach」は実際に困る target が出てから足す。
3. （決定、2026-09-24）**probe 全体の宣言と識別情報は `oep.core`（fn 0）の describe の TLV で返す。** `oep.probe.*` は
   今は作らない。識別情報はファームの版、機種の名前、**個体の番号**（CH340 の classic ESP32 は USB のシリアル番号を
   持たず、UART 直結や IP 経由には USB の記述子が無い。ESP32 の MAC や RP2350 の flash の UID のように probe 自身が
   返せば、transport によらず host の記録と照合できる）。confirm のあと fn 0 の describe を読めば probe について
   必要なことがそろう。LED は `LED` のラベルを付けたピンとして `oep.fixture.gpio` で動かす。probe の再起動などの
   probe 全体への操作は、必要になったら `oep.probe.*` として足す（名前は list で見つかるので、あとから足しても
   壊れない）。
4. （決定、2026-09-24）v1 を作り始めるときの fixture は、今の試験で使っているものだけにする。BASIC として確定させる
   意味ではなく、実装を始めるための仮の名前。

   | 名前 | 理由 |
   |---|---|
   | `oep.fixture.gpio` | 使う場面（ピンの試験、ADC の入力を H/L で与える）と 2 実装以上がある |
   | `oep.fixture.uart` | 同上（Serial の試験、UART のコンソール） |
   | `oep.fixture.capture` | 同上（I2C の線の証拠、PWM の測定） |
   | `io.github.ch32-riscv-ug.esp32.i2c-target` / `.spi-target`（独自） | 2 実装はあるが、どちらも ESP-IDF のスレーブドライバで、その癖（I2C は NACK で終わった転送でもフレームが出る、など）を引きずる。ESP-IDF でない 2 実装目（Pico の PIO など）が出るまで独自の名前 |

   ADC、DAC、電源、I2C controller は、使う場面が出てから作る。

   **USART は `oep.fixture.uart` の中で扱う。** パリティ、ストップビット、9 bit は設定の引数、半二重と BREAK の
   送信・検出は features のビット。同期モード（クロックの線）、IrDA、スマートカードは、必要になったら任意の役割
   `CK` や features のビットで足し、名前は分けない。最初に作るのは非同期の送受信だけ。
