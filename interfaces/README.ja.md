# OEP インターフェース

状態: **ガイド**（規範ではない）。名前が `oep.` で始まるインターフェースの文書の一覧。規範はそれぞれの文書で、本体は [OEP core](../docs/oep-core.ja.md) と
[OEP の経路](../docs/oep-transports.ja.md)。番号の唯一の定義は [`registry/oep-v1.toml`](../registry/oep-v1.toml)。凍結までは、日本語の文（`.ja.md`）が
作業の文である。英語の文書（`.md`）は古いことがあり、凍結のときに日本語から作り直す。

インターフェースは、本体の仕組みだけで定義した、名前つきの機能である。ここに並べるのは、project 自身のもので、逆 DNS の名前の代わりに
短い `oep.` の名前を持つ（core §13 の規則 1）。プロトコルの上では、ほかのどのインターフェースとも同じに扱う。probe は持つものを list に出し、
host は list で見つけて要るものだけを使う。

どの target の系統のためのものかは、各文書の冒頭の表と registry の `target` にある（core §13 の規則 8）。

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

インターフェースの書き方（逆 DNS の名前で、誰でも足せる）は core §13。
