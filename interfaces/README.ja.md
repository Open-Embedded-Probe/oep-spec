# OEP インターフェース

状態: **ガイド**（規範ではない）。名前が `oep.` で始まるインターフェースの文書の一覧。規範はそれぞれの文書で、本体は [OEP core](../docs/oep-core.ja.md) と
[OEP の経路](../docs/oep-transports.ja.md)。番号の唯一の定義は [`registry/oep-v1.toml`](../registry/oep-v1.toml)。凍結までは日本語の文（`.ja.md`）だけを保守する。

インターフェースは、本体の仕組みだけで定義した、名前つきの機能である。ここに並べるのは、project 自身のもので、逆 DNS の名前の代わりに
短い `oep.` の名前を持つ（core §12 の規則 1）。プロトコルの上では、ほかのどのインターフェースとも同じに扱う。probe は持つものを list に出し、
host は list で見つけて要るものだけを使う。

どの target の系統のためのものかは、各文書の冒頭の表と registry の `target` にある（core §12 の規則 8）。

| 文書 | インターフェース |
|---|---|
| [共通部品](oep-if-common.ja.md) | 位置つきのストリーム、debug の connection（インターフェースではない。使うと書いたインターフェースにだけ効く） |
| [線とデバッグ](oep-if-debug.ja.md) | `oep.wire.rvswd`、`oep.wire.swio`、`oep.wire.swd`、`oep.target.riscv-dm`、`oep.target.arm-adi` |
| [コンソール](oep-if-console.ja.md) | `oep.target.console`（framing の dmseq は [target-console-dmseq](target-console-dmseq.ja.md)） |
| [fixture](oep-if-fixture.ja.md) | `oep.fixture.gpio`、`oep.fixture.uart`、`oep.fixture.i2c-target`、`oep.fixture.spi-target` |
| [キャプチャ](oep-if-capture.ja.md) | `oep.fixture.logic`、`oep.fixture.analog`、`oep.fixture.capture-group` |
| [probe の設定](oep-if-probe-config.ja.md) | `oep.probe.config` |
| [plan](oep-if-plan.ja.md) | `oep.probe.plan`（どの役にどの channel を使うかの割り当て） |
| [再起動](oep-if-restart.ja.md) | `oep.probe.restart`（probe 自身の再起動） |
| [リンク](oep-if-link.ja.md) | `oep.probe.link`（線の試験と port_speed） |

インターフェースの書き方（逆 DNS の名前で、誰でも足せる）は core §12。

## 小さいProbeで採用する範囲

名前付き機能がないcoreだけのProbeも有効である。下の最小例は、その機能をlistへ出したときの選択で、全機能を一律に要求する表ではない。
詳しい必須操作・依存・拒否は各規範を参照する。任意のopはops、op以外の能力は各describeの定義で宣言する。

| 機能 | 小さい構成の例 | 一律に要求しないもの |
|---|---|---|
| plan | 選んだfnのpinを割り当てて解放 | 他の拡張へのplan採用 |
| GPIO | set/read、入力mode0 | 出力mode |
| UART | configure/read/status、明示configureからのRXだけ | marks/clear/mark/write、TX queue、暗黙の既定baud初期化 |
| I2C target | 1つの7bit address、小さいframe/queue | stretch、内部pull-up、受信timestampのTLV |
| SPI target | 1つの対応mode、1回のarm、小さいframe/queue | 全mode、LSB先、受信timestamp、全fnとの同時使用 |
| capture | 1トラック/1役割/ワンショットmode1、即時trigger、polling | query/force/calibration/通知/group、mode2を採らない場合のrelease、残るmode。別modeを選ぶ場合はそのmodeの契約を満たす |
| capture-group | 必要なトラックだけを宣言し、bind/start/stop/statusで組を扱う | 通知、全トラックの組合せ。連動trigger/pretriggerは将来の定義へ |
| wire | attach method0/detach/connections、1接続 | scan、複数接続、console、RISC-Vのattach method1 |
| RISC-V target | dmiだけ | halt/resume/reset/block/run/step、チップ固有flash手順 |
| ARM target | transferだけ | read_block/write_block |
| console | open/read/close/streams、1connection/1stream、対応mechanismだけ | marks/clear/mark/write、送信queue、全mechanism |
| probe.config | 対応項目だけ、RAM上の設定 | save/erase/state、不揮発領域。preset/ネットワーク設定は別の定義へ |
| link / restart | 提供する場合だけ採用 | coreへの一律の採用、linkのport_speed |

有限buffer、同じboot内で再利用しない資源ID、session終了時の解放はcoreの共通契約である。
frameへ収まる要求の数と、必要な成功応答の量を別々に確かめる。例えばcaptureのアナログ説明は役割数に応じて増え、最小64byteでは収まらない構成もある。
その場合に重要な結果を省くのではなく、必要なmax_frameを選ぶか、実行前に対応しない要求を断る。
